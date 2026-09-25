# BRIEF 0094-A — "choice storage and pure near names"

Lot: LOT-0094-concordance-h2.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- `tooling/tickets/TICKET-0093-day-narration-judge.md:5` `status: live-gate`.
- `src/world_engine/schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.06"`;
  `world-engine-schema.md:3` `Current schema version: v2.06`; newest
  changelog entry `- **v2.06** —`.
- `src/world_engine/models/pipeline.py:175` `class DayMentionResolution(` and
  `:205` the `# skill_resolution` comment block.
- `src/world_engine/writes/pipeline.py:40` imports `DayMentionResolution,
  DayRewrite` from `..models`; `:224` `def write_day_rewrite(`.
- `src/world_engine/lore_resolve.py:183` `def near_candidates(` with the
  regime guard at 190-191.
- `tooling/verify/checks/day_rewrite.py:42`
  `_TRACKED_MODELS = {"DayRewrite", "DayMentionResolution"}`.
- `scripts/migrate_v2_02_skill_resolution.py` exists.
- Neither `tooling/verify/checks/day_mention_choice_store.py` nor
  `tooling/verify/checks/day_choice.py` exists.

## Facts carried

#### R-04 — rewrite trace writer and reader
Opened: `src/world_engine/writes/pipeline.py:40-46`, `200-260`;
`src/world_engine/day_rewrite.py:72-147`
Finding [M]: `write_day_rewrite` validates every resolution dict, then builds
`DayRewrite`, flushes, then `DayMentionResolution` children; no commit.
`resolutions()` emits matched rows with `"rung": mm.rung`; `_reconstruct`
rebuilds `MatchedMention` from any stored `rung` string. No code validates
the rung value.
Consequence: an accepted choice becomes a `MatchedMention` with
`rung="model_choice"` and flows through the trace unchanged (Y3b). No change
to these two modules except the new writer (C-02) in `writes/pipeline.py`.

#### R-05 — `day_mention_resolution` declaration
Opened: `src/world_engine/models/pipeline.py:146-203`; `world-engine-schema.md:993-1029`
Finding [M]: category CHECK `('place','person','faction')`; verdict CHECK
`('matched','cast','unmatched')`; `rung` has no CHECK; the doc's NOTE says an
ambiguity is never stored because the route 409s first.
Consequence: no rebuild needed (R-04). The new table sits right after it in
both files.

