# BRIEF - Step "review component boundary check + docs"

## Context
TICKET-0041, step 3 of 3. BRIEF-0041-a and -b moved nine `region*` functions
into a generic `review*` component. Nothing yet PREVENTS the next contributor
from reaching back into `regionDraft` from a component function, which would
silently re-couple the component to region and quietly break TICKET-0042 before
it starts. This step ships the fail-closed gate and the docs. No behaviour
changes; if a single pixel of the region review moves in this brief, something
is wrong.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
- Read `tooling/verify/checks/relation_graph.py` for `_braced_function(text, name)`
  - brace-balanced extraction of a JS function from `index.html`. Reuse that
  idiom; do not invent a second one. Do NOT reuse its `_git_show` helper: a
  "byte-identical to main" criterion goes vacuous the moment this ticket merges,
  and that is exactly why it was rejected at intake.
- Read `tooling/verify/checks/json_ui_boundary.py` for the named allow-list
  idiom (rule 6 below follows it).
- Read `tooling/verify/checks/module_budget.py`'s docstring for the fail-closed
  wording to mirror: a missing input or zero rules evaluated is a FAILURE, never
  a vacuous pass.
- Read `tooling/verify/run.py`'s `machine_checks` parser: it only picks up a
  criterion whose line contains `-> verify/checks/<name>.py` with an ASCII
  arrow, inside a `### Machine` section. Confirm the arrows in
  `TICKET-0041-shared-review-tree-component.md` parse.
- Confirm the nine `review*` names actually present in `index.html` after
  BRIEF-0041-b, and the exact set of functions outside the component that
  reference a `review*` symbol. If that set is not exactly
  `regionRenderAll`, `regionReviewDescriptor`, `regionRenderFactionsPanel`,
  `_sheetEntityOptions`, STOP and report before writing the allow-list - a
  fifth caller means BRIEF-0041-a or -b drifted from its scope.
- Read `tooling/verify/checks/page_contract.py` for `_braced_block` /
  `_bracket_block` if an object-literal parse is needed.

## Scope IN

1. **`tooling/verify/checks/review_component.py`**, stdlib only, no DB, no
   subprocess, exit 0 on pass / 1 on failure, one printed line per failure.
   Docstring names TICKET-0041 and BRIEF-0041-c and states the fail-closed
   posture verbatim:

   ```
   Fail-closed: a missing index.html, a component function whose braces do not
   balance, or zero rules evaluated is a FAILURE, never a vacuous pass. This
   check is the ONLY thing standing between the review component and a silent
   re-coupling to region state; a rule that cannot fail is a rule that is not
   there.
   ```

2. **Constants at module level**, so the contract is readable without reading
   the rules:
   ```python
   GONE = ["regionCascade", "regionIsAccepted", "regionToggleAccept",
           "regionRenderNotes", "regionRenderLocationNode", "regionRenderTree",
           "regionToggleLocGraph", "regionLocGraphData", "regionLocGraphRender"]
   GENERICS = ["reviewCascade", "reviewIsAccepted", "reviewToggleAccept",
               "reviewNotes", "reviewNode", "reviewTree", "reviewOpenSheet",
               "reviewToggleGraph", "reviewGraphData", "reviewGraphRender",
               "reviewRegister", "reviewDescriptor"]
   CONSUMER_ALLOW_LIST = ["regionRenderAll", "regionReviewDescriptor",
                          "regionRenderFactionsPanel", "_sheetEntityOptions"]
   FORBIDDEN_IN_COMPONENT = ("region", "REGION_")
   ```

3. **Rule 1 - the nine are gone.** No name in `GONE` appears anywhere in
   `index.html`, in any context (definition, call, `onclick` string, comment).

4. **Rule 2 - each generic is defined exactly once.** For each name in
   `GENERICS`, `index.html` contains exactly one `function <name>(`. Zero is a
   failure (the component is absent); two is a failure (a duplicate shadows the
   other in a no-module-scope page).

5. **Rule 3 - the component is blind to region.** For each name in `GENERICS`,
   extract the brace-balanced body and fail if it contains any string in
   `FORBIDDEN_IN_COMPONENT`, case-sensitive. This is the ticket's anti-vacuity
   teeth: a rename that did not mutualise would keep `regionDraft` or
   `regionAccepted` in the body and fail here. The failure message names the
   function and the offending substring, and says explicitly that a CSS class
   name or a DOM id counts.

