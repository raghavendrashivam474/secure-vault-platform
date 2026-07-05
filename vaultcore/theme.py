"""
vaultcore/theme.py

Shared theme service for the Secure Vault Platform.
Provides consistent colours and fonts across all modules.
"""

from vaultcore.config import COLOURS


class Theme:
    """
    Platform-wide theme definition.

    All modules should reference Theme values
    rather than hardcoding colours or fonts.
    """

    # Colours
    BACKGROUND  = COLOURS["background"]
    PANEL       = COLOURS["panel"]
    ACCENT      = COLOURS["accent"]
    HIGHLIGHT   = COLOURS["highlight"]
    TEXT        = COLOURS["text"]
    SUBTLE      = COLOURS["subtle"]
    ENTRY_BG    = COLOURS["entry_bg"]
    SUCCESS     = COLOURS["success"]
    WARNING     = COLOURS["warning"]
    ERROR       = COLOURS["error"]

    # Fonts
    FONT_TITLE      = ("Segoe UI", 22, "bold")
    FONT_HEADING    = ("Segoe UI", 14, "bold")
    FONT_SUBHEADING = ("Segoe UI", 11, "bold")
    FONT_BODY       = ("Segoe UI", 10)
    FONT_SMALL      = ("Segoe UI", 9)
    FONT_LABEL      = ("Segoe UI", 9, "bold")
    FONT_BUTTON     = ("Segoe UI", 10, "bold")
    FONT_MONO       = ("Courier New", 9)

    @classmethod
    def apply_to_root(cls, root) -> None:
        """
        Apply the platform theme to the root Tkinter window.

        Args:
            root: The main application Tk window.
        """
        root.configure(bg=cls.BACKGROUND)

