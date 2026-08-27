# BRIEF — Step "request session read-only for the life of a stream"

TICKET-0072, decisions E1 / F1 / G1. **Supersedes BRIEF-0072-b, which was never
executed.** That brief named one write site; the RECON of 2026-08-22 found two,
and its own STOP condition fired correctly. Nothing in `BRIEF-0072-b.md` is
edited — it stays on disk as the withdrawn predecessor. One commit for both code
sites plus the check.

## Context

BRIEF-0072-a put the carrier in WAL, which stops a reader from blocking a
writer. It does not stop the second failure mode it was hiding. The request
session bound at `routes/play.py:171` is pinned to a read snapshot taken at
`play.py:143` and held for the whole SSE response. Under WAL, a pinned
transaction that then attempts to WRITE, after any other connection has
committed, fails instantly with `SQLITE_BUSY_SNAPSHOT` — surfaced as the same
`database is locked` message, and immune to `busy_timeout`.

Two sites in the stream write on that session:

- `play_stream.py:110` — `_perform_travel(..., ctx.db)`, committing at
  `play_stream.py:440-459`, after `_say_initiative_phase` (`play_stream.py:103`)
  may already have committed on nested sessions
  (`play_initiative.py:203`, `:207`, `:250`). This one crashes as soon as WAL
  lands. Measured: fails at 0.00s; succeeds on its own session.
- `play.py:390` — `_join_gathering(ctx.conv, resolved_id, ctx.db)`, committing at
  `play.py:911-913`. Measured live post-BRIEF-0072-a: a join turn currently
  completes cleanly, because on a join turn nothing commits between the pin at
  `play.py:143` and `play.py:686` — `play.py:266` is the only candidate and it
  aborts the turn instead of reaching the mode dispatch. Latent, not live: it is
  correct today by phase ordering, which is not a guarantee.

This step removes both, and makes "the request session is read-only for the life
of a streaming response" a checked property rather than a habit.

## Mini-RECON — verify before writing

Most of this was measured in the 2026-08-22 RECON. Re-verify the anchors only
(BRIEF-0072-a touched `db.py` alone, so the Play line numbers should be
unmoved). Report `file:line`. **STOP and escalate** if any does not hold.

1. BRIEF-0072-a has landed: `sqlite_concurrency.py` returns PASS and `db.py`
   carries `_SQLITE_JOURNAL_MODE`. This step is meaningless before that.
2. `play.py:390` and `play_stream.py:110` are still the ONLY one-hop call sites
   passing `ctx.db` or an alias to a writer, and the two-hop chain
   `_scene_response -> _get_or_open_session` is still confined to
   `routes/scene.py` callers. Re-confirm; if a third stream-reachable site
   appeared, STOP.
3. `_join_gathering` still has exactly one caller (`play.py:390`). If a second
   appeared, STOP — the signature change in Scope IN item 1 becomes wider than
   this brief.
4. `Session` and `engine` are already imported at module level in `play.py`
   (`from ..db import engine`, `play.py:33`) and in `play_stream.py`
   (used at `play_stream.py:116`). Report if either needs a new import.
5. The alias list is 8, not 6: `play.py:493`, `play.py:554`,
   `play_physical.py:74`, `:144`, `:210`, `:356`, `play_initiative.py:60`,
   `:104`. Re-measure and report the count the check's walker actually resolves.
6. Zero attribute assignments of the form `ctx.conv.<attr> = ...` exist in the
   four modules today. Re-measure. If any appeared, STOP — rule5 of the check
   would ship red and the site needs its own analysis.
7. `analyzer.py` and `gathering.py` contain writes and are called from the
   stream (`play_stream.py:432`, `play_stream.py:135`, `play_initiative.py:204`)
   — always on nested sessions today. `context.py`, `context_window.py` and
   `prompt_store.py` receive `ctx.db` directly and contain no writes. Re-confirm
   both halves; these facts set the check's declared module set.

## Scope IN

