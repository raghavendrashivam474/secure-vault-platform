"""
modules/secure_archive/core/report_builder.py

Builds ArchiveReport from plan + manifest + package info.
"""

import time
from pathlib import Path

from modules.secure_archive.models.archive_plan import ArchivePlan
from modules.secure_archive.models.manifest import ArchiveManifest
from modules.secure_archive.models.compression_result import CompressionRunResult
from modules.secure_archive.models.reports import ArchiveReport


class ReportBuilder:
    """
    Builds an ArchiveReport from the outputs of the archive pipeline.
    """

    def build(
        self,
        plan: ArchivePlan,
        manifest: ArchiveManifest,
        run_result: CompressionRunResult,
        package_path: Path,
        total_duration: float
    ) -> ArchiveReport:
        """
        Build the archive report.

        Args:
            plan:            The executed archive plan.
            manifest:        The generated manifest.
            run_result:      Compression results.
            package_path:    Final .sva.dev file path.
            total_duration:  Total operation time.

        Returns:
            An ArchiveReport for platform consumers.
        """
        package_size = 0
        if package_path.exists():
            package_size = package_path.stat().st_size

        compression_ratio = 0.0
        if run_result.total_original > 0:
            compression_ratio = (
                1.0 - (run_result.total_compressed / run_result.total_original)
            ) * 100

        return ArchiveReport(
            archive_id          = manifest.archive_id,
            archive_name        = manifest.archive_name,
            project_type        = manifest.project_type,
            project_confidence  = manifest.project_confidence,
            files_scanned       = plan.file_count + plan.ignored_count,
            files_included      = plan.file_count,
            files_ignored       = plan.ignored_count,
            original_size       = plan.total_original_size,
            archived_input_size = run_result.total_original,
            compressed_size     = run_result.total_compressed,
            space_saved         = run_result.total_original - run_result.total_compressed,
            compression_ratio   = compression_ratio,
            duration            = total_duration,
            package_size        = package_size
        )
