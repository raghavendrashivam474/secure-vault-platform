"""
modules/secure_archive/core/project_detector.py

Deterministic project type detection.

Uses marker files to identify common software project types.
Never uses AI, heuristics, or content inspection.
Detection is deterministic and priority-ordered.
"""

from modules.secure_archive.models.scan import ScanResult
from modules.secure_archive.models.project import (
    ProjectProfile,
    PROJECT_PYTHON, PROJECT_NODEJS, PROJECT_FLUTTER, PROJECT_RUST, PROJECT_GENERIC,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
)
from vaultcore.logger import log_debug


# Marker files per project type, in priority order
# Higher priority projects (more specific) checked first
PROJECT_MARKERS = {
    PROJECT_FLUTTER: {
        "high":   ["pubspec.yaml"],
        "medium": [".metadata"],
    },
    PROJECT_RUST: {
        "high":   ["Cargo.toml"],
        "medium": ["Cargo.lock"],
    },
    PROJECT_NODEJS: {
        "high":   ["package.json"],
        "medium": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
    },
    PROJECT_PYTHON: {
        "high":   ["pyproject.toml", "setup.py", "requirements.txt"],
        "medium": ["Pipfile", "setup.cfg", "poetry.lock"],
    },
}

# Priority order (most specific first)
DETECTION_PRIORITY = [
    PROJECT_FLUTTER,
    PROJECT_RUST,
    PROJECT_NODEJS,
    PROJECT_PYTHON,
]


class ProjectDetector:
    """
    Detects project type from a ScanResult using marker files.

    Detection is deterministic:
        1. Check each project type in priority order.
        2. High-confidence markers win over medium-confidence.
        3. Falls back to GENERIC when no markers match.
    """

    def detect(self, scan_result: ScanResult) -> ProjectProfile:
        """
        Detect the project type from scanned files.

        Args:
            scan_result: The scan output from InputScanner.

        Returns:
            A ProjectProfile.
        """
        # Extract root-level filenames only (markers usually at root)
        root_files = self._get_root_level_files(scan_result)

        # Check each project type in priority order
        for project_type in DETECTION_PRIORITY:
            markers      = PROJECT_MARKERS[project_type]
            high_matches = [m for m in markers["high"]   if m in root_files]
            med_matches  = [m for m in markers["medium"] if m in root_files]

            if high_matches:
                log_debug(
                    f"[ProjectDetector] Detected {project_type} "
                    f"(high confidence): {high_matches}"
                )
                return ProjectProfile(
                    project_type = project_type,
                    confidence   = CONFIDENCE_HIGH,
                    markers      = high_matches + med_matches,
                    root_path    = scan_result.source_root
                )
            elif med_matches:
                log_debug(
                    f"[ProjectDetector] Detected {project_type} "
                    f"(medium confidence): {med_matches}"
                )
                return ProjectProfile(
                    project_type = project_type,
                    confidence   = CONFIDENCE_MEDIUM,
                    markers      = med_matches,
                    root_path    = scan_result.source_root
                )

        # No markers matched
        log_debug("[ProjectDetector] No markers detected, using generic")
        return ProjectProfile(
            project_type = PROJECT_GENERIC,
            confidence   = CONFIDENCE_LOW,
            markers      = [],
            root_path    = scan_result.source_root
        )

    def _get_root_level_files(self, scan_result: ScanResult) -> set[str]:
        """
        Return the set of filenames at the scan root level.

        Marker files are always at the root.
        Sub-directory markers do not count.

        Args:
            scan_result: The scan output.

        Returns:
            Set of root-level filenames.
        """
        root_files = set()

        for file_entry in scan_result.files:
            # Check if file is at root (no path separator in relative_path)
            if "/" not in file_entry.relative_path:
                root_files.add(file_entry.filename)

        return root_files
