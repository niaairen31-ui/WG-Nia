"""Quest offers and accepted quests (schema v2.17, TICKET-0108, BRIEF-0108-A).

Canon stratum, quest family. An offer is what the creator authors (E1): who
gives it (a character or a faction, H1), its title, its steps and the
requirements that decide who it is offered to (eligibility, a requirement
row with no step) and what each step needs. Accepting it (B1) copies its
steps and their requirements into a new `agenda` of the player, born
`paused` (A1); `quest` links that agenda to the offer it came from. A
quest's state is its agenda's status, never a second column (M1).

The requirement vocabulary is the condition language's, not a second one
(B1, then I1 of TICKET-0111): an offer's eligibility and each step's
conditions are `condition` trees (models/config.py), like an agenda step's.

Offers are curated content: their steps and requirements are replaced
whole when the creator saves an offer (the `npc_price` full-replace
precedent); an accepted quest is unaffected, its agenda holds its own copy.
The offer row itself keeps a `change_history`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Index, JSON, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# The two lifecycle states of an offer: `open` is proposed to whoever is
# eligible, `closed` is proposed to no one. An offer is never deleted.
QUEST_OFFER_STATUSES: tuple[str, ...] = ("open", "closed")


# -----------------------------------------------------------------------------
# quest_offer  (a quest the creator authored)
# -----------------------------------------------------------------------------
class QuestOffer(SQLModel, table=True):
    __tablename__ = "quest_offer"
    __table_args__ = (
        CheckConstraint("status IN ('open','closed')", name="ck_quest_offer_status"),
        Index("idx_quest_offer_world", "world_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    # A character or a faction of the world (H1), checked by the writer.
    giver_entity_id: str = Field(foreign_key="entity.id", nullable=False)
    # v2.19 (TICKET-0110, X1): when the giver is a faction, the member who
    # speaks for it -- the person a debt born of this offer is linked to.
    # NULL for a character giver; optional for a faction (asked at « régler
    # à crédit » when absent). Checked by the writer.
    contact_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    title: str
    summary: Optional[str] = None
    # L1: a repeatable offer may be accepted again once the last quest taken
    # from it is over; any other offer once per character.
    repeatable: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    status: str = Field(default="open", sa_column_kwargs={"server_default": text("'open'")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# quest_offer_step  (one step of an offer, copied to agenda_step on accept)
# -----------------------------------------------------------------------------
class QuestOfferStep(SQLModel, table=True):
    __tablename__ = "quest_offer_step"
    __table_args__ = (
        CheckConstraint("cost BETWEEN 1 AND 4", name="ck_quest_offer_step_cost"),
        Index("idx_quest_offer_step_order", "offer_id", "step_order", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
    step_order: int
    objective: str
    cost: int  # day-budget slots, as agenda_step.cost
    domain: Optional[str] = None  # a base skill domain, or NULL: no roll


# -----------------------------------------------------------------------------
# quest  (an offer a character accepted: the link to its agenda). The
# quest's state is `agenda.status` (M1); `settled_at` (v2.18, TICKET-0109,
# D1) is set once, when « déclarer accomplie » applied its terms, and never
# moves again -- the row's only column that is ever written after creation.
# -----------------------------------------------------------------------------
class Quest(SQLModel, table=True):
    __tablename__ = "quest"
    __table_args__ = (
        Index("idx_quest_agenda", "agenda_id", unique=True),
        Index("idx_quest_character", "character_id"),
        Index("idx_quest_offer", "offer_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
    character_id: str = Field(foreign_key="entity.id", nullable=False)
    agenda_id: str = Field(foreign_key="agenda.id", nullable=False)
    accepted_at: datetime = _created_ts()
    settled_at: Optional[datetime] = None


# The two sides of a term (TICKET-0109, BRIEF-0109-A, B1, C-01): what the
# character gives to settle the quest, and what he receives.
QUEST_TERM_DIRECTIONS: tuple[str, ...] = ("cost", "reward")

# The five currencies of a quest (the series' D table).
QUEST_TERM_CURRENCIES: tuple[str, ...] = ("money", "item", "relation", "fact", "skill")

# The shape CHECK both term tables carry, byte for byte: an amount for the
# three counted currencies, a target for the three named ones.
QUEST_TERM_SHAPE_CHECK = (
    "(currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) "
    "AND (currency <> 'item' OR item_id IS NOT NULL) "
    "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
    "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
)
QUEST_TERM_DIRECTION_CHECK = "direction IN ('cost','reward')"
QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill')"


# -----------------------------------------------------------------------------
# quest_offer_term  (a cost or a reward of an offer, B1). Replaced whole with
# the offer's steps on save. `counterparty_entity_id` NULL = the giver.
# `skill_key` is a base domain or a skill definition id; `level` is the
# knowledge level a fact reward gives (NULL = `knows`).
# -----------------------------------------------------------------------------
class QuestOfferTerm(SQLModel, table=True):
    __tablename__ = "quest_offer_term"
    __table_args__ = (
        CheckConstraint(QUEST_TERM_DIRECTION_CHECK, name="ck_quest_offer_term_direction"),
        CheckConstraint(QUEST_TERM_CURRENCY_CHECK, name="ck_quest_offer_term_currency"),
        CheckConstraint(QUEST_TERM_SHAPE_CHECK, name="ck_quest_offer_term_shape"),
        Index("idx_quest_offer_term_offer", "offer_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
    term_order: int
    direction: str
    currency: str
    counterparty_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
    skill_key: Optional[str] = None
    amount: Optional[int] = None
    level: Optional[str] = None


# -----------------------------------------------------------------------------
# quest_term  (an accepted quest's own copy of its offer's terms, B1: editing
# the offer never changes a bargain already struck). Same columns and CHECKs
# as `quest_offer_term`, `quest_id` in place of `offer_id`; immutable.
# -----------------------------------------------------------------------------
class QuestTerm(SQLModel, table=True):
    __tablename__ = "quest_term"
    __table_args__ = (
        CheckConstraint(QUEST_TERM_DIRECTION_CHECK, name="ck_quest_term_direction"),
        CheckConstraint(QUEST_TERM_CURRENCY_CHECK, name="ck_quest_term_currency"),
        CheckConstraint(QUEST_TERM_SHAPE_CHECK, name="ck_quest_term_shape"),
        Index("idx_quest_term_quest", "quest_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    quest_id: str = Field(foreign_key="quest.id", nullable=False)
    term_order: int
    direction: str
    currency: str
    counterparty_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
    skill_key: Optional[str] = None
    amount: Optional[int] = None
    level: Optional[str] = None


# -----------------------------------------------------------------------------
# quest_economy  (a world's rates of the indicative unit, C1/E1 -- one row per
# world, the `conversation_window_config` precedent). A NULL column, or no
# row at all, reads the code's default (`quest_value.DEFAULT_RATES`); the
# reader never writes. Curated config, no `change_history`; written only by
# `writes.upsert_quest_economy`. The unit is a display: never converted.
# -----------------------------------------------------------------------------
class QuestEconomy(SQLModel, table=True):
    __tablename__ = "quest_economy"
    __table_args__ = (
        Index("idx_quest_economy_world", "world_id", unique=True),
        CheckConstraint(
            "(rate_money IS NULL OR rate_money >= 0) AND (rate_relation IS NULL OR rate_relation >= 0) "
            "AND (rate_fact IS NULL OR rate_fact >= 0) AND (rate_skill IS NULL OR rate_skill >= 0) "
            "AND (band_low_pct IS NULL OR band_low_pct >= 0) "
            "AND (band_high_pct IS NULL OR band_high_pct >= 0) "
            "AND (debt_fact_relation IS NULL OR debt_fact_relation >= 0) "
            "AND (debt_skill_relation IS NULL OR debt_skill_relation >= 0)",
            name="ck_quest_economy_rates",
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    rate_money: Optional[int] = None
    rate_relation: Optional[int] = None
    rate_fact: Optional[int] = None
    rate_skill: Optional[int] = None
    band_low_pct: Optional[int] = None
    band_high_pct: Optional[int] = None
    # v2.19 (TICKET-0110): what the creditor's regard falls by when a debt's
    # fact or skill can no longer be delivered (he already holds it); NULL
    # reads the code's default (`quest_value.DEFAULT_RATES`: 10 and 20).
    debt_fact_relation: Optional[int] = None
    debt_skill_relation: Optional[int] = None
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# debt  (what one entity owes another, v2.19, TICKET-0110, BRIEF-0110-A, J2)
#
# Born of a service (S2), of a quest settled on credit (A2) or of the
# creator's hand. The debtor is a character; the creditor a character or a
# faction (J1); a faction creditor always names its contact, an active
# member (X1), and a character creditor never does (writer-checked). What is
# owed is a list of typed terms (`debt_term`, C2); its indicative value is
# computed at read, never stored and never converted (C1 of the series).
#
# A debt is SETTLED or FORGIVEN, never deleted (J2): `status` leaves `open`
# once, with `closed_at` and, for a remission, `closed_note`; nothing else
# on the row moves after creation. Its fact (`fact_id`, a free `information`
# fact whose participants are the parties, F-a) receives a `changement` at
# that moment, so whoever learned the debt earlier keeps the old version
# until a later contact (TICKET-0105).
#
# This table is the one way to say « X owes Y » (I2): the relation type
# `debt` is retired and never written by this table or any other path.
# -----------------------------------------------------------------------------
DEBT_ORIGINS: tuple[str, ...] = ("service", "quest", "creator")
DEBT_STATUSES: tuple[str, ...] = ("open", "settled", "forgiven")
DEBT_CURRENCIES: tuple[str, ...] = ("money", "item", "fact", "skill")


class Debt(SQLModel, table=True):
    __tablename__ = "debt"
    __table_args__ = (
        CheckConstraint("origin IN ('service','quest','creator')", name="ck_debt_origin"),
        CheckConstraint("status IN ('open','settled','forgiven')", name="ck_debt_status"),
        CheckConstraint("debtor_entity_id <> creditor_entity_id", name="ck_debt_parties"),
        CheckConstraint("(origin = 'quest') = (origin_quest_id IS NOT NULL)", name="ck_debt_origin_quest"),
        CheckConstraint("(status = 'open') = (closed_at IS NULL)", name="ck_debt_closed"),
        Index("idx_debt_world", "world_id"),
        Index("idx_debt_debtor", "debtor_entity_id"),
        Index("idx_debt_creditor", "creditor_entity_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    debtor_entity_id: str = Field(foreign_key="entity.id", nullable=False)
    creditor_entity_id: str = Field(foreign_key="entity.id", nullable=False)
    contact_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    origin: str
    origin_quest_id: Optional[str] = Field(default=None, foreign_key="quest.id")
    reason: Optional[str] = None
    is_secret: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    fact_id: str = Field(foreign_key="fact.id", nullable=False)
    status: str = Field(default="open", sa_column_kwargs={"server_default": text("'open'")})
    created_at: datetime = _created_ts()
    closed_at: Optional[datetime] = None
    closed_note: Optional[str] = None


# -----------------------------------------------------------------------------
# debt_term  (one thing a debt owes, C2/T1). Written with its debt, never
# touched again. Money and items count; a fact is delivered (the creditor --
# his contact for a faction -- learns it); a skill is taught (the debtor
# must be Maître). No relation: regard is not repaid.
# -----------------------------------------------------------------------------
DEBT_TERM_SHAPE_CHECK = (
    "(currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) "
    "AND (currency <> 'item' OR item_id IS NOT NULL) "
    "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
    "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
)


class DebtTerm(SQLModel, table=True):
    __tablename__ = "debt_term"
    __table_args__ = (
        CheckConstraint("currency IN ('money','item','fact','skill')", name="ck_debt_term_currency"),
        CheckConstraint(DEBT_TERM_SHAPE_CHECK, name="ck_debt_term_shape"),
        Index("idx_debt_term_debt", "debt_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    debt_id: str = Field(foreign_key="debt.id", nullable=False)
    term_order: int
    currency: str
    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
    skill_key: Optional[str] = None
    amount: Optional[int] = None
