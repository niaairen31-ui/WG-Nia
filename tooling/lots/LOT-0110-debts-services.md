# LOT — TICKET-0110 "Debts and services: a debt is a row with its fact, a service owes the rest, a quest settles on credit"

## Objective and cut

A debt becomes a row of its own (J2): what a character owes a character or
a faction -- origin, motive, secrecy, the owed terms (C2: money, items, a
fact to deliver, a skill to teach -- T1), a status that leaves `open` once,
never deleted. Every debt has its fact, known by both parties (F-a,
F-b1), by a faction's members when it is not secret (U1); a faction
creditor is always linked to a person, its contact (X1). The relation type
`debt` is retired: the table is the one way to say « X owes Y » (I2).

A debt is born three ways: by Nia's hand (Création › Dettes), from a
service asked in Journée -- what the character does now applied as a
quest settlement applies its terms, the rest owed (S2) -- and from
« régler à crédit », when the coins or items a quest costs are all the
player lacks (A2). It is repaid all at once (D1); a fact or a skill the
receiver already holds lowers his regard instead, by a per-world setting
(10 and 20 by default). Two requirement forms judge debts: `has_debt_to`,
`no_debt_to` (G1). Journée gains three sub-tabs: « Journée », « Quêtes »,
« Dettes » (W-a).

The lot stops before: the relation's rise and fall at borrowing and
repayment (E -- its own ticket, with a calendar), the erosion of an unpaid
debt (H1), a partial repayment (D2), settling a debt in another currency
(C3), debts proposed by the model, porting « Mes savoirs » into Journée,
rank trials (K1 -- TICKET-0111), any change to the day-chain prompts, and
any change to `legacy.html`.

## Briefs in this lot

- **A — schema v2.19, the vocabulary** (`BRIEF-0110-A-debt-schema.md`):
  `debt`, `debt_term`, `quest_offer.contact_entity_id`, the economy's two
  debt settings (columns, defaults, the ⚖ panel); the two requirement forms
  in both CHECKs, `day_plan`, their evaluators, the French detail and the
  editor's form list; the relation type `debt` retired (the fiche's list,
  the link agent, the seed, `write_relation`, a prompt delivery script);
  `migrate_v2_19_debts.py`; check `debts.py` created (DA1-DA3).
- **B — the writers, reads and routes** (no schema change,
  `BRIEF-0110-B-debt-writers.md`): `writes/debts.py`,
  `writes/debt_sources.py`, the settlement's checks and application made
  reusable, the offer's contact in its writer, `debt_reads.py`, the credit
  preview, `routes/debts.py` and `settle-on-credit` (DB1-DB5).
- **C — Création** (no schema change, `BRIEF-0110-C-debt-creation.md`):
  the « Dettes » island, an owed-term row and its currency mirror, the
  offer editor's contact picker (DC1-DC3).
- **D — Journée** (no schema change, `BRIEF-0110-D-debt-journee.md`):
  three sub-tabs, « Dettes », « Demander un service », « Régler à crédit »
  in the recap (DD1-DD3).

## Dependency graph

Strictly sequential, A -> B -> C -> D.

- B writes A's tables and reads A's constants, settings and evaluators.
- C calls B's routes and mirrors A's `DEBT_CURRENCIES` (C-08).
- D calls B's routes and reuses C's `DebtTermRow.svelte` and `debtTerms.js`.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/debts.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A, C and D rebuild
  `static/`.
