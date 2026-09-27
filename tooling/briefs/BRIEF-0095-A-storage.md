# BRIEF 0095-A — "review storage: relational choices and the review record"

Lot: LOT-0095-choice-review.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `tooling/tickets/TICKET-0094-concordance-h2.md:5` reads `status: live-gate`.
- `src/world_engine/schema_version.py:15` `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.07"`;
  `world-engine-schema.md:3` `Current schema version: v2.07`; newest changelog
  entry `- **v2.07** — TICKET-0094, BRIEF-0094-A:`.
- `src/world_engine/models/pipeline.py:214` `class DayMentionChoice(`; `:250`
  the `# skill_resolution` comment line.
- `src/world_engine/writes/pipeline.py:41` imports `Batch, DayMentionChoice,
  DayMentionResolution, DayRewrite, PassPlay` from `..models`; `:294`
  `def write_day_mention_choices(`; its body ends with `db.add_all(rows)` /
  `return rows` and contains no `flush`.
- `src/world_engine/writes/facets.py:239` `_APPELLATION_SCOPES = ("rencontre", "world", "none")`.
- `tooling/verify/checks/day_rewrite.py:43`
  `_TRACKED_MODELS = {"DayRewrite", "DayMentionResolution", "DayMentionChoice"}`.
- `tooling/verify/checks/day_mention_choice_store.py:119` and `:134` contain `"autre"`.
- `scripts/migrate_v2_07_day_mention_choice.py` exists.
- Neither `tooling/verify/checks/day_mention_review_store.py` nor
  `tooling/verify/checks/choice_review.py` exists.

## Facts carried

Verbatim from the lot header.

#### R-01 — `day_mention_choice` declaration
Opened: `src/world_engine/models/pipeline.py:205-247`
Finding [M]: table `day_mention_choice`; CHECKs `category IN
('place','person','faction')`, `trigger IN ('ambiguous','near')`, `verdict IN
('accepted','rejected','declined','failed')`, `attempts IN (1, 2)`, and the
shape CHECK (`accepted` ⇒ `chosen_entity_id` set; `declined`/`failed` ⇒
NULL). `candidate_ids` and `evidence_fact_ids` are `str` columns holding JSON
arrays in display order. Indexes `idx_day_mention_choice_pass(pass_play_id)`
and `idx_day_mention_choice_world_verdict(world_id, verdict)`. The header
comment says append-only (W2), one row per model call, refused calls
included. `created_at = _created_ts()`; the next block is the
`# skill_resolution` comment at line 250.
Consequence: the table is not altered (no rebuild). The two id lists are
relationalized into two child tables (C-01, decision G1). The JSON columns
stay NOT NULL and keep being written as an audit copy that no code in `src/`
reads.

#### R-02 — the choice writer and the flush-before-children precedent
Opened: `src/world_engine/writes/pipeline.py:41`, `49`, `227-264`, `266-319`
Finding [M]: `write_day_mention_choices(db, *, world_id, pass_play_id,
records)` validates every record (`_validate_day_mention_choice`, 266-291),
then constructs one `DayMentionChoice` per record with `json.dumps(...,
ensure_ascii=False)` for both lists, `db.add_all`, returns the rows; no flush,
no commit. `write_day_rewrite`'s docstring (231-240) states the rule for a
parent and its children: "the parent is flushed BEFORE the children are
constructed — without a declared ORM `relationship()` between the two".
Measured on a prototype over `main`: a `day_mention_choice` row and a child
row referencing it, added in one session with no flush in between, fail the
commit with `IntegrityError: FOREIGN KEY constraint failed` (the unit of work
does not order them); the same rows with `db.flush()` after the parent commit
cleanly.
Consequence: C-02 adds the children after one `db.flush()` of the parents.
The validate-then-construct rule is unchanged.

