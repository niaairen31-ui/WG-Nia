---
id: TICKET-0072
title: Play stream crashes with "database is locked" on every NPC turn
type: bug
status: live-gate
created: 2026-08-22
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: large
brief_ids: [BRIEF-0072-a, BRIEF-0072-b, BRIEF-0072-c, BRIEF-0072-d]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket de bug 0072; lorsque je veux lance une discution avec un NPC, j'ai un
> erreur serveur et mon jeu plante. Analyse les cause probable, regarde le code
> directement, si tu le peu, test tes hypothese, si tu as besoin de plus
> d'information, pose moi la question ou fait moi une demande a faire a claude
> code pour faire des test avant de faire un ticket de reparation base sur une
> hypothese fausse.

Server-side, on every attempt:

```
File "src\world_engine\cockpit\play.py", line 617, in _say_npc_generation
    persist_db.commit()
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
```

## Clarifications resolved (intake)

**The defect.** This is not a `play.py` bug. It is an engine-configuration
regression introduced by BRIEF-0044-f (transactional DDL), which silently
invalidated the concurrency assumption every Play persist site is built on.
There are **two** failure modes, one visible today and one currently masked by
it. Both follow from the same fact: the request session holds an open
transaction for the entire SSE response.

### Failure mode 1 — a reader blocks a writer (visible today)

1. `db.py:90` sets `dbapi_connection.isolation_level = None` and `db.py:100`
   emits an explicit `conn.exec_driver_sql("BEGIN")` on the engine's `"begin"`
   event. Before BRIEF-0044-f, pysqlite opened a transaction only on DML, so a
   `SELECT` held no lock between statements. After it, **every** statement runs
   inside an explicit transaction, and under the default rollback journal a read
   holds a `SHARED` lock until that transaction ends.
2. `routes/play.py:171` binds the request session through
   `Depends(get_session)`; `routes/play.py:190` returns a `StreamingResponse`
   over `_say_build_stream(ctx)`. FastAPI tears a yield-dependency down only
   after the response completes, so the session stays open for the whole stream.
3. `play.py:136` commits the player line on that session, then `play.py:143`
   reads it back. That read opens a fresh explicit transaction which is never
   closed again for the remainder of the turn.
4. `play.py:609-617` opens a second connection (`with Session(engine) as
   persist_db`) to persist the NPC line. The `INSERT` succeeds (`RESERVED` is
   compatible with a foreign `SHARED`); the `COMMIT` must promote to
   `EXCLUSIVE`, waits on the request session's `SHARED`, exhausts the busy
   timeout and raises.

The traceback discriminates the two candidate causes on its own: the failure
lands in `do_commit`, not in the flush. A competing *writer* would have failed
at the `INSERT`. A competing *reader* fails exactly at the `COMMIT`. The
competing reader is the request session.

### Failure mode 2 — a pinned snapshot cannot upgrade to a write (masked)

The same open transaction also pins the request session to a read snapshot
taken at `play.py:143`. Under WAL, a transaction holding a stale snapshot that
then attempts to WRITE does not wait: SQLite returns `SQLITE_BUSY_SNAPSHOT`
immediately, surfacing as the same `database is locked` message, and
`busy_timeout` has no effect on it.

`play_stream.py:110` calls `_perform_travel(ctx.conv.player_id, travel_dest_id,
ctx.db)` — the only site in the stream that WRITES on the request session
(`play_stream.py:440-459`). It runs after `_say_initiative_phase`
(`play_stream.py:103`), whose nested sessions commit at `play_initiative.py:203`,
`:207` and `:250`. So on a travel turn, fixing failure mode 1 alone would move
the crash rather than remove it: dialogue turns would recover and travel turns
would break, with an identical error message. Today this is invisible because
mode 1 kills the turn first.

