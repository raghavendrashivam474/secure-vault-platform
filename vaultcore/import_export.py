"""
vaultcore/import_export.py

Import & Export Framework for the Secure Vault Platform.

Provides a common workflow for import and export operations.
Modules supply handlers. VaultCore manages the workflow.
"""

from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass

from vaultcore.logger import log_event, log_error
from vaultcore.event_bus import platform_bus, Events


@dataclass
class ImportHandler:
    """
    Represents a module-provided import handler.

    Attributes:
        module_id:    Owning module.
        file_types:   Supported file type filters.
        handler:      Callable(file_path) -> bool.
        description:  Human-readable description.
    """
    module_id:   str
    file_types:  list[tuple[str, str]]
    handler:     Callable
    description: str = ""


@dataclass
class ExportHandler:
    """
    Represents a module-provided export handler.

    Attributes:
        module_id:    Owning module.
        handler:      Callable(destination_folder) -> dict.
        description:  Human-readable description.
    """
    module_id:   str
    handler:     Callable
    description: str = ""


class ImportExportFramework:
    """
    Manages import and export workflows across modules.

    Modules register handlers.
    Framework coordinates file selection, validation,
    progress reporting, storage, and notifications.
    """

    def __init__(self) -> None:
        """Initialize the framework."""
        self._importers: dict[str, ImportHandler] = {}
        self._exporters: dict[str, ExportHandler] = {}

    def register_importer(self, importer: ImportHandler) -> None:
        """
        Register a module import handler.

        Args:
            importer: The ImportHandler to register.
        """
        self._importers[importer.module_id] = importer

    def register_exporter(self, exporter: ExportHandler) -> None:
        """
        Register a module export handler.

        Args:
            exporter: The ExportHandler to register.
        """
        self._exporters[exporter.module_id] = exporter

    def get_importer(self, module_id: str) -> Optional[ImportHandler]:
        """Return the import handler for a module."""
        return self._importers.get(module_id)

    def get_exporter(self, module_id: str) -> Optional[ExportHandler]:
        """Return the export handler for a module."""
        return self._exporters.get(module_id)

    def import_file(
        self,
        module_id: str,
        file_path: Path
    ) -> bool:
        """
        Execute an import operation through the registered handler.

        Args:
            module_id: The target module.
            file_path: The file to import.

        Returns:
            True if import succeeded.
        """
        importer = self._importers.get(module_id)

        if importer is None:
            log_error(f"[Import] No importer for {module_id}")
            return False

        try:
            result = importer.handler(file_path)
            if result:
                log_event("Imported", f"{module_id}: {file_path.name}")
                platform_bus.publish(Events.DOCUMENT_IMPORTED, {
                    "module_id": module_id,
                    "name":      file_path.name
                })
            return result
        except Exception as error:
            log_error(f"[Import] Failed: {error}")
            return False

    def export_to_folder(
        self,
        module_id: str,
        destination: Path
    ) -> dict:
        """
        Execute an export operation through the registered handler.

        Args:
            module_id:   The source module.
            destination: The export destination folder.

        Returns:
            A dictionary containing export statistics.
        """
        exporter = self._exporters.get(module_id)

        if exporter is None:
            log_error(f"[Export] No exporter for {module_id}")
            return {"success": False, "count": 0}

        try:
            result = exporter.handler(destination)
            log_event("Exported", f"{module_id} to {destination}")
            platform_bus.publish(Events.DOCUMENT_EXPORTED, {
                "module_id": module_id,
                "count":     result.get("count", 0)
            })
            return result
        except Exception as error:
            log_error(f"[Export] Failed: {error}")
            return {"success": False, "count": 0}

    def get_registered_modules(self) -> list[str]:
        """Return module IDs with registered handlers."""
        return list(set(list(self._importers.keys()) + list(self._exporters.keys())))
