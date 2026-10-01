<!-- slug: plus-lot -->
# BRIEF 0100-B — "« + lot » beside « + Nouveau »"

Lot: LOT-0100-lieux-tree-graph.md (authoritative on conflict)
Depends on: BRIEF-0100-A (textually only: both append to `ARCHITECTURE_DECISIONS.md`)
Commit header for decisions: `(BRIEF-0100-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0100`, on the tree BRIEF-0100-A left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `frontend/src/creation/tabs.js:185-192` → the `secondaryAction: { label, handler } | undefined (TICKET-0099, G1) --` contract comment, whose third line ends `page that creates two kinds of record. Its handler calls`
- `frontend/src/creation/tabs.js:228` → `  lieux: {`, with `containers: ['creation-editor-area', 'batch-panel-wrap'],`, `primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },` and no `secondaryAction`
- `frontend/src/creation/tabs.js:277` → `    secondaryAction: { label: '+ Ajouter un système', handler: () => triggerPrimaryAction('entitySheet', 'system') },`
- `frontend/src/creation/mount.js:134` → `export function triggerPrimaryAction(key, variant) {`, calling `existing.instance.primaryAction(variant);`
- `frontend/src/creation/Creation.svelte:113` → `    {#if activeEntry?.primaryAction && activeEntry?.secondaryAction}`
- `frontend/src/creation/Sheet.svelte:104` → `  import PjCreatePanel from './PjCreatePanel.svelte';`; `:132` → `    competences: 'Sélectionner une compétence',`; `:214` → `  export function primaryAction(variant) {`, whose body is six `reset…()` calls, `enterCreateMode(...)`, then the competences `blankRecord(variant)` line; `:228` → `  legacyDoc.addEventListener('creation:sheet-reset', () => {`
- `frontend/src/creation/roomBatch.svelte.js:52` → `export function openRoomBatch(anchorId, anchorName) {`
- `tooling/verify/checks/creation_island.py:952` → `def _rule11b_secondary(tabs_src: str) -> int:`
- `grep -rn "'batch')" frontend/src/creation` → no output

## Facts carried

### R-07 — the `secondaryAction` seam [M]
Opened: `frontend/src/creation/tabs.js:185-192` (the contract comment:
"a page that creates two kinds of record"), `:228-243` (`lieux`:
`primaryAction` routed through `triggerPrimaryAction('entitySheet')`, no
`secondaryAction`), `:277` (Compétences' `secondaryAction`, variant
`'system'`); `frontend/src/creation/mount.js:134-143`
(`triggerPrimaryAction(key, variant)` → `instance.primaryAction(variant)`);
`frontend/src/creation/Creation.svelte:113-115` (the band renders the
secondary button before the primary one when both exist);
`tooling/verify/checks/creation_island.py:952-982` (rule 11b: two string
literals, the same key as the routed primary, zero paired is a failure);
`frontend/src/creation/Sheet.svelte:214-226` (`primaryAction(variant)`:
resets six drafts, `enterCreateMode(...)`, then `blankRecord(variant)` for
a competences fiche only).
Finding: any variant reaches `Sheet.svelte`, which always enters create
mode today.
Consequence: B adds a `'batch'` variant that returns before the resets
(C-03); rule 11b counts 2 paired.

### R-08 — the room batch and its only trigger [M]
Opened: `frontend/src/creation/roomBatch.svelte.js:52-57`
(`export function openRoomBatch(anchorId, anchorName)`: reset, `open =
true`, anchor id and name); `frontend/src/creation/registry.js:323`
(`batch` island); `frontend/src/creation/Creation.svelte:131`
(`#batch-panel-wrap`); `tabs.js:231` (`lieux.containers` lists
`batch-panel-wrap`); `EntityList.svelte:345` (« Générer un lot ici »,
`openRoomBatch(lieuxParentId, <breadcrumb's last name>)`, disabled at the
root).
Finding: one caller (E2). The panel is visible whenever Lieux is.
Consequence: B gives the generator a second caller before C deletes the
first.

