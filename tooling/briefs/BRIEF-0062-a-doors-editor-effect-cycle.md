# BRIEF — Step "DoorsEditor effect cycle"

Ticket: TICKET-0062. Single brief. Executes between BRIEF-0059-d (landed) and
BRIEF-0059-e. Locks: **K1, L1, M1**.

## Context

Mutations performed in `RelationsEditor.svelte`, `KnowledgeEditor.svelte` and
`DiscDetailsEditor.svelte` persist correctly on the backend but do not repaint
— **only** when those components are mounted on a location sheet. The same
components work on character sheets. A bare test component in the same slot
reproduces it, so the cause is not in any one editor.

Planning RECON points at `frontend/src/creation/DoorsEditor.svelte:28-44`.
`resetFromProps` assigns `neighbours` at line 29 and reads it at line 37,
inside the body of `$effect(() => { resetFromProps(relations, doors); })` at
line 44. A fresh array is assigned on every run, so once `neighbours` has
become a dependency of the effect (which happens on the first run, after the
untracked initial write) the effect reschedules itself forever and Svelte
throws `effect_update_depth_exceeded` during the flush — taking every sibling
effect scheduled in that same pass down with it.

That is a hypothesis. **This brief confirms it before changing anything.**
A fix landed on an unconfirmed mechanism would be indistinguishable from a
fix that merely perturbs the timing, and the symptom is already known to be
intermittent.

## Scope IN

### Step 0 — empirical confirmation (NO code change, no commit)

1. On the unmodified tree, in a live session with browser devtools open and
   the console unfiltered: open Creation -> lieux, select an existing
   location that has at least one `connects_to` neighbour, and add a relation
   via the Relations editor.

2. Record, verbatim, every console error and warning produced. The prediction
   is a Svelte error whose code is `effect_update_depth_exceeded`.

   Note that the islands are mounted into the legacy **iframe** document
   (`frontend/src/creation/mount.js`). The error still surfaces in the same
   devtools console, but confirm the console's context selector is not
   filtering the frame out before concluding it is absent.

3. Repeat on a **character** sheet with the same action. Record the console
   output there too. The prediction is no such error.

4. Repeat on a location that has **no** `connects_to` neighbour
   (`neighbours` resolves to an empty array both runs, so the loop may not
   fire). Record whether the symptom appears. This distinguishes a real
   dependency cycle from a generic scheduler problem.

5. **STOP and escalate to Nia, changing nothing, if:**
   - `effect_update_depth_exceeded` does not appear in step 2; or
   - it appears in step 3 as well (the character branch is supposed to be
     clean, and its presence there would mean the cause is elsewhere); or
   - step 4 shows the symptom on a location with zero neighbours **and** no
     error is logged.

   Any of these means TICKET-0062's diagnosis is wrong. That is a correct
   outcome for this step, not a failure of it.

6. Write the recorded console output into the commit message of Commit 1, so
   the confirmation is in the history rather than in a session that ends.

### Commit 1 — the fix (lock L1)

7. In `frontend/src/creation/DoorsEditor.svelte`, replace the two
   pure-derivation `$state` bindings with `$derived`:

   - `neighbours` (line 24) becomes a `$derived` of `relations`, filtering
     `r.type === 'connects_to'` and mapping to `{ id: r.other_entity_id,
     name: r.other_entity_name }` — identical predicate, identical shape,
     identical field names.
   - `orphans` (line 25) becomes a `$derived` of `doors`, filtering
     `!d.edge_live` — identical predicate.

   `values` (line 26) stays `$state`: it is seeded from props and then
   mutated by `bind:value`. Its seeding effect now reads `neighbours` (a
   derivation) and `doors` (a prop), and writes only `values`. No binding it
   reads is a binding it writes.

8. `resetFromProps` collapses accordingly. Do not keep a function that
   assigns bindings which no longer exist.

9. `save()` (line 46) and `removeOrphan()` continue to read `neighbours`,
   `orphans` and `values` unchanged — reading a derivation from an event
   handler is not an effect and creates no dependency.

   One behaviour to preserve exactly: `removeOrphan(id)` currently filters
   `orphans` **and then** calls `save()`. With `orphans` derived, that local
   filter no longer sticks. The removal must still take effect the same way
   it does today — the orphan disappears and the change is persisted
   immediately. Read the current behaviour before porting: the legacy
   contract (BRIEF-0034-a) is that removing an orphan saves immediately, and
   `save()` sends only `neighbours`-derived rows, so an orphan is dropped by
   virtue of not being sent. Confirm that the derived version still drops it,
   and that the row disappears after `onSaved` refreshes `doors`. If it does
   not, that is a REPORT and an escalation — do not invent a local override
   list to paper over it.

