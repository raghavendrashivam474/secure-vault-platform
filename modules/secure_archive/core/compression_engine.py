"""
modules/secure_archive/core/compression_engine.py

Plan-driven compression execution engine.

Executes an ArchivePlan file by file. Each file uses
the compression strategy already assigned by the planner.

CRITICAL: This engine contains NO extension rules.
It executes decisions, it never makes them.
"""

import zlib
import time
from pathlib import Path
from typing import Optional, Callable

from modules.secure_archive.models.archive_plan import ArchivePlan, ArchivePlanEntry
from modules.secure_archive.models.compression_result import (
    CompressionResult, CompressionRunResult
)
from modules.secure_archive.models.compression import (
    STRATEGY_STORE, STRATEGY_DEFLATE_HIGH,
    STRATEGY_DEFLATE_NORMAL, STRATEGY_DEFLATE_FAST
)
from modules.secure_archive.core.checksum_engine import ChecksumEngine
from vaultcore.logger import log_debug, log_error


# Chunk size for streaming compression
CHUNK_SIZE = 64 * 1024   # 64 KB


class CompressionEngine:
    """
    Executes an ArchivePlan.

    For each file:
        1. Read source file in chunks.
        2. Apply assigned compression strategy.
        3. Write compressed bytes to output stream.
        4. Compute checksum during read.
        5. Record result.
    """

    def __init__(self) -> None:
        self._checksum_engine = ChecksumEngine()

    def compress_file(
        self,
        entry: ArchivePlanEntry,
        output_writer: Callable[[bytes], None]
    ) -> CompressionResult:
        """
        Compress a single file according to its plan entry.

        Args:
            entry:         The archive plan entry.
            output_writer: Callable that writes compressed bytes.

        Returns:
            CompressionResult with sizes and checksum.
        """
        source_path = Path(entry.source_path)

        if not source_path.exists():
            return CompressionResult(
                relative_path   = entry.relative_path,
                original_size   = 0,
                compressed_size = 0,
                strategy        = entry.compression_strategy,
                success         = False,
                error           = "Source file does not exist"
            )

        try:
            # STORE strategy: no compression, direct write
            if entry.compression_strategy == STRATEGY_STORE:
                return self._store_file(entry, source_path, output_writer)
            else:
                return self._deflate_file(entry, source_path, output_writer)

        except Exception as error:
            log_error(f"[CompressionEngine] Failed {entry.relative_path}: {error}")
            return CompressionResult(
                relative_path   = entry.relative_path,
                original_size   = entry.size,
                compressed_size = 0,
                strategy        = entry.compression_strategy,
                success         = False,
                error           = str(error)
            )

    def _store_file(
        self,
        entry: ArchivePlanEntry,
        source_path: Path,
        output_writer: Callable[[bytes], None]
    ) -> CompressionResult:
        """Store file without compression."""
        import hashlib
        hasher = hashlib.sha256()
        original_size   = 0
        compressed_size = 0

        with open(source_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                original_size += len(chunk)
                output_writer(chunk)
                compressed_size += len(chunk)

        return CompressionResult(
            relative_path   = entry.relative_path,
            original_size   = original_size,
            compressed_size = compressed_size,
            strategy        = entry.compression_strategy,
            checksum        = hasher.hexdigest(),
            success         = True
        )

    def _deflate_file(
        self,
        entry: ArchivePlanEntry,
        source_path: Path,
        output_writer: Callable[[bytes], None]
    ) -> CompressionResult:
        """Compress file with deflate at specified level."""
        import hashlib
        hasher = hashlib.sha256()
        compressor = zlib.compressobj(entry.compression_level)

        original_size   = 0
        compressed_size = 0

        with open(source_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                original_size += len(chunk)

                compressed_chunk = compressor.compress(chunk)
                if compressed_chunk:
                    output_writer(compressed_chunk)
                    compressed_size += len(compressed_chunk)

        # Flush remaining compressed data
        final_chunk = compressor.flush()
        if final_chunk:
            output_writer(final_chunk)
            compressed_size += len(final_chunk)

        return CompressionResult(
            relative_path   = entry.relative_path,
            original_size   = original_size,
            compressed_size = compressed_size,
            strategy        = entry.compression_strategy,
            checksum        = hasher.hexdigest(),
            success         = True
        )

    def execute_plan(
        self,
        plan: ArchivePlan,
        output_writer_factory: Callable[[str], Callable[[bytes], None]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> CompressionRunResult:
        """
        Execute the full archive plan.

        Args:
            plan:                  The archive plan.
            output_writer_factory: Factory that returns a writer for a given
                                   relative path. This decouples compression
                                   from packaging (Sprint 14.11 will provide
                                   the actual package writer).
            progress_callback:     Optional callback(current, total, path).

        Returns:
            CompressionRunResult aggregating all file results.
        """
        run = CompressionRunResult()
        start = time.time()
        total = len(plan.included_files)

        for index, entry in enumerate(plan.included_files, 1):
            if progress_callback:
                progress_callback(index, total, entry.relative_path)

            # Get writer for this entry
            writer = output_writer_factory(entry.relative_path)

            # Execute compression
            result = self.compress_file(entry, writer)
            run.results.append(result)

            # Aggregate
            run.total_original   += result.original_size
            run.total_compressed += result.compressed_size

            if result.success:
                run.successful += 1
            else:
                run.failed += 1
                run.errors.append(f"{entry.relative_path}: {result.error}")

        run.duration = time.time() - start

        log_debug(
            f"[CompressionEngine] {run.successful}/{total} files compressed "
            f"in {run.duration:.2f}s"
        )

        return run
