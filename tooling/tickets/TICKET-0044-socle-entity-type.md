---
id: TICKET-0044-socle-entity-type
title: Socle entity_type — governed runtime DDL foundation
type: feature
status: live-gate
created: 2026-07-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration, destructive_data]
blast_radius: large
brief_ids: [BRIEF-0044-a, BRIEF-0044-b, BRIEF-0044-f, BRIEF-0044-c, BRIEF-0044-d, BRIEF-0044-e]
schema_version_touched: v1.85-v1.87
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Verkhaal ajoute un constructeur de types d'entites. Ce ticket pose le socle
uniquement : tables `entity_type` et `entity_trait` [voir note P1 ci-dessous],
plus le chemin d'ecriture DDL runtime et ses garanties. Aucune UI, aucun trait
defini, aucune integration IA.

Decisions verrouillees en amont : D2 (materialisation a chaud — le constructeur
cree les tables SQL au runtime, pas via migration Claude Code), E2 (palette de
traits, pas de primitives nues), F1' (fermeture canon-write deplacee du scan AST
statique vers un check runtime fail-closed adosse a une table gouvernee).

Le probleme dur : D2 introduit une troisieme autorite d'ecriture qui modifie la
structure et non le contenu. Trois consequences a trancher :
1. `change_history` snapshot le contenu, pas le schema.
2. un rollback de code trouve des tables qu'il ne connait pas.
3. la version de schema cesse de decrire la base reelle si des tables naissent
   hors migration.

## Clarifications resolved (intake)

**Note P1 — `entity_trait` is NOT in this ticket.** The socle ships the two
registry/history tables `entity_type` + `entity_type_history`, plus the governed
runtime-DDL write path. Trait definitions (`entity_trait` and the five trait
readers) are TICKET-0045 (scope OUT here). The request line naming `entity_trait`
is superseded by this clarification.

**Version delta.** Live `main` head is v1.85 (`world-engine-schema.md:3`), not
v1.81. All version references below use `vX.YY` placeholders; Claude Code owns the
actual numbers and CHANGELOG entries.

**Decision codes locked pre-brief (2026-07-23):**
- **A1** — schema-birth history: dedicated append-only `entity_type_history`
  table (DDL event log carrying `ddl_text` + `definition_snapshot`). Source for
  B1 quarantine and C2 reconciliation.
- **B1** — rollback: quarantine-by-construction. Manifest = `entity_type`; a
  script rebuilds each runtime table WITHOUT its FK to `entity` (SQLite has no
  drop-single-FK), preserving data under `_orphan_ext_*`; roll-forward restore is
  potentially lossy, bounded to rows whose `entity` was deleted during the
  window, and that loss is LOGGED, never silent.
- **C2 (two-plane)** — versioning: a stored `schema_meta` (static-plane version +
  fail-closed boot guard) is kept SEPARATE from the per-world runtime-type
  manifest (`entity_type`). The two planes answer different questions; the
  constructor is structurally forbidden any write path to `schema_meta`.
  Reconciliation ("every physical table in static-set OR entity_type registry")
  is the shared plane-2 reader.
- **Dcol1** — closed, code-owned column-type enum; no free SQL type string ever
  reaches DDL (forced by E2).
- **Dname1** — mandatory `ext_` prefix + identifier validation + collision check;
  the prefix is the structural discriminant for C2 reconciliation and B1.
- **Ddrop1** — CREATE only; destructive `DROP`/`ALTER` forbidden by construction.
  Retire = status flag on `entity_type` (soft-retire), never a `DROP`. Additive
  `ADD COLUMN` is reserved-but-unused at the socle (0045 needs it for add-trait).
