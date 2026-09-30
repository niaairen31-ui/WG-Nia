"""Prompt resolution for creator-side authoring usages (TICKET-0098,
BRIEF-0098-D, decision N1 -- extracted verbatim from `lore_prompt.py`, which
now re-exports it for the consultation pipeline).

The one place that touches a `Session` to resolve a `prompt_template` row
for the Lore shell's usages, consultation and writing alike. It owns that
`Session` and nothing else: no canon table, no `Knowledge`, no `Relation`,
no `Entity` -- only `PromptTemplate` and `PromptVersion`
(`lore_isolation.py` R15). Callers that must stay Session-free
(`lore_render.render`, whose isolation is machine-checked) receive a
`RenderSpec` of plain strings instead of an ORM row: a detached
`PromptTemplate`/`PromptVersion` is not inert -- it can lazy-load through
its relationships, which would make it a door back to the database that no
static check could see. A plain string cannot be.

Every usage loaded here resolves through `_author_model` -- all are
`surface="authoring"` in `PROMPT_REGISTRY` -- so `load` hardcodes that
default rather than taking one as a parameter. A usage needing a different
default is a reason to add a parameter then, not to guess one now.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from . import llm_parse
from .models import PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt


@dataclass(frozen=True)
class RenderSpec:
    system_prompt: str
    user_template: str
    model: str


def _author_model() -> str:
    from .entity_author import AUTHOR_MODEL  # lazy: avoids the import cycle (prompt_registry precedent)
    return AUTHOR_MODEL


def load(db: Session, usage: str) -> RenderSpec:
    """Loads the active `prompt_template` head for `usage`, its current
    `prompt_version` text, and its effective model, and returns them as
    plain strings. Raises `LlmParseError` on a missing/inactive head --
    same failure mode `lore_plan.draft_plan` already surfaced for a missing
    template, now shared by every usage that calls through here."""
    template = db.exec(
        select(PromptTemplate)
        .where(PromptTemplate.usage == usage)
        .where(PromptTemplate.is_active == True)  # noqa: E712
    ).first()
    if template is None:
        raise llm_parse.LlmParseError(
            f"prompt_load: no active prompt_template for usage={usage!r}"
        )
    version = current_prompt(db, template)
    return RenderSpec(
        system_prompt=version.system_prompt,
        user_template=version.user_template,
        model=effective_model(template, _author_model()),
    )