**Measured evidence [M].** Reproduced end-to-end outside this repo with
FastAPI + SQLModel + the two real listeners from `db.py`, against scratch
databases (SQLAlchemy 2.0.52 / SQLModel 0.0.39, versus the 2.0.50 / 0.0.38 pair
recorded in BRIEF-0044-f's ADR entry):

| Configuration | Nested `persist_db.commit()` | `ctx.db` write after a nested commit |
|---|---|---|
| current (explicit `BEGIN`, journal `delete`) | **FAIL after 5.0s** | not reached |
| pre-BRIEF-0044-f (listeners removed) | OK, 0.0s | OK |
| current + `journal_mode=WAL` | OK, 0.0s | **FAIL at 0.00s (`SQLITE_BUSY_SNAPSHOT`)** |
| current + WAL + the write on its own session | OK, 0.0s | OK |

Live confirmation on the prod carrier (`~/.world_engine/world_engine.db`):
`PRAGMA journal_mode` -> `delete`. `PRAGMA busy_timeout` -> `5000`, which is
pysqlite's own `timeout=5.0` default rather than a value this project owns —
`db.py` never sets it. The 5.0s in the reproduction and the 5s stall before the
traceback are the same number.

Also measured: `journal_mode=WAL` does **not** cost the guarantee BRIEF-0044-f
was built for. A forced failure between `CREATE TABLE ext_zzz` and a following
`INSERT`, under WAL, leaves neither the table nor the row.

**Blast radius: a class, not a site.** Every nested session inside the SSE path
carries failure mode 1 — `play.py:266`, `play.py:609`, `play_stream.py:116`,
`play_stream.py:133`, `play_physical.py:266`, `play_physical.py:324`,
`play_physical.py:333`, `play_physical.py:395`, `play_initiative.py:203`,
`play_initiative.py:207`, `play_initiative.py:250`. Line 617 is simply the
first one a dialogue turn reaches. `play_initiative.py:200-204` states the
invalidated invariant in the code itself: *"the SSE generator's db session has
no open write transaction at this point ... so there is no nested-transaction
conflict"* — true before BRIEF-0044-f, false since, because a read transaction
is now sufficient to block the commit.

**Silent residue, out of scope by decision B1.** Beyond the write case above,
the pinned snapshot also means `ctx.db` READS during the stream cannot see rows
written by nested sessions in the same turn. Measured: session A reads (1 row),
session B inserts and commits, A re-reads and still sees 1 row; after
`A.commit()` it sees 2. Two such reads sit after a nested commit
(`play_physical.py:420`, `play_physical.py:427`). Neither is known to be wrong
today, because phase ordering happens to place every nested write after the data
those helpers read — a guarantee held by ordering rather than by construction.
That is a separate ticket with its own reader audit, not a crash fix.

**Checked and clear, recorded so it is not re-litigated.** `scripts/backup.py`
copies through SQLite's online backup API (`source.backup(target)`,
`backup.py:88-93`), which is WAL-safe; no backup change is needed. Nothing in
the tree binds a `:memory:` URL, but `WORLD_ENGINE_DATABASE_URL` can express
one and in-memory databases report `memory` rather than `wal`, so the assertion
must admit both.

**Locked decisions (A1, B1, C3, D1, E1).**

- **A1** — `PRAGMA journal_mode=WAL` plus an explicitly declared
  `PRAGMA busy_timeout` in the existing connect listener. One place, structural,
  measured, and it preserves BRIEF-0044-f rather than trading it away. Rejected:
  **A2** (end the request session's transaction before streaming — there are
  reads on `ctx.db` throughout the stream, so the fix would survive only as a
  rule people remember); **A3** (make the explicit `BEGIN` opt-in, DDL-only —
  reopens BRIEF-0044-f's doctrine and is fail-open the day a DDL path forgets to
  opt in; reactivation condition: WAL is measured unavailable or unsafe on the
  carrier filesystem); **A4** (one session per turn — deletes the independent
  commit boundaries that keep an NPC line persisted when a later phase fails).
- **B1** — read-side snapshot staleness is REPORT ONLY here, separate ticket.
- **C3** — two proofs with disjoint assertions and no second copy of either: a
  fail-closed corpus check `sqlite_concurrency.py`, and
  `scripts/test_ddl_atomicity.py` re-run **unmodified** as the regression proof
  that BRIEF-0044-f still holds.
- **D1** — takes precedence over TICKET-0066 / TICKET-0060 continuation work;
  Play is fully broken. Sequenced after TICKET-0071 by Nia's own ordering.
