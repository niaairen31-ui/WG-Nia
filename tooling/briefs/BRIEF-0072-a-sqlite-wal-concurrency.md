# BRIEF — Step "SQLite WAL concurrency posture"

TICKET-0072. Single brief: one commit for the engine change plus its check,
one separate commit if and only if the conditional fix in Scope IN item 6 is
triggered.

## Context

`db.py:90` and `db.py:100` (BRIEF-0044-f) made every transaction explicit so
DDL could not escape a rollback. Under the default rollback journal, that also
turned every read into a `SHARED` lock held for the life of its transaction.
The request session bound at `routes/play.py:171` outlives its handler because
`routes/play.py:190` returns a `StreamingResponse`, so it holds that lock for
the entire SSE turn; the nested `Session(engine)` at `play.py:609-617` can
INSERT but cannot COMMIT, and Play dies on the first NPC line of every
conversation. Eleven nested-session sites across the four Play modules carry
the same defect. This step makes readers stop blocking writers, structurally,
without giving back the DDL atomicity BRIEF-0044-f bought.

## Mini-RECON — verify before writing

Report `file:line` for each. **STOP and escalate** if any does not hold; do not
adapt the brief silently.

1. `db.py:83-93` — the connect listener is `_enable_sqlite_foreign_keys`,
   guarded by `engine.dialect.name == "sqlite"`, sets
   `dbapi_connection.isolation_level = None` (line 90) and executes
   `PRAGMA foreign_keys=ON` (line 92) on a cursor it closes. Confirm the guard
   and the cursor lifecycle before adding statements to it.
2. `db.py:96-100` — the `"begin"` listener is registered on the `engine`
   INSTANCE (`@event.listens_for(engine, "begin")`), not on the `Engine` class.
   Confirm; the two listeners have different registration scopes and the check
   in item 5 reads both.
3. Confirm `db.py` has no existing `journal_mode` or `busy_timeout` statement
   and that `_connect_args` (`db.py:70-72`) sets only `check_same_thread`.
4. The installed SQLAlchemy and SQLModel versions. Report them. BRIEF-0044-f's
   ADR entry records 2.0.50 / 0.0.38; this brief's reproduction ran on
   2.0.52 / 0.0.39. If the installed pair differs from BRIEF-0044-f's, say so
   in the report — it does not block, but it belongs in the record.
5. Confirm `tooling/verify/checks/corpus_gate.py` discovers checks by
   `CHECKS.glob("*.py")` (`corpus_gate.py:167`, re-globbed at
   `corpus_gate.py:229`), so a new file needs no registration, and that
   `TIMEOUT_SECONDS` is 15 (`corpus_gate.py:53`). The new check must finish
   well inside that; the reference prototype ran in under one second.
6. Confirm `scripts/backup.py:88-93` uses `source.backup(target)` — SQLite's
   online backup API — and not a filesystem copy. WAL keeps recent commits in
   a sidecar file until checkpoint, so a plain `shutil.copy` of the `.db`
   would silently start producing incomplete backups. If it is not the online
   API, STOP and escalate: the backup story becomes part of this ticket.
7. REPORT ONLY, do not fix: grep the tree for any other place that copies,
   moves, deletes or archives the SQLite carrier file by path (scripts, docs,
   `Activate.ps1`, CI). Under WAL the carrier is three files, not one. Report
   what you find with `file:line`; TICKET-0072 does not change them.

## Scope IN

1. **`src/world_engine/db.py` — module-level policy constants.** Insert
   immediately before the connect listener (currently `db.py:82`), verbatim:

   ```python
   # TICKET-0072 (BRIEF-0072-a). The concurrency posture, declared once here and
   # read structurally by tooling/verify/checks/sqlite_concurrency.py.
   #
   # BRIEF-0044-f made every transaction explicit (isolation_level = None plus an
   # explicit BEGIN) so DDL could not escape a rollback. Unintended consequence
   # under the default rollback journal: a SELECT now holds a SHARED lock for the
   # life of its transaction. A request-scoped session that outlives its handler
   # -- which is exactly what a StreamingResponse does -- therefore holds that
   # lock for the whole stream, and a second Session(engine) opened inside the
   # stream can INSERT but cannot COMMIT: promotion to EXCLUSIVE waits on the
   # reader, exhausts the busy timeout, and raises "database is locked". That is
   # every Play turn.
   #
   # WAL removes the conflict at its root -- readers never block writers -- and
   # leaves BRIEF-0044-f's transactional-DDL guarantee intact (re-proved by
   # scripts/test_ddl_atomicity.py, unmodified). busy_timeout is declared here
   # rather than inherited from pysqlite's 5.0s default, so the value is owned by
   # this module instead of by the driver, and is readable by the check.
   _SQLITE_JOURNAL_MODE = "WAL"
   _SQLITE_BUSY_TIMEOUT_MS = 5000
   # An in-memory database reports 'memory' and cannot be WAL. Nothing in the
   # tree binds one today, but WORLD_ENGINE_DATABASE_URL can express one, so the
   # accepted set is declared rather than assumed.
   _SQLITE_JOURNAL_MODES_OK = ("wal", "memory")
   ```

