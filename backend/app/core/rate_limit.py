"""Rate limiting simple en memoria (Fase 10: hardening).

Pensado deliberadamente para un despliegue de una sola instancia/un solo
proceso worker (ver `docker-compose.yml`: un único contenedor `backend`).
Un contador en memoria de proceso es suficiente para ese caso y evita
introducir una dependencia de infraestructura (p. ej. Redis) que este
proyecto no necesita todavía — ver `docs/SECURITY.md` para la limitación
conocida si en el futuro se despliega con varias réplicas/workers (en ese
caso cada proceso tendría su propio contador independiente, y haría falta
un almacén compartido).

Algoritmo: ventana fija por clave (`clave` = IP, id de credencial, etc.),
protegido por un lock — coste O(1) amortizado por comprobación, sin
crecimiento ilimitado de memoria (las colas antiguas se purgan en cada
comprobación de esa misma clave)."""

import threading
import time
from collections import defaultdict, deque


class LimitadorDeVentanaFija:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._peticiones: dict[str, deque[float]] = defaultdict(deque)

    def permitir(self, clave: str, *, limite: int, ventana_segundos: float) -> bool:
        """Devuelve True si la petición identificada por `clave` puede
        continuar, False si ha superado `limite` peticiones en los últimos
        `ventana_segundos`."""
        ahora = time.monotonic()
        with self._lock:
            cola = self._peticiones[clave]
            while cola and ahora - cola[0] > ventana_segundos:
                cola.popleft()
            if len(cola) >= limite:
                return False
            cola.append(ahora)
            return True

    def reiniciar(self) -> None:
        """Solo para tests: limpia todo el estado en memoria para que el
        límite de una prueba no se acumule sobre las siguientes (todas
        comparten el mismo proceso de pytest, y por tanto la misma
        instancia de este limitador)."""
        with self._lock:
            self._peticiones.clear()


# Instancias de proceso, una por superficie protegida — mantenerlas
# separadas evita que el abuso de una consuma el margen de la otra.
limitador_login = LimitadorDeVentanaFija()
limitador_api_key_por_ip = LimitadorDeVentanaFija()
limitador_api_key_por_token = LimitadorDeVentanaFija()