### R-09 — what the fiche holds [M]
Opened: `frontend/src/creation/sheetState.svelte.js:109-124` (as R-05);
`src/world_engine/cockpit/crud/entities.py:229-240` (`_entity_dict`:
`id`, `world_id`, `type`, `name`, `internal_name`, `is_public`, `status`,
two timestamps), `:486-508` (`get_entity` adds `extension`, `relations`,
`knowledge`, and for a location `geometry`, `doors`);
`Sheet.svelte:185-190` (`enterCreateMode`: `sheetIsNew = true`,
`sheetDetail = {}`); `Creation.svelte:219` (`#author-status`);
`Sheet.svelte:447, 482, 505, 509, 526, 615, 635` (every error in the fiche:
`statusEl.className = 'author-status err'; statusEl.textContent = …`).
Finding: a saved location open in the fiche is `sheetType === 'location'`,
`sheetIsNew === false`, `sheetDetail.id`/`.name` set.
Consequence: C-03's anchor test, and its message in the fiche's own status
line, in the fiche's own error idiom.

### R-17 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:14-17` (`STRICT_HEADER`:
`^## .+ \(BRIEF-\d{4}(-[a-z])?…, (schema v\d+\.\d+|no schema change)\)$`);
`tooling/standards/ARCHITECTURE_DECISIONS.md:17424-17426` (the footer
`---` / `*Co-built with Claude, June 2026.*`), `:17407-17421` (TICKET-0099's
G1 entry, whose last paragraph records G2's reactivation: "when a second
tab asks for a second button"); `tooling/glue/gen_decisions_index.py`
(regenerates `DECISIONS_INDEX.md`).
Consequence: each brief appends one entry above the footer and regenerates
the index; B's entry records that G2's condition fired and how it was
answered.

## Contracts

### C-03 — `Sheet.svelte`'s `primaryAction(variant)` (family)
Produced by: TICKET-0099 (none, `'system'`), B (`'batch'`)   Consumed by: B
| variant | effect |
|---|---|
| none | resets the six drafts, `enterCreateMode(<tab's type>)`; a competences fiche gets `blankRecord()` |
| `'system'` | same; a competences fiche gets `blankRecord('system')` |
| `'batch'` | returns BEFORE the resets: the fiche is untouched. When `sheetType === 'location'`, `!sheetIsNew` and `sheetDetail.id`: `openRoomBatch(sheetDetail.id, sheetDetail.name \|\| '')`. Otherwise `#author-status` gets class `author-status err` and the text `BATCH_NEEDS_LOCATION` = « Ouvrez un lieu pour y générer un lot. » |
Written before B's member; re-read after it.

### C-04 — Lieux' `secondaryAction`
Produced by: B   Consumed by: `Creation.svelte` (band), `creation_island.py` rule 11b
`CREATION_TABS.lieux.secondaryAction = { label: '+ lot', handler: () =>
triggerPrimaryAction('entitySheet', 'batch') }`, declared right after
`lieux.primaryAction`. The band renders « + lot » then « + Nouveau ».

## Context

The room batch generator is reachable today only from the Lieux list's descent view (« Générer un lot ici »), which brief C removes. Nia locked F1 + F-a: a « + lot » button beside « + Nouveau », routed like Compétences' second button, anchored on the location open in the fiche. This brief lands before C so the generator is never unreachable.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `Sheet.svelte`: imports `openRoomBatch`; adds `BATCH_NEEDS_LOCATION`; `primaryAction('batch')` returns into `openBatchOnOpenLocation()` before any reset (C-03); the doc comment names the new variant;
   - `tabs.js`: `CREATION_TABS.lieux.secondaryAction` (C-04); the `secondaryAction` contract comment names the second use;
   - the decision entry above the footer, which also records that TICKET-0099's G2 condition fired and how it was answered.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutation, run then restored with `git checkout -- frontend/src/creation/tabs.js` before committing:
   - `triggerPrimaryAction('entitySheet', 'batch')` → `triggerPrimaryAction('entitySheet')`: `creation_island.py` prints `FAIL: CREATION_TABS.lieux: secondaryAction.handler does not call triggerPrimaryAction('<key>', '<variant>') with two string literals`.
5. Commit message: `feat(creation): + lot beside + Nouveau on Lieux (BRIEF-0100-b)`.

````diff
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 6248b12..e2fb62c 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -102,6 +102,7 @@
   import CompetencesSheet from './CompetencesSheet.svelte';
   import { blankRecord, competenceSheetTitle, saveCompetenceRecord } from './competences.svelte.js';
   import PjCreatePanel from './PjCreatePanel.svelte';
+  import { openRoomBatch } from './roomBatch.svelte.js';
   import RelationsEditor from './RelationsEditor.svelte';
   import KnowledgeEditor from './KnowledgeEditor.svelte';
   import GoalsEditor from './GoalsEditor.svelte';
@@ -131,6 +132,7 @@
     evenements: 'Sélectionner un événement',
     competences: 'Sélectionner une compétence',
   };
