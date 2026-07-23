# BRIEF - Step "review component core + tree cutover"

## Context
TICKET-0041, step 1 of 3. `regionCascade` (`index.html:5915`) computes the
region root inside its own body (`rootLocal`, `:5917`) and hard-wires it as the
fallback parent of every orphaned location (`:5924`). TICKET-0042's batch
generator must re-attach to a creator-chosen anchor instead. This step extracts
the review core - cascade, accept/reject, notes, node, tree - into a generic
`review*` component driven by an explicit descriptor, and cuts the region tree
over to it. The graph trio is BRIEF-0041-b; the G1 check is BRIEF-0041-c. ZERO
new functionality: the region review must behave identically.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors taken on live `main`, schema v1.85, `index.html` = 11206 lines.
- `let regionDraft` `:5872`; `regionAccepted` `:5876`; `regionConfirmedLinks`
  `:5877`; `regionCommitResult` `:5878`; `regionLocGraphOpen` `:5879`.
- `const REGION_FACTION_COLORS` `:5881`; `regionFactionColor` `:5883`.
- `regionIsAccepted:5889`, `regionToggleAccept:5893`, `regionCascade:5915`,
  `regionEntityNotes:6151`, `regionRenderLinkToggles:6166`,
  `regionRenderNotes:6185`, `regionRenderFactionsPanel:6192`,
  `regionRenderLocationNode:6211`, `regionRenderTree:6232`,
  `regionRenderAll:6273`, `regionLocGraphData:6327`.
- CSS: `.region-loc-node:972`, `.region-loc-children:973`,
  `.region-rejected:974`, `.region-fac-badge:975`, `.region-name-link:1034-1035`.
- `_sheetEntityOptions:10881`, its `regionIsAccepted` call at `:10886`.
- `loader: regionRenderAll` in the `CREATION_TABS` registry, `:4191` - this name
  is covered by `tooling/verify/checks/page_contract.py` and MUST NOT change.
- Confirm `regionRenderFactionsPanel`'s body does not use its `cascade`
  parameter. If confirmed: REPORT ONLY, leave the signature alone.

## Scope IN

1. **New block**, inserted at `index.html:5870`, immediately BEFORE
   `let regionDraft`, opened by this header comment verbatim:

   ```
   /* ── Review component (TICKET-0041, BRIEF-0041-a) ─────────────────────────
    * Generic accept/reject review tree. Knows NOTHING about the world model:
    * no location, no faction, no draft, no sensed_link. A consumer registers a
    * descriptor under a key and the component drives the render from it.
    *
    * Inline onclick handlers are string literals and cannot carry a closure,
    * so every DOM-reachable entry point takes the registry key as its first
    * argument (E1). reviewCascade and reviewNotes are pure and take no key.
    *
    * DESCRIPTOR CONTRACT
    *   key               registry key, e.g. 'region'
    *   nodes             [{ id, name, subtitle, parentId, description,
    *                        notes[], extras }]
    *                     `extras` is a pre-rendered HTML string owned by the
    *                     consumer (region: the sensed_links toggles).
    *   accepted          plain map id -> bool. ABSENT or true means accepted
    *                     (default-accept, unchanged from BRIEF-36 B1).
    *   fallbackParentId  where an orphaned node re-attaches, or null.
    *                     region -> the draft root; batch -> the creator's
    *                     anchor. THIS is the parameter TICKET-0041 exists for:
    *                     it must never be recomputed inside the component.
    *   reparentedLabel   badge text shown on a re-attached node
    *   graphSvgId        DOM id of the <svg> the graph draws into
    *   graphOpen         bool, graph pane currently open
    *   onToggleAccept(id)  consumer mutates its own accepted map
    *   onToggleGraph()     consumer mutates its own open flag
    *   onOpenSheet(id)     consumer opens its own full sheet
    *   onRender()          consumer re-renders itself fully
    *   graphExtraEdges(acceptedIds, nodeById) -> [{ id, entity_a_id,
    *                       entity_b_id, kind }]   (BRIEF-0041-b)
    * ────────────────────────────────────────────────────────────────────── */
   ```

2. **Registry**, in that block:
   ```js
   const REVIEW_DESCRIPTORS = {};
   function reviewRegister(key, descriptor) { REVIEW_DESCRIPTORS[key] = descriptor; }
   function reviewDescriptor(key) { return REVIEW_DESCRIPTORS[key]; }
   ```

3. **`reviewCascade(descriptor)` - PURE.** No global read, no DOM, no
   `reviewDescriptor` call. Exactly one parameter. Returns
   `{ acceptedIds: Set, effectiveParent: {} }`. `rootLocal` is GONE: the
   fallback is `descriptor.fallbackParentId`. Logic transcribed from
   `regionCascade:5915-5928` with that single substitution:
   - `acceptedIds` = ids of `nodes` whose accepted state is not `false`;
   - for each node: `parentId == null` -> `effectiveParent = null`; parent
     accepted -> `effectiveParent = parentId`; otherwise
     `effectiveParent = (fallbackParentId && acceptedIds.has(fallbackParentId)
     && fallbackParentId !== node.id) ? fallbackParentId : null`.
   Note the returned shape drops `rootLocal` (RECON: nothing outside
   `regionCascade` ever read it).

