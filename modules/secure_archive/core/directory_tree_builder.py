"""
modules/secure_archive/core/directory_tree_builder.py

Builds an in-memory directory tree from a filesystem path.

Preserves complete hierarchy including empty directories.
Deterministic ordering. Never modifies source files.
"""

import os
from pathlib import Path

from modules.secure_archive.models.directory_tree import (
    TreeNode, DirectoryTree
)
from vaultcore.logger import log_debug


class DirectoryTreeBuilder:
    """
    Scans a filesystem path and builds a DirectoryTree.

    The tree preserves the complete hierarchy with:
        - Nested directories
        - Empty directories
        - Files with sizes
        - Deterministic sorted ordering
    """

    def build(self, source_path: Path) -> DirectoryTree:
        """
        Build a directory tree from a filesystem path.

        Args:
            source_path: Absolute path to scan.

        Returns:
            A DirectoryTree representing the complete hierarchy.

        Raises:
            FileNotFoundError: If source path does not exist.
        """
        source_path = source_path.resolve()

        if not source_path.exists():
            raise FileNotFoundError(f"Source path not found: {source_path}")

        if source_path.is_file():
            return self._build_single_file(source_path)

        root_node = self._build_directory_node(
            source_path, source_path
        )

        # Calculate totals
        all_files = root_node.get_all_files()
        all_dirs  = root_node.get_all_directories()
        empty     = [d for d in all_dirs if d.is_empty_directory]

        tree = DirectoryTree(
            root        = root_node,
            root_name   = source_path.name,
            root_path   = str(source_path),
            total_files = len(all_files),
            total_dirs  = len(all_dirs),
            total_size  = sum(f.size for f in all_files),
            empty_dirs  = len(empty)
        )

        log_debug(
            f"[DirectoryTreeBuilder] Built tree: "
            f"{tree.total_files} files, {tree.total_dirs} dirs, "
            f"{tree.empty_dirs} empty"
        )

        return tree

    def _build_directory_node(
        self,
        dir_path: Path,
        root_path: Path
    ) -> TreeNode:
        """Build a TreeNode for a directory, recursing into children."""
        try:
            relative = str(dir_path.relative_to(root_path)).replace("\\", "/")
        except ValueError:
            relative = dir_path.name

        if relative == ".":
            relative = ""

        node = TreeNode(
            name          = dir_path.name,
            relative_path = relative,
            is_directory  = True,
            size          = 0
        )

        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except (PermissionError, OSError):
            return node

        for entry in entries:
            if entry.is_dir():
                child = self._build_directory_node(entry, root_path)
                node.children.append(child)
            elif entry.is_file():
                try:
                    file_size = entry.stat().st_size
                except (OSError, PermissionError):
                    file_size = 0

                try:
                    file_relative = str(entry.relative_to(root_path)).replace("\\", "/")
                except ValueError:
                    file_relative = entry.name

                file_node = TreeNode(
                    name          = entry.name,
                    relative_path = file_relative,
                    is_directory  = False,
                    size          = file_size
                )
                node.children.append(file_node)

        return node

    def _build_single_file(self, file_path: Path) -> DirectoryTree:
        """Build a tree for a single file."""
        try:
            file_size = file_path.stat().st_size
        except (OSError, PermissionError):
            file_size = 0

        file_node = TreeNode(
            name          = file_path.name,
            relative_path = file_path.name,
            is_directory  = False,
            size          = file_size
        )

        root_node = TreeNode(
            name          = file_path.parent.name,
            relative_path = "",
            is_directory  = True,
            children      = [file_node]
        )

        return DirectoryTree(
            root        = root_node,
            root_name   = file_path.parent.name,
            root_path   = str(file_path.parent),
            total_files = 1,
            total_dirs  = 0,
            total_size  = file_size,
            empty_dirs  = 0
        )