- **E1** — `_perform_travel` at `play_stream.py:110` moves onto its own
  `Session(engine)`, making the request session **read-only for the entire
  stream**, and that property is held by a second fail-closed check
  (`stream_session_readonly.py`) rather than by convention. Rejected: **E2**
  (a `ctx.db.commit()` before the write to release the snapshot — one line, and
  purely disciplinary: nothing stops the next write from omitting it);
  **E3** (defer to a separate ticket — would ship 0072 knowing Play stays broken
  for a whole class of turns).

**Two-brief split.** BRIEF-0072-a is the engine posture (`db.py` + the
concurrency check); after it, dialogue turns are live-testable. BRIEF-0072-b is
E1 (`play_stream.py` + the read-only check); after it, travel turns are
live-testable. Two files, two commits, two independent live observations.

**Process lesson to record.** BRIEF-0044-f's verification surface was DDL,
migrations and `init_db.py` — thorough within its frame, and the frame was the
defect. An engine-wide transaction-semantics change alters the behaviour of
every concurrent path in the application, and the concurrent paths that mattered
were never exercised. Same shape as the "proves X, not Y" family already
recorded three times in `ARCHITECTURE_DECISIONS.md`: proving DDL is atomic does
not prove ordinary reads and writes still compose. A second instance appeared
inside this very ticket — the first proposed fix was measured against the
reported symptom and had to be re-measured against the paths that symptom was
hiding.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `db.py` declares the concurrency posture as module-level constants readable by AST, and the connect listener references them  -> verify/checks/sqlite_concurrency.py
- [ ] A fresh connection from the shared engine reports `journal_mode = wal` and `busy_timeout` equal to the declared constant  -> verify/checks/sqlite_concurrency.py
- [ ] With one session holding an open read transaction, a second session INSERTs and COMMITs successfully in under one second  -> verify/checks/sqlite_concurrency.py
- [ ] Vacuity guard: the reader is asserted to be genuinely inside an open transaction before the nested commit is attempted; if it is not, that is a FAILURE, never a pass  -> verify/checks/sqlite_concurrency.py
- [ ] Counterfactual guard: the same shape under a rollback journal is asserted to FAIL, so a blind instrument cannot report green  -> verify/checks/sqlite_concurrency.py
- [ ] The check touches only a scratch database and never the prod or test carrier  -> verify/checks/sqlite_concurrency.py
- [ ] No call in the four Play stream modules writes on the request session, directly or by passing it to a writing callee  -> verify/checks/stream_session_readonly.py
- [ ] That check is vacuous-proof: an empty writer set, an empty alias map, or zero request-session call sites found is a FAILURE  -> verify/checks/stream_session_readonly.py
- [ ] `scripts/test_ddl_atomicity.py` passes unmodified under the new configuration  -> demonstrated, file untouched
- [ ] `corpus_gate.py` is green, with both new checks discovered and executed  -> verify/checks/corpus_gate.py
- [ ] `pipeline_state.py` is green on this ticket's front-matter and section shape  -> verify/checks/pipeline_state.py

### Live  ->  human gate (Nia)

- [ ] `python scripts/backup.py` run before anything else, backup written
- [ ] Server boots; the first connection reports `journal_mode = wal`; `world_engine.db-wal` and `world_engine.db-shm` appear beside the carrier
- [ ] After BRIEF-0072-a: start a conversation with an NPC and send a line — the NPC replies, the MJ narration streams, no server traceback
- [ ] The NPC line and the MJ line are both present in the transcript after a page reload (they were persisted, not just streamed)
- [ ] A second and third turn in the same conversation both complete
- [ ] A physical action turn (skill check) completes without a traceback
- [ ] An NPC initiative turn completes without a traceback
- [ ] After BRIEF-0072-b: an in-fiction travel turn completes — the player moves, the previous conversation closes, no traceback
- [ ] A travel turn on which an NPC initiative also fires completes without a traceback (that ordering is what produces `SQLITE_BUSY_SNAPSHOT`)
- [ ] The three non-stream travel routes still work: door travel, spatial travel, and the direct conversation travel endpoint
- [ ] Creation and Observation surfaces still load and save normally
- [ ] `python scripts/init_db.py` against a scratch DB still creates a virgin database

## Docs to update

- `world-engine-schema-changelog.md`: an applicatif addendum entry, no schema
  change, in the same shape as BRIEF-0044-f's — engine transaction semantics and
  session ownership only, naming WAL, the declared busy timeout, the travel
  session change, and both new checks.
