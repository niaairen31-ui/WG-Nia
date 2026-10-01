<!-- slug: graph-node-click -->
# BRIEF 0100-A — "A node click stays on its node"

Lot: LOT-0100-lieux-tree-graph.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0100-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on `main` (expected `dbd10d0` or a descendant that has not touched these files) before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `frontend/src/graph/Graph.svelte:286` → `  function handleCanvasClick() {`; `:293` → `     onclick={handleCanvasClick}`; `:314-318` → the node `<g` whose attributes are `style=…`, `onmousedown={(onMoveNode || onConnect || onNodeClick) ? (e) => handleNodeMouseDown(e, node.id) : undefined}`, `ondblclick=…`, and NO `onclick`
- `frontend/src/graph/Graph.svelte:251-273` → `function handleNodeClick(nodeId)` calls `onNodeClick?.(nodeId);` on the first tap (`:255`) and on the second (`:260`)
- `frontend/src/graph/mount.js:180` → `      onNodeClick: wrapPlain(caps.onNodeClick),`
- `frontend/src/graph/consumers/lieux.js` → 57 lines, no `import`, no `onNodeClick`; `:25` → the `helpText` beginning `'Cliquez un nœud pour le sélectionner, puis un second pour le connecter.`; `:46` → `  async onMoveNode(nodeId, x, y) {`
- `frontend/src/graph/consumers/relations.js:26` → `import { getSelectedEntityId } from '../../creation/sheetState.svelte.js';`
- `frontend/src/creation/sheetState.svelte.js:109` → `export async function selectEntity(legacyDoc, id) {`
- `frontend/src/creation/mount.js:91` → `props: { legacyDoc: node.ownerDocument }`
- `tooling/verify/checks/graph_primitive.py:95` → `             sites collected is a FAILURE.` (last line of the rule list, rule 11c); `:362` → `        f"{counts['dispatches']} dispatch/listen site(s) on a single document"`; `:611` → `_KEY_RE = re.compile(r"(\w+)\s*:")`; `:874` → `    css_ok = _rule8_no_scoped_css()`
- `grep -n "rule12\|rule 12\|  12\." tooling/verify/checks/graph_primitive.py` → no output
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`

## Facts carried

### R-01 — why a node never stays selected [M]
Opened: `frontend/src/graph/Graph.svelte` (whole, 329 lines): `:194-217`
(`handleNodeMouseDown`: `e.stopPropagation()` on the mousedown, then either
`handleNodeClick` at once (force layout, or no `onMoveNode`) or a drag
armed on the window), `:232-249` (`handleMouseUp`: no movement →
`handleNodeClick(nodeId)`), `:251-273` (`handleNodeClick`: with `onConnect`,
the first tap sets `selectedNodeId`, the second connects), `:286-288`
(`handleCanvasClick`: clears `selectedNodeId`), `:290-293` (the `<svg>`
binds `onclick={handleCanvasClick}`), `:314-318` (the node `<g>` binds
`onmousedown` and `ondblclick`, no `onclick`).
Finding: the mousedown's `stopPropagation` stops only the mousedown. The
browser then fires `click` on the node; it bubbles to the `<svg>` and
`handleCanvasClick` clears the selection the press just set. Measured on
`main`: after one click on a Lieux node, every circle's `fill` is
`var(--card)` (none `var(--accent)`); after two clicks on two nodes,
`GET /api/locations/graph` returns zero edges. With an `onclick` that stops
propagation on the `<g>`, the first circle is `var(--accent)` and the edge
is created.
Consequence: the fix belongs to the primitive (C-01), not to a consumer.

### R-02 — the relations graph shares the defect [M]
Opened: `frontend/src/graph/consumers/relations.js:240-258`
(`capabilities(meta)`: global mode with `armed` declares `onConnect`, which
opens « Nouveau lien » in the side panel).
Finding: on `main`, NPC tab → Voir le graphe → Global → Lier → two node
clicks: the side panel shows the node info card (« Relations / Aucune
relation. »), never the form. With C-01: « Nouveau lien / Aldo → Brina ».
Consequence: G1 over G2 (fixing the Lieux consumer only).

### R-03 — how a consumer hears a node click [M]
Opened: `frontend/src/graph/mount.js:168-183` (`svelteMount(Graph, …)`:
`onNodeClick: wrapPlain(caps.onNodeClick)`; `caps` is the consumer object
itself when it exports no `capabilities`, `:166`), `:78-87` (`wrapPlain`:
calls the function, catches and logs, never reloads); `Graph.svelte:251-273`
(`onNodeClick?.(nodeId)` fires on the first tap AND on the second tap,
before `onConnect`).
Consequence: a Lieux `onNodeClick` opens the first node's fiche on the first
tap and the second node's on the second: after a connection, the second
node's fiche is the one open (a locked consequence of G1).

### R-04 — the Lieux consumer [M]
Opened: `frontend/src/graph/consumers/lieux.js` (whole, 57 lines).
Finding: exports `chrome` (title, `helpText` at `:25`), `dashedKinds`,
`load`, `onConnect` (POST `/api/entities/{a}/relations`, type
`connects_to`), `onDeleteEdge`, `onMoveNode` (`:46`). No `onNodeClick`, no
`capabilities`, no import.
Consequence: A adds `onNodeClick` and one import; the four existing
callbacks are untouched.

### R-05 — opening a fiche from outside the list [M]
Opened: `frontend/src/creation/sheetState.svelte.js:109-124`
(`export async function selectEntity(legacyDoc, id)`: GET
`/api/entities/{id}`, sets `sheetMode = 'view'`, `sheetIsNew = false`,
`sheetType = detail.type`, `sheetDetail = detail`, `selectedEntityId = id`,
then dispatches `'creation:selection'` on `legacyDoc`);
`frontend/src/creation/mount.js:91` (every Creation island receives
`legacyDoc: node.ownerDocument` — the shell document since TICKET-0059);
`frontend/src/creation/EntityList.svelte:208-215` (the list calls
`selectEntity(legacyDoc, id)` and listens for `'creation:selection'` on the
same document to highlight the row); `frontend/src/graph/consumers/
relations.js:26` (`import { getSelectedEntityId } from '../../creation/
sheetState.svelte.js'`).
Finding: a graph consumer already imports from `sheetState.svelte.js`;
`graph/mount.js` mounts into the shell `document` (`:121`,
`document.getElementById(containerId)`). Prototype: `import_cycle.py` PASS
with the new import.
Consequence: C-02 calls `selectEntity(document, nodeId)`; the list
highlights the row through its existing listener.

