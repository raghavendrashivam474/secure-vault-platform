"""
modules/secure_archive/core/key_derivation.py

Key derivation service for Secure Archive.

Converts user-supplied passwords into cryptographic keys
using PBKDF2-HMAC-SHA256.

CRITICAL: This service does exactly one thing.
It does NOT encrypt, decrypt, or handle files.
"""

import os
import hashlib
from typing import Optional

from vaultcore.logger import log_debug


# Default cryptographic parameters
DEFAULT_ITERATIONS  = 600_000        # OWASP 2023 recommendation for PBKDF2-SHA256
DEFAULT_KEY_LENGTH  = 32             # 256 bits (AES-256)
DEFAULT_SALT_LENGTH = 32             # 256 bits


class KeyDerivationService:
    """
    Derives cryptographic keys from passwords.

    Uses PBKDF2-HMAC-SHA256 with configurable iterations.

    Responsibilities:
        - Generate cryptographically secure salts
        - Derive 256-bit AES keys from password + salt

    Non-responsibilities:
        - Encrypt or decrypt anything
        - Read or write files
        - Persist keys or salts
    """

    def __init__(
        self,
        iterations: int = DEFAULT_ITERATIONS,
        key_length: int = DEFAULT_KEY_LENGTH
    ) -> None:
        """
        Initialize with configurable parameters.

        Args:
            iterations: PBKDF2 iteration count.
            key_length: Derived key length in bytes.
        """
        if iterations < 100_000:
            raise ValueError(
                f"Iterations too low: {iterations} "
                f"(minimum recommended: 100,000)"
            )
        if key_length not in (16, 24, 32):
            raise ValueError(
                f"Invalid key length: {key_length} "
                f"(must be 16, 24, or 32 bytes)"
            )

        self._iterations = iterations
        self._key_length = key_length

    @property
    def iterations(self) -> int:
        """Return configured iteration count."""
        return self._iterations

    @property
    def key_length(self) -> int:
        """Return configured key length in bytes."""
        return self._key_length

    def generate_salt(self, length: int = DEFAULT_SALT_LENGTH) -> bytes:
        """
        Generate a cryptographically secure random salt.

        Args:
            length: Salt length in bytes.

        Returns:
            Random salt bytes.
        """
        if length < 16:
            raise ValueError(f"Salt too short: {length} (minimum: 16 bytes)")

        return os.urandom(length)

    def derive_key(
        self,
        password: str,
        salt: bytes,
        iterations: Optional[int] = None,
        key_length: Optional[int] = None
    ) -> bytes:
        """
        Derive a key from password and salt.

        Args:
            password:   User-supplied password.
            salt:       Cryptographic salt.
            iterations: Optional override for iteration count.
            key_length: Optional override for key length.

        Returns:
            Derived key bytes.

        Raises:
            ValueError: If password is empty or salt is too short.
        """
        if not password:
            raise ValueError("Password cannot be empty")
        if not salt or len(salt) < 16:
            raise ValueError(f"Salt too short: {len(salt) if salt else 0}")

        iters   = iterations if iterations is not None else self._iterations
        keylen  = key_length if key_length is not None else self._key_length

        log_debug(
            f"[KeyDerivation] Deriving {keylen*8}-bit key "
            f"({iters:,} iterations)"
        )

        derived = hashlib.pbkdf2_hmac(
            hash_name    = "sha256",
            password     = password.encode("utf-8"),
            salt         = salt,
            iterations   = iters,
            dklen        = keylen
        )

        return derived

    def verify_password(
        self,
        password: str,
        salt: bytes,
        expected_key: bytes,
        iterations: Optional[int] = None
    ) -> bool:
        """
        Verify a password by deriving and comparing keys.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            password:     Password to verify.
            salt:         Salt used originally.
            expected_key: Previously derived key to compare.
            iterations:   Iteration count used originally.

        Returns:
            True if password matches.
        """
        import hmac

        try:
            derived = self.derive_key(password, salt, iterations)
            return hmac.compare_digest(derived, expected_key)
        except Exception:
            return False