- `ARCHITECTURE_DECISIONS.md`: a new entry recording that WAL is now a
  structural property of this engine; that the request session is read-only for
  the life of a streaming response and why both halves are needed (WAL alone
  moves the crash, the session change alone does not remove it); that
  BRIEF-0044-f's DDL guarantee is preserved and re-proved rather than traded;
  and the honest limits of both checks.
- `CLAUDE.md`: only if it states an engine or transaction doctrine this ticket
  makes false. Verify and report either way; do not spend budget lines here
  unless TICKET-0071 has already freed them (currently 499/500).
- `db.py`'s own module docstring carries the concurrency posture alongside the
  transactional-DDL paragraph it already has. This step IS that doc.

## Escalations

### E-01 — archived — QUESTION-TICKET-0072.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0072.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0072
Trigger: D1-c
## Context

BRIEF-0072-a landed and verified green (`sqlite_concurrency.py` PASS,
`test_ddl_atomicity.py` unmodified and passing, `corpus_gate.py` 84/84,
live-confirmed: server boots, prod carrier reports `journal_mode=wal`).
Executing BRIEF-0072-b next.

BRIEF-0072-b's mini-RECON item 2 requires: "Confirm `play_stream.py:110` is
the ONLY site reachable from `_say_build_stream` (across `play.py`,
`play_stream.py`, `play_physical.py`, `play_initiative.py`) that passes
`ctx.db`, or a local alias of it, to a function whose body contains `.add(`,
`.commit(`, `.delete(` or `.merge(`... If a second writing site exists,
STOP: the scope changes."

A second site exists. `play.py:390`, inside `_say_join_branch` (called at
`play.py:686`, itself called from `_say_run_turn` at `play.py:660` — the
SSE generator body wrapped by `_say_build_stream`, i.e. genuinely inside the
stream, on the held-open request session):

```python
# play.py:388-390 (_say_join_branch)
resolved_id = _play_physical._resolve_join_target(reference, open_gatherings, ctx.db)
if resolved_id is not None:
    gathering = _join_gathering(ctx.conv, resolved_id, ctx.db)
```

`_join_gathering` (`play.py:890-914`) writes and commits directly on
whatever session it receives:

```python
# play.py:904-914
if existing is None:
    db.add(GatheringMember(...))
conv.gathering_id = gathering_id
db.add(conv)
db.commit()
db.refresh(gathering)
```

