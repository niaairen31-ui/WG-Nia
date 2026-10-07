# LOT — TICKET-0108 "Quest offers: authored by the creator, accepted as open plans, pinned to a day"

## Objective and cut

The creator authors quest offers (E1): a giver (a character or a faction,
H1), a title, steps, and requirements -- with no step, the eligibility that
decides who the offer is proposed to; with a step, what that step needs.
The requirement language is the day plan's (B1), widened from four forms to
eight: `has_met`, `faction_member`, `skill_rank_gte`, `quest_completed` join
`knowledge`, `relation_gte`, `resource`, `location_reachable`; the day-plan
model may still emit only the first four. `relation_gte` reads what the
target feels toward the character (B-dir). Accepting an offer creates an
agenda of the player born `paused`: one open plan among the others, so the
player runs as many quests as he wants without lifting the one-active-agenda
rule (A1); a day selects the plan it advances, or the player pins it (O1).
A quest's state is its agenda's (M1). Journée shows the offers the player is
eligible for (I1), his quests, « Accepter » and « Abandonner » (N1); the
plan behind a quest stays invisible there.

The lot stops before: costs and rewards of a quest and the « déclarer
accomplie » button (D1, C1 -- TICKET-0109), objects held in quantity
(`item_holding`, E1 -- TICKET-0109), the indicative unit, debts and services
(J2 -- TICKET-0110), rank trials (K1 -- TICKET-0111), quests proposed by the
model, quests created from the Lore tool, a requirement on a faction role
(it needs `faction_membership.role` tied to `faction_role` first),
artifacts, and any change to `legacy.html`.

## Briefs in this lot

- **A — schema v2.17, the eight-form vocabulary**: `quest_offer`,
  `quest_offer_step`, `quest_offer_requirement`, `quest`;
  `agenda_step_requirement`'s two CHECKs widened; `REQUIREMENT_TYPES`,
  `MODEL_REQUIREMENT_TYPES` and the three shape groups in `day_plan.py`; four
  evaluators, `relation_gte` reoriented, `evaluate_specs`;
  `skill_access.held_rank`; four French blocked reasons; `_clean_requirement`
  validating every target; `migrate_v2_17_quests.py`; check `quests.py`
  created (QA1-QA3).
- **B — accept, pin, abandon** (no schema change): `write_agenda(status=
  "paused")`; `writes/quests.py`; `quest_reads.py`; `routes/quests.py`
  (creator offers, Journée quests); the `quest_id` pin on `/plan` (QB1-QB4).
- **C — the two surfaces** (no schema change): Création « Quêtes » (an island
  created as such); Journée's « Quêtes » panel and « Cette journée avance »
  (QC1-QC3).

## Dependency graph

Strictly sequential, A -> B -> C.

- B writes A's tables through A's `_clean_requirement` and evaluates
  eligibility with A's `evaluate_specs`.
- C calls B's routes and mirrors A's vocabulary (C-07).
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/quests.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; C rebuilds `static/`.
- A creates `quests.py` because every Machine arrow of the ticket must
  resolve from `brief` status on (`pipeline_state.py`).

## RECON

