"""AI event/agenda-authoring assistant — extracted from `entity_author.py`
(TICKET-0028, BRIEF-0028-d, decision H1).

Same posture as `entity_author.py`: a creator-side draft generator. The
creator types a one-line intent, this module calls the local author model
and returns a structured pre-fill plan for the existing creator-CRUD forms
(`POST /api/agendas`, `POST /api/events`). It writes NO canon — no `event`,
no `event_entity`, no `agenda`, no `agenda_step` row is ever created or
updated here; the creator's accept through the existing routes is the only
write. See "AI entity-authoring assistant" in ARCHITECTURE_DECISIONS.md for
the shared rationale (C3, D1, G1, G2), and the BRIEF-0028-d entry for the
extraction itself.

`generate_agenda_draft` (TICKET-0021, BRIEF-0021-b) and `generate_event_draft`
+ `build_world_roster` (TICKET-0022, BRIEF-0022-b) moved here verbatim —
names unchanged (R7); new decomposition extractions below take the
`_event_*` prefix.
"""

from __future__ import annotations

from sqlmodel import Session, select

from . import llm_parse
from .entity_author import AUTHOR_MODEL
from .models import Entity, PromptTemplate
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .tick_normalize import _EVENT_TYPES


def _load_agenda_draft_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "agenda_generation")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _load_event_draft_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "event_generation")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def generate_agenda_draft(
    owner_kind: str,        # "faction" | "personnage" (French, injected verbatim)
    owner_name: str,
    owner_context: str,     # pre-assembled public context (see the /generate route)
    brief: str,
    db: Session,
) -> dict:
    """Generate an agenda draft — title + 2-to-5 steps (TICKET-0021, BRIEF-0021-b,
    B1/C1/D1).

    Standalone sibling of `entity_author.generate_npc_goals` — agendas aren't
    `entity` rows, so this is NOT a `_TYPE_FIELDS` entry. Pure generate-and-
    return: writes no canon anywhere in this function; the only write is the
    creator's accept through the EXISTING `POST /api/agendas`. C2 (suggested
    goal-name links) is explicitly deferred — the JSON contract carries no
    `linked_goals` key.

    Never raises into the caller — every failure mode (missing template,
    unreachable model, malformed JSON, empty parse) returns
    {"ok": False, "error": "<reason>"}. On success returns {"ok": True,
    "title": str, "steps": [str, ...], "notes": [...]}: `title` is `""` when
    absent/malformed (noted); `steps` keeps trimmed non-empty strings only,
    truncated to 5 (noted on truncation); fewer than 2 is a PARTIAL accept
    (noted), never an error — the creator finishes the shell by hand.
    """
    template = _load_agenda_draft_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-agenda-draft template found"}

    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{owner_kind}", owner_kind or "")
        .replace("{owner_name}", owner_name or "")
        .replace("{owner_context}", owner_context or "")
        .replace("{brief}", brief or "")
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return {"ok": False, "error": "Model returned non-JSON output"}
    if not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed draft"}

    notes: list[str] = []

    title = parsed.get("title")
    title = title.strip() if isinstance(title, str) else ""
    if not title:
        notes.append("Titre absent du brouillon — à saisir manuellement.")

    steps_raw = parsed.get("steps")
    steps: list[str] = []
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if isinstance(item, str) and item.strip():
                steps.append(item.strip())
    if len(steps) > 5:
        steps = steps[:5]
        notes.append("Plus de 5 étapes reçues — tronqué à 5.")
    elif len(steps) < 2:
        notes.append("Moins de 2 étapes générées — compléter manuellement.")

    if not title and not steps:
        return {"ok": False, "error": "Model returned no usable draft"}

    return {"ok": True, "title": title, "steps": steps, "notes": notes}


def build_world_roster(db: Session, world_id: str) -> dict[str, str]:
    """name.casefold() -> entity_id for every active, public entity in the
    world (TICKET-0022, BRIEF-0022-b, J3) — feeds `generate_event_draft`'s
    name resolution for both `location` and `involved_entities`.

    `is_public` is filtered in the `where` clause, not post-filtered in
    Python — `context.py:615` post-filters it after the query, which is the
    pattern NOT to copy: secrets are excluded by query construction at every
    assembler, and this is an assembler. Only `name`/`type` leave this
    function; `internal_name` is never selected (`context.py:530`).

    Ambiguity discipline from `tick.py:_build_roster` (tick.py:929-940): two
    active public entities sharing a casefolded name are BOTH removed so
    resolution fails cleanly instead of guessing, rather than silently
    picking one.
    """
    rows = db.exec(
        select(Entity.id, Entity.name).where(
            Entity.world_id == world_id,
            Entity.status == "active",
            Entity.is_public.is_(True),
        )
    ).all()
    candidates: dict[str, list[str]] = {}
    for entity_id, name in rows:
        candidates.setdefault(name.casefold(), []).append(entity_id)
    return {name: ids[0] for name, ids in candidates.items() if len(ids) == 1}


