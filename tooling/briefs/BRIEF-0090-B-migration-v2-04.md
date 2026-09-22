# BRIEF 0090-B — "migration v2.04"

Lot: LOT-0090-oriented-relations.md (authoritative on conflict)
Depends on: BRIEF-0090-A (imports C-01, C-02, C-03, C-04)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/relation_orientation.py` exists and exports
  `lien_fact_content`, `connects_to_fact_content`, `is_social`,
  `RELATION_GRAPH_EXCLUDED_TYPES`, `orient_legacy`, `OrientedSpec`
  (brief A).
- `src/world_engine/schema_version.py` — `EXPECTED_STATIC_SCHEMA_VERSION`
  is `"v2.03"`.
- `world-engine-schema.md:3` — `Current schema version: v2.03`.
- `models/canon_knowledge.py:23-53` — `Relation.__table_args__` holds one
  CHECK (`intensity`) and three plain indexes.
- `scripts/migrate_v2_00_connects_to_facts.py:50-200` — the migration
  pattern: `sys.path.insert` for `src`, fail-closed on missing
  `WORLD_ENGINE_ENV`/`WORLD_ENGINE_DATABASE_URL`, `engine.raw_connection()`,
  explicit `BEGIN`/`COMMIT`/`ROLLBACK`, post-checks before commit, then
  `_converge_schema_meta()`.
- Prod snapshot to reproduce before writing anything (report the numbers; do
  not abort if they differ, they are a fingerprint, not a gate): social rows
  `a_to_b` 92, `b_to_a` 14, `mutual` 67; `a_to_b` with `visible_to_b=1`: 40;
  `b_to_a` with `visible_to_b=1`: 6; `connects_to` without a fact: 2.

## Facts carried

**R-01** — `relation` has no CHECK on `direction`, no unique index, and
`change_history` is JSON NOT NULL (`models/canon_knowledge.py:23-53`).

**R-13** — `migrate_v2_00_connects_to_facts.py` inserted one fact per
`connects_to` edge with content `"{name_a} communique avec {name_b}."`,
`default_level='knows'`, `created_by='migrate_v2_00'`, skipping any edge
that already had one, and post-checked with a checksum of the whole
`relation` table.

**R-14** — `knowledge` requires `fact_id` NOT NULL and `subject` NOT NULL
(`models/canon_knowledge.py:182-218`).

**R-19** — on directed rows the `visible_to_b` value passed a review surface
(`TICKET-0036:40-43`, `seed_pilot.py:1664`, `LinkAgent.svelte:150-151`); on
`mutual` rows it carries no information.

**R-20** — on a `b_to_a` row, "Visible to B" names the side that already
feels, and no code fixes the meaning (`crud/_shared.py:148`, plus the
absence of any play reader).

**R-23** — `_append_history_snapshot` (`writes/_shared.py:25-41`) records
`intensity`, `last_evolved_at` and `mutation_id` only — no endpoints, no
direction. The migration writes its own entry shape.

**R-25** — prod, 2026-09-22: `a_to_b` 52 FALSE / 40 TRUE, `b_to_a` 8 FALSE /
6 TRUE, `mutual` 67 TRUE / 0 FALSE; 2 `connects_to` edges without a fact.

**E-2** (RECON-0090 §6) — on SQLite 3.45.1, a partial unique index on
`relation(entity_a_id, entity_b_id) WHERE type NOT IN ('connects_to',
'controls')` accepts A->B and B->A and two `connects_to` rows on the same
pair, and rejects a second social A->B. It needs `CREATE INDEX` only, no
table rebuild.

## Contracts

Consumed verbatim from the lot header:

### C-01 — `lien_fact_content(name_a, relation_type, name_b) -> str`
`f"{name_a} éprouve « {relation_type} » envers {name_b}."`

### C-02 — `connects_to_fact_content(name_a, name_b) -> str`
`f"{name_a} communique avec {name_b}."`

### C-03 — `is_social(relation_type) -> bool`, and
`RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "controls")`.

### C-04 — `orient_legacy(direction, entity_a_id, entity_b_id, visible_to_b)`
| direction | visible_to_b | returns |
|---|---|---|
| `a_to_b` | True | `[(a, b, True, False)]` |
| `a_to_b` | False | `[(a, b, False, False)]` |
| `b_to_a` | True | `[(b, a, False, True)]` |
| `b_to_a` | False | `[(b, a, False, False)]` |
| `mutual` | either | `[(a, b, False, False), (b, a, False, False)]` |
| anything else | any | `ValueError` naming the value |

Produced by this brief:

### C-12 — the partial unique index
Name `idx_relation_oriented_social`, declared in
`models/canon_knowledge.py`'s `Relation.__table_args__` and created by the
migration:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_relation_oriented_social
  ON relation(entity_a_id, entity_b_id)
  WHERE type NOT IN ('connects_to','controls');
```

