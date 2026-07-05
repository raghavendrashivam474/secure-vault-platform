"""
vaultcore/session.py

Session Manager for the Secure Vault Platform.

Maintains the authenticated session state including
login timestamp, last activity, encryption key,
idle timeout, and lock state.

This is one of the most critical VaultCore components.
No module should ever manage session state independently.
"""

from datetime import datetime, timezone
from typing import Optional
from vaultcore.logger import log_event, log_info


class Session:
    """
    Represents a single authenticated platform session.

    Created after successful authentication.
    Destroyed on logout, auto-lock, or platform exit.
    """

    def __init__(self, master_password: str) -> None:
        """
        Create a new authenticated session.

        Args:
            master_password: The verified master password.
                             Held in memory for the session duration.
        """
        self._master_password: str             = master_password
        self._authenticated:   bool            = True
        self._locked:          bool            = False
        self._login_time:      datetime        = datetime.now(timezone.utc)
        self._last_activity:   datetime        = datetime.now(timezone.utc)

        log_event("SessionCreated", f"Login at {self._login_time.isoformat()}")

    @property
    def master_password(self) -> str:
        """Return the session master password."""
        return self._master_password

    @property
    def is_authenticated(self) -> bool:
        """Return True if the session is authenticated."""
        return self._authenticated and not self._locked

    @property
    def is_locked(self) -> bool:
        """Return True if the session is locked."""
        return self._locked

    @property
    def login_time(self) -> datetime:
        """Return the session login timestamp."""
        return self._login_time

    @property
    def last_activity(self) -> datetime:
        """Return the last recorded activity timestamp."""
        return self._last_activity

    def update_activity(self) -> None:
        """Record a user activity event."""
        self._last_activity = datetime.now(timezone.utc)

    def lock(self) -> None:
        """Lock the session without destroying it."""
        self._locked = True
        log_event("SessionLocked")

    def unlock(self, master_password: str) -> bool:
        """
        Attempt to unlock the session.

        Args:
            master_password: The password to verify.

        Returns:
            True if unlock succeeded.
        """
        if master_password == self._master_password:
            self._locked = False
            self._last_activity = datetime.now(timezone.utc)
            log_event("SessionUnlocked")
            return True
        return False

    def destroy(self) -> None:
        """
        Destroy the session and clear sensitive data from memory.

        Called on logout or platform exit.
        """
        self._master_password = ""
        self._authenticated   = False
        self._locked          = True
        log_event("SessionDestroyed")

    def formatted_login_time(self) -> str:
        """Return a formatted login timestamp string."""
        return self._login_time.strftime("%Y-%m-%d %H:%M:%S")

    def idle_seconds(self) -> float:
        """
        Return the number of seconds since last activity.

        Returns:
            Seconds as a float.
        """
        delta = datetime.now(timezone.utc) - self._last_activity
        return delta.total_seconds()


class SessionManager:
    """
    Manages the platform session lifecycle.

    Responsible for creating, storing, retrieving,
    locking, and destroying the active session.
    """

    def __init__(self) -> None:
        """Initialize with no active session."""
        self._session: Optional[Session] = None

    def create_session(self, master_password: str) -> Session:
        """
        Create and store a new authenticated session.

        Args:
            master_password: The verified master password.

        Returns:
            The newly created Session object.
        """
        if self._session:
            self._session.destroy()

        self._session = Session(master_password)
        log_info("New session created.")
        return self._session

    def get_session(self) -> Optional[Session]:
        """
        Return the current session if one exists.

        Returns:
            The active Session or None.
        """
        return self._session

    def is_authenticated(self) -> bool:
        """
        Return True if an active authenticated session exists.

        Returns:
            True if authenticated and unlocked.
        """
        return (
            self._session is not None
            and self._session.is_authenticated
        )

    def is_locked(self) -> bool:
        """
        Return True if the session is locked.

        Returns:
            True if locked or no session exists.
        """
        if self._session is None:
            return True
        return self._session.is_locked

    def lock(self) -> None:
        """Lock the current session."""
        if self._session:
            self._session.lock()

    def destroy_session(self) -> None:
        """Destroy the current session and clear sensitive data."""
        if self._session:
            self._session.destroy()
            self._session = None
            log_info("Session destroyed.")

    def update_activity(self) -> None:
        """Record user activity in the current session."""
        if self._session and self._session.is_authenticated:
            self._session.update_activity()

    def get_master_password(self) -> str:
        """
        Return the master password from the current session.

        Returns:
            The master password string or empty string if no session.
        """
        if self._session and self._session.is_authenticated:
            return self._session.master_password
        return ""
