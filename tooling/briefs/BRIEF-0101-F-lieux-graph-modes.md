<!-- slug: lieux-graph-modes -->
# BRIEF 0101-F — "The Lieux graph has three modes"

Lot: LOT-0101-zones.md (authoritative on conflict)
Depends on: A (C-01, C-03)
Commit header for decisions: `(BRIEF-0101-f, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- BRIEFS 0101-A to -E are committed.
- `src/world_engine/cockpit/crud/locations.py`: `@router.get("/locations/graph")` then `def get_locations_graph(db: DbSession = Depends(get_session)) -> dict:`, the function ending with `    return {"nodes": nodes, "edges": edges}` just before `@router.get("/locations")`; the import `from ...zone_rules import ZoneRefusal, is_zone, require_visitable` (E)
- `frontend/src/graph/Graph.svelte:45` → `  const NODE_R = 20;`; `:297` → the `<text …>Aucun nœud</text>`; `:327` → `        <circle cx={node.x.toFixed(1)} cy={node.y.toFixed(1)} r={NODE_R}`; `    onNodeDblClick = null,` then `  } = $props();`
- `frontend/src/graph/mount.js:181` → `      onNodeDblClick: wrapRemounter(containerId, caps.onNodeDblClick),`
- `frontend/src/graph/consumers/lieux.js` → 69 lines, imports `selectEntity` only, no `capabilities`
- `frontend/src/graph/consumers/relations.js:210` → `  defaultMeta: { mode: 'ego', armed: false, buckets: DEFAULT_BUCKETS, id: null },`

## Facts carried

### R-18 — the Lieux graph [M]
Opened: `crud/locations.py:219-261`; `frontend/src/graph/consumers/lieux.js`
(whole, 69 lines); `Graph.svelte` (whole, 337 lines: `NODE_R = 20` `:45`,
clamps `:120-121`, empty text `:297`, circle `:327`, label `:331`);
`mount.js:89-112` (controls: `button` | `checkbox`), `:166-185` (props);
`consumers/relations.js:185-258` (modes through `controls`,
`capabilities(meta)`, `defaultMeta`, `onNodeDblClick → {id}`).
Finding: one mode, every active location, `connects_to` edges.
Consequence: F, with two new optional primitive axes both exercised by
Lieux (`node.r`, `emptyText`).

## Contracts

### C-01 — `zone_rules.py` (family)
Produced by: A   Consumed by: A, B, C, D, E, F
Pure reads, a session's pending rows included (autoflush).
| function | returns | rule |
|---|---|---|
| `active_child_ids(db, location_id, *, exclude_id=None)` | `list[str]` | ids of ACTIVE `location` entities whose `parent_location_id` is `location_id`, oldest first (`entity.created_at`, then id), `exclude_id` left out |
| `is_zone(db, location_id)` | `bool` | at least one active child; None → False |
| `zone_ids(db, world_id)` | `set[str]` | distinct non-null parents of the world's active locations |
| `geographic_link_type(db, a, b)` | `"borde"` \| `"connects_to"` | `borde` iff either end is a zone |
| `require_visitable(db, location_id, *, what)` | `None` | raises `ZoneRefusal(ValueError)` « {what} : « {name} » est une zone, on ne peut s'y trouver que dans l'un de ses lieux » when a zone; None passes |
Written before any member; re-read after `require_visitable` (B's use).

### C-03 — the vocabulary
Produced by: A   Consumed by: A, D, F
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to",
"borde", "controls")` (a literal); `MAP_TOPOLOGY_TYPES: tuple[str, str] =
("connects_to", "borde")`; `borde_fact_content(a, b) -> f"{a} borde {b}."`.

