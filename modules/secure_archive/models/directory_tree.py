"""
modules/secure_archive/models/directory_tree.py

Directory tree data models for archive hierarchy preservation.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TreeNode:
    """
    Represents a single node in the directory tree.

    Attributes:
        name:           Name of the file or directory.
        relative_path:  Path relative to tree root (forward slashes).
        is_directory:   True if this node is a directory.
        size:           File size in bytes (0 for directories).
        children:       Child nodes (only for directories).
    """
    name:          str
    relative_path: str
    is_directory:  bool
    size:          int                = 0
    children:      list["TreeNode"]   = field(default_factory=list)

    @property
    def child_count(self) -> int:
        """Return number of direct children."""
        return len(self.children)

    @property
    def is_empty_directory(self) -> bool:
        """True if this is a directory with no children."""
        return self.is_directory and len(self.children) == 0

    def get_all_files(self) -> list["TreeNode"]:
        """Recursively collect all file nodes."""
        files = []
        for child in self.children:
            if child.is_directory:
                files.extend(child.get_all_files())
            else:
                files.append(child)
        return files

    def get_all_directories(self) -> list["TreeNode"]:
        """Recursively collect all directory nodes (including empty)."""
        dirs = []
        for child in self.children:
            if child.is_directory:
                dirs.append(child)
                dirs.extend(child.get_all_directories())
        return dirs


@dataclass
class DirectoryTree:
    """
    Complete directory tree for an archive source.

    Attributes:
        root:            The root TreeNode.
        root_name:       Name of the root directory.
        root_path:       Absolute path of the scan source.
        total_files:     Count of all file nodes.
        total_dirs:      Count of all directory nodes.
        total_size:      Sum of all file sizes.
        empty_dirs:      Count of empty directories.
    """
    root:         TreeNode
    root_name:    str  = ""
    root_path:    str  = ""
    total_files:  int  = 0
    total_dirs:   int  = 0
    total_size:   int  = 0
    empty_dirs:   int  = 0

    def get_all_relative_paths(self) -> list[str]:
        """Return sorted list of all file relative paths."""
        return sorted(f.relative_path for f in self.root.get_all_files())

    def get_all_directory_paths(self) -> list[str]:
        """Return sorted list of all directory relative paths."""
        paths = [d.relative_path for d in self.root.get_all_directories()]
        return sorted(paths)