+  const BATCH_NEEDS_LOCATION = 'Ouvrez un lieu pour y générer un lot.';
 
   let registry = $state(null);
 
@@ -198,8 +200,8 @@
 
   /** TICKET-0099 (G1): `variant` is what a secondaryAction button passes
    *  through triggerPrimaryAction ('system' for Compétences' second
-   *  button); the primary button passes none, and only a competences
-   *  fiche reads it.
+   *  button, 'batch' for Lieux' « + lot », TICKET-0100); the primary
+   *  button passes none.
    *
    *  Called by mount.js's _islandPrimaryAction('entitySheet') when the
    *  standard shell action band ("+ Nouveau"/"+ Nouvelle intrigue") is
@@ -212,6 +214,13 @@
    *  (the plain "+ Nouveau" idiom every entity tab shared before this
    *  brief), via the same legacy helper so the two paths never drift. */
   export function primaryAction(variant) {
+    // TICKET-0100 (BRIEF-0100-b, F-a): Lieux' « + lot » button opens no
+    // blank record -- it anchors the room batch generator on the location
+    // this fiche shows, and leaves the fiche untouched.
+    if (variant === 'batch') {
+      openBatchOnOpenLocation();
+      return;
+    }
     resetCreateDrafts();
     resetDraftRoles();
     resetFactsDraft();
@@ -225,6 +234,19 @@
     if (creationState.sheetType === 'competences') creationState.sheetDetail = blankRecord(variant);
   }
 
