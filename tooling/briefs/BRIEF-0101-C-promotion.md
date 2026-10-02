<!-- slug: promotion -->
# BRIEF 0101-C — "A first child makes a zone"

Lot: LOT-0101-zones.md (authoritative on conflict)
Amended by: AMENDMENT-0101-01 (C-06, C-08, assertion (f)) — regenerated
Depends on: A (C-01, C-02), B (C-05)
Commit header for decisions: `(BRIEF-0101-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- BRIEFS 0101-A and -B are committed: `zone_rules.active_child_ids`, `write_relation`'s `_require_map_shape`, `zone_placement.py` exist.
- `src/world_engine/cockpit/crud/entities.py`: `    mentions: Optional[list[dict]] = None` is the last field of `EntityWriteBody`; inside `_create_static_entity_core`, `    db.flush()` then `    db.add(ext_row)` then a blank line then `    if pending_faction_id:`; `create_entity` has `        entity = _create_entity_core(body, db)` then `        db.commit()`; in `update_entity`, `        if entity.type == "character":` / `            prior_location_id = ext.current_location_id`, and later `    db.commit()` / `    dissolve_emptied({row.gathering_id for row in closed}, db)`
- `src/world_engine/cockpit/mutations.py:429` (± the lines B added) → `def _mutation_apply_status_change(`; the `# ── item_update (BRIEF-07` banner follows it; the import `from ..zone_rules import ZoneRefusal, require_visitable` (B)
- `src/world_engine/cockpit/crud/locations.py`: `@router.get("/locations/{location_id}/schedule")`; the import `from ...zone_rules import ZoneRefusal, require_visitable` (B)
- `src/world_engine/gathering.py:283` → `def close_open_memberships(`; `:308` → `def dissolve_emptied(`; `:361` → `def attach_on_arrival(`
- `frontend/src/creation/Sheet.svelte:558` → `  async function submitEntity(isNewSave, type, entityData, extData) {`; `:843` → `<LocationTypeModal bind:this={locTypeModal} {legacyDoc} />`
- `frontend/src/creation/Modal.svelte:22` → `  let { title, open, dismissOnBackdrop = true, onClose, body } = $props();`
- `tooling/verify/canon_write_policy.txt:39` → `src/world_engine/writes/config.py::write_npc_schedule          npc_schedule`
- `tooling/verify/checks/knowledge_identity.py:109` → `_SUBJECT_CENSUS: dict[str, int] = {`, last entry `"src/world_engine/cockpit/play_discovery.py": 1,`
- `ls src/world_engine/writes/zone_promotion.py src/world_engine/cockpit/crud/zone_hooks.py` → no such file

## Facts carried

### R-09 — what sits at a location [M]
Opened: `models/canon.py:143-175` (`character`), `:482-500` (`event`),
`:527-540` (`artifact`), `:548-566` (`item`), `:678-695`
(`discoverable_detail`); `models/ephemeral.py:44-62` (`gathering`),
`:83-100` (`conversation`), `:143-155` (`visit`); `models/schedule.py:40-62`.
Consequence: K's table, row family by row family (C-07).

### R-10 — leaving a place closes gatherings [M]
Opened: `cockpit/crud/entities.py:770-792` (`update_entity`'s location
change); `gathering.py:283-305, 308-358, 361-` (the three functions).
Finding: a fiche location change runs `close_open_memberships`, then
`attach_on_arrival`, and after the commit `dissolve_emptied`, which
analyses an emptied gathering's open conversation (`analyze_window`, errors
logged) and dissolves it.
Consequence: the promotion moves beings with this exact recipe (C-08); « a
journey closes them » is satisfied without a new close path.

### R-11 — where a location gains or loses an active child [M]
Opened: `cockpit/crud/entities.py:525-660` (create cores), `:737-830`
(`update_entity`, `delete_entity`); `cockpit/mutations.py:429-451`
(`status_change`); grep of `parent_location_id\s*=[^=]` and `\.status\s*=`
over `src/` (E2).
Finding: gain — a location created with a parent (`_create_static_entity_
core`), an `update_entity` that re-parents a location or sets it back to
`active`, an approved AI `status_change` that reactivates one. Loss — the
same three, the other way, and `delete_entity` (soft). `update_entity` was
78 lines and `_create_static_entity_core` 72 on `main`.
Consequence: one seam (`promote_for_child`) for the two CRUD sites; the AI
path never shows a dialog, so it is refused when one would be needed.

### R-14 — checks that read this vocabulary [M]
Opened: `tooling/verify/checks/relation_graph.py:83-120` (implementation);
`known_reachability.py:303-335` (`DOCUMENTED_MODULES`);
`knowledge_identity.py:31-35, 109-113` (`_SUBJECT_CENSUS`);
`lore_write.py:185-210` (W2); `migrate_v2_11_lore_entry.py:142-156`
(`_converge_schema_meta`).
Finding: `relation_graph.py` resolves the tuple by regex on a literal;
`known_reachability.py` fails on any new module spelling `"connects_to"`
until it is listed (and classified in `tooling/tickets/connects-to-readers-
TICKET-0082.md`); `knowledge_identity.py` pins every file's count of
`subject` references; `lore_write.py` W2b pinned `"v2.11"` as the version
the v2.11 migration converges to — the migration converges to the code
constant.
Consequence: the tuple stays a literal; `zone_rules.py` (A) and
`writes/zone_promotion.py` (C) are listed and classified; the latter's three
`discoverable_detail.subject` reads join the census; W2b compares to the
constant (D).

### R-15 — the canon-write policy [M]
Opened: `tooling/verify/canon_write_policy.txt`; `single_canon_write.py`
(implementation, function-scoped attribution).
Finding: `write_character_location`, `write_npc_schedule`, `write_relation`
are listed; a new function writing `item` or `discoverable_detail` is not.
Consequence: `writes/zone_promotion.py::apply_promotion item
discoverable_detail` is added, with its reason (C).

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

### C-02 — L1/V1 in `write_relation`
Produced by: A   Consumed by: every caller of `write_relation`
Judged on a NEW row and on a `mode="set"` row whose type changes, before
anything is mutated (`_require_map_shape`): a retype into or out of
`MAP_TOPOLOGY_TYPES` raises; a geographic row whose two ends are not both
`location` entities raises; a geographic type other than
`geographic_link_type(a, b)` raises — all `ValueError`. An existing row
whose type does not change is never judged. A new `borde` row births one
fact, `borde_fact_content(token_a, token_b)`, `facet='lien'`,
`default_level='knows'`; a `connects_to` ↔ `borde` change rewrites the fact
through `update_typed_fact_content`.

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

### C-07 — `apply_promotion`
Produced by: C   Consumed by: C-08
`apply_promotion(db, *, parent_id, child_id, changed_by) -> dict` (the
preview it applied), commit-free, `child_id` already in the session: each
`links` row → `write_relation(mode="set", relation_id, type="borde", …)`;
each being → `write_character_location(… child_id)`; each NPC with a
schedule row at the parent → one full-replace `write_npc_schedule` of its
whole schedule with that location swapped; each item and detail →
`location_id = child_id`. Gatherings: listed, never touched here.

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

## Context

