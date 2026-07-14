"""
modules/secure_archive/models/project.py

Project type identification models.
"""

from dataclasses import dataclass, field
from typing import Optional


# Project type constants
PROJECT_PYTHON  = "python"
PROJECT_NODEJS  = "nodejs"
PROJECT_FLUTTER = "flutter"
PROJECT_RUST    = "rust"
PROJECT_GENERIC = "generic"

# Confidence levels
CONFIDENCE_HIGH   = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW    = "low"


PROJECT_LABELS = {
    PROJECT_PYTHON:  "Python",
    PROJECT_NODEJS:  "Node.js",
    PROJECT_FLUTTER: "Flutter",
    PROJECT_RUST:    "Rust",
    PROJECT_GENERIC: "Generic Folder",
}

PROJECT_ICONS = {
    PROJECT_PYTHON:  "🐍",
    PROJECT_NODEJS:  "📗",
    PROJECT_FLUTTER: "💙",
    PROJECT_RUST:    "🦀",
    PROJECT_GENERIC: "📁",
}


@dataclass
class ProjectProfile:
    """
    Represents the detected project type for a scan.

    Attributes:
        project_type: One of PROJECT_* constants.
        confidence:   CONFIDENCE_HIGH, MEDIUM, or LOW.
        markers:      List of marker files that triggered detection.
        root_path:    Absolute path to the scan root.
        label:        Human-readable project label.
        icon:         Display icon.
    """
    project_type: str
    confidence:   str
    markers:      list[str] = field(default_factory=list)
    root_path:    str       = ""
    label:        str       = ""
    icon:         str       = "📁"

    def __post_init__(self):
        if not self.label:
            self.label = PROJECT_LABELS.get(self.project_type, "Unknown")
        if self.icon == "📁" and self.project_type != PROJECT_GENERIC:
            self.icon = PROJECT_ICONS.get(self.project_type, "📁")
