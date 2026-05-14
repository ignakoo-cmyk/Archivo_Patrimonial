from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .repository import DocumentRepository
from .vector_store import VectorStorePort

class SearchEngine:
    """
    Context y aplicación de los algoritmos de búsqueda.
    Implementa Hybrid Search (RRF) combinando Exact Match, TF-IDF y ChromaDB.
    """
    def __init__(self, repository: DocumentRepository, vector_store: VectorStorePort):
        self.repository = repository
        self.vector_store = vector_store
        self.documents = repository.get_all()
        
        # Inicializar TF-IDF en memoria para fallback rápido (reemplaza a search_index.pkl)
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        self.tfidf_matrix = None
        self._build_tfidf_index()

    def _build_tfidf_index(self):
        if not self.documents:
            return
            
        texts = []
        for doc in self.documents:
            text = f"{doc.get('title', '')} {doc.get('description', '')}"
            texts.append(text)
            
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)
            print("✅ [SearchEngine] Índice TF-IDF construido en memoria.")
        except Exception as e:
            print(f"⚠️ [SearchEngine] Error construyendo TF-IDF: {e}")

    def search_exact(self, query: str) -> List[Dict[Any, Any]]:
        query_lower = query.lower().strip()
        results = []
        
        for doc in self.documents:
            title = doc.get('title', '').lower()
            score = 0.0
            
            if query_lower == title:
                score = 1.0
            elif query_lower in title:
                score = 0.9
            
            if score > 0:
                doc_copy = doc.copy()
                doc_copy['relevance_score'] = score
                results.append(doc_copy)
                
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)

    def search_tfidf(self, query: str) -> List[Dict[Any, Any]]:
        if self.tfidf_matrix is None:
            return []
            
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # Top 10
        top_indices = similarities.argsort()[-10:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1: # Umbral mínimo
                doc = self.documents[idx].copy()
                doc['relevance_score'] = float(similarities[idx])
                results.append(doc)
                
        return results

    def search_hybrid(self, query: str, limit: int = 5) -> List[Dict[Any, Any]]:
        """
        Aplica Reciprocal Rank Fusion (RRF)
        """
        exact_results = self.search_exact(query)
        tfidf_results = self.search_tfidf(query)
        semantic_results = self.vector_store.search_similar(query, n_results=10)
        
        # Mapa RRF: id -> score
        rrf_scores = {}
        
        def _apply_rrf(results, weight, k=60):
            for rank, doc in enumerate(results):
                doc_id = doc.get('id') or doc.get('slug')
                if not doc_id:
                    continue
                score = weight * (1.0 / (k + rank + 1))
                if doc_id in rrf_scores:
                    rrf_scores[doc_id] += score
                else:
                    rrf_scores[doc_id] = score
                    
        _apply_rrf(exact_results, weight=1.5)
        _apply_rrf(semantic_results, weight=1.2)
        _apply_rrf(tfidf_results, weight=1.0)
        
        # Ordenar por RRF Score
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_results = []
        for doc_id, score in sorted_ids[:limit]:
            doc = self.repository.get_by_id(doc_id)
            if doc:
                doc_copy = doc.copy()
                doc_copy['relevance_score'] = score
                final_results.append(doc_copy)
                
        return final_results
