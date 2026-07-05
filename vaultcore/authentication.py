"""
core/authentication.py

Authentication logic for the Personal Document Vault.
Coordinates password hashing, verification, and vault setup.
"""

from vaultcore.hashing import generate_salt, hash_password, verify_password
from vaultcore.database import (
    initialize_database,
    save_vault_settings,
    load_vault_settings,
    update_last_opened
)


def create_vault(password: str) -> bool:
    """
    Initialize a new vault with the given master password.

    Steps performed:
        1. Initialize the database schema.
        2. Generate a random salt.
        3. Hash the master password.
        4. Save the hash and salt to the database.

    Args:
        password: The plaintext master password chosen by the user.

    Returns:
        True if the vault was created successfully.
        False if an error occurred.
    """
    try:
        initialize_database()
        salt = generate_salt()
        password_hash = hash_password(password, salt)
        save_vault_settings(password_hash, salt)
        return True

    except Exception as error:
        print(f"[Authentication] Vault creation failed: {error}")
        return False


def verify_master_password(password: str) -> bool:
    """
    Verify a password attempt against the stored vault credentials.

    Args:
        password: The plaintext password entered by the user.

    Returns:
        True if the password is correct.
        False if incorrect or if vault settings cannot be loaded.
    """
    try:
        settings = load_vault_settings()

        if settings is None:
            return False

        result = verify_password(
            password,
            settings["salt"],
            settings["password_hash"]
        )

        if result:
            update_last_opened()

        return result

    except Exception as error:
        print(f"[Authentication] Verification failed: {error}")
        return False



