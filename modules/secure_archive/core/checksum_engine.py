"""
modules/secure_archive/core/checksum_engine.py

Streaming SHA-256 checksum engine.

Reads files in fixed-size chunks. Never loads entire
large files into memory. Same engine is used during
archive creation and restoration verification.
"""

import hashlib
from pathlib import Path
from typing import Optional, Callable

from vaultcore.logger import log_error


# Chunk size for streaming reads
CHUNK_SIZE = 64 * 1024   # 64 KB


class ChecksumEngine:
    """
    Streaming SHA-256 checksum generator.

    Uses hashlib.sha256() with chunked reads for memory efficiency.
    """

    def compute(
        self,
        file_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[str]:
        """
        Compute SHA-256 checksum for a file.

        Args:
            file_path:         Path to file.
            progress_callback: Optional callback(bytes_read, total_size).

        Returns:
            Hex-encoded SHA-256 digest, or None on error.
        """
        try:
            hasher = hashlib.sha256()
            total_size = file_path.stat().st_size
            bytes_read = 0

            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    bytes_read += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_read, total_size)

            return hasher.hexdigest()

        except (OSError, PermissionError) as error:
            log_error(f"[ChecksumEngine] Failed to read {file_path}: {error}")
            return None

    def compute_bytes(self, data: bytes) -> str:
        """
        Compute SHA-256 for a bytes object (used during restoration).

        Args:
            data: Raw bytes.

        Returns:
            Hex-encoded SHA-256 digest.
        """
        return hashlib.sha256(data).hexdigest()

    def compute_stream(
        self,
        file_path: Path,
        max_bytes: Optional[int] = None
    ) -> tuple[Optional[str], int]:
        """
        Compute checksum and return total bytes read.

        Useful when checksum + size are needed together.

        Args:
            file_path: Path to file.
            max_bytes: Optional limit on bytes to read.

        Returns:
            Tuple of (checksum, bytes_read).
        """
        try:
            hasher     = hashlib.sha256()
            bytes_read = 0

            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    if max_bytes and bytes_read + len(chunk) > max_bytes:
                        chunk = chunk[:max_bytes - bytes_read]
                    hasher.update(chunk)
                    bytes_read += len(chunk)
                    if max_bytes and bytes_read >= max_bytes:
                        break

            return hasher.hexdigest(), bytes_read

        except (OSError, PermissionError) as error:
            log_error(f"[ChecksumEngine] Stream failed: {error}")
            return None, 0

    def verify(
        self,
        file_path: Path,
        expected_checksum: str
    ) -> bool:
        """
        Verify a file matches an expected checksum.

        Args:
            file_path:         Path to file.
            expected_checksum: Hex-encoded expected SHA-256.

        Returns:
            True if checksums match, False otherwise.
        """
        actual = self.compute(file_path)
        if actual is None:
            return False
        return actual == expected_checksum