Opened on `main` at `4b06dde` (merge of PR #138, `ticket/0107`), schema
v2.16. Then prototyped on a copy (branch `proto/0108`): `main` ran the full
corpus green (140/140, `WORLD_ENGINE_ENV=test`), every brief's commit ran it
green (141/141 from A on), and the three diffs replayed in order on a clean
worktree of `main` reproduce the prototype tree exactly (generated files
regenerated; the build manifest differs by its `built_at` only). Findings
tagged [M] were measured. Line numbers are `main`'s.

### R-01 — one active agenda per character, held in code only [M]
Opened: `src/world_engine/writes/goals_agendas.py:234-282` (`write_agenda`:
the guard `:263-271`, the row born `status="active"` at `:277`), `:523-583`
(`write_agenda_status`: the same guard, `:549-563`); `src/world_engine/
models/canon.py:772-792` (`Agenda`: `ck_agenda_status` allows `paused`;
`idx_agenda_owner_status` is not unique).
Finding: the rule is an explicit SELECT in the two writers; the schema
allows several active rows. `write_agenda` always creates `active`.
Consequence: a quest accepted while a day plan is active would raise. An
accepted quest is born `paused` (A1): `write_agenda` takes `status`
(`active` or `paused`), the guard applying to `active` only.

### R-02 — a planned day is an agenda of the player [M]
Opened: `goals_agendas.py:640-684` (`write_day_plan` calls `write_agenda` at
`:670`); `src/world_engine/cockpit/routes/day.py:579-597` (`_finalize_plan`;
`pass_play.agenda_id` set at `:597`).
Finding: every newly planned day creates the player's active agenda.
Consequence: a quest coexists with day plans as one open plan among them.

### R-03 — several open plans; a day selects one (TICKET-0077) [M]
Opened: `src/world_engine/day_plans.py:24-58` (`OPEN_PLAN_STATUSES =
("active", "paused")`, `open_plans`, `active_plan`, `park_active_plan`);
`routes/day.py:629-688` (`plan_day`: `select_plan` over the open plans at
`:675-679`; `None` parks the active plan and emits a new one);
`src/world_engine/cockpit/day_reconcile_apply.py:138-179` (`modify` only
accepts an identical plan), `:181-205` (`replace` parks the standing plan),
`:207-258` (`_reconcile_and_finalize`: a `paused` selection is swapped in at
`:227-235`).
Finding: a parked plan is resumed by a day that selects it; no verdict
rewrites a plan's steps; `replace` parks.
Consequence: A1 needs no change to reconciliation. The pin (O1) replaces
only the selection call; a `replace` verdict still parks a pinned quest.

### R-04 — activating an agenda promotes its first pending step [M]
Opened: `goals_agendas.py:488-520` (`_activate_lowest_pending_step_if_none_
active`), called at `:583`.
Consequence: an accepted quest born with its first step `active` (R-17's
precedent) is consistent with every later activation.

### R-05 — the requirement table's CHECKs [M]
Opened: `src/world_engine/models/config.py:124-149` (the declaring file).
Finding: `ck_agenda_step_requirement_type` lists four forms;
`ck_agenda_step_requirement_shape` has three groups (entity target, key
target, threshold); unique index on `(step_id, type, target_entity_id,
target_key)`.
Consequence: widening needs a table rebuild -- SQLite cannot alter a CHECK.

### R-06 — the evaluators and the model's parser share one tuple [M]
Opened: `src/world_engine/day_plan.py:75` (`REQUIREMENT_TYPES`), `:144-221`
(the four evaluators, `_EVALUATORS`), `:256-276` (`evaluate_requirements`),
`:414-432` (`_validate_requirement`: the model's requirement is checked
against `REQUIREMENT_TYPES`).
Finding: widening `REQUIREMENT_TYPES` alone would let the day-plan model
emit a creator form.
Consequence: `MODEL_REQUIREMENT_TYPES` (the four) for the parser.

### R-07 — `relation_gte` reads either direction, structural rows included [M]
Opened: `day_plan.py:166-189`; `src/world_engine/models/canon_knowledge.py:
23-41` (`idx_relation_oriented_social`: one social row per ORIENTED pair,
`type NOT IN ('connects_to','borde','controls')`);
`src/world_engine/relation_orientation.py:1-40` (`entity_a` feels toward
`entity_b`; `is_social`); `src/world_engine/writes/relations.py:105-118`
(`_find_perceived_relation`: `entity_a = perceiver`, `entity_b = target`,
social only -- the reader of the NPC-goal prerequisite judge).
Finding: the evaluator takes the first row of the pair in either order,
with no type filter.
Consequence: B-dir -- the row `entity_a = target`, `entity_b = character`,
`is_social`, 0 when absent: `_find_perceived_relation`'s query restated
(importing it would cycle: `writes/goals_agendas.py` imports `day_plan`).
Model-emitted day plans read it too.

### R-08 — `resource` is money [M]
Opened: `day_plan.py:191-200`; `models/canon.py:454-473` (`Ledger`: signed
`amount`, no currency column).
Finding: the evaluator sums the character's whole ledger; `target_key` is
not read.
Consequence: `resource` stays the name and means money, its key a label;
an object is never a `resource` (objects held in quantity: TICKET-0109).

### R-09 — the requirement writer [M]
Opened: `goals_agendas.py:588-637` (`_clean_requirement`: entity forms
`("relation_gte", "location_reachable")` hard-coded, key otherwise, threshold
forms `("relation_gte", "resource")`; an entity target must exist in the
world; a key target is not resolved), `:46` (imports `REQUIREMENT_TYPES`).
Consequence: its three groups come from `day_plan`; key targets are
resolved (a fact, a skill, an offer of the world); `faction_member` must
name a faction; the two model-emitted entity forms keep exactly the check
they had, so no day plan is refused for anything new.

### R-10 — the player-facing reason is fail-closed [M]
Opened: `src/world_engine/day_resolve.py:255-275` (`_BLOCKED_DETAIL_FR`,
`requirement_detail_fr` raises on an unknown type);
`tooling/verify/checks/day_narration.py:651-682` (R15: its keys equal
`REQUIREMENT_TYPES`).
Consequence: four French lines, each naming its target through
`required_label`.

### R-11 — the other readers of requirement rows filter by type [M]
Opened: `routes/day.py:274-310` (`_account_rendezvous` reads `relation_gte`
targets), `src/world_engine/day_mutations.py:145-175` (reads `knowledge`
requirements), `:225-270` (reads `knowledge` verdicts), `day_resolve.py:
384-386` (keeps `character` and `location` refs only).
Finding: each selects a named type; none fails on another.
Consequence: the new forms pass them untouched. Report only: a `has_met`
target is not named as a rendezvous.

### R-12 — encounters [M]
Opened: `src/world_engine/models/ephemeral.py:160-196` (`rencontre`: one row
per UNORDERED pair, `entity_lo_id < entity_hi_id`, unique).
Consequence: `has_met` reads the sorted pair.

### R-13 — memberships [M]
Opened: `src/world_engine/models/canon_faction.py:83-129` (`FactionMembership`:
active iff `left_at IS NULL`; `is_secret`, whose comment asks every
non-creator READER to filter it out); `src/world_engine/tick_context.py:
315-330` (an NPC's own briefing reads its secret memberships, marked).
Consequence: `faction_member` counts the character's own secret membership
-- the gate is about him, the `tick_context` self-briefing precedent.

### R-14 — ranks [M]
Opened: `models/canon.py:655-690` (`Skill`: `rank` 0..5,
`skill_definition_id` NULL on a base row); `src/world_engine/skill_access.
py:45-58` (`_base_row`, `_definition_row`); `src/world_engine/skill_ranks.
py:32` (`DEFAULT_RANK: int = 1`, Initié).
Consequence: `skill_access.held_rank` -- a base domain without a row is
`DEFAULT_RANK`, a definition without a row is not held.

### R-15 — a step change does not check its agenda's status [M]
Opened: `src/world_engine/cockpit/mutations.py:828-887`.
Finding: the step must be `active` (`:843`); `complete` activates the next
pending step or writes the agenda `completed` (`:884`); `fail` writes it
`failed`; the agenda's own status is never read.
Consequence: a quest is abandoned only when no step change of it is
`proposed`; a quest's `completed`/`failed` come from here (M1).

### R-16 — awaiting review is `status = 'proposed'` [M]
Opened: `routes/day.py:741-773` (`_guard_no_pending_agenda_step_change`:
`mutation_type == "agenda_step_change"`, `status == "proposed"`, the
payload's `step_id`).
Consequence: `abandon_refusal` restates this query (the guard raises an
HTTP error and lives in a route module).

### R-17 — a creator agenda starts with its first step active [M]
Opened: `src/world_engine/cockpit/crud/agendas.py:173-207` (`:203`).

### R-18 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40 functions, 1000
lines per module), `tooling/verify/checks/function_length.py:29` (80 lines);
`routes/day.py` is 979 lines on `main`.
Consequence: the quest routes live in their own module; the pin adds 11
lines to `routes/day.py` (990).

### R-19 — Journée never sees the agenda [M]
Opened: `tooling/verify/checks/day_mutations.py:25-34`, `:332-352` (R7: no
dict built in `routes/day.py` has an `agenda_id`/`step_id` key; `Journee.
svelte` names neither).
Consequence: quest payloads carry `quest_id`/`offer_id` only; `quests.py`
extends R7 to the new modules (QB4, QC3).

### R-20 — the player and the active world [M]
Opened: `routes/day.py:126-139` (`_resolve_player_character`: exactly one
player character, else 400); `src/world_engine/cockpit/crud/_shared.py:
57-61` (`_world_id`).

### R-21 — a Création island created as such [M]
Opened: `tooling/verify/checks/creation_island.py:1-140` (rules 1-13:
registry `origin: 'new'` with `containerId`, `component`, `createdBy`;
rule 5 tabs <-> registry; rule 9 `loader: null`; rule 11 a routed
`primaryAction` needs `export function primaryAction` in the component;
rule 12 `COMPONENTS`); `frontend/src/creation/registry.js:544-553`
(`subjectWorklist`, `origin: 'new'`); `frontend/src/creation/tabs.js:343-
351` (`subjects`); `frontend/src/creation/mount.js:30-46`;
`frontend/src/creation/Creation.svelte:252`;
`tooling/verify/checks/page_contract.py:46-49` (`TAB_KEYS`);
`tooling/verify/checks/creation_container_sizing.py:17-23` with
`frontend/public/creation.css:311` (a single-container tab needs
`#<id> { flex: 1; min-height: 0 }`).

### R-22 — the world cascade names every world-scoped table [M]
Opened: `src/world_engine/writes/worlds.py:13-25`, `:66-78`
(`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/checks/world_cascade.py:
1-35` (W1 coverage, W3 one `_FIXTURE` row per cascaded table).

### R-23 — canon writes, and the full-replace deletes [M]
Opened: `tooling/verify/canon_write_policy.txt` (`[CANON_TABLES]`;
`[ALLOWED_SITES]` is function-scoped, not interprocedural);
`tooling/verify/checks/single_canon_write.py:46-90` (the hard-delete law
and its full-replace list); `src/world_engine/writes/config.py:76-106`
(`write_npc_prices`: `DELETE FROM` scoped to its parent, then insert).

### R-24 — the migration's shape [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py:126-180` (`_rebuild` and
`_create_from_model` on a raw connection, both PRAGMAs before `BEGIN`);
`scripts/migrate_v1_95_parked_plans.py:60-100` (why raw);
`scripts/migrate_v2_16_npc_skills.py:68` and `:148-170` (the foreign-key
post-check judges only the tables the migration writes, AMENDMENT-0107-01);
`src/world_engine/schema_version.py:15`; `tooling/verify/checks/
schema_partition.py` (the changelog's newest entry is the header version).
`agenda_step_requirement`'s v2.16 DDL was dumped from `main` (embedded in
`quests.py`).

### R-25 — JSON columns and decision headers [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-56` (every JSON column
named in `JSON_COLUMN_ALLOWLIST`); `tooling/verify/checks/decisions_index.
py:15-17` (strict header: the brief letter is lower case).

### R-26 — the frontend build [M]
Opened: `frontend/package.json` (`vite build` then the manifest); a rebuild
of unchanged sources changes only `.build-manifest.json`'s `built_at`
(`frontend_build_fresh.py` passes); `frontend/public/` is copied into
`static/`.

### R-27 — `api()` [M]
Opened: `frontend/src/creation/sheetRequest.svelte.js:30-35` (throws
`Error(detail)` on a non-2xx).

### R-28 — objects [M] (for the cut)
Opened: `models/canon.py:545-564` (`item`: an entity, one `owner_id`, no
quantity), `:521-540` (`artifact`: no reader or writer but the world
cascade, `writes/worlds.py:48`).
Consequence: nothing in this lot; `item_holding` is TICKET-0109.

## Contract sheet

### C-01 — the requirement vocabulary (family contract)
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B, BRIEF-0108-C
Written before its members; re-read after the last (`quest_completed`).

In `src/world_engine/day_plan.py`, literal tuples, in this order:

```python
REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable",
                     "has_met", "faction_member", "skill_rank_gte", "quest_completed")
MODEL_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
ENTITY_TARGET_TYPES = ("relation_gte", "location_reachable", "has_met", "faction_member")
KEY_TARGET_TYPES = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
THRESHOLD_TYPES = ("relation_gte", "resource", "skill_rank_gte")
```

The two CHECK texts, carried byte for byte by `agenda_step_requirement`
(`ck_agenda_step_requirement_type`, `_shape`) and `quest_offer_requirement`
(`ck_quest_offer_requirement_type`, `_shape`):

```
type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')
(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
```

Members (every row has all six columns):

| form | target | threshold | met iff | blocked reason (French) | `_clean_requirement` refuses | model |
|---|---|---|---|---|---|---|
| `knowledge` | key: fact id | -- | the character holds a row on the fact | unchanged | a fact not of the world | yes |
| `relation_gte` | entity | >= 1 | the target's social row toward the character >= threshold (0 if none) | unchanged | an entity not of the world | yes |
| `resource` | key: a label | >= 1 | the character's ledger balance >= threshold | unchanged | -- (label) | yes |
| `location_reachable` | entity | -- | the target is in the character's `connects_to` component | unchanged | an entity not of the world | yes |
| `has_met` | entity | -- | a `rencontre` row of the sorted pair | « il n'a encore jamais rencontré {name} » | an entity not of the world | no |
| `faction_member` | entity: a faction | -- | an active membership, secret included | « il n'appartient pas à {name} » | not a faction of the world | no |
| `skill_rank_gte` | key: base domain or definition id | 1-5 | `held_rank` >= threshold | « sa maîtrise de « {label} » ne suffit pas encore » | an unknown skill; threshold 0 or > 5 | no |
| `quest_completed` | key: quest offer id | -- | a quest of the character from that offer whose agenda is `completed` | « il doit d'abord mener à bien « {title} » » | an offer not of the world | no |

`Verdict.required_label` carries the target's name for `relation_gte` and
the four new forms.

### C-02 — evaluation
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B
Signature: `day_plan.evaluate_specs(requirements: tuple[RequirementSpec, ...],
character: Character, db: Session) -> list[Verdict]`; `evaluate_requirements
(step, character, db)` returns `evaluate_specs(step.requirements, character,
db)`. `skill_access.held_rank(db, character_id, skill_key) -> Optional[int]`.
Return shape: one `Verdict(type, met, current, required, reason,
required_label)` per requirement, in order.
Error and empty cases: an unknown type raises `ValueError`; an empty tuple
returns `[]`; `_day_reachable_ids` runs at most once, only for a
`location_reachable`.

### C-03 — the writers
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C (through C-04)

- `write_agenda(db, *, world_id, owner_entity_id, title, mutation_id=None,
  status="active") -> Agenda`: `status` is `active` or `paused`, else
  `ValueError`; the one-active guard applies to `active` only.
- `writes.quests.write_quest_offer(db, *, world_id, offer: Optional[QuestOffer],
  giver_entity_id, title, summary, repeatable, status, eligibility:
  list[RequirementSpec], steps: list[PlanStep]) -> QuestOffer`. Refuses,
  before any write, with `ValueError`: a blank title; a status outside
  `QUEST_OFFER_STATUSES`; a giver that is not an active character or
  faction of the world (`QUEST_GIVER_TYPES`); a requirement refused by
  `_clean_requirement`; 0 or more than `MAX_PLAN_STEPS` steps; a blank
  objective; a cost outside 1-4; a domain outside `BASE_SKILL_DOMAINS`; on a
  save, a `quest_completed` on the offer itself. A save snapshots the offer
  (`giver_entity_id`, `title`, `summary`, `repeatable`, `status`,
  `updated_at`) into `change_history`, then `DELETE FROM` its requirements
  and steps and writes the submitted set.
- `acceptance_refusal(db, offer, character) -> Optional[str]` (French):
  case table (b-1).
- `accept_quest(db, *, offer, character) -> Quest`: `ValueError` with the
  refusal, before any write. Writes one agenda (`paused`, the offer's
  title), its steps in order (the first `active`, the others `pending`, with
  `cost` and `domain`), each step's requirements (through
  `_clean_requirement`), one `quest` row.