- Two placements are forced by existing gates, not by taste: the two
  requirement forms' evaluators, French detail and form list land in A
  with the CHECKs (`day_plan.py` R1/R2, `quests.py` QA1/QC1 and
  `day_narration.py` R15 bind them to the vocabulary in the same commit);
  the economy's two settings land in A end to end, because `PUT
  /api/quest-economy` writes every column it declares (R-09).

## RECON

Opened on `main` at `42f2310` (merge of PR #140, `ticket/0109`), schema
v2.18. Then prototyped on a copy (branch `proto/0110`): `main` ran the full
corpus green (142/142, `WORLD_ENGINE_ENV=test`); every brief's commit ran
it green (143/143 from A on); the four diffs, replayed in order on a clean
worktree of `main` from the brief files, reproduce the prototype tree
exactly (generated files regenerated); every named mutation of every brief
turns `debts.py` red. Findings tagged [M] were measured. Line numbers are
`main`'s.

### R-01 — a relation's type is a free label on one row per oriented pair [M]
Opened: `src/world_engine/models/canon_knowledge.py:23-63` (`Relation`:
`type` TEXT, no CHECK on it; `idx_relation_oriented_social` `:37-40`, at
most one social row per `(entity_a_id, entity_b_id)`);
`src/world_engine/cockpit/crud/_shared.py:143-154` (`RELATION_TYPES`, the
fiche's `datalist` suggestions: `debt` among them).
Finding: the type is a label, suggested not enforced; a pair has one social
row, so a « debt » type would replace whatever the pair already is.
Consequence: I2 -- the table is the one home of a debt; the type is
retired from the suggestions and refused by the writer (C-02).

### R-02 — the model can write a `debt` link, and its prompt offers it [M]
Opened: `src/world_engine/link_author.py:72-78` (`_LINK_RELATION_TYPES`,
`debt` among them), `:274-275` (a type outside it is rejected);
`scripts/seed_pilot.py:1648-1659` (`NPC_LINK_PAIR_USER_TEMPLATE` lists
`ally, enemy, debt, fear, …`), `:2860-2870` (head `pt-npc-link-pair`,
variables `world_name, a_sheet, b_sheet, shared_context`);
`tooling/verify/checks/prompt_version.py:5-8` (the seed never touches text
once a head has a version; `prompt_store`/`write_prompt_version` is the
one path); `scripts/apply_ticket_0097_fact_code_prompts.py` (the delivery
precedent: a new `prompt_version` through `write_prompt_version`).
Consequence: `debt` leaves `_LINK_RELATION_TYPES` and the seed; the live
head loses it through `scripts/apply_ticket_0110_link_prompt.py`, which
edits the CURRENT head's text (one fragment) so a creator edit is kept.

### R-03 — `relation_gte` reads the pair's intensity, whatever its type [M]
Opened: `src/world_engine/day_plan.py:189-217` (`_eval_relation_gte`: the
social row target -> character, `is_social`, any type).
Consequence: retiring a type changes no requirement verdict.

### R-04 — the fact spine: a free fact, its participants, its changes [M]
Opened: `src/world_engine/models/canon_knowledge.py:87-125` (`Fact`:
`ck_fact_spine_exclusive`, a free fact has no typed FK), `:133-145`
(`FactParticipant`); `src/world_engine/writes/facts.py:56`
(`FACT_CHANGE_KINDS = ("correction", "changement")`), `:75-106`
(`create_fact`, `facet` required), `:130-139` (`update_fact_content`: the
previous content appended to `change_history` with its `kind`), `:175-201`
(`attach_participants`, free facts only); `src/world_engine/facets.py:75`
(`information`: family `monde`, granularity `affirmation`, preset `none`);
`src/world_engine/prose_render.py:28-35` (`TOKEN_RE`, `entity_token`);
`src/world_engine/writes/relations.py:150-155` (`_endpoint_tokens`: the
precedent for a server-written fact naming its parties by token).
Consequence: a debt's fact is a free `information` fact, aspect `dette`,
participants debtor, creditor, contact; its text names them by token;
settling and forgiving rewrite it as a `changement` (C-04).

### R-05 — knowledge: secrecy per row, contact dated by the stored row [M]
Opened: `src/world_engine/models/canon_knowledge.py:199-239` (`Knowledge`:
`is_secret` `:225`, per knower; unique `(entity_id, fact_id)`);
`src/world_engine/writes/knowledge.py:241-290` (`write_knowledge`: a create
on `fact_id` attaches to the fact, content may be None), `:202-213` (an
update appends the previous state and sets `updated_at = now`), `:77`
(`knowledge_level_rank`); `src/world_engine/knowledge_resolve.py:34-37`,
`:203-214` (`_as_of`: the later of the anchors' last contact and the stored
row's `updated_at`), `:46-49` (a resolved default never carries
`is_secret`); `src/world_engine/fact_refs.py:57-67` (`find_held` on a
`fact_id`: the stored row).
Finding: after a `changement`, a party whose row is older than the change
would know the old text.
Consequence: F-b1 is the parties' rows `is_secret`; closing a debt
refreshes both parties' rows (same values, `updated_at` now) so they know
at once (C-04).

### R-06 — a faction's members know through a `faction` default [M]
Opened: `src/world_engine/models/canon_knowledge.py:164-193` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, unique `(fact,
scope_type, scope_id)`); `src/world_engine/writes/facts.py:204-221`
(`create_fact_default`).
Consequence: U1 -- a debt toward a faction that is not secret gets one
`faction` default at `knows` (C-03).

### R-07 — the requirement vocabulary and every place that mirrors it [M]
Opened: `src/world_engine/day_plan.py:84-98` (`REQUIREMENT_TYPES`,
`MODEL_REQUIREMENT_TYPES`, the three shape groups), `:337-346`
(`_EVALUATORS`), `:379-400` (`evaluate_specs`: an unknown type raises),
`:545-561` (`_validate_requirement`: the model's four only, `:549`);
`src/world_engine/models/config.py:133-144` and
`src/world_engine/models/quests.py:91-103` (the two CHECK pairs, byte for
byte); `src/world_engine/writes/goals_agendas.py:607-609`
(`_TARGET_ENTITY_TYPE`, one type or None), `:631-675`
(`_clean_requirement`); `src/world_engine/day_resolve.py:260-270`
(`_BLOCKED_DETAIL_FR`); `frontend/src/creation/questRequirements.js:10-19`
(`REQUIREMENT_FORMS`); `tooling/verify/checks/quests.py:104-105`, `:153`,
`:180` (QA1), `:797-805` (QC1); `tooling/verify/checks/day_plan.py:
192-195` (R2), `:356-368` (R3); `tooling/verify/checks/day_narration.py:
651-682` (R15).
Consequence: the two forms land in every mirror in one commit (A); the
target is a character or a faction, so `_TARGET_ENTITY_TYPE` takes a tuple
of types (C-02).

### R-08 — the settlement's internals [M]
Opened: `src/world_engine/writes/quest_settlement.py:64-69` (`skill_row`),
`:80-108` (`_cost_refusals`, private, French), `:111-119`
(`settlement_refusals`), `:122-126` (`_money`: `source_type="quest"`
hard-written), `:129-135` (`_items`), `:145-158` (`_skill_reward`),
`:161-178` (`_apply_term(db, quest, …)`), `:181-198` (`settle_quest`: the
`quest` write); `src/world_engine/quest_settlement_view.py:23`
(imports `skill_row`, `settlement_refusals`, `skill_reward_points`);
`tooling/verify/canon_write_policy.txt:63-64` (`settle_quest` allow-listed
for `quest`).
Finding: every term application is bound to a quest row and to the
`quest` ledger origin; the refusals are strings with no kind.
Consequence: B makes them reusable without changing what a settlement
does: `cost_checks` returns `(kind, reason)`, `apply_term` takes the world
and the character (and `amount`, `source_type`), `finish_settlement` holds
the `quest` write -- the same one site, relocated in the policy (C-05).

### R-09 — the economy: defaults, columns, and a PUT that writes them all [M]
Opened: `src/world_engine/quest_value.py:22-25` (`DEFAULT_RATES`), `:43-47`
(`world_rates`: one key per default), `:50-61` (`term_value`);
`src/world_engine/writes/quest_terms.py:55-57` (`ECONOMY_COLUMNS`),
`:163-185` (`upsert_quest_economy`: every key it receives is written);
`src/world_engine/cockpit/routes/quests.py:88-94` (`EconomyBody`), `:168-
175` (`set_economy`: `body.model_dump()`, so a column absent from the body
is written None); `frontend/src/creation/QuestOffers.svelte:34-37`
(`RATE_LABELS`, the ⚖ panel's fields); `src/world_engine/models/quests.py:
222-243` (`QuestEconomy`: no `change_history`).
Consequence: the two debt settings join `DEFAULT_RATES`,
`ECONOMY_COLUMNS`, `EconomyBody` and `RATE_LABELS` in the same commit, or
saving the rates would erase them (A).

### R-10 — an offer names a giver, never a person for a faction [M]
Opened: `src/world_engine/models/quests.py:39-61` (`QuestOffer`:
`giver_entity_id` `:49`, a character or a faction, H1);
`src/world_engine/writes/quests.py:71-75` (`_check_giver`), `:78-86`
(`_snapshot`), `:89-147` (`write_quest_offer`);
`src/world_engine/cockpit/routes/quests.py:71-81` (`OfferBody`);
`src/world_engine/quest_reads.py:61-78` (`offer_dict`), `:93-116`
(`editor_choices`); `frontend/src/creation/questOffers.svelte.js:118-130`
(`draftBody`); `frontend/src/creation/QuestOffers.svelte:104-109` (« Donnée
par »).
Consequence: X1 -- `quest_offer.contact_entity_id`, written by the
writer, shown and edited in the offer editor.

### R-11 — an active membership is a row with no `left_at` [M]
Opened: `src/world_engine/models/canon_faction.py:85-129`
(`FactionMembership`: `left_at` `:129`, NULL = active;
`idx_membership_unique_active` `:103-106` on `left_at IS NULL`).
Consequence: « active member » is `left_at IS NULL` (C-03).

### R-12 — money, items and skills: the writers a debt calls [M]
Opened: `src/world_engine/ledger.py:18-23` (`get_balance`);
`src/world_engine/writes/characters.py:213-250` (`write_ledger_entry`: no
balance guard, INSERT only), `:105-142` (`write_skill_row`: refuses a row
already held); `src/world_engine/models/canon.py:467` (`ledger.source_type`
TEXT, no CHECK); `src/world_engine/writes/items.py:39-74`
(`write_holding`); `src/world_engine/holdings.py:16-20` (`held_quantity`);
`src/world_engine/skill_access.py:82-91` (`held_rank`), `:94-100`
(`skill_label`);
`src/world_engine/skill_ranks.py:30` (`MAX_RANK = 5`).
Consequence: repayment uses these writers; the ledger origins `debt` and
`service` need no migration (documented in the schema doc).

### R-13 — the surfaces [M]
Opened: `frontend/src/journee/Journee.svelte:1-238` (one view: declare
`:53`, `<QuestPanel />` `:77`, the days); `frontend/src/journee/
quests.svelte.js:84-87` (`settleQuest`); `frontend/src/journee/
SettlementRecap.svelte:52-54`; `frontend/src/creation/QuestTermRow.svelte:
10` (props `term, choices, onremove, onchange`);
`frontend/src/creation/questTerms.js:11-17`, `:36-48`;
`frontend/src/creation/tabs.js:52` (« 16 static entries »), `:343-351`
(the `quetes` entry); `frontend/src/creation/Creation.svelte:253`;
`frontend/src/creation/mount.js:47`; `frontend/src/creation/registry.js:
554-562` (the `questOffers` entry, `origin: 'new'`); `frontend/public/creation.css:287-297` (`.creation-sub-tab-bar`,
`.creation-sub-tab`, loaded for the whole shell by `frontend/index.html:7`),
`:312`; `tooling/verify/checks/page_contract.py:46-50` (`TAB_KEYS`);
`src/world_engine/cockpit/legacy.html:463-468` (Play's sub-tab bar: the
look W-a asks for), `:1759-1781` (« Mes savoirs » reads stored rows only);
`src/world_engine/cockpit/app.py:58`, `:142` (router registration);
`src/world_engine/cockpit/routes/day.py:126` (`_resolve_player_character`).
Consequence: Journée's sub-tabs reuse the shell's sub-tab classes; « Mes
savoirs » is not ported (W-a).

### R-14 — the migration's shape, and the governance a schema touches [M]
Opened: `scripts/migrate_v2_17_quests.py:103-114` (rebuild from the model),
`:118-149` (`_apply_ddl`: one raw transaction, `foreign_keys` OFF and
`legacy_alter_table` ON before `BEGIN`); `scripts/migrate_v2_18_quest_terms.py:
69` (the FK post-check scoped to the tables written), `:154` (`ALTER TABLE
… ADD COLUMN` precedent); the v2.18 DDL of `agenda_step_requirement`,
`quest_offer_requirement`, `quest_economy` and `quest_offer`, dumped from
`main` (embedded in `debts.py`); `src/world_engine/schema_version.py:15`;
`world-engine-schema.md:3`; `src/world_engine/writes/worlds.py:66-79`;
`tooling/verify/checks/world_cascade.py:150-207`;
`tooling/verify/canon_write_policy.txt:4-9` (`[CANON_TABLES]`);
`tooling/verify/checks/module_budget.py:57-58` (40 functions and 1000
lines per `src/` module -- not « 40 modules »);
`tooling/verify/checks/corpus_gate.py:53` (15 s per check);
`tooling/verify/checks/decisions_index.py:15-17` (strict header);
`CLAUDE.md` (37 838 characters of 38 000).
Consequence: A follows the v2.17 shape; no JSON column is added (no
`json_ui_boundary` entry); no CLAUDE.md change.

### R-15 — the engine keeps no world time [M]
Opened: `src/world_engine/models/pipeline.py:30-56` (`Batch`;
`day_number` `:44`, `max + 1` per SESSION `:40`, unique per session
`:33`); `grep -rn "world_day" src/world_engine/models` ->
nothing.
Consequence: H1 -- the erosion of an unpaid debt waits for a world-level
day counter: its reactivation is `grep -rn "world_day"
src/world_engine/models` returning a column.

## Contract sheet

### C-01 — schema v2.19
Produced by: BRIEF-0110-A   Consumed by: B, C, D
- `debt(id, world_id -> world, debtor_entity_id -> entity NOT NULL,
  creditor_entity_id -> entity NOT NULL, contact_entity_id -> entity,
  origin, origin_quest_id -> quest, reason, is_secret BOOLEAN NOT NULL
  DEFAULT 0, fact_id -> fact NOT NULL, status NOT NULL DEFAULT 'open',
  created_at, closed_at, closed_note)`, CHECKs byte for byte:
  ```
  ck_debt_origin        origin IN ('service','quest','creator')
  ck_debt_status        status IN ('open','settled','forgiven')
  ck_debt_parties       debtor_entity_id <> creditor_entity_id
  ck_debt_origin_quest  (origin = 'quest') = (origin_quest_id IS NOT NULL)
  ck_debt_closed        (status = 'open') = (closed_at IS NULL)
  ```
  indexes on `world_id`, `debtor_entity_id`, `creditor_entity_id`.
- `debt_term(id, world_id, debt_id -> debt, term_order, currency, item_id
  -> item, fact_id -> fact, skill_key, amount)`, CHECKs:
  ```
  ck_debt_term_currency currency IN ('money','item','fact','skill')
  ck_debt_term_shape    (currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)
  ```
  index on `debt_id`.
- `quest_offer.contact_entity_id -> entity` (nullable).
- `quest_economy.debt_fact_relation`, `.debt_skill_relation` (each NULL or
  >= 0, in `ck_quest_economy_rates`).
- Both requirement CHECK pairs gain `'has_debt_to','no_debt_to'` in the type
  list and in the `target_entity_id` group.
- `models.DEBT_ORIGINS`, `DEBT_STATUSES`, `DEBT_CURRENCIES` quote those
  CHECKs, in order.

### C-02 — the vocabulary
Produced by: BRIEF-0110-A   Consumed by: B, C
- `day_plan.REQUIREMENT_TYPES` = the eight, then `has_debt_to`,
  `no_debt_to`; both in `ENTITY_TARGET_TYPES`; neither in
  `THRESHOLD_TYPES` nor `MODEL_REQUIREMENT_TYPES`. Verdicts: case table
  (b-6). French detail: « il ne doit rien à {required} », « il a encore une
  dette envers {required} ».
- `writes.goals_agendas._TARGET_ENTITY_TYPE`: values are `None` or a tuple
  of entity types; the two debt forms take `("character", "faction")`.
- `frontend/src/creation/questRequirements.js`: `has_debt_to` « A une dette
  envers », `no_debt_to` « N’a aucune dette envers », both `list:
  'givers'`, `column: 'entity'`, `threshold: false`; `targetOptions` lists
  `choices.givers`.
- `relation_orientation.RETIRED_RELATION_TYPES = ("debt",)`;
  `write_relation` raises `ValueError` on a retired type, before any write;
  `debt` leaves `crud._shared.RELATION_TYPES`,
  `link_author._LINK_RELATION_TYPES` and the seeded link-pair prompt.
- `quest_value.DEFAULT_RATES` gains `debt_fact_relation: 10`,
  `debt_skill_relation: 20`; `writes.quest_terms.ECONOMY_COLUMNS`,
  `routes.quests.EconomyBody` and the ⚖ panel's `RATE_LABELS` list both.

### C-03 — the owed currencies and the debt writer (family contract)
Produced by: BRIEF-0110-B   Consumed by: B (C-04, C-05), C, D
Written before its members; re-read after the last (`skill`).

`DebtTermSpec(currency, item_id=None, fact_id=None, skill_key=None,
amount=None)`. The receiver of a fact or a skill is the creditor, his
contact for a faction (`receiver_of`).

| currency | target | amount | `clean_debt_term` refuses | owed line (`debt_term_line`) | in the fact | value |
|---|---|---|---|---|---|---|
| `money` | -- | >= 1 | amount < 1 | « N pièce(s) » | « N pièce(s) » | N x rate_money |
| `item` | `item_id`, an item of the world | >= 1 | not an item; amount < 1 | « N × name » | « N × [token] » | N x item.value |
| `fact` | `fact_id`, a fact of the world | -- | a fact elsewhere | « le savoir « text » » | « le savoir « text » » | rate_fact |
| `skill` | `skill_key`, a skill definition of the world | -- | a base domain; an unknown skill | « l'enseignement de « label » » | same | rate_skill |

`clean_debt_term` also refuses a currency outside `DEBT_CURRENCIES`.
- `prepare_debt(db, *, world_id, debtor_id, creditor_id, contact_id,
  origin, origin_quest_id=None, reason=None, is_secret=False, terms) ->
  PreparedDebt`: case table (b-1), nothing written. `reason` is stripped,
  empty -> None.
- `write_debt(db, prepared, *, changed_by) -> Debt`: the fact (free,
  `information`, aspect `dette`, `default_level` `unaware`, text
  `debt_fact_text(..., state="open")`), its participants (debtor, creditor,
  contact if any, in that order), the row `open`, its terms in order
  (`term_order` from 1), the parties' knowledge and the faction default
  (b-5). `create_debt(db, *, changed_by, **fields)` is the two in a row.
- `debt_fact_text(db, *, debtor_id, creditor_id, contact_id, terms, reason,
  state, note=None)`: with `D`, `C`, `K` the parties' tokens, `via` = «
  (par l'entremise de K) » or nothing, `tail` = « : owed » + « — reason »
  if any, `owed` = the terms' fact phrases joined by « , » or « une
  faveur »: `open` -> « D doit à C{via}{tail}. »; `settled` -> « D a réglé
  sa dette envers C{via}{tail}. »; `forgiven` -> « C a fait grâce à D de sa
  dette{via}{tail}. » + « (note) » if any.
- `is_active_member(db, character_id, faction_id) -> bool` (R-11).
- Constants: `DEBT_FACT_LEVEL = "knows"`, `DEBT_FACT_ASPECT = "dette"`,
  `DEBT_SOURCE = "dette"`, `DEBT_LEDGER_SOURCE = "debt"`,
  `STALE_RELATION_SETTING = {"fact": "debt_fact_relation", "skill":
  "debt_skill_relation"}`.

### C-04 — repaying and forgiving
Produced by: BRIEF-0110-B   Consumed by: C, D (through C-07)
- `debt_refusals(db, debt) -> list[str]` (French): case table (b-2).
- `settle_debt(db, *, debt, changed_by) -> Debt`: `ValueError(joined)` on a
  refusal, before any write; else every term delivered in term order (b-3),
  then closed `settled`.
- `forgive_debt(db, *, debt, note, changed_by) -> Debt`: `ValueError` when
  not `open`; else closed `forgiven`, `closed_note` the stripped note or
  None.
- Closing: `status`, `closed_at = now`, `closed_note`; the fact rewritten
  by `update_fact_content(kind="changement")` with the closed state's text;
  the debtor's and the receiver's knowledge rows refreshed (b-5). The
  ledger lines carry `source_type` `debt`, reason « Dette envers C ».

### C-05 — where a debt comes from (service, credit) and the settlement made reusable
Produced by: BRIEF-0110-B   Consumed by: C-06, C-07
- `writes/quest_settlement.py`: `cost_checks(db, character_id, terms,
  giver_id) -> [(kind, reason)]`, kind `money`, `item` or `other`, the
  reasons `_cost_refusals` gave, in its order; `closed_refusal(db, quest)`;
  `settlement_refusals` = `[closed]` or the reasons of `cost_checks`
  (unchanged output); `apply_term(db, *, world_id, character_id, term,
  giver_id, reason, source_type="quest", amount=None)` (the D table of
  0109; `amount` replaces a money or item term's own); `in_order(terms)`;
  `finish_settlement(db, quest)` (the agenda `completed` when it is not,
  `settled_at`); `settle_quest` = refusals, `apply_term` over `in_order`,
  `finish_settlement`. `canon_write_policy.txt` moves the `quest` site from
  `settle_quest` to `finish_settlement`.
- `writes/debt_sources.py`:
  - `request_service(db, *, character, provider_id, on_behalf_of_id, terms:
    [TermSpec], owed: [DebtTermSpec], reason, is_secret) -> Debt`: case
    table (b-7), nothing written before every check; then `apply_term` over
    `in_order` of the cleaned terms (giver = the provider, `source_type`
    `service`, reason « Service de P »), then `write_debt` (origin
    `service`, `changed_by` `service`).
  - `credit_plan(db, quest) -> CreditPlan(refusals, paid, owed)`: case
    table (b-4).
  - `credit_contact(db, quest, creditor_id, contacts) -> Optional[str]`:
    a character creditor -> None; a faction -> `contacts[creditor]` if set,
    else the offer's contact when the faction is the giver, else None.
  - `settle_quest_on_credit(db, *, quest, contacts, is_secret) -> Quest`:
    `ValueError` on any plan refusal, and « il faut choisir le membre de « F
    » qui porte la dette » for a faction creditor with no contact, before
    any write; every debt prepared (origin `quest`, `origin_quest_id`,
    reason « Quête « title » », the shortfall terms); then `apply_term` over
    `in_order` with `amount = paid` for a money or item cost (skipped when
    0), `finish_settlement`, then each debt written (`changed_by`
    `quest_credit`).
- `writes/quests.py`: `write_quest_offer(..., contact_entity_id=None)`;
  `_check_contact`: a contact on a character giver, or one who is not an
  active character member of the faction giver, raises; the value is
  written as given; `_snapshot` records it.

### C-06 — what the surfaces read
Produced by: BRIEF-0110-B   Consumed by: C, D
- `debt_reads.debt_dict(debt, db)` keys, always all present: `id,
  debtor_id, debtor_name, creditor_id, creditor_name, contact_id,
  contact_name, origin, origin_label` (« service », « création », « quête
  « title » »)`, reason, is_secret, status, status_label` (« due »,
  « réglée », « remise »)`, created_at, closed_at, closed_note, terms`
  (`[{currency, item_id, fact_id, skill_key, amount, line}]`)`, value` (the
  sum of `term_value` at the world's rates). No agenda or step id.
- `world_debts(world_id, db)`: every debt, open first, then most recent.
- `player_debts(character, db)`: `{owes, owed}` -- the debts he is debtor
  of, creditor of -- each with `refusals` (C-04, empty when closed) and
  `repayable`.
- `quest_reads.offer_dict` gains `contact_entity_id`, `contact_name`;
  `editor_choices` gains `members: {faction_id: [{id, name}]}` (active
  character members, by name).
- `quest_settlement_view.settlement_context` gains `credit: {possible,
  refusals, debts: [{creditor_id, creditor_name, is_faction, lines,
  contact_id, members}]}` (`contact_id` from `credit_contact(…, {})`).

### C-07 — routes
Produced by: BRIEF-0110-B   Consumed by: C, D

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/debts` | -- | `[debt_dict]` | 400 no world |
| `POST /api/debts` | `{debtor_entity_id, creditor_entity_id, contact_entity_id, reason, is_secret, terms: [{currency, item_id, fact_id, skill_key, amount}]}` | 201 `debt_dict` (origin `creator`) | 422 |
| `POST /api/debts/{id}/repay` | -- | `debt_dict` | 404 other world, 409 refusal |
| `POST /api/debts/{id}/forgive` | `{note}` | `debt_dict` | 404, 409 closed |
| `GET /api/journee/debts` | -- | `player_debts` | 400 |
| `POST /api/services` | `{provider_entity_id, on_behalf_of_id, terms: [TermBody], owed: [owed term], reason, is_secret}` | 201 `player_debts` | 422 |
| `POST /api/quests/{id}/settle-on-credit` | `{is_secret, contacts: {faction_id: member_id}}` | `journee_payload` | 404 not his, 409 refusal |
| `POST`/`PUT /api/quest-offers…` | `OfferBody` + `contact_entity_id` | `offer_dict` | 422 |