10. Add a comment above the `$derived` declarations, verbatim:

    > TICKET-0062. neighbours and orphans are pure derivations of props, not
    > state. They were $state, and resetFromProps assigned `neighbours` and
    > then read it inside the same $effect body -- once `neighbours` became a
    > dependency of that effect, every run rescheduled the effect with a
    > fresh array, so it never converged and Svelte threw
    > effect_update_depth_exceeded during the flush. That throw aborted the
    > whole flush, which is why sibling editors on the location sheet
    > (Relations, Knowledge, Discoverable details) silently stopped
    > repainting. Only `values` is state here: it is seeded from props and
    > then edited by the user.

### Commit 2 — the guard

11. Create `tooling/verify/checks/effect_self_write.py`, following the
    project idiom: module-level `FAILURES: list[str]`, a `fail()` appender,
    `_report_and_exit(counts)`, `ROOT` via `parents[3]`.

    The rule: **inside a `$effect` body, a `$state` binding that is assigned
    in that body must not be read afterwards in the same body.** Local
    functions called from the body are inlined one level deep, since that is
    exactly how `resetFromProps` hid the pattern.

    Implementation notes:
    - Collect every `.svelte` file under `frontend/src/`.
    - Per file, collect `$state` binding names from `let <name> = $state`.
    - Locate `$effect(() => {` bodies by brace matching.
    - Append the bodies of any local `function <name>(...) { ... }` called
      from within the effect body (one level, no recursion).
    - For each `$state` name, find the first assignment
      (`<name> =`, not `==`, not preceded by `.` or a word character); if a
      subsequent read of the form `<name>.` or `<name>[` occurs after that
      assignment's statement, FAIL naming file, line, binding and the reading
      expression.

    Reference implementation behaviour: on the tree **before** Commit 1 this
    rule yields exactly one finding, `DoorsEditor.svelte:44` / `neighbours`.
    On the tree **after** Commit 1 it yields zero. Verify both.

12. **The vacuity guard goes on the SCAN, not on the finding count.** This
    check is unlike most in `tooling/verify/checks/` — zero findings is the
    desired steady state, so "zero findings is a vacuous pass" does not
    apply. Instead:

    - Zero `.svelte` files collected -> FAIL, "vacuous scan: no components".
    - Zero `$effect` bodies parsed across all files -> FAIL, "vacuous scan:
      no effects parsed" (this catches the brace matcher silently breaking on
      a syntax it does not handle).
    - Zero `$state` bindings found across all files -> FAIL.

    State this distinction explicitly in the module docstring so a future
    reader does not "fix" the check by making zero findings a failure.

13. Register the check in `tooling/verify/run.py` alongside the others.

14. Add to the module docstring, verbatim:

    > TICKET-0062. Narrow by design: this forbids ASSIGN-then-READ of the
    > same $state binding within one $effect body, not self-referential
    > effects in general. RelationsEditor.svelte's `newOther` effect reads
    > that binding and then conditionally assigns it under a converging
    > guard -- a legitimate pattern this rule must not flag. The ordering is
    > the whole rule.

### Report only

