# Implementación de un Chatbot para el Archivo Patrimonial UAH con Integración a ATOM
## Documentación Técnica · Guion de Presentación (10 Slides)

> **Tono:** Académico · Técnico · Profesional  
> **Audiencia:** Ingenieros de Software, Evaluadores Técnicos, Académicos  
> **Stack:** Next.js 14 (Frontend) · Python 3.12 / FastAPI (Backend) · Docker · ChromaDB · PostgreSQL

---

## Slide 1: Visión General del Proyecto

### Propósito del Sistema
Esta plataforma de acceso inteligente al **Archivo Patrimonial de la Universidad Alberto Hurtado (UAH)** ha sido construida bajo una filosofía de *software académico de calidad de producción*. El sistema integra tres capacidades complementarias:

- **Integración de Datos con AtoM (Access to Memory):** Canal de interoperabilidad con el sistema oficial de catalogación archivística de la universidad. Permite la ingesta y estructuración de metadatos (respetando estándares como ISAD(G)), asegurando que la base de conocimiento se alimente de información oficial y manteniendo a AtoM como la fuente única de verdad.
- **Búsqueda Híbrida RAG** *(Retrieval-Augmented Generation)*: Recuperación de documentos históricos combinando búsqueda semántica (embeddings vectoriales) con búsqueda léxica (TF-IDF) y coincidencia exacta, fusionados mediante el algoritmo **RRF** *(Reciprocal Rank Fusion)*.
- **Chatbot Institucional**: Un asistente digital conversacional que responde consultas en lenguaje natural sobre el acervo documental, citando fuentes verificadas y enlaces del catálogo para garantizar confiabilidad y trazabilidad.

### Ecosistema a Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENTE                             │
│              Next.js 14 (TypeScript) — Puerto 3011          │
└─────────────────────────┬───────────────────────────────────┘
                           │ HTTP / SSE (Streaming)
┌─────────────────────────▼───────────────────────────────────┐
│                    API GATEWAY                               │
│          FastAPI + Uvicorn — Puerto 8059                     │
│    (Enrutamiento, CORS, Health Check, Proxy de Streaming)    │
└──────┬───────────────────────────────────────┬──────────────┘
       │ HTTP (httpx async)                    │ HTTP (httpx async)
┌──────▼────────────┐              ┌───────────▼───────────────┐
│   CHAT-SERVICE    │              │     SEARCH-SERVICE        │
│   Puerto 3001     │◄─────────────│     Puerto 3002           │
│   FastAPI/Uvicorn │  inter-svc   │     FastAPI/Uvicorn       │
│   Gemini AI Redis │             │   ChromaDB · TF-IDF · PG  │
└───────────────────┘              └───────────────────────────┘
       │                                       │
┌──────▼────────────┐              ┌───────────▼───────────────┐
│   Redis (Sesiones)│              │   PostgreSQL (Catálogo)   │
│   Puerto 6380     │              │   Puerto 5433             │
└───────────────────┘              │   ChromaDB (Embeddings)   │
                                   │   Puerto 8001             │
                                   └───────────────────────────┘
