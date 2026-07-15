"""
modules/secure_archive/core/sva_reader.py

Secure Vault Archive Reader.

Reverse counterpart of SVAWriter.
Parses .sva files and extracts header + encrypted payload.

CRITICAL: Does NOT decrypt. Does NOT ask for passwords.
It only understands the .sva file structure.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from modules.secure_archive.core.sva_header import SVAHeaderReader
from modules.secure_archive.models.header import SVAHeader, HEADER_FIXED_SIZE
from vaultcore.logger import log_debug, log_error


@dataclass
class SVAPackage:
    """
    Represents an opened but not yet decrypted .sva file.

    Attributes:
        file_path:         Path to the .sva file.
        file_size:         Total file size in bytes.
        header:            Parsed SVAHeader.
        encrypted_payload: Raw ciphertext bytes (still encrypted).
    """
    file_path:         str
    file_size:         int
    header:            SVAHeader
    encrypted_payload: bytes


class SVAReaderError(Exception):
    """Base exception for SVA reader errors."""
    pass


class InvalidSVAFileError(SVAReaderError):
    """Raised when the file is not a valid SVA archive."""
    pass


class UnsupportedSVAVersionError(SVAReaderError):
    """Raised when the SVA format version is not supported."""
    pass


class CorruptedSVAFileError(SVAReaderError):
    """Raised when the SVA file appears corrupted or truncated."""
    pass


class SVAReader:
    """
    Reads .sva files.

    Extracts the header and encrypted payload without decrypting.
    Validates file structure but not cryptographic authenticity.
    """

    def __init__(self) -> None:
        self._header_reader = SVAHeaderReader()

    def read(self, file_path: Path) -> SVAPackage:
        """
        Open and parse a .sva file.

        Args:
            file_path: Path to the .sva file.

        Returns:
            An SVAPackage with header and encrypted payload.

        Raises:
            FileNotFoundError:            If file does not exist.
            InvalidSVAFileError:          If magic bytes don't match.
            UnsupportedSVAVersionError:   If format version not supported.
            CorruptedSVAFileError:        If file is truncated or malformed.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"SVA file not found: {file_path}")

        log_debug(f"[SVAReader] Reading {file_path.name}")

        try:
            with open(file_path, "rb") as f:
                # Read full file
                file_bytes = f.read()
        except OSError as error:
            raise CorruptedSVAFileError(f"Cannot read file: {error}") from error

        file_size = len(file_bytes)

        # Validate minimum size for fixed header portion
        if file_size < HEADER_FIXED_SIZE:
            raise CorruptedSVAFileError(
                f"File too small to be a valid archive "
                f"({file_size} bytes, need at least {HEADER_FIXED_SIZE})"
            )

        # Peek header size without full deserialization
        try:
            header_size = self._header_reader.peek_size(
                file_bytes[:HEADER_FIXED_SIZE]
            )
        except ValueError as error:
            error_msg = str(error).lower()
            if "magic" in error_msg:
                raise InvalidSVAFileError(
                    f"Not a Secure Vault Archive: {error}"
                ) from error
            raise CorruptedSVAFileError(str(error)) from error

        # Validate we have enough bytes for full header
        if file_size < header_size:
            raise CorruptedSVAFileError(
                f"File truncated at header "
                f"(need {header_size}, got {file_size})"
            )

        # Parse full header
        try:
            header = self._header_reader.read(file_bytes[:header_size])
        except ValueError as error:
            error_msg = str(error).lower()
            if "version" in error_msg:
                raise UnsupportedSVAVersionError(str(error)) from error
            if "magic" in error_msg:
                raise InvalidSVAFileError(str(error)) from error
            raise CorruptedSVAFileError(str(error)) from error

        # Validate payload length
        expected_total = header_size + header.payload_length
        if file_size < expected_total:
            raise CorruptedSVAFileError(
                f"File truncated at payload "
                f"(need {expected_total}, got {file_size})"
            )

        # Extract encrypted payload
        encrypted_payload = file_bytes[header_size:header_size + header.payload_length]

        log_debug(
            f"[SVAReader] Parsed .sva: "
            f"{header_size} header + {len(encrypted_payload):,} payload bytes"
        )

        return SVAPackage(
            file_path         = str(file_path),
            file_size         = file_size,
            header            = header,
            encrypted_payload = encrypted_payload,
        )

    def peek_metadata(self, file_path: Path) -> Optional[SVAHeader]:
        """
        Read only the header of a .sva file without loading payload.

        Useful for showing archive info before password entry.

        Args:
            file_path: Path to the .sva file.

        Returns:
            The SVAHeader, or None if unreadable.
        """
        try:
            with open(file_path, "rb") as f:
                fixed_bytes = f.read(HEADER_FIXED_SIZE)
                if len(fixed_bytes) < HEADER_FIXED_SIZE:
                    return None

                header_size = self._header_reader.peek_size(fixed_bytes)

                f.seek(0)
                full_header_bytes = f.read(header_size)
                if len(full_header_bytes) < header_size:
                    return None

                return self._header_reader.read(full_header_bytes)
        except Exception as error:
            log_error(f"[SVAReader] Failed to peek {file_path}: {error}")
            return None
