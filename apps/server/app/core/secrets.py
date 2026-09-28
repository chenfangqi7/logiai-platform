import base64
import hashlib
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import get_settings

PREFIX = "enc:v1:"
MASK = "********"


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.connector_secret_key
    if not key:
        if settings.app_env != "development":
            raise ValueError("CONNECTOR_SECRET_KEY must be configured")
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest()).decode()
    return Fernet(key.encode())


def is_secret_name(name: str) -> bool:
    normalized = "".join(character for character in name.lower() if character.isalnum())
    return any(part in normalized for part in ("password", "secret", "token", "apikey", "authorization", "headervalue", "credential", "auth"))


def encrypt_config(value: Any, name: str = "", force_secret: bool = False) -> Any:
    if isinstance(value, dict):
        return {key: encrypt_config(item, str(key), force_secret or name == "headers") for key, item in value.items()}
    if isinstance(value, list):
        return [encrypt_config(item, name, force_secret) for item in value]
    if (force_secret or is_secret_name(name)) and value not in (None, ""):
        text = str(value)
        return text if text.startswith(PREFIX) else PREFIX + _fernet().encrypt(text.encode()).decode()
    return value


def decrypt_config(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: decrypt_config(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decrypt_config(item) for item in value]
    if isinstance(value, str) and value.startswith(PREFIX):
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    return value


def redact_config(value: Any, name: str = "", force_secret: bool = False) -> Any:
    if isinstance(value, dict):
        return {key: redact_config(item, str(key), force_secret or name == "headers") for key, item in value.items()}
    if isinstance(value, list):
        return [redact_config(item, name, force_secret) for item in value]
    if (force_secret or is_secret_name(name)) and value not in (None, ""):
        return MASK
    return value


def contains_secret(value: Any, name: str = "", force_secret: bool = False) -> bool:
    if isinstance(value, dict):
        return any(contains_secret(item, str(key), force_secret or name == "headers") for key, item in value.items())
    if isinstance(value, list):
        return any(contains_secret(item, name, force_secret) for item in value)
    return (force_secret or is_secret_name(name)) and value not in (None, "")


def merge_config(existing: dict, incoming: dict, force_secret: bool = False) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value == MASK and (force_secret or is_secret_name(str(key))):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_config(merged[key], value, force_secret or key == "headers")
        else:
            merged[key] = value
    return merged
