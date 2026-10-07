# BRIEF 0109-A — "v2.18: an item is a kind held in quantity; the quest-term tables laid"

Lot: LOT-0109-quest-terms.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (`main` at `1f80b9f` or later, schema v2.17).

- `src/world_engine/models/canon.py:545` -> `class Item(SQLModel, table=True):`; `:549` -> `"NOT equipped OR owner_id IS NOT NULL", name="ck_item_equipped_owner"`.
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.17"`.
- `src/world_engine/scene_format.py:94` -> `.where(Item.owner_id == player_character_id)`.
- `src/world_engine/cockpit/play_stream.py:216` -> `def _find_player_item(db: Session, player_id: str, item_name: str) -> Optional[tuple[Item, Entity]]:`; `:226` -> `.where(Item.owner_id == player_id, Entity.name == item_name)`.
- `src/world_engine/cockpit/crud/entities.py:201` -> the `equipped` registry field; `:345` -> `_PLACEMENT_FIELDS: dict[str, tuple[str, str]] = {`; `:903` -> `@router.get("/entities/{entity_id}/items")`; the file is 926 lines.
- `src/world_engine/cockpit/routes/mutations.py:460` -> `"item_update": _mutations._mutation_apply_item_update,`.
- `src/world_engine/cockpit/mutations.py:482` -> `def _mutation_apply_item_update(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:`.
- `tooling/verify/canon_write_policy.txt:87` -> `src/world_engine/cockpit/mutations.py::_mutation_apply_item_update      item`.
- `src/world_engine/writes/worlds.py:77` -> `"world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",`.
- `src/world_engine/writes/zone_promotion.py:86` -> `def _items(db: Session, parent_id: str) -> list[dict]:`; `:89` -> `.where(Item.location_id == parent_id).order_by(Entity.name)`.
- `src/world_engine/models/quests.py:120` -> `class Quest(SQLModel, table=True):`.
- `tooling/verify/checks/json_ui_boundary.py:58` -> `"QuestOffer.change_history",`.
- `tooling/verify/checks/world_cascade.py:67` -> `_FIXTURE: tuple[tuple[str, dict], ...] = (`.
- `scripts/migrate_v2_12_zone_borde.py:151` -> `select(Item, Entity).join(Entity, Entity.id == Item.id).where(Item.location_id.in_(zones))`.
- `scripts/seed_pilot.py:3395` -> `owner_id="char-player",`; `:3397` -> `equipped=True,`.
- `frontend/src/creation/Sheet.svelte:820` -> `<div id="author-items"><ItemsPanel entityId={detail.id} /></div>`; `frontend/src/creation/ItemsPanel.svelte` is 39 lines, read-only.
- No `item_holding`, `quest_offer_term`, `quest_term` or `quest_economy` table exists in `src/world_engine/models/`; no `scripts/migrate_v2_18_*.py` and no `tooling/verify/checks/quest_rewards.py` exist.

## Facts carried

### R-01 — an item is one entity with one owner [M]
Opened: `src/world_engine/models/canon.py:540-564` (`Item`: `owner_id`,
`location_id`, `equipped`, `condition`; `ck_item_equipped_owner`; indexes on
owner and location).
Finding: possession and place are columns of the object itself: ten furs
would be ten entities.
Consequence: A1 -- `item` a kind, `item_holding` (holder, quantity).

