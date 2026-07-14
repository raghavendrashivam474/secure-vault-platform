"""
modules/secure_archive/core/package_writer.py

Development archive package writer.

Creates .sva.dev packages containing:
    - manifest.json         (archive metadata)
    - payload/<files>       (compressed file entries)

Uses ZIP as the container format. This is the UNENCRYPTED
development format. The final encrypted .sva format will
be introduced in a future sprint.
"""

import zipfile
from pathlib import Path
from typing import Callable, Optional

from modules.secure_archive.models.archive_plan import ArchivePlan
from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.compression_result import CompressionRunResult
from modules.secure_archive.core.compression_engine import CompressionEngine
from modules.secure_archive.core.manifest_builder import ManifestBuilder
from vaultcore.logger import log_debug, log_error


# Development package extension
DEV_PACKAGE_EXTENSION = ".sva.dev"

# Manifest filename inside package
MANIFEST_FILENAME = "manifest.json"

# Payload directory inside package
PAYLOAD_PREFIX = "payload/"


class PackageWriter:
    """
    Writes development archive packages.

    A package contains:
        - manifest.json     (the archive blueprint)
        - payload/<path>    (compressed file contents)

    NOTE: This is the unencrypted development format.
    """

    def __init__(self) -> None:
        self._compressor      = CompressionEngine()
        self._manifest_builder = ManifestBuilder()

    def write(
        self,
        plan: ArchivePlan,
        output_path: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> tuple[ArchiveManifest, CompressionRunResult]:
        """
        Write a complete archive package.

        Args:
            plan:              The archive plan to execute.
            output_path:       Where to write the .sva.dev file.
            progress_callback: Optional progress callback.

        Returns:
            Tuple of (manifest, compression_run_result).
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Store compressed bytes per file in memory during writing
        # (For streaming later, we'd write to a temp buffer per file)
        compressed_buffers: dict[str, bytearray] = {}

        def make_writer(relative_path: str) -> Callable[[bytes], None]:
            """Factory that returns a writer capturing compressed bytes."""
            buf = bytearray()
            compressed_buffers[relative_path] = buf
            return buf.extend

        # Execute compression
        log_debug(f"[PackageWriter] Compressing {plan.file_count} files")
        run_result = self._compressor.execute_plan(
            plan                  = plan,
            output_writer_factory = make_writer,
            progress_callback     = progress_callback
        )

        # Build manifest from compression results
        manifest = self._manifest_builder.build(plan, run_result)

        # Write ZIP container
        log_debug(f"[PackageWriter] Writing package to {output_path}")
        try:
            with zipfile.ZipFile(
                output_path,
                mode        = "w",
                compression = zipfile.ZIP_STORED   # Container itself is not compressed
            ) as zf:
                # Write manifest first
                zf.writestr(MANIFEST_FILENAME, manifest.to_bytes())

                # Write each compressed payload entry
                for entry in manifest.files:
                    payload_path = PAYLOAD_PREFIX + entry.path
                    compressed   = bytes(compressed_buffers.get(entry.path, b""))
                    zf.writestr(payload_path, compressed)

            log_debug(f"[PackageWriter] Package written: {output_path.stat().st_size:,} bytes")
            return manifest, run_result

        except Exception as error:
            log_error(f"[PackageWriter] Failed to write package: {error}")
            # Clean up partial file
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise
