from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationRead

router = APIRouter()


@router.get("/me", response_model=OrganizationRead)
def read_my_organization(current_user: User = Depends(get_current_user)) -> Organization:
    """Devuelve la organización del usuario autenticado (nunca se acepta un id por parámetro)."""
    return current_user.organization
