# BRIEF — Step "request session read-only for the life of a stream"

TICKET-0072, decision E1. Second and final brief. Depends on BRIEF-0072-a:
until WAL is in place the stream dies earlier, so this step cannot be
live-tested before that one has landed. One commit for the session change plus
its check.

## Context

BRIEF-0072-a stops a reader from blocking a writer. It does not stop the second
failure mode the first one was hiding. The request session bound at
`routes/play.py:171` is pinned to a read snapshot taken at `play.py:143` and
held for the whole SSE response. Under WAL, a pinned transaction that then
attempts to WRITE, after any other connection has committed, fails instantly
with `SQLITE_BUSY_SNAPSHOT` — surfaced as the same `database is locked` message,
and immune to `busy_timeout`. `play_stream.py:110` is the one site in the stream
that writes on that session: `_perform_travel(ctx.conv.player_id,
travel_dest_id, ctx.db)`, whose body commits at `play_stream.py:440-459`. It
runs after `_say_initiative_phase` (`play_stream.py:103`), whose nested sessions
commit at `play_initiative.py:203`, `:207`, `:250`. Measured: with WAL alone,
that write fails at 0.00s; with the write on its own session, it succeeds. This
step removes the last write from the request session and makes "read-only for
the life of a stream" a checked property rather than a habit.

## Mini-RECON — verify before writing

Report `file:line` for each. **STOP and escalate** if any does not hold.

1. Confirm BRIEF-0072-a has landed: `db.py` carries `_SQLITE_JOURNAL_MODE` and
   the connect listener sets `PRAGMA journal_mode`, and
   `tooling/verify/checks/sqlite_concurrency.py` returns PASS. This step is
   meaningless before that.
2. `play_stream.py:110` — confirm it is the ONLY site reachable from
   `_say_build_stream` (across `play.py`, `play_stream.py`, `play_physical.py`,
   `play_initiative.py`) that passes `ctx.db`, or a local alias of it, to a
   function whose body contains `.add(`, `.commit(`, `.delete(` or `.merge(`.
   Enumerate every call site that passes the request session anywhere in those
   four modules, with `file:line`, and mark each callee read-only or writing.
   If a second writing site exists, STOP: the scope changes.
3. Enumerate every `db = ctx.db` alias binding in the four modules with
   `file:line` (expected at least `play_physical.py:74`, `:144`, `:210`, `:356`,
   `play_initiative.py:60`, `:104` — re-measure rather than trusting this list).
   The check in Scope IN item 2 must resolve all of them.
4. Confirm that after `play_stream.py:110`, nothing in the remainder of
   `_say_narrate_and_finish` or its callees reads an ATTRIBUTE of `ctx.conv`.
   `_perform_travel` closes the player's open conversations, so once it runs on
   a foreign session `ctx.conv` is a stale ORM object in the request session's
   identity map. Report every post-line-110 use of `ctx.conv` with `file:line`.
   If any reads an attribute rather than passing `ctx.conv_id`, STOP and
   escalate rather than patching around it.
5. Confirm `Session` and `engine` are already imported at module level in
   `play_stream.py` (they are used at `play_stream.py:116`). No new import
   should be needed; if one is, report it.
6. Confirm the three non-stream callers of `_perform_travel`
   (`routes/play.py:280`, `:384`, `:454`) each receive a request-scoped session
   through `Depends(get_session)` and none of them is inside a
   `StreamingResponse`. They are unchanged by this step and must stay unchanged.
7. Confirm `_analyze_window`, called inside `_perform_travel`
   (`play_stream.py:432`), uses the session passed to it and opens none of its
   own. If it opens its own, report before writing — it changes what the new
   session boundary contains.

## Scope IN

1. **`src/world_engine/cockpit/play_stream.py`, the travel transition.** Replace
   the call at line 110 (the body of the `if travel_dest_id is not None:` block
   introduced at `play_stream.py:108-110`) with:

   ```python
   if travel_dest_id is not None:
       # TICKET-0072 (BRIEF-0072-b, E1). Its own session, deliberately, and
       # this is the LAST write that used the request session inside a stream.
       # ctx.db has been pinned to a read snapshot since play.py:143 and every
       # nested persist above has committed since; under WAL a pinned
       # transaction that tries to upgrade to a write does not wait for the
       # lock, it fails instantly with SQLITE_BUSY_SNAPSHOT, reported as
       # "database is locked" and unaffected by busy_timeout. The request
       # session is read-only for the life of a streaming response --
       # tooling/verify/checks/stream_session_readonly.py holds that.
       with Session(engine) as travel_db:
           _perform_travel(ctx.conv.player_id, travel_dest_id, travel_db)
   ```

   `ctx.conv.player_id` is read BEFORE the call and is a plain string; the
   session boundary does not affect it. `_perform_travel` itself is not
   modified — it takes a session as a parameter and always has.

