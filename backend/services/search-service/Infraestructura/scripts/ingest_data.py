import json
import os
import chromadb
from chromadb.utils import embedding_functions
import time

def ingest():
    print("🧹 Iniciando proceso de ingesta de datos en ChromaDB con Modelo Local de IA...")
    
    # 1. Configurar modelo de embedding local (gratis, sin límites de API)
    # ChromaDB usa por defecto all-MiniLM-L6-v2 que es excelente y súper rápido
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    
    # 2. Conectar a ChromaDB
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = os.getenv("CHROMA_PORT", "8001")
    
    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        # Borrar si ya existe para asegurar ingesta limpia
        try:
            client.delete_collection("uah_archive")
        except:
            pass
            
        collection = client.get_or_create_collection(
            name="uah_archive",
            embedding_function=default_ef,
            metadata={"hnsw:space": "cosine"}
        )
        print("✅ Conectado a ChromaDB con motor de Embeddings Local.")
    except Exception as e:
        print(f"❌ No se pudo conectar a ChromaDB: {e}")
        return

    # 3. Leer JSON de documentos
    json_path = "Infraestructura/datos/clean_with_metadata.json"
    if not os.path.exists(json_path):
        json_path = "backend/services/search-service/Infraestructura/datos/clean_with_metadata.json"
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        print(f"📖 {len(documents)} documentos leídos del archivo JSON.")
    except Exception as e:
        print(f"❌ Error leyendo JSON: {e}")
        return

    # 4. Ingestar y generar embeddings localmente
    print(f"🚀 Generando embeddings locales e indexando {len(documents)} documentos...")
    
    batch_size = 200 # Podemos usar un lote mucho más grande porque es local
    total_procesados = 0
    
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        
        ids = []
        texts = []
        metadatas = []
        
        for j, doc in enumerate(batch_docs):
            doc_id = str(doc.get("id") or doc.get("slug") or (i + j))
            title = doc.get('title', '')
            desc = doc.get('description', '')
            content = f"{title}. {desc}"
            
            if not content.strip():
                continue
                
            ids.append(doc_id)
            texts.append(content)
            metadatas.append({
                "title": str(title),
                "href": str(doc.get("href", ""))
            })
            
        try:
            # Upsert en ChromaDB (la generación del embedding es automática y local)
            if ids:
                collection.upsert(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas
                )
                total_procesados += len(ids)
                print(f"📦 Procesados: {min(i + batch_size, len(documents))}/{len(documents)} (Total indexados: {total_procesados})")
            
        except Exception as e:
            print(f"⚠️ Error en lote {i}: {e}")
            time.sleep(2)
        
    print("✨ ¡Ingesta completada con éxito! La búsqueda semántica está lista para usar.")

if __name__ == "__main__":
    ingest()
