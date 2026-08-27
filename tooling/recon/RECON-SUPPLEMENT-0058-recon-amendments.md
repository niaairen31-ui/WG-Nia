# TICKET-0058 — RECON-0058-a amendments

Supplement to hand to the executor alongside each "OK to start" for briefs
-d .. -l. Each section AMENDS the named brief; where a supplement and the
brief disagree, the supplement wins. Written on locks **F2 / G1 / H1**.

Ticket-level corrections that apply to every remaining brief:

- **B2's rule is restated.** The cut follows the **call closure UNION the
  container occupancy**, with the generic dispatcher as a BOUNDARY, not a
  member. `_creationActivateTab`, `showCreationSubTab`, `renderCreationShell`,
  `_onDemandSlotToggle`, `_renderOnDemandToggles` appear in RECON-0058-a M4's
  closure and MUST NOT migrate under A1. Any brief that finds itself moving
  one of them has left the ticket; STOP and escalate.
- **The migration surface is nine `CREATION_TABS` keys**, not eleven and not
  eight: `npc`, `pj`, `lieux`, `factions`, `objets`, `intrigues`,
  `evenements`, `region`, `constructeur`.
  - `artefacts` and `queue` are OUT (own containers, zero `author*`
    references, confirmed three ways each in M4c). They join `competences`,
    `registre` and `prompts` in TICKET-0059.
  - `intrigues` is IN despite M4's verdict. It never calls `author*`, but its
    registry entry declares `containers: ['creation-editor-area']` and
    overrides `listLoader`/`listRenderer`/`sheetRenderer`/`createPanel` with
    its own hand-rolled functions, which write into `#author-entity-list` and
    `#author-main` - the exact nodes briefs -e and -f turn into mount targets.
    Left legacy, it would `innerHTML` over a live island: M5's destruction
    mode, arriving through a different door.
- **The expected residual at the end of the ticket is FIVE legacy tabs**
  (`competences`, `registre`, `prompts`, `artefacts`, `queue`), not three.
  Every brief that reports a residual reports against five.
- **M4 false positives - do not chase them.** `markCardDone` and
  `spatialTalkTo` do not call `author*`; their apparent call sites are inside
  the `CREATION_TABS` contract comment (index.html:4069-4076).
  `evenementsRemoveChip` likewise: `"authorSave"` appears only in a comment
  at 5247.

---

## Pre-flight — verification of BRIEF-0058-c (already executed)

Not an amendment; three findings arrived after -c was written. Confirm each
against the landed branch before -d starts. Any "no" is a regression to fix
in its own commit, not a finding to carry forward.

1. **Zoom and pan exist on the converged relation graph.** RECON M3 records
   that mouse-wheel zoom and canvas drag-to-pan were cytoscape DEFAULTS
   (`userZoomingEnabled`/`userPanningEnabled`) with no `cy.zoom()`/`cy.pan()`
   /`cy.fit()` call anywhere in the source - trivially invisible to a
   source-driven port, and promised to the user in the in-app help text at
   index.html:10563-10565. Confirm both gestures work.
2. **`relGraphGlobalNodeDblTap` was resolved deliberately.** It was the one
   DROP candidate (cosmetic, non-persisted "followed" enlargement, global
   mode only). Report whether it was ported or dropped. Note that ego-mode
   double-tap-to-recenter (index.html:10628) is a DIFFERENT behaviour and was
   a PORT item - confirm it survived.
3. **`linkAgentCommit`'s refresh call site was updated.** BRIEF-0058-c said
   to preserve `npcAgent*`/`linkAgent*` untouched; RECON M8(c) shows
   `linkAgentCommit` (index.html:11717-11729) called `relGraphFetchGlobal()`
   / `relGraphFetch(authorEntityId)` at 11723-11724 - the single coupling
   point. Confirm it now triggers the primitive's reload entry point
   (`graph:invalidate`, per `frontend/src/graph/mount.js`) and does not
   reference a deleted function.
4. **Record the substrate change.** Cytoscape painted to a `<canvas>`
   (M6); the primitive paints SVG DOM. Combined with M1's finding that
   legibility degrades at 10x under a fixed 960x480 viewBox, this is a
   headroom limit worth stating once in brief -l - not a defect to fix here.

---

## Supplement to BRIEF-0058-d — island seam + Constructeur pilot

**RECON M5 returned REFUTED. Do NOT implement the fix the RECON result
recommends.** Its recommendation - remount from inside `constructeurRender()`
on every call - is the fix for the PROBE, which mounted beside a surviving
legacy renderer. This brief DELETES `constructeurRender`. Applying the
recommendation literally would keep a destructive legacy renderer alive
permanently and make the mount's survival a matter of call-site discipline.
The answer is structural instead:

