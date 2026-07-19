"""
ProgressModel
-------------
A snapshot of execution progress at one point in time.

Populated by ProgressTracker and carried inside ProgressUpdatedEvent.
The UI renders this without knowing anything about threads.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressModel:
    """Snapshot of execution progress."""

    # Step label — e.g. "Scanning", "Compressing", "Verifying"
    current_step: str = ""

    # Item currently being processed — e.g. a file path
    current_item: str = ""

    # Counts
    items_processed: int = 0
    items_total:     int = 0

    # 0.0 – 100.0
    percentage: float = 0.0

    # Timing
    elapsed_seconds:   float          = 0.0
    estimated_seconds: Optional[float] = None

    # Human-readable status
    status_message: str = ""
