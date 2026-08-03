# BRIEF — Step "spine closure + force-layout viability (mini-RECON, report-only)"

Ticket: TICKET-0058. Relies on no prior RECON; this IS the ticket's RECON.

## Context

TICKET-0058 rests on three assumptions that no static reading can settle.
C2 assumes a force simulation over the real relation graph is viable inside
the legacy frame; B2 assumes the call closure of `author*` is bounded by
eleven Creation tabs; A1 assumes a Svelte island survives the legacy
document's show/hide tab mechanism, which toggles `style.display` rather
than re-emitting markup (`index.html:4463-4508`). TICKET-0044's lesson
stands: a mini-RECON assertion about runtime behaviour must be empirically
confirmed, never stated parenthetically.

M1 is load-bearing for the whole ticket. If it is REFUTED, Bloc C is not
constructible and the ticket returns to Nia before a line of the
convergence is written.

**This brief is REPORT ONLY.** No production file is modified. Probes are
deleted before the commit; the tree is left clean apart from one result
file.

## Scope IN

1. **Create the result file**
   `tooling/recon/RECON-0058-a-spine-closure.result.md`. One section per
   measurement below, each ending with a line of the exact form
   `VERDICT: <CONFIRMED|REFUTED|N/A> - <one sentence>`.

2. **M1 - force-layout viability (LOAD-BEARING).**
   - (a) Against the pilot world, call `GET /api/relation-graph`
     (`cockpit/crud/relations.py:271`) and record `|V|` and `|E|`. Then call
     `GET /api/characters/{id}/relation-graph` (`relations.py:211`) for the
     character with the most relations and record the ego sizes too.
   - (b) Write a throwaway force-directed simulation (plain
     repulsion/attraction/centring, fixed iteration count, no library) and
     run it over the real global data inside the legacy frame document.
     Record: iterations to a visually stable layout, wall-clock milliseconds,
     and whether the result is legible (no overlapping node clusters, edges
     distinguishable).
   - (c) Record the same at 3x and 10x the observed `|V|` using synthetic
     data, to report the headroom.
   - **ESCALATE AND STOP** if the observed-size layout takes more than 2000 ms
     or is not legible. C2 is refuted; Nia re-decides Bloc C.

3. **M2 - relation-graph parity inventory.** For each of the fifteen
   `relGraph*` functions (`index.html:10478..10820`), one row:
   function name, one-line behaviour, and a classification of exactly one of
   `CARRIED` (already provided by `Graph.svelte` as it stands), `PORT`
   (must be reimplemented in the primitive or its consumer), `CHROME`
   (belongs to the container's head bar, not the graph), or `DROP`
   (proposed for deliberate abandonment - list these separately and
   prominently; Nia decides, the executor does not).

4. **M3 - cytoscape API surface actually used.** Every cytoscape call,
   option and event handler reached from `relGraphRenderCanvas`
   (`index.html:10569`) and its callees. This is the reimplementation bill
   of materials for brief -c.

5. **M4 - the `author*` call closure (confirms or corrects B2).**
   - (a) Every non-`author*` top-level function in `index.html` that calls
     any `author*` function, with its line.
   - (b) Every non-`author*` function those callers in turn require, to
     fixed point, stopping at functions that call no `author*` code.
   - (c) The resulting set of `CREATION_TABS` keys the closure touches.
     Compare against this ticket's assumed eleven (`npc`, `pj`, `lieux`,
     `factions`, `objets`, `artefacts`, `intrigues`, `evenements`, `region`,
     `queue`, `constructeur`) and report any key added or removed.
   - (d) Report whether `competences`, `registre` or `prompts` fall inside
     the closure. If any does, say so plainly - it changes the 0058/0059
     boundary and Nia re-decides.

