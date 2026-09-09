# BRIEF — Step "Fact spine, participants, and the knowledge anchor"

## Mini-RECON (measured on tarball of `main`, schema v1.97)

- `Knowledge` (`models/canon.py:442-473` pre-BRIEF-0082-a, `canon_knowledge.py`
  after): `id, entity_id, subject, level, content, source, is_incorrect,
  is_secret, share_threshold, acquired_at, updated_at, session_id,
  change_history` [M]. `subject: str`, no FK. **`knowledge` has no
  `world_id`** — world is reachable only through `entity_id -> entity.world_id` [M].
- `idx_knowledge_subject` on `subject` was added at **v1.96**
  (`scripts/migrate_v1_96_knowledge_subject_index.py`) [M]. The string key is
  not legacy debris; it was invested in one version ago. This step does not
  remove it.
- `Knowledge.subject` is used as an **identity key** at ten sites [M]:
  `scene_format.py:61-63`, `cockpit/mutations.py:464-466`,
  `cockpit/mutations.py:724-726`, `cockpit/routes/mutations.py:172-174`,
  `day_plan.py:141-142`, `day_plan.py:332`, `day_plan.py:344-349`,
  `link_context.py:89-90`, `link_author.py:191-193`,
  `analyzer_transcript.py:658 / 716-726 / 834-836`.
- `link_author.py:193` matches `Knowledge.subject == f"npc:{other_id}"` [M] —
  a foreign key already encoded inside the string. This is the clearest
  evidence that the anchor is missing, and it is **not converted here**.
- `writes/knowledge.py:34` defines `KNOWLEDGE_LEVELS` as a frozenset and
  line 42 defines the same six values as an **ordered tuple**: `unaware,
  rumor, suspicious, partial, knows, fully_understands` [M].
- `writes/knowledge.py:142` and `cockpit/mutations.py:379` insert the literal
  `"unknown"` as the subject fallback [M].
- `event` already carries `knowledge_status` defaulting to `'secret'`
  (`models/canon.py:593+`) [M] — a precedent for a per-row default, not a
  thing to unify in this step.
- Migration convention: `scripts/migrate_v1_NN_slug.py`, one per version [M].
- `Faction.id` is `foreign_key="entity.id"` (`models/canon_faction.py:26`) [M]
  — a faction is an entity and can be a participant with no special case.
- Verify-check idiom in `tooling/verify/checks/`: `FAILURES` list,
  `_report_and_exit`, vacuous-proof guard, `ROOT` via `parents[3]` [M].

## Context

`knowledge` points at a string. Every consumer that needs identity has
either joined on that string or invented a namespace prefix inside it. This
step gives `knowledge` a structural target and gives the world a place to
state a fact that is about three people, or about no one. It does **not**
migrate the ten string-key readers — that enumeration is larger than the
design session assumed and is a successor ticket.

## Scope IN

1. **Table `fact`** in `models/canon_knowledge.py`:
   `id` (str, PK, `_uuid`), `world_id` (FK `world.id`, NOT NULL),
   `relation_id` (FK `relation.id`, nullable),
   `event_id` (FK `event.id`, nullable),
   `world_law_id` (FK `world_law.id`, nullable),
   `content` (str, NOT NULL — the canonical statement of the fact, French
   prose, the truth),
   `default_level` (str, NOT NULL, default `'unaware'`,
   `server_default text("'unaware'")`),
   `created_at`, `created_by` (str, NOT NULL),
   `change_history` (JSON, NOT NULL, `server_default '[]'`).
   Constraints, with these exact names:
   - `ck_fact_spine_exclusive`:
     `(relation_id IS NOT NULL) + (event_id IS NOT NULL) + (world_law_id IS NOT NULL) <= 1`
   - `ck_fact_default_level`:
     `default_level IN ('unaware','rumor','suspicious','partial','knows','fully_understands')`
   Indexes: `idx_fact_world` on `world_id`, `idx_fact_relation` on
   `relation_id`, `idx_fact_event` on `event_id`, `idx_fact_world_law` on
   `world_law_id`.
   Section-header comment, verbatim:
   ```
   # -----------------------------------------------------------------------------
   # fact  (the spine: anything that can be known, schema vNEXT, TICKET-0082,
   # BRIEF-0082-b)
   #
   # A fact is one proposition. It is EITHER a typed row that already exists
   # (relation | event | world_law — at most one FK set, ck_fact_spine_exclusive)
   # OR free-standing (every typed FK NULL), in which case `fact_participant`
   # carries its arity: zero participants for a world-level statement, one for
   # a statement about a single entity, three for a secret shared by three
   # conspirators.
   #
   # There is NO `entity_id` column here on purpose. An arity-1 fact is a nu
   # spine plus one participant row — exactly one way to say each thing.
   #
   # `content` is the TRUTH. A degraded or false belief lives on the knowledge
   # row that points here (`knowledge.is_incorrect`), never on the fact.
   #
   # `situation_id` is deliberately absent: the `situation` table does not
   # exist yet. Adding the FK before the table would be structure with no
   # reader.
   # -----------------------------------------------------------------------------
   ```
