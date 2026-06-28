"""AI entity-authoring assistant (NPC, Location) — BRIEF-24, BRIEF-25.

A creator-side draft generator: the creator types a one-line intent, this
module calls the local author model and returns a structured pre-fill plan
for the existing creator-CRUD form. It writes NO canon — no `entity`, no
`character`, no `location`, no `knowledge`, no `proposed_mutation`, no
`relation` row is ever created or updated here. The creator edits the draft
and accepts it through the existing author-CRUD path (`cockpit/crud.py`);
that accept is the only write. See "AI entity-authoring assistant" in
ARCHITECTURE_DECISIONS.md for the full rationale (C3, D1, G1, G2).

`_TYPE_FIELDS` is the config seam for entity types: `character` (BRIEF-24),
`location` (BRIEF-25), and `faction` (BRIEF-32) are populated; item/artifact
are not — adding one of those later is a config entry here, not new code.
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from .context import _SAFE_SUBCULTURE_KEYS
from .models import Entity, PromptTemplate, World
from .ollama_client import OllamaError, chat
from .writes import KNOWLEDGE_LEVELS

_LOCATION_TYPES = ("city", "district", "building", "natural", "underground", "other")
_ACCESS_LEVELS = ("public", "restricted", "secret")
_FACTION_TYPES = ("government", "criminal", "military", "esoteric", "other")

# Decision E1: same Ollama runtime as the game model — Ollama evicts/loads
# models on demand, so no manual unload logic is needed. The author model
# differs from the game model; a future swap to the abliterated game model
# is a one-line change to this constant.
AUTHOR_MODEL = "llama3.1:8b"

# Per-type field guidance injected into the user message as {type_fields}.
# "character" (BRIEF-24), "location" (BRIEF-25), and "faction" (BRIEF-32) are
# populated — adding another entity type later means adding a key here, not
# touching the template or parser.
_TYPE_FIELDS: dict[str, str] = {
    "character": (
        'public.name (string) ; public.description (string) ; '
        'public.appearance (string) ; public.backstory (string) ; '
        'public.aversion (string — ce que ce personnage rejette ou fuit : '
        'un concept, une catégorie ou un phénomène, ex. la technologie, le '
        'soleil ; PAS une entité nommée) ; '
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
    "location": (
        'public.name (string) ; public.description (string) ; '
        'public.location_type (un de city|district|building|natural|'
        'underground|other) ; public.access_level (un de public|restricted|'
        'secret) ; public.subculture (objet JSON — uniquement des clés parmi '
        f"{', '.join(_SAFE_SUBCULTURE_KEYS)} ; n'invente pas d'autre clé).\n"
        'secret.subculture_hidden (string — ce que ce lieu cache vraiment, '
        "inaccessible sans découverte en jeu) ; "
        'secret.sensed_links (tableau d\'objets {"kind","name","note"} — '
        "kind est un de parent|connection|faction|other ; un lieu parent, un "
        "lieu voisin, ou une faction qui contrôle ou influence ce lieu, "
        "perceptible mais non confirmé)."
    ),
    "faction": (
        "public.name — nom de la faction\n"
        "public.description — présentation publique : ce que le monde sait d'elle\n"
        "public.faction_type — exactement un parmi : government | criminal | military | esoteric | other\n"
        "public.philosophy — credo affiché, valeurs revendiquées publiquement\n"
        "public.internal_structure — forme d'organisation CONNAISSABLE, en prose "
        "(ex. « un conseil de sept anciens »). DOIT rester cohérente avec la liste roles.\n"
        "public.roles — liste ORDONNÉE du rang le plus élevé au plus bas. Chaque "
        'entrée est un objet { "name": <intitulé du rang>, "description": <une '
        "phrase décrivant la fonction du rang> }. DOIT refléter internal_structure.\n"
        "public.aversion — ce que la faction rejette ou combat : un concept ou "
        "une catégorie (ex. la technologie, la magie, les étrangers), PAS une "
        "entité nommée (les inimitiés envers une entité précise relèvent des "
        "relations)\n"
        "secret.internal_tensions — fractures, rivalités, faiblesses non avouées (créateur seul)\n"
        "secret.goals — le véritable agenda de la faction : ce qu'elle cherche réellement "
        "à accomplir, par-delà son credo affiché (créateur seul)"
    ),
}


def _load_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "entity_generation")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _load_world_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "world_generation")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _load_player_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "player_generation")
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


def _normalize_player_knowledge(raw: Any) -> list[dict]:
    """Validate each proposed PC knowledge row; drop malformed rows.

    Unlike `_normalize_knowledge` (NPC-only, forces `is_secret=True`), this
    does NOT set `is_secret` — the draft is data only; `is_secret=False` is
    applied at write time by the accept route (BRIEF-52, D1). Caps at 5 rows.
    """
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject")
        content = item.get("content")
        if not isinstance(subject, str) or not subject.strip():
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        level = item.get("level")
        if level not in KNOWLEDGE_LEVELS:
            level = "rumor"
        rows.append({"subject": subject, "level": level, "content": content})
        if len(rows) >= 5:
            break
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


def _validate_location_type(raw: Any, notes: list[str]) -> str:
    if isinstance(raw, str) and raw in _LOCATION_TYPES:
        return raw
    notes.append(
        f"Type de lieu '{raw}' non reconnu ou absent — repli sur 'other'"
    )
    return "other"


def _validate_access_level(raw: Any, notes: list[str]) -> str | None:
    """Decision: a missing/unrecognised access level is left BLANK for the
    creator to set — never defaulted to a permissive value (item 4)."""
    if isinstance(raw, str) and raw in _ACCESS_LEVELS:
        return raw
    notes.append(
        f"Niveau d'accès '{raw}' non reconnu ou absent — laissé vide pour le créateur"
    )
    return None


def _filter_subculture_public(raw: Any, notes: list[str]) -> dict:
    """B1 — the structural core of this brief.

    Reads the LIVE `_SAFE_SUBCULTURE_KEYS` constant (imported, never
    hardcoded) as the source of truth. Any key the model proposes under
    `public.subculture` that is not in that allow-list is dropped and
    noted; it can never reach the public region. `"hidden"` is not in the
    allow-list, so it cannot be set from here — it can only ever come from
    `secret.subculture_hidden` (see `generate_entity_draft`).
    """
    public: dict = {}
    if not isinstance(raw, dict):
        return public
    for key, value in raw.items():
        if key in _SAFE_SUBCULTURE_KEYS:
            public[key] = value
        else:
            notes.append(f"Clé subculture '{key}' hors allow-list — ignorée")
    return public


def _validate_faction_type(raw: Any, notes: list[str]) -> str:
    if isinstance(raw, str) and raw in _FACTION_TYPES:
        return raw
    notes.append(
        f"Type de faction '{raw}' non reconnu ou absent — repli sur 'other'"
    )
    return "other"


def _normalize_roles(raw: Any, notes: list[str]) -> list[dict]:
    """Validate each proposed faction role; drop nameless rows, note each drop.

    Order is preserved (order = rank). Unknown keys per entry are dropped;
    a missing description becomes an empty string.
    """
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            notes.append("Rôle proposé sans nom — ignoré")
            continue
        description = item.get("description")
        rows.append(
            {
                "name": name,
                "description": description if isinstance(description, str) else "",
            }
        )
    return rows


def _normalize_sensed_links(raw: Any) -> list[dict]:
    """Display-only notes (D1) — never resolved, never written anywhere."""
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        kind = item.get("kind")
        if kind not in ("parent", "connection", "faction", "other"):
            kind = "other"
        rows.append({"kind": kind, "name": name, "note": item.get("note") or ""})
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

    if entity_type == "location":
        subculture_public = _filter_subculture_public(
            public_in.get("subculture"), notes
        )
        draft = {
            "public": {
                "name": public_in.get("name") or "",
                "description": public_in.get("description") or "",
                "location_type": _validate_location_type(
                    public_in.get("location_type"), notes
                ),
                "access_level": _validate_access_level(
                    public_in.get("access_level"), notes
                ),
                "subculture": subculture_public,
            },
            "secret": {
                "subculture_hidden": secret_in.get("subculture_hidden") or "",
                "sensed_links": _normalize_sensed_links(secret_in.get("sensed_links")),
            },
        }
        return {"ok": True, "draft": draft, "notes": notes}

    if entity_type == "faction":
        draft = {
            "public": {
                "name": public_in.get("name") or "",
                "description": public_in.get("description") or "",
                "faction_type": _validate_faction_type(
                    public_in.get("faction_type"), notes
                ),
                "philosophy": public_in.get("philosophy") or "",
                "internal_structure": public_in.get("internal_structure") or "",
                "roles": _normalize_roles(public_in.get("roles"), notes),
                "aversion": public_in.get("aversion") or "",
            },
            "secret": {
                "internal_tensions": secret_in.get("internal_tensions") or "",
                "goals": secret_in.get("goals") or "",
            },
        }
        return {"ok": True, "draft": draft, "notes": notes}

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
            "aversion": public_in.get("aversion") or "",
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


def generate_world_draft(brief: str, db: Session) -> dict:
    """Generate a pre-fill draft for the world-create modal (BRIEF-47).

    Pure generate-and-return: writes no canon anywhere in this function or
    its call path — World is not an `entity` row, so this never touches
    `_create_entity_core`. `db` is read-only here: its single use is the
    `pt-world-generation` template lookup. Never raises into the caller —
    every failure mode (missing template, unreachable model, malformed
    JSON, empty parse) returns {"ok": False, "error": "<reason>"}. On
    success returns {"ok": True, "draft": {"public": {"name",
    "description", "fundamental_laws"}, "secret": {}}, "notes": [...]} —
    same top-level shape as `generate_entity_draft`.

    Unlike `region_author.generate_region_manifest`, this function creates
    a NEW world, so there is no existing world premise to read or inject
    here — that asymmetry is intentional.
    """
    if not brief or not brief.strip():
        return {"ok": False, "error": "brief must not be empty"}

    template = _load_world_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-world-generation template found"}

    try:
        user_message = template.user_template.format(brief=brief)
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

    notes: list[str] = []

    name = public_in.get("name") or ""
    if not name:
        notes.append("Aucun nom de monde proposé — champ laissé vide")
    description = public_in.get("description") or ""
    if not description:
        notes.append("Aucune description de monde proposée — champ laissé vide")

    laws_raw = public_in.get("fundamental_laws")
    if laws_raw is None:
        laws = []
    elif isinstance(laws_raw, list):
        laws = [str(item).strip() for item in laws_raw if str(item).strip()]
    else:
        notes.append(
            "Lois fondamentales reçues dans un format inattendu — ignorées"
        )
        laws = []
    fundamental_laws_str = "\n".join(f"{i + 1}. {law}" for i, law in enumerate(laws))

    draft = {
        "public": {
            "name": name,
            "description": description,
            "fundamental_laws": fundamental_laws_str,
        },
        "secret": {},
    }
    return {"ok": True, "draft": draft, "notes": notes}


def generate_player_draft(brief: str, db: Session) -> dict:
    """Generate a pre-fill draft for the PC creation assistant (BRIEF-52).

    Standalone sibling to `generate_world_draft` — NOT a `_TYPE_FIELDS`
    entry, NOT routed through `generate_entity_draft`. Pure generate-and-
    return: writes no canon anywhere in this function or its call path; it
    never calls `_create_entity_core` and emits no `world_id`/
    `current_location_id`/`faction`/`entity_id` (location stays creator-
    picked — C1). `db` is read-only here: its single use is the
    `pt-player-generation` template lookup.

    Parses a SINGLE top-level JSON object (no `public`/`secret` blocks —
    D1/G1): {"name", "description", "appearance", "backstory", "knowledge"}.
    Unrecognised keys are dropped. Knowledge is normalised by
    `_normalize_player_knowledge`, NOT `_normalize_knowledge` (which forces
    `is_secret=True` — wrong for a PC); `is_secret=False` is applied at
    write time by the accept route, not here.

    Never raises into the caller — every failure mode (missing template,
    unreachable model, malformed JSON, empty parse) returns
    {"ok": False, "error": "<reason>"}. On success returns
    {"ok": True, "draft": {"name", "description", "appearance", "backstory",
    "knowledge": [...]}, "notes": [...]}.
    """
    if not brief or not brief.strip():
        return {"ok": False, "error": "brief must not be empty"}

    template = _load_player_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-player-generation template found"}

    try:
        user_message = template.user_template.format(brief=brief)
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

    notes: list[str] = []

    name = parsed.get("name") or ""
    if not isinstance(name, str):
        name = ""
    if not name:
        notes.append("Aucun nom de personnage proposé — champ laissé vide")

    description = parsed.get("description") or ""
    if not isinstance(description, str):
        description = ""

    appearance = parsed.get("appearance") or ""
    if not isinstance(appearance, str):
        appearance = ""

    backstory = parsed.get("backstory") or ""
    if not isinstance(backstory, str):
        backstory = ""

    knowledge = _normalize_player_knowledge(parsed.get("knowledge"))

    draft = {
        "name": name,
        "description": description,
        "appearance": appearance,
        "backstory": backstory,
        "knowledge": knowledge,
    }
    return {"ok": True, "draft": draft, "notes": notes}