- `abandon_refusal(db, quest) -> Optional[str]` (French): case table (b-2).
- `abandon_quest(db, *, quest) -> Agenda`: `ValueError` with the refusal;
  the agenda to `abandoned` through `write_agenda_status`.
- `offer_requirements(db, offer_id, step_id) -> tuple[RequirementSpec, ...]`:
  `step_id` None reads the eligibility.
- `QUEST_GIVER_TYPES = ("character", "faction")`, `OPEN_QUEST_STATUSES =
  ("active", "paused")`.

None commits.

### C-04 — reads and routes
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C

`src/world_engine/quest_reads.py` (reads only):
- `QUEST_STATE_LABELS = {"active": "en cours", "paused": "en cours",
  "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"}`.
- `offer_dict(offer, db)`: `id, giver_entity_id, giver_name, title, summary,
  repeatable, status, eligibility: [req], steps: [{objective, cost, domain,
  requirements: [req]}]`, `req = {type, target_entity_id, target_key,
  threshold}`.
- `editor_choices(world_id, db)`: `givers, characters, locations, factions`
  (`{id, name}`), `facts` (`{id, text}`), `skills` (`{key, label}`: the four
  base domains, then the definitions), `offers` (`{id, title}`),
  `giver_types`.
- `available_offers(character, db)`: the open offers whose
  `acceptance_refusal` is None.
