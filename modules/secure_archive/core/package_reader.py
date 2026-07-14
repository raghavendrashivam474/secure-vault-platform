"""
modules/secure_archive/core/package_reader.py

Development archive package reader.

Reads .sva.dev packages to extract:
    - Archive manifest
    - Compressed payload entries
"""

import zipfile
from pathlib import Path
from typing import Optional

from modules.secure_archive.models.manifest import ArchiveManifest
from vaultcore.logger import log_debug, log_error


MANIFEST_FILENAME = "manifest.json"
PAYLOAD_PREFIX    = "payload/"


class PackageReader:
    """
    Reads development archive packages.

    Provides access to the manifest and compressed payload entries.
    """

    def __init__(self, package_path: Path) -> None:
        """
        Open a package for reading.

        Args:
            package_path: Path to the .sva.dev file.

        Raises:
            FileNotFoundError: If package does not exist.
            ValueError: If package is not a valid ZIP or missing manifest.
        """
        if not package_path.exists():
            raise FileNotFoundError(f"Package not found: {package_path}")

        self._package_path = package_path

        try:
            self._zip = zipfile.ZipFile(package_path, mode="r")
        except zipfile.BadZipFile as error:
            raise ValueError(f"Invalid archive package: {error}")

        # Verify manifest exists
        if MANIFEST_FILENAME not in self._zip.namelist():
            self._zip.close()
            raise ValueError(f"Package missing {MANIFEST_FILENAME}")

    def read_manifest(self) -> ArchiveManifest:
        """
        Read and parse the archive manifest.

        Returns:
            The ArchiveManifest.

        Raises:
            ValueError: If manifest format version is unsupported.
        """
        try:
            manifest_bytes = self._zip.read(MANIFEST_FILENAME)
            return ArchiveManifest.from_bytes(manifest_bytes)
        except Exception as error:
            log_error(f"[PackageReader] Failed to read manifest: {error}")
            raise

    def read_payload(self, relative_path: str) -> Optional[bytes]:
        """
        Read compressed payload for one file.

        Args:
            relative_path: The manifest-relative file path.

        Returns:
            Compressed bytes, or None if not found.
        """
        payload_path = PAYLOAD_PREFIX + relative_path

        if payload_path not in self._zip.namelist():
            log_error(f"[PackageReader] Payload not found: {relative_path}")
            return None

        try:
            return self._zip.read(payload_path)
        except Exception as error:
            log_error(f"[PackageReader] Failed to read payload {relative_path}: {error}")
            return None

    def list_payload_entries(self) -> list[str]:
        """
        Return all payload entry relative paths.

        Returns:
            List of relative paths (without PAYLOAD_PREFIX).
        """
        entries = []
        for name in self._zip.namelist():
            if name.startswith(PAYLOAD_PREFIX):
                entries.append(name[len(PAYLOAD_PREFIX):])
        return sorted(entries)

    def get_package_size(self) -> int:
        """Return total package file size in bytes."""
        return self._package_path.stat().st_size

    def close(self) -> None:
        """Close the package."""
        if self._zip:
            self._zip.close()
            self._zip = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
