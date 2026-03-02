"""
AES-256 encryption for sensitive data (Instagram session cookies).
Uses Fernet symmetric encryption from the cryptography library.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings


def _get_fernet() -> Fernet:
    """Get Fernet instance from configured encryption key."""
    if not settings.ENCRYPTION_KEY:
        # In development without a key, use a derived key from SECRET_KEY
        # WARNING: Do not use this in production - set ENCRYPTION_KEY explicitly
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(key_bytes)
    else:
        # Expect ENCRYPTION_KEY to be a 32-byte hex string
        key_bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
        key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext and return plaintext."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