#### R-03 — the JSON invariant and its check
Opened: `CLAUDE.md` (Invariants: "UI-visible data never lives in JSON —
relational only; enforced fail-closed by `json_ui_boundary`");
`tooling/verify/checks/json_ui_boundary.py:1-100`, `170-190` (volet c's scan)
Finding [M]: volet c scans only `Column(JSON` occurrences in `models/`; a
TEXT column holding JSON is invisible to it. The allow-list's stated doctrine
(for `Event.consequences` and others): "The FIRST UI consumer of any of these
MUST migrate it to relational storage in the same brief." K1 is the first UI
consumer of the choice's candidates and evidence.
Enumeration of today's readers (the only hits in `src/` that touch the stored
columns are the writer's `json.dumps` and the model fields; every other
`candidate_ids` is a dataclass attribute of another type):
```
$ grep -rn "candidate_ids\|evidence_fact_ids" src --include=*.py \
    | grep -v "^src/world_engine/day_concordance.py"
lore_query.py:167, lore_mentions_read.py:73, lore_resolve.py:138-236,
subject_resolve.py:30-74, cockpit/crud/knowledge.py:158, routes/day.py:448-476,
routes/lore.py:80, lore_render.py:223, day_rewrite.py:119, lore_candidates.py:*
    -> resolver / concordance dataclasses, not the stored column
writes/pipeline.py:288, 310, 311   -> the writer (validate, json.dumps)
day_choice.py:103, 186, 187        -> AmbiguousMention attr, record dict keys
models/pipeline.py:211-212, 238-239 -> the model
$ grep -rn "json.loads" src/world_engine --include=*.py | grep -i "choice\|candidate\|evidence"
llm_parse.py:55, 73                -> model-output parsing, unrelated
```
Consequence: decision G1 (relationalize). A new rule (R0 in
`choice_review.py`) keeps the JSON columns write-only in `src/`.

#### R-04 — which ids can disappear: facts are hard-deleted, entities are not
Opened: `src/world_engine/writes/facts.py:121-139`;
`src/world_engine/writes/facets.py:300-304`;
`src/world_engine/cockpit/crud/facets.py:130-133`;
`src/world_engine/cockpit/crud/entities.py:817-828`; `src/world_engine/db.py:116-126`
Finding [M]: `delete_free_fact` hard-deletes a free fact after its knowledge,
defaults and participants; `remove_entity_fact` calls it for any descriptive
fact, and the creator route `delete_entity_fact` calls that. Entity deletion
in CRUD is a soft delete (`status = 'inactive'`). SQLite FK enforcement is on
(`PRAGMA foreign_keys=ON` on every connection).
Consequence: an FK from a history row to `fact(id)` would make every fact
ever cited as evidence, or written as a reviewed appellation, undeletable.
So `day_mention_choice_evidence.fact_id` and
`day_mention_review.appellation_fact_id` carry **no FK** (plain TEXT, as the
JSON was). Entity ids keep their FK, as `chosen_entity_id` does.

#### R-05 — the world cascade does not know the day tables (pre-existing)
Opened: `src/world_engine/writes/worlds.py:22-95`
Finding [M]: `_SUBQUERY_SCOPED_DELETES` = conversation_message, gathering_member,
batch, pass_play, knowledge, skill, location, faction, artifact, item;
`_DIRECT_WORLD_SCOPED_DELETES` = faction_membership, relation, character,
discoverable_detail, proposed_mutation, ledger, event, gathering,
conversation, session, skill_definition, entity. None of `day_rewrite`,
`day_mention_resolution`, `day_mention_choice` appears. Measured on a
prototype over `main`: `delete_world_cascade` on a world holding one planned
day (a `day_rewrite` and a `day_mention_choice` row) fails its commit with
`IntegrityError: FOREIGN KEY constraint failed`.
Consequence: a pre-existing defect, outside this lot (a destructive path).
Named deferral: the cascade learns every day-chain table, including this
lot's three, in a ticket numbered above 0095. This lot adds no world-cascade
edit.

#### R-06 — `record_appellation`
Opened: `src/world_engine/writes/facets.py:60-70`, `92-145`, `239-259`
Finding [M]: `record_appellation(db, *, entity_id, surface, scope_type,
created_by) -> Optional[Fact]`; `_APPELLATION_SCOPES = ("rencontre", "world",
"none")` (line 239). `ValueError` on a scope outside it, a blank surface or an
unknown entity. Returns `None` and writes nothing when `normalize_surface(
surface)` equals the entity's name or one of its appellations (CREATOR
regime). Otherwise `add_entity_fact(facet="appellation", content=surface.strip(),
scope=...)`: `rencontre` → a `fact_default(rencontre, entity_id, knows)`,
`world` → `fact_default(world, NULL, knows)`, `none` → no default (creator-only
by scope). Never commits. Measured on a prototype (entities "Maelis Varn",
"Maelis Orn"): appellation "Maelis" on Varn at `world` is stored plain
(`content_raw == "Maelis"`), one default `('world', 'knows')`, zero
`unresolved_mention` rows; a second call with "maelis" returns `None`;
"Maelis" on Orn at `none` writes a fact with no default.
Consequence: « agree » and « disagree » write through this function only
(decision B1, creator CRUD, `created_by="creator_crud"`). The review row's
scope vocabulary equals `_APPELLATION_SCOPES` (asserted by V7, C-03).