2. **`src/world_engine/db.py` — extend the connect listener.** Inside
   `_enable_sqlite_foreign_keys`, after the existing
   `cursor.execute("PRAGMA foreign_keys=ON")` (line 92) and before
   `cursor.close()`, add the busy timeout and the journal mode, then fail closed
   on an unexpected mode. The existing `PRAGMA foreign_keys=ON` line, the
   dialect guard and the docstring's first sentence are unchanged; append to the
   docstring rather than rewriting it.

   ```python
           cursor.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
           journal_mode = cursor.execute(
               f"PRAGMA journal_mode={_SQLITE_JOURNAL_MODE}"
           ).fetchone()[0]
           cursor.close()
           if str(journal_mode).lower() not in _SQLITE_JOURNAL_MODES_OK:
               raise RuntimeError(
                   f"SQLite journal_mode is {journal_mode!r}, expected one of "
                   f"{_SQLITE_JOURNAL_MODES_OK}. Under a rollback journal, a "
                   "streaming request session's read lock blocks every nested "
                   "write commit (TICKET-0072). Refusing the connection rather "
                   "than serving a Play surface that cannot persist a turn."
               )
   ```

   Order matters and is not negotiable: both PRAGMAs must run at connect time,
   before any `BEGIN`, exactly as `PRAGMA foreign_keys=ON` already does —
   `journal_mode` cannot be changed inside a transaction. The single existing
   `cursor.close()` call moves above the raise so the cursor is released on the
   failure path too; do not add a second one.

3. **`src/world_engine/db.py` — module docstring.** Append one paragraph after
   the existing transactional-DDL paragraph, verbatim:

   ```
   Concurrency posture (TICKET-0072): the carrier runs in WAL. Readers never
   block writers there, which is what makes the nested-session persist pattern
   in the Play stream legal -- a request session holding an open read
   transaction for the life of an SSE response cannot stall a second session's
   commit. WAL is a persistent property of the database file, re-asserted on
   every connect and verified fail-closed; the busy timeout is declared here
   rather than inherited from the driver default.
   ```

4. **`tooling/verify/checks/sqlite_concurrency.py`** — new fail-closed check.
   Same idiom as `legacy_mount.py` and `corpus_gate.py`: module-level
   `FAILURES`, `fail()`, `_report_and_exit(counts)`, `ROOT` via `parents[3]`,
   stdlib plus `sqlalchemy`/`sqlmodel` only (both already in
   `corpus_gate.REQUIRED_TOOLS`), no subprocess. It must set
   `os.environ["WORLD_ENGINE_DATABASE_URL"]` to a file under
   `tempfile.gettempdir()` **before** importing `world_engine.db`, exactly as
   `scripts/test_ddl_atomicity.py:31-34` does, so it is independent of
   `WORLD_ENGINE_ENV` and can never touch the prod or test carrier. Delete the
   scratch file and its `-wal` / `-shm` sidecars at start and at end. Four
   rules:

   - **rule1 — the posture is declared.** AST-parse `db.py` (never regex, same
     discipline as `legacy_mount.py:18-19` and `single_canon_write.py`). Assert
     `_SQLITE_JOURNAL_MODE`, `_SQLITE_BUSY_TIMEOUT_MS` and
     `_SQLITE_JOURNAL_MODES_OK` exist as module-level literal assignments; that
     `_SQLITE_JOURNAL_MODE.lower() == "wal"`; that `_SQLITE_BUSY_TIMEOUT_MS` is
     an `int` greater than zero; and that the body of
     `_enable_sqlite_foreign_keys` references both of the first two names. A
     missing constant, a non-literal value, or a listener that no longer reads
     them is a FAILURE.
   - **rule2 — the posture is effective.** Open a connection from the imported
     engine and assert `PRAGMA journal_mode` returns `wal` and
     `PRAGMA busy_timeout` returns `_SQLITE_BUSY_TIMEOUT_MS`. Reading the value
     back from the driver, not from the source, is the point: rule1 proves it is
     written, rule2 proves it arrived.
   - **rule3 — a reader does not block a writer.** Create a scratch table.
     Session A: INSERT, commit, then SELECT — reproducing `play.py:136` followed
     by `play.py:143`. **Vacuity guard, before anything else:** assert A is
     genuinely inside an open transaction, both at the SQLAlchemy level
     (`A.connection().in_transaction()`) and at the driver level
     (`.connection.dbapi_connection.in_transaction`). Both were measured `True`
     under this configuration; if either is `False` the reader is holding
     nothing and the rest of the rule proves nothing — that is a FAILURE, never
     a pass. Then, with A still open, session B INSERTs and commits. Assert the
     commit succeeds and took under one second: a pass that consumed the busy
     timeout won a race rather than avoiding a conflict.
   - **rule4 — the instrument can see red.** Repeat rule3's shape on a second
     scratch file left in rollback-journal mode, using raw `sqlite3`
     connections with `timeout=0.2` so the failure is fast and the engine's own
     configuration is untouched. Assert the nested COMMIT **raises**
     `sqlite3.OperationalError`. If it succeeds, the harness cannot detect the
     defect this ticket exists to close and the whole check is vacuous — that
     is a FAILURE. Measured at 0.20s in the reference prototype.

   Success report line, matching the corpus style:
   `PASS: sqlite_concurrency — journal_mode=wal, busy_timeout=Nms declared and effective, nested commit under an open read in Xms, counterfactual red`

