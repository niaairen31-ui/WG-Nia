---
id: TICKET-0062
title: Location sheet effect cycle — async state updates do not paint
type: bug
status: done   # merged to main via PR #80 (rode ticket/0059's branch, K1/K2 -- no dedicated PR)
created: 2026-08-03
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0062-a]  # executes on ticket/0059 per K1/K2; no dedicated ticket/0062 branch
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Un bug a été découvert pendant l'exécution de D. On peut le régler dans un
brief en parallèle ou je le fais après le ticket, ta suggestion."

Field report, abridged: on the Creation "lieux" tab, a mutation performed in
`RelationsEditor.svelte`, `KnowledgeEditor.svelte` or `DiscDetailsEditor.svelte`
succeeds on the backend (verified by direct API check) but the component's own
list does not repaint. The same `RelationsEditor.svelte` works correctly on
character sheets. A bare minimal test component mounted in the same field-
section slot also failed to update; removing `GeometryEditor` and `DoorsEditor`
from `Sheet.svelte`'s template made it work again. Intermittent on retry.

## Clarifications resolved (intake)

**K1 — dedicated ticket, one brief, inserted between BRIEF-0059-d and
BRIEF-0059-e.**

TICKET-0059's remaining briefs (`-e` through `-l`) each carry live human gate
criteria, several of which run through the lieux tab. TICKET-0058's own live
gate was signed off on a surface that was already silently broken. Deferring
this to after TICKET-0059 means verifying eight briefs blind on the location
branch.

Rejected: a parallel branch (K2). Merge risk is genuinely low — the fix
touches `DoorsEditor.svelte` while BRIEF-0059-e rewrites `Sheet.svelte` — but
the blockage is present now and splitting attention across two branches buys
nothing.

Rejected: after TICKET-0059 (K3), for the reason above.

**Diagnosis (planning RECON, this session, against `main` after `-d`).**

`frontend/src/creation/DoorsEditor.svelte:28-44`. `resetFromProps` assigns
`neighbours` (line 29) and then reads it (line 37) inside the same
`$effect` body:

```js
neighbours = (rels || []).filter(...).map(...);   // new array every run
...
neighbours.forEach((n) => { next[n.id] = ...; }); // read of what was just written
values = next;
```

Presumed mechanism, to be confirmed empirically before any fix lands:

- **First run (mount).** `neighbours` is written before it is a dependency,
  so Svelte 5 records an untracked write and does not reschedule. It is then
  read, becoming a dependency. The first paint is correct — which is why the
  sheet looks fine until something changes.
- **Second run.** `onSaved(detail)` refreshes `detail`, so `relations` and
  `doors` change and the effect re-runs. `neighbours` is now already a
  dependency: writing it marks it dirty and reschedules the effect. A fresh
  array is assigned every run, so equality never holds and the loop never
  converges — `effect_update_depth_exceeded`.
- The throw happens during the flush, so sibling effects scheduled in the
  same pass never run. That is why `RelationsEditor`, `KnowledgeEditor` and
  `DiscDetailsEditor` stop painting, and why a bare test component in the
  same slot reproduces it.

`Sheet.svelte:575` and `:581` wrap `onSaved` in `flushSync(...)`, which turns
an asynchronous scheduler abort into a synchronous throw at the caller's call
site. That is the suspected amplifier and part of what the brief must confirm.

**`GeometryEditor.svelte` is not the cycle.** `resetFromGeometry` writes
`items` / `boundsWidth` / `boundsHeight` and reads none of them. It carries a
separate, lesser defect reported below.

**Structural scan.** Applying the rule *"inside a `$effect` body (local
functions inlined one level), a `$state` binding that is assigned must not be
read later in the same body"* across every `.svelte` file under
`frontend/src/` yields exactly one hit:

```
DoorsEditor.svelte:44  'neighbours': assigned then READ later
```

Zero false positives. `RelationsEditor.svelte:41` also writes a `$state`
binding it reads (`newOther`), but reads it *before* assigning and under a
converging guard — the ordering rule correctly leaves it alone. The rule is
therefore narrow enough to ship as a fail-closed check rather than a
convention.

**L1 — `neighbours` and `orphans` become `$derived`.**

They are pure functions of props, not state. Making them derivations removes
the cycle by construction rather than by careful write ordering. Only
`values` remains `$state`: it is seeded from props and then edited by the
user.

Rejected: reordering the assignments so the reads come first (L2). It fixes
the symptom and leaves three `$state` bindings that were never state.

Rejected: wrapping the read in `untrack()` (L3). That hides a cycle rather
than removing one.

**M1 — reproduce and confirm the error code before fixing.**

The brief's first step produces no code change: reproduce in a live session
with devtools open and confirm `effect_update_depth_exceeded` in the console.
If that error does not appear, the mechanism above is wrong and the brief
stops. A fix must not land on a diagnosis authored from a tarball, however
confidently written.

**Reported, not fixed by this ticket:**

- `Sheet.svelte:574` passes
  `geometry={detail.geometry || { bounds_width: null, bounds_height: null, obstacles: [] }}`
  — a fresh object literal whenever `detail.geometry` is falsy, so
  `GeometryEditor`'s effect re-runs and clobbers in-progress edits on any
  location that has no geometry yet. No cycle, but a real defect.
- `DoorsEditor`'s `values` is reseeded from props on every prop change, so a
  concurrent `onSaved` discards an in-flight x/y entry. Pre-existing.

Both are recorded for a follow-up ticket; neither is in scope here.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [x] `effect_self_write.py` exists, is fail-closed, and reports zero
      findings on the fixed tree  ->  verify/checks/effect_self_write.py
- [x] The check fails when its scan collects zero `.svelte` files, or parses
      zero `$effect` bodies — the vacuity guard is on the SCAN, not on the
      finding count, since zero findings is the goal state here  ->
      verify/checks/effect_self_write.py
- [x] Re-introducing the assign-then-read pattern in any `.svelte` file under
      `frontend/src/` makes the check exit non-zero  ->
      verify/checks/effect_self_write.py
- [x] `DoorsEditor.svelte` declares no `$state` binding that is assigned
      inside an `$effect` body and read later in that body
- [x] `npm run build` output is fresh  ->  verify/checks/frontend_build_fresh.py
- [x] `python tooling/verify/run.py` exits 0

### Live  ->  human gate (Nia)

Pre-verified via browser automation against the test DB during exec
(see BRIEF-0062-a commit 1's message for the full session): relations/
knowledge/Portes repaint correctly on a location with a `connects_to`
neighbour, the character-sheet control case is unaffected, geometry
still saves. Left unchecked below — this section is Nia's own gate,
not something exec checks off on her behalf.

- [ ] Devtools console shows `effect_update_depth_exceeded` on the
      unmodified tree when adding a relation to an existing location, and
      does not after the fix. (If it never appears before the fix, this
      ticket's diagnosis is wrong — escalate.)
- [ ] On an existing location: add a relation; the Relations list repaints
      immediately without reselecting or reloading.
- [ ] On the same location: add a discoverable detail; the list repaints.
      Add a knowledge row; the list repaints.
- [ ] On the same location: the Portes editor still lists `connects_to`
      neighbours, still shows orphan doors read-only, still saves x/y, and
      removing an orphan still saves immediately.
- [ ] Adding a `connects_to` relation makes a new neighbour row appear in
      Portes without a reload — this is the derived path working.
- [ ] The Spatial geometry editor still loads, adds, removes and saves
      obstacles.
- [ ] The same mutations on a character sheet still work (no regression on
      the branch that was already healthy).
