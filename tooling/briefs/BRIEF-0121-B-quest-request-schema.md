<!-- slug: quest-request-schema -->
# BRIEF 0121-B — "v2.28, a quest request is a row -- quest_request, its writer, the cascade, the « Demandes de quête » metric and three deferrals (schema v2.28)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `301d178` (BRIEF-0121-A touches none of these files).

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.27"`; `world-engine-schema.md` line 3 `Current schema version: v2.27`.
- `src/world_engine/models/pipeline.py` -> `class ProposedMutation` (no CHECK in `__table_args__`), `class LoreEntry`, `class ConditionDraft`; no `class QuestRequest`.
- `src/world_engine/writes/worlds.py:83` -> `    "event_type_effect", "mutation_review", "mutation_review_change",` closing `_DIRECT_WORLD_SCOPED_DELETES`.
- `tooling/verify/checks/world_cascade.py:203` -> the `("mutation_review", {...` fixture row; `:166` `("pass_play", {"id": "pp-{w}"`; `:118` `("agenda_step", {"id": "ags-{w}"`.
- `tooling/verify/checks/json_ui_boundary.py` -> `JSON_COLUMN_ALLOWLIST` ending with `"ConditionDraft.model_calls",`.
- `src/world_engine/dashboard_metrics.py:258` -> `METRICS` whose last entry is `Metric("needs_attention", ...`.
- `src/world_engine/dashboard_deferrals.py:50` -> `DEFERRALS`; module constants `_T0111` ... `_T0119`, `_DECISIONS`, `_JSON_BOUNDARY`.
- `tooling/tickets/TICKET-0121-journee-quest-designer.md` exists (Nia deposits it with the lot) and holds each of the three anchors of C-03 exactly once.
- No `scripts/migrate_v2_28_*.py`, no `src/world_engine/writes/quest_requests.py`, no `src/world_engine/quest_requests.py`, no `tooling/verify/checks/quest_requests.py`.

## Facts carried

