"""
modules/password_vault/ui/password_editor.py

Password add/edit form for the Password Vault module.
"""

import tkinter as tk
from typing import Callable, Optional

from vaultcore.theme import Theme

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.models.password_category import PasswordCategory
from modules.password_vault.core.database import (
    insert_password, update_password, load_all_categories
)
from modules.password_vault.core.strength import analyze_password
from modules.password_vault.ui.generator_dialog import GeneratorDialog


STRENGTH_COLOURS = {
    "Very Strong": Theme.SUCCESS,
    "Strong":      Theme.SUCCESS,
    "Fair":        Theme.WARNING,
    "Weak":        Theme.ERROR,
}


class PasswordEditor(tk.Toplevel):
    """Add or edit password entry dialog."""

    def __init__(
        self,
        parent: tk.Widget,
        master_password: str,
        entry: Optional[PasswordEntry],
        on_saved: Callable
    ) -> None:
        super().__init__(parent)
        title = "Edit Password" if entry else "New Password"
        self.title(title)
        self.geometry("560x680")
        self.minsize(500, 500)
        self.configure(bg=Theme.BACKGROUND)
        self.grab_set()

        self._master_password = master_password
        self._entry           = entry
        self._on_saved        = on_saved
        self._categories: list[PasswordCategory] = load_all_categories()

        self._build(title)
        self._analyze_current_password()

    def _build(self, title: str) -> None:
        """Construct the editor UI with scrollable body."""

        # Header (fixed)
        tk.Label(
            self,
            text=f"🔒  {title}",
            font=Theme.FONT_HEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(pady=(20, 12))

        # Buttons (fixed at bottom) - build FIRST so they always show
        button_frame = tk.Frame(self, bg=Theme.BACKGROUND)
        button_frame.pack(side="bottom", fill="x", padx=24, pady=(10, 20))

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

        tk.Button(
            button_frame,
            text="✓  Save",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._handle_save
        ).pack(side="right")

        # Scrollable form body
        canvas = tk.Canvas(self, bg=Theme.BACKGROUND, highlightthickness=0)
        sb     = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        form = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win  = canvas.create_window((0, 0), window=form, anchor="nw")

        form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        form_padded = tk.Frame(form, bg=Theme.BACKGROUND)
        form_padded.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Title
        self._var_title = tk.StringVar(value=self._entry.title if self._entry else "")
        self._field(form_padded, "Title", self._var_title)

        # Username
        self._var_username = tk.StringVar(value=self._entry.username if self._entry else "")
        self._field(form_padded, "Username / Email", self._var_username)

        # Password with generator and reveal
        tk.Label(
            form_padded,
            text="Password",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(12, 4))

        password_row = tk.Frame(form_padded, bg=Theme.BACKGROUND)
        password_row.pack(fill="x")

        self._var_password  = tk.StringVar()

        if self._entry:
            decrypted = decrypt_file_to_memory_string(
                self._entry.password_encrypted, self._master_password
            )
            self._var_password.set(decrypted)

        self._password_entry = tk.Entry(
            password_row,
            textvariable=self._var_password,
            font=("Courier New", 11),
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6,
            show="●"
        )
        self._password_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self._var_password.trace_add("write", lambda *a: self._analyze_current_password())

        tk.Button(
            password_row,
            text="👁",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=10,
            cursor="hand2",
            command=self._toggle_reveal
        ).pack(side="left", padx=(4, 0))

        tk.Button(
            password_row,
            text="🎲",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=10,
            cursor="hand2",
            command=self._open_generator
        ).pack(side="left", padx=(4, 0))

        # Strength indicator
        self._strength_label = tk.Label(
            form_padded,
            text="",
            font=Theme.FONT_SMALL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE,
            wraplength=480,
            justify="left"
        )
        self._strength_label.pack(anchor="w", pady=(6, 8))

        # URL
        self._var_url = tk.StringVar(value=self._entry.url if self._entry else "")
        self._field(form_padded, "Website URL (optional)", self._var_url)

        # Category
        tk.Label(
            form_padded,
            text="Category",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(12, 4))

        options = ["None"] + [c.name for c in self._categories]
        current = "None"
        if self._entry and self._entry.category_id:
            for cat in self._categories:
                if cat.id == self._entry.category_id:
                    current = cat.name
                    break

        self._var_category = tk.StringVar(value=current)
        cat_menu = tk.OptionMenu(form_padded, self._var_category, *options)
        cat_menu.config(
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            activebackground=Theme.ACCENT,
            relief="flat",
            highlightthickness=0
        )
        cat_menu["menu"].config(bg=Theme.ACCENT, fg=Theme.TEXT)
        cat_menu.pack(fill="x")

        # Notes
        tk.Label(
            form_padded,
            text="Notes (optional)",
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(12, 4))

        self._notes_text = tk.Text(
            form_padded,
            font=Theme.FONT_BODY,
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6,
            height=4,
            wrap="word"
        )
        self._notes_text.pack(fill="x")
        if self._entry and self._entry.notes:
            self._notes_text.insert("1.0", self._entry.notes)

    def _field(self, parent, label: str, variable: tk.StringVar) -> None:
        """Render a labeled text field."""
        tk.Label(
            parent,
            text=label,
            font=Theme.FONT_LABEL,
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(12, 4))

        tk.Entry(
            parent,
            textvariable=variable,
            font=Theme.FONT_BODY,
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6
        ).pack(fill="x", ipady=4)

    def _toggle_reveal(self) -> None:
        current = self._password_entry.cget("show")
        self._password_entry.config(show="" if current else "●")

    def _open_generator(self) -> None:
        GeneratorDialog(
            parent    = self,
            on_accept = lambda pwd: self._var_password.set(pwd)
        )

    def _analyze_current_password(self) -> None:
        password = self._var_password.get()
        if not password:
            self._strength_label.config(text="")
            return

        result = analyze_password(password)
        colour = STRENGTH_COLOURS.get(result.label, Theme.SUBTLE)

        text = f"● {result.label} ({result.score}/100)"
        if result.suggestions:
            text += "  •  " + result.suggestions[0]

        self._strength_label.config(text=text, fg=colour)

    def _handle_save(self) -> None:
        title    = self._var_title.get().strip()
        username = self._var_username.get().strip()
        password = self._var_password.get()

        if not title or not username or not password:
            return

        encrypted = encrypt_string(password, self._master_password)
        if not encrypted:
            return

        category_id = None
        selected = self._var_category.get()
        for cat in self._categories:
            if cat.name == selected:
                category_id = cat.id
                break

        strength = analyze_password(password)
        notes    = self._notes_text.get("1.0", "end-1c").strip() or None

        if self._entry:
            self._entry.title              = title
            self._entry.username           = username
            self._entry.password_encrypted = encrypted
            self._entry.url                = self._var_url.get().strip() or None
            self._entry.category_id        = category_id
            self._entry.notes              = notes
            self._entry.strength_score     = strength.score
            update_password(self._entry)
        else:
            entry = PasswordEntry(
                id                 = None,
                title              = title,
                username           = username,
                password_encrypted = encrypted,
                url                = self._var_url.get().strip() or None,
                category_id        = category_id,
                notes              = notes,
                strength_score     = strength.score
            )
            insert_password(entry)

        self._on_saved()
        self.destroy()


def encrypt_string(text: str, password: str) -> str:
    """Encrypt a string using AES-256-GCM."""
    import base64, os, hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt  = os.urandom(32)
    nonce = os.urandom(12)
    key   = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000, dklen=32)
    aes   = AESGCM(key)
    ct    = aes.encrypt(nonce, text.encode("utf-8"), None)
    combined = salt + nonce + ct
    return base64.b64encode(combined).decode("utf-8")


def decrypt_file_to_memory_string(encrypted_b64: str, password: str) -> str:
    """Decrypt a base64-encoded encrypted string."""
    import base64, hashlib
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        combined = base64.b64decode(encrypted_b64.encode("utf-8"))
        salt     = combined[:32]
        nonce    = combined[32:44]
        ct       = combined[44:]
        key      = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000, dklen=32)
        aes      = AESGCM(key)
        pt       = aes.decrypt(nonce, ct, None)
        return pt.decode("utf-8")
    except Exception:
        return ""
