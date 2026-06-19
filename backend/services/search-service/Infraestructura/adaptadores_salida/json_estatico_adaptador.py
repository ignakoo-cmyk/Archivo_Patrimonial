import json
import os
from typing import Optional

from Dominio.puertos.repositorio_salida import AtoMRepositoryPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


class StaticJsonRepositoryAdapter(AtoMRepositoryPort):
    """
    Adaptador estático JSON que simula la base de datos de AtoM.
    Carga eficientemente en memoria los archivos clean_with_metadata.json y categories.json.
    """

    def __init__(self, ruta_json: str = "Infraestructura/datos/clean_with_metadata.json") -> None:
        self._ruta_json = ruta_json
        self._documentos: list[DocumentoPatrimonial] = []
        self._indice_por_id: dict[str, DocumentoPatrimonial] = {}
        self._cargar_memoria()

    def _cargar_memoria(self) -> None:
        """Carga el JSON principal en memoria."""
        if not os.path.exists(self._ruta_json):
            return

        with open(self._ruta_json, "r", encoding="utf-8", errors="ignore") as f:
            datos = json.load(f)

        for idx, item in enumerate(datos):
            id_doc = item.get("id") or item.get("slug")
            if not id_doc:
                id_doc = str(idx)
            else:
                id_doc = str(id_doc)
                
            titulo = item.get("title", "").strip()
            if not titulo:
                continue

            doc = DocumentoPatrimonial(
                id=id_doc,
                titulo=titulo,
                descripcion=item.get("description", ""),
                url_catalogo=item.get("href", ""),
                anio=item.get("year") or item.get("date"),
            )
            
            self._documentos.append(doc)
            self._indice_por_id[doc.id] = doc
            if item.get("slug"):
                self._indice_por_id[str(item.get("slug"))] = doc

    def obtener_todos(self) -> list[DocumentoPatrimonial]:
        return self._documentos

    def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        return self._indice_por_id.get(id_documento)

    def buscar(self, query: str) -> list[DocumentoPatrimonial]:
        """
        Búsqueda simple por palabras clave en título o descripción
        para simular la búsqueda directa en base de datos.
        """
        query_lower = query.lower()
        resultados = []
        for doc in self._documentos:
            titulo_lower = doc.titulo.lower() if doc.titulo else ""
            desc_lower = doc.descripcion.lower() if doc.descripcion else ""
            
            if query_lower in titulo_lower or query_lower in desc_lower:
                resultados.append(doc)
                
        return resultados
