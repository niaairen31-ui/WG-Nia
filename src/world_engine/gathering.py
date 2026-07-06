"""Initial NPC clustering when a player enters a location (schema v1.8, Tier 1).

Splits the work into two deliberately separate functions:

- `generate_gatherings` is the structural core. It loads the NPCs present,
  asks the MJ to partition them into social clusters (template
  `pt-mj-gathering`), resolves the MJ's names back to entity ids — never
  inventing (contract A2) — and guarantees a complete partition (invariant
  B1: every present NPC lands in exactly one gathering). It never raises and
  never dissolves anything.
- `enter_location` is the single-player caller. It dissolves the location's
  open gathering(s) before regenerating — see its docstring for why that step
  must live here and not in the core.

Forming or dissolving a gathering is not a canon mutation (see
ARCHITECTURE_DECISIONS.md): only what happens *inside* one — a relation
shifting, a secret slipping — produces `proposed_mutation` rows.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from . import ollama_client
from .analyzer import analyze_window
from .models import Character, Conversation, Entity, Gathering, GatheringMember, PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

# Same mild repetition controls as MJ narration — short, low-drift output.
GATHERING_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


def _load_gathering_template(world_id: str | None, db: Session) -> PromptTemplate | None:
    """Return the active mj_gathering template (world-specific preferred), or None."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_gathering",
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


def _present_npcs(location_id: str, db: Session) -> list[tuple[Character, Entity]]:
    """NPCs actually present and able to take part in a scene.

    Filters: character_type='npc', vital_status='alive', entity.status='active'.
    The player is never included here — they're placed by a later, explicit step.
    """
    rows = db.exec(
        select(Character, Entity)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.current_location_id == location_id,
            Character.character_type == "npc",
            Character.vital_status == "alive",
            Entity.status == "active",
        )
    ).all()
    return list(rows)


def _request_partition(
    *,
    template: PromptTemplate,
    location_name: str,
    present: list[tuple[Character, Entity]],
    model: str,
    host: str,
    db: Session,
) -> list[Any] | None:
    """Ask the MJ to partition the present NPCs. Returns raw groups, or None on failure."""
    version = current_prompt(db, template)
    present_lines = "\n".join(
        f"- {entity.name} : {char.appearance or entity.description or '(pas de description)'}"
        for char, entity in present
    )
    user_msg = (
        version.user_template
        .replace("{location_name}", location_name)
        .replace("{present_list}", present_lines)
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": version.system_prompt},
                {"role": "user", "content": user_msg},
            ],
            model=effective_model(template, model),
            host=host,
            format="json",
            options=GATHERING_OPTIONS,
        )
        obj = json.loads(raw)
        groups = obj.get("groups")
        if not isinstance(groups, list) or not groups:
            return None
        return groups
    except Exception as exc:
        _log.warning("MJ gathering partition call failed (%s)", exc)
        return None


def _resolve_and_complete(
    raw_groups: list[Any],
    present: list[tuple[Character, Entity]],
) -> list[dict]:
    """Turn the MJ's name-based groups into a complete id-based partition.

    A2 — name resolution is structural, not generative: matching is exact and
    case-insensitive against the present roster ONLY. A name that doesn't
    resolve is dropped and logged — never guessed, never invented. (Fuzzy
    matching is a possible later refinement if the 8b model proves imprecise;
    not built now.)

    B1 — completeness net: any present NPC the MJ didn't place (or placed
    twice — first claim wins) ends up in its own solo gathering, so the
    partition is always total: every present NPC belongs to exactly one
    open gathering (B1).
    """
    by_lower_name = {entity.name.strip().lower(): entity.id for _char, entity in present}
    name_by_id = {entity.id: entity.name for _char, entity in present}

    claimed: set[str] = set()
    groups: list[dict] = []
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            continue
        raw_members = raw_group.get("members")
        if not isinstance(raw_members, list):
            continue

        ids: list[str] = []
        for raw_name in raw_members:
            name = str(raw_name).strip()
            entity_id = by_lower_name.get(name.lower())
            if entity_id is None:
                _log.info("MJ gathering: unresolved name %r — dropped (contract A2)", name)
                continue
            if entity_id in claimed or entity_id in ids:
                continue
            ids.append(entity_id)
        if not ids:
            continue

        claimed.update(ids)
        label = str(raw_group.get("label") or "").strip()
        if not label:
            label = "Groupe : " + ", ".join(name_by_id[i] for i in ids)
        groups.append({"label": label, "members": ids})

    # Completeness net (B1): nobody the MJ left out goes ungrouped.
    for _char, entity in present:
        if entity.id not in claimed:
            groups.append({"label": f"{entity.name}, seul·e", "members": [entity.id]})
            claimed.add(entity.id)

    return groups