1. **`src/world_engine/cockpit/play.py` — `_join_gathering` takes an id, not an
   object.** Replace the function at `play.py:890-915` with:

   ```python
   def _join_gathering(conv_id: str, gathering_id: str, db: Session) -> tuple[str, str]:
       """Insert the player as an active member of `gathering_id` and anchor the
       conversation to it. Idempotent — rejoining the same gathering is a no-op
       on membership (the row already exists and stays open).

       TICKET-0072 (BRIEF-0072-c, G1): takes `conv_id`, never a live
       Conversation, and returns plain values, never ORM objects. This function
       now runs on a session of its own, and the caller's `ctx.conv` belongs to
       the request session: handing it over would raise (already attached to
       another session), and anything returned attached would die at the
       session's close. Same shape every other nested writer here already uses
       -- re-fetch by id on your own session (cf. ss_db.get(Conversation, ...)).
       """
       conv = db.get(Conversation, conv_id)
       if conv is None:
           raise HTTPException(status_code=404, detail=f"Conversation {conv_id!r} not found")
       gathering = db.get(Gathering, gathering_id)
       if gathering is None:
           raise HTTPException(status_code=404, detail=f"Gathering {gathering_id!r} not found")
       gathering_label = gathering.label
       existing = db.exec(
           select(GatheringMember).where(
               GatheringMember.gathering_id == gathering_id,
               GatheringMember.entity_id == conv.player_id,
               GatheringMember.left_at.is_(None),
           )
       ).first()
       if existing is None:
           db.add(GatheringMember(
               gathering_id=gathering_id,
               entity_id=conv.player_id,
               joined_at=datetime.now(UTC),
               left_at=None,
           ))
       conv.gathering_id = gathering_id
       db.add(conv)
       db.commit()
       return gathering_id, gathering_label
   ```

   `gathering_label` is captured **before** the commit deliberately: `commit()`
   expires loaded attributes, and a post-commit read would issue a second
   SELECT for a value already in hand. The `db.refresh(gathering)` of the old
   body is dropped — its only purpose was to return a live object, and this
   function no longer returns one.

2. **`src/world_engine/cockpit/play.py` — the join call site.** Replace
   `play.py:390-391` (the `_join_gathering` call and the `extra_event` line
   that consumes it) with:

   ```python
           # TICKET-0072 (BRIEF-0072-c, E1/G1). Its own session, deliberately.
           # ctx.db has been pinned to a read snapshot since play.py:143; under
           # WAL a pinned transaction that tries to upgrade to a write fails
           # instantly with SQLITE_BUSY_SNAPSHOT, reported as "database is
           # locked" and unaffected by busy_timeout. It does not fire on a join
           # turn today only because nothing commits before this point -- an
           # ordering, not a guarantee.
           with Session(engine) as join_db:
               joined_id, joined_label = _join_gathering(ctx.conv_id, resolved_id, join_db)
           extra_event = {"joined": {"gathering_id": joined_id, "label": joined_label}}
   ```

   **`ctx.conv` is NOT mutated.** The RECON measured `autoflush = True` on the
   request session, so assigning `ctx.conv.gathering_id` in memory would emit an
   UPDATE into the pinned transaction at the next query on `ctx.db` — a write on
   the request session that no call-site rule can see, and one that FastAPI's
   dependency teardown then rolls back. That is the exact class this step
   exists to remove, arriving through the back door. The RECON also established
   there is no consumer: `player_gathering` is computed once at `play.py:677`
   and threaded unchanged into `_say_initiative_phase`, so on a first-time join
   it is `None`, initiative returns early at `play_initiative.py:61-62`, and
   `play_initiative.py:112` is never reached. No structure without a reader —
   the value is returned, not synced.

3. **`src/world_engine/cockpit/play_stream.py` — the travel transition.**
   Replace the body of the `if travel_dest_id is not None:` block
   (`play_stream.py:108-110`) with:

   ```python
   if travel_dest_id is not None:
       # TICKET-0072 (BRIEF-0072-c, E1). Its own session, for the same reason
       # as the join branch: ctx.db is pinned, and here nested persists HAVE
       # already committed (play_stream.py:116 above, play_initiative.py:203,
       # :207, :250 in the initiative phase), so this write fails under WAL.
       with Session(engine) as travel_db:
           _perform_travel(ctx.conv.player_id, travel_dest_id, travel_db)
   ```

   `ctx.conv.player_id` is READ before the call and is a plain string; reading
   an attribute is not a write and is unaffected. `_perform_travel` itself is
   not modified — it has always taken a session as a parameter.

