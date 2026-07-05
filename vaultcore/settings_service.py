"""
vaultcore/settings_service.py

Shared Settings Service for the Secure Vault Platform.

Centralizes all platform-wide settings.
Modules may read platform settings but should
store module-specific settings separately.
"""

from vaultcore.database import save_setting, load_setting
from vaultcore.logger import log_event


# Default platform settings
DEFAULTS: dict[str, str] = {
    "auto_lock":         "Never",
    "backup_frequency":  "Never",
    "backup_folder":     "backups",
    "theme":             "dark",
    "notifications":     "true",
    "last_backup_date":  "",
}

# Auto-lock options in seconds
AUTO_LOCK_OPTIONS: dict[str, int] = {
    "Never":       0,
    "30 seconds":  30,
    "1 minute":    60,
    "2 minutes":   120,
    "5 minutes":   300,
    "10 minutes":  600,
    "15 minutes":  900,
    "30 minutes":  1800,
}


class SettingsService:
    """
    Manages platform-wide settings persistence.

    Reads from and writes to the app_settings table
    via vaultcore.database. Provides typed accessors
    for commonly used settings.
    """

    def get(self, key: str) -> str:
        """
        Get a setting value by key.

        Args:
            key: The setting key.

        Returns:
            The stored value or the default for that key.
        """
        default = DEFAULTS.get(key, "")
        return load_setting(key, default)

    def set(self, key: str, value: str) -> None:
        """
        Save a setting value.

        Args:
            key:   The setting key.
            value: The value to store.
        """
        save_setting(key, value)
        log_event("SettingChanged", f"{key} = {value}")

    def get_auto_lock_seconds(self) -> int:
        """
        Return the configured auto-lock timeout in seconds.

        Returns:
            Seconds as an integer. 0 means disabled.
        """
        label = self.get("auto_lock")
        return AUTO_LOCK_OPTIONS.get(label, 0)

    def get_all(self) -> dict[str, str]:
        """
        Return all settings with defaults applied.

        Returns:
            A dictionary of all setting key-value pairs.
        """
        from vaultcore.database import load_all_settings
        stored   = load_all_settings()
        combined = dict(DEFAULTS)
        combined.update(stored)
        return combined
