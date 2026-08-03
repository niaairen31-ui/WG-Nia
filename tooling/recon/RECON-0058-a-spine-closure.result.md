<!-- slug: spine-closure-mini-recon -->
# BRIEF-0058-a — spine closure + force-layout viability (mini-RECON, result)

Report-only. Nine measurements against `main`/`ticket/0058` as checked out.
M1 and M5 were executed live against a real running cockpit
(`python -c "...uvicorn.run(app,...)"`, port 8001) backed by an isolated
scratch SQLite database seeded via `scripts/seed_pilot.py`
(`WORLD_ENGINE_DATABASE_URL=sqlite:///<scratchpad>/m1_probe.db`) — never the
user's prod database, never the shared `test/` database used by the
automated suite. M9 was executed against a scratch copy of
`frontend/src/graph/`, `src/world_engine/cockpit/index.html` and
`tooling/verify/` under the session scratchpad, never the working tree.
M2/M3/M4/M6/M7/M8 are static-analysis measurements against the real
`index.html` and `frontend/src/graph/` sources, unmodified. No production
file was edited by this brief; the probe server, scratch DB, scratch
registry copy and in-browser probe DOM were all torn down before commit —
nothing but this result file is new in `git status`.

## M1 — force-layout viability (LOAD-BEARING)

**(a) Observed graph size, pilot world (Verkhaal, seeded via
`scripts/seed_pilot.py`).**

- Global (`GET /api/relation-graph`): **|V| = 7, |E| = 8**.
- Ego (`GET /api/characters/{id}/relation-graph`), center = `npc-reike`
  (highest degree in the global graph, 5): **|V| = 4, |E| = 8** — the ego
  endpoint includes inter-neighbor edges, so at this graph's size the ego
  edge count equals the global edge count even though the node count is
  smaller.

**(b) Throwaway force simulation, run inside the legacy frame document**
(`http://127.0.0.1:8001/legacy`, injected via the Browser pane's JS
execution tool against the live DOM/window of that document — not a
standalone Node script). Plain repulsion (Coulomb-like, `k/d²`) +
attraction (spring-to-rest-length along edges) + centring force, fixed 300
iterations, no library, 960×480 viewport (matching `Graph.svelte`'s current
fixed, non-zoomable `viewBox`). Timed with `performance.now()` around the
iteration loop only (excludes fetch/render). 5 trials per size after JIT
warm-up; legibility measured two ways: minimum pairwise node distance (vs.
16px node diameter, for overlap) and a brute-force edge-segment crossing
count (non-adjacent edge pairs only).

| Size | \|V\| | \|E\| | min/median/max ms (5 trials) | min inter-node dist | edge crossings |
|---|---|---|---|---|---|
| observed | 7 | 8 | 0.10 / 0.20 / 0.30 | 88.8px (no overlap) | 1 of 8 |
| 3x (synthetic) | 21 | 24 | 1.3 / 1.7 / 2.3 | 65.0px (no overlap) | 13 of 24 |
| 10x (synthetic) | 70 | 80 | 6.2 / 12 / 18.6 | 0px (overlap present) | 278 of 80 |

The cold (first-call, pre-JIT-warmup) observed-size run measured 8ms, still
far under the 2000ms gate.

The observed-size layout is fast (sub-millisecond, warm) and legible (only
1 crossing among 8 edges, no node overlap) — the ESCALATE clause
("observed-size layout takes more than 2000 ms or is not legible") is not
triggered at any measured size, let alone the observed one. The headroom
figures show timing is not the constraint even at 10x (worst case 18.6ms,
~100x margin below the gate) — but legibility degrades at 10x under the
**current fixed 960×480 viewport** (nodes begin to overlap, crossing count
rises steeply), which is a direct consequence of M3's finding that
`Graph.svelte` has no zoom/pan today. This is a headroom caveat for a
future large-world graph, not a blocker for C2 at the pilot's current
scale.