1. **New rule, verbatim into the `CREATION_TABS` entry-contract comment**,
   appended to the `island` field documentation this brief already adds:

   ```
   //                 An entry declaring `island` MUST also declare
   //                 loader: null and state.onWorldSwitch: null. The shell
   //                 owns this tab's body; a legacy loader or world-switch
   //                 renderer would innerHTML over the mounted island
   //                 (RECON-0058-a M5). Island world-state resets are
   //                 driven by serverState, not by a legacy callback.
   ```

2. **`_creationActivateTab` dispatches `island:slot` on EVERY activation**,
   not only the first. It must not sit behind a first-time guard or an
   `onDemandSlotState`-style latch. `mount.js`'s existing stale-node
   reconciliation (`existing.node === node`, the "surrounding panel re-emitted
   its markup" branch) already tolerates repeated calls - RECON M5 confirmed
   re-mount after destruction succeeds cleanly with no new lifecycle code.

3. **The Constructeur registry entry becomes**
   `loader: null`, `state: { onTabEnter: null, onWorldSwitch: null }`,
   `island: { key: 'constructeur' }`, `primaryAction` unchanged. Delete
   `constructeurRender` (7196) AND `constructeurResetForm` (7247) - the
   latter is what destroyed the probe on world switch even when Constructeur
   was not the visible tab, because `_creationRunWorldSwitchResets`
   (index.html:4531) runs every entry's `onWorldSwitch` unconditionally.

4. **World-switch handling moves into the component.** `Constructeur.svelte`
   reads `serverState.worldId` (`frontend/src/lib/serverState.svelte.js:8`)
   and resets its own form reactively when it changes. The server is the
   authority on the active world (TICKET-0056 C3); the island reads that
   authority directly instead of being told by legacy code.

5. **`creation_island.py` gains two rules**, both vacuous-proof:
   - **rule 9** - every `CREATION_TABS` entry declaring `island` declares
     `loader: null` and `onWorldSwitch: null`. Zero entries collected is a
     failure.
   - **rule 10** - the `island:slot` dispatch in `_creationActivateTab` is
     unconditional: assert it is not nested inside any `if` that tests a
     first-time/loaded/open flag. If that is not expressible as a robust
     textual assertion, assert instead that no identifier matching
     `loaded|mounted|_once` appears within the dispatching statement's
     enclosing block, and say in the docstring why the weaker form was
     chosen.

6. **M7 confirms the pilot choice** - Constructeur carries 0 static and 2
   JS-emitted inline handlers (both `oninput`, index.html:7205/7209). M6
   confirms zero SVG anywhere in `index.html`, so no icon conversion is
   implied: the glyphs in play are already unicode.

7. **Add to Done means:** live, switch to another sub-tab and back, then
   switch worlds, and confirm the Constructeur island is alive and functional
   after each - these are the two paths M5 measured as destructive.

---

## Supplement to BRIEF-0058-e — entity list + return navigation

1. **`intrigues` is in scope** (see ticket-level correction). Its
   `listLoader` and `listRenderer` overrides target the same nodes this brief
   converts to mount points. Either migrate them here with the generic list,
   or - if that proves too large - convert `intrigues` to render into its own
   container in this commit and migrate its body in -f. Do not leave a legacy
   renderer pointed at a mount target for even one brief.

2. **All seven editor-area occupants already declare `loader: null`.** The
   M5 destruction mode does not apply to this container from the tab
   dispatcher. It DOES apply from `onWorldSwitch`: each of the seven declares
   a real reset (`_npcWorldReset`, `_pjWorldReset`, `_lieuxWorldReset`,
   `_factionsWorldReset`, `_entityListWorldReset`, `_intriguesWorldReset`,
   `_evenementsWorldReset`). Per the -d rule, each entry that gains `island`
   sets `onWorldSwitch: null` and its reset moves into the Svelte store,
   driven by `serverState.worldId`. Verify none of the seven resets does DOM
   work before deleting it; if one does, report it.

3. **`authorSelectEntity` is the selection entry point** and has four callers
   in the closure: `creationRenderEntityList` (7348), `renderLieuxBrowse`
   (7461), `creationOpenEntityFrom` (9373), `creationReturnToOrigin` (9385).
   `creationRenderReturnControl` (9392) does NOT call `author*` - it is called
   BY `authorSelectEntity`, so it enters the closure inward. Migrate it with
   the selection path, not with the crumb helpers.

4. **Also in the closure and belonging to this brief:**
   `creationResolveEntityTab`, `creationSelectRecord`, `lieuxHasActiveDescendant`,
   `lieuxChildrenOf`, `lieuxDescend`, `lieuxJumpTo`, `lieuxToggleActiveOnly`.

---

## Supplement to BRIEF-0058-f — entity sheet core

1. **The exact legacy callers of the save/sheet path**, from M4(a) - bridge
   these and no others, and enumerate them verbatim in the comment this brief
   requires: `renderEventSheet` (5259), `evenementsSave` (5282),
   `evenementsRenderCreatePanel` (5327), `evenementsSubmitCreate` (5400),
   `regionCommit` (6702), `batchCommit` (7083), `_buildRuntimeCreationTabs`
   (7285), `generatePendingCreation` (7991-7997), `_factionRosterRowHtml`
   (8919-8923), `npcGoalsBackfillAll` (10126), `pcCreateSubmit` (10242).

2. **Preserve the no-inline-handler field contract.** M7 records that
   `authorRenderField`'s generic cases (textarea/number/select/bool/text/
   entity_ref) deliberately carry NO inline handlers: they emit
   `data-field`/`data-kind` attributes that `authorReadField` reads back at
   save time. That is a real invariant, not an accident of style - the read-back
   is centralised and total. A Svelte port must keep read-back centralised
   (one function producing the payload from state); it must not scatter
   per-field change handlers that each write into a store, because that
   silently changes WHEN a value is captured.

