<!-- slug: zone-children-neighbours -->
# BRIEF 0101-E — "A zone's children take its neighbours"

Lot: LOT-0101-zones.md (authoritative on conflict)
Depends on: A (C-04), C (C-06, C-08)
Commit header for decisions: `(BRIEF-0101-e, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- BRIEFS 0101-A to -D are committed: `crud/zone_hooks.py` defines `promote_for_child` and `take_promotion_gatherings`; `PromotionModal.svelte` exports `gate`.
- `src/world_engine/cockpit/routes/room_batch.py:101` → `class RoomBatchCommitBody(BaseModel):`, whose last field is `    confirmed_edges: dict[str, bool] = {}`; `:150` → `            room_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data, facets=facets)`; `    except HTTPException as exc:` followed by `        return {"ok": False, "error": str(exc.detail)}`
- `src/world_engine/cockpit/crud/__init__.py:261` → `__all__ = ["router", "ENTITY_TYPE_REGISTRY"]`
- `src/world_engine/cockpit/crud/entities.py`: `    confirm_promotion: bool = False` (C) is the last field of `EntityWriteBody`; `    promote_for_child(db, entity, ext_row, confirmed=body.confirm_promotion)` (C)
- `frontend/src/creation/RoomBatch.svelte:46` → `  import { roomBatchState, resetRoomBatch } from './roomBatch.svelte.js';`; `  async function commit() {`
- `frontend/src/creation/roomBatch.svelte.js:27` → `  confirmedEdges: {},`
- `frontend/src/creation/Sheet.svelte` → `      {#if type === 'faction'}` (the Roles section) after the extension fields
- `frontend/src/creation/Field.svelte:27` → ``  const id = $derived(`${idPrefix}-${field.name}`);``

## Facts carried

### R-06 — the room batch nests and links each room to its parent [M]
Opened: `cockpit/routes/room_batch.py:101-262`.
Finding: K1 — every committed room's parent–child adjacency is written as a
link (`_commit_batch_tree_edges`, `:159-168`); a room's parent can be a
batch room (`_commit_batch_rooms`, `:109-157`); rooms are created through
`crud._create_entity_core` (`:151`); the commit catches `HTTPException` and
returns `{"ok": False, "error": str(exc.detail)}` (`:246-248`).
Consequence: the anchor, and any room that receives one, becomes a zone;
tree edges are `borde` once the type is derived (A). The anchor's
promotion goes through the S1 confirmation (C, E).

### R-19 — the fiche's location save [M]
Opened: `frontend/src/creation/Sheet.svelte:451-486` (`saveSheet`, the
location-type gate opening `LocationTypeModal`), `:558-640`
(`submitEntity`); `LocationTypeModal.svelte` (whole); `Modal.svelte`
(whole); `Field.svelte:27, 89-106` (`id = author-x-<name>`, `entity_ref`
select); `factsDraft.svelte.js` (the create-draft store pattern).
Consequence: `PromotionModal` follows `LocationTypeModal`'s instance shape;
the neighbour picker listens to `#author-x-parent_location_id` and keeps its
draft in a store like `factsDraft`.

## Contracts

### C-04 — `spatial_author.link_locations`
Produced by: A   Consumed by: A (`create_relation`, room batch), E
`link_locations(db, *, world_id, entity_a_id, entity_b_id, changed_by) ->
Relation`, commit-free. Type = `geographic_link_type`. The pair's existing
geographic row (`find_map_relation`, either order, oldest) is returned
as is when its type matches, retyped in place otherwise; else a new row
(`connects_to` through `connect_locations`, doors for both ends; `borde`
through `write_relation`, no door). A row retyped to `connects_to` gets
`materialize_doors`. `ValueError` (C-02) propagates.
`create_relation` routes any `MAP_TOPOLOGY_TYPES` body through it (422 on
`ValueError`); `update_relation` maps `ValueError` to 409.

### C-06 — `promotion_preview` (the dict)
Produced by: C   Consumed by: C (route, 409, modal), E (room batch gate)
`promotion_preview(db, parent_id, *, child_id=None) -> dict`:
`{"location_id", "location_name", "promotes": bool, "needs_confirmation":
bool, "target_is_zone": bool, "links": [{id, other_id, other_name}], "beings": [{id, name,
character_type}], "schedules": [{npc_id, npc_name, phase}], "items": [{id,
name}], "details": [{id, subject}], "gatherings": [{id, label}]}`.
`promotes` False (every list empty) when `parent_id` is None, not a
location, or has an active child other than `child_id`. `links` are the
parent's `connects_to` rows only. `needs_confirmation` = `promotes` and any
list non-empty. `target_is_zone` = `is_zone(child_id)` (False without a
`child_id`). Served read-only by `GET /api/locations/{id}/promotion-
preview?child_id=`.
Amended by AMENDMENT-0101-01 (`target_is_zone` added).

### C-08 — the CRUD seam and S1
Produced by: C   Consumed by: C, E
`EntityWriteBody.confirm_promotion: bool = False`.
`promote_for_child(db, entity, ext, *, confirmed, prior_parent_id=None,
prior_status=None)`: acts when `entity` is an active location whose
`ext.parent_location_id` is set and either differs from `prior_parent_id`
or `prior_status != "active"`; calls `promote_parent`:
| preview | `confirmed` | result |
|---|---|---|
| `promotes` False | any | nothing |
| `needs_confirmation` False | any | applied |
| `needs_confirmation` True, `target_is_zone` True | any | 409, detail a string: « « {child} » est déjà une zone : le contenu de « {parent} » ne peut pas y être déplacé. Rattachez d'abord un lieu visitable à « {parent} », ou videz « {parent} ». »; nothing written |
| `needs_confirmation` True | False | 409 `{"code": "promotion_required", "preview": <C-06>}` |
| `needs_confirmation` True | True | applied; moved beings `close_open_memberships` + `attach_on_arrival(child)` |
Gathering ids to dissolve (emptied ones, the parent's open ones) are parked
on `db.info`; `take_promotion_gatherings(db)` returns and removes them; the
caller passes them to `dissolve_emptied` after its commit.
`_mutation_apply_status_change` refuses a reactivation whose preview needs
confirmation. `PromotionModal.gate` opens no dialog when `target_is_zone`:
the save goes through and the 409 message reaches the fiche's status line.
Amended by AMENDMENT-0101-01 (the `target_is_zone` row).

### C-09 — children take the parent's neighbours
Produced by: E   Consumed by: E
`GET /api/locations/{id}/neighbours` → `[{id, name, is_zone}]`, the active
locations joined to `id` by a geographic row, by name.
`EntityWriteBody.link_to: list[str] = []`; on a location create, after any
promotion, each id (deduplicated, self skipped) goes through
`link_locations` (422 on `ValueError`).
`RoomBatchCommitBody.confirm_promotion: bool = False` (passed into every
room's `EntityWriteBody`) and `room_links: dict[str, list[str]] = {}`
(local_id → ids, linked after the tree and supplementary edges, rooms not
committed skipped); after the commit, `dissolve_emptied(take_promotion_
gatherings(db))`; an `HTTPException` whose detail is a dict reports its
`code` as `error`.

## Context

K's second row: creating a child of a zone offers the zone's neighbours as checkboxes; a ticked visitable neighbour becomes a `connects_to`, a ticked zone a `borde`. R1 brings the same to the room batch: the anchor's promotion goes through the dialog, and each top-level room may take the anchor's neighbours — otherwise a building would be unreachable from its street once it holds rooms.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `crud/zone_hooks.py`: `link_new_location`;
   - `crud/entities.py`: `EntityWriteBody.link_to`; `link_new_location` after the promotion in `_create_static_entity_core`;
   - `crud/locations.py`: `GET /api/locations/{location_id}/neighbours`;
   - `routes/room_batch.py`: `confirm_promotion` and `room_links` on the body, passed into every room body, `_commit_room_links`, the post-commit dissolve, the `code` of a dict detail as `error`;
   - `crud/__init__.py`: re-exports `take_promotion_gatherings`;
   - `frontend/src/creation/neighbourDraft.svelte.js`, `NeighbourPicker.svelte`; `Sheet.svelte`: the « Voisins » section on a new location, `link_to` on the create, the draft reset;
   - `RoomBatch.svelte` and `roomBatch.svelte.js`: the anchor neighbours per top-level room, `roomLinks`, the `PromotionModal` gate before the commit;
   - `tooling/verify/checks/zone_children.py`;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutations, each run with `python tooling/verify/checks/zone_children.py`, then restored:
   - in `crud/entities.py`, replace `        link_new_location(db, entity, body.link_to)` with `        pass` → `FAIL: (b) E-V is not connects_to`;
   - in `room_batch.py`, delete `        supplementary_written += _commit_room_links(body.room_links, room_id_map, world_id, db)` → `FAIL: (e) R1-S not linked by connects_to`;
   - in `room_batch.py`, replace `confirm_promotion=confirm_promotion,` with `confirm_promotion=False,` → `FAIL: (e) confirmed batch: {'ok': False, 'error': 'promotion_required'}`.
5. Commit message: `feat(zones): a zone's children take its neighbours; room batch promotes its anchor (BRIEF-0101-e)`.

````diff
diff --git a/frontend/src/creation/NeighbourPicker.svelte b/frontend/src/creation/NeighbourPicker.svelte
new file mode 100644
index 0000000..e91b440
--- /dev/null
+++ b/frontend/src/creation/NeighbourPicker.svelte
@@ -0,0 +1,46 @@
+<script>
+  /* TICKET-0101 (BRIEF-0101-E, K): "creating any child of a zone -- the
+     zone's neighbours are offered as checkboxes". Shown in a NEW location's
+     fiche. The parent is the fiche's own `parent_location_id` select
+     (#author-x-parent_location_id, read like every field at save); this
+     component listens to it, lists that parent's neighbours, and records
+     the ticked ones in neighbourDraft.svelte.js. A visitable neighbour
+     becomes a `connects_to`, a zone a `borde` -- decided by the server. */
+  import { onMount } from 'svelte';
+  import { neighbourDraftState, toggleNeighbour, resetNeighbourDraft, loadNeighbours } from './neighbourDraft.svelte.js';
+
+  let { legacyDoc } = $props();
+
+  let neighbours = $state([]);
+  let parentChosen = $state(false);
+
+  async function refresh(select) {
+    resetNeighbourDraft();
+    parentChosen = !!(select && select.value);
+    neighbours = parentChosen ? await loadNeighbours(select.value) : [];
+  }
+
+  onMount(() => {
+    const select = legacyDoc.getElementById('author-x-parent_location_id');
+    if (!select) return undefined;
+    const onChange = () => refresh(select);
+    select.addEventListener('change', onChange);
+    refresh(select);
+    return () => select.removeEventListener('change', onChange);
+  });
+</script>
+
+{#if !parentChosen}
+  <div style="font-size:12px; color:var(--muted)">Choisissez un lieu parent pour proposer ses voisins.</div>
+{:else if neighbours.length === 0}
+  <div style="font-size:12px; color:var(--muted)">Le lieu parent n'a aucun voisin.</div>
+{:else}
+  <div style="font-size:12px; color:var(--muted); margin-bottom:4px">Cochez les voisins du parent qui touchent aussi ce lieu.</div>
+  {#each neighbours as n (n.id)}
+    <label style="display:flex; gap:6px; align-items:center; font-size:12px">
+      <input type="checkbox" checked={neighbourDraftState.ids.includes(n.id)}
+        onchange={(e) => toggleNeighbour(n.id, e.currentTarget.checked)}>
+      {n.name}{n.is_zone ? ' (zone : lien « borde »)' : ''}
+    </label>
+  {/each}
+{/if}
diff --git a/frontend/src/creation/RoomBatch.svelte b/frontend/src/creation/RoomBatch.svelte
index 4dd40ae..c456b17 100644
--- a/frontend/src/creation/RoomBatch.svelte
+++ b/frontend/src/creation/RoomBatch.svelte
@@ -44,6 +44,8 @@
   import { reviewRegister } from './review/registry.js';
   import Review from './Review.svelte';
   import { roomBatchState, resetRoomBatch } from './roomBatch.svelte.js';
+  import PromotionModal from './PromotionModal.svelte';
+  import { loadNeighbours } from './neighbourDraft.svelte.js';
 
   let { legacyDoc } = $props();
 
@@ -52,6 +54,26 @@
   // (bind:value={r.location_type} below), so it reads the typed name
   // directly instead of locationType.js's readLocationTypeName DOM read.
   let locTypeModal;
+  // TICKET-0101 (BRIEF-0101-E, R1): the anchor becomes a zone when its first
+  // room commits -- confirmed through PromotionModal -- and each top-level
+  // room may take some of the anchor's neighbours (room_links).
+  let promotionModal;
+  let anchorNeighbours = $state([]);
+
+  $effect(() => {
+    const anchorId = roomBatchState.anchorId;
+    if (!anchorId || !roomBatchState.drafts) return;
+    loadNeighbours(anchorId).then((rows) => { anchorNeighbours = rows; });
+  });
+
+  function topLevelRooms() {
+    return (roomBatchState.drafts.rooms || []).filter((r) => !r.parent_room && isAccepted(r.local_id));
+  }
+
+  function toggleRoomLink(localId, neighbourId, checked) {
+    const current = (roomBatchState.roomLinks[localId] || []).filter((x) => x !== neighbourId);
+    roomBatchState.roomLinks = { ...roomBatchState.roomLinks, [localId]: checked ? [...current, neighbourId] : current };
+  }
 
   async function api(path, opts = {}) {
     const res = await fetch(path, opts);
@@ -242,6 +264,11 @@
   });
 
   async function commit() {
+    const first = topLevelRooms()[0];
+    await promotionModal.gate(roomBatchState.anchorId, null, first ? first.name : '', (confirmed) => commitBatch(confirmed));
+  }
+
+  async function commitBatch(confirmPromotion) {
     commitPending = true;
     const rooms = (roomBatchState.drafts.rooms || []).map((r) => ({ local_id: r.local_id, name: r.name, parent_room: r.parent_room, result: r.result }));
     const edges = (roomBatchState.coherence && roomBatchState.coherence.edges) || [];
@@ -252,6 +279,7 @@
         body: JSON.stringify({
           anchor_id: roomBatchState.anchorId, rooms, accepted: roomBatchState.accepted,
           edges, confirmed_edges: roomBatchState.confirmedEdges,
+          confirm_promotion: confirmPromotion, room_links: roomBatchState.roomLinks,
         }),
       });
     } catch (e) {
@@ -288,6 +316,7 @@
     <button class="btn-icon" onclick={resetRoomBatch}>Fermer</button>
   </div>
   <LocationTypeModal bind:this={locTypeModal} {legacyDoc} />
+  <PromotionModal bind:this={promotionModal} />
   <div style="padding:10px 14px; max-height:600px; overflow-y:auto">
     {#if !roomBatchState.manifest}
       <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px;">
@@ -355,6 +384,24 @@
         <span style="font-size:12px; color:var(--muted)">{coherenceStatus}</span>
         <button class="btn-send" onclick={commit} style="margin-left:auto" disabled={commitPending}>Commiter le lot</button>
       </div>
+      {#if anchorNeighbours.length && topLevelRooms().length}
+        <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
+          <div class="field-section-title">Accès depuis les voisins de « {roomBatchState.anchorName} »</div>
+          <div style="font-size:11px; color:var(--muted); margin-bottom:4px">L'ancre devient une zone : cochez, pour chaque pièce de premier niveau, les voisins qui y mènent.</div>
+          {#each topLevelRooms() as r (r.local_id)}
+            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center; font-size:12px; margin-top:4px">
+              <span style="min-width:140px">{r.name}</span>
+              {#each anchorNeighbours as n (n.id)}
+                <label style="display:flex; gap:4px; align-items:center">
+                  <input type="checkbox" checked={(roomBatchState.roomLinks[r.local_id] || []).includes(n.id)}
+                    onchange={(e) => toggleRoomLink(r.local_id, n.id, e.currentTarget.checked)}>
+                  {n.name}{n.is_zone ? ' (zone)' : ''}
+                </label>
+              {/each}
+            </div>
+          {/each}
+        </div>
+      {/if}
       {#if (roomBatchState.drafts.skipped || []).length}
         <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:10px;">
           <div class="field-section-title">Écartées à la génération</div>
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 25ad642..9b45918 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -80,6 +80,8 @@
   import { readFieldValue } from './fields.js';
   import LocationTypeModal from './LocationTypeModal.svelte';
   import PromotionModal from './PromotionModal.svelte';
+  import NeighbourPicker from './NeighbourPicker.svelte';
+  import { neighboursForCreate, resetNeighbourDraft } from './neighbourDraft.svelte.js';
   import Field from './Field.svelte';
   import GeometryEditor from './GeometryEditor.svelte';
   import DoorsEditor from './DoorsEditor.svelte';
@@ -586,6 +588,7 @@
         ...(isNewSave ? { facets: factsDraftForCreate() } : {}),
         ...(isNewSave && mutationId ? { mutation_id: mutationId } : {}),
         ...(confirmPromotion ? { confirm_promotion: true } : {}),
+        ...(isNewSave && type === 'location' ? { link_to: neighboursForCreate() } : {}),
       });
       let detail = isNewSave
         ? await api('/api/entities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
@@ -634,6 +637,7 @@
         resetGeneratePanel();
         resetDraftRoles();
         resetFactsDraft();
+        resetNeighbourDraft();
         resetPendingDrafts();
       }
 
@@ -752,6 +756,12 @@
         {/each}
       </div></div>
 
+      {#if isNew && type === 'location'}
+        <div class="field-section"><div class="field-section-title">Voisins</div>
+          <NeighbourPicker {legacyDoc} />
+        </div>
+      {/if}
+
       {#if type === 'faction'}
         <div class="field-section"><div class="field-section-title">Roles</div>
           <div id="author-roles"><RolesEditor {isNew} factionId={isNew ? null : detail.id} /></div>
diff --git a/frontend/src/creation/neighbourDraft.svelte.js b/frontend/src/creation/neighbourDraft.svelte.js
new file mode 100644
index 0000000..8e0ff08
--- /dev/null
+++ b/frontend/src/creation/neighbourDraft.svelte.js
@@ -0,0 +1,32 @@
+/* TICKET-0101 (BRIEF-0101-E, K). Draft state for a NEW location's
+   neighbours: the parent's geographic neighbours the creator ticked, sent
+   as the create body's `link_to` (crud/zone_hooks.link_new_location links
+   each with the type the server derives). Written by NeighbourPicker.svelte,
+   read by Sheet.svelte's submitEntity via neighboursForCreate(), reset with
+   the other create drafts. */
+export const neighbourDraftState = $state({ ids: [] });
+
+export function resetNeighbourDraft() {
+  neighbourDraftState.ids = [];
+}
+
+export function toggleNeighbour(id, checked) {
+  const others = neighbourDraftState.ids.filter((x) => x !== id);
+  neighbourDraftState.ids = checked ? [...others, id] : others;
+}
+
+export function neighboursForCreate() {
+  return [...neighbourDraftState.ids];
+}
+
+/** GET /api/locations/{id}/neighbours -- [{id, name, is_zone}], [] on any
+ *  failure (the checkboxes are an offer, never a gate). */
+export async function loadNeighbours(locationId) {
+  if (!locationId) return [];
+  try {
+    const res = await fetch(`/api/locations/${encodeURIComponent(locationId)}/neighbours`);
+    return res.ok ? await res.json() : [];
+  } catch (_err) {
+    return [];
+  }
+}
diff --git a/frontend/src/creation/roomBatch.svelte.js b/frontend/src/creation/roomBatch.svelte.js
index 7ffcd6b..523cb42 100644
--- a/frontend/src/creation/roomBatch.svelte.js
+++ b/frontend/src/creation/roomBatch.svelte.js
@@ -25,6 +25,9 @@ export const roomBatchState = $state({
   coherence: null,         // {edges: [{id, a_id, b_id, a_local, b_local, reason}], unresolved, notes}
   accepted: {},
   confirmedEdges: {},
+  // TICKET-0101 (BRIEF-0101-E, R1): local_id -> anchor neighbour ids ticked
+  // for that top-level room; sent as the commit's `room_links`.
+  roomLinks: {},
   graphOpen: false,
   commitResult: null,
 });
@@ -42,6 +45,7 @@ export function resetRoomBatch() {
   roomBatchState.coherence = null;
   roomBatchState.accepted = {};
   roomBatchState.confirmedEdges = {};
+  roomBatchState.roomLinks = {};
   roomBatchState.graphOpen = false;
   roomBatchState.commitResult = null;
 }
diff --git a/src/world_engine/cockpit/crud/__init__.py b/src/world_engine/cockpit/crud/__init__.py
index 353f0d8..fa6a324 100644
--- a/src/world_engine/cockpit/crud/__init__.py
+++ b/src/world_engine/cockpit/crud/__init__.py
@@ -258,4 +258,6 @@ from .prompts import (
     update_prompt_text,
 )
 
+from .zone_hooks import take_promotion_gatherings
+
 __all__ = ["router", "ENTITY_TYPE_REGISTRY"]
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index b9cce9e..9ff5acd 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -101,7 +101,7 @@ from ._shared import (
     _validate_entity_ref,
     _world_id,
 )
-from .zone_hooks import promote_for_child, take_promotion_gatherings
+from .zone_hooks import link_new_location, promote_for_child, take_promotion_gatherings
 from .entity_runtime import (
     _build_runtime_ext_kwargs,
     _insert_runtime_ext_row,
@@ -399,6 +399,9 @@ class EntityWriteBody(BaseModel):
     # TICKET-0101 (S1): the creator saw `promotion_preview` and confirmed that
     # this location's parent becomes a zone and its contents move here.
     confirm_promotion: bool = False
+    # TICKET-0101 (K): on a location create, the parent's neighbours the
+    # creator ticked; each is linked with its derived type.
+    link_to: list[str] = []
 
 
 class NpcPricesBody(BaseModel):
@@ -646,6 +649,8 @@ def _create_static_entity_core(body: EntityWriteBody, db: DbSession, entity_type
     db.flush()
     db.add(ext_row)
     promote_for_child(db, entity, ext_row, confirmed=body.confirm_promotion)
+    if entity_type == "location":
+        link_new_location(db, entity, body.link_to)
 
     if pending_faction_id:
         # Creator authority (this create/accept IS the creator action) — not
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index 1bf27d6..2e2d857 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -55,7 +55,8 @@ from ...prompt_store import current_prompt, get_version, list_versions
 from ...schedule_reads import unresolved_npcs, where_is, who_is_at
 from ...tick_normalize import _EVENT_TYPES
 from ...writes.zone_promotion import promotion_preview
-from ...zone_rules import ZoneRefusal, require_visitable
+from ...relation_orientation import MAP_TOPOLOGY_TYPES
+from ...zone_rules import ZoneRefusal, is_zone, require_visitable
 from ...writes import (
     KNOWLEDGE_LEVELS,
     NPC_GOAL_HORIZONS,
@@ -345,6 +346,26 @@ def _schedule_npc_brief(npc_id: str, db: DbSession) -> dict:
     return {"npc_id": npc_id, "name": entity.name if entity else npc_id}
 
 
+@router.get("/locations/{location_id}/neighbours")
+def get_location_neighbours(location_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
+    """The active locations linked to `location_id` by a geographic relation
+    (`connects_to` or `borde`), each with `is_zone` -- read-only, the
+    neighbour checkboxes offered when a child is created (TICKET-0101, K)."""
+    _get_entity(db, location_id)
+    rels = db.exec(
+        select(Relation).where(
+            Relation.type.in_(MAP_TOPOLOGY_TYPES),
+            (Relation.entity_a_id == location_id) | (Relation.entity_b_id == location_id),
+        )
+    ).all()
+    other_ids = {r.entity_b_id if r.entity_a_id == location_id else r.entity_a_id for r in rels}
+    rows = db.exec(
+        select(Entity).where(Entity.id.in_(other_ids), Entity.type == "location", Entity.status == "active")
+        .order_by(Entity.name)
+    ).all() if other_ids else []
+    return [{"id": e.id, "name": e.name, "is_zone": is_zone(db, e.id)} for e in rows]
+
+
 @router.get("/locations/{location_id}/promotion-preview")
 def get_promotion_preview(
     location_id: str,
diff --git a/src/world_engine/cockpit/crud/zone_hooks.py b/src/world_engine/cockpit/crud/zone_hooks.py
index 167734c..9848567 100644
--- a/src/world_engine/cockpit/crud/zone_hooks.py
+++ b/src/world_engine/cockpit/crud/zone_hooks.py
@@ -33,6 +33,7 @@ from sqlmodel import Session as DbSession
 
 from ...gathering import attach_on_arrival, close_open_memberships
 from ...models import Entity
+from ...spatial_author import link_locations
 from ...writes.zone_promotion import apply_promotion, promotion_preview
 
 _PENDING_KEY = "zone_promotion_gatherings"
@@ -85,6 +86,24 @@ def promote_for_child(
     return promote_parent(db, parent_id=parent_id, child_id=entity.id, confirmed=confirmed)
 
 
+def link_new_location(db: DbSession, entity: Entity, neighbour_ids: list[str]) -> None:
+    """K, "creating any child of a zone": the neighbours the creator ticked
+    are linked to the new location through `link_locations`, which derives
+    each type (`connects_to` to a visitable neighbour, `borde` to a zone).
+    Runs after any promotion, so the parent is already a zone. A neighbour
+    that is not a location is a 422."""
+    for neighbour_id in dict.fromkeys(neighbour_ids or []):
+        if neighbour_id == entity.id:
+            continue
+        try:
+            link_locations(
+                db, world_id=entity.world_id, entity_a_id=entity.id, entity_b_id=neighbour_id,
+                changed_by="creator",
+            )
+        except ValueError as exc:
+            raise HTTPException(422, str(exc))
+
+
 def take_promotion_gatherings(db: DbSession) -> set[str]:
     """The gathering ids parked by `promote_parent`, removed from `db.info`."""
     return db.info.pop(_PENDING_KEY, set())
diff --git a/src/world_engine/cockpit/routes/room_batch.py b/src/world_engine/cockpit/routes/room_batch.py
index b548fd2..bc839f4 100644
--- a/src/world_engine/cockpit/routes/room_batch.py
+++ b/src/world_engine/cockpit/routes/room_batch.py
@@ -30,6 +30,7 @@ from ...room_batch_author import _name_key  # commit-time name resolution must
 from ...room_batch_author import generate_room_batch_draft as _generate_room_batch_draft
 from ...room_batch_author import generate_room_batch_manifest as _generate_room_batch_manifest
 from ...room_batch_author import propose_batch_coherence as _propose_batch_coherence
+from ...gathering import dissolve_emptied
 from ...spatial_author import link_locations, location_classification
 from .. import crud as _crud
 
@@ -104,10 +105,15 @@ class RoomBatchCommitBody(BaseModel):
     accepted: dict[str, bool] = {}
     edges: list[RoomBatchCommitEdge] = []
     confirmed_edges: dict[str, bool] = {}
+    # TICKET-0101 (R1): the creator confirmed the anchor's promotion into a
+    # zone (S1), and, per room local_id, the anchor neighbours ticked for it.
+    confirm_promotion: bool = False
+    room_links: dict[str, list[str]] = {}
 
 
 def _commit_batch_rooms(
     rooms_in: list[dict], accepted: dict[str, bool], anchor_id: str, world_id: str, db: Session,
+    confirm_promotion: bool = False,
 ) -> tuple[dict[str, str], dict[str, str], list[dict]]:
     """Rooms only, dependency order (parent before child). Server-authoritative
     cascade (mirrors _region_resolve_location_parent's SHAPE, regions.py):
@@ -147,7 +153,9 @@ def _commit_batch_rooms(
             }
             # TICKET-0091, BRIEF-0091-E: the room keeps only its description, as a fact.
             facets = {"description": facet_text(draft.get("facets") or {}, "description")}
-            room_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data, facets=facets)
+            room_body = _crud.EntityWriteBody(
+                entity=entity_data, extension=ext_data, facets=facets, confirm_promotion=confirm_promotion,
+            )
             room_entity = _crud._create_entity_core(room_body, db)
             room_id_map[local_id] = room_entity.id
             parent_entity_of[room_entity.id] = parent_entity_id
@@ -194,6 +202,21 @@ def _commit_batch_edges(
     return written, unresolved
 
 
+def _commit_room_links(room_links: dict[str, list[str]], room_id_map: dict[str, str], world_id: str, db: Session) -> int:
+    """R1 (TICKET-0101): each committed room's ticked anchor neighbours,
+    linked with the type `link_locations` derives. A room that was rejected
+    or never committed writes nothing."""
+    written = 0
+    for local_id, neighbour_ids in room_links.items():
+        room_id = room_id_map.get(local_id)
+        if room_id is None:
+            continue
+        for neighbour_id in dict.fromkeys(neighbour_ids):
+            link_locations(db, world_id=world_id, entity_a_id=room_id, entity_b_id=neighbour_id, changed_by="creator")
+            written += 1
+    return written
+
+
 def _anchor_t1_note(anchor_location: Optional[Location], world_id: str, db: Session) -> Optional[str]:
     """T1: an anchor with NULL bounds or NULL classification never blocks
     the batch -- doors on that side degrade to the origin (placement.py).
@@ -234,20 +257,23 @@ def commit_room_batch(
 
     try:
         room_id_map, parent_entity_of, committed_rooms = _commit_batch_rooms(
-            rooms_in, body.accepted, body.anchor_id, world_id, db,
+            rooms_in, body.accepted, body.anchor_id, world_id, db, body.confirm_promotion,
         )
         tree_written = _commit_batch_tree_edges(parent_entity_of, world_id, db)
         supplementary_written, unresolved = _commit_batch_edges(
             edges_in, body.confirmed_edges, room_id_map, world_id, db,
         )
+        supplementary_written += _commit_room_links(body.room_links, room_id_map, world_id, db)
         notes = []
         t1_note = _anchor_t1_note(anchor_location, world_id, db)
         if t1_note:
             notes.append(t1_note)
         db.commit()
+        dissolve_emptied(_crud.take_promotion_gatherings(db), db)
     except HTTPException as exc:
         db.rollback()
-        return {"ok": False, "error": str(exc.detail)}
+        detail = exc.detail.get("code") if isinstance(exc.detail, dict) else exc.detail
+        return {"ok": False, "error": str(detail)}
     except IntegrityError as exc:
         db.rollback()
         return {"ok": False, "error": f"Database integrity error: {exc}"}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index a3df818..2806c23 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17564,6 +17564,20 @@ without moving it. Refuses a database older than v2.11; idempotent.
 **Rejected.** O2, the tuple alone with the index left as it was: the
 schema would claim `borde` is social.
 
+## A ZONE'S CHILDREN TAKE ITS NEIGHBOURS (TICKET-0101) -- CHECKBOXES, ROOM BATCH (BRIEF-0101-e, no schema change)
+
+**K, R1.** Creating a location under a parent offers the parent's
+geographic neighbours as checkboxes (`NeighbourPicker.svelte`,
+`GET /api/locations/{id}/neighbours`); the ticked ones are sent as
+`link_to` and linked with their derived type after any promotion. The room
+batch confirms the anchor's promotion through the same dialog
+(`confirm_promotion`) and offers the anchor's neighbours per top-level room
+(`room_links`); its tree edges are `borde`, since a parent that holds a room
+is a zone. A room that receives a room becomes a zone.
+
+**Rejected.** R3, flattening batches: changes the generator's prompt.
+Reactivates if R1 makes buildings unmanageable.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/zone_children.py b/tooling/verify/checks/zone_children.py
new file mode 100644
index 0000000..81c7401
--- /dev/null
+++ b/tooling/verify/checks/zone_children.py
@@ -0,0 +1,219 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-E) — a zone's children take its neighbours.
+
+DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
+DATABASE_URL set BEFORE any world_engine import), driven through the real
+routes with `TestClient(app, base_url="http://127.0.0.1")` (origin_guard).
+Zero outcomes in any assertion is a FAIL.
+
+Fixture: F, a zone (child F1) with a `borde` to V (visitable) and a `borde`
+to Z2 (a zone, child Z2a); A, a visitable anchor with a `connects_to` to S
+(visitable) and an NPC standing in A.
+
+Five assertions:
+  a. `GET /api/locations/{F}/neighbours` lists V (`is_zone` false) and Z2
+     (`is_zone` true), nothing else.
+  b. `POST /api/entities` creating E under F with `link_to: [V, Z2]` (F is
+     already a zone, so nothing to confirm) is a 201: E-V is `connects_to`
+     with its two door rows, E-Z2 is `borde` with none.
+  c. `link_to` naming a character is a 422 and creates no entity.
+  d. `POST /api/room-batch/commit` with one top-level room R1 under A and
+     no `confirm_promotion` is `ok: false`, error `promotion_required`, no
+     room committed, A-S still `connects_to`.
+  e. The same commit with `confirm_promotion` and `room_links: {R1: [S]}`
+     is `ok: true`: A-S is `borde` (same row), A-R1 is `borde` (the tree
+     edge), R1-S is `connects_to`, and the NPC stands in R1.
+
+Named mutations: drop `link_new_location(...)` from
+`_create_static_entity_core` -> (b); drop `_commit_room_links(...)` from
+`commit_room_batch` -> (e); stop passing `confirm_promotion` into the room
+bodies -> (e).
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
+    from world_engine.models import Character, Entity, Location, World
+    from world_engine.spatial_author import link_locations
+
+    ids: dict[str, str] = {}
+    with Session(engine) as db:
+        world = World(name="Children check", is_active=True)
+        db.add(world)
+        db.commit()
+        ids["world"] = world.id
+        for label, parent in (("F", None), ("F1", "F"), ("V", None), ("Z2", None), ("Z2a", "Z2"),
+                              ("A", None), ("S", None)):
+            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
+            db.add(entity)
+            db.flush()
+            db.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
+            db.commit()
+            ids[label] = entity.id
+        for a, b in (("F", "V"), ("F", "Z2"), ("A", "S")):
+            link_locations(db, world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
+        npc = Entity(world_id=world.id, type="character", name="Portier")
+        db.add(npc)
+        db.flush()
+        db.add(Character(id=npc.id, world_id=world.id, character_type="npc", current_location_id=ids["A"]))
+        db.commit()
+        ids["N"] = npc.id
+    return ids
+
+
+def _rel(db, a: str, b: str):
+    from sqlmodel import select
+
+    from world_engine.models import Relation
+
+    return db.exec(select(Relation).where(
+        ((Relation.entity_a_id == a) & (Relation.entity_b_id == b))
+        | ((Relation.entity_a_id == b) & (Relation.entity_b_id == a))
+    )).first()
+
+
+def _doors(db, a: str, b: str) -> int:
+    from sqlmodel import select
+
+    from world_engine.models import Door
+
+    return len(db.exec(select(Door).where(
+        ((Door.location_id == a) & (Door.target_location_id == b))
+        | ((Door.location_id == b) & (Door.target_location_id == a))
+    )).all())
+
+
+def check_a_neighbours(client, ids) -> None:
+    rows = client.get(f"/api/locations/{ids['F']}/neighbours").json()
+    got = {r["id"]: r["is_zone"] for r in rows}
+    COUNTS["a"] = _ok(got == {ids["V"]: False, ids["Z2"]: True}, f"(a) neighbours of F: {got}") + len(rows)
+
+
+def check_b_c_children(client, engine, ids) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Entity
+
+    body = {"entity": {"name": "Lieu E", "type": "location", "status": "active"},
+            "extension": {"parent_location_id": ids["F"]}, "link_to": [ids["V"], ids["Z2"]]}
+    resp = client.post("/api/entities", json=body)
+    n = _ok(resp.status_code == 201, f"(b) create under a zone answered {resp.status_code} {resp.text[:120]}")
+    if resp.status_code == 201:
+        e = resp.json()["id"]
+        with Session(engine) as db:
+            ev, ez = _rel(db, e, ids["V"]), _rel(db, e, ids["Z2"])
+            n += _ok(ev is not None and ev.type == "connects_to", "(b) E-V is not connects_to")
+            n += _ok(_doors(db, e, ids["V"]) == 2, "(b) E-V has no door pair")
+            n += _ok(ez is not None and ez.type == "borde", "(b) E-Z2 is not borde")
+            n += _ok(_doors(db, e, ids["Z2"]) == 0, "(b) E-Z2 got doors")
+    COUNTS["b"] = n
+    body = {"entity": {"name": "Lieu fautif", "type": "location", "status": "active"},
+            "extension": {"parent_location_id": ids["F"]}, "link_to": [ids["N"]]}
+    resp = client.post("/api/entities", json=body)
+    with Session(engine) as db:
+        left = db.exec(select(Entity).where(Entity.name == "Lieu fautif")).first()
+    COUNTS["c"] = _ok(resp.status_code == 422 and left is None, f"(c) link_to a character answered {resp.status_code}")
+
+
+def _batch(ids, **extra) -> dict:
+    room = {"local_id": "r1", "name": "Vestibule", "parent_room": None,
+            "result": {"draft": {"public": {"name": "Vestibule"}, "facets": {}}}}
+    return dict({"anchor_id": ids["A"], "rooms": [room], "accepted": {"r1": True}}, **extra)
+
+
+def check_d_e_room_batch(client, engine, ids) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Character, Entity
+
+    with Session(engine) as db:
+        rel_id = _rel(db, ids["A"], ids["S"]).id
+    out = client.post("/api/room-batch/commit", json=_batch(ids)).json()
+    with Session(engine) as db:
+        room = db.exec(select(Entity).where(Entity.name == "Vestibule")).first()
+        n = _ok(out.get("ok") is False and out.get("error") == "promotion_required" and room is None
+                and _rel(db, ids["A"], ids["S"]).type == "connects_to", f"(d) unconfirmed batch: {out}")
+    COUNTS["d"] = n
+    out = client.post("/api/room-batch/commit",
+                      json=_batch(ids, confirm_promotion=True, room_links={"r1": [ids["S"]]})).json()
+    n = _ok(out.get("ok") is True, f"(e) confirmed batch: {out}")
+    with Session(engine) as db:
+        room = db.exec(select(Entity).where(Entity.name == "Vestibule")).first()
+        if room is not None:
+            a_s = _rel(db, ids["A"], ids["S"])
+            n += _ok(a_s.id == rel_id and a_s.type == "borde", "(e) A-S not retyped in place to borde")
+            n += _ok(_rel(db, ids["A"], room.id).type == "borde", "(e) the tree edge A-R1 is not borde")
+            r_s = _rel(db, room.id, ids["S"])
+            n += _ok(r_s is not None and r_s.type == "connects_to", "(e) R1-S not linked by connects_to")
+            n += _ok(db.get(Character, ids["N"]).current_location_id == room.id, "(e) the NPC did not move to R1")
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
+    client = TestClient(app, base_url="http://127.0.0.1")
+    check_a_neighbours(client, ids)
+    check_b_c_children(client, engine, ids)
+    check_d_e_room_batch(client, engine, ids)
+
+    for key in ("a", "b", "c", "d", "e"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero outcomes examined")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_children — "
+        f"(a) neighbours route [{COUNTS['a']}], (b) link_to derives types [{COUNTS['b']}], "
+        f"(c) bad link_to refused [{COUNTS['c']}], (d) batch asks first [{COUNTS['d']}], "
+        f"(e) batch promotes and links [{COUNTS['e']}]"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Offering the neighbours when an EXISTING location is re-parented (K asks it at creation only).
- Flattening room batches (R3, rejected).
- Neighbour checkboxes in the region generator (all its locations are new; its links already derive their type, A).
- Graph modes (F).

## Invariants to defend

- **Every Création surface mounts through `mount.js` alone** (`creation_island.py`): the picker is rendered inside the fiche, the modal inside the room batch; neither is a new island.
- **Inside a `$effect`, a state assigned there is not read afterwards** (`effect_self_write.py`): the room batch's effect only assigns `anchorNeighbours` in a `then`.
- **Creator-CRUD location edits close gatherings**: the room batch dissolves what its promotion emptied, after its commit.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.
- `effect_self_write.py` or `creation_island.py` fails.

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
- `zone_children.py` → `PASS: zone_children — (a) neighbours route [3], (b) link_to derives types [5], (c) bad link_to refused [1], (d) batch asks first [1], (e) batch promotes and links [5]`.
- `room_batch_report_only.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `creation_island.py`, `decisions_index.py` → `PASS`.
- The three named mutations failed as stated.
- `corpus_gate.py` → 134/134.
- Live: « + Nouveau » on Lieux, parent « Forêt verte » (now a zone) → « Voisins » lists its neighbours, a zone marked « (zone : lien « borde ») »; ticking one and saving creates the link with that type.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A ZONE'S CHILDREN TAKE ITS NEIGHBOURS (TICKET-0101) -- CHECKBOXES, ROOM BATCH (BRIEF-0101-e, no schema change)` — in the diff.
