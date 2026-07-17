"""
modules/secure_archive/core/restore_planner.py

Intelligent restore planning engine.

Given a manifest and destination, generates a complete RestorePlan
describing what directories and files will be created.

No filesystem modifications. Only planning.
"""

from pathlib import Path
from typing import Optional

from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.restore_plan import (
    RestorePlan, RestorePlanEntry, RestoreDirectoryEntry,
    MODE_ORIGINAL_ROOT, MODE_CONTENTS_ONLY,
    MODE_ORIGINAL_LOCATION, MODE_CUSTOM
)
from vaultcore.logger import log_debug


class RestorePlanner:
    """
    Generates restore plans from manifest and destination.

    Supports multiple restore modes:
        - ORIGINAL_ROOT:     Recreate archive root as subfolder
        - CONTENTS_ONLY:     Extract contents directly to destination
        - ORIGINAL_LOCATION: Restore to original absolute path
        - CUSTOM:            Custom destination with root preserved
    """

    def plan(
        self,
        manifest: ArchiveManifest,
        destination: Path,
        mode: str = MODE_ORIGINAL_ROOT
    ) -> RestorePlan:
        """
        Generate a restore plan.

        Args:
            manifest:    The archive manifest.
            destination: User-chosen destination directory.
            mode:        Restore mode constant.

        Returns:
            A RestorePlan describing the complete restoration.
        """
        destination = destination.resolve()

        archive_root = manifest.archive_root or manifest.archive_name

        # Determine restore root based on mode
        if mode == MODE_ORIGINAL_ROOT:
            restore_root = destination / archive_root
        elif mode == MODE_CONTENTS_ONLY:
            restore_root = destination
        elif mode == MODE_ORIGINAL_LOCATION:
            original = manifest.original_source_path
            if original:
                restore_root = Path(original).resolve()
            else:
                restore_root = destination / archive_root
        elif mode == MODE_CUSTOM:
            restore_root = destination / archive_root
        else:
            restore_root = destination / archive_root

        # Build directory entries
        directories = []

        # Add the restore root itself if mode creates it
        if mode != MODE_CONTENTS_ONLY:
            directories.append(RestoreDirectoryEntry(
                relative_path    = "",
                destination_path = str(restore_root),
                is_empty         = False
            ))

        # Add all directories from manifest
        for dir_path in manifest.directory_paths:
            full_path = restore_root / dir_path
            directories.append(RestoreDirectoryEntry(
                relative_path    = dir_path,
                destination_path = str(full_path),
                is_empty         = False
            ))

        # Build file entries
        files = []
        total_size = 0

        for entry in manifest.files:
            full_path = restore_root / entry.path
            files.append(RestorePlanEntry(
                manifest_path    = entry.path,
                destination_path = str(full_path),
                size             = entry.original_size,
                checksum         = entry.checksum
            ))
            total_size += entry.original_size

        plan = RestorePlan(
            archive_name     = manifest.archive_name,
            archive_root     = archive_root,
            restore_mode     = mode,
            destination_root = str(destination),
            restore_root     = str(restore_root),
            directories      = directories,
            files            = files,
            total_files      = len(files),
            total_dirs       = len(directories),
            total_size       = total_size,
        )

        log_debug(
            f"[RestorePlanner] Plan: {plan.total_files} files, "
            f"{plan.total_dirs} dirs to {restore_root}"
        )

        return plan
