"""AI entity-authoring assistant (NPC) — BRIEF-24.

A creator-side draft generator: the creator types a one-line intent, this
module calls the local author model and returns a structured pre-fill plan
for the existing creator-CRUD form. It writes NO canon — no `entity`, no
`character`, no `knowledge`, no `proposed_mutation`, no `relation` row is
ever created or updated here. The creator edits the draft and accepts it
through the existing author-CRUD path (`cockpit/crud.py`); that accept is
the only write. See "AI entity-authoring assistant" in
ARCHITECTURE_DECISIONS.md for the full rationale (C3, D1, G1, G2).

A1 scope: `character` (NPC) entities only. `_TYPE_FIELDS` is the seam for
adding another entity type later — a config entry, not new code.
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from .models import Entity, PromptTemplate, World
from .ollama_client import OllamaError, chat
from .writes import KNOWLEDGE_LEVELS

# Decision E1: same Ollama runtime as the game model — Ollama evicts/loads
# models on demand, so no manual unload logic is needed. The author model
# differs from the game model; a future swap to the abliterated game model
# is a one-line change to this constant.
AUTHOR_MODEL = "llama3.1:8b"

# Per-type field guidance injected into the user message as {type_fields}.
# Only "character" is populated in this brief (A1) — adding another entity
# type later means adding a key here, not touching the template or parser.
_TYPE_FIELDS: dict[str, str] = {
    "character": (
        'public.name (string) ; public.description (string) ; '
        'public.appearance (string) ; public.backstory (string) ; '
        'public.physical_tier (entier -1..2 : -1 chétif, 0 ordinaire, '
        '1 capable, 2 redoutable) ; public.faction_name (string ou null — '
        "nom exact d'une faction existante, ou null si aucune).\n"
        'secret.knowledge (tableau d\'objets {"subject","level","content"} — '
        'level est un de rumor|suspicious|partial|knows|fully_understands) ; '
        'secret.creator_meta (string ou null — note du créateur sur la '
        "vraie nature ou l'arc prévu du personnage) ; "
        'secret.shared_with (tableau d\'objets {"with","note"} — qui '
        "pourrait déjà savoir ou se douter, et pourquoi)."
    ),
}


def _load_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "entity_generation")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _world_id(db: Session) -> str | None:
    world = db.exec(select(World)).first()
    return world.id if world is not None else None


def _resolve_faction_id(
    db: Session, world_id: str | None, faction_name: Any
) -> tuple[str | None, str | None]:
    """Case-insensitive name match against active `faction` entities.

    Returns (faction_id, note). A miss or a null/empty name leaves
    faction_id blank; a miss additionally returns an "introuvable" note.
    Never creates a faction entity (Scope OUT).
    """
    if not faction_name or not isinstance(faction_name, str):
        return None, None
    stmt = select(Entity).where(Entity.type == "faction")
    if world_id is not None:
        stmt = stmt.where(Entity.world_id == world_id)
    target = faction_name.strip().lower()
    for candidate in db.exec(stmt).all():
        if (candidate.name or "").strip().lower() == target:
            return candidate.id, None
    return None, f"Faction '{faction_name}' introuvable — champ laissé vide"


def _clamp_physical_tier(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(-1, min(2, value))


def _normalize_knowledge(raw: Any, notes: list[str]) -> list[dict]:
    """Validate each secret.knowledge row; drop malformed rows, note each drop.

    `is_secret` is forced TRUE here in code — the model never sets it
    (concealment is structural, never instructional).
    """
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject")
        content = item.get("content")
        if not subject or not content:
            notes.append(
                "Une ligne de savoir secret sans sujet ou contenu a été ignorée"
            )
            continue
        level = item.get("level")
        if level not in KNOWLEDGE_LEVELS or level == "unaware":
            level = "rumor"
        rows.append(
            {
                "subject": subject,
                "level": level,
                "content": content,
                "is_secret": True,
            }
        )
    return rows


def _normalize_shared_with(raw: Any) -> list[dict]:
    """Display-only notes (decision G1) — never written anywhere."""
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if isinstance(item, dict) and item.get("with"):
            rows.append({"with": item.get("with"), "note": item.get("note") or ""})
    return rows


def generate_entity_draft(entity_type: str, brief: str, db: Session) -> dict:
    """Generate a pre-fill draft for the creator-CRUD form.

    Pure generate-and-return: writes no canon anywhere in this function or
    its call path. Never raises into the caller — every failure mode
    (missing template, unreachable model, malformed JSON, empty parse)
    returns {"ok": False, "error": "<reason>"}. On success returns
    {"ok": True, "draft": {...}, "notes": [...]}.
    """
    if entity_type not in _TYPE_FIELDS:
        return {"ok": False, "error": f"Unsupported entity_type {entity_type!r}"}
    if not brief or not brief.strip():
        return {"ok": False, "error": "brief must not be empty"}

    template = _load_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-entity-generation template found"}

    try:
        user_message = template.user_template.format(
            entity_type=entity_type,
            type_fields=_TYPE_FIELDS[entity_type],
            brief=brief,
        )
    except (KeyError, IndexError) as exc:
        return {"ok": False, "error": f"Template formatting failed: {exc}"}

    messages = [
        {"role": "system", "content": template.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=AUTHOR_MODEL, format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"ok": False, "error": "Model returned non-JSON output"}

    if not isinstance(parsed, dict) or not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed draft"}

    public_in = parsed.get("public")
    public_in = public_in if isinstance(public_in, dict) else {}
    secret_in = parsed.get("secret")
    secret_in = secret_in if isinstance(secret_in, dict) else {}

    notes: list[str] = []

    faction_id, faction_note = _resolve_faction_id(
        db, _world_id(db), public_in.get("faction_name")
    )
    if faction_note:
        notes.append(faction_note)

    knowledge_rows = _normalize_knowledge(secret_in.get("knowledge"), notes)
    shared_with_rows = _normalize_shared_with(secret_in.get("shared_with"))

    draft = {
        "public": {
            "name": public_in.get("name") or "",
            "description": public_in.get("description") or "",
            "appearance": public_in.get("appearance") or "",
            "backstory": public_in.get("backstory") or "",
            "physical_tier": _clamp_physical_tier(public_in.get("physical_tier")),
            "faction_id": faction_id,
        },
        "secret": {
            "knowledge": knowledge_rows,
            "creator_meta": secret_in.get("creator_meta") or None,
            "shared_with": shared_with_rows,
        },
    }
    return {"ok": True, "draft": draft, "notes": notes}
