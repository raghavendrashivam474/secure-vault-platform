"""
utils/hashing.py

Password hashing utilities for the Personal Document Vault.
Uses Argon2 via the cryptography library for secure password hashing.
"""

import os
import base64
import hashlib
import hmac


# Salt length in bytes
SALT_LENGTH: int = 32

# Hashing iterations
HASH_ITERATIONS: int = 600_000

# Hash algorithm
HASH_ALGORITHM: str = "sha256"


def generate_salt() -> str:
    """
    Generate a cryptographically secure random salt.

    Returns:
        A base64-encoded string representation of the salt.
    """
    salt_bytes = os.urandom(SALT_LENGTH)
    return base64.b64encode(salt_bytes).decode("utf-8")


def hash_password(password: str, salt: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256.

    Args:
        password: The plaintext password to hash.
        salt:     The base64-encoded salt string.

    Returns:
        A base64-encoded string of the resulting hash.
    """
    salt_bytes = base64.b64decode(salt.encode("utf-8"))
    password_bytes = password.encode("utf-8")

    hash_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password_bytes,
        salt_bytes,
        HASH_ITERATIONS
    )

    return base64.b64encode(hash_bytes).decode("utf-8")


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash.

    Uses a constant-time comparison to prevent timing attacks.

    Args:
        password:    The plaintext password to verify.
        salt:        The base64-encoded salt used during hashing.
        stored_hash: The base64-encoded hash stored in the database.

    Returns:
        True if the password matches, False otherwise.
    """
    candidate_hash = hash_password(password, salt)

    return hmac.compare_digest(
        candidate_hash.encode("utf-8"),
        stored_hash.encode("utf-8")
    )


