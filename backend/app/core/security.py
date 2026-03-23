import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str | dict[str, Any],
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    if isinstance(subject, str):
        to_encode = {"sub": subject, "exp": expire}
    else:
        to_encode = {**subject, "exp": expire}

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None:
    payload = decode_token(token)
    if payload is None:
        return None

    if token_type == "refresh" and payload.get("type") != "refresh":
        return None

    return payload


def get_token_subject(token: str) -> str | None:
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("sub")


def _get_fernet_key() -> bytes:
    key = settings.SECRET_KEY[:32].encode()
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_token(encrypted_token: str) -> str:
    fernet = Fernet(_get_fernet_key())
    encrypted = base64.urlsafe_b64decode(encrypted_token.encode())
    decrypted = fernet.decrypt(encrypted)
    return decrypted.decode()


def encrypt_dict(data: dict[str, Any]) -> str:
    import json

    json_str = json.dumps(data)
    return encrypt_token(json_str)


def decrypt_dict(encrypted_data: str) -> dict[str, Any]:
    import json

    json_str = decrypt_token(encrypted_data)
    return json.loads(json_str)