+  /** TICKET-0100 (BRIEF-0100-b): the room batch's anchor is the location
+   *  open in this fiche -- a saved one, never a create-mode draft. With no
+   *  such location, the fiche's status line says so and nothing opens. */
+  function openBatchOnOpenLocation() {
+    const detail = creationState.sheetDetail;
+    if (creationState.sheetType === 'location' && !creationState.sheetIsNew && detail?.id) {
+      openRoomBatch(detail.id, detail.name || '');
+      return;
+    }
+    const statusEl = legacyDoc.getElementById('author-status');
+    if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = BATCH_NEEDS_LOCATION; }
+  }
+
   legacyDoc.addEventListener('creation:sheet-reset', () => {
     resetCreateDrafts();
     flushSync(() => {
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 9444fc6..458feab 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -184,7 +184,9 @@ async function api(path, options) {
 //                 the same side (creation_island.py rule 11).
 //   secondaryAction: { label, handler } | undefined (TICKET-0099, G1) --
 //                 a second shell-band button beside the primary one, for a
-//                 page that creates two kinds of record. Its handler calls
+//                 page that creates two kinds of record (Compétences), or
+//                 that launches a generator on the open record (Lieux'
+//                 « + lot », TICKET-0100). Its handler calls
 //                 triggerPrimaryAction with the SAME island key as
 //                 primaryAction plus a literal variant string, which that
 //                 component's exported primaryAction(variant) receives;
@@ -235,6 +237,7 @@ export const CREATION_TABS = {
     type: 'location',
     createPanel: null,
     primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('entitySheet') },
+    secondaryAction: { label: '+ lot', handler: () => triggerPrimaryAction('entitySheet', 'batch') },
     showPendingCreations: true,
     slots: [{ id: 'graph', containerId: 'creation-lieux-graph', loader: null, onSelect: null,
               display: 'on_demand', toggleLabel: 'Voir le graphe',
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 42cf9d3..3532d29 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17436,6 +17436,28 @@ click opens that location's fiche through `sheetState.svelte.js`'s
 **Rejected.** G2, fixing the Lieux consumer only: the defect sits in the
 shared primitive, and the relations graph's « Lier » arm stayed broken.
 
+## « + LOT » BESIDE « + NOUVEAU » (TICKET-0100) -- THE ROOM BATCH ON THE OPEN LOCATION (BRIEF-0100-b, no schema change)
+
+**F1 + F-a.** The room batch generator used to be reachable only from the
+Lieux list's descent view (« Générer un lot ici », anchored on the location
+descended into). Lieux now declares a `secondaryAction` « + lot »
+(TICKET-0099's G1 field), routed like every secondary action:
+`triggerPrimaryAction('entitySheet', 'batch')`. `Sheet.svelte`'s
+`primaryAction('batch')` opens no blank record: it anchors the generator on
+the saved location the fiche shows, or writes « Ouvrez un lieu pour y
+générer un lot. » in the fiche's status line when there is none.
+
+**TICKET-0099's G2 condition fired and was answered.** G2 (a generic
+`actions: [...]` list) was to reactivate "when a second tab asks for a
+second button". Lieux is that tab; each tab still needs exactly one extra
+button, which the single field already carries. Kept: G1. G2 now
+reactivates when one tab asks for a third button.
+
+**Rejected.** F-b, letting a secondary action route to another island
+(`batch`) directly: it would amend rule 11b for one button. F2, the trigger
+staying in the list header: the descent view it lived in is gone
+(BRIEF-0100-c).
+
 ---
 
 *Co-built with Claude, June 2026.*
````

## Scope OUT

- Removing « Générer un lot ici » or anything else in `EntityList.svelte` (brief C).
- Disabling « + lot » when no location is open: the registry carries no `disabled` state, and a shell branch on the tab is what `page_contract.py` forbids; the message in the fiche is the behaviour.
- A generic `actions: [...]` list (TICKET-0099's G2), a third button anywhere, or a `secondaryAction` routed to an island other than its primary's (F-b).
- Any change to `RoomBatch.svelte`, `roomBatch.svelte.js`, `mount.js` or `Creation.svelte`.
- Zones and anything about them (TICKET-0101).

## Invariants to defend

- **Every Création page is a `CREATION_TABS` entry rendered by the generic dispatcher; no page-specific branch outside it** (`page_contract.py`): « + lot » is registry data the band renders from `activeEntry`, never a `lieux` literal in `Creation.svelte`.
- **`Sheet.svelte` selects its render branch from `sheetType`** (`creation_tab_switch.py`): the `'batch'` variant chooses an action, not a render branch, and its anchor test reads `sheetType`, never `activeTabKey`.
- **`triggerPrimaryAction` is defined once in `mount.js`** (`creation_island.py` rule 8): the variant is a string, never a second function.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The named mutation of item 4 does not fail as stated.
- `creation_island.py` reports a mount-action count other than 8, or a secondaryAction count other than 2.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `creation_island.py` → `PASS … 8 mount-action identifier(s) confined, 11 island primaryAction(s) wired, 2 secondaryAction(s) paired …`.
- `page_contract.py`, `creation_tab_switch.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` → `PASS`.
- The named mutation of item 4 failed as stated.
- `corpus_gate.py` → 129/129.
- Live: the Lieux band shows « + lot » then « + Nouveau »; with no fiche open, « + lot » writes « Ouvrez un lieu pour y générer un lot. » in the fiche's status line; with a saved location open, it opens « Génération de lot — <its name> »; the NPC band shows only « + Nouveau »; the Compétences band is unchanged.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `« + LOT » BESIDE « + NOUVEAU » (TICKET-0100) -- THE ROOM BATCH ON THE OPEN LOCATION (BRIEF-0100-b, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