#### R-06 — rungs, near names and the normalizer
Opened: `src/world_engine/lore_resolve.py:1-56`, `70-86`, `90-122`, `183-214`
Finding [M]: `rung_named_partial(surface_form, category, name_surfaces)` is
pure (surface tokens all ≥3 chars and a subset of the name's tokens).
`near_candidates(surface_form, world_id, db, *, scope, exclude_ids)` raises
`ValueError` unless `scope.regime == "creator"`, reads
`surfaces(db, world_id, scope)`, keeps per entity the best surface with
`difflib` ratio ≥ `NEAR_RATIO` (0.8) or a shared 3+ token, scores
half-up to 0-100, sorts `(-score, name.casefold(), entity_id)`, returns at
most `NEAR_LIMIT` (5) `NearCandidate(entity_id, name, entity_type, surface,
score)`, every category. `normalize_surface` casefolds, strips accents, drops
up to three leading article tokens, splits on whitespace and apostrophes,
joins with single spaces; punctuation stays attached to tokens.
Consequence: A extracts the loop into pure `near_in_surfaces` (C-03);
`near_candidates` keeps its guard and output exactly. B calls
`rung_named_partial` and `near_in_surfaces` on the perceiver surfaces and
filters by category itself. The judge reuses `normalize_surface`, after
stripping edge punctuation from the excerpt.

#### R-07 — checks pinning the resolver
Opened: `tooling/verify/checks/name_resolution.py:1-45`;
`tooling/verify/checks/name_index.py:17-30`; `tooling/verify/checks/lore_resolve.py:1-20`
Finding [M]: G2 checks `near_candidates` scores (Maelys→83, reine→63/59),
`exclude_ids`, and that `scope=PROSE` raises. G5 checks a generator mention
"Varn" stays unresolved outside `creator` (tokenizer). name_index R5 confines
`CREATOR`; R6 requires a `scope=` keyword on every `resolve_named` /
`near_candidates` call. lore_resolve R1 forbids `db.add(`, `.commit(`,
`chat(` in `lore_resolve.py`.
Consequence: `near_in_surfaces` takes surfaces, not a scope; R6 does not
apply to it. `day_choice.py` never names `CREATOR` and never calls
`resolve_named` or `near_candidates`. G2 and G5 must stay green unchanged.

#### R-11 — day-chain structural checks
Opened: `tooling/verify/checks/day_concordance.py:1-50`, `74`, `292-317`;
`tooling/verify/checks/day_rewrite.py:1-24`, `42-43`
Finding [M]: day_concordance R1 forbids `chat(` in `day_concordance.py`; R4
forbids `Entity(` / `Character(` / `NpcSchedule(` in extract/concordance/
plan; `EXPECTED_RUNGS` pins `MATCHING_RUNGS`. day_rewrite W2: no attribute
assignment on, and no `db.delete(` of, a `_TRACKED_MODELS = {"DayRewrite",
"DayMentionResolution"}` instance, vacuity-guarded by requiring a
construction of each; W6: `routes/day.py` calls each `extract_*` exactly
once.
Consequence: the model call lives in `day_choice.py` (R1 untouched).
`"model_choice"` is a stored rung, not a `MATCHING_RUNGS` entry
(`EXPECTED_RUNGS` untouched). A adds `"DayMentionChoice"` to
`_TRACKED_MODELS`. W6 stays true.

#### R-12 — schema governance
Opened: `src/world_engine/schema_version.py`; `tooling/verify/checks/schema_version_agreement.py:1-30`;
`tooling/verify/checks/schema_partition.py:1-40`; `world-engine-schema-changelog.md:1-16`;
`scripts/migrate_v2_02_skill_resolution.py`; `src/world_engine/db.py:149-154`;
`src/world_engine/cockpit/app.py:195-210`
Finding [M]: the constant `EXPECTED_STATIC_SCHEMA_VERSION = "v2.06"`, the doc
header `Current schema version: v2.06` and the newest changelog entry
(`- **v2.06** — ...`) must agree. The boot guard refuses to start when
`schema_meta.static_version` differs. `migrate_v2_02_skill_resolution.py` is
the additive-table precedent: env guard, raw `CREATE TABLE` + indexes if
absent, post-check zero rows, converge `schema_meta`, idempotent.
`create_db_and_tables` runs `SQLModel.metadata.create_all`.
Consequence: A bumps all three to v2.07 in one commit and ships
`scripts/migrate_v2_07_day_mention_choice.py` (Nia runs it on prod before
starting the cockpit).

#### R-13 — models export and canon-write policy
Opened: `src/world_engine/models/__init__.py:98-110`;
`tooling/verify/checks/single_canon_write.py:1-12`
Finding [M]: pipeline models are re-exported from `models/__init__.py`. The
canon-write check ignores non-canon tables and fails on an unattributable
write site.
Consequence: `DayMentionChoice` is exported there; its only write site is
`writes/pipeline.py::write_day_mention_choices`, constructed with the model
class (attributable).

#### R-17 — TICKET-0093 front matter
Opened: `tooling/tickets/TICKET-0093-day-narration-judge.md:1-14`
Finding [M]: `status: live-gate` (line 5), `current_brief:` empty (12). Nia
reports 0093 passed.
Consequence: A sets `status: done`, in its own commit.

## Contracts

#### C-01 — table `day_mention_choice` / model `DayMentionChoice`
Produced by: A   Consumed by: C-02, K1 (0095)
DDL:
```sql
CREATE TABLE day_mention_choice (
  id                 TEXT PRIMARY KEY,
  world_id           TEXT NOT NULL REFERENCES world(id),
  pass_play_id       TEXT NOT NULL REFERENCES pass_play(id),
  category           TEXT NOT NULL CHECK (category IN ('place','person','faction')),
  surface_form       TEXT NOT NULL,
  trigger            TEXT NOT NULL CHECK (trigger IN ('ambiguous','near')),
  candidate_ids      TEXT NOT NULL,   -- JSON array, display order
  evidence_fact_ids  TEXT NOT NULL,   -- JSON array, facts shown to the model
  verdict            TEXT NOT NULL CHECK (verdict IN ('accepted','rejected','declined','failed')),
  chosen_entity_id   TEXT REFERENCES entity(id),
  excerpt            TEXT,
  reason             TEXT,
  verdict_detail     TEXT,
  attempts           INTEGER NOT NULL CHECK (attempts IN (1, 2)),
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'accepted' OR chosen_entity_id IS NOT NULL)
    AND (verdict NOT IN ('declined','failed') OR chosen_entity_id IS NULL)
  )
);
CREATE INDEX idx_day_mention_choice_pass ON day_mention_choice(pass_play_id);
CREATE INDEX idx_day_mention_choice_world_verdict ON day_mention_choice(world_id, verdict);
```
Append-only (W2). Non-canon.

#### C-02 — `write_day_mention_choices`
Produced by: A   Consumed by: D
Signature: `def write_day_mention_choices(db: Session, *, world_id: str,
pass_play_id: str, records: list[dict]) -> list[DayMentionChoice]` in
`src/world_engine/writes/pipeline.py`.
Record keys (the family shape, every key required):
`category, surface_form, trigger, candidate_ids (list[str]),
evidence_fact_ids (list[str]), verdict, chosen_entity_id (str|None),
excerpt (str|None), reason (str|None), verdict_detail (str|None),
attempts (int)`.
Behaviour: validate every record first (category, trigger, verdict in their
sets; attempts in (1, 2); accepted ⇒ chosen set; declined/failed ⇒ chosen
None; the two lists are lists of str); any violation raises `ValueError`
with nothing built. Then construct one row per record (lists stored with
`json.dumps`), `db.add_all`, return them. No flush, no commit.
Empty `records` → `[]`, nothing added.

#### C-03 — `near_in_surfaces`
Produced by: A   Consumed by: B (C-05), `near_candidates`
Signature: `def near_in_surfaces(surface_form: str, name_surfaces:
Sequence[NameSurface], *, exclude_ids: frozenset[str] = frozenset()) ->
tuple[NearCandidate, ...]` in `lore_resolve.py`. Pure.
Behaviour: exactly the body of today's `near_candidates` after its regime
guard, iterating `name_surfaces` instead of `surfaces(db, world_id, scope)`.
`near_candidates` becomes: the regime guard, then
`return near_in_surfaces(surface_form, surfaces(db, world_id, scope),
exclude_ids=exclude_ids)`.

## Context

H2 lets the model choose among candidates the code has narrowed; every call
is stored for the review loop (K1). This brief lays the ground with no
behaviour change in play: the table and its writer, and a pure near-name
function the day chain can call on the character's own surfaces. It also
closes TICKET-0093 and creates both new checks (every arrow must exist from
`exec` on).

## Scope IN

1. **Close TICKET-0093, in its own first commit.** In
   `tooling/tickets/TICKET-0093-day-narration-judge.md`, `status: live-gate`
   becomes `status: done`. Nothing else in that file. Commit message:
   `chore(tickets): close TICKET-0093 — live gate passed (Nia, 2026-09-25)`.

2. **Model.** In `src/world_engine/models/pipeline.py`, after
   `DayMentionResolution` and before the `# skill_resolution` block, add a
   comment header in the file's style naming `day_mention_choice (the H2
   choice record, schema v2.07, TICKET-0094, BRIEF-0094-A)` and stating
   "append-only, one row per model call, including refused calls (X1b)",
   then `class DayMentionChoice(SQLModel, table=True)` matching C-01
   exactly: `__tablename__ = "day_mention_choice"`; `__table_args__` with the
   two indexes and four `CheckConstraint`s named
   `ck_day_mention_choice_category`, `ck_day_mention_choice_trigger`,
   `ck_day_mention_choice_verdict`, `ck_day_mention_choice_attempts`, plus
   `ck_day_mention_choice_shape` for the combined CHECK; fields in C-01
   order, `candidate_ids` and `evidence_fact_ids` as `str`, `created_at =
   _created_ts()`. Export it from `models/__init__.py` in the
   `from .pipeline import (...)` list, alphabetically.

3. **Writer.** In `src/world_engine/writes/pipeline.py`: import
   `DayMentionChoice` and `json`; add module constants `_CHOICE_TRIGGERS = ("ambiguous",
   "near")`, `_CHOICE_VERDICTS = ("accepted", "rejected", "declined",
   "failed")`; add `_validate_day_mention_choice(record: dict) -> None` and
   `write_day_mention_choices(...)` exactly per C-02, after
   `write_day_rewrite`. Categories reuse `_MENTION_CATEGORIES`. Lists stored
   with `json.dumps(list, ensure_ascii=False)`. Re-export `write_day_mention_choices` from
   `src/world_engine/writes/__init__.py`, next to `write_day_rewrite` (line
   123), in both the import and `__all__` if the file keeps one.

4. **Schema v2.07.** In one commit:
   - `schema_version.py`: `"v2.06"` → `"v2.07"`;
   - `world-engine-schema.md`: header → `Current schema version: v2.07`; a
     new section `### \`day_mention_choice\`` right after the
     `day_mention_resolution` section, with a paragraph (what a row is,
     append-only, written on the 409 path too, read by K1) and C-01's DDL
     verbatim;
   - `world-engine-schema-changelog.md`: newest-first entry
     `- **v2.07** — TICKET-0094, BRIEF-0094-A: \`day_mention_choice\`, the
     H2 choice record (additive table, two indexes, zero rows).`

