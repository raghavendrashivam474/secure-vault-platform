"""
ui/login.py

Platform Login Screen for the Secure Vault Platform.

This is the first screen shown after platform launch.
Authentication is handled entirely by VaultCore.
The login screen never communicates with the database directly.
"""

import tkinter as tk
from typing import Callable

from vaultcore.config import PLATFORM_NAME, COLOURS
from vaultcore.authentication import verify_master_password, create_vault
from vaultcore.session import SessionManager
from vaultcore.logger import log_event, log_warning
from vaultcore.validators import validate_master_password, validate_login_password
from vaultcore.database import vault_exists


COLOUR_BACKGROUND = COLOURS["background"]
COLOUR_PANEL      = COLOURS["panel"]
COLOUR_ACCENT     = COLOURS["accent"]
COLOUR_HIGHLIGHT  = COLOURS["highlight"]
COLOUR_TEXT       = COLOURS["text"]
COLOUR_SUBTLE     = COLOURS["subtle"]
COLOUR_ENTRY_BG   = COLOURS["entry_bg"]
COLOUR_ERROR      = COLOURS["error"]
COLOUR_SUCCESS    = COLOURS["success"]


def _entry(parent: tk.Widget, show: str = "") -> tk.Entry:
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


def _button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    bg: str = None
) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 11, "bold"),
        bg=bg or COLOUR_HIGHLIGHT,
        fg="#ffffff",
        activebackground=COLOUR_ACCENT,
        activeforeground=COLOUR_TEXT,
        relief="flat",
        cursor="hand2",
        padx=20,
        pady=8
    )


class PlatformLoginScreen(tk.Frame):
    """
    Platform-wide login screen.

    Handles both first-launch vault creation and
    returning user authentication through VaultCore.
    """

    def __init__(
        self,
        parent: tk.Widget,
        session_manager: SessionManager,
        on_authenticated: Callable
    ) -> None:
        """
        Initialize the platform login screen.

        Args:
            parent:           The parent widget.
            session_manager:  The platform session manager.
            on_authenticated: Callback after successful authentication.
        """
        super().__init__(parent, bg=COLOUR_BACKGROUND)
        self._session_manager  = session_manager
        self._on_authenticated = on_authenticated
        self._attempts         = 0

        if vault_exists():
            self._build_login()
        else:
            self._build_setup()

    def _build_setup(self) -> None:
        """Build the first-time vault setup form."""
        self.pack(fill="both", expand=True)

        panel = tk.Frame(self, bg=COLOUR_PANEL, padx=60, pady=50)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐",
            font=("Segoe UI", 40),
            bg=COLOUR_PANEL,
            fg=COLOUR_HIGHLIGHT
        ).pack(pady=(0, 8))

        tk.Label(
            panel,
            text=PLATFORM_NAME,
            font=("Segoe UI", 20, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).pack(pady=(0, 4))

        tk.Label(
            panel,
            text="Create your master password to get started.",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(pady=(0, 28))

        tk.Label(
            panel,
            text="Master Password",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w")

        self._entry_password = _entry(panel, show="●")
        self._entry_password.pack(fill="x", pady=(4, 14), ipady=4)

        tk.Label(
            panel,
            text="Confirm Password",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w")

        self._entry_confirm = _entry(panel, show="●")
        self._entry_confirm.pack(fill="x", pady=(4, 6), ipady=4)

        tk.Label(
            panel,
            text="Minimum 8 characters.",
            font=("Segoe UI", 9),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w", pady=(0, 14))

        self._error_label = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_ERROR
        )
        self._error_label.pack(pady=(0, 10))

        _button(panel, "Create Vault", self._handle_create).pack(fill="x")

        self._entry_password.bind(
            "<Return>", lambda e: self._entry_confirm.focus()
        )
        self._entry_confirm.bind(
            "<Return>", lambda e: self._handle_create()
        )
        self._entry_password.focus()

    def _build_login(self) -> None:
        """Build the returning user login form."""
        self.pack(fill="both", expand=True)

        panel = tk.Frame(self, bg=COLOUR_PANEL, padx=60, pady=50)
        panel.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            panel,
            text="🔐",
            font=("Segoe UI", 40),
            bg=COLOUR_PANEL,
            fg=COLOUR_HIGHLIGHT
        ).pack(pady=(0, 8))

        tk.Label(
            panel,
            text=PLATFORM_NAME,
            font=("Segoe UI", 20, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_TEXT
        ).pack(pady=(0, 4))

        tk.Label(
            panel,
            text="Enter your master password to unlock the platform.",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(pady=(0, 28))

        tk.Label(
            panel,
            text="Master Password",
            font=("Segoe UI", 10, "bold"),
            bg=COLOUR_PANEL,
            fg=COLOUR_SUBTLE
        ).pack(anchor="w")

        self._entry_password = _entry(panel, show="●")
        self._entry_password.pack(fill="x", pady=(4, 6), ipady=4)

        self._error_label = tk.Label(
            panel,
            text="",
            font=("Segoe UI", 10),
            bg=COLOUR_PANEL,
            fg=COLOUR_ERROR
        )
        self._error_label.pack(pady=(0, 10))

        _button(panel, "Unlock Platform", self._handle_login).pack(fill="x")

        self._entry_password.bind(
            "<Return>", lambda e: self._handle_login()
        )
        self._entry_password.focus()

    def _handle_create(self) -> None:
        """Handle vault creation on first launch."""
        password     = self._entry_password.get()
        confirmation = self._entry_confirm.get()

        is_valid, error = validate_master_password(password, confirmation)
        if not is_valid:
            self._error_label.config(text=error)
            return

        success = create_vault(password)
        if success:
            log_event("VaultCreated", "Platform first launch")
            session = self._session_manager.create_session(password)
            self._on_authenticated()
        else:
            self._error_label.config(
                text="Failed to create vault. Please try again."
            )

    def _handle_login(self) -> None:
        """Handle returning user authentication."""
        password = self._entry_password.get()

        is_valid, error = validate_login_password(password)
        if not is_valid:
            self._error_label.config(text=error)
            return

        success = verify_master_password(password)

        if success:
            log_event("LoginSuccess", "Platform authenticated")
            session = self._session_manager.create_session(password)
            self._on_authenticated()
        else:
            self._attempts += 1
            self._entry_password.delete(0, tk.END)
            log_warning(f"Failed login attempt {self._attempts}")
            self._error_label.config(
                text=f"Incorrect password. (Attempt {self._attempts})"
            )
