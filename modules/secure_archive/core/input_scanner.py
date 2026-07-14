"""
modules/secure_archive/core/input_scanner.py

Deterministic filesystem scanner for Secure Archive.

Recursively walks files and folders. Returns structured
ScanResult describing what exists.

Does NOT classify, ignore, checksum, or compress.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from modules.secure_archive.models.scan import ScannedFile, ScanResult
from vaultcore.logger import log_debug, log_error


class InputScanner:
    """
    Scans filesystem paths to produce a deterministic ScanResult.

    Supports:
        - Single file input
        - Single folder input (recursive)
        - Multiple paths (aggregated under a common conceptual root)
    """

    def scan(self, source_path: Path) -> ScanResult:
        """
        Scan a filesystem path.

        Args:
            source_path: File or folder to scan.

        Returns:
            A ScanResult describing all discovered files.
        """
        start = time.time()
        source_path = source_path.resolve()

        if not source_path.exists():
            result = ScanResult(
                source_root = str(source_path),
                source_type = "unknown"
            )
            result.errors.append(f"Path does not exist: {source_path}")
            return result

        if source_path.is_file():
            return self._scan_single_file(source_path, start)
        elif source_path.is_dir():
            return self._scan_folder(source_path, start)
        else:
            result = ScanResult(
                source_root = str(source_path),
                source_type = "unknown"
            )
            result.errors.append(f"Unsupported path type: {source_path}")
            return result

    def _scan_single_file(self, file_path: Path, start_time: float) -> ScanResult:
        """Scan a single file."""
        result = ScanResult(
            source_root = str(file_path.parent),
            source_type = "file"
        )

        try:
            scanned = self._make_scanned_file(file_path, file_path.parent)
            if scanned:
                result.files.append(scanned)
                result.file_count = 1
                result.total_size = scanned.size
        except Exception as error:
            result.errors.append(f"{file_path}: {error}")
            log_error(f"[InputScanner] Failed to scan {file_path}: {error}")

        result.scan_duration = time.time() - start_time
        return result

    def _scan_folder(self, folder_path: Path, start_time: float) -> ScanResult:
        """Recursively scan a folder."""
        result = ScanResult(
            source_root = str(folder_path),
            source_type = "folder"
        )

        try:
            for root, dirs, files in os.walk(folder_path):
                root_path = Path(root)

                # Sort for deterministic ordering
                files.sort()
                dirs.sort()

                for filename in files:
                    file_path = root_path / filename
                    try:
                        scanned = self._make_scanned_file(file_path, folder_path)
                        if scanned:
                            result.files.append(scanned)
                            result.total_size += scanned.size
                    except (OSError, PermissionError) as error:
                        result.errors.append(f"{file_path}: {error}")
                        log_debug(f"[InputScanner] Skipped {file_path}: {error}")
                    except Exception as error:
                        result.errors.append(f"{file_path}: {error}")

            result.file_count = len(result.files)

        except Exception as error:
            log_error(f"[InputScanner] Walk failed on {folder_path}: {error}")
            result.errors.append(f"Scan failed: {error}")

        result.scan_duration = time.time() - start_time
        return result

    def _make_scanned_file(
        self,
        file_path: Path,
        scan_root: Path
    ) -> Optional[ScannedFile]:
        """
        Build a ScannedFile object from a filesystem path.

        Args:
            file_path: Absolute file path.
            scan_root: Root used for relative path calculation.

        Returns:
            A ScannedFile or None if file is unreadable.
        """
        try:
            stat = file_path.stat()
        except (OSError, PermissionError):
            return None

        try:
            relative = file_path.relative_to(scan_root)
            relative_str = str(relative).replace("\\", "/")
        except ValueError:
            relative_str = file_path.name

        modified = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()

        return ScannedFile(
            absolute_source_path = str(file_path),
            relative_path        = relative_str,
            filename             = file_path.name,
            extension            = file_path.suffix.lstrip(".").lower(),
            size                 = stat.st_size,
            modified_time        = modified
        )