### R-06 — the primitive's lock [M]
Opened: `tooling/verify/checks/graph_primitive.py` (whole, 916 lines on
`main`): rules 1–9 and 11 (no rule 10); `:585-597` (rule 7, a text scan of
`Graph.svelte`), `:600-608` (rule 8), `:611` (`_KEY_RE`), `:834-916`
(`main`: each rule's result joins the final `if FAILURES or …`;
`_report_and_exit(counts)` at `:350-364` prints one PASS line).
Finding: nothing examines a node's click. The check is under
`tooling/verify/`, outside `module_budget.py`'s scope (`src/**/*.py` and
`frontend/src/**`, `module_budget.py:1-25`).
Consequence: A adds rule 12 in the same idiom: a text scan, a count joined
to the PASS line, zero collected is a failure.

## Contracts

### C-01 — a node's click stays on the node
Produced by: A   Consumed by: every graph consumer (lieux, relations, review)
In `Graph.svelte`, every node `<g>` that declares `onmousedown=` also
declares `onclick={(e) => e.stopPropagation()}`. The press itself is still
handled on mousedown/mouseup (R-01); the canvas's `handleCanvasClick` still
clears the selection on a click on the empty canvas. Held by
`graph_primitive.py` rule 12: every `<g …>` opening tag declaring
`onmousedown=` declares an `onclick={…}` whose value contains
`stopPropagation()`; zero such tags collected is a failure.