def _solo_partition(present: list[tuple[Character, Entity]]) -> list[dict]:
    """Fallback partition used when the MJ call fails or yields nothing usable."""
    return [
        {"label": f"{entity.name}, seul·e", "members": [entity.id]}
        for _char, entity in present
    ]


def generate_gatherings(
    location_id: str,
    session_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> list[Gathering]:
    """Partition the NPCs present at a location into social clusters.

    Loads the present NPCs, asks the MJ (template `pt-mj-gathering`) for a
    partition with a descriptive `label` per group, resolves the returned
    names to entity ids (contract A2), and completes the partition so every
    present NPC lands in exactly one gathering (invariant B1 — a NPC the MJ
    left out gets a solo gathering of its own).

    Never raises: a missing template, an unreachable model, malformed JSON,
    or zero resolved names all fall back to a solo partition (one gathering
    per NPC) — the scene must stay playable regardless. Writes `gathering`
    (status='open') and `gathering_member` (left_at=NULL) rows and returns
    the created gatherings. Dissolves nothing — see `enter_location`.
    """
    location = db.get(Entity, location_id)
    if location is None:
        raise ValueError(f"No location entity found for id {location_id!r}")

    present = _present_npcs(location_id, db)
    if not present:
        return []

    groups: list[dict] | None = None
    template = _load_gathering_template(location.world_id, db)
    if template is None:
        _log.warning("No active 'mj_gathering' prompt template — solo-gathering fallback")
    else:
        raw_groups = _request_partition(
            template=template,
            location_name=location.name,
            present=present,
            model=model,
            host=host,
            db=db,
        )
        if raw_groups is not None:
            groups = _resolve_and_complete(raw_groups, present)
            if not groups:
                groups = None

    if groups is None:
        groups = _solo_partition(present)

    now = datetime.now(UTC)
    created: list[Gathering] = []
    for group in groups:
        gathering = Gathering(
            world_id=location.world_id,
            session_id=session_id,
            location_id=location_id,
            label=group["label"],
            status="open",
            created_at=now,
        )
        db.add(gathering)
        for entity_id in group["members"]:
            db.add(GatheringMember(
                gathering_id=gathering.id,
                entity_id=entity_id,
                joined_at=now,
                left_at=None,
            ))
        created.append(gathering)

    db.commit()
    for gathering in created:
        db.refresh(gathering)
    return created


def close_open_memberships(entity_id: str, db: Session) -> list[GatheringMember]:
    """Close every open `gathering_member` row for entity_id (B1 repair).

    Sets `left_at = now` on each matched row; never deletes a row (history
    is sacred). Writes no canon — closing a membership is not a
    `proposed_mutation` (gatherings are not canon). Does not commit; the
    caller owns the transaction.

    Extracted verbatim from `migrate_npc`'s inline close (the predicate and
    write are unchanged) so other write sites (creator-CRUD location/status
    edits — BRIEF-53) can reuse the same repair instead of duplicating it.
    """
    now = datetime.now(UTC)
    active_rows = db.exec(
        select(GatheringMember).where(
            GatheringMember.entity_id == entity_id,
            GatheringMember.left_at == None,  # noqa: E711
        )
    ).all()
    for row in active_rows:
        row.left_at = now
        db.add(row)
    return list(active_rows)


def migrate_npc(npc_id: str, target_gathering_id: str, db: Session) -> None:
    """Move an NPC from its current gathering to target_gathering_id.

    Primitive — takes an explicit target; caller resolves policy (which
    gathering to move into). Built for C2 (NPC joins the player's gathering)
    but reusable for future NPC↔NPC reshuffles: pass a different target_id.

    Invariants:
    - B1: all active rows for this entity are closed before the new one is
      inserted (single transaction). Closes ALL active rows even though B1
      normally guarantees at most one — this makes B1 true by repair if
      upstream ever drifts.
    - Idempotent: if the NPC already has an active row in target_gathering_id,
      returns immediately without any write.
    - Auto-dissolve: if closing the source leaves it with zero active members,
      the gathering is dissolved. Only fires on NPC-cluster sources — the
      player's gathering is always the target via C2, never the source.
    - Not a canon mutation: no proposed_mutation row is created.
    """
    now = datetime.now(UTC)

    # Idempotent guard: already in the target → nothing to do.
    already = db.exec(
        select(GatheringMember).where(
            GatheringMember.entity_id == npc_id,
            GatheringMember.gathering_id == target_gathering_id,
            GatheringMember.left_at == None,  # noqa: E711
        )
    ).first()
    if already is not None:
        return

    # Collect + close ALL active rows for this entity (B1 repair: close every one).
    active_rows = close_open_memberships(npc_id, db)
    source_gathering_ids = {row.gathering_id for row in active_rows}

    db.add(GatheringMember(
        gathering_id=target_gathering_id,
        entity_id=npc_id,
        joined_at=now,
        left_at=None,
    ))
    db.commit()

    # Auto-dissolve: any source gathering now empty of active members is dissolved.
    for source_id in source_gathering_ids:
        if source_id == target_gathering_id:
            continue
        remaining = db.exec(
            select(GatheringMember).where(
                GatheringMember.gathering_id == source_id,
                GatheringMember.left_at == None,  # noqa: E711
            )
        ).first()
        if remaining is None:
            source_g = db.get(Gathering, source_id)
            if source_g is not None and source_g.status == "open":
                open_convs = db.exec(
                    select(Conversation).where(
                        Conversation.gathering_id == source_id,
                        Conversation.status == "open",
                    )
                ).all()
                for conv in open_convs:
                    try:
                        analyze_window(conv.id, db)
                    except (Exception, SystemExit):
                        _log.exception("analyze_window failed for conversation %s", conv.id)
                source_g.status = "dissolved"
                source_g.dissolved_at = now
                db.add(source_g)
    db.commit()


def enter_location(
    location_id: str,
    session_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> list[Gathering]:
    """Single-player entry point: dissolve the location's open gathering(s), then regenerate.

    Dissolve-before-create lives HERE — deliberately not inside
    generate_gatherings. Multiplayer decoupling: the day a second player can
    also walk in, the right behaviour is to JOIN the existing partition, not
    wipe it out from under the first player. Only this caller will need to
    change then (a "is there already someone here" check replacing the blanket
    dissolution below); the core stays exactly as it is.
    """
    now = datetime.now(UTC)
    open_gatherings = db.exec(
        select(Gathering).where(
            Gathering.location_id == location_id,
            Gathering.session_id == session_id,
            Gathering.status == "open",
        )
    ).all()
    for gathering in open_gatherings:
        open_convs = db.exec(
            select(Conversation).where(
                Conversation.gathering_id == gathering.id,
                Conversation.status == "open",
            )
        ).all()
        for conv in open_convs:
            try:
                analyze_window(conv.id, db, model=model, host=host)
            except (Exception, SystemExit):
                _log.exception("analyze_window failed for conversation %s", conv.id)
        gathering.status = "dissolved"
        gathering.dissolved_at = now
        db.add(gathering)
    if open_gatherings:
        db.commit()

    return generate_gatherings(location_id, session_id, db, model=model, host=host)
