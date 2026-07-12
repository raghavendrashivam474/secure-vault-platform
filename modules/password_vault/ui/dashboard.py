"""
modules/password_vault/ui/dashboard.py

Password Vault dashboard - main UI with filters and sorting.
"""

import tkinter as tk
from typing import Callable, Optional

from vaultcore.theme import Theme
from vaultcore.event_bus import platform_bus, Events

from modules.password_vault.models.password_entry import PasswordEntry
from modules.password_vault.models.password_category import PasswordCategory
from modules.password_vault.core.database import (
    load_all_passwords, delete_password,
    update_last_accessed, get_password_statistics, toggle_favorite,
    load_all_categories
)
from modules.password_vault.core.filter_engine import (
    filter_entries, sort_entries,
    FILTER_ALL, FILTER_FAVORITES, FILTER_WEAK, FILTER_AGING, FILTER_OLD,
    FILTER_RECENTLY_USED, FILTER_UNCATEGORIZED,
    SORT_TITLE, SORT_MODIFIED, SORT_ACCESSED, SORT_STRENGTH
)
from modules.password_vault.core.aging_engine import (
    analyze_entry, get_aging_color,
    AGE_STATUS_FRESH, AGE_STATUS_AGING, AGE_STATUS_OLD, AGE_STATUS_CRITICAL
)
from modules.password_vault.core.commands import (
    register_password_commands,
    PWV_CREATE, PWV_SEARCH, PWV_GENERATE, PWV_AUDIT,
    PWV_IMPORT, PWV_EXPORT, PWV_RESTORE,
    PWV_SHOW_FAVORITES, PWV_SHOW_WEAK, PWV_SHOW_AGING,
    FILTER_ALL as _FILTER_ALL_UNUSED
) if False else None

from modules.password_vault.core.commands import (
    register_password_commands,
    PWV_CREATE, PWV_SEARCH, PWV_GENERATE, PWV_AUDIT,
    PWV_IMPORT, PWV_EXPORT, PWV_RESTORE,
    PWV_SHOW_FAVORITES, PWV_SHOW_WEAK, PWV_SHOW_AGING
)
from modules.password_vault.ui.password_editor import (
    PasswordEditor, decrypt_file_to_memory_string
)


STRENGTH_COLOURS = {
    "Very Strong": Theme.SUCCESS,
    "Strong":      Theme.SUCCESS,
    "Fair":        Theme.WARNING,
    "Weak":        Theme.ERROR,
}


SORT_OPTIONS = [
    ("Title A-Z",           SORT_TITLE,    True),
    ("Title Z-A",           SORT_TITLE,    False),
    ("Recently Modified",   SORT_MODIFIED, False),
    ("Recently Accessed",   SORT_ACCESSED, False),
    ("Weakest First",       SORT_STRENGTH, True),
    ("Strongest First",     SORT_STRENGTH, False),
]