#### R-15 — append-only rule W2
Opened: `tooling/verify/checks/day_rewrite.py:9-12`, `43`, `113-165`
Finding [M]: `_TRACKED_MODELS = {"DayRewrite", "DayMentionResolution",
"DayMentionChoice"}`. W2 fails on any attribute assignment on a name bound to
a tracked instance (constructor, `db.get(Model, ...)`, or a `for` over a query
naming it) and on `db.delete(` of one, anywhere in `src/`. Vacuity: every
tracked model must be constructed somewhere in `src/`.
Consequence: A adds the three new models to `_TRACKED_MODELS` in the same
commit as the writers that construct them.

#### R-16 — schema governance and the migration idiom
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3`,
`1031-1068`, `1071`; `world-engine-schema-changelog.md:14-17`;
`tooling/verify/checks/schema_partition.py:1-60`;
`scripts/migrate_v2_07_day_mention_choice.py` (whole); `src/world_engine/db.py:116-124`
Finding [M]: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.07"`; doc header
`Current schema version: v2.07`; the `### \`day_mention_choice\`` section runs
1031-1068 and `### \`skill_resolution\`` starts at 1071; newest changelog entry
`- **v2.07** — TICKET-0094, BRIEF-0094-A: ...`. The three must agree
(`schema_partition`, `schema_version_agreement`). The v2.07 script: env guard
before imports, raw `CREATE TABLE` + indexes when the table is absent, a
post-check, `_converge_schema_meta()`. Its post-check demands zero rows on
every run. `db.py` sets `isolation_level = None` so that DDL and writes share
one transaction; measured: a `CREATE TABLE` inside `engine.begin()` followed
by an exception leaves no table.
Consequence: A bumps the triple to v2.08 in one commit and ships
`scripts/migrate_v2_08_choice_review.py`. The two child tables and their
backfill run in ONE `engine.begin()` (all-or-nothing). The review table's
zero-rows post-check applies only on the run that creates it.

#### R-17 — exports
Opened: `src/world_engine/models/__init__.py:98-112`, `121-190`;
`src/world_engine/writes/__init__.py:112-127`, `144`
Finding [M]: `DayMentionChoice`, `DayMentionResolution`, `DayRewrite` are
imported in the `from .pipeline import (...)` block of `models/__init__.py`
and are absent from its `__all__`. `write_day_mention_choices` and
`write_day_rewrite` are imported in the `from .pipeline import (...)` block of
`writes/__init__.py` and are absent from its `__all__`.
`record_appellation` is not re-exported (callers import
`writes.facets.record_appellation`).
Consequence: new models and the new writer join those two import blocks,
alphabetically, and stay out of `__all__`.

#### R-18 — the 0094 store check's fixture
Opened: `tooling/verify/checks/day_mention_choice_store.py:52-100`, `102-195`
Finding [M]: S1 writes an `accepted` record with `candidate_ids=[maelis_id,
"autre"]` (line 119) and asserts `json.loads(row.candidate_ids) == [maelis_id,
"autre"]` (line 134). `"autre"` is not an entity id. `_record()` defaults
`candidate_ids=[]`, `evidence_fact_ids=[]`. `_parents` builds World → Session
→ Batch → two character entities → PassPlay, flushing each.
Consequence: once C-02 writes candidate rows with an FK to `entity`, S1's
`"autre"` fails the flush. A replaces it with a second real entity (S1 only);
S2-S5 are unchanged.

