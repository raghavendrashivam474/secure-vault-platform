"""
modules/secure_archive/core/sva_header.py

Header builder and reader for .sva files.

Handles fresh salt/nonce generation and header extraction.
"""

import os
from typing import Optional

from modules.secure_archive.models.header import (
    SVAHeader, MAGIC_BYTES, HEADER_VERSION, HEADER_FIXED_SIZE,
    DEFAULT_ENCRYPTION, DEFAULT_KDF, DEFAULT_ITERATIONS,
    DEFAULT_SALT_LENGTH, DEFAULT_NONCE_LENGTH
)


class SVAHeaderBuilder:
    """
    Builds new .sva headers with fresh cryptographic parameters.
    """

    def build(
        self,
        module_version: str = "0.2.0",
        payload_length: int = 0,
        salt: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
    ) -> SVAHeader:
        """
        Build a fresh SVA header.

        Args:
            module_version:  Secure Archive version.
            payload_length:  Length of encrypted payload (0 if not yet known).
            salt:            Optional salt bytes. Fresh if not provided.
            nonce:           Optional nonce bytes. Fresh if not provided.

        Returns:
            A new SVAHeader with fresh crypto parameters.
        """
        if salt is None:
            salt = os.urandom(DEFAULT_SALT_LENGTH)

        if nonce is None:
            nonce = os.urandom(DEFAULT_NONCE_LENGTH)

        return SVAHeader(
            magic                = MAGIC_BYTES,
            format_version       = HEADER_VERSION,
            header_size          = HEADER_FIXED_SIZE + len(salt) + len(nonce),
            module_version       = module_version,
            encryption_algorithm = DEFAULT_ENCRYPTION,
            kdf_algorithm        = DEFAULT_KDF,
            kdf_iterations       = DEFAULT_ITERATIONS,
            salt                 = salt,
            nonce                = nonce,
            payload_length       = payload_length,
        )


class SVAHeaderReader:
    """
    Reads and validates SVA headers from byte data or file streams.
    """

    def read(self, data: bytes) -> SVAHeader:
        """
        Read a header from bytes.

        Args:
            data: Bytes starting with the SVA header.

        Returns:
            The parsed SVAHeader.
        """
        return SVAHeader.from_bytes(data)

    def peek_size(self, first_bytes: bytes) -> int:
        """
        Peek at first bytes to determine total header size.

        Only reads the fixed portion to extract the header_size field.
        Does not require the full salt/nonce data.

        Args:
            first_bytes: At least HEADER_FIXED_SIZE bytes from file start.

        Returns:
            Total header size in bytes (fixed + salt + nonce).
        """
        import struct
        if len(first_bytes) < HEADER_FIXED_SIZE:
            raise ValueError(f"Need at least {HEADER_FIXED_SIZE} bytes to peek")

        # Read magic to verify this looks like an SVA file
        magic = first_bytes[:4]
        if magic != MAGIC_BYTES:
            raise ValueError(f"Invalid magic bytes: {magic}")

        # Header size is at offset 6 (uint16 big-endian)
        header_size = struct.unpack(">H", first_bytes[6:8])[0]
        return header_size