2. **`tooling/verify/checks/stream_session_readonly.py`** — new fail-closed
   check. Same idiom as `legacy_mount.py`: module-level `FAILURES`, `fail()`,
   `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib only, AST only —
   never regex, same discipline as `legacy_mount.py:18-19` and
   `single_canon_write.py`. No DB, no import of application code, no subprocess.

   Scope of analysis: the four Play stream modules, named in a module-level
   tuple constant so the set is declared rather than inferred —
   `src/world_engine/cockpit/{play,play_stream,play_physical,play_initiative}.py`.
   A named module that does not exist on disk is a FAILURE.

   Definitions the check computes, in this order:

   - **WRITERS** — every function defined in those four modules whose body
     contains a call to `.add(`, `.delete(`, `.merge(`, `.commit(` or `.flush(`
     on any receiver.
   - **REQUEST-SESSION EXPRESSIONS** — the attribute `ctx.db`, plus every local
     name bound to it by a direct assignment (`db = ctx.db`) inside the
     function being walked. Aliases are function-local; do not propagate them
     across functions.

   Four rules:

   - **rule1 — no direct write on the request session.** Any call
     `<req>.add(...)`, `.delete(...)`, `.merge(...)`, `.commit(...)` or
     `.flush(...)` where `<req>` is a request-session expression is a FAILURE,
     naming `file:line`.
   - **rule2 — no write by delegation.** Any call site in the four modules that
     passes a request-session expression as an argument (positional or keyword)
     to a callee whose name is in WRITERS is a FAILURE, naming `file:line` and
     the callee. This is the rule that would have caught `play_stream.py:110`.
   - **rule3 — vacuity guards, three of them.** WRITERS must be non-empty; the
     alias map must be non-empty; and the total count of call sites passing a
     request-session expression to any callee must be non-zero. Each empty
     result means the walker stopped seeing the code rather than that the code
     is clean, and each is a FAILURE, never a pass.
   - **rule4 — no exemption mechanism.** The check carries no allowlist, no
     `# noqa`-style escape and no skip list. If a future site legitimately needs
     to write on the request session, that is a doctrine change and a ticket,
     not a suppression. Assert this by construction: the module defines no
     allowlist constant.

   State the limit explicitly in the module docstring, in the "proves X, not Y"
   voice already used in the corpus: **this proves no request-session write at
   one hop; it does not prove it at two.** A helper that passes its session
   parameter on to a third function that writes is outside what a
   single-module-scope AST walk can see. Resolving arbitrary call graphs is not
   in scope; the honest boundary belongs in the docstring so the next reader
   does not over-trust the green.

   Success report line, matching the corpus style:
   `PASS: stream_session_readonly — 4 module(s), N writer(s), M alias(es), K request-session call site(s), zero writes on the request session`

3. **`ARCHITECTURE_DECISIONS.md`** — extend the entry opened by BRIEF-0072-a
   (append; do not rewrite it) with the E1 half: the request session is
   read-only for the life of a streaming response; both halves are load-bearing
   and neither is sufficient alone — WAL alone relocates the crash from dialogue
   turns to travel turns, and the session change alone leaves failure mode 1
   intact; and the two-hop limit of `stream_session_readonly.py`.

4. **`world-engine-schema-changelog.md`** — the applicatif addendum entry opened
   by BRIEF-0072-a gains the travel-session change and the second check. One
   entry for the ticket, not two.

## Scope OUT

- **`_perform_travel` itself** (`play_stream.py:382-459`). It takes a session
  parameter and is correct. Do not change its signature, its body, its commit,
  or its return value.
- **The three non-stream callers** (`routes/play.py:280`, `:384`, `:454`).
  They pass a request-scoped session outside any stream, where the pinned
  snapshot problem does not exist. Untouched.
- **The eleven nested `Session(engine)` sites.** They are already correct and
  are what this step makes the travel path resemble. Do not consolidate them,
  do not factor them into a helper, do not change their commit boundaries.
- **Read-side snapshot staleness (decision B1).** `play_physical.py:420` and
  `play_physical.py:427` read `ctx.db` after a nested commit. Not touched here.
  Do not add `refresh()`, `expire_all()`, `rollback()` or a session-scope change
  to chase it. REPORT ONLY.
- **The stale comment at `play_initiative.py:200-204`.** It documents an
  invariant BRIEF-0044-f invalidated; correcting it belongs with the B1 ticket
  and its reader audit.
- **`ctx.db` READS anywhere in the stream.** This step removes writes, not
  reads. Do not convert a single read to a nested session.
- **Making `_TurnCtx.db` structurally read-only** (a wrapper, a proxy, a
  read-only Session subclass). Tempting and out of scope: it would touch every
  read site in four modules to fix a write problem that has exactly one site.
  Reactivation condition: `stream_session_readonly.py` fails on a NEW site
  introduced after this ticket, i.e. the check catches a second occurrence —
  at which point one site is a pattern and deserves a type.
- **Anything in `db.py`.** That is BRIEF-0072-a and it is closed.
- **Schema, canon-write paths, mutation gating, prompts, `frontend/`.**

## Invariants to defend

- **Structural over disciplinary.** The whole point of E1 over E2. If the
  implementation ends up relying on anyone remembering that `ctx.db` must not
  be written to, it has failed. The property is held by rule1 + rule2.
- **Vacuous-proof.** rule3's three guards are the heart of the check. An AST
  walker that silently matches nothing is the classic green-by-blindness, and
  this check's whole subject is a site that looked innocuous for months.
- **Fail-closed.** A missing module, an unparseable file, an empty writer set:
  FAILURE. No rule may pass by finding nothing.
- **AST, never regex.**
- **One implementation per rule.** This check does not re-assert anything
  `sqlite_concurrency.py` asserts. Engine posture there, session ownership here,
  no overlap; a reader must be able to tell from the report line alone which
  guarantee lapsed.
- **History is sacred.** `_perform_travel` archives `scene_state` to `history[]`
  before clearing it (`play_stream.py:436`). Moving it to another session must
  not change what it writes or the order in which it writes it — only which
  connection carries it.
- **No canon-write path, no schema.** Session ownership only.

## Done means

- [ ] Mini-RECON items 1-7 reported with `file:line`, including the full alias list (item 3) and the full post-line-110 `ctx.conv` usage list (item 4)
- [ ] `git diff` on `play_stream.py` shows exactly one changed block: the travel transition. `_perform_travel`'s own body is byte-identical
- [ ] `WORLD_ENGINE_ENV=test PYTHONPATH=src python tooling/verify/checks/stream_session_readonly.py` returns PASS, report line showing non-zero writer, alias and call-site counts
- [ ] It returns FAIL when the travel call is temporarily reverted to `_perform_travel(..., ctx.db)` (demonstrate, revert) — this is the rule2 proof and it is the one that matters most
- [ ] It returns FAIL when a temporary `ctx.db.commit()` is added anywhere in the four modules (demonstrate, revert) — rule1 proof
- [ ] It returns FAIL when the module tuple is temporarily pointed at a non-existent file (demonstrate, revert)
- [ ] It returns FAIL when the writer-detection method names are temporarily emptied, i.e. an empty WRITERS set (demonstrate, revert) — rule3 proof
- [ ] `sqlite_concurrency.py` still returns PASS
- [ ] `python scripts/test_ddl_atomicity.py` still passes, file untouched
- [ ] `python tooling/verify/checks/corpus_gate.py` is green and its executed set includes both `sqlite_concurrency.py` and `stream_session_readonly.py`
- [ ] `python tooling/verify/checks/pipeline_state.py` is green
- [ ] Live: an in-fiction travel turn completes — the player moves, the previous conversation closes, no traceback
- [ ] Live: a travel turn on which an NPC initiative also fires completes without a traceback
- [ ] Live: after a travel turn, the transcript of the closed conversation still shows the NPC and MJ lines of that turn
- [ ] Live: door travel, spatial travel and the direct conversation travel endpoint all still work
- [ ] Live: a dialogue turn and a physical-action turn still complete (no regression from BRIEF-0072-a)
- [ ] `/review-step` and `/close-step` run (engine code touched: `play_stream.py`)
- [ ] B1 residue and any mini-RECON item 2 second-site finding delivered as REPORT ONLY, no edits made

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — append the E1 half to the entry BRIEF-0072-a
  opened (Scope IN item 3).
- `world-engine-schema-changelog.md` — extend the ticket's single applicatif
  addendum entry (Scope IN item 4).
- `stream_session_readonly.py`'s own module docstring carries the four numbered
  rules and the stated two-hop limit, in the same voice as `legacy_mount.py`.
  This step IS that doc.
- `CLAUDE.md` — no change expected from this brief; BRIEF-0072-a already carries
  the verify-and-report obligation.
