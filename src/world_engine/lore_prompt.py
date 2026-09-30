"""Prompt resolution for the lore consultation chantier (TICKET-0085,
BRIEF-0085-d).

Since TICKET-0098 (BRIEF-0098-D, N1) the loader lives in `prompt_load.py`,
shared with the Lore shell's writing panel, which may not import this
pipeline module (`lore_isolation.py` R17). This module re-exports it so the
consultation pipeline's imports are unchanged.
"""

from __future__ import annotations

from .prompt_load import RenderSpec, load

__all__ = ["RenderSpec", "load"]