#### R-22 — governance files
Opened: `tooling/tickets/TICKET-0094-concordance-h2.md:1-15`;
`tooling/verify/checks/claude_md_contract.py:12-14`, `71`, `149-153`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16502`, `16669-16720`;
`tooling/verify/checks/decisions_index.py:15-17`;
`tooling/verify/checks/pipeline_state.py:1-60`
Finding [M]: TICKET-0094 line 5 reads `status: live-gate`, `current_brief:`
empty (Nia reports it passed). CLAUDE.md's File-structure section is capped at
80 lines, and 0094-D recorded it at the cap (no line added). Its file-map line
`lore_*.py, subject_resolve.py  # resolver/selectors/plan/names-panel reads;
subject<->entity` already covers a `lore_choices_read.py`. Decision headers
must match `^## .+ \(BRIEF-\d{4}(-[a-z])?(, ...)*, (schema v\d+\.\d+|no schema
change)\)$`. `pipeline_state.py`'s docstring (line 22) says "at least one
arrow resolving to a real file"; its implementation (`check_section_shape`,
lines 107-114) fails on EVERY Machine-checkable arrow that does not resolve,
once `status` is in `{brief, exec, verify, live-gate, done}`. Measured: this
lot's ticket at `status: brief` fails pipeline_state on the two new checks
until they exist.
Consequence: A closes 0094 in its own commit and creates both new checks
before running any gate (pipeline_state stays red on this ticket from its
deposit until A's check files exist). No CLAUDE.md edit in this lot.
Decision headers use the lowercase brief letter.

## Contracts

Verbatim from the lot header.

Two families are written here first and re-read after their last member:

- **review verdict** — the values `agreed` / `disagreed` and the appellation
  scopes `rencontre` / `world` / `none`: the table CHECKs (C-01), the writer
  (C-03), the route (C-07), the panel (C-08).
- **pending row** — the dict one reviewable choice becomes (C-06): built only
  by `list_pending_choices` (C-05), returned unchanged by the GET route
  (C-07), rendered by the panel (C-08).

#### C-01 — tables `day_mention_choice_candidate`, `day_mention_choice_evidence`, `day_mention_review`
Produced by: A   Consumed by: C-02, C-03, C-05, the migration
DDL (schema v2.08):
```sql
CREATE TABLE day_mention_choice_candidate (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  entity_id  TEXT NOT NULL REFERENCES entity(id)
);
CREATE UNIQUE INDEX idx_day_mention_choice_candidate_choice
  ON day_mention_choice_candidate(choice_id, ordinal);

CREATE TABLE day_mention_choice_evidence (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  fact_id    TEXT NOT NULL    -- no FK: a descriptive fact can be hard-deleted (R-04)
);
CREATE UNIQUE INDEX idx_day_mention_choice_evidence_choice
  ON day_mention_choice_evidence(choice_id, ordinal);

