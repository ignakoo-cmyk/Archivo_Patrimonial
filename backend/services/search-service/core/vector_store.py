import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any

class VectorStorePort:
    """
    Adapter para ChromaDB. Maneja los embeddings semánticos.
    Reemplaza al antiguo uso de Pickle y cosine_similarity manual.
    """
    def __init__(self):
        chroma_host = os.getenv("CHROMA_HOST", "chromadb")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        try:
            self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            self.collection = self.client.get_or_create_collection(
                name="uah_archive",
                metadata={"hnsw:space": "cosine"}
            )
            print("✅ [VectorStore] Conectado a ChromaDB exitosamente.")
        except Exception as e:
            print(f"⚠️ [VectorStore] Error conectando a ChromaDB (¿está corriendo?): {e}")
            self.client = None
            self.collection = None

    def search_similar(self, query_text: str, n_results: int = 5) -> List[Dict[Any, Any]]:
        """Busca documentos semánticamente similares a la query."""
        if not self.collection:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            # Formatear resultados
            formatted_results = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "relevance_score": 1.0 - (results['distances'][0][i] if 'distances' in results else 0),
                        "metadata": results['metadatas'][0][i] if 'metadatas' in results else {}
                    })
            return formatted_results
        except Exception as e:
            print(f"❌ [VectorStore] Error en búsqueda semántica: {e}")
            return []

    def index_documents(self, documents: List[Dict[Any, Any]]):
        """Indexa documentos en ChromaDB (Reemplaza a convert_embeddings.py)"""
        if not self.collection or not documents:
            return
            
        ids = []
        documents_text = []
        metadatas = []
        
        for doc in documents:
            doc_id = doc.get("id") or doc.get("slug")
            text = f"{doc.get('title', '')}. {doc.get('description', '')}"
            
            if not doc_id or not text.strip():
                continue
                
            ids.append(str(doc_id))
            documents_text.append(text)
            
            # Limpiar metadata para ChromaDB
            meta = {
                "title": str(doc.get("title", "")),
                "href": str(doc.get("href", ""))
            }
            metadatas.append(meta)
            
        try:
            # Upsert en lotes para no saturar
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                self.collection.upsert(
                    documents=documents_text[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size]
                )
            print(f"✅ [VectorStore] {len(ids)} documentos indexados en ChromaDB.")
        except Exception as e:
            print(f"❌ [VectorStore] Error indexando documentos: {e}")