A visual (screenshot) confirmation of legibility could not be captured in
this session — the Browser pane's screenshot compositor was unavailable
("the Browser pane is not displayed, so the page is not compositing
frames"), consistently across retries. The quantitative proxies above
(inter-node distance vs. node diameter; geometric edge-crossing count) were
used instead of a visual read.

VERDICT: CONFIRMED - a plain, library-free force simulation lays out the pilot world's real relation graph (7 nodes/8 edges) in under 1ms, legibly (no node overlap, 1 edge crossing), with wall-clock time never approaching the 2000ms gate even at 10x synthetic scale (worst case 18.6ms); legibility at 10x is compromised only by Graph.svelte's current fixed, zoomless viewport, not by simulation cost — C2 is constructible at the pilot's scale and the observed-size escalation gate is not triggered.

## M2 — relGraph* parity inventory

Capability baseline: `Graph.svelte` (180 lines) renders SVG nodes/edges
with auto-circular placement for unpositioned nodes (or explicit
`coord_x`/`coord_y`), a single fixed viewBox (960×480, no zoom/pan), and
exactly three optional capability callbacks — `onConnect(a,b)` (click node
A then B), `onDeleteEdge(edgeId)` (click an edge), `onMoveNode(id,x,y)`
(drag, ≥5px threshold). It has no concept of multiple layout algorithms,
node info panels, edge metadata forms, colour-coded strength buckets,
ego/global modes, double-tap, or a "link-armed" gating state. `mount.js`
adds one generic, consumer-agnostic layer on top: a chrome head bar
(title + ↻ refresh button) built from an optional `chrome` descriptor,
load-on-open via a `graph:slot` DOM event, and reload-on-demand via a
`graph:invalidate` DOM event or the refresh button. Both `lieux.js` and
`review.js` confirm the contract: `load(meta)`, optional
`onConnect`/`onDeleteEdge`/`onMoveNode`, optional `chrome`,
optional `dashedKinds`.

| Function | Location | Behaviour | Classification |
|---|---|---|---|
| `relGraphLoad` | index.html:10478 | On-demand slot loader; updates mode UI, checks NPC/link-agent open batches, then fetches ego or global data depending on `relGraphMode` | PORT |
| `relGraphOnSelect` | index.html:10496 | Refetches ego graph when the NPC list selection changes, only while panel is open and in ego mode | PORT |
| `relGraphFetch` | index.html:10503 | Fetches `/api/characters/{id}/relation-graph` (ego data) and renders | PORT |
| `relGraphFetchGlobal` | index.html:10514 | Fetches `/api/relation-graph` (global data) and renders | PORT |
| `relGraphToggleMode` | index.html:10527 | Flips ego↔global, disarms in-progress link creation, refetches | PORT |
| `relGraphToggleLinkMode` | index.html:10544 | Arms/disarms the "Lier" two-tap connect gate (global mode only) | PORT |
| `relGraphRenderCanvas` | index.html:10569 | Builds/destroys the cytoscape instance: elements, layout (concentric/cose), full style sheet, mode-conditional event bindings | PORT |
| `relGraphGlobalNodeTap` | index.html:10638 | While armed: captures node A then B and opens the create-edge panel; otherwise falls through to the info card | PORT |
| `relGraphGlobalNodeDblTap` | index.html:10659 | Toggles a cosmetic, non-persisted "followed" (enlarged) node class | DROP candidate (below) |
| `relGraphEdgeTap` | index.html:10665 | Opens the edge panel in edit mode for the tapped edge (global mode) | PORT |
| `relGraphBucketToggle` | index.html:10679 | Updates bucket-visibility state and re-applies edge `display` per intensity bucket | PORT |
| `relGraphRenderInfoCard` | index.html:10684 | Renders the selected node's name/type/description plus its relation list (ego: vs. center; global: all) into the side panel | PORT |
| `relGraphOpenEdgePanel` | index.html:10722 | Renders the create/edit form (type, intensity, direction, notes) for an edge, driven by `_relGraphEdgePanelCtx` | PORT |
| `relGraphSaveEdgePanel` | index.html:10762 | Reads the edge-panel form and POSTs (create) or PUTs (edit) via the sanctioned relation-CRUD routes, then refetches global | PORT |
| `relGraphDeleteEdge` | index.html:10791 | Confirms, DELETEs the relation via the sanctioned route, refetches global | CARRIED — matches `onDeleteEdge`'s existing contract (confirm-then-DELETE; `mount.js`'s `wrapMutator` already auto-reloads on success); `lieux.js`'s `onDeleteEdge` is the identical pattern already live |

No function among the fifteen is pure CHROME: the mode/link/bucket
controls are static HTML (index.html:1299-1325) wired to these functions,
but every one of the fifteen does graph-state or data work, not head-bar
bookkeeping — the actual chrome bookkeeping helper (`_relGraphUpdateModeUI`)
is a separate `_`-prefixed function outside the counted fifteen.

### DROP candidates (Nia decides, listed separately)

- **`relGraphGlobalNodeDblTap`** (index.html:10659) — toggles a cosmetic
  "followed" (enlarged) node class in global mode only; explicitly
  non-persisted, purely session-local decoration with no data behind it.
  (Ego mode's double-tap-to-recenter is a separate, inline behaviour at
  index.html:10628 and is covered by the ticket's "double-tap recentring"
  PORT item, not this function.)