5. **Migration.** Create `scripts/migrate_v2_07_day_mention_choice.py` as a
   copy of `scripts/migrate_v2_02_skill_resolution.py` with: the docstring
   rewritten for `day_mention_choice` (same paragraphs: what it creates,
   purely additive, idempotent per object, post-check, run line); the
   refusal message naming this file; `_create_day_mention_choice_table()`
   executing C-01's `CREATE TABLE` and both `CREATE INDEX` verbatim; the
   table-existence check, post-check (row count 0, message naming v2.07) and
   `_converge_schema_meta` kept as in the precedent.

6. **Append-only.** In `tooling/verify/checks/day_rewrite.py`,
   `_TRACKED_MODELS` becomes `{"DayRewrite", "DayMentionResolution",
   "DayMentionChoice"}`; W2's docstring names the third model with
   `(TICKET-0094)`. The vacuity guard then requires a `DayMentionChoice(`
   construction, which item 3 provides.

7. **Pure near names.** In `src/world_engine/lore_resolve.py`, move the body
   of `near_candidates` after its regime guard into
   `near_in_surfaces(surface_form, name_surfaces, *, exclude_ids=frozenset())`
   placed immediately above it (C-03), iterating `name_surfaces`. Its
   docstring: `"""Names close to `surface_form` among `name_surfaces` (C-03,
   TICKET-0094): the pure half of `near_candidates`. The caller chose the
   surfaces — and therefore the regime; the day chain passes the perceiver's
   own (Y2b), the creator surfaces pass through `near_candidates`."""`.
   `near_candidates` keeps its signature, docstring and guard, and returns
   `near_in_surfaces(surface_form, surfaces(db, world_id, scope),
   exclude_ids=exclude_ids)`. In the module docstring, after "and so do near
   candidates.", add: `The day chain (TICKET-0094, H2) calls the pure
   `rung_named_partial` and `near_in_surfaces` on the perceiver's own
   surfaces to narrow candidates for a model choice — never as a match.`

8. **Create `tooling/verify/checks/day_mention_choice_store.py`**
   (fixture, temp SQLite; copy `_fresh_engine` and `_world` from
   `checks/identity_tokens.py:108-134`; FAILURES idiom; vacuity guard; one
   `PASS:` line). Cases:
   - S1: a valid `accepted` record and a valid `failed` record write two
     rows; after commit, `candidate_ids` round-trips through `json.loads`.
   - S2: each invalid record raises `ValueError` and adds nothing
     (`db.new` empty): unknown category, unknown trigger, unknown verdict,
     `attempts=3`, `accepted` with `chosen_entity_id=None`, `declined` with
     a chosen id, `candidate_ids` not a list.
   - S3: a batch mixing one valid and one invalid record adds nothing.
   - S4: `write_day_mention_choices(db, ..., records=[])` returns `[]`.
   - S5: inserting through the raw SQL of C-01 an `accepted` row with a NULL
     `chosen_entity_id` fails the DB CHECK (the DB agrees with the writer).
   Parents (FK enforcement is on; flush each before its children): the
   `_world` helper's `World`; `models.Session(world_id=world.id, number=1)`;
   the `Batch` returned by `writes.write_batch(db, session_id=...,
   changed_by="creator")`; a `character` entity from `_world`'s helper; the
   `PassPlay` returned by `writes.write_pass_play(db, batch_id=...,
   session_id=..., character_id=..., declared_action="Je vais voir Maelis.")`.
   Both writers return an unadded row: `db.add` then `db.flush` it.

9. **Create `tooling/verify/checks/day_choice.py`** (docstring: created by A
   with the near cases; B adds narrowing and judge; C adds the call; D adds
   the static route rules). Pure cases on hand-built `NameSurface` tuples:
   Surfaces (all `source="name"`, `fact_id=None`, `entity_name=text`):
   `Maelis` (id `m`, character), `La Reine Grise` (`g`, character),
   `Reine Ysolde` (`y`, character), `Porte de Vesk` (`p`, location).
   - N1: `near_in_surfaces("Maelys", S)` → `[("m", 83)]` as
     `(entity_id, score)`; `near_in_surfaces("reine", S)` →
     `[("g", 63), ("y", 59)]`.
   - N2: `near_in_surfaces("reine", S, exclude_ids=frozenset({"g"}))` →
     `[("y", 59)]`.
   - N3: `near_in_surfaces("Vesk", S)` contains `p` with `entity_type ==
     "location"` (every category counts; the caller filters).
   (Values measured on a prototype of C-03 over `main`'s `lore_resolve`.)

10. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
    `## THE H2 CHOICE RECORD (TICKET-0094) -- EVERY MODEL CHOICE IS STORED WITH ITS REASON (BRIEF-0094-A, schema v2.07)`:
    Y3b, X1b, C-01, the writer's validate-then-construct rule, W2 extended,
    `near_in_surfaces` and why `near_candidates` keeps its guard. Regenerate
    `DECISIONS_INDEX.md`.

