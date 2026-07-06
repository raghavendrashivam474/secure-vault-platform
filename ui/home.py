"""
ui/home.py

Platform Dashboard for the Secure Vault Platform.
Updated in Sprint 9 to display dynamic module metadata.
"""

import tkinter as tk
from typing import Callable

from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION
from vaultcore.module_manager import ModuleManager, ModuleDefinition
from vaultcore.session import SessionManager
from vaultcore.theme import Theme


HEALTH_COLOURS = {
    "healthy": Theme.SUCCESS,
    "warning": Theme.WARNING,
    "error":   Theme.ERROR,
    "unknown": Theme.SUBTLE,
}


class PlatformHome(tk.Frame):
    """
    The authenticated platform dashboard with dynamic module cards.
    """

    def __init__(
        self,
        parent: tk.Widget,
        module_manager: ModuleManager,
        session_manager: SessionManager,
        on_settings: Callable,
        on_security: Callable,
        on_about: Callable,
        on_lock: Callable,
        on_exit: Callable
    ) -> None:
        super().__init__(parent, bg=Theme.BACKGROUND)
        self._module_manager  = module_manager
        self._session_manager = session_manager
        self._on_settings     = on_settings
        self._on_security     = on_security
        self._on_about        = on_about
        self._on_lock         = on_lock
        self._on_exit         = on_exit
        self._build()

    def _build(self) -> None:
        self.pack(fill="both", expand=True)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=Theme.PANEL, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🔐",
            font=("Segoe UI", 24),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(24, 8), pady=12)

        title_frame = tk.Frame(header, bg=Theme.PANEL)
        title_frame.pack(side="left", pady=12)

        tk.Label(
            title_frame,
            text=PLATFORM_NAME,
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(anchor="w")

        session    = self._session_manager.get_session()
        login_info = ""
        if session:
            login_info = (
                f"Authenticated  •  "
                f"Session started {session.formatted_login_time()}"
            )

        tk.Label(
            title_frame,
            text=login_info,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        for text, command, bg in [
            ("🔒  Lock",    self._on_lock,     Theme.HIGHLIGHT),
            ("Exit",        self._on_exit,     Theme.PANEL),
            ("ℹ  About",   self._on_about,    Theme.PANEL),
            ("🛡  Security",self._on_security, Theme.ACCENT),
            ("⚙  Settings", self._on_settings, Theme.ACCENT),
        ]:
            fg = "#ffffff" if bg == Theme.HIGHLIGHT else (
                Theme.SUBTLE if bg == Theme.PANEL else Theme.TEXT
            )
            tk.Button(
                header,
                text=text,
                font=Theme.FONT_BODY,
                bg=bg,
                fg=fg,
                activebackground=Theme.ACCENT,
                activeforeground=Theme.TEXT,
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
                command=command
            ).pack(side="right", padx=(0, 6), pady=16)

    def _build_body(self) -> None:
        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(
            body,
            text="Installed Modules",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(anchor="w", pady=(0, 20))

        grid    = tk.Frame(body, bg=Theme.BACKGROUND)
        grid.pack(fill="both", expand=True)
        modules = self._module_manager.get_all()

        for col, module in enumerate(modules):
            metadata = None
            if module.vault_module is not None:
                try:
                    metadata = module.vault_module.metadata()
                except Exception:
                    pass
            self._render_module_card(grid, module, col, metadata)

        grid.columnconfigure(
            tuple(range(max(len(modules), 1))), weight=1
        )

    def _render_module_card(
        self,
        parent: tk.Widget,
        module: ModuleDefinition,
        column: int,
        metadata=None
    ) -> None:
        card = tk.Frame(parent, bg=Theme.PANEL, padx=24, pady=24)
        card.grid(row=0, column=column, padx=12, pady=8, sticky="nsew")

        tk.Label(
            card,
            text=module.icon,
            font=("Segoe UI", 34),
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(pady=(0, 8))

        tk.Label(
            card,
            text=module.name,
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack()

        tk.Label(
            card,
            text=f"v{module.version}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(pady=(2, 8))

        if metadata is not None:
            # Dynamic metadata display
            health_colour = HEALTH_COLOURS.get(metadata.health, Theme.SUBTLE)

            tk.Label(
                card,
                text=f"● {metadata.health.capitalize()}",
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=health_colour
            ).pack(pady=(0, 6))

            stats_text = (
                f"📄 {metadata.document_count} docs  "
                f"🗂 {metadata.category_count} cats  "
                f"💾 {metadata.formatted_storage()}"
            )
            tk.Label(
                card,
                text=stats_text,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack(pady=(0, 4))

            if metadata.last_backup and metadata.last_backup != "Never":
                tk.Label(
                    card,
                    text=f"Backup: {metadata.last_backup}",
                    font=Theme.FONT_SMALL,
                    bg=Theme.PANEL,
                    fg=Theme.SUBTLE
                ).pack(pady=(0, 8))
        else:
            tk.Label(
                card,
                text=module.description,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE,
                wraplength=180,
                justify="center"
            ).pack(pady=(0, 16))

        if module.available:
            tk.Button(
                card,
                text="Open",
                font=Theme.FONT_BUTTON,
                bg=Theme.HIGHLIGHT,
                fg="#ffffff",
                activebackground=Theme.ACCENT,
                activeforeground=Theme.TEXT,
                relief="flat",
                padx=24,
                pady=8,
                cursor="hand2",
                width=14,
                command=lambda m=module: self._launch_module(m)
            ).pack(pady=(8, 0))
        else:
            tk.Label(
                card,
                text="Coming Soon",
                font=Theme.FONT_SMALL,
                bg=Theme.ACCENT,
                fg=Theme.SUBTLE,
                padx=24,
                pady=8
            ).pack(pady=(8, 0))

    def _launch_module(self, module: ModuleDefinition) -> None:
        self._module_manager.launch(module.id)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=Theme.PANEL, height=32)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        tk.Label(
            footer,
            text=f"{PLATFORM_NAME}  •  {PLATFORM_VERSION}  •  Offline  •  Encrypted",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=20, pady=6)

        tk.Label(
            footer,
            text="🔒 Secured",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUCCESS
        ).pack(side="right", padx=20, pady=6)