4. **`tooling/verify/checks/stream_session_readonly.py`** — new fail-closed
   check. Same idiom as `legacy_mount.py`: module-level `FAILURES`, `fail()`,
   `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib only, AST only —
   never regex, same discipline as `legacy_mount.py:18-19` and
   `single_canon_write.py`. No DB, no import of application code, no subprocess.

   **Declared module set**, as a module-level tuple constant so the scope is
   declared rather than inferred: the four Play modules
   (`src/world_engine/cockpit/{play,play_stream,play_physical,play_initiative}.py`)
   plus every module they hand a session to
   (`src/world_engine/{context,context_window,analyzer,gathering,prompt_store}.py`).
   A named module missing from disk is a FAILURE.

   **Definitions**, computed in this order:

   - **WRITERS** — every function defined anywhere in the declared set whose
     body calls `.add(`, `.delete(`, `.merge(`, `.commit(` or `.flush(` on any
     receiver, **transitively closed** over calls between functions in the
     declared set: a function that calls a writer by name is itself a writer.
     Iterate to a fixed point. `_scene_response -> _get_or_open_session` is the
     shape this exists for, and `analyzer.py` / `gathering.py` are the reason
     the set reaches past the four Play modules.
   - **REQUEST-SESSION EXPRESSIONS** — the attribute `ctx.db`, plus every local
     name bound to it by a direct assignment (`db = ctx.db`) inside the function
     being walked. Function-local; never propagated across functions.

   Six rules:

   - **rule1 — no direct write.** Any `<req>.add/.delete/.merge/.commit/.flush(...)`
     where `<req>` is a request-session expression is a FAILURE, naming
     `file:line`.
   - **rule2 — no write by delegation.** Any call site in the four Play modules
     passing a request-session expression to a callee in WRITERS is a FAILURE,
     naming `file:line` and the callee. This is the rule that catches both
     `play.py:390` and `play_stream.py:110`.
   - **rule3 — unresolvable callee is a failure, not a pass.** If a
     request-session expression is passed to a callee whose defining module
     cannot be resolved — through the caller module's own `import` statements —
     to a module in the declared set, that is a FAILURE. The declared set then
     has to grow deliberately, in a ticket. Fail-closed on the unknown is the
     whole point: the alternative is a green that means "I could not see."
   - **rule4 — no attribute assignment on the request session's conversation.**
     Any `ctx.conv.<attr> = ...`, or the same through a local name bound to
     `ctx.conv`, is a FAILURE. Autoflush turns such an assignment into an
     implicit UPDATE on the pinned transaction at the next query — a write with
     no call site, invisible to rule1 and rule2. Measured zero occurrences
     today, so this rule ships green and freezes the property.
   - **rule5 — vacuity guards, four of them.** Every declared module must exist
     and parse; WRITERS must be non-empty; the alias map must be non-empty
     (expected 8 — report the resolved count, do not hard-code it); and the
     total count of call sites passing a request-session expression to any
     callee must be non-zero. Each empty result means the walker stopped seeing
     the code, not that the code is clean. Each is a FAILURE.
   - **rule6 — no exemption mechanism.** No allowlist, no skip list, no
     comment-directive escape. If a future site legitimately needs to write on
     the request session, that is a doctrine change and a ticket, not a
     suppression.

   State the remaining limit in the module docstring, in the "proves X, not Y"
   voice already used in the corpus: **this proves no request-session write
   inside the declared module set; a call chain leaving that set is caught by
   rule3 as a failure, never waved through.** That is the honest boundary — the
   check does not resolve the whole program, it refuses to guess about what it
   cannot see.

   Success report line, matching the corpus style:
   `PASS: stream_session_readonly — N module(s) declared, W writer(s) (transitive), A alias(es), K request-session call site(s), zero writes on the request session`

5. **`ARCHITECTURE_DECISIONS.md`** — append to the entry BRIEF-0072-a opened; do
   not rewrite it. Record: the request session is read-only for the life of a
   streaming response; both halves of TICKET-0072 are load-bearing and neither
   suffices alone (WAL alone relocates the crash from dialogue turns to travel
   turns; the session change alone leaves failure mode 1 intact); the
   autoflush finding, that an in-memory mutation on a session-attached object is
   an invisible write and is therefore forbidden by rule4; and the named
   condition under which `ctx.conv.gathering_id`'s staleness after a join stops
   being harmless — **the day `player_gathering` is recomputed after the mode
   dispatch, the joined id must be threaded explicitly to the initiative phase**.

6. **`world-engine-schema-changelog.md`** — extend the ticket's single
   applicatif addendum entry opened by BRIEF-0072-a with both session changes
   and the second check. One entry for the ticket, not two.

## Scope OUT

- **`_perform_travel` itself** (`play_stream.py:382-459`). Correct as written.
  Do not change its signature, body, commit, or return value.
- **The three non-stream callers of `_perform_travel`** (`routes/play.py:280`,
  `:384`, `:454`) and the four callers of `_scene_response`
  (`routes/scene.py:77`, `:156`, `:395`, `:426`). Outside any stream, no pinned
  snapshot, untouched.
- **The eleven nested `Session(engine)` sites.** Already correct; they are what
  the two fixed sites now resemble. Do not consolidate them into a helper, do
  not change their commit boundaries.
- **Mutating `ctx.conv` in any way**, including the in-memory
  `gathering_id` sync the RECON proposed. Explicitly rejected in Scope IN item 2
  and forbidden by rule4.
- **Read-side snapshot staleness (decision B1).** `play_physical.py:420` and
  `play_physical.py:427` read `ctx.db` after a nested commit. Not touched. Do
  not add `refresh()`, `expire_all()`, `rollback()` or a session-scope change to
  chase it. REPORT ONLY.
- **The stale comment at `play_initiative.py:200-204`.** Belongs to the B1
  ticket and its reader audit.
- **`ctx.db` READS anywhere in the stream.** This step removes writes, not
  reads. Do not convert a single read to a nested session.
- **Making `_TurnCtx.db` structurally read-only** (a proxy, a wrapper, a
  read-only Session subclass). Reactivation condition:
  `stream_session_readonly.py` fails on a NEW site introduced after this ticket
  — one site is a bug, two is a pattern that deserves a type.
- **Widening the declared module set beyond Scope IN item 4.** If rule3 fires on
  something unexpected, that is a report and an escalation, not a quiet addition
  to the tuple.
- **`db.py`.** BRIEF-0072-a is closed.
- **Schema, canon-write paths, mutation gating, prompts, `frontend/`.**

## Invariants to defend

- **Structural over disciplinary.** The point of E1 over E2 and of rule4 over a
  comment. If the result relies on anyone remembering that `ctx.db` must not be
  written to, or that `ctx.conv` must not be mutated, it has failed.
- **Fail-closed, and fail-closed on the unknown.** rule3 is the sharp edge: an
  unresolvable callee fails. A missing module, an unparseable file, an empty
  writer set: FAILURE.
- **Vacuous-proof.** rule5's four guards. An AST walker that silently matches
  nothing is green-by-blindness, and this check's whole subject is a site that
  read as innocuous for months.
- **AST, never regex.**
- **One implementation per rule.** No overlap with `sqlite_concurrency.py` —
  engine posture there, session ownership here. A reader must be able to tell
  from the report line alone which guarantee lapsed.
- **History is sacred.** `_join_gathering` stays idempotent: re-joining the same
  gathering must still leave the existing open `GatheringMember` row untouched
  rather than closing and reopening it. `_perform_travel` still archives
  `scene_state` to `history[]` before clearing (`play_stream.py:436`) — moving
  it to another session changes which connection carries the write, nothing
  about what is written or in what order.
- **No structure without a reader.** The joined id is returned because
  `extra_event` reads it. It is not synced onto `ctx.conv`, because nothing
  reads that.
- **No canon-write path, no schema.** Session ownership only.

## Done means

- [ ] Mini-RECON items 1-7 reported with `file:line`, including the resolved alias count and the re-measured zero for `ctx.conv.<attr> = ...`
- [ ] `git diff` shows exactly three changed blocks in application code: `_join_gathering`'s body/signature, the join call site, the travel transition. `_perform_travel`'s own body is byte-identical
- [ ] `WORLD_ENGINE_ENV=test PYTHONPATH=src python tooling/verify/checks/stream_session_readonly.py` returns PASS, report line showing non-zero module, writer, alias and call-site counts
- [ ] It returns FAIL when the join call is temporarily reverted to `_join_gathering(ctx.conv, resolved_id, ctx.db)` (demonstrate, revert) — rule2 proof, site 1
- [ ] It returns FAIL when the travel call is temporarily reverted to `_perform_travel(..., ctx.db)` (demonstrate, revert) — rule2 proof, site 2
- [ ] It returns FAIL when a temporary `ctx.db.commit()` is added anywhere in the four Play modules (demonstrate, revert) — rule1 proof
- [ ] It returns FAIL when a temporary `ctx.db` is passed to a callee outside the declared module set (demonstrate, revert) — rule3 proof, the one that matters most
- [ ] It returns FAIL when a temporary `ctx.conv.gathering_id = resolved_id` is added (demonstrate, revert) — rule4 proof
- [ ] It returns FAIL when the transitive closure is temporarily disabled, i.e. WRITERS computed one-hop only, with a temporary `ctx.db` passed to `_scene_response` (demonstrate, revert) — proves the closure is doing work, not decorating
- [ ] It returns FAIL when a declared module path is temporarily pointed at a non-existent file, and when the writer-method name set is temporarily emptied (demonstrate both, revert) — rule5 proofs
- [ ] The check's runtime is reported and is under 15s (`corpus_gate.TIMEOUT_SECONDS`)
- [ ] `sqlite_concurrency.py` still returns PASS
- [ ] `python scripts/test_ddl_atomicity.py` still passes, file untouched
- [ ] `python tooling/verify/checks/corpus_gate.py` is green, executed set includes both new checks
- [ ] `python tooling/verify/checks/pipeline_state.py` is green
- [ ] Live: a join turn completes — the `joined` SSE event carries the right gathering id and label, no traceback; the `GatheringMember` row and `conversation.gathering_id` are both persisted, verified on a fresh connection after the response
- [ ] Live: re-joining the same gathering is still a no-op — no second `GatheringMember` row, the original `joined_at` unchanged
- [ ] Live: an in-fiction travel turn completes — the player moves, the previous conversation closes, no traceback
- [ ] Live: a travel turn on which an NPC initiative also fires completes without a traceback (that ordering is what produces `SQLITE_BUSY_SNAPSHOT`)
- [ ] Live: dialogue and physical-action turns still complete (no regression from BRIEF-0072-a)
- [ ] Live: door travel, spatial travel and the direct conversation travel endpoint all still work
- [ ] `/review-step` and `/close-step` run (engine code touched: `play.py`, `play_stream.py`)
- [ ] B1 residue reported, no edits made

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — append to BRIEF-0072-a's entry (Scope IN item 5).
- `world-engine-schema-changelog.md` — extend the ticket's single applicatif
  addendum entry (Scope IN item 6).
- `stream_session_readonly.py`'s module docstring carries the six numbered rules,
  the declared module set and its rationale, and the stated boundary, in the
  same voice as `legacy_mount.py`. This step IS that doc.
- `_join_gathering`'s docstring carries the id-not-object contract (Scope IN
  item 1). This step IS that doc.
- `CLAUDE.md` — no change expected here; BRIEF-0072-a already carries the
  verify-and-report obligation.
