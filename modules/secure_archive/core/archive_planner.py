"""
modules/secure_archive/core/archive_planner.py

Combines scanner, detector, ignore engine, classifier, and strategy
into a single immutable ArchivePlan.

The plan is the source of truth for the compression engine.
"""

from pathlib import Path
from modules.secure_archive.models.scan import ScanResult
from modules.secure_archive.models.project import ProjectProfile
from modules.secure_archive.models.ignore import IgnoreDecision, IgnoreSummary
from modules.secure_archive.models.classification import FileClassification
from modules.secure_archive.models.compression import CompressionDecision
from modules.secure_archive.models.archive_plan import (
    ArchivePlan, ArchivePlanEntry
)


class ArchivePlanner:
    """
    Builds an ArchivePlan by combining all intelligence outputs.

    Inputs:
        - ScanResult
        - ProjectProfile
        - Ignore decisions and summary
        - File classifications (for included files only)
        - Compression decisions (for included files only)

    Output:
        - Immutable ArchivePlan
    """

    def build(
        self,
        scan_result: ScanResult,
        project_profile: ProjectProfile,
        ignore_decisions: list[IgnoreDecision],
        ignore_summary: IgnoreSummary,
        classifications: list[FileClassification],
        compression_decisions: list[CompressionDecision]
    ) -> ArchivePlan:
        """
        Build the archive plan.

        Args:
            scan_result:           From InputScanner.
            project_profile:       From ProjectDetector.
            ignore_decisions:      From IgnoreEngine (one per scanned file).
            ignore_summary:        From IgnoreEngine (aggregated).
            classifications:       From FileClassifier (included files only).
            compression_decisions: From CompressionStrategyEngine (included only).

        Returns:
            An ArchivePlan ready for execution.
        """
        # Build lookup: relative_path -> ignore decision
        ignore_lookup = {d.relative_path: d for d in ignore_decisions}

        # Build lookup for classification and compression by relative path
        classification_lookup = {c.relative_path: c for c in classifications}
        compression_lookup    = {d.relative_path: d for d in compression_decisions}

        included_entries = []
        ignored_entries  = []

        for scanned_file in scan_result.files:
            ignore_dec = ignore_lookup.get(scanned_file.relative_path)

            if ignore_dec is None:
                continue

            if ignore_dec.ignored:
                # Include in ignored list as metadata only
                ignored_entries.append({
                    "relative_path": scanned_file.relative_path,
                    "size":          scanned_file.size,
                    "rule":          ignore_dec.rule,
                    "reason":        ignore_dec.reason
                })
            else:
                # Build plan entry with strategy
                cls  = classification_lookup.get(scanned_file.relative_path)
                comp = compression_lookup.get(scanned_file.relative_path)

                if cls is None or comp is None:
                    continue

                included_entries.append(ArchivePlanEntry(
                    source_path          = scanned_file.absolute_source_path,
                    relative_path        = scanned_file.relative_path,
                    size                 = scanned_file.size,
                    file_class           = cls.file_class,
                    compression_strategy = comp.strategy,
                    compression_level    = comp.compression_level,
                    strategy_reason      = comp.reason
                ))

        # Build summaries
        strategy_summary = {}
        class_summary    = {}
        for entry in included_entries:
            strategy_summary[entry.compression_strategy] = \
                strategy_summary.get(entry.compression_strategy, 0) + 1
            class_summary[entry.file_class] = \
                class_summary.get(entry.file_class, 0) + 1

        # Derive archive name from source
        source_path = Path(scan_result.source_root)
        archive_name = source_path.name if source_path.name else "archive"

        return ArchivePlan(
            archive_name        = archive_name,
            source_root         = scan_result.source_root,
            project_profile     = project_profile,
            included_files      = included_entries,
            ignored_files       = ignored_entries,
            total_original_size = scan_result.total_size,
            included_size       = ignore_summary.included_size,
            ignored_size        = ignore_summary.ignored_size,
            strategy_summary    = strategy_summary,
            class_summary       = class_summary,
            ignore_summary      = dict(ignore_summary.by_rule),
        )
