# BRIEF — Step "legacyCall seal" (v2)

Ticket: TICKET-0059. Requires BRIEF-0059-a landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendments 2 and 6**. Cites RECON-0059-a
**M1**, **M7**, **M8**.

**This brief supersedes the v1 issue of BRIEF-0059-b, which scoped the census
to the literal string `legacyCall(` and would have been fail-open against the
bypass class M1 found. Do not execute the v1 text.**

## Context

TICKET-0058 converged five Creation surfaces onto Svelte islands, but several
of those components still reach back into the legacy window. RECON-0059-a M1
counted 20 sites spelling `legacyCall(` — and then found that the string is
the wrong thing to count.

The actual primitive is the private, unexported `callLegacy(fnName, ...args)`
at `frontend/src/legacy/bridge.js:24`. `legacyCall` (`bridge.js:153`) is one
thin passthrough over it; eight further named exports reach the identical
legacy window through the identical primitive without ever spelling the
string. A grep-for-`legacyCall(` guard would be blind to all of them, and to
any new site added the same way.

That is the whole risk this brief exists to close, and closing it against the
wrong token would have produced a green check over a live bypass — worse than
no check, because it would have been believed.

This guard lands before any migration brief, so that briefs `-c` through `-l`
must each prove a decrement rather than promise one. A ban written at `-m`
would protect exactly the ten briefs during which the risk exists, and none of
the ones after.

## Scope IN

### Commit 1 — the seal

1. **Census the bridge's reaching surface.** Read
   `frontend/src/legacy/bridge.js` and enumerate every **export** whose body
   reaches `callLegacy` (directly or transitively). M1 reports nine:
   `legacyCall`, `showSurface`, `activateWorldViaLegacy`, `openWorldCreate`,
   `openWorldDelete`, `showCreationTab`, `getSelectedCharacterId`,
   `selectEntity`, `selectRecord`. Confirm that list against the file rather
   than trusting it — a tenth export added since M1 must appear.

   Then find every **call site** of those exports across `frontend/src/`,
   excluding `bridge.js` itself. For `legacyCall`, the legacy target is its
   first argument's string literal; for the other eight, the legacy target is
   whatever their body passes to `callLegacy` (a constant per export, except
   `showSurface`, whose target is `entry.showFn` from `LEGACY_MOUNTS` —
   record it as the literal token `showFn` rather than expanding it).

   Expected order of magnitude: 28-32 records. M1 named callers for only
   three of the eight wrappers, so the rest is this brief's own measurement.
   A materially different total is REPORTED in the commit message; it is not
   a stop.

   **`legacyContainer` and `legacyDocument` are OUT of scope** and must not
   enter the baseline. They hand out a DOM node rather than calling a legacy
   function; that coupling is already governed by `creation_island.py` and
   `legacy_mount.py`, and duplicating it here would conflate two distinct
   seams.

2. **Create `tooling/verify/baselines/legacy_calls.baseline`**, sorted,
   newline-terminated, one record per call site:

   ```
   <path-relative-to-repo-root>::<legacy function name>::<TICKET-NNNN>
   ```

   Example:

   ```
   frontend/src/creation/Sheet.svelte::authorRenderRelations::TICKET-0059
   ```

   One record per **site**, never deduplicated by name: a file calling the
   same legacy function twice contributes two identical-but-for-nothing
   records, and the file's count is its record count. No line numbers —
   they churn on every edit and would make the baseline a merge-conflict
   generator.

3. **Assign `retiredBy` per Amendment 2.** A record is `TICKET-0059` when its
   legacy target is Creation-side: the `author*` families, the `creation*`
   chrome helpers, `worldCreateOpen` / `worldDeleteOpen`,
   `showCreationSubTab`, `genericModalOpen` / `genericModalClose`. It is
   `TICKET-0061` only where the target is demonstrably read by the still-
   legacy Play surface — `showFn` (via `showSurface`) and `activateWorld`.

   **Ambiguous cases take `TICKET-0059`.** That is the fail-closed direction:
   a record wrongly marked 0059 blocks `-l` and produces a visible
   escalation; a record wrongly marked 0061 survives the ticket silently,
   which is the exact failure this seal exists to prevent. Justify every
   non-0059 assignment in the commit message, by name.