CREATE TABLE day_mention_review (
  id                   TEXT PRIMARY KEY,
  world_id             TEXT NOT NULL REFERENCES world(id),
  choice_id            TEXT NOT NULL REFERENCES day_mention_choice(id),
  verdict              TEXT NOT NULL CHECK (verdict IN ('agreed','disagreed')),
  entity_id            TEXT REFERENCES entity(id),
  appellation_fact_id  TEXT,  -- no FK: the appellation can be hard-deleted later (R-04)
  appellation_scope    TEXT CHECK (appellation_scope IS NULL
                                   OR appellation_scope IN ('rencontre','world','none')),
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'agreed' OR entity_id IS NOT NULL)
    AND (appellation_fact_id IS NULL OR entity_id IS NOT NULL)
    AND ((appellation_fact_id IS NULL) = (appellation_scope IS NULL))
  )
);
CREATE INDEX idx_day_mention_review_choice ON day_mention_review(choice_id);
```
Meaning: a candidate row is the `ordinal`-th candidate shown to the model;
an evidence row is the `ordinal`-th fact shown, flattened across candidates
in display order (the JSON order). A review row is Nia's verdict on one
choice: `agreed` → `entity_id` is the model's choice; `disagreed` →
`entity_id` is the entity she picked, or NULL for "no known entity" (H2).
`appellation_fact_id` / `appellation_scope` are set only when an appellation
was actually written. All three tables are append-only (W2), non-canon.
`choice_id` on the review is NOT unique: J1's "one review per choice" is the
route's rule (C-07), so a later re-review needs no rebuild (A1).
Models (`src/world_engine/models/pipeline.py`): `DayMentionChoiceCandidate`,
`DayMentionChoiceEvidence`, `DayMentionReview`, fields in DDL order,
`created_at = _created_ts()` on the review only, ids `default_factory=_uuid`,
CHECK names `ck_day_mention_choice_candidate_ordinal`,
`ck_day_mention_choice_evidence_ordinal`, `ck_day_mention_review_verdict`,
`ck_day_mention_review_scope`, `ck_day_mention_review_shape`.

#### C-02 — `write_day_mention_choices` (amended)
Produced by: A   Consumed by: the plan route (unchanged call sites)
Signature unchanged: `def write_day_mention_choices(db: Session, *, world_id:
str, pass_play_id: str, records: list[dict]) -> list[DayMentionChoice]`.
Record keys unchanged (the 0094 family shape: `category, surface_form,
trigger, candidate_ids, evidence_fact_ids, verdict, chosen_entity_id,
excerpt, reason, verdict_detail, attempts`).
Behaviour:
1. `records == []` → return `[]`, nothing added, no flush.
2. Validate every record (`_validate_day_mention_choice`, unchanged); any
   violation raises `ValueError` with nothing added.
3. Construct the `DayMentionChoice` rows exactly as today (the two JSON
   columns still written with `json.dumps(..., ensure_ascii=False)`: the
   audit copy), `db.add_all(rows)`, then `db.flush()`.
4. For each record and its row: one `DayMentionChoiceCandidate(choice_id=
   row.id, ordinal=i, entity_id=e)` per `e` of `record["candidate_ids"]`,
   `i` from 1; one `DayMentionChoiceEvidence(choice_id=row.id, ordinal=i,
   fact_id=f)` per `f` of `record["evidence_fact_ids"]`, `i` from 1;
   `db.add_all(children)`.
5. Return the parent rows. No commit.

#### C-03 — `write_day_mention_review`
Produced by: A   Consumed by: C-07
In `src/world_engine/writes/pipeline.py`, with module constants
`_REVIEW_VERDICTS: tuple[str, ...] = ("agreed", "disagreed")` and
`_REVIEW_SCOPES: tuple[str, ...] = ("rencontre", "world", "none")` (must equal
`writes.facets._APPELLATION_SCOPES`; V7 asserts it).
Signature: `def write_day_mention_review(db: Session, *, world_id: str,
choice_id: str, verdict: str, entity_id: Optional[str],
appellation_fact_id: Optional[str], appellation_scope: Optional[str]) ->
DayMentionReview`.
Behaviour: validate, in this order, each failure raising `ValueError` whose
message starts `write_day_mention_review: ` and adding nothing:
1. `verdict` not in `_REVIEW_VERDICTS`;
2. `verdict == "agreed"` and `entity_id is None`;
3. `appellation_fact_id is not None` and `entity_id is None`;
4. `(appellation_fact_id is None) != (appellation_scope is None)`;
5. `appellation_scope is not None` and not in `_REVIEW_SCOPES`.
Then construct one `DayMentionReview`, `db.add` it, return it. No flush, no
commit.

## Case tables

Verbatim from the lot header's gate output.

**(b5) Migration states (R-16):**

| candidate table | evidence table | review table | action |
|---|---|---|---|
| absent | absent | any | create both + backfill, one transaction |
| present | present | any | skip children |
| exactly one present | | | abort, no write (impossible after an atomic run) |
| any | any | absent | create; post-check 0 rows |
| any | any | present | skip; no row-count demand |

Backfill aborts, writing nothing, when a JSON value is not a list of str or
a candidate id is not an `entity.id`. Post-check (every run): candidate rows ==
Σ len(candidate_ids), evidence rows == Σ len(evidence_fact_ids).

## Context

H2 stores every model choice in `day_mention_choice`, with its candidates and
evidence as JSON in TEXT. K1 (this ticket) is the first screen to show them,
which the JSON invariant forbids (R-03, decision G1). This brief moves them to
rows, adds the review record (A1), and writes nothing a player sees. It also
closes TICKET-0094 and creates both new checks: from `brief` status on,
`pipeline_state.py` fails on every Machine-checkable arrow whose file is
missing (R-22), so the corpus is red on this ticket until item 8 and 9 exist.

## Scope IN

1. **Close TICKET-0094, in its own first commit.** In
   `tooling/tickets/TICKET-0094-concordance-h2.md`, `status: live-gate`
   becomes `status: done`. Nothing else in that file. Commit message:
   `chore(tickets): close TICKET-0094 — live gate passed (Nia, 2026-09-25)`.

2. **Models.** In `src/world_engine/models/pipeline.py`, after
   `DayMentionChoice` and before the `# skill_resolution` comment block, add
   one comment block in the file's style (dashes, as above
   `DayMentionChoice`) reading:
   ```
   # day_mention_choice_candidate / day_mention_choice_evidence /
   # day_mention_review  (the K1 review record, schema v2.08, TICKET-0095,
   # BRIEF-0095-A)
   #
   # The candidates and evidence of one H2 choice, as rows (G1): the JSON
   # columns of day_mention_choice stay as an audit copy that nothing in src/
   # reads (`verify/checks/choice_review.py` R0). A review row is Nia's
   # verdict on one choice (A1); the route allows one per choice (J1).
   # `fact_id` / `appellation_fact_id` carry no FK: a descriptive fact can be
   # hard-deleted by creator CRUD. Append-only, all three (W2).
   ```
   then `DayMentionChoiceCandidate`, `DayMentionChoiceEvidence`,
   `DayMentionReview` exactly per C-01 (table names, fields in DDL order,
   `Field(foreign_key=...)` on `choice_id`, `entity_id`, `world_id` only,
   the index and CHECK names of C-01). Add the three names to the
   `from .pipeline import (...)` block of `models/__init__.py`,
   alphabetically; not to `__all__` (R-17).

