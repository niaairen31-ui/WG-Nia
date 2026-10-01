<!-- slug: lieux-tree -->
# BRIEF 0100-C — "The Lieux list unfolds in place"

Lot: LOT-0100-lieux-tree-graph.md (authoritative on conflict)
Depends on: BRIEF-0100-B (the room batch's new trigger, C-04, must exist before its old one is deleted)
Commit header for decisions: `(BRIEF-0100-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0100`, on the tree BRIEF-0100-B left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `frontend/src/creation/EntityList.svelte` → 388 lines; `:56` → `  import { openRoomBatch } from './roomBatch.svelte.js';`; `:64` → `  const LOCATION_TYPE_ORDER = ['city', 'district', 'building', 'room', 'natural', 'underground', 'other'];`; `:79-81` → `let lieuxParentId = $state(null);`, `let lieuxBreadcrumb = $state([]);`, `let lieuxActiveOnly = $state(false);`; `:192` → `    if (tabKey === 'lieux' && isNewActivation) {`; `:267` → `  function lieuxChildrenOf(parentId) {`; `:277` → `  function lieuxBuckets() {`; `:331` → `{:else if mode === 'lieux'}`; `:367` → `{:else if mode === 'record' && !recordsReady}`
- `frontend/src/creation/tabs.js` → `CREATION_TABS.lieux` declares `secondaryAction: { label: '+ lot', handler: () => triggerPrimaryAction('entitySheet', 'batch') },` (BRIEF-0100-B)
- `frontend/src/creation/Sheet.svelte` → imports `openRoomBatch` and declares `function openBatchOnOpenLocation()` (BRIEF-0100-B)
- `frontend/public/creation.css:217` → `.author-list-item {`; `:228` → `/* ── Lieux hierarchy browse (BRIEF-51) ───────────────────────────────────── */`; `:284` → `/* TICKET-0060 (BRIEF-0060-e, K1): .row-table and .row-card moved to`
- `frontend/src/creation/CompetencesList.svelte:77` → `           style="padding-left:28px" role="button" tabindex="0"`
- `tooling/verify/checks/location_tree.py:42` → `TOKEN = "linkagent-loc-node"`; `:126` → `        if TOKEN in text and _self_recursive(text):`
- `grep -rn "lieux-children-btn\|lieuxVisibleRows" frontend/src frontend/public` → no output

## Facts carried

### R-10 — the Lieux list today [M]
Opened: `frontend/src/creation/EntityList.svelte` (whole, 388 lines):
`:56` (`import { openRoomBatch }`), `:63-68` (`GENERIC_TYPE_BY_TAB`,
`LOCATION_TYPE_ORDER`, `LOCATION_TYPE_LABELS`), `:75-81` (descent state:
`lieuxParentId`, `lieuxBreadcrumb`, `lieuxActiveOnly`), `:176-196`
(`activateTab`: a new Lieux activation resets the descent), `:255-265`
(`lieuxHasActiveDescendant`), `:267-275` (`lieuxChildrenOf`: roots are
locations with no parent or an unknown parent; filtered by
`lieuxActiveOnly`), `:277-306` (`lieuxBuckets`, `lieuxDescend`,
`lieuxJumpTo`), `:322-329` (the flat mode's row:
`.author-list-item`, `.ali-name`, `.ali-meta` « type · status »,
`active`/`inactive` classes), `:331-366` (the lieux markup: checkbox,
breadcrumb, lot button, buckets, `.lieux-node-row` rows with a name button,
a status pill and « N enfants › » that descends).
Consequence: C replaces `:75-81`'s descent pair, `:192-195`, `:277-306` and
`:331-366`; keeps `lieuxActiveOnly`, `lieuxHasActiveDescendant`,
`lieuxChildrenOf` unchanged.

### R-11 — location types belong to each world [M]
Opened: `src/world_engine/models/canon.py:209-230` (`Location.location_type:
Optional[str]`, no constraint), `:246-271` (`LocationTypeCatalog`: one row
per type string per world, unique on `(world_id, name COLLATE NOCASE)`;
types are added one at a time from the picker).
Finding: a world's types are whatever its creator typed (`quartier`,
`bâtiment` in the prototype world). `LOCATION_TYPE_ORDER` matches only the
seven English strings; everything else lands in « Autres ».
Consequence: the buckets go; the type is shown as the row's meta.

