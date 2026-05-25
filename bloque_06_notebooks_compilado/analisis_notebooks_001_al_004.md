# Análisis de Cuadernos: 001 a 004 (NotebookLM)

Este documento compila el análisis técnico y la evolución arquitectónica documentada en los cuatro cuadernos principales almacenados en tu NotebookLM. Sirve como registro maestro y "fuente de la verdad" de las decisiones del Proyecto Hermes.

## 📓 Cuaderno 001: Proyecto Web (Mostaza Elite / MTZ_ Informes)
Se centra en la herramienta de campo utilizada por los técnicos para recolectar los datos.
- **Arquitectura PWA Offline-First:** La aplicación es una *Progressive Web App* monolítica alojada en GitHub Pages. Utiliza un `Service Worker` y `localStorage` para poder funcionar sin conexión en las cocinas de los locales, donde suele haber mala señal.
- **Pipeline de Imágenes Seguro:** Para evitar fallos de memoria (el temido *OOM*) en celulares de gama baja, procesa las fotos de manera secuencial usando `<canvas>` y compresión a JPEG.
- **Generación Local (jsPDF):** Renderiza el informe legal PDF (con prefijo `MTZ_`) directamente en el teléfono del técnico. Añade una página de "Resumen Ejecutivo" (un ticket digital) para lectura rápida del encargado del local.
- **Candados de Seguridad:** Las firmas digitales se sellan de inmediato para evitar cualquier alteración posterior del documento.

## 📓 Cuaderno 002: Proyecto VPS y Ecosistema de IA
Detalla el enfoque inicial de infraestructura en la nube y cómo se maneja la IA.
- **Abandono de LLMs Locales:** Ejecutar Llama 3 localmente consume ~4.5 GB de RAM. Para evitar asfixiar el servidor, se adopta un **Enrutamiento Inteligente**: Groq para transcripción ultrarrápida, Gemini/OpenRouter para visión multimodal, y Mistral como respaldo (Circuit Breaker).
- **Memoria Segmentada (RAG por Local):** Para evitar que el agente "alucine" y mezcle datos de diferentes franquicias, la memoria de largo plazo se divide por local.
- **Manejo de Asincronía:** Establece la obligatoriedad de usar colas de mensajes (Dead Letter Queues) para manejar picos de envíos simultáneos de los técnicos.

## 📓 Cuaderno 003: Proyecto Supervisor de Mantenimiento
Analiza la dicotomía entre usar servidores físicos contra apoyarse 100% en el ecosistema de Google Workspace.
- **Sistema de 4 Niveles:** 1. Base de conocimiento (Drive/NotebookLM). 2. Análisis de datos (Gemini). 3. Agente especializado (Gems). 4. Ejecución y Reportes (Docs/Sheets).
- **Google Chat como UI Oficial:** Se escoge Google Chat y sus Espacios en lugar de WhatsApp o Telegram para evitar la fuga de información técnica y mantener un canal auditable y corporativo.
- **Riesgos Técnicos Descubiertos:** Si se usara exclusivamente Google Workspace, el sistema colapsaría por el límite de 90 minutos diarios de ejecución de Google Apps Script y las restricciones para cuentas gratuitas al momento de usar "Gems" de forma automática.

## 📓 Cuaderno 004: Ideas Proyecto Supervisor (El Consenso Final)
Consolida todas las ideas anteriores en la arquitectura definitiva e híbrida.
- **Hardware Definitivo (Mini PC Lenovo M700):** Se descartan los servidores virtuales (VPS) pagos en dólares. Se aprueba la Mini PC Intel Core i3 con Ubuntu 24.04 y 8GB de RAM.
- **Tolerancia a Cortes Eléctricos (UPS):** Integración clave de la UPS Lyonn CTB-800V vía `apcupsd`. Si hay un corte de luz y la batería llega al 15%, un script cierra Docker, apaga la base de datos PostgreSQL y apaga el sistema operativo de manera segura para evitar corrupción.
- **Orquestación Distribuida:** *Antigravity* actúa como el cerebro en segundo plano. *Google Sheets* es la base de datos plana ("La Sábana"), *Google Drive* es la bóveda de archivos (vía Rclone), y *NotebookLM* actúa como Memoria de Largo Plazo (usando un cuaderno para cada local).
- **Jerarquía Hídrica:** La regla de negocio suprema. Si la IA detecta que la calidad del agua supera las 200 PPM, fuerza el estado del informe a CRÍTICO (ROJO), independientemente de que la cafetera mecánicamente esté bien.
