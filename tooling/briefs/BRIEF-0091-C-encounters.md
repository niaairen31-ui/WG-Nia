# BRIEF 0091-C — "the encounter registry and its write points"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: A (table), B (`play.py` headroom)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `models/ephemeral.py` defines `Rencontre` and `ENCOUNTER_SOURCES` (A).
- `routes/scene.py:153-158` — `db.add(Visit(...))` in `enter_scene`
  (`:94`), `present_npc_ids=current_npc_ids`.
- `gathering.py:254` in `generate_gatherings`, `:440` in `migrate_npc`.
- `cockpit/play.py` `_join_gathering` adds the player's
  `GatheringMember` (after B, line numbers shift; the function body is
  unchanged from `:901-926`).
- `routes/play.py:126` in `start_conversation` (`:82`), `npc_id=body.npc_id`.
- `writes/config.py:462` `write_npc_schedule`; `writes/relations.py:285-292`
  the `is_new` branch calling `_birth_typed_fact`.

## Facts carried

### R-17 — encounter traces and their write points
Opened: `models/ephemeral.py:40-158`; `routes/scene.py:140-300`;
`gathering.py`; `cockpit/play.py:895-925`; `routes/play.py:118-135` [M].
Finding: `visit` (`ephemeral.py:144-158`, `present_npc_ids` JSON `:154`,
append-only per `checks/visit_delta.py` rule 1) is added once, at
`routes/scene.py:153-158` inside `enter_scene` (`:94`). `gathering.session_id` is NOT NULL
(`ephemeral.py:52`). `gathering_member` rows are added at
`gathering.py:254` (`generate_gatherings`, `:191`, one gathering per group,
NPC members), `:394` (`attach_on_arrival`, `:346`, solo gathering),
`:440` (`migrate_npc`, `:403`), `cockpit/play.py:916` (`_join_gathering`,
`:901`, the player). `conversation` (`ephemeral.py:84-100`, `player_id` NOT
NULL, `npc_id` nullable) is created at `routes/scene.py:217` and `:293`
(`npc_id=None`) and `routes/play.py:126` inside `start_conversation` (`:82`,
`npc_id=body.npc_id`).
Consequence: C records encounters at `scene.py` (visit), the four
membership sites (pairs among the gathering's open members), and
`routes/play.py:126`. `scene.py:217/293` carry no NPC and record nothing.

### R-18 — `npc_schedule`
Opened: `models/schedule.py:40-64`; `writes/config.py:462-539` [M].
Finding: one row per `(npc_id, phase)` (`idx_npc_schedule_npc_phase`
unique), `location_id` NOT NULL, no `change_history`; sole writer
`write_npc_schedule` (full replace per NPC, policy `:40`). Prod (Nia,
2026-09-22) [C]: 3 co-present pairs across two worlds, never more than 2
NPCs per `(location, phase)`.
Consequence: Q10a/Q11a — `write_npc_schedule` records a `schedule`
encounter for every other NPC sharing an exact `(location_id, phase)` with
the rows it writes.

### R-19 — `write_relation` and the lien fact
Opened: `writes/relations.py:123-294`; `relation_orientation.py:23-45` [M].
Finding: `write_relation` (`:220-294`) creates then flushes, then
`_birth_typed_fact` (`:133-147`) when `is_new` (`:285-292`). The function
body is about 75 lines (80 is the ceiling). `_endpoint_names` (`:123-130`)
returns the two names. `lien_fact_content(name_a, relation_type, name_b)`
(`relation_orientation.py:33-35`) returns
`f"{name_a} éprouve « {relation_type} » envers {name_b}."`;
`connects_to_fact_content` (`:38-41`). Both typed births pass through
`create_fact(relation_id=…)`.
Consequence: C adds the encounter in a helper called from the `is_new`
branch (not inline, to stay under 80 lines). A tags both typed births with
facet `lien`. J poses tokens in the lien content.

### R-20 — non-canon bookkeeping posture
Opened: `tooling/verify/canon_write_policy.txt:152-159`;
`models/ephemeral.py:136-141`;
`tooling/verify/checks/single_canon_write.py:1-30` [M].
Finding: `single_canon_write.py` gates only tables in `[CANON_TABLES]`;
`visit`, `gathering`, `conversation` and the observation telemetry tables
are deliberately outside it, each with its own chokepoint and, for
observation, its own check (`observation_socle.py`).
Consequence: `rencontre` (derived from play traces and authored state,
never edited by hand) and `unresolved_mention` (a worklist) are non-canon.
Each gets one writer module and a dedicated check (C-06, C-15).

### R-31 — the crud router and write timestamps
Opened: `src/world_engine/cockpit/crud/_router.py:12`;
`cockpit/crud/__init__.py:8-16,62-97`; `models/ephemeral.py:84-160` [M].
Finding: every `crud/<domain>.py` decorates the single
`router = APIRouter(prefix="/api", tags=["author-crud"])`; `crud/__init__.py`
imports each domain module (a re-export surface, no logic).
`conversation.started_at`, `visit.entered_at`, `gathering_member.joined_at`
/ `left_at`, `relation.created_at`, `npc_schedule.created_at` are the
timestamps available to the backfill.
Consequence: C-12 lives in a new `crud/facets.py` imported by
`crud/__init__.py`; C's backfill orders candidate pairs by those columns.

## Contracts

### C-06 — the `rencontre` table (`models/ephemeral.py`)
Produced by: A   Consumed by: C, D
```python
class Rencontre(SQLModel, table=True):
    __tablename__ = "rencontre"
    # idx_rencontre_pair UNIQUE (entity_lo_id, entity_hi_id)
    # idx_rencontre_hi (entity_hi_id)
    id: str (uuid pk); world_id: str FK world NOT NULL
    entity_lo_id: str FK entity NOT NULL   # min(a, b) as strings
    entity_hi_id: str FK entity NOT NULL   # max(a, b)
    first_at: datetime NOT NULL
    source: str NOT NULL     # in ENCOUNTER_SOURCES
    source_ref: str | None   # id of the visit/gathering/conversation/relation row
ENCOUNTER_SOURCES = ("visit", "gathering", "conversation", "schedule", "relation")
```
One row per unordered pair; the earliest known encounter wins; never
updated, never deleted. No JSON column.

### C-07 — the encounter writer (`src/world_engine/encounters.py`, new)
Produced by: C   Consumed by: D, the live sites
```python
def record_encounter(db, *, world_id, a_id, b_id, source, at=None,
                     source_ref=None) -> Rencontre | None
def record_encounters_among(db, *, world_id, entity_ids, source, at=None,
                            source_ref=None) -> int
def record_gathering_join(db, *, gathering_id, joiner_id) -> int
def acquaintances(db, entity_id) -> set[str]
def have_met(db, a_id, b_id) -> bool
```
`record_encounter`: `a_id == b_id` returns `None`; `source` outside
`ENCOUNTER_SOURCES` raises `ValueError`; an existing pair returns `None`
(idempotent, read guard before add); else adds and returns the row. `at`
defaults to now (UTC). `record_encounters_among`: every unordered pair of
the distinct ids, returns the number of new rows. `record_gathering_join`:
reads the gathering's `world_id`, pairs `joiner_id` with every other member
whose `left_at IS NULL`, source `gathering`, `source_ref` = the gathering
id; returns the number of new rows. `acquaintances`: every entity id paired
with `entity_id` in `rencontre`. The only module that adds a `Rencontre`.

## Context

Physique is "known from the first encounter" (R1). This brief gives
encounters a registry and records them where they happen: in play, in
standing schedules, and when a social relation is born.

## Scope IN

1. New `src/world_engine/encounters.py` per C-07 (all four functions).
2. `routes/scene.py::enter_scene`: bind the new `Visit` to a variable; after
   `db.add`, for each id in `current_npc_ids`, `record_encounter(world_id,
   player_id, npc_id, "visit", source_ref=<visit id>)`; commit unchanged.
3. `gathering.py::generate_gatherings`: after a group's members are added,
   `record_encounters_among(world_id=location.world_id,
   entity_ids=group["members"], source="gathering",
   source_ref=gathering.id)`.
4. `gathering.py::migrate_npc` and `cockpit/play.py::_join_gathering`:
   after the `GatheringMember` add, `record_gathering_join(db,
   gathering_id=<target>, joiner_id=<npc_id | conv.player_id>)`. The
   player's join inserts only when `existing is None`; record in the same
   branch.
5. `routes/play.py::start_conversation`: when `body.npc_id`,
   `record_encounter(world_id, player_id, body.npc_id, "conversation",
   source_ref=conv.id)` after the conversation is added.
6. `writes/config.py::write_npc_schedule`: after the rows are built, for
   each `(phase, location_id)`, every other NPC with a row at the same
   `(location_id, phase)` is recorded with source `schedule`.
7. `writes/relations.py`: new helper `_on_relation_born(db, rel,
   provenance)` = `_birth_typed_fact(db, rel, provenance)` then, when
   `is_social(rel.type)`, `record_encounter(rel.world_id, rel.entity_a_id,
   rel.entity_b_id, "relation", source_ref=rel.id)`. The `is_new` branch of
   `write_relation` calls the helper instead of `_birth_typed_fact`.
8. New `scripts/apply_ticket_0091_encounters.py` (idempotent backfill):
   collects candidate pairs from `visit` (player × `present_npc_ids`,
   `entered_at`), `gathering_member` (members of the same gathering whose
   intervals overlap, at the later `joined_at`), `conversation` (`player_id`
   × `npc_id`, `started_at`), `npc_schedule` (same `location_id`, `phase`,
   later `created_at`), social `relation` rows (`created_at`); sorts all
   candidates by timestamp and calls `record_encounter` in order, so each
   pair keeps its earliest encounter and source; prints counts per source;
   a second run inserts nothing.
9. New `tooling/verify/checks/encounter_registry.py`, rules R1-R4 of gate
   (e), with the function list of gate (e).

## Scope OUT

- Any read of `rencontre` by the resolver or a context (D, G).
- `attach_on_arrival` (a solo gathering has no pair).
- `routes/scene.py:217` and `:293` (no NPC on those conversations).
- A declared day creating encounters (R-b1, locked).
- Changing `_join_gathering`'s signature or place (R-29).

## Invariants to defend

- `visit` stays append-only (`visit_delta.py` rule 1): the brief only
  reads the row it just added.
- The canon-write doctrine: `rencontre` is non-canon; no canon table is
  written from a new site.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- `enter_scene` does not add the `Visit` in one place.
- A membership insert site exists beyond the four of R-17.

ADAPT:
- `write_relation` is still above 78 lines after the helper: move the
  `is_new` block into the helper as a whole; report.

REPORT-ONLY:
- Backfill counts per source on the DB it was run against.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Entering a scene with two NPCs present creates two `rencontre` rows
      with source `visit`; re-entering creates none.
- [ ] Creating a social relation A->B creates one `rencontre` row for
      `{A, B}`; creating B->A creates none.
- [ ] Two NPC schedules at the same `(location, phase)` create one row.
- [ ] The backfill, run twice, inserts rows once.
- [ ] Green: `encounter_registry.py`, `visit_delta.py`,
      `relation_orientation.py`, `function_length.py`, `module_budget.py`,
      `stream_session_readonly.py`, `gathering_lifecycle.py`,
      `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: "Encounter registry (TICKET-0091)" —
non-canon, one writer, materialized state encounters (Q10a, Q11a).