`routes/debts.py` is registered after `routes/quests.py` in `app.py`.

### C-08 — Création
Produced by: BRIEF-0110-C   Consumed by: D (`DebtTermRow`, `debtTerms.js`)
- `frontend/src/creation/debtTerms.js`: `DEBT_CURRENCY_FORMS` in
  `DEBT_CURRENCIES`' order (`money` and `item` counted), `blankDebtTerm`,
  `debtTargetOptions` (skills: definitions only), `debtTermBody`,
  `owedFromService(terms)` (the money and item rewards, as owed terms).
- `DebtTermRow.svelte` (props `term, choices, onremove`).
- « Dettes » tab (`dettes`, container `creation-dettes`, island `debts`,
  origin `new`, « + Nouvelle dette ») -> `Debts.svelte` /
  `debts.svelte.js`: the list (C-06), « Rembourser », « Remettre » with a
  note, the editor (debtor, creditor, a faction's contact among
  `choices.members`, motive, « Transaction secrète », owed terms). No PUT,
  no DELETE.
- `QuestOffers.svelte`: « Contact de la faction » when the giver has
  members; changing the giver clears it; `questOffers.svelte.js` loads
  and sends `contact_entity_id`.

### C-09 — Journée
Produced by: BRIEF-0110-D   Consumed by: nothing in this lot
- `Journee.svelte`: `SUB_TABS = { journee: 'Journée', quetes: 'Quêtes',
  dettes: 'Dettes' }`, the shell's `.creation-sub-tab-bar`; « Journée »
  holds the declaration, `<ServiceForm />` and the days; « Quêtes »
  `<QuestPanel />`; « Dettes » `<DebtsPanel />`.
