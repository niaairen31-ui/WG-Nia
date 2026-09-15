# BRIEF 0087-C — "Backfill the existing subjects, and report what is left"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: BRIEF-0087-a (consumes C-01 and C-02)
Regenerated after AMENDMENT-0087-1 (code `J2`): the `role="subject"` discriminator
is dropped; `fact_participant` is uniquely keyed on `(fact_id, entity_id)`.

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `scripts/apply_ticket_0078_narration_seed.py` exists -> the `apply_ticket_<NNNN>_<slug>.py` convention for a non-DDL pass.
- `scripts/migrate_v2_03_drop_world_magic_status.py` is the highest-numbered migration, and `schema_meta.static_version` reads `v2.03`.
- `scripts/backup.py` exists, with 2-file rotation.
- `src/world_engine/writes/facts.py:57-83` -> `attach_participants(db, *, fact, entity_ids, role=None)`, performing a plain `db.add` per entity with no duplicate check of its own.
- `src/world_engine/models/canon_knowledge.py:119-122` -> `idx_fact_participant_unique` on `(fact_id, entity_id)`, unique.
- `src/world_engine/lore_resolve.py:42-94` -> `normalize_surface`, `rung_named_exact`, `rung_named_token` unchanged.
- Production database: 615 `knowledge` rows, 312 distinct `fact_id`, 310 distinct `subject`, 0 `fact_participant` rows.

## Facts carried

**R-02** — `attach_participants` is the single sanctioned write site for
`fact_participant`; it raises `ValueError` on a typed fact and assigns
`position` in list order from 0. The model declares
`idx_fact_participant_unique` on `(fact_id, entity_id)`, **unique**
(`canon_knowledge.py:119-122`), with `role` outside that key;
`attach_participants` performs a plain `db.add` and carries no duplicate
check of its own, so a second attach for an existing pair raises
`IntegrityError` at commit and aborts the surrounding transaction. Row count
in production: 0.

**R-03** — 615 of 615 production `knowledge` rows point at a free-standing
fact; 312 distinct `fact_id`; 0 orphans. A fact is shared by roughly two
knowers, so a subject attaches once per fact and every knower inherits it —
312 attachments cover 615 rows.

**R-06** — replaying `lore_resolve`'s rungs over production:

| | distinct subjects | knowledge rows |
|---|---|---|
| matched | 69 / 312 (22.1%) | 98 / 615 (15.9%) |
| ambiguous | 0 | 0 |
| unmatched | 243 / 312 (77.9%) | 517 / 615 (84.1%) |

Verkhaal alone: 8 of 36 distinct subjects, 13 of 46 rows.

**R-07** — after a complete backfill, "qui sait quoi sur X" has a non-empty
answer for 42 of 297 active entities (14.1%). On Verkhaal, 6 of 57: Maelis
(6 knowers), La Mer Rouge (2), and four entities with one knower each.

**R-09** — zero ambiguous subjects across all eleven worlds.

**R-16** — `migrate_v<MAJOR>_<NN>_<slug>.py` is for DDL passes;
`apply_ticket_<NNNN>_<slug>.py` is for data and prompt passes carrying no
DDL. Measurement scripts take a bare verb name.

## Contracts

Consumes **C-01** and **C-02** (verbatim copies in BRIEF-0087-a; do not
re-describe them). Produces **C-06**.

### C-06 — the unresolved residue query

```python
def unresolved_subjects(world_id: str, db: Session) -> list[dict]
```

Lives in `subject_resolve.py` beside `C-02`. One row per distinct
`knowledge.subject` in `world_id` whose fact carries **no participant at
all**. Required keys:

```
subject, fact_ids (tuple, sorted), row_count, resolution (SubjectResolution)
```

`resolution` is `C-02`'s verdict for that subject, computed once per distinct
subject, never once per row. Ordered by `row_count` descending, then
`subject` ascending.

This is the one query behind both the backfill's report and the creator
surface's worklist, so the two can never disagree about what is unresolved.

## Context

Existing lore was written before any of this existed. Without a backfill the
selector answers on zero entities at launch, on worlds Nia has been building
for months. Decision C2 chose the backfill; under A2 it is a data pass
through the sanctioned writer, not a migration, so its risk is a fraction of
what the inbound handover assumed.

The measured yield is modest and known in advance: 98 rows, 42 entities. The
point of stating it here is that the run must match it — a number far off
R-06 means something is wrong, not that the world grew.

## Scope IN

1. **`src/world_engine/subject_resolve.py`** — add `unresolved_subjects` per `C-06`, beside `resolve_subject`. Group by distinct `subject` before resolving, so `resolve_subject` runs once per distinct subject and not once per row. World scoping goes in the `select(...).where(...)` via the join to `entity`, never as a post-fetch filter.

2. **`scripts/apply_ticket_0087_subject_participants.py`** — new script.
   - Default mode is **report only**. It prints the per-world table and writes nothing. Running it by accident does nothing.
   - `--apply` performs the writes. `--world <id>` restricts to one world; absent, every world.
   - For each world, walk `unresolved_subjects(world_id, db)`. For every entry whose `resolution.verdict == "matched"`, attach the resolved entity to each of that subject's `fact_ids` through `write_knowledge`'s sibling path — that is, call `attach_participants(db, fact=<fact>, entity_ids=[resolution.entity_id])` directly — **no `role` argument** — with the same read-before-write idempotency guard `C-01` specifies, on `(fact_id, entity_id)` and with no role predicate. The guard is mandatory: `idx_fact_participant_unique` would otherwise raise `IntegrityError` mid-run and abort the pass. `write_knowledge` is not called here: no `knowledge` row is created or edited by this script.
   - Entries whose verdict is `ambiguous` or `unmatched` are left untouched and counted.
   - Print, per world and in total: subjects matched, subjects ambiguous, subjects unmatched, facts attached, knowledge rows now covered, knowledge rows still uncovered.
   - The script refuses to run against a database whose `schema_meta.static_version` is not the version this lot was written against, naming both versions. A schema that has moved is a reason to stop, not to guess.
   - Idempotent end to end: a second `--apply` run attaches nothing and reports the same totals.

