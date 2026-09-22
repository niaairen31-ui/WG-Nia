# LOT — TICKET-0090 "Perceiver-oriented relations"

## Objective and cut

Every social relation row becomes one perceiver's feeling toward one target
(`entity_a` feels, `entity_b` receives, `direction = 'a_to_b'` always), each
carrying one typed `lien` fact so the relation can be known, with
`visible_to_b` replaced by real knowledge rows. The four surfaces that
display a relation say who feels what toward whom instead of printing
`a_to_b`.

The lot stops there. Identity tokens in prose (F1), facets (G2), the
`rencontre` registry (R1), and the physical drop of the now-dead
`relation.visible_to_b` column are later tickets. `controls` keeps its
current shape and gets no fact.

## Briefs in this lot

| letter | slug | one line |
|---|---|---|
| A | oriented-core | pure orientation module, `write_relation` guard, typed fact at birth, oriented finder, fixtures, new G1 check |
| B | migration-v2-04 | partial unique index, data migration (orient, split, lien facts, U3 knowledge, connects_to backfill), schema docs |
| C | crud-and-lore | relation payload, create/PUT/DELETE routes, target-knows route, Lore dossier rendering |
| D | editors | RelationsEditor and the graph edge form: sentences, reciprocal, "X le sait" |
| E | link-agent | commit through the oriented writer, coherence whitelist, LinkAgent staged-row labels |

## Dependency graph

- A -> B: B's migration imports C-01, C-02 and C-03 from the module A creates.
- A -> C: C's routes call C-06, C-07, C-08 and C-09.
- B -> C: C's `target_knows` and delete cascade assume every existing social
  relation already has its lien fact.
- C -> D: D renders the payload shape C-10.
- A -> E: E's commit calls C-07.
- E last **by choice, not by dependency** (locked decision: the creator
  surfaces are proven by hand before the agent writes through the new path).

## RECON

Carried from RECON-0090 (run 2026-09-22 against `main` at `8b939361`), with
the session-2 findings appended. Every property asserted below was opened in
the file that declares it.

### R-01 — the relation row
Opened: `models/canon_knowledge.py:23-53`.
Finding: the only CHECK is `intensity BETWEEN 1 AND 100`; the three indexes
(`entity_a_id`, `entity_b_id`, `world_id`) are plain; `direction` defaults to
`'mutual'` with no CHECK; `visible_to_b` defaults TRUE; `type` is free text;
`change_history` is JSON NOT NULL.
Consequence: orientation and uniqueness are new; both guards are added by
this lot.

### R-02 — direction vocabulary and perceiver readers
Opened: `crud/_shared.py:141`, `link_author.py:71`, `context.py:113-114`,
`tick_context.py:87-88`, `play_initiative.py:458-460`; the perceiver
functions `context.py:128-134`, `tick_context.py:112-116` (imported by
`tick_normalize.py:28`, used at `:113`), `play_initiative.py:457-462`.
Finding: every perceiver reader treats `entity_a` as the perceiver under
`a_to_b`.
Consequence: normalizing every social row to `a_to_b` leaves all four
readers correct with no edit. Their `b_to_a`/`mutual` branches become
unreachable for social rows, not wrong.

### R-03 — the social/structural split already has one definition
Opened: `context.py:108-110`.
Finding: `RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "controls")`,
imported by `crud/relations.py:18`, `link_context.py:21`,
`link_author.py:34`.
Consequence: the lot reuses it and never re-types it; moving its definition
into the new pure module keeps it single.

### R-04 — the write chokepoint
Opened: `writes/relations.py:1-174`; `tooling/verify/canon_write_policy.txt:19`.
Finding: `_find_relation_pair` (`:36-51`) matches both orders, no world or
type filter, `.first()`. Delta (`:62-79`) changes only `intensity` and
`last_evolved_at` on an existing row; the delta's `type` is used only when
creating. New rows default to `direction='mutual'` (`:123`) and
`visible_to_b=True` (`:124`). Set with `relation_id` (`:88-100`) snapshots
history, then overwrites type, direction, visible_to_b, notes.

