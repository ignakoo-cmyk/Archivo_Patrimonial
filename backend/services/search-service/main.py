"""
Entry Point — Composición de la Aplicación (Composition Root)
==============================================================
Este es el ÚNICO lugar donde todas las capas se ensamblan y las
dependencias concretas se conectan a los puertos abstractos.

Aquí se decide:
  - Qué almacén vectorial usar (ChromaDB hoy, otro mañana).
  - Qué motor léxico usar (TF-IDF hoy, BM25 mañana).
  - Qué repositorio usar (JSON local hoy, API AtoM en producción).

Cambiar cualquiera de esas decisiones = cambiar una sola línea aquí.
El dominio, los puertos y todos los demás adaptadores permanecen intactos.
"""

import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Adaptadores de Infraestructura (código que depende de librerías) ───────────────
from Infraestructura.adaptadores_salida.chromadb_adaptador import ChromaDBAdapter
from Infraestructura.adaptadores_salida.tfidf_adaptador import TFIDFAdapter
from Infraestructura.adaptadores_salida.json_estatico_adaptador import StaticJsonRepositoryAdapter
from Infraestructura.adaptadores_salida.postgres_adaptador import PostgresRepositoryAdapter
from Infraestructura.adaptadores_salida.metadata_filter_adaptador import InMemoryMetadataFilterAdapter
from Infraestructura.adaptadores_salida.nlp_extractor_adaptador import NLPExtractorAdapter
#
# ── PUNTO DE EXTENSIÓN: AtomApiAdapter (producción futura) ───────────────────────────
# Cuando la API REST de AtoM esté disponible, descomentar y sustituir el
# adaptador JSON en el bloque de lifespan (ver comentario más abajo):
#
# from Infraestructura.adaptadores_salida.atom_api_adaptador import AtomApiAdapter
#
# → El contrato lo define Dominio/puertos/repositorio_salida.py (AtoMRepositoryPort).
# → Dominio, Aplicación y todos los demás adaptadores quedan intactos.
# ─────────────────────────────────────────────────────────────────────────────
from Presentacion.controladores.http_controlador_busqueda import router as router_busqueda

