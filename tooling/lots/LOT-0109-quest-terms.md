# LOT — TICKET-0109 "Quest costs and rewards, objects held in quantity, the indicative unit, « déclarer accomplie »"

## Objective and cut

An item becomes a kind held in quantity (A1): `item_holding` says who holds
how many -- a character, a faction, or a place; `equipped` disappears. A
quest offer gains terms (B1): costs and rewards in five currencies -- money,
items, relation, a fact, a skill -- copied into the quest when it is
accepted. Each term is weighed in an indicative unit whose rates a world
sets (C1/E1); the editor shows whether the reward lies in the world's band.
« Déclarer accomplie » (D1) shows the measured context of a quest (G1) and,
when every cost can be paid, applies every cost then every reward at once,
completes the agenda and marks the quest settled. A reward is always given
(C-src1); a skill reward gives 10 % of the points its rank needs, the
surplus not carried (C-skill1); teaching needs a Maître (C-teach1).

The lot stops before: debts and services (J2 -- TICKET-0110), rank trials
(K1 -- TICKET-0111), a « déclarer échouée » button (D-fail2), forcing an
unpayable settlement (D2), artifacts, quests proposed by the model or the
Lore tool, any change to the day-chain prompts, and any change to
`legacy.html`.

## Briefs in this lot

- **A — schema v2.18, objects held in quantity**: `item` a kind (`value`
  added; `owner_id`, `location_id`, `equipped` dropped); `item_holding` and
  `writes.write_holding`; `holdings.py`; the inventory line, the possession
  check, the sheets' « Objets » panel, the zone promotion on holdings;
  `item_update` retired; the term tables, `quest_economy` and
  `quest.settled_at` laid for B-C; `migrate_v2_18_quest_terms.py`; check
  `quest_rewards.py` created (RA1-RA3).
- **B — terms and the indicative unit** (no schema change):
  `writes/quest_terms.py`; `write_quest_offer(terms=)`, the copy at
  acceptance; `quest_value.py`; `quest_wording.py`;
  `skill_access.skill_label`; the value preview and economy routes (RB1-RB3).
- **C — « déclarer accomplie »** (no schema change):
  `writes/quest_settlement.py`; `quest_settlement_view.py`; the settlement
  routes; the Journée payload's `terms`, `settled`, `settleable` (RC1-RC3).
- **D — the surfaces** (no schema change): terms and the world's rates in
  Création › Quêtes; terms, the recap and « Déclarer accomplie » in Journée
  (RD1-RD3).

## Dependency graph

Strictly sequential, A -> B -> C -> D.

- B writes A's term tables and reads A's `item.value`.
- C reads B's `quest_terms`, applies through A's `write_holding`, and words
  through B's `quest_wording`.
- D calls B's and C's routes and mirrors B's currencies (C-08).
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/quest_rewards.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A and D rebuild `static/`.
- A creates `quest_rewards.py` because every Machine arrow of the ticket
  must resolve from `brief` status on (`pipeline_state.py`).

## RECON

