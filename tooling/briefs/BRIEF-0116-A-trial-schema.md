<!-- slug: trial-schema -->
# BRIEF 0116-A — "v2.29: the trial columns, the rank currency's CHECKs, the trial request's shape"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.28"`.
- `src/world_engine/models/config.py:240-256` -> `SkillRank` declares exactly `id, world_id, rank, label, points_to_next, updated_at`; CHECKs `ck_skill_rank_rank`, `ck_skill_rank_points`; `:23` imports `text`.
- `src/world_engine/models/canon.py:591-612` -> `SkillSystem` ends `points_to_rank_5: Optional[int] = None`, then `created_at`, `updated_at`; `:617-660` -> `SkillDefinition`'s `points_to_rank_5` (`:653`) is followed by the `requires_master` comment and field (`:654-656`).
- `src/world_engine/models/quests.py:116` -> `QUEST_TERM_CURRENCIES: tuple[str, ...] = ("money", "item", "relation", "fact", "skill")`; `:120-125` `QUEST_TERM_SHAPE_CHECK` of four clauses; `:127` `QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill')"`.
- `src/world_engine/models/pipeline.py:591-630` -> `QuestRequest` with `pass_play_id` and `agenda_step_id` NOT NULL, CHECKs `ck_quest_request_trigger` / `_status` / `_answer`, indexes `idx_quest_request_world`, `idx_quest_request_step` (unique).
- `tooling/verify/checks/skill_progression.py:201` -> `{"id", "world_id", "rank", "label", "points_to_next", "updated_at"}`.
- `tooling/verify/checks/skill_system_shape.py:29-35` -> `EXPECTED_SKILL_SYSTEM_COLUMNS` (six base columns plus the five `points_to_rank_<n>`).
- `tooling/verify/checks/quest_requests.py:46-50` -> `COLUMNS` (19 names), `CHECKS` (3), `INDEXES` (2).
- `world-engine-schema.md:3` -> `Current schema version: v2.28`; `world-engine-schema-changelog.md:14` -> the v2.28 entry is the newest.

## Facts carried

### R-01 — the ladder and its cascade [M]
Opened: `src/world_engine/skill_ranks.py:1-111` (docstring, `RANKS`, `MAX_RANK = 5`, `RankStep` at `:46-50`, `default_ladder` `:60-65`, `world_ladder` `:68-79`, `points_to_next` `:82-95`, `skill_owners` `:98-105`, `skill_points_to_next` `:108-111`); `src/world_engine/models/config.py:240-256` (`SkillRank`); `src/world_engine/models/canon.py:580-612` (`RANK_POINTS_CHECK`, `SkillSystem`), `:617-660` (`SkillDefinition`).
Finding: `RankStep(rank, label, points_to_next)` is a frozen dataclass; `world_ladder` reads the world's `skill_rank` rows over `default_ladder()` and never writes; `points_to_next(rank, ladder, *, system, definition)` takes the definition's `points_to_rank_<rank+1>`, else the system's, else the ladder's, None at `MAX_RANK`; `RANK_POINTS_COLUMNS[rank]` is `points_to_rank_<rank+1>` (index = rank left). `skill_rank` declares `id, world_id, rank, label, points_to_next, updated_at`, CHECKs `ck_skill_rank_rank`, `ck_skill_rank_points`, unique `idx_skill_rank_world_rank`. `SkillSystem` and `SkillDefinition` declare `points_to_rank_1..5: Optional[int] = None` and one `ck_*_rank_points` CHECK each; `SkillDefinition.requires_master` follows them. `models/config.py:23` imports `text` from sqlalchemy. `skill_ranks.py` imports only `models`.
Consequence: the trial flag mirrors the points exactly -- `skill_rank.trial_to_next` (index = rank left), `trial_to_rank_<n>` on the system and the definition, the most specific non-null value winning (B1). No CHECK is added on `skill_rank` (A1 of `skill_progression.py` pins its CHECK set, R-17); the writer refuses a trial at rank 5.