15. Record, without fixing, in the Commit 2 message:
    - `Sheet.svelte:574` passes
      `geometry={detail.geometry || { bounds_width: null, bounds_height: null, obstacles: [] }}`
      — a fresh object literal whenever `detail.geometry` is falsy, so
      `GeometryEditor`'s effect re-runs on every parent update and discards
      in-progress edits on a location with no geometry yet.
    - `DoorsEditor`'s `values` is reseeded whenever props change, so a
      concurrent `onSaved` discards an in-flight x/y entry.
    - Whether `flushSync` at `Sheet.svelte:575` and `:581` was observed to
      convert the scheduler abort into a synchronous throw at the caller
      (step 2's console output should show where the stack originates).

## Scope OUT

- **`GeometryEditor.svelte`.** It has no assign-then-read and is not the
  cycle. Its object-literal prop defect is REPORTED (item 15), not fixed —
  fixing it here would make it impossible to attribute the live-gate result
  to one change.
- **`RelationsEditor.svelte`, `KnowledgeEditor.svelte`,
  `DiscDetailsEditor.svelte`.** Byte-untouched. They are victims, not causes;
  if the fix is right they need no change, and if they need a change the
  diagnosis was wrong and this is an escalation.
- **`Sheet.svelte`.** Byte-untouched, including the `flushSync` wrappers and
  the object-literal geometry prop. BRIEF-0059-e rewrites this file's state
  ownership; touching it here would collide.
- **Removing or relocating `flushSync`.** It is a suspected amplifier, not
  the cause, and its removal has its own live-behaviour consequences
  (`sheetRequest.svelte.js` documents that the header-sync effect depends on
  flush ordering).
- **A generic ban on self-referential `$effect`s.** Item 14 exists precisely
  to prevent that broadening. `RelationsEditor:41` must keep passing.
- **Converting other components' `$state` to `$derived`** because it would be
  tidier. Nothing else trips the rule. Speculative conversion here is
  unreviewable churn inside a bug ticket.
- **Any TICKET-0059 work.** This brief lands, is verified live, and then
  BRIEF-0059-e proceeds.
- **Any backend change.** The backend was confirmed correct by direct API
  check during the field report; there is nothing to fix there.

## Invariants to defend

- **Structural over disciplinary.** The fix alone would leave the pattern
  reconstructible at the next port. Commit 2 makes it non-constructible.
- **Fail-closed, with the vacuity guard in the right place.** Item 12. A
  check whose brace matcher silently parses nothing must fail, not pass —
  and it must not be "corrected" into treating zero findings as failure.
- **Empirically confirmed, not assumed.** Step 0 exists because the
  mechanism in this brief was reasoned out from a source tarball, not
  observed. The project's standing rule is that assertions about runtime
  behaviour are confirmed before they become law.
- **Frontend-only scope.** Nothing under `src/world_engine/` is touched.
- **No behaviour change beyond the repaint.** The Portes editor's neighbour
  rows, orphan rows, x/y semantics, immediate-save-on-orphan-removal and
  status messages are all identical before and after.

## Done means

- [ ] Step 0's console output is recorded verbatim in Commit 1's message,
      including the character-sheet control case and the zero-neighbour case.
- [ ] `python tooling/verify/checks/effect_self_write.py` reports exactly one
      finding (`DoorsEditor.svelte`, `neighbours`) when run against the tree
      **before** Commit 1, and zero findings after. Both runs recorded.
- [ ] Scratch A: re-introduce assign-then-read of a `$state` binding in any
      component; the check exits non-zero naming the file, line and binding;
      revert.
- [ ] Scratch B: point the scan at an empty directory; exits non-zero naming
      "vacuous scan", never 0; restore.
- [ ] Scratch C: confirm `RelationsEditor.svelte:41` (`newOther`) does NOT
      trip the check — the read-then-guarded-assign pattern must stay legal.
- [ ] `git diff --stat` for Commit 1 shows `DoorsEditor.svelte` only.
- [ ] Live: on an existing location with at least one `connects_to`
      neighbour — add a relation; the Relations list repaints immediately,
      with no reselect and no reload.
- [ ] Live: same location — add a discoverable detail, then a knowledge row;
      both lists repaint immediately.
- [ ] Live: adding a `connects_to` relation makes a new neighbour row appear
      in Portes without a reload.
- [ ] Live: Portes still lists neighbours, still shows orphan doors
      read-only, still saves x/y, and removing an orphan still persists
      immediately and the row disappears.
- [ ] Live: Spatial geometry still loads, adds, removes and saves obstacles.
- [ ] Live: the same three mutations on a character sheet still work.
- [ ] Live: devtools console is clean of `effect_update_depth_exceeded`
      through all of the above.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

`ARCHITECTURE_DECISIONS.md` gains one short entry recording the rule and its
reason: pure derivations of props are `$derived`, not `$state`, and
assign-then-read of a `$state` binding inside one `$effect` body is
structurally forbidden by `effect_self_write.py`. Include the observed
failure mode — a flush aborted by `effect_update_depth_exceeded` silently
stops sibling components repainting — because the symptom is far from the
cause and the next person to hit it will not connect them.

`CLAUDE.md` gains the check in its inventory only if the inventory enumerates
checks by name; do not expand the file otherwise (500-line budget,
law-only).