6. **Rule 4 - the fallback rule is a parameter, not a constant.**
   `reviewCascade` must: take exactly one parameter (parse the parenthesised
   signature, split on `,`, expect one non-empty token); contain
   `fallbackParentId` in its body; contain neither `document.` nor
   `getElementById` nor `reviewDescriptor(`. This is the criterion the whole
   ticket exists for - if it ever fails, the batch generator cannot re-attach to
   its anchor.

7. **Rule 5 - a single descriptor factory.** `function regionReviewDescriptor(`
   appears exactly once, and `reviewRegister('region'` appears exactly once.
   Both counts are exact, not minimums. When TICKET-0042 lands,
   `reviewRegister('lot'` will be a second, DIFFERENT literal - this rule stays
   green without amendment, by construction.

8. **Rule 6 - the boundary holds in the other direction.** Walk every
   `function <name>(` in `index.html`. For each function NOT in `GENERICS` and
   NOT in `CONSUMER_ALLOW_LIST`, fail if its brace-balanced body contains the
   substring `review` (case-sensitive). This is the permanent replacement for
   the rejected `_git_show` footprint criterion: it proves the blast radius is
   exactly the four sanctioned consumer functions, and keeps proving it after
   merge. Precedent: `json_ui_boundary.py`'s named allow-list.

9. **Rule 7 - fail-closed and anti-vacuous.** Fail if `index.html` is missing or
   empty; fail if `_braced_function` returns an empty string for any name in
   `GENERICS` (unbalanced braces or a name matched only in a comment); fail if
   the number of rules evaluated is zero. Explicitly print the number of rules
   evaluated on success, so a silently-shrinking check is visible in the verdict
   line.

10. **Ticket wiring.** The seven Machine-checkable criteria in
    `TICKET-0041-shared-review-tree-component.md` already route to
    `verify/checks/review_component.py` with ASCII arrows. Run
    `python tooling/verify/run.py --ticket TICKET-0041` and confirm the verdict
    JSON lands green in `tooling/verify/results/`.

11. **`CLAUDE.md`.** Append to the standing-conventions prose, in the same
    register as the existing frontend line (`:17`), keeping the file's line
    budget:

    ```
    The review tree (`review*`, index.html) is a generic accept/reject component
    driven by a registered descriptor, never by consumer globals: a consumer
    calls `reviewRegister(key, descriptor)` and every DOM-reachable entry point
    takes that key as its first argument (inline `onclick` handlers are strings
    and cannot carry a closure). `reviewCascade` is PURE and re-attaches an
    orphan to `descriptor.fallbackParentId` - region passes its draft root, the
    room batch generator will pass the creator's anchor; that fallback is never
    recomputed inside the component. No `review*` body may name `region`, and
    outside the component only `regionRenderAll`, `regionReviewDescriptor`,
    `regionRenderFactionsPanel` and `_sheetEntityOptions` may name a `review*`
    symbol - both directions enforced fail-closed by
    `tooling/verify/checks/review_component.py`. `index.html` remains a single
    file with no build step; splitting it is a doctrine change, not a refactor.
    ```