### R-05 — how a migration moves the schema [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py:1-215` (raw DBAPI transaction, `PRAGMA foreign_keys=OFF` and `legacy_alter_table=ON` before `BEGIN`, `_rebuild` = drop the table's indexes, rename to `<table>_old`, create from the model, copy named columns, drop the old; post-checks; `_converge_schema_meta`); `scripts/migrate_v2_16_npc_skills.py:1-35`, `:103-106` (`ALTER TABLE skill_definition ADD COLUMN requires_master BOOLEAN NOT NULL DEFAULT 0`); `scripts/migrate_v2_28_quest_requests.py:1-25`, `:55`, `:115-118`; `src/world_engine/schema_version.py:15` (`EXPECTED_STATIC_SCHEMA_VERSION = "v2.28"`); `world-engine-schema.md:3`; `world-engine-schema-changelog.md:14-21`.
Finding: SQLite cannot add a table CHECK nor change a column's nullability in place: such a table is rebuilt from its model; a nullable or defaulted column is added with `ADD COLUMN`. A migration refuses an older database, is idempotent, post-checks before moving `schema_meta`, and lists a dangling reference outside its own tables without stopping (AMENDMENT-0107-01). v2.28's post-check requires its three CHECK names present (a subset), not an exact set. No model declares a foreign key to `quest_request`, `quest_offer_term` or `quest_term` (`grep` of `models/`, empty).
Consequence: v2.29 adds eleven columns with `ADD COLUMN` and rebuilds `quest_offer_term`, `quest_term` and `quest_request` from their models, in one raw transaction.

### R-06 — the term vocabulary [M]
Opened: `src/world_engine/models/quests.py:111-184` (`QUEST_TERM_DIRECTIONS`, `QUEST_TERM_CURRENCIES = ("money", "item", "relation", "fact", "skill")`, `QUEST_TERM_SHAPE_CHECK`, `QUEST_TERM_DIRECTION_CHECK`, `QUEST_TERM_CURRENCY_CHECK`, `QuestOfferTerm`, `QuestTerm`), `:290-308` (`DebtTerm`, CHECK `ck_debt_term_currency` `currency IN ('money','item','fact','skill')`, its own literal); `src/world_engine/writes/quest_terms.py:42-138`; `src/world_engine/cockpit/quest_offer_save.py:47-55`, `:79`.
Finding: both term tables carry the same three CHECK texts, built from the three module literals; the currency CHECK is a literal, not derived from the tuple; `clean_term` refuses a currency outside the tuple before any write. A debt's terms have their own CHECK: a `rank` can never be owed.
Consequence: A widens the two CHECK literals (the schema allows a `rank` row); C widens the tuple and gives `clean_term` the rank's rules.

### R-10 — the quest request [M]
Opened: `src/world_engine/models/pipeline.py:591-630` (`QuestRequest`); `src/world_engine/writes/quest_requests.py:1-92`; `src/world_engine/quest_requests.py:1-50`; `src/world_engine/dashboard_metrics.py:259-296`; `src/world_engine/writes/worlds.py:84` (`"quest_request",` in the cascade).
Finding: `pass_play_id` and `agenda_step_id` are NOT NULL; `trigger IN ('route','blocked','dropped')`; one request per step (`idx_quest_request_step` unique). `open_request` refuses a trigger outside `QUEST_REQUEST_TRIGGERS`.
Consequence: the table is rebuilt (A); a `trial` request has no day and no step, a skill and a target rank, and its own writer (D).