4. **Create `tooling/verify/checks/legacy_call.py`**, following the
   `legacy_mount.py` idiom M7 reports: module-level `FAILURES: list[str]`, a
   `fail()` appender, `_report_and_exit(counts)`, `ROOT` via `parents[3]`.

   Rules, each named in its own failure message:

   - **rule1 (scan is real).** Collect every `.svelte` and `.js` file under
     `frontend/src/`. Zero files collected -> FAIL, "vacuous scan". If
     `frontend/src/legacy/bridge.js` is absent from the collection -> FAIL.
   - **rule2 (the reaching surface is derived, not hardcoded).** Parse
     `bridge.js` and derive the set of exports that reach `callLegacy`. If
     that set is empty -> FAIL. **Do not hardcode the nine names** in the
     check: a tenth wrapper added later must be picked up automatically, or
     the check reproduces the exact blindness it was written to fix.
   - **rule3 (census).** For every collected file except `bridge.js`, find
     every call site of any name in rule2's set, skipping `//` line comments
     and `/* */` block comments. A `legacyCall(` whose first argument is not
     a plain string literal is itself a FAIL — a computed legacy function
     name defeats the census.
   - **rule4 (subset).** Every observed site must have a matching baseline
     record. An observed site with no record FAILS:
     `rule4: new bridge-reach site <path>::<fn> — the seam may only shrink`.
   - **rule5 (monotone shrink).** The observed multiset must be a
     sub-multiset of the baseline multiset. A baseline record with no
     observed site is NOT a failure — a brief closed it — but is printed as
     `stale: <record>` so the closing commit is reminded to prune.
   - **rule6 (primitive confinement).** `callLegacy` is defined exactly once
     in the tree, in `bridge.js`, and is NOT exported. `legacyCall` is
     defined exactly once and IS exported. A second definition of either, or
     an exported `callLegacy`, FAILS.
   - **rule7 (terminal ordering).** If any record bearing `TICKET-0059`
     remains in the baseline AND `frontend/src/legacy/registry.js`'s
     `LEGACY_MOUNTS` no longer declares `creation`, FAIL:
     `rule7: creation mount retired with <n> TICKET-0059 bridge-reach
     site(s) still open`. The converse — an empty 0059 set while `creation`
     is still declared — is the expected state entering `-l` and is not a
     failure.
   - **rule8 (ticket vocabulary).** Every `retiredBy` value matches
     `^TICKET-\d{4}$`. An unparseable third field FAILS rather than being
     skipped.

5. **Register the check in `tooling/verify/run.py`** the way every other
   check is registered, so it runs in the standard sweep and `run.py` stays
   fail-closed.

6. **Header comment, verbatim, on both the check and the baseline:**

   > TICKET-0059 (BRIEF-0059-b). The bridge-reach seam: an enumerated,
   > MONOTONICALLY SHRINKING list of the sites where a Svelte module still
   > reaches into the legacy window through callLegacy -- by ANY of
   > bridge.js's exports, not only legacyCall. RECON-0059-a M1 found that
   > counting the string `legacyCall(` misses eight narrow-named wrappers
   > over the same primitive; rule2 therefore derives the reaching surface
   > from bridge.js rather than hardcoding it. The set may only lose
   > records. Every record bearing TICKET-0059 must be gone before
   > `creation` may leave LEGACY_MOUNTS -- rule7 enforces that ordering
   > structurally, not by brief sequencing.

7. **Prune protocol, in the check's module docstring:** the brief that closes
   a site deletes its baseline record in the same commit. Closing without
   pruning leaves a `stale:` line; pruning without closing FAILS rule4 on the
   next run. Neither direction drifts silently.

### Commit 2 — the frontend module budget (Amendment 6)

8. **Extend `module_budget.py`** with a line-count rule over
   `frontend/src/**/*.svelte` and `frontend/src/**/*.js`, using the same
   1000-line ceiling (R5) the Python path enforces. The existing AST-based
   Python analysis is untouched; this is an additional, separate rule with
   its own name in the failure output.

   Vacuous-proof: if the frontend glob collects zero files, that is a
   failure, not a pass — the same guard rule1 applies to `legacy_call.py`.

   M8's measurements at this commit: largest frontend files are
   `Sheet.svelte` (656), `Region.svelte` (650), `RoomBatch.svelte` (447),
   `EntityList.svelte` (353). Nothing breaches today; `-c` and `-d` are the
   first briefs that could.

9. **No exemption mechanism.** Do not add a per-file override, an
   `// budget-ok` annotation, or a grandfathering list. There is nothing to
   grandfather — every file passes today.

## Scope OUT