3. **`pj` pulls a skills panel into the closure** (`pcRenderDraftKnowledge`,
   `skillLoadCharacters`, `skillSelectCharacter`, `skillRender`,
   `skillSaveTier`, M4b). Decide explicitly and report: migrate the skills
   panel with the PJ sheet in this brief, or leave it legacy inside a
   migrated sheet. Leaving it legacy means a legacy renderer inside a Svelte
   sheet - the -d rule says that is not acceptable, so the default is
   migrate. If the size is prohibitive, STOP and escalate rather than deciding.

---

## Supplement to BRIEF-0058-g — sheet sub-editors

1. **First task, before any port: an exhaustive handler enumeration.** M7's
   editor-area figures (5 static / 69 `onclick`, 2 static / 9 `onchange`) are
   explicitly a high-confidence APPROXIMATION over a ~6300-line span across
   ~35 sub-renderers. Produce the exact per-function count and append it to
   the brief's own result. A family whose real count is far above the estimate
   is a re-sizing signal, reported before it is ported.

2. **The four DOM-scraping sync helpers are a port hazard**:
   `_syncPendingKnowledgeFromDom`, `_syncPendingGoalsFromDom`,
   `_syncSubcultureDraftFromDom`, `_syncFactionRolesFromDom` (M4b). Each
   reads the live DOM at save time. In Svelte they become state, not
   `querySelector` sweeps over a rendered tree. A port that keeps DOM
   scraping inside a Svelte component reintroduces exactly the coupling this
   workstream exists to remove - and will silently read a stale tree.

3. **The Lieux create/save flow belongs to family (a)**:
   `_authorLocationTypeOptionLabel`, `_authorOpenTemplateModalFor`,
   `_authorPromptLocationTypeClassification`, `_authorClassifyLocationType`
   (M4b). The last one reaches a model; it must stay proposal-only.

---

## Supplement to BRIEF-0058-h — AI draft path

1. **`generatePendingCreation` (7977) is the pending-AI-creation card path**
   and calls `authorRenderSheet` plus all three `authorApply*Draft` functions
   at 7991-7997 (M4a). It migrates here, together with `loadPendingCreations`
   (7937) if brief -f left it, and with the pending-card sync helpers not
   already taken by -g.

2. **This is the highest-risk file in the ticket for the doctrine.** The
   pending-creation card is where a model-proposed entity is closest to a
   write. Confirm in the result that no path exists from a draft to a save
   call without a creator submit, and name the function where the submit
   occurs.

---

## Supplement to BRIEF-0058-i — RE-SCOPED: review component + Region

**This brief's stated subject was wrong.** `reviewRegister` has exactly two
call sites in the whole file: `reviewRegister('region', ...)` at
index.html:6647 and `reviewRegister('batch', ...)` at 7116. The Review Queue
tab does NOT use the governed review component - its loader (`loadQueue`,
2819) and the whole proposed-mutation section (~2760-3200) contain zero
`author*` and zero review-component references (M4c).

Re-scope, per lock G1:

1. **In scope:** the generic review tree (`reviewRegister`, `reviewDescriptor`,
   `reviewCascade`, `reviewIsAccepted`, `reviewToggleAccept`, `reviewNotes`,
   `reviewOpenSheet`, `reviewNode`, `reviewTree`, `reviewToggleGraph`) AND
   its first consumer, `region`. Re-home `review_component.py` and
   `review_root_fallback.py` here.
