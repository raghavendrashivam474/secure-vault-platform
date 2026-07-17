"""
modules/secure_archive/core/progress_manager.py

Real-time restore progress tracking and statistics.

Operates on RestoreSession. Calculates rate, ETA, percentage.
Emits progress events for UI consumption.
"""

import time
from dataclasses import dataclass
from typing import Optional, Callable

from modules.secure_archive.models.restore_session import RestoreSession
from vaultcore.event_bus import platform_bus
from vaultcore.logger import log_debug


@dataclass
class RestoreStatistics:
    """
    Point-in-time restore statistics.

    Attributes:
        files_processed:  Files done so far.
        files_total:      Total files expected.
        bytes_processed:  Bytes written so far.
        bytes_total:      Total bytes expected.
        percent_complete: 0-100 percentage.
        elapsed_seconds:  Time since start.
        rate_bytes_sec:   Bytes per second.
        rate_files_sec:   Files per second.
        eta_seconds:      Estimated time remaining.
        current_file:     Currently processing file path.
    """
    files_processed:  int   = 0
    files_total:      int   = 0
    bytes_processed:  int   = 0
    bytes_total:      int   = 0
    percent_complete: float = 0.0
    elapsed_seconds:  float = 0.0
    rate_bytes_sec:   float = 0.0
    rate_files_sec:   float = 0.0
    eta_seconds:      float = 0.0
    current_file:     str   = ""

    def formatted_eta(self) -> str:
        """Return ETA as human-readable string."""
        if self.eta_seconds <= 0:
            return "almost done"
        if self.eta_seconds < 60:
            return f"{self.eta_seconds:.0f}s"
        minutes = self.eta_seconds / 60
        return f"{minutes:.1f}m"

    def formatted_rate(self) -> str:
        """Return byte rate as human-readable string."""
        if self.rate_bytes_sec < 1024:
            return f"{self.rate_bytes_sec:.0f} B/s"
        elif self.rate_bytes_sec < 1024 ** 2:
            return f"{self.rate_bytes_sec / 1024:.1f} KB/s"
        else:
            return f"{self.rate_bytes_sec / (1024**2):.1f} MB/s"


class RestoreProgressManager:
    """
    Calculates and emits restore progress statistics.

    Updated after each file restoration.
    """

    def __init__(self) -> None:
        self._last_emit_time: float = 0
        self._emit_interval:  float = 0.5   # Minimum seconds between UI updates

    def calculate(
        self,
        session: RestoreSession,
        current_file: str = ""
    ) -> RestoreStatistics:
        """
        Calculate current statistics from session state.

        Args:
            session:      The active RestoreSession.
            current_file: Path of file currently being processed.

        Returns:
            RestoreStatistics snapshot.
        """
        elapsed = session.elapsed
        files_done = session.files_restored + session.files_failed + session.files_skipped
        files_total = session.files_expected

        percent = 0.0
        if files_total > 0:
            percent = (files_done / files_total) * 100

        rate_bytes = 0.0
        rate_files = 0.0
        eta = 0.0

        if elapsed > 0:
            rate_bytes = session.bytes_restored / elapsed
            rate_files = files_done / elapsed

            remaining_files = files_total - files_done
            if rate_files > 0:
                eta = remaining_files / rate_files

        return RestoreStatistics(
            files_processed  = files_done,
            files_total      = files_total,
            bytes_processed  = session.bytes_restored,
            bytes_total      = session.bytes_expected,
            percent_complete = percent,
            elapsed_seconds  = elapsed,
            rate_bytes_sec   = rate_bytes,
            rate_files_sec   = rate_files,
            eta_seconds      = eta,
            current_file     = current_file
        )

    def emit_progress(
        self,
        session: RestoreSession,
        current_file: str = "",
        force: bool = False
    ) -> Optional[RestoreStatistics]:
        """
        Calculate and emit progress if enough time has passed.

        Args:
            session:      The active RestoreSession.
            current_file: Current file being processed.
            force:        If True, emit regardless of interval.

        Returns:
            RestoreStatistics if emitted, None if throttled.
        """
        now = time.time()

        if not force and (now - self._last_emit_time) < self._emit_interval:
            return None

        stats = self.calculate(session, current_file)

        platform_bus.publish("archive.restore.progress", {
            "session_id":       session.session_id,
            "percent_complete": stats.percent_complete,
            "files_processed":  stats.files_processed,
            "files_total":      stats.files_total,
            "rate":             stats.formatted_rate(),
            "eta":              stats.formatted_eta(),
            "current_file":     stats.current_file
        })

        self._last_emit_time = now

        return stats