# ── Capa de Aplicación y Dominio (código puro) ───────────────────────────────
from Aplicacion.casos_de_uso.buscar_contenido import BuscarContenidoService
from Dominio.servicios.gestor_busqueda import GestorBusqueda


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan de FastAPI: Composition Root.

    Se ejecuta UNA sola vez al iniciar la aplicación.
    Aquí se instancian todos los adaptadores y se ensambla el grafo
    completo de dependencias (dominio ← puertos ← adaptadores).
    """
    print("🔍 [search-service] Iniciando composición de dependencias...")

    # ── 1. Repositorio: Composition Root — PUNTO DE EXTENSIÓN ─────────────────────
    # Aquí se decide QUÉ adaptador cumple AtoMRepositoryPort.
    # Para activar AtomApiAdapter en producción basta con:
    #   import httpx
    #   atom_cliente = httpx.AsyncClient()
    #   repositorio = AtomApiAdapter(
    #       base_url=os.getenv("ATOM_BASE_URL"),
    #       api_key=os.getenv("ATOM_API_KEY"),
    #       cliente_http=atom_cliente,
    #   )
    # El resto del lifespan (GestorBusqueda, TF-IDF, ChromaDB) queda intacto.
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            import asyncpg
            print(f"🐘 [search-service] Conectando a PostgreSQL...")
            pg_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
            repositorio = PostgresRepositoryAdapter(pool=pg_pool)
            await repositorio.cargar_cache()
            print("✅ [search-service] PostgreSQL activo como repositorio principal.")
        except Exception as e:
            print(f"⚠️ [search-service] PostgreSQL no disponible ({e}). Usando fallback JSON.")
            pg_pool = None
            repositorio = StaticJsonRepositoryAdapter(
                ruta_json=os.getenv("DATA_PATH", "Infraestructura/datos/clean_with_metadata.json")
            )
    else:
        pg_pool = None
        print("ℹ️ [search-service] DATABASE_URL no definida — modo desarrollo con JSON.")
        repositorio = StaticJsonRepositoryAdapter(
            ruta_json=os.getenv("DATA_PATH", "Infraestructura/datos/clean_with_metadata.json")
        )

    chroma_adapter = ChromaDBAdapter(
        host=os.getenv("CHROMA_HOST", "chromadb"),
        puerto=int(os.getenv("CHROMA_PORT", "8000")),
    )

    tfidf_adapter = TFIDFAdapter()
    # Construir índice léxico con todos los documentos del repositorio
    tfidf_adapter.construir_indice(await repositorio.obtener_todos())

    # ── 1b. Instanciar Motor de Pre-filtrado por Metadatos (NUEVO) ──────────────
    todos_los_docs = await repositorio.obtener_todos()

    metadata_filter = InMemoryMetadataFilterAdapter()
    metadata_filter.construir_indices(todos_los_docs)

    # ── 1c. Instanciar Extractor NLP con vocabularios dinámicos (NUEVO) ─────────
    # Cargamos dinámicamente las categorías reales desde categories.json para
    # maximizar la capacidad de reconocimiento del NLP
    top_materias = set()
    ruta_categorias = os.getenv("CATS_PATH", "Infraestructura/datos/categories.json")
    try:
        with open(ruta_categorias, "r", encoding="utf-8") as f:
            datos_cats = json.load(f)
            # Tomamos el top 2000 materias (las más frecuentes, filtrando typos)
            top_materias = {c["name"] for c in datos_cats.get("materias", [])[:2000]}
    except Exception as e:
        print(f"⚠️ [search-service] No se pudo cargar {ruta_categorias} ({e}). Se usará tesauro básico.")

    nlp_extractor = NLPExtractorAdapter(
        vocabulario_creators=repositorio.vocabulario_creators,
        vocabulario_materias=top_materias
    )
    print(f"🧠 [search-service] NLP Extractor listo con {len(repositorio.vocabulario_creators)} creators y {len(top_materias)} materias dinámicas.")

    # ── 2. Ensamblar el Servicio de Dominio ───────────────────────────────────────
    # GestorBusqueda recibe los Puertos (abstracciones), no los adaptadores concretos.
    # Python resuelve esto porque los adaptadores implementan las interfaces ABC.
    gestor = GestorBusqueda(
        almacen_vectorial=chroma_adapter,
        indice_lexico=tfidf_adapter,
        repositorio=repositorio,
        motor_filtrado=metadata_filter,  # Puerto de pre-filtrado
    )

    # ── 3. Instanciar el Caso de Uso y alojar en el estado de la app ────────
    app.state.caso_de_uso = BuscarContenidoService(gestor=gestor)
    app.state.nlp_extractor = nlp_extractor  # Disponible para el controlador HTTP

    print("✅ [search-service] Listo en puerto 3002.")
    yield
    print("👋 [search-service] Cerrando.")
    if pg_pool:
        await pg_pool.close()
        print("🐘 [search-service] Pool PostgreSQL cerrado.")


# ── Configuración de la aplicación FastAPI ────────────────────────────────────
app = FastAPI(
    title="UAH Archivo Patrimonial — Search Service",
    description=(
        "Motor de búsqueda híbrida (RRF sobre ChromaDB + TF-IDF + Coincidencia Exacta). "
        "Arquitectura Hexagonal / Puertos y Adaptadores + DDD."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Registro del Router (Adaptador de Entrada) ────────────────────────────────
app.include_router(router_busqueda)


@app.get("/health", tags=["Infraestructura"])
async def health_check():
    """Endpoint de verificación de estado para Docker y monitoreo."""
    return {
        "servicio": "search-service",
        "estado": "saludable",
        "version": "2.0.0",
        "arquitectura": "hexagonal",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3002, reload=True)
