"""
Adaptador de Infraestructura — NLPExtractorAdapter (Regex + Taxonomía)
=======================================================================
Extrae entidades del lenguaje natural del usuario y las mapea a la
taxonomía del Archivo Patrimonial UAH para producir un FiltroMetadatos.

Estrategia: Regex + Vocabulario Controlado (sin dependencias externas).
  Por qué no spaCy aquí:
    - El corpus del archivo es un dominio cerrado y conocido.
    - spaCy agrega ~43MB al contenedor Docker y latencia en startup.
    - Los actores, materias y lugares del archivo son un vocabulario finito
      extraído de los metadatos Dublin Core del propio JSON.
    - Para nombres desconocidos: el patrón "Apellido, Nombre" es suficientemente
      discriminativo en español para detectar personas sin NER externo.

Flujo de extracción:
  1. Detectar rango de años con regex de fechas (1800-2030).
  2. Detectar nombres de personas por patrón "Apellido, Nombre" (Dublin Core).
  3. Detectar nombres de instituciones por prefijos conocidos.
  4. Detectar materias por matching contra el tesauro controlado del archivo.
  5. Detectar lugares por matching contra la lista de coberturas geográficas.
  → Producir FiltroMetadatos inmutable.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from Dominio.objetos_de_valor.filtro_metadatos import FiltroMetadatos


# ─────────────────────────────────────────────────────────────────────────────
# Tesauro controlado del Archivo Patrimonial UAH
# (extraído de los valores más frecuentes en dc:subject del JSON real)
# ─────────────────────────────────────────────────────────────────────────────

# Materias del tesauro archivístico — mapeadas a tokens de búsqueda
_MATERIAS_TESAURO: dict[str, tuple[str, ...]] = {
    "Derechos humanos":         ("derechos humanos", "ddhh", "derechos"),
    "Dictadura":                ("dictadura", "regimen militar", "junta militar", "pinochet"),
    "Democracia":               ("democracia", "democratizacion", "transicion"),
    "Plebiscito":               ("plebiscito", "voto", "referendum", "no"),
    "Educación":                ("educacion", "educacional", "enseñanza", "profesores", "estudiantes"),
    "Movimientos Sociales":     ("movimientos sociales", "protesta", "marcha", "manifestacion"),
    "Movimientos Estudiantiles":("movimientos estudiantiles", "feuc", "feutem", "federacion estudiantil"),
    "Partidos políticos":       ("partidos politicos", "partido", "dc", "democracia cristiana", "ps", "pdc"),
    "Iglesia":                  ("iglesia", "jesuita", "jesuitas", "sacerdote", "obispo", "vicaría"),
    "Fotografías":              ("fotografia", "fotografias", "foto", "imagen", "archivo fotografico"),
    "Documentos":               ("documento", "documentos", "acta", "carta", "correspondencia", "informe"),
    "Volantes":                 ("volante", "volantes", "panfleto"),
    "Música":                   ("musica", "musical", "compositor", "concierto", "docta"),
    "Historia":                 ("historia", "historico", "memoria", "patrimonio"),
    "Universidad":              ("universidad", "uah", "hurtado", "academico", "facultad"),
    "Derechos Civiles":         ("derechos civiles", "ciudadania", "civil"),
    "Minorías":                 ("minorias", "minoria sexual", "homosexual", "lgbtq"),
    "Acuerdos económicos":      ("economicos", "economia", "acuerdo economico", "tratado"),
    "Medioambiente":            ("medioambiente", "ambiental", "ecologia"),
    "Mujer":                    ("mujer", "mujeres", "genero", "feminismo", "feminista"),
}

# Lugares del dc:coverage más frecuentes
_LUGARES_CONOCIDOS: tuple[str, ...] = (
    "Santiago", "Chile", "Valparaíso", "Concepción", "Temuco",
    "Antofagasta", "Iquique", "La Serena", "Rancagua", "Talca",
    "Latinoamerica", "América Latina", "Argentina", "Peru", "Bolivia",
)

# Instituciones prefijo — dc:creator de tipo institución
_PREFIJOS_INSTITUCIONES: tuple[str, ...] = (
    "universidad", "partido", "movimiento", "comando", "asociacion",
    "federacion", "corporacion", "ministerio", "fundacion", "iglesia",
    "comite", "comision", "congreso", "gobierno", "municipio",
)

# Patrón para nombres de personas en formato "Apellido, Nombre" (Dublin Core)
_PATRON_PERSONA_DC = re.compile(
    r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)"
    r"\s*,\s*"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\b"
)

# Patrón para años válidos (1800–2030)
_PATRON_ANIO = re.compile(r"\b(1[89]\d{2}|20[012]\d)\b")

# Patrón para rangos de años: "entre 1990 y 2000", "de 1973 a 1990", "desde 1973"
_PATRON_RANGO_ANIO = re.compile(
    r"(?:entre|de|desde)\s+(1[89]\d{2}|20[012]\d)"
    r"(?:\s+(?:y|a|hasta)\s+(1[89]\d{2}|20[012]\d))?"
)


def _normalizar_query(texto: str) -> str:
    """Normaliza el texto de consulta para matching."""
    nfd = unicodedata.normalize("NFD", texto.lower())
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return sin_acentos


class NLPExtractorAdapter:
    """
    Extractor de entidades semánticas desde lenguaje natural.

    Traduce la consulta libre del usuario a un FiltroMetadatos estructurado
    que puede usarse directamente para pre-filtrar el corpus archivístico.

    No tiene dependencias externas: usa Python estándar + re + unicodedata.
    """

    def __init__(self, vocabulario_creators: set[str] | None = None, vocabulario_materias: set[str] | None = None) -> None:
        """
        Args:
            vocabulario_creators: Conjunto de todos los dc:creator únicos del JSON,
                                  pre-cargados para matching exacto. Opcional pero
                                  mejora enormemente la precisión de detección de actores.
            vocabulario_materias: Conjunto de todas las materias reales de categories.json.
        """
        self._vocabulario_creators: set[str] = vocabulario_creators or set()
        self._vocabulario_materias: set[str] = vocabulario_materias or set()
        # Índice normalizado de creators para búsqueda O(1)
        self._creators_normalizados: dict[str, str] = {
            _normalizar_query(c): c
            for c in self._vocabulario_creators
        }

        # Índice normalizado de materias para búsqueda O(1)
        self._materias_normalizadas: dict[str, str] = {
            _normalizar_query(m): m
            for m in self._vocabulario_materias
        }

    def extraer_filtros(self, consulta: str) -> FiltroMetadatos:
        """
        Extrae un FiltroMetadatos desde el texto libre del usuario.

        Algoritmo:
          1. Rango de años con regex (mayor prioridad, alta precision).
          2. Actor/Creador:
             a. Matching exacto contra vocabulario de creators.
             b. Patrón "Apellido, Nombre" en el texto.
             c. Nombres propios solitarios reconocibles.
          3. Materias: matching contra el tesauro controlado.
          4. Lugar: matching contra lista de lugares conocidos.

        Args:
            consulta: Texto libre del usuario en español.

        Returns:
            FiltroMetadatos inmutable (puede estar vacío si no se detecta nada).
        """
        consulta_norm = _normalizar_query(consulta)

        actor_creador = self._extraer_actor(consulta, consulta_norm)
        materias = self._extraer_materias(consulta_norm)
        lugar = self._extraer_lugar(consulta, consulta_norm)
        anio_desde, anio_hasta = self._extraer_rango_anios(consulta)

        filtro = FiltroMetadatos(
            actor_creador=actor_creador,
            materias=tuple(materias),
            lugar=lugar,
            anio_desde=anio_desde,
            anio_hasta=anio_hasta,
        )

        if not filtro.esta_vacio:
            print(f"🧠 [NLPExtractor] Extraído: {filtro.resumen}")

        return filtro

    # ──────────────────────────────────────────────────────────
    # Métodos privados de extracción
    # ──────────────────────────────────────────────────────────

    def _extraer_actor(self, consulta: str, consulta_norm: str) -> Optional[str]:
        """
        Estrategia 1: matching contra vocabulario de dc:creator del JSON.
        Estrategia 2: patrón regex "Apellido, Nombre" (Dublin Core).
        Estrategia 3: cognomen reconocidos del dominio (lista corta de actores frecuentes).
        """
        # --- Estrategia 1: matching exacto contra vocabulario del archivo ---
        for creator_norm, creator_original in self._creators_normalizados.items():
            # Verificar si el nombre normalizado aparece en la consulta
            if len(creator_norm) >= 5 and creator_norm in consulta_norm:
                return creator_original
            # Matching por apellido solo (primera palabra antes de la coma)
            apellido = creator_norm.split(",")[0].strip()
            if len(apellido) >= 4 and re.search(r"\b" + re.escape(apellido) + r"\b", consulta_norm):
                return creator_original

        # --- Estrategia 2: patrón "Apellido, Nombre" directamente en el texto ---
        match = _PATRON_PERSONA_DC.search(consulta)
        if match:
            return f"{match.group(1)}, {match.group(2)}"

        return None

    def _extraer_materias(self, consulta_norm: str) -> list[str]:
        """Detecta materias en la consulta normalizada usando el tesauro estático y dinámico."""
        materias_encontradas: list[str] = []
        
        # 1. Matching contra el tesauro oficial (sinónimos duros)
        for materia_oficial, tokens in _MATERIAS_TESAURO.items():
            for token in tokens:
                # Buscar token completo en la consulta
                if re.search(r"\b" + re.escape(token) + r"\b", consulta_norm):
                    materias_encontradas.append(materia_oficial)
                    break  # Solo añadir una vez por materia

        # 2. Matching dinámico inteligente contra categories.json
        # Como pueden ser miles, usamos 'in' y luego regex para confirmar boundaries.
        for materia_norm, materia_original in self._materias_normalizadas.items():
            # Evitar falsos positivos en palabras cortas
            if len(materia_norm) >= 4 and materia_norm in consulta_norm:
                if re.search(r"\b" + re.escape(materia_norm) + r"\b", consulta_norm):
                    if materia_original not in materias_encontradas:
                        materias_encontradas.append(materia_original)

        return materias_encontradas

    def _extraer_lugar(self, consulta: str, consulta_norm: str) -> Optional[str]:
        """Detecta lugares por matching contra la lista de coberturas conocidas."""
        for lugar in _LUGARES_CONOCIDOS:
            lugar_norm = _normalizar_query(lugar)
            if re.search(r"\b" + re.escape(lugar_norm) + r"\b", consulta_norm):
                return lugar
        return None

    def _extraer_rango_anios(self, consulta: str) -> tuple[Optional[int], Optional[int]]:
        """
        Extrae rango de años de la consulta.
        Detecta: "entre 1990 y 2000", "desde 1973", "de 1973 a 1990", "en 1973".
        """
        anio_desde: Optional[int] = None
        anio_hasta: Optional[int] = None

        # Buscar rango explícito
        match_rango = _PATRON_RANGO_ANIO.search(consulta.lower())
        if match_rango:
            anio_desde = int(match_rango.group(1))
            if match_rango.group(2):
                anio_hasta = int(match_rango.group(2))
            return anio_desde, anio_hasta

        # Buscar año solitario → filtro puntual (margen ±3 años para flexibilidad)
        todos_anios = [int(a) for a in _PATRON_ANIO.findall(consulta)]
        if len(todos_anios) == 1:
            anio_desde = todos_anios[0] - 3
            anio_hasta = todos_anios[0] + 3
        elif len(todos_anios) >= 2:
            anio_desde = min(todos_anios)
            anio_hasta = max(todos_anios)

        return anio_desde, anio_hasta
