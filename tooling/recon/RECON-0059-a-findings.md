<!-- slug: periphery-closure-mini-recon -->
# RECON-0059-a — periphery closure mini-RECON findings

Brief: BRIEF-0059-a. Report-only. Measured against the `ticket/0059` working
tree (branched from `main` at `1770f75`, this session, 2026-08-03). No file
under `src/` or `frontend/` was edited to produce this report.

## STOP-RULE TRIGGERED — M4

**The Stop rule (hard) fires.** `_npcAgentTreeHtml` and `_linkAgentTreeHtml`
are **not** a copy-paste of the same behaviour modulo cosmetic renames. They
implement two different selection models:

- `_npcAgentTreeHtml` (`index.html:7463`) renders a **single-select radio**
  tree (`name="npcagent-root"`), backed by `npcAgentSelectedRoot` (a lone
  id). The code's own comment at declaration (`index.html:7377`) says so
  explicitly: `// single root_location_id (C1/S1 — intra-region v1, radio
  not checkbox)`.
- `_linkAgentTreeHtml` (`index.html:7959`) renders a **multi-select
  checkbox** tree, backed by `linkAgentCheckedRoots` (a `Set`), **and**
  `_linkAgentIsChecked` (`index.html:7948`) additionally treats a node as
  checked if **any ancestor** is checked (implicit subtree selection) — a
  behaviour `_npcAgentTreeHtml` has no equivalent of at all.

This is not modulo (a) the radio `name` attribute, (b) the `onchange`
handler name, or (c) the selected-id variable read — the interaction model
itself differs (one root vs. many roots, no inheritance vs. ancestor-implied
checked state). Per the brief: **"If they differ behaviourally, say how and
STOP — lock C1 assumed a copy-paste and a single `LocationTree.svelte`
cannot absorb a real difference silently."**

**No further brief in this chain (`-b` onward) should start until Nia
resolves this.** The rest of this document still reports M1/M2/M3/M5–M8 in
full, since this brief's deliverable is the finding record regardless of the
stop — but TICKET-0059's C1 clause needs an amendment: either
`LocationTree.svelte` grows a `mode: 'single' | 'multi'` prop (with the
ancestor-inheritance behaviour gated on `multi`), or the two pickers stay
separate and C1 is withdrawn. That decision is Nia's, not this brief's.

Both pickers are confirmed to be plain location pickers, not review-tree
consumers — see M4 below for the check.

---

## M1 — `legacyCall(` census

**CONFIRMED exactly.** 20 call sites in 5 files, matching planning RECON's
list line-for-line and name-for-name:

```
frontend/src/creation/Sheet.svelte:167   '_authorResetCreateDrafts'
frontend/src/creation/Sheet.svelte:311   'authorLoadGoals'
frontend/src/creation/Sheet.svelte:317   'authorLoadDiscDetails'
frontend/src/creation/Sheet.svelte:393   'creationRefreshList'
frontend/src/creation/Sheet.svelte:415   '_authorGetPendingCreationMutationId'
frontend/src/creation/Sheet.svelte:465   '_authorConsumePendingCreationMutationId'
frontend/src/creation/Sheet.svelte:474   'creationRefreshList'
frontend/src/creation/Sheet.svelte:475   '_authorNotifySaved'
frontend/src/creation/Sheet.svelte:589   'authorRenderRelations'
frontend/src/creation/Sheet.svelte:590   'authorRenderRelationForm'
frontend/src/creation/Sheet.svelte:593   'authorRenderKnowledge'
frontend/src/creation/Sheet.svelte:594   'authorRenderKnowledgeForm'
frontend/src/creation/Sheet.svelte:640   'authorBackfillGoals'
frontend/src/creation/Sheet.svelte:643   'authorRenderGoalForm'
frontend/src/creation/Sheet.svelte:650   'authorRenderDiscDetailForm'
frontend/src/creation/Region.svelte:311  'creationRefreshList'
frontend/src/creation/RoomBatch.svelte:246 'creationRefreshList'
frontend/src/creation/FactionRoster.svelte:58 'creationOpenEntityFrom'
frontend/src/creation/locationType.js:46 'genericModalOpen'
frontend/src/creation/locationType.js:104 'genericModalClose'
```

`frontend/src/creation/GeneratePanel.svelte:5` mentions `legacyCall` inside a
comment only — confirmed NOT a call site.

### Note — a second, invisible bridge-reach mechanism (relevant to `-b`)

`frontend/src/legacy/bridge.js` implements the actual generic reach into the
legacy window as a **private, unexported** function `callLegacy(fnName,
...args)` (line 24). The exported `legacyCall(...)` (line 153) is only a
thin passthrough — but `callLegacy` is **also** called directly by several
other named exports that never say `legacyCall`:

```
getSelectedCharacterId()  -> callLegacy('authorGetSelectedEntityId')   (bridge.js:123)
selectEntity(id)          -> callLegacy('authorSelectEntity', id)      (bridge.js:136)
selectRecord(tabId, rec)  -> callLegacy('creationSelectRecord', ...)   (bridge.js:140)
showSurface(key)          -> callLegacy(entry.showFn)                  (bridge.js:38)
activateWorldViaLegacy()  -> callLegacy('activateWorld', worldId)      (bridge.js:42)
openWorldCreate()         -> callLegacy('worldCreateOpen')             (bridge.js:46)
openWorldDelete()         -> callLegacy('worldDeleteOpen')             (bridge.js:50)
showCreationTab(tabId)    -> callLegacy('showCreationSubTab', ...)     (bridge.js:95)
```

`getSelectedCharacterId` is called from `frontend/src/graph/consumers/
relations.js:214`; `selectEntity`/`selectRecord` from
`frontend/src/creation/EntityList.svelte:168,172`. **A literal grep for
`legacyCall(` — which is exactly what M1 and (per its own scope) `-b`'s
`legacy_call.py` baseline are defined to do — does not and will not see
these 8 call sites**, because they never spell the string `legacyCall(`.
They reach the identical legacy window through the identical `callLegacy`
primitive, just via a differently-named export.

This does **not** change M1's count (the brief scoped M1 strictly to the
literal string `legacyCall(`, and that count is exactly 20 — no drift, no
Stop trigger on M1 itself). But `-b`'s `legacy_call.py` check, if it also
only greps for the string `legacyCall(`, would be structurally blind to
these 8 sites and to any new one added the same way — a fail-open gap in
the exact seam E1 says must be fail-closed and monotonically shrinking.
**Recommend `-b` either (a) scope `legacy_call.py` to every export of
`legacy/bridge.js` that resolves through `callLegacy` (all 9, including
`legacyCall` itself), or (b) explicitly document why the 8 narrow-named
wrappers are out of scope and add a companion rule closing them somewhere
in the chain.** This is a recommendation, not a Stop trigger — M1's letter
is satisfied — but leaving it unaddressed would let `-b`'s new gate pass
vacuously against a real, present bypass class.

---

## M2 — the residual `author*` cluster

**CONFIRMED exactly.** All 42 listed `author*`/`_author*` declarations exist
in `index.html` at the exact planning-RECON line numbers (spot-verified via
grep against the working tree):

- Relations (6): `authorRenderRelations` (6610), `authorRenderRelationForm`
  (6641), `authorAddRelation` (6670), `authorUpdateRelation` (6682),
  `authorDeleteRelation` (6693), `authorRelationRequest` (6698).
  `RELATION_DIRECTIONS` const at **6639** (planning said "~6638" — off by
  one, confirmed as the same constant, no discrepancy).
- Knowledge (6): `authorRenderKnowledge` (6719), `authorRenderKnowledgeForm`
  (6749), `authorAddKnowledge` (6770), `authorUpdateKnowledge` (6783),
  `authorDeleteKnowledge` (6796), `authorKnowledgeRequest` (6801).
- Goals (13): `authorLoadGoals` (6824), `authorRenderGoals` (6840),
  `authorRenderGoalPrerequisites` (6884), `authorAddGoalPrerequisite`
  (6914), `authorRemoveGoalPrerequisite` (6925), `authorSetGoalPrerequisites`
  (6931), `authorAttachGoalLink` (6946), `authorDetachGoalLink` (6962),
  `authorRenderGoalForm` (6972), `authorAddGoal` (6990),
  `authorSetGoalStatus` (6998), `authorBackfillGoals` (7009),
  `authorGoalRequest` (7039). (`_goalPrereqRawList` at 6907 is a private
  helper, not itself `author*`-prefixed, but is exclusively used by this
  family — noted for whichever brief ports it.)
- Discipline details (9): `authorLoadDiscDetails` (6193),
  `authorRenderDiscDetails` (6204), `authorRenderDiscDetailRow` (6235),
  `authorRenderDiscDetailForm` (6259), `authorAddDiscDetail` (6294),
  `authorDeleteDiscDetail` (6323), `authorResetDiscDetail` (6333),
  `authorEditDiscDetail` (6346), `authorSaveDiscDetail` (6381).
- Lifecycle/shared (8): `authorSelectEntity` (6422), `_authorNotifySaved`
  (6451), `authorDelete` (6592), `_authorGetPendingCreationMutationId`
  (6581), `_authorConsumePendingCreationMutationId` (6587),
  `_authorResetCreateDrafts` (5912), `authorGetSelectedEntityId` (3236),
  `authorAddLedgerEntry` (4801).

6 + 6 + 13 + 9 + 8 = 42. Confirmed.

### Per-family detail (container id / API paths / inline handlers)

- **Relations** — container `#author-relations` (`Sheet.svelte:589`).
  Endpoints: `POST /api/entities/{id}/relations`, `PUT /api/relations/{id}`,
  `DELETE /api/relations/{id}`, plus a re-fetch of `GET
  /api/entities/{id}` after every write. Inline handlers emitted in the
  generated HTML: `onclick="authorUpdateRelation('...')"`,
  `onclick="authorDeleteRelation('...')"` (per-row), `onclick=
  "authorAddRelation()"` (new-row form).