### C-10 — `GET /api/locations/graph?mode=&center=`
Produced by: F   Consumed by: `consumers/lieux.js`
| mode | nodes | edges |
|---|---|---|
| `visitable` (default) | active locations not in `zone_ids` | `connects_to`, both ends kept |
| `zones` | active zones; `r = 30` when no parent | `borde`, both ends kept |
| `ego` | `center` (`r = 30`) and its active children | both types, both ends kept |
| `ego`, `center` not a zone | none; `"empty_text": "Ouvrez une zone."` | none |
| other | 422 | — |
Node `{id, name, coord_x, coord_y, is_zone[, r]}`; edge `{id, entity_a_id,
entity_b_id, direction, kind}`.

### C-11 — two primitive axes
Produced by: F   Consumed by: Lieux (the only consumer passing them)
`Graph.svelte`: a node's optional `r` sizes its circle and offsets its
label (`radiusOf(node) = node.r ?? NODE_R`); prop `emptyText = 'Aucun
nœud'`. `mount.js` passes `emptyText: data.emptyText` (undefined keeps the
default).

## Context

M1: one « Voir le graphe » with three modes in its head — the travel map (visitable places, `connects_to`), the zones (`borde`, top-level zones drawn larger) and an ego view of the zone open in the fiche. The primitive gains two optional axes, both first used here: a per-node radius and the empty-graph text.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `crud/locations.py`: `get_locations_graph(mode, center)` per C-10, `TOP_ZONE_RADIUS`, `GRAPH_MODES`;
   - `Graph.svelte`: `radiusOf`, the `emptyText` prop (C-11);
   - `mount.js`: passes `emptyText`;
   - `consumers/lieux.js`: three mode buttons, `defaultMeta`, `capabilities(meta)`, Ego's centre and double-click, `dashedKinds: ['borde']`;
   - `tooling/verify/checks/zone_graph.py`;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutations, each run with `python tooling/verify/checks/zone_graph.py`, then restored:
   - in `crud/locations.py`, replace `keep, edge_types = {e.id for e, _ in rows if e.id not in zones}, ("connects_to",)` with `keep, edge_types = {e.id for e, _ in rows}, ("connects_to",)` → `FAIL: (a) visitable nodes …`;
   - replace `(e.id in zones and loc.parent_location_id is None)` with `(e.id in zones)` → `FAIL: (b) radii …`;
   - replace `    elif center not in zones:` with `    elif center is None:` → `FAIL: (c) non-zone centre: …`;
   - in `Graph.svelte`, replace `r={radiusOf(node)}` with `r={NODE_R}` → `FAIL: (e) Graph.svelte circles ignore node.r`.
5. Commit message: `feat(zones): the Lieux graph's three modes (BRIEF-0101-f)`.

````diff
diff --git a/frontend/src/graph/Graph.svelte b/frontend/src/graph/Graph.svelte
index 55417f6..bc4866c 100644
--- a/frontend/src/graph/Graph.svelte
+++ b/frontend/src/graph/Graph.svelte
@@ -38,11 +38,17 @@
     onMoveNode = null,
     onNodeClick = null,
     onNodeDblClick = null,
+    // TICKET-0101 (BRIEF-0101-F, M1): what an empty graph says (the Lieux
+    // Ego mode: « Ouvrez une zone. »).
+    emptyText = 'Aucun nœud',
   } = $props();
 
   const GRAPH_W = 960;
   const GRAPH_H = 480;
   const NODE_R = 20;
+  // TICKET-0101 (BRIEF-0101-F, M1): a node may carry its own radius `r`
+  // (the Lieux Zones mode draws top-level zones larger); NODE_R otherwise.
+  const radiusOf = (node) => node.r ?? NODE_R;
   const DRAG_THRESHOLD = 5;
   const FORCE_ITERATIONS = 300;
 