Opened on `main` at `1f80b9f` (merge of PR #139, `ticket/0108`), schema
v2.17. Then prototyped on a copy (branch `proto/0109`): `main` ran the full
corpus green (141/141, `WORLD_ENGINE_ENV=test`), every brief's commit ran
it green (142/142 from A on), the four diffs replayed in order on a clean
worktree of `main` reproduce the prototype tree exactly (generated files
regenerated; the build manifest differs by its `built_at` only), and the
corpus ran green on that replayed tree. Findings tagged [M] were measured.
Line numbers are `main`'s.

### R-01 — an item is one entity with one owner [M]
Opened: `src/world_engine/models/canon.py:540-564` (`Item`: `owner_id`,
`location_id`, `equipped`, `condition`; `ck_item_equipped_owner`; indexes on
owner and location).
Finding: possession and place are columns of the object itself: ten furs
would be ten entities.
Consequence: A1 -- `item` a kind, `item_holding` (holder, quantity).

### R-02 — the readers of possession and place [M]
Opened: `src/world_engine/scene_format.py:83-110` (the MJ's inventory line
and the interpretation list, both `Item.owner_id`);
`src/world_engine/cockpit/play_stream.py:216-227` (`_find_player_item`: the
binary possession check, by exact `Entity.name`);
`src/world_engine/cockpit/play.py:345-356` (its caller's docstring);
`src/world_engine/cockpit/crud/entities.py:195-202` (registry fields
`owner_id`, `location_id`, `equipped`, `condition`), `:345-361`
(`_PLACEMENT_FIELDS`: an item's `location_id` refused in a zone), `:380-384`
(the equip guard), `:903-925` (`GET /entities/{id}/items`).
Consequence: every reader moves to `holdings.py`; the interpretation list
keeps names only (the model answers a name, the check matches it exactly);
the registry keeps `condition` and gains `value`.

### R-03 — `item_update` has no producer [M]
Opened: `src/world_engine/cockpit/mutations.py:477-498` (the equip toggle),
`src/world_engine/cockpit/routes/mutations.py:375-390` (« dormant since
BRIEF-08/D2a.1 — no live code path produces it ») and `:460`;
`tooling/verify/canon_write_policy.txt:87`.
Consequence: retired with `equipped` (Nia: « cela ne sert à rien »).

### R-04 — no item lies in a zone [M]
Opened: `CLAUDE.md:226-231`; `src/world_engine/zone_rules.py:76-84`
(`require_visitable`); `src/world_engine/writes/zone_promotion.py:86-91`
(`_items`: items at the parent), `:166-173` (moved by setting
`location_id`); `tooling/verify/checks/zone_placement.py:1-40`, `:180-183`
(« fiche, item »); `tooling/verify/checks/zone_promotion.py:125-131`,
`:221`.
Consequence: `write_holding` refuses a zone that RECEIVES; taking out of a
place that just became a zone is allowed -- the promotion moves a place's
holdings to its first child through it.

### R-05 — scripts that read items through today's models [M]
Opened: `scripts/migrate_v2_12_zone_borde.py:135-160` (its report reads
`Item.location_id` through the model; `tooling/verify/checks/
zone_migration.py` runs it on a database built from today's models);
`scripts/seed_pilot.py:3381-3399` (`Item(owner_id=..., equipped=True)`).
Consequence: the v2.12 report reads the column in raw SQL when it exists;
the seed gives the dagger as a holding.

### R-06 — a number field [M]
Opened: `src/world_engine/cockpit/crud/_shared.py:80-110` (`kind:
"number"`, `default`, `min`/`max` clamped).

### R-07 — tables a world owns, and JSON columns [M]
Opened: `src/world_engine/writes/worlds.py:66-78`;
`tooling/verify/checks/world_cascade.py:1-35`, `:60-200`;
`tooling/verify/checks/json_ui_boundary.py:43-58`.
Consequence: the four new tables named in the cascade and its fixture;
`ItemHolding.change_history` allow-listed.

### R-08 — money [M]
Opened: `src/world_engine/writes/characters.py:213-247`
(`write_ledger_entry`: INSERT only, no balance guard, `amount != 0`);
`src/world_engine/ledger.py:18-23` (`get_balance`);
`world-engine-schema.md:863` (`source_type` vocabulary documented, not
CHECKed); `src/world_engine/cockpit/crud/ledger.py:86` (creator types).
Consequence: a money term is two ledger lines, `source_type` `quest`; a
counterparty may go below 0 (C-src1).

### R-09 — relation [M]
Opened: `src/world_engine/writes/relations.py:267-288`
(`_build_relation_delta`: a social type finds the perceiver's own row,
`_find_perceived_relation`; a missing row is created at `50 + value`;
clamped 1-100), `:322-395` (`write_relation`).
Consequence: a relation term moves what the counterparty feels toward the
character (B-dir of 0108), type `other` on a new row.

### R-10 — fact [M]
Opened: `src/world_engine/writes/knowledge.py:65-67` (`KNOWLEDGE_LEVELS`),
`:180-238` (`_build_knowledge_update`: a create on a `fact_id` attaches to
the fact; `content` may be None); `src/world_engine/models/
canon_knowledge.py:216-221` (`content` nullable);
`src/world_engine/fact_refs.py:57-67` (`find_held` on a `fact_id`).
Consequence: a fact term writes a row only when the receiver holds none --
a level never falls.

### R-11 — skills [M]
Opened: `src/world_engine/writes/characters.py:105-150`
(`write_skill_row`: refuses a row already held), `:153-210`
(`write_skill_progress`: at the threshold the rank rises and `xp` restarts
at 0 -- `:187`, the surplus is not carried; at `MAX_RANK` points still
accumulate); `src/world_engine/skill_ranks.py:30` (`MAX_RANK = 5`), `:39`
(`DEFAULT_POINTS_TO_NEXT = (5, 10, 20, 40, 80)`), `:108-111`;
`src/world_engine/skill_access.py:82-92` (`held_rank`);
`src/world_engine/cockpit/crud/skills.py:227-258` (teaching from a Maître);
`src/world_engine/day_plan.py:296-300` (`_skill_label`, private).
Consequence: C-skill1 is `ceil(10 % of points_to_next)`, at least 1, through
`write_skill_progress` (no carry by construction); nothing at Maître;
`skill_label` moves to `skill_access` for a second reader.

### R-12 — what completes a quest today [M]
Opened: `src/world_engine/cockpit/mutations.py:828-887` (the last step's
change approved writes the agenda `completed` at `:884`; nothing else).
Finding: no column records that a quest's terms were applied.
Consequence: `quest.settled_at`; D1 completes the agenda when it is not.

### R-13 — the 0108 writers and views [M]
Opened: `src/world_engine/writes/quests.py:88-139` (`write_quest_offer`,
full-replace `:118-120`), `:172-198` (`accept_quest`);
`src/world_engine/quest_reads.py:57-71` (`offer_dict`), `:85-104`
(`editor_choices`), `:115-127` (`_steps_view`), `:129-147`
(`player_quests`), `:149-158` (`journee_payload`);
`src/world_engine/cockpit/routes/quests.py:52-60` (`OfferBody`), `:75`
(the one caller of `write_quest_offer` in `src/`).

### R-14 — the days that advanced a quest [M]
Opened: `src/world_engine/models/pipeline.py:74-80` (`pass_play.agenda_id`,
written once at plan time), `:160-172` (`day_rewrite`);
`src/world_engine/writes/pipeline.py:128-150` (`read_latest_resolution`);
`src/world_engine/day_resolve.py:444-464` (`fact_sheet_dict`: steps with
`objective` and `band`).
Consequence: G1's days are the pass_plays whose `agenda_id` is the quest's.

### R-15 — awaiting review [M]
Opened: `src/world_engine/cockpit/routes/day.py:741-773`
(`agenda_step_change`, `status == "proposed"`, the payload's `step_id`).

### R-16 — one config row per world [M]
Opened: `src/world_engine/models/config.py:26-58`
(`ConversationWindowConfig`: unique per world, absence reads defaults, the
reader never writes).
Consequence: `quest_economy`, same shape.

### R-17 — the migration's shape [M]
Opened: `scripts/migrate_v2_17_quests.py` (env guard, refusal, raw-
connection rebuild, tables from models, FK post-check scoped to the tables
it writes, `schema_meta` convergence); `src/world_engine/schema_version.py:
15`. `item` and `quest` v2.17 DDL dumped from `main` (embedded in
`quest_rewards.py`).

### R-18 — the surfaces [M]
Opened: `frontend/src/creation/ItemsPanel.svelte:1-40` (read-only);
`frontend/src/creation/Sheet.svelte:818-825` (the panel on a character
only); `frontend/src/creation/sheetRequest.svelte.js:30-35` (`api()`
throws `Error(detail)`); `frontend/src/creation/QuestOffers.svelte:121`,
`questOffers.svelte.js:62-73`; `frontend/src/journee/QuestPanel.svelte:
45-66`, `quests.svelte.js:58-64`;
`tooling/verify/checks/creation_island.py` (unchanged: no new island).

### R-19 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40/1000 per `src/`
module), `tooling/verify/checks/function_length.py:29` (80).
Consequence: four new modules (`holdings.py`, `writes/items.py`,
`writes/quest_terms.py`, `writes/quest_settlement.py`) and three reads
(`quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`); none
over budget.

## Contract sheet

### C-01 — schema v2.18
Produced by: BRIEF-0109-A   Consumed by: B, C, D
- `item(id -> entity, condition DEFAULT 'intact', value INTEGER NOT NULL
  DEFAULT 1 CHECK (value >= 0))`.
- `item_holding(id, world_id, item_id -> item, holder_entity_id -> entity,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0), updated_at,
  change_history JSON)`, unique `(item_id, holder_entity_id)`, index on
  `holder_entity_id`.
- `quest_offer_term(id, world_id, offer_id -> quest_offer, term_order,
  direction, currency, counterparty_entity_id -> entity, item_id -> item,
  fact_id -> fact, skill_key, amount, level)` and `quest_term` (same,
  `quest_id -> quest`), three CHECKs each, byte for byte:
  ```
  direction IN ('cost','reward')
  currency IN ('money','item','relation','fact','skill')
  (currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)
  ```
- `quest_economy(id, world_id unique, rate_money, rate_relation, rate_fact,
  rate_skill, band_low_pct, band_high_pct -- each NULL or >= 0, updated_at)`.
- `quest.settled_at DATETIME NULL`.

### C-02 — holdings
Produced by: BRIEF-0109-A   Consumed by: C
- `writes.write_holding(db, *, world_id, item_id, holder_entity_id,
  quantity=None, delta=None, changed_by) -> ItemHolding`: case table (b-1).
- `holdings.held_quantity(db, holder, item) -> int` (0 when none);
  `items_held(db, holder) -> [(ItemHolding, Item, Entity)]` and
  `holders_of(db, item) -> [(ItemHolding, Entity)]`, `quantity > 0`, by
  name; `held_label(name, n)` -> « name » or « name ×n ».
- Routes (creator CRUD, `crud/items.py`): `GET /api/items/{id}/holders`
  -> `[{id, name, type, quantity}]`; `PUT /api/item-holdings {item_id,
  holder_entity_id, quantity}` -> 200, 422 on a refusal.
  `GET /api/entities/{id}/items` -> `[{id, name, quantity, condition,
  value}]`.

### C-03 — the currencies (family contract)
Produced by: BRIEF-0109-B   Consumed by: C, D
Written before its members; re-read after the last (`skill`).

`QUEST_TERM_DIRECTIONS = ("cost", "reward")`; `QUEST_TERM_CURRENCIES =
("money", "item", "relation", "fact", "skill")`; `COUNTED_CURRENCIES =
("money", "item", "relation")`; `PERSONAL_CURRENCIES = ("relation", "fact",
"skill")`; `FACT_REWARD_LEVELS` = `KNOWLEDGE_LEVELS` minus `unaware`,
sorted. The counterparty is the term's own entity (an active character or
faction of the world), else the offer's giver.

| currency | target | amount | counterparty | `clean_term` refuses | unit (default) |
|---|---|---|---|---|---|
| `money` | -- | >= 1 | character or faction | amount < 1 | 1 a coin |
| `item` | `item_id` (an item of the world) | >= 1 | character or faction | not an item; amount < 1 | the item's `value` a piece |
| `relation` | -- | 1-99 | a character | amount < 1 or > 99; a faction | 1 a point |
| `fact` | `fact_id` (a fact of the world); reward `level` in `FACT_REWARD_LEVELS` or None | -- | a character | a fact elsewhere; level `unaware`; a faction | 5 |
| `skill` | `skill_key`: cost a skill definition of the world; reward a definition or a base domain | -- | a character | a cost on a base domain; an unknown skill; a faction | 20 |

Every term also refuses a direction or a currency outside the vocabulary
and a counterparty that is not an active character or faction of the world.

### C-04 — the indicative unit
Produced by: BRIEF-0109-B   Consumed by: C, D
`quest_value.DEFAULT_RATES = {rate_money: 1, rate_relation: 1, rate_fact:
5, rate_skill: 20, band_low_pct: 100, band_high_pct: 150}`;
`world_rates(db, world_id)` (a NULL column or no row -> the default);
`term_value(db, term, rates)` (C-03's last column); `offer_value(db,
world_id, terms) -> OfferValue(cost, reward, ratio_pct, band_low_pct,
band_high_pct, verdict)`, `ratio_pct = round(reward * 100 / cost)`; verdict
case table (b-3); `value_dict` adds `verdict_label` (« sans coût »,
« maigre », « équilibrée », « généreuse »).
`writes.upsert_quest_economy(db, *, world_id, values)`: refuses an unknown
column, a value that is not a whole number >= 0, and an effective band
whose low end is above its high end, before any write; None returns a rate
to its default.
`quest_wording.term_line(db, term, giver_id)`: one French line per term
(« Donner 2 × Fourrure de loup à Garde », « La relation de Garde envers
vous monte de 5 », ...).

### C-05 — settlement
Produced by: BRIEF-0109-C   Consumed by: D (through C-07)
`writes.settlement_refusals(db, quest) -> list[str]` (French) and
`writes.settle_quest(db, *, quest) -> Quest`: refusals case table (b-4),
application table (b-5). Order: every cost (term order), then every reward
(term order); then the agenda `completed` through `write_agenda_status`
when it is not already; then `settled_at = now`. All in the caller's
transaction; any refusal raises `ValueError(joined)` before the first
write. `SKILL_REWARD_SHARE = 0.10`, `LEARNED_RANK = 0`,
`DEFAULT_FACT_LEVEL = "knows"`, `changed_by = "quest_settlement"`.

### C-06 — the measured context (G1)
Produced by: BRIEF-0109-C   Consumed by: D
`quest_settlement_view.settlement_context(db, quest) -> {quest_id, title,
state, settled, steps: [{order, objective, status, outcome, blocked}],
terms: [{direction, line, note}], value, days: [{day_number,
declared_action, rewritten, steps: [{objective, band}]}], pending_reviews,
refusals, can_settle}`. `note` only on a skill reward: « +N point(s) en
« label » », « apprend « label » (Inexpérimenté) », or « déjà Maître en
« label » : rien ». No model call; no `agenda_id`/`step_id`.

### C-07 — routes
Produced by: B and C   Consumed by: D

| route | body | success | refusal |
|---|---|---|---|
| `POST /api/quest-offers`, `PUT /api/quest-offers/{id}` | `OfferBody` + `terms: [TermBody] | null` (null keeps) | `offer_dict` + `terms: [term + line]`, `value` | 422 |
| `POST /api/quest-offers/value` | `{terms: [TermBody]}` | `value_dict` | -- |
| `GET /api/quest-economy` | -- | `{stored, effective, defaults}` | 400 |
| `PUT /api/quest-economy` | the six columns | same as GET | 422 |
| `GET /api/quest-offers/choices` | -- | + `items: [{id, name, value}]`, `fact_levels`, `rates` | 400 |
| `GET /api/quests/{quest_id}/settlement` | -- | C-06 | 404 not his |
| `POST /api/quests/{quest_id}/settle` | -- | `journee_payload` | 404, 409 refusal |

`journee_payload`: each offer gains `terms: [line]`; each quest gains
`terms: [line]`, `settled`, `settleable` (`settled_at` NULL and agenda
`active`/`paused`/`completed`); each step gains `outcome`.

### C-08 — the surfaces
Produced by: BRIEF-0109-D   Consumed by: nothing in this lot
- `frontend/src/creation/questTerms.js`: `TERM_DIRECTIONS`,
  `CURRENCY_FORMS[c] = {label, list, counted, personal}` in C-03's order.
- Création › Quêtes: « Coûts » / « Récompenses » (`QuestTermRow.svelte`),
  the live value and verdict, ⚖ the world's rates.
- Journée: offer and quest term lines; « Déclarer accomplie » under
  `settleable`; `SettlementRecap.svelte` with « Confirmer : quête
  accomplie », disabled while `can_settle` is false.
- Sheets: « Objets » on a character, a faction, a location (what it holds)
  and « Détenu par » on an item; each row's quantity editable, 0 removes.

## Gate output

### (a) Property trace

| property asserted by the lot | finding | file opened (declaring) |
|---|---|---|
| `item`'s columns and CHECK | R-01 | `models/canon.py` |
| inventory line and interpretation list read `owner_id` | R-02 | `scene_format.py` |
| possession check matches an exact name | R-02 | `cockpit/play_stream.py` |
| registry fields, placement, equip guard, items route | R-02 | `cockpit/crud/entities.py` |
| `item_update` has no producer | R-03 | `cockpit/routes/mutations.py` (docstring + appliers), `cockpit/mutations.py` |
| `require_visitable` | R-04 | `zone_rules.py` |
| zone promotion moves items by `location_id` | R-04 | `writes/zone_promotion.py` |
| the v2.12 report reads the model | R-05 | `scripts/migrate_v2_12_zone_borde.py` |
| the seed's dagger | R-05 | `scripts/seed_pilot.py` |
| `number` field kind with `min` | R-06 | `cockpit/crud/_shared.py` |
| cascade lists; JSON allowlist | R-07 | `writes/worlds.py`, `checks/json_ui_boundary.py` |
| ledger INSERT-only, no balance guard | R-08 | `writes/characters.py` |
| `get_balance` | R-08 | `ledger.py` |
| relation delta: perceiver's row, created at 50 + value | R-09 | `writes/relations.py` |
| knowledge create on a fact, content nullable | R-10 | `writes/knowledge.py`, `models/canon_knowledge.py` |
| `find_held` on a fact | R-10 | `fact_refs.py` |
| rank rise resets xp to 0 | R-11 | `writes/characters.py` |
| `MAX_RANK`, default thresholds | R-11 | `skill_ranks.py` |
| `held_rank` | R-11 | `skill_access.py` |
| teaching from a Maître | R-11 | `cockpit/crud/skills.py` |
| last step approved completes the agenda | R-12 | `cockpit/mutations.py` |
| 0108 writers and views | R-13 | `writes/quests.py`, `quest_reads.py`, `cockpit/routes/quests.py` |
| `pass_play.agenda_id`, `day_rewrite` | R-14 | `models/pipeline.py` |
| `read_latest_resolution` | R-14 | `writes/pipeline.py` |
| fact sheet steps carry objective and band | R-14 | `day_resolve.py` |
| awaiting review is `proposed` | R-15 | `cockpit/routes/day.py` |
| one config row per world | R-16 | `models/config.py` |
| migration shape | R-17 | `scripts/migrate_v2_17_quests.py` |
| `api()` | R-18 | `creation/sheetRequest.svelte.js` |
| module and function caps | R-19 | `checks/module_budget.py`, `checks/function_length.py` |

### (b) Case tables

**b-1 — `write_holding`**, checked in this order:

| input | result |
|---|---|
| both or neither of `quantity`/`delta` | `ValueError` |
| `quantity`/`delta` not an integer | `ValueError` |
| item not an item of the world | `ValueError` |
| holder not an active entity of the world | `ValueError` |
| holder a location that is a zone, and the quantity grows | `ValueError` (the zone message) |
| holder a zone, and the quantity falls | accepted |
| result below 0 | `ValueError` |
| otherwise | the row (created at 0 when absent), previous quantity appended to `change_history` |

**b-2 — the migration's holdings** (per item, at v2.17):

| `owner_id` | `location_id` | holding | note |
|---|---|---|---|
| set, alive | -- | owner, 1 | -- |
| -- | set, alive | place, 1 | « lies in a zone » when the place is a zone (kept) |
| set | set | owner, 1 | « owner kept, place dropped » |
| -- | -- | none | -- |
| set, gone | any | none | « holder no longer exists, skipped » |

**b-3 — the value verdict**: cost 0 -> `free`; `ratio_pct < band_low` ->
`meagre`; `ratio_pct > band_high` -> `generous`; otherwise `balanced`.

**b-4 — `settlement_refusals`**, in order (the first two end the list):

| condition | reason |
|---|---|
| `settled_at` set | « cette quête est déjà réglée » |
| agenda missing, `failed` or `abandoned` | « cette quête est terminée sans succès » |
| a fact cost the character does not know | « il faut connaître le fait à transmettre » |
| a skill cost he is not at Maître in | « il faut être Maître en « label » pour l'enseigner » |
| a skill cost the counterparty holds | « X connaît déjà « label » » |
| the money costs exceed his balance | « il faut N pièce(s), vous en avez M » |
| an item's costs (summed) exceed what he holds | « il faut N × item, vous en avez M » |

**b-5 — what each term writes** (X = the counterparty, C = the character):

| currency | cost | reward |
|---|---|---|
| money | ledger C -n (counterparty X), X +n (counterparty C) | ledger X -n, C +n |
| item | holding C -n, X +n | X -min(n, held), C +n |
| relation | X's row toward C: -n | +n |
| fact | X learns it (`knows`) unless X holds a row | C learns it (`level` or `knows`) unless C holds a row |
| skill | X's row at rank 0, `taught_by` C | held: + max(1, ceil(10 % x points_to_next)), none at Maître; base domain not held: row at `held_rank` then points; definition not held: row at rank 0, `taught_by` X when X is Maître, else none |

### (c) Enumerations

E1 -- every read or write of an item's possession, place or equip state on
`main`:
```
src/world_engine/writes/zone_promotion.py:89:        .where(Item.location_id == parent_id).order_by(Entity.name)
src/world_engine/scene_format.py:94:        .where(Item.owner_id == player_character_id)
src/world_engine/cockpit/mutations.py:493:    if item.owner_id is None:
src/world_engine/cockpit/mutations.py:496:    item.equipped = bool(payload.get("equipped"))
src/world_engine/cockpit/play_stream.py:226:        .where(Item.owner_id == player_id, Entity.name == item_name)
src/world_engine/cockpit/crud/entities.py:382:        owner_id = ext_kwargs["owner_id"] if "owner_id" in ext_kwargs else getattr(current, "owner_id", None)
src/world_engine/cockpit/crud/entities.py:914:        .where(Item.owner_id == entity_id)
src/world_engine/cockpit/crud/entities.py:921:            "equipped": item.equipped,
src/world_engine/cockpit/crud/entities.py:923:            "location_id": item.location_id,
scripts/migrate_v2_12_zone_borde.py:151:        select(Item, Entity).join(Entity, Entity.id == Item.id).where(Item.location_id.in_(zones))
scripts/seed_pilot.py:3395:        owner_id="char-player",
tooling/verify/checks/zone_promotion.py:130:    db.add(Item(id=item.id, location_id=ids["F"]))
tooling/verify/checks/zone_promotion.py:221:        n += _expect(db.get(Item, ids["item"]).location_id == child, "(b) item not moved")
tooling/verify/checks/zone_placement.py:180:    n += _expect_http("fiche, item", lambda: _build_extension_kwargs(
```
(The registry fields `crud/entities.py:199-201` and `_PLACEMENT_FIELDS`
`:347` name the columns as strings.)

E2 -- callers of `write_quest_offer(` on `main`:
```
src/world_engine/cockpit/routes/quests.py:75:        offer = write_quest_offer(
tooling/verify/checks/quests.py:524, 542, 550, 556, 561, 628, 639 (positional-free keyword calls, no `terms`)
```
`terms` defaults to None (keep), so every existing call keeps its meaning.

E3 -- `_apply_mutation`'s `appliers` keys on `main` (`cockpit/routes/
mutations.py:456-470`): `relation_change, new_knowledge, status_change,
item_update, knowledge_change, goal_change, npc_move, event_creation,
resource_change, agenda_step_change, agenda_creation, agenda_delegation,
skill_progress`. After A: the same minus `item_update`.

### (d) Family contracts
C-03 was written before its five members and re-read after `skill`: each
row carries its target, amount rule, counterparty rule, refusals and unit;
`COUNTED_CURRENCIES` and `PERSONAL_CURRENCIES` are the rows' own columns
(RD1 checks the mirror). Tick.

### (e) Gates and the modules that satisfy them

Proposed (`tooling/verify/checks/quest_rewards.py`):
- RA1 <- `models/canon.py`, `models/quests.py`, `crud/entities.py`
  registry, `routes/mutations.py` appliers.
- RA2 <- `scripts/migrate_v2_18_quest_terms.py`.
- RA3 <- `writes/items.py`, `holdings.py`, `scene_format.py`,
  `play_stream.py`, `crud/items.py`, `crud/entities.py`.
- RB1-RB3 <- `writes/quest_terms.py`, `writes/quests.py`, `quest_value.py`,
  `quest_wording.py`, `routes/quests.py`.
- RC1-RC3 <- `writes/quest_settlement.py`, `quest_settlement_view.py`,
  `quest_reads.py`, `routes/quests.py`.
- RD1-RD3 <- `questTerms.js`, `questOffers.svelte.js`, `QuestOffers.svelte`,
  `quests.svelte.js`, `QuestPanel.svelte`, `SettlementRecap.svelte`.
None needs judgment; none teaches an exception.

Passed (existing): `zone_placement.py` (« holding, item » replaces
« fiche, item », A), `zone_promotion.py` (holdings moved, A),
`zone_migration.py` (the v2.12 report, A), `world_cascade.py` (four tables,
A), `json_ui_boundary.py` (A), `single_canon_write.py` (`write_holding` A;
`write_offer_terms`, `copy_terms_to_quest`, `upsert_quest_economy` B;
`settle_quest` C; the full-replace list names `write_offer_terms`; the
retired `item_update` site removed), `day_mutations.py` R5 (the appliers),
`quests.py` (0108, unchanged), `schema_version_agreement.py`,
`schema_partition.py`, `decisions_index.py`, `module_budget.py`,
`function_length.py`, `frontend_build_fresh.py`.

## Amendments

(none)
