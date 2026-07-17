"""
modules/secure_archive/core/manifest_builder.py

Builds an ArchiveManifest from plan + compression results.
"""

import uuid
from datetime import datetime, timezone

from modules.secure_archive.models.archive_plan import ArchivePlan
from modules.secure_archive.models.compression_result import CompressionRunResult
from modules.secure_archive.models.manifest import (
    ArchiveManifest, ManifestFileEntry, MANIFEST_FORMAT_VERSION
)


# Secure Archive module version at time of manifest creation
MODULE_VERSION = "0.1.0"


class ManifestBuilder:
    """
    Combines an ArchivePlan with CompressionRunResult to produce
    the final ArchiveManifest.

    The manifest records what was actually archived,
    not what was planned.
    """

    def build(
        self,
        plan: ArchivePlan,
        run_result: CompressionRunResult,
        root_info = None
    ) -> ArchiveManifest:
        """
        Build the manifest from plan and compression results.

        Args:
            plan:       The archive plan that was executed.
            run_result: The compression execution results.

        Returns:
            An ArchiveManifest ready for serialization.
        """
        # Build lookup: relative_path -> plan entry
        plan_lookup = {e.relative_path: e for e in plan.included_files}

        # Only include successful compression results
        file_entries = []
        for result in run_result.results:
            if not result.success:
                continue

            plan_entry = plan_lookup.get(result.relative_path)
            if plan_entry is None:
                continue

            file_entries.append(ManifestFileEntry(
                path                 = result.relative_path,
                original_size        = result.original_size,
                compressed_size      = result.compressed_size,
                checksum             = result.checksum or "",
                file_class           = plan_entry.file_class,
                compression_strategy = result.strategy,
                compression_level    = plan_entry.compression_level,
            ))

        return ArchiveManifest(
            format_version     = MANIFEST_FORMAT_VERSION,
            archive_id         = str(uuid.uuid4()),
            archive_name       = plan.archive_name,
            module_version     = MODULE_VERSION,
            project_type       = plan.project_profile.project_type,
            project_confidence = plan.project_profile.confidence,
            created_at         = datetime.now(timezone.utc).isoformat(),
            file_count         = len(file_entries),
            original_size      = run_result.total_original,
            compressed_size    = run_result.total_compressed,
            files              = file_entries,
            archive_root       = root_info.archive_root if root_info else plan.archive_name,
            original_source_path = root_info.original_path if root_info else "",
            directory_paths    = root_info.directory_paths if root_info else [],
            empty_directory_count = root_info.empty_dir_count if root_info else 0,
        )

