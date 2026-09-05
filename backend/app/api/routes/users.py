import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    """Crea un usuario dentro de la organización del administrador autenticado.

    La organización nunca se toma del cuerpo de la petición: siempre es la del
    usuario que realiza la llamada, para garantizar el aislamiento entre organizaciones.
    """
    ya_existe = db.query(User).filter(User.email == payload.email).first()
    if ya_existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo electrónico.",
        )

    nuevo_usuario = User(
        organization_id=current_user.organization_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[User]:
    """Lista los usuarios de la organización del administrador autenticado."""
    return (
        db.query(User)
        .filter(User.organization_id == current_user.organization_id)
        .order_by(User.created_at)
        .all()
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    """Obtiene un usuario por id, siempre restringido a la propia organización.

    Si el usuario existe pero pertenece a otra organización, se responde 404
    (no 403) para no revelar la existencia de datos de otras organizaciones.
    """
    usuario = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == current_user.organization_id)
        .first()
    )
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return usuario
