"""`knowledge` canon-write chokepoint (TICKET-0028, BRIEF-0028-b —
decomposed from `writes.py`).

- `write_knowledge(...)`               : insert or update a `knowledge` row.
  `knowledge_id=None` creates; otherwise updates that row in place, appending
  the previous state to `change_history` first (history is sacred on this
  path too — see `_append_knowledge_history`).
- `write_knowledge(mode="level_change", ...)` : `_apply_mutation`'s
  `knowledge_change` branch. Narrower than the default update: only
  `level`, `source` and `updated_at` change (the previous state is still
  appended to `change_history` first) — `content`, `is_incorrect`,
  `is_secret`, `share_threshold` and `subject` on the existing row are left
  untouched, unlike a default-mode update.

`_build_knowledge_level_change`/`_build_knowledge_update` are pure builds
(no `db.add`) carved out of `write_knowledge` at this brief so the function
fits the 80-line cap (R7). `write_knowledge` itself owns the single
`db.add` call.

`knowledge.fact_id` (TICKET-0082, BRIEF-0082-b) is NOT NULL: every create
call site (`_apply_mutation`'s `new_knowledge`/`resource_change` branches,
`link_author.py`'s batch commit, `create_player_character`'s draft
knowledge, and the creator CRUD) passes through this one function, so the
fallback lives here rather than being duplicated at each caller — an
explicit `fact_id` attaches to that existing fact; omitting it auto-creates
a free-standing one (`writes/facts.py::create_fact`) with `content =
subject`, matching the creator CRUD's documented behaviour exactly.

`subject_entity_ids` (TICKET-0087, BRIEF-0087-a) attaches participants to
the row's fact on create only, with no `role`; a participant IS the
aboutness claim, so no discriminator distinguishes a subject from
TICKET-0082 arity (decision J2, AMENDMENT-0087-1); the attachment is
idempotent per `(fact_id, entity_id)`, which `idx_fact_participant_unique`
enforces and the read-before-write guard exists to avoid tripping;
validation of the ids belongs to the caller.

New knowledge prose is written with identity tokens (TICKET-0091,
BRIEF-0091-J): `_tokenized_content` runs `prose_tokens.tokenize` on the
content path and `write_knowledge` records the names it could not resolve
(`writes/mentions.py`). `apply_knowledge_patch` (the link agent's coherence
patch) and `upsert_knowledge_row` (the seed's idempotent upsert) live here so
raw stored text is read only in `writes/`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..models import Entity, Fact, FactParticipant, Knowledge
from ..prose_render import render
from ..prose_tokens import tokenize
from ._shared import _clamp
from .facts import attach_participants, create_fact
from .mentions import record_unresolved

# knowledge.level enum (world-engine-schema.md): unaware | rumor | suspicious |
# partial | knows | fully_understands.
KNOWLEDGE_LEVELS = frozenset(
    {"unaware", "rumor", "suspicious", "partial", "knows", "fully_understands"}
)

# Ordered ladder, lowest to highest. Shared by the analyzer (overhearing /
# direct-affirmation upgrade detection) and `_apply_mutation`'s monotone
# guard for `knowledge_change` — one source of truth for level ordering.
KNOWLEDGE_LEVEL_LADDER: tuple[str, ...] = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)


def knowledge_level_rank(level: Optional[str]) -> int:
    """Return `level`'s position on `KNOWLEDGE_LEVEL_LADDER`, or -1 if unrecognised.

    An unrecognised level ranks below 'unaware' so it can never satisfy a
    monotone "target > existing" check — invalid levels fail safe.
    """
    try:
        return KNOWLEDGE_LEVEL_LADDER.index(level)
    except ValueError:
        return -1


def cap_knowledge_level(level: str, cap: str = "knows") -> str:
    """Clamp `level` to at most `cap` on the ladder.

    Direct-affirmation rule: a target level is never granted above `cap`
    (default `knows`) by hearsay — `fully_understands` is creator CRUD only.
    """
    if knowledge_level_rank(level) > knowledge_level_rank(cap):
        return cap
    return level


def _append_knowledge_history(row: Knowledge, changed_by: str) -> None:
    """Append a snapshot of `row`'s PREVIOUS state to its `change_history`.

    Called before any overwrite of an existing `knowledge` row — history is
    sacred on every write path that updates `knowledge` (creator CRUD via
    `write_knowledge`; `knowledge_change` apply in `_apply_mutation`).
    `changed_by` is `"creator_crud"` or `"apply_mutation"`.
    """
    history = list(row.change_history or [])
    history.append({
        "level": row.level,
        "content": row.content_raw,
        "source": row.source,
        "is_incorrect": row.is_incorrect,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "changed_by": changed_by,
        "changed_at": datetime.now(UTC).isoformat(),
    })
    row.change_history = history
    # flag_modified ensures SQLAlchemy detects the JSON list change
    # even though we replaced the object (not mutated it in place).
    sa_attrs.flag_modified(row, "change_history")


def _build_knowledge_level_change(
    db: Session, *, knowledge_id: Optional[str], level: Optional[str],
    source: Optional[Any], changed_by: str,
) -> Knowledge:
    """Pure build for `write_knowledge(mode="level_change")` — no `db.add`."""
    if knowledge_id is None:
        raise ValueError("write_knowledge(mode='level_change'): knowledge_id is required")
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
    _append_knowledge_history(k, changed_by=changed_by)
    k.level = level
    k.source = str(source or k.source)
    k.updated_at = datetime.now(UTC)
    return k


def _attach_subject_participants(
    db: Session, *, fact: Fact, subject_entity_ids: Optional[list[str]],
) -> None:
    """Attach each id in `subject_entity_ids` to `fact`, no `role` (TICKET-0087,
    BRIEF-0087-a, decision J2: a participant IS the aboutness claim, no
    discriminator distinguishes a subject from TICKET-0082 arity). Idempotent
    per `(fact_id, entity_id)`, which `idx_fact_participant_unique` enforces;
    the read-before-write guard is mandatory, not defensive — a collision
    raises `IntegrityError` at commit and aborts the surrounding transaction.
    """
    for entity_id in subject_entity_ids or []:
        existing = db.exec(
            select(FactParticipant).where(
                FactParticipant.fact_id == fact.id,
                FactParticipant.entity_id == entity_id,
            )
        ).first()
        if existing is not None:
            continue
        attach_participants(db, fact=fact, entity_ids=[entity_id])


def _tokenized_content(
    db: Session, entity_id: Optional[str], content: Any, previous: Optional[str] = None,
) -> tuple[Any, Optional[tuple]]:
    """(stored text, pending) for knowledge prose (TICKET-0091, BRIEF-0091-J):
    new text gets identity tokens (`prose_tokens.tokenize`); `pending` is
    `(world_id, unresolved)` for `record_unresolved`, or None. Text equal to
    the stored text, raw or rendered, is not new writing: the stored text is
    kept as is, so a re-sent row never loses a token nor re-reports a name."""
    if previous is not None and content in (previous, render(db, previous)):
        return previous, None
    entity = db.get(Entity, entity_id) if entity_id else None
    if not isinstance(content, str) or not content.strip() or entity is None:
        return content, None
    result = tokenize(db, world_id=entity.world_id, text=content)
    return result.text, ((entity.world_id, result.unresolved) if result.unresolved else None)


def _build_knowledge_update(
    db: Session, *, knowledge_id: Optional[str], entity_id: Optional[str],
    subject: Optional[str], level: Optional[str], content: Optional[Any],
    source: Optional[Any], is_incorrect: bool, is_secret: bool,
    share_threshold: int, session_id: Optional[str], changed_by: str,
    fact_id: Optional[str] = None,
    subject_entity_ids: Optional[list[str]] = None,
) -> tuple[Knowledge, Optional[tuple]]:
    """Pure build for `write_knowledge(mode="update")` (default) — no
    `db.add`. Returns the row and its pending unresolved mentions
    (`_tokenized_content`). `level` falls back to "rumor" if missing/unrecognised
    (matches the analyzer's default for unreliable local-model output).
    On create, `fact_id` attaches to an existing fact; omitting it
    auto-creates a free-standing one via `writes/facts.py::create_fact`
    with `content = subject` (see module docstring). `subject_entity_ids`
    is attached to that fact on create only (see module docstring); ignored
    when updating an existing row.
    """
    norm_level = level if level in KNOWLEDGE_LEVELS else "rumor"
    threshold = _clamp(share_threshold)

    if knowledge_id is not None:
        k = db.get(Knowledge, knowledge_id)
        if k is None:
            raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
        _append_knowledge_history(k, changed_by=changed_by)
        if subject is not None:
            k.subject = subject
        k.level = norm_level
        k.content_raw, pending = _tokenized_content(db, k.entity_id, content, previous=k.content_raw)
        k.source = source
        k.is_incorrect = bool(is_incorrect)
        k.is_secret = bool(is_secret)
        k.share_threshold = threshold
        k.updated_at = datetime.now(UTC)
        return k, pending

    if not entity_id:
        raise ValueError("write_knowledge: entity_id is required to create")
    resolved_subject = subject or "unknown"
    if fact_id is None:
        entity = db.get(Entity, entity_id)
        if entity is None:
            raise ValueError(f"write_knowledge: entity {entity_id!r} not found")
        fact = create_fact(
            db, world_id=entity.world_id, content=resolved_subject, created_by=changed_by,
            facet="information",
        )
    else:
        fact = db.get(Fact, fact_id)
        if fact is None:
            raise ValueError(f"write_knowledge: fact {fact_id!r} not found")
    _attach_subject_participants(db, fact=fact, subject_entity_ids=subject_entity_ids)
    stored, pending = _tokenized_content(db, entity_id, content)
    return Knowledge(
        entity_id=entity_id, fact_id=fact.id, subject=resolved_subject, level=norm_level,
        content_raw=stored, source=source, is_incorrect=bool(is_incorrect),
        is_secret=bool(is_secret), share_threshold=threshold, session_id=session_id,
    ), pending


def write_knowledge(
    db: Session,
    *,
    mode: str = "update",
    knowledge_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    subject: Optional[str] = None,
    level: Optional[str] = None,
    content: Optional[Any] = None,
    source: Optional[Any] = None,
    is_incorrect: bool = False,
    is_secret: bool = False,
    share_threshold: int = 50,
    session_id: Optional[str] = None,
    changed_by: str = "creator_crud",
    fact_id: Optional[str] = None,
    subject_entity_ids: Optional[list[str]] = None,
) -> Knowledge:
    """Insert or update a `knowledge` row — the single sanctioned `knowledge`
    write site; this function itself calls `db.add`.

    mode="update" (default; creator CRUD and `_apply_mutation`'s
    `new_knowledge`/`resource_change` branches): see `_build_knowledge_update`.
    `fact_id` is ignored when updating an existing row (`knowledge_id` set).
    `subject_entity_ids` (TICKET-0087, BRIEF-0087-a) attaches participants to
    the row's fact on create only, with no `role`; ignored on update and on
    `mode="level_change"`. Idempotent per `(fact_id, entity_id)`, which
    `idx_fact_participant_unique` enforces; validation of the ids is the
    caller's responsibility.

    mode="level_change" (`_apply_mutation`'s `knowledge_change` branch
    only): see `_build_knowledge_level_change`.
    """
    pending = None
    if mode == "level_change":
        k = _build_knowledge_level_change(
            db, knowledge_id=knowledge_id, level=level, source=source, changed_by=changed_by,
        )
    else:
        k, pending = _build_knowledge_update(
            db, knowledge_id=knowledge_id, entity_id=entity_id, subject=subject,
            level=level, content=content, source=source, is_incorrect=is_incorrect,
            is_secret=is_secret, share_threshold=share_threshold, session_id=session_id,
            changed_by=changed_by, fact_id=fact_id, subject_entity_ids=subject_entity_ids,
        )

    db.add(k)
    if pending:
        db.flush()
        record_unresolved(db, world_id=pending[0], knowledge_id=k.id, items=pending[1])
    return k


def apply_knowledge_patch(db: Session, *, knowledge: Knowledge, patch: dict, changed_by: str) -> Knowledge:
    """Merge `patch` ({field: new value}) over `knowledge`'s current state and
    write the result through `write_knowledge` (history appended) — moved
    unchanged in logic out of `link_author._apply_canon_knowledge_patch`
    (TICKET-0091, AMENDMENT-0091-04): the current text is read raw here, in
    `writes/`, so an untouched content keeps its tokens. A patched content is
    new writing and is tokenized by `write_knowledge`."""
    merged = {
        "level": knowledge.level, "content": knowledge.content_raw, "source": knowledge.source,
        "is_incorrect": knowledge.is_incorrect, "is_secret": knowledge.is_secret,
        "share_threshold": knowledge.share_threshold,
    }
    merged.update(patch)
    return write_knowledge(
        db, mode="update", knowledge_id=knowledge.id, entity_id=knowledge.entity_id,
        subject=knowledge.subject, level=merged["level"], content=merged["content"],
        source=merged["source"], is_incorrect=merged["is_incorrect"],
        is_secret=merged["is_secret"], share_threshold=merged["share_threshold"],
        session_id=knowledge.session_id, changed_by=changed_by,
    )


def upsert_knowledge_row(db: Session, *, id: str, created_by: str, **fields) -> str:
    """Create the knowledge row `id`, or converge its fields in place — the
    seed's idempotent upsert, moved unchanged in logic out of
    `scripts/seed_pilot.py::upsert_knowledge` (TICKET-0091, AMENDMENT-0091-05).
    The `content` key maps to `content_raw`; the text is stored as given,
    never tokenized (seed text is a reproducible dataset, like migrated text).
    On create, absent a `fact_id`, a free-standing fact is created with
    `content = subject` (the `write_knowledge` fallback); an existing row's
    `fact_id` is never touched. Returns "created", "updated" or "existing"."""
    if "content" in fields:
        fields = {("content_raw" if key == "content" else key): value for key, value in fields.items()}
    obj = db.get(Knowledge, id)
    if obj is None:
        if "fact_id" not in fields:
            entity = db.get(Entity, fields["entity_id"])
            fact = create_fact(
                db, world_id=entity.world_id,
                content=fields.get("subject") or "unknown", created_by=created_by,
                facet="information",
            )
            fields = {**fields, "fact_id": fact.id}
        db.add(Knowledge(id=id, **fields))
        return "created"
    changed = False
    for key, value in fields.items():
        if getattr(obj, key) != value:
            setattr(obj, key, value)
            changed = True
    if changed:
        obj.updated_at = datetime.now(UTC)
        return "updated"
    return "existing"
