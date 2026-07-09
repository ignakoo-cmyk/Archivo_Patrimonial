"""
Locust — Prueba de Carga del API Gateway (puerto 8059)
=======================================================
Simula usuarios concurrentes accediendo al sistema a través del Gateway.

Configuración:
    locust -f backend/locustfile.py --host http://localhost:8059 --users 100 --spawn-rate 10 --run-time 60s --headless

Endpoints probados:
  - GET  /health                    → verificación de latencia base
  - GET  /api/v1/search/query?q=... → búsqueda con query params (legado)
  - POST /api/v1/search             → búsqueda con body JSON (nuevo endpoint)
"""

from locust import HttpUser, task, between
import json
import random


CONSULTAS_PRUEBA = [
    "decretos fundacionales del archivo patrimonial",
    "actas de sesión universidad alberto hurtado",
    "colección fotografías históricas",
    "documentos Aylwin presidencia",
    "archivos jesuitas Chile colonial",
    "memorias anuales facultad teología",
    "correspondencia rectoría siglo XX",
]


class UsuarioArchivoPatrimonial(HttpUser):
    """
    Simula un usuario real del Archivo Patrimonial UAH:
    - 75% del tiempo hace búsquedas (carga intensiva)
    - 25% verifica el health del gateway (carga liviana)
    """
    wait_time = between(1, 3)

    @task(1)
    def validar_health_check(self):
        """Verifica que el Gateway esté respondiendo (latencia de referencia)."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check falló: HTTP {response.status_code}")

    @task(3)
    def simular_busqueda_post(self):
        """
        Búsqueda vía POST /api/v1/search with {"query": "..."} body for search.
        Endpoint nuevo (P1 fix): corrige el 100% error rate de Locust.
        El campo requerido es 'query'.
        """
        consulta = random.choice(CONSULTAS_PRUEBA)
        payload = {"query": consulta, "limite": 5}
        headers = {"Content-Type": "application/json"}

        with self.client.post(
            "/api/v1/search",
            data=json.dumps(payload),
            headers=headers,
            catch_response=True,
            name="POST /api/v1/search",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 422:
                response.failure(f"Error de validación (422): {response.text[:200]}")
            elif response.status_code == 503:
                response.failure("Search service no disponible (503)")
            elif response.status_code == 0:
                response.failure("Fallo de conexión al Gateway (servidor colapsado)")
            else:
                response.failure(f"Error inesperado: HTTP {response.status_code} — {response.text[:100]}")

    @task(1)
    def simular_busqueda_get(self):
        """
        Búsqueda vía GET /api/v1/search/query?q=... (endpoint legado).
        Mantiene compatibilidad y cobertura de ambos endpoints en la prueba de carga.
        """
        consulta = random.choice(CONSULTAS_PRUEBA)

        with self.client.get(
            f"/api/v1/search/query?q={consulta}&limite=5",
            catch_response=True,
            name="GET /api/v1/search/query",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 422:
                response.failure(f"Error de validación (422): {response.text[:200]}")
            elif response.status_code == 0:
                response.failure("Fallo de conexión al Gateway (servidor colapsado)")
            else:
                response.failure(f"Error inesperado: HTTP {response.status_code}")