12. **`ARCHITECTURE_DECISIONS.md`** - append one section, newest at the end,
    matching the file's existing style. Title:
    `SHARED REVIEW-TREE COMPONENT - extraction (TICKET-0041, no schema change)`.
    It records, in prose: the structural justification (`regionCascade`'s
    hard-wired `rootLocal` versus the batch anchor - one parameter, not one
    behaviour, S-norme); E1 (the registry, and WHY - inline `onclick` strings
    cannot carry a closure); B1 (why the anti-vacuity teeth are purity plus a
    parameterised fallback and NOT a caller count - the second consumer is
    TICKET-0042, so a caller count could not be green at this ticket's close,
    and a gate that cannot be green is broken); the REJECTION of the
    `_git_show` byte-identical footprint criterion as vacuous after merge, and
    its replacement by the bidirectional allow-list; C1 (why splitting
    `index.html` is a doctrine amendment - `CLAUDE.md:17` plus `module_budget`
    scanning `src/**/*.py` only plus the `/vendor/{filename}` serving
    restriction plus `const NODE_R`'s TDZ - and is deferred to its own ticket);
    and the named deferral itself.

13. **Named deferral, recorded in the same section.** `D3 - index.html file
    split`. Trigger: the next ticket that needs a JS unit or golden-render test,
    since such a test cannot exist without a loadable module. Blocked on: a
    serving decision (new route or `StaticFiles` mount), an evaluation-order
    decision (`const NODE_R`), and a `CLAUDE.md:17` amendment.

## Scope OUT
- Any change to `index.html`. If this brief needs to edit `index.html` to make a
  rule pass, the rule is wrong or BRIEF-0041-a/-b drifted - STOP and report,
  do not adjust the code to fit the check.
- Any JS runtime, `package.json`, node harness, golden render snapshot or build
  step. A3 is locked: non-regression of RENDERING is a live human gate, not a
  machine gate, and the ticket says so rather than pretending otherwise.
- Any `_git_show` / git-subprocess criterion, in any rule.
- Any baseline or allow-list file under `tooling/verify/baselines/`. The
  allow-list is a module constant in the check, four names long, reviewable at a
  glance - not a transition artifact.
- Extending the check to any other part of `index.html`: the Lieux graph, the
  NPC relation graph, `CREATION_TABS`, the manifest, the commit path. Those have
  their own checks.
- `DECISIONS_INDEX.md` - mechanically generated, never hand-edited here.
- Splitting `index.html` (that IS the deferral, not the work).

## Invariants to defend
- **Fail-closed checks over advisory rules.** Zero parsed criteria is a failure.
  Mirror `module_budget.py`'s and `run.py`'s posture explicitly.
- **Vacuous-proof.** Every rule must be demonstrably falsifiable - see the Done
  means negative tests. A rule nobody can make fail is not shipped.
- **`CLAUDE.md` line budget** and its pointer-freshness contract
  (`claude_md_contract.py`): if the appended prose trips that check, shorten the
  prose, never widen the contract.
- **Append-only decision registry.** `ARCHITECTURE_DECISIONS.md` gains a
  section; no existing section is edited or reordered.
- **Named deferrals carry trigger conditions.** D3 without its trigger is not a
  deferral, it is a wish.

## Done means
- [ ] `python tooling/verify/checks/review_component.py` exits 0 and prints the number of rules evaluated.
- [ ] `python tooling/verify/run.py --ticket TICKET-0041` writes a green verdict to `tooling/verify/results/TICKET-0041.json` with all seven criteria PASS.
- [ ] Negative test, rule 3: temporarily insert `regionDraft` into `reviewTree`'s body -> the check exits 1 and names `reviewTree`. Revert.
- [ ] Negative test, rule 4: temporarily replace `fallbackParentId` in `reviewCascade` with a locally-recomputed root -> the check exits 1. Revert.
- [ ] Negative test, rule 6: temporarily add a `reviewNotes(...)` call inside `regionCommit` -> the check exits 1 and names `regionCommit`. Revert.
- [ ] Negative test, rule 7: temporarily point the check at a non-existent path -> it exits 1, it does not report green on zero rules. Revert.
- [ ] `git diff --stat` for this brief touches no file under `src/`.
- [ ] `python tooling/verify/checks/claude_md_contract.py` exits 0 after the `CLAUDE.md` edit.
- [ ] `python tooling/verify/checks/decisions_index.py` exits 0 after the `ARCHITECTURE_DECISIONS.md` append (regenerate `DECISIONS_INDEX.md` through its normal mechanism if the check requires it).
- [ ] The full verify suite still passes - no other check regressed on the CSS renames of BRIEF-0041-a, in particular `page_contract.py`, `relation_graph.py`, `event_tab.py` and `schema_0024.py`, the four checks that read `index.html`.
- [ ] Live: the ticket's full Live gate sequence is run once end to end and every line is ticked.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
`CLAUDE.md` (item 11) and `ARCHITECTURE_DECISIONS.md` (items 12-13). No schema
change, so no `world-engine-schema.md` bump and no changelog entry - and no
version-number reconciliation pass.