### R-05 — every delta producer puts the changing side in `entity_a`
Opened: `tick_normalize.py:673-674`, `analyzer_transcript.py:308-313`,
`cockpit/mutations.py:150-175` and `:335-356`, `day_mutations.py:184-190`.
Consequence: an oriented lookup keyed on the perceiver matches producer
semantics; no payload shape changes.

### R-06 — `_find_relation_pair` callers
Opened: `writes/relations.py:68`, `cockpit/mutations.py:556`,
`tick_context.py:171`, `cockpit/crud/relations.py:129`; the finder docstring
`writes/relations.py:37-45`.
Finding: three social callers (delta, the `relation_gte` prerequisite judge,
the briefing line) and one `connects_to` caller that must stay unordered.

### R-07 — creator CRUD
Opened: `cockpit/crud/relations.py:80-208`.
Finding: `RelationWriteBody` carries `direction` and `visible_to_b`
(`:95-104`); create makes the sheet entity `entity_a` (`:136`) and
delegates `connects_to` to `connect_locations` (`:123-130`); PUT overwrites
direction (`:149-170`); DELETE removes the relation row only (`:173-180`);
graph edges expose `source`, `target`, `direction` (`:196-208`).

### R-08 — link agent
Opened: `link_author.py:60-71`, `:243`, `:296-320`, `:561`, `:586-600`,
`:646-690`, `:830-843`, `:930-946`; `checks/link_agent_strata.py:1-30`.
Finding: `_LINK_RELATION_TYPES` excludes `connects_to`/`controls`; a staged
relation payload is exactly `write_relation`'s kwargs
(`mode`, `relation_id`, `world_id`, `entity_a_id`, `entity_b_id`, `type`,
`value`, `direction`, `visible_to_b`, `notes`); commit calls
`write_relation(db, **row.payload)` (`:942`); the coherence whitelist
`_CANON_RELATION_WHITELIST` includes `direction` and `visible_to_b`
(`:646`); pair exclusion skips a pair holding a relation in either
direction (`:243`, `:561`). `link_agent_strata.py` forbids any direct
`db.add(Relation(...))` in `link_author.py` and requires the commit path to
route through `write_relation`.

### R-09 — display readers
Opened: `lore_selectors.py:102-137` (carries `subject_side`; excludes only
`connects_to`), `lore_render.py:39-44` (prints raw `direction`, ignores
`subject_side`), `crud/_shared.py:153-177` (`_relation_dict` returns
`role`, `_list_relations` feeds the entity payload),
`crud/entities.py:512,800,850,875` and `crud/entity_geometry.py:111,141`
(the sheet payload), `day_concordance.py:281-303` (`_cast_relation` reads
both orders, never direction).

### R-10 — frontend consumers
Opened: `creation/RelationsEditor.svelte:1-152` (raw select `:14`,
`:98-103`, `:136-141`; drops `role` `:22-31`; "Visible to B" `:106-108`,
`:144-146`), `graph/consumers/relations.js:84`, `:109-124`, `:143`,
`:148-166`, `creation/LinkAgent.svelte:137-151`,
`creation/DoorsEditor.svelte:34-36` (reads `type`, `other_entity_id`,
`other_entity_name` from the same payload), `graph/consumers/lieux.js:32-45`
(creates and deletes `connects_to` edges).
Consequence: the payload change must be additive — DoorsEditor reads three
existing keys.

### R-11 — `relation.notes` is the perceiver's own view
Opened: `context.py:137-142`, `tick_context.py:122`.
Finding: rendered into the perceiver's context as
`- {name} : {notes} (perception : {type}, disposition : …)`.
Consequence: notes stay on the relation row (decision V1).

### R-12 — `visible_to_b`
Opened: `writes/relations.py:124`, `crud/relations.py:141`,
`link_author.py:318` (all default TRUE); readers `crud/_shared.py:148,165`
and `link_context.py:102` only.
Consequence: no play assembler reads it; converting it creates knowledge
that will be read (`context.py:384`, `:732`).

### R-13 — typed facts
Opened: `models/canon_knowledge.py` (`ck_fact_spine_exclusive`,
`default_level` default `'unaware'`), `writes/facts.py:22-46` (`create_fact`
signature, with `relation_id`), `:66-74` (`attach_participants` refuses a
typed fact), `scripts/migrate_v2_00_connects_to_facts.py:69-160`.
Finding: v2.00 inserted one fact per `connects_to` edge with content
`"{name_a} communique avec {name_b}."`, `default_level='knows'`,
`created_by='migrate_v2_00'`, idempotent, with a `relation`-table checksum
as its post-check.