### R-12 — entity status values [M]
Opened: `src/world_engine/models/canon.py:133-135` (`Entity.status: str`,
default `'active'`, no CHECK); `src/world_engine/cockpit/crud/entities.py:112`
(`ENTITY_STATUSES = ("active", "inactive", "destroyed", "missing")`, the
fiche's choices).
Finding: four values offered, none enforced. The old Lieux rows dimmed
every non-`active` status (`:357`); the flat list strikes only `inactive`
(`:324`).
Consequence: C keeps the Lieux behaviour: any status but `active` takes the
`inactive` row class, and the status is printed in the meta line.

### R-13 — the rows the tree reads [M]
Opened: `src/world_engine/cockpit/crud/locations.py:264-284`
(`GET /api/locations`: every location of the active world, every status,
each `{id, name, parent_location_id, location_type, status}`);
`EntityList.svelte:100` (`creationState.locationTree = locations`).
Consequence: C-05 needs no new fetch.

### R-14 — the one recursive location tree [M]
Opened: `tooling/verify/checks/location_tree.py` (implementation `:94-137`:
a `.svelte` file other than `LocationTree.svelte` fails when it contains
BOTH the token `linkagent-loc-node` AND a self-recursive render — a
`{#snippet NAME(…)}` calling `{@render NAME(` inside itself, or
`<svelte:self`); `frontend/src/creation/LocationTree.svelte:47-69` (props
`locations` and `row`; every node rendered as a `<label>` inside
`.linkagent-loc-node`, always fully expanded).
Finding: the primitive has no folded state and renders labelled controls,
not list rows. A recursive snippet in `EntityList.svelte` without the token
would pass the check while duplicating exactly what it exists to prevent.
Consequence: C flattens the tree iteratively (C-05) and renders one
`{#each}`; no recursion, no token.

### R-15 — the list row the other tabs use [M]
Opened: `frontend/public/creation.css:217-226` (`.author-list-item`:
`padding: 9px 14px`, left border, `.active` highlighted, `.inactive`
struck and faded; `.ali-name`, `.ali-meta`);
`frontend/src/creation/CompetencesList.svelte:52-90` (record rows:
`role="button" tabindex="0"`, `onclick`, `onkeydown` on Enter; a child row
indented with `style="padding-left:28px"` at `:77`).
Consequence: C's rows are that markup; depth sets `padding-left` to
`14 + 16 × depth` px (14 px is the class's own left padding).

### R-16 — the descent view's CSS [M]
Opened: `frontend/public/creation.css:228-282` (`.lieux-browse-head`,
`.lieux-breadcrumb` and its `.lb-*`, `.lieux-bucket-head`,
`.lieux-node-row` and its `.ali-name-btn`/`.dimmed`, `.lieux-status-pill`,
`.lieux-descend-btn`); `tooling/verify/checks/stylesheet_partition.py:385-399`
(rule 6: `static/creation.css` must byte-match the `frontend/public/` copy;
the build copies it, measured).
Finding: enumeration E1 — every one of those classes is used by
`EntityList.svelte` alone, except `.lieux-bucket-head`, also used by
`CompetencesList.svelte`; none in `legacy.html` or `static/index.html`.
Consequence: C deletes the rules only `EntityList.svelte` used and no longer
applies, keeps `.lieux-browse-head` and `.lieux-bucket-head`, adds
`.lieux-children-btn`.

### E1 — files using each class of the descent view's CSS (outside built assets), on `main`
```
lieux-browse-head: frontend/src/creation/EntityList.svelte
lieux-breadcrumb:  frontend/src/creation/EntityList.svelte
lb-seg / lb-sep / lb-current: frontend/src/creation/EntityList.svelte
lieux-bucket-head: frontend/src/creation/EntityList.svelte frontend/src/creation/CompetencesList.svelte
lieux-node-row / ali-name-btn / dimmed: frontend/src/creation/EntityList.svelte
lieux-status-pill / lieux-descend-btn: frontend/src/creation/EntityList.svelte
legacy.html and static/index.html: 0 occurrences of each
```

## Contracts

### C-05 — the Lieux tree
Produced by: C   Consumed by: C (markup)
`lieuxExpanded`: a `$state` `Set` of location ids, replaced (never mutated
in place) by `lieuxToggleExpanded(id)`; reset to an empty `Set` on a new
Lieux activation (where the descent pair was reset). Kept across list
refreshes.
`lieuxVisibleRows()` → `[{ loc, depth, childCount, expanded }]`, preorder:
the roots of `lieuxChildrenOf(null)` (unchanged, R-10), then, under each
row whose id is in `lieuxExpanded`, its `lieuxChildrenOf(id)` at `depth +
1`; siblings sorted by `name.localeCompare` at every level; a `seen` set
skips an id met twice (a parent cycle). `childCount` is
`lieuxChildrenOf(id).length`, so « Actifs seulement » filters it too.
Row: `.author-list-item`, `active` when `loc.id === selectedEntityId`,
`inactive` when `loc.status !== 'active'`, `padding-left: 14 + 16 × depth`
px, `role="button" tabindex="0"`, click/Enter → `onSelectEntity(loc.id)`.
`.ali-name` = name; `.ali-meta` = `location_type || '—'` « · » `status`,
then, when `childCount > 0`, `<button class="lieux-children-btn">` « N
enfant(s) › » folded or « … ⌄ » unfolded, whose click stops propagation and
toggles. Empty → « Aucun lieu. ».

## Context

Nia asked for a Lieux list that looks like every other tab's and that unfolds in place: « 3 enfants » adds the children, indented, without hiding the rest, and a second click folds them. Today's list is a descent view keyed on English type buckets her world's types never match (R-10, R-11). Brief B already moved « Générer un lot ici » to the « + lot » shell button, so this brief can delete the descent view whole.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `EntityList.svelte`: deletes the `openRoomBatch` import, `LOCATION_TYPE_ORDER`/`LOCATION_TYPE_LABELS`, `lieuxParentId`/`lieuxBreadcrumb`, `lieuxBuckets`/`lieuxDescend`/`lieuxJumpTo`; adds `lieuxExpanded`, `lieuxVisibleRows()`, `lieuxToggleExpanded(id)` (C-05); the new-activation reset clears `lieuxExpanded`; the lieux markup becomes the checkbox head plus one `{#each}` of C-05 rows; the header comment notes where « Générer un lot ici » went;
   - `frontend/public/creation.css`: the « Lieux hierarchy browse » block keeps `.lieux-browse-head` and `.lieux-bucket-head`, drops `.lieux-breadcrumb`/`.lb-*`, `.lieux-node-row`/`.ali-name-btn`/`.dimmed`, `.lieux-status-pill`, `.lieux-descend-btn`, and gains `.lieux-children-btn`;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build` (it also copies `creation.css` into `static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutation, run then restored with `git checkout -- src/world_engine/cockpit/static/creation.css` before committing:
   - after the build, put back the previous built stylesheet (`git show HEAD:src/world_engine/cockpit/static/creation.css > src/world_engine/cockpit/static/creation.css`): `stylesheet_partition.py` prints `FAIL: rule6: …/src/world_engine/cockpit/static/creation.css does not byte-match …/frontend/public/creation.css -- run "npm run build" in frontend/ and commit the output`.
   (No mutation is named for `.lieux-children-btn` itself: renaming the class on the button leaves `stylesheet_partition.py` green, measured — rule 7 only covers class names the legacy inline sheet also uses. Carried forward on the ticket, not fixed here.)
5. Commit message: `feat(creation): the Lieux list unfolds in place (BRIEF-0100-c)`.

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index 13269c0..0cf0709 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -225,7 +225,10 @@ input.notes::placeholder { color: var(--muted); }
 .author-list-item .ali-meta { font-size: 11px; color: var(--muted); margin-top: 2px; }
 .author-list-item.inactive .ali-name { opacity: 0.5; text-decoration: line-through; }
 
-/* ── Lieux hierarchy browse (BRIEF-51) ───────────────────────────────────── */
+/* ── Lieux hierarchy browse (BRIEF-51; TICKET-0100, BRIEF-0100-c: the
+   descent view's breadcrumb, typed buckets' rows, status pill and descend
+   button gave way to the shared .author-list-item rows, unfolded in place
+   by .lieux-children-btn) ─────────────────────────────────────────────── */
 .lieux-browse-head {
   padding: 8px 14px;
   border-bottom: 1px solid var(--border);
@@ -234,11 +237,6 @@ input.notes::placeholder { color: var(--muted); }
   gap: 6px;
 }
 .lieux-browse-head .field-row.checkbox { margin: 0; }
-.lieux-breadcrumb { font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px; }
-.lieux-breadcrumb .lb-seg { cursor: pointer; color: var(--accent); }
-.lieux-breadcrumb .lb-seg:hover { text-decoration: underline; }
-.lieux-breadcrumb .lb-sep { color: var(--muted); }
-.lieux-breadcrumb .lb-current { color: var(--text); cursor: default; }
 .lieux-bucket-head {
   padding: 6px 14px 2px;
   font-size: 11px;
@@ -246,40 +244,18 @@ input.notes::placeholder { color: var(--muted); }
   letter-spacing: 0.04em;
   color: var(--muted);
 }
-.lieux-node-row {
-  display: flex;
-  align-items: center;
-  gap: 6px;
-  padding: 2px 14px;
-}
-.lieux-node-row .ali-name-btn {
-  flex: 1;
-  text-align: left;
-  background: none;
-  border: none;
-  cursor: pointer;
-  padding: 7px 0;
-  color: var(--text);
-  font-size: 13px;
-}
-.lieux-node-row .ali-name-btn:hover { text-decoration: underline; }
-.lieux-node-row.dimmed .ali-name-btn { opacity: 0.5; }
-.lieux-status-pill {
-  font-size: 10px;
-  color: var(--muted);
-  border: 1px solid var(--border);
-  border-radius: 8px;
-  padding: 1px 6px;
-}
-.lieux-descend-btn {
+.lieux-children-btn {
+  margin-left: 6px;
   font-size: 11px;
   color: var(--muted);
   background: none;
-  border: none;
+  border: 1px solid var(--border);
+  border-radius: 8px;
+  padding: 0 6px;
   cursor: pointer;
   white-space: nowrap;
 }
-.lieux-descend-btn:hover { color: var(--accent); }
+.lieux-children-btn:hover { color: var(--accent); border-color: var(--accent); }
 
 /* TICKET-0060 (BRIEF-0060-e, K1): .row-table and .row-card moved to
    shared.css -- the legacy document applies both and cannot link this
diff --git a/frontend/src/creation/EntityList.svelte b/frontend/src/creation/EntityList.svelte
index a6ff40d..271d793 100644
--- a/frontend/src/creation/EntityList.svelte
+++ b/frontend/src/creation/EntityList.svelte
@@ -34,7 +34,9 @@
      buts manquants" (BRIEF-0058-j) reach the room-batch island and the
      goals-backfill endpoint by plain import/fetch now too -- neither is a
      legacy function any more, so legacy/bridge.js's openBatchPanel/
-     triggerNpcGoalsBackfill are gone.
+     triggerNpcGoalsBackfill are gone. TICKET-0100 (BRIEF-0100-c): « Générer
+     un lot ici » left with the Lieux descent view it lived in; the room
+     batch is Lieux' « + lot » shell button now (BRIEF-0100-b).
 
      No scoped <style> block: like Graph.svelte and Constructeur.svelte,
      this renders inside the legacy iframe document, where Svelte's
@@ -53,7 +55,6 @@
   import { creationState } from './state.svelte.js';
   import { creationSelectRecord } from './tabs.js';
   import { selectEntity } from './sheetState.svelte.js';
-  import { openRoomBatch } from './roomBatch.svelte.js';
   import { loadAgendas } from './intrigues.svelte.js';
   import { loadCatalogue } from './competences.svelte.js';
   import CompetencesList from './CompetencesList.svelte';
@@ -61,23 +62,19 @@
   let { legacyDoc } = $props();
 
   const GENERIC_TYPE_BY_TAB = { npc: 'character', pj: 'character', lieux: 'location', factions: 'faction', objets: 'item' };
-  const LOCATION_TYPE_ORDER = ['city', 'district', 'building', 'room', 'natural', 'underground', 'other'];
-  const LOCATION_TYPE_LABELS = {
-    city: 'Villes', district: 'Quartiers', building: 'Bâtiments', room: 'Pièces',
-    natural: 'Lieux naturels', underground: 'Souterrains', other: 'Autres',
-  };
 
   let mode = $state('loading'); // 'loading' | 'flat' | 'lieux' | 'record' | 'error'
   let errorMessage = $state('');
   let recordsReady = $state(false);
   let previousTabKey = null;
 
-  // Lieux browse view-state -- component-local (unlike entities/agendas,
-  // nothing outside this island reads it once renderLieuxBrowse and its
-  // helpers are gone; the room-batch "Générer un lot ici" trigger reaches
-  // the room-batch island's own store directly, BRIEF-0058-j).
-  let lieuxParentId = $state(null);
-  let lieuxBreadcrumb = $state([]);
+  // Lieux tree view-state -- component-local (nothing outside this island
+  // reads it). TICKET-0100 (BRIEF-0100-c, E): the descent view (a parent
+  // id plus its breadcrumb) gave way to one tree whose rows unfold in
+  // place; `lieuxExpanded` holds the ids whose children are shown. The
+  // room batch trigger left with the descent view: it is Lieux' « + lot »
+  // shell button now (BRIEF-0100-b).
+  let lieuxExpanded = $state(new Set());
   let lieuxActiveOnly = $state(false);
 
   async function api(path) {
@@ -190,8 +187,7 @@
       return;
     }
     if (tabKey === 'lieux' && isNewActivation) {
-      lieuxParentId = null;
-      lieuxBreadcrumb = [];
+      lieuxExpanded = new Set();
     }
     loadGenericEntities();
   }
@@ -274,35 +270,37 @@
     return children;
   }
 
-  function lieuxBuckets() {
-    const children = lieuxChildrenOf(lieuxParentId);
-    const buckets = {};
-    for (const loc of children) {
-      const key = LOCATION_TYPE_ORDER.includes(loc.location_type) ? loc.location_type : 'other';
-      (buckets[key] = buckets[key] || []).push(loc);
+  /** TICKET-0100 (BRIEF-0100-c, E): the Lieux list as one tree, flattened
+   *  for rendering -- every root row, then, under each EXPANDED row, its
+   *  children one level deeper, alphabetical at every level. Iterative on
+   *  purpose: the recursive location-tree render belongs to
+   *  LocationTree.svelte alone (location_tree.py), and the rows here are
+   *  the shared list's own `.author-list-item` rows, not that primitive's
+   *  labelled controls. `seen` stops a parent cycle from looping. */
+  function lieuxVisibleRows() {
+    const byName = (list) => list.slice().sort((a, b) => a.name.localeCompare(b.name));
+    const rows = [];
+    const seen = new Set();
+    const stack = byName(lieuxChildrenOf(null)).reverse().map((loc) => ({ loc, depth: 0 }));
+    while (stack.length) {
+      const { loc, depth } = stack.pop();
+      if (seen.has(loc.id)) continue;
+      seen.add(loc.id);
+      const children = byName(lieuxChildrenOf(loc.id));
+      const expanded = lieuxExpanded.has(loc.id);
+      rows.push({ loc, depth, childCount: children.length, expanded });
+      if (expanded) {
+        for (const child of children.reverse()) stack.push({ loc: child, depth: depth + 1 });
+      }
     }
-    return LOCATION_TYPE_ORDER
-      .filter((t) => buckets[t] && buckets[t].length)
-      .map((t) => ({
-        type: t,
-        label: LOCATION_TYPE_LABELS[t],
-        rows: buckets[t].slice().sort((a, b) => a.name.localeCompare(b.name)),
-      }));
-  }
-
-  function lieuxDescend(id, name) {
-    lieuxBreadcrumb = [...lieuxBreadcrumb, { id, name }];
-    lieuxParentId = id;
+    return rows;
   }
 
-  function lieuxJumpTo(index) {
-    if (index < 0) {
-      lieuxParentId = null;
-      lieuxBreadcrumb = [];
-    } else {
-      lieuxBreadcrumb = lieuxBreadcrumb.slice(0, index + 1);
-      lieuxParentId = lieuxBreadcrumb[lieuxBreadcrumb.length - 1].id;
-    }
+  function lieuxToggleExpanded(id) {
+    const next = new Set(lieuxExpanded);
+    if (next.has(id)) next.delete(id);
+    else next.add(id);
+    lieuxExpanded = next;
   }
 </script>
 
@@ -334,34 +332,23 @@
       <input type="checkbox" checked={lieuxActiveOnly} onchange={(ev) => { lieuxActiveOnly = ev.currentTarget.checked; }}>
       <span style="font-size:12px">Actifs seulement</span>
     </label>
-    <div class="lieux-breadcrumb">
-      <span class="lb-seg {lieuxParentId == null ? 'lb-current' : ''}" onclick={() => lieuxJumpTo(-1)}>Racine</span>
-      {#each lieuxBreadcrumb as seg, i (seg.id)}
-        <span class="lb-sep">›</span>
-        <span class="lb-seg {i === lieuxBreadcrumb.length - 1 ? 'lb-current' : ''}" onclick={() => lieuxJumpTo(i)}>{seg.name}</span>
-      {/each}
-    </div>
-    {#if lieuxParentId != null}
-      <button class="btn-icon" onclick={() => openRoomBatch(lieuxParentId, lieuxBreadcrumb[lieuxBreadcrumb.length - 1]?.name || '')}>Générer un lot ici</button>
-    {:else}
-      <button class="btn-icon" disabled title="Descends dans un lieu pour l'utiliser comme ancre">Générer un lot ici</button>
-    {/if}
   </div>
-  {#if lieuxBuckets().length === 0}
+  {#if lieuxVisibleRows().length === 0}
     <div class="empty">Aucun lieu.</div>
   {:else}
-    {#each lieuxBuckets() as bucket (bucket.type)}
-      <div class="lieux-bucket-head">{bucket.label}</div>
-      {#each bucket.rows as loc (loc.id)}
-        {@const childCount = lieuxChildrenOf(loc.id).length}
-        <div class="lieux-node-row {loc.status !== 'active' ? 'dimmed' : ''}">
-          <button class="ali-name-btn" onclick={() => onSelectEntity(loc.id)}>{loc.name}</button>
-          {#if loc.status !== 'active'}<span class="lieux-status-pill">{loc.status}</span>{/if}
-          {#if childCount > 0}
-            <button class="lieux-descend-btn" onclick={() => lieuxDescend(loc.id, loc.name)}>{childCount} enfant{childCount > 1 ? 's' : ''} ›</button>
+    {#each lieuxVisibleRows() as row (row.loc.id)}
+      <div class="author-list-item {row.loc.id === creationState.selectedEntityId ? 'active' : ''} {row.loc.status !== 'active' ? 'inactive' : ''}"
+           style="padding-left:{14 + row.depth * 16}px" role="button" tabindex="0"
+           onclick={() => onSelectEntity(row.loc.id)}
+           onkeydown={(ev) => { if (ev.key === 'Enter') onSelectEntity(row.loc.id); }}>
+        <div class="ali-name">{row.loc.name}</div>
+        <div class="ali-meta">
+          {row.loc.location_type || '—'} · {row.loc.status}
+          {#if row.childCount > 0}
+            <button class="lieux-children-btn" onclick={(ev) => { ev.stopPropagation(); lieuxToggleExpanded(row.loc.id); }}>{row.childCount} enfant{row.childCount > 1 ? 's' : ''} {row.expanded ? '⌄' : '›'}</button>
           {/if}
         </div>
-      {/each}
+      </div>
     {/each}
   {/if}
 {:else if mode === 'record' && !recordsReady}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 3532d29..4878b10 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17458,6 +17458,24 @@ reactivates when one tab asks for a third button.
 staying in the list header: the descent view it lived in is gone
 (BRIEF-0100-c).
 
+## THE LIEUX LIST UNFOLDS IN PLACE (TICKET-0100) -- ONE TREE ON THE SHARED ROWS (BRIEF-0100-c, no schema change)
+
+**E.** The Lieux list stops being a descent view (a breadcrumb, a parent to
+descend into, rows bucketed by a fixed English type list that a world's own
+type catalog never matched, so every typed location fell into « Autres »).
+It is one tree drawn with the shared list's `.author-list-item` rows: name,
+then « type · status » as meta, the selected row highlighted like every
+other tab. A row with children carries « N enfant(s) › »; clicking it
+unfolds those children in place, one indentation step deeper, and clicking
+it again folds them -- the rest of the list stays where it was. « Actifs
+seulement » stays. The tree is flattened iteratively in `EntityList.svelte`
+(`lieuxVisibleRows`): the recursive location-tree render stays
+`LocationTree.svelte`'s alone (`location_tree.py`).
+
+**Rejected.** E2, a flat list with « type · parent » as meta: loses the
+hierarchy Nia reads at a glance. E3, the descent view restyled: the
+descent itself was what she asked to lose.
+
 ---
 
 *Co-built with Claude, June 2026.*
````

## Scope OUT

- Unfolding a folded location's ancestors when it is opened from the graph, or keeping a selected child visible when its parent folds (carried forward).
- Using `LocationTree.svelte` here, or giving it a folded state: it renders labelled controls for the two agents, not list rows (R-14).
- Any change to `lieuxChildrenOf`, `lieuxHasActiveDescendant`, the flat or record modes, `CompetencesList.svelte`, or `/api/locations`.
- A drag-and-drop reparenting, a « tout déplier » control, or remembering what was unfolded across tab changes.
- Anything about zones (TICKET-0101): no row is marked « zone » in this ticket.

## Invariants to defend

- **Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards** (`effect_self_write.py`): `lieuxExpanded` is written only by the click handler and by `activateTab`, which already runs inside the island's one `$effect` and does not read it after writing.
- **Every Création page is a registry entry, no page-specific branch outside it** (`page_contract.py`): the tree lives in the existing `mode === 'lieux'` branch of the list island; nothing moves into `Creation.svelte`.
- **A Création tab that owns a single container sizes it** (`creation_container_sizing.py`): Lieux owns two containers and is not examined; nothing here changes its containers.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of item 4 does not fail as stated.
- `location_tree.py` or `effect_self_write.py` fails after the commit.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed by `npm run build` (the prototype removed two `EntityList.svelte` warning pairs and added none, LOT E3).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `grep -rn "openRoomBatch\|Générer un lot ici" frontend/src/creation/EntityList.svelte` → only the header comment line naming where « Générer un lot ici » went.
- `grep -rn "lieux-breadcrumb\|lieux-node-row\|lieux-descend-btn\|lieux-status-pill" frontend/src frontend/public src/world_engine/cockpit/static/creation.css` → no output.
- `location_tree.py`, `stylesheet_partition.py`, `effect_self_write.py`, `page_contract.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` → `PASS`.
- The named mutation of item 4 failed as stated.
- `corpus_gate.py` → 129/129.
- Live: the Lieux list shows only top-level locations, each a standard row with « type · status »; « 4 enfants › » under the Secte du Phoenix unfolds its children indented below it, the other rows staying in place; a child with children unfolds one step deeper; « 4 enfants ⌄ » folds them; clicking any row opens its fiche and highlights the row; « Actifs seulement » still hides inactive locations.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE LIEUX LIST UNFOLDS IN PLACE (TICKET-0100) -- ONE TREE ON THE SHARED ROWS (BRIEF-0100-c, no schema change)` — in the diff. This is the last brief: after it the ticket goes to `/verify` and the live gate.