3. **No `change_history` entry.** A subject attachment is an index annotation on a fact, not an edit to a `knowledge` row. Writing history for it would pollute the history of every row in the database for a change no creator made.

4. The script prints a one-line instruction to run `scripts/backup.py` before `--apply`, and refuses `--apply` without an explicit `--yes`.

## Scope OUT

- **The dedup guard**, in all three of its forms (`routes/mutations.py:294-311`, `routes/mutations.py:281-282`, `cockpit/mutations.py:73-108`). Untouched.
- **`knowledge.subject`.** No row's `subject` value is edited, normalized, or cleaned. The label stays exactly as authored.
- **Ambiguous and unmatched subjects.** Left null, deliberately. The residue is BRIEF-0087-d's subject, and this script's job is to hand it over, not to guess at it.
- **A third rung.** R-06's 78% unmatched rate is a measured fact about the data, not a defect in `lore_resolve`. Widening `NAMED_RUNGS` would change the day chain's behaviour too and is a decision Nia has not taken.
- **Fuzzy or substring matching.** Explicitly rejected during the decision session: "Relation avec Kaelin Darkshadow" substring-matches the entity "Kael", which is a false positive, and a false subject is worse than a null one.
- **Typed facts.** The 56 relation-typed facts in production carry no `knowledge` rows (R-03) and `attach_participants` would raise on them anyway. The walk never reaches them.
- **`fact.content`.** Not rewritten, not normalized.
- **Any DDL.** No `migrate_` script, no version bump, no changelog column entry.

## Invariants to defend

- **Single canon-write paths.** The script writes `fact_participant` only, only through `attach_participants`. Any direct `db.add(FactParticipant(...))` in the script fails `fact_spine.py`'s AST scan — the scan covers `src/`, so verify whether it also covers `scripts/`; if it does not, the discipline still holds by hand and the deviation is REPORT-ONLY.
- **History is sacred.** No `change_history` is written and none is overwritten. This is a deliberate judgment recorded in Scope IN item 3, not an omission.
- **Fail-closed over advisory.** Default mode writes nothing; `--apply` requires `--yes`; a schema version mismatch refuses the run.
- **Commit before touching any canon-writing path.** The script writes canon rows. Commit before the first edit, and take a backup before the first `--apply` against the production database.

## Decision rights

**STOP:**
- Any anchor above has moved.
- `schema_meta.static_version` on the target database is not `v2.03`.
- The measured matched-subject count on Nia's production database differs from R-06 by more than a handful — that means the resolver, the data, or `C-02` is not what this lot measured.
- `attach_participants` raises on any fact reached by the walk.

**ADAPT:**
- `fact_spine.py`'s AST scan does not cover `scripts/`: keep using `attach_participants` anyway, proceed, report.
- A world contains zero `knowledge` rows: skip it silently in `--apply`, list it with zeros in the report, proceed.
- A `knowledge` row whose `fact_id` has no matching `fact` row: R-03 measured zero of these; if one appears, skip it, count it in a named "orphan" line of the report, proceed, and report.
- The report table is too wide for a terminal: one row per world, wrap rather than drop columns, proceed.

**REPORT-ONLY:**
- The list of the ten highest-`row_count` unmatched subjects per world. This is the worklist BRIEF-0087-d inherits and Nia will want to see it.
- Any subject that matched but looks wrong on inspection.
- Any two distinct subjects resolving to the same entity.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit exists on the branch before the first edit.
- [ ] Running the script with no flags writes nothing: `fact_participant` row count is unchanged afterward.
- [ ] `--apply` without `--yes` refuses and writes nothing.
- [ ] Against a copy of the production database, `--apply --yes` reports **69 subjects matched, 0 ambiguous, 243 unmatched**, and a covered-rows total of **98 of 615**. A different number is a STOP, not a new baseline.
- [ ] After that run, `SELECT COUNT(*) FROM fact_participant` is non-zero, every row's `role` IS NULL, and every row's fact has `relation_id`, `event_id` and `world_law_id` all NULL.
- [ ] A second `--apply --yes` run attaches zero new rows, prints the same totals, and raises no `IntegrityError`.
- [ ] Verkhaal's per-world line reads 8 subjects matched of 36, 13 rows of 46.
- [ ] No `knowledge` row's `subject`, `content`, `level` or `change_history` differs before and after the run.
- [ ] `unresolved_subjects("verkhaal", db)` returns 28 entries after the run, ordered by `row_count` descending.
- [ ] Running against a database whose `schema_meta.static_version` is not `v2.03` refuses and names both versions.
- [ ] `python tooling/run.py` — `fact_spine.py`, `single_canon_write.py`, `module_budget.py`, `function_length.py`, `corpus_gate.py` all PASS.
- [ ] `/review-step` and `/close-step` run; engine code is touched.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: one entry for C2 — a one-off backfill of `fact_participant` rows through `attach_participants`, role left NULL (J2), unambiguous matches only, writing no `change_history` because a subject attachment is an index annotation and not a canon edit. Record the measured yield (98 of 615 rows, 42 of 297 entities) so a future reader knows the feature shipped knowingly partial.
- No schema changelog entry. No version bump.
