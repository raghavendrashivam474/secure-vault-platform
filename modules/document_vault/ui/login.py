"""
ui/login.py

Login and vault setup screens for the Personal Document Vault.
Updated in Final Sprint to include vault restore option
on the setup screen for disaster recovery.
"""

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from pathlib import Path
from typing import Callable

from vaultcore.validators import validate_master_password, validate_login_password
from vaultcore.authentication import create_vault, verify_master_password
from modules.document_vault.core.vault import VaultState
from vaultcore.backup import restore_backup, verify_backup


COLOUR_BACKGROUND = "#1a1a2e"
COLOUR_PANEL      = "#16213e"
COLOUR_ACCENT     = "#0f3460"
COLOUR_HIGHLIGHT  = "#e94560"
COLOUR_TEXT       = "#eaeaea"
COLOUR_SUBTLE     = "#a0a0b0"
COLOUR_ENTRY_BG   = "#0d1b2a"
COLOUR_BUTTON_BG  = "#e94560"
COLOUR_BUTTON_FG  = "#ffffff"
COLOUR_ERROR      = "#ff6b6b"
COLOUR_SUCCESS    = "#51cf66"


def _make_label(
    parent: tk.Widget,
    text: str,
    font_size: int = 11,
    colour: str = COLOUR_TEXT,
    bold: bool = False
) -> tk.Label:
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", font_size, weight),
        bg=COLOUR_PANEL,
        fg=colour
    )


def _make_entry(parent: tk.Widget, show: str = "") -> tk.Entry:
    return tk.Entry(
        parent,
        show=show,
        font=("Segoe UI", 11),
        bg=COLOUR_ENTRY_BG,
        fg=COLOUR_TEXT,
        insertbackground=COLOUR_TEXT,
        relief="flat",
        bd=8
    )


def _make_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    bg: str = COLOUR_BUTTON_BG
) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 11, "bold"),
        bg=bg,
        fg=COLOUR_BUTTON_FG,
        activebackground=COLOUR_ACCENT,
        activeforeground=COLOUR_TEXT,
        relief="flat",
        cursor="hand2",
        padx=20,
        pady=8
    )


