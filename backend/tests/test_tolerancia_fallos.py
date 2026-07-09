import pytest
import httpx
import subprocess
import time

@pytest.mark.asyncio
async def test_tolerancia_fallos_y_recuperacion_docker():
    """
    Simula un fallo crítico (caída) en un microservicio interno para validar
    que el API Gateway aísla el error (no colapsa) y que el motor de Docker
    auto-recupera el contenedor basándose en las políticas del compose.
    """
    nombre_contenedor = "uah_search_service"
    
    # 1. CAOS: Simulamos un colapso interno forzando al proceso principal 1 a cerrarse con error
    print(f"\n[Caos] Provocando un fallo interno fatal en {nombre_contenedor}...")
    subprocess.run(["docker", "exec", nombre_contenedor, "kill", "-9", "1"], capture_output=True)
    
    # 2. AISLAMIENTO: Verificamos que el Gateway (puerto 8059) SIGUE VIVO
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            response = await client.get("http://localhost:8059/")
            assert response.status_code != 0 
            print("[Éxito] El Gateway sobrevivió a la caída de un microservicio interno.")
        except httpx.ConnectError:
            pytest.fail("Fallo de Resiliencia: El Gateway colapsó porque un microservicio interno murió.")
            
    # 3. AUTO-RECUPERACIÓN: Esperamos a que Docker aplique su política 'restart'
    print("[Espera] Dándole 5 segundos a Docker para revivir el contenedor tras el fallo...")
    time.sleep(5)
    
    # 4. VERIFICACIÓN: Comprobamos el estado del contenedor en Docker
    resultado = subprocess.run(
        ["docker", "ps", "--filter", f"name={nombre_contenedor}", "--format", "{{.Status}}"], 
        capture_output=True, text=True
    )
    
    estado_docker = resultado.stdout.strip()
    # Si Docker lo revivió, el status dirá algo como "Up 2 seconds"
    assert "Up" in estado_docker, f"Fallo de Infraestructura: Docker no recuperó el contenedor. Estado actual: '{estado_docker}'"
    print(f"[Éxito] Contenedor auto-recuperado exitosamente. Estado de Docker: {estado_docker}")