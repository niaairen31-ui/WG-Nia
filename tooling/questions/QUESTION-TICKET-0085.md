# QUESTION — TICKET-0085
Trigger: D1-d
## Context

BRIEF-0085-f (planner-unavailable message) is implemented and live-verified
on `ticket/0085`, which is now rebased onto `main` (picking up TICKET-0086's
corpus_gate fix, merged as #111):

- `lore_isolation.py` R16 (new, this brief) passes: `ask_lore`'s
  `OllamaError` handler now raises `HTTPException(detail=
  _lore_render.PLANNER_UNAVAILABLE_MESSAGE)`.
- Live-verified with Ollama actually stopped: a fresh `POST /api/lore/ask`
  returns HTTP 503 with `detail` equal, verbatim, to
  `PLANNER_UNAVAILABLE_MESSAGE`. `POST /api/lore/resolve` with a
  previously-obtained plan still returns HTTP 200, `renderer: "template"`
  (regression-checked, unaffected).
- Live-verified with Ollama running: a fresh `POST /api/lore/ask` behaves
  exactly as before this brief (model drafts a plan, executes it,
  renders normally) — confirmed with "Qui est Maelis ?" (verdict
  `answered`, `renderer: "model"`) and "Est-ce que Maelis connaît Reike ?"
  (verdict `unsupported_selector`, correctly rejected before any DB read).
  Note: the PR's own previously-cited test question, "Est-ce que Mara
  connaît Corvin ?", no longer resolves either name in the current seed
  data (unrelated data drift, not a regression from this brief).

`/verify` for the full ticket is red on a check unrelated to BRIEF-0085-f:

```
FAIL: npc_goal_read.py — FAIL: src/world_engine/lore_selectors.py:169:
  NpcGoal referenced outside the allowlist
SUMMARY: 1 check(s) failed (0 environment, 0 crash, 0 timeout, 1 other)
```

`lore_selectors.py`'s `entity_dossier` selector has a `_goal_rows` helper
(reading `NpcGoal` directly, returning `description`/`status`/`horizon`/
`kind` as the dossier's "goals" section) that was added by BRIEF-0085-b —
this ticket's own earlier work, already merged into `ticket/0085` and
already live-tested end-to-end as part of PR #112 (goals are part of the
"identity, relations, knowledge, memberships, goals" dossier documented in
`lore_selectors.py`'s own docstring). `lore_selectors.py` was never added to
`npc_goal_read.py`'s `ALLOWED_MODULES` — the N1 doctrine gate that lists
every module allowed to reference `NpcGoal` (`context.py`,
`day_concordance.py`, the CRUD routes, etc.). This is not something
BRIEF-0085-f touches or could fix within its own Scope IN
(`cockpit/routes/lore.py` / `lore_render.py` / `lore_isolation.py` only) —
confirmed by diff: `lore_selectors.py` has zero uncommitted changes on this
branch. It is exactly the same shape of problem TICKET-0086 just fixed
twice in this same file (`ALLOWED_MODULES` not yet widened to cover a
legitimate new reader) — but this one is inside TICKET-0085's own delivered
code, not pre-existing on `main`.

Per V1, `retry_count` is already `1` from the prior escalation cycle
(D1-d, resolved by your answer + TICKET-0086). BRIEF-0085-f's own Scope OUT
/ Decision rights explicitly STOP if fixing a corpus_gate item "requires
touching a file outside `cockpit/routes/lore.py` / `lore_render.py` /
`lore_isolation.py`" — this does (`npc_goal_read.py`, and arguably a design
call on `lore_selectors.py` itself). I have not attempted an in-scope fix
because none exists; escalating rather than widening a different brief's
already-closed scope or silently editing a structural allowlist.

## Question

`lore_selectors.py`'s `entity_dossier` goals section trips `npc_goal_read.py`'s
module allowlist. Is creator-facing goal exposure through the lore
consultation surface intended (in which case the allowlist should simply
grow, same precedent as `context.py`/`day_concordance.py`), or should the
"goals" section come out of `entity_dossier` — and either way, how should
the fix land given it's outside this brief's Scope IN?

## Options

- (a) Intended: add `src/world_engine/lore_selectors.py` to
  `npc_goal_read.py`'s `ALLOWED_MODULES` (one line + a justifying comment,
  same shape as the two entries TICKET-0086 just added), as its own small
  ticket landed on `main` first — same playbook as TICKET-0086 — then
  rebase `ticket/0085` and re-verify.
- (b) Not intended: drop the "goals" section from `entity_dossier` /
  `lore_render.py`'s section contract (a real code change, its own brief on
  `ticket/0085`, since the surface is already live-tested with goals
  present).
- (c) Something else — you may want goals gated differently (e.g. only
  non-secret/standing goals) rather than an all-or-nothing include/exclude.

## Response
(empty)
