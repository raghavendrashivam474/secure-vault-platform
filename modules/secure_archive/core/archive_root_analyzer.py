"""
modules/secure_archive/core/archive_root_analyzer.py

Determines the archive root for proper restoration hierarchy.

If user archives 'Temp_Workspace/', the archive root is 'Temp_Workspace'.
Restoration should recreate 'Temp_Workspace/' as a subdirectory.
"""

from pathlib import Path
from dataclasses import dataclass

from modules.secure_archive.models.directory_tree import DirectoryTree


@dataclass
class ArchiveRootInfo:
    """
    Archive root metadata.

    Attributes:
        archive_root:     Name of the root folder being archived.
        original_path:    Full original absolute path (metadata only).
        root_is_folder:   True if root is a folder (vs single file).
        directory_count:  Total directories in the tree.
        file_count:       Total files in the tree.
        empty_dir_count:  Empty directories to preserve.
        directory_paths:  All relative directory paths.
    """
    archive_root:     str
    original_path:    str
    root_is_folder:   bool
    directory_count:  int
    file_count:       int
    empty_dir_count:  int
    directory_paths:  list[str]


class ArchiveRootAnalyzer:
    """
    Analyzes a DirectoryTree to determine archive root metadata.

    This metadata is stored in the manifest for intelligent restoration.
    The original_path is stored as metadata only — never trusted
    automatically during restoration.
    """

    def analyze(self, tree: DirectoryTree) -> ArchiveRootInfo:
        """
        Analyze a directory tree and extract root metadata.

        Args:
            tree: The DirectoryTree from DirectoryTreeBuilder.

        Returns:
            An ArchiveRootInfo with root metadata.
        """
        return ArchiveRootInfo(
            archive_root    = tree.root_name,
            original_path   = tree.root_path,
            root_is_folder  = tree.root.is_directory,
            directory_count = tree.total_dirs,
            file_count      = tree.total_files,
            empty_dir_count = tree.empty_dirs,
            directory_paths = tree.get_all_directory_paths()
        )