```

---

## Slide 2: Stack Tecnológico del Backend

### Lenguaje Elegido: Python 3.12
Python 3.12 fue seleccionado por razones arquitectónicas y de dominio:
- **Tipado estricto nativo**: Con `from __future__ import annotations` y la integración completa de PEP 695, todo el código utiliza anotaciones de tipo que el linter verifica en tiempo de desarrollo, eliminando errores de integración antes del runtime.
- **Asincronía nativa de primera clase**: El modelo `async/await` permite al servidor gestionar miles de peticiones concurrentes con un único hilo del sistema operativo, crítico para el I/O de red hacia Gemini, ChromaDB y PostgreSQL.

### Frameworks y Librerías Principales
- **FastAPI** (basado en Starlette/ASGI): Maneja SSE *(Server-Sent Events)* para streaming de respuestas del LLM y genera OpenAPI automáticamente.
- **Pydantic v2** (validación en tiempo de runtime): Los DTOs validan la forma exacta de los datos de entrada en los endpoints, rechazando peticiones malformadas antes de llegar a la capa de aplicación.
- **Uvicorn** (servidor ASGI): Entrega un rendimiento muy superior a servidores WSGI tradicionales para cargas de trabajo I/O-bound.
- **httpx**: Cliente HTTP asíncrono para la comunicación no bloqueante entre servicios.
- **ChromaDB**: Base de datos vectorial para el almacenamiento y consulta rápida de embeddings semánticos.
- **PostgreSQL**: Motor relacional robusto para almacenar el catálogo documental patrimonial.
- **Redis**: Almacenamiento rápido en memoria utilizado para la persistencia y control de sesiones del chat.

---

## Slide 3: Arquitectura Dual (Macro y Micro)

### Macro-Arquitectura: Microservicios
El sistema se descompone en **servicios autónomos y desacoplados**, cada uno con una responsabilidad de negocio única y su propio proceso de despliegue:

| Microservicio | Responsabilidad | Base de datos |
|---|---|---|
| `gateway` | Enrutamiento, seguridad perimetral, proxy de streaming | — |
| `chat-service` | Gestión de sesiones de chat, orquestación de prompts con el LLM | Redis |
| `search-service` | Búsqueda híbrida RAG (semántica + léxica), pre-filtrado NLP | PostgreSQL + ChromaDB |
| `atom-integration-service` | Ingesta y conector con la API externa de AtoM | — |

### Micro-Arquitectura: Diseño en Capas (Nivel Micro)
Cada microservicio implementa internamente una estructura limpia de **Arquitectura en Capas**, donde las dependencias apuntan estrictamente hacia el núcleo interno (Dominio):

```
+------------------------------------------------+
|              PRESENTACIÓN                      |  <- Controladores FastAPI, Rutas HTTP
|  (Capas Externas / Adaptadores de Entrada)     |
+------------------------------------------------+
|              APLICACIÓN                        |  <- Casos de Uso, DTOs de Entrada/Salida
|  (Orquestación de Lógica de Negocio)           |
+------------------------------------------------+
|   +==================================+         |
|   ||           DOMINIO              ||         |  <- Entidades, Puertos (Interfaces ABC)
|   ||       (Núcleo del Sistema)     ||         |     CERO dependencias externas
|   +==================================+         |
+------------------------------------------------+
|              INFRAESTRUCTURA                   |  <- ChromaDB, PostgreSQL, Gemini,
|  (Capas Tecnológicas / Adaptadores de Salida)  |     TF-IDF, Redis, Clientes de API HTTP
+------------------------------------------------+
```

> **Regla de Dependencia**: El Dominio no tiene conocimiento de la existencia de frameworks como FastAPI, ChromaDB o Redis. Toda la comunicación con el exterior se realiza a través de interfaces definidas en el Dominio (Puertos), implementadas en la Infraestructura (Adaptadores).

---

## Slide 4: Justificación de la Arquitectura

### Beneficios frente al Monolito Tradicional
- **Escalado Independiente**: Permite escalar las réplicas del servicio de búsqueda (intensivo en cómputo/memoria) sin replicar innecesariamente el servicio de chat.
- **Aislamiento de Fallos**: Un problema de conexión con el LLM en el servicio de chat no inhabilita el motor de búsqueda ni la integración con AtoM.
- **Despliegues Selectivos**: Es posible actualizar y desplegar mejoras en la búsqueda RAG sin interrumpir las sesiones activas en el servicio de chat.
- **Desacoplamiento Tecnológico**: El cambio de un componente externo (por ejemplo, reemplazar ChromaDB por otra base vectorial) afecta exclusivamente al adaptador en la capa de Infraestructura, manteniendo a salvo el núcleo del dominio.

### Prevención del "Monolito Distribuido"
El sistema evita este anti-patrón de la siguiente manera:
1. **Comunicación Asíncrona Tolerante a Fallos**: La llamada a través de `httpx.AsyncClient` implementa timeouts y respuestas degradadas de forma asíncrona si un microservicio de soporte experimenta problemas.
2. **Base de Datos por Servicio**: Cada microservicio opera bajo su propio esquema aislado. El servicio de chat nunca escribe ni accede directamente al almacenamiento del buscador.
3. **Contratos Fuertes**: Intercambio de datos regulado estrictamente a través de DTOs validados con Pydantic en los límites de cada servicio.

---

## Slide 5: Mantenibilidad, Testeabilidad y Latencia

### Mantenibilidad: Aislamiento de Capas
Agregar un nuevo formato de búsqueda o exportar información requiere únicamente:
1. Crear un adaptador concreto en `Infraestructura/adaptadores_salida/`.
2. Registrar el nuevo adaptador en el punto de inicio del servicio (`main.py`).
3. **Ninguna modificación** en las capas de `Dominio/` o `Aplicacion/`.

### Testeabilidad: Inyección de Dependencias y Mocks
El desacoplamiento a través de interfaces abstractas (Puertos) facilita las pruebas de software:

```python
# Test unitario sin depender de conexiones de red reales o APIs externas
class MockModeloLenguaje(ModeloLenguajePort):
    async def generar_respuesta(self, prompt: PromptContextualizado) -> str:
        return "Respuesta mock del test."
    def esta_disponible(self) -> bool:
        return True