@@ -294,7 +300,7 @@
      onwheel={layout === 'force' ? handleWheel : undefined}
      onmousedown={layout === 'force' ? handleCanvasMouseDown : undefined}>
   {#if nodes.length === 0}
-    <text x={GRAPH_W / 2} y={GRAPH_H / 2} text-anchor="middle" fill="var(--muted)" font-size="13">Aucun nœud</text>
+    <text x={GRAPH_W / 2} y={GRAPH_H / 2} text-anchor="middle" fill="var(--muted)" font-size="13">{emptyText}</text>
   {:else}
     {#each edges as edge (edge.id)}
       {@const a = nodeMap[edge.entity_a_id]}
@@ -324,11 +330,11 @@
         onclick={(e) => e.stopPropagation()}
         ondblclick={onNodeDblClick ? (e) => handleNodeDblClick(e, node.id) : undefined}
       >
-        <circle cx={node.x.toFixed(1)} cy={node.y.toFixed(1)} r={NODE_R}
+        <circle cx={node.x.toFixed(1)} cy={node.y.toFixed(1)} r={radiusOf(node)}
           fill={node.id === selectedNodeId ? 'var(--accent)' : 'var(--card)'}
           stroke={node.id === selectedNodeId ? 'var(--accent)' : 'var(--border)'}
           stroke-width={node.id === selectedNodeId ? 2.5 : 1.5} />
-        <text x={node.x.toFixed(1)} y={(node.y + NODE_R + 13).toFixed(1)}
+        <text x={node.x.toFixed(1)} y={(node.y + radiusOf(node) + 13).toFixed(1)}
           text-anchor="middle" fill="var(--text)" font-size="11"
           style="pointer-events:none;user-select:none">{node.name}</text>
       </g>
diff --git a/frontend/src/graph/consumers/lieux.js b/frontend/src/graph/consumers/lieux.js
index fc609dd..27996a9 100644
--- a/frontend/src/graph/consumers/lieux.js
+++ b/frontend/src/graph/consumers/lieux.js
@@ -8,8 +8,27 @@
    consumer already imports from that module (getSelectedEntityId). The
    shell document IS the document every Creation island receives as
    legacyDoc (creation/mount.js passes node.ownerDocument), so `document`
-   is passed. */
-import { selectEntity } from '../../creation/sheetState.svelte.js';
+   is passed.
+
+   TICKET-0101 (BRIEF-0101-F, M1): three modes in the head, one per
+   `GET /api/locations/graph?mode=` -- « Lieux visitables » (the travel
+   map, `connects_to`), « Zones » (`borde`; top-level zones larger through
+   the node's own `r`) and « Ego » (the zone open in the fiche and its
+   children; a double-click on a child zone recentres; anything else shows
+   « Ouvrez une zone. »). Mode and centre live in the mount's meta, the
+   relations consumer's pattern (consumers/relations.js: controls,
+   capabilities(meta), defaultMeta). Connecting two nodes in any mode posts
+   `connects_to`; the server derives `borde` whenever a zone is an end. A
+   `borde` edge is drawn dashed. */
+import { getSelectedEntityId, selectEntity } from '../../creation/sheetState.svelte.js';
+
+const MODES = [
+  { id: 'visitable', label: 'Lieux visitables' },
+  { id: 'zones', label: 'Zones' },
+  { id: 'ego', label: 'Ego' },
+];
+
+let lastNodes = [];
 
 async function api(path, options) {
   const res = await fetch(path, options);
@@ -30,40 +49,65 @@ async function api(path, options) {
 export default {
   chrome: {
     title: 'Carte des lieux',
-    helpText: 'Cliquez un nœud pour le sélectionner et ouvrir sa fiche, puis un second pour le connecter. Glissez pour repositionner. Cliquez un lien pour le supprimer.',
-  },
-  dashedKinds: [],
-
-  async load() {
-    return api('/api/locations/graph');
+    helpText: (meta) => (meta.mode === 'ego'
+      ? 'La zone ouverte dans la fiche et ses lieux enfants. Double-cliquez une zone enfant pour la recentrer. Cliquez un nœud pour ouvrir sa fiche, puis un second pour les relier.'
+      : 'Cliquez un nœud pour le sélectionner et ouvrir sa fiche, puis un second pour les relier (« borde » dès qu\'une zone est en jeu). Glissez pour repositionner. Cliquez un lien pour le supprimer.'),
+    controls: MODES.map((m) => ({
+      id: `mode-${m.id}`, kind: 'button',
+      label: (meta) => (meta.mode === m.id ? `● ${m.label}` : m.label),
+      onActivate: () => ({ mode: m.id, id: null }),
+    })),
   },
+  dashedKinds: ['borde'],
+  defaultMeta: { mode: 'visitable', id: null },
 
-  async onConnect(a, b) {
-    await api(`/api/entities/${encodeURIComponent(a)}/relations`, {
-      method: 'POST',
-      headers: { 'Content-Type': 'application/json' },
-      body: JSON.stringify({ other_entity_id: b, type: 'connects_to' }),
-    });
-  },
-
-  async onDeleteEdge(edgeId) {
-    if (!confirm('Supprimer cette connexion ?')) return false;
-    await api(`/api/relations/${encodeURIComponent(edgeId)}`, { method: 'DELETE' });
-  },
-
-  onNodeClick(nodeId) {
-    selectEntity(document, nodeId);
+  async load(meta) {
+    const mode = meta.mode || 'visitable';
+    let path = `/api/locations/graph?mode=${mode}`;
+    if (mode === 'ego') {
+      const center = meta.id || getSelectedEntityId();
+      if (!center) {
+        lastNodes = [];
+        return { nodes: [], edges: [], emptyText: 'Ouvrez une zone.' };
+      }
+      path += `&center=${encodeURIComponent(center)}`;
+    }
+    const data = await api(path);
+    lastNodes = data.nodes;
+    return { nodes: data.nodes, edges: data.edges, emptyText: data.empty_text };
   },
 
-  async onMoveNode(nodeId, x, y) {
-    // coord_x/coord_y are two scalar columns -- no merge discipline needed
-    // (TICKET-0025, BRIEF-0025-b; was a JSON read-merge-write).
-    const full = await api(`/api/entities/${encodeURIComponent(nodeId)}`);
-    const ext = Object.assign({}, full.extension, { coord_x: Math.round(x), coord_y: Math.round(y) });
-    await api(`/api/entities/${encodeURIComponent(nodeId)}`, {
-      method: 'PUT',
-      headers: { 'Content-Type': 'application/json' },
-      body: JSON.stringify({ entity: full, extension: ext }),
-    });
+  capabilities(meta) {
+    return {
+      onConnect: async (a, b) => {
+        await api(`/api/entities/${encodeURIComponent(a)}/relations`, {
+          method: 'POST',
+          headers: { 'Content-Type': 'application/json' },
+          body: JSON.stringify({ other_entity_id: b, type: 'connects_to' }),
+        });
+      },
+      onDeleteEdge: async (edgeId) => {
+        if (!confirm('Supprimer cette connexion ?')) return false;
+        await api(`/api/relations/${encodeURIComponent(edgeId)}`, { method: 'DELETE' });
+      },
+      onNodeClick: (nodeId) => { selectEntity(document, nodeId); },
+      onNodeDblClick: meta.mode === 'ego'
+        ? (nodeId) => {
+          const node = lastNodes.find((n) => n.id === nodeId);
+          return node && node.is_zone ? { id: nodeId } : null;
+        }
+        : null,
+      onMoveNode: async (nodeId, x, y) => {
+        // coord_x/coord_y are two scalar columns -- no merge discipline needed
+        // (TICKET-0025, BRIEF-0025-b; was a JSON read-merge-write).
+        const full = await api(`/api/entities/${encodeURIComponent(nodeId)}`);
+        const ext = Object.assign({}, full.extension, { coord_x: Math.round(x), coord_y: Math.round(y) });
+        await api(`/api/entities/${encodeURIComponent(nodeId)}`, {
+          method: 'PUT',
+          headers: { 'Content-Type': 'application/json' },
+          body: JSON.stringify({ entity: full, extension: ext }),
+        });
+      },
+    };
   },
 };
diff --git a/frontend/src/graph/mount.js b/frontend/src/graph/mount.js
index d0151f5..aff0eee 100644
--- a/frontend/src/graph/mount.js
+++ b/frontend/src/graph/mount.js
@@ -179,6 +179,7 @@ async function renderInto(containerId, consumerKey, meta) {
       onMoveNode: caps.onMoveNode || null,
       onNodeClick: wrapPlain(caps.onNodeClick),
       onNodeDblClick: wrapRemounter(containerId, caps.onNodeDblClick),
+      emptyText: data.emptyText,
     },
   });
   live[containerId] = { node, consumerKey, meta: effectiveMeta, instance, data };
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index 2e2d857..494923b 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -56,7 +56,7 @@ from ...schedule_reads import unresolved_npcs, where_is, who_is_at
 from ...tick_normalize import _EVENT_TYPES
 from ...writes.zone_promotion import promotion_preview
 from ...relation_orientation import MAP_TOPOLOGY_TYPES
-from ...zone_rules import ZoneRefusal, is_zone, require_visitable
+from ...zone_rules import ZoneRefusal, is_zone, require_visitable, zone_ids
 from ...writes import (
     KNOWLEDGE_LEVELS,
     NPC_GOAL_HORIZONS,
@@ -224,48 +224,68 @@ def delete_discoverable_detail(
     return {"deleted": detail_id}
 
 
-@router.get("/locations/graph")
-def get_locations_graph(db: DbSession = Depends(get_session)) -> dict:
-    """Active location nodes + connects_to edges — read-only, creator surface.
+# TICKET-0101 (M1): a top-level zone (no parent) is drawn larger than a
+# nested one; every other node takes the primitive's default radius.
+TOP_ZONE_RADIUS = 30
+GRAPH_MODES = ("visitable", "zones", "ego")
 
-    nodes: all active location entities joined to their extension (for
-    coord_x/coord_y). edges: connects_to relations whose both endpoints are
-    in nodes (dangling edges from soft-deleted locations are filtered out
-    server-side).
-    """
-    world_id = _world_id(db)
 
+@router.get("/locations/graph")
+def get_locations_graph(
+    mode: str = Query(default="visitable"),
+    center: Optional[str] = Query(default=None),
+    db: DbSession = Depends(get_session),
+) -> dict:
+    """The Lieux graph, read-only, creator surface (TICKET-0101, M1):
+
+    - `visitable` (default): the travel map -- active visitable locations,
+      `connects_to` edges between two of them.
+    - `zones`: active zones, `borde` edges between two of them; a zone
+      without a parent carries `r = TOP_ZONE_RADIUS`.
+    - `ego`: the zone `center`, larger, and its active children, with every
+      geographic edge among them; a `center` that is not a zone answers no
+      node and `empty_text` « Ouvrez une zone. ».
+
+    Nodes: `{id, name, coord_x, coord_y, is_zone[, r]}`; edges: `{id,
+    entity_a_id, entity_b_id, direction, kind}` (`kind` = relation type)."""
+    if mode not in GRAPH_MODES:
+        raise HTTPException(422, f"mode must be one of {GRAPH_MODES}")
+    world_id = _world_id(db)
     rows = db.exec(
         select(Entity, Location)
         .join(Location, Location.id == Entity.id)
-        .where(Entity.type == "location")
-        .where(Entity.world_id == world_id)
-        .where(Entity.status == "active")
+        .where(Entity.type == "location", Entity.world_id == world_id, Entity.status == "active")
         .order_by(Entity.name)
     ).all()
+    zones = zone_ids(db, world_id)
+    if mode == "visitable":
+        keep, edge_types = {e.id for e, _ in rows if e.id not in zones}, ("connects_to",)
+    elif mode == "zones":
+        keep, edge_types = {e.id for e, _ in rows if e.id in zones}, ("borde",)
+    elif center not in zones:
+        return {"nodes": [], "edges": [], "empty_text": "Ouvrez une zone."}
+    else:
+        keep = {center} | {e.id for e, loc in rows if loc.parent_location_id == center}
+        edge_types = MAP_TOPOLOGY_TYPES
+
+    def radius(e: Entity, loc: Location) -> dict:
+        big = e.id == center if mode == "ego" else (e.id in zones and loc.parent_location_id is None)
+        return {"r": TOP_ZONE_RADIUS} if big else {}
 
-    active_ids = {e.id for e, _ in rows}
     nodes = [
-        {"id": e.id, "name": e.name, "coord_x": loc.coord_x, "coord_y": loc.coord_y}
-        for e, loc in rows
+        {"id": e.id, "name": e.name, "coord_x": loc.coord_x, "coord_y": loc.coord_y,
+         "is_zone": e.id in zones, **radius(e, loc)}
+        for e, loc in rows if e.id in keep
     ]
-
     rels = db.exec(
-        select(Relation)
-        .where(Relation.world_id == world_id)
-        .where(Relation.type == "connects_to")
+        select(Relation).where(Relation.world_id == world_id, Relation.type.in_(edge_types))
     ).all()
     edges = [
-        {
-            "id": r.id,
-            "entity_a_id": r.entity_a_id,
-            "entity_b_id": r.entity_b_id,
-            "direction": r.direction,
-        }
+        {"id": r.id, "entity_a_id": r.entity_a_id, "entity_b_id": r.entity_b_id,
+         "direction": r.direction, "kind": r.type}
         for r in rels
-        if r.entity_a_id in active_ids and r.entity_b_id in active_ids
+        if r.entity_a_id in keep and r.entity_b_id in keep
     ]
-
     return {"nodes": nodes, "edges": edges}
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 2806c23..cf976ae 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17578,6 +17578,20 @@ is a zone. A room that receives a room becomes a zone.
 **Rejected.** R3, flattening batches: changes the generator's prompt.
 Reactivates if R1 makes buildings unmanageable.
 
+## THE LIEUX GRAPH HAS THREE MODES (TICKET-0101) -- VISITABLE, ZONES, EGO (BRIEF-0101-f, no schema change)
+
+**M1.** `GET /api/locations/graph?mode=` serves the travel map
+(`visitable`: visitable nodes, `connects_to` edges), the zones (`zones`:
+zone nodes, `borde` edges, a top-level zone with `r = 30`) and the ego view
+(`ego&center=`: the zone, larger, and its children, every geographic edge
+among them; a non-zone centre answers « Ouvrez une zone. »). The graph
+primitive gains two optional axes, both exercised by Lieux: a per-node
+radius (`node.r`, `NODE_R` otherwise) and `emptyText`. The Lieux consumer
+switches modes through three head buttons (the relations consumer's
+`controls` + `capabilities(meta)` pattern), draws `borde` dashed, and
+recentres Ego on a double-clicked child zone. Linking two nodes posts
+`connects_to`; the server derives the type.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/zone_graph.py b/tooling/verify/checks/zone_graph.py
new file mode 100644
index 0000000..e25c356
--- /dev/null
+++ b/tooling/verify/checks/zone_graph.py
@@ -0,0 +1,169 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-F) — the Lieux graph's three modes.
+
+DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
+DATABASE_URL set BEFORE any world_engine import), driven through
+`GET /api/locations/graph` with `TestClient(app, base_url=...)`, plus a
+text read of the three frontend files the mode switch lives in. Zero
+outcomes in any assertion is a FAIL.
+
+Fixture: zone D (top level) with children D1 (visitable) and D2 (a nested
+zone, child D2a); visitable T; D1-T `connects_to`, D-T `borde`, D2-D
+`borde`.
+
+Five assertions:
+  a. `mode=visitable` (and the default): nodes are the visitable locations
+     only (D1, D2a, T), edges `connects_to` only (D1-T), no node carries `r`.
+  b. `mode=zones`: nodes D and D2 only; D carries `r` = 30, D2 none; the
+     one edge is D2-D, `kind` `borde`.
+  c. `mode=ego&center=D`: D (with `r`), D1 and D2; edges among them only
+     (D2-D); `center=T` answers no node and `empty_text`
+     « Ouvrez une zone. ».
+  d. An unknown mode is a 422.
+  e. Frontend: `Graph.svelte` draws each circle with `radiusOf(node)` and
+     shows `{emptyText}`; `mount.js` passes `emptyText`; `consumers/lieux.js`
+     declares the three mode buttons, `dashedKinds: ['borde']` and an Ego
+     double-click.
+
+Named mutations: drop the `e.id not in zones` filter of `visitable` -> (a);
+give every zone `r` -> (b); keep `T` as an ego centre -> (c); revert the
+circle to `r={NODE_R}` -> (e).
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src"
+FRONT = ROOT / "frontend" / "src" / "graph"
+
+FAILURES: list[str] = []
+COUNTS: dict[str, int] = {}
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _ok(cond: bool, msg: str) -> int:
+    if not cond:
+        fail(msg)
+        return 0
+    return 1
+
+
+def _fresh_engine():
+    tmp_dir = tempfile.mkdtemp()
+    db_path = pathlib.Path(tmp_dir) / "check.db"
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    sys.path.insert(0, str(SRC))
+    for name in list(sys.modules):
+        if name == "world_engine" or name.startswith("world_engine."):
+            del sys.modules[name]
+
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    return engine
+
+
+def _seed(engine) -> dict[str, str]:
+    from sqlmodel import Session
+
+    from world_engine.models import Entity, Location, World
+    from world_engine.spatial_author import link_locations
+
+    ids: dict[str, str] = {}
+    with Session(engine) as db:
+        world = World(name="Graph check", is_active=True)
+        db.add(world)
+        db.commit()
+        for label, parent in (("D", None), ("D1", "D"), ("D2", "D"), ("D2a", "D2"), ("T", None)):
+            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
+            db.add(entity)
+            db.flush()
+            db.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
+            db.commit()
+            ids[label] = entity.id
+        for a, b in (("D1", "T"), ("D", "T"), ("D2", "D")):
+            link_locations(db, world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
+        db.commit()
+    return ids
+
+
+def _names(data, ids) -> set[str]:
+    back = {v: k for k, v in ids.items()}
+    return {back.get(n["id"], n["id"]) for n in data["nodes"]}
+
+
+def _edges(data, ids) -> set[tuple[str, str, str]]:
+    back = {v: k for k, v in ids.items()}
+    return {(*sorted((back[e["entity_a_id"]], back[e["entity_b_id"]])), e["kind"]) for e in data["edges"]}
+
+
+def check_routes(client, ids) -> None:
+    for query in ("", "?mode=visitable"):
+        data = client.get(f"/api/locations/graph{query}").json()
+        n = _ok(_names(data, ids) == {"D1", "D2a", "T"}, f"(a) visitable nodes {_names(data, ids)}")
+        n += _ok(_edges(data, ids) == {("D1", "T", "connects_to")}, f"(a) visitable edges {_edges(data, ids)}")
+        n += _ok(all("r" not in node for node in data["nodes"]), "(a) a visitable node carries r")
+        COUNTS["a"] = COUNTS.get("a", 0) + n
+    data = client.get("/api/locations/graph?mode=zones").json()
+    radii = {node["id"]: node.get("r") for node in data["nodes"]}
+    n = _ok(_names(data, ids) == {"D", "D2"}, f"(b) zone nodes {_names(data, ids)}")
+    n += _ok(radii.get(ids["D"]) == 30 and radii.get(ids["D2"]) is None, f"(b) radii {radii}")
+    n += _ok(_edges(data, ids) == {("D", "D2", "borde")}, f"(b) zone edges {_edges(data, ids)}")
+    COUNTS["b"] = n
+    data = client.get(f"/api/locations/graph?mode=ego&center={ids['D']}").json()
+    n = _ok(_names(data, ids) == {"D", "D1", "D2"}, f"(c) ego nodes {_names(data, ids)}")
+    n += _ok(_edges(data, ids) == {("D", "D2", "borde")}, f"(c) ego edges {_edges(data, ids)}")
+    n += _ok(any(node["id"] == ids["D"] and node.get("r") == 30 for node in data["nodes"]), "(c) ego centre not larger")
+    data = client.get(f"/api/locations/graph?mode=ego&center={ids['T']}").json()
+    n += _ok(data["nodes"] == [] and data.get("empty_text") == "Ouvrez une zone.", f"(c) non-zone centre: {data}")
+    COUNTS["c"] = n
+    resp = client.get("/api/locations/graph?mode=carte")
+    COUNTS["d"] = _ok(resp.status_code == 422, f"(d) unknown mode answered {resp.status_code}")
+
+
+def check_frontend() -> None:
+    graph = (FRONT / "Graph.svelte").read_text(encoding="utf-8")
+    mount = (FRONT / "mount.js").read_text(encoding="utf-8")
+    lieux = (FRONT / "consumers" / "lieux.js").read_text(encoding="utf-8")
+    n = _ok("r={radiusOf(node)}" in graph and "r={NODE_R}" not in graph, "(e) Graph.svelte circles ignore node.r")
+    n += _ok("{emptyText}" in graph, "(e) Graph.svelte does not show emptyText")
+    n += _ok("emptyText: data.emptyText" in mount, "(e) mount.js does not pass emptyText")
+    for needle in ("'visitable'", "'zones'", "'ego'", "dashedKinds: ['borde']", "onNodeDblClick"):
+        n += _ok(needle in lieux, f"(e) consumers/lieux.js lacks {needle}")
+    COUNTS["e"] = n
+
+
+def main() -> int:
+    engine = _fresh_engine()
+    from fastapi.testclient import TestClient
+
+    from world_engine.cockpit.app import app
+
+    ids = _seed(engine)
+    check_routes(TestClient(app, base_url="http://127.0.0.1"), ids)
+    check_frontend()
+
+    for key in ("a", "b", "c", "d", "e"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero outcomes examined")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_graph — "
+        f"(a) visitable mode [{COUNTS['a']}], (b) zones mode, top-level radius [{COUNTS['b']}], "
+        f"(c) ego mode [{COUNTS['c']}], (d) unknown mode refused [{COUNTS['d']}], "
+        f"(e) primitive radius + empty text, three mode buttons [{COUNTS['e']}]"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Making Ego follow the fiche live on every selection: it centres on the fiche's zone when the mode opens or the graph refreshes (↻), and on a double-clicked child zone.
- Per-mode node positions: the three modes share each location's `coord_x/coord_y`.
- Any change to the relations consumer or the review consumer.
- A new graph spec key (`graph_primitive.py` rule 9 stays closed).

## Invariants to defend

- **The graph primitive is the ONE graph component** (`graph_primitive.py`): the new axes are props; the primitive still never fetches or writes (rule 7).
- **`connects_to` and `borde` never touch a social reader**: the graph route reads them for the map only.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `graph_primitive.py` fails.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm ci` warns that `package.json` asks for a newer Node than the local one: proceed if the build succeeds, and report the version.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff plus `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `zone_graph.py` → `PASS: zone_graph — (a) visitable mode [6], (b) zones mode, top-level radius [3], (c) ego mode [4], (d) unknown mode refused [1], (e) primitive radius + empty text, three mode buttons [8]`.
- `graph_primitive.py`, `relation_graph.py`, `frontend_build_fresh.py`, `decisions_index.py` → `PASS`.
- The four named mutations failed as stated.
- `corpus_gate.py` → 135/135.
- Live: Lieux → « Voir le graphe » → « ● Lieux visitables » shows no zone; « Zones » shows the zones with `borde` dashed; « Ego » with no zone open shows « Ouvrez une zone. », with the Forêt verte open and ↻ shows it larger, its children around.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE LIEUX GRAPH HAS THREE MODES (TICKET-0101) -- VISITABLE, ZONES, EGO (BRIEF-0101-f, no schema change)` — in the diff.