- `journee/debts.svelte.js`: `GET /api/journee/debts`, repay and forgive
  through C-07, `POST /api/services`; S2's prefill (`servicePrefill`: the
  owed list follows `owedFromService` until it is edited).
- `ServiceForm.svelte`: who helps; « Pour le compte de » among the
  factions he is a member of; « Ce qu’il fait pour vous » / « Ce que ça
  coûte tout de suite » (`QuestTermRow`); « Ce que vous devrez »
  (`DebtTermRow`); motive; secrecy; « Accepter le service ».
- `DebtsPanel.svelte`: « Ce que je dois », « Ce qu’on me doit »; an open
  debt shows its refusals (« Pas encore : … »), « Rembourser » (disabled
  unless `repayable`) and « Remettre » with a note.
- `quests.svelte.js`: `settleOnCredit(questId, contacts, isSecret)`;
  `SettlementRecap.svelte`: under `ctx.credit?.possible`, « Régler à
  crédit »: each creditor and its lines, a member picker for a faction
  (its contact preselected), secrecy, « Confirmer : régler à crédit »;
  Journée's debts are re-read after it.

## Gate output

### (a) Property trace

| property asserted by the lot | finding | file opened (declaring) |
|---|---|---|
| relation type has no CHECK; one social row per oriented pair | R-01 | `models/canon_knowledge.py` |
| the fiche's relation types are datalist suggestions | R-01 | `cockpit/crud/_shared.py` |
| the link agent's closed vocabulary includes `debt` | R-02 | `link_author.py` |
| the seed lists `debt` in the link-pair template; head id and variables | R-02 | `scripts/seed_pilot.py` |
| the seed never rewrites a versioned head | R-02 | `checks/prompt_version.py` (its rule text) and `prompt_store`/`writes/prompts.py` |
| `relation_gte` reads any social type | R-03 | `day_plan.py` |
| free fact, spine exclusivity, participants on free facts only | R-04 | `models/canon_knowledge.py`, `writes/facts.py` |
| `FACT_CHANGE_KINDS`, history appended with kind | R-04 | `writes/facts.py` |
| `information` facet: affirmation, preset none | R-04 | `facets.py` |
| token form | R-04 | `prose_render.py` |
| `is_secret` per knowledge row; unique (entity, fact) | R-05 | `models/canon_knowledge.py` |
| update sets `updated_at`, appends history | R-05 | `writes/knowledge.py` |
| `as_of` reads the stored row's `updated_at` | R-05 | `knowledge_resolve.py` |
| `faction` scope of `fact_default` | R-06 | `models/canon_knowledge.py` |
| requirement vocabulary, groups, evaluator dispatch, model parser | R-07 | `day_plan.py` |
| the two CHECK pairs | R-07 | `models/config.py`, `models/quests.py` |
| target type map, cleaning | R-07 | `writes/goals_agendas.py` |
| French blocked detail | R-07 | `day_resolve.py` |
| the editor's form list | R-07 | `frontend/src/creation/questRequirements.js` |
| QA1/QC1, R2/R3, R15 rules | R-07 | `checks/quests.py`, `checks/day_plan.py`, `checks/day_narration.py` |
| settlement internals and the `quest` ledger origin | R-08 | `writes/quest_settlement.py` |
| `settle_quest` is the `quest` write site | R-08 | `canon_write_policy.txt` |
| defaults, rates per key, term value | R-09 | `quest_value.py` |
| economy columns; upsert writes every key received | R-09 | `writes/quest_terms.py` |
| PUT writes `model_dump()` | R-09 | `cockpit/routes/quests.py` |
| the ⚖ panel's fields | R-09 | `frontend/src/creation/QuestOffers.svelte` |
| `quest_economy` has no `change_history` | R-09 | `models/quests.py` (and the dumped DDL) |
| giver character or faction, no contact | R-10 | `models/quests.py`, `writes/quests.py` |
| active membership = `left_at IS NULL` | R-11 | `models/canon_faction.py` |
| money, holdings, skill rows, labels | R-12 | `ledger.py`, `writes/characters.py`, `writes/items.py`, `holdings.py`, `skill_access.py`, `skill_ranks.py` |
| `ledger.source_type` free text | R-12 | `models/canon.py` |
| Journée one view; recap; term row props | R-13 | `frontend/src/journee/*`, `frontend/src/creation/QuestTermRow.svelte` |
| tab registration points | R-13 | `tabs.js`, `Creation.svelte`, `mount.js`, `registry.js`, `creation.css`, `checks/page_contract.py` |
| sub-tab classes global | R-13 | `frontend/public/creation.css`, `frontend/index.html` |
| Play's « Mes savoirs » reads stored rows | R-13 | `cockpit/legacy.html` |
| router registration; player resolution | R-13 | `cockpit/app.py`, `cockpit/routes/day.py` |
| migration shape; ADD COLUMN precedent; FK post-check scope | R-14 | `scripts/migrate_v2_17_quests.py`, `scripts/migrate_v2_18_quest_terms.py` |
| caps 40/1000, 15 s, strict header | R-14 | `checks/module_budget.py`, `checks/corpus_gate.py`, `checks/decisions_index.py` |
| no world-level day | R-15 | `models/pipeline.py` + the pasted grep |