### R-14 — knowledge on a typed fact
Opened: `models/canon_knowledge.py:182-218`, `writes/knowledge.py:150-207`,
`:226-254`.
Finding: `write_knowledge` accepts `fact_id`; `subject` is required text;
`subject_entity_ids` is the only path to participants and must stay unused
for a typed fact.

### R-15 — deleting a relation that carries a fact fails
Opened: `db.py:126` (`PRAGMA foreign_keys=ON`), `crud/relations.py:173-180`;
experiment E-1 (RECON-0090 §6).
Finding: `IntegrityError`, HTTP 500. It already affects every
`connects_to` edge that v2.00 gave a fact, including the graph editor's
delete (`graph/consumers/lieux.js:41-44`).

### R-16 — scoped defaults reach play
Opened: `context.py:384`, `:732`, `knowledge_resolve.py:278-300`.
Finding: NPC context and the MJ player block union stored knowledge rows
with `resolve_default_rows`.

### R-17 — checks that build relations
Opened: `checks/fact_spine.py:126-135` (social `ally`, `direction="mutual"`,
then a manual `create_fact(relation_id=…)`; the typed fact is only the
target of the deliberate participant break at `:168-172`),
`checks/known_reachability.py:122-137` (three `connects_to` edges built
through `write_relation`, each followed by a manual
`create_fact(default_level="knows")`), `:224-238` (edge D->E whose manual
fact carries a world-scoped `rumor` default), `:277-283` (an edge
**deliberately** left without a fact, to prove the fail-closed rule),
`checks/door_coverage.py:126-133`, `checks/door_distinct_points.py:125,192-193`
(via `connect_locations`), `checks/context_disclosure_floor.py:105-112`
(`Relation(...)` built directly, already `a_to_b`).
Consequence: a typed fact born inside `write_relation` breaks
`known_reachability`'s cases 2 and 3 unless their fixtures are rebuilt in
the same brief. This is gate (e)'s central item.

### R-18 — budgets
Opened: `checks/module_budget.py:58` (`MAX_LINES = 1000`),
`checks/function_length.py:29` (`MAX_LINES = 80`); `wc -l`:
`link_author.py` 955, `context.py` 956, `mutations.py` 925,
`writes/relations.py` 174, `writes/facts.py` 103,
`crud/relations.py` 304, `crud/_shared.py` 274, `lore_render.py` 262.
Consequence: nothing new lands in `link_author.py`, `context.py` or
`mutations.py` beyond a call and an import.

### R-19 — where the directed `visible_to_b` values come from
Opened: `tooling/tickets/TICKET-0036-npc-link-agent.md:40-43`,
`scripts/seed_pilot.py:1664` (the prompt asks the model to prefer a relation
one side hides), `:3522-3742` (12 FALSE and 3 TRUE written by hand),
`creation/LinkAgent.svelte:150-151` (the checkbox is editable before
commit).
Finding: on directed rows the value passed a review surface; on `mutual`
rows it carries no information.
Consequence: decision U3 converts the `a_to_b` TRUE rows only.

### R-20 — `visible_to_b` has no defined meaning on a `b_to_a` row
Opened: R-12's enumeration (no play reader), `crud/_shared.py:148`.
Finding: on `b_to_a`, `entity_b` is the perceiver, so "Visible to B" names
the side that already feels; no code fixes the meaning.
Consequence: the 6 `b_to_a` TRUE rows are reported, never converted.

### R-21 — canon write policy and its check
Opened: `tooling/verify/canon_write_policy.txt:9-20`, `:105-150`;
`checks/single_canon_write.py:1-20`.
Finding: `[ALLOWED_SITES]` is `path::function  tables`; the check is
function-scoped and attributes every `.add()`/`.delete()`/raw `execute()`.
Current relation-family sites: `writes/relations.py::write_relation
relation`, `crud/relations.py::delete_relation relation`,
`writes/facts.py::create_fact fact`, `::attach_participants
fact_participant`, `::create_fact_default fact_default`,
`writes/knowledge.py::write_knowledge knowledge`,
`crud/knowledge.py::delete_knowledge knowledge`.