3. **Writers.** In `src/world_engine/writes/pipeline.py`:
   - import the three new models (same `from ..models import` line, sorted);
     `Optional` is already imported;
   - add `_REVIEW_VERDICTS` and `_REVIEW_SCOPES` (C-03) next to
     `_CHOICE_VERDICTS`;
   - change `write_day_mention_choices` to C-02: early `return []` on empty
     `records`; after `db.add_all(rows)`, `db.flush()`, then build and
     `db.add_all` the children. Append to its docstring: "Then flushes the
     parents and adds one `day_mention_choice_candidate` row per candidate id
     and one `day_mention_choice_evidence` row per evidence fact id, ordinals
     from 1, in the lists' order (G1, TICKET-0095, BRIEF-0095-A): the JSON
     columns remain an audit copy, never read. The flush precedes the
     children for the reason `write_day_rewrite` gives." — and replace "No
     flush, no commit" with "No commit";
   - add `write_day_mention_review` right after it, exactly per C-03, with a
     docstring naming C-03, A1 and "No flush, no commit: the caller commits.";
   - re-export `write_day_mention_review` from `writes/__init__.py`, in the
     `from .pipeline import (...)` block, alphabetically; not in `__all__`.

4. **Schema v2.08** (one commit with items 2, 3 and 5):
   - `schema_version.py`: `"v2.07"` → `"v2.08"`;
   - `world-engine-schema.md`: header → `Current schema version: v2.08`; at
     the end of the `day_mention_choice` section (before its closing `-----`)
     add: `**NOTE — the two JSON columns are an audit copy (v2.08,
     TICKET-0095).** \`day_mention_choice_candidate\` and
     \`day_mention_choice_evidence\` hold the same ids as rows; nothing in
     \`src/\` reads the JSON (\`choice_review.py\` R0).`; then three new
     sections, in C-01's order, each `-----`-separated like its neighbours,
     each with one paragraph taken from C-01's "Meaning" and its DDL (table
     + index) verbatim from C-01;
   - `world-engine-schema-changelog.md`, newest first:
     `- **v2.08** — TICKET-0095, BRIEF-0095-A: the K1 review record —
     \`day_mention_choice_candidate\` and \`day_mention_choice_evidence\` (a
     choice's candidates and evidence as rows, backfilled from the JSON
     columns, which stay as an audit copy) and \`day_mention_review\`
     (append-only, zero rows).`

