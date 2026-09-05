import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.audit import registrar_evento
from app.core.database import get_db
from app.core.security import generar_integration_token, hash_integration_token
from app.models.integration_token import INTEGRATION_TOKEN_PREFIX_LEN, IntegrationToken
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.integration_token import IntegrationTokenCreate, IntegrationTokenCreated, IntegrationTokenRead

router = APIRouter()

# Solo Admin gestiona credenciales de integración (crear/revocar); GRC Manager
# puede consultarlas (visibilidad de qué integraciones existen) pero no
# crearlas ni revocarlas — no aporta valor real concederle más que lectura.
_ROLES_LECTURA = (UserRole.ADMIN, UserRole.GRC_MANAGER)
_ROLES_ESCRITURA = (UserRole.ADMIN,)


def _ip_del_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def _obtener_token_o_404(db: Session, token_id: uuid.UUID, current_user: User) -> IntegrationToken:
    integracion = (
        db.query(IntegrationToken)
        .filter(
            IntegrationToken.id == token_id,
            IntegrationToken.organization_id == current_user.organization_id,
        )
        .first()
    )
    if integracion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial de integración no encontrada.")
    return integracion


@router.post("", response_model=IntegrationTokenCreated, status_code=status.HTTP_201_CREATED)
def create_integration_token(
    payload: IntegrationTokenCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> IntegrationTokenCreated:
    secreto = generar_integration_token()
    integracion = IntegrationToken(
        organization_id=current_user.organization_id,
        name=payload.name,
        token_hash=hash_integration_token(secreto),
        token_prefix=secreto[:INTEGRATION_TOKEN_PREFIX_LEN],
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        created_by_id=current_user.id,
    )
    db.add(integracion)
    db.flush()
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="integration_token_created",
        entity_type="integration_token",
        entity_id=integracion.id,
        ip_address=_ip_del_cliente(request),
        details={"name": payload.name, "scopes": payload.scopes},
    )
    db.commit()
    db.refresh(integracion)
    return IntegrationTokenCreated(
        **IntegrationTokenRead.model_validate(integracion).model_dump(),
        token=secreto,
    )


@router.get("", response_model=Page[IntegrationTokenRead])
def list_integration_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_LECTURA)),
    page: int = 1,
    page_size: int = 20,
) -> Page[IntegrationTokenRead]:
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    consulta = db.query(IntegrationToken).filter(
        IntegrationToken.organization_id == current_user.organization_id
    )
    total = consulta.count()
    tokens = (
        consulta.order_by(IntegrationToken.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(items=tokens, total=total, page=page, page_size=page_size)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_integration_token(
    token_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ROLES_ESCRITURA)),
) -> None:
    integracion = _obtener_token_o_404(db, token_id, current_user)
    integracion.is_active = False
    integracion.revoked_at = datetime.now(timezone.utc)
    registrar_evento(
        db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="integration_token_revoked",
        entity_type="integration_token",
        entity_id=integracion.id,
        ip_address=_ip_del_cliente(request),
        details={"name": integracion.name},
    )
    db.commit()