4. **`reviewIsAccepted(key, id)`** - `reviewDescriptor(key).accepted[id] !== false`.
   **`reviewToggleAccept(key, id)`** - flips through `d.onToggleAccept(id)` then
   calls `d.onRender()`.

5. **`reviewNotes(notes)` - PURE.** Byte-for-byte the body of
   `regionRenderNotes:6185-6190`.

6. **`reviewNode(key, node, cascade, childrenByParent)`** - transcribed from
   `regionRenderLocationNode:6211-6230`, reading `node.*` instead of
   `loc.result.draft.public.*`:
   - re-parented test: `node.parentId != null && cascade.effectiveParent[node.id] !== node.parentId`;
   - badge text is `d.reparentedLabel`, never a literal;
   - name click calls `reviewOpenSheet(key, id)` - add this two-line entry point
     delegating to `d.onOpenSheet(id)`;
   - accept button calls `reviewToggleAccept('<key>','<id>')`;
   - body order UNCHANGED: header row, description, `reviewNotes(node.notes)`,
     `node.extras`, children;
   - recursion on `reviewNode(key, child, cascade, childrenByParent)`.

7. **`reviewTree(key, cascade)`** - transcribed from `regionRenderTree:6232-6247`,
   including verbatim the BRIEF-0033-c comment about rendering every top-level
   node, not only the first. Empty-list messages become descriptor-free generic
   strings: `'<div class="empty">Aucun element propose.</div>'` and
   `'<div class="empty">Aucun element racine dans le brouillon.</div>'`.

8. **CSS renames** (required by the ticket's regle 3 - a `region-` class name
   inside the component would leave the token there):
   - `.region-loc-node` -> `.review-node` (`:972`; use at `:6217`)
   - `.region-loc-children` -> `.review-children` (`:973`; use at `:6228`)
   - `.region-rejected` -> `.review-rejected` (`:974`; uses at `:6199`, `:6217`)
   - `.region-name-link` -> `.review-name-link` (`:1034-1035`; uses at `:6201`,
     `:6219`)
   `.region-fac-badge` stays as is - faction-only, never emitted by the component.

9. **`regionReviewDescriptor()`** - new, region-side, placed immediately after
   `regionCascade`'s former position. THE single site that reads
   `regionDraft`/`regionAccepted` to build a descriptor. Returns:
   - `key: 'region'`;
   - `nodes`: one per `regionDraft.locations`, `{ id: l.local_id,
     name: l.result.draft.public.name, subtitle: l.result.draft.public.location_type || '',
     parentId: l.parent_local_id, description: l.result.draft.public.description,
     notes: regionEntityNotes(l, 'location'), extras: regionRenderLinkToggles(l) }`;
   - `accepted: regionAccepted`;
   - `fallbackParentId`: the former `rootLocal` expression, computed HERE:
     `(regionDraft.locations.find(l => l.parent_local_id == null) || {}).local_id || null`;
   - `reparentedLabel: 'rattache a la racine'` - **write the accented literal
     exactly as it renders today: `rattaché à la racine`**;
   - `graphSvgId: 'region-lieux-graph-svg'`, `graphOpen: regionLocGraphOpen`;
   - `onToggleAccept: id => { regionAccepted[id] = !reviewIsAccepted('region', id); }`;
   - `onToggleGraph: () => { regionLocGraphOpen = !regionLocGraphOpen; }`;
   - `onOpenSheet: id => regionRenderSheet('location', id)`;
   - `onRender: regionRenderAll`;
   - `graphExtraEdges`: `() => []` in this brief, filled in BRIEF-0041-b.

10. **`regionRenderAll` rewiring** (`:6273`, name UNCHANGED - `page_contract.py`
    depends on it): replace `const cascade = regionCascade()` with
    ```js
    const descriptor = regionReviewDescriptor();
    reviewRegister('region', descriptor);
    const cascade = reviewCascade(descriptor);
    ```
    and `${regionRenderTree(cascade)}` with `${reviewTree('region', cascade)}`.
    Everything else in that function - the header row, the skipped block, the
    graph pane markup, the two-column layout, the commit status div - is
    untouched in this brief.

11. **`regionRenderFactionsPanel` (`:6192`) - three call sites only:**
    `regionIsAccepted(f.local_id)` -> `reviewIsAccepted('region', f.local_id)`;
    `onclick="regionToggleAccept(...)"` -> `onclick="reviewToggleAccept('region', ...)"`;
    `regionRenderNotes(...)` -> `reviewNotes(...)`. Plus the two CSS class
    renames of item 8 that occur in its template. Its structure, its faction
    colouring, its badge, its `cascade` parameter: untouched.

12. **`_sheetEntityOptions` (`:10881`) - one call site:**
    `regionIsAccepted(e.local_id)` -> `reviewIsAccepted('region', e.local_id)`.

