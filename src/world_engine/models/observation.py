"""Observation SQLModel table classes (TICKET-0051, schema v1.90).

Observed-scene instrumentation: a creator watches NPCs act among themselves
and every agent decision is recorded. None of these tables appear in
``canon_write_policy.txt``'s ``[CANON_TABLES]`` — they are observation
telemetry, never durable world canon. A lasting consequence of an observed
run reaches the world only through ``proposed_mutation`` under creator
approval, exactly like a played scene.

Append-only: no row in this module is ever updated in place except
``observation_run``'s terminal ``status`` / ``stop_reason`` / ``ended_at``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# -----------------------------------------------------------------------------
# observation_run
# -----------------------------------------------------------------------------
class ObservationRun(SQLModel, table=True):
    __tablename__ = "observation_run"
    __table_args__ = (
        CheckConstraint(
            "player_presence IN ('absent','silent','active')",
            name="ck_observation_run_player_presence",
        ),
        CheckConstraint(
            "propensity_mode IN ('flat','relation_weighted')",
            name="ck_observation_run_propensity_mode",
        ),
        CheckConstraint(
            "status IN ('running','completed','stopped','failed')",
            name="ck_observation_run_status",
        ),
        CheckConstraint(
            "stop_reason IS NULL OR stop_reason IN "
            "('max_beats','quiescence','creator_stop','error')",
            name="ck_observation_run_stop_reason",
        ),
        Index("idx_observation_run_world", "world_id"),
        Index("idx_observation_run_location", "location_id"),
    )

    # NOTE: player_presence is a closed vocabulary, not a boolean, because a
    #       SILENT player is still an AUDITOR for disclosure gating (E2) while
    #       an ABSENT one is not. Only 'absent' is implemented at v1.90;
    #       'silent' and 'active' are named deferrals (TICKET-0051, H2) and the
    #       runner refuses them explicitly rather than silently treating them
    #       as 'absent'.
    # NOTE: cooldown_beats / debt_weight / propensity_mode are pinned PER RUN,
    #       not read from code constants, so that two runs separated by a tuning
    #       pass remain attributable. They are not a replay mechanism: the world
    #       mutates under play and bit-exact replay is out of scope by decision.

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    gathering_id: Optional[str] = Field(default=None, foreign_key="gathering.id")
    player_presence: str = Field(
        default="absent",
        sa_column_kwargs={"server_default": text("'absent'")},
    )
    max_beats: int
    quiescence_limit: int
    mj_narration: bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default=text("0"))
    )
    cooldown_beats: int
    debt_weight: float
    propensity_mode: str
    model: str
    status: str = Field(
        default="running",
        sa_column_kwargs={"server_default": text("'running'")},
    )
    stop_reason: Optional[str] = None
    started_at: datetime = _created_ts()
    ended_at: Optional[datetime] = None


# -----------------------------------------------------------------------------
# observation_run_template  (per-usage prompt pinning, L)
# -----------------------------------------------------------------------------
class ObservationRunTemplate(SQLModel, table=True):
    __tablename__ = "observation_run_template"
    __table_args__ = (
        Index(
            "idx_observation_run_template_unique", "run_id", "usage", unique=True
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    run_id: str = Field(foreign_key="observation_run.id", nullable=False)
    usage: str
    template_id: str
    version: int


# -----------------------------------------------------------------------------
# observation_beat
# -----------------------------------------------------------------------------
class ObservationBeat(SQLModel, table=True):
    __tablename__ = "observation_beat"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('acted','silence','degraded','event')",
            name="ck_observation_beat_outcome",
        ),
        Index("idx_observation_beat_unique", "run_id", "beat_index", unique=True),
    )

    # NOTE: outcome is explicit and never inferred from actor_id being NULL.
    #       'silence'  = every candidate declined (a datum: passivity mode (a))
    #       'degraded' = every intent call failed (a bug, not a datum)
    #       'event'    = a creator-injected event line (no NPC actor)
    #       Conflating the first two would let a JSON parse failure be read as
    #       "the NPCs are passive" — the exact misreading this table exists to
    #       prevent.

    id: str = Field(default_factory=_uuid, primary_key=True)
    run_id: str = Field(foreign_key="observation_run.id", nullable=False)
    beat_index: int
    outcome: str
    actor_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    line: Optional[str] = None
    mj_narration: Optional[str] = None
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# observation_intent  (one row per NPC per beat, ALWAYS written)
# -----------------------------------------------------------------------------
class ObservationIntent(SQLModel, table=True):
    __tablename__ = "observation_intent"
    __table_args__ = (
        CheckConstraint(
            "call_status IN ('ok','parse_error','timeout','error')",
            name="ck_observation_intent_call_status",
        ),
        Index("idx_observation_intent_unique", "beat_id", "npc_id", unique=True),
        Index("idx_observation_intent_run", "run_id"),
    )

    # NOTE: there is deliberately NO not_selected_reason column. A candidate can
    #       be excluded by cooldown AND by debt AND by arbitration at once; a
    #       single-valued reason would force a precedence and destroy the rest of
    #       the information. The COMPONENTS are stored (propensity,
    #       cooldown_active, debt_score, final_score) and the reason is DERIVED
    #       at read time by a documented precedence:
    #         act = FALSE                       -> no_intent
    #         cooldown_active = TRUE            -> cooldown
    #         selected = FALSE, debt_score < 0  -> debt
    #         otherwise                         -> lost_arbitration
    #       The arbitration is therefore reconstructible, not merely reported.
    # NOTE: a row is written for every candidate on every beat, including when
    #       the model call fails (call_status != 'ok'). A missing row is a bug,
    #       never a silent decline.
    # NOTE: latency_ms and raw_response have a DIFFERENT reader from the rest of
    #       this table: run feasibility (does a 5-NPC / 30-beat run stay
    #       tractable) and parse diagnosis. They are not scene-analysis columns.

    id: str = Field(default_factory=_uuid, primary_key=True)
    run_id: str = Field(foreign_key="observation_run.id", nullable=False)
    beat_id: str = Field(foreign_key="observation_beat.id", nullable=False)
    npc_id: str = Field(foreign_key="entity.id", nullable=False)
    act: bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default=text("0"))
    )
    urgency: Optional[int] = None
    target_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    why: Optional[str] = None
    propensity: float
    cooldown_active: bool
    debt_score: float
    final_score: float
    selected: bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default=text("0"))
    )
    call_status: str
    latency_ms: Optional[int] = None
    raw_response: Optional[str] = None
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# observation_mutation_link  (provenance without altering a canon table)
# -----------------------------------------------------------------------------
class ObservationMutationLink(SQLModel, table=True):
    __tablename__ = "observation_mutation_link"
    __table_args__ = (
        Index("idx_observation_mutation_link_unique", "mutation_id", unique=True),
    )

    # NOTE: provenance lives here rather than as a column on proposed_mutation
    #       so that a canon table is not altered to serve observation telemetry.
    #       proposed_by = 'observed_scene' carries the FILTER; this table carries
    #       the JOIN back to the run and beat that produced the proposal.

    id: str = Field(default_factory=_uuid, primary_key=True)
    run_id: str = Field(foreign_key="observation_run.id", nullable=False)
    beat_id: Optional[str] = Field(default=None, foreign_key="observation_beat.id")
    mutation_id: str = Field(foreign_key="proposed_mutation.id", nullable=False)
