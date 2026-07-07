"""
vaultcore/permission_manager.py

Permission Manager for the Secure Vault Platform.

Provides a permission-check layer for sensitive operations.
Even in an offline application, dangerous actions should
pass through explicit permission gates.
"""

from typing import Callable, Optional
from vaultcore.logger import log_event, log_debug


# Standard protected operations
class Permissions:
    """Standard permission constants."""

    DELETE_DOCUMENT      = "document.delete"
    EXPORT_DOCUMENT      = "document.export"
    BULK_DELETE          = "document.bulk_delete"
    CREATE_BACKUP        = "backup.create"
    RESTORE_BACKUP       = "backup.restore"
    CHANGE_PASSWORD      = "security.change_password"
    CHANGE_SECURITY      = "security.change_settings"
    DELETE_CATEGORY      = "category.delete"
    PERMANENT_REMOVAL    = "storage.permanent_removal"
    EXPORT_VAULT         = "vault.export"
    LOCK_PLATFORM        = "platform.lock"
    EXIT_PLATFORM        = "platform.exit"


class PermissionManager:
    """
    Centralized permission checks for sensitive operations.

    All destructive or security-sensitive actions should
    be gated through this manager.
    """

    def __init__(self) -> None:
        """Initialize with default permissions granted."""
        self._granted: set[str] = {
            Permissions.DELETE_DOCUMENT,
            Permissions.EXPORT_DOCUMENT,
            Permissions.BULK_DELETE,
            Permissions.CREATE_BACKUP,
            Permissions.RESTORE_BACKUP,
            Permissions.CHANGE_PASSWORD,
            Permissions.CHANGE_SECURITY,
            Permissions.DELETE_CATEGORY,
            Permissions.PERMANENT_REMOVAL,
            Permissions.EXPORT_VAULT,
            Permissions.LOCK_PLATFORM,
            Permissions.EXIT_PLATFORM,
        }
        self._confirm_handler: Optional[Callable] = None

    def set_confirm_handler(self, handler: Callable) -> None:
        """
        Set the callback used to prompt for user confirmation.

        Args:
            handler: A callable taking (title, message) returning bool.
        """
        self._confirm_handler = handler

    def is_granted(self, permission: str) -> bool:
        """
        Check whether a permission is granted.

        Args:
            permission: The permission constant to check.

        Returns:
            True if granted.
        """
        return permission in self._granted

    def grant(self, permission: str) -> None:
        """Grant a permission."""
        self._granted.add(permission)
        log_debug(f"[Permission] Granted: {permission}")

    def revoke(self, permission: str) -> None:
        """Revoke a permission."""
        if permission in self._granted:
            self._granted.remove(permission)
            log_debug(f"[Permission] Revoked: {permission}")

    def check_and_confirm(
        self,
        permission: str,
        confirmation_title: str = "Confirm Action",
        confirmation_message: str = "Are you sure?"
    ) -> bool:
        """
        Check permission and prompt user for confirmation.

        Args:
            permission:           The permission to check.
            confirmation_title:   Dialog title.
            confirmation_message: Dialog message.

        Returns:
            True if permission granted and user confirmed.
        """
        if not self.is_granted(permission):
            log_event("PermissionDenied", permission)
            return False

        if self._confirm_handler:
            return self._confirm_handler(
                confirmation_title, confirmation_message
            )

        return True

    def get_all_permissions(self) -> list[str]:
        """Return a list of all granted permissions."""
        return sorted(self._granted)
