from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Valor de desarrollo únicamente: apunta a un Postgres local con credenciales
# triviales. Se usa como valor por defecto para no exigir un .env en un
# primer arranque local, pero está explícitamente prohibido en producción
# (ver _validar_seguridad_en_produccion más abajo).
_DATABASE_URL_DESARROLLO = "postgresql+psycopg://grcplatform:grcplatform@localhost:5433/grcplatform"

_ENTORNOS_VALIDOS = {"development", "test", "production"}


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "GRCPlatform"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = _DATABASE_URL_DESARROLLO

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Almacenamiento de evidencias. Ruta relativa al directorio de trabajo del
    # backend (dentro del bind mount de Docker, por lo que persiste en el host).
    EVIDENCE_STORAGE_PATH: str = "storage/evidence"
    MAX_EVIDENCE_FILE_SIZE_MB: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def max_evidence_file_size_bytes(self) -> int:
        return self.MAX_EVIDENCE_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _validar_seguridad_en_produccion(self) -> "Settings":
        """Fase 10 (hardening): un valor de desarrollo razonable como valor
        por defecto nunca debe colarse silenciosamente en producción. Falla
        rápido y explícito al arrancar en vez de arrancar "seguro a medias"."""
        if self.ENVIRONMENT not in _ENTORNOS_VALIDOS:
            raise ValueError(
                f"ENVIRONMENT={self.ENVIRONMENT!r} no es válido. Usa uno de: {sorted(_ENTORNOS_VALIDOS)}."
            )

        if not self.is_production:
            return self

        if self.DATABASE_URL == _DATABASE_URL_DESARROLLO:
            raise ValueError(
                "ENVIRONMENT=production pero DATABASE_URL sigue siendo el valor de "
                "desarrollo por defecto. Define una DATABASE_URL real en el entorno."
            )
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                "ENVIRONMENT=production exige SECRET_KEY de al menos 32 caracteres "
                "(genera uno con: python -c \"import secrets; print(secrets.token_urlsafe(32))\")."
            )
        if "*" in self.cors_origins_list:
            raise ValueError(
                "ENVIRONMENT=production no permite CORS_ORIGINS='*'. Define los "
                "orígenes exactos permitidos (separados por comas)."
            )
        return self


settings = Settings()
