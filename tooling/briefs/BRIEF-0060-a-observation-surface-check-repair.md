# BRIEF — Step "repair observation_surface.py on the current tree"

## Context

`tooling/verify/checks/observation_surface.py` is RED on `main` and has been
since TICKET-0059 merged. Two of its rules encode a three-view cockpit that no
longer exists: TICKET-0059 (BRIEF-0059-l commit 4) took Creation out of the
legacy document, so `showObservationView` toggles two views instead of three,
and the `CREATION_TABS` registry moved to `frontend/src/creation/tabs.js`.

Nothing caught it because `tooling/verify/run.py` executes only the checks a
ticket's `### Machine-checkable` section names, and TICKET-0059's section does
not name this one. The corpus-wide gate that would have caught it is
BRIEF-0060-d; this brief does not build it.

Decision **A1**: repair the check against **today's** tree, in its own brief,
with zero product-code change, before the migration touches anything. The
migration (BRIEF-0060-b) re-homes the same check onto the Svelte surface. Two
moves, two separate proofs — so that the TICKET-0059 regression is understood
and demonstrated green before it is overwritten by a rewrite.

## Mini-RECON — verify before writing

Report `file:line` for each. **If any anchor does not resolve as described,
STOP and escalate — do not adapt.**

1. `tooling/verify/checks/observation_surface.py` — confirm the current
   failure set by running it with `WORLD_ENGINE_ENV=dev PYTHONPATH=src`.
   Expected three genuine failures (Rule 1 ×2, Rule 2) plus, in a container
   without `sqlalchemy`, a Rule 5 subprocess failure. **In the dev
   environment Rule 5 must be re-measured: if `json_ui_boundary.py` fails for
   a reason other than a missing dependency, that is a separate finding —
   REPORT ONLY, do not fix it here.**
2. `src/world_engine/cockpit/index.html` — confirm `showObservationView()` is
   defined once, near line 1808, and that its body names exactly
   `play-view`, `observation-view`, `mode-tab-play`, `mode-tab-observation`
   and no `creation-*` token.
3. `src/world_engine/cockpit/index.html` — confirm there is **no**
   `CREATION_TABS` literal anywhere in the file.
4. `frontend/src/creation/tabs.js` — confirm `export const CREATION_TABS = {`
   is declared exactly once (expected near line 178) and that it is an object
   literal whose top-level keys are the tab slugs.
5. `tooling/verify/checks/page_contract.py` — confirm `TAB_KEYS` is still a
   list literal (expected near line 31) with fourteen entries and no
   `observation` member. Rule 2's first half reads this file and must keep
   doing so unchanged.
6. Count the functions the vacuous-proof guard collects today:
   `showObservationView`, `_obsRenderTranscript`, `_obsRenderRunDetail`,
   `observationRunBeats`. Confirm the guard's threshold is 4 and that four
   are in fact reachable.

## Scope IN

One commit. Only `tooling/verify/checks/observation_surface.py` changes.

### 1. Rule 1 — narrow the mode-tab contract to two views

In `check_rule1_mode_tab`, the token loop currently asserts six needles. Drop
the two Creation tokens. The loop becomes exactly:

```python
    for needle in (
        "play-view", "observation-view",
        "mode-tab-play", "mode-tab-observation",
    ):
```

Leave the `id="mode-tab-observation"` and `onclick="showObservationView()"`
assertions, the `_braced_block` lookup, and the `_renderer_functions_found`
increment untouched.

Add this comment immediately above the loop, verbatim:

```python
    # TICKET-0060 (BRIEF-0060-a). Two views, not three. TICKET-0059
    # (BRIEF-0059-l commit 4) made Creation shell-native, so the legacy
    # document owns Play and Observation only and showObservationView has
    # no creation-view / mode-tab-creation to toggle. This rule asserted
    # the pre-0059 contract and had been RED on main ever since --
    # undetected because verify/run.py executes only the checks a ticket's
    # Machine-checkable section names, and TICKET-0059's section does not
    # name this one. BRIEF-0060-d builds the corpus gate that closes that
    # class of gap; BRIEF-0060-b re-homes this rule onto the Svelte
    # surface once Observation leaves this document entirely.
```

### 2. Rule 2 — read `CREATION_TABS` from its real home

In `check_rule2_no_creation_leak`:

- Leave the first half (the `TAB_KEYS` read from `page_contract.py`) exactly
  as it is, including its failure message.
- Replace the second half. It must read
  `frontend/src/creation/tabs.js` instead of the `html` argument, resolve the
  registry with the module's existing `_braced_block` helper against the
  pattern `r"export const CREATION_TABS\s*=\s*\{"`, and fail closed when the
  literal is not found.

Add a module-level constant beside the existing path constants:

```python
CREATION_TABS_FILE = ROOT / "frontend" / "src" / "creation" / "tabs.js"
```

Failure messages, verbatim:

```
"Rule 2: CREATION_TABS registry literal not found in frontend/src/creation/tabs.js"
"Rule 2: CREATION_TABS has an 'observation' entry — the surface leaked into the Creation registry"
```

Keep the existing entry regex (`(?:^|[{,\s])observation\s*:\s*\{`) unchanged —
the registry's shape did not change, only its file.

Add this comment above the second half, verbatim:

```python
    # TICKET-0060 (BRIEF-0060-a). CREATION_TABS moved to
    # frontend/src/creation/tabs.js (TICKET-0058/0059). Reading it from
    # index.html made this rule vacuously unsatisfiable, not vacuously
    # satisfied -- it FAILED rather than passing, which is the correct
    # direction but the wrong anchor. The assertion is unchanged: the
    # Observation surface must never appear as a Creation sub-surface.
```

### 3. `html` parameter hygiene

