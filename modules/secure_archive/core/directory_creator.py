"""
modules/secure_archive/core/directory_creator.py

Creates directory hierarchy from a RestorePlan.

Executes before file restoration to ensure all parent
directories exist. Handles empty directories, validation,
and graceful handling of existing directories.
"""

from pathlib import Path
from dataclasses import dataclass, field

from modules.secure_archive.models.restore_plan import RestorePlan, RestoreDirectoryEntry
from modules.secure_archive.core.path_validator import PathValidator
from vaultcore.logger import log_debug, log_error


@dataclass
class DirectoryCreationResult:
    """
    Result of creating the directory hierarchy.

    Attributes:
        created:           Count of newly created directories.
        already_existed:   Count of directories that already existed.
        failed:            Count of directories that failed to create.
        errors:            List of error messages.
    """
    created:         int        = 0
    already_existed: int        = 0
    failed:          int        = 0
    errors:          list[str]  = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class DirectoryCreator:
    """
    Creates directories from a RestorePlan.

    All directory paths are validated before creation.
    Invalid paths (traversal, absolute, etc.) are rejected.
    """

    def __init__(self) -> None:
        self._validator = PathValidator()

    def create_from_plan(
        self,
        plan: RestorePlan
    ) -> DirectoryCreationResult:
        """
        Create all directories specified in a RestorePlan.

        Args:
            plan: The restore plan containing directory entries.

        Returns:
            DirectoryCreationResult with success/failure counts.
        """
        result = DirectoryCreationResult()
        restore_root = Path(plan.restore_root)

        for entry in plan.directories:
            dest = Path(entry.destination_path)

            # Validate path safety (for non-root entries)
            if entry.relative_path:
                validation = self._validator.validate(
                    entry.relative_path, restore_root
                )
                if not validation.is_safe:
                    result.failed += 1
                    result.errors.append(
                        f"Rejected: {entry.relative_path} - {validation.rejection_reason}"
                    )
                    log_error(
                        f"[DirectoryCreator] Rejected: "
                        f"{entry.relative_path} - {validation.rejection_reason}"
                    )
                    continue

            # Create directory
            try:
                if dest.exists():
                    result.already_existed += 1
                else:
                    dest.mkdir(parents=True, exist_ok=True)
                    result.created += 1
            except (OSError, PermissionError) as error:
                result.failed += 1
                result.errors.append(
                    f"Failed: {entry.destination_path} - {error}"
                )
                log_error(
                    f"[DirectoryCreator] Failed: {entry.destination_path}: {error}"
                )

        log_debug(
            f"[DirectoryCreator] {result.created} created, "
            f"{result.already_existed} existed, {result.failed} failed"
        )

        return result