async def test_orquestador_procesa_mensaje():
    orquestador = ChatOrchestratorService(
        modelo_lenguaje=MockModeloLenguaje(),
        servicio_busqueda=MockBusquedaAdapter(docs_fijos=[doc_fixture]),
        repositorio_sesiones=InMemorySesionRepositorio(),
    )
    resultado = await orquestador.procesar_mensaje("consulta", "session-123")
    assert resultado is not None
```

### Latencia: Optimización Asíncrona
- **Paralelismo I/O**: Ejecución concurrente y no bloqueante de la búsqueda vectorial (ChromaDB) y de la búsqueda léxica (TF-IDF).
- **Pre-filtrado Inteligente**: Un analizador liviano en memoria evalúa los límites espaciales/temporales de la consulta antes de enviar solicitudes al motor de búsqueda pesada.

---

## Slide 6: El Santuario del Core (Protección del Dominio)

### Cero Dependencias Externas en Dominio
Cualquier módulo ubicado dentro de `Dominio/` tiene dependencias externas estrictamente limitadas a tipos estándar de Python y objetos de valor del propio dominio:

```python
# Dominio/puertos/puertos_salida.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from Dominio.objetos_de_valor.chat import PromptContextualizado

# En esta capa queda PROHIBIDO importar librerías de infraestructura como:
# import google.generativeai
# import chromadb
# import fastapi
```

### Contratos Definidos por Clases Abstractas (ABC)
El Dominio establece cómo interactuar con el exterior mediante interfaces obligatorias:

```python
class ModeloLenguajePort(ABC):
    @abstractmethod
    async def generar_respuesta(self, prompt: PromptContextualizado) -> str:
        pass
        
    @abstractmethod
    def esta_disponible(self) -> bool:
        pass
```

El adaptador en la Infraestructura debe implementar estas interfaces con exactitud:

```python
class GeminiAdapter(ModeloLenguajePort):
    async def generar_respuesta(self, prompt: PromptContextualizado) -> str:
        return await self._cliente_gemini.generate_content_async(str(prompt))
        
    def esta_disponible(self) -> bool:
        return self._api_key is not None
```

---

## Slide 7: Extensibilidad de la Ingesta de Datos (AtoM)

### Transición de Datos Estáticos a Dinámicos
Actualmente, el sistema utiliza un **volcado estático en JSON** para operar y probar los algoritmos de forma estable. No obstante, gracias a la Arquitectura en Capas, el conector está diseñado para su transición a entornos dinámicos:

```python
class AtoMRepositoryPort(ABC):
    @abstractmethod
    async def obtener_todos(self) -> list[DocumentoPatrimonial]:
        pass
