"""
modules/secure_archive/core/archive_encryptor.py

Archive encryption engine.

Wraps AES-256-GCM authenticated encryption.
Consumes ArchivePayload and an AES key.
Produces encrypted bytes with authentication tag.

CRITICAL: This engine does exactly one thing.
It does NOT derive keys, read files, or handle passwords.
"""

import os
from dataclasses import dataclass
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from modules.secure_archive.models.archive_payload import ArchivePayload
from vaultcore.logger import log_debug, log_error


# Cryptographic constants
NONCE_LENGTH = 12                # 96 bits - AES-GCM standard
KEY_LENGTH   = 32                # 256 bits - AES-256
TAG_LENGTH   = 16                # 128 bits - GCM auth tag


@dataclass
class EncryptedPayload:
    """
    Result of encrypting an ArchivePayload.

    Attributes:
        ciphertext:    Encrypted bytes (includes appended auth tag from AESGCM).
        nonce:         Nonce used for encryption.
        original_size: Size of plaintext payload before encryption.
    """
    ciphertext:    bytes
    nonce:         bytes
    original_size: int

    @property
    def encrypted_size(self) -> int:
        """Total size of encrypted ciphertext (includes auth tag)."""
        return len(self.ciphertext)


class ArchiveEncryptor:
    """
    Encrypts an ArchivePayload using AES-256-GCM.

    Responsibilities:
        - Generate cryptographic nonces
        - Encrypt payload bytes with authenticated encryption

    Non-responsibilities:
        - Derive keys from passwords
        - Read or write files
        - Build headers or archives
    """

    def encrypt(
        self,
        payload: ArchivePayload,
        key: bytes,
        nonce: Optional[bytes] = None,
        associated_data: Optional[bytes] = None
    ) -> EncryptedPayload:
        """
        Encrypt an ArchivePayload.

        Args:
            payload:         The ArchivePayload to encrypt.
            key:             256-bit AES key (32 bytes).
            nonce:           Optional nonce. Fresh if not provided.
            associated_data: Optional additional authenticated data (AAD).
                             Not encrypted but authenticated.

        Returns:
            An EncryptedPayload containing ciphertext and nonce.

        Raises:
            ValueError: If key length is invalid.
        """
        # Validate key
        if len(key) != KEY_LENGTH:
            raise ValueError(
                f"Invalid key length: {len(key)} bytes "
                f"(expected {KEY_LENGTH} for AES-256)"
            )

        # Generate fresh nonce if not provided
        if nonce is None:
            nonce = os.urandom(NONCE_LENGTH)

        if len(nonce) != NONCE_LENGTH:
            raise ValueError(
                f"Invalid nonce length: {len(nonce)} bytes "
                f"(expected {NONCE_LENGTH} for AES-GCM)"
            )

        # Serialize payload
        plaintext = payload.to_bytes()
        original_size = len(plaintext)

        log_debug(
            f"[ArchiveEncryptor] Encrypting {original_size:,} bytes "
            f"with AES-256-GCM"
        )

        # Encrypt with AES-GCM (tag is appended to ciphertext automatically)
        try:
            aesgcm     = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        except Exception as error:
            log_error(f"[ArchiveEncryptor] Encryption failed: {error}")
            raise

        log_debug(
            f"[ArchiveEncryptor] Encrypted to {len(ciphertext):,} bytes "
            f"(overhead: {len(ciphertext) - original_size} bytes)"
        )

        return EncryptedPayload(
            ciphertext    = ciphertext,
            nonce         = nonce,
            original_size = original_size
        )

    def encrypt_bytes(
        self,
        plaintext: bytes,
        key: bytes,
        nonce: Optional[bytes] = None,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Encrypt raw bytes directly.

        Lower-level helper used by encrypt() and future streaming variants.

        Args:
            plaintext:       Bytes to encrypt.
            key:             256-bit AES key.
            nonce:           Optional nonce. Fresh if not provided.
            associated_data: Optional AAD.

        Returns:
            Ciphertext with appended authentication tag.
        """
        if len(key) != KEY_LENGTH:
            raise ValueError(f"Invalid key length: {len(key)}")

        if nonce is None:
            nonce = os.urandom(NONCE_LENGTH)

        aesgcm = AESGCM(key)
        return aesgcm.encrypt(nonce, plaintext, associated_data)
