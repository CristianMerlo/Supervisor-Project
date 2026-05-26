import gspread
from google.oauth2.service_account import Credentials

# PONER EL LINK O ID DE LA SABANA AQUÍ
SHEET_URL = "https://docs.google.com/spreadsheets/d/18vwFQb3sNTDqqHdac58o_8carqEMCpNlLpYiT3Ymi1Y/edit?usp=sharing" 

# Base de datos cruda proveída por el usuario
DATOS_CRUDOS = """SIGLA SISTEMA|SIGLA TICKETS|REGIONAL|SUPERVISOR (GTE ZONA)|LOCAL|MAIL|DIRECCION|LOCALIDAD|PROVINCIA|TIPO DE LOCAL|RAZON SOCIAL
FVDP|FVDP|Martin Medina|Iris Ayala|VILLA DEL PARQUE|villadelparque@mostazaweb.com.ar|Cuenca 3070|VILLA DEL PARQUE|CABA|A la calle|TRESOL S.R.L
FSJU|FCSJ3|Martin Medina|Micaela Pardo|SAN JUSTO|sanjusto3@mostazaweb.com.ar|Arieta 3150|SAN JUSTO|BUENOS AIRES|A la calle|Puesto Rico S.A.
FLF2|FLF2|Martin Medina|Micaela Pardo|LAFERRERE 2|laferrere2@mostazaweb.com.ar|Av. Luro 5917|LAFERRERE|BUENOS AIRES|A la calle|MAZZEO MARCELO Y BARREIRO WALTER S. CAP I SECC IV
-|FMRAM|Martin Medina|Micaela Pardo|RAMOS|ramosejia@mostazaweb.com.ar|BELGRANO 86|RAMOS MEJIA|BUENOS AIRES|-|-
FEZE|FEZEA|Martin Medina|Micaela Pardo|EZEIZA|ezeiza@mostazaweb.com.ar|Conquista del Desierto 322|Ezeiza|BUENOS AIRES|A la calle|ABOSBIAN SRL
FMCAN|FMCAN|Martin Medina|Micaela Pardo|CANNING|canning@mostazaweb.com.ar|interseccion ruta 58 y Ruta 16|CANNING|BUENOS AIRES|Auto Mostaza|FGC FUELS MARKETING SA
FMGD|FMGRA|Martin Medina|Micaela Pardo|MONTEGRANDE|montegrande@mostazaweb.com.ar|Leandro Alem 401|Monte Grande|BUENOS AIRES|A la calle|DECHUNES S.R.L.
FZAR|FMZAR|Martin Medina|Micaela Pardo|ZARATE|zarate@mostazaweb.com.ar|Felix Pagola 22|ZARATE|BUENOS AIRES|A la calle|Lyson SRL
-|-|Martin Medina|Micaela Pardo|MERCADO PARAGUAY X 15|-|-|-|-|-|-
FCAB|FCABI|Martin Medina|Iris Ayala|CABILDO|cabildo@mostazaweb.com.ar|CABILDO 2150|CABA|CABA|A la calle|BAYRES MEAT S.R.L
FMCYM|FMCYM|Martin Medina|Iris Ayala|CABILDO 2|cabildo2@mostazaweb.com.ar|CABILDO 2530|CABA|CABA|A la calle|MOSTAZA 2530 S.A.
-|-|Martin Medina|Iris Ayala|AV CORDOBA|-|-|-|-|-|-
FURQ|FMURQ|Martin Medina|Iris Ayala|URQUIZA|urquiza@mostazaweb.com.ar|Av. Triunvirato 4714|CABA|CABA|A la calle|LOS INVENCIBLES S.A
FPPI|FPMPI|Martin Medina|Iris Ayala|PALMAS PILAR|palmasdelpilar@mostazaweb.com.ar|LAS MAGNOLIAS 754|PILAR|BUENOS AIRES|Shopping|AYAM MARCELO ROBERTO
FSIS|FMSIS|Martin Medina|Iris Ayala|SAN ISIDRO|sanisidro@mostazaweb.com.ar|Av. Centenario 302|SAN ISIDRO|BUENOS AIRES|A la calle|BARSI FOODS SA
FMRVP|FMRVP|Martin Medina|Iris Ayala|LA RIOJA|larioja@mostazaweb.com.ar|25 DE MAYO 48|LA RIOJA|LA RIOJA|A la calle|ARLEQUINO SRL
FCAT|-|Martin Medina|Iris Ayala|CATAMARCA|catamarca@mostazaweb.com.ar|Rivadavia 662|S.F. DEL VALLE|CATAMARCA|A la calle|CORCAN S.R.L
FFRA|FFRA|Martin Medina|Paula Martinez|F. ALVAREZ|franciscoalvarez@mostazaweb.com.ar|Gorriti 1077|Moreno|BUENOS AIRES|A la calle|EL SENUELO S.A.S
FMORE|FMMRE|Martin Medina|Paula Martinez|MORENO|moreno2@mostazaweb.com.ar|Bartolomé Mitre 2679|MORENO|BUENOS AIRES|A la calle|EL SENUELO S.A.S
FLUJ|FLUJA|Martin Medina|Paula Martinez|LUJAN|lujan@mostazaweb.com.ar|AV SAN MARTIN 165|LUJAN|BUENOS AIRES|A la calle|ALIMENTOS EXPRESS S.A
FMSVP|FMSVP|Martin Medina|Paula Martinez|SAN MARTIN PEATONAL|smpeatonal@mostazaweb.com.ar|ALBERTO CAMPOS 2045|SAN MARTIN|BUENOS AIRES|A la calle|CORTINA 1444 SRL
FSMA|F3DF|Martin Medina|Paula Martinez|SAN MARTIN AUTO|sanmartinauto@mostazaweb.com.ar|RICARDO BALBIN 2276|SAN MARTIN|BUENOS AIRES|Auto Mostaza|LOS INVENCIBLES S.A
FSJN|-|Martin Medina|Paula Martinez|SAN JUAN|sanjuan@mostazaweb.com.ar|Tucumán Sur 101|San Juan Capital|SAN JUAN|A la calle / Peatonal|Alimentos del Oeste S.R.L
FSJ2|-|Martin Medina|Paula Martinez|SAN JUAN 2|sanjuan2@mostazaweb.com.ar|Av. Libertador Gral. San Martín 1710|San Juan Capital|SAN JUAN|Auto Mostaza|Alimentos del Oeste S.R.L
FTU2|-|Martin Medina|Ailen Perez|TUCUMAN 2|tucuman2@mostazaweb.com.ar|Av. Aconquija 1300|YERBA BUENA|TUCUMAN|A la calle|GASTRONOMIA MODERNA SRL
FTU3|-|Martin Medina|Ailen Perez|TUCUMAN 3|tucuman3@mostazaweb.com.ar|25 DE MAYO 392|S.M. DE TUCUMAN|TUCUMAN|A la calle|DRAS SRL
FTU4|FMTU4|Martin Medina|Ailen Perez|TUCUMAN 4|tucuman4@mostazaweb.com.ar|Av Juan Domingo Peron 1900|YERBA BUENA|TUCUMAN|Shopping|ZONSUR SRL
FTC5|-|Martin Medina|Ailen Perez|TUCUMAN 5|tucuman5@mostazaweb.com.ar|Av. Mate de Luna 4107|YERBA BUENA|TUCUMAN|Auto Mostaza|FELMOR GROUP SAS
FTC6|-|Martin Medina|Ailen Perez|TUCUMAN 6|tucuman6@mostazaweb.com.ar|SOLDATI 26|S.M. DE TUCUMAN|TUCUMAN|Auto Mostaza|REDFOOD SRL
FMTU7|-|Martin Medina|Ailen Perez|TUCUMAN 7|concepcion@mostazaweb.com.ar|San Martin 1563|CONCEPCION|TUCUMAN|Auto Mostaza|GOLDENSIDE S. R. L.
FTC8|-|Martin Medina|Ailen Perez|TUCUMAN 8|tucuman8@mostazaweb.com.ar|Av. 24 de Septiembre 771|S.M. DE TUCUMAN|TUCUMAN|A la calle|PUNTO 24 SRL
MPTG|-|Martin Medina|Ailen Perez|PORTAL TUCUMAN|-|-|-|TUCUMAN|-|-
FMTU9|-|Martin Medina|Ailen Perez|TUCUMAN 9|tucuman9@mostazaweb.com.ar|-|-|TUCUMAN|A la calle|MILON S.A.S
FCAS|FCAST|Martin Medina|Marina Gonzalez|CASTELAR|castelar@mostazaweb.com.ar|Gdor. Inocencio arias 2396|CASTELAR|BUENOS AIRES|A la calle|Parador 71 S.R.L.
FQUP|FMQCA|Hernán Dalto|Hernán Dalto|QUILMES P.|quilmespeatonal@mostazaweb.com.ar|Av rivadavia 49|Quilmes|BUENOS AIRES|Shopping|ACENDRADO FAST FOOD SA
FLP2|FLPCA|Hernán Dalto|Elisabet Gassman|LA PLATA 2|laplata2@mostazaweb.com.ar|calle 47 627 (e 7 y 8)|La Plata|BUENOS AIRES|A la calle|BELNO S.A
FLP3|FLPC3|Hernán Dalto|Elisabet Gassman|LA PLATA 3|laplata3@mostazaweb.com.ar|calle 8 932 (e 50 y 51)|La Plata|BUENOS AIRES|A la calle|GUSPABEL - SOL S.A.
FLP4|FLPC4|Hernán Dalto|Elisabet Gassman|LA PLATA 4|lp4@mostazaweb.com.ar|calle 12 1200 y calle 56|La Plata|BUENOS AIRES|A la calle|FRANUS S.A.
FLP6|FLPC6|Hernán Dalto|Elisabet Gassman|LA PLATA 6|laplata6@mostazaweb.com.ar|calle 137 1598|La Plata|BUENOS AIRES|A la calle|MOSTORNOS SA
FCYB|-|Hernán Dalto|Elisabet Gassman|CITY BELL|citybell@mostazaweb.com.ar|av cantilo 282|City Bell|BUENOS AIRES|A la calle|MEMASES SA
FRDN|FRPNI|Hernán Dalto|Elisabet Gassman|REPUBLICA|republica@mostazaweb.com.ar|Calle 34 entre 12 y 13|La Plata|BUENOS AIRES|A la calle|SOBREMESA SRL
FSDE|FSANT|Hernán Dalto|Brenda Moreno|S DEL ESTERO|portalsantiago@mostazaweb.com.ar|Av ejercito Argentino y rivadavia|Sgo. del Estero|SGO DEL ESTERO|Shopping|GASTRONOMIA MODERNA SRL
FMMSM|FMMSM|Hernán Dalto|Agostina Grigas|MENDOZA CENTRO|avsanmartin@mostazaweb.com.ar|Lavalle 35 piso 5to depto 9|Mendoza Capital|MENDOZA|A la calle|JERAL MOSTAZA SAS
FMMCO|FMMCO|Hernán Dalto|Agostina Grigas|MENDOZA COLON|avcolon@mostazaweb.com.ar|Chile 925 piso 9 depto 6|Mendoza Capital|MENDOZA|Auto Mostaza|ALIMENTOS DEL OESTE S.R.L
FSRM|-|Hernán Dalto|Brenda Moreno|SAN RAFAEL|sanrafael@mostazaweb.com.ar|Hipolito Yrigoyen 1530|San rafael|MENDOZA|Auto Mostaza|FARTRES MDZ S.A
FGON|FGONN|Hernán Dalto|Elisabet Gassman|GONNET|gonnet@mostazaweb.com.ar|Calle 522 esquina 19|La Plata|BUENOS AIRES|Auto Mostaza|TEN POINTS SA
FBER|FMBER|Hernán Dalto|Brenda Moreno|BERAZATEGUI|berazategui@mostazaweb.com.ar|Calle 14 Nro 4936|Berazategui|BUENOS AIRES|A la calle|Mostabera S.A.S
FMRG|FROG|Hernán Dalto|Brenda Moreno|ROTONDA|gutierrez@mostazaweb.com.ar|Avenida presidente Illia N°25|Berazategui|BUENOS AIRES|Auto Mostaza|NINE POINTS S. A.
FLOZ|FLOA|Hernán Dalto|Brenda Moreno|LOMAS AUTO|lomas2@mostazaweb.com.ar|Hipolito Yrigoyen 3916|Lomas Oeste|BUENOS AIRES|A la calle|LOS PROVEEDORES S.R.L
-|FMLCA|Hernán Dalto|Brenda Moreno|LOMAS|-|Fonrouge 111 piso 7 dpto 6|Lomas de Zamora|BUENOS AIRES|-|-
FMWVP|FMWVP|Hernán Dalto|Brenda Moreno|WILDE|wilde@mostazaweb.com.ar|Av. Bartolomé Mitre 6551 (esquina Salcedo)|Wilde (Avellaneda)|BUENOS AIRES|Auto Mostaza|MITRE BURGUER POINT S.A.
FBA1|-|Hernán Dalto|Elisabet Gassman|BARILOCHE|bariloche@mostazaweb.com.ar|-|Bariloche|RIO NEGRO|A la calle|BURIEL GASTRONOMICA SRL
FUSH|FUSHA/FSHU|Hernán Dalto|Brenda Moreno|USHUAIA|ushuaia@mostazaweb.com.ar|shopping Paseo del FUego|Ushuaia|TIERRA DEL FUEGO|Shopping|LOGISTICA Y SERVICIOS S.R.L.
FRGD|FRGRD|Hernán Dalto|Brenda Moreno|RIO GRANDE|riogrande@mostazaweb.com.ar|11 de julio 795|Río Grande|TIERRA DEL FUEGO|Shopping|LOGISTICA Y SERVICIOS S.R.L.
FPSA|-|Hernán Dalto|Fabrizio Bollero|PORTAL SALTA|portalsalta@mostazaweb.com.ar|20 de Febrero 1437|SALTA|SALTA|Shopping|GASTRONOMIA SAN FRANCISCO S.R.L.
FSLI|FSLIB|Hernán Dalto|Fabrizio Bollero|SALTA LIBERTAD|saltalibertad@mostazaweb.com.ar|Av Tavella s/n|SALTA|SALTA|Shopping|ZONSUR SRL
FSVP|-|Hernán Dalto|Fabrizio Bollero|SALTA PEATONAL|saltapeatonal@mostazaweb.com.ar|ALBERDI 242|SALTA|SALTA|A la calle|AMICI VERDE SRL
FSAA|-|Hernán Dalto|Fabrizio Bollero|SALTA AUTO|saltaesquinaauto@mostazaweb.com.ar|-|SALTA|SALTA|A la calle|SABADI S.R.L.
-|-|Hernán Dalto|Fabrizio Bollero|SALTA NOA|-|-|SALTA|SALTA|-|-
FJUJ|-|Hernán Dalto|Fabrizio Bollero|JUJUY|jujuy@mostazaweb.com.ar|Belgrano 563 piso 2 local 308|San Salvador de Jujuy|JUJUY|Shopping|CANDELIA SRL
FSAO|FSAO|Hernán Dalto|Fabrizio Bollero|SALTA ORAN|oran@mostazaweb.com.ar|LOPEZ Y PLANES 585|ORAN|SALTA|A la calle|ZENTA FOOD S.A.S
FPCH|FMPCH|Cecilia Riccadonna|Aylen Crespin|PARQUE CHAC|chacabuco@mostazaweb.com.ar|AV ASAMBLEA 915|CHACABUCO|CABA|A la calle|EZIO S.A
FMCNT|FMCNT|Cecilia Riccadonna|Aylen Crespin|CONSTITUCION|constitucion@mostazaweb.com.ar|AV. BRASIL 1153|CABA|CABA|A la calle|MAYONESA S.R.L
FSPI|-|Cecilia Riccadonna|Aylen Crespin|SPINETTO|spinetto@mostazaweb.com.ar|Adolfo Alsina 2302|CABA|CABA|Shopping|RECCO LUCAS R. Y ALONSO MARTINEZ E. SH
FLA2|FMLAC|Cecilia Riccadonna|Aylen Crespin|LANUS 2|lanus2@mostazaweb.com.ar|9 de julio 1476|Lanus este|BUENOS AIRES|A la calle|MUSTARD SRL
FCQU|FCFQU|Cecilia Riccadonna|Aylen Crespin|CARRE QUILMES|carrefourquilmes@mostazaweb.com.ar|Av la plata 1400|Quilmes|BUENOS AIRES|Shopping|OCTOPUS
FLPA|-|Cecilia Riccadonna|Aylen Crespin|LA PAMPA|santarosa@mostazaweb.com.ar|AV SAN MARTIN 125|SANTA ROSA|LA PAMPA|A la calle|CALDENIA GASTRONOMICA S.R.L.
FMFOR|-|Cecilia Riccadonna|Raúl Ayala|FORMOSA|formosa@mostazaweb.com.ar|-|FORMOSA|FORMOSA|Auto Mostaza|IDAVE SRL
FFLO|FFLOR|Cecilia Riccadonna|Raúl Ayala|FLORES|flores@mostazaweb.com.ar|AV RIVADAVIA 6912|FLORES|CABA|A la calle|MAGRETA SA
FMPRI|FMPRI|Cecilia Riccadonna|Raúl Ayala|PRIMERA JUNTA|primerajunta@mostazaweb.com.ar|AV RIVADAVIA 5576|CABALLITO|CABA|Auto Mostaza|BIG B POINTS S.A
FLIN|FLINR|Cecilia Riccadonna|Raúl Ayala|LINIERS|liniers@mostazaweb.com.ar|AV RIVADAVIA 11576|LINIERS|CABA|A la calle|PARADOR 71
FMONC|FMONC|Cecilia Riccadonna|Raúl Ayala|ONCE|once@mostazaweb.com.ar|AV RIVADAVIA 2261|ONCE|CABA|A la calle|EVOLUCION DRF SRL
FMTER|-|Cecilia Riccadonna|Raúl Ayala|TERRADA|-|Av. Rivadavia 7299|Flores|CABA|-|-
FBOL|FMBLV|Cecilia Riccadonna|Raúl Ayala|BOLIVAR|bolivar@mostazaweb.com.ar|DOMINGO FAUSTINO SARMIENTO 770|BOLIVAR|BUENOS AIRES|A la calle|COMERCIAL BOLIVAR S.A
FMJUN|FMJUN|Cecilia Riccadonna|Raúl Ayala|JUNIN|junin@mostazaweb.com.ar|-|-|BUENOS AIRES|A la calle|COMERCIAL BOLIVAR S.A
FRGA|-|Cecilia Riccadonna|Raúl Ayala|RIO GALLEGOS|riogallegos@mostazaweb.com.ar|Alberdi 174|Rio Gallegos|SANTA CRUZ|A la calle|ANDES FOOD SA
FMPYA|FMPYA|Cecilia Riccadonna|Aylen Crespin|POMPEYA|pompeya@mostazaweb.com.ar|Avenida Saenz 1043|Pompeya|CABA|A la calle|EXPANSION DRF S.R.L
FMP1|FMDQG|Cecilia Riccadonna|Mayra Illuminati|GALLEGOS|losgallegos@mostazaweb.com.ar|BELGRANO 3050|MAR DEL PLATA|BUENOS AIRES|Shopping|FERNANDEZ NATALIA Y DEZUBIZARRETA FERNANDO S.H.
FMP2|FMDQ2|Cecilia Riccadonna|Mayra Illuminati|ALDREY|paseoaldrey@mostazaweb.com.ar|SARMIENTO 2685|MAR DEL PLATA|BUENOS AIRES|Shopping|FERNANDEZ NATALIA Y DEZUBIZARRETA FERNANDO S.H.
FMD3|FMP3|Cecilia Riccadonna|Mayra Illuminati|LA PERLA|laperla@mostazaweb.com.ar|YPOLITO YRIGOYEN 1008|MAR DEL PLATA|BUENOS AIRES|A la calle|VILLA MATILDE MDQ SA
FMDQ4|FMDQ4|Cecilia Riccadonna|Mayra Illuminati|PEATONAL|mardelplata4@mostazaweb.com.ar|SAN MARTIN 2501|MAR DEL PLATA|BUENOS AIRES|A la calle|VILLA MATILDE MDQ SA
FOLAV|FOLAV|Cecilia Riccadonna|Mayra Illuminati|OLAVARRIA|olavarria@mostazaweb.com.ar|AV.COLON 2716|OLAVARRIA|BUENOS AIRES|Auto Mostaza|FERNANDEZ NATALIA Y DEZUBIZARRETA FERNANDO S.H.
FCTA|FTAND|Cecilia Riccadonna|Mayra Illuminati|TANDIL|tandil@mostazaweb.com.ar|PANAMA 353|TANDIL|BUENOS AIRES|Shopping|FERNANDEZ NATALIA Y DEZUBIZARRETA FERNANDO S.H.
FMNVP|-|Cecilia Riccadonna|Yohana Gonzalez|NEUQUEN CENTRO|neuquencentro@mostazaweb.com.ar|Eugenio Perticone 215|NEUQUEN CAPITAL|NEUQUEN|A la calle|TIESUR SAS
MNA|-|Cecilia Riccadonna|Yohana Gonzalez|ALTO COMAHUE|altocomahue@mostazaweb.com.ar|-|-|NEUQUEN|Shopping|GASTRO MANANGET GROUP S.A
FSAF|FSAF|Melisa Castillo|Ranquel Pereiro|SAN FERNANDO|sanfernando@mostazaweb.com.ar|CONSTITUCION 804|SAN FERNANDO|BUENOS AIRES|A la calle|L.C.TRESM S.R.L.
FGBG|FGRBG|Melisa Castillo|Ranquel Pereiro|GRAND BOURG|grandbourg@mostazaweb.com.ar|Av. Eva Duarte de Perón 1461|Grand Bourg|BUENOS AIRES|A la calle|ZVEZA S.R.L
FJCP|FMJCP|Melisa Castillo|Ranquel Pereiro|JOSE C PAZ|josecpaz@mostazaweb.com.ar|Hipólito Yrigoyen 1740|José C Paz|BUENOS AIRES|A la calle|BURGERBUS SA
FSM2|FSM3|Melisa Castillo|Ranquel Pereiro|SAN MIGUEL 3|sanmiguel2@mostazaweb.com.ar|Av. Pres. J.D.Peron 1398|SAN MIGUEL|BUENOS AIRES|A la calle|JULUSA SRL
FMSMA|FMSMA|Melisa Castillo|Ranquel Pereiro|SAN MIGUEL A.|sanmiguelauto@mostazaweb.com.ar|ARTURO ILLIA 3811|SAN MIGUEl|BUENOS AIRES|Auto Mostaza|LOS INVENCIBLES S.A
FMER|FMERL|Melisa Castillo|Ranquel Pereiro|MERLO|merlo@mostazaweb.com.ar|AV LIBERTADOR 487|MERLO|BUENOS AIRES|A la calle|BARSI FOODS SA
FCOR|-|Melisa Castillo|Ranquel Pereiro|CORRIENTES|corrientes1@mostazaweb.com.ar|Av. Raul Alfonsin 3525|Corrientes|CORRIENTES|A la calle|GASTRONOMIA MODERNA SRL
FMRES|-|Melisa Castillo|Ranquel Pereiro|RESISTENCIA|resistencia@mostazaweb.com.ar|Sta Maria de oro y Roca 99|Resistencia|CHACO|A la calle|GASTRONOMIA MODERNA SRL
FSLS|-|Melisa Castillo|Ranquel Pereiro|SAN LUIS|sanluis@mostazaweb.com.ar|Rivadavia 681|SAN LUIS|SAN LUIS|A la calle|GRUPO KRAN SAS
FGUE|FGUE|Martin Medina|Iris Ayala|GUEMES|guemes@mostazaweb.com.ar|guemes 3901|palermo caba|CABA|A la calle|LOS INVENCIBLES S.A
FBOE|FMBOE|Melisa Castillo|Camilo Silva|BOEDO|boedo@mostazaweb.com.ar|Boedo 750|CABA|CABA|A la calle|BOEDO GOURMET SRL
FSTM|FMSTO|Melisa Castillo|Camilo Silva|SAN TELMO|santelmo@mostazaweb.com.ar|DEFENSA 984|SAN TELMO|CABA|A la calle|ROSDA SRL
FAVM|-|Melisa Castillo|Camilo Silva|AV DE MAYO|avenidademayo@mostazaweb.com.ar|avenida de mayo 1402|CABA|CABA|A la calle|Trevago S.A.
FAVM2|-|Melisa Castillo|Camilo Silva|AV DE MAYO 2|avenidademayo2@mostazaweb.com.ar|bernardo de irigoyen 60|CABA|CABA|A la calle|Trevago S.A.
F9DJ|FM9JU|Melisa Castillo|Camilo Silva|9 DE JULIO|9dejulio@mostazaweb.com.ar|av santa fe 1101|CABA|CABA|A la calle|L&A BURGUER SA
FMCYC|FMCYC|Melisa Castillo|Camilo Silva|CALLAO|corrientes3@mostazaweb.com.ar|AV CALLAO 402|CABA|CABA|A la calle|CUANTODEJA SRL
FRAF|FRAFA|Melisa Castillo|Camilo Silva|RAFAELA|rafaela@mostazaweb.com.ar|Sargento Cabral 95|Rafaela|SANTA FE|A la calle|IMPRUV S.A.
FRSF|FSFER|Melisa Castillo|Camilo Silva|RIBERA SANTA FE|santafe@mostazaweb.com.ar|shopping la ribera dique 1|santa fe|SANTA FE|Shopping|IMEGA SRL
FWSF|FSFEW|Melisa Castillo|Camilo Silva|WALMART STA FE|wsantafe@mostazaweb.com.ar|Ruta 168 km|santa fe|SANTA FE|Shopping|IMEGA SRL
FMSFV|FMSFV|Melisa Castillo|Camilo Silva|SANTA FE P.|santafe4@mostazaweb.com.ar|San martin 2601|santa fe|SANTA FE|A la calle|LIBERTAD PRESENTE SA
FPRO|FPROS|Melisa Castillo|Sabrina Orlando|PORTAL ROSARIO|portalrosario@mostazaweb.com.ar|NANSE 323|ROSARIO|SANTA FE|Shopping|IMEGA SRL
FPEL|FMROS|Melisa Castillo|Sabrina Orlando|PELLEGRINI|pellegrinirosario@mostazaweb.com.ar|Pellegrini 1431|Rosario|SANTA FE|Auto Mostaza|PELLEGRINI BESTFOOD SA C
FRSM|FRSM|Melisa Castillo|Sabrina Orlando|ROSARIO SUR|rosariosur@mostazaweb.com.ar|Avenida San Martin|Rosario|SANTA FE|A la calle|GAMISUR S. A
FROA|FORO|Melisa Castillo|Sabrina Orlando|OROÑO|autoorono@mostazaweb.com.ar|Oroño 3120|Rosario|SANTA FE|Auto Mostaza|MADILAGA S.A.
FMSNI|FMSNI|Melisa Castillo|Sabrina Orlando|SAN NICOLAS|sannicolas@mostazaweb.com.ar|Mitre 449|San Nicolás|BUENOS AIRES|Auto Mostaza|PUA NANI SRL
FMPUM|FMPUM|Melisa Castillo|Sabrina Orlando|PUMA|pumarosario@mostazaweb.com.ar|-|-|SANTA FE|Auto Mostaza|FGC FUELS MARKETING SA
FMFUN|-|Melisa Castillo|Sabrina Orlando|FUNES|-|Av. Córdoba 1291|FUNES|SANTA FE|-|-
-|-|Melisa Castillo|Sabrina Orlando|ALTO ROSARIO|-|Junín 501 (Shopping Alto Rosario)|ROSARIO|SANTA FE|-|-
-|-|Melisa Castillo|Sabrina Orlando|CITY CENTER|-|Blvd. Oroño 3152|ROSARIO|SANTA FE|-|-
MFT2|MFT2|-|-|FOOD TRUCK 2|foodtruck1@mostazaweb.com.ar|Ruta 40 km 355|San Juan|SAN JUAN|Food Truck|GASTRO MANANGET GROUP S.A"""

def ejecutar():
    creds = Credentials.from_service_account_file("credentials.json", scopes=["https://www.googleapis.com/auth/spreadsheets"])
    cliente = gspread.authorize(creds)
    try:
        sabana = cliente.open_by_url(SHEET_URL)
        # Verifica si existe la pestaña o la crea
        try:
            hoja = sabana.worksheet("Locales_Maestro")
        except gspread.exceptions.WorksheetNotFound:
            hoja = sabana.add_worksheet(title="Locales_Maestro", rows="1000", cols="15")
        
        # Convierte el string en lista de listas
        filas = [linea.split("|") for linea in DATOS_CRUDOS.strip().split("\n") if linea.strip()]
        
        # Limpia y actualiza
        hoja.clear()
        hoja.update(range_name='A1', values=filas)
        print("[✓] Base de Locales_Maestro actualizada exitosamente con", len(filas)-1, "locales.")
        
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    ejecutar()