- **Dgov1** — reserve the governance columns on `entity_type` NOW, unpopulated
  (reader is 0047/F1'). A named cross-ticket exception to "no structure without a
  reader", accepted to avoid migrating the chantier's central table every
  subsequent ticket.

**Socle scope boundary on the "third authority".** At the socle the constructor
writes STRUCTURE (`CREATE TABLE ext_*`) plus rows into two static
config/history tables (`entity_type`, `entity_type_history`). It performs NO row
write into any `ext_*` table (entities of a runtime type are authored later:
0046 creator CRUD, 0047 AI dispatch). Therefore the F1' runtime write-authority
check for DYNAMIC-table ROW writes is genuinely 0047's concern; the socle does
not yet challenge the canon-write row closure. This boundary is load-bearing and
is asserted in each brief's Scope OUT.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Code-side static schema version constant equals the `world-engine-schema.md`
      `Current schema version:` line  -> verify/checks/schema_version_agreement.py
- [ ] `writes/schema.py` runtime-DDL writer is CREATE-only (no `DROP`/`ALTER`
      token), emits column types only from the closed enum (no free type-string
      interpolation), single-sources the `ext_` prefix, and contains no row write
      to a dynamic table  -> verify/checks/runtime_ddl_guard.py
- [ ] Schema-reconciliation mechanism is present and wired: `schema_reconcile.py`
      defines the accounting functions, derives the static set from
      `SQLModel.metadata` (not a hardcoded literal), single-sources the `ext_`
      prefix, and is imported by the boot guard  -> verify/checks/schema_reconciliation.py
- [ ] Canon-write policy stays closed: `entity_type` + `entity_type_history`
      added to `[CANON_TABLES]`, their only write site is the governed writer
      in `[ALLOWED_SITES]`  -> verify/checks/single_canon_write.py
- [ ] No regression on structure gates  -> verify/checks/function_length.py
- [ ] No regression on structure gates  -> verify/checks/module_budget.py
- [ ] No regression on structure gates  -> verify/checks/import_cycle.py
- [ ] No regression on structure gates  -> verify/checks/undefined_names.py
- [ ] No regression on structure gates  -> verify/checks/no_print_in_src.py

### Live  ->  human gate (Nia)
- [ ] Boot guard: with `schema_meta.static_version` != code constant (or the row
      absent), the app refuses to start with a clear "run migrations" message; on
      match, it starts normally.
- [ ] `create_entity_type(...)` for a throwaway type creates `ext_<slug>`, the
      `entity_type` row, and the `entity_type_history` `type_created` row ATOMICALLY
      — a forced failure mid-operation leaves none of the three.
- [ ] `ext_<slug>` carries `id TEXT PRIMARY KEY REFERENCES entity(id)` and only
      columns drawn from the closed enum.
- [ ] A hand-created stray `ext_zzz` table (no registry row): reconcile CLI exits
      non-zero naming it, and boot refuses; dropping it -> CLI exits 0, boot starts.
- [ ] `scripts/test_rollback_quarantine.py` passes: quarantine produces
      `_orphan_ext_<slug>` without the entity FK, data preserved, original gone,
      history logged; reconciliation stays green; restore re-attaches, and a row
      whose `entity` was deleted during the window is parked in `_orphan_lost_*`
      and reported, never silently dropped.
- [ ] `/review-step` + `/close-step` run for every brief that touches engine code;
      `/verify` green at ticket close.

## Escalations

### E-01 — archived — QUESTION-TICKET-0044.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0044.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0044
Trigger: D1-c (architecture change above BRIEF-0044-c's stated blast_radius)
## Context
BRIEF-0044-c's mini-RECON item 2 instructed: "confirm on this SQLite build
that CREATE TABLE inside an open transaction commits/rolls back atomically
with the row INSERTs (it does; verify the session/engine transaction
boundary so a mid-operation failure rolls back ALL THREE writes)." I
implemented `writes/schema.py::create_entity_type` exactly to spec (Dcol1
closed enum, Dname1 identifier validator, Ddrop1 CREATE-only, the two
INSERTs) and then ran the brief's own "Done means" live-gate check — force
a failure between the DDL and the second INSERT, confirm none of the three
writes survive.

**The mini-RECON's "(it does)" is false on this codebase's actual engine.**
Minimal reproduction, bypassing my module entirely:
```python
with engine.connect() as conn:
    trans = conn.begin()
    conn.execute(text("CREATE TABLE ext_raw (id TEXT PRIMARY KEY)"))
    conn.execute(text("INSERT INTO ext_raw (id) VALUES ('x')"))
    trans.rollback()
# after rollback: inspect(engine).has_table("ext_raw") == True
# but SELECT * FROM ext_raw returns zero rows
```
The `CREATE TABLE` survives `rollback()`; the `INSERT` correctly does not.
Full `create_entity_type` smoke test confirms the same: happy path,
collision rejection, and bad-`col_type` rejection (no partial write) all
pass, but the forced-mid-operation-failure case leaves `ext_ghost` behind
as an orphan table with no `entity_type` row — exactly the state A1 exists
to prevent.

**Root cause.** Python's stdlib `sqlite3` driver (pysqlite, used under
SQLAlchemy) only auto-manages transactions around DML by default; DDL
statements implicitly commit any pending transaction and run outside it,
unless the engine explicitly disables the driver's isolation handling and
issues its own `BEGIN` — SQLAlchemy's documented "transactional DDL on
SQLite" recipe (`isolation_level = None` on connect +
`conn.exec_driver_sql("BEGIN")` on the `"begin"` event). `src/world_engine/
db.py`'s `engine` has no such configuration today — only the
`PRAGMA foreign_keys=ON` connect listener (`db.py:45-52`).