- **Closing a single call site.** Not one. This brief adds guards and changes
  no behaviour. `Sheet.svelte`, `Region.svelte`, `RoomBatch.svelte`,
  `FactionRoster.svelte`, `locationType.js`, `EntityList.svelte`,
  `graph/consumers/relations.js`, `App.svelte` and `Header.svelte` are all
  byte-untouched.
- **Deleting any function from `index.html`.** Briefs `-c` onward.
- **Refactoring `bridge.js`** — including the obvious "the eight wrappers
  could just be `legacyCall` calls at their call sites". They could; that is
  a migration decision belonging to the briefs that close them, and doing it
  here would rewrite the very files this brief is measuring.
- **Touching `legacy_mount.py`, `LEGACY_MOUNTS`, or
  `legacy_mounts.baseline`.** Rule7 READS the registry; it never writes it.
  The `creation` entry leaves at `-l`.
- **Re-homing any check.** Each re-homing lands with its surface.
- **Extending the seal to Play or Observation surfaces.** The `retiredBy`
  column records their ownership; their closure is TICKET-0060/0061's work.
  A guard written for them now is structure without a reader (E2).
- **Any `// legacy-call-ok` escape hatch.** An override in the same commit as
  the guard defeats the guard.
- **Splitting `module_budget.py` into two checks.** One check, two rules.
- **Any backend change.** Frontend and tooling only.

## Invariants to defend

- **Structural over disciplinary.** The ordering "close the seam before
  retiring the mount" becomes rule7, not a sequencing convention a future
  session could forget. The frontend line budget becomes a rule, not a
  reminder in two briefs.
- **Fail-closed and vacuous-proof.** rule1 and the module-budget glob guard
  both exist so that an empty scan reports failure rather than green. A green
  `legacy_call.py` over zero files would be the failure mode this project
  treats as worse than no check at all.
- **Derived, not hardcoded.** rule2 is the whole lesson of M1: a guard that
  hardcodes today's nine export names reproduces the blindness it replaces
  the moment a tenth appears.
- **No structure without a reader (E2).** The baseline's reader is the check
  in this same brief; its consumers are every later brief in the chain.
- **Frontend-only scope.** Nothing under `src/world_engine/` is touched.

## Done means

- [ ] `tooling/verify/baselines/legacy_calls.baseline` exists, sorted, every
      record carrying a `TICKET-NNNN` third field; total reported in the
      commit message alongside M1's 20 for comparison.
- [ ] Every record NOT marked `TICKET-0059` is justified by name in the
      commit message.
- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 on the unmodified
      tree.
- [ ] Scratch A: add `legacyCall('authorDelete')` to a component under
      `frontend/src/creation/`; exits non-zero naming rule4; revert.
- [ ] Scratch B: add a call to `selectEntity(...)` in a file that has none;
      exits non-zero naming rule4 — **this is the case v1 of this brief would
      have missed**; revert.
- [ ] Scratch C: add a tenth export to `bridge.js` wrapping `callLegacy`, and
      call it from a component; exits non-zero naming rule4, proving rule2
      derived rather than hardcoded; revert.
- [ ] Scratch D: delete one baseline record; exits non-zero naming rule4;
      restore.
- [ ] Scratch E: point the scan root at an empty temp directory; exits
      non-zero naming rule1, never 0; restore.
- [ ] Scratch F: remove `creation` from `LEGACY_MOUNTS` while 0059 records
      remain; exits non-zero naming rule7; restore.
- [ ] Scratch G: change a site to `legacyCall(someVariable)`; exits non-zero
      naming rule3; revert.
- [ ] Scratch H: `export function callLegacy`; exits non-zero naming rule6;
      revert.
- [ ] Scratch I: pad any file under `frontend/src/` past 1000 lines;
      `module_budget.py` exits non-zero naming the frontend rule; revert.
- [ ] Scratch J: point the module-budget frontend glob at an empty directory;
      exits non-zero, never 0; restore.
- [ ] `python tooling/verify/run.py` includes `legacy_call` and exits 0.
- [ ] `git diff --stat` shows only: the new check, the new baseline, the
      harness registration, and `module_budget.py`. No file under
      `frontend/src/` or `src/world_engine/` is modified.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. `CLAUDE.md`'s check inventory and `ARCHITECTURE_DECISIONS.md`'s entry
for the seam are written at `-m`, once the seam is actually closed. Recording
a guard as doctrine while its baseline still carries open records would put a
half-truth in the law file.
