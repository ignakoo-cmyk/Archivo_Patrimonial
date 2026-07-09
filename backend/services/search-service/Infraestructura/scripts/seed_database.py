"""
Script de Inicializacion y Migracion de Datos - seed_database.py
=================================================================
Estrategia de Semillero (Seed): lee los archivos JSON del catalogo
patrimonial UAH y los inserta en PostgreSQL como fuente de verdad
de produccion. Los archivos JSON permanecen como respaldo.

Uso:
    # Dentro del contenedor search-service:
    python Infraestructura/scripts/seed_database.py

    # O desde el host (requiere DATABASE_URL correcta):
    DATABASE_URL=postgresql://uah_user:uah_secret@localhost:5433/uah_archivo \
    python Infraestructura/scripts/seed_database.py

Que hace este script:
    1. Conecta a PostgreSQL usando DATABASE_URL del entorno.
    2. Crea las tablas si no existen (idempotente).
    3. Lee clean_with_metadata.json y extrae metadatos Dublin Core.
    4. Inserta todos los registros con UPSERT (ON CONFLICT DO UPDATE).
    5. Lee categories.json e inserta/actualiza la tabla categorias.
    6. Llama al ChromaDBAdapter para regenerar los embeddings en ChromaDB
       usando los IDs correctos de PostgreSQL como nexo.
    7. Imprime estadisticas finales.

Los archivos JSON no se eliminan: quedan en Infraestructura/datos/
como respaldo de desarrollo y fuente de re-semillero.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import asyncpg


# ── Constantes ────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
SERVICE_ROOT = SCRIPT_DIR.parent.parent
JSON_DOCS = SERVICE_ROOT / "Infraestructura" / "datos" / "clean_with_metadata.json"
JSON_CATS = SERVICE_ROOT / "Infraestructura" / "datos" / "categories.json"

TAMANO_LOTE = 500


# ── DDL — Creacion de Tablas ──────────────────────────────────────────────────

DDL_DOCUMENTOS = """
CREATE TABLE IF NOT EXISTS documentos_patrimoniales (
    id           TEXT PRIMARY KEY,
    titulo       TEXT NOT NULL,
    descripcion  TEXT DEFAULT '',
    url_catalogo TEXT DEFAULT '',
    anio         TEXT,
    creator      TEXT,
    materias     TEXT,
    lugar        TEXT,
    categorias   TEXT,
    slug         TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_creator
    ON documentos_patrimoniales(creator)
    WHERE creator IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_doc_titulo_gin
    ON documentos_patrimoniales
    USING GIN(to_tsvector('spanish', titulo));

CREATE INDEX IF NOT EXISTS idx_doc_materias_gin
    ON documentos_patrimoniales
    USING GIN(to_tsvector('spanish', COALESCE(materias, '')));

CREATE INDEX IF NOT EXISTS idx_doc_slug
    ON documentos_patrimoniales(slug)
    WHERE slug IS NOT NULL;
"""

DDL_CATEGORIAS = """
CREATE TABLE IF NOT EXISTS categorias (
    name  TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0
);
"""


# ── Funciones de transformacion Dublin Core ───────────────────────────────────

def extraer_creator(raw: list) -> str | None:
    """Extrae el primer dc:creator como string desde lista de strings o dicts."""
    if not raw:
        return None
    item = raw[0]
    if isinstance(item, dict):
        return (
            item.get("authorized_form_of_name")
            or item.get("name", "")
            or None
        )
    return str(item).strip() or None


def extraer_materias(raw: list) -> str | None:
    """Convierte dc:subject (lista) a string separado por ' | '."""
    if not raw:
        return None
    if raw and isinstance(raw[0], dict):
        partes = [
            s.get("name", "") or s.get("authorized_form_of_name", "")
            for s in raw if s
        ]
    else:
        partes = [str(s) for s in raw if s]
    resultado = " | ".join(p.strip() for p in partes if p.strip())
    return resultado or None


def extraer_lugar(raw: list) -> str | None:
    """Extrae la primera cobertura geografica dc:coverage."""
    if not raw:
        return None
    item = raw[0]
    if isinstance(item, dict):
        return item.get("name", "") or item.get("authorized_form_of_name", "") or None
    return str(item).strip() or None


def extraer_categorias(raw: list) -> str | None:
    """Convierte el arbol de categorias a string para busqueda de texto."""
    if not raw:
        return None
    if raw and isinstance(raw[0], dict):
        partes = [c.get("name", "") for c in raw if c.get("name")]
    else:
        partes = [str(c) for c in raw if c]
    resultado = " ".join(p.strip() for p in partes if p.strip())
    return resultado or None


def json_a_fila(idx: int, item: dict) -> dict | None:
    """
    Convierte un item del JSON de catalogo a un diccionario con el esquema PG.
    Retorna None si el item no tiene titulo (documento invalido).
    """
    titulo = str(item.get("title", "") or item.get("dc:title", "")).strip()
    if not titulo:
        return None

    id_doc = item.get("id") or item.get("slug")
    if not id_doc:
        id_doc = str(idx)
    else:
        id_doc = str(id_doc)

    return {
        "id": id_doc,
        "titulo": titulo,
        "descripcion": str(item.get("description", "") or "").strip(),
        "url_catalogo": str(item.get("href", "") or "").strip(),
        "anio": str(item.get("year", "") or item.get("date", "") or "").strip() or None,
        "creator": extraer_creator(item.get("dc:creator", []) or []),
        "materias": extraer_materias(item.get("dc:subject", []) or []),
        "lugar": extraer_lugar(item.get("dc:coverage", []) or []),
        "categorias": extraer_categorias(item.get("categories", []) or []),
        "slug": str(item.get("slug", "") or "").strip() or None,
    }


# ── Insercion en PostgreSQL ───────────────────────────────────────────────────

async def crear_tablas(conn: asyncpg.Connection) -> None:
    """Crea las tablas si no existen (idempotente)."""
    await conn.execute(DDL_DOCUMENTOS)
    await conn.execute(DDL_CATEGORIAS)
    print("✅ [seed] Tablas verificadas/creadas.")


async def insertar_documentos(pool: asyncpg.Pool, documentos_raw: list) -> int:
    """
    Inserta todos los documentos del catalogo JSON en PostgreSQL.
    Usa UPSERT para ser idempotente: re-ejecutar no genera duplicados.
    """
    print(f"📖 [seed] {len(documentos_raw)} registros leidos del JSON.")

    filas = []
    for idx, item in enumerate(documentos_raw):
        fila = json_a_fila(idx, item)
        if fila:
            filas.append(fila)

    print(f"🔍 [seed] {len(filas)} documentos validos (con titulo) para insertar.")

    total_insertados = 0
    inicio_tiempo = time.time()

    async with pool.acquire() as conn:
        for i in range(0, len(filas), TAMANO_LOTE):
            lote = filas[i:i + TAMANO_LOTE]
            await conn.executemany(
                """
                INSERT INTO documentos_patrimoniales
                    (id, titulo, descripcion, url_catalogo, anio,
                     creator, materias, lugar, categorias, slug)
                VALUES
                    ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    titulo       = EXCLUDED.titulo,
                    descripcion  = EXCLUDED.descripcion,
                    url_catalogo = EXCLUDED.url_catalogo,
                    anio         = EXCLUDED.anio,
                    creator      = EXCLUDED.creator,
                    materias     = EXCLUDED.materias,
                    lugar        = EXCLUDED.lugar,
                    categorias   = EXCLUDED.categorias,
                    slug         = EXCLUDED.slug
                """,
                [
                    (
                        f["id"], f["titulo"], f["descripcion"], f["url_catalogo"],
                        f["anio"], f["creator"], f["materias"], f["lugar"],
                        f["categorias"], f["slug"],
                    )
                    for f in lote
                ],
            )
            total_insertados += len(lote)
            pct = total_insertados / len(filas) * 100
            print(f"   📦 {total_insertados}/{len(filas)} ({pct:.0f}%) insertados...")

    duracion = time.time() - inicio_tiempo
    print(f"✅ [seed] {total_insertados} documentos insertados en {duracion:.1f}s.")
    return total_insertados


async def insertar_categorias(pool: asyncpg.Pool, cats_raw: dict) -> int:
    """Inserta las categorias/materias desde categories.json."""
    materias = cats_raw.get("materias", [])
    if not materias:
        print("⚠️ [seed] No se encontraron materias en categories.json.")
        return 0

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO categorias (name, count)
            VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE SET count = EXCLUDED.count
            """,
            [(m["name"], m.get("count", 0)) for m in materias if m.get("name")],
        )

    print(f"✅ [seed] {len(materias)} categorias insertadas.")
    return len(materias)


