"""
modules/password_vault/ui/generator_dialog.py

Password generator dialog for the Password Vault module.
"""

import tkinter as tk
from typing import Callable, Optional

from vaultcore.theme import Theme
from modules.password_vault.core.generator import (
    GeneratorPolicy, generate_password
)


class GeneratorDialog(tk.Toplevel):
    """
    Password generator dialog with live preview.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_accept: Callable[[str], None]
    ) -> None:
        """
        Initialize the generator dialog.

        Args:
            parent:    The parent widget.
            on_accept: Callback with the generated password.
        """
        super().__init__(parent)
        self.title("Password Generator")
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._on_accept = on_accept
        self._policy = GeneratorPolicy()
        self._build()
        self._regenerate()

    def _build(self) -> None:
        """Construct the dialog UI."""
        tk.Label(
            self,
            text="🎲  Password Generator",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 12))

        # Generated password display
        preview_frame = tk.Frame(self, bg=Theme.PANEL, padx=16, pady=12)
        preview_frame.pack(fill="x", padx=24, pady=(0, 16))

        self._preview_var = tk.StringVar()
        preview_entry = tk.Entry(
            preview_frame,
            textvariable=self._preview_var,
            font=("Courier New", 12),
            bg=Theme.ENTRY_BG,
            fg=Theme.SUCCESS,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6
        )
        preview_entry.pack(fill="x", ipady=6)

        # Options
        options = tk.Frame(self, bg=Theme.BACKGROUND)
        options.pack(fill="x", padx=24)

        # Length slider
        tk.Label(
            options,
            text="Length",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        length_row = tk.Frame(options, bg=Theme.BACKGROUND)
        length_row.pack(fill="x", pady=(4, 12))

        self._length_var = tk.IntVar(value=16)
        length_slider = tk.Scale(
            length_row,
            from_=8, to=64,
            orient="horizontal",
            variable=self._length_var,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT,
            troughcolor=Theme.PANEL,
            highlightthickness=0,
            command=lambda e: self._regenerate()
        )
        length_slider.pack(side="left", fill="x", expand=True)

        # Checkboxes
        self._var_upper     = tk.BooleanVar(value=True)
        self._var_lower     = tk.BooleanVar(value=True)
        self._var_numbers   = tk.BooleanVar(value=True)
        self._var_symbols   = tk.BooleanVar(value=True)
        self._var_ambiguous = tk.BooleanVar(value=False)

        checks = [
            ("Uppercase (A-Z)",           self._var_upper),
            ("Lowercase (a-z)",           self._var_lower),
            ("Numbers (0-9)",             self._var_numbers),
            ("Symbols (!@#\$%)",           self._var_symbols),
            ("Exclude ambiguous (0OIl1)", self._var_ambiguous),
        ]

        for text, var in checks:
            tk.Checkbutton(
                options,
                text=text,
                variable=var,
                font=Theme.FONT_BODY,
                bg=Theme.BACKGROUND,
                fg=Theme.TEXT,
                activebackground=Theme.BACKGROUND,
                selectcolor=Theme.ACCENT,
                command=self._regenerate
            ).pack(anchor="w", pady=2)

        # Buttons
        button_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        button_frame.pack(fill="x", padx=24, pady=(20, 20))

        tk.Button(
            button_frame,
            text="🔄  Regenerate",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._regenerate
        ).pack(side="left")

        tk.Button(
            button_frame,
            text="✓  Use Password",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._handle_accept
        ).pack(side="right")

        tk.Button(
            button_frame,
            text="Cancel",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.destroy
        ).pack(side="right", padx=(0, 8))

    def _regenerate(self) -> None:
        """Generate a new password based on current options."""
        policy = GeneratorPolicy(
            length            = self._length_var.get(),
            use_uppercase     = self._var_upper.get(),
            use_lowercase     = self._var_lower.get(),
            use_numbers       = self._var_numbers.get(),
            use_symbols       = self._var_symbols.get(),
            exclude_ambiguous = self._var_ambiguous.get()
        )
        password = generate_password(policy)
        self._preview_var.set(password)

    def _handle_accept(self) -> None:
        """Accept the generated password."""
        password = self._preview_var.get()
        if password:
            self._on_accept(password)
            self.destroy()
