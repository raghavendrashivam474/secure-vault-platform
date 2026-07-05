"""
utils/validators.py

Input validation helpers for the Personal Document Vault.
Handles password strength checks and confirmation matching.
"""

from typing import Optional


# Minimum number of characters required for a master password
MINIMUM_PASSWORD_LENGTH: int = 8


def is_empty(value: str) -> bool:
    """Return True if the value is empty or contains only whitespace."""
    return not value or not value.strip()


def meets_minimum_length(password: str) -> bool:
    """Return True if the password meets the minimum length requirement."""
    return len(password) >= MINIMUM_PASSWORD_LENGTH


def passwords_match(password: str, confirmation: str) -> bool:
    """Return True if the password and confirmation are identical."""
    return password == confirmation


def validate_master_password(
    password: str,
    confirmation: str
) -> tuple[bool, Optional[str]]:
    """
    Validate a master password during vault setup.

    Checks performed:
        - Password is not empty
        - Password meets minimum length
        - Confirmation matches password

    Args:
        password:     The master password entered by the user.
        confirmation: The confirmation password entered by the user.

    Returns:
        A tuple of (is_valid, error_message).
        If valid, error_message is None.
        If invalid, error_message describes the problem.
    """
    if is_empty(password):
        return False, "Password cannot be empty."

    if not meets_minimum_length(password):
        return False, f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters."

    if not passwords_match(password, confirmation):
        return False, "Passwords do not match."

    return True, None


def validate_login_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate input on the login screen.

    Only checks that something was entered.
    Full verification happens in the authentication layer.

    Args:
        password: The password entered by the user.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if is_empty(password):
        return False, "Please enter your master password."

    return True, None