### R-22 — the cascade-delete precedent
Opened: `CLAUDE.md:288-292`.
Finding: a `skill_definition` delete already removes its dependent rows then
itself in one transaction, with no history snapshot — "a named exception to
History is sacred, scoped to one row".
Consequence: T1 follows a pattern that exists; the ARCHITECTURE_DECISIONS
entry names it.

### R-23 — history snapshots
Opened: `writes/_shared.py:25-41`.
Finding: `_append_history_snapshot(rel, mutation_id)` records only
`intensity`, `last_evolved_at` and `mutation_id`. Endpoints and direction
are not in the snapshot shape.
Consequence: the migration writes its own history entry naming what it
changed.

### R-24 — every `connects_to` creation path
Opened: `crud/relations.py:123-130` and `routes/room_batch.py:162,186`
(via `connect_locations`), `routes/regions.py:281-286` (direct
`write_relation`, despite `spatial_author.py:110-131`'s docstring claiming
region commit goes through `connect_locations`),
`spatial_author.py:124-131` (writes the relation and no fact).
Consequence: W1 belongs in `write_relation`, the one point all four paths
cross. It is also why S-1 exists.

### R-25 — prod counts, 2026-09-22
Social relations by `direction` and `visible_to_b`: `a_to_b` 52 FALSE /
40 TRUE, `b_to_a` 8 FALSE / 6 TRUE, `mutual` 67 TRUE / 0 FALSE.
`connects_to` edges with no typed fact: 2.
Consequence: the migration ends with 240 social rows, 240 lien facts,
2 new `connects_to` facts, 40 knowledge rows, 6 reported rows.

## Contract sheet

### C-01 — `lien_fact_content`
Produced by: BRIEF-0090-A   Consumed by: A (writer), B (migration)
Module: `src/world_engine/relation_orientation.py`
Signature: `lien_fact_content(name_a: str, relation_type: str, name_b: str) -> str`
Return: `f"{name_a} éprouve « {relation_type} » envers {name_b}."`
Error and empty cases: no validation, no DB; an empty name or type is
rendered as given (the caller resolves names before calling).

### C-02 — `connects_to_fact_content`
Produced by: BRIEF-0090-A   Consumed by: A (writer), B (migration)
Signature: `connects_to_fact_content(name_a: str, name_b: str) -> str`
Return: `f"{name_a} communique avec {name_b}."` — byte-identical to
migrate_v2_00's content (R-13), so a re-run finds nothing to change.

### C-03 — `is_social` and the excluded set
Produced by: BRIEF-0090-A   Consumed by: A, B, C, E
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to", "controls")`
`is_social(relation_type: str) -> bool` — `relation_type not in
RELATION_GRAPH_EXCLUDED_TYPES`. `None` returns False.
`context.py` imports the constant from here instead of declaring it; every
current importer of `context.RELATION_GRAPH_EXCLUDED_TYPES` keeps working.

### C-04 — `orient_legacy`
Produced by: BRIEF-0090-A   Consumed by: B (migration), E (link agent)
```
@dataclass(frozen=True)
class OrientedSpec:
    perceiver_id: str
    target_id: str
    target_knows: bool
    visibility_ambiguous: bool

orient_legacy(direction: str, entity_a_id: str, entity_b_id: str,
              visible_to_b: bool) -> list[OrientedSpec]
```
Case table (the whole closed set):
| direction | visible_to_b | returns |
|---|---|---|
| `a_to_b` | True | `[(a, b, True, False)]` |
| `a_to_b` | False | `[(a, b, False, False)]` |
| `b_to_a` | True | `[(b, a, False, True)]` |
| `b_to_a` | False | `[(b, a, False, False)]` |
| `mutual` | True or False | `[(a, b, False, False), (b, a, False, False)]` |
| anything else | any | `ValueError` naming the value |

### C-05 — `write_relation`, amended
Produced by: BRIEF-0090-A   Consumed by: B (none), C, E, and every existing caller
Signature unchanged except `direction: str = "a_to_b"` (was `"mutual"`).
Rules:
- `is_social(type)` and `direction != "a_to_b"` -> `ValueError`
  (`"write_relation: social relation <type> must be a_to_b, got <direction>"`).
