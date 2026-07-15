"""
modules/secure_archive/core/sva_writer.py

Secure Vault Archive Writer.

Assembles the final .sva file from:
    - Header (fixed + salt + nonce)
    - Encrypted payload (ciphertext + auth tag from AES-GCM)

File structure:
    [Header bytes] [Ciphertext + Auth Tag]

The SVA Writer orchestrates the full creation pipeline:
    Payload → KDF → Header → Encrypt → Write file
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from modules.secure_archive.models.archive_payload import ArchivePayload
from modules.secure_archive.core.sva_header import SVAHeaderBuilder
from modules.secure_archive.core.key_derivation import KeyDerivationService
from modules.secure_archive.core.archive_encryptor import ArchiveEncryptor
from vaultcore.logger import log_debug, log_event, log_error


# File extension for encrypted archives
SVA_EXTENSION = ".sva"


@dataclass
class SVAWriteResult:
    """
    Result of writing an SVA file.

    Attributes:
        file_path:       Path to the written .sva file.
        file_size:       Total file size in bytes.
        header_size:     Size of header portion.
        payload_size:    Size of encrypted payload portion.
        original_size:   Size of unencrypted payload.
    """
    file_path:     str
    file_size:     int
    header_size:   int
    payload_size:  int
    original_size: int


class SVAWriter:
    """
    Writes .sva files.

    Orchestrates the encryption pipeline:
        1. Generate salt (KDF service)
        2. Derive key from password (KDF service)
        3. Encrypt payload (Encryptor)
        4. Build header (Header builder)
        5. Write file (this writer)

    Does NOT:
        - Compress files
        - Read source files
        - Build the payload itself
    """

    def __init__(
        self,
        key_derivation: Optional[KeyDerivationService] = None,
        encryptor: Optional[ArchiveEncryptor]          = None,
        header_builder: Optional[SVAHeaderBuilder]     = None
    ) -> None:
        """
        Initialize with injectable services.

        Args:
            key_derivation: KDF service. Default one created if None.
            encryptor:      Encryption engine. Default if None.
            header_builder: Header builder. Default if None.
        """
        self._kdf      = key_derivation or KeyDerivationService()
        self._enc      = encryptor      or ArchiveEncryptor()
        self._hdr      = header_builder or SVAHeaderBuilder()

    def write(
        self,
        payload: ArchivePayload,
        password: str,
        output_path: Path,
        module_version: str = "0.2.0"
    ) -> SVAWriteResult:
        """
        Write an encrypted .sva file.

        Args:
            payload:        The ArchivePayload to encrypt and write.
            password:       User password for key derivation.
            output_path:    Where to write the .sva file.
            module_version: Secure Archive version.

        Returns:
            SVAWriteResult with file statistics.

        Raises:
            ValueError: If password is empty.
            OSError:    If file cannot be written.
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        log_debug(f"[SVAWriter] Creating .sva file: {output_path.name}")

        # Step 1: Generate salt
        salt = self._kdf.generate_salt()
        log_debug(f"[SVAWriter] Generated {len(salt)}-byte salt")

        # Step 2: Derive key
        key = self._kdf.derive_key(password, salt)
        log_debug(f"[SVAWriter] Derived {len(key)*8}-bit AES key")

        # Step 3: Encrypt payload (fresh nonce generated internally)
        encrypted = self._enc.encrypt(payload, key)
        log_debug(
            f"[SVAWriter] Encrypted payload: "
            f"{encrypted.original_size:,} → {encrypted.encrypted_size:,} bytes"
        )

        # Step 4: Build header
        header = self._hdr.build(
            module_version = module_version,
            payload_length = encrypted.encrypted_size,
            salt           = salt,
            nonce          = encrypted.nonce
        )

        # Step 5: Serialize header
        header_bytes = header.to_bytes()

        # Step 6: Write file (header + ciphertext)
        try:
            with open(output_path, "wb") as f:
                f.write(header_bytes)
                f.write(encrypted.ciphertext)
        except OSError as error:
            log_error(f"[SVAWriter] Failed to write {output_path}: {error}")
            # Clean up partial file
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise

        file_size = output_path.stat().st_size

        log_event(
            "SVAFileCreated",
            f"{output_path.name}: {file_size:,} bytes"
        )

        return SVAWriteResult(
            file_path     = str(output_path),
            file_size     = file_size,
            header_size   = len(header_bytes),
            payload_size  = encrypted.encrypted_size,
            original_size = encrypted.original_size
        )
