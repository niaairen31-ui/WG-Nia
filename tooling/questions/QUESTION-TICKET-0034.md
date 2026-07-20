# QUESTION — TICKET-0034
Trigger: D1-c
## Context

Executing BRIEF-0034-c, Scope IN item 1: capture `origin_location_id` in
`_perform_travel` (`src/world_engine/cockpit/play_stream.py`) and add it to
the `ok` return, with a mandatory verbatim comment at the capture site
(6 comment lines + the assignment).

`play_stream.py` was already at exactly 1000 lines before this step (the
`module_budget.py` cap, last touched at BRIEF-0028-e's decomposition —
confirmed via `git log`). The brief's own "Invariants to defend" section
only checked headroom on `routes/play.py` (649/1000, room available) and
did not anticipate `play_stream.py` being flush against its cap. Adding the
mandated comment + assignment (minimum 7 lines, verbatim text non-negotiable
per Scope IN) pushes it to 1007-1008 lines, failing `module_budget.py`:

```
FAIL: src/world_engine/cockpit/play_stream.py is 26 functions / 1008 lines
(cap 40/1000) and not present in module_budget.json
```

No baseline file exists (`tooling/verify/baselines/module_budget.json` is
absent — the check treats a missing file as an EMPTY exemption set, and
its own docstring states the baseline mechanism was "retired at
TICKET-0028's close" and "may only shrink or disappear," never regrow).
`module_budget.py`'s docstring is explicit: "a doctrinal registry module
legitimately growing past the cap is the intended tripwire forcing a
split — the failing check IS the mechanism, not a bug to route around."
CLAUDE.md's own invariant for this brief echoes the same posture for
`routes/play.py`: "If it does not [have room], the failing check IS the
mechanism: REPORT, do not baseline."

Splitting `play_stream.py` (26 functions, several sizeable — `_say_stream_mj_narration`,
`_mj_user_physical`, `_build_mj_user`, the initiative chain) is a real
architecture decision — which function(s) move, to what new module, updating
every caller — squarely outside BRIEF-0034-c's Scope IN (4 listed items) and
Scope OUT ("Touching `_perform_travel`'s behavior... REPORT ONLY"), and
above TICKET-0034's stated `blast_radius: medium`.

## Question

How should `play_stream.py` clear the 1000-line module-budget cap for this
step: shorten the mandated comment (deviating from the brief's "verbatim"
instruction), split `play_stream.py` into two modules (a follow-up brief,
out of this ticket's scope), or something else?

## Options

A. Shorten the comment to convey the same content (G1 rationale: transient,
   no `character.last_location_id` column, client carries it to
   `GET /api/spatial/spawn`) in fewer lines, deviating from the brief's
   "verbatim" text. Minimal, stays in this ticket, but is exactly the kind
   of check-dodge `module_budget.py`'s docstring calls out as not the
   intended response.
B. Split `play_stream.py` now, as a same-ticket addendum to BRIEF-0034-c
   (or a new BRIEF-0034-e), moving a natural seam (e.g. the NPC-initiative
   chain, `_say_initiative_*` + helpers, ~350 lines) to a new module. Matches
   the check's own stated intent but is real, unplanned architecture work
   above this ticket's `blast_radius: medium`.
C. Add a one-line baseline entry for `play_stream.py` at 1008 lines in a
   newly-created `tooling/verify/baselines/module_budget.json`. Directly
   reverses the TICKET-0028 retirement of that mechanism ("this check never
   rewrites the baseline" / "may only shrink or disappear") — a policy
   decision, not an execution one.
D. Something else Nia specifies.

## Response