- On every create, after `db.add(rel)` and `db.flush()`:
  social -> `create_fact(content=lien_fact_content(name_a, type, name_b),
  default_level="unaware", relation_id=rel.id, created_by=changed_by)`;
  `connects_to` -> same call with C-02's content and `default_level="knows"`;
  `controls` -> no fact.
- `mode="set"` with `relation_id` on a social row whose `type` changes ->
  `update_typed_fact_content` (C-11) on its lien fact.
- `mode="delta"`: social -> `_find_perceived_relation` (C-06); excluded
  types -> `_find_relation_pair`, unchanged.
- Return value unchanged (the `Relation`).
Error cases: an endpoint entity that does not exist -> `ValueError` naming
the id (needed for the fact's content).

### C-06 — `_find_perceived_relation`
Produced by: BRIEF-0090-A   Consumed by: A (delta), `mutations.py`, `tick_context.py`
`_find_perceived_relation(db: Session, perceiver_id: str, target_id: str) -> Optional[Relation]`
Exactly `entity_a_id == perceiver_id and entity_b_id == target_id` and
`is_social(type)`. `.first()`; C-12's index makes at most one row possible
after the migration. Returns None when there is none.

### C-07 — `write_oriented_relations`
Produced by: BRIEF-0090-A   Consumed by: C (create route), E (link agent commit)
```
write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type,
                         value, direction, visible_to_b=False, notes=None,
                         changed_by, mode="set", relation_id=None) -> list[Relation]
```
Normalizes with C-04, then one `write_relation(mode="set", direction="a_to_b")`
per spec, in the returned order, then `set_target_knows` (C-08) for each spec
whose `target_knows` is True. `mode != "set"` or `relation_id is not None`
-> `ValueError`. `visibility_ambiguous` is ignored here (the migration is the
only reader that reports it). Accepting `mode` and `relation_id` lets the
link agent pass `**row.payload` unchanged (R-08).

### C-08 — `set_target_knows`
Produced by: BRIEF-0090-A   Consumed by: A (C-07), C (route)
`set_target_knows(db, *, rel: Relation, knows: bool, changed_by: str) -> Optional[Knowledge]`
- `is_social(rel.type)` is required, else `ValueError`.
- True: if `entity_b` has no knowledge row on the lien fact, create one with
  `write_knowledge(mode="update", entity_id=rel.entity_b_id, fact_id=lien.id,
  subject=lien.content, content=lien.content, level="knows",
  source=f"relation {rel.id}", is_secret=False, is_incorrect=False,
  share_threshold=50, changed_by=changed_by)`; returns it. Already there ->
  returns it unchanged.
- False: deletes that row if present (`db.delete`), returns None.
- No lien fact -> `ValueError` naming the relation id.

### C-09 — `lien_fact_of`
Produced by: BRIEF-0090-A   Consumed by: A, C
`lien_fact_of(db: Session, rel: Relation) -> Optional[Fact]` — the single
`fact` row whose `relation_id` is `rel.id`, or None.

### C-10 — the relation payload
Produced by: BRIEF-0090-C   Consumed by: D
`_relation_dict` keeps every key it returns today (`id`, `role`,
`other_entity_id`, `other_entity_name`, `other_entity_type`, `type`,
`direction`, `intensity`, `visible_to_b`, `notes`, `last_evolved_at`) — the
doors editor reads three of them (R-10) — and adds:
`perceiver_id`, `perceiver_name`, `target_id`, `target_name`,
`sheet_side` (`"perceiver"` or `"target"`), `is_social` (bool),
`target_knows` (bool; False for a structural row).

### C-11 — `update_typed_fact_content`
Produced by: BRIEF-0090-A   Consumed by: A
`update_typed_fact_content(db, *, fact: Fact, content: str, changed_by: str) -> Fact`
in `writes/facts.py`: appends `{"content": <previous>, "changed_by": …,
"at": <iso>}` to `fact.change_history`, `flag_modified`, sets the new
content, `db.add(fact)`. Policy line
`writes/facts.py::update_typed_fact_content  fact`.

### C-12 — the partial unique index
Produced by: BRIEF-0090-B   Consumed by: A (C-06's "at most one"), C (409)
Name: `idx_relation_oriented_social`, declared in
`models/canon_knowledge.py`'s `Relation.__table_args__` and created by the
migration:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_relation_oriented_social
  ON relation(entity_a_id, entity_b_id)
  WHERE type NOT IN ('connects_to','controls');
```

### C-13 — the target-knows route
Produced by: BRIEF-0090-C   Consumed by: D
`PUT /api/relations/{relation_id}/target-knows`, body `{"knows": bool}`.
404 unknown relation; 409 on a structural relation; returns
`_relation_dict(rel, rel.entity_a_id, db)`.

## Gate output

### (a) Property trace — every asserted property, its finding, the file opened

| property asserted | finding | declaring file opened |
|---|---|---|
| `relation` has no direction CHECK, no unique index, `visible_to_b` defaults TRUE | R-01 | `models/canon_knowledge.py:23-53` |
| every perceiver reader treats `entity_a` as perceiver under `a_to_b` | R-02 | `context.py:113-134`, `tick_context.py:87-116`, `play_initiative.py:457-462` |
| the social/structural split is one constant | R-03 | `context.py:108-110` |
| the delta ignores `type` on an existing row; pair lookup is order-blind | R-04 | `writes/relations.py:36-79` |
| producers put the changing side in `entity_a` | R-05 | `tick_normalize.py:673-674`, `analyzer_transcript.py:308-313` |
| four callers of `_find_relation_pair`, one structural | R-06 | the four call sites |
| CRUD create makes the sheet entity `entity_a`; DELETE removes the row only | R-07 | `crud/relations.py:106-208` |
| the staged link payload is `write_relation`'s kwargs; commit routes through it | R-08 | `link_author.py:296-320`, `:930-946`, `checks/link_agent_strata.py` |
| `lore_render` prints raw direction and ignores `subject_side` | R-09 | `lore_render.py:39-44`, `lore_selectors.py:102-137` |
| DoorsEditor reads `type`/`other_entity_id`/`other_entity_name` | R-10 | `creation/DoorsEditor.svelte:34-36` |
| `notes` is rendered to the perceiver | R-11 | `context.py:137-142`, `tick_context.py:122` |
| `visible_to_b` has no play reader and defaults TRUE in all writers | R-12 | `writes/relations.py:124`, `crud/relations.py:141`, `link_author.py:318` |
| `create_fact` takes `relation_id`; a typed fact refuses participants | R-13 | `writes/facts.py:22-74` |
| `write_knowledge` takes `fact_id`; `subject` is required | R-14 | `writes/knowledge.py:150-207` |
| deleting a relation with a fact raises IntegrityError under FK ON | R-15 | `db.py:126` + experiment E-1 |
| scoped defaults are unioned into NPC and MJ contexts | R-16 | `context.py:384`, `:732`, `knowledge_resolve.py:278-300` |
| `known_reachability` case 3 needs an edge with no fact | R-17 | `checks/known_reachability.py:277-283` |
| `link_author.py` has 45 lines of budget left | R-18 | `checks/module_budget.py:58` + `wc -l` |
| directed `visible_to_b` values passed a review surface | R-19 | `TICKET-0036:40-43`, `seed_pilot.py:1664`, `LinkAgent.svelte:150-151` |
| `visible_to_b` is undefined on `b_to_a` | R-20 | `crud/_shared.py:148` + R-12's absence of a reader |
| allowed-site lines are `path::function tables`, function-scoped | R-21 | `canon_write_policy.txt:9-20`, `checks/single_canon_write.py:1-20` |
| a cascade delete precedent exists | R-22 | `CLAUDE.md:288-292` |
| the history snapshot shape carries no endpoints | R-23 | `writes/_shared.py:25-41` |
| four `connects_to` creation paths, all crossing `write_relation` | R-24 | `crud/relations.py:123-130`, `room_batch.py:162,186`, `regions.py:281-286`, `spatial_author.py:124-131` |

### (b) Case tables

**Orientation of a legacy row (C-04).** Written out in C-04; all six rows
reachable: prod holds `a_to_b` TRUE (40) and FALSE (52), `b_to_a` TRUE (6)
and FALSE (8), `mutual` TRUE (67); the `ValueError` row is reachable only
from a hand-written value, and the migration's pre-check counts them.

**`write_relation` by type class and mode (C-05).**

| type class | create (set) | create (delta) | update (set) | update (delta) |
|---|---|---|---|---|
| social | row + lien fact, `a_to_b` forced, any other direction raises | same, direction `a_to_b` | type change refreshes lien content | intensity only, row found by C-06 |
| `connects_to` | row + fact (C-02, `knows`) | row + fact | no fact touched | row found by `_find_relation_pair` |
| `controls` | row, no fact | row, no fact | no fact touched | row found by `_find_relation_pair` |

**Delete (T1).** `connects_to`/`controls` with a fact -> knowledge rows of
that fact, then its `fact_default` rows, then the fact, then the relation.
Social -> identical. A relation with no fact (legacy `controls`) -> the
relation alone. Each layer flushed before the next (R-13's FK ordering
trap).

**`target_knows` (C-08).** knows=True with no row -> created; with a row ->
unchanged; knows=False with a row -> deleted; knows=False with no row ->
no-op; structural relation -> `ValueError` (route: 409).

### (c) Enumerations

Pasted in RECON-0090 §8 (direction vocabulary sites; files reading
`direction`; `_find_relation_pair` callers; `write_relation` call sites;
`visible_to_b` sites; `rel.notes` readers; frontend files naming the
vocabulary; checks constructing relations) and §11 (prod Q1/Q2).
Negative claims used by this lot and the positive look behind each:
- "no play assembler reads `visible_to_b`" — the full `grep -rn
  visible_to_b src` output in §8.5, every hit accounted for.
- "`connects_to` is created at four places" — the `connect_locations(` and
  `write_relation(` call-site enumerations in §8.4 plus R-24.
- "nothing else constructs a `Relation` in `src/`" — `grep -rn "Relation("
  --include=*.py src` returns `writes/relations.py`, `models/`, and the
  finder signatures only.

### (d) Family contracts

Written before their members and re-read after the last one:
- the writer family C-05 / C-06 / C-07 / C-08 / C-09 — every member takes
  `db` first, keyword-only after, raises `ValueError` (never a bare
  `assert`), and returns the row it wrote or None.
- the content family C-01 / C-02 — same shape, pure, no DB.
- the payload family C-10 / C-13 — both return `_relation_dict`'s shape.

### (e) Check satisfaction

Gates this lot proposes:
- `relation_orientation.py` (new, brief A) — satisfied by
  `relation_orientation.py` + `writes/relations.py`; it needs a DB, so it
  uses the temp-file SQLite fixture idiom of `fact_spine.py` /
  `door_coverage.py` and never touches the real database.

Gates this lot must merely pass:
- `module_budget.py` — `link_author.py` is at 955/1000, so brief E adds one
  import and one call; the orientation logic lives in its own module.
- `function_length.py` — `write_relation` gains the fact birth through a
  helper (`_birth_typed_fact`), not inline.
- `fact_spine.py` — its fixture writes a social `mutual` relation (R-17);
  brief A rewrites that fixture to `a_to_b` and takes the auto-born lien
  fact as the typed fact for its deliberate break.
- `known_reachability.py` — cases 1, 2 and 3 assume `write_relation` births
  no fact (R-17); brief A rewrites all three: case 1 reads the auto fact,
  case 2 puts its world-scoped `rumor` default on the auto fact, case 3
  builds its deliberately fact-less edge with a direct
  `session.add(Relation(...))` (a check fixture, outside `src/`, so
  `single_canon_write.py` and `fact_spine.py`'s AST scan do not see it).
- `single_canon_write.py` — three policy lines: `set_target_knows`
  (knowledge), `update_typed_fact_content` (fact), and `delete_relation`
  gains `knowledge fact_default fact`.
- `link_agent_strata.py` — brief E's commit still routes through
  `writes/relations.py`; no `LinkBatch` name enters `writes/`.
- `lore_isolation.py` — brief C touches only the pure renderer and the
  selector's row shape; no `db.add`/`commit` enters either module.
- `schema_version_agreement.py` — brief B moves the constant, the doc
  header and the changelog in one commit.
- `frontend_build_fresh.py` / `static_asset_freshness.py` — briefs D and E
  each rebuild and commit the bundle.
- `corpus_gate.py` — run at the end of every brief.

## Amendments

(none yet)
