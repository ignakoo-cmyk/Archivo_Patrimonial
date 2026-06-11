# 🏛️ Archivo Patrimonial UAH - Chatbot Inteligente

Este proyecto implementa una plataforma de búsqueda inteligente y un chatbot conversacional para explorar el Archivo Patrimonial de la Universidad Alberto Hurtado (UAH). Utiliza un enfoque basado en RAG (Retrieval-Augmented Generation) combinando una búsqueda híbrida con Inteligencia Artificial generativa.

## 🧠 Arquitectura y Flujo de la Información (Bajo el Capó)

El sistema está diseñado utilizando una arquitectura de microservicios. A continuación, se detalla el flujo de información paso a paso desde que un usuario realiza una consulta:

### 1. Interacción del Usuario (Frontend)
El usuario ingresa su consulta a través de la interfaz web desarrollada en **Next.js**. Esta solicitud se envía al **API Gateway**.

### 2. Enrutamiento (API Gateway)
El Gateway (FastAPI) actúa como el punto de entrada único (puerto 3000). Recibe la petición HTTP, verifica el endpoint y la enruta hacia el microservicio correspondiente, en este caso, el **Chat Service**.

### 3. Orquestación y RAG (Chat Service)
El `chat-service` recibe la consulta y necesita contexto para responder. Antes de contactar a la IA (NLP), realiza una petición interna al **Search Service** para recuperar los documentos más relevantes del archivo.

### 4. Búsqueda Híbrida (Search Service)
El `search-service` procesa la búsqueda utilizando tres estrategias diferentes simultáneamente:
- **Búsqueda Semántica (ChromaDB)**: Transforma la consulta en un vector (embedding) y busca similitudes semánticas en la base de datos vectorial (Vector Store).
- **Búsqueda Léxica (TF-IDF)**: Busca coincidencias basadas en la frecuencia y peso de los términos en los documentos.
- **Coincidencia Exacta (Exact Match)**: Busca coincidencias exactas y parciales en los títulos de los documentos.

Finalmente, el motor de búsqueda combina estos resultados utilizando el algoritmo **RRF (Reciprocal Rank Fusion)** para obtener un listado unificado y ordenado por relevancia, y lo devuelve al Chat Service.

### 5. Procesamiento NLP (Gemini)
El `chat-service` recibe los documentos relevantes y construye un *Prompt* complejo. Este prompt inyecta el contexto (RAG) e incluye:
- El rol y comportamiento esperado (System Prompt).
- Los documentos recuperados del Search Service con sus puntajes.
- La consulta original del usuario.

Esta información consolidada se envía a la API de **Google Gemini** (nuestro motor NLP). La IA procesa la instrucción y genera una respuesta coherente, académica y en español, basándose **estrictamente** en los documentos proporcionados, evitando alucinaciones.

### 6. Integración con AtoM y Scraper (AtoM Integration Service)
Para mantener la base de conocimientos, el **AtoM Integration Service** actúa como un adaptador (Arquitectura Hexagonal) que se conecta con la plataforma oficial AtoM (Access to Memory) de la UAH. Este servicio puede:
- Hacer peticiones directas a la API de AtoM en tiempo real.
- Utilizar datos pre-recolectados por un scraper (formato JSON) operando en "Modo Mock" cuando la API no está disponible o para agilizar búsquedas. Los datos limpios del scraper alimentan el repositorio documental del `search-service`.

### 7. Respuesta Final
La respuesta generada por Gemini (formateada en Markdown) junto con la metadata de los documentos (títulos, URLs), es enviada de vuelta a través del Gateway hacia el Frontend, donde se visualiza de forma amigable para el usuario.

---

## 🛠️ Pre-requisitos

Para ejecutar este proyecto de forma local, necesitas:
- **Docker** y **Docker Compose** instalados en tu sistema.
- Una clave de API válida de Google Gemini (AI Studio).
- Puertos `3000`, `3001`, `3002`, `3003`, `8000` y `8090` disponibles.

---

## ⚙️ Instalación y Configuración

1. **Navegar a la carpeta del proyecto**:
   ```bash
   cd uah-archive-chatbot
   ```

2. **Configurar las variables de entorno**:
   Asegúrate de que exista un archivo `.env` en la raíz (puedes basarte en `.env.example`). Añade tu clave de API de Gemini:
   ```env
   # Clave de API de Google Gemini (Obligatoria)
   GEMINI_API_KEY=AIzaSy...tu_clave_aqui

   # URL de tu instancia de AtoM
   ATOM_BASE_URL=http://localhost:8081
   
   # Activar modo Mock si no tienes AtoM corriendo localmente
   USE_MOCK_ADAPTER=true
   ```

---

## 🚀 Ejecución

La forma más robusta y automatizada de ejecutar todo el ecosistema es mediante Docker Compose.

1. **Levantar los servicios**:
   Abre una terminal en la raíz del proyecto y ejecuta:
   ```bash
   docker compose up -d --build
   ```
   *Nota: Este proceso descargará las imágenes, instalará las dependencias (Python/Node) y orquestará los 5 servicios.*

2. **Verificar que el sistema esté funcionando**:
   Puedes revisar los logs de los contenedores con:
   ```bash
   docker ps
   ```

3. **Acceder a la aplicación**:
   - **Frontend (Interfaz de Chat)**: Abre en tu navegador [http://localhost:8090](http://localhost:8090)
   - **API Gateway**: [http://localhost:3000](http://localhost:3000)
