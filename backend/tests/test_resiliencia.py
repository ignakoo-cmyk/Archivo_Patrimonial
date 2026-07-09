import pytest
import httpx

@pytest.mark.asyncio
async def test_resiliencia_aislamiento_red():
    """
    Verifica que los microservicios internos no expongan sus puertos al exterior,
    obligando a que todo el tráfico sea orquestado de forma segura por el API Gateway.
    """
    url_interna_chat = "http://localhost:3001/api/v1/chat/message"

    # Le ponemos un timeout corto (3 segundos) para que no se quede colgado
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            response = await client.post(
                url_interna_chat, 
                json={"message": "test de intrusión", "conversation_id": "test-resiliencia"}
            )
            
            # Si el servicio responde, verificamos que lo haya bloqueado por seguridad
            assert response.status_code in [401, 403], f"Vulnerabilidad detectada: El microservicio permitió el acceso y respondió con código {response.status_code}."
            
        except httpx.ConnectError:
            # ÉXITO: El puerto está completamente cerrado y aislado. (Este es el comportamiento deseado)
            assert True
            
        except httpx.TimeoutException:
            # FALLO: El puerto está abierto, aceptó la conexión, pero tardó demasiado en responder.
            pytest.fail("Vulnerabilidad detectada: El puerto 3001 está abierto al exterior. (El servidor aceptó la conexión pero dio Timeout).")