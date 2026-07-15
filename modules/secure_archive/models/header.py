"""
modules/secure_archive/models/header.py

Secure Vault Archive Header v1.

The header is the small public prefix of every .sva file.
It contains only the cryptographic parameters needed to
decrypt the archive. It does NOT contain secrets, keys,
manifest data, or compressed content.

Binary layout (fixed at 128 bytes for future extensibility):

    Offset  Size  Field
    ------  ----  -----
    0       4     Magic bytes ('SVA1')
    4       2     Format version (uint16 big-endian)
    6       2     Header size (uint16 big-endian)
    8       32    Module version (UTF-8, null-padded)
    40      16    Encryption algorithm (UTF-8, null-padded)
    56      16    KDF algorithm (UTF-8, null-padded)
    72      4     PBKDF2 iterations (uint32 big-endian)
    76      2     Salt length (uint16 big-endian)
    78      2     Nonce length (uint16 big-endian)
    80      8     Payload length (uint64 big-endian)
    88      40    Reserved (zero-padded)
    128     N     Salt bytes (Salt length)
    128+N   M     Nonce bytes (Nonce length)
"""

import struct
from dataclasses import dataclass, field
from typing import Optional


# Header format constants
MAGIC_BYTES         = b"SVA1"
HEADER_VERSION      = 1
HEADER_FIXED_SIZE   = 128    # Fixed portion before salt/nonce

# Default cryptographic parameters
DEFAULT_ENCRYPTION  = "AES-256-GCM"
DEFAULT_KDF         = "PBKDF2-HMAC-SHA256"
DEFAULT_ITERATIONS  = 600_000
DEFAULT_SALT_LENGTH = 32     # 256 bits
DEFAULT_NONCE_LENGTH = 12    # 96 bits (AES-GCM standard)


@dataclass
class SVAHeader:
    """
    Secure Vault Archive header.

    Attributes:
        magic:                Magic bytes ('SVA1').
        format_version:       Header format version.
        header_size:          Total header size in bytes (fixed + salt + nonce).
        module_version:       Secure Archive version.
        encryption_algorithm: Cipher name (e.g. 'AES-256-GCM').
        kdf_algorithm:        Key derivation function.
        kdf_iterations:       PBKDF2 iteration count.
        salt:                 Random salt for key derivation.
        nonce:                Random nonce for encryption.
        payload_length:       Length of encrypted payload following header.
    """
    magic:                bytes = MAGIC_BYTES
    format_version:       int   = HEADER_VERSION
    header_size:          int   = 0
    module_version:       str   = "0.2.0"
    encryption_algorithm: str   = DEFAULT_ENCRYPTION
    kdf_algorithm:        str   = DEFAULT_KDF
    kdf_iterations:       int   = DEFAULT_ITERATIONS
    salt:                 bytes = b""
    nonce:                bytes = b""
    payload_length:       int   = 0

    def __post_init__(self):
        # Calculate header size if not set
        if self.header_size == 0:
            self.header_size = HEADER_FIXED_SIZE + len(self.salt) + len(self.nonce)

    def to_bytes(self) -> bytes:
        """
        Serialize header to bytes.

        Returns:
            Header bytes (128 + salt + nonce total).
        """
        # Pad strings to fixed lengths
        module_ver = self.module_version.encode("utf-8")[:32].ljust(32, b"\x00")
        enc_algo   = self.encryption_algorithm.encode("utf-8")[:16].ljust(16, b"\x00")
        kdf_algo   = self.kdf_algorithm.encode("utf-8")[:16].ljust(16, b"\x00")

        # Build fixed portion
        header = struct.pack(
            ">4sHH32s16s16sIHHQ40s",
            self.magic,
            self.format_version,
            self.header_size,
            module_ver,
            enc_algo,
            kdf_algo,
            self.kdf_iterations,
            len(self.salt),
            len(self.nonce),
            self.payload_length,
            b"\x00" * 40           # Reserved
        )

        # Append variable-length salt and nonce
        return header + self.salt + self.nonce

    @classmethod
    def from_bytes(cls, data: bytes) -> "SVAHeader":
        """
        Deserialize header from bytes.

        Args:
            data: Bytes starting with the SVA header.

        Returns:
            An SVAHeader.

        Raises:
            ValueError: If magic bytes don't match, version unsupported, or truncated.
        """
        if len(data) < HEADER_FIXED_SIZE:
            raise ValueError(
                f"Data too small for header "
                f"(got {len(data)}, need {HEADER_FIXED_SIZE})"
            )

        # Unpack fixed portion
        (
            magic, format_version, header_size,
            module_ver, enc_algo, kdf_algo,
            iterations, salt_length, nonce_length,
            payload_length, reserved
        ) = struct.unpack(
            ">4sHH32s16s16sIHHQ40s",
            data[:HEADER_FIXED_SIZE]
        )

        # Validate magic
        if magic != MAGIC_BYTES:
            raise ValueError(
                f"Invalid magic bytes: expected {MAGIC_BYTES}, got {magic}"
            )

        # Validate version
        if format_version != HEADER_VERSION:
            raise ValueError(
                f"Unsupported header version: {format_version} "
                f"(expected {HEADER_VERSION})"
            )

        # Extract salt and nonce
        expected_total = HEADER_FIXED_SIZE + salt_length + nonce_length
        if len(data) < expected_total:
            raise ValueError(
                f"Header truncated: expected {expected_total} bytes, "
                f"got {len(data)}"
            )

        salt  = data[HEADER_FIXED_SIZE:HEADER_FIXED_SIZE + salt_length]
        nonce = data[HEADER_FIXED_SIZE + salt_length:HEADER_FIXED_SIZE + salt_length + nonce_length]

        # Decode strings (strip null padding)
        module_version = module_ver.rstrip(b"\x00").decode("utf-8")
        enc_algorithm  = enc_algo.rstrip(b"\x00").decode("utf-8")
        kdf_algorithm  = kdf_algo.rstrip(b"\x00").decode("utf-8")

        return cls(
            magic                = magic,
            format_version       = format_version,
            header_size          = header_size,
            module_version       = module_version,
            encryption_algorithm = enc_algorithm,
            kdf_algorithm        = kdf_algorithm,
            kdf_iterations       = iterations,
            salt                 = salt,
            nonce                = nonce,
            payload_length       = payload_length,
        )
