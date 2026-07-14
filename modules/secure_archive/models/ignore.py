"""
modules/secure_archive/models/ignore.py

Ignore decision models for the ignore engine.
"""

from dataclasses import dataclass, field
from typing import Optional


# Ignore reason categories
REASON_PROJECT_ARTIFACT   = "project_artifact"   # node_modules, .venv, target
REASON_BUILD_OUTPUT       = "build_output"       # dist, build, .next
REASON_CACHE              = "cache"              # __pycache__, .cache
REASON_OS_ARTIFACT        = "os_artifact"        # .DS_Store, Thumbs.db
REASON_VCS                = "vcs"                # .git (optional)
REASON_TEMP               = "temp"               # *.tmp, ~files


@dataclass
class IgnoreDecision:
    """
    Represents a decision to ignore or include one file.

    Attributes:
        relative_path:  Path relative to scan root.
        ignored:        True if file should be excluded from archive.
        rule:           Pattern that matched (e.g. 'node_modules/').
        reason:         Category of ignore reason.
        estimated_size: Size in bytes for reporting.
    """
    relative_path:  str
    ignored:        bool
    rule:           Optional[str] = None
    reason:         Optional[str] = None
    estimated_size: int = 0


@dataclass
class IgnoreSummary:
    """
    Aggregated ignore statistics for a scan.

    Attributes:
        total_files:      All files scanned.
        ignored_files:    Files marked as ignored.
        included_files:   Files that will be archived.
        ignored_size:     Total size of ignored files (bytes).
        included_size:    Total size of included files (bytes).
        by_reason:        Ignored file count per reason category.
        by_rule:          Ignored file count per matching rule.
    """
    total_files:    int = 0
    ignored_files:  int = 0
    included_files: int = 0
    ignored_size:   int = 0
    included_size:  int = 0
    by_reason:      dict[str, int] = field(default_factory=dict)
    by_rule:        dict[str, int] = field(default_factory=dict)