### R-02 — the readers of possession and place [M]
Opened: `src/world_engine/scene_format.py:83-110` (the MJ's inventory line
and the interpretation list, both `Item.owner_id`);
`src/world_engine/cockpit/play_stream.py:216-227` (`_find_player_item`: the
binary possession check, by exact `Entity.name`);
`src/world_engine/cockpit/play.py:345-356` (its caller's docstring);
`src/world_engine/cockpit/crud/entities.py:195-202` (registry fields
`owner_id`, `location_id`, `equipped`, `condition`), `:345-361`
(`_PLACEMENT_FIELDS`: an item's `location_id` refused in a zone), `:380-384`
(the equip guard), `:903-925` (`GET /entities/{id}/items`).
Consequence: every reader moves to `holdings.py`; the interpretation list
keeps names only (the model answers a name, the check matches it exactly);
the registry keeps `condition` and gains `value`.

### R-03 — `item_update` has no producer [M]
Opened: `src/world_engine/cockpit/mutations.py:477-498` (the equip toggle),
`src/world_engine/cockpit/routes/mutations.py:375-390` (« dormant since
BRIEF-08/D2a.1 — no live code path produces it ») and `:460`;
`tooling/verify/canon_write_policy.txt:87`.
Consequence: retired with `equipped` (Nia: « cela ne sert à rien »).

### R-04 — no item lies in a zone [M]
Opened: `CLAUDE.md:226-231`; `src/world_engine/zone_rules.py:76-84`
(`require_visitable`); `src/world_engine/writes/zone_promotion.py:86-91`
(`_items`: items at the parent), `:166-173` (moved by setting
`location_id`); `tooling/verify/checks/zone_placement.py:1-40`, `:180-183`
(« fiche, item »); `tooling/verify/checks/zone_promotion.py:125-131`,
`:221`.
Consequence: `write_holding` refuses a zone that RECEIVES; taking out of a
place that just became a zone is allowed -- the promotion moves a place's
holdings to its first child through it.

### R-05 — scripts that read items through today's models [M]
Opened: `scripts/migrate_v2_12_zone_borde.py:135-160` (its report reads
`Item.location_id` through the model; `tooling/verify/checks/
zone_migration.py` runs it on a database built from today's models);
`scripts/seed_pilot.py:3381-3399` (`Item(owner_id=..., equipped=True)`).
Consequence: the v2.12 report reads the column in raw SQL when it exists;
the seed gives the dagger as a holding.

### R-06 — a number field [M]
Opened: `src/world_engine/cockpit/crud/_shared.py:80-110` (`kind:
"number"`, `default`, `min`/`max` clamped).

### R-07 — tables a world owns, and JSON columns [M]
Opened: `src/world_engine/writes/worlds.py:66-78`;
`tooling/verify/checks/world_cascade.py:1-35`, `:60-200`;
`tooling/verify/checks/json_ui_boundary.py:43-58`.
Consequence: the four new tables named in the cascade and its fixture;
`ItemHolding.change_history` allow-listed.

### R-16 — one config row per world [M]
Opened: `src/world_engine/models/config.py:26-58`
(`ConversationWindowConfig`: unique per world, absence reads defaults, the
reader never writes).
Consequence: `quest_economy`, same shape.

### R-17 — the migration's shape [M]
Opened: `scripts/migrate_v2_17_quests.py` (env guard, refusal, raw-
connection rebuild, tables from models, FK post-check scoped to the tables
it writes, `schema_meta` convergence); `src/world_engine/schema_version.py:
15`. `item` and `quest` v2.17 DDL dumped from `main` (embedded in
`quest_rewards.py`).

### R-18 — the surfaces [M]
Opened: `frontend/src/creation/ItemsPanel.svelte:1-40` (read-only);
`frontend/src/creation/Sheet.svelte:818-825` (the panel on a character
only); `frontend/src/creation/sheetRequest.svelte.js:30-35` (`api()`
throws `Error(detail)`); `frontend/src/creation/QuestOffers.svelte:121`,
`questOffers.svelte.js:62-73`; `frontend/src/journee/QuestPanel.svelte:
45-66`, `quests.svelte.js:58-64`;
`tooling/verify/checks/creation_island.py` (unchanged: no new island).

### R-19 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40/1000 per `src/`
module), `tooling/verify/checks/function_length.py:29` (80).
Consequence: four new modules (`holdings.py`, `writes/items.py`,
`writes/quest_terms.py`, `writes/quest_settlement.py`) and three reads
(`quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`); none
over budget.

## Contracts

### C-01 — schema v2.18
Produced by: BRIEF-0109-A   Consumed by: B, C, D
- `item(id -> entity, condition DEFAULT 'intact', value INTEGER NOT NULL
  DEFAULT 1 CHECK (value >= 0))`.
- `item_holding(id, world_id, item_id -> item, holder_entity_id -> entity,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0), updated_at,
  change_history JSON)`, unique `(item_id, holder_entity_id)`, index on
  `holder_entity_id`.
- `quest_offer_term(id, world_id, offer_id -> quest_offer, term_order,
  direction, currency, counterparty_entity_id -> entity, item_id -> item,
  fact_id -> fact, skill_key, amount, level)` and `quest_term` (same,
  `quest_id -> quest`), three CHECKs each, byte for byte:
  ```
  direction IN ('cost','reward')
  currency IN ('money','item','relation','fact','skill')
  (currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)
  ```
- `quest_economy(id, world_id unique, rate_money, rate_relation, rate_fact,
  rate_skill, band_low_pct, band_high_pct -- each NULL or >= 0, updated_at)`.
- `quest.settled_at DATETIME NULL`.

### C-02 — holdings
Produced by: BRIEF-0109-A   Consumed by: C
- `writes.write_holding(db, *, world_id, item_id, holder_entity_id,
  quantity=None, delta=None, changed_by) -> ItemHolding`: case table (b-1).
- `holdings.held_quantity(db, holder, item) -> int` (0 when none);
  `items_held(db, holder) -> [(ItemHolding, Item, Entity)]` and
  `holders_of(db, item) -> [(ItemHolding, Entity)]`, `quantity > 0`, by
  name; `held_label(name, n)` -> « name » or « name ×n ».
- Routes (creator CRUD, `crud/items.py`): `GET /api/items/{id}/holders`
  -> `[{id, name, type, quantity}]`; `PUT /api/item-holdings {item_id,
  holder_entity_id, quantity}` -> 200, 422 on a refusal.
  `GET /api/entities/{id}/items` -> `[{id, name, quantity, condition,
  value}]`.

### C-08 — the surfaces
Produced by: BRIEF-0109-D   Consumed by: nothing in this lot
- `frontend/src/creation/questTerms.js`: `TERM_DIRECTIONS`,
  `CURRENCY_FORMS[c] = {label, list, counted, personal}` in C-03's order.
- Création › Quêtes: « Coûts » / « Récompenses » (`QuestTermRow.svelte`),
  the live value and verdict, ⚖ the world's rates.
- Journée: offer and quest term lines; « Déclarer accomplie » under
  `settleable`; `SettlementRecap.svelte` with « Confirmer : quête
  accomplie », disabled while `can_settle` is false.
- Sheets: « Objets » on a character, a faction, a location (what it holds)
  and « Détenu par » on an item; each row's quantity editable, 0 removes.

## Case tables carried (lot, gate output (b))

**b-1 — `write_holding`**, checked in this order:

| input | result |
|---|---|
| both or neither of `quantity`/`delta` | `ValueError` |
| `quantity`/`delta` not an integer | `ValueError` |
| item not an item of the world | `ValueError` |
| holder not an active entity of the world | `ValueError` |
| holder a location that is a zone, and the quantity grows | `ValueError` (the zone message) |
| holder a zone, and the quantity falls | accepted |
| result below 0 | `ValueError` |
| otherwise | the row (created at 0 when absent), previous quantity appended to `change_history` |

**b-2 — the migration's holdings** (per item, at v2.17):

| `owner_id` | `location_id` | holding | note |
|---|---|---|---|
| set, alive | -- | owner, 1 | -- |
| -- | set, alive | place, 1 | « lies in a zone » when the place is a zone (kept) |
| set | set | owner, 1 | « owner kept, place dropped » |
| -- | -- | none | -- |
| set, gone | any | none | « holder no longer exists, skipped » |

## Context

Nia locked A1: an item is a kind, and who holds how many of it -- a character, a faction, a place -- is an `item_holding` row; `equipped` disappears (« cela ne sert à rien »), and `item_update`, its only writer, with it. This brief lays all of v2.18 in one migration (F1): the holdings, `item.value` for the indicative unit (E1), and the tables B and C fill -- the offer's and the quest's terms, the world's rates, `quest.settled_at`. It moves every reader of possession and place to `holdings.py` and makes the sheets' « Objets » panel editable.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `models/canon.py`: `Item` keeps `id`, `condition`, gains `value` (`CHECK (value >= 0)`), loses `owner_id`, `location_id`, `equipped`, the CHECK and both indexes; adds `ItemHolding` (C-01);
   - in `models/quests.py`: `Quest.settled_at`; `QUEST_TERM_DIRECTIONS`, `QUEST_TERM_CURRENCIES`, the three CHECK texts; `QuestOfferTerm`, `QuestTerm`, `QuestEconomy` (C-01); exports them from `models/__init__.py`;
   - creates `src/world_engine/holdings.py` and `src/world_engine/writes/items.py` (`write_holding`, b-1), exported by `writes`; allow-lists `write_holding` in `canon_write_policy.txt` and removes the `item_update` line;
   - `scene_format.py`: the inventory line with quantities, the interpretation list names only; `play_stream._find_player_item` joins a holding of quantity > 0 (its caller's docstring in `play.py`);
   - `crud/entities.py`: the item registry keeps `condition`, gains `value` (`kind: "number"`, `min: 0`); `_PLACEMENT_FIELDS` names characters only; the equip guard removed; `GET /entities/{id}/items` reads holdings (C-02); creates `crud/items.py` (`GET /api/items/{id}/holders`, `PUT /api/item-holdings`) and re-exports it from `crud/__init__.py`;
   - `writes/zone_promotion.py`: a place's holdings move to the first child through `write_holding`;
   - retires `item_update`: the applier in `cockpit/mutations.py`, its key in `routes/mutations.py`'s `appliers` (E3);
   - the four tables in `writes/worlds._DIRECT_WORLD_SCOPED_DELETES` and one fixture row each in `world_cascade.py`; `ItemHolding.change_history` allow-listed in `json_ui_boundary.py`;
   - `scripts/migrate_v2_12_zone_borde.py`: its report reads `item.location_id` in raw SQL, only when the column exists (R-05); `scripts/seed_pilot.py`: the dagger as a holding of 1;
   - `zone_placement.py` (« holding, item ») and `zone_promotion.py` (holdings moved) follow;
   - bumps the version to v2.18 (constant, schema doc header), documents the five tables and the column, adds the v2.18 changelog entry;
   - creates `scripts/migrate_v2_18_quest_terms.py` (the v2.17 migration's shape: env guard, refusal below v2.17, holdings planned from `owner_id`/`location_id` per b-2 before the rebuild, the raw-connection rebuild of `item` and `quest`, tables created from their models, post-checks scoped to the tables it writes, `schema_meta` convergence);
   - `ItemsPanel.svelte` editable (`entityId`, `entityType`; « Détenu par » on an item), mounted by `Sheet.svelte` on a character, a faction, a location and an item;
   - creates `tooling/verify/checks/quest_rewards.py` with RA1-RA3;
   - appends the decision entry above the `---` / `*Co-built…*` footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build`.
4. Commit message: `feat(items): an item is a kind held in quantity; quest terms and economy tables, schema v2.18 (BRIEF-0109-a)`.

````diff
diff --git a/frontend/src/creation/ItemsPanel.svelte b/frontend/src/creation/ItemsPanel.svelte
index fefb3be..9a2bae8 100644
--- a/frontend/src/creation/ItemsPanel.svelte
+++ b/frontend/src/creation/ItemsPanel.svelte
@@ -1,39 +1,86 @@
 <script>
-  /* TICKET-0058 (BRIEF-0058-g, family d). Faithful port of the read-only
-     "Items" section on a character sheet -- authorLoadItems/authorRenderItems
-     (index.html, now deleted). Single write path is the entity/item flow
-     elsewhere; this panel only reads GET /api/entities/{id}/items. */
-  let { entityId } = $props();
+  /* TICKET-0058 (BRIEF-0058-g, family d) read-only port; editable since
+     TICKET-0109 (BRIEF-0109-A, A1). An item is a kind held in quantity:
+     on a character, faction or location sheet this panel lists what that
+     entity holds; on an item's sheet, who holds it. Every change is one
+     PUT /api/item-holdings (absolute quantity; 0 removes it from the list).
+     The server refuses a zone as a place that receives. */
+  import { api } from './sheetRequest.svelte.js';
 
-  let items = $state([]);
+  let { entityId, entityType } = $props();
+
+  let rows = $state([]);
+  let choices = $state([]);
   let loadError = $state('');
+  let saveError = $state('');
+  let busy = $state(false);
+  let adding = $state({ id: '', quantity: 1 });
+
+  let ofItem = $derived(entityType === 'item');
 
   async function load() {
     try {
-      items = await fetch(`/api/entities/${encodeURIComponent(entityId)}/items`).then((r) => r.json());
+      rows = await api(ofItem
+        ? `/api/items/${encodeURIComponent(entityId)}/holders`
+        : `/api/entities/${encodeURIComponent(entityId)}/items`);
+      const all = ofItem
+        ? (await Promise.all(['character', 'faction', 'location'].map((t) => api('/api/entities?type=' + t)))).flat()
+        : await api('/api/entities?type=item');
+      choices = all.filter((e) => e.id !== entityId);
       loadError = '';
     } catch (e) {
       loadError = e.message;
     }
   }
 
-  $effect(() => { load(); });
+  $effect(() => { void entityId; load(); });
+
+  async function setQuantity(otherId, quantity) {
+    busy = true;
+    saveError = '';
+    const body = ofItem
+      ? { item_id: entityId, holder_entity_id: otherId, quantity: Number(quantity) }
+      : { item_id: otherId, holder_entity_id: entityId, quantity: Number(quantity) };
+    try {
+      await api('/api/item-holdings', {
+        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
+      });
+      adding = { id: '', quantity: 1 };
+      await load();
+    } catch (e) {
+      saveError = e.message;
+    } finally {
+      busy = false;
+    }
+  }
 </script>
 
 {#if loadError}
   <div class="empty">{loadError}</div>
-{:else if items.length === 0}
-  <div class="empty">No items.</div>
 {:else}
-  <div class="row-table">
-    {#each items as it}
-      <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;">
-        <span>{it.name}</span>
-        <span style="display:flex; align-items:center; gap:8px;">
-          <span style="color:var(--muted); font-size:12px;">{it.condition}</span>
-          <span class="badge {it.equipped ? 'b-equipped' : 'b-stowed'}">{it.equipped ? 'equipped' : 'stowed'}</span>
-        </span>
-      </div>
-    {/each}
+  {#if rows.length === 0}
+    <div class="empty">{ofItem ? 'Personne ne le détient.' : 'Aucun objet.'}</div>
+  {:else}
+    <div class="row-table">
+      {#each rows as r (r.id)}
+        <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;">
+          <span>{r.name}{#if !ofItem && r.condition && r.condition !== 'intact'} <span style="color:var(--muted); font-size:12px;">({r.condition})</span>{/if}</span>
+          <span style="display:flex; align-items:center; gap:6px;">
+            <input type="number" min="0" style="width:64px" value={r.quantity} disabled={busy}
+                   onchange={(e) => setQuantity(r.id, e.currentTarget.value)}>
+            <button class="btn-icon" title="Retirer" disabled={busy} onclick={() => setQuantity(r.id, 0)}>✕</button>
+          </span>
+        </div>
+      {/each}
+    </div>
+  {/if}
+  <div style="display:flex; gap:6px; align-items:center; margin-top:6px;">
+    <select bind:value={adding.id} disabled={busy}>
+      <option value="">{ofItem ? '— donner à —' : '— ajouter un objet —'}</option>
+      {#each choices as c (c.id)}<option value={c.id}>{c.name}{ofItem ? ` (${c.type})` : ''}</option>{/each}
+    </select>
+    <input type="number" min="1" style="width:64px" bind:value={adding.quantity} disabled={busy}>
+    <button disabled={busy || !adding.id} onclick={() => setQuantity(adding.id, adding.quantity)}>Ajouter</button>
   </div>
+  {#if saveError}<div style="color:var(--red); font-size:12px;">{saveError}</div>{/if}
 {/if}
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 686c10d..1d479ba 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -815,10 +815,13 @@
         </div>
       {/if}
 
-      {#if !isNew && type === 'character'}
-        <div class="field-section"><div class="field-section-title">Items</div>
-          <div id="author-items"><ItemsPanel entityId={detail.id} /></div>
+      {#if !isNew && ['character', 'faction', 'location', 'item'].includes(type)}
+        <div class="field-section"><div class="field-section-title">{type === 'item' ? 'Détenu par' : 'Objets'}</div>
+          <div id="author-items"><ItemsPanel entityId={detail.id} entityType={type} /></div>
         </div>
+      {/if}
+
+      {#if !isNew && type === 'character'}
         <div class="field-section"><div class="field-section-title">Appartenances</div>
           <MembershipsPanel entityId={detail.id} {legacyDoc} />
         </div>
diff --git a/scripts/migrate_v2_12_zone_borde.py b/scripts/migrate_v2_12_zone_borde.py
index 8faa558..63246e9 100644
--- a/scripts/migrate_v2_12_zone_borde.py
+++ b/scripts/migrate_v2_12_zone_borde.py
@@ -58,7 +58,7 @@ from sqlmodel import Session, select  # noqa: E402
 from world_engine import models  # noqa: E402
 from world_engine.db import engine  # noqa: E402
 from world_engine.models import (  # noqa: E402
-    Character, DiscoverableDetail, Entity, Item, NpcSchedule, Relation, World,
+    Character, DiscoverableDetail, Entity, NpcSchedule, Relation, World,
 )
 from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
 from world_engine.writes.relations import write_relation  # noqa: E402
@@ -147,10 +147,17 @@ def _report(session: Session, zones: set[str]) -> int:
         npc = session.get(Entity, row.npc_id)
         lines.append(f"  horaire {row.phase} de « {npc.name if npc else row.npc_id} » vise la zone "
                      f"« {names[row.location_id]} »")
-    for item, ent in session.exec(
-        select(Item, Entity).join(Entity, Entity.id == Item.id).where(Item.location_id.in_(zones))
-    ).all():
-        lines.append(f"  objet « {ent.name} » est posé dans la zone « {names[item.location_id]} »")
+    # Raw SQL (TICKET-0109): `item.location_id` exists on a v2.11/v2.12
+    # database; the v2.18 model no longer declares it, and a database built
+    # from today's models has no such column -- then no item lies anywhere.
+    item_columns = {row[1] for row in session.execute(text("PRAGMA table_info(item)")).fetchall()}
+    placed = session.execute(text(
+        "SELECT e.name, i.location_id FROM item i JOIN entity e ON e.id = i.id "
+        "WHERE i.location_id IS NOT NULL"
+    )).fetchall() if "location_id" in item_columns else []
+    for item_name, location_id in placed:
+        if location_id in zones:
+            lines.append(f"  objet « {item_name} » est posé dans la zone « {names[location_id]} »")
     for detail in session.exec(select(DiscoverableDetail).where(DiscoverableDetail.location_id.in_(zones))).all():
         lines.append(f"  détail « {detail.subject} » est dans la zone « {names[detail.location_id]} »")
     for line in lines:
diff --git a/scripts/migrate_v2_18_quest_terms.py b/scripts/migrate_v2_18_quest_terms.py
new file mode 100644
index 0000000..69f624a
--- /dev/null
+++ b/scripts/migrate_v2_18_quest_terms.py
@@ -0,0 +1,237 @@
+"""Migration v2.18 — objects held in quantity, quest terms, the quest economy
+(TICKET-0109, BRIEF-0109-A, decisions A1, B1, D1, E1).
+
+1. Holdings (A1). Every `item` row becomes a KIND: one `item_holding` of
+   quantity 1 for its `owner_id` when set, else for its `location_id` when
+   set (an object lying somewhere is held by that place). An item with both
+   keeps its owner's holding; its place is listed, never kept. A holder that
+   no longer exists is listed and skipped. A place that is now a zone keeps
+   its holding and is listed (the v2.12 posture: existing data is reported,
+   never moved).
+2. Rebuild. `item` is rebuilt from the model: `owner_id`, `location_id`,
+   `equipped` and the CHECK that tied them are dropped; `value` is added
+   (default 1). Columns copied: `id`, `condition`.
+3. Create. `item_holding`, `quest_offer_term`, `quest_term`, `quest_economy`
+   from their models, when missing; `quest.settled_at` (nullable) added.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.17 (the migrations are sequential), before any change.
+
+Idempotent: steps 1-2 run only while `item` still has `owner_id`; each table
+and the column are created only when missing.
+
+Post-checks, before `schema_meta` converges: `item` has the model's columns
+and its row count is unchanged; one holding per item that had a living
+owner or place; the four tables and `quest.settled_at` exist; `PRAGMA
+foreign_key_check` is empty on the six tables this migration writes. A
+dangling reference elsewhere in the database predates it: it is listed,
+never a reason to stop (AMENDMENT-0107-01).
+
+Run from the project root:
+
+    python scripts/migrate_v2_18_quest_terms.py
+"""
+
+from __future__ import annotations
+
+import json
+import os
+import sys
+import uuid
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_18_quest_terms.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+from world_engine.zone_rules import is_zone  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.17"
+_NEW_MODELS = (models.ItemHolding, models.QuestOfferTerm, models.QuestTerm, models.QuestEconomy)
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("item", "quest") + tuple(m.__tablename__ for m in _NEW_MODELS)
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _columns(table: str) -> set[str]:
+    return {c["name"] for c in inspect(engine).get_columns(table)}
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.18 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _plan_holdings() -> tuple[list[tuple], list[str]]:
+    """(world_id, item_id, holder_id) per item to hold, and the notes."""
+    holdings: list[tuple] = []
+    notes: list[str] = []
+    with Session(engine) as session:
+        rows = session.execute(text(
+            "SELECT i.id, e.world_id, e.name, i.owner_id, i.location_id FROM item i "
+            "JOIN entity e ON e.id = i.id ORDER BY e.name, i.id"
+        )).fetchall()
+        for item_id, world_id, name, owner_id, location_id in rows:
+            holder_id = owner_id or location_id
+            if owner_id and location_id:
+                notes.append(f"{name} ({item_id}): owner kept, place {location_id} dropped")
+            if holder_id is None:
+                continue
+            if session.get(models.Entity, holder_id) is None:
+                notes.append(f"{name} ({item_id}): holder {holder_id} no longer exists, skipped")
+                continue
+            if holder_id == location_id and is_zone(session, holder_id):
+                notes.append(f"{name} ({item_id}): lies in a zone ({holder_id}), kept as is")
+            holdings.append((world_id, item_id, holder_id))
+    return holdings, notes
+
+
+def _rebuild_items(cursor) -> None:
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='item' AND sql IS NOT NULL"
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute("ALTER TABLE item RENAME TO item_old")
+    _create_from_model(cursor, models.Item)
+    cursor.execute("INSERT INTO item (id, condition) SELECT id, condition FROM item_old")
+    cursor.execute("DROP TABLE item_old")
+
+
+def _apply_ddl(holdings: list[tuple]) -> list[str]:
+    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
+    PRAGMAs must land before any transaction exists)."""
+    convert = "owner_id" in _columns("item")
+    existing = set(inspect(engine).get_table_names())
+    missing = [m for m in _NEW_MODELS if m.__tablename__ not in existing]
+    add_settled = "settled_at" not in _columns("quest")
+    if not (convert or missing or add_settled):
+        return []
+    applied: list[str] = []
+    now = datetime.now(UTC).isoformat(sep=" ")
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        for model in missing:
+            _create_from_model(cursor, model)
+            applied.append(f"{model.__tablename__} created")
+        if add_settled:
+            cursor.execute("ALTER TABLE quest ADD COLUMN settled_at DATETIME")
+            applied.append("quest.settled_at added")
+        if convert:
+            for world_id, item_id, holder_id in holdings:
+                cursor.execute(
+                    "INSERT INTO item_holding (id, world_id, item_id, holder_entity_id, quantity, updated_at, "
+                    "change_history) VALUES (?, ?, ?, ?, 1, ?, ?)",
+                    (str(uuid.uuid4()), world_id, item_id, holder_id, now, json.dumps([])))
+            _rebuild_items(cursor)
+            applied.append(f"item rebuilt, {len(holdings)} holding(s) written")
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    return applied
+
+
+def _post_checks(items_before: int, holdings_expected: int) -> None:
+    item_columns = _columns("item")
+    if item_columns != set(models.Item.__table__.columns.keys()):
+        raise SystemExit(f"Migration v2.18 aborted, post-check failed: item columns are {sorted(item_columns)}.")
+    with engine.connect() as conn:
+        items_after = conn.execute(text("SELECT COUNT(*) FROM item")).scalar_one()
+        holdings = conn.execute(text("SELECT COUNT(*) FROM item_holding")).scalar_one()
+    if items_after != items_before:
+        raise SystemExit(f"Migration v2.18 aborted, post-check failed: item rows {items_before} -> {items_after}.")
+    if holdings < holdings_expected:
+        raise SystemExit(f"Migration v2.18 aborted, post-check failed: {holdings} holding(s), expected {holdings_expected}.")
+    tables = set(inspect(engine).get_table_names())
+    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
+    if missing or "settled_at" not in _columns("quest"):
+        raise SystemExit(f"Migration v2.18 aborted, post-check failed: missing {missing or 'quest.settled_at'}.")
+    with engine.connect() as conn:
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    if dangling:
+        raise SystemExit(f"Migration v2.18 aborted, post-check failed: foreign_key_check {dangling}.")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: item has {sorted(item_columns)}; {items_after} item(s); {holdings} holding(s); "
+          "four tables and quest.settled_at in place.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.18 — item holdings, quest terms, quest economy, quest.settled_at")
+    _refuse()
+    with engine.connect() as conn:
+        items_before = conn.execute(text("SELECT COUNT(*) FROM item")).scalar_one()
+    holdings, notes = _plan_holdings() if "owner_id" in _columns("item") else ([], [])
+    for note in notes:
+        print(f"  Note: {note}")
+    applied = _apply_ddl(holdings)
+    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
+    _post_checks(items_before, len(holdings))
+    _converge_schema_meta()
+    print("\nMigration v2.18 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index acdecc4..0ce925e 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -3392,11 +3392,19 @@ Ne renvoie que le resume, sans preambule ni conclusion.\
         session,
         m.Item,
         "item-dague",
-        owner_id="char-player",
-        location_id=None,
-        equipped=True,
         condition="intact",
     )
+    # TICKET-0109 (A1): an item is a kind; the player holds one dagger.
+    get_or_create(
+        session,
+        m.ItemHolding,
+        "hold-dague-player",
+        world_id=WORLD_ID,
+        item_id="item-dague",
+        holder_entity_id="char-player",
+        quantity=1,
+        change_history=[],
+    )
 
     # ----- skill sheet test player character (entity + character + skill) ----
     # BRIEF-10: dedicated test character for the skill sheet, separate from
diff --git a/src/world_engine/cockpit/crud/__init__.py b/src/world_engine/cockpit/crud/__init__.py
index fa521cd..8ca24c0 100644
--- a/src/world_engine/cockpit/crud/__init__.py
+++ b/src/world_engine/cockpit/crud/__init__.py
@@ -10,10 +10,10 @@ over world state.
 Package split from a single `crud.py` (TICKET-0027, BRIEF-0027-d, R5): one
 domain module per concern (`entities`, `relations`, `knowledge`, `goals`,
 `agendas`, `events`, `factions`, `skills`, `locations`, `ledger`,
-`prompts`), all decorating the single shared `router` (`_router.py`). This
-`__init__.py` is a re-export surface only — no logic lives here — so every
-existing call site (`from . import crud as _crud`, `_crud.<name>`) keeps
-working unchanged.
+`prompts`; `items` since TICKET-0109), all decorating the single shared
+`router` (`_router.py`). This `__init__.py` is a re-export surface only
+— no logic lives here — so every existing call site (`from . import crud
+as _crud`, `_crud.<name>`) keeps working unchanged.
 
 Scope (see Claude Code Brief — Author CRUD):
 - Composite editors for `character`, `faction`, `location` (entity + its
@@ -258,6 +258,7 @@ from .prompts import (
     update_prompt_text,
 )
 
+from .items import HoldingBody, list_item_holders, set_holding
 from .zone_hooks import take_promotion_gatherings
 
 __all__ = ["router", "ENTITY_TYPE_REGISTRY"]
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index a4459b4..2d6ed7c 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -19,6 +19,7 @@ from sqlalchemy.exc import IntegrityError
 from sqlmodel import Session as DbSession, select
 
 from ...db import get_session
+from ...holdings import items_held
 from ...entity_author import generate_npc_goals
 from ...gathering import attach_on_arrival, close_open_memberships, dissolve_emptied
 from ...ledger import get_balance, list_entries
@@ -195,11 +196,11 @@ ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
     "item": {
         "label": "Item",
         "model": Item,
+        # An item is a KIND since v2.18 (TICKET-0109, A1): who holds how many
+        # is `item_holding`, edited from the sheet's « Objets » panel.
         "fields": [
-            {"name": "owner_id", "label": "Owner", "kind": "entity_ref", "ref_type": "character"},
-            {"name": "location_id", "label": "Location", "kind": "entity_ref", "ref_type": "location"},
-            {"name": "equipped", "label": "Equipped", "kind": "bool", "default": False},
             {"name": "condition", "label": "Condition", "kind": "text", "default": "intact"},
+            {"name": "value", "label": "Valeur (unités)", "kind": "number", "default": 1, "min": 0},
         ],
     },
 }
@@ -338,13 +339,13 @@ def _apply_base_fields(db: DbSession, entity: Entity, data: dict) -> None:
         setattr(entity, name, value)
 
 
-# TICKET-0101 (B1/Q1): the registry fields that place a being or an item
-# somewhere -- a zone is refused there, on create and whenever the value
-# changes (an unchanged value already sitting in a zone is reported by the
-# v2.12 migration, never re-judged on an unrelated save).
+# TICKET-0101 (B1/Q1): the registry fields that place a being somewhere --
+# a zone is refused there, on create and whenever the value changes (an
+# unchanged value already sitting in a zone is reported by the v2.12
+# migration, never re-judged on an unrelated save). An item is placed by a
+# holding since v2.18 (`writes.write_holding` refuses a zone itself).
 _PLACEMENT_FIELDS: dict[str, tuple[str, str]] = {
     "character": ("current_location_id", "Lieu du personnage"),
-    "item": ("location_id", "Lieu de l'objet"),
 }
 
 
@@ -367,21 +368,14 @@ def _build_extension_kwargs(
 ) -> dict:
     """`present_only=False` (create): one entry per registry field, absent
     keys coerced from `None`. `present_only=True` (update): only fields whose
-    name is a key of `data` appear; the item/equipped guard then reads each
-    input's EFFECTIVE value -- the built value when present, else
-    `getattr(current, name, None)` -- so an omitted field still guards
-    correctly against the stored row."""
+    name is a key of `data` appear; the placement guard then reads the
+    stored row (`current`) to tell a changed value from an unchanged one."""
     spec = ENTITY_TYPE_REGISTRY[entity_type]
     fields = spec["fields"]
     if present_only:
         ext_kwargs = {f["name"]: _coerce_field(db, f, data[f["name"]]) for f in fields if f["name"] in data}
     else:
         ext_kwargs = {f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in fields}
-    if entity_type == "item":
-        equipped = ext_kwargs["equipped"] if "equipped" in ext_kwargs else getattr(current, "equipped", None)
-        owner_id = ext_kwargs["owner_id"] if "owner_id" in ext_kwargs else getattr(current, "owner_id", None)
-        if equipped and not owner_id:
-            raise HTTPException(422, "Equipping an item requires an owner")
     _require_placement_visitable(db, entity_type, ext_kwargs, current)
     return ext_kwargs
 
@@ -902,25 +896,12 @@ def set_npc_prices(entity_id: str, body: NpcPricesBody, db: DbSession = Depends(
 
 @router.get("/entities/{entity_id}/items")
 def list_entity_items(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
-    """Items owned by `entity_id` — read-only listing for the character sheet.
-
-    Single write path: item edition lives only in the entity author flow
-    (ENTITY_TYPE_REGISTRY["item"]).
-    """
+    """What `entity_id` holds (TICKET-0109, A1) -- a character, a faction or a
+    location; read for the sheet's « Objets » panel. The one write path is
+    `PUT /api/item-holdings` (`crud/items.py`)."""
     _get_entity(db, entity_id)
-    rows = db.exec(
-        select(Item, Entity)
-        .join(Entity, Entity.id == Item.id)
-        .where(Item.owner_id == entity_id)
-        .order_by(Entity.name)
-    ).all()
     return [
-        {
-            "id": item.id,
-            "name": entity.name,
-            "equipped": item.equipped,
-            "condition": item.condition,
-            "location_id": item.location_id,
-        }
-        for item, entity in rows
-    ]
+        {"id": item.id, "name": entity.name, "quantity": holding.quantity, "condition": item.condition,
+         "value": item.value}
+        for holding, item, entity in items_held(db, entity_id)
+    ]
\ No newline at end of file
diff --git a/src/world_engine/cockpit/crud/items.py b/src/world_engine/cockpit/crud/items.py
new file mode 100644
index 0000000..d77666b
--- /dev/null
+++ b/src/world_engine/cockpit/crud/items.py
@@ -0,0 +1,47 @@
+"""Author CRUD — who holds how many of an item (TICKET-0109, BRIEF-0109-A,
+A1). The creator's one write path into `item_holding`: an item is a kind
+since v2.18, and giving it to someone, or laying it somewhere, is a holding.
+
+    GET /api/items/{item_id}/holders   who holds the item
+    PUT /api/item-holdings             set one holding's quantity
+
+Every rule lives in `writes.write_holding`; a refusal is a 422.
+"""
+
+from __future__ import annotations
+
+from fastapi import Depends, HTTPException
+from pydantic import BaseModel
+from sqlmodel import Session as DbSession
+
+from ...db import get_session
+from ...holdings import holders_of
+from ...writes import write_holding
+from ._router import router
+from ._shared import _get_entity, _world_id
+
+
+class HoldingBody(BaseModel):
+    item_id: str
+    holder_entity_id: str
+    quantity: int
+
+
+@router.get("/items/{item_id}/holders")
+def list_item_holders(item_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
+    _get_entity(db, item_id)
+    return [{"id": holder.id, "name": holder.name, "type": holder.type, "quantity": holding.quantity}
+            for holding, holder in holders_of(db, item_id)]
+
+
+@router.put("/item-holdings")
+def set_holding(body: HoldingBody, db: DbSession = Depends(get_session)) -> dict:
+    try:
+        row = write_holding(db, world_id=_world_id(db), item_id=body.item_id,
+                            holder_entity_id=body.holder_entity_id, quantity=body.quantity,
+                            changed_by="creator_crud")
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(422, str(exc)) from exc
+    db.commit()
+    return {"item_id": row.item_id, "holder_entity_id": row.holder_entity_id, "quantity": row.quantity}
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index 46c78d2..120f22d 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -18,9 +18,10 @@ reach helpers that live there because they are used elsewhere too
 Sanctioned canon-write site (relocated from the single `_apply_mutation`
 entry in `canon_write_policy.txt`, TICKET-0027 stage c — see that file's
 comment at the relocated entries): the direct (non-`writes.py`) writes
-formerly inside `_apply_mutation` — `entity` (status_change), `item`
-(item_update), `discoverable_detail` (new_knowledge's discovery flip) — now
-live in their own named functions below.
+formerly inside `_apply_mutation` — `entity` (status_change),
+`discoverable_detail` (new_knowledge's discovery flip) — now live in their
+own named functions below. (`item_update`, the equip toggle, was retired with
+`item.equipped` at v2.18, TICKET-0109.)
 """
 
 from __future__ import annotations
@@ -45,7 +46,6 @@ from ..models import (
     FactionMembership,
     FactionRole,
     GoalPrerequisite,
-    Item,
     Location,
     NpcGoal,
     ProposedMutation,
@@ -474,30 +474,6 @@ def _zone_promotion_refusal(entity: Entity, new_status: str, db: Session) -> Opt
     )
 
 
-# ── item_update (BRIEF-07, schema v1.19 — equip toggle) ────────────────────
-# Dormant since BRIEF-08/D2a.1: no live code path produces this mutation type
-# anymore; the apply branch and cockpit toggle remain functional for
-# reactivation (see "Auto-applied mutations" in ARCHITECTURE_DECISIONS.md).
-
-def _mutation_apply_item_update(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
-    """Set item.equipped."""
-    item_id = payload.get("item_id") or mut.target_id
-    if not item_id:
-        return "item_update: payload must contain item_id (or set target_id)"
-    if "equipped" not in payload:
-        return "item_update: payload must contain 'equipped'"
-
-    item = db.get(Item, str(item_id))
-    if item is None:
-        return f"item_update: item {item_id!r} not found"
-    if item.owner_id is None:
-        return f"item_update: item {item_id!r} has no owner — cannot equip (schema CHECK)"
-
-    item.equipped = bool(payload.get("equipped"))
-    db.add(item)
-    return None
-
-
 def _payload_fact(mut: ProposedMutation, payload: dict, entity_id: str, db: Session):
     """(fact_id, refusal) for a `new_knowledge` payload (TICKET-0097). A
     `fact_id` is written only by code (a coded list or a discovery), yet is
diff --git a/src/world_engine/cockpit/play.py b/src/world_engine/cockpit/play.py
index ebe8cdb..ec9efd9 100644
--- a/src/world_engine/cockpit/play.py
+++ b/src/world_engine/cockpit/play.py
@@ -351,8 +351,8 @@ def _say_possession_check(
     Code judges possession against canon `item` rows — the structural
     fix for the D1 finding that the 8b model does not reliably honor
     prohibition rules in free-text narration. `used_object` owned by the
-    player → pass; not owned or `unknown_object` → refused. The
-    equipped/stowed distinction is dormant — `item.equipped` is not read.
+    player → pass; not owned or `unknown_object` → refused. Owned means
+    held at least once (`item_holding`, TICKET-0109).
     A refusal no longer skips the NPC phase: the gesture is socially
     visible, so the turn proceeds as a normal dialogue turn with a
     one-shot [GESTE RATÉ] instruction telling the NPC what it just saw.
diff --git a/src/world_engine/cockpit/play_stream.py b/src/world_engine/cockpit/play_stream.py
index 8d18a55..d42f37f 100644
--- a/src/world_engine/cockpit/play_stream.py
+++ b/src/world_engine/cockpit/play_stream.py
@@ -26,6 +26,7 @@ from ..models import (
     Gathering,
     GatheringMember,
     Item,
+    ItemHolding,
     ProposedMutation,
     PromptTemplate,
 )
@@ -217,13 +218,14 @@ def _find_player_item(db: Session, player_id: str, item_name: str) -> Optional[t
     """Resolve a canonical item name (`_interpret_mode`'s `used_object`) to
     the player's owned `item` + `entity` rows, or `None` if not owned.
 
-    Possession is binary since BRIEF-08/D2a.1 — `item.equipped` is no longer
-    read by the check (dormant, cockpit-only).
+    Possession is binary since BRIEF-08/D2a.1: the player holds at least one
+    (`item_holding.quantity > 0`, TICKET-0109).
     """
     return db.exec(
         select(Item, Entity)
         .join(Entity, Entity.id == Item.id)
-        .where(Item.owner_id == player_id, Entity.name == item_name)
+        .join(ItemHolding, ItemHolding.item_id == Item.id)
+        .where(ItemHolding.holder_entity_id == player_id, ItemHolding.quantity > 0, Entity.name == item_name)
     ).first()
 
 
diff --git a/src/world_engine/cockpit/routes/mutations.py b/src/world_engine/cockpit/routes/mutations.py
index 0052edf..d360246 100644
--- a/src/world_engine/cockpit/routes/mutations.py
+++ b/src/world_engine/cockpit/routes/mutations.py
@@ -68,7 +68,6 @@ from ...models import (
     FactionMembership,
     Gathering,
     GatheringMember,
-    Item,
     Knowledge,
     Location,
     NpcGoal,
@@ -308,7 +307,7 @@ def _find_applied_duplicate_conversation_sourced(mut: ProposedMutation, db: Sess
     channel awakens alongside the tick producer, so a --force re-analysis
     must not double an event either).
 
-    relation_change, item_update, knowledge_change, and resource_change all
+    relation_change, knowledge_change, and resource_change all
     fall through unguarded, deliberately — see `_find_applied_duplicate`'s
     docstring for the per-type rationale.
     """
@@ -377,16 +376,12 @@ def _find_applied_duplicate(
     already-applied comparison) otherwise — see each for its per-type match
     keys and deliberate inclusion/exclusion rationale.
 
-    relation_change, item_update, knowledge_change, and resource_change all
+    relation_change, knowledge_change, and resource_change all
     fall through BOTH entry points unguarded, deliberately:
     - relation_change deltas ACCUMULATE — two independent +5 events sum to
       +10 and must both apply. These come only from per-turn immediate
       flags (one per turn), so they are never re-proposed by the final
       pass and can never be double-applied by --force.
-    - item_update is a state transition (equipped true/false); a legitimate
-      draw→stow→draw sequence within one conversation must apply each
-      time. Dormant since BRIEF-08/D2a.1 — no live code path produces it
-      anymore (see "Auto-applied mutations" in ARCHITECTURE_DECISIONS.md).
     - knowledge_change: successive legitimate upgrades in one conversation
       (e.g. rumor → partial, then later partial → knows) must both apply —
       the monotone re-check inside _apply_mutation ("level already >=
@@ -457,7 +452,6 @@ def _apply_mutation(mut: ProposedMutation, db: Session) -> Optional[str]:
         "relation_change": _mutations._mutation_apply_relation_change,
         "new_knowledge": _mutations._mutation_apply_new_knowledge,
         "status_change": _mutations._mutation_apply_status_change,
-        "item_update": _mutations._mutation_apply_item_update,
         "knowledge_change": _mutations._mutation_apply_knowledge_change,
         "goal_change": _mutations._mutation_apply_goal_change,
         "npc_move": _mutations._mutation_apply_npc_move,
diff --git a/src/world_engine/holdings.py b/src/world_engine/holdings.py
new file mode 100644
index 0000000..1919e8e
--- /dev/null
+++ b/src/world_engine/holdings.py
@@ -0,0 +1,46 @@
+"""Who holds how many of an item (TICKET-0109, BRIEF-0109-A, A1). Reads
+only: the one writer is `writes.write_holding`.
+
+A holding at 0 reads as absent; every reader here filters `quantity > 0`.
+The holder may be a character, a faction or a location (an object lying
+somewhere is held by that place).
+"""
+
+from __future__ import annotations
+
+from sqlmodel import Session, select
+
+from .models import Entity, Item, ItemHolding
+
+
+def held_quantity(db: Session, holder_entity_id: str, item_id: str) -> int:
+    """How many of `item_id` `holder_entity_id` holds (0 when none)."""
+    row = db.exec(select(ItemHolding).where(
+        ItemHolding.holder_entity_id == holder_entity_id, ItemHolding.item_id == item_id)).first()
+    return row.quantity if row is not None else 0
+
+
+def items_held(db: Session, holder_entity_id: str) -> list[tuple[ItemHolding, Item, Entity]]:
+    """What `holder_entity_id` holds, by item name."""
+    return list(db.exec(
+        select(ItemHolding, Item, Entity)
+        .join(Item, Item.id == ItemHolding.item_id)
+        .join(Entity, Entity.id == Item.id)
+        .where(ItemHolding.holder_entity_id == holder_entity_id, ItemHolding.quantity > 0)
+        .order_by(Entity.name, Entity.id)
+    ).all())
+
+
+def holders_of(db: Session, item_id: str) -> list[tuple[ItemHolding, Entity]]:
+    """Who holds `item_id`, by holder name."""
+    return list(db.exec(
+        select(ItemHolding, Entity)
+        .join(Entity, Entity.id == ItemHolding.holder_entity_id)
+        .where(ItemHolding.item_id == item_id, ItemHolding.quantity > 0)
+        .order_by(Entity.name, Entity.id)
+    ).all())
+
+
+def held_label(name: str, quantity: int) -> str:
+    """« Dague », or « Fourrure de loup ×10 » -- one line of an inventory."""
+    return name if quantity == 1 else f"{name} ×{quantity}"
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 7e93cb2..89c3bf9 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -30,7 +30,9 @@ Layout, by stratum:
                         absent from canon_write_policy.txt's [CANON_TABLES].
     quests.py        — quest offers and accepted quests (QuestOffer,
                         QuestOfferStep, QuestOfferRequirement, Quest;
-                        TICKET-0108, schema v2.17), canon.
+                        TICKET-0108, schema v2.17), their terms and a
+                        world's quest economy (QuestOfferTerm, QuestTerm,
+                        QuestEconomy; TICKET-0109, v2.18), canon.
 
 This module re-exports the ENTIRE former public surface of the flat
 `models.py` — every class, constant, and the two module functions
@@ -61,6 +63,7 @@ from .canon import (
     GoalAgendaLink,
     GoalPrerequisite,
     Item,
+    ItemHolding,
     Ledger,
     Location,
     LocationTypeCatalog,
@@ -127,7 +130,18 @@ from .observation import (
     ObservationRun,
     ObservationRunTemplate,
 )
-from .quests import QUEST_OFFER_STATUSES, Quest, QuestOffer, QuestOfferRequirement, QuestOfferStep
+from .quests import (
+    QUEST_OFFER_STATUSES,
+    QUEST_TERM_CURRENCIES,
+    QUEST_TERM_DIRECTIONS,
+    Quest,
+    QuestEconomy,
+    QuestOffer,
+    QuestOfferRequirement,
+    QuestOfferStep,
+    QuestOfferTerm,
+    QuestTerm,
+)
 
 __all__ = [
     "World",
@@ -173,6 +187,7 @@ __all__ = [
     "EventEntity",
     "Artifact",
     "Item",
+    "ItemHolding",
     "SkillDefinition",
     "SkillSystem",
     "SkillRank",
@@ -196,6 +211,11 @@ __all__ = [
     "QuestOffer",
     "QuestOfferRequirement",
     "QuestOfferStep",
+    "QUEST_TERM_CURRENCIES",
+    "QUEST_TERM_DIRECTIONS",
+    "QuestEconomy",
+    "QuestOfferTerm",
+    "QuestTerm",
     "GoalAgendaLink",
     "EntityType",
     "EntityTypeHistory",
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index 9d14ce1..9bd65ec 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -540,28 +540,51 @@ class Artifact(SQLModel, table=True):
 
 
 # -----------------------------------------------------------------------------
-# item  (mundane tracked objects — static possession, schema v1.18)
+# item  (a KIND of object -- "Fourrure de loup", schema v1.18; a kind since
+# v2.18, TICKET-0109, BRIEF-0109-A, E1/A1). Who holds how many of it is
+# `item_holding`; the kind carries its condition and its indicative value
+# (`value`, units of the quest economy, C1). `owner_id`, `location_id` and
+# `equipped` were dropped at v2.18: possession and place are holdings.
 # -----------------------------------------------------------------------------
 class Item(SQLModel, table=True):
     __tablename__ = "item"
-    __table_args__ = (
-        CheckConstraint(
-            "NOT equipped OR owner_id IS NOT NULL", name="ck_item_equipped_owner"
-        ),
-        Index("idx_item_owner", "owner_id"),
-        Index("idx_item_location", "location_id"),
-    )
+    __table_args__ = (CheckConstraint("value >= 0", name="ck_item_value"),)
 
     id: str = Field(primary_key=True, foreign_key="entity.id")
-    owner_id: Optional[str] = Field(default=None, foreign_key="entity.id")
-    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
-    equipped: bool = Field(
-        default=False, sa_column_kwargs={"server_default": text("0")}
-    )
     condition: str = Field(
         default="intact",
         sa_column_kwargs={"server_default": text("'intact'")},
     )
+    value: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
+
+
+# -----------------------------------------------------------------------------
+# item_holding  (who holds how many of an item -- schema v2.18, TICKET-0109,
+# BRIEF-0109-A, A1). The holder is any entity of the world: a character, a
+# faction, or a location (an object lying somewhere is held by that place,
+# never a zone -- `require_visitable`). One row per (item, holder); a row at
+# 0 is kept, never deleted (absence and 0 read the same). Written only by
+# `writes.write_holding`, which appends the previous quantity to
+# `change_history`.
+# -----------------------------------------------------------------------------
+class ItemHolding(SQLModel, table=True):
+    __tablename__ = "item_holding"
+    __table_args__ = (
+        CheckConstraint("quantity >= 0", name="ck_item_holding_quantity"),
+        Index("idx_item_holding_pair", "item_id", "holder_entity_id", unique=True),
+        Index("idx_item_holding_holder", "holder_entity_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    item_id: str = Field(foreign_key="item.id", nullable=False)
+    holder_entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    quantity: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+    updated_at: datetime = _created_ts()
+    change_history: list = Field(
+        default_factory=list,
+        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
+    )
 
 
 # The four structural skill domains — single source of truth (decision 3,
diff --git a/src/world_engine/models/quests.py b/src/world_engine/models/quests.py
index 1a473c8..600cee8 100644
--- a/src/world_engine/models/quests.py
+++ b/src/world_engine/models/quests.py
@@ -114,8 +114,10 @@ class QuestOfferRequirement(SQLModel, table=True):
 
 
 # -----------------------------------------------------------------------------
-# quest  (an offer a character accepted: the link to its agenda). Immutable:
-# the quest's state is `agenda.status` (M1).
+# quest  (an offer a character accepted: the link to its agenda). The
+# quest's state is `agenda.status` (M1); `settled_at` (v2.18, TICKET-0109,
+# D1) is set once, when « déclarer accomplie » applied its terms, and never
+# moves again -- the row's only column that is ever written after creation.
 # -----------------------------------------------------------------------------
 class Quest(SQLModel, table=True):
     __tablename__ = "quest"
@@ -131,3 +133,111 @@ class Quest(SQLModel, table=True):
     character_id: str = Field(foreign_key="entity.id", nullable=False)
     agenda_id: str = Field(foreign_key="agenda.id", nullable=False)
     accepted_at: datetime = _created_ts()
+    settled_at: Optional[datetime] = None
+
+
+# The two sides of a term (TICKET-0109, BRIEF-0109-A, B1, C-01): what the
+# character gives to settle the quest, and what he receives.
+QUEST_TERM_DIRECTIONS: tuple[str, ...] = ("cost", "reward")
+
+# The five currencies of a quest (the series' D table).
+QUEST_TERM_CURRENCIES: tuple[str, ...] = ("money", "item", "relation", "fact", "skill")
+
+# The shape CHECK both term tables carry, byte for byte: an amount for the
+# three counted currencies, a target for the three named ones.
+QUEST_TERM_SHAPE_CHECK = (
+    "(currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) "
+    "AND (currency <> 'item' OR item_id IS NOT NULL) "
+    "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
+    "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
+)
+QUEST_TERM_DIRECTION_CHECK = "direction IN ('cost','reward')"
+QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill')"
+
+
+# -----------------------------------------------------------------------------
+# quest_offer_term  (a cost or a reward of an offer, B1). Replaced whole with
+# the offer's steps on save. `counterparty_entity_id` NULL = the giver.
+# `skill_key` is a base domain or a skill definition id; `level` is the
+# knowledge level a fact reward gives (NULL = `knows`).
+# -----------------------------------------------------------------------------
+class QuestOfferTerm(SQLModel, table=True):
+    __tablename__ = "quest_offer_term"
+    __table_args__ = (
+        CheckConstraint(QUEST_TERM_DIRECTION_CHECK, name="ck_quest_offer_term_direction"),
+        CheckConstraint(QUEST_TERM_CURRENCY_CHECK, name="ck_quest_offer_term_currency"),
+        CheckConstraint(QUEST_TERM_SHAPE_CHECK, name="ck_quest_offer_term_shape"),
+        Index("idx_quest_offer_term_offer", "offer_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
+    term_order: int
+    direction: str
+    currency: str
+    counterparty_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
+    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+    level: Optional[str] = None
+
+
+# -----------------------------------------------------------------------------
+# quest_term  (an accepted quest's own copy of its offer's terms, B1: editing
+# the offer never changes a bargain already struck). Same columns and CHECKs
+# as `quest_offer_term`, `quest_id` in place of `offer_id`; immutable.
+# -----------------------------------------------------------------------------
+class QuestTerm(SQLModel, table=True):
+    __tablename__ = "quest_term"
+    __table_args__ = (
+        CheckConstraint(QUEST_TERM_DIRECTION_CHECK, name="ck_quest_term_direction"),
+        CheckConstraint(QUEST_TERM_CURRENCY_CHECK, name="ck_quest_term_currency"),
+        CheckConstraint(QUEST_TERM_SHAPE_CHECK, name="ck_quest_term_shape"),
+        Index("idx_quest_term_quest", "quest_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    quest_id: str = Field(foreign_key="quest.id", nullable=False)
+    term_order: int
+    direction: str
+    currency: str
+    counterparty_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
+    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+    level: Optional[str] = None
+
+
+# -----------------------------------------------------------------------------
+# quest_economy  (a world's rates of the indicative unit, C1/E1 -- one row per
+# world, the `conversation_window_config` precedent). A NULL column, or no
+# row at all, reads the code's default (`quest_value.DEFAULT_RATES`); the
+# reader never writes. Curated config, no `change_history`; written only by
+# `writes.upsert_quest_economy`. The unit is a display: never converted.
+# -----------------------------------------------------------------------------
+class QuestEconomy(SQLModel, table=True):
+    __tablename__ = "quest_economy"
+    __table_args__ = (
+        Index("idx_quest_economy_world", "world_id", unique=True),
+        CheckConstraint(
+            "(rate_money IS NULL OR rate_money >= 0) AND (rate_relation IS NULL OR rate_relation >= 0) "
+            "AND (rate_fact IS NULL OR rate_fact >= 0) AND (rate_skill IS NULL OR rate_skill >= 0) "
+            "AND (band_low_pct IS NULL OR band_low_pct >= 0) "
+            "AND (band_high_pct IS NULL OR band_high_pct >= 0)",
+            name="ck_quest_economy_rates",
+        ),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    rate_money: Optional[int] = None
+    rate_relation: Optional[int] = None
+    rate_fact: Optional[int] = None
+    rate_skill: Optional[int] = None
+    band_low_pct: Optional[int] = None
+    band_high_pct: Optional[int] = None
+    updated_at: datetime = _created_ts()
diff --git a/src/world_engine/scene_format.py b/src/world_engine/scene_format.py
index 2a68032..b0bcf09 100644
--- a/src/world_engine/scene_format.py
+++ b/src/world_engine/scene_format.py
@@ -11,7 +11,8 @@ from __future__ import annotations
 
 from sqlmodel import Session, select
 
-from .models import DiscoverableDetail, Entity, Item, Knowledge
+from .holdings import held_label, items_held
+from .models import DiscoverableDetail, Knowledge
 
 
 def active_signposts(db: Session, location_id: str, player_character_id: str) -> list[str]:
@@ -81,30 +82,26 @@ def active_signposts(db: Session, location_id: str, player_character_id: str) ->
 
 
 def format_inventory_line(db: Session, player_character_id: str) -> str:
-    """Render the player's static inventory as one compact French line
-    (BRIEF-08, D2a.1): a single comma-separated list of canonical item names —
-    the equipped/stowed split went dormant in this step (`item.equipped`
-    stays in the schema, cockpit-only; see ARCHITECTURE_DECISIONS.md).
+    """Render the player's inventory as one compact French line (BRIEF-08,
+    D2a.1; quantities since TICKET-0109, A1): what he holds
+    (`holdings.items_held`), « Fourrure de loup ×10 » for more than one.
 
-    Read fresh from `item` at every turn (no caching).
+    Read fresh at every turn (no caching).
     """
-    rows = db.exec(
-        select(Item, Entity)
-        .join(Entity, Entity.id == Item.id)
-        .where(Item.owner_id == player_character_id)
-    ).all()
-
+    rows = items_held(db, player_character_id)
     if not rows:
         return "Objets du joueur : aucun."
-
-    items = ", ".join(entity.name for item, entity in rows)
+    items = ", ".join(held_label(entity.name, holding.quantity) for holding, _item, entity in rows)
     return f"Objets du joueur : {items}."
 
 
 def format_item_list_for_interpretation(db: Session, player_character_id: str) -> str:
-    """Render the player's tracked items for the interpretation prompt
-    (BRIEF-08, D2a.1): same single list as `format_inventory_line` — the
-    equip-state annotation is dropped now that the possession check is
-    binary (owned/not owned).
+    """Render the player's items for the interpretation prompt (BRIEF-08,
+    D2a.1): the canonical NAMES only, never a quantity (TICKET-0109) -- the
+    model answers `used_object` with one of them, and the possession check
+    matches that name exactly (`play_stream._find_player_item`).
     """
-    return format_inventory_line(db, player_character_id)
+    rows = items_held(db, player_character_id)
+    if not rows:
+        return "Objets du joueur : aucun."
+    return "Objets du joueur : " + ", ".join(entity.name for _holding, _item, entity in rows) + "."
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 0a5a0bb..7ab189a 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.17"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.18"
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index 9098738..c5675b7 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -38,6 +38,8 @@ Layout, by canon domain:
     prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                           moved for module hygiene, not policy).
     pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
+    items.py            — `item_holding`: `write_holding` (TICKET-0109,
+                          BRIEF-0109-A).
     quests.py           — `quest_offer`/`quest_offer_step`/
                           `quest_offer_requirement`/`quest`:
                           `write_quest_offer`, `accept_quest`,
@@ -116,6 +118,7 @@ from .knowledge import (
     upsert_knowledge_row,
     write_knowledge,
 )
+from .items import write_holding
 from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
 from .quests import (
     OPEN_QUEST_STATUSES,
diff --git a/src/world_engine/writes/items.py b/src/world_engine/writes/items.py
new file mode 100644
index 0000000..f3e8b3e
--- /dev/null
+++ b/src/world_engine/writes/items.py
@@ -0,0 +1,74 @@
+"""`item_holding`: the one writer (TICKET-0109, BRIEF-0109-A, A1).
+
+`write_holding` sets (`quantity=`) or moves (`delta=`) how many of an item
+an entity holds. It refuses, before any write: an item that is not of the
+world, a holder that is not an active entity of the world, a location holder
+that is a zone when the quantity grows (`require_visitable`, CLAUDE.md « no
+being, item or discoverable detail is placed in a zone »; taking items out of
+a place that became a zone is how a promotion moves them), a result below 0,
+and both or neither of `quantity`/`delta`. The previous quantity goes to the
+row's `change_history`; a row at 0 is kept, never deleted.
+"""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlalchemy.orm import attributes as sa_attrs
+from sqlmodel import Session, select
+
+from ..models import Entity, Item, ItemHolding
+from ..zone_rules import ZoneRefusal, require_visitable
+
+
+def _check_parties(db: Session, world_id: str, item_id: str, holder_entity_id: str, adds: bool) -> None:
+    item = db.get(Entity, item_id) if item_id else None
+    if item is None or item.world_id != world_id or item.type != "item" or db.get(Item, item_id) is None:
+        raise ValueError(f"write_holding: {item_id!r} is not an item of this world")
+    holder = db.get(Entity, holder_entity_id) if holder_entity_id else None
+    if holder is None or holder.world_id != world_id or holder.status != "active":
+        raise ValueError(f"write_holding: holder {holder_entity_id!r} is not an active entity of this world")
+    if holder.type == "location" and adds:
+        try:
+            require_visitable(db, holder.id, what="Lieu de l'objet")
+        except ZoneRefusal as exc:
+            raise ValueError(str(exc)) from exc
+
+
+def write_holding(
+    db: Session,
+    *,
+    world_id: str,
+    item_id: str,
+    holder_entity_id: str,
+    quantity: Optional[int] = None,
+    delta: Optional[int] = None,
+    changed_by: str,
+) -> ItemHolding:
+    """Set or move one holding; returns the row (added to the session)."""
+    if (quantity is None) == (delta is None):
+        raise ValueError("write_holding: give exactly one of quantity and delta")
+    value = quantity if quantity is not None else delta
+    if not isinstance(value, int) or isinstance(value, bool):
+        raise ValueError(f"write_holding: {value!r} is not an integer")
+    row = db.exec(select(ItemHolding).where(
+        ItemHolding.item_id == item_id, ItemHolding.holder_entity_id == holder_entity_id)).first()
+    before = row.quantity if row is not None else 0
+    after = quantity if quantity is not None else before + delta
+    _check_parties(db, world_id, item_id, holder_entity_id, adds=after > before)
+    if after < 0:
+        raise ValueError(f"write_holding: {before} held, cannot remove {-delta}")
+    if row is None:
+        row = ItemHolding(world_id=world_id, item_id=item_id, holder_entity_id=holder_entity_id,
+                          quantity=0, change_history=[])
+    else:
+        history = list(row.change_history or [])
+        history.append({"quantity": before, "updated_at": row.updated_at.isoformat() if row.updated_at else None,
+                        "by": changed_by})
+        row.change_history = history
+        sa_attrs.flag_modified(row, "change_history")
+    row.quantity = after
+    row.updated_at = datetime.now(UTC)
+    db.add(row)
+    return row
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 9138c2b..2972ed2 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -75,6 +75,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
     "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
     "world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",
+    "item_holding", "quest_offer_term", "quest_term", "quest_economy",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/src/world_engine/writes/zone_promotion.py b/src/world_engine/writes/zone_promotion.py
index 7630e1e..07dc5c6 100644
--- a/src/world_engine/writes/zone_promotion.py
+++ b/src/world_engine/writes/zone_promotion.py
@@ -24,7 +24,7 @@ Resolution table (K), one line per row family:
   through `write_character_location`.
 - `npc_schedule` rows at the parent -> the first child, through a
   full-replace `write_npc_schedule` of each affected NPC's whole schedule.
-- items lying at the parent (`item.location_id`) and discoverable details
+- items the parent holds (lying there; `item_holding`, TICKET-0109) and discoverable details
   (`discoverable_detail.location_id`) -> the first child.
 - open gatherings at the parent -> listed; the caller closes them.
 - bounds, obstacles, doors, events, facts, knowledge, `controls`,
@@ -38,10 +38,12 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
-from ..models import Character, DiscoverableDetail, Entity, Gathering, Item, NpcSchedule, Relation
+from ..holdings import items_held
+from ..models import Character, DiscoverableDetail, Entity, Gathering, NpcSchedule, Relation
 from ..zone_rules import active_child_ids, is_zone
 from .characters import write_character_location
 from .config import write_npc_schedule
+from .items import write_holding
 from .relations import write_relation
 
 
@@ -84,11 +86,8 @@ def _schedules(db: Session, parent_id: str) -> list[dict]:
 
 
 def _items(db: Session, parent_id: str) -> list[dict]:
-    rows = db.exec(
-        select(Item, Entity).join(Entity, Entity.id == Item.id)
-        .where(Item.location_id == parent_id).order_by(Entity.name)
-    ).all()
-    return [{"id": i.id, "name": e.name} for i, e in rows]
+    """The items the parent holds (lying there, TICKET-0109 A1)."""
+    return [{"id": item.id, "name": e.name, "quantity": h.quantity} for h, item, e in items_held(db, parent_id)]
 
 
 def _details(db: Session, parent_id: str) -> list[dict]:
@@ -168,9 +167,10 @@ def apply_promotion(db: Session, *, parent_id: str, child_id: str, changed_by: s
     _retarget_schedules(db, world_id, preview, parent_id, child_id, changed_by)
     now = datetime.now(UTC)
     for item in preview["items"]:
-        row = db.get(Item, item["id"])
-        row.location_id = child_id
-        db.add(row)
+        write_holding(db, world_id=world_id, item_id=item["id"], holder_entity_id=parent_id,
+                      delta=-item["quantity"], changed_by=changed_by)
+        write_holding(db, world_id=world_id, item_id=item["id"], holder_entity_id=child_id,
+                      delta=item["quantity"], changed_by=changed_by)
     for detail in preview["details"]:
         row = db.get(DiscoverableDetail, detail["id"])
         row.location_id = child_id
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index c7abc80..5ffd84a 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18132,6 +18132,33 @@ quest stays invisible, as in the rest of Journée.
 the creator's tools live in Création. The pin as a separate button per
 quest: one choice per day, made where the day is planned.
 
+
+## AN ITEM IS A KIND HELD IN QUANTITY (TICKET-0109) -- ANY ENTITY HOLDS IT, A PLACE INCLUDED; EQUIPPED IS GONE (BRIEF-0109-a, schema v2.18)
+
+**A1.** `item` is a kind (« Fourrure de loup »); `item_holding` says who
+holds how many -- a character, a faction, or a location (an object lying
+somewhere is held by that place). Ten furs are one item and one holding of
+10, never ten entities. `write_holding` is the one writer: it sets or moves
+a quantity, keeps a row at 0, appends the previous quantity to the row's
+history, and refuses a zone as a place that RECEIVES (taking items out of a
+place that just became a zone is how a promotion moves them to its first
+child). The MJ's inventory line reads « Fourrure de loup ×10 »; the list the
+interpretation model answers from names items without quantities, so the
+possession check still matches a name exactly, and passes when at least one
+is held.
+
+**Equipped is gone** (Nia: « cela ne sert à rien »): the column, its CHECK,
+the registry field and `item_update`, the equip toggle no producer had
+emitted since BRIEF-08.
+
+**Schema for the next briefs.** `quest_offer_term`, `quest_term`,
+`quest_economy`, `quest.settled_at` and `item.value` are added here, read
+from BRIEF-0109-b on.
+
+**Rejected.** A2, keeping `item.location_id`: a kind held in ten places
+cannot lie in one. A quantity on `item` with one owner (E2 of the series):
+two holders of furs would be two « Fourrure » entities.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 1991453..107d2c9 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -6,6 +6,7 @@ npc_price world_law obstacle obstacle_vertex door
 location_type_catalog entity_type entity_type_history conversation_window_config
 npc_schedule agenda_step_requirement fact fact_participant fact_default
 skill_rank quest_offer quest_offer_step quest_offer_requirement quest
+item_holding quest_offer_term quest_term quest_economy
 
 [ALLOWED_SITES]
 # path::function                                              tables
@@ -45,7 +46,9 @@ src/world_engine/writes/config.py::write_npc_schedule          npc_schedule
 # TICKET-0106, BRIEF-0106-C: upsert_skill_rank is the one writer of skill_rank -- a world's rank names and default points, curated-config family (upsert_conversation_window_config precedent), never a DELETE.
 src/world_engine/writes/config.py::upsert_skill_rank           skill_rank
 # TICKET-0101, BRIEF-0101-C: apply_promotion moves the items and discoverable details lying in a location that becomes a zone to its first child (creator CRUD only, behind the S1 confirmation); its characters, schedules and links go through write_character_location, write_npc_schedule and write_relation, allow-listed above.
-src/world_engine/writes/zone_promotion.py::apply_promotion     item discoverable_detail
+src/world_engine/writes/zone_promotion.py::apply_promotion     discoverable_detail
+# TICKET-0109, BRIEF-0109-A: write_holding is the one writer of item_holding -- set or move how many of an item an entity holds; apply_promotion now moves a place's items through it.
+src/world_engine/writes/items.py::write_holding                item_holding
 # TICKET-0075, BRIEF-0075-b: write_day_plan is the 30th site — its OWN body writes agenda_step_requirement only (it calls write_agenda/write_agenda_step, whose own db.add sites are already allow-listed above; single_canon_write.py is function-scoped, not interprocedural).
 src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requirement
 # TICKET-0108, BRIEF-0108-B: write_quest_offer creates or saves one quest offer -- its steps and requirements replaced whole (the write_npc_prices full-replace shape), the offer row snapshotted; creator CRUD only.
@@ -82,9 +85,10 @@ src/world_engine/cockpit/app.py::_purge_closed_batches          *
 # app.py now only dispatches; its direct (non-writes.py) canon writes moved
 # to per-type appliers in mutations.py. Three sites replace the one former
 # _apply_mutation entry — same relocated path, still the same count of
-# sanctioned canon-write paths, not a broadening.
+# sanctioned canon-write paths, not a broadening. TICKET-0109, BRIEF-0109-A:
+# the third, _mutation_apply_item_update (the equip toggle), is retired with
+# item.equipped.
 src/world_engine/cockpit/mutations.py::_mutation_apply_status_change    entity
-src/world_engine/cockpit/mutations.py::_mutation_apply_item_update      item
 src/world_engine/cockpit/mutations.py::_mutation_apply_new_knowledge    discoverable_detail
 # Router + crud split (TICKET-0027, BRIEF-0027-d): every site below re-keyed
 # to its new file — same relocation-not-broadening rule as the stage-c
diff --git a/tooling/verify/checks/json_ui_boundary.py b/tooling/verify/checks/json_ui_boundary.py
index d083a53..5577b2d 100644
--- a/tooling/verify/checks/json_ui_boundary.py
+++ b/tooling/verify/checks/json_ui_boundary.py
@@ -56,6 +56,8 @@ JSON_COLUMN_ALLOWLIST = {
     # TICKET-0108 (BRIEF-0108-A): an offer's audit trail, the same posture
     # as the change_history columns above -- never rendered as a UI field.
     "QuestOffer.change_history",
+    # TICKET-0109 (BRIEF-0109-A): a holding's previous quantities, same posture.
+    "ItemHolding.change_history",
     # Internal engine snapshots — never rendered in any UI surface.
     "PassPlay.injected_context",
     "PassPlay.history",
diff --git a/tooling/verify/checks/quest_rewards.py b/tooling/verify/checks/quest_rewards.py
new file mode 100644
index 0000000..526d48d
--- /dev/null
+++ b/tooling/verify/checks/quest_rewards.py
@@ -0,0 +1,422 @@
+"""G1 check for TICKET-0109 -- objects held in quantity, quest terms, the
+indicative unit, and « déclarer accomplie ».
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`quests.py` precedent, TICKET-0108). Each brief adds its rules here in the
+same commit.
+
+RA1 -- schema (BRIEF-0109-A, v2.18). `item` has exactly the columns `id`,
+   `condition`, `value` (default 1, CHECK >= 0); `item_holding` has a unique
+   `(item_id, holder_entity_id)` and `quantity >= 0`; `quest_offer_term` and
+   `quest_term` carry the same three CHECK texts; `quest.settled_at` is a
+   nullable column; `quest_economy` is unique per world. The `item` registry
+   fields are `condition` and `value`; no `owner_id`, `location_id` or
+   `equipped` attribute is read under `src/` (AST); `_apply_mutation`'s
+   `appliers` has no `item_update`.
+RA2 -- migration `scripts/migrate_v2_18_quest_terms.py`, on a v2.17-shaped
+   database (`item` and `quest` in their v2.17 DDL, verbatim below, none of
+   the four new tables), holding an item owned by a character, one lying in
+   a place, one with both, one with neither, one whose owner is gone, and a
+   `session` row pointing to a missing world:
+   a. at v2.16 it refuses (non-zero exit) and changes nothing;
+   b. at v2.17 it writes one holding of 1 for the owned item (its owner),
+      the lying one (its place), the one with both (its owner), none for the
+      others; `item` keeps its five rows with the model's columns and their
+      `condition`; the four tables and `quest.settled_at` exist; `PRAGMA
+      foreign_key_check` is empty on the six tables it writes; the orphan
+      `session` is noted and not stopped on; `schema_meta` is the code's
+      version;
+   c. a second run exits zero and changes no row.
+RA3 -- holdings (fixture). `write_holding` sets and moves a quantity, keeps
+   a row at 0, appends the previous quantity to `change_history`; refuses,
+   with no write, a result below 0, an entity that is not an item, a holder
+   of another world, both or neither of `quantity`/`delta`, and a zone as a
+   place that receives -- while taking out of a zone is accepted. The
+   inventory line reads « Dague, Fourrure de loup ×10 »; the interpretation
+   list names « Dague, Fourrure de loup » with no quantity; the possession
+   check finds an item held and not one held at 0; `GET /api/entities/{id}/
+   items` and `GET /api/items/{id}/holders` give quantities; `PUT
+   /api/item-holdings` sets one and answers 422 on a refusal.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+MIGRATION = ROOT / "scripts" / "migrate_v2_18_quest_terms.py"
+
+FAILURES: list[str] = []
+
+NEW_TABLES = ("item_holding", "quest_offer_term", "quest_term", "quest_economy")
+
+# `item` and `quest` as v2.17 created them (dumped from `main` at 1f80b9f).
+_V217_DDL = (
+    """CREATE TABLE item (
+	id VARCHAR NOT NULL, owner_id VARCHAR, location_id VARCHAR,
+	equipped BOOLEAN DEFAULT 0 NOT NULL, condition VARCHAR DEFAULT 'intact' NOT NULL,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_item_equipped_owner CHECK (NOT equipped OR owner_id IS NOT NULL),
+	FOREIGN KEY(id) REFERENCES entity (id),
+	FOREIGN KEY(owner_id) REFERENCES entity (id),
+	FOREIGN KEY(location_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_item_location ON item (location_id)",
+    "CREATE INDEX idx_item_owner ON item (owner_id)",
+    """CREATE TABLE quest (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL,
+	character_id VARCHAR NOT NULL, agenda_id VARCHAR NOT NULL,
+	accepted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	PRIMARY KEY (id),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
+	FOREIGN KEY(character_id) REFERENCES entity (id),
+	FOREIGN KEY(agenda_id) REFERENCES agenda (id))""",
+    "CREATE INDEX idx_quest_offer ON quest (offer_id)",
+    "CREATE UNIQUE INDEX idx_quest_agenda ON quest (agenda_id)",
+    "CREATE INDEX idx_quest_character ON quest (character_id)",
+)
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+# --- RA1 -----------------------------------------------------------------------
+
+def _checks(table) -> dict[str, str]:
+    from sqlalchemy import CheckConstraint
+
+    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+
+
+def _attribute_reads(names: set[str]) -> list[str]:
+    """`x.owner_id` / `x.location_id` / `x.equipped` on an Item-shaped read:
+    every attribute access named so whose object mentions `item`/`Item`."""
+    found = []
+    for path in SRC.rglob("*.py"):
+        tree = ast.parse(path.read_text(encoding="utf-8"))
+        for node in ast.walk(tree):
+            if isinstance(node, ast.Attribute) and node.attr in names:
+                owner = ast.unparse(node.value)
+                if "item" in owner.lower():
+                    found.append(f"{path.relative_to(ROOT)}:{node.lineno} {owner}.{node.attr}")
+    return found
+
+
+def check_ra1() -> None:
+    from world_engine.cockpit.crud.entities import ENTITY_TYPE_REGISTRY
+    from world_engine.models import Item, ItemHolding, Quest, QuestEconomy, QuestOfferTerm, QuestTerm
+
+    if set(Item.__table__.columns.keys()) != {"id", "condition", "value"}:
+        fail(f"RA1: item columns are {sorted(Item.__table__.columns.keys())}")
+    value = Item.__table__.columns.get("value")
+    if value is None or str(value.server_default.arg) != "1" or "value >= 0" not in _checks(Item.__table__).values():
+        fail("RA1: item.value is not default 1 with CHECK value >= 0")
+    unique = {tuple(c.name for c in i.columns) for i in ItemHolding.__table__.indexes if i.unique}
+    if ("item_id", "holder_entity_id") not in unique or "quantity >= 0" not in _checks(ItemHolding.__table__).values():
+        fail(f"RA1: item_holding uniques {unique}, checks {_checks(ItemHolding.__table__)}")
+    offer, quest = _checks(QuestOfferTerm.__table__), _checks(QuestTerm.__table__)
+    for kind in ("direction", "currency", "shape"):
+        if not offer.get(f"ck_quest_offer_term_{kind}") or offer.get(f"ck_quest_offer_term_{kind}") != quest.get(f"ck_quest_term_{kind}"):
+            fail(f"RA1: the {kind} CHECK differs between quest_offer_term and quest_term")
+    settled = Quest.__table__.columns.get("settled_at")
+    if settled is None or not settled.nullable:
+        fail("RA1: quest.settled_at is missing or not nullable")
+    if not any(i.unique and [c.name for c in i.columns] == ["world_id"] for i in QuestEconomy.__table__.indexes):
+        fail("RA1: quest_economy is not unique per world")
+    names = [f["name"] for f in ENTITY_TYPE_REGISTRY["item"]["fields"]]
+    if names != ["condition", "value"]:
+        fail(f"RA1: the item registry fields are {names}")
+    reads = _attribute_reads({"owner_id", "location_id", "equipped"})
+    if reads:
+        fail(f"RA1: an item's dropped column is still read: {reads}")
+    tree = ast.parse((SRC / "cockpit" / "routes" / "mutations.py").read_text(encoding="utf-8"))
+    keys = [k.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(
+        isinstance(t, ast.Name) and t.id == "appliers" for t in n.targets) and isinstance(n.value, ast.Dict)
+        for k in n.value.keys if isinstance(k, ast.Constant)]
+    if not keys or "item_update" in keys:
+        fail(f"RA1: the appliers are {keys}")
+
+
+# --- RA2 -----------------------------------------------------------------------
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def _shape(conn, table: str) -> list[tuple]:
+    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))
+
+
+def _seed_v217(db_path: str) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import Entity, Location, SchemaMeta, World
+
+    create_db_and_tables()
+    ids: dict = {}
+    with Session(engine) as session:
+        world = World(name="Quest rewards RA2", is_active=True)
+        session.add(world)
+        session.flush()
+        ids["world"] = world.id
+        for key, kind in (("pc", "character"), ("place", "location"), ("owned", "item"), ("lying", "item"),
+                          ("both", "item"), ("loose", "item"), ("orphan", "item")):
+            row = Entity(world_id=world.id, type=kind, name=key)
+            session.add(row)
+            session.flush()
+            ids[key] = row.id
+        session.add(Location(id=ids["place"]))
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.17"))
+        session.commit()
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        ids["model_shapes"] = {t: _shape(conn, t) for t in ("item", "quest") + NEW_TABLES}
+        conn.execute("PRAGMA foreign_keys=OFF")
+        for table in NEW_TABLES + ("item", "quest"):
+            conn.execute(f"DROP TABLE {table}")
+        for statement in _V217_DDL:
+            conn.execute(statement)
+        rows = (("owned", ids["pc"], None, "intact"), ("lying", None, ids["place"], "usé"),
+                ("both", ids["pc"], ids["place"], "intact"), ("loose", None, None, "intact"),
+                ("orphan", "gone-entity", None, "brisé"))
+        for key, owner, place, condition in rows:
+            conn.execute("INSERT INTO item (id, owner_id, location_id, equipped, condition) VALUES (?, ?, ?, 0, ?)",
+                         (ids[key], owner, place, condition))
+        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
+        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
+    return ids
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        holdings = (sorted(conn.execute("SELECT item_id, holder_entity_id, quantity FROM item_holding").fetchall())
+                    if "item_holding" in tables else None)
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "items": sorted(conn.execute("SELECT id, condition FROM item").fetchall()),
+            "holdings": holdings,
+            "shapes": {t: _shape(conn, t) for t in ("item", "quest") + NEW_TABLES if t in tables},
+        }
+
+
+def check_ra2(db_path: str) -> None:
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    ids = _seed_v217(db_path)
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.16' WHERE id = 1")
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail(f"RA2a: at v2.16 the migration exit {result.returncode} or the database changed")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.17' WHERE id = 1")
+    result = _run_migration(db_path)
+    if result.returncode != 0:
+        fail(f"RA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
+        return
+    after = _state(db_path)
+    expected = sorted([(ids["owned"], ids["pc"], 1), (ids["lying"], ids["place"], 1), (ids["both"], ids["pc"], 1)])
+    if after["holdings"] != expected:
+        fail(f"RA2b: the holdings are {after['holdings']}, expected {expected}")
+    if after["items"] != before["items"] or len(after["items"]) != 5:
+        fail(f"RA2b: the item rows are {after['items']}")
+    if after["shapes"] != ids["model_shapes"]:
+        fail(f"RA2b: the tables are {after['shapes']}, expected the models' {ids['model_shapes']}")
+    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"RA2b: schema_meta is {after['version']}")
+    if "Note: session rowid" not in result.stdout or "no longer exists" not in result.stdout:
+        fail("RA2b: the orphan session row or the gone owner was not noted")
+    with sqlite3.connect(db_path) as conn:
+        dangling = [r for t in ("item", "quest") + NEW_TABLES
+                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
+    if dangling:
+        fail(f"RA2b: foreign_key_check {dangling}")
+    again = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode != 0 or _state(db_path) != again:
+        fail(f"RA2c: a second run exit {result.returncode} or changed a row")
+
+
+# --- RA3 -----------------------------------------------------------------------
+
+def _ra3_world(session) -> dict:
+    from world_engine.models import Character, Entity, Item, Location, World
+
+    worlds = []
+    for name in ("Quest rewards RA3", "Elsewhere"):
+        world = World(name=name, is_active=False)
+        session.add(world)
+        session.flush()
+        worlds.append(world.id)
+    ids = {"world": worlds[0], "other_world": worlds[1]}
+    pc = Entity(world_id=worlds[0], type="character", name="Millys")
+    stranger = Entity(world_id=worlds[1], type="character", name="Étranger")
+    session.add_all([pc, stranger])
+    session.flush()
+    session.add(Character(id=pc.id, world_id=worlds[0], character_type="player"))
+    ids.update(pc=pc.id, stranger=stranger.id)
+    for key, parent in (("zone", None), ("room", "zone")):
+        loc = Entity(world_id=worlds[0], type="location", name=key)
+        session.add(loc)
+        session.flush()
+        session.add(Location(id=loc.id, parent_location_id=ids.get(parent)))
+        ids[key] = loc.id
+    for key, name in (("dague", "Dague"), ("fur", "Fourrure de loup"), ("rope", "Corde")):
+        row = Entity(world_id=worlds[0], type="item", name=name)
+        session.add(row)
+        session.flush()
+        session.add(Item(id=row.id))
+        ids[key] = row.id
+    session.commit()
+    return ids
+
+
+def _refused(session, label: str, **kwargs) -> None:
+    from sqlmodel import func, select
+
+    from world_engine.models import ItemHolding
+    from world_engine.writes import write_holding
+
+    before = session.exec(select(func.count()).select_from(ItemHolding)).one()
+    try:
+        write_holding(session, changed_by="check", **kwargs)
+    except ValueError:
+        session.rollback()
+        if session.exec(select(func.count()).select_from(ItemHolding)).one() != before:
+            fail(f"RA3: a refused holding ({label}) wrote a row")
+        return
+    session.rollback()
+    fail(f"RA3: write_holding accepts {label}")
+
+
+def _ra3_writer(session, ids) -> None:
+    from world_engine.holdings import held_quantity
+    from world_engine.writes import write_holding
+
+    w = ids["world"]
+    write_holding(session, world_id=w, item_id=ids["dague"], holder_entity_id=ids["pc"], quantity=1, changed_by="check")
+    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=4, changed_by="check")
+    row = write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], delta=6, changed_by="check")
+    session.commit()
+    if row.quantity != 10 or [h["quantity"] for h in row.change_history] != [4]:
+        fail(f"RA3: fur is {row.quantity}, history {row.change_history}")
+    write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["pc"], quantity=2, changed_by="check")
+    rope = write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["pc"], delta=-2, changed_by="check")
+    session.commit()
+    if rope.quantity != 0 or held_quantity(session, ids["pc"], ids["rope"]) != 0:
+        fail("RA3: a holding moved to 0 is not kept at 0")
+    _refused(session, "a result below 0", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], delta=-11)
+    _refused(session, "a character as the item", world_id=w, item_id=ids["pc"], holder_entity_id=ids["pc"], quantity=1)
+    _refused(session, "a holder of another world", world_id=w, item_id=ids["fur"], holder_entity_id=ids["stranger"], quantity=1)
+    _refused(session, "both quantity and delta", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=1, delta=1)
+    _refused(session, "neither quantity nor delta", world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"])
+    _refused(session, "a zone that receives", world_id=w, item_id=ids["fur"], holder_entity_id=ids["zone"], quantity=1)
+    session.execute(__import__("sqlalchemy").text(
+        "INSERT INTO item_holding (id, world_id, item_id, holder_entity_id, quantity, updated_at, change_history) "
+        "VALUES ('legacy-zone', :w, :i, :z, 3, CURRENT_TIMESTAMP, '[]')"), {"w": w, "i": ids["rope"], "z": ids["zone"]})
+    session.commit()
+    try:
+        write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["zone"], delta=-3, changed_by="check")
+        session.commit()
+    except ValueError as exc:
+        session.rollback()
+        fail(f"RA3: taking items out of a zone is refused: {exc}")
+
+
+def _ra3_readers(session, ids) -> None:
+    from world_engine.cockpit.play_stream import _find_player_item
+    from world_engine.scene_format import format_inventory_line, format_item_list_for_interpretation
+
+    line = format_inventory_line(session, ids["pc"])
+    if line != "Objets du joueur : Dague, Fourrure de loup ×10.":
+        fail(f"RA3: the inventory line is {line!r}")
+    names = format_item_list_for_interpretation(session, ids["pc"])
+    if names != "Objets du joueur : Dague, Fourrure de loup.":
+        fail(f"RA3: the interpretation list is {names!r}")
+    if _find_player_item(session, ids["pc"], "Fourrure de loup") is None:
+        fail("RA3: the possession check misses an item held")
+    if _find_player_item(session, ids["pc"], "Corde") is not None:
+        fail("RA3: the possession check finds an item held at 0")
+
+
+def _ra3_routes(session, ids) -> None:
+    from fastapi import HTTPException
+
+    from world_engine.cockpit.crud.entities import list_entity_items
+    from world_engine.cockpit.crud.items import HoldingBody, list_item_holders, set_holding
+    from world_engine.models import World
+
+    for world in session.exec(__import__("sqlmodel").select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    session.flush()
+    session.get(World, ids["world"]).is_active = True
+    session.commit()
+    items = {(r["name"], r["quantity"]) for r in list_entity_items(ids["pc"], db=session)}
+    if items != {("Dague", 1), ("Fourrure de loup", 10)}:
+        fail(f"RA3: GET items gives {items}")
+    set_holding(HoldingBody(item_id=ids["fur"], holder_entity_id=ids["room"], quantity=3), db=session)
+    holders = {(r["name"], r["quantity"]) for r in list_item_holders(ids["fur"], db=session)}
+    if holders != {("Millys", 10), ("room", 3)}:
+        fail(f"RA3: GET holders gives {holders}")
+    try:
+        set_holding(HoldingBody(item_id=ids["fur"], holder_entity_id=ids["zone"], quantity=1), db=session)
+        fail("RA3: PUT item-holdings accepts a zone")
+    except HTTPException as exc:
+        if exc.status_code != 422:
+            fail(f"RA3: PUT item-holdings on a zone answers {exc.status_code}")
+
+
+def check_ra3(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _ra3_world(session)
+        _ra3_writer(session, ids)
+        _ra3_readers(session, ids)
+        _ra3_routes(session, ids)
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_ra1()
+    check_ra2(db_path)
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_ra3(engine)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, "
+          "migrates owners and places to holdings from v2.17 only, drops equipped, and one writer "
+          "keeps every holding, its history, and zones empty")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 89c35a9..37035fa 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -197,6 +197,13 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                                  "target_entity_id": "{w}-char"}),
     ("quest", {"id": "qu-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
                "character_id": "{w}-char", "agenda_id": "ag-{w}"}),
+    ("item_holding", {"id": "ih-{w}", "world_id": "{w}", "item_id": "{w}-item",
+                      "holder_entity_id": "{w}-char", "quantity": 2}),
+    ("quest_offer_term", {"id": "qot-{w}", "world_id": "{w}", "offer_id": "qo-{w}", "term_order": 1,
+                          "direction": "reward", "currency": "item", "item_id": "{w}-item", "amount": 1}),
+    ("quest_term", {"id": "qt-{w}", "world_id": "{w}", "quest_id": "qu-{w}", "term_order": 1,
+                    "direction": "cost", "currency": "money", "amount": 3}),
+    ("quest_economy", {"id": "qe-{w}", "world_id": "{w}", "rate_fact": 4}),
 )
 
 
diff --git a/tooling/verify/checks/zone_placement.py b/tooling/verify/checks/zone_placement.py
index ac4e286..4d57c8f 100644
--- a/tooling/verify/checks/zone_placement.py
+++ b/tooling/verify/checks/zone_placement.py
@@ -15,7 +15,8 @@ Three assertions:
        npc_move          `mutations._mutation_apply_npc_move` -> message
        PC creation       `routes/creator._validate_pc_creation` -> 409
        fiche, character  `crud/entities._build_extension_kwargs` -> 409
-       fiche, item       `crud/entities._build_extension_kwargs` -> 409
+       holding, item     `writes/items.write_holding` -> `ValueError` (an item
+                         is placed by a holding since TICKET-0109)
        schedule          `writes/config.write_npc_schedule` -> `ValueError`
        detail            `crud/locations.create_discoverable_detail` -> 409
      A fiche save whose `current_location_id` is UNCHANGED and already Z is
@@ -78,7 +79,7 @@ def _fresh_engine():
 
 
 def _seed(session) -> dict[str, str]:
-    from world_engine.models import Character, Entity, Location, User, World
+    from world_engine.models import Character, Entity, Item, Location, User, World
 
     world = World(name="Zone Placement", is_active=True)
     session.add(world)
@@ -104,6 +105,12 @@ def _seed(session) -> dict[str, str]:
         ))
         session.commit()
         ids[label] = entity.id
+    item = Entity(world_id=world.id, type="item", name="Lanterne")
+    session.add(item)
+    session.flush()
+    session.add(Item(id=item.id))
+    session.commit()
+    ids["I"] = item.id
     return ids
 
 
@@ -144,6 +151,7 @@ def check_a_paths(session, ids) -> None:
     from world_engine.cockpit.routes.creator import PlayerCharacterCreateBody, _validate_pc_creation
     from world_engine.models import Character
     from world_engine.writes.config import write_npc_schedule
+    from world_engine.writes.items import write_holding
 
     n = 0
     result = _perform_travel(ids["P"], ids["Z"], session)
@@ -177,10 +185,18 @@ def check_a_paths(session, ids) -> None:
         session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=npc_row))
     n += _accepts("fiche, character", lambda: _build_extension_kwargs(
         session, "character", {"current_location_id": ids["V"]}, present_only=True, current=npc_row))
-    n += _expect_http("fiche, item", lambda: _build_extension_kwargs(
-        session, "item", {"name": "x", "location_id": ids["Z"]}))
-    n += _accepts("fiche, item", lambda: _build_extension_kwargs(
-        session, "item", {"name": "x", "location_id": ids["C"]}))
+    try:
+        write_holding(session, world_id=ids["world"], item_id=ids["I"], holder_entity_id=ids["Z"],
+                      quantity=1, changed_by="check")
+    except ValueError:
+        n += 1
+    else:
+        fail("(a) holding, item: a zone was accepted")
+    session.rollback()
+    n += _accepts("holding, item", lambda: write_holding(
+        session, world_id=ids["world"], item_id=ids["I"], holder_entity_id=ids["C"], quantity=1,
+        changed_by="check"))
+    session.rollback()
     already = SimpleNamespace(current_location_id=ids["Z"])
     n += _accepts("fiche save with an unchanged zone", lambda: _build_extension_kwargs(
         session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=already))
diff --git a/tooling/verify/checks/zone_promotion.py b/tooling/verify/checks/zone_promotion.py
index 7e99e36..b4e7ef9 100644
--- a/tooling/verify/checks/zone_promotion.py
+++ b/tooling/verify/checks/zone_promotion.py
@@ -100,7 +100,8 @@ def _character(db, world_id: str, name: str, ctype: str, at: str, user_id=None)
 
 def _seed(db) -> dict[str, str]:
     from world_engine.models import (
-        DiscoverableDetail, Entity, Gathering, GatheringMember, Item, NpcSchedule, Session, User, World,
+        DiscoverableDetail, Entity, Gathering, GatheringMember, Item, ItemHolding, NpcSchedule, Session, User,
+        World,
     )
     from world_engine.writes.relations import write_relation
 
@@ -127,7 +128,8 @@ def _seed(db) -> dict[str, str]:
     item = Entity(world_id=w, type="item", name="Lanterne")
     db.add(item)
     db.flush()
-    db.add(Item(id=item.id, location_id=ids["F"]))
+    db.add(Item(id=item.id))
+    db.add(ItemHolding(world_id=w, item_id=item.id, holder_entity_id=ids["F"], quantity=2, change_history=[]))
     detail = DiscoverableDetail(world_id=w, location_id=ids["F"], subject="trace", content="Une trace.")
     db.add(detail)
     sess = Session(world_id=w, number=1)
@@ -198,7 +200,8 @@ def check_a_refused(client, engine, ids) -> None:
 def check_b_confirmed(client, engine, ids) -> None:
     from sqlmodel import Session, select
 
-    from world_engine.models import DiscoverableDetail, Gathering, Item, NpcSchedule
+    from world_engine.holdings import held_quantity
+    from world_engine.models import DiscoverableDetail, Gathering, NpcSchedule
 
     with Session(engine) as db:
         rel = _rel(db, ids["F"], ids["V"])
@@ -218,7 +221,8 @@ def check_b_confirmed(client, engine, ids) -> None:
             n += _expect(_where(db, ids[being]) == child, f"(b) {being} not moved to the first child")
         rows = {r.phase: r.location_id for r in db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == ids["N"])).all()}
         n += _expect(rows == {"matin": child, "soir": ids["V"]}, f"(b) schedule after promotion: {rows}")
-        n += _expect(db.get(Item, ids["item"]).location_id == child, "(b) item not moved")
+        n += _expect(held_quantity(db, child, ids["item"]) == 2 and held_quantity(db, ids["F"], ids["item"]) == 0,
+                     "(b) the place's two items not moved to the first child")
         n += _expect(db.get(DiscoverableDetail, ids["detail"]).location_id == child, "(b) detail not moved")
         n += _expect(db.get(Gathering, ids["gathering"]).status == "dissolved", "(b) gathering left open")
     COUNTS["b"] = n
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 484ab87..a2d171e 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,14 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.18** — TICKET-0109, BRIEF-0109-A: objects held in quantity, quest
+  terms, the quest economy. `item` becomes a kind: `owner_id`,
+  `location_id`, `equipped` and `ck_item_equipped_owner` dropped, `value`
+  added (default 1). `item_holding` (who holds how many; a character, a
+  faction or a place), `quest_offer_term`, `quest_term`, `quest_economy` are
+  added, and `quest.settled_at`. `migrate_v2_18_quest_terms.py` gives each
+  item one holding for its owner, else its place, rebuilds `item` from the
+  model, creates the four tables, and refuses a database older than v2.17.
 - **v2.17** — TICKET-0108, BRIEF-0108-A: quest offers and quests.
   `quest_offer`, `quest_offer_step`, `quest_offer_requirement` and `quest`
   are added. `agenda_step_requirement`'s two CHECKs gain four forms
diff --git a/world-engine-schema.md b/world-engine-schema.md
index d540925..ac4350e 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.17
+Current schema version: v2.18
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -1439,8 +1439,10 @@ CREATE TABLE proposed_mutation (
   mutation_type   TEXT NOT NULL,
                   -- relation_change | new_knowledge | knowledge_change |
                   -- event_creation | status_change | entity_creation |
-                  -- item_update | resource_change | goal_change |
-                  -- npc_move | other
+                  -- resource_change | goal_change | npc_move | other
+                  -- (item_update, the equip toggle, retired at v2.18 with
+                  -- item.equipped -- TICKET-0109; no row of it was ever
+                  -- produced since BRIEF-08)
                   -- (goal_change targets npc_goal — TICKET-0013/BRIEF-0013-c)
                   -- (npc_move targets character.current_location_id,
                   -- tick-only producer, no schema bump — TICKET-0015/
@@ -1622,26 +1624,48 @@ CREATE TABLE artifact (
 
 ### `item`
 
-Mundane tracked objects — static possession (schema v1.18). Extension of
-entity for type `item`.
+A KIND of object (schema v1.18; a kind since v2.18, TICKET-0109,
+BRIEF-0109-A, A1) -- « Fourrure de loup », « Dague ». Extension of entity
+for type `item`. Who holds how many of it is `item_holding`; the kind
+carries its condition and its indicative `value` (units of the quest
+economy, never a price). `owner_id`, `location_id`, `equipped` and their
+CHECK were dropped at v2.18. `artifact` stays reserved for the unique,
+magical or historic object.
 
 ```sql
 CREATE TABLE item (
-  id           TEXT PRIMARY KEY REFERENCES entity(id),
-  owner_id     TEXT REFERENCES entity(id),   -- NULL = lying in a location
-  location_id  TEXT REFERENCES entity(id),   -- NULL = carried (follows owner)
-  equipped     BOOLEAN DEFAULT FALSE,
-  condition    TEXT DEFAULT 'intact',
-  CHECK (NOT equipped OR owner_id IS NOT NULL)
+  id         TEXT PRIMARY KEY REFERENCES entity(id),
+  condition  TEXT NOT NULL DEFAULT 'intact',
+  value      INTEGER NOT NULL DEFAULT 1 CHECK (value >= 0)
 );
 ```
 
-> Three states, never deletion: equipped (`owner_id` set + `equipped=TRUE`),
-> carried but stowed (`owner_id` set + `equipped=FALSE`), lying in a
-> location (`owner_id` NULL + `location_id` set). Mundane tracked objects
-> live here; `artifact` remains reserved for magical/historically
-> significant objects. An item can be promoted to artifact later if the
-> fiction demands it.
+-----
+
+### `item_holding`
+
+Who holds how many of an item (v2.18, A1). The holder is any entity of the
+world: a character, a faction, or a location (an object lying somewhere is
+held by that place; a zone never receives one -- `require_visitable`). One
+row per (item, holder); a row at 0 is kept, never deleted, and reads as
+absent. Written only by `writes.write_holding`, which appends the previous
+quantity to `change_history`. Read by the MJ's inventory line, the Play
+possession check (held at least once), the sheets' « Objets » panel and the
+zone promotion (a place's holdings move to its first child).
+
+```sql
+CREATE TABLE item_holding (
+  id                TEXT PRIMARY KEY,
+  world_id          TEXT NOT NULL REFERENCES world(id),
+  item_id           TEXT NOT NULL REFERENCES item(id),
+  holder_entity_id  TEXT NOT NULL REFERENCES entity(id),
+  quantity          INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
+  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
+  change_history    JSON NOT NULL DEFAULT '[]'
+);
+CREATE UNIQUE INDEX idx_item_holding_pair ON item_holding(item_id, holder_entity_id);
+CREATE INDEX idx_item_holding_holder ON item_holding(holder_entity_id);
+```
 
 -----
 
@@ -2335,9 +2359,11 @@ CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement(offer_
 
 An offer a character accepted (v2.17, B1): the link to the agenda the
 acceptance created, born `paused` (A1) -- one open plan among the player's,
-which a day selects or the player pins. Immutable: a quest's state is its
-agenda's status (M1: `active`/`paused` open, `completed`, `failed`,
-`abandoned`). Written only by `writes.accept_quest`.
+which a day selects or the player pins. A quest's state is its agenda's
+status (M1: `active`/`paused` open, `completed`, `failed`, `abandoned`).
+Written by `writes.accept_quest`; `settled_at` (v2.18, TICKET-0109, D1) is
+set once, by « déclarer accomplie », when the quest's terms were applied --
+the only column written after creation.
 
 ```sql
 CREATE TABLE quest (
@@ -2346,7 +2372,8 @@ CREATE TABLE quest (
   offer_id      TEXT NOT NULL REFERENCES quest_offer(id),
   character_id  TEXT NOT NULL REFERENCES entity(id),
   agenda_id     TEXT NOT NULL REFERENCES agenda(id),
-  accepted_at   DATETIME DEFAULT CURRENT_TIMESTAMP
+  accepted_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
+  settled_at    DATETIME                  -- v2.18: set once, at « déclarer accomplie »
 );
 CREATE UNIQUE INDEX idx_quest_agenda ON quest(agenda_id);
 CREATE INDEX idx_quest_character ON quest(character_id);
@@ -2355,6 +2382,80 @@ CREATE INDEX idx_quest_offer ON quest(offer_id);
 
 -----
 
+### `quest_offer_term`
+
+A cost or a reward of an offer (v2.18, TICKET-0109, B1). `direction`:
+`cost` (what the character gives to settle the quest) or `reward` (what he
+receives). `currency`: `money`, `item`, `relation`, `fact`, `skill`.
+`counterparty_entity_id` NULL = the offer's giver. `amount`: coins, items,
+or relation points; `item_id`, `fact_id`, `skill_key` (a base domain or a
+skill definition id) name the target; `level` is the knowledge level a fact
+reward gives (NULL = `knows`). Replaced whole with the offer's steps on
+save. Written only by `writes.write_quest_offer`.
+
+```sql
+CREATE TABLE quest_offer_term (
+  id                      TEXT PRIMARY KEY,
+  world_id                TEXT NOT NULL REFERENCES world(id),
+  offer_id                TEXT NOT NULL REFERENCES quest_offer(id),
+  term_order              INTEGER NOT NULL,
+  direction               TEXT NOT NULL CHECK (direction IN ('cost','reward')),
+  currency                TEXT NOT NULL CHECK (currency IN ('money','item','relation','fact','skill')),
+  counterparty_entity_id  TEXT REFERENCES entity(id),
+  item_id                 TEXT REFERENCES item(id),
+  fact_id                 TEXT REFERENCES fact(id),
+  skill_key               TEXT,
+  amount                  INTEGER,
+  level                   TEXT,
+  CHECK (
+    (currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1))
+    AND (currency <> 'item' OR item_id IS NOT NULL)
+    AND (currency <> 'fact' OR fact_id IS NOT NULL)
+    AND (currency <> 'skill' OR skill_key IS NOT NULL)
+  )
+);
+CREATE INDEX idx_quest_offer_term_offer ON quest_offer_term(offer_id);
+```
+
+-----
+
+### `quest_term`
+
+An accepted quest's own copy of its offer's terms (v2.18, B1): editing the
+offer never changes a bargain already struck. Same columns and CHECKs as
+`quest_offer_term`, `quest_id` (REFERENCES `quest`) in place of `offer_id`;
+index `idx_quest_term_quest`. Written only by `writes.accept_quest`;
+immutable.
+
+-----
+
+### `quest_economy`
+
+A world's rates of the indicative unit (v2.18, C1/E1): one row per world,
+the `conversation_window_config` precedent. Each column NULL, or no row,
+reads the code's default (`quest_value.DEFAULT_RATES`: money 1, relation
+point 1, fact 5, skill 20; band 100-150 %); an item's rate is its own
+`value`. The unit is a display -- never converted, never spent. Written
+only by `writes.upsert_quest_economy`.
+
+```sql
+CREATE TABLE quest_economy (
+  id             TEXT PRIMARY KEY,
+  world_id       TEXT NOT NULL REFERENCES world(id),
+  rate_money     INTEGER,
+  rate_relation  INTEGER,
+  rate_fact      INTEGER,
+  rate_skill     INTEGER,
+  band_low_pct   INTEGER,
+  band_high_pct  INTEGER,
+  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
+  CHECK (every column IS NULL OR >= 0)
+);
+CREATE UNIQUE INDEX idx_quest_economy_world ON quest_economy(world_id);
+```
+
+-----
+
 ### `goal_agenda_link`
 
 Many-to-many tie between an `npc_goal` and the `agenda` intrigue(s) it
````

## Scope OUT

- Writing or reading terms, the unit, the value preview, the economy routes (B).
- Settlement, `settled_at` written (C). The quest surfaces (D).
- Artifacts (unique objects); a « porté » or « équipé » state of any kind.
- Showing quantities in the interpretation list, or matching a used object other than by exact name.
- A `currency` column on `ledger`; any change to the ledger.
- Deleting a holding row that falls to 0 (it stays, with its history; readers filter `quantity > 0`).
- Running the migration on Nia's database (live gate).
- Every later brief of this lot.

## Invariants to defend

**The schema is authoritative:** model, schema doc, changelog, constant and migration move together, in this commit. **History is sacred:** every item with a living owner or place becomes a holding (b-2, post-checked); what is dropped is listed in the migration's notes; a holding never loses its history. **No being or item lies in a zone** (CLAUDE.md): `write_holding` refuses a zone that receives; the migration reports, never invents, an item already in a zone. **Two canon-write paths:** `write_holding` is the one writer of `item_holding`, allow-listed by function; the creator's `PUT /api/item-holdings` goes through it. **The model proposes, Python judges:** the possession check stays an exact name match on a held item.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- RA2 of `quest_rewards.py` fails (the migration on a v2.17-shaped database).
- An item with a living owner or place would end without a holding, other than the rows b-2 lists.
- A producer of `item_update` exists on `main` (contradicts R-03).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `tooling/verify/checks/world_cascade.py` because another fixture row was appended last: add this brief's four rows at the end of `_FIXTURE` by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).
- `npm ci` engine warnings (`EBADENGINE`); the pre-existing Svelte warning on `<option value="">`.
- Item rows on prod whose owner and place are both set, or whose place is a zone (the migration's notes).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quest_rewards.py` -> `PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, migrates owners and places to holdings from v2.17 only, drops equipped, and one writer keeps every holding, its history, and zones empty`.
- `quests.py`, `zone_placement.py`, `zone_promotion.py`, `zone_migration.py`, `single_canon_write.py`, `world_cascade.py`, `json_ui_boundary.py`, `day_mutations.py`, `schema_version_agreement.py`, `schema_partition.py`, `env_guard.py`, `module_budget.py`, `function_length.py`, `creation_island.py`, `page_contract.py`, `frontend_build_fresh.py`, `pipeline_state.py`, `decisions_index.py`, `claude_md_contract.py` -> `PASS`.
- Mutation tests, each red then reverted: in the migration, `            holder_id = owner_id or location_id` -> `            holder_id = location_id or owner_id` -> `RA2b`; in `writes/items.py`, `    _check_parties(db, world_id, item_id, holder_entity_id, adds=after > before)` -> the same line with `adds=True` -> `RA3`; in `scene_format.format_item_list_for_interpretation`, `entity.name for _holding, _item, entity in rows` -> `held_label(entity.name, holding.quantity) for holding, _item, entity in rows` -> `RA3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 142/142.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema changelog v2.18, schema doc header and sections, decision entry `AN ITEM IS A KIND HELD IN QUANTITY (TICKET-0109) -- ANY ENTITY HOLDS IT, A PLACE INCLUDED; EQUIPPED IS GONE (BRIEF-0109-a, schema v2.18)` — all in the diff. CLAUDE.md is not touched (the zone rule already covers items; no new invariant).