## Context

Brief A made the writer refuse a social row that is not `a_to_b` and give
every new social relation its lien fact. Production still holds 67 `mutual`
and 14 `b_to_a` social rows, 173 social rows with no fact at all, and 2
`connects_to` edges without one. This brief moves the data and closes the
schema.

## Scope IN

1. `models/canon_knowledge.py`: add C-12 to `Relation.__table_args__`, with
   a comment naming TICKET-0090 and stating that the partial predicate is
   the same social/structural split as
   `relation_orientation.RELATION_GRAPH_EXCLUDED_TYPES`, re-typed here only
   because SQLite index predicates cannot import Python.
2. `src/world_engine/schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION`
   becomes `"v2.04"`.
3. `world-engine-schema.md`: header `Current schema version: v2.04`; in the
   `relation` section, a NOTE stating that a social relation is always
   `direction='a_to_b'` with `entity_a` the perceiver, that
   `idx_relation_oriented_social` allows at most one social row per oriented
   pair, that every social relation carries exactly one typed `lien` fact,
   and that `visible_to_b` is dead weight kept for one ticket — the fact's
   knowledge rows carry who knows.
4. `world-engine-schema-changelog.md`: an append-only v2.04 entry naming the
   index, the orientation normalization, the lien facts, the 40 converted
   knowledge rows and the 2 backfilled `connects_to` facts.
5. `scripts/migrate_v2_04_oriented_relations.py`, following the v2.00
   pattern anchor for anchor, importing C-01 to C-04 from
   `world_engine.relation_orientation` (never re-typing a template or the
   excluded set), in one transaction, in this order:
   - **S0 snapshot** — count social rows by direction and `visible_to_b`;
     capture the id set of `a_to_b` rows with `visible_to_b=1` and of
     `b_to_a` rows with `visible_to_b=1` BEFORE any change.
   - **S1 pre-check** — compute the oriented pairs the run will produce and
     abort (ROLLBACK + SystemExit) if any `(entity_a_id, entity_b_id)`
     appears twice among social rows, listing the offenders. An unknown
     `direction` value anywhere in social rows aborts the same way.
   - **S2 `b_to_a`** — swap `entity_a_id`/`entity_b_id`, set
     `direction='a_to_b'`, and append to `change_history` the entry
     `{"migration": "v2.04", "was": {"entity_a_id": …, "entity_b_id": …,
     "direction": "b_to_a"}}`.
   - **S3 `mutual`** — set `direction='a_to_b'` on the row with the same
     history entry shape (`"direction": "mutual"`), then insert its mirror:
     a new uuid, endpoints swapped, same `world_id`, `type`, `intensity`,
     `notes`, `visible_to_b`, `created_at` and `last_evolved_at`, and
     `change_history` `[{"migration": "v2.04", "split_from": "<id>"}]`.
   - **S4 lien facts** — one `fact` per social relation that has none:
     `content` from C-01 with both entity names read from `entity`,
     `default_level='unaware'`, `created_by='migrate_v2_04'`.
   - **S5 `connects_to` backfill** — one `fact` per `connects_to` relation
     that has none: content from C-02, `default_level='knows'`,
     `created_by='migrate_v2_04'`.
   - **S6 converted visibility (U3)** — for each id captured in S0 as
     `a_to_b` + `visible_to_b=1`, insert one `knowledge` row for that row's
     `entity_b_id` on its lien fact: `subject` and `content` = the fact's
     content, `level='knows'`, `source='migrate_v2_04 (visible_to_b)'`,
     `share_threshold=50`, `is_incorrect=0`, `is_secret=0`,
     `change_history='[]'`. Skip any pair that already has a row.
   - **S7 index** — C-12.
   - **S8 report** — print: rows swapped, rows split, lien facts inserted,
     `connects_to` facts inserted, knowledge rows inserted; then two lists.
     First, every `b_to_a` id captured in S0 with `visible_to_b=1`
     (perceiver name, target name), under a line saying their visibility was
     not converted because the flag has no defined meaning on that shape and
     that the sheet's "X le sait" control sets it. Second, every converted
     row whose target entity is a player character, under a line saying the
     player now knows that feeling.
   - **S9 post-checks** — before COMMIT: zero social rows with
     `direction != 'a_to_b'`; every social row has exactly one fact; every
     `connects_to` row has exactly one fact; `controls` rows have none; the
     social row count equals S0's social count plus the `mutual` count; the
     knowledge count equals S0's captured `a_to_b`+TRUE count; the index
     exists in `sqlite_master`. Any failure: ROLLBACK and SystemExit naming
     the numbers.
   - **S10** — `_converge_schema_meta()`, copied from v2.00.
