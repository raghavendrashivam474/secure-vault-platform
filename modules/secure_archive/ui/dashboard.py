"""
modules/secure_archive/ui/dashboard.py

Secure Archive dashboard - Sprint 15 integrated.

Now supports both .sva (encrypted, default) and .sva.dev (development).
Users interact primarily with .sva. The .sva.dev format remains
available for debugging.
"""

import time
from pathlib import Path
from typing import Callable, Optional

import tkinter as tk
from tkinter import filedialog, simpledialog

from vaultcore.theme import Theme

# Sprint 14 pipeline
from modules.secure_archive.core.input_scanner import InputScanner
from modules.secure_archive.core.project_detector import ProjectDetector
from modules.secure_archive.core.ignore_engine import IgnoreEngine
from modules.secure_archive.core.file_classifier import FileClassifier
from modules.secure_archive.core.compression_strategy import CompressionStrategyEngine
from modules.secure_archive.core.archive_planner import ArchivePlanner
from modules.secure_archive.core.package_writer import PackageWriter, DEV_PACKAGE_EXTENSION
from modules.secure_archive.core.package_reader import PackageReader
from modules.secure_archive.core.compression_engine import CompressionEngine
from modules.secure_archive.core.manifest_builder import ManifestBuilder
from modules.secure_archive.core.restore_engine import RestoreEngine
from modules.secure_archive.core.report_builder import ReportBuilder
from modules.secure_archive.core import events

# Sprint 15 encryption
from modules.secure_archive.core.archive_payload import ArchivePayloadBuilder
from modules.secure_archive.core.sva_writer import SVAWriter, SVA_EXTENSION
from modules.secure_archive.core.sva_reader import SVAReader
from modules.secure_archive.core.sva_restore import SVARestoreOrchestrator
from modules.secure_archive.core.error_mapper import ArchiveErrorMapper

from modules.secure_archive.ui.archive_plan_view import ArchivePlanView
from modules.secure_archive.ui.restore_view import (
    RestorePreviewDialog, RestoreReportDialog
)


