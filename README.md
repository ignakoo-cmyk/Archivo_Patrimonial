# 🏛️ Guía de Inicio: Chatbot Inteligente Archivo Patrimonial UAH

Esta guía detalla los pasos exactos para poner en marcha la plataforma completa de búsqueda inteligente del Archivo Patrimonial de la Universidad Alberto Hurtado.

---

## 🛠️ Requisitos del Sistema
Antes de comenzar, asegúrate de tener instalado:
1. **Docker Desktop**: Esencial para correr los microservicios, bases de datos y el frontend de manera orquestada.
2. **Conexión a Internet**: Para descargar las imágenes de Docker y conectar con la API de Gemini.

---

## ⚙️ Paso 1: Configuración de Variables de Entorno

El sistema necesita tu clave de API de Google Gemini para funcionar.
1. Busca el archivo `.env` en la raíz de la carpeta `uah-archive-chatbot`.
2. Asegúrate de que tenga el siguiente contenido (reemplaza con tu clave real):

```env
# Clave de API de Google Gemini (Indispensable)
GEMINI_API_KEY=AIzaSy...tu_clave_aqui

# URL de tu instancia de AtoM local (donde viven los documentos)
ATOM_BASE_URL=http://host.docker.internal:8081
```

---

## 🚀 Paso 2: Cómo Encender la Plataforma Completa

No necesitas instalar Python o Node.js manualmente si usas Docker. Sigue estos pasos:

1. **Abre una terminal** (PowerShell o CMD) y navega hasta la carpeta del proyecto:
   ```powershell
   cd "C:\Users\Nacho\Desktop\Archivo Patromonial\uah-archive-chatbot"
   ```

2. **Ejecuta el comando de construcción y arranque**:
   ```powershell
   docker compose up -d --build
   ```
   *Este comando descargará las dependencias, compilará el frontend de Next.js y levantará los 5 microservicios.*

3. **Verifica que todo esté corriendo**:
   Ejecuta `docker ps` o revisa el Dashboard de Docker Desktop. Deberías ver contenedores llamados:
   *   `uah_frontend`
   *   `uah_gateway`
   *   `uah_chat_service`
   *   `uah_search_service`
   *   `uah_atom_integration`
   *   `uah_chroma`
   *   `uah_redis`

---

## 🌐 Paso 3: Acceso a la Interfaz y Servicios

Una vez que Docker termine (puede tardar un par de minutos la primera vez):

*   **💻 Interfaz de Usuario (Chat):** Abre en tu navegador [http://localhost:8090](http://localhost:8090). Aquí verás la interfaz con el diseño vintage institucional y podrás empezar a preguntar.
*   **🔌 API Gateway (Backend Central):** [http://localhost:3000](http://localhost:3000). Es el punto de entrada para todas las consultas técnicas.
*   **📊 Base de Datos de Vectores (Chroma):** [http://localhost:8001](http://localhost:8001). Donde se almacenan los embeddings para la búsqueda semántica.

---

## 📂 Estructura de Datos Importante

*   **Documentos del Archivo**: Los datos del archivo patrimonial (`clean_with_metadata.json`) ya han sido migrados a:
    `backend/services/search-service/data/`.
*   **Lógica de Búsqueda**: Si quieres ajustar cómo el bot busca (pesos de RRF, filtros), el archivo clave es:
    `backend/services/search-service/core/engine.py`.

---

## ❓ Solución de Problemas (Troubleshooting)

*   **El Chat no responde**: Verifica que pusiste la `GEMINI_API_KEY` correcta en el archivo `.env` y que reiniciaste los contenedores con `docker compose restart`.
*   **Error de puertos**: Si los puertos 3000 u 8090 están ocupados por otra aplicación, deberás cerrarlas o cambiarlos en el archivo `docker-compose.yml`.
*   **Refrescar cambios**: Si haces cambios en el código de Python o CSS, ejecuta siempre `docker compose up -d --build` para que Docker compile la nueva versión.

---

## 🗑️ Limpieza del Proyecto Anterior
**Nota importante**: Ahora que hemos migrado la lógica y los datos a esta nueva carpeta `uah-archive-chatbot`, puedes mantener la carpeta `UAH_ARCHIVO_10-12-main` como respaldo por unos días, pero **ya no es necesaria** para ejecutar el chatbot.
