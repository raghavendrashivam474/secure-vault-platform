"""
ui/home.py

Platform Dashboard for the Secure Vault Platform.

Displayed after successful platform authentication.
Shows all registered modules and platform navigation.
"""

import tkinter as tk
from typing import Callable

from vaultcore.config import PLATFORM_NAME, PLATFORM_VERSION
from vaultcore.module_manager import ModuleManager, ModuleDefinition
from vaultcore.session import SessionManager
from vaultcore.theme import Theme


class PlatformHome(tk.Frame):
    """
    The authenticated platform dashboard.

    Displays module cards, session info,
    and platform navigation options.
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
        """
        Initialize the platform dashboard.

        Args:
            parent:          The parent widget.
            module_manager:  The platform module registry.
            session_manager: The platform session manager.
            on_settings:     Open platform settings callback.
            on_security:     Open security center callback.
            on_about:        Open about screen callback.
            on_lock:         Lock the platform callback.
            on_exit:         Exit the platform callback.
        """
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
        """Construct the platform dashboard layout."""
        self.pack(fill="both", expand=True)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self) -> None:
        """Build the top header bar."""
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

        session = self._session_manager.get_session()
        login_info = ""
        if session:
            login_info = f"Authenticated  •  Session started {session.formatted_login_time()}"

        tk.Label(
            title_frame,
            text=login_info,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w")

        # Right side buttons
        tk.Button(
            header,
            text="🔒  Lock",
            font=Theme.FONT_BODY,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            activebackground=Theme.ACCENT,
            activeforeground=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_lock
        ).pack(side="right", padx=12, pady=16)

        tk.Button(
            header,
            text="Exit",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            activebackground=Theme.ACCENT,
            activeforeground=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_exit
        ).pack(side="right", padx=(0, 4), pady=16)

        tk.Button(
            header,
            text="ℹ  About",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            activebackground=Theme.ACCENT,
            activeforeground=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_about
        ).pack(side="right", padx=(0, 4), pady=16)

        tk.Button(
            header,
            text="🛡  Security",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_security
        ).pack(side="right", padx=(0, 4), pady=16)

        tk.Button(
            header,
            text="⚙  Settings",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_settings
        ).pack(side="right", padx=(0, 4), pady=16)

    def _build_body(self) -> None:
        """Build the module grid area."""
        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True, padx=40, pady=30)

        tk.Label(
            body,
            text="Installed Modules",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack(anchor="w", pady=(0, 20))

        grid = tk.Frame(body, bg=Theme.BACKGROUND)
        grid.pack(fill="both", expand=True)

        modules = self._module_manager.get_all()
        for col, module in enumerate(modules):
            self._render_module_card(grid, module, col)

        grid.columnconfigure(
            tuple(range(max(len(modules), 1))), weight=1
        )

    def _render_module_card(
        self,
        parent: tk.Widget,
        module: ModuleDefinition,
        column: int
    ) -> None:
        """Render a single module card."""
        card = tk.Frame(
            parent,
            bg=Theme.PANEL,
            padx=28,
            pady=28
        )
        card.grid(row=0, column=column, padx=12, pady=8, sticky="nsew")

        tk.Label(
            card,
            text=module.icon,
            font=("Segoe UI", 36),
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(pady=(0, 10))

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

        tk.Label(
            card,
            text=module.description,
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE,
            wraplength=200,
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
                width=16,
                command=lambda m=module: self._launch_module(m)
            ).pack()
        else:
            tk.Label(
                card,
                text="Coming Soon",
                font=Theme.FONT_SMALL,
                bg=Theme.ACCENT,
                fg=Theme.SUBTLE,
                padx=24,
                pady=8
            ).pack()

    def _launch_module(self, module: ModuleDefinition) -> None:
        """Launch a module via the module manager."""
        self._module_manager.launch(module.id)

    def _build_footer(self) -> None:
        """Build the bottom status bar."""
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