- `journee_payload(character, db)`: `{offers: [{offer_id, title, summary,
  giver_name, steps: [objective]}], quests: [{quest_id, offer_id, title,
  giver_name, summary, state, open, steps: [{order, objective, status,
  blocked: [French reason]}]}]}` -- `blocked` only for the active step. No
  `agenda_id` or `step_id` at any depth.
- `pinned_plan(quest_id, character, db) -> Agenda` (C-05).

`src/world_engine/cockpit/routes/quests.py`:

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/quest-offers` | -- | 200 `[offer_dict]` | 400 no active world |
| `GET /api/quest-offers/choices` | -- | 200 `editor_choices` | 400 |
| `POST /api/quest-offers` | `OfferBody` | 201 `offer_dict` | 422 the writer's message |
| `PUT /api/quest-offers/{id}` | `OfferBody` | 200 `offer_dict` | 404 unknown, 422 |
| `GET /api/quests` | -- | 200 `journee_payload` | 400 not one player |
| `POST /api/quests/accept` | `{offer_id}` | 201 `journee_payload` | 404 unknown offer, 409 refusal |
| `POST /api/quests/{quest_id}/abandon` | -- | 200 `journee_payload` | 404 not his quest, 409 refusal |

`OfferBody = {giver_entity_id, title, summary?, repeatable=false,
status="open", eligibility: [req], steps: [{objective, cost, domain?,
requirements: [req]}]}`.

### C-05 — the pin (O1)
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C
`routes/day.py`: `class PlanDayBody(BaseModel): quest_id: Optional[str] =
None`; `plan_day(batch_id, body: Optional[PlanDayBody] = None, db)`. A
non-empty `body.quest_id` -> `quest_reads.pinned_plan(...)` is the selected
plan and `select_plan` is not called; otherwise unchanged. `pinned_plan`
raises `LookupError` (-> 404) when the quest is not the character's,
`ValueError` (-> 409) when its agenda is not `active`/`paused`. The
selected plan then goes through `_reconcile_and_finalize` unchanged.

### C-06 — schema v2.17
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B
`src/world_engine/models/quests.py`, canon:
- `quest_offer(id, world_id, giver_entity_id -> entity, title, summary,
  repeatable BOOLEAN DEFAULT 0, status DEFAULT 'open' CHECK IN ('open',
  'closed'), created_at, updated_at, change_history JSON)`, index on
  `world_id`; `QUEST_OFFER_STATUSES = ("open", "closed")`.
- `quest_offer_step(id, world_id, offer_id -> quest_offer, step_order,
  objective, cost CHECK BETWEEN 1 AND 4, domain)`, unique `(offer_id,
  step_order)`.
- `quest_offer_requirement(id, world_id, offer_id -> quest_offer, step_id ->
  quest_offer_step NULL, type, target_entity_id -> entity, target_key,
  threshold)`, C-01's two CHECKs, index on `offer_id`.
- `quest(id, world_id, offer_id -> quest_offer, character_id -> entity,
  agenda_id -> agenda, accepted_at)`, unique `agenda_id`, indexes on
  `character_id`, `offer_id`.
- `agenda_step_requirement`: C-01's two CHECKs.

### C-07 — the surfaces
Produced by: BRIEF-0108-C   Consumed by: nothing in this lot
- `frontend/src/creation/questRequirements.js`: `REQUIREMENT_FORMS[form] =
  { label, list, column: 'entity'|'key', threshold: bool }`, the keys of
  C-01 in its order, `list` one of `facts, characters, money, locations,
  factions, skills, offers`; `MONEY_KEY = 'monnaie'`.
- Création: tab key `quetes`, label « Quêtes », container `creation-quetes`,
  island key `questOffers` (`QuestOffers.svelte`, `origin: 'new'`),
  primary action « + Nouvelle quête ».
- Journée: `QuestPanel.svelte`; `quests.svelte.js`'s `questState = {offers,
  quests, loading, loadError, busy, actionError, pin}`; `planDay(id,
  questId)` sends `{quest_id}` when `questId` is set.

## Gate output

### (a) Property trace

| property asserted by the lot | finding | file opened (declaring) |
|---|---|---|
| one-active guard in `write_agenda`, row born `active` | R-01 | `writes/goals_agendas.py` |
| the same guard in `write_agenda_status` | R-01 | `writes/goals_agendas.py` |
| `agenda.status` allows `paused` | R-01 | `models/canon.py` |
| a planned day creates the player's agenda | R-02 | `writes/goals_agendas.py`, `routes/day.py` |
| open plans are `active`/`paused`; a day selects one | R-03 | `day_plans.py`, `routes/day.py` |
| `modify` never rewrites steps; `replace` parks | R-03 | `cockpit/day_reconcile_apply.py` |
| activation promotes the first pending step | R-04 | `writes/goals_agendas.py` |
| the requirement CHECKs and unique index | R-05 | `models/config.py` |
| the model's parser reads `REQUIREMENT_TYPES` | R-06 | `day_plan.py` |
| `relation_gte` reads either direction, no type filter | R-07 | `day_plan.py` |
| one social row per oriented pair | R-07 | `models/canon_knowledge.py` |
| `entity_a` feels toward `entity_b`; `is_social` | R-07 | `relation_orientation.py` |
| `_find_perceived_relation`'s query | R-07 | `writes/relations.py` |
| the ledger has no currency column | R-08 | `models/canon.py` |
| `_clean_requirement`'s groups and checks | R-09 | `writes/goals_agendas.py` |
| `requirement_detail_fr` is fail-closed | R-10 | `day_resolve.py` |
| R15 compares `_BLOCKED_DETAIL_FR` keys to `REQUIREMENT_TYPES` | R-10 | `checks/day_narration.py` |
| the other requirement readers filter by type | R-11 | `routes/day.py`, `day_mutations.py`, `day_resolve.py` |
| `rencontre`: unordered pair, lo < hi, unique | R-12 | `models/ephemeral.py` |
| membership active iff `left_at IS NULL`; `is_secret` | R-13 | `models/canon_faction.py` |
| an NPC's own briefing reads its secret memberships | R-13 | `tick_context.py` |
| `skill.rank` 0..5; base row has no definition | R-14 | `models/canon.py` |
| `_base_row`, `_definition_row` | R-14 | `skill_access.py` |
| `DEFAULT_RANK = 1` | R-14 | `skill_ranks.py` |
| a step change ignores the agenda's status; completes/fails it | R-15 | `cockpit/mutations.py` |
| awaiting review is `status = 'proposed'`, payload `step_id` | R-16 | `routes/day.py` |
| a creator agenda's first step is `active` | R-17 | `cockpit/crud/agendas.py` |
| module caps 40/1000, function cap 80 | R-18 | `checks/module_budget.py`, `checks/function_length.py` |
| R7: no `agenda_id`/`step_id` in day dicts or `Journee.svelte` | R-19 | `checks/day_mutations.py` |
| one player per world; the active world | R-20 | `routes/day.py`, `crud/_shared.py` |
| island rules 1-13 | R-21 | `checks/creation_island.py` |
| `TAB_KEYS` | R-21 | `checks/page_contract.py` |
| a single-container tab needs `flex: 1; min-height: 0` | R-21 | `checks/creation_container_sizing.py` |
| the cascade lists and the fixture rule | R-22 | `writes/worlds.py`, `checks/world_cascade.py` |
| allowed sites are function-scoped | R-23 | `canon_write_policy.txt`, `checks/single_canon_write.py` |
| the full-replace delete shape | R-23 | `writes/config.py` |
| the raw-connection rebuild | R-24 | `scripts/migrate_v2_15_skill_ranks.py` |
| the scoped FK post-check | R-24 | `scripts/migrate_v2_16_npc_skills.py` |
| the code's schema version | R-24 | `schema_version.py` |
| the JSON column allowlist | R-25 | `checks/json_ui_boundary.py` |
| the strict decision header | R-25 | `checks/decisions_index.py` |
| the build copies `public/`, only `built_at` moves | R-26 | `frontend/package.json` (+ a rebuild) |
| `api()` throws `Error(detail)` | R-27 | `creation/sheetRequest.svelte.js` |

No instruction in the lot gestures at a convention: each brief names its
precedent's file and lines (R-17, R-21, R-23, R-24).

### (b) Case tables

**b-1 — `acceptance_refusal(offer, character)`**, checked in this order:

| offer status | quests taken from it by the character | repeatable | eligibility | result |
|---|---|---|---|---|
| `closed` | any | any | any | « cette quête n'est plus proposée » |
| `open` | at least one | no | any | « quête déjà acceptée » |
| `open` | one still `active`/`paused` | yes | any | « quête déjà en cours » |
| `open` | none open (all over) | yes | unmet | the unmet reasons |
| `open` | none | any | unmet | the unmet reasons |
| `open` | none, or all over and repeatable | -- | met | None (accepted) |

Every row is reachable. QB2 exercises rows 1, 2, 3, 5 and 6, QB3 row 2
again once the quest is over; row 4 (a repeatable offer, its quests over,
its eligibility no longer met) is reached by the same code path as row 5
and is not exercised separately.

**b-2 — `abandon_refusal(quest)`**, in order:

| agenda | a day `resolving` on it | a step change `proposed` | result |
|---|---|---|---|
| missing, `completed`, `failed`, `abandoned` | -- | -- | « cette quête est terminée » |
| `active`/`paused` | yes | -- | « une journée est en cours de résolution sur cette quête » |
| `active`/`paused` | no | yes | « une étape de cette quête attend la revue » |
| `active`/`paused` | no | no | None (abandoned) |

**b-3 — `plan_day`'s selection**:

| body | quest | selected plan | then |
|---|---|---|---|
| none, or `quest_id` empty | -- | `select_plan(...)` (unchanged) | unchanged |
| `quest_id` | the player's, agenda `active` | that agenda | continue / modify / replace |
| `quest_id` | the player's, agenda `paused` | that agenda | resume (swap) / replace (parks it) |
| `quest_id` | the player's, agenda over | -- | 409 |
| `quest_id` | unknown or another character's | -- | 404 |

**b-4 — `write_agenda(status)`**: `active` -> guard, row `active`;
`paused` -> no guard, row `paused`; anything else -> `ValueError` before any
read. Callers on `main` pass none (E1): all keep `active`.

**b-5 — a quest's state (M1)**: `active`, `paused` -> « en cours », open;
`completed` -> « accomplie »; `failed` -> « échouée »; `abandoned` ->
« abandonnée »; `ck_agenda_status` admits no other value.

**b-6 — the eight forms**: C-01's member table, each row exercised by QA3
(met and unmet) and QC1 (mirror).

### (c) Enumerations

E1 -- callers of `write_agenda(` on `main` (none passes `status`):
```
src/world_engine/writes/goals_agendas.py:670:    agenda = write_agenda(db, world_id=world_id, owner_entity_id=owner_entity_id, title=title)
src/world_engine/cockpit/mutations.py:909:        agenda = write_agenda(
src/world_engine/cockpit/crud/agendas.py:187:        agenda = write_agenda(
```

E2 -- readers of the vocabulary on `main`:
```
src/world_engine/day_resolve.py:260:_BLOCKED_DETAIL_FR: dict[str, str] = {
src/world_engine/day_resolve.py:272:    template = _BLOCKED_DETAIL_FR.get(verdict.type)
src/world_engine/writes/goals_agendas.py:46:from ..day_plan import REQUIREMENT_TYPES, PlanStep, RequirementSpec
src/world_engine/writes/goals_agendas.py:595:    if req.type not in REQUIREMENT_TYPES:
src/world_engine/cockpit/routes/day.py:558:        EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step, character, db)))
src/world_engine/day_plan.py:75:REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")
src/world_engine/day_plan.py:218:_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
src/world_engine/day_plan.py:256:def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
src/world_engine/day_plan.py:271:        evaluator = _EVALUATORS.get(req.type)
src/world_engine/day_plan.py:299:    verdicts = tuple(evaluate_requirements(plan_step, character, db))
src/world_engine/day_plan.py:418:    if req_type not in REQUIREMENT_TYPES:
tooling/verify/checks/day_plan.py:190:EXPECTED_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
tooling/verify/checks/day_narration.py:676:    from world_engine.day_plan import REQUIREMENT_TYPES  # noqa: E402
tooling/verify/checks/day_feasibility.py:191:_FORBIDDEN_REQUIREMENT_NAMES = {"REQUIREMENT_TYPES", "_EVALUATORS", "evaluate_requirements"}
```

E3 -- writers of `agenda_step_requirement` rows on `main`:
```
src/world_engine/writes/goals_agendas.py:682:            db.add(AgendaStepRequirement(world_id=world_id, step_id=agenda_step.id, **clean))
```

E4 -- readers of requirement rows or verdicts by type on `main` (R-11):
```
src/world_engine/cockpit/routes/day.py:303:            AgendaStepRequirement.type == "relation_gte",
src/world_engine/day_mutations.py:158:            AgendaStepRequirement.type == "knowledge",
src/world_engine/day_mutations.py:241:        if v.type != "knowledge" or v.met:
src/world_engine/day_resolve.py:272:    template = _BLOCKED_DETAIL_FR.get(verdict.type)
src/world_engine/day_plan.py:266:    needs_reachable = any(r.type == "location_reachable" for r in step.requirements)
src/world_engine/day_plan.py:380:            if req.type == "knowledge" and req.target_key not in anchorable:
src/world_engine/day_plan.py:493:            if req.type == "knowledge" else req
```

E5 -- checks that enumerate Création tabs:
```
tooling/verify/checks/creation_container_sizing.py
tooling/verify/checks/creation_island.py
tooling/verify/checks/creation_return_nav.py
tooling/verify/checks/observation_surface.py
tooling/verify/checks/page_contract.py
```

E6 -- callers of `planDay(` on `main`:
```
frontend/src/journee/Journee.svelte:87:            <button disabled={journeeState.planning} onclick={() => planDay(day.id)}>
frontend/src/journee/journee.svelte.js:72:export async function planDay(id) {
```

### (d) Family contracts
C-01 was written before its eight members and re-read after
`quest_completed`: each member row carries its target column, threshold,
meaning, French reason, refusal and model flag; the three groups partition
the eight forms (QA1). Tick.

### (e) Gates and the modules that satisfy them

Proposed (`tooling/verify/checks/quests.py`):
- QA1 <- `day_plan.py` (the five tuples, `_validate_requirement`),
  `models/config.py` and `models/quests.py` (identical CHECKs).
- QA2 <- `scripts/migrate_v2_17_quests.py`.
- QA3 <- `day_plan.py` (evaluators), `skill_access.held_rank`,
  `day_resolve.py`, `writes/goals_agendas.py::_clean_requirement`.
- QB1-QB3 <- `writes/quests.py`, `writes/goals_agendas.py::write_agenda`,
  `quest_reads.py`.
- QB4 <- `quest_reads.py`, `cockpit/routes/quests.py`, `cockpit/routes/
  day.py::plan_day`.
- QC1 <- `frontend/src/creation/questRequirements.js`.
- QC2 <- `tabs.js`, `QuestOffers.svelte`, `questOffers.svelte.js`.
- QC3 <- `QuestPanel.svelte`, `quests.svelte.js`, `Journee.svelte`,
  `journee.svelte.js`.
None needs judgment; none teaches an exception.

Passed (existing): `day_plan.py` R2-R3 <- its `EXPECTED_REQUIREMENT_TYPES`
and pairs, updated in A; `day_narration.py` R15 <- `_BLOCKED_DETAIL_FR`;
`single_canon_write.py` <- `[CANON_TABLES]` (A) and the two sites (B);
`world_cascade.py` <- `_DIRECT_WORLD_SCOPED_DELETES` and `_FIXTURE` (A);
`json_ui_boundary.py` <- `QuestOffer.change_history` allow-listed (A);
`schema_version_agreement.py`, `schema_partition.py` <- the constant, the
doc header, the changelog entry (A); `decisions_index.py` <- lower-case
headers (A-C); `module_budget.py` <- `routes/day.py` at 990 lines (B);
`function_length.py` <- every new function under 80 lines; `day_mutations.
py` R7 <- `Journee.svelte` names no agenda id (C); `creation_island.py`,
`page_contract.py`, `creation_container_sizing.py` <- the registry entry,
`TAB_KEYS`, the `#creation-quetes` rule (C); `frontend_build_fresh.py` <-
the rebuild (C).

## Amendments

(none)
