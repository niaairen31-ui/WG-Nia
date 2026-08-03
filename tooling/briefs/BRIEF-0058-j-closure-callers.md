# BRIEF — Step "closing the call closure: Evenements, Region, roster, backfill"

Ticket: TICKET-0058. Relies on RECON-0058-a M4. Requires BRIEF-0058-h and
BRIEF-0058-i landed.

## Context

Bloc B2 defined this ticket's scope as the call closure of `author*` rather
than the label "spine". This is the brief that closes it. Its members were
measured on `main`: `evenementsRenderCreatePanel` (`index.html:5306`),
`evenementsSave` (`5274`), `evenementsSubmitCreate`, `regionCommit` (`6687`),
`batchCommit` (`7061`), `npcGoalsBackfillAll` (`10111`) and
`_factionRosterRowHtml` (`8915`, moved in brief -g). RECON-0058-a M4 either
confirmed that set or corrected it; execute against the RECON, not against
this paragraph.

When this brief lands, no legacy function calls migrated code, and the
reverse-direction CustomEvent bridges introduced in briefs -d, -e and -f can
be removed. That removal is the observable proof that the closure is closed.

## Scope IN

1. **Evenements.** Port the create panel, save and submit paths. The tab
   stays `archetype: 'entity'` with `containers: ['creation-editor-area']` -
   `page_contract.py` asserts both, and `event_tab.py` guards the surface.
   Re-home `event_tab.py` in this commit.

2. **Region.** Port `regionCommit` and the region authoring surface that
   reaches the sheet engine. Its review descriptor moves to the Svelte
   review registry (brief -i left it registering through the legacy path).
   The lieux-graph consumer is already converged (TICKET-0057) and is
   consumed, not re-implemented - this is the second confirmation that the
   0057 lock holds against a genuinely different graph.

3. **Room batch.** Port `batchCommit` and move its review descriptor.
   `#batch-graph-mount` (`index.html:7134`) keeps its `graph:slot` dispatch
   with `consumer: 'review'`; the mount id and consumer key do not change.

4. **`npcGoalsBackfillAll`.** Port it and remove the temporary bridge brief
   -e installed for it.

5. **Remove every reverse-direction bridge** installed by briefs -d, -e and
   -f, plus `reviewGraphData` from `legacy/bridge.js` (`bridge.js:117-124`)
   if brief -i left it, once no legacy descriptor remains. Each removal is
   an assertion that the closure is closed; if one cannot be removed, say
   which caller survives and why, and STOP rather than leaving an
   undocumented permanent bridge.

6. **Re-home `faction_roster_panel.py`, `faction_roster_order.py` and
   `event_tab.py`** if brief -g did not already. Zero collected is a
   failure in each.

7. **Report the residual.** List, in the commit message and in the result
   handed to Nia, every `CREATION_TABS` entry still rendering from the
   legacy document. **Correction (ticket-level, superseding this
   paragraph): the expectation is exactly FIVE — `competences`, `registre`,
   `prompts`, `artefacts` and `queue`** (both confirmed outside the `author*`
   closure and outside the container-occupancy migration surface; see
   TICKET-0058.md's intake correction and RECON-0058-a M4c), plus the link
   agent and world CRUD. Any other name is a finding: the closure was
   mis-measured and TICKET-0059's scope changes.

## Scope OUT

- **`competences`, `registre`, `prompts`, the link agent, world CRUD.**
  TICKET-0059. They keep working from the legacy document, untouched.
- **`npcAgent*` / `linkAgent*`.** TICKET-0059. Their launchers were
  preserved in brief -c and stay preserved.
- **Retiring `creation` from `frontend/src/legacy/registry.js`.**
  TICKET-0059 - the entry declares it.
- **Region generation prompts or rubric.** Untouched.
- **Any backend change.**

## Invariants to defend

- **Single canon-write authority** - region commit and batch commit are
  among the most write-heavy paths in Creation; both stay on sanctioned
  routes.
- **`proposed_mutation` is the sole gate** for anything AI-proposed in the
  region and batch flows.
- **Fail-closed guards never lapse** - three checks re-home in their own
  commits here.
- **No structure without a reader** - every bridge removed is structure whose
  reader is gone.

## Done means

- [ ] `python tooling/verify/checks/event_tab.py`,
      `faction_roster_panel.py`, `faction_roster_order.py` exit 0 at their
      new loci and are proven to still bite.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0.
- [ ] `frontend/src/legacy/bridge.js` contains no `reviewGraphData` export
      and no reverse-direction save bridge.
- [ ] Live: create and save an evenement; confirm it appears in the world.
- [ ] Live: run a region generation end to end - draft, pre-commit graph
      preview, review, commit - and confirm the created locations.
- [ ] Live: run the room batch generator end to end, including its preview.
- [ ] Live: "Générer les buts manquants" completes on the NPC list.
- [ ] Live: `competences`, `registre` and `prompts` still work.
- [ ] The residual list is reported and matches the three expected tabs.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief -l.
