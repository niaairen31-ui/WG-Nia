# BRIEF — Step "Canon-write convention normalization" (BRIEF-0003-a)

Ticket: TICKET-0003. Recon: RECON-0003 (result). Sequence: runs BEFORE
BRIEF-0003-b. Engine code is touched: commit discipline applies
(/review-step + /close-step), live-testable before b starts.

## Context

RECON-0003 found two places where a `change_history`-bearing table is
written in two different code shapes. (1) `_apply_mutation`'s
`knowledge_change` branch (app.py:846-870) bypasses the public
`write_knowledge` and instead imports writes.py's private
`_append_knowledge_history` (app.py:86, :865) then hand-mutates
`row.level`/`row.source`/`row.updated_at` + `db.add(row)`. (2)
`cockpit/crud.py`'s `update_skill_tier` (crud.py:1082-1085) hand-rolls the
`skill.change_history` append with no writes.py helper at all. Locked
decisions M1 and W1: one table, one write shape — every
`change_history`-bearing table writes exclusively through `writes.py`.
This also makes BRIEF-0003-b's allowlist clean.

RECON anchors were taken at `ticket/0001` HEAD (`426b2a9`); re-verify each
anchor by content before editing.

## Scope IN

1. **M1 — extend `write_knowledge` with the level-change operation**
   (writes.py:256-319):
   - Add an explicit mode following the module's existing idiom
     (`write_relation` has `mode="delta"|"set"`, `write_membership` has
     `mode="open"|"close"`). Suggested: `mode="level_change"` with the
     current behavior as the default mode, existing callers untouched.
   - The new mode must reproduce EXACTLY the semantics of app.py:865-869:
     append the history entry via `_append_knowledge_history` (internal
     call, as `write_knowledge` already does at writes.py:293), then set
     `level`, `source`, `updated_at`, then persist. The history-entry
     dict shape must be byte-identical to what the hand-rolled branch
     produces today (same keys, same value formats) — existing rows'
     history must remain homogeneous.
   - **Stop-and-report** if `write_knowledge`'s current signature cannot
     absorb the operation without changing any existing caller's behavior.

2. **M1 — rewrite the `knowledge_change` branch** (app.py:846-870) to call
   `write_knowledge(mode="level_change", ...)`. Remove
   `_append_knowledge_history` from app.py's import list (app.py:84-92).
   After this step, `_append_knowledge_history` has exactly one caller:
   `write_knowledge` itself.

3. **W1 — create `write_skill_tier` in `writes.py`**: appends the
   `skill.change_history` entry (byte-identical shape to the hand-rolled
   entry at crud.py:1082-1085 today), sets `tier`, persists. Docstring
   states it is the sole write shape for `skill` tier changes. Follow the
   module's existing docstring/style conventions (writes.py:1-30 preamble).

4. **W1 — rewrite `update_skill_tier`** (crud.py:1076-1085 area) to call
   `write_skill_tier`. No hand-rolled history append remains in crud.py.

5. Two commits: commit 1 = items 1-2 (M1), commit 2 = items 3-4 (W1).

## Scope OUT

- The check, the allowlist/policy file, the CLAUDE.md hard-delete list —
  all of it is BRIEF-0003-b.
- The three hard-delete routes (`delete_relation`, `delete_knowledge`,
  `delete_discoverable_detail`): do NOT touch them; L1 handles them in b.
- No helper is created for tables that have none today (`entity`,
  `character`, `world`, `discoverable_detail`, `item`, ...) — W1 covers
  `skill` only, because only `skill` carries a `change_history` written
  outside writes.py.
- `scripts/seed_pilot.py`'s `upsert_knowledge` and
  `align_relation_intensity` bypasses: untouched (scripts are outside the
  live-path doctrine; classification E1 handled in b via check scope).
- No schema change, no version bump.
- `pass_play.history` (models.py:417-420): dormant legacy, no active
  write path (RECON A2) — not W1's business.

## Invariants to defend

- **History is sacred**: the history-entry shapes must not change — this
  brief moves WHERE the append happens, never WHAT is appended.
- **`_apply_mutation` is the sole apply path**: unchanged; only the
  internal shape of one branch changes.
- **Model proposes, code judges**: untouched — no prompt, no proposal
  format changes.

## Done means

- [ ] Grep: `_append_knowledge_history` appears in exactly one module
      (`writes.py`); no hand-rolled `change_history` append remains in
      `crud.py`.
- [ ] Live test (Nia): trigger a `knowledge_change` proposal in play,
      approve it in the cockpit → `knowledge.level` updated AND the new
      history entry is shape-identical to pre-existing entries on the same
      row.
- [ ] Live test (Nia): update a skill tier in the cockpit → tier updated,
      history appended, same shape as existing entries.
- [ ] /review-step + /close-step run for both commits (engine code).
- [ ] /verify TICKET-0003 not yet expected green (the check ships in b).

## Docs to update

No schema change → no changelog entry (confirm via close-step). The
consolidated decision record for K1/L1/M1/W1/T1 is written in
BRIEF-0003-b. CLAUDE.md untouched by this brief.
