"""
modules/secure_archive/core/archive_decryptor.py

Archive decryption engine.

Reverse counterpart of ArchiveEncryptor.
Uses AES-256-GCM authenticated decryption.
Authenticates before returning any decrypted data.

CRITICAL: This engine does exactly one thing.
It does NOT derive keys, restore files, or handle passwords.
"""

from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from modules.secure_archive.models.archive_payload import ArchivePayload
from modules.secure_archive.core.archive_encryptor import (
    KEY_LENGTH, NONCE_LENGTH, TAG_LENGTH
)
from vaultcore.logger import log_debug, log_error


class DecryptionError(Exception):
    """Base exception for decryption failures."""
    pass


class AuthenticationFailedError(DecryptionError):
    """
    Raised when authentication tag verification fails.

    Causes:
        - Wrong password (produces wrong key)
        - Tampered ciphertext
        - Modified nonce
        - Modified associated data
    """
    pass


class PayloadCorruptedError(DecryptionError):
    """Raised when decrypted bytes cannot be parsed as ArchivePayload."""
    pass


class ArchiveDecryptor:
    """
    Decrypts an encrypted ArchivePayload.

    Authentication happens first (AES-GCM tag verification).
    If authentication fails, NO plaintext is returned.

    Responsibilities:
        - AES-256-GCM authenticated decryption
        - ArchivePayload deserialization

    Non-responsibilities:
        - Derive keys from passwords
        - Read or write files
        - Restore archives
    """

    def decrypt(
        self,
        ciphertext: bytes,
        key: bytes,
        nonce: bytes,
        associated_data: Optional[bytes] = None
    ) -> ArchivePayload:
        """
        Decrypt encrypted archive payload.

        Args:
            ciphertext:      Encrypted bytes (must include GCM auth tag).
            key:             256-bit AES key.
            nonce:           Nonce used during encryption.
            associated_data: Optional AAD (must match encryption).

        Returns:
            The decrypted ArchivePayload.

        Raises:
            ValueError:                 If key or nonce length invalid.
            AuthenticationFailedError:  If tag verification fails.
            PayloadCorruptedError:      If decrypted bytes cannot be parsed.
        """
        # Validate key
        if len(key) != KEY_LENGTH:
            raise ValueError(
                f"Invalid key length: {len(key)} bytes "
                f"(expected {KEY_LENGTH} for AES-256)"
            )

        # Validate nonce
        if len(nonce) != NONCE_LENGTH:
            raise ValueError(
                f"Invalid nonce length: {len(nonce)} bytes "
                f"(expected {NONCE_LENGTH} for AES-GCM)"
            )

        # Validate minimum ciphertext length (must be at least tag length)
        if len(ciphertext) < TAG_LENGTH:
            raise AuthenticationFailedError(
                f"Ciphertext too short: {len(ciphertext)} bytes "
                f"(must be at least {TAG_LENGTH} for auth tag)"
            )

        log_debug(
            f"[ArchiveDecryptor] Authenticating and decrypting "
            f"{len(ciphertext):,} bytes"
        )

        # AES-GCM decrypt (authenticates first, decrypts if valid)
        try:
            aesgcm    = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
        except InvalidTag as error:
            log_error("[ArchiveDecryptor] Authentication failed")
            raise AuthenticationFailedError(
                "Authentication failed. Wrong password or corrupted archive."
            ) from error
        except Exception as error:
            log_error(f"[ArchiveDecryptor] Decryption error: {error}")
            raise DecryptionError(f"Decryption failed: {error}") from error

        log_debug(
            f"[ArchiveDecryptor] Decrypted to {len(plaintext):,} bytes"
        )

        # Deserialize into ArchivePayload
        try:
            payload = ArchivePayload.from_bytes(plaintext)
        except ValueError as error:
            log_error(f"[ArchiveDecryptor] Payload parse failed: {error}")
            raise PayloadCorruptedError(
                f"Decrypted payload is corrupted: {error}"
            ) from error

        log_debug(
            f"[ArchiveDecryptor] Recovered payload with "
            f"{payload.entry_count} entries"
        )

        return payload

    def decrypt_bytes(
        self,
        ciphertext: bytes,
        key: bytes,
        nonce: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Lower-level decrypt returning raw bytes (not deserialized).

        Args:
            ciphertext:      Encrypted bytes.
            key:             256-bit AES key.
            nonce:           Nonce used during encryption.
            associated_data: Optional AAD.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            AuthenticationFailedError: If tag verification fails.
        """
        if len(key) != KEY_LENGTH:
            raise ValueError(f"Invalid key length: {len(key)}")
        if len(nonce) != NONCE_LENGTH:
            raise ValueError(f"Invalid nonce length: {len(nonce)}")

        try:
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, associated_data)
        except InvalidTag as error:
            raise AuthenticationFailedError(
                "Authentication failed"
            ) from error