class SetupScreen(tk.Frame):
    """
    Displayed on first launch when no vault exists.

    Presents three options:
        1. Create a new vault
        2. Restore from an existing backup
        3. Exit the application
    """

    def __init__(
        self,
        parent: tk.Widget,
        vault_state: VaultState,
        on_success: Callable[[str], None],
        on_restored: Callable
    ) -> None:
        """
        Initialize the setup screen.

        Args:
            parent:      The parent widget.
            vault_state: The shared vault state object.
            on_success:  Callback with master password after vault creation.
            on_restored: Callback after successful vault restoration.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._vault_state = vault_state
        self._on_success  = on_success
        self._on_restored = on_restored
        self._mode        = "choice"
        self._build_choice()

    def _build_choice(self) -> None:
        """Show the initial choice screen."""
        for widget in self.winfo_children():
            widget.destroy()

        self.pack(fill="both", expand=True)

        panel = tk.Frame(self, bg=COLOUR_PANEL, padx=60, pady=50)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐  Personal Document Vault",
            font=("Segoe UI", 22, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).pack(pady=(0, 8))

        tk.Label(
            panel,
            text="Welcome. How would you like to get started?",
            font=("Segoe UI", 11),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(pady=(0, 36))

        # Create new vault button
        tk.Button(
            panel,
            text="＋  Create New Vault",
            font=("Segoe UI", 12, "bold"),
            bg=COLOUR_HIGHLIGHT,
            fg="#ffffff",
            activebackground=COLOUR_ACCENT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            padx=24,
            pady=12,
            command=self._show_create_form
        ).pack(fill="x", pady=(0, 12))

        # Restore from backup button
        tk.Button(
            panel,
            text="🔄  Restore Existing Vault",
            font=("Segoe UI", 12, "bold"),
            bg=COLOUR_ACCENT,
            fg="#ffffff",
            activebackground=COLOUR_HIGHLIGHT,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            padx=24,
            pady=12,
            command=self._handle_restore
        ).pack(fill="x", pady=(0, 12))

        # Exit button
        tk.Button(
            panel,
            text="Exit",
            font=("Segoe UI", 11),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            activebackground=COLOUR_PANEL,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            padx=24,
            pady=8,
            command=self.quit
        ).pack(fill="x")

    def _show_create_form(self) -> None:
        """Switch to the password creation form."""
        for widget in self.winfo_children():
            widget.destroy()

        panel = tk.Frame(self, bg=COLOUR_PANEL, padx=50, pady=40)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐  Create Your Vault",
            font=("Segoe UI", 20, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))

        tk.Label(
            panel,
            text="Set a master password to protect your vault.",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).grid(row=1, column=0, columnspan=2, pady=(0, 28))

        _make_label(panel, "Master Password").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        self._entry_password = _make_entry(panel, show="●")
        self._entry_password.grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(0, 16), ipadx=4
        )

        _make_label(panel, "Confirm Password").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        self._entry_confirm = _make_entry(panel, show="●")
        self._entry_confirm.grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(0, 6), ipadx=4
        )

        tk.Label(
            panel,
            text="Minimum 8 characters.",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self._label_error = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_ERROR
        )
        self._label_error.grid(row=7, column=0, columnspan=2, pady=(0, 12))

        _make_button(panel, "Create Vault", self._handle_create).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        tk.Button(
            panel,
            text="← Back",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE,
            activebackground=COLOUR_PANEL,
            activeforeground=COLOUR_TEXT,
            relief="flat",
            cursor="hand2",
            command=self._build_choice
        ).grid(row=9, column=0, columnspan=2)

        panel.columnconfigure(0, weight=1)
        self._entry_password.bind("<Return>", lambda e: self._entry_confirm.focus())
        self._entry_confirm.bind("<Return>",  lambda e: self._handle_create())
        self._entry_password.focus()

    def _handle_create(self) -> None:
        """Validate input and create the vault."""
        password     = self._entry_password.get()
        confirmation = self._entry_confirm.get()

        is_valid, error_message = validate_master_password(password, confirmation)

        if not is_valid:
            self._label_error.config(text=error_message)
            return

        success = create_vault(password)

        if success:
            self._vault_state.unlock()
            self._on_success(password)
        else:
            self._label_error.config(
                text="Failed to create vault. Please try again."
            )

    def _handle_restore(self) -> None:
        """
        Handle vault restoration from a backup file.

        Presents a file picker, prompts for the backup password,
        verifies the archive, restores the vault, and invokes
        the on_restored callback.
        """
        path_str = filedialog.askopenfilename(
            title     = "Select Vault Backup to Restore",
            filetypes = [
                ("Vault Backup", "*.pdvbackup"),
                ("All Files",    "*.*")
            ],
            parent = self
        )

        if not path_str:
            return

        backup_path = Path(path_str)

        backup_password = simpledialog.askstring(
            "Backup Password",
            "Enter the password used when this backup was created:",
            show   = "●",
            parent = self
        )

        if not backup_password:
            return

        # Verify before restoring
        is_valid, verify_message = verify_backup(backup_path, backup_password)

        if not is_valid:
            messagebox.showerror(
                "Verification Failed",
                f"Cannot restore backup:\n\n{verify_message}",
                parent=self
            )
            return

        success, message = restore_backup(backup_path, backup_password)

        if success:
            messagebox.showinfo(
                "Restore Complete",
                f"{message}\n\n"
                "Please log in with your master password to continue.",
                parent=self
            )
            self._on_restored()
        else:
            messagebox.showerror(
                "Restore Failed",
                message,
                parent=self
            )


class LoginScreen(tk.Frame):
    """
    Displayed on subsequent launches when a vault already exists.
    """

    def __init__(
        self,
        parent: tk.Widget,
        vault_state: VaultState,
        on_success: Callable[[str], None]
    ) -> None:
        """
        Initialize the login screen.

        Args:
            parent:      The parent widget.
            vault_state: The shared vault state object.
            on_success:  Callback with master password after authentication.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._vault_state = vault_state
        self._on_success  = on_success
        self._attempts    = 0
        self._build()

    def _build(self) -> None:
        """Construct the login screen."""
        self.pack(fill="both", expand=True)

        panel = tk.Frame(self, bg=COLOUR_PANEL, padx=50, pady=40)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐  Personal Document Vault",
            font=("Segoe UI", 20, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).grid(row=0, column=0, pady=(0, 6))

        tk.Label(
            panel,
            text="Enter your master password to unlock your vault.",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).grid(row=1, column=0, pady=(0, 28))

        _make_label(panel, "Master Password").grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self._entry_password = _make_entry(panel, show="●")
        self._entry_password.grid(
            row=3, column=0, sticky="ew", pady=(0, 16), ipadx=4
        )

        self._label_error = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_ERROR
        )
        self._label_error.grid(row=4, column=0, pady=(0, 12))

        _make_button(panel, "Unlock Vault", self._handle_login).grid(
            row=5, column=0, sticky="ew"
        )

        panel.columnconfigure(0, weight=1)
        self._entry_password.bind("<Return>", lambda e: self._handle_login())
        self._entry_password.focus()

    def _handle_login(self) -> None:
        """Validate input and verify the master password."""
        password = self._entry_password.get()

        is_valid, error_message = validate_login_password(password)

        if not is_valid:
            self._label_error.config(text=error_message)
            return

        success = verify_master_password(password)

        if success:
            self._vault_state.unlock()
            self._on_success(password)
        else:
            self._attempts += 1
            self._entry_password.delete(0, tk.END)
            self._label_error.config(
                text=f"Incorrect password. Please try again. "
                     f"(Attempt {self._attempts})"
            )

