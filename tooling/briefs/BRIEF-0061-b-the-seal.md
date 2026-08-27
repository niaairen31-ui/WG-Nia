# BRIEF — Step "the seal: Play sealed, the pointer made true, the document put on a ratchet"

Ticket: TICKET-0061 · Brief: BRIEF-0061-b · Branch: `ticket/0061`

## Context

Decision A3: Play is sealed, not migrated. `LEGACY_MOUNTS` keeps `play`; the
legacy document stays; its migration becomes TICKET-0069.

That decision is worthless if the tree keeps saying the opposite.
`registry.js` reads `retiredBy: 'TICKET-0061'` and `legacy_calls.baseline`
reads `::TICKET-0061` — both will be false the moment this ticket merges, and
both are blessed by checks that validate only the FORMAT of a ticket id.
This brief makes the pointer true, and then makes it *unable* to become
false again (3b).

It also closes the one thing a year-long seal actually risks: the legacy
document is exempt from every budget the rest of the codebase obeys.

**HARD PREREQUISITE.** `tooling/tickets/TICKET-0069-play-surface-migration.md`
must be on `main` before commit 2. Rule 3b reads it. Measured at this brief's
RECON: it is **not** there yet.

Three commits.

---

## Mini-RECON — anchors measured on `main`, 2026-08-20, post-TICKET-0067

Tree-specific claims. **Verify each locally.** If any has drifted, STOP.

| Anchor | Measured |
|---|---|
| `frontend/src/legacy/registry.js:24` | `play: Object.freeze({ showFn: 'showPlayView', retiredBy: 'TICKET-0061' }),` |
| `frontend/src/legacy/registry.js:4` | the comment says `play` *survives at* TICKET-0061 — contradicting the field five lines below |
| `tooling/verify/baselines/legacy_calls.baseline` | one line: `frontend/src/App.svelte::showFn::TICKET-0061` |
| `tooling/verify/baselines/legacy_mounts.baseline` | `observation`, `play` |
| `legacy_mount.py:51` | `RETIRED_BY_RE = re.compile(r"^TICKET-\d{4}$")` |
| `legacy_mount.py:113-121` | `_check_retired_by` — validates the format and **nothing else** |
| `legacy_call.py` rule 8 | same shape: `retiredBy` format only |
| `legacy_call.py` rule 6 | asserts `legacyCall` is defined **exactly once and exported** in `bridge.js` |
| `frontend/src/legacy/bridge.js:68` | `export function legacyCall(...)` — **zero call sites** in `frontend/src` |
| `src/world_engine/cockpit/index.html` | **2 762 lines**, 73 top-level functions |
| `module_budget.py:43-44` | `MAX_LINES = 1000`, `FRONTEND_MAX_LINES = 1000` |
| `module_budget.py:105-125` | `_check_frontend_line_budget` — scans `frontend/src/**/*.{svelte,js}` only |
| `tooling/verify/baselines/module_budget.json` | **does not exist**; a missing baseline is an empty exemption set, cap enforced fail-closed |
| `function_length.py` | scans `src/**/*.py` only — the legacy document's JS is outside it too |
| Repoint dry-run | repointing both `retiredBy` fields to `TICKET-0069` leaves `legacy_call`, `legacy_mount` and `stylesheet_partition` green (verified on a simulated tree) |

### A correction the ticket carries and this brief overrides

TICKET-0067's decision table and TICKET-0061's brief decomposition both list
"`legacyCall` removed from `bridge.js` and `legacy_calls.baseline` shrunk
accordingly" as part of this brief. **That specification is wrong and is
withdrawn here.** Measured: deleting `export function legacyCall` produces

```
FAIL: rule6: legacyCall is defined 0 time(s) in the tree, expected exactly 1
```

`legacyCall` is not dead code awaiting a purge — it is the *declared shape of
the bridge primitive*, held in place by a fail-closed confinement rule. It
has zero call sites because every consumer migrated, which is the rule
working, not rotting. It dies with the bridge at TICKET-0069. Do not remove
it, and do not weaken rule 6 to permit its removal.

### Hard STOP conditions

1. **`TICKET-0069-*.md` is not on `main`.** Rule 3b is red by construction
   without it. Stop before commit 2 and report.