# ── Indexacion en ChromaDB (opcional) ────────────────────────────────────────

def indexar_en_chromadb(documentos_raw: list) -> None:
    """
    Regenera los embeddings en ChromaDB a partir de los datos del JSON.
    Usa el ChromaDBAdapter del servicio para garantizar consistencia
    con los IDs que quedaron en PostgreSQL.

    Se ejecuta solo si CHROMA_HOST esta definido en el entorno.
    """
    chroma_host = os.getenv("CHROMA_HOST")
    if not chroma_host:
        print("ℹ️ [seed] CHROMA_HOST no definido — omitiendo indexacion ChromaDB.")
        return

    try:
        # Agregar el raiz del servicio al path para importar adaptadores
        sys.path.insert(0, str(SERVICE_ROOT))
        from Infraestructura.adaptadores_salida.chromadb_adaptador import ChromaDBAdapter
        from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial

        chroma = ChromaDBAdapter(
            host=chroma_host,
            puerto=int(os.getenv("CHROMA_PORT", "8000")),
        )

        docs_para_chroma: list[DocumentoPatrimonial] = []
        for idx, item in enumerate(documentos_raw):
            fila = json_a_fila(idx, item)
            if not fila:
                continue
            try:
                doc = DocumentoPatrimonial(
                    id=fila["id"],
                    titulo=fila["titulo"],
                    descripcion=fila["descripcion"],
                    url_catalogo=fila["url_catalogo"],
                    anio=fila["anio"],
                    creator=fila["creator"],
                    materias=fila["materias"],
                    lugar=fila["lugar"],
                    categorias=fila["categorias"],
                )
                docs_para_chroma.append(doc)
            except ValueError:
                continue

        print(f"🤖 [seed] Generando embeddings para {len(docs_para_chroma)} documentos en ChromaDB...")
        chroma.indexar_documentos(docs_para_chroma)
        print("✅ [seed] ChromaDB indexado correctamente.")

    except Exception as e:
        print(f"⚠️ [seed] Error al indexar en ChromaDB: {e}")
        print("   La migracion a PostgreSQL continuo correctamente.")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ [seed] DATABASE_URL no definida. Ejemplo:")
        print("   DATABASE_URL=postgresql://uah_user:uah_secret@localhost:5433/uah_archivo \\")
        print("   python Infraestructura/scripts/seed_database.py")
        sys.exit(1)

    print("=" * 60)
    print("  UAH Archivo Patrimonial — Seed de Base de Datos")
    print("=" * 60)
    print(f"🔌 Conectando a: {database_url.split('@')[-1]}")

    # 1. Verificar archivos JSON
    if not JSON_DOCS.exists():
        print(f"❌ [seed] No se encontro: {JSON_DOCS}")
        sys.exit(1)
    if not JSON_CATS.exists():
        print(f"⚠️ [seed] No se encontro categories.json — se omitira.")

    # 2. Leer JSONs
    print(f"\n📂 Leyendo {JSON_DOCS.name} ({JSON_DOCS.stat().st_size / 1024 / 1024:.1f} MB)...")
    with open(JSON_DOCS, "r", encoding="utf-8", errors="ignore") as f:
        documentos_raw = json.load(f)

    cats_raw = {}
    if JSON_CATS.exists():
        print(f"📂 Leyendo {JSON_CATS.name}...")
        with open(JSON_CATS, "r", encoding="utf-8", errors="ignore") as f:
            cats_raw = json.load(f)

    # 3. Conectar a PostgreSQL
    pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    print("✅ Pool de conexiones PostgreSQL creado.")

    try:
        async with pool.acquire() as conn:
            await crear_tablas(conn)

        # 4. Insertar documentos
        print(f"\n🚀 Insertando documentos patrimoniales...")
        total_docs = await insertar_documentos(pool, documentos_raw)

        # 5. Insertar categorias
        print(f"\n🏷️  Insertando categorias...")
        total_cats = await insertar_categorias(pool, cats_raw)

    finally:
        await pool.close()

    # 6. Indexar en ChromaDB (opcional)
    print(f"\n🔍 Indexando embeddings en ChromaDB...")
    indexar_en_chromadb(documentos_raw)

    # 7. Resumen final
    print("\n" + "=" * 60)
    print("  Resumen de la Migracion")
    print("=" * 60)
    print(f"  📄 Documentos insertados en PostgreSQL: {total_docs:,}")
    print(f"  🏷️  Categorias insertadas:              {total_cats:,}")
    print(f"  💾 Archivos JSON conservados en:       {JSON_DOCS.parent}")
    print("=" * 60)
    print("✨ Seed completado. El search-service puede iniciar con PostgreSQL.")


if __name__ == "__main__":
    asyncio.run(main())
