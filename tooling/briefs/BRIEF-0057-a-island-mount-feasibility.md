# BRIEF — Step "island mount feasibility (mini-RECON, report-only)"

## Context

TICKET-0057 rests on one unverified assumption: that a Svelte 5 component
mounted from the SHELL window into the LEGACY iframe's document behaves
correctly - events fire, drag works, attribute-styled SVG resolves against
the legacy CSS variables. TICKET-0044's lesson stands: a mini-RECON
assertion about runtime/driver behaviour must be empirically confirmed, not
stated parenthetically. If M2 below fails every tested listener host, A1 is
not constructible and the ticket needs re-decision before any code is
written.

Four secondary measurements (M4..M7) settle facts that later briefs would
otherwise guess at.

**This brief is REPORT ONLY.** No production file is modified. Scratch
copies live outside the working tree; the tree is left clean apart from one
result file.

## Scope IN

1. **Create the result file** `tooling/recon/RECON-0057-a-island-mount.result.md`.
   It carries one section per measurement below, each ending with a line of
   the exact form `VERDICT: <CONFIRMED|REFUTED|N/A> - <one sentence>`.

2. **Build a throwaway probe.** On the ticket branch, a scratch Svelte
   component and a scratch mount call, driven by `npm run dev` or a
   temporary build. It mounts into the live legacy document via
   `frameEl.contentDocument.getElementById('creation-lieux-graph')`.
   The probe is DELETED before this brief's commit; only the result file is
   committed. Do not add it to `frontend/src/` in a form that survives.

3. **M1 - event delivery across the frame boundary.** Svelte 5 delegates
   many DOM events at a root node. Mount a component containing a
   `<button onclick={...}>` into the legacy document and click it. Report:
   does the handler fire? If it does not, report what Svelte attached the
   listener to and whether passing an explicit delegation root, or using
   `on:` with a manual `addEventListener`, fixes it. Record the exact
   working form - brief -b will copy it.

