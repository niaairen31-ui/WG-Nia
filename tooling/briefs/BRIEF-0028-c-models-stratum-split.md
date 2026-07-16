<!-- slug: models-stratum-split -->
# BRIEF-0028-c — `models/` package split by schema stratum

Ticket: TICKET-0028 | Danger: none as intent — but this brief touches
the DDL source of truth for every table in the engine; equivalence is
proven, not assumed | Blast radius: large | Depends on: BRIEF-0028-b
merged (`main` @ post-b, verify green)

## Context

Decision C1 (locked): `models.py` (1188 lines / 41 classes / 2
functions, `baselines/module_budget.json`) becomes a `models/` package
split by schema stratum — canon / ephemeral / pipeline-internal — with
`models/__init__.py` re-exporting everything so existing imports freeze.

Rationale correction, stated openly (supersedes the intake wording in
`TICKET-0028-residual-decomposition.md`): the machine reader of the
stratum classification is NOT `schema_partition.py` (that check guards
the hot/cold doc partition). The real readers are
`canon_write_policy.txt` `[CANON_TABLES]` plus the class->table mapping
that `single_canon_write.py:69` (`build_model_tables`) derives by
parsing `models.py`. The canon stratum therefore has a concrete,
enforced consumer; the split makes the file layout mirror what the
policy already distinguishes. C1 stands; the citation moves.

RECON finding this brief must absorb: FIVE checks hard-anchor
`models.py` as a single file —
`single_canon_write.py:24` (`MODELS_FILE`),
`json_ui_boundary.py:34` (`MODELS_PY`, text/regex scan for
`Column(JSON`), `prompt_version.py:47` (scanned-file set),
`world_tick.py:137` (`MODELS_FILE`), `npc_goal_read.py:36` (path list).
All five re-anchor under the 0027-c relocation precedent: assertions
verbatim, location anchors only, one recorded fail-closed proof each.

## Scope IN

1. **Stratum inventory first.** Before moving anything, produce in the
   execution notes a complete table: every SQLModel class in
   `models.py`, its `__tablename__`, and its stratum, derived as:
   canon = table appears in `[CANON_TABLES]`; pipeline-internal =
   prompt/pipeline/approval machinery (`proposed_mutation`, prompt
   tables, batch/window analysis tables); ephemeral = the rest
   (session, gathering, gathering_member, conversation, visit, and
   kin). Ambiguous rows are ESCALATED to Nia before the move, not
   silently classified. This inventory is the first machine-checkable
   completeness pass over the strata — note in the PR description that
   promoting it to a standing verify check is a candidate follow-up
   ticket (out of scope here).

2. **Package layout**:
   - `models/canon.py` — every `[CANON_TABLES]` class.
   - `models/ephemeral.py` — session/scene-lifetime tables.
   - `models/pipeline.py` — proposal queue, prompt store, analysis
     machinery.
   - `models/__init__.py` — re-exports every class, constant, and the 2
     module functions; every existing `from .models import X` /
     `from world_engine.models import X` in `src/` and `scripts/`
     resolves unchanged, byte-identical import statements.
   - The 2 module-level functions and any `text(...)` index definitions
     move with the tables they serve.
   - Cross-stratum foreign keys and string-name relationships are
     expected; keep table registration order deterministic via
     `__init__.py` import order (canon, ephemeral, pipeline) and prove
     equivalence rather than reasoning about it (next item).

3. **Generated-DDL equivalence proof (mandatory, locked at intake).**
   Script (execution-note artifact, may live in the PR only): create a
   fresh SQLite DB from metadata pre-refactor and post-refactor, dump
   normalized `sqlite_master` (`CREATE TABLE` / `CREATE INDEX`, sorted,
   whitespace-normalized), diff. EMPTY DIFF required. Run against the
   live DB path? NO — temp paths only; the live DB is never touched.

4. **Five check re-anchors.** Each check's models anchor becomes the
   set of the three package files (walk `models/*.py`), assertions
   verbatim. One recorded fail-closed proof per check: plant a
   violating instance in a PACKAGE file (e.g. an unattributed
   `Column(JSON` for `json_ui_boundary.py`, a rogue canon write for
   `single_canon_write.py`, a stray version string for
   `prompt_version.py`), observe FAIL, remove. Five proofs, five
   recordings in execution notes.

5. **Baseline shrink.** Remove the `models.py` module entry. Residual
   after this brief: 22 function entries (models.py had none), 1 module
   entry (`entity_author.py`).

## Scope OUT

- Any schema change: zero tables, columns, indexes, or constraints
  added, removed, or altered. This brief moves declarations; v1.79
  stays v1.79 and `schema_partition.py` proves the doc side untouched.
- Any migration script. Any change to `writes/` (post-b) or crud.
- Promoting the stratum inventory to a verify check (logged candidate).
- `entity_author.py` (stage d), remaining residual (stage e),
  deletions (stage f).

## Invariants to defend

- Generated DDL byte-equivalent (normalized) — the one proof that
  dominates all reasoning about SQLModel registration order.
- Import surface frozen across `src/` AND `scripts/` (migrations import
  models; `grep` census in execution notes proving zero import edits).
- `[CANON_TABLES]` untouched; `single_canon_write.py` site count
  unchanged.
- JSON-column allow-list in `json_ui_boundary.py` semantically
  identical: same class.field entries, only the file anchor moves.
- R3/R5/R1: package files within caps unbaselined; no `print()`.
- Full suite green; baselines strictly smaller.

## Done means

### Machine-checkable
- [ ] Stratum inventory complete: every class classified, zero
      unresolved rows (or Nia's escalation answers recorded).
- [ ] DDL equivalence: empty normalized diff, recorded in execution
      notes.
- [ ] Five re-anchored checks green, five fail-closed proofs recorded.
- [ ] `module_budget.py` green: `models.py` entry removed; all three
      package files within caps unbaselined.
- [ ] Import census: zero import-statement edits outside
      `models/__init__.py` itself.
- [ ] Full suite (30 checks) green.

### Live gate (Nia)
- [ ] Cockpit boots, a real world loads, one scene entry + one `/say`
      round-trip, one creator CRUD edit — all unchanged.
- [ ] `backup.py` runs clean against the live DB (it imports models).

## Docs to update

- `TICKET-0028` front-matter: append `BRIEF-0028-c`; ALSO append one
  line to its Clarifications section recording the schema_partition ->
  single_canon_write citation correction (supersede openly, never
  silently).
- Nothing in `world-engine-schema.md` (no schema change).