5. **`scripts/test_ddl_atomicity.py`** — run it, do not edit it, do not copy any
   of its assertions into the new check. It is the regression proof that
   BRIEF-0044-f's guarantee survived. Report its verdict in the execution
   report.

6. **Conditional fix, narrow.** IF and ONLY IF mini-RECON item 6 finds that
   `scripts/backup.py` does not use SQLite's online backup API: STOP, escalate,
   and do not proceed. Do not repair `backup.py` inside this commit. Every other
   finding from mini-RECON item 7 is REPORT ONLY.

7. **`world-engine-schema-changelog.md`** — an applicatif addendum entry, no
   schema change, following BRIEF-0044-f's own entry as the model: what broke,
   the exact PRAGMAs added, that DDL atomicity was re-proved unmodified, and
   the new check's name.

8. **`ARCHITECTURE_DECISIONS.md`** — append an entry. It must record: WAL as a
   structural property of this engine and the reader/writer invariant it buys;
   that the nested `Session(engine)` persist pattern across the Play modules is
   legal *because of* that invariant rather than by luck; that BRIEF-0044-f is
   preserved, not traded; the process lesson (an engine-wide transaction-semantics
   change alters every concurrent path, and BRIEF-0044-f's verification surface
   was DDL, migrations and `init_db.py` only — thorough within a frame that was
   itself the defect); and the honest limit — **this check proves a reader does
   not block a writer; it does not prove that no path holds an open WRITE
   transaction across a nested commit**, which WAL would not save.

## Scope OUT

- **`PRAGMA synchronous`.** Do not touch it. WAL with the default `FULL` is the
  durable setting; `NORMAL` is the common performance tweak and it trades away
  recent commits on power loss. History is sacred; the crash is not a
  performance problem.
- **Refactoring the nested-session pattern.** All eleven sites
  (`play.py:266`, `play.py:609`, `play_stream.py:116`, `play_stream.py:133`,
  `play_physical.py:266`, `play_physical.py:324`, `play_physical.py:333`,
  `play_physical.py:395`, `play_initiative.py:203`, `play_initiative.py:207`,
  `play_initiative.py:250`) stay exactly as they are. Their independent commit
  boundaries are deliberate.
- **The snapshot-staleness defect (decision B1).** The request session is pinned
  to a read snapshot from its first read until it commits, so `ctx.db` reads
  cannot see rows written by nested sessions in the same turn. Measured, real,
  silent, and NOT fixed here. Do not add a `rollback()`, a `refresh()`, an
  `expire_all()` or a session-scope change anywhere to chase it. Report only.
- **The stale comment at `play_initiative.py:200-204`** ("no open write
  transaction ... so there is no nested-transaction conflict"). It documents an
  invariant BRIEF-0044-f invalidated. Correcting it belongs with the B1 ticket,
  where the reader audit happens. Do not edit it.
- **Reverting or narrowing BRIEF-0044-f** (decision A3, rejected). The explicit
  `BEGIN` listener and `isolation_level = None` both stay engine-wide.
  Reactivation condition: WAL is measured to be unavailable or unsafe on the
  carrier filesystem.
- **Ending the request session's transaction before the stream** (decision A2,
  rejected). Do not add a `db.commit()` or `db.rollback()` at the end of
  `_say_prepare_turn`, and do not convert `ctx.db` reads inside the stream to
  nested sessions.
