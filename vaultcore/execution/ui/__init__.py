"""
VaultCore Execution UI
----------------------
Generic UI components tied to the Execution Framework.

Nothing here references a specific module.
Any module using the Execution Engine gets these overlays for free.
"""

from vaultcore.execution.ui.progress_overlay import ProgressOverlay
from vaultcore.execution.ui.progress_overlay_service import ProgressOverlayService

__all__ = [
    "ProgressOverlay",
    "ProgressOverlayService",
]
