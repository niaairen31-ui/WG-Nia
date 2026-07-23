"""Canon SQLModel table classes — faction domain, extracted from
``canon.py`` (TICKET-0048, BRIEF-0048-a) to keep each stratum module under
the `module_budget.py` line cap. Same schema-fidelity conventions as
`canon.py` — see that module's docstring for the full convention list
(primary keys, JSON columns, ``server_default`` usage, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid


# -----------------------------------------------------------------------------
# faction  (extension of entity)
# -----------------------------------------------------------------------------
class Faction(SQLModel, table=True):
    __tablename__ = "faction"
    __table_args__ = (Index("idx_faction_parent", "parent_faction_id"),)

    id: str = Field(primary_key=True, foreign_key="entity.id")
    faction_type: Optional[str] = None
    internal_structure: Optional[str] = None
    philosophy: Optional[str] = None
    magic_knowledge_level: str = Field(
        default="unaware",
        sa_column_kwargs={"server_default": text("'unaware'")},
    )
    internal_tensions: Optional[str] = None
    # DORMANT (BRIEF-26, schema v1.38): containment tree, mirror of
    # location.parent_location_id. No assembler or guard traverses it yet —
    # creator-CRUD only, metadata-config category, no change_history (same
    # as location_type / coordinates).
    parent_faction_id: Optional[str] = Field(
        default=None, foreign_key="entity.id"
    )
    # DORMANT: descriptive scale label, NOT derived from tree depth. No code
    # reads it yet. global | national | regional | local | other.
    scope: Optional[str] = None
    # DORMANT: prose, what the faction is trying to do. No mechanic, no
    # structured consumer.
    goals: Optional[str] = None
    # DORMANT (BRIEF-33, schema v1.44): prose dual of `philosophy` — what the
    # faction rejects/opposes. Public-tagged, authored + proposed, but read
    # by no assembler yet. Future reader MUST route through
    # `read_public_memberships` (see ARCHITECTURE_DECISIONS.md).
    aversion: Optional[str] = None


# -----------------------------------------------------------------------------
# faction_role  (declared role vocabulary of a faction, schema v1.76,
# TICKET-0024, BRIEF-0024-d — corrective: replaces the disconnected
# `faction.role_capacities` JSON map and `entity.metadata['roles']` list with
# one relational table)
#
# Declared role vocabulary of a faction. Public by construction (BRIEF-31
# lineage) — safe to expose to prompts and player-facing reads. Closed
# vocabulary for the AI path (K1). Case-duplicate names are schema-impossible
# via the unique index below (structural, not a code-side casefold check).
# Curated config, same family as `faction_type` / `philosophy` — no
# `change_history` column.
# -----------------------------------------------------------------------------
class FactionRole(SQLModel, table=True):
    __tablename__ = "faction_role"
    __table_args__ = (
        Index(
            "idx_faction_role_name", "faction_id", text("name COLLATE NOCASE"),
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    faction_id: str = Field(foreign_key="faction.id", nullable=False)
    name: str
    description: Optional[str] = None
    max_holders: Optional[int] = None  # NULL = unlimited
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    created_at: datetime = _created_ts()
    created_by: str


# -----------------------------------------------------------------------------
# faction_membership  (durable member <-> faction roster, schema v1.39)
#
# Durable counterpart to `gathering_member` (which is session-ephemeral).
# Roster predicate, single source: a membership is ACTIVE iff
# `left_at IS NULL`. Rows are append/close only — never updated in place or
# deleted; a role/primary change is close + reopen (a new row), so the closed
# rows ARE the history (no `change_history` column here, by construction).
# `role` and `is_secret` are DORMANT this step: stored, creator-editable, but
# read by no assembler — the first reader is the next brief, which must also
# add the structural `is_secret = FALSE` exclusion for non-creator contexts.
# -----------------------------------------------------------------------------
class FactionMembership(SQLModel, table=True):
    __tablename__ = "faction_membership"
    __table_args__ = (
        Index("idx_faction_membership_entity", "entity_id"),
        Index("idx_faction_membership_faction", "faction_id"),
        # At most one ACTIVE primary membership per member.
        Index(
            "idx_membership_one_primary", "entity_id",
            unique=True, sqlite_where=text("is_primary = 1 AND left_at IS NULL"),
        ),
        # No duplicate ACTIVE membership of the same member in the same faction.
        Index(
            "idx_membership_unique_active", "entity_id", "faction_id",
            unique=True, sqlite_where=text("left_at IS NULL"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)  # the member (a character, by intent)
    faction_id: str = Field(foreign_key="entity.id", nullable=False)
    role: Optional[str] = None  # creator-authored label. DORMANT: no assembler reads it yet.
    # Prompt-facing façade role (schema v1.41, BRIEF-30). NULL by default —
    # `read_public_memberships` resolves `cover_role ?? role`. The true
    # `role` stays creator-only when a cover is set; never read directly by
    # any prompt assembler.
    cover_role: Optional[str] = None
    is_primary: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    # DORMANT: the mole. Present but its exclusion is NOT enforced this step
    # (no reader exists). The first reader MUST filter is_secret=FALSE for
    # every non-creator context, by query construction.
    is_secret: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    joined_at: datetime = _created_ts()
    left_at: Optional[datetime] = None  # NULL = active, never erased
