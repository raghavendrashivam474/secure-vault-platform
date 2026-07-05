"""
core/encryption.py

File encryption and decryption for the Personal Document Vault.
Uses AES-256-GCM via the cryptography library.

Security design:
    - AES-256-GCM provides both encryption and authentication.
    - A unique 256-bit key is derived from the master password
      using PBKDF2-HMAC-SHA256.
    - A unique 96-bit nonce is generated for every encryption operation.
    - The nonce and salt are stored alongside the ciphertext.
    - No plaintext data is ever written to disk.

Encrypted file format:
    [ salt (32 bytes) ][ nonce (12 bytes) ][ tag (16 bytes) ][ ciphertext ]
"""

import os
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Key derivation constants
SALT_LENGTH:       int = 32
NONCE_LENGTH:      int = 12
KEY_LENGTH:        int = 32
KDF_ITERATIONS:    int = 600_000
KDF_ALGORITHM:     str = "sha256"


def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit AES key from a password and salt.

    Uses PBKDF2-HMAC-SHA256 for key derivation.

    Args:
        password: The master password string.
        salt:     A cryptographically random salt.

    Returns:
        A 32-byte derived key suitable for AES-256.
    """
    return hashlib.pbkdf2_hmac(
        KDF_ALGORITHM,
        password.encode("utf-8"),
        salt,
        KDF_ITERATIONS,
        dklen=KEY_LENGTH
    )


def encrypt_file(
    source_path: Path,
    destination_path: Path,
    password: str
) -> bool:
    """
    Encrypt a file using AES-256-GCM and write it to the destination.

    The encrypted output format is:
        salt (32 bytes) + nonce (12 bytes) + tag (16 bytes) + ciphertext

    The source file is read entirely into memory.
    No temporary files are created.

    Args:
        source_path:      Path to the plaintext file to encrypt.
        destination_path: Path where the encrypted file will be written.
        password:         The master password used for key derivation.

    Returns:
        True if encryption succeeded.
        False if an error occurred.
    """
    try:
        salt  = os.urandom(SALT_LENGTH)
        nonce = os.urandom(NONCE_LENGTH)
        key   = _derive_key(password, salt)

        plaintext  = source_path.read_bytes()
        aesgcm     = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # ciphertext from AESGCM includes the 16-byte tag appended
        destination_path.write_bytes(salt + nonce + ciphertext)
        return True

    except Exception as error:
        print(f"[Encryption] Failed to encrypt {source_path.name}: {error}")
        return False


def decrypt_file_to_memory(
    encrypted_path: Path,
    password: str
) -> bytes | None:
    """
    Decrypt an encrypted file entirely in memory.

    The decrypted data is returned as bytes.
    Nothing is written to disk.

    Args:
        encrypted_path: Path to the encrypted .enc file.
        password:       The master password used for key derivation.

    Returns:
        The decrypted file contents as bytes, or None if decryption fails.
    """
    try:
        raw   = encrypted_path.read_bytes()
        salt  = raw[:SALT_LENGTH]
        nonce = raw[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
        ciphertext_with_tag = raw[SALT_LENGTH + NONCE_LENGTH:]

        key    = _derive_key(password, salt)
        aesgcm = AESGCM(key)

        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext

    except Exception as error:
        print(f"[Encryption] Failed to decrypt {encrypted_path.name}: {error}")
        return None