2. **`registry.js` declares more than one entry**, or an entry other than
   `play`. The seal assumes exactly one survivor.
3. **`legacy_calls.baseline` holds more than one record**, or a record whose
   `retiredBy` is not `TICKET-0061`. `_load_baseline` fails on an empty
   file, so the file must never be emptied.
4. **The legacy document's line count differs from 2 762.** The ratchet is
   set to the committed count; a different number means the tree drifted and
   the ceiling must be re-measured, not copied from this brief.
5. **Any check outside `legacy_mount.py` and `module_budget.py` changes
   verdict.**

---

## Scope IN

### Commit 1 — the pointer becomes true (A3)

**1.1 — `frontend/src/legacy/registry.js`:** `retiredBy: 'TICKET-0069'`.

**1.2 — `tooling/verify/baselines/legacy_calls.baseline`:** the single
record becomes `frontend/src/App.svelte::showFn::TICKET-0069`. Same reason:
`showSurface` survives this ticket, so the ticket that retires it is 0069.

**1.3 — Correct `registry.js`'s comment by APPENDING, never by editing.**
The existing block says `play` survives at TICKET-0061 while the field said
it retires there — the contradiction is now resolved and the resolution is
the record. Append beneath the existing comment, verbatim:

```
   TICKET-0061 (A3). The contradiction above is settled: `play` SURVIVES
   this ticket. TICKET-0056's own decision entry said so ("survives to
   TICKET-0061 and beyond, until its own rewrite"); TICKET-0060's entry
   later said the opposite ("TICKET-0061 empties LEGACY_MOUNTS"), and this
   field carried that second reading. Resolved in favour of TICKET-0056 and
   repointed at TICKET-0069, the Play migration, deposited paused. Rule 3b
   (legacy_mount.py) now asserts that ticket exists and is not done, so
   this field can no longer be a well-formed sentence naming a finished
   ticket.
```

Do not delete the sentence that was wrong. It is history, and the appended
paragraph is what makes it legible.

### Commit 2 — rule 3b: the pointer cannot become false again

`legacy_mount.py`'s `_check_retired_by` validates a regex. Extend it so that
for every entry, the named ticket **exists on disk** and its `status` is
**not** `done`. A `retiredBy` naming a finished ticket while the mount still
lives is a contradiction, and after this commit it is unconstructible.

Requirements on the implementation:

- **Resolve the ticket by glob**: `tooling/tickets/{retiredBy}-*.md`. Exactly
  one match; zero or several is a FAILURE naming the pattern.
- **Read `status` from the YAML front-matter** the same way
  `pipeline_state.py` does — a bare enum member. Do not re-implement a YAML
  parser; mirror that module's field extraction.
- **`status == "done"` is a FAILURE** whose message names the mount key, the
  ticket, and the contradiction — not a generic mismatch.
- **Vacuous-proof**: a missing ticket file, an unreadable one, or a
  front-matter with no `status` field are each a FAILURE. A rule that
  passes because it found nothing to inspect is the flaw the whole ticket
  exists to close.
- Extend `legacy_mount.py`'s docstring rule 3 to state both new clauses.
  Append; do not rewrite.

Apply the same reasoning to `legacy_call.py` rule 8 **only if** it can be
done by reusing the helper written here rather than duplicating it. If it
would mean a second implementation of the same assertion, leave rule 8
alone and record it as a named deferral with its reactivation condition
(a shared helper exists) — two implementations of one rule is the
divergence this project's whole doctrine is against.

**Red-tests to run and record in commit 2's message:**

1. Point `retiredBy` at a ticket id with no file → FAIL naming the glob.
2. Set `TICKET-0069`'s status to `done` → FAIL naming the contradiction.
3. Delete `TICKET-0069-*.md` → FAIL naming the missing path.

Revert each.

### Commit 3 — the legacy document goes on a ratchet

The legacy document is outside `module_budget.py` (which covers
`src/**/*.py` and `frontend/src/**/*.{svelte,js}`) and outside
`function_length.py` (`src/**/*.py`). At 2 762 lines it is 2.7× the cap every
other frontend module obeys, and under A3 that exemption lives a year or
more.

Add a rule to `module_budget.py` — **a ratchet, not the 1000-line cap**,
which would be red on arrival and prove nothing:

- The ceiling is the document's **committed line count**, declared as a
  named constant with a comment recording that it may only ever decrease.
- Exceeding it is a FAILURE naming both numbers.
- **Coming in under it is also a FAILURE**, with a message instructing that
  the constant be lowered to the new count in the same commit. That is what
  makes it a ratchet rather than a ceiling: the document is on the same
  monotonically-shrinking discipline as `LEGACY_MOUNTS`, and the constant
  cannot silently drift above the truth.
- The file must exist: absence is a FAILURE, not a vacuous pass. (After
  brief -c it is `legacy.html`; this commit lands before the rename, so the
  constant names `index.html` and brief -c moves it with the other eight
  path sites.)
- Amend `module_budget.py`'s docstring to name the new rule and why the
  legacy document needs one. Append.

**Red-tests, recorded in commit 3's message:** add one line to the document
→ FAIL; delete one line → FAIL instructing the constant be lowered; delete
the file → FAIL. Revert each.

---

## Scope OUT

REPORT ONLY:

- **Removing `legacyCall` from `bridge.js`.** Withdrawn above, with the
  measured reason. It retires with the bridge at TICKET-0069.
- **Any change to `legacy_call.py` rule 6.** Weakening a confinement rule so
  a dead-looking export can be deleted is the inverse of this ticket.
- **`legacy_mounts.baseline`.** It holds `observation` and `play`; the
  registry is a subset; nothing to do. Do not shrink it to match.
- **Bringing the legacy document under `function_length.py`.**
  `sendPlayerLine` is ~247 lines against an 80-line cap. A per-function
  ratchet is a second, different mechanism and would mean baselining 73
  functions in a seal ticket. Named deferral, reactivates with TICKET-0069,
  which deletes the functions rather than baselining them.
- **The rename, the doctrine, the AD supplement.** Brief -c.
- **Any edit to the legacy document itself.** Not one byte. The ratchet
  reads it; nothing writes it.
- **`stylesheet_partition.py` rule7 (legacy).** Its retirement condition
  (`LEGACY_MOUNTS` empty) is deliberately unmet. Leave it and its alarm
  alone.
- **Backend, schema, canon-write.** Untouched.

---

## Invariants to defend

- **The registry may only SHRINK.** This brief changes a field's value, never
  the key set. `play` stays; nothing is added.
- **`legacy_calls.baseline` may only lose records**, and `_load_baseline`
  fails on an empty file. This brief edits one record's ticket id and
  removes nothing.
- **One implementation per rule.** If rule 8 cannot share rule 3b's helper,
  it does not get its own copy.
- **Fail-closed and vacuous-proof.** Every new clause fails on absent input.
  Rule 3b that cannot find a ticket must fail, never skip.
- **History is sacred.** `registry.js`'s stale sentence is corrected by an
  appended paragraph. Docstring amendments are appended.
- **PART C rule 2 — frontend-only.** `frontend/src/legacy/registry.js`, two
  baselines, two checks. Nothing under `src/world_engine/`.

---

## Done means

- [ ] `frontend/src/legacy/registry.js` reads `retiredBy: 'TICKET-0069'` and
      carries the appended correction paragraph verbatim.
- [ ] `legacy_calls.baseline` reads
      `frontend/src/App.svelte::showFn::TICKET-0069`.
- [ ] `grep -c "export function legacyCall" frontend/src/legacy/bridge.js`
      returns 1 — unchanged.
- [ ] `legacy_mount.py` exits 0, and its three red-tests are recorded and
      reverted.
- [ ] `legacy_call.py` exits 0 (rules 6 and 8 both).
- [ ] `module_budget.py` exits 0, names the legacy document with its
      committed ceiling, and its three red-tests are recorded and reverted.
- [ ] `stylesheet_partition.py` exits 0 — rule5 and rule7 (legacy) both
      still meaningful, alarm silent.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits **0**.
- [ ] Three commits on `ticket/0061`, each green on its own.
- [ ] `/review-step` and `/close-step` run.

---

## Docs to update

- Docstrings of `legacy_mount.py` and `module_budget.py` — appended, in
  place, as part of their own commits.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — **nothing here.** One
  supplement for the whole ticket, in brief -c.
- `CLAUDE.md` — nothing here. Brief -c.