class PasswordVaultDashboard(tk.Frame):
    """Main Password Vault dashboard with filter sidebar."""

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
        self._on_close            = on_close

        self._passwords:      list[PasswordEntry]    = []
        self._categories:     list[PasswordCategory] = []
        self._active_filter:  str = FILTER_ALL
        self._active_category: Optional[int] = None
        self._search_query:   str = ""
        self._sort_by:        str = SORT_TITLE
        self._sort_asc:       bool = True

        self._build()
        self._load_data()
        self._register_commands()

    def _register_commands(self) -> None:
        """Register Password Vault commands with the platform Command Registry."""
        try:
            # Get command registry from parent chain
            root = self.master
            while root and not hasattr(root, "_command_registry"):
                root = root.master
            if root is None or root._command_registry is None:
                return

            handlers = {
                PWV_CREATE:         self._handle_add,
                PWV_GENERATE:       self._cmd_open_generator,
                PWV_AUDIT:          self._show_security_dashboard,
                PWV_IMPORT:         self._handle_import_csv,
                PWV_EXPORT:         self._handle_export_vault,
                PWV_RESTORE:        self._handle_restore_vault,
                PWV_SHOW_FAVORITES: lambda: self._set_filter("favorites"),
                PWV_SHOW_WEAK:      lambda: self._set_filter("weak"),
                PWV_SHOW_AGING:     lambda: self._set_filter("aging"),
            }
            register_password_commands(root._command_registry, handlers)
        except Exception as error:
            print(f"[PasswordVault] Command registration failed: {error}")

    def _cmd_open_generator(self) -> None:
        """Command handler: open standalone generator."""
        from modules.password_vault.ui.generator_dialog import GeneratorDialog
        GeneratorDialog(
            parent    = self,
            on_accept = lambda pwd: self._clipboard.copy_text(
                pwd, "password_vault", auto_clear_seconds=30
            )
        )
        self._notifications.info("Generated password copied. Clears in 30s.")

    def _build(self) -> None:
        self.pack(fill="both", expand=True)
        self._build_header()

        body = tk.Frame(self, bg=Theme.BACKGROUND)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main(body)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=Theme.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🔒",
            font=("Segoe UI", 22),
            bg=Theme.PANEL,
            fg=Theme.HIGHLIGHT
        ).pack(side="left", padx=(20, 8), pady=12)

        tk.Label(
            header,
            text="Password Vault",
            font=Theme.FONT_HEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left", pady=12)

        tk.Button(
            header,
            text="＋  Add Password",
            font=Theme.FONT_BUTTON,
            bg=Theme.HIGHLIGHT,
            fg="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_add
        ).pack(side="right", padx=(0, 16), pady=12)

        tk.Button(
            header,
            text="🛡  Security",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._show_security_dashboard
        ).pack(side="right", padx=(0, 6), pady=12)

        tk.Button(
            header,
            text="📥  Import CSV",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_import_csv
        ).pack(side="right", padx=(0, 6), pady=12)

        tk.Button(
            header,
            text="📤  Export Vault",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_export_vault
        ).pack(side="right", padx=(0, 6), pady=12)

        tk.Button(
            header,
            text="🔄  Restore",
            font=Theme.FONT_BODY,
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._handle_restore_vault
        ).pack(side="right", padx=(0, 6), pady=12)

    def _build_sidebar(self, parent: tk.Widget) -> None:
        sidebar = tk.Frame(parent, bg=Theme.PANEL, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="FILTERS",
            font=Theme.FONT_LABEL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", padx=16, pady=(16, 6))

        self._filter_buttons = {}

        filters = [
            ("📋  All Passwords",     FILTER_ALL),
            ("⭐  Favorites",         FILTER_FAVORITES),
            ("⚠  Weak",               FILTER_WEAK),
            ("🕒  Aging (90+ days)",  FILTER_AGING),
            ("⏰  Old (180+ days)",   FILTER_OLD),
            ("👁  Recently Used",     FILTER_RECENTLY_USED),
            ("📂  Uncategorized",     FILTER_UNCATEGORIZED),
        ]

        for label, filter_id in filters:
            btn = tk.Button(
                sidebar,
                text=label,
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT,
                activebackground=Theme.ACCENT,
                relief="flat",
                anchor="w",
                padx=16,
                pady=6,
                cursor="hand2",
                command=lambda f=filter_id: self._set_filter(f)
            )
            btn.pack(fill="x", padx=4)
            self._filter_buttons[filter_id] = btn

        # Categories section
        tk.Label(
            sidebar,
            text="CATEGORIES",
            font=Theme.FONT_LABEL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", padx=16, pady=(20, 6))

        self._categories_frame = tk.Frame(sidebar, bg=Theme.PANEL)
        self._categories_frame.pack(fill="x")

        self._highlight_filter()

    def _build_main(self, parent: tk.Widget) -> None:
        main = tk.Frame(parent, bg=Theme.BACKGROUND)
        main.pack(side="left", fill="both", expand=True)

        # Toolbar
        toolbar = tk.Frame(main, bg=Theme.PANEL, height=44)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text="🔍",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=(16, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._on_search())

        tk.Entry(
            toolbar,
            textvariable=self._search_var,
            font=Theme.FONT_BODY,
            bg=Theme.ENTRY_BG,
            fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief="flat",
            bd=6,
            width=30
        ).pack(side="left", ipady=3, pady=6)

        tk.Label(
            toolbar,
            text="  Sort:",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(side="left", padx=(12, 4))

        self._sort_var = tk.StringVar(value="Title A-Z")
        sort_menu = tk.OptionMenu(
            toolbar,
            self._sort_var,
            *[label for label, _, _ in SORT_OPTIONS],
            command=self._on_sort_change
        )
        sort_menu.config(
            bg=Theme.ACCENT,
            fg=Theme.TEXT,
            activebackground=Theme.HIGHLIGHT,
            relief="flat",
            highlightthickness=0
        )
        sort_menu["menu"].config(bg=Theme.ACCENT, fg=Theme.TEXT)
        sort_menu.pack(side="left", pady=6)

        # Stats
        self._stats_frame = tk.Frame(main, bg=Theme.BACKGROUND)
        self._stats_frame.pack(fill="x", padx=16, pady=8)

        # List area
        list_container = tk.Frame(main, bg=Theme.BACKGROUND)
        list_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        canvas = tk.Canvas(list_container, bg=Theme.BACKGROUND, highlightthickness=0)
        sb = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        self._list_inner = tk.Frame(canvas, bg=Theme.BACKGROUND)
        win = canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._list_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width)
        )

    def _load_data(self) -> None:
        self._passwords  = load_all_passwords()
        self._categories = load_all_categories()
        self._render_categories()
        self._render_stats()
        self._render_list()

    def _render_categories(self) -> None:
        for widget in self._categories_frame.winfo_children():
            widget.destroy()

        for cat in self._categories:
            count = f"  ({cat.entry_count})" if cat.entry_count > 0 else ""
            btn = tk.Button(
                self._categories_frame,
                text=f"{cat.icon}  {cat.name}{count}",
                font=Theme.FONT_BODY,
                bg=Theme.PANEL,
                fg=Theme.TEXT,
                activebackground=Theme.ACCENT,
                relief="flat",
                anchor="w",
                padx=16,
                pady=5,
                cursor="hand2",
                command=lambda c=cat: self._set_category_filter(c.id)
            )
            btn.pack(fill="x", padx=4)

    def _render_stats(self) -> None:
        for widget in self._stats_frame.winfo_children():
            widget.destroy()

        stats = get_password_statistics()

        cards = [
            ("Total",     str(stats["total_passwords"]),    Theme.TEXT),
            ("Favorites", str(stats["favorite_passwords"]), Theme.HIGHLIGHT),
            ("Weak",      str(stats["weak_passwords"]),     Theme.WARNING),
            ("Categories",str(stats["categories"]),         Theme.SUBTLE),
        ]

        for label, value, colour in cards:
            card = tk.Frame(self._stats_frame, bg=Theme.PANEL, padx=16, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=4)

            tk.Label(
                card,
                text=value,
                font=("Segoe UI", 16, "bold"),
                bg=Theme.PANEL,
                fg=colour
            ).pack()

            tk.Label(
                card,
                text=label,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack()

    def _on_search(self) -> None:
        self._search_query = self._search_var.get()
        self._render_list()

    def _on_sort_change(self, selected_label: str) -> None:
        for label, sort_by, ascending in SORT_OPTIONS:
            if label == selected_label:
                self._sort_by  = sort_by
                self._sort_asc = ascending
                break
        self._render_list()

    def _set_filter(self, filter_type: str) -> None:
        self._active_filter   = filter_type
        self._active_category = None
        self._highlight_filter()
        self._render_list()

    def _set_category_filter(self, category_id: int) -> None:
        self._active_filter   = FILTER_ALL
        self._active_category = category_id
        self._highlight_filter()
        self._render_list()

    def _highlight_filter(self) -> None:
        for filter_id, btn in self._filter_buttons.items():
            if filter_id == self._active_filter and self._active_category is None:
                btn.config(bg=Theme.ACCENT)
            else:
                btn.config(bg=Theme.PANEL)

    def _render_list(self) -> None:
        for widget in self._list_inner.winfo_children():
            widget.destroy()

        filtered = filter_entries(
            self._passwords,
            filter_type   = self._active_filter,
            category_id   = self._active_category,
            search_query  = self._search_query
        )
        entries = sort_entries(filtered, self._sort_by, self._sort_asc)

        if not entries:
            self._render_empty()
            return

        for entry in entries:
            self._render_entry_row(entry)

    def _render_empty(self) -> None:
        tk.Label(
            self._list_inner,
            text="🔑",
            font=("Segoe UI", 40),
            bg=Theme.BACKGROUND,
            fg=Theme.SUBTLE
        ).pack(pady=(60, 8))

        tk.Label(
            self._list_inner,
            text="No passwords match this filter.",
            font=Theme.FONT_SUBHEADING,
            bg=Theme.BACKGROUND,
            fg=Theme.TEXT
        ).pack()

    def _render_entry_row(self, entry: PasswordEntry) -> None:
        row = tk.Frame(self._list_inner, bg=Theme.PANEL, padx=16, pady=12)
        row.pack(fill="x", padx=4, pady=3)

        left = tk.Frame(row, bg=Theme.PANEL)
        left.pack(side="left", fill="x", expand=True)

        title_row = tk.Frame(left, bg=Theme.PANEL)
        title_row.pack(fill="x", anchor="w")

        # Favorite star button (clickable)
        star_text = "⭐" if entry.is_favorite else "☆"
        star_color = Theme.HIGHLIGHT if entry.is_favorite else Theme.SUBTLE
        tk.Button(
            title_row,
            text=star_text,
            font=("Segoe UI", 12),
            bg=Theme.PANEL,
            fg=star_color,
            relief="flat",
            cursor="hand2",
            command=lambda e=entry: self._toggle_favorite(e)
        ).pack(side="left", padx=(0, 4))

        tk.Label(
            title_row,
            text=entry.title,
            font=Theme.FONT_SUBHEADING,
            bg=Theme.PANEL,
            fg=Theme.TEXT
        ).pack(side="left")

        colour = STRENGTH_COLOURS.get(entry.strength_label(), Theme.SUBTLE)
        tk.Label(
            title_row,
            text=f"  ● {entry.strength_label()}",
            font=Theme.FONT_SMALL,
            bg=Theme.PANEL,
            fg=colour
        ).pack(side="left")

        # Age badge
        aging = analyze_entry(entry)
        if aging.status in (AGE_STATUS_AGING, AGE_STATUS_OLD, AGE_STATUS_CRITICAL):
            age_color = get_aging_color(aging.status)
            age_text  = f"  🕒 {aging.label} ({aging.age_days}d)"
            tk.Label(
                title_row,
                text=age_text,
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=age_color
            ).pack(side="left")

        tk.Label(
            left,
            text=f"👤  {entry.username}",
            font=Theme.FONT_BODY,
            bg=Theme.PANEL,
            fg=Theme.SUBTLE
        ).pack(anchor="w", pady=(2, 0))

        if entry.url:
            tk.Label(
                left,
                text=f"🌐  {entry.display_url()}",
                font=Theme.FONT_SMALL,
                bg=Theme.PANEL,
                fg=Theme.SUBTLE
            ).pack(anchor="w")

        actions = tk.Frame(row, bg=Theme.PANEL)
        actions.pack(side="right")

        for text, cmd in [
            ("📋 User", lambda e=entry: self._copy_username(e)),
            ("🔑 Pass", lambda e=entry: self._copy_password(e)),
            ("✏  Edit", lambda e=entry: self._handle_edit(e)),
            ("🗑",      lambda e=entry: self._handle_delete(e)),
        ]:
            tk.Button(
                actions,
                text=text,
                font=Theme.FONT_SMALL,
                bg=Theme.ACCENT,
                fg=Theme.TEXT,
                relief="flat",
                padx=8,
                pady=4,
                cursor="hand2",
                command=cmd
            ).pack(side="left", padx=2)

    def _toggle_favorite(self, entry: PasswordEntry) -> None:
        new_state = not entry.is_favorite
        if toggle_favorite(entry.id, new_state):
            entry.is_favorite = new_state
            platform_bus.publish("password.favorite_changed", {
                "entry_id":    entry.id,
                "is_favorite": new_state
            })
            self._activity_service.record(
                "PasswordFavorited" if new_state else "PasswordUnfavorited",
                "password_vault",
                entry.title
            )
            self._load_data()

    def _handle_restore_vault(self) -> None:
        """Restore from an encrypted .pvexport package."""
        from tkinter import filedialog, simpledialog
        from pathlib import Path
        from modules.password_vault.core.vault_import import (
            read_package_preview, restore_package
        )
        from modules.password_vault.ui.recovery_dialog import RecoveryPreviewDialog

        # Select file
        file_str = filedialog.askopenfilename(
            title     = "Select Password Vault Export",
            filetypes = [
                ("Password Vault Export", "*.pvexport"),
                ("All Files", "*.*")
            ],
            parent = self
        )
        if not file_str:
            return

        file_path = Path(file_str)

        # Prompt for package password
        package_password = simpledialog.askstring(
            "Package Password",
            "Enter the master password used when this package was created:",
            show="●",
            parent=self
        )
        if not package_password:
            return

        # Read and validate package
        success, error, preview = read_package_preview(file_path, package_password)

        if not success:
            self._notifications.error(error)
            self._dialogs.error("Recovery Failed", error)
            return

        # Show preview dialog
        def on_confirm(skip_duplicates: bool) -> None:
            self._execute_restore(preview, skip_duplicates)

        RecoveryPreviewDialog(
            parent     = self,
            preview    = preview,
            on_confirm = on_confirm
        )

    def _execute_restore(self, preview, skip_duplicates: bool) -> None:
        """Execute the restore after user confirms."""
        from modules.password_vault.core.vault_import import restore_package
        from vaultcore.event_bus import platform_bus

        result = restore_package(preview, skip_duplicates=skip_duplicates)

        if not result.success:
            self._notifications.error(result.error)
            self._dialogs.error("Restore Failed", result.error)
            return

        # Publish event
        platform_bus.publish("password.recovery_completed", {
            "imported":   result.imported,
            "duplicates": result.duplicates,
            "history":    result.history_added
        })

        # Log
        self._activity_service.record(
            "PasswordRecovery", "password_vault",
            f"{result.imported} restored"
        )

        # Notify
        self._notifications.success(f"Restored {result.imported} entries.")

        # Detail dialog
        self._dialogs.success(
            "Recovery Complete",
            f"Imported:      {result.imported}\n"
            f"Duplicates:    {result.duplicates}\n"
            f"History:       {result.history_added}\n"
            f"Failed:        {result.failed}"
        )

        # Refresh
        self._load_data()

    def _handle_export_vault(self) -> None:
        """Export the entire Password Vault as an encrypted package."""
        from tkinter import filedialog
        from pathlib import Path
        from modules.password_vault.core.vault_export import export_vault
        from vaultcore.event_bus import platform_bus

        # Confirm
        if not self._dialogs.confirm(
            "Export Password Vault",
            f"Export all {len(self._passwords)} password(s) as an encrypted package?\n\n"
            "The export is encrypted with your master password."
        ):
            return

        # Choose destination
        folder_str = filedialog.askdirectory(
            title  = "Choose Export Destination",
            parent = self
        )
        if not folder_str:
            return

        destination = Path(folder_str)

        # Execute export
        result = export_vault(destination, self._master_password)

        if not result.success:
            self._notifications.error(result.error)
            self._dialogs.error("Export Failed", result.error)
            return

        # Publish event
        platform_bus.publish("password.export_completed", {
            "entries":  result.entry_count,
            "history":  result.history_count,
            "path":     result.file_path
        })

        # Log activity
        self._activity_service.record(
            "PasswordExport", "password_vault",
            f"{result.entry_count} entries exported"
        )

        # Notify
        self._notifications.success(f"Exported {result.entry_count} entries.")
        self._dialogs.success(
            "Export Complete",
            f"Exported {result.entry_count} password(s) and "
            f"{result.history_count} history record(s).\n\n"
            f"Location:\n{result.file_path}"
        )

    def _handle_import_csv(self) -> None:
        """Open CSV import workflow."""
        from pathlib import Path
        from tkinter import filedialog
        from modules.password_vault.core.csv_import import (
            parse_csv, detect_duplicates
        )
        from modules.password_vault.ui.import_dialog import ImportPreviewDialog

        file_str = filedialog.askopenfilename(
            title     = "Select Browser CSV Export",
            filetypes = [("CSV Files", "*.csv"), ("All Files", "*.*")],
            parent    = self
        )

        if not file_str:
            return

        file_path = Path(file_str)
        rows, error = parse_csv(file_path)

        if error:
            self._notifications.error(f"CSV parse failed: {error}")
            return

        if not rows:
            self._notifications.warning("CSV contains no data rows.")
            return

        # Detect duplicates
        detect_duplicates(rows, self._passwords)

        # Show preview
        ImportPreviewDialog(
            parent     = self,
            rows       = rows,
            on_confirm = self._execute_import
        )

    def _execute_import(self, rows, skip_duplicates: bool) -> None:
        """Perform the actual import after user confirmation."""
        from modules.password_vault.core.database import insert_password
        from modules.password_vault.models.password_entry import PasswordEntry
        from modules.password_vault.core.strength import analyze_password
        from modules.password_vault.ui.password_editor import encrypt_string
        from modules.password_vault.core.csv_import import ImportReport
        from vaultcore.event_bus import platform_bus

        report = ImportReport(rows_found=len(rows))

        for row in rows:
            if not row.is_valid:
                report.invalid += 1
                continue

            if row.is_duplicate and skip_duplicates:
                report.duplicates += 1
                continue

            try:
                # Encrypt password
                encrypted = encrypt_string(row.password, self._master_password)
                if not encrypted:
                    report.failed += 1
                    continue

                # Analyze strength
                strength = analyze_password(row.password)

                # Create entry
                entry = PasswordEntry(
                    id                 = None,
                    title              = row.title,
                    username           = row.username,
                    password_encrypted = encrypted,
                    url                = row.url,
                    category_id        = None,
                    notes              = row.notes,
                    strength_score     = strength.score
                )

                if insert_password(entry) is not None:
                    report.imported += 1
                else:
                    report.failed += 1

            except Exception:
                report.failed += 1

        # Publish event
        platform_bus.publish("password.import_completed", {
            "imported":   report.imported,
            "skipped":    report.skipped,
            "duplicates": report.duplicates,
            "invalid":    report.invalid
        })

        # Log activity
        self._activity_service.record(
            "PasswordImport", "password_vault",
            f"{report.imported} imported"
        )

        # Show result
        self._notifications.success(
            f"Imported {report.imported} password(s). "
            f"Skipped: {report.duplicates + report.invalid}"
        )

        # Show plaintext CSV warning
        self._dialogs.warning(
            "Security Reminder",
            "The imported CSV file contains plaintext passwords.\n\n"
            "Consider securely deleting the CSV file after successful import.\n\n"
            "How to delete depends on your operating system and storage type. "
            "Secure deletion cannot be guaranteed on SSDs or cloud storage."
        )

        # Refresh
        self._load_data()

    def _show_security_dashboard(self) -> None:
        """Open the vault security dashboard."""
        from modules.password_vault.ui.security_dashboard import SecurityDashboard
        SecurityDashboard(
            parent           = self,
            master_password  = self._master_password,
            notifications    = self._notifications,
            activity_service = self._activity_service
        )

    def _handle_add(self) -> None:
        PasswordEditor(
            parent          = self,
            master_password = self._master_password,
            entry           = None,
            on_saved        = self._on_saved
        )

    def _handle_edit(self, entry: PasswordEntry) -> None:
        PasswordEditor(
            parent          = self,
            master_password = self._master_password,
            entry           = entry,
            on_saved        = self._on_saved
        )

    def _handle_delete(self, entry: PasswordEntry) -> None:
        if self._dialogs.confirm_destructive(
            "Delete Password",
            f"Delete '{entry.title}'?"
        ):
            delete_password(entry.id)
            self._notifications.success(f"Deleted: {entry.title}")
            self._notification_center.add(
                "Password Deleted", f"{entry.title} removed.",
                "info", "password_vault"
            )
            self._activity_service.record(
                "PasswordDeleted", "password_vault", entry.title
            )
            self._load_data()

    def _copy_username(self, entry: PasswordEntry) -> None:
        self._clipboard.copy_text(
            entry.username,
            module_id="password_vault",
            auto_clear_seconds=30
        )
        self._notifications.success("Username copied. Clears in 30s.")
        self._activity_service.record(
            "UsernameCopied", "password_vault", entry.title
        )

    def _copy_password(self, entry: PasswordEntry) -> None:
        decrypted = decrypt_file_to_memory_string(
            entry.password_encrypted, self._master_password
        )
        if not decrypted:
            self._notifications.error("Failed to decrypt password.")
            return

        self._clipboard.copy_text(
            decrypted,
            module_id="password_vault",
            auto_clear_seconds=30
        )
        update_last_accessed(entry.id)
        self._recent_items.record_access(
            item_id=str(entry.id),
            module_id="password_vault",
            name=entry.title,
            item_type="password"
        )
        self._notifications.success("Password copied. Clears in 30s.")
        self._notification_center.add(
            "Password Copied",
            f"{entry.title} - auto-clears in 30 seconds.",
            "info", "password_vault"
        )
        self._activity_service.record(
            "PasswordCopied", "password_vault", entry.title
        )

    def _on_saved(self) -> None:
        self._notifications.success("Password saved.")
        self._activity_service.record(
            "PasswordSaved", "password_vault"
        )
        self._load_data()