- **Knowledge** — container `#author-knowledge` (`Sheet.svelte:593`).
  Endpoints: `POST /api/entities/{id}/knowledge`, `PUT
  /api/knowledge/{id}`, `DELETE /api/knowledge/{id}`, same
  `GET /api/entities/{id}` re-fetch pattern. Inline handlers:
  `onclick="authorUpdateKnowledge('...')"`,
  `onclick="authorDeleteKnowledge('...')"`, `onclick="authorAddKnowledge()"`.
- **Goals** — container `#author-goals` (`Sheet.svelte:311`/`:640` load
  sites). Endpoints: `GET /api/entities/{id}/goals`, `GET /api/agendas`,
  `PATCH /api/goals/{id}/prerequisites`, `POST /api/goal-agenda-links`,
  `POST /api/goal-agenda-links/{id}/detach`, `POST
  /api/entities/{id}/goals`, `POST /api/goals/{id}/status`, `POST
  /api/npc-goals/backfill`. Inline handlers: `onclick=
  "authorDetachGoalLink('...')"`, `onclick="authorAttachGoalLink('...')"`,
  `onclick="authorSetGoalStatus('...','completed'|'abandoned')"`, `onclick=
  "authorRemoveGoalPrerequisite('...', i)"`, `onclick=
  "authorAddGoalPrerequisite('...')"`, `onclick="authorAddGoal()"`. Also a
  `document.addEventListener('creation:goals-backfilled', ...)` listener
  (line 7033) that re-triggers `authorLoadGoals` when
  `EntityList.svelte`'s already-migrated `backfillNpcGoals` fires — a
  legacy-listens-to-Svelte-event coupling in the opposite direction from
  `legacyCall`, worth `-d` knowing about since it's an extra caller path
  into this family that M1's census (which only looks at Svelte->legacy
  calls) does not surface.
- **Discipline details** — container `#author-disc-list`
  (`Sheet.svelte:317`). Endpoints: `GET/POST
  /api/locations/{id}/discoverable-details`, `PUT`/`DELETE
  /api/discoverable-details/{id}`. Inline handlers: `onclick=
  "authorEditDiscDetail('...','...')"`, `onclick=
  "authorDeleteDiscDetail('...','...')"`, `onclick=
  "authorResetDiscDetail('...','...')"`, `onclick=
  "authorSaveDiscDetail('...','...')"`, `onclick=
  "authorAddDiscDetail('...','...')"`.

---

## M3 — residual functions with callers outside their own family

**CONFIRMED**, with one added precision the planning RECON didn't have: the
mechanism differs per function.

- **`authorSelectEntity`** — reached from `EntityList.svelte:168` via
  `bridge.js`'s dedicated `selectEntity(id)` export (not the generic
  `legacyCall`; see M1's note). Cross-cluster: EntityList is a different
  island than Sheet.
- **`authorGetSelectedEntityId`** — reached from
  `graph/consumers/relations.js:214` via `bridge.js`'s dedicated
  `getSelectedCharacterId()` export. Cross-cluster: the relations-graph
  consumer, not Sheet.
- **`authorDelete`** — has **no** Svelte/bridge caller today. Its only
  caller is the static markup button `#author-delete-btn` in `index.html`
  itself (`onclick="authorDelete()"`, line 1353) — part of the still-legacy
  sheet header shell, not yet reached from any migrated component.
- **`_authorNotifySaved`, `_authorResetCreateDrafts`,
  `_authorGetPendingCreationMutationId`,
  `_authorConsumePendingCreationMutationId`** — all four reached
  exclusively via the generic `legacyCall(...)` from `Sheet.svelte` (already
  enumerated in M1); no caller outside Sheet.
- **`authorAddLedgerEntry`** — **confirmed** to belong to the `registre` tab,
  not the sheet: its only caller is the static markup button at
  `index.html:1468` (`onclick="authorAddLedgerEntry()"`), which lives inside
  the Registre tab's own add-form markup, not inside any entity-sheet
  container. It closes in **`-h`** (competences + registre + artefacts),
  not `-d` (Sheet goals/discipline) — matching the brief's own framing of
  the open question.

---

## M4 — location-tree duplication (lock C1)

See the **STOP** banner at the top of this document for the full
behavioural-difference finding (this is the Stop-rule trigger). Summary of
the checkable facts:

- `_npcAgentTreeHtml`: `index.html:7463-7475` (13 lines). Emits
  `class="linkagent-loc-node"` (yes — literally the `linkagent-` prefixed
  class name on the NPC-agent's own tree node; copy-paste evidence per the
  ticket's own C1 note) wrapping a `<label><input type="radio"
  name="npcagent-root" ...></label>` plus a
  `class="linkagent-loc-children"` wrapper div for the recursive children.
- `_linkAgentTreeHtml`: `index.html:7959-7971` (13 lines). Emits the
  **same** two class names (`linkagent-loc-node`, `linkagent-loc-children`)
  wrapping a `<label><input type="checkbox" ...></label>`.
- CSS: both classes are handled by one shared `<style>` rule set (a single
  `.linkagent-loc-node` / `.linkagent-loc-children` selector pair styles
  both trees identically) — the visual shell IS shared; only the input
  type/selection semantics diverge.
- Neither function, nor its containing NPC-agent/link-agent cluster,
  references `reviewRegister` or `reviewCascade` anywhere — grep across all
  of `index.html` for both identifiers returns zero matches. **Confirmed:**
  both are plain location pickers, not review-tree consumers, exactly as
  planning RECON concluded.

---

## M5 — standalone tab clusters

Planning RECON's per-cluster function *counts* are confirmed accurate for
five of nine buckets and require correction for the rest, where the bucket
boundary bundles more than the tab's own logic. Reported per-cluster below
with the concrete function list, container id(s), `CREATION_TABS` fields,
and the endpoints touched. **No cross-read between Play and Creation was
found for any function in any cluster — the Stop-rule condition for M5 does
NOT fire.**

- **`competences`** — **CONFIRMED, 12 fns**, `4222`-`4765`:
  `_competencesWorldReset` (4222), `competencesGenerateDraft` (4599),
  `_competencesDomainOptions` (4627), `competencesRenderDraft` (4633),
  `competencesDiscardDraftRow` (4660), `competencesAcceptDraftRow` (4665),
  `competencesAddManualRow` (4688), `competencesLoadList` (4693),
  `_competencesRenderTable` (4704), `competencesSaveRow` (4729),
  `competencesDeleteOpen` (4751), `competencesDeleteConfirm` (4765).
  Container: `creation-competences`. `CREATION_TABS.competences`:
  `archetype:'bespoke'`, `loader: competencesLoadList`, `state.onWorldSwitch:
  _competencesWorldReset`, `primaryAction: competencesAddManualRow`.
  Endpoints: `POST /api/skill-definitions/generate`, `POST
  /api/skill-definitions`, `GET /api/skill-definitions`, `PUT`/`DELETE
  /api/skill-definitions/{id}`.
- **`registre`** — **CORRECTED**: planning said 5 fns; the tab-owned
  functions are indeed 5 (`_registreWorldReset` 4224,
  `_registrePopulateEntityFilter` 4782, `registreToggleAddForm` 4839,
  `loadRegistre` 4844, `_registreRenderTable` 4863) — `authorAddLedgerEntry`
  (4801) sits physically between them but is tallied under M2/M3's
  author-cluster count instead (see M3: it belongs here functionally, but
  is a different family for counting purposes — 5 + 1 shared = 6 functions
  actually execute this tab). Container: `creation-registre`.
  `CREATION_TABS.registre`: `archetype:'bespoke'`, `loader: loadRegistre`,
  `state.onWorldSwitch: _registreWorldReset`, `primaryAction:
  registreToggleAddForm`. Endpoints: `GET /api/entities`, `POST
  /api/ledger`, `GET /api/ledger[?params]`.
- **`artefacts`** — **CONFIRMED, 1 fn**, `loadCreationArtefacts` (5203).
  Container: `creation-artefacts`. `CREATION_TABS.artefacts`:
  `archetype:'entity'` (comment: "degenerate: no create control"), `loader:
  loadCreationArtefacts`, `primaryAction: null`. Endpoint: `GET
  /api/entities?type=artifact`.
- **`intrigues`** — **CONFIRMED, 13 fns**, `4226`-`5157`:
  `_intriguesTabEnterReset` (4226), `_intriguesPopulateOwnerSelect` (4892),
  `loadAgendasList` (4915), `_intriguesRenderStep` (4925),
  `_intriguesRenderLinkedGoal` (4948), `renderAgendaSheet` (4964),
  `_intriguesRefreshSelection` (5008), `intriguesSetAgendaStatus` (5014),
  `intriguesDetachLink` (5035), `intriguesStepStatus` (5045),
  `intriguesRenderCreatePanel` (5062), `intriguesGenerateDraft` (5115),
  `intriguesSubmitCreate` (5157). Container: `creation-editor-area`
  (`archetype:'entity'`, shared shell) — `sheetRenderer: renderAgendaSheet`,
  `createPanel: intriguesRenderCreatePanel` (bespoke, per D-0059's own note
  this stays legacy). Endpoints: `GET /api/entities?type=faction|character`,
  `GET/POST /api/agendas`, `PATCH /api/agendas/{id}`, `POST
  /api/goal-agenda-links/{id}/detach`, `PATCH /api/agenda-steps/{id}`, `POST
  /api/agendas/generate`.
- **`pj`/`pc`/`skill`** — **CONFIRMED, 12 fns**, `7069`-`7342` (note: `pj`
  and `pc`/`skill` are not three separate tabs — only `pj` is a
  `CREATION_TABS` key/static `#ctab-pj` button; `pc` (player-character
  create flow) and `skill` (the Fiche/skill-sheet slot) are sub-features
  reached inside `pj`'s `createPanel`/`slots`, not independent tabs):
  `skillInit` (7069), `pcCreateLoadLocations` (7079), `pcCreateSubmit`
  (7095), `pjRenderCreatePanel` (7170), `pjFicheOnSelect` (7235),
  `pcRenderDraftKnowledge` (7241), `pcGenerateDraft` (7253), `pcApplyDraft`
  (7273), `skillLoadCharacters` (7283), `skillSelectCharacter` (7303),
  `skillRender` (7316), `skillSaveTier` (7342). `CREATION_TABS.pj`:
  `createPanel: pjRenderCreatePanel`, `slots: [{id:'fiche',
  containerId:'creation-pj-skill', loader: skillInit, onSelect:
  pjFicheOnSelect}]`. Endpoints: `GET /api/entities?type=location`, `POST
  /api/characters/player`, `POST /api/characters/player/generate`, `GET
  /api/skills/player-characters`, `GET /api/skills?character_id=...`, `PUT
  /api/skills/{id}`.
