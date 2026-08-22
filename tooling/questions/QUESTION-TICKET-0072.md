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
