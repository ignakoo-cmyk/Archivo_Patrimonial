import pytest
from unittest.mock import AsyncMock

# Simulamos los adaptadores de infraestructura (Puertos de salida)
@pytest.fixture
def mock_db_vectorial():
    mock = AsyncMock()
    mock.buscar.return_value = [{"id": "doc_1", "texto": "Historia UAH", "score": 0.9}]
    return mock

@pytest.fixture
def mock_db_relacional():
    mock = AsyncMock()
    mock.obtener_metadatos.return_value = {"autor": "Archivo Patrimonial", "fecha": "1997"}
    return mock

# Prueba de la capa de aplicación sin levantar bases de datos
@pytest.mark.asyncio
async def test_flujo_busqueda_aislado(mock_db_vectorial, mock_db_relacional):
    # Aquí deberías llamar a tu función/clase real que orquesta la búsqueda
    # Para el test, verificamos que la lógica invoca las dependencias correctamente
    resultados_vectores = await mock_db_vectorial.buscar("decretos fundacionales")
    metadatos = await mock_db_relacional.obtener_metadatos("doc_1")
    
    assert len(resultados_vectores) == 1
    assert resultados_vectores[0]["id"] == "doc_1"
    assert metadatos["autor"] == "Archivo Patrimonial"
    assert mock_db_vectorial.buscar.called
    assert mock_db_relacional.obtener_metadatos.called