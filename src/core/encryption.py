"""
Fernet encryption for sensitive data storage.

Provides encryption/decryption for OAuth tokens and other secrets stored in
the database. Uses Fernet symmetric encryption (AES-128-CBC with HMAC).

Key Management:
- Reads from Docker secret file (/run/secrets/ENCRYPTION_KEY)
- Falls back to environment variable (ENCRYPTION_KEY)
- Key must be 32 URL-safe base64-encoded bytes (use generate_encryption_key())

Usage:
    from src.core.encryption import encrypt_token, decrypt_token

    # Encrypt before storing in database
    encrypted = encrypt_token("shpat_12345_access_token")
    credential.access_token = encrypted  # LargeBinary column

    # Decrypt when reading from database
    plaintext = decrypt_token(credential.access_token)
    # Use plaintext for API calls
"""
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from src.core.secrets import get_secret

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from Docker secret or environment variable.

    Returns:
        32-byte Fernet key (URL-safe base64-encoded)

    Raises:
        ValueError: If ENCRYPTION_KEY is not set or invalid
    """
    key_str = get_secret('ENCRYPTION_KEY')

    if not key_str:
        raise ValueError(
            "ENCRYPTION_KEY not found. Generate one with:\n"
            "  python -c 'from src.core.encryption import generate_encryption_key; "
            "print(generate_encryption_key())'\n"
            "Then set it in .env or Docker secrets."
        )

    try:
        # Fernet keys are URL-safe base64-encoded 32 bytes
        # Validate by attempting to create Fernet instance
        key_bytes = key_str.encode('utf-8')
        Fernet(key_bytes)  # Will raise if invalid
        return key_bytes
    except Exception as e:
        raise ValueError(
            f"Invalid ENCRYPTION_KEY format: {e}\n"
            "Generate a valid key with:\n"
            "  python -c 'from src.core.encryption import generate_encryption_key; "
            "print(generate_encryption_key())'"
        )


def encrypt_token(plaintext: str) -> bytes:
    """
    Encrypt a string token for storage in LargeBinary column.

    Args:
        plaintext: OAuth token or other secret (string)

    Returns:
        Encrypted bytes for database storage

    Raises:
        ValueError: If encryption key is not configured
    """
    if not plaintext:
        return b''

    key = get_encryption_key()
    fernet = Fernet(key)

    plaintext_bytes = plaintext.encode('utf-8')
    encrypted = fernet.encrypt(plaintext_bytes)

    logger.debug(f"Encrypted token ({len(plaintext)} chars -> {len(encrypted)} bytes)")
    return encrypted


def decrypt_token(ciphertext: bytes) -> Optional[str]:
    """
    Decrypt a token from database storage.

    Args:
        ciphertext: Encrypted bytes from LargeBinary column

    Returns:
        Decrypted string, or None if decryption fails

    Note:
        Returns None on failure rather than raising exception.
        This allows graceful handling of corrupted/expired tokens.
    """
    if not ciphertext:
        return None

    try:
        key = get_encryption_key()
        fernet = Fernet(key)

        decrypted_bytes = fernet.decrypt(ciphertext)
        plaintext = decrypted_bytes.decode('utf-8')

        logger.debug(f"Decrypted token ({len(ciphertext)} bytes -> {len(plaintext)} chars)")
        return plaintext

    except (InvalidToken, ValueError) as e:
        logger.error(f"Failed to decrypt token: {e}")
        return None


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        URL-safe base64-encoded 32-byte key

    Usage:
        key = generate_encryption_key()
        # Add to .env or Docker secrets:
        # ENCRYPTION_KEY=<key>
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


# Example usage in models:
#
# class ShopifyCredential(db.Model):
#     access_token = db.Column(db.LargeBinary, nullable=False)
#
#     def set_access_token(self, token: str):
#         from src.core.encryption import encrypt_token
#         self.access_token = encrypt_token(token)
#
#     def get_access_token(self) -> str:
#         from src.core.encryption import decrypt_token
#         return decrypt_token(self.access_token)