2. **Table `fact_participant`** in the same module:
   `id`, `world_id` (FK `world.id`, NOT NULL),
   `fact_id` (FK `fact.id`, NOT NULL),
   `entity_id` (FK `entity.id`, NOT NULL),
   `role` (str, nullable — creator-authored label),
   `position` (int, NOT NULL, default 0, `server_default text("0")`).
   Unique index `idx_fact_participant_unique` on `(fact_id, entity_id)`.
   Index `idx_fact_participant_entity` on `entity_id`.
3. **Column `knowledge.fact_id`**, FK `fact.id`, **NOT NULL**, plus index
   `idx_knowledge_fact` on `fact_id`. `subject` stays exactly as it is —
   same column, same `idx_knowledge_subject`, same ten readers.
4. **Single write chokepoint.** Add `writes/facts.py` exposing
   `create_fact(...)` and `attach_participants(...)`. Every insert into
   `fact` and `fact_participant` in `src/` goes through it. It enforces, in
   code, the one rule SQLite cannot express as a CHECK because it spans two
   tables: **a participant may be attached only to a fact whose typed FKs are
   all NULL.** Raise `ValueError` otherwise; never silently drop.
5. **Migration** `scripts/migrate_v1_NN_fact_spine.py` (Claude Code assigns
   NN; v1.97 is current), in one transaction:
   - create the two tables;
   - for each distinct `(entity.world_id, knowledge.subject)` pair reachable
     through `knowledge.entity_id -> entity.world_id`, insert one
     free-standing `fact` with `content = subject`, `default_level = 'unaware'`,
     `created_by = 'migrate_v1_NN'`, zero participants;
   - rebuild `knowledge` with `fact_id` NOT NULL (SQLite table-rebuild:
     create new, copy with the resolved `fact_id`, drop old, rename), every
     other column and index preserved including `idx_knowledge_subject`;
   - assert `COUNT(knowledge)` before equals `COUNT(knowledge)` after, and
     assert zero NULL `fact_id`. On either assertion failing, roll back the
     whole transaction and exit non-zero.
   Rows whose `subject` is the literal `"unknown"` produce one fact per world
   with `content = 'unknown'` like any other — do not special-case them, do
   not skip them, do not repair them. They are surfaced by the report, not
   fixed here.
6. **First reader — creator CRUD.** In `cockpit/crud/knowledge.py`:
   - `KnowledgeWriteBody` (line 93) gains an optional `fact_id`. When
     absent, `_create_knowledge_core` (line 109) creates a free-standing
     fact via `writes/facts.py` with `content = subject` and attaches the
     new knowledge row to it. When present, it attaches to the existing fact
     and the request is rejected with 404 if that fact does not exist.
   - `_knowledge_dict` (`cockpit/crud/_shared.py:199`) gains `fact_id`,
     the fact's `content`, its `default_level`, and its participants as a
     list of `{entity_id, name, role}`.
   - Add a creator endpoint to attach and detach a participant on a
     free-standing fact, refusing with 409 when the fact has any typed FK
     set (the same rule as item 4, surfaced instead of crashed).
7. **Verify check** `tooling/verify/checks/fact_spine.py`, following the
   house idiom (`FAILURES`, `_report_and_exit`, `ROOT` via `parents[3]`).
   Four assertions, each **vacuous-proof — zero rows collected is FAIL,
   not PASS**:
   - no `fact_participant` row whose `fact` has any typed FK non-NULL;
   - no `knowledge` row with NULL `fact_id`;
   - every `fact.default_level` and every level value in the six-value
     vocabulary, read from `writes/knowledge.py`'s `KNOWLEDGE_LEVELS` —
     never a re-typed literal set in the check;
   - AST scan: no `db.add(Fact(` / `db.add(FactParticipant(` /
     `sa_insert` against those tables outside `writes/facts.py`.

## Scope OUT

- **Do not convert any of the ten `Knowledge.subject` sites.** Not
  `day_plan.py:141-142`, not `link_author.py:191-193`, not
  `analyzer_transcript.py`, not the two mutation dedup sites. They keep
  matching on the string. Converting them is the successor ticket and is
  named as a deferral in TICKET-0082.
- **Do not drop, rename or deprecate `Knowledge.subject`**, and do not drop
  `idx_knowledge_subject`. It was added at v1.96.
- **Do not add `situation_id`.** The table does not exist.
- **Do not add `entity_id` to `fact`.** The amendment during intake removed
  it deliberately; re-adding it recreates two ways to express arity 1.