### C-02 — the Lieux node click
Produced by: A   Consumed by: nothing in this lot (Nia, live)
`consumers/lieux.js` exports `onNodeClick(nodeId)` →
`selectEntity(document, nodeId)`, imported from
`'../../creation/sheetState.svelte.js'`. Fires on both taps of a connection
(R-03). Help text: « Cliquez un nœud pour le sélectionner et ouvrir sa
fiche, puis un second pour le connecter. Glissez pour repositionner.
Cliquez un lien pour le supprimer. »

## Context

Nia is building Aestia and cannot connect two locations on the Lieux graph: a node never stays selected, and its fiche never opens. The defect is in the shared graph primitive (R-01) and also breaks the relations graph's « Lier » arm (R-02). Nia locked G1: fix the primitive, and let a Lieux node click open its fiche.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `Graph.svelte`: the node `<g>` gains `onclick={(e) => e.stopPropagation()}`, with a comment naming why (C-01);
   - `consumers/lieux.js`: imports `selectEntity`, declares `onNodeClick(nodeId)` → `selectEntity(document, nodeId)`, rewords the help text (C-02), and says why in its header comment;
   - `graph_primitive.py`: rule 12 (`_g_open_tags`, `_rule12_node_click_contained`), its docstring entry, its count in the PASS line;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutations, each run then restored with `git checkout -- frontend/src/graph/Graph.svelte` before committing:
   - delete the line `        onclick={(e) => e.stopPropagation()}`: `graph_primitive.py` prints `FAIL: rule12: a node <g> in Graph.svelte declares onmousedown= without an onclick= calling stopPropagation() -- the node's click bubbles to handleCanvasClick and clears the selection in the same gesture`;
   - replace `e.stopPropagation()` on that line with `e.preventDefault()`: the same failure.
5. Commit message: `fix(graph): a node click stays on its node; Lieux node opens its fiche (BRIEF-0100-a)`.