6. Idempotence: a second run inserts nothing, swaps nothing, and prints
   zeros — every step is guarded by `WHERE NOT EXISTS` or by the already
   normalized `direction`.
7. `tooling/standards/ARCHITECTURE_DECISIONS.md`: one entry for TICKET-0090
   — perceiver orientation, one social row per oriented pair, the lien fact
   as the relation's knowable face, `visible_to_b` retired into knowledge
   with the U3 split (directed TRUE converted, `b_to_a` reported, `mutual`
   ignored), and the cascade delete as a named exception to "History is
   sacred", in the same family as the `skill_definition` delete
   (CLAUDE.md:288-292).

## Scope OUT

- Any route, payload or renderer: brief C.
- Any frontend file or build: briefs D and E.
- The link agent: brief E.
- Dropping `relation.visible_to_b` — the column stays; the changelog says
  so.
- Touching `controls` rows in any way.
- Re-writing the lien content of a relation whose entity was renamed (F1's
  job, later ticket).
- Any change to `writes/` — brief A owns the writer; if the migration needs
  a behaviour the writer lacks, that is a STOP.

## Invariants to defend

- **Schema is authoritative, and the version moves in one commit:** the
  constant, the doc header, the changelog entry and the migration land
  together, or `schema_version_agreement.py` fails.
- **History is sacred:** every row this migration changes gets its previous
  endpoints and direction appended to `change_history` (R-23's shape does
  not cover them, so the entry is written by hand).
- **Commit before touching canon-write paths.** This brief writes canon.
- **`connects_to` is map topology:** the backfill gives it the same content
  and `default_level` v2.00 used, so reachability behaviour is restored, not
  invented.

## Decision rights

STOP:
- Any anchor above has moved, or `relation_orientation.py` does not export
  what C-01 to C-04 name.
- S1 finds a duplicate oriented pair, or a `direction` value outside the
  three.
- A social relation is found with more than one typed fact.
- The migration would need a change in `writes/` to work.

ADAPT (do it, then report):
- The prod counts differ from R-25: proceed, print both, and say so — the
  numbers are a fingerprint, not a gate.
- An entity referenced by a relation is missing or soft-deleted, so C-01
  cannot render a name: use the entity id in place of the name for that fact
  and list those relations in S8.
- `_converge_schema_meta` has drifted since v2.00: copy the current shape
  from the newest migration script in `scripts/`.
- SQLite refuses the partial index syntax on the running version: report the
  version and use a full unique index ONLY if no `connects_to`/`controls`
  pair is duplicated; otherwise STOP.

REPORT-ONLY:
- Rows whose `notes` is NULL (nothing to carry).
- Any `controls` relation without a fact (expected, by design).
- The `mutual` `visible_to_b` values dropped on the floor (67, all TRUE).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python scripts/migrate_v2_04_oriented_relations.py`
      on a COPY of the production database prints the S8 report and every
      S9 post-check passes.
- [ ] Re-running it on the same copy prints zeros everywhere and changes no
      row (verified by a `relation`+`fact`+`knowledge` count before and
      after).
- [ ] On that copy: `SELECT COUNT(*) FROM relation WHERE type NOT IN
      ('connects_to','controls') AND direction != 'a_to_b'` returns 0.
- [ ] On that copy: every social relation has exactly one `fact`, and
      `SELECT COUNT(*) FROM knowledge WHERE source = 'migrate_v2_04
      (visible_to_b)'` equals the S0 count of `a_to_b` + `visible_to_b=1`.
- [ ] The S8 report lists the 6 `b_to_a` TRUE rows by name.
- [ ] `python tooling/verify/checks/schema_version_agreement.py` prints PASS.
- [ ] `python tooling/verify/checks/corpus_gate.py` — every check executed
      and passed.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `world-engine-schema.md` header and `relation` NOTE (Scope IN 3).
- `world-engine-schema-changelog.md` v2.04 entry (Scope IN 4).
- `tooling/standards/ARCHITECTURE_DECISIONS.md` (Scope IN 7).