4. **M2 - drag listeners (LOAD-BEARING).** The legacy code registers
   `mousemove`/`mouseup` on `window` (`index.html:10525-10526`,
   `10541-10542`). A shell-mounted component's `window` is the SHELL's, not
   the frame's. Measure three hosts, in this order, and report each
   separately:
   - (a) `window` (the shell's) - expected: does NOT fire for a drag
     happening inside the iframe.
   - (b) `node.ownerDocument.defaultView` where `node` is the mounted
     target - expected: fires. **This is the form brief -b specifies.**
   - (c) `node.ownerDocument` - report for completeness.
   Perform a real press-move-release inside the frame for each.
   **ESCALATE AND STOP** if none of (b) or (c) delivers a complete
   press-move-release sequence: A1 is refuted and the ticket returns to
   Nia for a re-decision on Bloc A.

5. **M3 - styling.** Two sub-measurements:
   - (a) Render an SVG element with `fill="var(--card)"` and
     `stroke="var(--border)"` as ATTRIBUTES inside the frame. Confirm the
     variables resolve against the legacy document's stylesheet
     (`index.html:6..1045`) and the shapes are visible.
   - (b) Add a Svelte scoped `<style>` block to the probe component.
     Confirm where the generated CSS lands (shell `<head>` vs frame
     `<head>`) and therefore whether it applies inside the frame.
   Report both. Brief -b forbids `<style>` blocks in the primitive on the
   strength of (b); if (b) unexpectedly shows the CSS reaching the frame,
   say so - the rule stays anyway (see -b Scope IN 2), but Nia should know
   the rule is belt-and-braces rather than load-bearing.
   - (c) Confirm the legacy classes `lieux-graph-head` (`index.html:991`)
     and `btn-icon` apply to markup emitted by the mounted component.

6. **M4 - `page_contract.py` vs a nested slot object.** `_slot_objects` /
   `_slot_by_container` (`page_contract.py:58-60`) parse the `slots: [`
   literal. In a scratch COPY of `index.html`, add a nested
   `graph: { consumer: 'lieux' }` inside `CREATION_TABS.lieux.slots[0]`
   (`index.html:4313`). Run `page_contract.py` against the scratch copy.
   Report: pass or fail, and if fail, the exact line and regex that broke.
   Brief -b's Scope IN 7 branches on this verdict.

7. **M5 - `review_component.py` vs the deletion of `reviewGraphRender`.**
   In a scratch COPY, delete `function reviewGraphRender(...)` and its two
   call sites (`index.html:6699`, `7158`). Run `review_component.py`.
   Report every failing rule by number and message. Expected: rule 2
   (`defined 0 time(s), expected exactly 1`). Report whether rule 6 also
   fires. Brief -c's amendment is written against this output.

8. **M6 - build/verify sequence for new frontend sources.** Add a scratch
   file under `frontend/src/`, run `npm run build`, then
   `frontend_build_fresh.py`. Report the exact command sequence that leaves
   the check green, and confirm whether `app.py`'s
   `_check_frontend_build_on_startup` (`app.py:208-220`) is satisfied by it.
   Remove the scratch file and restore the build.

9. **M7 - dead-symbol confirmation.** For each of `GRAPH_W`, `GRAPH_H`,
   `NODE_R`, `DRAG_THRESHOLD`, `graphData`, `graphSelectedNodeId`,
   `_graphDrag`, `_graphPlaced`, list every occurrence in `index.html` with
   its line number, and state whether it falls inside one of the 13
   functions this ticket deletes. This session's RECON found zero
   occurrences outside them; confirm or contradict. Any occurrence OUTSIDE
   the 13 is a finding that changes brief -b's deletion list -> REPORT, do
   not act.

10. **M8 - container survival across a review re-render.** `regionRenderAll`
    and `batchRenderAll` re-emit their panel markup, including the graph
    container (`index.html:6681-6684`, `7140-7143`). Measure whether the
    container DOM node identity survives a re-render or is replaced.
    Report the answer. Brief -c's re-mount strategy depends on it.

## Scope OUT

- No production file is modified. Not `index.html`, not `bridge.js`, not
  `app.py`, not any check. Scratch copies only, outside the tree or
  reverted.
- No `Graph.svelte`, no `frontend/src/graph/` directory. That is brief -b.
- No fix applied to any check found failing. M4/M5 are measurements; their
  fixes belong to -b and -c respectively.
- No investigation of the cytoscape/relation graph. It is not converged by
  this ticket (TICKET-0058) and its runtime behaviour is not in question.
- No performance measurement, no bundle-size measurement.
- Do not "improve" the probe into something reusable. It is deleted.

## Invariants to defend

- **RECON is report-only.** No action is taken during a RECON phase. A
  finding that looks like an easy fix is still a finding.
- **`file:line` citations required** on every reported finding.
- **Empirical over parenthetical.** No verdict line may be written from
  reasoning about how Svelte or the DOM "should" behave. Every VERDICT
  must be backed by an observation actually made in a running browser or a
  really-executed check. If a measurement could not be performed, the
  verdict is `N/A` with the reason - never a guess dressed as a result.
- **Working tree left clean.** `git status` shows the result file and
  nothing else.

## Done means

- [ ] `tooling/recon/RECON-0057-a-island-mount.result.md` exists.
- [ ] It contains exactly eight `VERDICT:` lines, one per M1..M8, each in
      the specified form.
- [ ] M2's section reports all three listener hosts (a), (b), (c)
      separately, each with the observed press-move-release outcome.
- [ ] M3's section states, explicitly, where Svelte's scoped CSS landed.
- [ ] M4's section states pass/fail and, on fail, the breaking regex with
      its `page_contract.py` line number.
- [ ] M5's section lists every failing rule of `review_component.py` by
      number.
- [ ] M6's section gives a command sequence that a reader can copy.
- [ ] M7's section is a table of symbol -> line numbers -> inside/outside
      the 13 functions.
- [ ] M8's section states whether the container node identity survives.
- [ ] `git status` clean apart from the result file; the probe is gone;
      `npm run build` output matches the committed one
      (`frontend_build_fresh.py` green).
- [ ] If M2 escalated: the result file's M2 section ends with
      `ESCALATION: A1 refuted` and NO further brief is executed.

## Docs to update

None. This brief IS a report; its output is consumed by briefs -b, -c and
-d, and its findings are folded into ARCHITECTURE_DECISIONS by brief -e.