If narrowing Rule 2 leaves `html` unused inside
`check_rule2_no_creation_leak`, keep the parameter in the signature and keep
`main()`'s call site unchanged. Do **not** refactor the call chain — every
other rule takes the same argument, and a signature divergence here would be a
gratuitous diff in a brief whose whole point is a minimal, provable repair.

### 4. Red-test both repairs

Each repaired rule must be shown to still catch the thing it exists to catch.
Perform each test, capture the transcript, then **revert the mutation** — no
mutation is committed.

- **Rule 1.** Temporarily delete the `mode-tab-observation` line from
  `showObservationView()`'s body in `index.html`. Run the check. It must FAIL
  with `Rule 1: showObservationView() does not reference 'mode-tab-observation'`.
  Revert.
- **Rule 2, missing-literal branch.** Temporarily rename
  `export const CREATION_TABS` to `export const CREATION_TABS_X` in
  `tabs.js`. Run the check. It must FAIL with the not-found message. Revert.
- **Rule 2, leak branch.** Temporarily insert `observation: {` as a top-level
  key inside the `CREATION_TABS` literal. Run the check. It must FAIL with
  the leak message. Revert.

Paste all three transcripts into the execution report. A repair without a red
test is a green check with no evidence it can ever be red.

### 5. Confirm the vacuous-proof guard is intact

After the repair, running the check must still print a PASS line naming
**4 renderer function(s)** and **4 outcome literal(s)**. If either count
drops, the repair removed an assertion rather than re-anchoring it — STOP and
escalate.

## Scope OUT

Named explicitly because each is a live temptation in this file:

1. **Do not touch `showObservationView`, `showPlayView`, or any other line of
   `src/world_engine/cockpit/index.html`.** Except for the temporary,
   reverted red-test mutations of item 4, this brief changes no product code.
   The two-view contract is correct as it stands; the check was wrong.
2. **Do not re-home the check onto the Svelte surface.** That is
   BRIEF-0060-b. Rule 1 must still assert the legacy `showObservationView`
   after this brief.
3. **Do not build the corpus gate**, do not add a "this check is linked by a
   ticket" assertion, do not edit `tooling/verify/run.py`. That is
   BRIEF-0060-d.
4. **Do not extend `stylesheet_partition.py`.** The rule7 `APPLIED`-domain
   extension is BRIEF-0060-c.
5. **Do not fix the `.r-warn` / `.r-err` stranding.** It cannot be fixed
   in isolation: re-adding the `creation.css` link to `cockpit/index.html`
   would fail `stylesheet_partition.py` rule5 (the link's lifetime is tied to
   `LEGACY_MOUNTS.creation`, which is retired), and copying the two rules
   into the inline block would fail rule2 (duplicate selectors). The migration
   is the fix, under decision D1, in BRIEF-0060-b.
6. **Do not fix the stale `WORLD_ID`.** Decision F1 fixes it via the
   migration; decision F3 defers the server-side hardening to a named ticket
   after TICKET-0061.
7. **Do not fix anything `json_ui_boundary.py` reports.** Rule 5 invokes it
   as a subprocess; if it fails in the dev environment for a real reason,
   that is a REPORT ONLY finding for a separate ticket.
8. **Do not audit the other checks for the same drift.** Fifteen other checks
   reference `cockpit/index.html`; all fifteen passed when RECON-0060-a ran
   them. If one is red in the dev environment, REPORT ONLY.
9. **Do not add rules.** Not a `LEGACY_MOUNTS`-consistency rule, not a
   two-view `showPlayView` rule, not an eighth rule of any kind. This brief
   repairs anchors; it adds no assertions.

## Invariants to defend

- **Fail-closed over advisory.** Every repaired branch must FAIL on a missing
  input, never pass vacuously. Rule 2's new file read fails closed when the
  literal is absent — that is why item 4's second red test exists.
- **Vacuous-proof guards.** The `_renderer_functions_found < 4 or
  len(_outcome_literals_found) < 4` guard at the tail of `main()` is the
  module's floor. It must survive unchanged, and item 5 proves it still
  reports 4/4.
- **Structural over disciplinary.** The repair re-anchors an assertion; it
  does not soften one. If a rule cannot be re-anchored without weakening what
  it proves, that is an escalation, not a judgement call.
- **The check is a guard, not documentation.** A repair that makes the check
  green by asserting less is worse than leaving it red.

CLAUDE.md invariants at risk: none directly — this brief touches no engine
code, no canon-write path, no schema, and no product surface.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/observation_surface.py`
      exits 0 on a tree whose `src/` and `frontend/` are byte-identical to
      `main` before this brief.
- [ ] Its PASS line names **4 renderer function(s)** and **4 outcome
      literal(s)**.
- [ ] `git diff --stat` for the commit lists exactly one file:
      `tooling/verify/checks/observation_surface.py`.
- [ ] The execution report contains three red-test transcripts (Rule 1
      missing token; Rule 2 missing literal; Rule 2 observation leak), each
      showing the exact expected failure message, and confirms every mutation
      was reverted.
- [ ] `git status` is clean apart from the single committed file — no
      leftover red-test mutation in the tree.
- [ ] Rule 5's behaviour in the dev environment is stated in the report:
      passing, or failing with the reason, recorded as REPORT ONLY.
- [ ] The fifteen other `index.html`-anchored checks are not run as part of
      this brief's gate and are not modified.

## Docs to update

None. No schema change, no `ARCHITECTURE_DECISIONS.md` section, no CLAUDE.md
line.

The decision record for this repair — why the guard lapsed, and the
per-ticket-gate versus corpus-gate distinction it exposes — is written once,
by BRIEF-0060-d, alongside the gate that closes the gap. Writing it twice
would put the same rationale in two places, and this brief is the symptom,
not the cause.