class SecureArchiveDashboard(tk.Frame):
    """
    Secure Archive dashboard with encrypted .sva support.

    Primary workflows:
        - Create Secure Archive (.sva, encrypted)
        - Restore Secure Archive (.sva)

    Development workflows still available:
        - Create Development Archive (.sva.dev, unencrypted)
        - Restore Development Archive
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

        # Domain services
        self._scanner      = InputScanner()
        self._detector     = ProjectDetector()
        self._ignore       = IgnoreEngine()
        self._classifier   = FileClassifier()
        self._strategy     = CompressionStrategyEngine()
        self._planner      = ArchivePlanner()
        self._compressor   = CompressionEngine()
        self._mbuilder     = ManifestBuilder()
        self._pbuilder     = ArchivePayloadBuilder()
        self._writer_dev   = PackageWriter()
        self._writer_sva   = SVAWriter()
        self._reader_sva   = SVAReader()
        self._restorer_dev = RestoreEngine()
        self._restorer_sva = SVARestoreOrchestrator()
        self._reporter     = ReportBuilder()
        self._error_mapper = ArchiveErrorMapper()

        self._build()

    def _build(self) -> None:
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=Theme.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="📦", font=("Segoe UI", 22),
            bg=Theme.PANEL, fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(20, 8), pady=12)

        tk.Label(
            header, text="Secure Archive",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL, fg=Theme.TEXT
        ).pack(side="left", pady=12)

        tk.Label(
            header, text="v0.2.0", font=Theme.FONT_SMALL,
            bg=Theme.PANEL, fg=Theme.SUBTLE
        ).pack(side="left", padx=(8, 0), pady=(20, 0))

        # Body
        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(
            body, text="Intelligent Project Archiving",
            font=("Segoe UI", 18, "bold"),
            bg=Theme.BACKGROUND, fg=Theme.TEXT
        ).pack(pady=(20, 4))

        tk.Label(
            body,
            text="Encrypted archives with SHA-256 verified restoration.",
            font=Theme.FONT_BODY,
            bg=Theme.BACKGROUND, fg=Theme.SUBTLE
        ).pack(pady=(0, 30))

        # Primary actions (encrypted .sva)
        primary_frame = tk.Frame(body, bg=Theme.BACKGROUND)
        primary_frame.pack(pady=(0, 20))

        self._make_action_button(
            primary_frame, "🔒  Create Archive",
            "Encrypted .sva archive",
            self._handle_create_secure,
            column=0, primary=True
        )
        self._make_action_button(
            primary_frame, "🔑  Restore Archive",
            "Restore encrypted .sva",
            self._handle_restore_secure,
            column=1, primary=True
        )

        # Secondary actions (unencrypted development)
        tk.Label(
            body, text="Development Format (Unencrypted)",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND, fg=Theme.SUBTLE
        ).pack(pady=(20, 10))

        secondary_frame = tk.Frame(body, bg=Theme.BACKGROUND)
        secondary_frame.pack()

        self._make_action_button(
            secondary_frame, "📦  Dev Archive",
            ".sva.dev (unencrypted)",
            self._handle_create_dev,
            column=0, primary=False
        )
        self._make_action_button(
            secondary_frame, "🔄  Dev Restore",
            "Restore .sva.dev",
            self._handle_restore_dev,
            column=1, primary=False
        )

        # Info panel
        info = tk.Frame(body, bg=Theme.PANEL, padx=20, pady=14)
        info.pack(fill="x", pady=(30, 0))

        tk.Label(
            info, text="Format Overview",
            font=Theme.FONT_LABEL,
            bg=Theme.PANEL, fg=Theme.SUBTLE
        ).pack(anchor="w")

        info_text = (
            ".sva      → Encrypted (AES-256-GCM), password-protected, production format\n"
            ".sva.dev  → Unencrypted development format for debugging and testing\n"
            "All restorations verify every file with SHA-256 checksums."
        )
        tk.Label(
            info, text=info_text,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL, fg=Theme.SUBTLE,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

    def _make_action_button(
        self, parent, text, subtitle, command,
        column, primary=True
    ) -> None:
        card = tk.Frame(parent, bg=Theme.PANEL, padx=28, pady=20)
        card.grid(row=0, column=column, padx=12, pady=6, sticky="nsew")

        bg = Theme.HIGHLIGHT if primary else Theme.ACCENT

        tk.Button(
            card, text=text,
            font=Theme.FONT_SUBHEADING if primary else Theme.FONT_BODY,
            bg=bg, fg="#ffffff",
            relief="flat",
            padx=20, pady=10,
            cursor="hand2",
            width=20,
            command=command
        ).pack()

        tk.Label(
            card, text=subtitle, font=Theme.FONT_SMALL,
            bg=Theme.PANEL, fg=Theme.SUBTLE
        ).pack(pady=(6, 0))

    # ── SECURE (.sva) WORKFLOWS ───────────────────────────────────────────────

    def _handle_create_secure(self) -> None:
        """Create encrypted .sva archive."""
        source_str = filedialog.askdirectory(
            title="Select folder to archive",
            parent=self
        )
        if not source_str:
            return

        source_path = Path(source_str)

        self._notifications.info("Analyzing project...")
        self.update()

        try:
            plan = self._analyze(source_path)
        except Exception as error:
            self._notifications.error(f"Analysis failed: {error}")
            return

        events.publish_analysis_completed(
            archive_name=plan.archive_name,
            project_type=plan.project_profile.project_type,
            files_included=plan.file_count,
            files_ignored=plan.ignored_count
        )

        # Show plan preview
        ArchivePlanView(
            parent=self,
            plan=plan,
            on_confirm=lambda: self._prompt_and_encrypt(plan)
        )

    def _prompt_and_encrypt(self, plan) -> None:
        """After plan confirmation, get password and encrypt."""
        # Get password
        password = simpledialog.askstring(
            "Archive Password",
            "Set a password for this archive:\n"
            "(Required to restore later)",
            show="●",
            parent=self
        )
        if not password:
            self._notifications.warning("Archive creation cancelled")
            return

        # Confirm password
        confirm = simpledialog.askstring(
            "Confirm Password",
            "Re-enter password to confirm:",
            show="●",
            parent=self
        )
        if password != confirm:
            self._dialogs.error(
                "Password Mismatch",
                "Passwords do not match. Please try again."
            )
            return

        # Choose output location
        output_str = filedialog.asksaveasfilename(
            title="Save encrypted archive",
            defaultextension=SVA_EXTENSION,
            initialfile=f"{plan.archive_name}{SVA_EXTENSION}",
            filetypes=[("Secure Vault Archive", "*.sva"), ("All Files", "*.*")],
            parent=self
        )
        if not output_str:
            return

        output_path = Path(output_str)
        self._execute_secure_creation(plan, password, output_path)

    def _execute_secure_creation(self, plan, password: str, output_path: Path) -> None:
        """Execute the full encrypted archive creation."""
        events.publish_creation_started(
            archive_name=plan.archive_name,
            project_type=plan.project_profile.project_type,
            file_count=plan.file_count
        )
        events.publish_encryption_started(
            archive_name=plan.archive_name,
            file_count=plan.file_count
        )

        self._notifications.info(
            f"Creating encrypted archive: {plan.file_count} files..."
        )
        self.update()

        start = time.time()

        try:
            # Sprint 14 pipeline (in memory)
            import io
            buffers = {}
            def make_writer(path):
                buf = io.BytesIO()
                buffers[path] = buf
                return buf.write

            run_result = self._compressor.execute_plan(plan, make_writer)
            manifest = self._mbuilder.build(plan, run_result)
            compressed_entries = {p: b.getvalue() for p, b in buffers.items()}
            payload = self._pbuilder.build(manifest, compressed_entries)

            # Sprint 15 encryption
            sva_result = self._writer_sva.write(
                payload=payload,
                password=password,
                output_path=output_path
            )
        except Exception as error:
            self._notifications.error(f"Archive creation failed: {error}")
            events.publish_creation_failed(plan.archive_name, str(error))
            return

        duration = time.time() - start

        # Build report using existing reporter
        report = self._reporter.build(
            plan, manifest, run_result, output_path, duration
        )

        events.publish_encryption_completed(
            archive_name=plan.archive_name,
            file_size=sva_result.file_size
        )
        events.publish_created(report)

        self._activity_service.record(
            "SecureArchiveCreated", "secure_archive",
            f"{plan.archive_name}: {plan.file_count} files, encrypted"
        )

        self._notifications.success(
            f"Encrypted archive: {report.formatted_size(sva_result.file_size)}"
        )

        self._dialogs.info(
            "Encrypted Archive Created",
            f"Archive: {report.archive_name}\n"
            f"Files:      {report.files_included}\n"
            f"Original:   {report.formatted_size(report.original_size)}\n"
            f"Compressed: {report.formatted_size(report.compressed_size)}\n"
            f"Encrypted:  {report.formatted_size(sva_result.file_size)}\n"
            f"Duration:   {duration:.2f}s\n\n"
            f"Encryption: AES-256-GCM\n"
            f"KDF:        PBKDF2 (600,000 iterations)\n\n"
            f"Location:\n{output_path}"
        )

    def _handle_restore_secure(self) -> None:
        """Restore encrypted .sva archive."""
        sva_str = filedialog.askopenfilename(
            title="Select encrypted archive to restore",
            filetypes=[("Secure Vault Archive", "*.sva"), ("All Files", "*.*")],
            parent=self
        )
        if not sva_str:
            return

        sva_path = Path(sva_str)

        # Peek metadata first
        header = self._reader_sva.peek_metadata(sva_path)
        if header is None:
            self._dialogs.error(
                "Invalid Archive",
                "This file is not a valid Secure Vault Archive."
            )
            return

        # Get password
        password = simpledialog.askstring(
            "Archive Password",
            f"Enter password for:\n{sva_path.name}",
            show="●",
            parent=self
        )
        if not password:
            self._notifications.warning("Restore cancelled")
            return

        # Choose destination
        dest_str = filedialog.askdirectory(
            title="Choose restore destination",
            parent=self
        )
        if not dest_str:
            return

        destination = Path(dest_str)
        self._execute_secure_restore(sva_path, password, destination)

    def _execute_secure_restore(
        self, sva_path: Path, password: str, destination: Path
    ) -> None:
        """Execute the full encrypted archive restoration."""
        events.publish_restore_started(sva_path.name, 0)
        events.publish_decryption_started(sva_path.name)

        self._notifications.info("Decrypting and restoring...")
        self.update()

        result = self._restorer_sva.restore(
            sva_path=sva_path,
            password=password,
            destination_root=destination
        )

        if not result.success:
            # Map error to user-friendly info
            error_info = self._error_mapper.map(
                result.error_type or "unknown",
                result.error_message or ""
            )

            # Publish appropriate event
            if result.error_type == "authentication_failed":
                events.publish_authentication_failed(sva_path.name)
            else:
                events.publish_restore_failed(sva_path.name, result.error_message or "")

            self._notifications.error(error_info.title)
            self._dialogs.error(error_info.title, error_info.message)

            self._activity_service.record(
                "SecureArchiveRestoreFailed",
                "secure_archive",
                f"{sva_path.name}: {error_info.category}"
            )
            return

        # Success
        report = result.report

        events.publish_decryption_completed(
            archive_name=sva_path.name,
            files_restored=report.files_verified
        )
        events.publish_restored(report)

        if report.integrity_failures > 0:
            events.publish_integrity_failed(
                archive_name=sva_path.name,
                failures=report.integrity_failures
            )

        self._activity_service.record(
            "SecureArchiveRestored", "secure_archive",
            f"{report.archive_name}: {report.files_verified}/{report.files_expected} verified"
        )

        self._notifications.success(
            f"Restored {report.files_verified}/{report.files_expected} files"
        )

        RestoreReportDialog(parent=self, report=report)

    # ── DEVELOPMENT (.sva.dev) WORKFLOWS ──────────────────────────────────────

    def _handle_create_dev(self) -> None:
        """Create unencrypted development archive (Sprint 14 flow)."""
        source_str = filedialog.askdirectory(
            title="Select folder to archive",
            parent=self
        )
        if not source_str:
            return

        source_path = Path(source_str)

        self._notifications.info("Analyzing project...")
        self.update()

        try:
            plan = self._analyze(source_path)
        except Exception as error:
            self._notifications.error(f"Analysis failed: {error}")
            return

        ArchivePlanView(
            parent=self,
            plan=plan,
            on_confirm=lambda: self._execute_dev_creation(plan)
        )

    def _execute_dev_creation(self, plan) -> None:
        """Create unencrypted development archive."""
        output_str = filedialog.asksaveasfilename(
            title="Save development archive",
            defaultextension=DEV_PACKAGE_EXTENSION,
            initialfile=f"{plan.archive_name}{DEV_PACKAGE_EXTENSION}",
            filetypes=[("Development Archive", "*.sva.dev"), ("All Files", "*.*")],
            parent=self
        )
        if not output_str:
            return

        output_path = Path(output_str)

        start = time.time()
        try:
            manifest, run = self._writer_dev.write(plan, output_path)
        except Exception as error:
            self._notifications.error(f"Archive creation failed: {error}")
            return

        duration = time.time() - start
        report = self._reporter.build(plan, manifest, run, output_path, duration)

        self._notifications.success(
            f"Development archive: {report.formatted_size(report.compressed_size)}"
        )

    def _handle_restore_dev(self) -> None:
        """Restore unencrypted development archive."""
        package_str = filedialog.askopenfilename(
            title="Select development archive",
            filetypes=[("Development Archive", "*.sva.dev"), ("All Files", "*.*")],
            parent=self
        )
        if not package_str:
            return

        package_path = Path(package_str)

        try:
            with PackageReader(package_path) as reader:
                manifest = reader.read_manifest()
        except Exception as error:
            self._notifications.error(f"Cannot read package: {error}")
            return

        dest_str = filedialog.askdirectory(
            title="Choose restore destination",
            parent=self
        )
        if not dest_str:
            return

        destination = Path(dest_str)

        RestorePreviewDialog(
            parent=self,
            manifest=manifest,
            destination=str(destination),
            on_confirm=lambda: self._execute_dev_restore(package_path, destination, manifest)
        )

    def _execute_dev_restore(self, package_path, destination, manifest) -> None:
        """Execute unencrypted restoration."""
        self._notifications.info(f"Restoring {manifest.file_count} files...")
        self.update()

        try:
            report = self._restorer_dev.restore(package_path, destination)
        except Exception as error:
            self._notifications.error(f"Restore failed: {error}")
            return

        self._notifications.success(
            f"Restored {report.files_verified}/{report.files_expected} files"
        )
        RestoreReportDialog(parent=self, report=report)

    # ── SHARED HELPERS ────────────────────────────────────────────────────────

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
