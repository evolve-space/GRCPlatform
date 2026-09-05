from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limitador_login
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token, UserRead

router = APIRouter()

# Protección contra fuerza bruta: 10 intentos por IP y por minuto. Es
# deliberadamente generoso (no una autenticación de dos factores) para no
# bloquear a un usuario legítimo que se equivoca un par de veces, pero basta
# para hacer inviable un ataque de fuerza bruta automatizado contra el login.
_LIMITE_INTENTOS_LOGIN = 10
_VENTANA_INTENTOS_LOGIN_SEGUNDOS = 60


def _limitar_intentos_de_login(request: Request) -> None:
    ip = request.client.host if request.client else "desconocida"
    if not limitador_login.permitir(
        f"login:{ip}", limite=_LIMITE_INTENTOS_LOGIN, ventana_segundos=_VENTANA_INTENTOS_LOGIN_SEGUNDOS
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesión. Inténtalo de nuevo en un minuto.",
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _limite: None = Depends(_limitar_intentos_de_login),
) -> Token:
    """Inicia sesión con email (como 'username') y contraseña, y devuelve un token JWT."""
    user = db.query(User).filter(User.email == form_data.username).first()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está desactivado.",
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
