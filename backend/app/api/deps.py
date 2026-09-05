import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.core.database import get_db
from app.core.rate_limit import limitador_api_key_por_ip, limitador_api_key_por_token
from app.core.security import decode_access_token, hash_integration_token
from app.models.integration_token import IntegrationToken
from app.models.user import User, UserRole

# Fase 10 (hardening): límites deliberadamente distintos para dos abusos
# distintos. Por IP, generoso pero acotado, para encarecer probar muchas
# claves distintas (fuerza bruta/spray) sin bloquear a una integración
# legítima que reintenta tras un error transitorio. Por credencial ya
# válida, más permisivo en volumen (una integración real hace ráfagas de
# peticiones) pero existente, para que una clave filtrada no pueda usarse
# para un abuso ilimitado sin que salte un 429.
_LIMITE_INTENTOS_API_KEY_POR_IP = 30
_VENTANA_INTENTOS_API_KEY_POR_IP_SEGUNDOS = 60
_LIMITE_PETICIONES_POR_TOKEN = 120
_VENTANA_PETICIONES_POR_TOKEN_SEGUNDOS = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# No lanza 401 si falta el header: permite que `require_access` compruebe
# primero si hay una credencial de integración (X-API-Key) antes de exigir un
# JWT humano.
_oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _credenciales_invalidas() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise _credenciales_invalidas() from None

    user_id = payload.get("sub")
    if user_id is None:
        raise _credenciales_invalidas()

    try:
        user = db.get(User, uuid.UUID(user_id))
    except ValueError:
        raise _credenciales_invalidas() from None

    if user is None or not user.is_active:
        raise _credenciales_invalidas()

    return user


def require_roles(*roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción.",
            )
        return current_user

    return dependency


# --- Fase 9: identidad unificada (usuario humano o integración/API key) ---


@dataclass
class Actor:
    """Representa a quien hace la petición a un endpoint de la superficie de
    integración: un usuario humano autenticado por JWT, o una integración
    (p. ej. el servidor MCP) autenticada por API key. Solo uno de
    ``user``/``integration`` está relleno."""

    organization_id: uuid.UUID
    user: User | None = None
    integration: IntegrationToken | None = None

    @property
    def id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None

    @property
    def is_integration(self) -> bool:
        return self.integration is not None


def _autenticar_integration_token(db: Session, api_key: str, client_ip: str) -> IntegrationToken:
    if not limitador_api_key_por_ip.permitir(
        f"api_key:{client_ip}",
        limite=_LIMITE_INTENTOS_API_KEY_POR_IP,
        ventana_segundos=_VENTANA_INTENTOS_API_KEY_POR_IP_SEGUNDOS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos con credenciales de integración. Inténtalo de nuevo en un minuto.",
        )

    token_hash = hash_integration_token(api_key)
    integracion = db.query(IntegrationToken).filter(IntegrationToken.token_hash == token_hash).first()
    if integracion is None:
        raise _credenciales_invalidas()
    if integracion.revoked_at is not None or not integracion.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La credencial de integración ha sido revocada.",
        )
    if integracion.expires_at is not None and integracion.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La credencial de integración ha caducado.",
        )
    if not limitador_api_key_por_token.permitir(
        f"token:{integracion.id}",
        limite=_LIMITE_PETICIONES_POR_TOKEN,
        ventana_segundos=_VENTANA_PETICIONES_POR_TOKEN_SEGUNDOS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Esta credencial de integración ha superado su límite de peticiones. Inténtalo de nuevo en un minuto.",
        )
    integracion.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return integracion


def require_access(*, roles: tuple[UserRole, ...], scope: str):
    """Autoriza el acceso a un endpoint tanto a un usuario humano (JWT, por
    rol) como a una integración (API key, por scope). Ambos casos devuelven
    un `Actor` unificado con `organization_id` ya resuelto — nunca se confía
    en un valor de organización recibido del cliente.

    Toda petición autenticada por integración (nunca las de un usuario
    humano, para no inflar el registro con el tráfico normal del frontend)
    genera un evento ``mcp_tool_call`` en el AuditLog — la superficie de
    integración es de gobierno/cumplimiento por sí misma, no solo sus
    operaciones de escritura. El scope solicitado hace de nombre de
    herramienta implícito (coincide 1:1 con las herramientas MCP)."""

    def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        token: str | None = Depends(_oauth2_scheme_opcional),
        db: Session = Depends(get_db),
    ) -> Actor:
        if x_api_key is not None:
            client_ip = request.client.host if request.client else "desconocida"
            integracion = _autenticar_integration_token(db, x_api_key, client_ip)
            if scope not in integracion.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Esta credencial de integración no tiene el scope necesario ({scope}).",
                )
            registrar_evento(
                db,
                organization_id=integracion.organization_id,
                user_id=None,
                integration_token_id=integracion.id,
                action="mcp_tool_call",
                entity_type=scope.split(":", 1)[0],
                ip_address=request.client.host if request.client else None,
                details={"scope": scope, "method": request.method, "path": request.url.path},
            )
            db.commit()
            return Actor(organization_id=integracion.organization_id, integration=integracion)

        if token is not None:
            usuario = get_current_user(token=token, db=db)
            if usuario.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para realizar esta acción.",
                )
            return Actor(organization_id=usuario.organization_id, user=usuario)

        raise _credenciales_invalidas()

    return dependency