13. **`regionLocGraphData` (`:6327`) transitional rewiring** - `regionCascade`
    must not survive this brief, so replace its call with
    `reviewCascade(regionReviewDescriptor())`. The three graph functions keep
    their `region*` names in this brief; BRIEF-0041-b renames them.

14. **Delete** `regionCascade`, `regionIsAccepted`, `regionToggleAccept`,
    `regionRenderNotes`, `regionRenderLocationNode`, `regionRenderTree`. Six of
    the nine. The other three go in BRIEF-0041-b.

## Scope OUT
- The graph trio rename (`regionToggleLocGraph`, `regionLocGraphData`,
  `regionLocGraphRender`) and `graphExtraEdges`: BRIEF-0041-b. Leave them named
  `region*`.
- `tooling/verify/checks/review_component.py`: BRIEF-0041-c. Write no check here.
- Splitting `index.html` into files, extracting a `<script src>`, adding a
  serving route or a build step: C1, its own future ticket. The component is a
  BLOCK inside `index.html`, nothing more.
- The Factions panel's structure, `regionFactionColor`, the seven
  `regionManifest*`, `regionCommit`, `regionRenderCommitResult`,
  `regionRenderSheet` itself, `regionEntityNotes`, `regionRenderLinkToggles`,
  `regionLinkKey`, `regionIsLinkConfirmed`, `regionToggleLink`,
  `regionRenderBriefForm`, `regionGenerate`, `regionBuild`, `regionRestart`,
  `regionShellNewRegion`.
- Removing the dead `cascade` parameter of `regionRenderFactionsPanel`: REPORT
  ONLY, do not touch.
- Any event-delegation / `data-` attribute rewrite of the inline `onclick`
  idiom. The registry (E1) is the locked mechanism.
- Any change to `regionRenderAll`'s registration in `CREATION_TABS` (`:4191`).
- Any new endpoint, any fetch, any canon read or write. This step is pure client
  render.

## Invariants to defend
- **`page_contract.py`**: `regionRenderAll` is the `region` tab's `loader` in the
  `CREATION_TABS` registry. Renaming it breaks the G1 gate.
- **No structure without a reader**: no descriptor field is added that no
  function reads. `graphExtraEdges` is the single sanctioned exception - it is
  declared here as `() => []` and read in BRIEF-0041-b, one brief later, and is
  named in this brief's Scope OUT for that reason.
- **Default-accept (BRIEF-36 B1)** and **default-unconfirmed links (BRIEF-37)**
  are opposite defaults on purpose. `reviewIsAccepted` keeps `!== false`; the
  link toggles are not touched.
- **Secrets structurally excluded**: `regionEntityNotes` and
  `regionRenderLinkToggles` read `draft.secret.*` and stay region-side. The
  component never sees a `secret` object; it receives a rendered string. Do not
  move them into the component to "complete" the extraction.
- **Client-side only**: the region review is a pure render over in-memory
  `regionDraft` (BRIEF-41 R4a). No fetch enters the component.

## Done means
- [ ] `grep -c "regionCascade\|regionIsAccepted\|regionToggleAccept\|regionRenderNotes\|regionRenderLocationNode\|regionRenderTree" src/world_engine/cockpit/index.html` returns 0.
- [ ] `grep -c "region-loc-node\|region-loc-children\|region-rejected\|region-name-link" src/world_engine/cockpit/index.html` returns 0.
- [ ] `grep -n "reviewRegister('region'" src/world_engine/cockpit/index.html` returns exactly one line.
- [ ] No body of a `function review*` contains the substring `region` (case-sensitive), CSS class names included.
- [ ] `reviewCascade` takes exactly one parameter, its body contains `fallbackParentId`, and contains neither `document.` nor `getElementById`.
- [ ] Live: generate a region; the tree renders with identical indentation, subtitles and descriptions.
- [ ] Live: reject an intermediate location that has children -> children re-attach under the root, each carrying the `rattaché à la racine` badge; the rejected node dims at opacity 0.5.
- [ ] Live: reject the root itself -> its children fall to top level, unchanged.
- [ ] Live: re-accept everything -> the tree returns to its original shape.
- [ ] Live: the sensed_links confirm/discard toggles still render and still default to unconfirmed; non-wirable links still render as plain notes.
- [ ] Live: click an entity name -> the full sheet opens; its parent select still suffixes rejected entities with ` (rejeté)`; closing it refreshes the tree.
- [ ] Live: the Factions panel renders identically - same colours, same badges, same accept/reject, same notes.
- [ ] Live: the pre-commit graph still opens and renders (it is still on the old `region*` path in this brief).
- [ ] Live: commit the region -> committed counts, written/unresolved links and notes identical in shape to a pre-ticket commit.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update
None in this brief - no schema change, no new invariant yet. `CLAUDE.md` and
`ARCHITECTURE_DECISIONS.md` are written once, in BRIEF-0041-c, when the boundary
is enforced by a check rather than by convention.