6. **M5 - island survival across the legacy tab mechanism.** Build a
   throwaway Svelte component and mount it into `#creation-constructeur`
   (`index.html:1429`) from the shell, using the form
   `BRIEF-0057-a` established. Then:
   - (a) Switch to another sub-tab and back. `showCreationSubTab` sets
     `el.style.display = 'none'` and back to `''` (`index.html:4487-4497`)
     without touching innerHTML. Confirm the component is still live and
     reactive afterwards - or report that it is not.
   - (b) Trigger `refreshCreationTabs()` (`index.html:7301`) and confirm the
     island is unaffected.
   - (c) Switch worlds via `activateWorld` and report what happens to the
     island, given `_creationRunWorldSwitchResets` (`index.html:4531`).
   - Record whether brief -d must mount once and leave it, or mount and
     unmount per activation. Brief -d copies the working form.

7. **M6 - SVG census in migrating code.** `graph_primitive.py` rule 6
   forbids `<svg` anywhere under `frontend/src/` outside
   `frontend/src/graph/`. List every `<svg`, `<path`, `<circle` or inline
   SVG icon emitted by JS or markup inside `#creation-editor-area`
   (`index.html:1331`), `#creation-constructeur` (`index.html:1429`) and
   `#creation-npc-relgraph` (`index.html:1299`). Each one is either a
   graph (belongs to the primitive) or an icon that must become a
   non-SVG glyph.

8. **M7 - inline handler census inside the migrating containers.** Count
   `on{click,change,input,keydown,submit,mousedown}="..."` occurrences
   inside each of the three containers above, and separately count how many
   are emitted by JS template strings versus present in static markup.
   Brief -e..-j sizing depends on this.

9. **M8 - foreign chrome in the relation-graph container.** The head bar of
   `#creation-npc-relgraph` carries `npcAgentToggle()` and
   `linkAgentToggle()` launchers plus their panels
   (`index.html:1302-1318`). Confirm whether `npcAgent*` and `linkAgent*`
   are inside or outside the M4 closure, and report which container their
   panels render into. If they are outside the closure, brief -c must
   preserve that chrome untouched while replacing the graph beneath it -
   state explicitly whether that is possible without editing those
   functions.

10. **M9 - the empty-registry failure, confirmed by execution.** On a
    scratch copy of the tree (never the working tree), delete the single
    entry from `frontend/src/graph/registry.js` and run
    `tooling/verify/checks/graph_primitive.py`. Record the exact failure
    line. Brief -b's amendment is written against that observed output, not
    against a reading of `graph_primitive.py:151`.

## Scope OUT

- **Any fix.** A surprising finding is a result. No refactor, no
  correction, no "while I was there".
- **Writing the force layout for real.** M1(b) is a throwaway probe,
  deleted before commit. The real implementation is brief -c.
- **Amending any check.** M9 measures the failure; brief -b amends.
- **Touching `frontend/src/`, `index.html`, or any check file** in a form
  that survives the commit.
- **Deciding anything.** Every `DROP` proposed in M2, and any closure
  correction in M4, is reported for Nia's decision. The executor does not
  resolve them.

## Invariants to defend

- RECON is report-only (CLAUDE.md). The only committed artefact is the
  result file.
- "Model extracts, code judges" applies to the executor here too: M2's
  classification is an extraction, not a verdict on what may be dropped.

## Done means

- [ ] `tooling/recon/RECON-0058-a-spine-closure.result.md` exists, with nine
      sections M1..M9, each ending in a `VERDICT:` line of the exact form.
- [ ] M1 reports `|V|`, `|E|`, milliseconds and legibility at observed, 3x
      and 10x size.
- [ ] M2 classifies all fifteen `relGraph*` functions, with `DROP`
      candidates listed separately.
- [ ] M4 reports the closure's `CREATION_TABS` key set and names any
      difference from the assumed eleven.
- [ ] M5 states, in one sentence, whether brief -d mounts once or per
      activation.
- [ ] M9 quotes the observed failure line verbatim.
- [ ] `git status` on the ticket branch shows exactly one added file.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None. This step IS a document.