- **`queue` + mutation review** — **CORRECTED, materially**: planning
  RECON's span `2079..3132` is wrong on both ends and its "13 fns" figure
  undercounts by roughly half. The actual Review-queue section is delimited
  by its own comment header at `index.html:2748` ("Review queue") through
  the "Card helpers" section ending at `markCardDone`'s close
  (`index.html:3220`); the section immediately before it (`2079`-`2747`) is
  **entirely Play-scene code** (target selector, transcript rendering,
  scene join/travel, tick controls) with **zero** queue/mutation functions
  interleaved into it — there is no literal interleaving of the two
  clusters' function bodies, contrary to the planning note. The actual
  queue/mutation-review function list, all confirmed **Creation/Queue-only**
  by caller trace (none read from any Play code path):
  `setFilter` (2752), `setFilterByName` (2760), `_loadMutationEntityNames`
  (2773), `_mutationEntityName` (2783), `_loadMutationAgendaNames` (2793),
  `_mutationAgendaName` (2803), `loadQueue` (2809), `renderBatchBar` (2839),
  `_renderResourceChangeLegs` (2857), `_renderAgendaProvenanceSummary`
  (2896), `renderCard` (2923), `doApprove` (3017), `doReject` (3066),
  `getSelectedMutationIds` (3093), `toggleSelectAll` (3099),
  `updateBatchBar` (3107), `hideBatchVerdict` (3127), `showBatchVerdict`
  (3132), `doBatchAction` (3141), `showResult` (3174), `lockCard` (3180),
  `unlockCard` (3185), `markCardDone` (3191) — **23 functions**, not 13.
  `showResult`/`lockCard`/`unlockCard`/`markCardDone` ("Card helpers",
  3170-3220) are called only from `doApprove`/`doReject`/`doBatchAction` —
  confirmed queue-private, not a shared Play/Creation helper despite the
  generic-sounding names. **No Stop trigger**: nothing in this list is
  called from Play. Container: `creation-queue`, plus
  `creation-shell-extra` (the filter-bar/tick-controls/batch-bar slot,
  `CREATION_TABS.queue.slots[0]`). Endpoints: `GET
  /api/mutations?status=...`, `POST /api/mutations/{id}/approve`, `POST
  /api/mutations/{id}/reject`, `POST /api/mutations/batch-review`, `POST
  /api/world-tick`.
- **`prompts`** — **CONFIRMED, 31 fns**, `5256`-`5854`, **with one
  clarifying note**: the raw line range also contains 3 more functions
  (`cwLoadConfig` 5323, `_cwRenderConfig` 5334, `cwPatchField` 5359) that
  planning RECON's "31" figure excludes. These implement the "Fenêtre de
  conversation" (conversation-window) config panel, which is rendered
  *inside* the Prompts tab (`promptsLoadList` calls `cwLoadConfig()` at
  line 5304) but is a **functionally distinct, world-level config surface**
  parked here only per the code's own comment: "N2, until a dedicated
  world-configuration surface exists (named deferral D-0050)". 31 (prompt
  editing proper) + 3 (`cw*`) = 34 functions physically in the range.
  Container: `creation-prompts`. `CREATION_TABS.prompts`: `archetype:
  'bespoke'`, `loader: promptsLoadList`, `state.onWorldSwitch:
  _promptsWorldReset`, `primaryAction: null` (read-only management
  surface). Endpoints: `GET /api/ollama/models`, `GET/PATCH
  /api/prompts[...]`, `GET/PATCH /api/conversation-window-config`, `GET
  /api/prompts/{id}/versions[...]`, `POST
  /api/prompts/{id}/versions/{n}/restore`, `GET
  /api/prompts/preview/{usage}`. **`-i` (the brief scoped to `prompts`)
  needs to decide whether `cw*` migrates with it or is carved out** — it is
  currently undecided and not named in the ticket's brief-chain table.