````diff
diff --git a/frontend/src/graph/Graph.svelte b/frontend/src/graph/Graph.svelte
index f02c199..55417f6 100644
--- a/frontend/src/graph/Graph.svelte
+++ b/frontend/src/graph/Graph.svelte
@@ -311,9 +311,17 @@
       {/if}
     {/each}
     {#each placed as node (node.id)}
+      <!-- TICKET-0100 (BRIEF-0100-a): a node press is handled on mousedown/
+           mouseup above, but the browser still fires `click` on the node
+           afterwards, and that click bubbled to the <svg>'s own
+           handleCanvasClick, which cleared the selection in the same
+           gesture -- no node ever stayed selected, so select-to-connect
+           could never reach its second tap. The node's click stops here;
+           graph_primitive.py rule 12 holds it. -->
       <g
         style={onMoveNode ? 'cursor:grab' : undefined}
         onmousedown={(onMoveNode || onConnect || onNodeClick) ? (e) => handleNodeMouseDown(e, node.id) : undefined}
+        onclick={(e) => e.stopPropagation()}
         ondblclick={onNodeDblClick ? (e) => handleNodeDblClick(e, node.id) : undefined}
       >
         <circle cx={node.x.toFixed(1)} cy={node.y.toFixed(1)} r={NODE_R}
diff --git a/frontend/src/graph/consumers/lieux.js b/frontend/src/graph/consumers/lieux.js
index 5031b9d..fc609dd 100644
--- a/frontend/src/graph/consumers/lieux.js
+++ b/frontend/src/graph/consumers/lieux.js
@@ -1,7 +1,15 @@
 /* TICKET-0057. Fetch/write layer for the canonical Lieux adjacency graph.
    All three writes go through pre-existing sanctioned endpoints, unchanged
    and unwidened -- the primitive itself (Graph.svelte) never fetches or
-   writes; that invariant is what this file exists to preserve. */
+   writes; that invariant is what this file exists to preserve.
+
+   TICKET-0100 (BRIEF-0100-a): a node click opens that location's fiche,
+   through the same selectEntity the Lieux list calls -- the relations
+   consumer already imports from that module (getSelectedEntityId). The
+   shell document IS the document every Creation island receives as
+   legacyDoc (creation/mount.js passes node.ownerDocument), so `document`
+   is passed. */
+import { selectEntity } from '../../creation/sheetState.svelte.js';
 
 async function api(path, options) {
   const res = await fetch(path, options);
@@ -22,7 +30,7 @@ async function api(path, options) {
 export default {
   chrome: {
     title: 'Carte des lieux',
-    helpText: 'Cliquez un nœud pour le sélectionner, puis un second pour le connecter. Glissez pour repositionner. Cliquez un lien pour le supprimer.',
+    helpText: 'Cliquez un nœud pour le sélectionner et ouvrir sa fiche, puis un second pour le connecter. Glissez pour repositionner. Cliquez un lien pour le supprimer.',
   },
   dashedKinds: [],
 
@@ -43,6 +51,10 @@ export default {
     await api(`/api/relations/${encodeURIComponent(edgeId)}`, { method: 'DELETE' });
   },
 
+  onNodeClick(nodeId) {
+    selectEntity(document, nodeId);
+  },
+
   async onMoveNode(nodeId, x, y) {
     // coord_x/coord_y are two scalar columns -- no merge discipline needed
     // (TICKET-0025, BRIEF-0025-b; was a JSON read-merge-write).
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 9363718..42cf9d3 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17421,6 +17421,21 @@ occurrence, in the registry.
 second tab asks for a second button, or this tab for a third. G3, the
 button in the list header: not where the creator asked for it.
 
+## A NODE CLICK STAYS ON ITS NODE (TICKET-0100) -- GRAPH SELECTION (BRIEF-0100-a, no schema change)
+
+**G1.** The graph primitive handles a node press on mousedown/mouseup, but
+the browser still fires `click` on the node afterwards. That click bubbled
+to the `<svg>`'s own `handleCanvasClick`, which cleared the selection in the
+same gesture: no node ever stayed selected, so neither the Lieux graph nor
+the relations graph's « Lier » arm could reach a second tap. The node's
+`<g>` now stops its own click; `graph_primitive.py` rule 12 holds it for
+every node group. The Lieux consumer also declares `onNodeClick`: a node
+click opens that location's fiche through `sheetState.svelte.js`'s
+`selectEntity`, the function the Lieux list already calls.
+
+**Rejected.** G2, fixing the Lieux consumer only: the defect sits in the
+shared primitive, and the relations graph's « Lier » arm stayed broken.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/graph_primitive.py b/tooling/verify/checks/graph_primitive.py
index 6f6b3b5..b4d80d8 100644
--- a/tooling/verify/checks/graph_primitive.py
+++ b/tooling/verify/checks/graph_primitive.py
@@ -93,6 +93,15 @@ satisfied comparison.
              bare `document`. A dispatch against `legacyDocument()` or any
              `contentWindow`-derived document is a FAILURE. Zero dispatch
              sites collected is a FAILURE.
+  12. A node press never reaches the canvas (TICKET-0100, BRIEF-0100-a).
+      The primitive handles a node press on mousedown/mouseup, but the
+      browser still fires `click` on the node afterwards; left to bubble,
+      it reached the <svg>'s handleCanvasClick and cleared the selection in
+      the same gesture, so select-to-connect never reached its second tap
+      (Lieux and the relations "Lier" arm alike). Every `<g ...>` opening
+      tag in Graph.svelte that declares `onmousedown=` must also declare an
+      `onclick=` whose value calls `stopPropagation()`. Zero such `<g>`
+      tags collected is a FAILURE.
 """
 from __future__ import annotations
 
@@ -359,7 +368,8 @@ def _report_and_exit(counts: dict | None = None) -> None:
         f"{counts['specs']} graph spec(s) validated, "
         f"{counts['live']} live graph impl(s), {counts['retired']} retired graph impl(s) proven absent, "
         f"{counts['mounts']} mount target(s) resolved in the shell document, "
-        f"{counts['dispatches']} dispatch/listen site(s) on a single document"
+        f"{counts['dispatches']} dispatch/listen site(s) on a single document, "
+        f"{counts['node_clicks']} node click(s) contained"
     )
     sys.exit(0)
 
@@ -608,6 +618,46 @@ def _rule8_no_scoped_css() -> bool:
     return True
 
 
+def _g_open_tags(text: str) -> list[str]:
+    """Every `<g` opening tag's full source, `{...}` attribute values
+    included -- the tag ends at the first `>` outside braces, so an arrow
+    function's `=>` inside an attribute never ends it early."""
+    tags: list[str] = []
+    for m in re.finditer(r"<g\b", text):
+        depth, i = 0, m.end()
+        while i < len(text):
+            ch = text[i]
+            if ch == "{":
+                depth += 1
+            elif ch == "}":
+                depth -= 1
+            elif ch == ">" and depth == 0:
+                tags.append(text[m.start():i + 1])
+                break
+            i += 1
+    return tags
+
+
+def _rule12_node_click_contained() -> int:
+    if not GRAPH_SVELTE.is_file():
+        fail(f"{GRAPH_SVELTE} does not exist")
+        return 0
+    count = 0
+    for tag in _g_open_tags(GRAPH_SVELTE.read_text(encoding="utf-8")):
+        if "onmousedown=" not in tag:
+            continue
+        count += 1
+        click_m = re.search(r"onclick=\{([^}]*)\}", tag)
+        if not click_m or "stopPropagation()" not in click_m.group(1):
+            fail("rule12: a node <g> in Graph.svelte declares onmousedown= without an onclick= calling "
+                 "stopPropagation() -- the node's click bubbles to handleCanvasClick and clears the "
+                 "selection in the same gesture")
+    if count == 0:
+        fail("rule12: zero node <g> tag(s) with onmousedown= collected in Graph.svelte -- "
+             "a rule that passes on nothing proves nothing")
+    return count
+
+
 _KEY_RE = re.compile(r"(\w+)\s*:")
 
 
@@ -872,6 +922,7 @@ def main() -> None:
 
     primitive_ok = _rule7_no_fetch_write()
     css_ok = _rule8_no_scoped_css()
+    node_click_count = _rule12_node_click_contained()
     spec_count = _rule9_closed_vocab(html)
 
     legacy_container_ok = _rule11a_no_legacy_container()
@@ -908,6 +959,7 @@ def main() -> None:
             "retired": retired_proven_count,
             "mounts": mount_target_count,
             "dispatches": dispatch_count + listen_count,
+            "node_clicks": node_click_count,
         }
     )
 
````

## Scope OUT

- Anything about zones, the `borde` relation, or graph modes (TICKET-0101).
- Revealing, in the Lieux list, a location opened from the graph whose ancestors are folded (carried forward).
- Any change to `handleCanvasClick`, the drag, the pan/zoom, edge clicks, or the relations consumer: they are fixed by C-01 without being touched.
- An `onNodeClick` on the review consumer.
- Briefs B and C of this lot.

## Invariants to defend

- **The graph primitive is the ONE graph component** (`graph_primitive.py`, CLAUDE.md): the fix is one attribute on the primitive's node group, never a consumer-side workaround, and the primitive still never fetches or writes (rule 7) — the fiche opens from the consumer.
- **Every Création surface mounts through `mount.js` alone** (`creation_island.py`): the consumer calls an exported function of `sheetState.svelte.js`; it mounts nothing.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of item 4 does not fail as stated.
- `import_cycle.py` fails after the commit.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm ci` warns that `package.json` asks for Node ≥ 24.18 while the local Node is older: proceed if the build succeeds, and report the version.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `graph_primitive.py` → `PASS … 9 dispatch/listen site(s) on a single document, 1 node click(s) contained`.
- `import_cycle.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` → `PASS`.
- Both named mutations of item 4 failed as stated.
- `corpus_gate.py` → 129/129.
- Live: on Lieux, « Voir le graphe », one click on a node fills it with the accent color and opens its fiche below; a click on a second node draws the connection and leaves the second node's fiche open. On NPC, « Voir le graphe » → Global → « Lier », two node clicks open « Nouveau lien ».
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A NODE CLICK STAYS ON ITS NODE (TICKET-0100) -- GRAPH SELECTION (BRIEF-0100-a, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
