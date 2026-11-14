"""The perspective renderer: the answer to a question asked as everybody or as one character, in prose or by code (TICKET-0125, BRIEF-0125-D, C-08; TICKET-0127, C-11).

Every verdict other than `answered` is one fixed sentence, written by code:
the model never explains an absence (INV-58), and an unknown, a secret and
a non-public entity read the same. Asked as a character, the two absence
sentences name him. `answered` goes through `lore_render.render` with the
view's rows only. No database handle here.
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
CHARACTER_NOTHING_KNOWN_MESSAGE = "Rien de ce que {nom} sait ne répond à cette question."
CHARACTER_UNSUPPORTED_MESSAGE = "Cette question ne peut pas recevoir de réponse à partir de ce que {nom} sait."

_DETERMINISTIC = {
    "nothing_known": NOTHING_KNOWN_MESSAGE,
    "unsupported_selector": UNSUPPORTED_MESSAGE,
    "ambiguous_mention": AMBIGUOUS_MESSAGE,
}

_CHARACTER_DETERMINISTIC = {
    "nothing_known": CHARACTER_NOTHING_KNOWN_MESSAGE,
    "unsupported_selector": CHARACTER_UNSUPPORTED_MESSAGE,
    "ambiguous_mention": AMBIGUOUS_MESSAGE,
}


def render_perspective(
    result: PerspectiveResult, question: str, spec: RenderSpec, *, nom: Optional[str] = None,
    exchanges: Optional[list[model_exchange.ModelExchange]] = None,
) -> RenderedAnswer:
    """A non-`answered` verdict is its constant (formatted with `nom` when
    asked as a character), renderer `deterministic`, no model call;
    `answered` is `lore_render.render` over the rows."""
    if result.verdict != "answered":
        if nom is None:
            return RenderedAnswer(_DETERMINISTIC[result.verdict], "deterministic", [])
        return RenderedAnswer(_CHARACTER_DETERMINISTIC[result.verdict].format(nom=nom), "deterministic", [])
    lore_result = LoreResult(
        verdict="answered", rows=result.rows, trace=[], ambiguous_mentions=(),
        unmatched_surface_forms=(), rejection_reason=None,
    )
    return render(lore_result, question, spec, {}, exchanges)


def render_public(
    result: PerspectiveResult, question: str, spec: RenderSpec,
    exchanges: Optional[list[model_exchange.ModelExchange]] = None,
) -> RenderedAnswer:
    """Everybody's answer: `render_perspective` with no character."""
    return render_perspective(result, question, spec, nom=None, exchanges=exchanges)
