"""
ui/settings.py

Settings screen for the Personal Document Vault.
Provides vault statistics, backup management,
auto-lock configuration, and password change.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from pathlib import Path
from typing import Callable, Optional

from vaultcore.backup import (
    create_backup,
    restore_backup,
    verify_backup,
    list_backups,
    get_vault_size,
    get_backup_count,
    get_latest_backup_date,
    BACKUP_FOLDER
)
from vaultcore.database import (
    get_vault_statistics,
    save_setting,
    load_setting
)
from vaultcore.authentication import verify_master_password, create_vault
from modules.document_vault.core.vault import AUTO_LOCK_OPTIONS
from vaultcore.hashing import generate_salt, hash_password
from vaultcore.database import save_vault_settings


COLOUR_BACKGROUND = "#1a1a2e"
COLOUR_PANEL      = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_ENTRY_BG   = "#0d1b2a"
COLOUR_SUCCESS    = "#51cf66"
COLOUR_ERROR      = "#ff6b6b"


class SettingsScreen(tk.Frame):
    """
    Full settings screen with sections for vault info,
    backup management, security, and auto-lock.
    """

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        on_close: Callable,
        on_lock: Callable,
        vault_state
    ) -> None:
        """
        Initialize the settings screen.

        Args:
            parent:          The parent widget.
            master_password: The current session master password.
            on_close:        Callback to return to dashboard.
            on_lock:         Callback to lock the vault.
            vault_state:     The shared VaultState object.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._master_password = master_password
        self._on_close        = on_close
        self._on_lock         = on_lock
        self._vault_state     = vault_state
        self._build()

    def _build(self) -> None:
        """Construct the full settings layout."""
        self.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(self, bg=COLOUR_PANEL, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="←  Back",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_close
        ).pack(side="left", padx=16, pady=10)

        tk.Label(
            header,
            text="⚙  Settings & Vault Management",
            font=("Segoe UI", 13, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).pack(side="left", padx=8)

        # Scrollable body
        canvas = tk.Canvas(self, bg=COLOUR_BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=COLOUR_BACKGROUND)
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        # Two column layout
        left  = tk.Frame(body, bg=COLOUR_BACKGROUND)
        right = tk.Frame(body, bg=COLOUR_BACKGROUND)
        left.pack(side="left", fill="both", expand=True, padx=(24, 12), pady=24)
        right.pack(side="left", fill="both", expand=True, padx=(12, 24), pady=24)

        self._build_vault_info(left)
        self._build_backup_section(left)
        self._build_security_section(right)
        self._build_autolock_section(right)
        self._build_restore_section(right)
        self._build_health_section(right)

    # ── Section builders ──────────────────────────────────────────────────────

    def _build_vault_info(self, parent: tk.Widget) -> None:
        """Build the vault information panel."""
        panel = self._section_panel(parent, "📊  Vault Information")

        stats      = get_vault_statistics()
        vault_size = get_vault_size()
        bk_count   = get_backup_count()
        bk_date    = get_latest_backup_date() or "Never"

        def fmt_size(b: int) -> str:
            if b < 1024:
                return f"{b} B"
            elif b < 1024 ** 2:
                return f"{b/1024:.1f} KB"
            else:
                return f"{b/(1024**2):.1f} MB"

        rows = [
            ("Documents",        str(stats["document_count"])),
            ("Categories",       str(stats["category_count"])),
            ("Favorites",        str(stats["favorite_count"])),
            ("Vault Created",    stats["created_at"]),
            ("Last Opened",      stats["last_opened"]),
            ("Encrypted Size",   fmt_size(vault_size)),
            ("Backups",          str(bk_count)),
            ("Latest Backup",    bk_date),
            ("Encryption",       "AES-256-GCM"),
            ("Vault Version",    "1.0"),
        ]

        for label, value in rows:
            self._info_row(panel, label, value)

    def _build_backup_section(self, parent: tk.Widget) -> None:
        """Build the backup creation panel."""
        panel = self._section_panel(parent, "💾  Backup")

        self._backup_status = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUCCESS,
            wraplength=340
        )
        self._backup_status.pack(anchor="w", pady=(0, 8))

        tk.Button(
            panel,
            text="Create Backup Now",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._handle_create_backup
        ).pack(fill="x", pady=(0, 8))

        tk.Button(
            panel,
            text="Choose Backup Folder",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._handle_choose_backup_folder
        ).pack(fill="x", pady=(0, 8))

        # Auto-backup frequency
        tk.Label(
            panel,
            text="Auto-Backup Frequency",
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", pady=(8, 4))

        self._backup_freq_var = tk.StringVar(
            value=load_setting("backup_frequency", "Never")
        )
        for option in ["Never", "Daily", "Weekly", "Monthly"]:
            tk.Radiobutton(
                panel,
                text=option,
                variable=self._backup_freq_var,
                value=option,
                font=("Segoe UI", 10),
                bg=COLOUR_PANEL,
                fg=COLOUR_TEXT,
                activebackground=COLOUR_PANEL,
                selectcolor=COLOUR_ACCENT,
                command=self._save_backup_frequency
            ).pack(anchor="w")

        # List recent backups
        tk.Label(
            panel,
            text="Recent Backups",
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", pady=(12, 4))

        backups = list_backups()
        if backups:
            for bk in backups[:5]:
                tk.Label(
                    panel,
                    text=f"📦  {bk.name}",
                    font=("Segoe UI", 9),
                    bg=COLOUR_PANEL,
                    fg=COLOUR_TEXT,
                    anchor="w"
                ).pack(fill="x")
        else:
            tk.Label(
                panel,
                text="No backups found.",
                font=("Segoe UI", 9),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUBTLE
            ).pack(anchor="w")

    def _build_security_section(self, parent: tk.Widget) -> None:
        """Build the password change panel."""
        panel = self._section_panel(parent, "🔐  Security")

        self._pw_status = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUCCESS,
            wraplength=340
        )
        self._pw_status.pack(anchor="w", pady=(0, 8))

        for label_text, attr in [
            ("Current Password",  "_entry_current"),
            ("New Password",      "_entry_new"),
            ("Confirm Password",  "_entry_confirm"),
        ]:
            tk.Label(
                panel,
                text=label_text,
                font=("Segoe UI", 9, "bold"),
                bg=COLOUR_PANEL,
                fg=COLOUR_SUBTLE
            ).pack(anchor="w", pady=(6, 2))

            entry = tk.Entry(
                panel,
                show="●",
                font=("Segoe UI", 10),
                bg=COLOUR_ENTRY_BG,
                fg=COLOUR_TEXT,
                insertbackground=COLOUR_TEXT,
                relief="flat",
                bd=6
            )
            entry.pack(fill="x", ipady=4)
            setattr(self, attr, entry)

        tk.Button(
            panel,
            text="Change Master Password",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._handle_change_password
        ).pack(fill="x", pady=(12, 0))

    def _build_autolock_section(self, parent: tk.Widget) -> None:
        """Build the auto-lock configuration panel."""
        panel = self._section_panel(parent, "⏱  Auto-Lock")

        tk.Label(
            panel,
            text="Lock vault after inactivity:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", pady=(0, 8))

        saved = load_setting("auto_lock", "Never")
        self._auto_lock_var = tk.StringVar(value=saved)

        for option in AUTO_LOCK_OPTIONS.keys():
            tk.Radiobutton(
                panel,
                text=option,
                variable=self._auto_lock_var,
                value=option,
                font=("Segoe UI", 10),
                bg=COLOUR_PANEL,
                fg=COLOUR_TEXT,
                activebackground=COLOUR_PANEL,
                selectcolor=COLOUR_ACCENT,
                command=self._save_auto_lock
            ).pack(anchor="w")

    def _build_restore_section(self, parent: tk.Widget) -> None:
        """Build the restore and verify backup panel."""
        panel = self._section_panel(parent, "🔄  Restore & Verify")

        self._restore_status = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUCCESS,
            wraplength=340
        )
        self._restore_status.pack(anchor="w", pady=(0, 8))

        tk.Button(
            panel,
            text="Verify Backup",
            font=("Segoe UI", 10),
            bg=COLOUR_ACCENT,
            fg=COLOUR_TEXT,
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._handle_verify_backup
        ).pack(fill="x", pady=(0, 8))

        tk.Button(
            panel,
            text="Restore from Backup",
            font=("Segoe UI", 10, "bold"),
            bg="#8b4513",
            fg="#ffffff",
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._handle_restore_backup
        ).pack(fill="x")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _handle_create_backup(self) -> None:
        """Create an encrypted vault backup."""
        folder_str = load_setting("backup_folder", "")
        folder     = Path(folder_str) if folder_str else BACKUP_FOLDER

        self._backup_status.config(
            text="Creating backup...", fg=COLOUR_SUBTLE
        )
        self.update()

        success, message = create_backup(
            password           = self._master_password,
            destination_folder = folder
        )

        if success:
            save_setting("last_backup_date", message)
            self._backup_status.config(
                text=f"✓ Backup created:\n{Path(message).name}",
                fg=COLOUR_SUCCESS
            )
        else:
            self._backup_status.config(
                text=f"⚠ {message}",
                fg=COLOUR_ERROR
            )

    def _handle_choose_backup_folder(self) -> None:
        """Let the user choose a custom backup destination folder."""
        folder = filedialog.askdirectory(
            title="Choose Backup Folder",
            parent=self
        )
        if folder:
            save_setting("backup_folder", folder)
            self._backup_status.config(
                text=f"✓ Backup folder set:\n{folder}",
                fg=COLOUR_SUCCESS
            )

    def _handle_verify_backup(self) -> None:
        """Verify the integrity of a selected backup file."""
        path_str = filedialog.askopenfilename(
            title     = "Select Backup to Verify",
            filetypes = [("Vault Backup", "*.pdvbackup"), ("All Files", "*.*")],
            parent    = self
        )
        if not path_str:
            return

        backup_path = Path(path_str)

        # Ask for the backup password
        backup_password = simpledialog.askstring(
            "Backup Password",
            "Enter the password used when this backup was created:",
            show="●",
            parent=self
        )

        if not backup_password:
            return

        is_valid, message = verify_backup(backup_path, backup_password)

        if is_valid:
            self._restore_status.config(
                text=f"✓ {message}", fg=COLOUR_SUCCESS
            )
        else:
            self._restore_status.config(
                text=f"⚠ {message}", fg=COLOUR_ERROR
            )

    def _handle_restore_backup(self) -> None:
        """Restore the vault from a selected backup file."""
        confirmed = messagebox.askyesno(
            "Restore Vault",
            "Restoring will replace your current vault contents.\n\n"
            "Your existing data will be overwritten.\n\n"
            "Continue?",
            parent=self
        )
        if not confirmed:
            return

        path_str = filedialog.askopenfilename(
            title     = "Select Backup to Restore",
            filetypes = [("Vault Backup", "*.pdvbackup"), ("All Files", "*.*")],
            parent    = self
        )
        if not path_str:
            return

        backup_path = Path(path_str)

        # Ask for the backup password
        backup_password = simpledialog.askstring(
            "Backup Password",
            "Enter the password used when this backup was created:",
            show="●",
            parent=self
        )

        if not backup_password:
            return

        self._restore_status.config(
            text="Restoring vault...", fg=COLOUR_SUBTLE
        )
        self.update()

        success, message = restore_backup(backup_path, backup_password)

        if success:
            self._restore_status.config(
                text=f"✓ {message}", fg=COLOUR_SUCCESS
            )
            messagebox.showinfo(
                "Restore Complete",
                f"{message}\n\nThe application will now lock.\n"
                "Please log in again to continue.",
                parent=self
            )
            self._on_lock()
        else:
            self._restore_status.config(
                text=f"⚠ {message}", fg=COLOUR_ERROR
            )
            messagebox.showerror("Restore Failed", message, parent=self)

    def _handle_change_password(self) -> None:
        """Validate and change the master password."""
        current = self._entry_current.get()
        new_pw  = self._entry_new.get()
        confirm = self._entry_confirm.get()

        if not current:
            self._pw_status.config(
                text="⚠ Enter your current password.", fg=COLOUR_ERROR
            )
            return

        if not verify_master_password(current):
            self._pw_status.config(
                text="⚠ Current password is incorrect.", fg=COLOUR_ERROR
            )
            return

        if len(new_pw) < 8:
            self._pw_status.config(
                text="⚠ New password must be at least 8 characters.",
                fg=COLOUR_ERROR
            )
            return

        if new_pw != confirm:
            self._pw_status.config(
                text="⚠ New passwords do not match.", fg=COLOUR_ERROR
            )
            return

        salt          = generate_salt()
        password_hash = hash_password(new_pw, salt)
        save_vault_settings(password_hash, salt)

        self._master_password = new_pw
        self._entry_current.delete(0, tk.END)
        self._entry_new.delete(0, tk.END)
        self._entry_confirm.delete(0, tk.END)

        self._pw_status.config(
            text="✓ Password changed successfully.", fg=COLOUR_SUCCESS
        )

    def _save_auto_lock(self) -> None:
        """Save the auto-lock setting and apply it immediately."""
        selected = self._auto_lock_var.get()
        save_setting("auto_lock", selected)
        minutes = AUTO_LOCK_OPTIONS.get(selected, 0)
        self._vault_state.set_auto_lock(minutes)

    def _save_backup_frequency(self) -> None:
        """Save the auto-backup frequency setting."""
        save_setting("backup_frequency", self._backup_freq_var.get())

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section_panel(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a titled section panel."""
        outer = tk.Frame(parent, bg=COLOUR_BACKGROUND)
        outer.pack(fill="x", pady=(0, 16))

        tk.Label(
            outer,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=COLOUR_BACKGROUND,
            fg=COLOUR_TEXT
        ).pack(anchor="w", pady=(0, 8))

        panel = tk.Frame(outer, bg=COLOUR_PANEL, padx=20, pady=16)
        panel.pack(fill="x")
        return panel

    def _info_row(
        self,
        parent: tk.Widget,
        label: str,
        value: str
    ) -> None:
        """Render a single info key-value row."""
        row = tk.Frame(parent, bg=COLOUR_PANEL)
        row.pack(fill="x", pady=3)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 9, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            width=16,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT,
            anchor="w"
        ).pack(side="left")




    def _build_health_section(self, parent):
        panel = self._section_panel(parent, '🏥  Vault Health')
        tk.Label(
            panel,
            text='Run a full integrity and consistency scan of your vault.',
            font=('Segoe UI', 9),
            bg='#16213e',
            fg='#a0a0b0',
            wraplength=340
        ).pack(anchor='w', pady=(0, 8))
        tk.Button(
            panel,
            text='Open Health Check',
            font=('Segoe UI', 10, 'bold'),
            bg='#0f3460',
            fg='#eaeaea',
            activebackground='#e94560',
            activeforeground='#ffffff',
            relief='flat',
            padx=16,
            pady=7,
            cursor='hand2',
            command=self._on_close
        ).pack(fill='x')