This is not one of BRIEF-0072-a's eleven documented nested-`Session(engine)`
sites — it commits on `ctx.db` itself, the request session, when the turn's
mode is `join` (the "parler n'a pas de cible tant qu'on n'a pas rejoint"
path). Functionally it may not crash TODAY: nothing earlier in the `join`
branch of `_say_run_turn` appears to open a competing nested session before
`_say_join_branch` runs, so `ctx.db`'s snapshot likely has no foreign commit
to collide with yet. But that safety is held by phase ordering, not by
construction — the same fragility TICKET-0072 already named and explicitly
rejected for the read-side residue (decision B1: "a guarantee held by
ordering rather than by construction"). More concretely: BRIEF-0072-b's own
Scope IN item 2 (`stream_session_readonly.py`, rule2 — "no write by
delegation") would fail on `play.py:390` the moment it exists, independent
of and in addition to the travel site the brief was written to fix. I have
implemented nothing from BRIEF-0072-b's Scope IN yet — no files touched, no
commit made — precisely because building the check as specified would
immediately and correctly flag a genuine site the brief did not know about
and has no planned fix for.

## Question

BRIEF-0072-b's Scope IN item 1 only converts the travel write
(`play_stream.py:110`) to its own session. `play.py:390`'s join-gathering
write is a second, structurally identical case (E1's exact failure shape,
a write attempted on the pinned request session mid-stream) that the brief
never named. How should this be handled?

## Options

A. Fold the join-gathering write into BRIEF-0072-b's scope: give it the same
   treatment as the travel write — `with Session(engine) as join_db:
   _join_gathering(ctx.conv, resolved_id, join_db)` — and design the
   post-call read (`gathering.id`, `gathering.label`, used immediately after
   at `play.py:391`) the same careful way BRIEF-0072-b already had to for
   `_perform_travel`'s `ctx.conv.player_id` (read before the call / re-fetch
   after, never a stale cross-session ORM object read). One brief, two
   sites, both closed together; `stream_session_readonly.py` then covers
   both from the start.

B. Split it into a new BRIEF-0072-c, landed immediately after -b: keep -b
   scoped exactly as written (travel only), accept that
   `stream_session_readonly.py` will report the join site as a known,
   named, temporarily-accepted gap (an explicit allowlist entry or a
   narrower rule2 scope for this landing only) until -c closes it. Rule4 of
   the brief explicitly forbids "no exemption mechanism... no allowlist" —
   so option B would require a brief amendment to permit one, or the check
   would simply stay red between -b and -c.

C. Re-scope BRIEF-0072-b in place (amend the brief file) to fix both sites
   as one unit, folding option A's design into the existing brief rather
   than opening a new one — same code outcome as A, different paperwork
   (no BRIEF-0072-c, -b's own text is corrected before execution resumes).

## Response
Escalation accepted; the specification error was mine, not the executor's.
`play.py:390 -> _join_gathering (play.py:890-915)` verified independently --
the STOP was correct and stopping was the right call.

None of A/B/C. A and C both require editing a deposited artifact
(BRIEF-0072-b.md); B requires weakening rule4 to sanction a known hole.
Decision: BRIEF-0072-b is withdrawn unexecuted, superseded by BRIEF-0072-c,
which covers every request-session write site in the stream as one unit,
with a transitively-closed writer set in the check. BRIEF-0072-b.md stays
on disk unedited -- the withdrawn predecessor, not rewritten, not deleted.

Before authoring -c: requested a report-only RECON (no code, no commit, no
branch change) -- one-hop/two-hop write-site enumeration, reachability under
every ResponseMode, nested-commit ordering on a join turn, every reader of
ctx.conv.gathering_id after the join branch, a measured (not inferred)
autoflush probe, and one live observation of a join turn post-BRIEF-0072-a.
Delivered in-session. BRIEF-0072-c is authored from it: `_join_gathering`
takes conv_id (not the live Conversation) and returns plain values;
`ctx.conv` is never mutated (autoflush would turn an in-memory
`gathering_id` sync into an invisible write on the pinned transaction,
exactly what this step removes); the check's writer set is transitively
closed rather than one-hop, with a fail-closed rule3 on any call leaving the
declared module set.

Proceed: execute BRIEF-0072-c on ticket/0072.
~~~~

### E-02 — archived — QUESTION-TICKET-0072-2.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0072-2.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0072
Trigger: D1-c
## Context

Executing BRIEF-0072-c (BRIEF-0072-a landed; BRIEF-0072-b withdrawn
unexecuted per `QUESTION-TICKET-0072.md`'s resolved response). Mini-RECON
item 3 says verbatim: "`_join_gathering` still has exactly one caller
(`play.py:390`). If a second appeared, STOP — the signature change in Scope
IN item 1 becomes wider than this brief."

A second caller exists: `src/world_engine/cockpit/routes/scene.py:303`,
inside `_scene_join_create_for_gathering` (itself called from `scene_join`,
`POST /api/scene/join`, both the `target_gathering_id` path at
`routes/scene.py:357` and the free-text path via
`_scene_join_resolve_and_create` at `routes/scene.py:270`):

```python
# routes/scene.py:299-304
db.add(conv)
db.flush()  # get conv.id before _join_gathering commits

# _join_gathering inserts gathering_member + sets conv.gathering_id, then commits.
gathering = _join_gathering(conv, resolved_id, db)
db.refresh(conv)
```

This is a real, live, non-streaming endpoint (`db: Session =
Depends(get_session)`, never inside a `StreamingResponse` — outside any
pinned-snapshot concern, so BRIEF-0072-c's WAL/session-boundary fix does not
need to touch it functionally). But it calls the OLD `_join_gathering(conv:
Conversation, gathering_id: str, db: Session) -> Gathering` signature —
passing the live, just-flushed-but-not-yet-committed `conv` object (its
whole reason for calling `db.flush()` first is to get `conv.id` while
`_join_gathering` still expects the object) and reading the OLD return shape
(`gathering.id`, `gathering.label` as an ORM object, `routes/scene.py:308`:
`_gathering_brief(gathering.id, db)`).

BRIEF-0072-c's Scope IN item 1 replaces `_join_gathering` with:
`_join_gathering(conv_id: str, gathering_id: str, db: Session) -> tuple[str,
str]`, which does `db.get(Conversation, conv_id)` — if landed unmodified,
this second site would break immediately (`db.get()` against an ORM
instance, not a pk value). I made the two `play.py` edits (Scope IN items 1
and 2), then, doing my own pass over every `_join_gathering` reference
before moving to the check (Scope IN item 4), found this second caller and
reverted both edits (`git diff --stat src/world_engine/cockpit/play.py` now
shows no changes) rather than either silently widening the brief to include
`routes/scene.py`, or leaving the repo mid-edit. Nothing else in Scope IN
was touched; no commit was made.

One relevant technical note for whichever way this resolves: `routes/scene.py`'s
own session (`db`) is never `ctx.db` and never inside a stream, so a
like-for-like adaptation is small — pass `conv.id` instead of `conv` (the
`db.flush()` immediately before already makes the row visible to a
`db.get()` on the SAME session/transaction), and read the new
`(gathering_id, gathering_label)` tuple instead of the old `Gathering`
object at `routes/scene.py:303-308`. That is an observation for scoping the
next step, not a decision made here.

This is filed as a SEPARATE QUESTION file (`-2` suffix) rather than reusing
`QUESTION-TICKET-0072.md`, whose `## Response` is already filled and closed
— the append-only-trace rule means that file is never rewritten once
resolved, even for a second, later escalation on the same ticket.

## Question

`_join_gathering`'s signature change (Scope IN item 1) has a second caller
BRIEF-0072-c never named, in a file (`routes/scene.py`) outside its Scope
IN. How should this be handled?

## Options

A. Widen BRIEF-0072-c's own scope in place to include the small
   `routes/scene.py:303-308` adaptation (pass `conv.id`, read the new tuple
   return) as part of this same commit — one signature change, both call
   sites updated together, landed atomically so `_join_gathering` never has
   a moment where one caller is broken.

B. Amend BRIEF-0072-c before executing further (same withdraw-and-supersede
   shape as -b -> -c): leave `-c` on disk unedited as a withdrawn
   predecessor, author `BRIEF-0072-d` covering both call sites as one unit
   — same code outcome as A, different paperwork.

C. Keep `_join_gathering`'s current object-taking signature untouched;
   instead give the `play.py:390` call site its own small adapter — a
   one-off nested-session wrapper at the call site only that re-fetches
   `Conversation`/`Gathering` locally and reimplements the insert+commit
   inline, without changing the shared `_join_gathering` function or
   touching `routes/scene.py` at all. Keeps this brief's file perimeter
   exactly as stated, at the cost of the shared helper duplicating logic
   with its own caller.

## Response
None of A/B/C. BRIEF-0072-c is withdrawn unexecuted (stays on disk unedited,
same shape as the -b -> -c supersession), replaced by BRIEF-0072-d.

Decision (H1): leave _join_gathering's signature, body and return type
untouched (play.py:890-915 stays byte-identical) rather than changing it to
take conv_id. The RECON that followed -c's own STOP found the function has
THREE callers repo-wide, not two -- play.py:390, routes/scene.py:303, and
routes/play.py:239 -- one of which (routes/scene.py:300) pre-flush()es a
still-pending Conversation specifically to obtain its id before calling
_join_gathering. A signature change touches two working HTTP endpoints and
makes correctness depend on an exhaustive caller enumeration -- and on this
ticket, enumeration scope has been wrong three times now (BRIEF-0072-b's
one-site assumption, BRIEF-0072-c's two-site assumption, now three). BRIEF-
0072-d instead owns the session boundary at the play.py:390 call site only:
open a nested Session(engine), re-fetch the Conversation on it by id, call
_join_gathering unchanged, read joined_id/joined_label out of the returned
Gathering before the session closes. Same idiom already used at
play_physical.py:324-330. The two route callers are not touched, cannot
regress, and do not need to be enumerated correctly for this fix to be
correct -- the corollary this ticket is recording: prefer the fix whose
correctness does not depend on a complete enumeration.

Proceed: execute BRIEF-0072-d on ticket/0072.
~~~~
