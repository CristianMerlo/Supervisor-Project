# Auditoría y Arquitectura — hermes-core-orchestrator (PIT-V3)

Este documento detalla la planificación técnica y arquitectura del Proyecto Hermes-V3, diseñado para coordinar el mantenimiento de 100 locales comerciales mediante un orquestador que correrá en una máquina local.

## 1. Proceso de Compilación de Historial
**Evolución del Proyecto:**
El requerimiento original planteaba un sistema en la nube (100% Google Apps Script) para 120 locales. Al detectarse el límite de 6 minutos de ejecución de Google, la arquitectura pivotó hacia un hardware local dedicado. 
- Se descartó un cliente ligero (M625) en favor de una **Mini PC Lenovo ThinkCentre M700 Tiny** (Intel Core i3, 8GB RAM, 240GB SSD) corriendo Ubuntu 24.04 LTS. 
- Este nodo físico ejecuta Antigravity IDE como orquestador 24/7, conectado a una **UPS Lyonn CTB-800V** gestionada por `apcupsd` vía USB para telemetría de energía y apagado seguro.

**Enfoques y Tecnologías Rechazados:**
- **Google Apps Script Exclusivo:** Descartado por el timeout de 6 minutos.
- **Servidores VPS (DonWeb/Hostinger):** Rechazados en esta iteración para eliminar el gasto mensual (OPEX) y aprovechar el hardware local potente (8GB RAM).
- **Modelos Locales (Ollama):** Descartados para no saturar los 8GB RAM, delegando la inferencia a APIs en la nube.
- **Integración Office 365:** Vetada por complejidad de autenticación; se usa Gmail corporativo.
- **Renderizado de PDF en Backend:** Descartado; la aplicación PWA V12.5 de los técnicos ya genera el PDF nativamente.

**Núcleo Inmutable del Proyecto:**
Un "Supervisor Digital" autónomo (*headless*) en la Mini PC local que:
- Ingiere PDFs vía Google Drive, Gmail y Chat.
- Extrae datos visuales con Gemini Vision.
- Aplica estrictamente la **Jerarquía Hídrica** (Ej: PPM > 200 o fallo en ablandador = Alerta ROJA forzada).
- Almacena metadatos y vectores en PostgreSQL (`pgvector`) aislando el contexto de cada local (tenant-aware).
- Respalda los archivos físicos en Google Drive mediante `Rclone`.
- Ejecuta un Circuit Breaker de APIs (Groq -> Gemini Pro -> Mistral) para garantizar que nunca deje de responder.

---

## 2. POR QUÉ ESTO FALLARÁ (Simulación Adversarial)
La arquitectura colapsará por **Race Conditions** (Falta de control de concurrencia) y **Cuellos de Botella de Red Doméstica**. 
Al depender de una conexión residencial sin un gestor de colas estricto local, el envío simultáneo de varios PDFs pesados por parte de los técnicos colapsará el puente de subida de Rclone hacia Drive. Escribir directamente en "La Sábana" (Google Sheets) desde múltiples hilos sin bloqueo transaccional (Row Locking) provocará sobreescritura silenciosa de celdas, duplicación de IDs y corrupción de la data. El sistema se congelará por timeout esperando a Google.

---

## 3. Evidence & Uncertainty Calibration
- **Ejecución Local (Lenovo M700 + Ubuntu):** Certeza 1.0. Mitiga los límites de la nube.
- **Ingesta Multicanal (Drive, Gmail, Chat):** Certeza 1.0.
- **Jerarquía Hídrica (PPM > 200 = ROJO):** Certeza 1.0. Prioridad absoluta en la lógica del negocio.
- **Memoria de Largo Plazo (pgvector + Rclone):** Certeza 0.9. Clave para que la IA no mezcle el estado de las cafeteras entre un local y otro.
- **Conectividad Externa (Túneles):** Certeza 0.4 (RIESGO ALTO). No confirmado si se usará Cloudflare Tunnel para exponer la máquina de forma segura al internet.
- **Manejo de Concurrencia (Cola Local):** Certeza 0.5 (RIESGO ALTO). Faltaba definir el uso de SQLite para encolar antes de subir a Sheets.

---

## 4. GAP Analysis & RFI (Preguntas a Resolver)
1. **Gestión de Colas (Queueing):** ¿Se usará SQLite local o Redis en Docker para encolar los reportes entrantes y empujarlos de a uno a Google Sheets (evitando el error HTTP 429)?
2. **Exposición de Red (Ingress):** ¿Se configurará un Cloudflare Tunnel para recibir los webhooks, o se utilizará Long-Polling (donde la PC pregunta cada X segundos a internet)?
3. **Autenticación GCP:** ¿Se usará un archivo de Service Account (.json) para autenticarse contra Google silenciosamente? (Es obligatorio).

---

## 5. BLUEPRINT DE ENTREGABLE (`hermes-core-orchestrator`)

### Arquitectura General & Directorios
**Stack:** Ubuntu 24.04, Node.js (Antigravity), Python 3.12+, PostgreSQL 16 + pgvector, rclone, apcupsd.

```text
/opt/hermes-core-orchestrator/
├── .antigravity/           # Configuración del motor IDE
├── config/
│   ├── .env                # API Keys
│   ├── apcupsd_hook.sh     # Script de intercepción de apagones
│   └── service_account.json# Credenciales headless GCP
├── src/
│   ├── ingestion/          # Listeners de Drive y Gmail
│   ├── parser/             # Gemini Vision extrayendo datos
│   ├── validators/         # Reglas (Pydantic: PPM > 200)
│   ├── db/                 # Conexión pgvector y encolamiento SQLite
│   └── output/             # Sheets updater
├── docker-compose.yml      # Límites de RAM estrictos
└── logs/
```

### Protocolo de Flujo de Datos
- **Triggers:** Cron job interno pollea (revisa) Google Drive/Gmail cada 60s. El demonio `apcupsd` emite `ONBATT` si se corta la luz.
- **Lógica de Procesamiento:** 
  1. Ingesta: PDF descargado y encolado temporalmente en SQLite local.
  2. Extracción: Gemini Vision (o Mistral de respaldo) analiza el PDF.
  3. Auditoría: Aplica la "Jerarquía Hídrica" (altera a CRÍTICO_ROJO si PPM alto).
  4. Vectorización: Guarda semántica en `pgvector`.
  5. Sincronización: Push unificado a Google Sheets y backup físico vía Rclone.

### Configuración Crítica (Tolerancia a Fallos y Energía)
- **Timeouts ciegos:** Ninguna llamada a API externa debe durar más de 15 segundos sin abortar y reencolar.
- **Exponential Backoff:** Si Google bloquea la petición, se congela el reporte en SQLite y reintenta más tarde, liberando el hilo.
- **Hooks de Energía No-Interactivos (`apcupsd_hook.sh`):** Al detectar que la batería de la UPS Lyonn bajó a menos del 15%, el script detiene todas las ingestas de red, cierra las bases de datos de forma segura bajando los contenedores de Docker (`docker-compose down`) y apaga el sistema operativo (`shutdown -h now`), previniendo la corrupción masiva de la base de datos PostgreSQL local.
