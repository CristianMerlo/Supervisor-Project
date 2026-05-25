# Auditoría Técnica y Arquitectónica — OP_HERMES_NEXUS (PIT-V3)

Este documento detalla el diseño de Hermes como un supervisor de mantenimiento inteligente alojado en un servidor privado virtual (VPS) para gestionar equipos técnicos, basado en el historial y las decisiones documentadas.

## 1. Proceso de Compilación de Historial
**Mapeo de Evolución:** 
El proyecto mutó de un modelo pesado con hardware internacional a una arquitectura ligera de orquestación local. Inicialmente, se concibió un agente autónomo con modelos locales (Ollama), pero la realidad del hardware forzó un pivote hacia la delegación de inferencia en la nube. 
- Se priorizó la soberanía financiera y flexibilidad de salida eligiendo un VPS local en Argentina (DonWeb).
- La comunicación evolucionó de depender exclusivamente de Telegram a un sistema dual: correos electrónicos (cargas pesadas) y Telegram (alertas y consultas rápidas).

**Tecnologías y Enfoques RECHAZADOS EXPLÍCITAMENTE:**
- **Ollama / LLMs Locales:** Descartados por consumir ~4.5 GB de RAM, estrangulando el VPS de 4/8 GB y generando latencias inaceptables.
- **Proveedores Internacionales (Hostinger, etc.):** Rechazados por el riesgo cambiario (impuestos en Argentina) y el "lock-in" contractual a largo plazo.
- **Servidor Android con Termux:** Descartado por inestabilidad de red, degradación de hardware y políticas agresivas del OS móvil que matan procesos en segundo plano.
- **GitHub para Datos Sensibles/Multimedia:** Descartado; GitHub es exclusivamente para código y el dashboard estático. Google Drive (vía Rclone) manejará bases de datos, logs y adjuntos pesados.
- **Procesamiento de Video por IA:** Descartado por el alto costo de tokens; los videos se almacenan en Drive como respaldo humano, no como insumo para el LLM.

**Núcleo Inmutable del Proyecto:**
Sistema supervisor asíncrono en un VPS DonWeb Cloud (Ubuntu 24.04, 4GB RAM), sin LLMs locales, que orquesta reportes de 5 técnicos. Extrae datos duros vía Mail/Telegram, delega el razonamiento a APIs en la nube (Groq para costo cero, OpenRouter para visión), guarda estado persistente y actualiza autónomamente un dashboard estático en GitHub Pages mediante `git push`.

---

## 2. POR QUÉ ESTO FALLARÁ (Simulación Adversarial)
El sistema colapsará por asfixia concurrente y bloqueo de estado si no se gestionan las colas:
- El envío simultáneo de tres correos con PDFs pesados y audios de Telegram obligará a lanzar procesos paralelos, saturando la memoria (4GB) e invocando el *OOM Killer* de Linux, matando el proceso principal.
- Al intentar actualizar el dashboard en GitHub simultáneamente, se generará una condición de carrera (Race Condition) en Git. El archivo `.git/index.lock` quedará huérfano y bloqueará todas las actualizaciones futuras.
- **Solución Obligatoria:** Implementar Dead Letter Queue (DLQ), una cola con Redis/Celery y limitadores de memoria estrictos en Docker.

---

## 3. Evidence & Uncertainty Calibration
- **Infraestructura (DonWeb VPS 4GB, Ubuntu 24.04):** Certeza: 0.85 (El margen de RAM es crítico si no se configuran límites en contenedores).
- **Delegación Híbrida de Inferencia (Groq + OpenRouter):** Certeza: 0.95 (Sólido. Groq maneja lógica; OpenRouter maneja visión).
- **Routing Multicanal (Mail Primario, Telegram Secundario):** Certeza: 0.90 (Reduce el ruido en la IA y ahorra tokens).
- **Persistencia (GitHub + GDrive Rclone):** Certeza: 0.65 (RIESGO ALTO). Faltan mecanismos de reintento idempotente si el `git push` falla por pérdida de red temporal.

---

## 4. GAP Analysis & RFI (Request for Information)
Para inyectar el código y levantar contenedores sin interacción humana, se necesita:
1. **IP y Credenciales del VPS:** Dirección IPv4 exacta de DonWeb y puerto SSH abierto.
2. **Tokens Secretos:** GitHub PAT (Personal Access Token) y App Password de Google Workspace para el `.env`.
3. **Estructura del Payload:** Nombre y estructura JSON exacta del archivo que el bot modificará en el repositorio `dashboard_cafeteras`.
4. **Esquema de Base de Datos Base:** Columnas operativas exactas (ej. ID Local, Shots, PPM, Técnico).

---

## 5. BLUEPRINT DE ENTREGABLE PARA ANTIGRAVITY (OP_HERMES_NEXUS)

### Protocolo de Flujo de Datos
- **Triggers:** IMAP IDLE (Correo) / Webhook de Telegram / Cronjob a las 20:00 hs.
- **Lógica de Procesamiento:** Payload recibido -> Ingesta en Redis Queue (evita OOM) -> Worker Celery toma el job -> Extrae datos (Groq / OpenRouter) -> Actualiza SQLite local -> Llama `github_dashboard_updater.py` -> Limpia `.git/index.lock` -> Commit -> Fin del job.
- **Outputs:** PDF por mail al gerente del local, Commit en GitHub Pages alterando `data.json`, Sincronización Rclone a GDrive.

### Configuración de Automatización (Prevención OOM en Docker)
```yaml
version: '3.8'
services:
  redis_queue:
    image: redis:alpine
    restart: always
    deploy:
      resources:
        limits:
          memory: 256M # Prevención OOM
  hermes_core:
    build: ./src
    restart: always
    depends_on:
      - redis_queue
    deploy:
      resources:
        limits:
          memory: 1G # Protege el VPS de 4GB
  celery_worker:
    build: ./src
    command: celery -A config.celery worker --loglevel=info
    restart: always
    deploy:
      resources:
        limits:
          memory: 1.5G # Maneja carga pesada
```

### Fragmento de Prevención de Bloqueos en Git (`github_dashboard_updater.py`)
```python
import os
import subprocess

def update_dashboard_git(data_payload):
    repo_dir = "/opt/hermes_nexus/data/dashboard_cafeteras"
    
    # 1. Idempotencia y Prevención de Lock (Race Condition)
    lock_file = os.path.join(repo_dir, ".git/index.lock")
    if os.path.exists(lock_file):
        os.remove(lock_file)
        
    # 2. Operación No-Interactiva
    try:
        subprocess.run(["git", "-C", repo_dir, "pull"], check=True)
        # Lógica de actualización de archivo JSON
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", "Auto-update Hermes"], check=True)
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
    except subprocess.CalledProcessError as e:
        # DLQ Logging para intervención posterior
        log_error("Fallo crítico en Git Push", str(e))
```
