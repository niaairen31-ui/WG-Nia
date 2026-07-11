# BRIEF — Step "Prerequisite judge + briefing injection" (TICKET-0024, BRIEF-0024-b)

## Context

BRIEF-0024-a shipped `npc_goal.prerequisites` (v1 type: `relation_gte`)
with its creator editor. This brief makes the column live on the AI path:
the code judges goal completion against canon ("model proposes, code
judges" — Nia's type-1 mechanic: *to claim you gained someone's trust, the
relation must actually be ≥ threshold*), and the per-NPC tick briefing
shows prerequisite state so the model does not propose doomed completions
in a loop.

## Scope IN

1. **Judge — `_apply_mutation`, `goal_change` branch, `complete` action
   only** (`cockpit/app.py`, after the unique-active-goal match, before
   `write_npc_goal_status`): if the matched goal has non-empty
   `prerequisites`, evaluate each in order. For `relation_gte`: load the
   relation between the goal's `npc_id` and `target_entity_id` using the
   SAME both-directions first-match search as
   `write_relation(mode="delta")` (single source of pair semantics — if a
   small shared helper is needed, extract `_find_relation_pair` into
   `writes.py` and have BOTH call sites use it). Missing relation counts
   as intensity 0. Any unmet prerequisite -> return (whole-mutation
   reject) the exact string:
   `goal_change: prerequisite not met — relation with {entity_name} is {current}, requires >= {threshold}`
   `abandon` and `create_short` are untouched. `fail` does not exist on
   goals — do not add it.
2. **Unknown prerequisite type at judge time** (future-proofing, column is
   creator-authored): reject with
   `goal_change: unknown prerequisite type {type!r}` — fail-closed, never
   skip-and-apply.
3. **Briefing injection — per-NPC tick briefing** (`tick.py`, the goals
   section of the NPC briefing builder): for each ACTIVE goal that has
   prerequisites, resolve each `relation_gte` in code and append ONE line
   per prerequisite, French, verbatim format:
   `  (prérequis : relation >= {threshold} avec {entity_name} — actuel : {current})`
   Resolution reuses the same pair-search helper as the judge (item 1) so
   briefing and judge can never disagree. No prerequisite -> no line
   (prose-only goals stay clean). No new prompt-template text — this is
   assembled context, not rubric (prompts propres: code resolves, injects
   a single line).
4. **Cockpit visibility**: in the Needs-attention / mutation review list,
   the reject reason from item 1 is already surfaced by the existing notes
   plumbing — verify it renders; no new UI.
5. **Docs**: schema doc flips the `prerequisites` DORMANT note to "read by
   `_apply_mutation` goal_change complete + per-NPC tick briefing
   (BRIEF-0024-b)".

## Scope OUT

- NO effects (`effects[]`, H1 strip, clamps) — that is BRIEF-0024-c. The
  judge here only gates; it writes nothing new.
- NO prerequisite check on `agenda_step_change` (G3 deferred, named).
- NO new prerequisite types; NO model-proposed prerequisites (G2).
- NO auto-completion when a prerequisite becomes satisfied — satisfaction
  never triggers anything by itself; the model still proposes, Nia still
  approves.
- NO prompt-template edits, NO apply-prompt script — injection is
  code-assembled context only.
- Do not extend the reject into the conversation-analyzer path:
  `goal_change` there (BRIEF-0013-c) gets the SAME judge for free because
  the judge lives in `_apply_mutation` — do not duplicate it anywhere
  else.

## Invariants to defend

- **Model proposes, code judges**: the model never sees or evaluates
  thresholds itself; it sees resolved state (one injected line) and the
  code alone decides.
- **Single canon-write path**: the judge adds a gate inside the existing
  `goal_change` branch — no new write path, no bypass.
- **Exclusion is structural**: the injected line exposes only the
  relation intensity, which the briefing already exposes through the
  relations section — no secret leakage vector. Confirm the entity name
  used is the plain entity name, not any creator-only field.

## Done means

- [ ] Goal with `relation_gte` 65, live relation intensity 48 -> approving its `goal_change complete` routes to Needs attention with reason `... relation with X is 48, requires >= 65`; goal stays `active`
- [ ] Same goal after relation raised to 70 (creator CRUD) -> completion applies; goal `completed`
- [ ] Goal with prerequisite but NO existing relation row -> reject shows `is 0`
- [ ] Prose-only goal (NULL prerequisites) -> completion applies unchanged (no regression on the 0013-c path)
- [ ] Hand-written unknown type in DB -> reject `unknown prerequisite type`
- [ ] `scripts/preview_tick_context.py` for an NPC owning a prerequisite goal shows the verbatim French line with live numbers; an NPC without prerequisite goals shows no such line
- [ ] `/review-step` and `/close-step` pass

## Docs to update

- `world-engine-schema.md`: DORMANT note flip on `npc_goal.prerequisites`
  (no version bump — no schema shape change; Claude Code judges).
- `ARCHITECTURE_DECISIONS.md`: append record "Prerequisite judge (G1):
  fail-closed, briefing shows resolved state, single pair-search helper
  shared judge/briefing".