- **`world*`** — **CONFIRMED, 6 fns**, `8400`-`8513`: `worldCreateOpen`
  (8400), `worldCreateSubmit` (8431), `worldGenerateDraft` (8456),
  `worldApplyDraft` (8476), `worldDeleteOpen` (8494),
  `worldDeleteConfirm` (8513). **Note**: `loadWorldSelector` (8349) and
  `activateWorld` (8364) sit immediately before this range and are
  functionally adjacent (world switcher / world activation) but are
  correctly excluded from the "6" — they are shell-header / chrome
  concerns reached on every boot and every tab, not part of the
  create/delete CRUD surface `world*` denotes here; see M6, they are part
  of the chrome inventory instead. Endpoints: `GET /api/worlds`, `POST
  /api/worlds/{id}/activate`, `POST /api/worlds`, `POST
  /api/worlds/generate`, `DELETE /api/worlds/{id}`.
- **`npcAgent`** — **CONFIRMED, 29 fns**, `7395`-`7811` (one extra:
  `npcAgentSelectRoot` at 7477 belongs to the tree-picker, counted here).
  **`linkAgent`** — **CONFIRMED, 27 fns**, `7882`-`8280`. Both slot onto
  `CREATION_TABS.npc.slots[0]` (`relgraph`, `onOpen:
  npcAgentCheckOpenBatch(); linkAgentCheckOpenBatch()`) — i.e. both agents
  are launched from the **npc** tab's on-demand relation-graph slot, not
  their own top-level tab. Endpoints enumerated inline in M5 already
  covered by the api() census (all `/api/npc-batches/...` and
  `/api/link-batches/...` paths).
- **`chrome`** — see M6 (the count and boundary don't cleanly reconcile to
  a flat 18-in-one-span; reported there instead of duplicated here).

---

## M6 — chrome inventory (lock D1)

- `#creation-view` opens at `index.html:1209`, closes `1517`.
- 14 static `#ctab-*` buttons, `index.html:1213-1226`, one per
  `CREATION_TABS` key, in this order: `npc`, `pj`, `lieux`, `factions`,
  `objets`, `competences`, `region`, `constructeur`, `artefacts`,
  `registre`, `intrigues`, `evenements`, `queue`, `prompts`.
- Shell band markup, `index.html:1235-1275`: `#creation-shell-band` >
  `#creation-shell-title`, `#creation-shell-extra` (queue's filter-bar +
  tick-controls + batch-bar relocation slot), `#creation-shell-toggles`
  (on-demand slot toggles), `#creation-shell-action` (the one primaryAction
  button).
- `const CREATION_TABS = {` at **`index.html:4260`**, closing `4421` (161
  lines, 14 entries — exhaustively read this session, matches the buttons
  above 1:1). Every entry declares `label`, `archetype`, `containers`,
  `loader`, `state` (`onTabEnter`/`onWorldSwitch`), `primaryAction`; entity
  archetypes additionally declare `islands`/`type`/`entityFilter`/
  `createPanel`/`showPendingCreations`/`slots`.
- `_buildRuntimeCreationTabs` at **5940**, `refreshCreationTabs` at
  **5979** — both confirmed present at the planning-RECON line numbers.
  `_buildRuntimeCreationTabs` fetches `GET /api/entity-types` (assigned to
  `authorRegistry`, same call `creationInit` also makes at 5988).
