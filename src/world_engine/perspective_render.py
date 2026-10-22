"""The public perspective's renderer: the answer to a public question, in prose or by code (TICKET-0125, BRIEF-0125-D, C-08).

Every verdict other than `answered` is one fixed sentence, written by code:
the model never explains an absence (INV-58), and an unknown, a secret and
a non-public entity read the same. `answered` goes through
`lore_render.render` with the public rows only. No database handle here.
"""

from __future__ import annotations

from typing import Optional

from . import model_exchange
from .lore_prompt import RenderSpec
from .lore_query import LoreResult
from .lore_render import RenderedAnswer, render
from .perspective_query import PerspectiveResult

NOTHING_KNOWN_MESSAGE = "Rien de ce que tout le monde sait ne répond à cette question."
UNSUPPORTED_MESSAGE = "Cette question ne peut pas recevoir de réponse à partir de ce que tout le monde sait."
AMBIGUOUS_MESSAGE = "Plusieurs entités connues portent ce nom. Laquelle ?"

_DETERMINISTIC = {
    "nothing_known": NOTHING_KNOWN_MESSAGE,
    "unsupported_selector": UNSUPPORTED_MESSAGE,
    "ambiguous_mention": AMBIGUOUS_MESSAGE,
}


def render_public(
    result: PerspectiveResult, question: str, spec: RenderSpec,
    exchanges: Optional[list[model_exchange.ModelExchange]] = None,
) -> RenderedAnswer:
    """A non-`answered` verdict is its constant, renderer `deterministic`,
    no model call; `answered` is `lore_render.render` over the rows."""
    if result.verdict != "answered":
        return RenderedAnswer(_DETERMINISTIC[result.verdict], "deterministic", [])
    lore_result = LoreResult(
        verdict="answered", rows=result.rows, trace=[], ambiguous_mentions=(),
        unmatched_surface_forms=(), rejection_reason=None,
    )
    return render(lore_result, question, spec, {}, exchanges)
