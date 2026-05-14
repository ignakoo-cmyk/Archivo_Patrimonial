import json
import os
from typing import List, Dict, Any

class DocumentRepository:
    """
    Port (Hexagonal Architecture) para acceder a los documentos.
    Actualmente lee del JSON exportado, pero podría cambiarse a la API de AtoM en el futuro.
    """
    def __init__(self, data_path: str = "data/clean_with_metadata.json"):
        self.data_path = data_path
        self._documents = []
        self._load_documents()

    def _load_documents(self):
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8', errors="ignore") as f:
                    self._documents = json.load(f)
                print(f"✅ [DocumentRepository] {len(self._documents)} documentos cargados desde {self.data_path}")
            else:
                print(f"⚠️ [DocumentRepository] Archivo {self.data_path} no encontrado.")
        except Exception as e:
            print(f"❌ [DocumentRepository] Error cargando documentos: {e}")

    def get_all(self) -> List[Dict[Any, Any]]:
        return self._documents

    def get_by_id(self, doc_id: str) -> Dict[Any, Any]:
        for doc in self._documents:
            if doc.get("id") == doc_id or doc.get("slug") == doc_id:
                return doc
        return {}
