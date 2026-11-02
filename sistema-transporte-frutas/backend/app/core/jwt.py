from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_token_pair(subject: str) -> dict[str, str]:
    return {
        "access_token": create_token(
            subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
        ),
        "refresh_token": create_token(
            subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS)
        ),
        "token_type": "bearer",
    }


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token inválido o vencido") from exc
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise ValueError("Tipo de token inválido")
    return payload
