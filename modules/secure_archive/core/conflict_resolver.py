"""
modules/secure_archive/core/conflict_resolver.py

Restore conflict detection and resolution.

Detects existing files and directories at restoration targets.
Applies resolution policies to produce a Resolved Restore Plan.
No filesystem modifications.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from modules.secure_archive.models.restore_plan import (
    RestorePlan, RestorePlanEntry
)
from vaultcore.logger import log_debug


# Conflict type constants
CONFLICT_EXISTING_FILE    = "existing_file"
CONFLICT_EXISTING_DIR     = "existing_directory"
CONFLICT_PERMISSION       = "permission_denied"
CONFLICT_NAME_COLLISION   = "name_collision"

# Resolution policy constants
POLICY_OVERWRITE   = "overwrite"
POLICY_RENAME      = "rename"
POLICY_SKIP        = "skip"
POLICY_ASK_USER    = "ask_user"


@dataclass
class Conflict:
    """
    Represents a single restore conflict.

    Attributes:
        manifest_path:     File path from manifest.
        destination_path:  Target destination path.
        conflict_type:     Type of conflict detected.
        existing_size:     Size of existing file (if applicable).
        existing_modified: Modified date of existing file.
        resolution:        Chosen resolution policy.
    """
    manifest_path:     str
    destination_path:  str
    conflict_type:     str
    existing_size:     int            = 0
    existing_modified: Optional[str]  = None
    resolution:        str            = POLICY_OVERWRITE


@dataclass
class ConflictReport:
    """
    Summary of all detected conflicts.

    Attributes:
        conflicts:         List of individual conflicts.
        total_conflicts:   Total count.
        files_to_overwrite: Count after resolution.
        files_to_rename:   Count after resolution.
        files_to_skip:     Count after resolution.
    """
    conflicts:          list[Conflict] = field(default_factory=list)
    total_conflicts:    int = 0
    files_to_overwrite: int = 0
    files_to_rename:    int = 0
    files_to_skip:      int = 0

    @property
    def has_conflicts(self) -> bool:
        return self.total_conflicts > 0


class ConflictDetector:
    """
    Scans a RestorePlan's destination for conflicts.
    """

    def detect(self, plan: RestorePlan) -> ConflictReport:
        """
        Scan the plan destination for conflicts.

        Args:
            plan: The restore plan to check.

        Returns:
            A ConflictReport listing all detected conflicts.
        """
        report = ConflictReport()

        for entry in plan.files:
            dest = Path(entry.destination_path)

            if dest.exists():
                try:
                    stat = dest.stat()
                    existing_size = stat.st_size
                    existing_mod  = datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat()
                except (OSError, PermissionError):
                    existing_size = 0
                    existing_mod  = None

                conflict = Conflict(
                    manifest_path     = entry.manifest_path,
                    destination_path  = entry.destination_path,
                    conflict_type     = CONFLICT_EXISTING_FILE,
                    existing_size     = existing_size,
                    existing_modified = existing_mod,
                    resolution        = POLICY_OVERWRITE  # default
                )
                report.conflicts.append(conflict)

        report.total_conflicts = len(report.conflicts)

        log_debug(
            f"[ConflictDetector] Found {report.total_conflicts} conflicts"
        )

        return report


class ConflictResolver:
    """
    Applies a resolution policy to all conflicts.
    """

    def resolve(
        self,
        report: ConflictReport,
        policy: str = POLICY_OVERWRITE
    ) -> ConflictReport:
        """
        Apply a resolution policy to all conflicts.

        Args:
            report: The conflict report from ConflictDetector.
            policy: Resolution policy to apply.

        Returns:
            Updated ConflictReport with resolutions applied.
        """
        report.files_to_overwrite = 0
        report.files_to_rename    = 0
        report.files_to_skip      = 0

        for conflict in report.conflicts:
            conflict.resolution = policy

            if policy == POLICY_OVERWRITE:
                report.files_to_overwrite += 1
            elif policy == POLICY_RENAME:
                report.files_to_rename += 1
            elif policy == POLICY_SKIP:
                report.files_to_skip += 1

        log_debug(
            f"[ConflictResolver] Resolved {len(report.conflicts)} conflicts "
            f"with policy: {policy}"
        )

        return report

    def apply_to_plan(
        self,
        plan: RestorePlan,
        report: ConflictReport
    ) -> RestorePlan:
        """
        Update a RestorePlan based on resolved conflicts.

        Removes skipped files. Renames renamed files.

        Args:
            plan:   The original restore plan.
            report: The resolved conflict report.

        Returns:
            Updated RestorePlan (may have fewer files if skipped).
        """
        # Build skip set
        skip_paths = {
            c.manifest_path for c in report.conflicts
            if c.resolution == POLICY_SKIP
        }

        # Build rename map
        rename_map = {}
        for conflict in report.conflicts:
            if conflict.resolution == POLICY_RENAME:
                original = Path(conflict.destination_path)
                stem   = original.stem
                suffix = original.suffix
                parent = original.parent

                # Find available name
                counter = 1
                while True:
                    new_name = f"{stem} ({counter}){suffix}"
                    new_path = parent / new_name
                    if not new_path.exists():
                        rename_map[conflict.manifest_path] = str(new_path)
                        break
                    counter += 1

        # Build updated file list
        updated_files = []
        for entry in plan.files:
            if entry.manifest_path in skip_paths:
                continue  # Skip this file

            if entry.manifest_path in rename_map:
                # Create renamed entry
                updated_files.append(RestorePlanEntry(
                    manifest_path    = entry.manifest_path,
                    destination_path = rename_map[entry.manifest_path],
                    size             = entry.size,
                    checksum         = entry.checksum
                ))
            else:
                updated_files.append(entry)

        plan.files       = updated_files
        plan.total_files = len(updated_files)
        plan.total_size  = sum(f.size for f in updated_files)

        return plan
