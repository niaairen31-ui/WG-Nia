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