2. **Out of scope:** the Review Queue tab. It goes to TICKET-0059 with
   `artefacts`. Delete the brief's Scope IN item 6 (the Play-adjacent batch
   review cluster) entirely - it belongs to the queue, not to this component.
3. **`region` carries a destructive loader** (`loader: regionRenderAll`) and
   a real `onWorldSwitch` (`_regionWorldReset`). Apply the -d rule: on
   migration, `loader: null`, `onWorldSwitch: null`, world reset driven by
   `serverState`.
4. **Region has its own parallel field renderer** - `_sheetListSection`,
   `_regionSheetNode`, `_sheetFieldInput`, `_sheetFieldTextarea`,
   `_sheetEntityOptions`, `_regionSheetRolesHtml`, `_regionSheetAddRole/
   RemoveRole/MoveRole`, `regionRenderSheet` (M4b) - distinct from
   `authorRenderField`. It is a genuine "plusieurs choses qui font la meme
   chose" candidate. **REPORT ONLY.** Do not converge it onto the migrated
   field engine in this brief; document the overlap and let Nia decide
   whether it earns its own step.
5. **The room-batch generator lives inside the `lieux` tab**
   (batch-panel-wrap container, M4b), not in `queue`. It is the review
   component's second consumer and lands in -j.

---

## Supplement to BRIEF-0058-j — RE-SCOPED: closure sealing

1. **Scope becomes:** `evenements` (create panel, save, submit, chips,
   `renderEventSheet`, `evenementsGenerateDraft`, `loadEventsList`), the
   room-batch generator (`batchReset`, `batchOpenPanel`,
   `batchGenerateManifest`, `batchManifest*`, `batchRenderManifestTable`,
   `batchGenerateDrafts`, `batchRunCoherence`, `_batchNodeName`,
   `batchToggleEdgeConfirm`, `batchRenderEdgesPanel`, `batchOpenSheet`,
   `batchReviewDescriptor`, `batchRenderCommitResult`, `batchCommit`,
   `batchRenderAll`) as the review component's second consumer,
   `npcGoalsBackfillAll`, `pcCreateSubmit`, and the faction roster helpers
   (`_factionRoleOptionsHtml`, `_factionRosterRowHtml`) if -g left them.
   `region` moved to -i.
2. **The residual report expects FIVE tabs**: `competences`, `registre`,
   `prompts`, `artefacts`, `queue`. Any other name is a finding.
3. **Bridge removal is the proof of closure.** After this brief, no legacy
   function calls migrated code. If a bridge cannot be removed, name the
   surviving caller and STOP - an undocumented permanent bridge is the
   failure mode this ticket exists to avoid.

---

## Supplement to BRIEF-0058-k — route sync + tab contract

1. **The `page_contract.py` partition assertion extends to the -d rule:**
   an entry declaring `island` must also declare `loader: null` and
   `onWorldSwitch: null`. If `creation_island.py` rule 9 already asserts it,
   do not duplicate - assert it in exactly one check and say in the other's
   docstring where it lives.
2. **The pass line reports five legacy entries and nine islands**, not three
   and eleven.

---

## Supplement to BRIEF-0058-l — doctrine + docs

Add to the ARCHITECTURE_DECISIONS entry, beyond what the brief already
requires:

1. **B2 was measured wrong and corrected in flight.** Record the rule as it
   now stands - call closure UNION container occupancy, dispatcher as
   boundary - and record WHY the call-graph rule alone was insufficient:
   `intrigues` writes into the shared editor-area container without ever
   calling `author*`. This is the ticket's most transferable lesson and it
   belongs in the record, not in a brief.
2. **M5's refutation and the structural answer.** A legacy `loader` or
   `onWorldSwitch` that renders will destroy a mounted island. The answer is
   not a remount convention but a registry rule enforced by
   `creation_island.py`: an island entry declares neither. Record the
   disciplinary fix that was rejected, so no future reader re-invents it.
3. **The Review Queue never used the review component.** Correct the
   workstream map's assumption in the record; the queue goes to TICKET-0059.
4. **Substrate change and its headroom limit.** The relation graph moved from
   cytoscape's `<canvas>` to the primitive's SVG DOM. At the pilot's real
   size (|V|=7, |E|=8) layout is sub-millisecond and legible; at 10x
   synthetic scale (|V|=70) layout still costs under 20ms but legibility
   degrades under a fixed 960x480 viewBox. State it as a known ceiling with
   its numbers, not as a defect.
5. **Region's parallel field renderer** is recorded as a named, unresolved
   convergence candidate (-i item 4), with no ticket opened.
6. **The `relGraphGlobalNodeDblTap` decision**, whichever way it went.
