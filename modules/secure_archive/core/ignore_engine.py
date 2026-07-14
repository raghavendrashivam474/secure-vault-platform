"""
modules/secure_archive/core/ignore_engine.py

Project-aware ignore engine.

Identifies candidate files to exclude from archives.
Rules apply based on detected project type plus universal rules.

CRITICAL: This engine only recommends. It never mutates source files.
"""

import fnmatch
from modules.secure_archive.models.scan import ScanResult, ScannedFile
from modules.secure_archive.models.project import (
    ProjectProfile,
    PROJECT_PYTHON, PROJECT_NODEJS, PROJECT_FLUTTER, PROJECT_RUST, PROJECT_GENERIC
)
from modules.secure_archive.models.ignore import (
    IgnoreDecision, IgnoreSummary,
    REASON_PROJECT_ARTIFACT, REASON_BUILD_OUTPUT, REASON_CACHE,
    REASON_OS_ARTIFACT, REASON_VCS, REASON_TEMP
)
from vaultcore.logger import log_debug


# Project-specific ignore patterns
# Format: (pattern, reason)
# Patterns ending with / match directory prefixes
# Patterns with * use fnmatch glob matching
PROJECT_RULES = {
    PROJECT_PYTHON: [
        (".venv/",           REASON_PROJECT_ARTIFACT),
        ("venv/",            REASON_PROJECT_ARTIFACT),
        ("env/",             REASON_PROJECT_ARTIFACT),
        ("__pycache__/",     REASON_CACHE),
        (".pytest_cache/",   REASON_CACHE),
        (".mypy_cache/",     REASON_CACHE),
        (".tox/",            REASON_CACHE),
        ("*.pyc",            REASON_CACHE),
        ("*.pyo",            REASON_CACHE),
        ("dist/",            REASON_BUILD_OUTPUT),
        ("build/",           REASON_BUILD_OUTPUT),
        ("*.egg-info/",      REASON_BUILD_OUTPUT),
    ],
    PROJECT_NODEJS: [
        ("node_modules/",    REASON_PROJECT_ARTIFACT),
        ("dist/",            REASON_BUILD_OUTPUT),
        ("build/",           REASON_BUILD_OUTPUT),
        (".next/",           REASON_BUILD_OUTPUT),
        (".nuxt/",           REASON_BUILD_OUTPUT),
        (".cache/",          REASON_CACHE),
        (".parcel-cache/",   REASON_CACHE),
        ("coverage/",        REASON_BUILD_OUTPUT),
    ],
    PROJECT_FLUTTER: [
        ("build/",           REASON_BUILD_OUTPUT),
        (".dart_tool/",      REASON_PROJECT_ARTIFACT),
        (".flutter-plugins", REASON_PROJECT_ARTIFACT),
        (".flutter-plugins-dependencies", REASON_PROJECT_ARTIFACT),
        (".packages",        REASON_PROJECT_ARTIFACT),
    ],
    PROJECT_RUST: [
        ("target/",          REASON_BUILD_OUTPUT),
        ("Cargo.lock",       REASON_PROJECT_ARTIFACT),
    ],
}

# Universal rules applied to all project types
UNIVERSAL_RULES = [
    (".DS_Store",      REASON_OS_ARTIFACT),
    ("Thumbs.db",      REASON_OS_ARTIFACT),
    ("desktop.ini",    REASON_OS_ARTIFACT),
    ("*.tmp",          REASON_TEMP),
    ("*.temp",         REASON_TEMP),
    ("*.swp",          REASON_TEMP),
    (".git/",          REASON_VCS),
    (".svn/",          REASON_VCS),
    (".hg/",           REASON_VCS),
]


class IgnoreEngine:
    """
    Determines which files should be excluded from an archive.

    Rules are project-aware and never modify source files.
    """

    def evaluate(
        self,
        scan_result: ScanResult,
        project_profile: ProjectProfile
    ) -> tuple[list[IgnoreDecision], IgnoreSummary]:
        """
        Evaluate all scanned files against ignore rules.

        Args:
            scan_result:     The scan output.
            project_profile: The detected project type.

        Returns:
            A tuple of (list of IgnoreDecision, IgnoreSummary).
        """
        # Build applicable ruleset
        rules = list(UNIVERSAL_RULES)
        if project_profile.project_type in PROJECT_RULES:
            rules.extend(PROJECT_RULES[project_profile.project_type])

        decisions = []
        summary   = IgnoreSummary()

        for file_entry in scan_result.files:
            decision = self._evaluate_file(file_entry, rules)
            decisions.append(decision)

            # Update summary
            summary.total_files += 1

            if decision.ignored:
                summary.ignored_files += 1
                summary.ignored_size  += decision.estimated_size

                # Aggregate by reason and rule
                summary.by_reason[decision.reason] = \
                    summary.by_reason.get(decision.reason, 0) + 1
                summary.by_rule[decision.rule] = \
                    summary.by_rule.get(decision.rule, 0) + 1
            else:
                summary.included_files += 1
                summary.included_size  += decision.estimated_size

        log_debug(
            f"[IgnoreEngine] {summary.included_files} included, "
            f"{summary.ignored_files} ignored"
        )

        return decisions, summary

    def _evaluate_file(
        self,
        file_entry: ScannedFile,
        rules: list[tuple[str, str]]
    ) -> IgnoreDecision:
        """
        Evaluate a single file against all rules.

        Args:
            file_entry: The scanned file.
            rules:      List of (pattern, reason) tuples.

        Returns:
            An IgnoreDecision.
        """
        for pattern, reason in rules:
            if self._matches_pattern(file_entry.relative_path, file_entry.filename, pattern):
                return IgnoreDecision(
                    relative_path  = file_entry.relative_path,
                    ignored        = True,
                    rule           = pattern,
                    reason         = reason,
                    estimated_size = file_entry.size
                )

        # No match - file will be included
        return IgnoreDecision(
            relative_path  = file_entry.relative_path,
            ignored        = False,
            estimated_size = file_entry.size
        )

    def _matches_pattern(self, relative_path: str, filename: str, pattern: str) -> bool:
        """
        Check if a file matches an ignore pattern.

        Rules:
            - Pattern ending with '/' matches directory prefix.
              Example: 'node_modules/' matches 'node_modules/foo/bar.js'
            - Pattern with '*' uses fnmatch (glob).
              Example: '*.pyc' matches 'foo/bar.pyc'
            - Plain string matches exact filename.
              Example: '.DS_Store' matches any file named '.DS_Store'
        """
        # Directory prefix match
        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            # Check if any path segment matches the prefix
            path_parts = relative_path.split("/")
            return prefix in path_parts

        # Glob pattern match
        if "*" in pattern:
            # Match against filename OR full relative path
            return (
                fnmatch.fnmatch(filename, pattern)
                or fnmatch.fnmatch(relative_path, pattern)
            )

        # Exact filename match
        return filename == pattern