## Scope OUT

- `day_choice.py` (the module): B and C. Any route change: D.
- Any change to `near_candidates`' output, guard or callers; to
  `resolve_named`; to `rung_named_partial`.
- Running the migration on prod: Nia (live gate).
- Columns on `day_mention_resolution` (Y3a, rejected); any rebuild.
- K1's reads or UI.

## Invariants to defend

- "Schema is authoritative; a migration bumps constant, doc and
  `schema_meta` together": items 4 and 5 in the same commit.
- "History is sacred": the new table is append-only (item 6).
- Secrets structurally excluded: `near_in_surfaces` sees only the surfaces
  it is given; it never builds a scope.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `schema_partition.py` or `schema_version_agreement.py` needs anything
  beyond items 4's three edits;
- `name_resolution.py` G2 changes result after item 7.

ADAPT:
- `_created_ts` or `_uuid` are named differently in `models/pipeline.py`:
  use the names `DayMentionResolution` uses, report.
- the pass_play fixture needs extra parents: build them as
  `checks/day_concordance_golden.py` does, report which.

REPORT-ONLY:
- other checks that enumerate tables by name and could want the new one.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `git log -1 --format=%s` on the first commit reads the item 1 message,
      and `grep -n "^status:" tooling/tickets/TICKET-0093-*.md` prints `status: done`.
- [ ] `python tooling/verify/checks/day_mention_choice_store.py` → `PASS:` (S1-S5).
- [ ] `python tooling/verify/checks/day_choice.py` → `PASS:` (N1-N3).
- [ ] `python tooling/verify/checks/day_rewrite.py`, `name_resolution.py`,
      `schema_version_agreement.py`, `schema_partition.py` → pass.
- [ ] On a scratch copy of a v2.06 DB: the migration prints the table
      creation and `'v2.06' -> 'v2.07'`; a second run prints "already
      exists"; the cockpit boot guard accepts the DB.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- Schema doc + changelog v2.07 (item 4); `ARCHITECTURE_DECISIONS.md` +
  `DECISIONS_INDEX.md` (item 10). No CLAUDE.md.
