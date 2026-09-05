import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

INTEGRATION_TOKEN_PREFIX = "grc_"


def generar_integration_token() -> str:
    """Genera un secreto de integración de alta entropía. Solo se muestra al
    cliente en el momento de la creación; nunca se recupera después."""
    return f"{INTEGRATION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_integration_token(token: str) -> str:
    """Hash determinista (SHA-256) para poder buscar el token por igualdad
    indexada. No es un hash lento (bcrypt) a propósito: el secreto ya tiene
    entropía suficiente por ser generado por el servidor, no elegido por un
    humano (ver docstring de IntegrationToken)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
