"""Day-declaration extraction passes (TICKET-0075, BRIEF-0075-c — the
extraction-and-concordance step; decision C1: the resolver never authors).

Three SEPARATE model calls read the player's day declaration and pull out
mentions of places, persons and factions — one pass per category, on
purpose, the same discipline as one prompt per surface elsewhere in the
engine. Each pass sees the declaration and a compact, secret-free world
frame (`World.name`/`World.description` — `world` carries no secret column,
so this is not an ad-hoc frame assembled from a per-entity query). **It
never sees the registry**: no `select(` against `Entity`, `Faction` or any
location model appears in this module. Matching mentions against real rows
is `day_concordance.py`'s job, in Python — a lookup cannot hallucinate an
id, a model handed the registry can.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .models import PromptTemplate, World
from .prompt_registry import effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

# Bound on mentions returned per pass (Scope IN item 1). Over the bound,
# truncate and report the count — never silently drop the excess without a
# log line.
MAX_MENTIONS_PER_PASS = 8

# Same mild repetition controls as day_plan's emission call — short,
# low-drift JSON output.
_EXTRACT_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


@dataclass(frozen=True)
class Mention:
    category: str  # "place" | "person" | "faction"
    surface_form: str  # the words the player used
    kind: str  # "named" | "inferred"
    role_hint: Optional[str] = None  # set iff kind == "inferred"


def world_frame(world: Optional[World]) -> str:
    """A compact world frame — name + description only. No per-entity query
    backs this (R2): `World` carries no secret column, so reading it directly
    cannot leak one. Public (BRIEF-0075-g): `day_feasibility.py` reuses this
    EXACT builder rather than assembling a second one — the mini-RECON's D1,
    resolved: the day chain's only per-request "context" is this secret-free
    world frame plus the character's name (looked up the same way
    `day_plan.emit_plan` already does); nothing deeper is ever assembled."""
    if world is None:
        return ""
    parts = [world.name]
    if world.description:
        parts.append(world.description)
    return " — ".join(parts)


def _load_extract_template(usage: str, world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan._load_day_plan_template`'s precedent: world-specific
    template preferred, else the world-agnostic one, else the first found."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == usage,
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _validate_mention(raw: object, category: str) -> Optional[Mention]:
    if not isinstance(raw, dict):
        return None
    surface_form = str(raw.get("surface_form") or "").strip()
    if not surface_form:
        return None
    kind = raw.get("kind")
    if kind not in ("named", "inferred"):
        return None
    role_hint_raw = raw.get("role_hint")
    role_hint = str(role_hint_raw).strip() if role_hint_raw else ""
    # role_hint present when and only when kind == "inferred" (Scope IN item 1).
    if kind == "inferred" and not role_hint:
        return None
    if kind == "named":
        role_hint = ""
    return Mention(category=category, surface_form=surface_form, kind=kind, role_hint=role_hint or None)


def _extract(usage: str, category: str, declaration: str, db: Session) -> list[Mention]:
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    world_id = world.id if world is not None else None

    template = _load_extract_template(usage, world_id, db)
    if template is None:
        raise llm_parse.LlmParseError(f"day_extract: no active prompt_template for usage={usage!r}")
    version = current_prompt(db, template)

    user_msg = (
        version.user_template
        .replace("{declaration}", declaration)
        .replace("{world_frame}", world_frame(world))
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
        format="json",
        options=_EXTRACT_OPTIONS,
    )
    obj = llm_parse.extract_object(raw)
    raw_mentions = obj.get("mentions")
    if not isinstance(raw_mentions, list):
        raw_mentions = []

    if len(raw_mentions) > MAX_MENTIONS_PER_PASS:
        truncated = len(raw_mentions) - MAX_MENTIONS_PER_PASS
        raw_mentions = raw_mentions[:MAX_MENTIONS_PER_PASS]
        _log.info(
            "day_extract: %s truncated %d mention(s) beyond MAX_MENTIONS_PER_PASS=%d",
            usage, truncated, MAX_MENTIONS_PER_PASS,
        )

    mentions: list[Mention] = []
    for item in raw_mentions:
        mention = _validate_mention(item, category)
        if mention is not None:
            mentions.append(mention)
    return mentions


def extract_places(declaration: str, db: Session) -> list[Mention]:
    return _extract("day_extract_place", "place", declaration, db)


def extract_persons(declaration: str, db: Session) -> list[Mention]:
    return _extract("day_extract_person", "person", declaration, db)


def extract_factions(declaration: str, db: Session) -> list[Mention]:
    return _extract("day_extract_faction", "faction", declaration, db)