### R-05 — where a pipeline table lives, and how a migration moves the schema [M]
Opened: `models/pipeline.py:98-150` (`ProposedMutation`), `:418-445` (`LoreEntry`, `LoreEntryRow`), `:537-570` (`ConditionDraft`); `schema_version.py:15`; `scripts/migrate_v2_27_mutation_reviews.py:1-80`; `writes/worlds.py:64-84` (`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/canon_write_policy.txt:1-13` (`[CANON_TABLES]`); `world-engine-schema-changelog.md:14-24`.
Finding: non-canon pipeline tables live in `models/pipeline.py`; `EXPECTED_STATIC_SCHEMA_VERSION = "v2.27"`; a migration refuses an older database, is idempotent, runs one raw transaction with `foreign_keys` set, post-checks its touched tables with `PRAGMA foreign_key_check`, then moves `schema_meta`; a world's tables are deleted by name in `_DIRECT_WORLD_SCOPED_DELETES` (last line `"event_type_effect", "mutation_review", "mutation_review_change",`); pipeline tables are not in `[CANON_TABLES]`, so `single_canon_write.py` does not police their writers.
Consequence: `quest_request` is a pipeline table in `models/pipeline.py`, v2.28, added to the cascade list.

### R-06 — a proposal row [M]
Opened: `models/pipeline.py:98-150`; `tooling/verify/checks/json_ui_boundary.py:40-130`; `dashboard_deferrals.py:115-119`.
Finding: `proposed_mutation` has no CHECK on `mutation_type`, `source_type`, `status` or `proposed_by`; exactly one source (`pass_play_id`, `conversation_id`, or `tick_id`); `payload` JSON, NOT NULL; `target_id` free text; `ProposedMutation.payload` and `.original_payload` are listed exceptions of `json_ui_boundary.py`.
Finding (cont.): the exemption's justification reads « rendered readonly in the review queue; shape is the mutation type's contract, not a UI field. First structured UI consumer must relationalize » (`json_ui_boundary.py:44-47`); TICKET-0119's typed event card is already such a consumer, and TICKET-0115 registered that condition as reached, without a ticket: `dashboard_deferrals.py:115-119`, `Deferral("payload", "TICKET-0025", ..., _JSON_BOUNDARY, "First structured UI consumer must relationalize.", status="reached")` -- its anchor is that sentence of `json_ui_boundary.py`, found exactly once by DB1.
Consequence: `quest_offer_creation` needs no DDL; its payload carries the draft offer as JSON and the card edits it field by field -- a second structured consumer of a reached deferral, flagged to Nia as a drafting decision; the exemption's comment gains one line naming both cards, its anchor sentence untouched; `quest_request.change_history` (JSON, never rendered) needs its own listed exception.

### R-08 — the dashboard registries [M]
Opened: `dashboard_deferrals.py:1-50` (docstring, `Deferral`), `:50-110` (`DEFERRALS`); `dashboard_metrics.py:36-75` (`Scope`, `Row`, `Metric`), `:258-290` (`METRICS`, `compute_metrics`); `tooling/verify/checks/dashboard_registry.py:1-40` (DB1-DB5).
Finding: a `Deferral(code, ticket, deferred_fr, condition_fr, source, anchor, metric=None, status="open", follow_up=None)`; DB1 finds each `anchor` exactly once in its `source`; a `Metric(key, title, question, watches, dated, compute)` whose `compute(db, scope) -> (rows, note)`; DB2 forbids a JSON column and `text(` in `dashboard_metrics.py`; DB3 compares `dashboard(world=A)` to `EXPECTED` only for the metric keys `EXPECTED` names (`dashboard_registry.py:246-249`), and fails a dated metric that counts anything after tomorrow.
Consequence: B adds one metric and three deferrals, their anchors in the ticket file; DB3 needs no change (the new key is not in `EXPECTED`, and an empty fixture counts zero); the metric's numbers are asserted by B's own check.

### R-13 — the agenda tables and their writers [M]
Opened: `models/config.py:71-100` (`AgendaStep`: CHECK `status IN ('pending','active','completed','failed')`, one active step per agenda); `models/canon.py:779-797` (`Agenda`: CHECK `status IN ('active','paused','completed','failed','abandoned')`); `writes/goals_agendas.py:289-325` (`write_agenda_step`), `:326-360` (`write_agenda_step_status`), `:532-560` (`write_agenda_status`), `:610-655` (`write_day_plan`); `canon_write_policy.txt:106-107`.
Finding: both status writers append the previous state to `change_history`; they are allow-listed write sites; `write_day_plan` writes one agenda, its steps, their prerequisites.
Consequence: the inquiry day is a one-step plan written by `write_day_plan`; the inquiry band closes its step with `write_agenda_step_status(..., "completed", outcome="inquiry")` and, when no open step remains, the agenda with `write_agenda_status(..., "completed")`.

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.


## Contracts

### C-02 — `quest_request` (v2.28) and its writer
Produced by: BRIEF-0121-B   Consumed by: D, E, G
Table `quest_request` in `models/pipeline.py`:
`id` TEXT PK; `world_id` FK world NOT NULL; `character_id` FK entity NOT NULL; `pass_play_id` FK pass_play NOT NULL; `agenda_step_id` FK agenda_step NOT NULL; `trigger` TEXT NOT NULL; `declaration` TEXT NOT NULL; `subject` TEXT NULL; `status` TEXT NOT NULL DEFAULT `'new'`; `existence_answer` TEXT NULL; `creator_text` TEXT NULL; `existing_entity_id` FK entity NULL; `lore_entry_id` FK lore_entry NULL; `mutation_id` FK proposed_mutation NULL; `offer_id` FK quest_offer NULL; `note` TEXT NULL; `created_at`, `updated_at` (`_created_ts()`); `change_history` JSON NOT NULL DEFAULT `'[]'`.
CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped')`; `ck_quest_request_status` `status IN ('new','asking','writing_lore','proposed','covered','dropped')`; `ck_quest_request_answer` `existence_answer IS NULL OR existence_answer IN ('exists','absent','already')`.
Indexes: `idx_quest_request_world` (`world_id`, `created_at`); `idx_quest_request_step` UNIQUE (`agenda_step_id`): one request per step.
Constants in `writes/quest_requests.py`: `QUEST_REQUEST_TRIGGERS = ("route", "blocked", "dropped")`, `QUEST_REQUEST_STATUSES = ("new", "asking", "writing_lore", "proposed", "covered", "dropped")`, `EXISTENCE_ANSWERS = ("exists", "absent", "already")`, `QUEST_OFFER_CREATION = "quest_offer_creation"`, `DESIGNER_PRODUCER = "local_ai_quest_designer"`.
Writer:
- `open_request(db, *, world_id, character_id, pass_play_id, trigger, declaration, agenda_step_id) -> QuestRequest` -- `ValueError` on an unknown trigger, an empty declaration, a missing step; a step that already has a request returns that request unchanged (idempotent per step). Adds and flushes, never commits.
Reads in `src/world_engine/quest_requests.py`: `inquiry_step_ids(db, agenda_id) -> frozenset[str]` -- the `agenda_step_id`s of the requests on that agenda's steps whose trigger is `route` or `dropped`.
- `move_request(db, request, status, **fields) -> QuestRequest` -- appends `{status, updated_at, <every field it changes, before>}` to `change_history`, then sets `status`, `updated_at` and the given fields (only `subject`, `existence_answer`, `creator_text`, `existing_entity_id`, `lore_entry_id`, `mutation_id`, `offer_id`, `note`); `ValueError` on an unknown status, an unknown field, an answer outside `EXISTENCE_ANSWERS`. Never commits.
Status meanings: `new` -- waits for « Concevoir »; `asking` -- the subject is unknown, the existence question is shown; `writing_lore` -- answered `exists` or `absent`, the Lore panel is open for it; `proposed` -- a `quest_offer_creation` (`mutation_id`) exists; whether it was approved or rejected is that row's `status`, never a second column; `covered` -- an open offer already covers it (`offer_id`); `dropped` -- the creator set it aside. Re-design is allowed from `new`, `covered`, and `proposed` when its proposal is `rejected`; refused otherwise (C-12).

### C-03 — the « Demandes de quête » metric and three deferrals
Produced by: BRIEF-0121-B   Consumed by: (Suivi)
`dashboard_metrics.METRICS` gains, last, `Metric("quest_requests", "Demandes de quête", "D'où viennent les demandes de quête, et que deviennent-elles ?", ("P1", "S3", "D2"), True, _quest_requests)`. Rows, in this order: group `Origine` -- one row per trigger (`route` « Déclaration aiguillée », `blocked` « Étape bloquée », `dropped` « Savoir introuvable »), value = requests of that trigger, `of` = the requests in scope; plus one row « Journées aiguillées vers une quête », value = `route` requests, `of` = `pass_play` rows with `submitted_at` in scope and a non-null `agenda_id` (P1); group `Existence` -- one row per answer of `EXISTENCE_ANSWERS` (« Elle existe », « Elle n'existe pas », « Le lore le disait déjà ») (S3); group `Donneur` -- « Offres approuvées », value = requests whose proposal is `applied`; « Donneur créé après la proposition », value = those whose offer's giver entity has `created_at` after the proposal's `proposed_at`, `of` = the approved ones (D2). Relational columns only (DB2). Dated on `quest_request.created_at`.
`dashboard_deferrals.DEFERRALS` gains, last, three entries, `ticket="TICKET-0121"`, `source=_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"`, `metric="quest_requests"`:
- `D2` -- « Le concepteur invente un donneur, créé à l'approbation. » / « Nia crée souvent un PNJ juste pour donner une offre proposée. » / anchor `D2 (an invented giver; reactivation: the creator often creates a character just to give a proposed offer)`;
- `S3` -- « Une recherche du lore par le sens. » / « Des demandes où Nia répond que le lore le disait déjà. » / anchor `S3 (a search by meaning; reactivation: requests the creator answers « the lore already says it »)`;
- `P1` -- « Revoir l'outil de plan en plan global. » / « La part des journées aiguillées vers une quête le demande. » / anchor `P1 (the plan tool reworked; reactivation: the share of days routed to a quest asks for it)`.
Error and empty cases: no request in scope -> every row with value 0 (rows are always emitted).


## Context

L1: each quest request -- a day routed to a quest, a step blocked, a
knowledge nobody can anchor -- is a relational row the creator works
through: designed, asked about, written into the lore, proposed, set aside.
This brief lays the table and its writer, and the dashboard's way to watch
the three deferrals Nia asked to follow (D2, S3, P1). Nothing writes a
request yet: D opens them, E designs them, G shows them.

## Scope IN

1. `models/pipeline.py`: `class QuestRequest(SQLModel, table=True)` exactly as C-02 (table name, columns, types, defaults with `server_default`, FKs, the three CHECKs by name, the two indexes -- the unique one plain, `agenda_step_id` being NOT NULL), placed after `ConditionDraft`, with a header comment in the file's style (v2.28, TICKET-0121, BRIEF-0121-B, L1; « a status is one of `QUEST_REQUEST_STATUSES`; a proposal's fate is its `proposed_mutation.status`, never a second column »). Export it from `models/__init__.py` beside `ConditionDraft`.
2. `scripts/migrate_v2_28_quest_requests.py`, R-05's shape verbatim in kind: refuses a database older than v2.27; idempotent (the table and each index checked before creating); `CreateTable`/`CreateIndex` from the model (never hand-written DDL); one raw transaction with `foreign_keys` set; post-check: the table exists with its CHECKs and indexes, `PRAGMA foreign_key_check(quest_request)` empty; then `schema_meta.static_version = 'v2.28'`; prints « Migration v2.28 applied » (or « already at v2.28 »). Env guard as in v2.27's script.
3. `schema_version.py`: `"v2.28"`. `world-engine-schema.md`: header v2.28; a section `### quest_request` (the name in backticks, the other sections' style) after the `condition_draft` section -- what a row is, its CREATE TABLE and indexes as the model generates them, the statuses and triggers, « written only by `writes/quest_requests.py` ». `world-engine-schema-changelog.md`: a `- **v2.28** — TICKET-0121, BRIEF-0121-B: ...` entry at the top of the list, in the v2.27 entry's style.
4. `src/world_engine/writes/quest_requests.py` (new): the constants and `open_request`, `move_request` of C-02, docstring first sentence for FILE_MAP. `open_request` flushes so the caller can read the row's id; neither commits (INV-18's posture).
5. `src/world_engine/quest_requests.py` (new, reads): `inquiry_step_ids(db, agenda_id)` of C-02.
6. `writes/worlds.py`: add `"quest_request"` to `_DIRECT_WORLD_SCOPED_DELETES` (last line). `tooling/verify/checks/world_cascade.py`: one `_FIXTURE` row `("quest_request", {"id": "qr-{w}", "world_id": "{w}", "character_id": "{w}-char", "pass_play_id": "pp-{w}", "agenda_step_id": "ags-{w}", "trigger": "route", "declaration": "d", "status": "new"})`, after the `mutation_review_change` row.
7. `tooling/verify/checks/json_ui_boundary.py`: `"QuestRequest.change_history"` in `JSON_COLUMN_ALLOWLIST`, under a comment « TICKET-0121 (BRIEF-0121-B, L1): a request's former states -- an audit snapshot, never rendered in any UI surface (the change_history posture). ».
8. `dashboard_metrics.py`: `_quest_requests(db, scope)` and its `METRICS` entry, last, as C-03 -- relational columns only (`QuestRequest`, `ProposedMutation.status`/`proposed_at`, `QuestOffer.giver_entity_id`, `Entity.created_at`, `PassPlay.submitted_at`/`agenda_id`); every row emitted even at zero; the `note` « Ce que deviennent les demandes de quête nées des journées (P1, S3, D2). ».
9. `dashboard_deferrals.py`: `_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"` and the three entries of C-03, last.
10. New check `tooling/verify/checks/quest_requests.py` (R-24's `_fresh_db` and `create_all`, rows through the real writers):
    - **QR1** `QuestRequest`'s columns, CHECK names and index names equal C-02's; `EXPECTED_STATIC_SCHEMA_VERSION == "v2.28"`; the migration script exists, refuses an older version (its `_PREVIOUS_VERSION == "v2.27"`).
    - **QR2** `open_request` refuses an unknown trigger, an empty declaration, a missing step; a second call for the same step returns the same row (one row in the table).
    - **QR3** `move_request` appends one `change_history` entry per call holding the former status and every field it changed; refuses an unknown status, an unknown field, an answer outside `EXISTENCE_ANSWERS`.
    - **QR4** a raw INSERT with `status='done'`, then one with `trigger='other'`, each raises `IntegrityError` (the CHECKs hold).
    - **QR5** `inquiry_step_ids` returns the steps of `route` and `dropped` requests of that agenda only (a `blocked` one and another agenda's are absent).
    - **QR6** `compute_metrics` over a fixture with one request of each trigger, one answered `already`, one proposal `applied` whose offer's giver was created after the proposal: the `quest_requests` rows equal a literal expected dict (every group of C-03), and a world with none gives the same labels at 0.
    - **QR7** the three deferrals `D2`, `S3`, `P1` of `TICKET-0121` exist with `metric == "quest_requests"`.
11. `tooling/standards/ARCHITECTURE_DECISIONS.md`: an entry above the footer, `## A QUEST REQUEST IS A ROW THE CREATOR WORKS THROUGH (TICKET-0121) -- quest_request (BRIEF-0121-b, schema v2.28)`: L1, the statuses and why a proposal's fate is not a column, the deferrals watched. Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.

## Scope OUT

- Opening a request (D), designing one and its routes (E), the panel (G).
- The producer entry in `PRODUCERS` (E writes the first `proposed_by` of it).
- Any `quest_request` reader in a prompt or a player surface: none exists in this ticket.
- Every later brief of this lot.

## Invariants to defend

- **INV-60** -- the boot guard: the constant, the doc header and `schema_meta` move together, in this commit; `schema_version_agreement.py` checks the first two.
- **INV-20** -- every visible field relational; `change_history` listed as never rendered.
- **INV-12** -- no new hard delete beyond the existing world cascade, which now names the table.
- **INV-18** -- the writer never commits.

## Decision rights

STOP:
- an anchor does not hold;
- the ticket file is absent or an anchor of C-03 is not in it exactly once (DB1 would go red: the ticket text is Nia's, never edited here);
- `world_cascade.py` W1 requires something other than the list entry and the fixture row.
ADAPT:
- the schema doc's section order differs from « after `condition_draft` »: place the section beside the other pipeline tables, report.
- `create_all` does not create the table: export the model from `models/__init__.py` where `ConditionDraft` is exported, report.
REPORT-ONLY:
- any production fact the migration's post-check prints.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `quest_requests.py` PASS (QR1-QR7); `world_cascade.py`, `json_ui_boundary.py`, `schema_version_agreement.py`, `dashboard_registry.py`, `decisions_index.py`, `file_map.py` PASS.
- [ ] On a scratch copy of a v2.27 test database: `migrate_v2_28_quest_requests.py` prints « Migration v2.28 applied »; a second run prints that it is already done; the cockpit boots.
- [ ] Named mutations, each red then reverted: drop the `ck_quest_request_status` CHECK (QR4); make `open_request` insert a second row for the same step (QR2); count `blocked` in `inquiry_step_ids` (QR5); set the `D2` deferral's `metric` to None (QR7).
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `world-engine-schema.md`, `world-engine-schema-changelog.md` (v2.28), `ARCHITECTURE_DECISIONS.md`, regenerated `DECISIONS_INDEX.md` and `FILE_MAP.md`.