VERDICT: CONFIRMED - all fifteen relGraph* functions are accounted for, fourteen PORT and one CARRIED (relGraphDeleteEdge, matching Graph.svelte's existing onDeleteEdge contract exactly); one DROP candidate (relGraphGlobalNodeDblTap) is flagged separately for Nia, not resolved here.

## M3 — cytoscape API surface census

The vendored `cytoscape-3.34.0.min.js` (loaded index.html:1605) is used
**only** inside the relGraph cluster (index.html:10448-10822) — no other
live cytoscape usage remains in the file (Lieux and the review previews
already converged onto `Graph.svelte` in TICKET-0057).

- **`cytoscape({...})` constructor** — index.html:10589-10620, called from
  `relGraphRenderCanvas`. Options: `container` (10590, `#relgraph-canvas`),
  `elements` (10591, built 10576-10587 from `relGraphData.nodes`/`.edges`
  with per-node `id`/`label`/`isCenter` and per-edge
  `id`/`source`/`target`/`type`/`intensity`/`direction`/`bucket`), `layout`
  (10592-10594: `{name:'cose'}` global, `{name:'concentric', concentric: n
  => (n.data('isCenter') ? 2 : 1)}` ego), `style` (10595-10619, below).

- **Style-spec selectors/properties** (same constructor call):
  `'node'` (label, background/border colour+width, font-size, text colour,
  `text-valign:bottom`, `text-margin-y:4`); `'node[?isCenter]'`
  (accent background, `border-width:3`, `44x44`); `'node.followed'`
  (`56x56`, `border-width:3`); `'node.link-source'` (accent border,
  `border-width:3`); `'edge'` (`width:2`, `curve-style:bezier`, no default
  arrows); `'edge[direction = "a_to_b"]'` / `'edge[direction = "b_to_a"]'`
  (target/source arrow); `'edge[bucket = 1..4]'` (loop-generated,
  line/arrow colour from `RELGRAPH_BUCKET_COLORS` = `{1:'#e5534b',
  2:'#d29922', 3:'#58a6ff', 4:'#3fb950'}`, index.html:10459).

- **Event bindings** (`.on('tap'|'dbltap', selector, handler)`,
  index.html:10623-10628): node tap (global) -> `relGraphGlobalNodeTap`;
  node dbltap (global) -> `relGraphGlobalNodeDblTap`; edge tap (global) ->
  `relGraphEdgeTap`; node tap (ego) -> `relGraphRenderInfoCard`; node
  dbltap (ego) -> `relGraphFetch` (recenter on that node).

- **`cy` instance API calls** (post-construction): `.destroy()`
  (index.html:10469, 10572, 10808); `.nodes().removeClass('link-source')`
  (10548, 10647); `.getElementById(id).addClass('link-source')` (10642);
  `.getElementById(id).toggleClass('followed')` (10661);
  `.edges('[bucket = N]').style('display', ...)` (10675, looped 1-4).

- **Implicit (default, non-code-configured) capabilities** relied on per
  the in-app help text (index.html:10563-10565, "Molette pour zoomer,
  glisser pour déplacer… double-cliquez pour l'agrandir et le suivre /
  pour le recentrer"): mouse-wheel zoom and drag-to-pan the *canvas*
  (cytoscape's default `userZoomingEnabled`/`userPanningEnabled`) — no
  explicit `cy.zoom()`/`cy.pan()`/`cy.fit()` call exists in source, so this
  is easy to overlook but is real, user-facing behaviour the primitive does
  not have today (ties directly to M1's 10x legibility caveat: no zoom/pan
  means no escape hatch for a denser graph). Canvas drag-to-pan is distinct
  from `Graph.svelte`'s existing node-drag (`onMoveNode`), which
  repositions one node, not the viewport.

VERDICT: CONFIRMED - the vendored cytoscape usage is fully enumerated (one constructor call, nine style selectors, five event bindings, five post-construction API call sites, plus zoom/pan as unconfigured default behaviour); this is the complete reimplementation bill of materials for brief -c.

## M4 — the `author*` call closure (confirms or corrects B2)

Methodology: a JS-aware brace/string/comment scanner over `index.html`
(not naive line-range grepping) isolated exact top-level function bodies
(527 top-level functions total, 107 `author*`-prefixed), then every
non-`author*` body was searched for literal `author[A-Z]\w*(` call sites,
and the result BFS-expanded outward through non-`author*` callees to a
fixed point.

**(a) Non-`author*` top-level functions calling `author*`, directly** — 16
functions, correcting the intake note's list:

- `renderEventSheet` (5248) -> `authorRenderField` (5259)
- `evenementsSave` (5274) -> `authorReadField` (5282)
- `evenementsRenderCreatePanel` (5306) -> `authorRenderField` (5327)
- `evenementsSubmitCreate` (5395) -> `authorReadField` (5400)
- `regionCommit` (6687) -> `authorLoadEntityList` (6702)
- `batchCommit` (7061) -> `authorLoadEntityList` (7083)
- `_buildRuntimeCreationTabs` (7263) -> embeds `authorRenderSheet` (7285)
  inside the runtime-type `createPanel` closure it constructs
- `creationRenderEntityList` (7321) -> `authorSelectEntity` (7348)
- `renderLieuxBrowse` (7409) -> `authorSelectEntity` (7461)
- `generatePendingCreation` (7977) -> `authorRenderSheet`,
  `authorApplyLocationDraft`, `authorApplyFactionDraft`,
  `authorApplyCharacterDraft` (7991-7997)
- `_factionRosterRowHtml` (8915) -> `authorMemberRoleEditSubmit` /
  `...Cancel` / `...Start` (8919-8923)
- `creationOpenEntityFrom` (9359) -> `authorSelectEntity` (9373)
- `creationReturnToOrigin` (9380) -> `authorSelectEntity` (9385)
- `_authorSaveSubmit` (9562) -> `authorLoadEntityList`,
  `authorRenderSheet` (9666-9667)
- `npcGoalsBackfillAll` (10111) -> `authorLoadGoals` (10126)
- `pcCreateSubmit` (10189) -> `authorLoadEntityList` (10242)

**Corrections to the intake note:** `markCardDone` and `spatialTalkTo`
were false positives in the ticket's own intake list — their apparent
`author*` calls actually land inside a *comment block* (the CREATION_TABS
contract doc, index.html:4069-4076), which a naive line-range read
misattributes to the wrong enclosing function. `evenementsRemoveChip` is
likewise a false positive (the string `"authorSave"` appears only in a
comment at 5247, never a call). The third `creation*` navigation helper
near 9392, `creationRenderReturnControl`, does **not** call `author*`
itself — it is called *by* `authorSelectEntity`, the reverse direction, so
it enters the closure in (b), not (a).

**(b) Fixed-point closure — 112 non-`author*` functions**, including the
16 seeds. Grouped by what pulls each group in:

- Generic shell/dispatcher, shared by every `CREATION_TABS` entry:
  `esc`, `api`, `shortId`, `loadBootstrap`, `loadPlayerName`,
  `_onDemandSlotToggle*`, `_renderOnDemandToggles`, `_creationActivateTab`,
  `showCreationSubTab`, `renderCreationShell`, `creationInit`,
  `creationRenderEntityList`, `creationResolveEntityTab`,
  `creationOpenEntityFrom`, `creationReturnToOrigin`,
  `creationRenderReturnControl`, `creationSelectRecord`,
  `genericModalOpen`/`Close`.
- `evenements`: `loadEventsList`, `_evenementsRenderChips`,
  `evenementsAddChip`/`RemoveChip`, `renderEventSheet`, `evenementsSave`,
  `evenementsRenderCreatePanel`, `evenementsGenerateDraft`,
  `evenementsSubmitCreate`.
- Generic review-tree component (consumed by `region` + the room-batch
  generator inside `lieux`): `reviewRegister`, `reviewDescriptor`,
  `reviewCascade`, `reviewIsAccepted`, `reviewToggleAccept`, `reviewNotes`,
  `reviewOpenSheet`, `reviewNode`, `reviewTree`, `reviewToggleGraph`.
- `region`: `regionFactionColor`, `regionLinkKey`,
  `regionIsLinkConfirmed`, `regionToggleLink`, `regionReviewDescriptor`,
  `regionRenderBriefForm`, `regionGenerate`, `regionManifest*`,
  `regionBuild`, `regionRestart`, `regionEntityNotes`,
  `regionRenderLinkToggles`, `regionRenderFactionsPanel`,
  `regionRenderCommitResult`, `regionRenderAll`, `regionCommit`,
  `_sheetListSection`/`_regionSheetNode`/`_sheetFieldInput`/
  `_sheetFieldTextarea`/`_sheetEntityOptions`/`_regionSheetRolesHtml`/
  `_regionSheetAddRole`/`RemoveRole`/`MoveRole`, `regionRenderSheet`.
- Room-batch generator, living **inside** the `lieux` tab (batch-panel-wrap
  container): `batchReset`, `batchOpenPanel`, `batchGenerateManifest`,
  `batchManifest*`, `batchRenderManifestTable`, `batchGenerateDrafts`,
  `batchRunCoherence`, `_batchNodeName`, `batchToggleEdgeConfirm`,
  `batchRenderEdgesPanel`, `batchOpenSheet`, `batchReviewDescriptor`,
  `batchRenderCommitResult`, `batchCommit`, `batchRenderAll`.
- Dynamic runtime-type tab factory (built by `constructeur` — see the
  addendum below): `_buildRuntimeCreationTabs`.
- `lieux`: `lieuxHasActiveDescendant`, `lieuxChildrenOf`, `lieuxDescend`,
  `lieuxJumpTo`, `lieuxToggleActiveOnly`, `renderLieuxBrowse`.
- Pending-AI-creation review cards (embedded in npc/lieux/factions):
  `loadPendingCreations`, `generatePendingCreation`,
  `_syncPendingKnowledgeFromDom`, `_syncPendingGoalsFromDom`,
  `_syncSubcultureDraftFromDom`, `_syncFactionRolesFromDom`.
- `factions`: `_factionRoleOptionsHtml`, `_factionRosterRowHtml`.
- `lieux` create/save flow: `_authorLocationTypeOptionLabel`,
  `_authorOpenTemplateModalFor`, `_authorPromptLocationTypeClassification`,
  `_authorClassifyLocationType`.
- Generic save dispatcher for every entity-archetype sheet
  (npc/pj/lieux/factions/objets/runtime types): `_authorSaveSubmit`.
- `npc`: `npcGoalsBackfillAll`.
- `pj`: `pcCreateSubmit`, `pcRenderDraftKnowledge`, `skillLoadCharacters`,
  `skillSelectCharacter`, `skillRender`, `skillSaveTier`.

**Addendum, not caught by a pure outward walk but genuine:**
`constructeurSubmit` (7220) calls `refreshCreationTabs()` (7241), which
calls `_buildRuntimeCreationTabs()` (already in the closure above) — a real
inward chain that pulls `constructeur` into the closure despite no
function in `constructeur`'s own body textually containing an
`author...(` call.

**(c) `CREATION_TABS` keys touched: `npc`, `pj`, `lieux`, `factions`,
`objets`, `evenements`, `region`, `constructeur` — eight keys, NOT the
assumed eleven.**

**REMOVED from the assumed eleven, confirmed three independent ways each:**
- **`artefacts`** — its registry entry (index.html:4363-4371) sets
  `createPanel: null`, `primaryAction: null`, and `containers:
  ['creation-artefacts']` (excludes `'creation-editor-area'`, so
  `_creationActivateTab`'s `authorLoadEntityList` fallback never fires for
  it). Its own loader `loadCreationArtefacts` (5428-5446) renders
  non-clickable cards with zero `author` references.
- **`intrigues`** — its registry entry (4380-4391) overrides all four
  polymorphic entry points (`listLoader`, `listRenderer`, `sheetRenderer`,
  `createPanel`) with its own functions, none of which (nor their own
  callees) ever touches `author*` — unlike `evenements`, none of its field
  rendering is delegated to the generic `authorRenderField`/
  `authorReadField` widgets; it is fully hand-rolled.
- **`queue`** — its loader (`loadQueue`, 2819) and slot loader
  (`loadTickControls`, 2675) were grepped along with the whole
  proposed-mutation review-queue section (~2760-3200): zero `author`
  references.

**ADDED:** none.

This directly corrects B2's stated assumption (`TICKET-0058.md`, intake
section) that the closure is the eleven tabs `npc, pj, lieux, factions,
objets, artefacts, intrigues, evenements, region, queue, constructeur`.
Per this brief's Scope OUT, this correction is reported here for the
project owner to re-decide the ticket's boundary — not resolved by this
brief.

**(d) `competences`, `registre`, `prompts`:** **NOT** in the closure for
any of the three — none of `competencesLoadList`/`competencesAddManualRow`,
`loadRegistre`/`registreToggleAddForm`, or `promptsLoadList` appear
anywhere in it, and the generic dispatcher trio that IS in the closure
(`_creationActivateTab`/`showCreationSubTab`/`renderCreationShell`)
contains zero tab-id literals or special-casing — it dispatches purely via
`entry.loader()`/`entry.primaryAction.handler`/`entry.state.onTabEnter()`
read dynamically off `CREATION_TABS[currentCreationSubTab]`, a
non-statically-resolvable call that cannot textually pull those three
tabs' functions in, and indeed does not.

**Caveat for the project owner:** the generic dispatcher functions
themselves (`_creationActivateTab`, `showCreationSubTab`,
`renderCreationShell`, `_onDemandSlotToggle*`/`_renderOnDemandToggles`)
ARE in the closure, and `competences`/`registre`/`prompts` also depend on
these exact same shared functions to be dispatched to at all. So while
none of those three tabs' own logic calls or is called by `author*`, a
migration that moves the generic shell dispatcher (as opposed to just
`author*` and its direct closure) will mechanically touch code those three
tabs also rely on — a scope-boundary risk worth a deliberate call, not an
implicit assumption either way.

VERDICT: REFUTED - B2's assumed eleven CREATION_TABS keys are wrong: the measured author* closure touches only eight (npc, pj, lieux, factions, objets, evenements, region, constructeur); artefacts, intrigues and queue are each independently confirmed to never touch author* code, and competences/registre/prompts are confirmed to stay outside the closure as B2 already assumed. Reported for the project owner to re-decide the ticket's boundary, not resolved here.

## M5 — island survival across the legacy tab mechanism

Executed live against the running shell (`http://127.0.0.1:8001/`, real
`iframe#legacy-frame`) with the *actual*, already-converged `graph:slot`
mount channel (`frontend/src/graph/mount.js`, TICKET-0057) as the
throwaway probe mechanism — the same form BRIEF-0057-a established — rather
than authoring a brand-new `.svelte` file: a `lieux` consumer was mounted
via `graph:slot` into a scratch `#m5-probe-mount` div appended as a child
of `#creation-constructeur` (index.html:1429). This exercises the identical
mount/target/lifecycle code path a real Constructeur island would use.

**(a) Switch away to another sub-tab and back.** The island did **NOT**
survive. `showCreationSubTab` itself only toggles `style.display`
(index.html:4487-4497, confirmed unaffected), but `_creationActivateTab()`
(index.html:4433-4459) unconditionally calls `entry.loader()` on *every*
activation (index.html:4445) — and `constructeur`'s registry entry sets
`loader: constructeurRender` (index.html:4359), whose body
unconditionally does `root.innerHTML = ...` over the whole container
(index.html:7200), destroying the probe div (and, with it, the orphaned
Svelte instance's DOM) on the very next activation. Confirmed live:
`probeStillExists: false` after `ctab-npc` -> `ctab-constructeur`.

**(b) `refreshCreationTabs()`.** The island survived unaffected
(`probeLen` unchanged, `containerChildren` unchanged) — this function only
rebuilds the runtime-type tab buttons/registry (BRIEF-0046-d), it does not
touch `#creation-constructeur`'s content.

**(c) `activateWorld()` (world switch).** The island did **NOT** survive,
via a *different* path than (a): `activateWorld` calls
`_creationRunWorldSwitchResets()` (index.html:4531-4537) unconditionally
for *every* `CREATION_TABS` entry's `state.onWorldSwitch`, regardless of
which tab is currently active. `constructeur`'s entry sets
`onWorldSwitch: constructeurResetForm` (index.html:4360), and
`constructeurResetForm` calls `constructeurRender()` directly
(index.html:7247-7250) — same destructive `root.innerHTML =` as (a), but
triggered even if Constructeur was never the visible tab at switch time.
Confirmed live via a real `POST /api/worlds/{id}/activate` round-trip
(re-activating the same already-active pilot world in the isolated scratch
DB): probe destroyed, container replaced with `constructeurRender()`'s
fresh markup.

Re-mounting into a freshly-appended probe div with the same id after each
destruction succeeded cleanly with no error both times — `mount.js`'s
existing stale-node reconciliation (`mountGraph`'s `existing.node === node`
check, "the surrounding panel re-emitted its markup" branch, already
written for BRIEF-0057-a M8's identical finding on a different container)
already handles this case; no new mount.js logic is implied.

**Brief -d must mount (or re-request the mount) per activation, not once
and leave it.** Specifically: because `constructeurRender()` unconditionally
replaces the whole container on both tab-enter and world-switch, the future
Svelte island for Constructeur must be (re)mounted from inside (or
immediately after) `constructeurRender()` itself on every call — the
existing `mountGraph` reconciliation path already tolerates being called
into a stale/replaced node, so this is a call-site change, not new
lifecycle code.

VERDICT: REFUTED - a Svelte island mounted as a plain child of #creation-constructeur does NOT survive either a sub-tab switch away-and-back or a world switch (both destroy it via constructeurRender()'s unconditional root.innerHTML replace); it does survive refreshCreationTabs(). Brief -d must mount per activation, re-using mount.js's existing stale-node reconciliation, never mount once and leave it.

## M6 — SVG census in migrating containers

**Container boundaries used:** `#creation-npc-relgraph`
index.html:1299-1328; `#creation-editor-area` index.html:1331-1388 (static
shell only — seven `CREATION_TABS` entries — `npc`, `pj`, `factions`,
`objets`, `intrigues`, `evenements`, plus any runtime type — render their
sheets into this one shared shell at runtime, all included below);
`#creation-constructeur` index.html:1429 (single empty `<div>`, populated
entirely at runtime by `constructeurRender()`).

**File-wide result: zero occurrences of `<svg`, `<path`, `<circle`, or even
the bare substring `svg` (case-insensitive) anywhere in
`src/world_engine/cockpit/index.html`** — static markup and every JS
template string alike. All three containers are therefore empty for this
census, **including the relation graph's own rendering**: cytoscape paints
to a `<canvas>` (`#relgraph-canvas`, index.html:1320) via the vendored
`cytoscape-3.34.0.min.js`, not SVG DOM — no `cytoscape-svg` extension is
vendored. So `graph_primitive.py` rule 6 ("no `<svg` outside
`frontend/src/graph/`") has nothing to enforce against this legacy surface
today; it is already canvas-based, not SVG-based. All icon-like glyphs
found in these containers (`↻`, `⟳`, `●`, `›`, etc.) are already unicode
characters, not SVG — no icon-conversion work is implied here.

VERDICT: CONFIRMED - zero <svg/<path/<circle occurrences exist anywhere in index.html today; the relation graph itself already renders to a <canvas> via vendored cytoscape, not SVG, so graph_primitive.py rule 6 has nothing to enforce against the legacy document and no icon needs conversion in any of the three containers.

## M7 — inline handler census inside the migrating containers

| Container | onclick static/JS | onchange static/JS | oninput static/JS | onkeydown/onsubmit/onmousedown |
|---|---|---|---|---|
| `#creation-editor-area` (+ 7 sheet-tab consumers) | 5 / 69 | 2 / 9 | 0 / 0 | 0 / 0 |
| `#creation-npc-relgraph` (+ relGraph*/npcAgent*/linkAgent*) | 4 / 26 | 4 / 24 | 0 / 1 | 0 / 0 |
| `#creation-constructeur` | 0 / 0 | 0 / 0 | 0 / 2 | 0 / 0 |

Static handlers, `#creation-editor-area` (index.html:1335, 1350, 1358,
1361, 1362 `onclick`; 1376, 1378 `onchange`); `#creation-npc-relgraph`
(index.html:1302-1305 `onclick`, 1307-1310 `onchange`);
`#creation-constructeur` (index.html:7205, 7209 `oninput`, JS-emitted by
`constructeurRender()` itself — the container's static markup is a single
empty div).

JS-emitted handlers are spread across ~35 sheet sub-renderer functions for
the editor-area shell (`authorRenderField`, `authorRenderSheet`,
`authorRenderRolesEditor`, `authorRenderMemberships`,
`authorRenderFactionRoster`, `authorRenderGoals`, etc.,
index.html:4877-10430 — the editor-area figure is a high-confidence
approximation given the ~6,300-line span, not an exhaustive count) and
~15 functions for the relgraph/NPC-agent/link-agent block
(index.html:10448-11760, exhaustively scanned, higher confidence given its
~1,300-line, self-contained span). Generic dynamic fields
(`authorRenderField`'s textarea/number/select/bool/text/entity_ref cases)
deliberately carry no inline handlers — they use `data-field`/`data-kind`
attributes read back by `authorReadField` at save time, which is why
`oninput`/`onkeydown` are essentially absent from the editor-area despite
the large field count. Note: Constructeur's primary-action button ("Créer
le type") is not an inline handler in this container at all — per
CREATION_TABS (index.html:4355-4362) it is wired via the shared shell's
`primaryAction: { handler: constructeurSubmit }`, outside the container.

Sizing note for brief -e..-j: the editor-area shell is the overwhelmingly
larger surface (≈78 JS-emitted handlers across seven tabs sharing one
render tree) versus the relgraph container (≈51, concentrated in the
NPC-agent/link-agent chrome — see M8) and Constructeur (≈2, trivially
small, consistent with it being a from-scratch pilot rather than a port).

VERDICT: CONFIRMED - inline handlers are counted for all three containers (editor-area ≈7 static/78 JS-emitted, relgraph 8 static/51 JS-emitted, constructeur 0 static/2 JS-emitted), sizing briefs -e..-j: the editor-area shell is by far the largest surface.

## M8 — foreign chrome in the relation-graph container

**(a) `npcAgent*`/`linkAgent*` inside or outside the M4 closure.**
**Outside.** All 36 top-level `npcAgent*`/`linkAgent*` functions
(index.html:~10852-11730) were enumerated and their own outward call graph
walked (73 non-`author*` functions reached). Zero direct `author*` calls
in any of the 36 bodies. The only overlap with the M4 closure is through
trivial, file-wide shared utilities (`api`, `esc`, `shortId`) — not a
meaningful coupling. Their real callee graph is self-contained:
`_npcAgent*`/`_linkAgent*` private helpers plus the legacy `relGraph*`
cytoscape functions (see (c)).

**(b) Panel render targets.** `npcAgentToggle()` (10889-10897) toggles
`#npcagent-panel` (declared 1315); `linkAgentToggle()` (11371) toggles
`#linkagent-panel` (declared 1318). Both panels are DOM **siblings** of
`#relgraph-canvas` (1320) inside `#creation-npc-relgraph` (1299) — not
nested inside the graph's own render target. The launcher buttons
(`#npcagent-launcher-btn` 1304, `#linkagent-launcher-btn` 1305) sit in the
same head bar as the graph's own mode/link buttons (1302-1303).

**(c) Can a future brief replace the graph without touching
`npcAgent*`/`linkAgent*`?** **Mostly yes, with one narrow exception.** They
are structurally decoupled — separate DOM containers, separate function
families, no dependency on `author*` or the M4 closure. The one coupling
point: `linkAgentCommit` (11717-11729) calls `relGraphFetchGlobal()` /
`relGraphFetch(authorEntityId)` (11723-11724) to refresh the relation-graph
canvas after committing a batch of AI-proposed relation links (it also
reads the global `authorEntityId`/`relGraphMode` sheet-engine state to
decide which refresh to run). That is the only call from
`npcAgent*`/`linkAgent*` into the graph-rendering layer. Cross-reference:
`frontend/src/graph/registry.js` already names `relGraph*`
(`relation_cytoscape`) as the last non-converged legacy graph
implementation, `retiredBy: 'TICKET-0058'` — so the brief that replaces
`relGraphFetchGlobal`/`relGraphFetch` is this ticket itself, and when it
does, `linkAgentCommit`'s one refresh call site needs updating to whatever
the primitive's reload entry point is — a one-line touch to one function,
not a structural change to the `npcAgent*`/`linkAgent*` families.

VERDICT: CONFIRMED - npcAgent*/linkAgent* are outside the M4 closure and render into their own sibling panels, not nested inside the graph's render target; a future brief can replace the graph beneath this chrome without editing those functions except for updating linkAgentCommit's single graph-refresh call site.

## M9 — the empty-registry failure, confirmed by execution

Scratch copy of `frontend/src/graph/` (registry.js + Graph.svelte +
consumers/), `src/world_engine/cockpit/index.html`, and
`tooling/verify/{checks,baselines}` under the session scratchpad (never
the working tree). `frontend/src/graph/registry.js`'s `GRAPH_IMPLS` export
was changed from its one `relation_cytoscape` entry to
`Object.freeze({})`. Ran `python tooling/verify/checks/graph_primitive.py`
from the scratch root (the check resolves its `ROOT` from its own file's
path, three parents up, so the scratch copy's relative layout had to
mirror the real repo's for this to be meaningful):

```
FAIL: <scratch>\frontend\src\graph\registry.js: zero GRAPH_IMPLS entries parsed
EXIT CODE: 1
```

Exactly one failure line — no other rule fired (the scratch `index.html`
copy is otherwise untouched, so rules 1/2/7/8/9 all pass on their own
terms). This confirms `_parse_registry()`'s empty-dict guard
(`graph_primitive.py:151-153`) is the sole failure surface for a
zero-entry registry, exactly the line brief -b's amendment must target.

VERDICT: CONFIRMED - deleting the registry's single entry, run for real, fails graph_primitive.py with exactly `FAIL: .../registry.js: zero GRAPH_IMPLS entries parsed` (graph_primitive.py:152, `_parse_registry`'s empty-entries guard) and nothing else; brief -b amends against this observed line, not a reading of the source.

## Escalation

M1 did not refute C2 — the observed-size force layout is both fast
(sub-millisecond) and legible (no overlap, 1 crossing), well inside the
2000ms/legibility gate. **M1's own ESCALATE-AND-STOP clause is not
triggered; Bloc C is constructible and this brief does not stop.**

Two of the nine measurements came back REFUTED, and per this brief's Scope
OUT ("Deciding anything... any closure correction in M4, is reported for
Nia's decision. The executor does not resolve them") both are reported
here, unresolved, for Nia:

- **M4 (LOAD-BEARING for scoping brief -e onward): B2's assumed eleven
  `CREATION_TABS` keys are wrong.** The measured `author*` closure touches
  only eight — `artefacts`, `intrigues`, and `queue` are each independently
  confirmed to never call or be called by `author*` code. This is not a
  minor correction: three of the eleven tabs the ticket's brief list
  (-e..-j) was scoped against do not belong in this ticket's migration
  surface under B2's own stated rule ("the cut follows the call graph").
  Nia needs to re-decide the ticket's boundary — either narrow briefs
  -e..-j to the eight confirmed tabs, or state a different reason
  `artefacts`/`intrigues`/`queue` should migrate alongside the sheet engine
  anyway — before those briefs are written.
- **M5: a Svelte island mounted as a plain child of `#creation-constructeur`
  does not survive a tab switch or a world switch**, both via
  `constructeurRender()`'s unconditional full re-render. This does not
  block brief -d — the fix (mount per activation, reusing `mount.js`'s
  existing stale-node reconciliation) is identified and low-risk — but it
  is a real constraint brief -d must implement against, not assume away.

Three additional non-blocking items are worth Nia's attention when brief
-a's findings are reviewed: `relGraphGlobalNodeDblTap`'s cosmetic
"followed" toggle as a DROP candidate (M2); the fixed-viewport (no
zoom/pan) legibility ceiling observed at 10x synthetic scale (M1) as a
headroom limitation of `Graph.svelte` as it stands today; and the scope
risk that migrating the generic Creation-shell dispatcher (as opposed to
just `author*` and its closure) would mechanically touch code that
`competences`/`registre`/`prompts` also depend on to be dispatched to,
even though none of those three tabs is itself in the `author*` closure
(M4d).
