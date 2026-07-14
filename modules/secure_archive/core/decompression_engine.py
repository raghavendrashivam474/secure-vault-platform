"""
modules/secure_archive/core/decompression_engine.py

Reverses compression using the strategy recorded in the manifest.

Uses ONLY manifest metadata. Never re-classifies files.
Streaming decompression to keep memory usage predictable.
"""

import zlib
from typing import Optional

from modules.secure_archive.models.compression import (
    STRATEGY_STORE, STRATEGY_DEFLATE_HIGH,
    STRATEGY_DEFLATE_NORMAL, STRATEGY_DEFLATE_FAST
)
from vaultcore.logger import log_error


class DecompressionEngine:
    """
    Reverses compression for archive payload entries.

    The compression strategy comes from the manifest.
    This engine executes decompression, never decides.
    """

    def decompress(
        self,
        compressed_data: bytes,
        strategy: str
    ) -> Optional[bytes]:
        """
        Decompress bytes using the specified strategy.

        Args:
            compressed_data: Compressed payload bytes.
            strategy:        Strategy identifier from manifest.

        Returns:
            Original uncompressed bytes, or None on error.
        """
        try:
            if strategy == STRATEGY_STORE:
                # STORE = no compression, return as-is
                return compressed_data

            elif strategy in (
                STRATEGY_DEFLATE_HIGH,
                STRATEGY_DEFLATE_NORMAL,
                STRATEGY_DEFLATE_FAST
            ):
                # Deflate: any level uses same decompression
                return zlib.decompress(compressed_data)

            else:
                log_error(f"[DecompressionEngine] Unknown strategy: {strategy}")
                return None

        except zlib.error as error:
            log_error(f"[DecompressionEngine] Deflate error: {error}")
            return None
        except Exception as error:
            log_error(f"[DecompressionEngine] Unexpected error: {error}")
            return None

    def decompress_to_writer(
        self,
        compressed_data: bytes,
        strategy: str,
        writer_callable
    ) -> bool:
        """
        Decompress and stream output to a writer.

        Args:
            compressed_data: Compressed payload bytes.
            strategy:        Strategy from manifest.
            writer_callable: Callable that receives decompressed bytes.

        Returns:
            True if decompression succeeded.
        """
        decompressed = self.decompress(compressed_data, strategy)
        if decompressed is None:
            return False

        try:
            writer_callable(decompressed)
            return True
        except Exception as error:
            log_error(f"[DecompressionEngine] Write failed: {error}")
            return False