def _event_draft_call(
    brief: str,
    location_hint: str,
    location_context: str,
    roster: dict[str, str],
    db: Session,
) -> dict:
    """Prompt assembly + model call + parse for `generate_event_draft`.

    Returns {"ok": False, "error": "<reason>"} on any failure mode, else
    {"ok": True, "parsed": dict}.
    """
    template = _load_event_draft_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-event-draft template found"}

    version = current_prompt(db, template)
    roster_names = ", ".join(sorted(roster.keys()))
    user_message = (
        version.user_template
        .replace("{brief}", brief or "")
        .replace("{location_hint}", location_hint or "")
        .replace("{location_context}", location_context or "")
        .replace("{roster_names}", roster_names)
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return {"ok": False, "error": "Model returned non-JSON output"}
    if not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed draft"}
    return {"ok": True, "parsed": parsed}


def _event_resolve_location(
    parsed: dict, location_hint: str, roster: dict[str, str], notes: list[str]
) -> str | None:
    """The creator's pre-selection (location_hint), when present, wins
    outright over the model's own proposal (drafting decision 2) — only the
    disagreement is noted, never silently swallowed."""
    if location_hint:
        location_id = roster.get(location_hint.casefold())
        model_location = parsed.get("location")
        model_location = model_location.strip() if isinstance(model_location, str) else ""
        if model_location and model_location.casefold() != location_hint.casefold():
            notes.append(
                f"lieu proposé par le modèle ({model_location!r}) ignoré — "
                f"le lieu présélectionné ({location_hint!r}) prévaut."
            )
        return location_id
    model_location = parsed.get("location")
    model_location = model_location.strip() if isinstance(model_location, str) else ""
    location_id = roster.get(model_location.casefold()) if model_location else None
    if model_location and location_id is None:
        notes.append(f"lieu non résolu, ignoré : {model_location!r}")
    return location_id


def _event_resolve_involved(
    parsed: dict, roster: dict[str, str], notes: list[str]
) -> list[str]:
    involved_raw = parsed.get("involved_entities")
    involved_entities: list[str] = []
    seen_ids: set[str] = set()
    if isinstance(involved_raw, list):
        for name in involved_raw:
            entity_id = roster.get(str(name).casefold())
            if entity_id:
                if entity_id not in seen_ids:
                    involved_entities.append(entity_id)
                    seen_ids.add(entity_id)
            else:
                notes.append(f"nom non résolu, ignoré : {name!r}")
    return involved_entities


def generate_event_draft(
    brief: str,
    location_hint: str,          # location name, or "" when none pre-selected
    location_context: str,       # pre-assembled public context, see the /generate route
    roster: dict[str, str],      # name.casefold() -> entity_id, see build_world_roster
    db: Session,
) -> dict:
    """Generate an event draft — title, description, type, location and
    involved entities (TICKET-0022, BRIEF-0022-b, I2/J3).

    Standalone sibling of `generate_agenda_draft`/`entity_author.generate_npc_goals`
    — `event` is not an `entity` row, so this is NOT a `_TYPE_FIELDS` entry.
    Pure generate-and-return: writes no canon anywhere in this function; the
    only write is the creator's accept through the EXISTING
    `POST /api/events` (BRIEF-0022-a).

    `knowledge_status` is deliberately never read from `parsed` and never
    appears in the returned dict, even if the model volunteers one (I2): the
    model must never decide what the world knows. Every id returned was
    resolved from `roster` by code; an unresolvable name is dropped with a
    note, never coerced into a plausible id.

    Never raises into the caller — every failure mode (missing template,
    unreachable model, malformed JSON, empty parse) returns
    {"ok": False, "error": "<reason>"}.
    """
    call_result = _event_draft_call(brief, location_hint, location_context, roster, db)
    if not call_result.get("ok"):
        return call_result
    parsed = call_result["parsed"]

    notes: list[str] = []

    title = parsed.get("title")
    title = title.strip() if isinstance(title, str) else ""
    if not title:
        notes.append("Titre absent du brouillon — à saisir manuellement.")

    description = parsed.get("description")
    description = description.strip() if isinstance(description, str) else ""

    if not title and not description:
        return {"ok": False, "error": "Model returned no usable draft"}

    raw_type = str(parsed.get("type") or "").strip().casefold()
    if raw_type in _EVENT_TYPES:
        event_type = raw_type
    else:
        event_type = "other"
        notes.append(f"type {parsed.get('type')!r} inconnu, ramené à 'other'.")

    location_id = _event_resolve_location(parsed, location_hint, roster, notes)
    involved_entities = _event_resolve_involved(parsed, roster, notes)

    return {
        "ok": True,
        "title": title,
        "description": description,
        "type": event_type,
        "location_id": location_id,
        "involved_entities": involved_entities,
        "notes": notes,
    }