### (b) Case tables

**b-1 — `prepare_debt`**, checked in this order (the first failure raises):

| input | result |
|---|---|
| debtor not an active character of the world | `ValueError` |
| creditor not an active character or faction of the world | `ValueError` |
| creditor = debtor | `ValueError` |
| character creditor with a contact | `ValueError` |
| faction creditor with no contact | `ValueError` (X1) |
| contact not an active character, or not an active member of the faction | `ValueError` |
| origin outside `DEBT_ORIGINS` | `ValueError` |
| origin `quest` without a quest of the world, or a quest with another origin | `ValueError` |
| a term refused by `clean_debt_term` (C-03) | `ValueError` naming the term |
| no term and no reason | `ValueError` |
| otherwise | `PreparedDebt` |

**b-2 — `debt_refusals`** (D = the debtor's name; the first two end the list):

| condition | reason |
|---|---|
| `settled` | « cette dette est déjà réglée » |
| `forgiven` | « cette dette a été remise » |
| a fact term, the receiver does not hold it, the debtor does not know it | « D doit connaître le fait à transmettre » |
| a skill term, the receiver does not hold it, the debtor is not at Maître | « D doit être Maître en « label » pour l'enseigner » |
| a fact or skill term the receiver already holds | no refusal (b-3) |
| the money terms exceed the debtor's balance | « il faut N pièce(s), D en a M » |
| an item's terms (summed) exceed what he holds | « il faut N × item, D en a M » |

**b-3 — what repaying writes** (D debtor, C creditor, R receiver):

| currency | write |
|---|---|
| money | ledger D -n (counterparty C), C +n (counterparty D), `source_type` `debt` |
| item | holding D -n, C +n |
| fact, R does not hold it | R learns it at `knows`, source « dette » |
| skill, R does not hold it | R's row at rank 0, `taught_by` D |
| fact, R holds it | R's regard toward D: `- debt_fact_relation` (none when 0) |
| skill, R holds it | R's regard toward D: `- debt_skill_relation` (none when 0) |

**b-4 — `credit_plan`** (the quest's cost terms, in order):

| condition | result |
|---|---|
| quest settled, or its agenda missing, failed, abandoned | refused: `closed_refusal` |
| any `other` cost check (a fact unknown, a skill not Maître, the counterparty holds it) | refused: those reasons |
| a money cost | pay = min(amount, money left of max(0, balance)); the rest owed to its counterparty, else the giver |
| an item cost | pay = min(amount, that item left of what he holds); the rest owed likewise |
| nothing owed | refused: « rien à régler à crédit : la quête peut être déclarée accomplie » |
| otherwise | `paid` per cost term, `owed` per creditor, in term order |

**b-5 — who knows a debt's fact**:

| creditor | secret | at creation | at closing |
|---|---|---|---|
| character | no | debtor, creditor: rows `knows` | both rows refreshed |
| character | yes | debtor, creditor: rows `knows`, `is_secret` | both rows refreshed (secrecy kept) |
| faction | no | debtor, contact: rows `knows`; `faction` default `knows` | debtor's and contact's rows refreshed |
| faction | yes | debtor, contact: rows `knows`, `is_secret`; no default | likewise |

A refreshed row keeps its level when it is `knows` or above, else rises to
`knows`; its other fields are kept; `updated_at` is now.

**b-6 — the debt forms** (C the character, T the target):

| state | `has_debt_to` | `no_debt_to` |
|---|---|---|
| C debtor of an `open` debt toward T | met | not met |
| C's debts toward T all `settled`/`forgiven`, or none | not met | met |
| only debts toward others, or debts T owes C | not met | met |

**b-7 — `request_service`**, in order:

| input | result |
|---|---|
| provider not another active character of the world | `ValueError` |
| `on_behalf_of_id` a faction the provider is not an active member of | `ValueError` |
| a term refused by `clean_terms` (0109 C-03, giver = provider) | `ValueError` |
| a cost the player cannot pay now (`cost_checks`, any kind) | `ValueError` (French reasons) |
| the debt refused by `prepare_debt` (b-1) | `ValueError` |
| otherwise | the terms applied, then the debt written |

### (c) Enumerations

E1 -- every literal of the relation type `debt` on `main`:
```
src/world_engine/observation_reads.py:63:        return "debt"
src/world_engine/cockpit/crud/_shared.py:144:    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
src/world_engine/link_author.py:73:    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
scripts/seed_pilot.py:1656:{"kind":"relation","type":<one of: ally, enemy, debt, fear, fascination, \
```
(`observation_reads.py:63` is the observation engine's « speaking debt », a
score's name, not a relation type: untouched.) Production holds no
`relation` row of type `debt` (Nia's query, read-only, 2026-10-07: 0 rows).

E2 -- every mirror of the requirement vocabulary on `main`:
```
src/world_engine/day_plan.py:84 REQUIREMENT_TYPES; :92 MODEL_REQUIREMENT_TYPES; :96-98 the three groups; :337 _EVALUATORS
src/world_engine/models/config.py:133-144 ck_agenda_step_requirement_type/_shape
src/world_engine/models/quests.py:91-103 ck_quest_offer_requirement_type/_shape
src/world_engine/writes/goals_agendas.py:47-50 imports; :607 _TARGET_ENTITY_TYPE
src/world_engine/day_resolve.py:260 _BLOCKED_DETAIL_FR
src/world_engine/day_feasibility.py:162 (docstring: never references REQUIREMENT_TYPES)
frontend/src/creation/questRequirements.js:10 REQUIREMENT_FORMS
tooling/verify/checks/quests.py:104-105, 153, 180 (QA1), 797-805 (QC1)
tooling/verify/checks/day_plan.py:192 EXPECTED_REQUIREMENT_TYPES; :356-368 required_pairs
tooling/verify/checks/day_narration.py:676-682 (R15 reads REQUIREMENT_TYPES)
tooling/verify/checks/day_feasibility.py:191 (forbidden names, unaffected)
```

E3 -- every caller of the settlement's private helpers and of
`settle_quest(` on `main`:
```
src/world_engine/writes/quest_settlement.py:119 _cost_refusals; :165 _money; :167 _items; :177 _skill_reward; :193 _apply_term
src/world_engine/cockpit/routes/quests.py:234 settle_quest
tooling/verify/checks/quest_rewards.py:750, 848, 855 settle_quest
```
(The other `_items(`/`_money(` hits of a raw grep are unrelated functions of
other modules: `zone_promotion._items`, `tick._tick_normalize_*_items`.)

E4 -- callers of `write_quest_offer(` on `main`: `cockpit/routes/quests.py`
(1), `checks/quest_rewards.py` (6), `checks/quests.py` (7), all keyword
calls with no `contact_entity_id`; its default None keeps their meaning.

E5 -- every reader of `DEFAULT_RATES` / `ECONOMY_COLUMNS` on `main`:
```
src/world_engine/writes/quest_terms.py:39, 55, 167, 174-176
src/world_engine/quest_value.py:47 (world_rates)
src/world_engine/cockpit/routes/quests.py:36, 39, 163-164
tooling/verify/checks/quest_rewards.py:590-593 (world_rates == DEFAULT_RATES), 607-622
```
Extending both by two keys keeps every one of them true.

E6 -- world time: `grep -rn "world_day" src/world_engine/models` -> no
output (H1's reactivation condition).

### (d) Family contracts
C-03 (the owed currencies) was written before its four members and re-read
after `skill`: each row carries its target, amount rule, refusals, owed
line, fact phrase and value; `DebtTermRow`/`debtTerms.js` mirror its first
two columns (DC1). Tick.

### (e) Gates and the modules that satisfy them

Proposed (`tooling/verify/checks/debts.py`, growing A -> D):
- DA1 <- `models/quests.py`, `models/config.py`, `quest_value.py`,
  `writes/quest_terms.py`, `schema_version.py`, `day_plan.py`,
  `day_resolve.py`, `questRequirements.js`, `relation_orientation.py`,
  `cockpit/crud/_shared.py`, `link_author.py`, `scripts/seed_pilot.py`,
  `writes/relations.py`.
- DA2 <- `scripts/migrate_v2_19_debts.py`.
- DA3 <- `day_plan.py`, `day_resolve.py`, `writes/goals_agendas.py`.
- DB1-DB5 <- `writes/debts.py`, `writes/debt_sources.py`,
  `writes/quest_settlement.py`, `writes/quests.py`, `debt_reads.py`,
  `quest_reads.py`, `quest_settlement_view.py`, `cockpit/routes/debts.py`,
  `cockpit/routes/quests.py`.
- DC1-DC3 <- `debtTerms.js`, `DebtTermRow.svelte`, `Debts.svelte`,
  `debts.svelte.js`, `tabs.js`, `questOffers.svelte.js`,
  `QuestOffers.svelte`.
- DD1-DD3 <- `Journee.svelte`, `journee/debts.svelte.js`,
  `ServiceForm.svelte`, `DebtsPanel.svelte`, `quests.svelte.js`,
  `SettlementRecap.svelte`.
None needs judgment; none teaches an exception.

Passed (existing): `quests.py` (QA1 learns `DEBT_FORMS`, A),
`day_plan.py` (R2's expected types, R3's pairs, A), `day_narration.py`
(R15, A's two French details), `world_cascade.py` (two tables, A),
`single_canon_write.py` (A's tables in `[CANON_TABLES]`; B's
`write_debt`, `_close`, and the `quest` site moved to
`finish_settlement`), `fact_spine.py` (B: facts and participants through
`create_fact`/`attach_participants` only), `quest_rewards.py` (B's
settlement refactor keeps RC1-RC3), `prompt_version.py` (A's script writes
through `write_prompt_version`), `schema_version_agreement.py` (A),
`decisions_index.py` (each brief), `module_budget.py`,
`function_length.py` (A: the retired-type guard is its own helper,
`write_relation` stays under 80), `undefined_names.py`,
`frontend_build_fresh.py` (A, C, D), `creation_island.py` and
`page_contract.py` (C), `json_ui_boundary.py` (no JSON column added).

## Amendments

(none)
