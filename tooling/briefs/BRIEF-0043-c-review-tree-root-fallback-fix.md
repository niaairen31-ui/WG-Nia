# BRIEF — Step "Fix review-tree root fallback + guard it"

## Context
Live-testing TICKET-0041 surfaced a bug that predates that ticket (confirmed
byte-identical logic on `main` before the `regionCascade`/`regionRenderTree`
-> `reviewCascade`/`reviewTree` rename): when a region draft's sole root
location is rejected, its children — whose fallback parent (the rejected
root) is no longer accepted — vanish from the tree entirely, instead of
rendering at top level as the ticket's own acceptance language promises
("reject the root -> its children fall to no-parent and render at top
level"). Root cause: `reviewTree` (`index.html:5967`) builds
`childrenByParent` from `cascade.effectiveParent` (fallback-aware,
`index.html:5910`'s `reviewCascade`) but filters `roots` (line 5980) from the
raw, non-fallback-aware `n.parentId` — a node whose fallback resolves to
`null` is excluded from both structures. Only one consumer, `'region'`
(registered `index.html:6425`), exists today; TICKET-0042's room-batch
generator will register a second on this same shared component, so this is
worth fixing before it lands.

## Scope IN
1. In `src/world_engine/cockpit/index.html`, `reviewTree` (line 5980): change
   `const roots = d.nodes.filter(n => n.parentId == null);` to
   `const roots = d.nodes.filter(n => cascade.effectiveParent[n.id] ==
   null);`. No other line in `reviewTree` or `reviewCascade` changes —
   `effectiveParent` already resolves to `null` unconditionally both for
   genuine roots (raw `parentId == null`) and for fallback-orphaned nodes, so
   this is a full replacement of the predicate, not an added `||` condition.
2. Add a new G1 check, `tooling/verify/checks/review_root_fallback.py`: a
   plain text/regex scan (no DB, same style as `relation_graph.py`'s
   braced-function scans) asserting that `reviewTree`'s `const roots = ...`
   line references `cascade.effectiveParent`, and does not use a bare
   `n.parentId == null` filter for `roots`. Scope the assertion to that
   specific line inside `reviewTree`'s body only — `parentId` legitimately
   still appears elsewhere in the function (e.g. `reviewNode`'s `reparented`
   line), and the check must not flag those.

## Scope OUT
- No change to `reviewCascade`, `reviewNode`, `reviewDescriptor`, or
  `reviewRegister` — the bug and its fix are confined to the one line in
  `reviewTree`.
- No change to the `'region'` descriptor or its registration — this fix must
  render identically for every already-correct tree shape (zero behavior
  change for accepted cases), only correcting the previously-vanishing case.
- Do not add a `'room-batch'` descriptor or anything else needed by
  TICKET-0042 — that ticket hasn't started; this brief only protects the
  shared component ahead of it.
- Do not build a dedicated live-test script for deeper multi-level rejection
  chains (e.g., grandparent and parent both rejected) — the Live gate below
  covers the two-level case from the original bug report; the fix is general
  by construction (re-derived from `reviewCascade`'s own logic) but a chained
  scenario is not separately hand-tested in this brief.

## Invariants to defend
- No `CLAUDE.md` canon-write invariant is touched — this is a review-time
  (pre-commit) rendering fix only; no `_apply_mutation`, no creator CRUD, no
  canon write happens in `reviewTree`/`reviewCascade`.
- BRIEF-0033-c's already-noted behavior ("render every top-level location,
  not just the first found") must not regress — `.filter(...)` still returns
  every matching node; only the predicate changes, preserving that guarantee
  by construction.

## Done means
- [ ] `python tooling/verify/checks/review_root_fallback.py` exits 0 on the
      fixed `index.html`, and exits 1 if the line is reverted to
      `n.parentId == null` (manually confirmed, reverted before commit).
- [ ] Live (Nia): generate a region draft where location A is the sole root
      and locations B, C have `parent_local_id == A`; reject A; confirm B and
      C render as top-level nodes in the review tree, not missing.
- [ ] Live (Nia): a normal draft with no rejections still renders its full
      tree exactly as before (zero-behavior-change sanity pass for the
      unaffected path).
- [ ] `/review-step` run on this brief's diff is clean (touches `index.html`
      and adds `review_root_fallback.py` only).

## Docs to update
- This step IS the doc update — no schema change, no
  `ARCHITECTURE_DECISIONS.md` entry (a bug fix restoring already-documented
  intended behavior, not a new decision).
