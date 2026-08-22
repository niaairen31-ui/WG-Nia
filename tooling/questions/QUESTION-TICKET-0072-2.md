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