```

La evolución técnica se puede realizar alternando adaptadores sin tocar una sola línea de la lógica de búsqueda:

1. **Fase Inicial (JSON Estático):**
   ```python
   class JsonEstaticoRepositorio(AtoMRepositoryPort):
       async def obtener_todos(self) -> list[DocumentoPatrimonial]:
           # Lee del archivo local clean_with_metadata.json
   ```
2. **Fase de Producción Dinámica (API REST de AtoM):**
   ```python
   class AtoMHttpAdapter(AtoMRepositoryPort):
       async def obtener_todos(self) -> list[DocumentoPatrimonial]:
           # Realiza peticiones HTTP GET a /api/informationobjects de AtoM
   ```

---

## Slide 8: Aplicación de Principios SOLID

### Ejemplos en el Diseño del Backend
*   **Responsabilidad Única (S)**: Cada clase tiene un único propósito. Por ejemplo, `BuscarContenidoUseCase` solo orquesta la llamada al motor de búsqueda híbrido.
*   **Abierto/Cerrado (O)**: El combinador RRF está diseñado para aceptar cualquier número de fuentes de resultados ordenados (listas de documentos) sin requerir modificaciones en su lógica interna.
*   **Sustitución de Liskov (L)**: `JsonEstaticoRepositorio` y `AtoMHttpAdapter` implementan con fidelidad la interfaz `AtoMRepositoryPort`, por lo que son completamente intercambiables a nivel del sistema de inyección.
*   **Inversión de Dependencias (D)**: Las clases de la capa de Aplicación no instancian directamente conexiones a bases de datos ni clientes de Inteligencia Artificial; los reciben a través de sus constructores parametrizados en el archivo central de inicio (`main.py`).

---

## Slide 9: Cohesión y Acoplamiento

### Métrica de Inestabilidad (Martin)
Mide la robustez y dependencia del software según la fórmula:
$$I = \frac{\text{Fan-Out}}{\text{Fan-In} + \text{Fan-Out}}$$
*(Donde 0 representa estabilidad máxima y 1 inestabilidad completa).*

| Capa / Módulo | Fan-In | Fan-Out | Inestabilidad (I) | Estado de Diseño |
|---|---|---|---|---|
| `Dominio/` | Alta | **0** | **0.00** | Estabilidad Máxima (Ideal) |
| `Aplicacion/` | Media | Baja | **~0.30** | Estable |
| `Infraestructura/` | Baja | Alta | **~0.80** | Adaptable a cambios |
| `Presentacion/` | Baja | Alta | **~0.90** | Punto de entrada del tráfico |

El flujo de inestabilidad respeta la regla: **los módulos inestables dependen de módulos estables.**

---

## Slide 10: Escalabilidad y Roadmap del Proyecto

### Despliegue y Orquestación Horizontal
Mediante Docker Compose es posible escalar dinámicamente las réplicas del servicio de búsqueda:
```bash
docker compose up --scale search-service=3 -d
```
El gateway de API se encarga de balancear la carga de consultas entre los contenedores concurrentes.

```
                  +--- search-service (réplica 1)
Gateway (Proxy)  +--- search-service (réplica 2)
                  +--- search-service (réplica 3)
```

### Plan de Evolución
*   **v1.0 (Actual):** Ingesta basada en JSON estático normalizado y consultas de embeddings a ChromaDB + TF-IDF local.
*   **v1.5:** Implementación del adaptador `AtoMHttpAdapter` para consumir directamente el API REST del servidor de archivo histórico institucional.
*   **v2.0:** Integración de un componente de Re-ranking (Cross-Encoder) para reordenar contextualmente los 10 mejores resultados de la búsqueda híbrida.

---

## Referencias Técnicas
- Fowler, M. (2018). *Patterns of Enterprise Application Architecture*. Addison-Wesley.
- Martin, R. C. (2017). *Clean Architecture*. Prentice Hall.
- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.
- Cormack, G. V., & Clarke, C. L. A. (2009). *Reciprocal Rank Fusion*. SIGIR '09.
