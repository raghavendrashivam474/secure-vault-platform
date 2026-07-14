"""
modules/secure_archive/ui/dashboard.py

Secure Archive dashboard - full functionality.

Provides Create Archive and Restore Archive workflows.
Orchestrates domain services. Never contains archive logic.
"""

import time
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog

from vaultcore.theme import Theme

from modules.secure_archive.core.input_scanner import InputScanner
from modules.secure_archive.core.project_detector import ProjectDetector
from modules.secure_archive.core.ignore_engine import IgnoreEngine
from modules.secure_archive.core.file_classifier import FileClassifier
from modules.secure_archive.core.compression_strategy import CompressionStrategyEngine
from modules.secure_archive.core.archive_planner import ArchivePlanner
from modules.secure_archive.core.package_writer import PackageWriter, DEV_PACKAGE_EXTENSION
from modules.secure_archive.core.package_reader import PackageReader
from modules.secure_archive.core.restore_engine import RestoreEngine
from modules.secure_archive.core.report_builder import ReportBuilder
from modules.secure_archive.core import events

from modules.secure_archive.ui.archive_plan_view import ArchivePlanView
from modules.secure_archive.ui.restore_view import (
    RestorePreviewDialog, RestoreReportDialog
)


class SecureArchiveDashboard(tk.Frame):
    """
    Full Secure Archive dashboard.

    Orchestrates the archive creation and restoration pipelines
    using domain services. No archive logic lives here.
    """

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        clipboard,
        dialogs,
        notifications,
        notification_center,
        activity_service,
        recent_items,
        storage_manager,
        on_close: Callable
    ) -> None:
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._master_password     = master_password
        self._clipboard           = clipboard
        self._dialogs             = dialogs
        self._notifications       = notifications
        self._notification_center = notification_center
        self._activity_service    = activity_service
        self._recent_items        = recent_items
        self._storage_manager     = storage_manager
        self._on_close            = on_close

        # Domain services (persistent instances)
        self._scanner    = InputScanner()
        self._detector   = ProjectDetector()
        self._ignore     = IgnoreEngine()
        self._classifier = FileClassifier()
        self._strategy   = CompressionStrategyEngine()
        self._planner    = ArchivePlanner()
        self._writer     = PackageWriter()
        self._restorer   = RestoreEngine()
        self._reporter   = ReportBuilder()

        self._build()

    def _build(self) -> None:
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=Theme.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📦",
            font=("Segoe UI", 22),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(20, 8), pady=12)

        tk.Label(
            header,
            text="Secure Archive",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", pady=12)

        tk.Label(
            header,
            text="v0.1.0",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=(8, 0), pady=(20, 0))

        # Body
        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(
            body,
            text="Intelligent Project Archiving",
            font=("Segoe UI", 18, "bold"),
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 4))

        tk.Label(
            body,
            text="Scans, analyzes, compresses, and verifies your projects.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(0, 40))

        # Action buttons row
        actions = tk.Frame(body, bg=Theme.BACKGROUND)
        actions.pack()

        self._make_action_button(
            actions, "📦  Create Archive",
            "Scan and compress a project or folder",
            self._handle_create_archive,
            column=0
        )

        self._make_action_button(
            actions, "🔄  Restore Archive",
            "Restore and verify an archive package",
            self._handle_restore_archive,
            column=1
        )

        # Info panel
        info = tk.Frame(body, bg=Theme.PANEL, padx=24, pady=20)
        info.pack(fill="x", pady=(60, 0))

        tk.Label(
            info,
            text="Sprint 14 Foundation",
            font=Theme.FONT_LABEL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        tk.Label(
            info,
            text="Development Format",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(anchor="w", pady=(4, 8))

        tk.Label(
            info,
            text=(
                "Archives use the .sva.dev format for validation and testing.\n"
                "The encrypted .sva format will be introduced in a future sprint.\n"
                "All files use SHA-256 checksum verification on restore."
            ),
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            justify="left"
        ).pack(anchor="w")

    def _make_action_button(
        self, parent, text, subtitle, command, column
    ) -> None:
        card = tk.Frame(parent, bg=Theme.PANEL, padx=32, pady=24)
        card.grid(row=0, column=column, padx=16, pady=8, sticky="nsew")

        tk.Button(
            card, text=text,
            font=Theme.FONT_HEADING,
            bg=Theme.HIGHLIGHT, fg="#ffffff",
            relief="flat",
            padx=24, pady=12,
            cursor="hand2",
            width=20,
            command=command
        ).pack()

        tk.Label(
            card, text=subtitle,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL, fg=Theme.SUBTLE
        ).pack(pady=(8, 0))

    # ── Create Archive Flow ───────────────────────────────────────────────────

    def _handle_create_archive(self) -> None:
        """Full create-archive workflow."""
        # Step 1: Choose source
        source_str = filedialog.askdirectory(
            title  = "Select folder to archive",
            parent = self
        )
        if not source_str:
            return

        source_path = Path(source_str)

        # Step 2: Analyze
        self._notifications.info("Analyzing project...")
        self.update()

        try:
            plan = self._analyze(source_path)
        except Exception as error:
            self._notifications.error(f"Analysis failed: {error}")
            events.publish_creation_failed(source_path.name, str(error))
            return

        # Step 3: Publish analysis event
        events.publish_analysis_completed(
            archive_name   = plan.archive_name,
            project_type   = plan.project_profile.project_type,
            files_included = plan.file_count,
            files_ignored  = plan.ignored_count
        )

        # Step 4: Show preview
        ArchivePlanView(
            parent     = self,
            plan       = plan,
            on_confirm = lambda: self._execute_archive(plan)
        )

    def _analyze(self, source_path: Path):
        """Run analysis pipeline and build ArchivePlan."""
        result = self._scanner.scan(source_path)
        profile = self._detector.detect(result)
        ignore_dec, ignore_sum = self._ignore.evaluate(result, profile)
        included = [f for f, d in zip(result.files, ignore_dec) if not d.ignored]
        classifications = self._classifier.classify_all(included)
        comp_decisions = self._strategy.decide_all(classifications)
        return self._planner.build(
            result, profile, ignore_dec, ignore_sum,
            classifications, comp_decisions
        )

    def _execute_archive(self, plan) -> None:
        """Execute the confirmed archive plan."""
        # Choose output location
        output_str = filedialog.asksaveasfilename(
            title            = "Save archive package",
            defaultextension = DEV_PACKAGE_EXTENSION,
            initialfile      = f"{plan.archive_name}{DEV_PACKAGE_EXTENSION}",
            filetypes        = [("Secure Archive Dev", "*.sva.dev"), ("All Files", "*.*")],
            parent           = self
        )
        if not output_str:
            return

        output_path = Path(output_str)

        # Publish start event
        events.publish_creation_started(
            archive_name = plan.archive_name,
            project_type = plan.project_profile.project_type,
            file_count   = plan.file_count
        )

        # Execute
        self._notifications.info(f"Creating archive: {plan.file_count} files...")
        self.update()

        start = time.time()
        try:
            manifest, run_result = self._writer.write(plan, output_path)
        except Exception as error:
            self._notifications.error(f"Archive creation failed: {error}")
            events.publish_creation_failed(plan.archive_name, str(error))
            return

        total_duration = time.time() - start

        # Build report
        report = self._reporter.build(
            plan, manifest, run_result, output_path, total_duration
        )

        # Publish created event
        events.publish_created(report)

        # Activity tracking
        self._activity_service.record(
            "ArchiveCreated", "secure_archive",
            f"{plan.archive_name}: {plan.file_count} files, {report.compression_ratio:.1f}% saved"
        )

        # Notify
        self._notifications.success(
            f"Archive created: {report.formatted_size(report.compressed_size)} "
            f"({report.compression_ratio:.1f}% saved)"
        )

        self._dialogs.info(
            "Archive Complete",
            f"Archive: {report.archive_name}\n\n"
            f"Files:         {report.files_included}\n"
            f"Original:      {report.formatted_size(report.original_size)}\n"
            f"Compressed:    {report.formatted_size(report.compressed_size)}\n"
            f"Saved:         {report.compression_ratio:.1f}%\n"
            f"Duration:      {report.duration:.2f}s\n\n"
            f"Location:\n{output_path}"
        )

    # ── Restore Archive Flow ──────────────────────────────────────────────────

    def _handle_restore_archive(self) -> None:
        """Full restore-archive workflow."""
        # Step 1: Choose package
        package_str = filedialog.askopenfilename(
            title     = "Select archive package to restore",
            filetypes = [("Secure Archive Dev", "*.sva.dev"), ("All Files", "*.*")],
            parent    = self
        )
        if not package_str:
            return

        package_path = Path(package_str)

        # Step 2: Choose destination
        dest_str = filedialog.askdirectory(
            title  = "Choose restore destination folder",
            parent = self
        )
        if not dest_str:
            return

        destination = Path(dest_str)

        # Step 3: Read manifest
        try:
            with PackageReader(package_path) as reader:
                manifest = reader.read_manifest()
        except (FileNotFoundError, ValueError) as error:
            self._notifications.error(f"Cannot read package: {error}")
            events.publish_restore_failed(package_path.name, str(error))
            return

        # Step 4: Preview
        RestorePreviewDialog(
            parent      = self,
            manifest    = manifest,
            destination = str(destination),
            on_confirm  = lambda: self._execute_restore(package_path, destination, manifest)
        )

    def _execute_restore(self, package_path: Path, destination: Path, manifest) -> None:
        """Execute the confirmed restore."""
        events.publish_restore_started(
            archive_name = manifest.archive_name,
            file_count   = manifest.file_count
        )

        self._notifications.info(f"Restoring {manifest.file_count} files...")
        self.update()

        try:
            report = self._restorer.restore(package_path, destination)
        except Exception as error:
            self._notifications.error(f"Restore failed: {error}")
            events.publish_restore_failed(manifest.archive_name, str(error))
            return

        # Publish events
        events.publish_restored(report)
        if report.integrity_failures > 0:
            events.publish_integrity_failed(
                archive_name = manifest.archive_name,
                failures     = report.integrity_failures
            )

        # Activity
        self._activity_service.record(
            "ArchiveRestored", "secure_archive",
            f"{report.archive_name}: {report.files_verified}/{report.files_expected}"
        )

        # Notify
        if report.success:
            self._notifications.success(
                f"Restored {report.files_verified}/{report.files_expected} files (all verified)"
            )
        else:
            self._notifications.warning(
                f"Restore complete with {report.integrity_failures} integrity failures"
            )

        # Show report
        RestoreReportDialog(parent=self, report=report)