This means A1 — the load-bearing invariant BRIEF-0044-c is built around —
cannot hold today, regardless of how `writes/schema.py` is written. The fix
is well-understood, but it touches `db.py`'s shared engine setup, which
governs transaction behavior for every canon-write path in the app, not
just this one — outside BRIEF-0044-c's Scope IN (which lists only
`writes/schema.py`, `canon_write_policy.txt`, and the new
`runtime_ddl_guard.py`).

Everything else in BRIEF-0044-c is complete and verified green in the
working tree, uncommitted pending this decision: `writes/schema.py`
(happy path, collision, bad-`col_type` all smoke-tested correct),
`runtime_ddl_guard.py` (red-path tested: catches an injected DROP/ALTER
token and a duplicate `"ext_"` literal, both confirmed to turn it red and
back to green on removal), `canon_write_policy.txt`,
`ARCHITECTURE_DECISIONS.md`, `CLAUDE.md` (still exactly 500 lines, contract
check green), and the schema changelog applicatif addendum. `single_canon_
write.py`, `function_length.py`, `module_budget.py`, `import_cycle.py`,
`undefined_names.py`, `no_print_in_src.py` all pass.

## Question
How should the A1 atomicity gap be resolved — and is the `db.py` engine
fix in scope for this brief, a follow-up brief in the same ticket, or a
separately ticketed change?

## Options
A. Fix `db.py` now, inside BRIEF-0044-c: add the standard SQLAlchemy
   pysqlite transactional-DDL recipe (`isolation_level = None` on connect,
   explicit `BEGIN` on the `"begin"` event) to `engine`. Well-understood,
   low-risk per SQLAlchemy's own docs, but changes transaction behavior for
   every existing canon-write path in the same commit as the new writer —
   a blast-radius expansion beyond this brief's stated Scope IN.
B. Same fix, but as a new BRIEF-0044-f (or a follow-up ticket) scoped
   specifically to `db.py`'s transactional-DDL boundary, reviewed and
   verified independently of BRIEF-0044-c's other changes — keeps this
   brief's diff to exactly its stated files.
C. Narrow A1's claim instead of fixing the engine: accept that on this
   SQLite build, a CREATE TABLE that succeeds is not undone by a later
   row-insert failure in the same call; treat the resulting orphan
   `ext_*` table (with no `entity_type` row) as a case for BRIEF-0044-d's
   reconciliation / BRIEF-0044-e's quarantine to catch and report, rather
   than something `create_entity_type` itself must prevent. Requires
   rewording A1's docstring/doc claims from "all three commit together or
   none do" to the weaker guarantee actually deliverable today.
## Response
B - separate brief. Confirmed 2026-07-23: the db.py transactional-DDL fix
landed as its own BRIEF-0044-f (scoped to db.py's transactional-DDL
boundary, independently reviewed/verified), keeping BRIEF-0044-c's diff to
exactly its stated Scope IN. BRIEF-0044-c was then re-run against the
fixed engine and completed clean. Chain resumes at BRIEF-0044-d.
~~~~