- **No `fact_default` table** and no scope resolution — BRIEF-0082-c.
- **No knowledge-filtered reachability**, no new BFS, no change to any
  `connects_to` reader — BRIEF-0082-d.
- **Do not backfill a fact per `relation`.** BRIEF-0082-d does that for
  `connects_to` with its own default; doing it here would ship rows with no
  reader.
- Do not touch `faction.magic_knowledge_level`. Its subsumption is a named
  deferral with its own condition.
- Do not add a mechanical effect column to `fact` (E1 stands, E2 deferred).
- Do not "improve" the `"unknown"` fallbacks at `writes/knowledge.py:142` or
  `cockpit/mutations.py:379`. REPORT ONLY.

## Invariants to defend

- **Single canon-write authority.** `fact` and `fact_participant` are canon.
  Register both in `tooling/verify/canon_write_policy.txt` under
  `[CANON_TABLES]`, and confirm `single_canon_write.py` covers the new write
  path. Note in the report whether the known `db.execute(sa_insert(...))`
  blind spot (R3) applies here; the AST scan in item 7 exists partly to
  cover it for these two tables.
- **History is sacred.** The migration adds a column and rebuilds a table;
  it must not alter a single existing value in any other column. Assert
  equality of a checksum over `(id, entity_id, subject, level, content,
  acquired_at)` pre and post.
- **No structure without a reader.** Every field above has one:
  `content` and `default_level` read by the CRUD read path now and by
  BRIEF-0082-c; participants read by the CRUD read path now.
  If any field ends the step with no reader, STOP and report rather than
  shipping it dormant.
- **Fail-closed.** All four checks in item 7 are vacuous-proof.
- **Commit before touching canon-write paths.** Item 4 changes a write path;
  commit items 1-3 first.

## Done means

- [ ] Tables `fact` and `fact_participant` exist in the live dev database and
      appear in `static_table_names()`.
- [ ] `python -m world_engine.schema_reconcile` reports no orphan.
- [ ] `SELECT COUNT(*) FROM knowledge WHERE fact_id IS NULL` returns 0.
- [ ] `COUNT(*) FROM knowledge` is unchanged by the migration. Paste both
      numbers.
- [ ] `COUNT(DISTINCT content) FROM fact` equals
      `COUNT(DISTINCT subject) FROM knowledge` grouped by world. Paste both.
- [ ] The pre/post checksum over the six preserved columns is equal.
- [ ] Inserting a `fact_participant` against a fact with a non-NULL
      `relation_id` raises from `writes/facts.py` and is rejected 409 by the
      creator endpoint. Show both.
- [ ] Deleting every row from `fact` makes `fact_spine.py` report FAIL, not
      PASS (vacuous-proof, demonstrated on a scratch copy — never on the dev
      database).
- [ ] `fact_spine.py` PASS on the real dev database.
- [ ] `grep -rn "Knowledge.subject" src/world_engine | wc -l` returns the
      same count as before this step. The string readers are untouched.
- [ ] `module_budget.py`, `function_length.py`, `single_canon_write.py`,
      `import_cycle.py`, `runtime_ddl_guard.py` all PASS.
- [ ] Corpus gate green. `/review-step` and `/close-step` run.
- [ ] Live: in Creation, add a knowledge row to an NPC with no `fact_id` —
      a fact is created and the row reads back with it. Then create a
      free-standing fact, attach three character participants, and attach a
      knowledge row on a fourth character to that same fact. Screenshot or
      transcript of the read-back.

## Docs to update

- `world-engine-schema.md`: the two new tables, the new column, and the
  `Current schema version:` line. **Claude Code assigns the version number**
  (v1.97 is current) and writes the changelog entry in
  `world-engine-schema-changelog.md` in the house format.
- `src/world_engine/schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION`
  must match the doc line — `schema_version_agreement.py` enforces it.
- `tooling/verify/canon_write_policy.txt`: add both tables to `[CANON_TABLES]`.
- `ARCHITECTURE_DECISIONS.md`: a "Deferred decisions" entry for the
  `Knowledge.subject` cutover, with the ten sites listed and the
  reactivation condition from TICKET-0082.

## STOP conditions

- If the `Knowledge.subject` enumeration produces more than the ten sites
  listed above, **stop before the migration** and report the additional
  sites. The scope of this brief assumes that count.
- If the SQLite table rebuild cannot preserve `change_history` JSON or
  `idx_knowledge_subject` exactly, stop and report rather than dropping
  either.
- If any distinct `subject` string cannot be resolved to a world through
  `entity_id` (an orphan knowledge row), stop, report the row ids, and do
  not invent a world for it.
- If `single_canon_write.py` cannot see the new write path because of the
  known `sa_insert` blind spot, report it explicitly rather than treating a
  green verdict as coverage.
