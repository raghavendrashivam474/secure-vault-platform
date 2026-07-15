"""
modules/secure_archive/core/error_mapper.py

Maps internal archive errors to user-friendly messages.

Ensures the UI displays clear, actionable messages while
technical details stay in logs.
"""

from dataclasses import dataclass


# Error category constants
CATEGORY_FILE_ACCESS       = "file_access"
CATEGORY_FORMAT_INVALID    = "format_invalid"
CATEGORY_VERSION_MISMATCH  = "version_mismatch"
CATEGORY_CORRUPTION        = "corruption"
CATEGORY_AUTHENTICATION    = "authentication"
CATEGORY_PASSWORD_MISSING  = "password_missing"
CATEGORY_DECRYPTION        = "decryption"
CATEGORY_RESTORE_FAILED    = "restore_failed"
CATEGORY_UNKNOWN           = "unknown"


@dataclass
class ArchiveErrorInfo:
    """
    User-friendly error information.

    Attributes:
        category:       Error category constant.
        title:          Short title for dialogs.
        message:        User-facing message.
        technical:      Technical detail (for logs, not UI).
        can_retry:      True if user should try again (e.g., wrong password).
    """
    category:  str
    title:     str
    message:   str
    technical: str
    can_retry: bool = False


# Error type → user-friendly mapping
ERROR_MAPPINGS = {
    "file_not_found": ArchiveErrorInfo(
        category  = CATEGORY_FILE_ACCESS,
        title     = "Archive Not Found",
        message   = "The archive file could not be found. Please verify the file path.",
        technical = "",
        can_retry = False
    ),
    "invalid_format": ArchiveErrorInfo(
        category  = CATEGORY_FORMAT_INVALID,
        title     = "Invalid Archive",
        message   = "This file is not a valid Secure Vault Archive.",
        technical = "",
        can_retry = False
    ),
    "unsupported_version": ArchiveErrorInfo(
        category  = CATEGORY_VERSION_MISMATCH,
        title     = "Unsupported Archive Version",
        message   = "This archive was created with an incompatible version of Secure Archive.",
        technical = "",
        can_retry = False
    ),
    "corrupted_file": ArchiveErrorInfo(
        category  = CATEGORY_CORRUPTION,
        title     = "Corrupted Archive",
        message   = "The archive file appears to be damaged or incomplete.",
        technical = "",
        can_retry = False
    ),
    "authentication_failed": ArchiveErrorInfo(
        category  = CATEGORY_AUTHENTICATION,
        title     = "Authentication Failed",
        message   = "The password is incorrect or the archive has been tampered with.",
        technical = "",
        can_retry = True
    ),
    "empty_password": ArchiveErrorInfo(
        category  = CATEGORY_PASSWORD_MISSING,
        title     = "Password Required",
        message   = "Please enter the archive password.",
        technical = "",
        can_retry = True
    ),
    "payload_corrupted": ArchiveErrorInfo(
        category  = CATEGORY_CORRUPTION,
        title     = "Corrupted Archive Payload",
        message   = "The archive payload is corrupted and cannot be parsed.",
        technical = "",
        can_retry = False
    ),
    "decryption_error": ArchiveErrorInfo(
        category  = CATEGORY_DECRYPTION,
        title     = "Decryption Failed",
        message   = "The archive could not be decrypted.",
        technical = "",
        can_retry = False
    ),
    "kdf_error": ArchiveErrorInfo(
        category  = CATEGORY_DECRYPTION,
        title     = "Key Derivation Failed",
        message   = "Could not derive the encryption key from the password.",
        technical = "",
        can_retry = False
    ),
    "restore_error": ArchiveErrorInfo(
        category  = CATEGORY_RESTORE_FAILED,
        title     = "Restoration Failed",
        message   = "The archive was decrypted but files could not be restored.",
        technical = "",
        can_retry = False
    ),
    "read_error": ArchiveErrorInfo(
        category  = CATEGORY_FILE_ACCESS,
        title     = "Read Error",
        message   = "The archive file could not be read.",
        technical = "",
        can_retry = False
    ),
}


class ArchiveErrorMapper:
    """
    Maps internal archive error types to user-friendly information.
    """

    def map(
        self,
        error_type: str,
        technical_detail: str = ""
    ) -> ArchiveErrorInfo:
        """
        Map an error type to user-facing info.

        Args:
            error_type:       Internal error type string.
            technical_detail: Detailed technical message.

        Returns:
            An ArchiveErrorInfo with user-friendly messaging.
        """
        base = ERROR_MAPPINGS.get(error_type)

        if base is None:
            return ArchiveErrorInfo(
                category  = CATEGORY_UNKNOWN,
                title     = "Archive Error",
                message   = "An unexpected error occurred while processing the archive.",
                technical = technical_detail,
                can_retry = False
            )

        # Return a copy with technical detail included
        return ArchiveErrorInfo(
            category  = base.category,
            title     = base.title,
            message   = base.message,
            technical = technical_detail,
            can_retry = base.can_retry
        )

    def format_for_user(self, info: ArchiveErrorInfo) -> str:
        """
        Format error info as a user-facing message.

        Args:
            info: Error info from map().

        Returns:
            Formatted message string.
        """
        return f"{info.title}\n\n{info.message}"

    def format_for_log(self, info: ArchiveErrorInfo) -> str:
        """
        Format error info for log entries.

        Args:
            info: Error info from map().

        Returns:
            Formatted log message with technical detail.
        """
        detail = f"  Detail: {info.technical}" if info.technical else ""
        return f"[{info.category}] {info.title}{detail}"
