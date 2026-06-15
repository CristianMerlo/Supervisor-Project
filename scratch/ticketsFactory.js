//TODO: esta mostrando todos los canales de tickets, no solo los del usuario logueado. Revisar endpoint y filtros
module.factory("ticketsFactory", function ($http, exceptions, authMz, geolocationFactory) {
    var interfaz = {
        // Consulta a la api para traer resumen o detalle
        // user_ids, channel_id, ticket_view, is_summary
        getTickets: function (params = {}) {
            console.log("params: ", params);

            return new Promise((resolve, reject) => {
                $("#loading").show();

                geolocationFactory.getCurrentLocation().then(function (location) {
                    // Fusiona los datos de geolocalización con los parámetros proporcionados
                    let fusionData = {
                        ...geolocationFactory.trackingData,
                        ...params, // Se incluyen solo las propiedades presentes en params
                    };
                    console.log("fusionData: ", fusionData);
                    $("#msg-load").html("Buscando información de Tickets...");
                    $http({
                        method: "GET",
                        url: API_URL + "tickets",
                        params: fusionData,
                        headers: { Authorization: "Bearer " + authMz.loginInfo.access_token },
                    }).then(
                        function successCallback(response) {
                            resolve(response.data);
                        },
                        function errorCallback(response) {
                            reject(
                                exceptions.handleError(response.status, response.message, interfaz.getTickets, params)
                            );
                        }
                    );
                });
            });
        },

        // recibe el "channel.tickets" y devuelve la cantidad excedidos
        getOutOfDate: function (priorities, priority_id) {
            cont = 0;
            for (let priority in priorities) {
                let states = priorities[priority];
                for (const [key, value] of Object.entries(states)) {
                    if (key == priority_id) {
                        cont += value.length;
                    }
                }
            }
            return cont;
        },
        // parsea la fecha de un numero a dias horas y minutos
        dateToStringByType: function (num, max) {
            if (!Number.isFinite(num) || num <= 0) {
                return "0m.";
            }

            const minutosTemp = Math.trunc(num % 60);
            const minutos = minutosTemp > 0 ? minutosTemp + "m." : "";

            if (max >= 1440) {
                const diasTemp = Math.trunc(num / 1440);
                const dias = diasTemp >= 1 ? diasTemp + "d. " : "";
                const horasTemp = Math.trunc((num % (60 * 24)) / 60);
                const horas = horasTemp >= 1 ? horasTemp + "h. " : "";
                const out = dias + horas + minutos;
                return out ? out : "0m.";
            }

            const horasTemp = Math.trunc(num / 60);
            const horas = horasTemp >= 1 ? horasTemp + "h. " : minutos + "m.";
            const out = horas + minutos;
            return out ? out : "0m.";
        },

        // parsea la fecha de un numero a horas y minutos
        dateToString: function (num) {
            if (!Number.isFinite(num) || num <= 0) {
                return "0m.";
            }

            const diasTemp = Math.trunc(num / 1440);
            const dias = diasTemp >= 1 ? diasTemp + "d. " : "";
            const horasTemp = Math.trunc((num % (60 * 24)) / 60);
            const horas = horasTemp >= 1 ? horasTemp + "h. " : "";
            const minutosTemp = Math.trunc(num % 60);
            const minutos = minutosTemp > 0 ? minutosTemp + "m." : "";
            const out = dias + horas + minutos;
            return out ? out : "0m.";
        },

        // promedia los tiempos de resolucion de tickets de una prioridad en un grupo de sucursales
        storesPriorityAverage: function (stores) {
            acum = 0;
            cont = 0;
            if (stores) {
                for (const [clave, valor] of Object.entries(stores)) {
                    acum += valor;
                    ++cont;
                }
            }
            return acum / cont;
        },

        averageByStore: function (stores, store_id) {
            avg = 0;
            for (const [key, value] of Object.entries(stores)) {
                if (key == store_id) {
                    avg = value;
                }
            }
            return avg;
        },

        markTicketAsResolved: function (data) {
            $("#loading").show();
            $("#msg-load").html("Marcando ticket como resuelto");
            return new Promise((resolve, reject) => {
                geolocationFactory.getCurrentLocation().then(function (location) {
                    let fusionData = { ...data, ...geolocationFactory.trackingData };
                    $http({
                        method: "POST",
                        url: API_URL + "resolved-tickets",
                        data: fusionData,
                        headers: { Authorization: "Bearer " + authMz.loginInfo.access_token },
                    }).then(
                        function successCallback(response) {
                            resolve(response.data);
                        },
                        function errorCallback(response) {
                            let errorMessage;
                            if (response.status == 422) {
                                errorMessage = response.data.errors;
                            } else {
                                response.data.message;
                            }
                            reject(
                                exceptions.handleError(
                                    response.status,
                                    errorMessage,
                                    interfaz.markTicketAsResolved,
                                    data
                                )
                            );
                        }
                    );
                });
            });
        },

        editTicket: function (data) {
            $("#loading").show();
            return new Promise((resolve, reject) => {
                geolocationFactory.getCurrentLocation().then(function (location) {
                    let fusionData = { ...data, ...geolocationFactory.trackingData };
                    $http({
                        method: "POST",
                        url: API_URL + "tickets/" + data.ticket_id,
                        data: fusionData,
                        headers: { Authorization: "Bearer " + authMz.loginInfo.access_token },
                    }).then(
                        function successCallback(response) {
                            resolve(response.data);
                        },
                        function errorCallback(response) {
                            let errorMessage;
                            if (response.status == 422) {
                                errorMessage = response.data.errors;
                            } else {
                                response.data.message;
                            }
                            reject(
                                exceptions.handleError(
                                    response.status,
                                    errorMessage,
                                    interfaz.markTicketAsResolved,
                                    data
                                )
                            );
                        }
                    );
                });
            });
        },

        // Calificar un ticket resuelto
        reviewResolvedTicket: function (data) {
            $("#loading").show();
            $("#msg-load").html("Calificando ticket");
            return new Promise((resolve, reject) => {
                geolocationFactory.getCurrentLocation().then(function (location) {
                    let fusionData = { ...data, ...geolocationFactory.trackingData };
                    $http({
                        method: "PATCH",
                        url: API_URL + "resolved-tickets/" + data.resolved_ticket_id + "/confirm",
                        data: fusionData,
                        headers: { Authorization: "Bearer " + authMz.loginInfo.access_token },
                    }).then(
                        function successCallback(response) {
                            resolve(response.data);
                        },
                        function errorCallback(response) {
                            let errorMessage;
                            if (response.status == 422) {
                                errorMessage = response.data.errors;
                            } else {
                                response.data.message;
                            }
                            reject(
                                exceptions.handleError(
                                    response.status,
                                    errorMessage,
                                    interfaz.markTicketAsResolved,
                                    data
                                )
                            );
                        }
                    );
                });
            });
        },

        getTicketsStats: function (params) {
            $("#msg-load").html("Cargando información estadística...");

            console.log("los parámetros que paso al factory:", params);

            // Declarar las variables en un ámbito superior
            let startDateCopy = "";
            let endDateCopy = "";

            // Asegurarse que el dato esté en el formato correcto para el endpoint
            if (params.start_date) {
                startDateCopy = formatDate(new Date(params.start_date));
                endDateCopy = formatDate(new Date(params.end_date));
            }

            // Asegurar que siempre es un array
            const queryParams = {
                users_ids: Array.isArray(params.users_ids) ? params.users_ids : [],
                channel_ids: Array.isArray(params.channel_ids) ? params.channel_ids : [],
                store_ids: Array.isArray(params.store_ids) ? params.store_ids : [],
                start_date: startDateCopy,
                end_date: endDateCopy,
            };

            console.log("queryParams: ", queryParams);

            return new Promise((resolve, reject) => {
                $http({
                    method: "GET",
                    url: API_URL + "resolved-tickets/stats",
                    params: queryParams,
                    paramSerializer: function (params) {
                        return Object.keys(params)
                            .map((key) => {
                                if (Array.isArray(params[key])) {
                                    return params[key].map((val) => `${key}[]=${encodeURIComponent(val)}`).join("&");
                                }
                                return `${key}=${encodeURIComponent(params[key])}`;
                            })
                            .join("&");
                    }, // Serialización personalizada para Arrays
                    headers: {
                        Authorization: "Bearer " + authMz.loginInfo.access_token,
                    },
                }).then(
                    function successCallback(response) {
                        console.log("TRAJE LOS STATS DE TICKETS");
                        console.log(response.data);
                        resolve(response.data);
                    },
                    function errorCallback(response) {
                        console.log("Error en la petición:", response);
                        reject(exceptions.handleError(params));
                    }
                );
            });
        },

        // getChildrenStats
        getChannelsStats: function (channelsData) {
            const statsByChannel = {};

            channelsData.forEach((channel) => {
                // Inicializo las métricas para este canal
                statsByChannel[channel.id] = {
                    name: channel.name,
                    resolved_count: 0,
                    closed_count: 0,
                    reopened_count: 0,
                };

                // Recorro cada usuario del canal y acumulo
                channel.users.forEach((user) => {
                    statsByChannel[channel.id].resolved_count += Number(user.resolved_count) || 0;
                    statsByChannel[channel.id].closed_count += Number(user.closed_count) || 0;
                    statsByChannel[channel.id].reopened_count += Number(user.reopened_count) || 0;
                });
            });

            return statsByChannel;
        },

        getStatsDateRange: function (option) {
            var startDate, endDate, label, state;
            var today = new Date();
            switch (option) {
                case "today":
                    startDate = new Date(today);
                    endDate = new Date(today);
                    label = "Hoy";
                    state = "today";
                    console.log("selecciono today");
                    break;
                case "currentMonth":
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                    endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                    label = "Mes en curso";
                    state = "currentMonth";
                    console.log("selecciono currentMonth");
                    break;
                case "previousMonth":
                    startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                    label = "Mes anterior";
                    state = "previousMonth";
                    console.log("selecciono previousMonth");
                    break;
                case "custom":
                    startDate = null;
                    endDate = null;
                    label = "Rango personalizado";
                    state = "custom";
                    console.log("selecciono custom");
                    break;
                default:
                    // En caso de opción no reconocida, se puede definir un valor por defecto.
                    startDate = new Date(today);
                    endDate = new Date(today);
                    label = "Hoy";
                    state = "today";
                    console.log("no selecciono nada");
                    break;
            }
            return {
                label: label,
                startDate: startDate,
                endDate: endDate,
                state: state,
            };
        },

        computeTicketsStatsForRank: computeTicketsStatsForRank,
    };

    // Función helper para computar totales a partir de un array de canales
    function computeTotals(channels) {
        return channels.reduce(
            function (acc, channel) {
                acc.resolved_count += channel.resolved_count || 0;
                acc.closed_count += channel.closed_count || 0;
                acc.reopened_count += channel.reopened_count || 0;
                return acc;
            },
            { resolved_count: 0, closed_count: 0, reopened_count: 0 }
        );
    }

    // Función helper para agregar recursivamente las stats de los hijos (usuarios de cada nodo children)
    function aggregateChildrenStats(children) {
        var agg = {
            totals: { resolved_count: 0, closed_count: 0, reopened_count: 0 },
            channels: [], // Aquí se acumulan todos los canales de los hijos
        };

        children.forEach(function (child) {
            // Procesa los usuarios de este child
            if (Array.isArray(child.users)) {
                child.users.forEach(function (user) {
                    if (user.statsTickets) {
                        agg.totals.resolved_count += user.statsTickets.totals.resolved_count || 0;
                        agg.totals.closed_count += user.statsTickets.totals.closed_count || 0;
                        agg.totals.reopened_count += user.statsTickets.totals.reopened_count || 0;
                        agg.channels = agg.channels.concat(user.statsTickets.channels);
                    }
                });
            }
            // Si el child tiene children, se agregan sus stats recursivamente
            if (Array.isArray(child.children)) {
                var childAgg = aggregateChildrenStats(child.children);
                agg.totals.resolved_count += childAgg.totals.resolved_count;
                agg.totals.closed_count += childAgg.totals.closed_count;
                agg.totals.reopened_count += childAgg.totals.reopened_count;
                agg.channels = agg.channels.concat(childAgg.channels);
            }
        });
        return agg;
    }

    // Nueva función para agregar stats a la estructura Rank y generar la lista de usuarios únicos con sus stats
    function computeTicketsStatsForRank(rank, statsRes) {
        $("#loading").show();
        $("#msg-load").html("Procesando informacion de tickets");

        var uniqueUsersStats = [];

        // 1) Construir mapa userId → canales
        var statsByUser = {};
        statsRes.forEach(function (channel) {
            channel.users.forEach(function (u) {
                statsByUser[u.id] = statsByUser[u.id] || [];
                statsByUser[u.id].push({
                    channel_id: channel.id,
                    resolved_count: u.resolved_count || 0,
                    closed_count: u.closed_count || 0,
                    reopened_count: u.reopened_count || 0,
                    average_rating: u.average_rating != null ? u.average_rating : null,
                });
            });
        });

        function aggregateChannelsById(channelsArray) {
            var agg = {};
            channelsArray.forEach(function (ch) {
                var id = ch.channel_id;
                if (!agg[id]) {
                    agg[id] = {
                        channel_id: id,
                        resolved_count: ch.resolved_count,
                        closed_count: ch.closed_count,
                        reopened_count: ch.reopened_count,
                        ratingSum: ch.average_rating != null ? ch.average_rating : 0,
                        ratingCount: ch.average_rating != null ? 1 : 0,
                    };
                } else {
                    agg[id].resolved_count += ch.resolved_count;
                    agg[id].closed_count += ch.closed_count;
                    agg[id].reopened_count += ch.reopened_count;
                    if (ch.average_rating != null) {
                        agg[id].ratingSum += ch.average_rating;
                        agg[id].ratingCount += 1;
                    }
                }
            });
            var out = [];
            Object.keys(agg).forEach(function (k) {
                var o = agg[k];
                o.average_rating = o.ratingCount > 0 ? o.ratingSum / o.ratingCount : null;
                delete o.ratingSum;
                delete o.ratingCount;
                out.push(o);
            });
            return out;
        }

        function computeTotals(channels) {
            return channels.reduce(
                function (acc, ch) {
                    acc.resolved_count += ch.resolved_count;
                    acc.closed_count += ch.closed_count;
                    acc.reopened_count += ch.reopened_count;
                    return acc;
                },
                { resolved_count: 0, closed_count: 0, reopened_count: 0 }
            );
        }

        function processRank(node) {
            // 4.1) asignar stats propios a cada usuario
            if (Array.isArray(node.users)) {
                node.users.forEach(function (user) {
                    var ownChannels = statsByUser[user.id] || [];

                    user.statsTickets = {
                        channels: ownChannels,
                        totals: computeTotals(ownChannels),
                        channelsPlusChilds: [], // rellenamos abajo
                        totalsPlusChilds: {},
                    };

                    // por defecto iguales a propios
                    user.statsTickets.channelsPlusChilds = angular.copy(ownChannels);
                    user.statsTickets.totalsPlusChilds = angular.copy(user.statsTickets.totals);

                    console.log("Stats añadidos a user", user.id, user.statsTickets);

                    if (
                        !uniqueUsersStats.some(function (u) {
                            return u.id === user.id;
                        })
                    ) {
                        uniqueUsersStats.push(user);
                    }
                });
            }

            // 4.2) procesar recursivamente hijos
            if (Array.isArray(node.children)) {
                node.children.forEach(processRank);

                // agregar stats de hijos
                var childAggChannels = [],
                    childAggTotals = { resolved_count: 0, closed_count: 0, reopened_count: 0 };

                node.children.forEach(function (child) {
                    if (!child.users) return;
                    child.users.forEach(function (cu) {
                        var cpl = cu.statsTickets.channelsPlusChilds,
                            tpl = cu.statsTickets.totalsPlusChilds;
                        childAggChannels = childAggChannels.concat(cpl);
                        childAggTotals.resolved_count += tpl.resolved_count;
                        childAggTotals.closed_count += tpl.closed_count;
                        childAggTotals.reopened_count += tpl.reopened_count;
                    });
                });

                if (Array.isArray(node.users)) {
                    node.users.forEach(function (user) {
                        var merged = user.statsTickets.channels.concat(childAggChannels);
                        user.statsTickets.channelsPlusChilds = aggregateChannelsById(merged);
                        user.statsTickets.totalsPlusChilds = {
                            resolved_count: user.statsTickets.totals.resolved_count + childAggTotals.resolved_count,
                            closed_count: user.statsTickets.totals.closed_count + childAggTotals.closed_count,
                            reopened_count: user.statsTickets.totals.reopened_count + childAggTotals.reopened_count,
                        };
                        console.log("Stats+children para user", user.id, user.statsTickets);

                        if (
                            !uniqueUsersStats.some(function (u) {
                                return u.id === user.id;
                            })
                        ) {
                            uniqueUsersStats.push(user);
                        }
                    });
                }
            }
        }

        // 5) arrancamos
        processRank(rank);

        console.log("rank modificado", rank);

        $("#loading").hide();
        // ahora rank trae statsTickets en cada usuario,
        // y uniqueUsersStats es solo el array de usuarios únicos.
        return { rankWithStats: rank, uniqueUsersStats: uniqueUsersStats };
    }

    function formatDate(date) {
        if (!date) {
            return "";
        }
        var tempDate = new Date(date);
        var year = tempDate.getFullYear();
        // Se suma 1 al mes ya que getMonth() retorna valores de 0 a 11
        var month = (tempDate.getMonth() + 1).toString().padStart(2, "0");
        var day = tempDate.getDate().toString().padStart(2, "0");
        return year + "-" + month + "-" + day;
    }

    return interfaz;
});
