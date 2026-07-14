"""
modules/secure_archive/core/path_validator.py

Path safety validator for archive restoration.

Prevents path traversal attacks and unsafe restoration.
All restored files must remain within the destination root.

Rejects:
    - Parent traversal:  ../file.txt
    - Absolute paths:    /etc/file, C:/Windows/file
    - Drive letters:     D:file.txt
    - UNC paths:         forward-slash-server-share
    - Null bytes:        file\x00.txt
"""

import os
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Optional
from dataclasses import dataclass

from vaultcore.logger import log_error


@dataclass
class PathValidationResult:
    """
    Result of validating a restore path.

    Attributes:
        is_safe:         True if path is safe to write.
        resolved_path:   The final absolute Path (if safe).
        rejection_reason: Why rejected (if not safe).
    """
    is_safe:          bool
    resolved_path:    Optional[Path] = None
    rejection_reason: Optional[str]  = None


class PathValidator:
    """
    Validates that a relative path from a manifest is safe
    to restore inside a destination directory.
    """

    def validate(
        self,
        relative_path: str,
        destination_root: Path
    ) -> PathValidationResult:
        """
        Validate a manifest-relative path.

        Args:
            relative_path:    Path string from manifest.
            destination_root: Root directory for restoration.

        Returns:
            PathValidationResult indicating safety.
        """
        # Check for null bytes
        if "\x00" in relative_path:
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = "Path contains null byte"
            )

        # Check for empty path
        if not relative_path.strip():
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = "Path is empty"
            )

        # Reject absolute paths (Unix style)
        if relative_path.startswith("/") or relative_path.startswith("\\"):
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = f"Absolute path not allowed: {relative_path}"
            )

        # Reject UNC paths
        if relative_path.startswith("\\\\") or relative_path.startswith("//"):
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = f"UNC path not allowed: {relative_path}"
            )

        # Reject drive letters (Windows)
        if len(relative_path) >= 2 and relative_path[1] == ":":
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = f"Drive letter not allowed: {relative_path}"
            )

        # Reject parent traversal explicitly
        # Split on both slash styles
        parts = relative_path.replace("\\", "/").split("/")
        for part in parts:
            if part == "..":
                return PathValidationResult(
                    is_safe          = False,
                    rejection_reason = f"Parent traversal not allowed: {relative_path}"
                )

        # Resolve the intended path
        try:
            destination_root = destination_root.resolve()
            candidate_path   = (destination_root / relative_path).resolve()
        except (OSError, ValueError) as error:
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = f"Path resolution failed: {error}"
            )

        # Verify containment
        try:
            candidate_path.relative_to(destination_root)
        except ValueError:
            return PathValidationResult(
                is_safe          = False,
                rejection_reason = f"Path escapes destination: {relative_path}"
            )

        return PathValidationResult(
            is_safe       = True,
            resolved_path = candidate_path
        )