D + K: a visitable location that gets its first child becomes a zone, and what can only sit in a visitable place moves to that child — links become `borde`, beings, schedules, items and details move, gatherings close. S1: the server refuses such a write unless the creator confirmed it after seeing the list; a promotion that moves nothing needs no dialog. The fiche shows the list in a dialog before saving.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/writes/zone_promotion.py` (C-06, C-07);
   - creates `src/world_engine/cockpit/crud/zone_hooks.py` (C-08, with AMENDMENT-0101-01's `target_is_zone` refusal and its message);
   - `crud/entities.py`: `EntityWriteBody.confirm_promotion`; `promote_for_child` after the extension row in `_create_static_entity_core` and before the commit in `update_entity` (whose prior "where" now also captures a location's parent); `take_promotion_gatherings` joins both post-commit `dissolve_emptied` calls;
   - `crud/locations.py`: `GET /api/locations/{location_id}/promotion-preview`;
   - `mutations.py`: `_zone_promotion_refusal`, called by `status_change` (and the `Location` import);
   - `frontend/src/creation/PromotionModal.svelte` (no dialog when `target_is_zone`); `Sheet.svelte`: `submitGated`, `submitEntity(..., confirmPromotion)`, the modal instance;
   - `canon_write_policy.txt`: `apply_promotion item discoverable_detail`, with its reason;
   - `knowledge_identity.py`: the census line; `known_reachability.py` and the classification table: `writes/zone_promotion.py`;
   - `tooling/verify/checks/zone_promotion.py`;
   - the decision entry above the footer.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Named mutations, each run with `python tooling/verify/checks/zone_promotion.py`, then restored:
   - in `zone_hooks.py`, replace `if preview["needs_confirmation"] and not confirmed:` with `if False:` → `FAIL: (a) unconfirmed promotion answered 201 …`;
   - in `writes/zone_promotion.py`, delete the two lines `    for being in preview["beings"]:` / `        write_character_location(db, entity_id=being["id"], to_location_id=child_id)` → `FAIL: (b) P not moved to the first child`;
   - in `zone_hooks.py`, replace `if preview["needs_confirmation"] and not confirmed:` with `if not confirmed:` → `FAIL: (c) silent promotion answered 409`;
   - in `mutations.py`, delete the three lines `    refusal = _zone_promotion_refusal(entity, str(new_status), db)` / `    if refusal:` / `        return refusal` → `FAIL: (e) an AI status_change promoted F without the dialog`;
   - in `zone_hooks.py`, delete the two lines `    if preview["needs_confirmation"] and preview["target_is_zone"]:` / `        raise HTTPException(409, _target_is_zone_message(db, parent_id, child_id))` → `FAIL: (f) re-parenting a zone under an inhabited place answered 200 …` and `FAIL: (f) the NPC left V3`.
5. Commit message: `feat(zones): a first child promotes its parent, confirmed (BRIEF-0101-c)`.

````diff
diff --git a/frontend/src/creation/PromotionModal.svelte b/frontend/src/creation/PromotionModal.svelte
new file mode 100644
index 0000000..57cf6c2
--- /dev/null
+++ b/frontend/src/creation/PromotionModal.svelte
@@ -0,0 +1,81 @@
+<script>
+  /* TICKET-0101 (BRIEF-0101-C, S1). The promotion dialog: a location about
+     to receive its first active child becomes a zone, and what can only sit
+     in a visitable place moves to that child. Fed by the read-only
+     GET /api/locations/{id}/promotion-preview (writes/zone_promotion.py's
+     promotion_preview); the write that follows carries confirm_promotion
+     only after the creator confirms here. Same instance shape as
+     LocationTypeModal.svelte: Sheet.svelte owns one, opened from its save
+     path; open/close state lives here, the Modal primitive renders it. */
+  import Modal from './Modal.svelte';
+
+  let open = $state(false);
+  let preview = $state(null);
+  let childName = $state('');
+  let onConfirmCb = () => {};
+
+  const SECTIONS = [
+    { key: 'links', title: 'Liens, qui deviennent « borde » (non traversables)', label: (r) => r.other_name },
+    { key: 'beings', title: 'Personnages présents, déplacés', label: (r) => r.name },
+    { key: 'schedules', title: 'Horaires, reciblés', label: (r) => `${r.npc_name} (${r.phase})` },
+    { key: 'items', title: 'Objets posés, déplacés', label: (r) => r.name },
+    { key: 'details', title: 'Détails découvrables, déplacés', label: (r) => r.subject },
+    { key: 'gatherings', title: 'Rassemblements ouverts, fermés', label: (r) => r.label || 'sans nom' },
+  ];
+
+  /** Resolves the save: `proceed(false)` at once when the write promotes
+   *  nothing that moves, else after the dialog, `proceed(true)` on confirm
+   *  (cancel calls nothing). A failed preview read lets the save go through
+   *  unconfirmed -- the server still refuses it (409) if it had to ask.
+   *  AMENDMENT-0101-01: a child that is itself a zone cannot receive the
+   *  contents; no dialog, the save goes through and the server's 409
+   *  message lands in the fiche's status line. */
+  export async function gate(parentId, childId, name, proceed) {
+    if (!parentId) return proceed(false);
+    const query = childId ? `?child_id=${encodeURIComponent(childId)}` : '';
+    let data;
+    try {
+      const res = await fetch(`/api/locations/${encodeURIComponent(parentId)}/promotion-preview${query}`);
+      data = res.ok ? await res.json() : null;
+    } catch (_err) {
+      data = null;
+    }
+    if (!data || !data.needs_confirmation || data.target_is_zone) return proceed(false);
+    preview = data;
+    childName = name || 'le nouveau lieu';
+    onConfirmCb = () => proceed(true);
+    open = true;
+  }
+
+  function close() {
+    open = false;
+  }
+
+  async function confirmPromotion() {
+    open = false;
+    await onConfirmCb();
+  }
+</script>
+
+<Modal title="Ce lieu devient une zone" {open} dismissOnBackdrop={false} onClose={close}>
+  {#snippet body()}
+    {#if preview}
+      <p>« {preview.location_name} » reçoit son premier lieu enfant : il devient une zone, qu'on
+      ne visite plus directement. Ce qui suit va dans « {childName} ».</p>
+      {#each SECTIONS as section (section.key)}
+        {#if preview[section.key].length}
+          <div class="field-section-title" style="margin-top:8px">{section.title}</div>
+          {#each preview[section.key] as row (row.id || `${row.npc_id}-${row.phase}`)}
+            <div style="font-size:12px">· {section.label(row)}</div>
+          {/each}
+        {/if}
+      {/each}
+      <p style="font-size:11px; color:var(--muted); margin-top:8px">Plan intérieur, événements,
+      faits, connaissances et contrôle de faction restent sur la zone.</p>
+      <div class="row-card-actions" style="margin-top:10px">
+        <button class="btn-send" onclick={confirmPromotion}>Confirmer</button>
+        <button class="btn-icon" onclick={close}>Annuler</button>
+      </div>
+    {/if}
+  {/snippet}
+</Modal>
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index e2fb62c..25ad642 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -79,6 +79,7 @@
   import { creationRefreshList, loadPendingCreations } from './tabs.js';
   import { readFieldValue } from './fields.js';
   import LocationTypeModal from './LocationTypeModal.svelte';
+  import PromotionModal from './PromotionModal.svelte';
   import Field from './Field.svelte';
   import GeometryEditor from './GeometryEditor.svelte';
   import DoorsEditor from './DoorsEditor.svelte';
@@ -120,6 +121,8 @@
   // split) -- this one is not tied to any button, only saveSheet's own
   // uncatalogued-type check.
   let locTypeModal;
+  // TICKET-0101 (BRIEF-0101-C, S1): the promotion dialog, opened by submitGated.
+  let promotionModal;
 
   const GENERIC_TYPE_BY_TAB = { npc: 'character', pj: 'character', lieux: 'location', factions: 'faction', objets: 'item' };
   const EMPTY_BODY_BY_TAB = {
@@ -477,13 +480,27 @@
         const folded = chosenType.toLowerCase();
         const catalogRow = creationState.locationTypeCatalog.find((r) => r.name.toLowerCase() === folded);
         if (!catalogRow || catalogRow.classification == null) {
-          locTypeModal.openFor(chosenType, () => submitEntity(isNewSave, type, entityData, extData));
+          locTypeModal.openFor(chosenType, () => submitGated(isNewSave, type, entityData, extData));
           return;
         }
       }
     }
 
-    await submitEntity(isNewSave, type, entityData, extData);
+    await submitGated(isNewSave, type, entityData, extData);
+  }
+
+  /** TICKET-0101 (BRIEF-0101-C, S1): a location that becomes an active child
+   *  -- new, re-parented, or reactivated -- may make its parent a zone. The
+   *  same condition as the server's promote_for_child; PromotionModal shows
+   *  what moves and the save carries confirm_promotion once confirmed. */
+  async function submitGated(isNewSave, type, entityData, extData) {
+    const prior = isNewSave ? null : creationState.sheetDetail;
+    const parentId = extData.parent_location_id || null;
+    const becomesChild = type === 'location' && parentId && (entityData.status || 'active') === 'active'
+      && (!prior || (prior.extension || {}).parent_location_id !== parentId || prior.status !== 'active');
+    if (!becomesChild) { await submitEntity(isNewSave, type, entityData, extData, false); return; }
+    await promotionModal.gate(parentId, prior ? prior.id : null, entityData.name,
+      (confirmed) => submitEntity(isNewSave, type, entityData, extData, confirmed));
   }
 
   /** competences' save (TICKET-0099, BRIEF-0099-b): the header Save button
@@ -555,7 +572,7 @@
    *  fetched via legacyCall right before, exactly as authorFactionRolesDraft/
    *  authorLocationSubcultureDraft/pendingDraftKnowledge/pendingDraftGoals
    *  were read in place before. */
-  async function submitEntity(isNewSave, type, entityData, extData) {
+  async function submitEntity(isNewSave, type, entityData, extData, confirmPromotion = false) {
     const statusEl = legacyDoc.getElementById('author-status');
     const rolesToCreate = (isNewSave && type === 'faction') ? draftRolesForCreate() : [];
     const knowledgeToCreate = (isNewSave && type === 'character') ? knowledgeForCreate() : [];
@@ -568,6 +585,7 @@
         extension: extData,
         ...(isNewSave ? { facets: factsDraftForCreate() } : {}),
         ...(isNewSave && mutationId ? { mutation_id: mutationId } : {}),
+        ...(confirmPromotion ? { confirm_promotion: true } : {}),
       });
       let detail = isNewSave
         ? await api('/api/entities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
@@ -841,3 +859,4 @@
 </div>
 <div id="author-legacy-sheet-slot" style={mode === 'legacy' ? '' : 'display:none'}></div>
 <LocationTypeModal bind:this={locTypeModal} {legacyDoc} />
+<PromotionModal bind:this={promotionModal} />
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index c57f027..b9cce9e 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -101,6 +101,7 @@ from ._shared import (
     _validate_entity_ref,
     _world_id,
 )
+from .zone_hooks import promote_for_child, take_promotion_gatherings
 from .entity_runtime import (
     _build_runtime_ext_kwargs,
     _insert_runtime_ext_row,
@@ -395,6 +396,9 @@ class EntityWriteBody(BaseModel):
     # TICKET-0091, BRIEF-0091-J (C-11): a generator's
     # [{"name", "category": "place"|"person"|"faction"}], passed to `tokenize`.
     mentions: Optional[list[dict]] = None
+    # TICKET-0101 (S1): the creator saw `promotion_preview` and confirmed that
+    # this location's parent becomes a zone and its contents move here.
+    confirm_promotion: bool = False
 
 
 class NpcPricesBody(BaseModel):
@@ -641,6 +645,7 @@ def _create_static_entity_core(body: EntityWriteBody, db: DbSession, entity_type
     # extension row before its own entity row.
     db.flush()
     db.add(ext_row)
+    promote_for_child(db, entity, ext_row, confirmed=body.confirm_promotion)
 
     if pending_faction_id:
         # Creator authority (this create/accept IS the creator action) — not
@@ -720,6 +725,7 @@ def create_entity(body: EntityWriteBody, db: DbSession = Depends(get_session)) -
     try:
         entity = _create_entity_core(body, db)
         db.commit()
+        dissolve_emptied(take_promotion_gatherings(db), db)
     except IntegrityError:
         db.rollback()
         raise HTTPException(
@@ -784,8 +790,8 @@ def update_entity(entity_id: str, body: EntityWriteBody, db: DbSession = Depends
         ext = db.get(ext_model, entity_id)
         if ext is None:
             raise HTTPException(500, f"Missing {entity.type} extension row for entity {entity_id!r}")
-        if entity.type == "character":
-            prior_location_id = ext.current_location_id
+        # The prior "where": a character's place, or a location's parent (TICKET-0101).
+        prior_location_id = getattr(ext, "current_location_id", getattr(ext, "parent_location_id", None))
         # Key-present-wins: an absent key preserves the stored column, same distinction set_location_geometry draws via body.model_fields_set.
         ext_kwargs = _build_extension_kwargs(db, entity.type, body.extension, present_only=True, current=ext)
         for key, value in ext_kwargs.items():
@@ -813,9 +819,10 @@ def update_entity(entity_id: str, body: EntityWriteBody, db: DbSession = Depends
         attach_on_arrival(entity_id, ext.current_location_id, db)
     if prior_status == "active" and entity.status != "active":
         closed += close_open_memberships(entity_id, db)
-
+    promote_for_child(db, entity, ext, confirmed=body.confirm_promotion,
+                      prior_parent_id=prior_location_id, prior_status=prior_status)
     db.commit()
-    dissolve_emptied({row.gathering_id for row in closed}, db)
+    dissolve_emptied({row.gathering_id for row in closed} | take_promotion_gatherings(db), db)
     db.refresh(entity)
 
     result = _entity_dict(entity)
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index 2238f1b..1bf27d6 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -54,6 +54,7 @@ from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
 from ...schedule_reads import unresolved_npcs, where_is, who_is_at
 from ...tick_normalize import _EVENT_TYPES
+from ...writes.zone_promotion import promotion_preview
 from ...zone_rules import ZoneRefusal, require_visitable
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -344,6 +345,19 @@ def _schedule_npc_brief(npc_id: str, db: DbSession) -> dict:
     return {"npc_id": npc_id, "name": entity.name if entity else npc_id}
 
 
+@router.get("/locations/{location_id}/promotion-preview")
+def get_promotion_preview(
+    location_id: str,
+    child_id: Optional[str] = Query(default=None),
+    db: DbSession = Depends(get_session),
+) -> dict:
+    """What `location_id` gaining `child_id` (or any first child) would move
+    -- read-only, the dialog's source (TICKET-0101, S1). The same dict a
+    refused write returns in its 409 detail (`promotion_preview`)."""
+    _get_entity(db, location_id)
+    return promotion_preview(db, location_id, child_id=child_id)
+
+
 @router.get("/locations/{location_id}/schedule")
 def get_location_schedule(location_id: str, db: DbSession = Depends(get_session)) -> dict:
     """F1 — "qui est ici, par phase" (T-C1's read-only counterpart), the
diff --git a/src/world_engine/cockpit/crud/zone_hooks.py b/src/world_engine/cockpit/crud/zone_hooks.py
new file mode 100644
index 0000000..167734c
--- /dev/null
+++ b/src/world_engine/cockpit/crud/zone_hooks.py
@@ -0,0 +1,90 @@
+"""Zone promotion seam of the creator CRUD (TICKET-0101, D + K, S1).
+
+A location that gains its first active child becomes a zone. The creator
+CRUD reaches that moment in two places -- a location created with a parent
+(`_create_static_entity_core`) and a location whose parent or status changes
+(`update_entity`) -- and both call `promote_for_child`:
+
+- nothing to move (`needs_confirmation` False): the promotion is applied
+  silently -- a fresh parent, a room nested in a room just created;
+- something to move and the child is itself a zone (it has an active child
+  already -- a re-parent or a reactivation): 409 with a creator-facing
+  message, nothing written, confirmed or not (AMENDMENT-0101-01: the
+  contents would land in a zone, which B1 forbids);
+- something to move and the request did not carry `confirm_promotion`:
+  409 with `{"code": "promotion_required", "preview": <promotion_preview>}`,
+  nothing written (S1);
+- confirmed: `writes.zone_promotion.apply_promotion`, then each moved being
+  leaves its gatherings and joins the first child's live one, as a fiche
+  location change does (`close_open_memberships`, `attach_on_arrival`).
+
+The gatherings those moves may have emptied, and the open gatherings of the
+promoted location, are parked on `db.info` and dissolved by
+`take_promotion_gatherings(db)` in the caller's post-commit
+`dissolve_emptied`, never before the commit.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from fastapi import HTTPException
+from sqlmodel import Session as DbSession
+
+from ...gathering import attach_on_arrival, close_open_memberships
+from ...models import Entity
+from ...writes.zone_promotion import apply_promotion, promotion_preview
+
+_PENDING_KEY = "zone_promotion_gatherings"
+
+
+def promote_parent(db: DbSession, *, parent_id: str, child_id: str, confirmed: bool) -> Optional[dict]:
+    """Promote `parent_id` around `child_id` when it is the first active
+    child; returns the applied preview, or None when nothing promotes."""
+    db.flush()
+    preview = promotion_preview(db, parent_id, child_id=child_id)
+    if not preview["promotes"]:
+        return None
+    if preview["needs_confirmation"] and preview["target_is_zone"]:
+        raise HTTPException(409, _target_is_zone_message(db, parent_id, child_id))
+    if preview["needs_confirmation"] and not confirmed:
+        raise HTTPException(409, detail={"code": "promotion_required", "preview": preview})
+    apply_promotion(db, parent_id=parent_id, child_id=child_id, changed_by="creator")
+    closed = []
+    for being in preview["beings"]:
+        closed.extend(close_open_memberships(being["id"], db))
+        attach_on_arrival(being["id"], child_id, db)
+    pending = db.info.setdefault(_PENDING_KEY, set())
+    pending.update(row.gathering_id for row in closed)
+    pending.update(g["id"] for g in preview["gatherings"])
+    return preview
+
+
+def _target_is_zone_message(db: DbSession, parent_id: str, child_id: str) -> str:
+    parent, child = db.get(Entity, parent_id), db.get(Entity, child_id)
+    p_name = parent.name if parent is not None else parent_id
+    c_name = child.name if child is not None else child_id
+    return (
+        f"« {c_name} » est déjà une zone : le contenu de « {p_name} » ne peut pas y être "
+        f"déplacé. Rattachez d'abord un lieu visitable à « {p_name} », ou videz « {p_name} »."
+    )
+
+
+def promote_for_child(
+    db: DbSession, entity: Entity, ext: Any, *, confirmed: bool,
+    prior_parent_id: Optional[str] = None, prior_status: Optional[str] = None,
+) -> Optional[dict]:
+    """The CRUD trigger: `entity` is a location that is, after this write, an
+    active child of `ext.parent_location_id`, and was not one before (new,
+    re-parented, or reactivated)."""
+    if entity.type != "location" or ext is None or entity.status != "active":
+        return None
+    parent_id = getattr(ext, "parent_location_id", None)
+    if not parent_id or (parent_id == prior_parent_id and prior_status == "active"):
+        return None
+    return promote_parent(db, parent_id=parent_id, child_id=entity.id, confirmed=confirmed)
+
+
+def take_promotion_gatherings(db: DbSession) -> set[str]:
+    """The gathering ids parked by `promote_parent`, removed from `db.info`."""
+    return db.info.pop(_PENDING_KEY, set())
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index d387aaa..7e9f2a3 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -46,6 +46,7 @@ from ..models import (
     FactionRole,
     GoalPrerequisite,
     Item,
+    Location,
     NpcGoal,
     ProposedMutation,
 )
@@ -68,6 +69,7 @@ from ..writes import (
     write_npc_goal_status,
     write_relation,
 )
+from ..writes.zone_promotion import promotion_preview
 from ..zone_rules import ZoneRefusal, require_visitable
 from .routes import mutations as _routes_mutations
 
@@ -444,6 +446,9 @@ def _mutation_apply_status_change(mut: ProposedMutation, payload: dict, db: Sess
     entity = db.get(Entity, str(entity_id))
     if entity is None:
         return f"status_change: entity {entity_id!r} not found"
+    refusal = _zone_promotion_refusal(entity, str(new_status), db)
+    if refusal:
+        return refusal
 
     entity.status = str(new_status)
     entity.updated_at = datetime.now(UTC)
@@ -451,6 +456,23 @@ def _mutation_apply_status_change(mut: ProposedMutation, payload: dict, db: Sess
     return None
 
 
+def _zone_promotion_refusal(entity: Entity, new_status: str, db: Session) -> Optional[str]:
+    """TICKET-0101 (S1): reactivating a location that would promote its
+    parent into a zone AND move something there needs the creator's
+    confirmation, which only the fiche gives -- "Needs attention" here. A
+    promotion with nothing to move proceeds."""
+    if entity.type != "location" or entity.status == "active" or new_status != "active":
+        return None
+    location = db.get(Location, entity.id)
+    preview = promotion_preview(db, location.parent_location_id if location else None, child_id=entity.id)
+    if not preview["needs_confirmation"]:
+        return None
+    return (
+        f"status_change: réactiver « {entity.name} » fait de « {preview['location_name']} » une zone "
+        "et déplace son contenu -- à faire depuis la fiche"
+    )
+
+
 # ── item_update (BRIEF-07, schema v1.19 — equip toggle) ────────────────────
 # Dormant since BRIEF-08/D2a.1: no live code path produces this mutation type
 # anymore; the apply branch and cockpit toggle remain functional for
diff --git a/src/world_engine/writes/zone_promotion.py b/src/world_engine/writes/zone_promotion.py
new file mode 100644
index 0000000..7630e1e
--- /dev/null
+++ b/src/world_engine/writes/zone_promotion.py
@@ -0,0 +1,179 @@
+"""Promotion of a visitable location into a zone (TICKET-0101, D + K, N1).
+
+A location becomes a zone the moment it gains its first active child (A1).
+Everything that only makes sense in a place one can stand in moves, in the
+same transaction, to that first child; everything that describes the place
+stays and now describes the zone.
+
+- `promotion_preview(db, parent_id, child_id=None)` : read-only. Whether
+  gaining `child_id` (or any first child) promotes `parent_id`, the exact
+  rows that would move, and whether `child_id` is itself a zone
+  (`target_is_zone`, AMENDMENT-0101-01: such a child cannot receive them). The confirmation dialog and the 409 of S1
+  both show this dict; `apply_promotion` moves exactly these rows.
+- `apply_promotion(db, parent_id, child_id, changed_by)` : moves them.
+  Never commits; the caller owns the transaction and, after its commit,
+  dissolves the gatherings the moves emptied (`gathering.dissolve_emptied`
+  -- gatherings are not canon, so they are the caller's, never this
+  module's).
+
+Resolution table (K), one line per row family:
+- `connects_to` rows touching the parent -> retyped in place to `borde`
+  through `write_relation(mode="set")`: row history and fact history kept
+  (N1). Existing `borde` rows are untouched.
+- characters whose `current_location_id` is the parent -> the first child,
+  through `write_character_location`.
+- `npc_schedule` rows at the parent -> the first child, through a
+  full-replace `write_npc_schedule` of each affected NPC's whole schedule.
+- items lying at the parent (`item.location_id`) and discoverable details
+  (`discoverable_detail.location_id`) -> the first child.
+- open gatherings at the parent -> listed; the caller closes them.
+- bounds, obstacles, doors, events, facts, knowledge, `controls`,
+  artefacts -> untouched.
+"""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from ..models import Character, DiscoverableDetail, Entity, Gathering, Item, NpcSchedule, Relation
+from ..zone_rules import active_child_ids, is_zone
+from .characters import write_character_location
+from .config import write_npc_schedule
+from .relations import write_relation
+
+
+def _names(db: Session, ids: list[str]) -> dict[str, str]:
+    if not ids:
+        return {}
+    return {e.id: e.name for e in db.exec(select(Entity).where(Entity.id.in_(ids))).all()}
+
+
+def _links(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(Relation)
+        .where(
+            Relation.type == "connects_to",
+            (Relation.entity_a_id == parent_id) | (Relation.entity_b_id == parent_id),
+        )
+        .order_by(Relation.created_at, Relation.id)
+    ).all()
+    other_ids = [r.entity_b_id if r.entity_a_id == parent_id else r.entity_a_id for r in rows]
+    names = _names(db, other_ids)
+    return [{"id": r.id, "other_id": o, "other_name": names.get(o, o)} for r, o in zip(rows, other_ids)]
+
+
+def _beings(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(Character, Entity)
+        .join(Entity, Entity.id == Character.id)
+        .where(Character.current_location_id == parent_id)
+        .order_by(Entity.name)
+    ).all()
+    return [{"id": c.id, "name": e.name, "character_type": c.character_type} for c, e in rows]
+
+
+def _schedules(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(NpcSchedule).where(NpcSchedule.location_id == parent_id).order_by(NpcSchedule.npc_id)
+    ).all()
+    names = _names(db, [r.npc_id for r in rows])
+    return [{"npc_id": r.npc_id, "npc_name": names.get(r.npc_id, r.npc_id), "phase": r.phase} for r in rows]
+
+
+def _items(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(Item, Entity).join(Entity, Entity.id == Item.id)
+        .where(Item.location_id == parent_id).order_by(Entity.name)
+    ).all()
+    return [{"id": i.id, "name": e.name} for i, e in rows]
+
+
+def _details(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(DiscoverableDetail).where(DiscoverableDetail.location_id == parent_id)
+        .order_by(DiscoverableDetail.subject)
+    ).all()
+    return [{"id": d.id, "subject": d.subject} for d in rows]
+
+
+def _gatherings(db: Session, parent_id: str) -> list[dict]:
+    rows = db.exec(
+        select(Gathering).where(Gathering.location_id == parent_id, Gathering.status == "open")
+    ).all()
+    return [{"id": g.id, "label": g.label or ""} for g in rows]
+
+
+MOVING_KEYS = ("links", "beings", "schedules", "items", "details", "gatherings")
+
+
+def promotion_preview(db: Session, parent_id: Optional[str], *, child_id: Optional[str] = None) -> dict:
+    """What `parent_id` gaining `child_id` moves. `promotes` is False -- and
+    every list empty -- when `parent_id` is None, not a location, or already
+    has an active child other than `child_id`. `needs_confirmation` is True
+    when it promotes and at least one list is non-empty (S1).
+    `target_is_zone` is True when `child_id` itself has an active child."""
+    parent = db.get(Entity, parent_id) if parent_id else None
+    preview: dict = {
+        "location_id": parent_id,
+        "location_name": parent.name if parent is not None else None,
+        "promotes": False,
+        "needs_confirmation": False,
+        "target_is_zone": is_zone(db, child_id),
+        **{key: [] for key in MOVING_KEYS},
+    }
+    if parent is None or parent.type != "location" or active_child_ids(db, parent.id, exclude_id=child_id):
+        return preview
+    preview.update(
+        promotes=True,
+        links=_links(db, parent.id), beings=_beings(db, parent.id), schedules=_schedules(db, parent.id),
+        items=_items(db, parent.id), details=_details(db, parent.id), gatherings=_gatherings(db, parent.id),
+    )
+    preview["needs_confirmation"] = any(preview[key] for key in MOVING_KEYS)
+    return preview
+
+
+def _retarget_schedules(db: Session, world_id: str, preview: dict, parent_id: str, child_id: str, changed_by: str) -> None:
+    for npc_id in sorted({row["npc_id"] for row in preview["schedules"]}):
+        rows = db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == npc_id)).all()
+        write_npc_schedule(
+            db, world_id=world_id, npc_id=npc_id, changed_by=changed_by,
+            rows=[{
+                "phase": r.phase,
+                "location_id": child_id if r.location_id == parent_id else r.location_id,
+                "standing_goal_id": r.standing_goal_id,
+            } for r in rows],
+        )
+
+
+def apply_promotion(db: Session, *, parent_id: str, child_id: str, changed_by: str) -> dict:
+    """Promote `parent_id` into a zone around its first child `child_id`,
+    which must already be in the session. Returns the preview it applied
+    (`promotes=False`: nothing was done). Never commits."""
+    preview = promotion_preview(db, parent_id, child_id=child_id)
+    if not preview["promotes"]:
+        return preview
+    world_id = db.get(Entity, parent_id).world_id
+    for link in preview["links"]:
+        rel = db.get(Relation, link["id"])
+        write_relation(
+            db, mode="set", relation_id=rel.id, type="borde", value=rel.intensity,
+            direction=rel.direction, visible_to_b=rel.visible_to_b, notes=rel.notes,
+            changed_by=changed_by,
+        )
+    for being in preview["beings"]:
+        write_character_location(db, entity_id=being["id"], to_location_id=child_id)
+    _retarget_schedules(db, world_id, preview, parent_id, child_id, changed_by)
+    now = datetime.now(UTC)
+    for item in preview["items"]:
+        row = db.get(Item, item["id"])
+        row.location_id = child_id
+        db.add(row)
+    for detail in preview["details"]:
+        row = db.get(DiscoverableDetail, detail["id"])
+        row.location_id = child_id
+        row.updated_at = now
+        db.add(row)
+    return preview
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 084591b..c917d88 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17520,6 +17520,38 @@ that assign `current_location_id`.
 generic fiche write. Reactivates when a seventh write site appears
 (`zone_placement.py` (c) fails on it).
 
+## A FIRST CHILD MAKES A ZONE (TICKET-0101) -- PROMOTION, CONFIRMED (BRIEF-0101-c, no schema change)
+
+**D + K, S1.** When a location becomes the first active child of another
+(created with a parent, re-parented, or reactivated), the parent is
+promoted: its `connects_to` rows are retyped to `borde` in place, its
+characters, schedule rows, items and discoverable details move to that
+child, and its open gatherings close through the fiche's own recipe. Bounds,
+obstacles, doors, events, facts, knowledge, `controls` and artefacts stay.
+`writes/zone_promotion.py` holds `promotion_preview` (read-only, also
+`GET /api/locations/{id}/promotion-preview`) and `apply_promotion`;
+`cockpit/crud/zone_hooks.py` is the CRUD seam. A promotion that moves
+something needs `confirm_promotion` on the write, else a 409 carrying the
+preview; one that moves nothing is applied silently. `PromotionModal.svelte`
+shows the preview before the fiche saves. An AI `status_change` that would
+need the dialog is refused ("Needs attention"). A zone that loses its last
+child becomes visitable again; nothing moves, its `borde` rows stay.
+
+**P2-1 (AMENDMENT-0101-01).** A location that becomes a child while it is
+itself a zone (re-parented or reactivated with active children of its own)
+cannot receive its new parent's contents: when something would move, the
+write is a 409 with a creator-facing message, confirmed or not; the preview
+says `target_is_zone` and the dialog does not open. Nothing to move: the
+promotion stays silent.
+
+**Rejected.** P2-2, re-targeting the contents to the zone's first
+visitable descendant: an arbitrary pick nobody decided. Reactivates if Nia
+wants to graft a whole subtree onto an inhabited place in one step. P2-3,
+deferring: the lot would ship a path that breaks B1.
+
+**Rejected.** S2, a client-only dialog: any other write path would promote
+silently.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/tickets/connects-to-readers-TICKET-0082.md b/tooling/tickets/connects-to-readers-TICKET-0082.md
index 90c9a95..e4537ba 100644
--- a/tooling/tickets/connects-to-readers-TICKET-0082.md
+++ b/tooling/tickets/connects-to-readers-TICKET-0082.md
@@ -94,6 +94,9 @@ named mutation).
 - `zone_rules.py` — `geographic_link_type` returns `"connects_to"` or `"borde"`
   (TICKET-0101, BRIEF-0101-A); `relation_orientation.py` also gained
   `MAP_TOPOLOGY_TYPES = ("connects_to", "borde")` there. A derived type, never a traversal.
+- `writes/zone_promotion.py` — `promotion_preview` lists the `connects_to` rows touching a
+  location about to become a zone; `apply_promotion` retypes them to `borde` (TICKET-0101,
+  BRIEF-0101-C). A write site, never a traversal.
 
 These three are outside the twelve-module traversal count (they hold a type
 literal, never execute a `connects_to` traversal) but are listed here for
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 1a1f21b..d2f076c 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -37,6 +37,8 @@ src/world_engine/writes/config.py::upsert_location_type        location_type_cat
 src/world_engine/writes/config.py::upsert_conversation_window_config conversation_window_config
 # TICKET-0074, BRIEF-0074-a: write_npc_schedule is the 29th site — standing per-phase location default, curated-config family (write_location_doors precedent).
 src/world_engine/writes/config.py::write_npc_schedule          npc_schedule
+# TICKET-0101, BRIEF-0101-C: apply_promotion moves the items and discoverable details lying in a location that becomes a zone to its first child (creator CRUD only, behind the S1 confirmation); its characters, schedules and links go through write_character_location, write_npc_schedule and write_relation, allow-listed above.
+src/world_engine/writes/zone_promotion.py::apply_promotion     item discoverable_detail
 # TICKET-0075, BRIEF-0075-b: write_day_plan is the 30th site — its OWN body writes agenda_step_requirement only (it calls write_agenda/write_agenda_step, whose own db.add sites are already allow-listed above; single_canon_write.py is function-scoped, not interprocedural).
 src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requirement
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index b02a3da..6890477 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -110,6 +110,9 @@ _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/analyzer_transcript.py": 3,
     "src/world_engine/cockpit/crud/locations.py": 7,
     "src/world_engine/cockpit/play_discovery.py": 1,
+    # TICKET-0101, BRIEF-0101-C: `discoverable_detail.subject`, the label a
+    # promotion lists for a detail it moves -- never a knowledge key.
+    "src/world_engine/writes/zone_promotion.py": 3,
 }
 
 A = "11111111-1111-1111-1111-111111111111"
diff --git a/tooling/verify/checks/known_reachability.py b/tooling/verify/checks/known_reachability.py
index 9672dca..fc1a381 100644
--- a/tooling/verify/checks/known_reachability.py
+++ b/tooling/verify/checks/known_reachability.py
@@ -335,6 +335,9 @@ DOCUMENTED_MODULES = frozenset({
     # TICKET-0101, BRIEF-0101-A: returns the literal as a derived link type
     # (`geographic_link_type`); vocabulary site, never a traversal.
     "world_engine/zone_rules.py",
+    # TICKET-0101, BRIEF-0101-C: lists the parent's connects_to rows a
+    # promotion retypes to borde; a write site, never a traversal.
+    "world_engine/writes/zone_promotion.py",
 })
 
 
diff --git a/tooling/verify/checks/zone_promotion.py b/tooling/verify/checks/zone_promotion.py
new file mode 100644
index 0000000..7e99e36
--- /dev/null
+++ b/tooling/verify/checks/zone_promotion.py
@@ -0,0 +1,347 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-C) — a location's first child makes it a zone.
+
+DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
+DATABASE_URL set BEFORE any world_engine import), driven through the real
+creator routes with `TestClient(app, base_url="http://127.0.0.1")`
+(origin_guard). Zero outcomes in any assertion is a FAIL.
+
+Fixture — the Forêt verte example: F (visitable) linked by `connects_to` to
+V; a PC and an NPC at F; the NPC's `matin` schedule at F, its `soir` at V;
+an item lying at F; a discoverable detail at F; an open gathering at F
+holding the NPC. W, visitable and empty.
+
+Five assertions:
+  a. S1: `POST /api/entities` creating E under F without `confirm_promotion`
+     is a 409 whose detail is `{"code": "promotion_required", "preview": …}`
+     listing the link, both beings, the schedule, the item, the detail and
+     the gathering; nothing moved and no E exists. `GET
+     /api/locations/{F}/promotion-preview` returns the same lists.
+  b. Confirmed: the same POST with `confirm_promotion: true` is a 201; F-V is
+     the same relation row, now `borde`, its `change_history` one longer;
+     the PC and the NPC are at E; the NPC's `matin` row is at E and its
+     `soir` row still at V; the item and the detail are at E; the gathering
+     is dissolved.
+  c. Silent promotion: creating a child under W (nothing to move) needs no
+     confirmation (201) and W is a zone.
+  d. Demotion: soft-deleting F's only child makes F visitable again;
+     nothing moves and F-V stays `borde`.
+  e. Re-parent and reactivation: a `PUT` moving location X under V2 (V2
+     holding an NPC) without `confirm_promotion` is a 409 and X keeps its
+     parent; reactivating F's deleted child through an AI `status_change`
+     with F holding a PC again is refused ("Needs attention"), and through
+     `PUT` with `confirm_promotion` it promotes F.
+  f. AMENDMENT-0101-01: a confirmed `PUT` moving Y -- itself a zone (child
+     Ya) -- under V3, which holds an NPC, is a 409 whose detail is a string
+     naming Y as a zone; Y keeps no parent, the NPC stays at V3, nothing is
+     retyped; `GET /api/locations/{V3}/promotion-preview?child_id={Y}` says
+     `target_is_zone`. The same move under W2 (nothing to move) is a 200.
+
+Named mutations: make `promote_parent` ignore `confirmed` -> (a);
+delete the `for being in preview["beings"]` loop of `apply_promotion` ->
+(b); require `confirmed` even when `needs_confirmation` is False -> (c); drop `_zone_promotion_refusal` from `status_change` -> (e); delete
+the `target_is_zone` refusal in `promote_parent` -> (f).
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sys
+import tempfile
+from types import SimpleNamespace
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src"
+
+FAILURES: list[str] = []
+COUNTS: dict[str, int] = {}
+MOVING = ("links", "beings", "schedules", "items", "details", "gatherings")
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
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
+def _location(db, world_id: str, name: str, parent=None) -> str:
+    from world_engine.models import Entity, Location
+
+    entity = Entity(world_id=world_id, type="location", name=name)
+    db.add(entity)
+    db.flush()
+    db.add(Location(id=entity.id, parent_location_id=parent))
+    db.commit()
+    return entity.id
+
+
+def _character(db, world_id: str, name: str, ctype: str, at: str, user_id=None) -> str:
+    from world_engine.models import Character, Entity
+
+    entity = Entity(world_id=world_id, type="character", name=name)
+    db.add(entity)
+    db.flush()
+    db.add(Character(id=entity.id, world_id=world_id, character_type=ctype, user_id=user_id, current_location_id=at))
+    db.commit()
+    return entity.id
+
+
+def _seed(db) -> dict[str, str]:
+    from world_engine.models import (
+        DiscoverableDetail, Entity, Gathering, GatheringMember, Item, NpcSchedule, Session, User, World,
+    )
+    from world_engine.writes.relations import write_relation
+
+    world = World(name="Aestia check", is_active=True)
+    db.add(world)
+    db.commit()
+    w = world.id
+    ids = {"world": w}
+    for label in ("F", "V", "W", "V2", "X", "V3", "W2", "Y"):
+        ids[label] = _location(db, w, f"Lieu {label}")
+    ids["Ya"] = _location(db, w, "Lieu Ya", parent=ids["Y"])
+    write_relation(db, mode="set", world_id=w, entity_a_id=ids["F"], entity_b_id=ids["V"],
+                   type="connects_to", value=50, direction="mutual")
+    db.commit()
+    user = User(name="creator", role="creator")
+    db.add(user)
+    db.commit()
+    ids["P"] = _character(db, w, "Millys", "player", ids["F"], user.id)
+    ids["N"] = _character(db, w, "Garde", "npc", ids["F"])
+    ids["N2"] = _character(db, w, "Veilleur", "npc", ids["V2"])
+    ids["N3"] = _character(db, w, "Passeur", "npc", ids["V3"])
+    db.add(NpcSchedule(world_id=w, npc_id=ids["N"], phase="matin", location_id=ids["F"]))
+    db.add(NpcSchedule(world_id=w, npc_id=ids["N"], phase="soir", location_id=ids["V"]))
+    item = Entity(world_id=w, type="item", name="Lanterne")
+    db.add(item)
+    db.flush()
+    db.add(Item(id=item.id, location_id=ids["F"]))
+    detail = DiscoverableDetail(world_id=w, location_id=ids["F"], subject="trace", content="Une trace.")
+    db.add(detail)
+    sess = Session(world_id=w, number=1)
+    db.add(sess)
+    db.flush()
+    gathering = Gathering(world_id=w, session_id=sess.id, location_id=ids["F"])
+    db.add(gathering)
+    db.flush()
+    db.add(GatheringMember(gathering_id=gathering.id, entity_id=ids["N"]))
+    db.commit()
+    ids.update(item=item.id, detail=detail.id, gathering=gathering.id)
+    return ids
+
+
+def _body(name: str, parent: str, confirm: bool = False) -> dict:
+    body = {"entity": {"name": name, "type": "location", "status": "active"},
+            "extension": {"parent_location_id": parent}}
+    if confirm:
+        body["confirm_promotion"] = True
+    return body
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
+def _where(db, character_id: str):
+    from world_engine.models import Character
+
+    return db.get(Character, character_id).current_location_id
+
+
+def check_a_refused(client, engine, ids) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Entity
+
+    n = 0
+    resp = client.post("/api/entities", json=_body("Entrée de la forêt", ids["F"]))
+    detail = resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else None
+    if resp.status_code != 409 or not isinstance(detail, dict) or detail.get("code") != "promotion_required":
+        fail(f"(a) unconfirmed promotion answered {resp.status_code} {resp.text[:160]}")
+        return
+    preview = detail["preview"]
+    sizes = {key: len(preview[key]) for key in MOVING}
+    expected = {"links": 1, "beings": 2, "schedules": 1, "items": 1, "details": 1, "gatherings": 1}
+    if sizes != expected:
+        fail(f"(a) preview lists {sizes}, expected {expected}")
+    n += sum(sizes.values())
+    with Session(engine) as db:
+        if db.exec(select(Entity).where(Entity.name == "Entrée de la forêt")).first() is not None:
+            fail("(a) the refused create left its entity behind")
+        if _where(db, ids["P"]) != ids["F"] or _rel(db, ids["F"], ids["V"]).type != "connects_to":
+            fail("(a) the refused create moved something")
+    got = client.get(f"/api/locations/{ids['F']}/promotion-preview").json()
+    if {key: len(got[key]) for key in MOVING} != expected:
+        fail("(a) GET promotion-preview disagrees with the 409 preview")
+    COUNTS["a"] = n
+
+
+def check_b_confirmed(client, engine, ids) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import DiscoverableDetail, Gathering, Item, NpcSchedule
+
+    with Session(engine) as db:
+        rel = _rel(db, ids["F"], ids["V"])
+        rel_id, history = rel.id, len(rel.change_history or [])
+    resp = client.post("/api/entities", json=_body("Entrée de la forêt", ids["F"], confirm=True))
+    if resp.status_code != 201:
+        fail(f"(b) confirmed promotion answered {resp.status_code} {resp.text[:160]}")
+        return
+    child = resp.json()["id"]
+    ids["E"] = child
+    n = 0
+    with Session(engine) as db:
+        rel = _rel(db, ids["F"], ids["V"])
+        n += _expect(rel.id == rel_id and rel.type == "borde" and len(rel.change_history) == history + 1,
+                     f"(b) F-V after promotion: id kept={rel.id == rel_id}, type={rel.type!r}")
+        for being in ("P", "N"):
+            n += _expect(_where(db, ids[being]) == child, f"(b) {being} not moved to the first child")
+        rows = {r.phase: r.location_id for r in db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == ids["N"])).all()}
+        n += _expect(rows == {"matin": child, "soir": ids["V"]}, f"(b) schedule after promotion: {rows}")
+        n += _expect(db.get(Item, ids["item"]).location_id == child, "(b) item not moved")
+        n += _expect(db.get(DiscoverableDetail, ids["detail"]).location_id == child, "(b) detail not moved")
+        n += _expect(db.get(Gathering, ids["gathering"]).status == "dissolved", "(b) gathering left open")
+    COUNTS["b"] = n
+
+
+def _expect(ok: bool, msg: str) -> int:
+    if not ok:
+        fail(msg)
+        return 0
+    return 1
+
+
+def check_c_silent(client, engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine.zone_rules import is_zone
+
+    resp = client.post("/api/entities", json=_body("Coin de W", ids["W"]))
+    with Session(engine) as db:
+        COUNTS["c"] = _expect(resp.status_code == 201 and is_zone(db, ids["W"]),
+                              f"(c) silent promotion answered {resp.status_code}")
+
+
+def check_d_demotion(client, engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine.zone_rules import is_zone
+
+    resp = client.post(f"/api/entities/{ids['E']}/delete")
+    with Session(engine) as db:
+        n = _expect(resp.status_code == 200 and not is_zone(db, ids["F"]), "(d) F still a zone without children")
+        n += _expect(_rel(db, ids["F"], ids["V"]).type == "borde", "(d) F-V changed on demotion")
+        n += _expect(_where(db, ids["P"]) == ids["E"], "(d) demotion moved the PC")
+    COUNTS["d"] = n
+
+
+def check_e_update_paths(client, engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.mutations import _mutation_apply_status_change
+    from world_engine.models import Character, Location
+    from world_engine.zone_rules import is_zone
+
+    n = 0
+    body = {"entity": {"name": "Lieu X", "type": "location", "status": "active"},
+            "extension": {"parent_location_id": ids["V2"]}}
+    resp = client.put(f"/api/entities/{ids['X']}", json=body)
+    with Session(engine) as db:
+        n += _expect(resp.status_code == 409 and db.get(Location, ids["X"]).parent_location_id is None,
+                     f"(e) unconfirmed re-parent answered {resp.status_code}")
+    with Session(engine) as db:
+        db.get(Character, ids["P"]).current_location_id = ids["F"]
+        db.commit()
+        mut = SimpleNamespace(id="m", world_id=ids["world"], target_id=None)
+        message = _mutation_apply_status_change(mut, {"entity_id": ids["E"], "status": "active"}, db)
+        db.rollback()
+        n += _expect(bool(message), "(e) an AI status_change promoted F without the dialog")
+    body = {"entity": {"name": "Entrée de la forêt", "type": "location", "status": "active"},
+            "extension": {"parent_location_id": ids["F"]}, "confirm_promotion": True}
+    resp = client.put(f"/api/entities/{ids['E']}", json=body)
+    with Session(engine) as db:
+        n += _expect(resp.status_code == 200 and is_zone(db, ids["F"]) and _where(db, ids["P"]) == ids["E"],
+                     f"(e) confirmed reactivation answered {resp.status_code}")
+    COUNTS["e"] = n
+
+
+def check_f_target_is_zone(client, engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Location
+
+    body = {"entity": {"name": "Lieu Y", "type": "location", "status": "active"},
+            "extension": {"parent_location_id": ids["V3"]}, "confirm_promotion": True}
+    resp = client.put(f"/api/entities/{ids['Y']}", json=body)
+    detail = resp.json().get("detail")
+    n = _expect(resp.status_code == 409 and isinstance(detail, str) and "Lieu Y" in detail and "zone" in detail,
+                f"(f) re-parenting a zone under an inhabited place answered {resp.status_code} {resp.text[:160]}")
+    with Session(engine) as db:
+        n += _expect(db.get(Location, ids["Y"]).parent_location_id is None, "(f) Y was re-parented")
+        n += _expect(_where(db, ids["N3"]) == ids["V3"], "(f) the NPC left V3")
+    got = client.get(f"/api/locations/{ids['V3']}/promotion-preview?child_id={ids['Y']}").json()
+    n += _expect(got.get("target_is_zone") is True and got.get("needs_confirmation") is True,
+                 f"(f) preview flags: {got.get('target_is_zone')}, {got.get('needs_confirmation')}")
+    body["extension"]["parent_location_id"] = ids["W2"]
+    resp = client.put(f"/api/entities/{ids['Y']}", json=body)
+    n += _expect(resp.status_code == 200, f"(f) re-parenting a zone under an empty place answered {resp.status_code}")
+    COUNTS["f"] = n
+
+
+def main() -> int:
+    engine = _fresh_engine()
+    from fastapi.testclient import TestClient
+    from sqlmodel import Session
+
+    from world_engine.cockpit.app import app
+
+    with Session(engine) as db:
+        ids = _seed(db)
+    client = TestClient(app, base_url="http://127.0.0.1")
+    check_a_refused(client, engine, ids)
+    check_b_confirmed(client, engine, ids)
+    if "E" in ids:
+        check_c_silent(client, engine, ids)
+        check_d_demotion(client, engine, ids)
+        check_e_update_paths(client, engine, ids)
+        check_f_target_is_zone(client, engine, ids)
+
+    for key in ("a", "b", "c", "d", "e", "f"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero outcomes examined")
+
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_promotion — "
+        f"(a) S1 refusal + preview [{COUNTS['a']} rows], (b) K applied [{COUNTS['b']}], "
+        f"(c) silent promotion [{COUNTS['c']}], (d) demotion moves nothing [{COUNTS['d']}], "
+        f"(e) re-parent / reactivation [{COUNTS['e']}], (f) a zone child receives nothing [{COUNTS['f']}]"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- The neighbour checkboxes at child creation and everything room-batch (E): here the room batch still promotes its anchor only when nothing moves, and otherwise reports `promotion_required`.
- Moving doors, bounds or obstacles to the child (K: the inner plan stays dormant on the zone).
- Moving events, facts, knowledge, `controls`, artefacts (K: untouched).
- Any action when a zone loses its last child (K: nothing moves, its `borde` rows stay).
- Re-targeting a promotion's contents into a zone child's descendants (P2-2, rejected by AMENDMENT-0101-01).
- Copying the parent's links to the child (E offers them).

## Invariants to defend

- **Creator control is structural** (CLAUDE.md): an AI `status_change` can never promote with moves; only the fiche's confirmed write does.
- **Creator-CRUD location edits close gatherings; an emptied gathering is dissolved** (CLAUDE.md): the moved beings go through `close_open_memberships` / `attach_on_arrival`, and `dissolve_emptied` runs after the commit, never before.
- **History is sacred**: links retype through `write_relation(mode="set")`.
- **Commit before touching a canon-write path**: this brief adds one (`apply_promotion`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `single_canon_write.py` names a write site of `apply_promotion` other than `item` and `discoverable_detail`.
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
- `zone_promotion.py` → `PASS: zone_promotion — (a) S1 refusal + preview [7 rows], (b) K applied [7], (c) silent promotion [1], (d) demotion moves nothing [3], (e) re-parent / reactivation [3], (f) a zone child receives nothing [5]`.
- `single_canon_write.py`, `knowledge_identity.py`, `known_reachability.py`, `function_length.py`, `frontend_build_fresh.py`, `effect_self_write.py`, `decisions_index.py` → `PASS`.
- The five named mutations failed as stated.
- `corpus_gate.py` → 132/132.
- Live: on Lieux, « + Nouveau », name « Entrée de la forêt », parent « Forêt verte » (which has a neighbour, a character, a schedule, an item and a detail), Save → « Ce lieu devient une zone » lists them; Confirmer → saved, the character now stands in the Entrée.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A FIRST CHILD MAKES A ZONE (TICKET-0101) -- PROMOTION, CONFIRMED (BRIEF-0101-c, no schema change)` and the policy line — in the diff.