- `route:subtab` custom-event dispatch at **`index.html:4533`**, confirmed.
- Chrome function inventory (the mechanism — tab-switch/dispatch/registry/
  world-activation — as opposed to any one tab's own content): `showPlayView`
  (3293), `showCreationView` (3302), `showPlaySubTab` (3330),
  `_onDemandSlotReset` (4114), `_onDemandSlotToggle` (4123),
  `_onDemandSlotToggleById` (4149), `_renderOnDemandToggles` (4158),
  `creationRefreshList` (4432), `_creationActivateTab` (4457),
  `showCreationSubTab` (4485), `renderCreationShell` (4540),
  `_islandPrimaryAction` (4562), `_creationRunWorldSwitchResets` (4571),
  `_buildRuntimeCreationTabs` (5940), `refreshCreationTabs` (5979),
  `creationInit` (5986), `loadWorldSelector` (8349), `activateWorld`
  (8364) — **18 functions**, matching planning RECON's "18 fns" count.
  **Correction**: the count is right but the claimed span `3302..6560` is
  not a tight bound — 4 of the 18 (`showPlayView` at 3293,
  `loadWorldSelector` at 8349, `activateWorld` at 8364, plus
  `showObservationView`/`showCreationView` sit right at the boundary) fall
  outside that range; the chrome cluster is scattered across the file
  (3293-8364), not contained in one contiguous span. `showObservationView`
  (3318) is adjacent but NOT counted as chrome (it's the Observation
  view-switch, a sibling top-level view, not a Creation concern).

### `document.getElementById` reaching the legacy document from `frontend/src/creation/*`

**Zero** such call sites exist. A grep across every file under
`frontend/src/creation/` for `document.getElementById(` returns exactly one
hit, and it is prose inside a comment (`Sheet.svelte:24`, describing how the
*legacy* functions Sheet.svelte calls into behave once invoked — not a
Svelte-side DOM read). The only mechanism by which `frontend/src/creation/*`
reaches into the legacy document is the sanctioned, already-declared
island-mount seam: `frontend/src/creation/mount.js` calls
`legacyContainer(entry.containerId)` (bridge.js's own accessor) at two call
sites (`mount.js:63`, `:134`) to resolve each island's own mount point —
this is the `island:slot` mechanism `creation_island.py` already governs,
not a new or hidden binding. **Confirmed: no invisible bindings beyond the
already-documented mount mechanism exist today** — this part of M6 is a
clean pass, nothing for the chrome inversion to sever that isn't already
known.

---

## M7 — check anchoring

All eight named checks read `INDEX_HTML = ROOT / "src" / "world_engine" /
"cockpit" / "index.html"` via `ROOT = pathlib.Path(__file__).resolve()
.parents[3]`, and all use the same vacuous-proof idiom: a module-level
`FAILURES: list[str]`, a `fail()` appender, and either an explicit
`_report_and_exit()` helper or (in `page_contract.py`'s slightly older
form) an inline `if failures: ... return 1` — zero assertions/rules
evaluated is itself a failure in every one of them (`_ASSERTIONS_EVALUATED`
counters in the `-c`/`-d`-era checks, `rules_evaluated` in
`review_component.py`, explicit "zero collected" failures in
`creation_island.py` / `graph_primitive.py`).

Per-check disposition (does this ticket's migration retarget it, and does
the chain name a brief for that):

- **`page_contract.py`** — reads `TAB_KEYS` (14, matches M6), the
  `CREATION_TABS` literal, `showCreationSubTab`, `_creationActivateTab`,
  `_buildRuntimeCreationTabs`, `creationInit`, plus several literal-string
  assertions, ALL against `index.html`. Every one of these targets moves at
  brief **`-l`** per D1 ("page_contract.py re-anchors onto tabs.js plus the
  new Creation.svelte") — **named**, ticket acceptance list is explicit.
- **`creation_return_nav.py`** — reads `creationReturnTo`,
  `showCreationSubTab`, `creationOpenEntityFrom`, `creationResolveEntityTab`,
  `_creationRunWorldSwitchResets` (all chrome-cluster, index.html) plus
  `FactionRoster.svelte` (already fine). Every index.html anchor here is
  chrome, moving at **`-l`** — covered by the ticket's generic
  "re-anchored... in the same commit as the surface it guards" clause.
  **Named** (generically, via the chrome-inversion brief).
  Confirmed still valid until brief `-l` lands.
- **`faction_roster_panel.py`** — its function-body assertions already
  target `Sheet.svelte`, `factionPanel.svelte.js`, `FactionRoster.svelte`
  (moved by TICKET-0058); its only remaining `index.html` dependency is a
  trivial literal-absence scan (`'Membres (lecture seule)' not in html`),
  which names no function scheduled to move. **Does not need re-homing by
  this ticket at all** — a genuine "nothing to do here" result, worth
  confirming so `-l` doesn't spend effort on it.
- **`review_component.py`** — rule 6a scans **every** function name index.html
  currently has (`re.findall(r"function\s+(\w+)\s*\(", html)`), generic over
  whatever set that is; not anchored to any named function this ticket
  moves. **Self-adapting, no re-home needed.**
- **`schema_0024.py`** — two literal-absence substring checks against
  `index.html` (`'detail.metadata.roles'`/`'entityData.metadata.roles'`,
  `'role-capacities'`/`'authorFactionCapacitiesDraft'`) for already-dead
  code; names no function this ticket's chain touches. **No re-home
  needed.**
- **`legacy_mount.py`** — generic over whatever `LEGACY_MOUNTS` registry
  entries exist; the `creation` mount's removal (brief `-l`, per ticket
  acceptance: "`LEGACY_MOUNTS` no longer contains `creation`;
  `legacy_mounts.baseline` shrinks to `observation` + `play`") is a **data**
  change to `frontend/src/legacy/registry.js` +
  `legacy_mounts.baseline`, not a change to `legacy_mount.py`'s own code.
  **Named** (as a data update, at `-l`), check mechanism itself untouched.
- **`creation_island.py`** — rules 4/5/9/10/11 are all anchored on the
  `CREATION_TABS` literal, `_creationActivateTab`, and `creationRefreshList`
  living in `index.html` — the exact structures D1 says move to
  `frontend/src/creation/tabs.js` + `Creation.svelte` at brief `-l`. **This
  check is NOT explicitly named** in the ticket's re-homing text (only
  rule 7's *mechanism* — "zero `function <prefix>...(` declarations" — is
  named in the acceptance list, and that rule alone survives the move
  intact since it only scans for retired prefixes, not the registry
  literal). Rules 4/5/9/10/11 will hard-fail the moment `-l` empties
  `CREATION_TABS` out of `index.html`, unless `-l`'s scope is read to
  include rewriting them (a plausible reading of the chain table's generic
  "chrome inversion, mount retirement, **check re-homing**" label for
  `-l`). **Flagging this explicitly for `-l`'s author** — it is not a
  Stop-rule trigger (the generic label plausibly covers it, so the chain
  does "name" a re-homing brief for it, just not by this check's name) but
  it is easy to miss since no acceptance-criteria line spells out
  `creation_island.py` the way it spells out `page_contract.py`.
- **`graph_primitive.py`** — rule 9 already collects `graph: {...}` specs
  from **both** `index.html` and `frontend/src/creation/` (a dual-locus
  design, per its own BRIEF-0058-i note); rule 1's `GONE_PLAIN` list is a
  data list extended in the same commit as whichever brief retires a
  cluster's functions (its own docstring: "TICKET-0058 (BRIEF-0058-c) grew
  the list again"). `-f`/`-g` (npcAgent/linkAgent islands) will need to
  extend `GONE_PLAIN` with their retired function names in those same
  commits. **Self-adapting, no structural re-home; a data-list update per
  migrating brief**, same pattern as `legacy_mount.py`.

**No check was found anchored on `index.html` that the chain fails to cover
at all** — `creation_island.py` is the one soft gap (covered only by a
generic label, not a named line), reported above; everything else is
either explicitly named or structurally self-adapting. **M7's Stop-rule
condition does not fire.**

---

## M8 — module budget headroom

**CORRECTED**: `frontend/src/creation/` holds **33 files**, not "30" as
stated in the ticket's intake text (verified via `find frontend/src/creation
-type f`, this session). Full line counts, smallest to largest:

```
    14 subcultureDraft.svelte.js        99 DoorsEditor.svelte
    19 PendingGoalsEditor.svelte       109 locationType.js
    29 fields.js                      114 GeometryEditor.svelte
    35 eventDraft.svelte.js           129 factionPanel.svelte.js
    37 pendingDrafts.svelte.js        140 MembershipsPanel.svelte
    39 ItemsPanel.svelte              140 generatePanel.svelte.js
    42 PendingKnowledgeEditor.svelte  140 mount.js
    50 state.svelte.js                149 Constructeur.svelte
    57 roomBatch.svelte.js            156 Evenements.svelte
    64 LedgerPanel.svelte             160 RolesEditor.svelte
    65 review/registry.js             178 FactionRoster.svelte
    67 RoleRow.svelte                 191 registry.js
    79 GeneratePanel.svelte           353 EntityList.svelte
    82 PricingEditor.svelte           447 RoomBatch.svelte
    89 Field.svelte                   650 Region.svelte
    89 Review.svelte                  656 Sheet.svelte
    93 SubcultureEditor.svelte
```

`src/world_engine/cockpit/index.html` is **8903 lines** (`wc -l`, matches
the ticket's own figure exactly).

**Headroom flag (load-bearing for `-c`/`-d`)**: `Sheet.svelte` is currently
**656** lines — not yet within 150 of the 1000-line module budget (R5), but
the brief chain's own estimates put `-c` at ~230 lines and `-d` at ~400
lines, **both landing inside Sheet.svelte** per the ticket's brief-chain
table ("Sheet sub-editors: relations + knowledge" / "... goals +
discipline details"). 656 + 230 = **886** (already inside the 150-line
flag zone) and 656 + 230 + 400 = **1286** — **over the 1000-line cap**
before `-d` even closes, if the four sub-editors are inlined directly into
`Sheet.svelte` rather than extracted into their own component files (the
same pattern `factionPanel.svelte.js`/`FactionRoster.svelte` already
established for the faction roster in TICKET-0058). **Recommend `-c` and
`-d` each extract their sub-editor(s) into sibling files (e.g.
`RelationsEditor.svelte`/`relationsPanel.svelte.js`,
`KnowledgeEditor.svelte`, `GoalsEditor.svelte`,
`DiscDetailsEditor.svelte`) rather than growing `Sheet.svelte` directly** —
this is a recommendation for those briefs' authors, not a blocker for this
one.

**`module_budget.py` does NOT cover `frontend/src/`** — confirmed by
reading the check: it is AST-based (Python's `ast` module), globs only
`SRC.rglob("*.py")` where `SRC = ROOT / "src"`, and has no code path that
touches `.svelte`/`.js` files at all. The 1000-line budget is presently a
**doctrinal convention only** for frontend files — nothing in the G1 gate
would catch `Sheet.svelte` crossing 1000 lines. This is worth a decision at
`-c`/`-d` time (extract, or accept the check gap) but is not itself a gap
this brief is scoped to close.

---

## Done-means checklist

- [x] `tooling/briefs/RECON-0059-a-findings.md` exists and contains M1..M8,
      each with `file:line` anchors read this session.
- [x] `git status` will show exactly one added file and zero modified files
      (verified before commit).
- [x] Every planning-RECON figure quoted in Scope IN is explicitly marked
      CONFIRMED or CORRECTED above — none left unaddressed.
- [x] Every M4 and M7 question is answered with a yes/no, not a hedge: M4 —
      **yes**, they differ behaviourally (STOP fires); the review-component
      question — **no**, neither is a consumer. M7 — **no** check is left
      uncovered by the chain (one soft gap flagged for `-l`'s attention).
- [x] The Stop-rule trigger (M4) is reported at the top of this document;
      **no further brief in this chain is started** as a result of this
      session's execution of BRIEF-0059-a.
