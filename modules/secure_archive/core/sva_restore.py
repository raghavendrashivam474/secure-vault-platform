"""
modules/secure_archive/core/sva_restore.py

Orchestrates the full .sva restoration pipeline.

Uses the existing Sprint 14 RestoreEngine after decryption.
No restoration logic is duplicated.

Pipeline:
    .sva → SVAReader → decrypt → ArchivePayload
         → adapt to package format → RestoreEngine → RestoreReport
"""

import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from modules.secure_archive.core.sva_reader import (
    SVAReader, SVAReaderError, InvalidSVAFileError,
    UnsupportedSVAVersionError, CorruptedSVAFileError
)
from modules.secure_archive.core.key_derivation import KeyDerivationService
from modules.secure_archive.core.archive_decryptor import (
    ArchiveDecryptor, AuthenticationFailedError,
    PayloadCorruptedError, DecryptionError
)
from modules.secure_archive.core.restore_engine import RestoreEngine
from modules.secure_archive.core.package_writer import (
    MANIFEST_FILENAME, PAYLOAD_PREFIX
)
from modules.secure_archive.models.archive_payload import ArchivePayload
from modules.secure_archive.models.restore_result import RestoreReport
from vaultcore.logger import log_debug, log_event, log_error


@dataclass
class SVARestoreResult:
    """
    Complete SVA restoration result.

    Attributes:
        success:         True if restoration succeeded.
        report:          The underlying RestoreReport (if reached).
        error_type:      Category of failure if any.
        error_message:   Human-readable error message.
    """
    success:       bool
    report:        Optional[RestoreReport] = None
    error_type:    Optional[str]           = None
    error_message: Optional[str]           = None


class SVARestoreOrchestrator:
    """
    Full restoration pipeline for .sva files.

    Reuses Sprint 14 RestoreEngine after decryption.
    """

    def __init__(
        self,
        reader: Optional[SVAReader] = None,
        kdf: Optional[KeyDerivationService] = None,
        decryptor: Optional[ArchiveDecryptor] = None,
        restore_engine: Optional[RestoreEngine] = None
    ) -> None:
        """
        Initialize with injectable services.
        """
        self._reader    = reader        or SVAReader()
        self._kdf       = kdf           or KeyDerivationService()
        self._decryptor = decryptor     or ArchiveDecryptor()
        self._restorer  = restore_engine or RestoreEngine()

    def restore(
        self,
        sva_path: Path,
        password: str,
        destination_root: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> SVARestoreResult:
        """
        Restore an .sva archive to a destination directory.

        Args:
            sva_path:          Path to the .sva file.
            password:          User password.
            destination_root:  Where files will be restored.
            progress_callback: Optional progress callback.

        Returns:
            SVARestoreResult with success flag and details.
        """
        # Step 1: Read the .sva file structure
        try:
            package = self._reader.read(sva_path)
        except FileNotFoundError as error:
            return self._failed("file_not_found", str(error))
        except InvalidSVAFileError as error:
            return self._failed("invalid_format", str(error))
        except UnsupportedSVAVersionError as error:
            return self._failed("unsupported_version", str(error))
        except CorruptedSVAFileError as error:
            return self._failed("corrupted_file", str(error))
        except SVAReaderError as error:
            return self._failed("read_error", str(error))

        log_event(
            "SVARestoreStarted",
            f"{sva_path.name}: {package.file_size:,} bytes"
        )

        # Step 2: Validate password non-empty
        if not password:
            return self._failed(
                "empty_password",
                "Password cannot be empty"
            )

        # Step 3: Derive key from password + salt
        try:
            key = self._kdf.derive_key(
                password  = password,
                salt      = package.header.salt,
                iterations = package.header.kdf_iterations
            )
        except Exception as error:
            log_error(f"[SVARestore] Key derivation failed: {error}")
            return self._failed("kdf_error", "Key derivation failed")

        # Step 4: Decrypt (authenticates first)
        try:
            payload = self._decryptor.decrypt(
                ciphertext = package.encrypted_payload,
                key        = key,
                nonce      = package.header.nonce
            )
        except AuthenticationFailedError as error:
            log_event("SVAAuthenticationFailed", sva_path.name)
            return self._failed("authentication_failed", str(error))
        except PayloadCorruptedError as error:
            return self._failed("payload_corrupted", str(error))
        except DecryptionError as error:
            return self._failed("decryption_error", str(error))
        finally:
            # Clear sensitive material from memory as soon as possible
            key = None

        log_debug(
            f"[SVARestore] Decrypted payload: "
            f"{payload.entry_count} entries"
        )

        # Step 5: Feed decrypted payload into existing restore engine
        # RestoreEngine expects a package file, so we create a temp
        # .sva.dev-format container in memory (ZIP)
        report = self._restore_with_engine(
            payload, destination_root, progress_callback
        )

        # Step 6: Clear payload from memory
        payload = None

        if report is None:
            return self._failed(
                "restore_error",
                "Restoration failed during engine execution"
            )

        log_event(
            "SVARestoreFinished",
            f"{sva_path.name}: {report.files_verified}/{report.files_expected} verified"
        )

        return SVARestoreResult(
            success = report.success,
            report  = report
        )

    def _restore_with_engine(
        self,
        payload: ArchivePayload,
        destination_root: Path,
        progress_callback: Optional[Callable[[int, int, str], None]]
    ) -> Optional[RestoreReport]:
        """
        Create a temporary package and hand to RestoreEngine.

        RestoreEngine expects a .sva.dev ZIP-format package.
        We build one in a temporary file, restore from it,
        then delete the temporary file.
        """
        tmp_path = None
        try:
            # Create a temp .sva.dev-format package
            fd, tmp_name = tempfile.mkstemp(suffix=".sva.dev")
            import os
            os.close(fd)
            tmp_path = Path(tmp_name)

            log_debug(f"[SVARestore] Creating temp package: {tmp_path}")

            # Write ZIP container with manifest + payloads
            with zipfile.ZipFile(
                tmp_path,
                mode="w",
                compression=zipfile.ZIP_STORED
            ) as zf:
                zf.writestr(MANIFEST_FILENAME, payload.manifest.to_bytes())
                for entry in payload.manifest.files:
                    payload_path = PAYLOAD_PREFIX + entry.path
                    compressed = payload.compressed_entries.get(entry.path, b"")
                    zf.writestr(payload_path, compressed)

            # Restore using existing engine
            report = self._restorer.restore(
                package_path       = tmp_path,
                destination_root   = destination_root,
                progress_callback  = progress_callback
            )

            return report

        except Exception as error:
            log_error(f"[SVARestore] Engine handoff failed: {error}")
            return None

        finally:
            # Clean up temp file
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                    log_debug(f"[SVARestore] Cleaned up temp package")
                except Exception:
                    pass

    def _failed(self, error_type: str, message: str) -> SVARestoreResult:
        """Build a failed restore result."""
        return SVARestoreResult(
            success       = False,
            error_type    = error_type,
            error_message = message
        )
