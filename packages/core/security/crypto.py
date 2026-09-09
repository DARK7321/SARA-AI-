"""Cryptographic utilities for encrypting sensitive credentials and tokens at rest."""
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet

from apps.api.settings import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    # Deterministically derive a 32-byte URL-safe base64 key from JWT_SECRET_KEY
    key_digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_digest)
    return Fernet(fernet_key)


def encrypt_token(plain_token: str) -> str:
    """Encrypt a plain token string into ciphertext."""
    if not plain_token:
        return ""
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plain_token.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt ciphertext back into plain token string."""
    if not encrypted_token:
        return ""
    fernet = _get_fernet()
    decrypted_bytes = fernet.decrypt(encrypted_token.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")