- **A single session per turn** (decision A4, rejected).
- **`scripts/backup.py`, `Activate.ps1`, and any other carrier-file consumer.**
  Mini-RECON item 7 reports them; nothing changes.
- **Anything in `frontend/`.** No surface, no bundle, no stylesheet.
- **Schema, canon-write paths, mutation gating, prompts.** Untouched.
  `_apply_mutation` is not read, not called, not referenced.

## Invariants to defend

- **Transactional DDL (BRIEF-0044-f).** The guarantee this brief is most likely
  to threaten, since it edits the very listener that implements it. Defended by
  running `scripts/test_ddl_atomicity.py` unmodified, and by leaving both
  listeners' existing statements byte-identical.
- **Fail-closed, never fail-open.** An unexpected `journal_mode` refuses the
  connection. A check that cannot parse `db.py`, cannot import the engine, or
  finds a constant missing FAILS; none of its four rules may pass by finding
  nothing.
- **Vacuous-proof.** rule3's transaction guard and rule4's counterfactual are
  the heart of the check — a concurrency proof where nothing was actually
  contended is the textbook vacuous pass. Demonstrate each firing individually,
  not just the aggregate verdict.
- **Structural over disciplinary.** The posture is declared in constants and
  verified from the driver, never left as a fact someone must remember about
  the database file.
- **AST, never regex, for Python constants.**
- **One implementation per rule.** The new check does not re-assert DDL
  atomicity; `scripts/test_ddl_atomicity.py` owns that. It does not re-assert
  foreign keys; that is already covered.
- **No canon-write, no schema.** Engine configuration only.

## Done means

- [ ] `python scripts/backup.py` run BEFORE any code change (danger_class: db_write), backup path reported
- [ ] Mini-RECON items 1-7 reported with `file:line`, including the installed SQLAlchemy / SQLModel versions and item 7's carrier-file consumer list
- [ ] `WORLD_ENGINE_ENV=test PYTHONPATH=src python tooling/verify/checks/sqlite_concurrency.py` returns PASS, report line showing `journal_mode=wal`, the declared timeout, and a sub-second nested-commit measurement
- [ ] The check's own runtime is reported and is under 15s (`corpus_gate.TIMEOUT_SECONDS`)
- [ ] It returns FAIL when `_SQLITE_JOURNAL_MODE` is temporarily set to `"DELETE"` (demonstrate, revert)
- [ ] It returns FAIL when the `PRAGMA journal_mode` line is temporarily removed from the connect listener (demonstrate, revert)
- [ ] It returns FAIL when rule3's vacuity guard is temporarily inverted, i.e. the reader is made to hold no open transaction (demonstrate, revert)
- [ ] It returns FAIL when rule4's counterfactual database is temporarily switched to WAL, i.e. the instrument is blinded (demonstrate, revert)
- [ ] `python scripts/test_ddl_atomicity.py` passes, file untouched (`git diff --stat` shows it unchanged)
- [ ] `python scripts/init_db.py` against a scratch `WORLD_ENGINE_DATABASE_URL` still creates a virgin database; table count reported
- [ ] `python tooling/verify/checks/corpus_gate.py` is green and its executed set includes `sqlite_concurrency.py`
- [ ] `python tooling/verify/checks/pipeline_state.py` is green
- [ ] Live: server boots, first connection reports `journal_mode = wal`, and `world_engine.db-wal` / `world_engine.db-shm` exist beside the carrier
- [ ] Live: a dialogue turn with an NPC completes — NPC reply, MJ narration, no traceback; both lines still present after a page reload
- [ ] Live: a physical-action turn and an NPC-initiative turn each complete without a traceback
- [ ] Live: Creation and Observation still load and save
- [ ] `/review-step` and `/close-step` run (engine code touched: `db.py`)
- [ ] Snapshot-staleness (B1) and mini-RECON item 7 delivered as REPORT ONLY, no edits made

## Docs to update

- `world-engine-schema-changelog.md` — applicatif addendum, no schema change
  (Scope IN item 7).
- `ARCHITECTURE_DECISIONS.md` — the concurrency-posture entry, including the
  process lesson and the check's stated limit (Scope IN item 8).
- `src/world_engine/db.py` module docstring (Scope IN item 3). This step IS that
  doc.
- `sqlite_concurrency.py`'s own module docstring carries the four numbered rules
  in the same voice as `legacy_mount.py`. This step IS that doc.
- `CLAUDE.md` — verify whether any line states an engine or transaction doctrine
  this ticket makes false. Report either way; amend only if such a line exists
  and TICKET-0071 has freed budget (currently 499/500 lines).