5. **Migration.** Create `scripts/migrate_v2_08_choice_review.py` from
   `scripts/migrate_v2_07_day_mention_choice.py`'s structure (env guard
   before imports with this file's name, `sys.path` insert, `engine`,
   `_converge_schema_meta` verbatim), with:
   - a docstring: what it creates (C-01's three tables), that the two child
     tables are created AND backfilled in one transaction from every existing
     `day_mention_choice` row (ordinal = position in the JSON list, from 1),
     the abort conditions, idempotency per (b5), the post-checks, the run
     line;
   - `_CHILD_DDL`: the two child `CREATE TABLE` and two `CREATE UNIQUE INDEX`
     statements of C-01, verbatim; `_REVIEW_DDL`: the review `CREATE TABLE`
     and its index, verbatim;
   - `_backfill(conn) -> tuple[int, int]`: `SELECT id, candidate_ids,
     evidence_fact_ids FROM day_mention_choice ORDER BY created_at, id`;
     `json.loads` both; any value that is not a list of str →
     `raise SystemExit(f"Migration v2.08 aborted: day_mention_choice {id}
     {column} is not a JSON list of str")`; then every candidate id must be in
     `SELECT id FROM entity`, else `raise SystemExit(f"Migration v2.08
     aborted: candidate ids not in entity: {sorted(missing)}")` — both checks
     before the first INSERT; then one parameterized INSERT per child row
     (`id = str(uuid.uuid4())`); returns (candidate rows, evidence rows)
     inserted;
   - `_apply_ddl() -> bool`: per (b5) — both child tables absent → in ONE
     `with engine.begin() as conn:` run `_CHILD_DDL` then `_backfill(conn)`
     and print `Backfilled {n} candidate row(s) and {m} evidence row(s).`;
     both present → print that they exist; exactly one present →
     `raise SystemExit("Migration v2.08 aborted: exactly one of the two child
     tables exists — investigate before re-running")`. Review table absent →
     create it (own `engine.begin()`); returns `True` iff it created the
     review table;
   - `_post_checks(review_created: bool)`: candidate row count == Σ
     `len(json.loads(candidate_ids))` over every choice, evidence row count ==
     Σ `len(json.loads(evidence_fact_ids))`, else `SystemExit` naming both
     numbers; if `review_created`, `day_mention_review` has 0 rows; print
     each result;
   - `main()`: title line `Migration v2.08 — choice review`, `_apply_ddl`,
     `_post_checks`, `_converge_schema_meta`, `Migration v2.08 applied.`

6. **Append-only.** In `tooling/verify/checks/day_rewrite.py`,
   `_TRACKED_MODELS` gains `"DayMentionChoiceCandidate"`,
   `"DayMentionChoiceEvidence"`, `"DayMentionReview"`; W2's docstring line
   names them with `(TICKET-0095)`. Item 3's writers provide the
   constructions the vacuity guard needs.

7. **Fix the 0094 store check's fixture (R-18).** In
   `tooling/verify/checks/day_mention_choice_store.py`: `_parents` also
   creates `orn = entity("character", "Orn")` after `maelis` and returns
   `world, pass_play, maelis, orn`; `check_store` unpacks it and keeps
   `orn_id = orn.id` beside `maelis_id`; lines 119 and 134 use `orn_id` in
   place of `"autre"`. Nothing else in that file changes.

8. **Create `tooling/verify/checks/day_mention_review_store.py`**: docstring
   listing V1-V7; FAILURES idiom; `_fresh_engine`, `_world` and `_parents`
   copied from `day_mention_choice_store.py` as item 7 leaves them; one
   `PASS:` line. Fixture: `_parents(db)`, plus
   `add_entity_fact(db, entity_id=maelis.id, facet="histoire",
   content="Elle tient la forge.", created_by="creator")` (import from
   `world_engine.writes`), committed; `write = write_day_mention_choices(db,
   world_id=..., pass_play_id=..., records=...)`. Cases:
   - V1: records `r1` = accepted, chosen `maelis`, `candidate_ids=[maelis,
     orn]`, `evidence_fact_ids=["fact-gone"]`; `r2` = failed, chosen None,
     `candidate_ids=[orn]`, `evidence_fact_ids=[]` (other keys as the 0094
     `_record`). After commit: candidate rows of r1's row by ordinal ==
     `[(1, maelis), (2, orn)]`, of r2's == `[(1, orn)]`; evidence rows ==
     `[(1, "fact-gone")]` and `[]`; `json.loads(row.candidate_ids)` of r1's
     row == `[maelis, orn]` (audit copy still written).
   - V2: a record with `verdict="ambiguous"` raises `ValueError`; `db.new`
     empty.
   - V3: `records=[]` returns `[]`; `db.new` empty.
   - V4: `write_day_mention_review` (choice id = r1's row) writes
     `(agreed, maelis, None, None)`, `(disagreed, None, None, None)`,
     `(agreed, maelis, "f-1", "world")`: 3 rows after commit. Each of these
     raises `ValueError` whose message starts `write_day_mention_review: ` and
     leaves `db.new` empty: verdict `"maybe"`; `agreed` with entity None;
     `disagreed`, entity None, fact `"f"`, scope `"rencontre"`; fact `"f"`
     with scope None; scope `"world"` with fact None; fact `"f"` with scope
     `"public"`.
   - V5: raw SQL `INSERT INTO day_mention_review (id, world_id, choice_id,
     verdict, entity_id) VALUES ('v5', :w, :c, 'agreed', NULL)` raises
     `IntegrityError`; `INSERT INTO day_mention_choice_candidate (id,
     choice_id, ordinal, entity_id) VALUES ('v5c', :c, 0, :e)` raises
     `IntegrityError`.
   - V6: an evidence row (via `write_day_mention_choices`, one accepted
     record citing the fixture fact's id) and a review row with
     `appellation_fact_id` = that fact id and scope `"none"`; then
     `remove_entity_fact(db, fact_id=...)` and `db.commit()` succeed; both
     rows still exist.
   - V7: `writes.pipeline._REVIEW_SCOPES == writes.facets._APPELLATION_SCOPES`.
   Vacuity: V1 read back three candidate rows.

9. **Create `tooling/verify/checks/choice_review.py`** with R0 only.
   Docstring: "G1 check for TICKET-0095 (K1). Created by BRIEF-0095-A with
   R0; BRIEF-0095-B adds L0-L6 (the reader); BRIEF-0095-C adds T0-T10 (the
   route)." R0 (AST, every `.py` under `src/world_engine/`):
   - (a) no call whose callee name is `loads` has, anywhere in its arguments,
     an `ast.Attribute` whose `attr` is `candidate_ids` or
     `evidence_fact_ids`;
   - (b) no `ast.Attribute` with such an `attr` has as `value` the
     `ast.Name` `DayMentionChoice`;
   - vacuity: `src/world_engine/writes/pipeline.py` holds a `json.dumps(`
     call whose first argument is a `Subscript` keyed `"candidate_ids"` and
     one keyed `"evidence_fact_ids"`; otherwise FAIL "R0 vacuous".
   FAILURES idiom; `PASS: choice_review — R0` for now.

10. Append to `tooling/standards/ARCHITECTURE_DECISIONS.md` an entry headed
    `## THE K1 REVIEW RECORD (TICKET-0095) -- A CHOICE'S CANDIDATES AND EVIDENCE BECOME ROWS, EVERY REVIEW IS KEPT (BRIEF-0095-a, schema v2.08)`:
    G1 and the first-UI-consumer doctrine (R-03); the three tables (C-01) and
    why fact ids carry no FK (R-04); the flush before children (R-02); A1 and
    J1 (a non-unique `choice_id`); the migration's one-transaction backfill;
    W2 extended; R0; the pre-existing world-cascade defect (R-05) named as a
    deferral. Regenerate `DECISIONS_INDEX.md` with
    `python tooling/glue/gen_decisions_index.py`.

## Scope OUT

- The reader, `excerpt_key`: B. The route: C. The panel: D.
- Any change to `day_choice.py`, the plan route, `choose`, the judge or the
  H2 prompt.
- Dropping or rebuilding `day_mention_choice` (the JSON columns stay).
- Adding any table to `delete_world_cascade` (R-05, deferred).
- `json_ui_boundary.py` edits (no new `Column(JSON`).
- Running the migration on prod: Nia (live gate).

## Invariants to defend

- "UI-visible data never lives in JSON": after this brief the ids exist as
  rows; R0 keeps the JSON write-only in `src/`.
- "History is sacred": all three tables append-only (item 6); the backfill
  copies, never rewrites, `day_mention_choice`.
- "Schema is authoritative": constant, doc and changelog in one commit;
  `schema_meta` converged by the script.
- Creator control: nothing here writes canon.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- the backfill would need to alter or delete a `day_mention_choice` row;
- `schema_partition.py` or `schema_version_agreement.py` needs more than
  item 4's three edits;
- `day_choice.py` (the check) fails after item 3.

ADAPT:
- a check other than item 7's inserts choice records with ids that are not
  entities: give it real entities the way item 7 does, one commit, report.
- `_created_ts` / `_uuid` are named differently in `models/pipeline.py`: use
  the names `DayMentionChoice` uses, report.

REPORT-ONLY:
- any other check that enumerates tables by name and could want the new ones;
- the count of `day_mention_choice` rows on the executor's own DB, if any.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `git log --format=%s` shows item 1's message on its own commit, and
      `grep -n "^status:" tooling/tickets/TICKET-0094-*.md` prints `status: done`.
- [ ] `python tooling/verify/checks/day_mention_review_store.py` → `PASS:` (V1-V7).
- [ ] `python tooling/verify/checks/choice_review.py` → `PASS:` (R0).
- [ ] `python tooling/verify/checks/pipeline_state.py` → pass (both new arrows resolve).
- [ ] `python tooling/verify/checks/day_mention_choice_store.py`,
      `day_rewrite.py`, `day_choice.py`, `schema_version_agreement.py`,
      `schema_partition.py`, `json_ui_boundary.py` → pass.
- [ ] On a scratch copy of a v2.07 DB holding at least one `day_mention_choice`
      row (or one made by `day_mention_choice_store.py`'s fixture): the
      migration prints the backfill counts, the post-check equalities and
      `'v2.07' -> 'v2.08'`; a second run prints that both child tables and the
      review table exist and converges nothing; the boot guard accepts the DB.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- Schema doc + changelog v2.08 (item 4); `ARCHITECTURE_DECISIONS.md` +
  `DECISIONS_INDEX.md` (item 10). No CLAUDE.md (R-22).