### R-17 — the existing checks that read what this lot changes [M] (the lines this brief needs)
- `skill_progression.py:201-204` (A1: `skill_rank` columns exactly `{id, world_id, rank, label, points_to_next, updated_at}`; its CHECK set);
- `skill_system_shape.py:29-35` (`EXPECTED_SKILL_SYSTEM_COLUMNS`, exact);
- `quest_requests.py:46-50` (`COLUMNS` in order, `CHECKS`, `INDEXES`, exact), `:100-102` (one unique index, `idx_quest_request_step`);
- `quest_rewards.py:198-201` (RA1: the two tables' CHECK texts equal);
- `npc_skills.py:100-125`, `:173-174`, `:240-270`, `:598-605` (A2 recreates `skill_definition` in v2.15 DDL, runs v2.16 -- `ADD COLUMN` --, compares the migrated shapes with the models'; A3+ write into that same file);
- `world_cascade.py:207-209`, `:222-225`, `:111` (raw fixture rows of `quest_request` -- `route`, a day and a step --, the two term tables -- `item`, `money` --, `skill_rank` without `trial_to_next`).

### R-19 — the time a check may take [M]
Opened: `tooling/verify/checks/corpus_gate.py:53-62` (`TIMEOUT_SECONDS = 15`); local runs at `246e89b`: `skill_progression.py` 9.4 s, `quest_rewards.py` 9.8 s, `debts.py` 9.1 s, `quests.py` 8.7 s.
Consequence: this brief's rules live in a new check, `rank_trial_schema.py`; the three checks it edits gain no rule, only their pinned sets.

### R-22 — the v2.28 shape of the six tables v2.29 changes [M]
Opened: `CreateTable`/`CreateIndex` of the six models, compiled on the SQLite dialect at `246e89b`. The DDL is pasted verbatim in Scope IN item 8 (TS3's fixture).

## Contracts

### C-01 — schema v2.29
Produced by: BRIEF-0116-A   Consumed by: B, C, D, E
- `skill_rank.trial_to_next` BOOLEAN NOT NULL DEFAULT 0 -- model `trial_to_next: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})`, after `points_to_next`. No CHECK.
- `skill_system.trial_to_rank_1` .. `trial_to_rank_5`, and the same five on `skill_definition`: BOOLEAN NULL -- model `trial_to_rank_<n>: Optional[bool] = None`, right after `points_to_rank_5`. NULL inherits; `trial_to_rank_<n>` says whether reaching rank n asks a trial. No CHECK.
- `QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill','rank')"`.
- `QUEST_TERM_SHAPE_CHECK` = its current four clauses, then ` AND (currency <> 'rank' OR (direction = 'reward' AND skill_key IS NOT NULL AND amount BETWEEN 1 AND 5))`.
- `quest_request`: `pass_play_id` and `agenda_step_id` nullable; `skill_key` TEXT NULL and `target_rank` INTEGER NULL after `note`; column order `id, world_id, character_id, pass_play_id, agenda_step_id, trigger, declaration, subject, status, existence_answer, creator_text, existing_entity_id, lore_entry_id, mutation_id, offer_id, note, skill_key, target_rank, created_at, updated_at, change_history`. CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped','trial')`; `ck_quest_request_status`, `ck_quest_request_answer` unchanged; `ck_quest_request_origin` `(trigger = 'trial' AND skill_key IS NOT NULL AND target_rank BETWEEN 1 AND 5 AND pass_play_id IS NULL AND agenda_step_id IS NULL) OR (trigger <> 'trial' AND skill_key IS NULL AND target_rank IS NULL AND pass_play_id IS NOT NULL AND agenda_step_id IS NOT NULL)`. Indexes: `idx_quest_request_world`, `idx_quest_request_step` (unique, unchanged), `idx_quest_request_trial` (`world_id`, `skill_key`, `target_rank`), not unique.
- `EXPECTED_STATIC_SCHEMA_VERSION = "v2.29"`; `scripts/migrate_v2_29_rank_trials.py` (`_PREVIOUS_VERSION = "v2.28"`).
- `QUEST_TERM_CURRENCIES` and `QUEST_REQUEST_TRIGGERS` are NOT changed by A (C and D).
Error and empty cases: a `rank` cost, a `rank` with no skill or a rank outside 1-5, a `trial` request with a step, a step request with a skill -- `IntegrityError` at the database.

## Context

TICKET-0116 makes rank trials quests. This first step lays the storage only:
where a world, a system or a skill says that leaving a rank asks a trial,
the room in the term tables for a `rank` reward, and the room in
`quest_request` for a request born of a skill rather than a day. No code
reads or writes the new columns yet (B to E do); nothing changes for any
existing world.

## Scope IN

1. `src/world_engine/models/config.py`, `SkillRank`: after `points_to_next: Optional[int] = None`, add
   ```python
   # TICKET-0116 (BRIEF-0116-A, B1): leaving this rank asks a trial -- a quest
   # whose reward is the next rank. False by default: no world asks one.
   trial_to_next: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
   ```
   No new CHECK.
2. `src/world_engine/models/canon.py`, `SkillSystem` and `SkillDefinition`: right after each `points_to_rank_5: Optional[int] = None`, add one comment line and five fields:
   ```python
   # Whether reaching rank n asks a trial (v2.29, TICKET-0116, B1); NULL inherits.
   trial_to_rank_1: Optional[bool] = None
   trial_to_rank_2: Optional[bool] = None
   trial_to_rank_3: Optional[bool] = None
   trial_to_rank_4: Optional[bool] = None
   trial_to_rank_5: Optional[bool] = None
   ```
   No new CHECK. The file stays under 1000 lines (946 today).
3. `src/world_engine/models/quests.py`: `QUEST_TERM_SHAPE_CHECK` becomes its four current clauses followed by
   `"AND (currency <> 'rank' OR (direction = 'reward' AND skill_key IS NOT NULL AND amount BETWEEN 1 AND 5))"`
   (the previous last clause gains a trailing space, as the others have); `QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill','rank')"`. The comment above the shape CHECK gains: `# TICKET-0116 (BRIEF-0116-A, D2): a rank is a reward only, naming a skill and the rank it gives.` `QUEST_TERM_CURRENCIES` is NOT changed here. **Only `QUEST_TERM_SHAPE_CHECK` (`:120-125`) changes: `DEBT_TERM_SHAPE_CHECK` (`:285-290`) ends with the same literal line `"AND (currency <> 'skill' OR skill_key IS NOT NULL)"` and is NOT touched** -- `debt_term` has no `direction` column, and a replace-all of that line breaks every `create_all` (measured on a prototype of this brief).
4. `src/world_engine/models/pipeline.py`, `QuestRequest` -- exactly C-01: `pass_play_id: Optional[str] = Field(default=None, foreign_key="pass_play.id")`, `agenda_step_id: Optional[str] = Field(default=None, foreign_key="agenda_step.id")`; after `note`, `skill_key: Optional[str] = None` and `target_rank: Optional[int] = None`, under the comment `# TICKET-0116 (BRIEF-0116-A, F1-b): a trial request names the skill (a base domain or a skill definition id) and the rank it waits for; a step request names neither.`; `ck_quest_request_trigger`'s text with `'trial'`; a new `CheckConstraint(<C-01's origin text>, name="ck_quest_request_origin")`; `Index("idx_quest_request_trial", "world_id", "skill_key", "target_rank")`. The table's comment block above the class gains one sentence: a `trial` request has no day and no step.
5. `src/world_engine/schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.29"`.
6. `scripts/migrate_v2_29_rank_trials.py`, on the `migrate_v2_15_skill_ranks.py` skeleton (its env guard, `_version_key`, `_refuse_if_behind`, `_create_from_model`, `_rebuild`, `_converge_schema_meta`, `main`), with the docstring stating what follows:
   - `_PREVIOUS_VERSION = "v2.28"`; refuses below it, before any change.
   - DDL in ONE raw transaction (`PRAGMA foreign_keys=OFF`, `legacy_alter_table=ON`, `BEGIN` ... `COMMIT`, then both pragmas back):
     a. `ALTER TABLE skill_rank ADD COLUMN trial_to_next BOOLEAN NOT NULL DEFAULT 0` when the column is missing;
     b. for `skill_system` then `skill_definition`, for `n` in 1-5: `ALTER TABLE <t> ADD COLUMN trial_to_rank_<n> BOOLEAN` when missing (the five names as a literal tuple of the script -- `skill_ranks` has no such constant yet);
     c. rebuild `quest_offer_term` then `quest_term` when the table's `sqlite_master.sql` does not contain `'rank'`, copying `id, world_id, offer_id, term_order, direction, currency, counterparty_entity_id, item_id, fact_id, skill_key, amount, level` (`quest_id` in place of `offer_id` for `quest_term`);
     d. rebuild `quest_request` when it has no `skill_key` column, copying its 19 v2.28 columns (`id, world_id, character_id, pass_play_id, agenda_step_id, "trigger", declaration, subject, status, existence_answer, creator_text, existing_entity_id, lore_entry_id, mutation_id, offer_id, note, created_at, updated_at, change_history` -- `trigger` double-quoted in the SQL).
   - Post-checks, before `schema_meta` moves, each a `SystemExit` naming what failed: the row counts of the three rebuilt tables unchanged; the eleven columns present; every `skill_rank.trial_to_next` is 0; the rebuilt tables carry their models' CHECK names (`ck_quest_offer_term_direction/_currency/_shape`, `ck_quest_term_direction/_currency/_shape`, `ck_quest_request_trigger/_status/_answer/_origin`) and their indexes (`idx_quest_offer_term_offer`, `idx_quest_term_quest`, `idx_quest_request_world`, `idx_quest_request_step` unique, `idx_quest_request_trial`); `PRAGMA foreign_key_check` of the six tables (`skill_rank`, `skill_system`, `skill_definition`, `quest_offer_term`, `quest_term`, `quest_request`) is compared with the same check taken before the DDL: a row dangling after and not before fails; one dangling before is printed as a note and does not stop the migration (AMENDMENT-0107-01).
   - Idempotent: a second run applies nothing and prints « DDL already applied. ».
   - Prints `Migration v2.29 applied.` last. Writes no data row.
7. `world-engine-schema.md`: header `Current schema version: v2.29`; in `### skill_rank`, the column `trial_to_next   BOOLEAN NOT NULL DEFAULT 0,  -- leaving this rank asks a trial (v2.29)` after `points_to_next` and one sentence in its prose: a skill system's or definition's `trial_to_rank_<n>` overrides it, the most specific value winning, and a world asks no trial by default; in `### skill_system` and `### skill_definition`, after `points_to_rank_5`, the five lines `trial_to_rank_<n>  BOOLEAN,` with the comment `-- reaching rank n asks a trial (v2.29); NULL = inherited`; in `### quest_offer_term`, the two CHECK texts of item 3 and one sentence: a `rank` term is a reward only -- `skill_key` names the skill, `amount` the rank it gives (1-5); `quest_term` (« same columns and CHECKs ») needs no other change; in `### quest_request`, the DDL of C-01 (nullable `pass_play_id`/`agenda_step_id`, `skill_key`, `target_rank`, the four CHECKs, `idx_quest_request_trial`) and one paragraph: a `trial` request (v2.29) is born of a player character's skill ready for a rank that asks a trial -- no day, no step, its `skill_key` and `target_rank` instead; `ck_quest_request_origin` ties each trigger to its columns.
8. `tooling/verify/checks/rank_trial_schema.py` (new; `rules/verify-checks.md`; the `quest_requests.py` fixture idiom: `_fresh_db()` before any `world_engine` import, `FAILURES`, `fail()`, one `PASS:` line), docstring holding these rules:
   - **TS1** -- shapes (import). `SkillRank.trial_to_next` is a NOT NULL boolean with server default `0`; `SkillSystem` and `SkillDefinition` each declare `trial_to_rank_1..5`, nullable; `QUEST_TERM_CURRENCY_CHECK` and `QUEST_TERM_SHAPE_CHECK` equal C-01's texts exactly; `QuestOfferTerm` and `QuestTerm` carry them under their `ck_*_currency`/`ck_*_shape` names; `QuestRequest`'s columns are C-01's tuple in order, `pass_play_id` and `agenda_step_id` nullable, its CHECK names `{answer, origin, status, trigger}`, `ck_quest_request_origin`'s text is C-01's, its indexes `{idx_quest_request_step, idx_quest_request_trial, idx_quest_request_world}` with only `idx_quest_request_step` unique; `EXPECTED_STATIC_SCHEMA_VERSION == "v2.29"`; the migration exists and `_PREVIOUS_VERSION == "v2.28"`.
   - **TS2** -- the CHECKs hold (fresh `create_all`, raw INSERTs, parents inserted raw): a `quest_offer_term` reward `rank` with `skill_key='agility'`, `amount=2` inserts; a `rank` cost, a `rank` with `amount` 6, a `rank` with `skill_key` NULL each raise `IntegrityError`; a `quest_request` `trial` with `skill_key`, `target_rank=3`, no day, no step inserts; a `trial` with a step, a `trial` with `target_rank` 0, a `route` with no step, a `route` with a `skill_key` each raise `IntegrityError`.
   - **TS3** -- the migration, run as a subprocess (`WORLD_ENGINE_DATABASE_URL` the fixture, `WORLD_ENGINE_ENV=test`) on a v2.28-shaped file: `create_all`, then the six tables dropped and recreated in their v2.28 DDL, verbatim below; one row in each (a `skill_rank` at rank 2; a system; a definition; an offer term `money` 5; a quest term `money` 3; a `route` request whose `pass_play_id` names no row -- a dangling reference that predates the migration), parents inserted raw:
     a. at `schema_meta` v2.27 it exits non-zero and changes nothing (the six tables' `PRAGMA table_info` unchanged);
     b. at v2.28 it exits zero; the eleven columns exist; the six rows are kept with their ids; `trial_to_next` is 0; the rebuilt tables carry the model's CHECK names and indexes; its output names the dangling `quest_request` row as a note; `schema_meta` is v2.29;
     c. a second run exits zero, prints « DDL already applied. » and changes no row.
   The v2.28 DDL (compiled from the models at `246e89b`):
   ```sql
   CREATE TABLE skill_rank (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	rank INTEGER NOT NULL,
   	label VARCHAR NOT NULL,
   	points_to_next INTEGER,
   	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_skill_rank_rank CHECK (rank BETWEEN 0 AND 5),
   	CONSTRAINT ck_skill_rank_points CHECK ((rank = 5 AND points_to_next IS NULL) OR (rank < 5 AND points_to_next >= 1)),
   	FOREIGN KEY(world_id) REFERENCES world (id)
   );
   CREATE UNIQUE INDEX idx_skill_rank_world_rank ON skill_rank (world_id, rank);

   CREATE TABLE skill_system (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	name VARCHAR NOT NULL,
   	description VARCHAR,
   	points_to_rank_1 INTEGER,
   	points_to_rank_2 INTEGER,
   	points_to_rank_3 INTEGER,
   	points_to_rank_4 INTEGER,
   	points_to_rank_5 INTEGER,
   	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_skill_system_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
   	FOREIGN KEY(world_id) REFERENCES world (id)
   );
   CREATE INDEX idx_skill_system_world ON skill_system (world_id);
   CREATE UNIQUE INDEX idx_skill_system_world_name ON skill_system (world_id, name);

   CREATE TABLE skill_definition (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	name VARCHAR NOT NULL,
   	base_domain VARCHAR NOT NULL,
   	system_id VARCHAR,
   	description VARCHAR,
   	points_to_rank_1 INTEGER,
   	points_to_rank_2 INTEGER,
   	points_to_rank_3 INTEGER,
   	points_to_rank_4 INTEGER,
   	points_to_rank_5 INTEGER,
   	requires_master BOOLEAN DEFAULT 0 NOT NULL,
   	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_skill_definition_base_domain CHECK (base_domain IN ('physical','agility','perception','composure')),
   	CONSTRAINT ck_skill_definition_rank_points CHECK ((points_to_rank_1 IS NULL OR points_to_rank_1 >= 1) AND (points_to_rank_2 IS NULL OR points_to_rank_2 >= 1) AND (points_to_rank_3 IS NULL OR points_to_rank_3 >= 1) AND (points_to_rank_4 IS NULL OR points_to_rank_4 >= 1) AND (points_to_rank_5 IS NULL OR points_to_rank_5 >= 1)),
   	FOREIGN KEY(world_id) REFERENCES world (id),
   	FOREIGN KEY(system_id) REFERENCES skill_system (id) ON DELETE RESTRICT
   );
   CREATE INDEX idx_skill_definition_system ON skill_definition (system_id);
   CREATE INDEX idx_skill_definition_world ON skill_definition (world_id);
   CREATE UNIQUE INDEX idx_skill_definition_world_name ON skill_definition (world_id, name);

   CREATE TABLE quest_offer_term (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	offer_id VARCHAR NOT NULL,
   	term_order INTEGER NOT NULL,
   	direction VARCHAR NOT NULL,
   	currency VARCHAR NOT NULL,
   	counterparty_entity_id VARCHAR,
   	item_id VARCHAR,
   	fact_id VARCHAR,
   	skill_key VARCHAR,
   	amount INTEGER,
   	level VARCHAR,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_quest_offer_term_direction CHECK (direction IN ('cost','reward')),
   	CONSTRAINT ck_quest_offer_term_currency CHECK (currency IN ('money','item','relation','fact','skill')),
   	CONSTRAINT ck_quest_offer_term_shape CHECK ((currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)),
   	FOREIGN KEY(world_id) REFERENCES world (id),
   	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
   	FOREIGN KEY(counterparty_entity_id) REFERENCES entity (id),
   	FOREIGN KEY(item_id) REFERENCES item (id),
   	FOREIGN KEY(fact_id) REFERENCES fact (id)
   );
   CREATE INDEX idx_quest_offer_term_offer ON quest_offer_term (offer_id);

   CREATE TABLE quest_term (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	quest_id VARCHAR NOT NULL,
   	term_order INTEGER NOT NULL,
   	direction VARCHAR NOT NULL,
   	currency VARCHAR NOT NULL,
   	counterparty_entity_id VARCHAR,
   	item_id VARCHAR,
   	fact_id VARCHAR,
   	skill_key VARCHAR,
   	amount INTEGER,
   	level VARCHAR,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_quest_term_direction CHECK (direction IN ('cost','reward')),
   	CONSTRAINT ck_quest_term_currency CHECK (currency IN ('money','item','relation','fact','skill')),
   	CONSTRAINT ck_quest_term_shape CHECK ((currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)),
   	FOREIGN KEY(world_id) REFERENCES world (id),
   	FOREIGN KEY(quest_id) REFERENCES quest (id),
   	FOREIGN KEY(counterparty_entity_id) REFERENCES entity (id),
   	FOREIGN KEY(item_id) REFERENCES item (id),
   	FOREIGN KEY(fact_id) REFERENCES fact (id)
   );
   CREATE INDEX idx_quest_term_quest ON quest_term (quest_id);

   CREATE TABLE quest_request (
   	id VARCHAR NOT NULL,
   	world_id VARCHAR NOT NULL,
   	character_id VARCHAR NOT NULL,
   	pass_play_id VARCHAR NOT NULL,
   	agenda_step_id VARCHAR NOT NULL,
   	"trigger" VARCHAR NOT NULL,
   	declaration VARCHAR NOT NULL,
   	subject VARCHAR,
   	status VARCHAR DEFAULT 'new' NOT NULL,
   	existence_answer VARCHAR,
   	creator_text VARCHAR,
   	existing_entity_id VARCHAR,
   	lore_entry_id VARCHAR,
   	mutation_id VARCHAR,
   	offer_id VARCHAR,
   	note VARCHAR,
   	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
   	change_history JSON DEFAULT '[]' NOT NULL,
   	PRIMARY KEY (id),
   	CONSTRAINT ck_quest_request_trigger CHECK (trigger IN ('route','blocked','dropped')),
   	CONSTRAINT ck_quest_request_status CHECK (status IN ('new','asking','writing_lore','proposed','covered','dropped')),
   	CONSTRAINT ck_quest_request_answer CHECK (existence_answer IS NULL OR existence_answer IN ('exists','absent','already')),
   	FOREIGN KEY(world_id) REFERENCES world (id),
   	FOREIGN KEY(character_id) REFERENCES entity (id),
   	FOREIGN KEY(pass_play_id) REFERENCES pass_play (id),
   	FOREIGN KEY(agenda_step_id) REFERENCES agenda_step (id),
   	FOREIGN KEY(existing_entity_id) REFERENCES entity (id),
   	FOREIGN KEY(lore_entry_id) REFERENCES lore_entry (id),
   	FOREIGN KEY(mutation_id) REFERENCES proposed_mutation (id),
   	FOREIGN KEY(offer_id) REFERENCES quest_offer (id)
   );
   CREATE UNIQUE INDEX idx_quest_request_step ON quest_request (agenda_step_id);
   CREATE INDEX idx_quest_request_world ON quest_request (world_id, created_at);
   ```
9. Four existing checks follow the shapes (R-17), each docstring line updated with the same words:
   - `tooling/verify/checks/skill_progression.py:201`: the set gains `"trial_to_next"`; A1's docstring reads `id, world_id, rank, label, points_to_next, trial_to_next (v2.29), updated_at`. Its CHECK set (`:204`) is unchanged.
   - `tooling/verify/checks/skill_system_shape.py`: `EXPECTED_SKILL_SYSTEM_COLUMNS` gains the five `trial_to_rank_<n>` under the comment `# TICKET-0116 (BRIEF-0116-A, v2.29): whether reaching each rank asks a trial.`; assertion 1 of the docstring names them.
   - `tooling/verify/checks/npc_skills.py`: its A2 fixture recreates `skill_definition` in its v2.15 DDL and runs v2.16 (`ADD COLUMN` only), so the migrated file lacks the five `trial_to_rank_<n>`: A2b's shape comparison fails and A3's ORM insert raises (`table skill_definition has no column named trial_to_rank_1`, measured). After `_shape` add, verbatim:
     ```python
     # Columns the models gained after v2.16, by a later migration: a database
     # migrated to v2.16 lacks them. A2b leaves them out of the models' shape, and
     # `_catch_up` adds them before the later rules write into the migrated file.
     # TICKET-0116 (BRIEF-0116-A, v2.29): whether reaching a rank asks a trial.
     _LATER_COLUMNS: dict[str, tuple[str, ...]] = {
         "skill_definition": tuple(f"trial_to_rank_{n}" for n in range(1, 6)),
     }


     def _without_later(shapes: dict) -> dict:
         return {t: [c for c in cols if c[0] not in _LATER_COLUMNS.get(t, ())] for t, cols in shapes.items()}


     def _catch_up(db_path: str) -> None:
         with sqlite3.connect(db_path) as conn:
             for table, columns in _LATER_COLUMNS.items():
                 present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
                 for column in columns:
                     if column not in present:
                         conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} BOOLEAN")
     ```
     A2b compares `after["shapes"]` with `_without_later(ids["model_shapes"])`; `main()` calls `_catch_up(db_path)` right after `check_a2(db_path)`. A2's docstring gains « (columns added after v2.16 -- `_LATER_COLUMNS` -- are left out of the comparison and added before A3) ».
   - `tooling/verify/checks/quest_requests.py`: `COLUMNS` = C-01's order; `CHECKS = ("ck_quest_request_answer", "ck_quest_request_origin", "ck_quest_request_status", "ck_quest_request_trigger")`; `INDEXES = ("idx_quest_request_step", "idx_quest_request_trial", "idx_quest_request_world")`; QR1's docstring: « exactly its contract's columns, CHECK names and index names (v2.29: the trial columns) ». Its other rules are unchanged.
10. `world-engine-schema-changelog.md`, newest first, verbatim:
    ```
    - **v2.29** — TICKET-0116, BRIEF-0116-A: a rank may ask a trial, and a
      trial is a quest. `skill_rank` gains `trial_to_next` (BOOLEAN, default
      0: leaving this rank asks a trial); `skill_system` and
      `skill_definition` gain `trial_to_rank_1` .. `trial_to_rank_5`
      (nullable: NULL inherits, the most specific value winning).
      `quest_offer_term` and `quest_term` are rebuilt, their CHECKs admitting
      a sixth currency, `rank` -- a reward only, naming a skill and the rank
      it gives (1-5). `quest_request` is rebuilt: its day and step become
      optional; the trigger `trial` (a player character's skill ready for a
      rank that asks a trial) carries `skill_key` and `target_rank`;
      `ck_quest_request_origin` ties each trigger to its columns;
      `idx_quest_request_trial` indexes (world, skill, rank).
      `migrate_v2_29_rank_trials.py` writes no data: every row is kept, and
      no rank asks a trial.
    ```
11. `tooling/standards/ARCHITECTURE_DECISIONS.md`, inserted above the footer (`---` / `*Co-built…*`), header verbatim `## A RANK MAY ASK A TRIAL, A TRIAL IS A QUEST (TICKET-0116) -- THE STORAGE OF v2.29 (BRIEF-0116-a, schema v2.29)`; body: B1 (the cascade of the points, per rank), D2 and D2-d (a sixth currency in the existing term tables, both rebuilt), F1-b (`quest_request` with no day for a trial), why no CHECK on `skill_rank` (A1's pinned set; the writer refuses at rank 5, BRIEF-0116-B), the migration writes no data. Then `python tooling/glue/gen_decisions_index.py` and `python tooling/glue/gen_file_map.py`, both outputs staged.

## Scope OUT

- Any reader or writer of the new columns: the cascade and the waiting threshold (B), the `rank` currency in `QUEST_TERM_CURRENCIES`, `clean_term`, settlement, the editor (C), `QUEST_REQUEST_TRIGGERS`, `open_trial_request` (D), the designer (E), every frontend file (C, F).
- A CHECK on `skill_rank.trial_to_next` (rank 5): the writer's job in B.
- Backfilling any trial flag: no world asks a trial after the migration.
- Changing `debt_term`: a rank is never owed (D2-a).
- Any edit to `skill_progression.py`, `quest_requests.py`, `skill_system_shape.py` or `npc_skills.py` beyond item 9; any rule added to a check of R-19.

## Invariants to defend

- **INV-60** -- the boot guard compares `schema_meta` to `EXPECTED_STATIC_SCHEMA_VERSION`: the constant, the doc header and the migration's `schema_meta` move in this commit together.
- **INV-11** -- commit before touching the canon tables' DDL; DDL rides the migration's transaction.
- **History is sacred** -- the migration copies every row of the rebuilt tables, `change_history` included; a dangling reference that predates it is listed, never deleted.
- **INV-20** -- no new JSON column.

## Decision rights

STOP:
- an anchor of the Mini-RECON does not hold;
- the six tables' DDL compiled from the models at the branch point differs from item 8's (the fixture would not be v2.28's);
- any check other than the four of item 9 goes red after the model change;
- the migration's post-check fails on a copy of a real database for a reason other than a pre-existing dangling row.
ADAPT:
- `PRAGMA table_info` after the migration lists the eleven added columns at the end of their tables while the models declare them earlier: expected (`ADD COLUMN` appends; the v2.16 precedent); change nothing.
- `text` is not imported in `models/config.py`: import it from `sqlalchemy` beside the existing names; report.
REPORT-ONLY:
- the doc's prose of a rebuilt table that already mentions something item 7 adds.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/rank_trial_schema.py` -> `PASS` (TS1-TS3).
- [ ] Named mutations, each red then reverted: `QUEST_TERM_CURRENCY_CHECK` without `,'rank'` -> TS1 red; the shape clause without `direction = 'reward' AND ` -> TS2 red (a rank cost inserts); the migration's step d skipped -> TS3b red; `idx_quest_request_trial` removed from the model -> TS1 red.
- [ ] `skill_progression.py`, `skill_system_shape.py`, `quest_requests.py`, `npc_skills.py`, `quest_rewards.py`, `world_cascade.py`, `schema_version_agreement.py`, `schema_partition.py`, `file_map.py`, `decisions_index.py`, `module_budget.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] On a copy of the production database (`WORLD_ENGINE_DATABASE_URL` pointed at the copy): `python scripts/migrate_v2_29_rank_trials.py` prints `Migration v2.29 applied.`; a second run prints « DDL already applied. ».
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `world-engine-schema.md` and `world-engine-schema-changelog.md` (items 7, 10).
- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 11); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
