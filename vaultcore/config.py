"""
vaultcore/config.py

Platform-wide configuration constants for the Secure Vault Platform.
"""

from pathlib import Path

# Platform identity
PLATFORM_NAME:    str = "Secure Vault Platform"
PLATFORM_VERSION: str = "0.1.0"

# Paths
BASE_DIR:          Path = Path(".")
DATABASE_DIR:      Path = BASE_DIR / "database"
VAULT_DIR:         Path = BASE_DIR / "vault" / "encrypted"
BACKUP_DIR:        Path = BASE_DIR / "backups"
LOG_DIR:           Path = BASE_DIR / "logs"
ASSETS_DIR:        Path = BASE_DIR / "assets"

# Window
DEFAULT_GEOMETRY:  str  = "1100x680"
MIN_WIDTH:         int  = 900
MIN_HEIGHT:        int  = 550

# Colour palette (shared across all modules)
COLOURS: dict[str, str] = {
    "background":  "#1a1a2e",
    "panel":       "#16213e",
    "accent":      "#0f3460",
    "highlight":   "#e94560",
    "text":        "#eaeaea",
    "subtle":      "#a0a0b0",
    "entry_bg":    "#0d1b2a",
    "success":     "#51cf66",
    "warning":     "#ffd43b",
    "error":       "#ff6b6b",
}

