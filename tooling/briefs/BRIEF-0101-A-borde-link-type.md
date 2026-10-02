<!-- slug: borde-link-type -->
# BRIEF 0101-A — "`borde` and the derived link type"

Lot: LOT-0101-zones.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0101-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/relation_orientation.py:23` → `RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to", "controls")`; `:38` → `def connects_to_fact_content(name_a: str, name_b: str) -> str:`
- `src/world_engine/models/canon_knowledge.py:38` → `            unique=True, sqlite_where=text("type NOT IN ('connects_to','controls')"),` (read only: D changes it)
- `src/world_engine/writes/relations.py:144` → `def _birth_typed_fact(db: Session, rel: Relation, changed_by: str) -> Optional[Fact]:`; `:151` → `    elif rel.type == "connects_to":`; `:172` → `def _refresh_lien_content(`; `:307` → `    is_new = sa_inspect(rel).transient`; `:315` → `        _refresh_lien_content(db, rel, old_type, provenance)`
- `src/world_engine/spatial_author.py:110` → `def connect_locations(`; `:134` → `def _catalog_row(db: Session, *, world_id: str, type_name: str) -> Optional[LocationTypeCatalog]:`
- `src/world_engine/cockpit/crud/relations.py:174` → `    if body.type == "connects_to":`; `:204` → `def update_relation(`
- `src/world_engine/cockpit/crud/_shared.py:140` → `RELATION_TYPES = (`
- `src/world_engine/lore_selectors.py:140` and `src/world_engine/day_concordance.py:301` → `            Relation.type != "connects_to",`
- `src/world_engine/cockpit/routes/room_batch.py:166` and `:190` → `        connect_locations(db, world_id=world_id, …, changed_by="creator")`
- `src/world_engine/cockpit/routes/regions.py:274` → `                    type="connects_to", value=50, direction="mutual",`
- `tooling/verify/checks/known_reachability.py:334` → `    "world_engine/relation_orientation.py",` (last entry of `DOCUMENTED_MODULES`)
- `tooling/verify/checks/relation_graph.py:111` → the regex `RELATION_GRAPH_EXCLUDED_TYPES(?:\s*:[^=]*)?\s*=\s*\(([^)]*)\)`
- `CLAUDE.md:218` → `- **\`connects_to\` is location map topology, never a social signal.** Its`
- `cockpit/play.py:860,866`, `day_plan.py:239`, `tick_context.py:554` → `Relation.type == "connects_to",` (read only: they must not change)
- `ls src/world_engine/zone_rules.py tooling/verify/checks/zone_map_links.py` → no such file
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`

## Facts carried

### R-01 — `Relation` model [M]
Opened: `src/world_engine/models/canon_knowledge.py:23-61` (the model).
Finding: no status column; `type` a free `str`; `change_history` a non-null
JSON list. `idx_relation_oriented_social (entity_a_id, entity_b_id)`, unique,
`sqlite_where=text("type NOT IN ('connects_to','controls')")` (`:36-39`),
commented as a re-typing of `RELATION_GRAPH_EXCLUDED_TYPES`.
Consequence: a relation is retyped in place or hard-deleted, never closed
(N1). `borde` in the structural split is DDL on this index (D).

### R-02 — the social/structural split [M]
Opened: `src/world_engine/relation_orientation.py:20-43` (the module that
declares it; `context.py:114` re-exports).
Finding: `RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to",
"controls")` (`:23`); `is_social(t)` = `t not in` the tuple (`:26-30`);
`connects_to_fact_content(a, b)` → `"{a} communique avec {b}."` (`:38-43`).
Consequence: absent from the tuple, `borde` would be social — forced
`a_to_b` (`writes/relations.py:120-123`), a lien fact « éprouve « borde » »
at `unaware`, an encounter between two places (`:161-168`), and the social
unique index. It joins the tuple (A) and the index (D).

### R-03 — `write_relation` [M]
Opened: `src/world_engine/writes/relations.py` (whole, 387 lines).
Finding: `mode="set", relation_id=…` snapshots the row (`_append_history_
snapshot`) then overwrites `type` in place (`_build_relation_set`,
`:213-229`). A new row births its typed fact (`_birth_typed_fact`,
`:144-158`: social → lien `unaware`, `connects_to` → `knows`, else none). A
`set` that changes a type refreshes the fact only social → social
(`_refresh_lien_content`, `:172-186`). The new-row/existing-row switch is
`is_new = sa_inspect(rel).transient` (`:307`). `write_relation` was 78 lines
on `main` (`function_length.py` cap 80).
Consequence: N1 is an in-place retype plus a structural refresh through
`writes/facts.py::update_typed_fact_content` (`:142-154`, keeps the
previous content in `fact.change_history`). The L1 judgment for a type
change runs before any mutation, in a helper, to stay under 80 lines.

### R-04 — the delete path [M]
Opened: `cockpit/crud/relations.py:232-263`; `tooling/verify/checks/
single_canon_write.py:49-80` (the closed list).
Finding: `delete_relation` is a creator-correction hard delete, listed.
Consequence: close-and-recreate (N2) is rejected; nothing in the lot deletes.

### R-05 — who writes a geographic link [M]
Opened: grep of `write_relation(` and `connect_locations(` over `src/` (E3).
Finding: `spatial_author.connect_locations` (`:110-131`, edge + doors) is
called by `crud/relations.create_relation` (`:174-181`) and the room batch
(`room_batch.py:166`, `:190`); the region commit writes `connects_to`
directly (`regions.py:271-279`); `lore_write_apply` writes `controls` only
(`:312`); the two `mutations.py` sites write `relation_change` deltas
(`:171`, `:347`). `PUT /relations/{id}` passes any type to
`write_relation` (`crud/relations.py:204-227`).
Consequence: L1 lives in `write_relation` (C-02), the single writer, so
every path above is judged; the creator paths derive the type before
writing (C-04).

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

### R-07 — the region commit [M]
Opened: `cockpit/routes/regions.py:183-215`, `:217-290`.
Finding: creates a tree of NEW locations, then the confirmed `connection`
links as `connects_to`, whatever the tree; `_touched_location_ids` keeps
only `type == "connects_to"` links for door materialization (`:294-305`).
Consequence: the region writes the derived type (A); a new parent moves
nothing, so no confirmation is ever needed there.

### R-12 — travel and reachability readers [M]
Opened: each site (E4).
Finding: every traversal reads `type == "connects_to"` and nothing else.
Consequence: L1 holds by construction; none of these lines changes.

### R-13 — structural-exclusion readers [M]
Opened: grep (E5).
Finding: the tuple serves `crud/relations.py:341,365,401`,
`link_context.py:85`, `link_author.py:228,545` and every `is_social`; two
scans spell `!= "connects_to"`: `lore_selectors.py:140` (the dossier, keeps
`controls` on purpose) and `day_concordance.py:301` (keyed on a character).
`regions.py:302` filters links for door materialization, not a scan.
Consequence: the tuple covers the first group; the two scans exclude
`MAP_TOPOLOGY_TYPES` (A).

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

### R-20 — budgets [M]
Opened: `module_budget.py:57-58`; `function_length.py` + baseline;
`claude_md_contract.py:69-71`.
Finding: 40 functions / 1000 lines per module, 80 lines per function,
CLAUDE.md 38 000 characters and 100 per line, no `TICKET-` in Invariants.
Consequence: new modules for zones and promotion; `_perform_travel`'s
refusals extracted (`_travel_refusal`); `write_npc_schedule`'s docstring
tightened; the CLAUDE.md bullet names no ticket.

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

### C-03 — the vocabulary
Produced by: A   Consumed by: A, D, F
`RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to",
"borde", "controls")` (a literal); `MAP_TOPOLOGY_TYPES: tuple[str, str] =
("connects_to", "borde")`; `borde_fact_content(a, b) -> f"{a} borde {b}."`.

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

## Context

Nia confirmed the definition: a location with an active child is a zone, one without is visitable; travel only joins two visitable places (J3); a link touching a zone is a new type, `borde`, derived from its ends, never chosen (L1). This first brief writes that rule and the type, and makes every existing writer of a geographic link derive it. Nothing else moves yet: placement guards are B, promotion C.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/zone_rules.py` (C-01);
   - `relation_orientation.py`: `borde` in the tuple, `MAP_TOPOLOGY_TYPES`, `borde_fact_content` (C-03);
   - `writes/relations.py`: `_require_map_shape`, `_checked_old_type`, `_map_fact_content`, `_refresh_map_content`, the `borde` fact at birth, the module and function docstrings (C-02);
   - `spatial_author.py`: `find_map_relation`, `link_locations` (C-04);
   - `crud/relations.py`: `create_relation` routes both geographic types through `link_locations` (422), `update_relation` maps `ValueError` to 409, the unused `_find_relation_pair` import goes;
   - `room_batch.py`: both edge writers call `link_locations`; `regions.py`: the `connection` link takes `geographic_link_type`;
   - `lore_selectors.py`, `day_concordance.py`: `Relation.type.not_in(MAP_TOPOLOGY_TYPES)`;
   - `crud/_shared.py`: the V1 comment above `RELATION_TYPES` (`connects_to` stays the one geographic entry, `borde` is not offered);
   - `known_reachability.py` and `tooling/tickets/connects-to-readers-TICKET-0082.md`: `zone_rules.py` listed and classified as a vocabulary site;
   - `CLAUDE.md`: the `connects_to` bullet covers `borde`; a new zone bullet;
   - `tooling/verify/checks/zone_map_links.py`;
   - the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Named mutations, each run with `python tooling/verify/checks/zone_map_links.py`, then restored with `git checkout -- <file>` (commit first, so the restore cannot touch unrelated work):
   - in `writes/relations.py`, change `    if new_type != expected:` to `    if False and new_type != expected:` → `FAIL: (a) connects_to V1-Z: write accepted`;
   - in `relation_orientation.py`, drop `"borde", ` from the tuple → the check fails (it crashes in (a) on the orientation guard — a non-zero exit is the failure);
   - in `writes/relations.py`, replace `        _refresh_map_content(db, rel, old_type, provenance)` with `        pass` → `FAIL: (d) fact content … communique avec …`;
   - in `spatial_author.py`, replace `    existing = find_map_relation(db, entity_a_id, entity_b_id)` with `    existing = None` → `FAIL: (b) a second link_locations(Z, V2) returned a different row`.
4. Commit message: `feat(zones): borde and the derived geographic link type (BRIEF-0101-a)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index ca0d0b2..8eaf778 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -215,11 +215,15 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   TRAP — never add `"hidden"` to `FACETS["coutume"].aspects`, and every play
   reader filters `notorious_at_location` at query construction; discoverable
   content lives ONLY in `discoverable_detail`.
-- **`connects_to` is location map topology, never a social signal.** Its
-  `intensity=50` is meaningless. Every gameplay reader of `relation` keyed
-  on a character/player id is structurally blind to `connects_to` rows; the
-  sole intentional gameplay reader is `_location_neighbours`. Any new
-  world-wide relation scan MUST exclude `type='connects_to'`.
+- **`connects_to` and `borde` are location map topology, never a social
+  signal.** Their `intensity=50` is meaningless. Every gameplay reader of
+  `relation` keyed on a character/player id is structurally blind to them;
+  the sole intentional gameplay reader is `_location_neighbours`. Any new
+  world-wide relation scan MUST exclude both (`MAP_TOPOLOGY_TYPES`).
+- **A location with an active child is a zone, derived, never stored
+  (`zone_rules.py`).** Only `connects_to` is traversable and it never
+  touches a zone; a link touching a zone is `borde`. A geographic link's
+  type is derived from its endpoints (`link_locations`), never chosen.
 - **The `ledger` is append-only.** INSERT-only on both canon-write paths;
   corrections are new compensating lines. No UPDATE/DELETE endpoint or code
   path may touch a `ledger` row.
diff --git a/src/world_engine/cockpit/crud/_shared.py b/src/world_engine/cockpit/crud/_shared.py
index 0271576..1070be5 100644
--- a/src/world_engine/cockpit/crud/_shared.py
+++ b/src/world_engine/cockpit/crud/_shared.py
@@ -137,6 +137,9 @@ def _coerce_field(db: DbSession, field: dict, raw: Any) -> Any:
     return str(raw)
 
 
+# The fiche relation form's datalist. `connects_to` is its ONE geographic
+# entry (TICKET-0101, V1): `borde` is never offered, the server derives the
+# geographic type from the two locations (`spatial_author.link_locations`).
 RELATION_TYPES = (
     "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
     "instrumentalizes", "interest", "indifference", "rejection",
diff --git a/src/world_engine/cockpit/crud/relations.py b/src/world_engine/cockpit/crud/relations.py
index 317968b..b45d991 100644
--- a/src/world_engine/cockpit/crud/relations.py
+++ b/src/world_engine/cockpit/crud/relations.py
@@ -53,8 +53,8 @@ from ...models import (
 )
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
-from ...relation_orientation import is_social
-from ...spatial_author import connect_locations
+from ...relation_orientation import MAP_TOPOLOGY_TYPES, is_social
+from ...spatial_author import link_locations
 from ...tick_normalize import _EVENT_TYPES
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -62,7 +62,6 @@ from ...writes import (
     NPC_GOAL_PREREQUISITE_TYPES,
     PromptValidationError,
     _find_perceived_relation,
-    _find_relation_pair,
     detach_goal_agenda_link,
     set_target_knows,
     write_agenda,
@@ -160,8 +159,10 @@ def create_relation(entity_id: str, body: RelationWriteBody, db: DbSession = Dep
     """Create a relation from the sheet entity. Orientation rule
     (TICKET-0090): a social type makes the sheet entity the perceiver
     (`entity_a`) -- `reciprocal` adds the reverse row, `direction` and
-    `visible_to_b` are ignored; `connects_to` delegates to
-    `connect_locations`; `controls` makes the sheet entity the controller."""
+    `visible_to_b` are ignored; a geographic type (`connects_to` or `borde`,
+    TICKET-0101 V1) delegates to `link_locations`, which derives the type
+    from the two locations; `controls` makes the sheet entity the
+    controller."""
     entity = _get_entity(db, entity_id)
     if not body.other_entity_id:
         raise HTTPException(422, "other_entity_id is required")
@@ -171,13 +172,16 @@ def create_relation(entity_id: str, body: RelationWriteBody, db: DbSession = Dep
     if not body.type:
         raise HTTPException(422, "type is required")
 
-    if body.type == "connects_to":
-        connect_locations(
-            db, world_id=entity.world_id, entity_a_id=entity_id,
-            entity_b_id=body.other_entity_id, changed_by="creator",
-        )
+    if body.type in MAP_TOPOLOGY_TYPES:
+        try:
+            rel = link_locations(
+                db, world_id=entity.world_id, entity_a_id=entity_id,
+                entity_b_id=body.other_entity_id, changed_by="creator",
+            )
+        except ValueError as exc:
+            raise HTTPException(422, str(exc))
         db.commit()
-        rel = _find_relation_pair(db, entity_id, body.other_entity_id)
+        db.refresh(rel)
         return _relation_dict(rel, entity_id, db)
 
     if is_social(body.type):
@@ -206,23 +210,27 @@ def update_relation(relation_id: str, body: RelationWriteBody, db: DbSession = D
     (TICKET-0090): the endpoints never move; a social row stays `a_to_b`, a
     structural row keeps its own direction; `body.direction` and
     `body.visible_to_b` are never read (`visible_to_b` passes through from
-    the row)."""
+    the row). A type change into, out of, or within the geographic pair that
+    breaks L1/V1 (TICKET-0101) is a 409."""
     rel = db.get(Relation, relation_id)
     if rel is None:
         raise HTTPException(404, f"Relation {relation_id!r} not found")
     if not body.type:
         raise HTTPException(422, "type is required")
 
-    write_relation(
-        db,
-        mode="set",
-        relation_id=relation_id,
-        type=body.type,
-        value=body.intensity if body.intensity is not None else rel.intensity,
-        direction="a_to_b" if is_social(body.type) else rel.direction,
-        visible_to_b=rel.visible_to_b,
-        notes=body.notes,
-    )
+    try:
+        write_relation(
+            db,
+            mode="set",
+            relation_id=relation_id,
+            type=body.type,
+            value=body.intensity if body.intensity is not None else rel.intensity,
+            direction="a_to_b" if is_social(body.type) else rel.direction,
+            visible_to_b=rel.visible_to_b,
+            notes=body.notes,
+        )
+    except ValueError as exc:
+        raise HTTPException(409, str(exc))
     db.commit()
     db.refresh(rel)
     return _relation_dict(rel, rel.entity_a_id, db)
diff --git a/src/world_engine/cockpit/routes/regions.py b/src/world_engine/cockpit/routes/regions.py
index 93afe0f..95ada58 100644
--- a/src/world_engine/cockpit/routes/regions.py
+++ b/src/world_engine/cockpit/routes/regions.py
@@ -24,6 +24,7 @@ from ...db import get_session
 from ...models import Entity, Location, Relation
 from ...spatial_author import location_classification, materialize_doors
 from ...writes import write_faction_role, write_relation
+from ...zone_rules import geographic_link_type
 from .. import crud as _crud
 
 router = APIRouter()
@@ -268,13 +269,17 @@ def _commit_region_links(
                 continue
 
             if kind == "connection":
+                # TICKET-0101 (R1): the type follows the endpoints -- `borde`
+                # when either is a zone of this commit's tree, else
+                # `connects_to`; doors materialize for `connects_to` only.
+                link_type = geographic_link_type(db, source_id, target_id)
                 write_relation(
                     db, mode="set", world_id=world_id,
                     entity_a_id=source_id, entity_b_id=target_id,
-                    type="connects_to", value=50, direction="mutual",
+                    type=link_type, value=50, direction="mutual",
                 )
                 written_links.append({
-                    "location_local_id": local_id, "kind": kind, "type": "connects_to",
+                    "location_local_id": local_id, "kind": kind, "type": link_type,
                     "entity_a_id": source_id, "entity_b_id": target_id,
                 })
             else:  # kind == "faction" — controller is entity_a, asset is entity_b
diff --git a/src/world_engine/cockpit/routes/room_batch.py b/src/world_engine/cockpit/routes/room_batch.py
index 47d635e..b548fd2 100644
--- a/src/world_engine/cockpit/routes/room_batch.py
+++ b/src/world_engine/cockpit/routes/room_batch.py
@@ -5,7 +5,7 @@ phases -- same no-canon-write neighbourhood as /api/regions/manifest and
 /api/regions/generate (regions.py). The commit route (BRIEF-0042-e) is the
 SOLE canon-write path for a batch, posture identical to commit_region: the
 client is untrusted, the parent cascade is re-derived server-side, doors
-materialize through spatial_author.connect_locations, and the whole batch
+materialize through spatial_author.link_locations, and the whole batch
 commits in one transaction with full rollback on any exception.
 """
 
@@ -30,7 +30,7 @@ from ...room_batch_author import _name_key  # commit-time name resolution must
 from ...room_batch_author import generate_room_batch_draft as _generate_room_batch_draft
 from ...room_batch_author import generate_room_batch_manifest as _generate_room_batch_manifest
 from ...room_batch_author import propose_batch_coherence as _propose_batch_coherence
-from ...spatial_author import connect_locations, location_classification
+from ...spatial_author import link_locations, location_classification
 from .. import crud as _crud
 
 router = APIRouter()
@@ -158,12 +158,14 @@ def _commit_batch_rooms(
 
 def _commit_batch_tree_edges(parent_entity_of: dict[str, str], world_id: str, db: Session) -> int:
     """K1 spanning-tree edges -- every committed room's parent-child
-    adjacency IS a passage (N1: doors materialize on the perimeter via
-    connect_locations, never model-proposed). Unconditional -- not gated by
-    confirmed_edges, which governs the SUPPLEMENTARY edges only."""
+    adjacency is written, never model-proposed. Unconditional -- not gated by
+    confirmed_edges, which governs the SUPPLEMENTARY edges only. The type is
+    derived by link_locations (TICKET-0101, R1): a parent that holds a room
+    is a zone, so a tree edge is a `borde`; doors materialize only on a
+    `connects_to`."""
     written = 0
     for entity_id, parent_entity_id in parent_entity_of.items():
-        connect_locations(db, world_id=world_id, entity_a_id=parent_entity_id, entity_b_id=entity_id, changed_by="creator")
+        link_locations(db, world_id=world_id, entity_a_id=parent_entity_id, entity_b_id=entity_id, changed_by="creator")
         written += 1
     return written
 
@@ -187,7 +189,7 @@ def _commit_batch_edges(
         if a_id is None or b_id is None:
             unresolved.append({"a_id": edge["a_id"], "b_id": edge["b_id"], "reason": "Extrémité rejetée ou non commitée"})
             continue
-        connect_locations(db, world_id=world_id, entity_a_id=a_id, entity_b_id=b_id, changed_by="creator")
+        link_locations(db, world_id=world_id, entity_a_id=a_id, entity_b_id=b_id, changed_by="creator")
         written += 1
     return written, unresolved
 
@@ -216,9 +218,9 @@ def commit_room_batch(
     room batch, posture identical to commit_region (regions.py): the client
     is untrusted, the parent cascade is re-derived server-side from the
     `accepted` map (never from a client-sent effective parent), every
-    `connects_to` edge (K1 spanning tree AND confirmed supplementary edges)
-    is written through spatial_author.connect_locations so doors materialize
-    on the perimeter, and the whole batch commits in ONE transaction with
+    geographic edge (K1 spanning tree AND confirmed supplementary edges)
+    is written through spatial_author.link_locations, which derives its type
+    (TICKET-0101) and materializes doors on every `connects_to`, and the whole batch commits in ONE transaction with
     full rollback on any exception -- no half-batch is ever observable.
     """
     world_id = _crud._world_id(db)
diff --git a/src/world_engine/day_concordance.py b/src/world_engine/day_concordance.py
index 3aa8ece..1ec2a23 100644
--- a/src/world_engine/day_concordance.py
+++ b/src/world_engine/day_concordance.py
@@ -74,6 +74,7 @@ from .models import (
     Relation,
 )
 from .name_index import NameScope, surfaces as name_surfaces
+from .relation_orientation import MAP_TOPOLOGY_TYPES
 from .schedule_reads import who_is_at
 
 _log = logging.getLogger(__name__)
@@ -293,12 +294,12 @@ def _cast_presence(candidates: list[str], ctx: _ConcordContext, character: Chara
 
 def _cast_relation(candidates: list[str], ctx: _ConcordContext, character: Character, db: Session) -> list[str]:
     # A NEW relation scan keyed on `character.id` (a player id): structurally
-    # blind to `connects_to` — that type is location map topology, never a
-    # social signal, and its `intensity=50` is meaningless here.
+    # blind to `connects_to` and `borde` — location map topology, never a
+    # social signal, and their `intensity=50` is meaningless here.
     rows = db.exec(
         select(Relation).where(
             Relation.world_id == ctx.world_id,
-            Relation.type != "connects_to",
+            Relation.type.not_in(MAP_TOPOLOGY_TYPES),
             (
                 (Relation.entity_a_id == character.id) & Relation.entity_b_id.in_(tuple(candidates))
             ) | (
diff --git a/src/world_engine/lore_selectors.py b/src/world_engine/lore_selectors.py
index c674ee8..ab91ef1 100644
--- a/src/world_engine/lore_selectors.py
+++ b/src/world_engine/lore_selectors.py
@@ -20,6 +20,7 @@ from .facet_reads import creator_only_fact_ids, facts_of, joined
 from .facets import DESCRIPTIVE_FACETS, FACETS
 from .models import Character, Entity, Fact, FactParticipant, Faction, Knowledge, NpcGoal, Relation
 from .prose_render import fact_texts, knowledge_texts
+from .relation_orientation import MAP_TOPOLOGY_TYPES
 from .writes.knowledge import knowledge_level_rank
 
 
@@ -129,15 +130,16 @@ def _facet_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
 
 
 def _relation_rows(entity_id: str, world_id: str, db: Session) -> list[dict]:
-    # `connects_to` is location map topology, never a social signal, and its
-    # intensity=50 is meaningless (CLAUDE.md invariant) -- any new
-    # world-wide relation scan must exclude it, on pain of presenting map
-    # adjacency as if it were a narrative relation in the dossier.
+    # `connects_to` and `borde` are location map topology, never a social
+    # signal, and their intensity=50 is meaningless (CLAUDE.md invariant) --
+    # any new world-wide relation scan must exclude them, on pain of
+    # presenting map adjacency as if it were a narrative relation in the
+    # dossier. `controls` stays: a dossier shows who controls a place.
     rows = db.exec(
         select(Relation).where(
             Relation.world_id == world_id,
             (Relation.entity_a_id == entity_id) | (Relation.entity_b_id == entity_id),
-            Relation.type != "connects_to",
+            Relation.type.not_in(MAP_TOPOLOGY_TYPES),
         )
     ).all()
     other_ids = {r.entity_b_id if r.entity_a_id == entity_id else r.entity_a_id for r in rows}
diff --git a/src/world_engine/relation_orientation.py b/src/world_engine/relation_orientation.py
index 8b075ef..debbf0a 100644
--- a/src/world_engine/relation_orientation.py
+++ b/src/world_engine/relation_orientation.py
@@ -2,7 +2,8 @@
 
 The single source of the social/structural split of `relation` types
 (`RELATION_GRAPH_EXCLUDED_TYPES`, `is_social`) and of the two typed-fact
-content templates (`lien_fact_content`, `connects_to_fact_content`).
+content templates (`lien_fact_content`, `connects_to_fact_content`,
+`borde_fact_content`) and of the map-topology pair (`MAP_TOPOLOGY_TYPES`).
 `context.py` re-imports `RELATION_GRAPH_EXCLUDED_TYPES` from here, so every
 existing importer of `context.RELATION_GRAPH_EXCLUDED_TYPES` keeps working
 and the constant is never re-typed.
@@ -18,9 +19,15 @@ from __future__ import annotations
 from dataclasses import dataclass
 
 # Structural exclusion shared by every world-wide relation scan (CLAUDE.md:
-# "connects_to is location map topology, never a social signal" / "controls"
-# is a faction-control edge, also never a social signal).
-RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str] = ("connects_to", "controls")
+# "connects_to and borde are location map topology, never a social signal" /
+# "controls" is a faction-control edge, also never a social signal).
+RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to", "borde", "controls")
+
+# The two geographic link types (TICKET-0101, L1). `connects_to` joins two
+# visitable locations and is the only traversable link; `borde` is the link
+# whenever a zone is an endpoint. The type is derived from the endpoints
+# (`zone_rules.geographic_link_type`), never chosen by the creator.
+MAP_TOPOLOGY_TYPES: tuple[str, str] = ("connects_to", "borde")
 
 
 def is_social(relation_type: str) -> bool:
@@ -43,6 +50,12 @@ def connects_to_fact_content(name_a: str, name_b: str) -> str:
     return f"{name_a} communique avec {name_b}."
 
 
+def borde_fact_content(name_a: str, name_b: str) -> str:
+    """Content of a `borde` edge's typed fact (TICKET-0101) — the sibling of
+    `connects_to_fact_content`, same arguments, same `knows` default."""
+    return f"{name_a} borde {name_b}."
+
+
 @dataclass(frozen=True)
 class OrientedSpec:
     perceiver_id: str
diff --git a/src/world_engine/spatial_author.py b/src/world_engine/spatial_author.py
index 27e2dd1..ed5702e 100644
--- a/src/world_engine/spatial_author.py
+++ b/src/world_engine/spatial_author.py
@@ -21,7 +21,9 @@ from sqlmodel import Session, select
 
 from . import placement
 from .models import Door, Entity, Location, LocationTypeCatalog, Relation
+from .relation_orientation import MAP_TOPOLOGY_TYPES
 from .writes import write_location_doors, write_relation
+from .zone_rules import geographic_link_type
 
 
 def _live_neighbour_ids(location_id: str, db: Session) -> list[str]:
@@ -131,6 +133,61 @@ def connect_locations(
     )
 
 
+def find_map_relation(db: Session, entity_a_id: str, entity_b_id: str) -> Optional[Relation]:
+    """The geographic (`connects_to` or `borde`) row between two locations,
+    either column order, oldest first; None when they are not linked."""
+    return db.exec(
+        select(Relation)
+        .where(
+            Relation.type.in_(MAP_TOPOLOGY_TYPES),
+            ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
+            | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id)),
+        )
+        .order_by(Relation.created_at, Relation.id)
+    ).first()
+
+
+def link_locations(
+    db: Session,
+    *,
+    world_id: str,
+    entity_a_id: str,
+    entity_b_id: str,
+    changed_by: str,
+) -> Relation:
+    """The creator entry for a geographic link (TICKET-0101, L1/V1): the type
+    is derived from the two endpoints (`zone_rules.geographic_link_type`),
+    never chosen. A pair already linked keeps its one row: retyped in place
+    when its type no longer matches (N1), never duplicated. A new or retyped
+    `connects_to` materializes doors for both endpoints (J1); a `borde`
+    never does. Does NOT commit — caller owns the commit."""
+    link_type = geographic_link_type(db, entity_a_id, entity_b_id)
+    existing = find_map_relation(db, entity_a_id, entity_b_id)
+    if existing is not None and existing.type == link_type:
+        return existing
+    if existing is not None:
+        write_relation(
+            db, mode="set", relation_id=existing.id, type=link_type, value=existing.intensity,
+            direction=existing.direction, visible_to_b=existing.visible_to_b,
+            notes=existing.notes, changed_by=changed_by,
+        )
+        rel = existing
+    elif link_type == "connects_to":
+        connect_locations(
+            db, world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
+            changed_by=changed_by,
+        )
+        return find_map_relation(db, entity_a_id, entity_b_id)
+    else:
+        rel = write_relation(
+            db, mode="set", world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
+            type="borde", value=50, direction="mutual", changed_by=changed_by,
+        )
+    if rel.type == "connects_to":
+        materialize_doors(db, world_id=world_id, location_ids=[entity_a_id, entity_b_id], changed_by=changed_by)
+    return rel
+
+
 def _catalog_row(db: Session, *, world_id: str, type_name: str) -> Optional[LocationTypeCatalog]:
     """The single catalog read path (J1, TICKET-0040). Both the
     interior/exterior classification and the size template resolve a
diff --git a/src/world_engine/writes/relations.py b/src/world_engine/writes/relations.py
index ea2834d..0f97056 100644
--- a/src/world_engine/writes/relations.py
+++ b/src/world_engine/writes/relations.py
@@ -22,7 +22,8 @@ Two finders, one per class of relation:
 Typed fact at birth: every newly created social relation gets one `lien`
 fact (`lien_fact_content`, `default_level='unaware'`); every new
 `connects_to` edge gets one fact (`connects_to_fact_content`,
-`default_level='knows'`); `controls` gets none. The row is flushed before
+`default_level='knows'`); every new `borde` edge gets one fact
+(`borde_fact_content`, `knows`, TICKET-0101); `controls` gets none. The row is flushed before
 `create_fact` runs (`_birth_typed_fact`). A `mode="set"` update that
 changes a social row's type rewrites its lien fact's content through
 `writes/facts.py::update_typed_fact_content`, which keeps the previous
@@ -30,6 +31,16 @@ content in the fact's `change_history`. Both endpoints are written as
 identity tokens (TICKET-0091, BRIEF-0091-J), so renaming an endpoint
 renames it in the rendered lien fact.
 
+Map topology (TICKET-0101, L1/V1): `connects_to` and `borde` are the two
+geographic types (`MAP_TOPOLOGY_TYPES`). A new geographic row, or a row whose
+type changes, must join two locations and carry exactly the type
+`zone_rules.geographic_link_type` derives (`borde` when either end is a
+zone). Retyping a row into or out of the geographic pair is refused. A
+`connects_to` <-> `borde` change rewrites the row's typed fact through
+`update_typed_fact_content` (N1). An existing row whose type does not change
+is never re-judged: a zone that loses its last child keeps its `borde`
+links (K).
+
 - `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
   relation, apply a clamped intensity delta, append the previous state to
   `change_history`. Used by `_apply_mutation`.
@@ -62,11 +73,14 @@ from ..encounters import record_encounter
 from ..models import Entity, Fact, Knowledge, Relation
 from ..prose_render import entity_token
 from ..relation_orientation import (
+    MAP_TOPOLOGY_TYPES,
+    borde_fact_content,
     connects_to_fact_content,
     is_social,
     lien_fact_content,
     orient_legacy,
 )
+from ..zone_rules import geographic_link_type
 from ._shared import _append_history_snapshot, _clamp
 from .facts import create_fact, update_typed_fact_content
 from .knowledge import write_knowledge
@@ -148,8 +162,8 @@ def _birth_typed_fact(db: Session, rel: Relation, changed_by: str) -> Optional[F
     name_a, name_b = _endpoint_tokens(db, rel)
     if is_social(rel.type):
         content, level = lien_fact_content(name_a, rel.type, name_b), "unaware"
-    elif rel.type == "connects_to":
-        content, level = connects_to_fact_content(name_a, name_b), "knows"
+    elif rel.type in MAP_TOPOLOGY_TYPES:
+        content, level = _map_fact_content(rel.type, name_a, name_b), "knows"
     else:
         return None
     return create_fact(
@@ -158,6 +172,53 @@ def _birth_typed_fact(db: Session, rel: Relation, changed_by: str) -> Optional[F
     )
 
 
+def _map_fact_content(relation_type: str, name_a: str, name_b: str) -> str:
+    """The typed-fact content of a geographic edge of `relation_type`."""
+    if relation_type == "borde":
+        return borde_fact_content(name_a, name_b)
+    return connects_to_fact_content(name_a, name_b)
+
+
+def _require_map_shape(
+    db: Session, *, entity_a_id: str, entity_b_id: str, new_type: str, old_type: Optional[str],
+) -> None:
+    """L1/V1 (TICKET-0101), judged on a new row (`old_type=None`) or a type
+    change only: no retype into or out of the geographic pair; a geographic
+    row joins two locations and carries the type `geographic_link_type`
+    derives. Raises `ValueError` before anything is mutated."""
+    new_is_map = new_type in MAP_TOPOLOGY_TYPES
+    if old_type is not None and (old_type in MAP_TOPOLOGY_TYPES) != new_is_map:
+        raise ValueError(f"write_relation: a {old_type} relation cannot become {new_type}")
+    if not new_is_map:
+        return
+    for entity_id in (entity_a_id, entity_b_id):
+        entity = db.get(Entity, entity_id)
+        if entity is None or entity.type != "location":
+            raise ValueError(f"write_relation: {new_type} joins two locations, {entity_id!r} is not one")
+    expected = geographic_link_type(db, entity_a_id, entity_b_id)
+    if new_type != expected:
+        raise ValueError(
+            f"write_relation: these two locations take a {expected} link, not {new_type}"
+        )
+
+
+def _checked_old_type(db: Session, *, mode: str, relation_id: Optional[str], new_type: Optional[str]) -> Optional[str]:
+    """The current type of the row a `mode="set"` update targets (None
+    otherwise), after judging a type change against L1/V1 before anything
+    is mutated."""
+    if mode != "set" or relation_id is None:
+        return None
+    existing = db.get(Relation, relation_id)
+    if existing is None:
+        return None
+    if new_type is not None and new_type != existing.type:
+        _require_map_shape(
+            db, entity_a_id=existing.entity_a_id, entity_b_id=existing.entity_b_id,
+            new_type=new_type, old_type=existing.type,
+        )
+    return existing.type
+
+
 def _on_relation_born(db: Session, rel: Relation, provenance: str) -> None:
     """Birth hook of a new relation: its typed fact, then, for a social
     type, the `relation` encounter between its endpoints (BRIEF-0091-C)."""
@@ -184,6 +245,21 @@ def _refresh_lien_content(db: Session, rel: Relation, old_type: Optional[str], c
     )
 
 
+def _refresh_map_content(db: Session, rel: Relation, old_type: Optional[str], changed_by: str) -> None:
+    """Rewrite a geographic edge's typed fact after a `connects_to` <-> `borde`
+    change (N1); the previous content stays in the fact's `change_history`.
+    A row with no typed fact is left alone."""
+    if old_type == rel.type or old_type not in MAP_TOPOLOGY_TYPES or rel.type not in MAP_TOPOLOGY_TYPES:
+        return
+    fact = lien_fact_of(db, rel)
+    if fact is None:
+        return
+    name_a, name_b = _endpoint_tokens(db, rel)
+    update_typed_fact_content(
+        db, fact=fact, content=_map_fact_content(rel.type, name_a, name_b), changed_by=changed_by,
+    )
+
+
 def _build_relation_delta(
     db: Session, *, world_id, entity_a_id, entity_b_id, type, value, direction,
     visible_to_b, notes, mutation_id, now,
@@ -272,7 +348,8 @@ def write_relation(
     `visible_to_b` and `notes`.
 
     A social type with a `direction` other than `'a_to_b'` raises
-    `ValueError`; so does a missing endpoint entity on create. Every create
+    `ValueError`; so does a missing endpoint entity on create, and so does a
+    geographic row that breaks L1/V1 (`_require_map_shape`). Every create
     births its typed fact (module docstring). `changed_by` is the fact's
     provenance; it defaults to `mutation:<id>` when `mutation_id` is set,
     else `creator_crud`.
@@ -282,10 +359,7 @@ def write_relation(
 
     now = datetime.now(UTC)
     provenance = changed_by or (f"mutation:{mutation_id}" if mutation_id else "creator_crud")
-    old_type = None
-    if mode == "set" and relation_id is not None:
-        existing = db.get(Relation, relation_id)
-        old_type = existing.type if existing is not None else None
+    old_type = _checked_old_type(db, mode=mode, relation_id=relation_id, new_type=type)
     _require_orientation(type if type is not None else old_type, direction)
 
     if mode == "delta":
@@ -307,12 +381,16 @@ def write_relation(
     is_new = sa_inspect(rel).transient
     if is_new:
         _endpoint_names(db, rel.entity_a_id, rel.entity_b_id)
+        _require_map_shape(
+            db, entity_a_id=rel.entity_a_id, entity_b_id=rel.entity_b_id, new_type=rel.type, old_type=None,
+        )
     db.add(rel)
     if is_new:
         db.flush()
         _on_relation_born(db, rel, provenance)
     elif mode == "set":
         _refresh_lien_content(db, rel, old_type, provenance)
+        _refresh_map_content(db, rel, old_type, provenance)
     return rel
 
 
diff --git a/src/world_engine/zone_rules.py b/src/world_engine/zone_rules.py
new file mode 100644
index 0000000..6b6326b
--- /dev/null
+++ b/src/world_engine/zone_rules.py
@@ -0,0 +1,84 @@
+"""Zones and visitable locations (TICKET-0101) — pure reads, no write.
+
+A location is a **zone** when at least one ACTIVE location names it as
+`parent_location_id`; every other location is **visitable** (A1). The
+property is derived from the tree on every call and never stored: there is
+no zone flag, no per-type setting, no cache.
+
+- `active_child_ids(db, location_id, exclude_id=None)` : the active children,
+  oldest first (`entity.created_at`, then id).
+- `is_zone(db, location_id)` : at least one active child.
+- `zone_ids(db, world_id)` : every zone of a world, in one query.
+- `geographic_link_type(db, a, b)` : `"borde"` when either endpoint is a zone,
+  else `"connects_to"` (L1). The only place the type of a geographic link is
+  decided.
+- `require_visitable(db, location_id, what=...)` : raises `ZoneRefusal` when
+  `location_id` is a zone (B1/Q1). `what` names the refused thing in the
+  message shown to the creator.
+
+Reads see the session's pending rows (autoflush), so a child added earlier in
+the same transaction already makes its parent a zone.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .models import Entity, Location
+
+
+class ZoneRefusal(ValueError):
+    """A being, an item or a discoverable detail was placed in a zone."""
+
+
+def active_child_ids(db: Session, location_id: str, *, exclude_id: Optional[str] = None) -> list[str]:
+    """Ids of the ACTIVE locations whose parent is `location_id`, oldest first;
+    `exclude_id` is left out (the child being created or moved)."""
+    rows = db.exec(
+        select(Entity.id)
+        .join(Location, Location.id == Entity.id)
+        .where(Location.parent_location_id == location_id, Entity.status == "active")
+        .order_by(Entity.created_at, Entity.id)
+    ).all()
+    return [row for row in rows if row != exclude_id]
+
+
+def is_zone(db: Session, location_id: Optional[str]) -> bool:
+    """True when `location_id` has at least one active child (A1)."""
+    if not location_id:
+        return False
+    return bool(active_child_ids(db, location_id))
+
+
+def zone_ids(db: Session, world_id: str) -> set[str]:
+    """Every zone of `world_id`: the distinct parents of its active locations."""
+    rows = db.exec(
+        select(Location.parent_location_id)
+        .join(Entity, Entity.id == Location.id)
+        .where(
+            Entity.world_id == world_id,
+            Entity.status == "active",
+            Location.parent_location_id.is_not(None),
+        )
+    ).all()
+    return {row for row in rows if row}
+
+
+def geographic_link_type(db: Session, entity_a_id: str, entity_b_id: str) -> str:
+    """The type a geographic link between two locations must have (L1)."""
+    if is_zone(db, entity_a_id) or is_zone(db, entity_b_id):
+        return "borde"
+    return "connects_to"
+
+
+def require_visitable(db: Session, location_id: Optional[str], *, what: str) -> None:
+    """Refuse a zone as the place of `what` (B1/Q1). A null id passes."""
+    if not is_zone(db, location_id):
+        return
+    entity = db.get(Entity, location_id)
+    name = entity.name if entity is not None else location_id
+    raise ZoneRefusal(
+        f"{what} : « {name} » est une zone, on ne peut s'y trouver que dans l'un de ses lieux"
+    )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 4878b10..f27708b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17476,6 +17476,32 @@ seulement » stays. The tree is flattened iteratively in `EntityList.svelte`
 hierarchy Nia reads at a glance. E3, the descent view restyled: the
 descent itself was what she asked to lose.
 
+## ZONES AND VISITABLE PLACES (TICKET-0101) -- `borde` AND THE DERIVED LINK TYPE (BRIEF-0101-a, no schema change)
+
+**A1, L1.** A location with at least one active child is a zone; every
+other location is visitable. The property is derived from
+`location.parent_location_id` on every read (`zone_rules.py`) and never
+stored. `connects_to` joins two visitable locations and stays the only
+traversable link; `borde` is the link whenever a zone is an endpoint. The
+type is derived from the two endpoints (`geographic_link_type`), never
+chosen: `write_relation` refuses a new geographic row, or a type change,
+whose type is not the derived one, and refuses any retype into or out of
+the geographic pair (V1). `spatial_author.link_locations` is the creator
+entry: it derives the type, reuses the pair's existing row (retyped in
+place when needed, N1), and materializes doors on `connects_to` only. The
+fiche relation form keeps one geographic entry (`connects_to`); room
+batches and regions write derived types.
+
+**O1.** `borde` joins `RELATION_GRAPH_EXCLUDED_TYPES` (kept a literal for
+`relation_graph.py`); `MAP_TOPOLOGY_TYPES = ("connects_to", "borde")`
+replaces the two `!= "connects_to"` scans (`lore_selectors.py`,
+`day_concordance.py`). A `borde` row births one typed fact, « A borde B. »,
+at `knows`, and records no encounter. The travel and reachability readers
+change no line: none can reach a zone.
+
+**Rejected.** A stored zone flag or per-type setting (A1: derived only).
+Letting the creator pick `borde` (L1: the type follows the endpoints).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/tickets/connects-to-readers-TICKET-0082.md b/tooling/tickets/connects-to-readers-TICKET-0082.md
index 0cc8604..90c9a95 100644
--- a/tooling/tickets/connects-to-readers-TICKET-0082.md
+++ b/tooling/tickets/connects-to-readers-TICKET-0082.md
@@ -91,6 +91,9 @@ named mutation).
   moved out of `context.py` at TICKET-0090, BRIEF-0090-a (`context.py` re-imports it).
 - `cockpit/crud/_shared.py:137` — the relation-type datalist literal.
 - `link_author.py:68` — `assert "connects_to" not in _LINK_RELATION_TYPES`.
+- `zone_rules.py` — `geographic_link_type` returns `"connects_to"` or `"borde"`
+  (TICKET-0101, BRIEF-0101-A); `relation_orientation.py` also gained
+  `MAP_TOPOLOGY_TYPES = ("connects_to", "borde")` there. A derived type, never a traversal.
 
 These three are outside the twelve-module traversal count (they hold a type
 literal, never execute a `connects_to` traversal) but are listed here for
diff --git a/tooling/verify/checks/known_reachability.py b/tooling/verify/checks/known_reachability.py
index e03d509..9672dca 100644
--- a/tooling/verify/checks/known_reachability.py
+++ b/tooling/verify/checks/known_reachability.py
@@ -332,6 +332,9 @@ DOCUMENTED_MODULES = frozenset({
     "world_engine/lore_selectors.py",
     "world_engine/writes/relations.py",
     "world_engine/relation_orientation.py",
+    # TICKET-0101, BRIEF-0101-A: returns the literal as a derived link type
+    # (`geographic_link_type`); vocabulary site, never a traversal.
+    "world_engine/zone_rules.py",
 })
 
 
diff --git a/tooling/verify/checks/zone_map_links.py b/tooling/verify/checks/zone_map_links.py
new file mode 100644
index 0000000..1835c96
--- /dev/null
+++ b/tooling/verify/checks/zone_map_links.py
@@ -0,0 +1,289 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-A) — geographic links follow the tree.
+
+DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
+DATABASE_URL set BEFORE any world_engine import) — same idiom as
+relation_orientation.py, so this check never touches Nia's real DB. Fixture
+data is built through the REAL sanctioned writers (`write_relation`,
+`spatial_author.link_locations`). Zero rows examined in any assertion is a
+FAIL, never a vacuous pass.
+
+Fixture: visitable locations V1, V2, V3; zone Z with active child C; P,
+visitable at first, linked to V3 by `connects_to`, then given a child Q.
+
+Five assertions:
+  a. L1 at write: `connects_to` V1-Z and `borde` V1-V2 are refused
+     (`ValueError`); `connects_to` V1-V2 and `borde` V1-Z are accepted;
+     `connects_to` between a location and a character is refused.
+  b. Derivation: `link_locations` writes `borde` for V2-Z and `connects_to`
+     for V2-V3; a second call on the same pair returns the same row and
+     writes no second one.
+  c. V1, no retype across the pair: a `borde` row cannot become `ally`; an
+     `ally` row cannot become `connects_to`.
+  d. N1: once P has a child, `link_locations(V3, P)` retypes the existing
+     row in place — same id, type `borde`, `change_history` one longer — and
+     rewrites its fact to `borde_fact_content(...)`, the old content kept in
+     the fact's `change_history`.
+  e. The structural split: `borde` is in `RELATION_GRAPH_EXCLUDED_TYPES`,
+     `is_social("borde")` is False, a born `borde` row has exactly one fact
+     at `knows` and records no encounter; the two relation scans that spelled
+     `!= "connects_to"` (lore_selectors.py, day_concordance.py) now exclude
+     `MAP_TOPOLOGY_TYPES` and spell no such literal.
+
+Named mutations: delete `_require_map_shape`'s derived-type raise -> (a);
+drop `"borde"` from the tuple -> (e); delete `_refresh_map_content`'s call
+-> (d); make `link_locations` skip its `find_map_relation` reuse -> (b).
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
+def _seed(session):
+    """V1, V2, V3, P visitable; Z with child C; one character H."""
+    from world_engine.models import Entity, Location, World
+
+    world = World(name="Zone Check", is_active=True)
+    session.add(world)
+    session.commit()
+    session.refresh(world)
+    ids: dict[str, str] = {}
+    for label, parent in (("V1", None), ("V2", None), ("V3", None), ("P", None), ("Z", None), ("C", "Z")):
+        entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
+        session.add(entity)
+        session.flush()
+        session.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
+        session.commit()
+        ids[label] = entity.id
+    hero = Entity(world_id=world.id, type="character", name="Héros")
+    session.add(hero)
+    session.commit()
+    ids["H"] = hero.id
+    return world.id, ids
+
+
+def _refused(session, label: str, **kwargs) -> int:
+    from world_engine.writes.relations import write_relation
+
+    try:
+        write_relation(session, mode="set", value=50, direction="mutual", **kwargs)
+    except ValueError:
+        session.rollback()
+        return 1
+    session.rollback()
+    fail(f"{label}: write accepted")
+    return 0
+
+
+def check_a_l1(session, world_id, ids) -> None:
+    from world_engine.writes.relations import write_relation
+
+    n = _refused(session, "(a) connects_to V1-Z", world_id=world_id, entity_a_id=ids["V1"],
+                 entity_b_id=ids["Z"], type="connects_to")
+    n += _refused(session, "(a) borde V1-V2", world_id=world_id, entity_a_id=ids["V1"],
+                  entity_b_id=ids["V2"], type="borde")
+    n += _refused(session, "(a) connects_to V1-character", world_id=world_id, entity_a_id=ids["V1"],
+                  entity_b_id=ids["H"], type="connects_to")
+    for a, b, t in (("V1", "V2", "connects_to"), ("V1", "Z", "borde")):
+        rel = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids[a],
+                             entity_b_id=ids[b], type=t, value=50, direction="mutual")
+        session.commit()
+        if rel.type != t:
+            fail(f"(a) {a}-{b} stored as {rel.type!r}, expected {t!r}")
+        n += 1
+    if n != 5:
+        fail(f"(a) expected 3 refusals and 2 writes, got {n} outcomes")
+    COUNTS["a"] = n
+
+
+def check_b_derivation(session, world_id, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Relation
+    from world_engine.spatial_author import link_locations
+
+    seen = 0
+    for a, b, expected in (("V2", "Z", "borde"), ("V2", "V3", "connects_to")):
+        first = link_locations(session, world_id=world_id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
+        session.commit()
+        again = link_locations(session, world_id=world_id, entity_a_id=ids[b], entity_b_id=ids[a], changed_by="check")
+        session.commit()
+        if first.type != expected:
+            fail(f"(b) link_locations({a}, {b}) wrote {first.type!r}, expected {expected!r}")
+        if again.id != first.id:
+            fail(f"(b) a second link_locations({b}, {a}) returned a different row")
+        rows = session.exec(select(Relation).where(
+            ((Relation.entity_a_id == ids[a]) & (Relation.entity_b_id == ids[b]))
+            | ((Relation.entity_a_id == ids[b]) & (Relation.entity_b_id == ids[a]))
+        )).all()
+        if len(rows) != 1:
+            fail(f"(b) {a}-{b} carries {len(rows)} relation rows, expected 1")
+        seen += len(rows)
+    COUNTS["b"] = seen
+
+
+def check_c_no_cross_retype(session, world_id, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Entity, Relation
+    from world_engine.writes.relations import write_relation
+
+    borde = session.exec(select(Relation).where(Relation.type == "borde")).first()
+    other = Entity(world_id=world_id, type="character", name="Autre")
+    session.add(other)
+    session.commit()
+    ally = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids["H"],
+                          entity_b_id=other.id, type="ally", value=60)
+    session.commit()
+    n = 0
+    for rel, new_type, direction in ((borde, "ally", "a_to_b"), (ally, "connects_to", "mutual")):
+        if rel is None:
+            fail("(c) fixture row missing")
+            continue
+        before = rel.type
+        try:
+            write_relation(session, mode="set", relation_id=rel.id, type=new_type, value=50, direction=direction)
+        except ValueError:
+            n += 1
+        else:
+            fail(f"(c) a {before} row was retyped into {new_type}")
+        session.rollback()
+        session.refresh(rel)
+        if rel.type != before:
+            fail(f"(c) refused retype still changed the row to {rel.type!r}")
+    COUNTS["c"] = n
+
+
+def check_d_in_place_retype(session, world_id, ids) -> None:
+    from world_engine.models import Entity, Location
+    from world_engine.prose_render import entity_token
+    from world_engine.relation_orientation import borde_fact_content
+    from world_engine.spatial_author import link_locations
+    from world_engine.writes.relations import lien_fact_of, write_relation
+
+    rel = write_relation(session, mode="set", world_id=world_id, entity_a_id=ids["V3"],
+                         entity_b_id=ids["P"], type="connects_to", value=50, direction="mutual")
+    session.commit()
+    rel_id, history_before = rel.id, len(rel.change_history or [])
+    fact = lien_fact_of(session, rel)
+    fact_history_before = len(fact.change_history or []) if fact else -1
+
+    child = Entity(world_id=world_id, type="location", name="Lieu Q")
+    session.add(child)
+    session.flush()
+    session.add(Location(id=child.id, parent_location_id=ids["P"]))
+    session.commit()
+
+    out = link_locations(session, world_id=world_id, entity_a_id=ids["V3"], entity_b_id=ids["P"], changed_by="check")
+    session.commit()
+    session.refresh(out)
+    if out.id != rel_id:
+        fail("(d) the retype wrote a new row instead of changing the existing one")
+    if out.type != "borde":
+        fail(f"(d) V3-P is {out.type!r} after P gained a child, expected 'borde'")
+    if len(out.change_history or []) != history_before + 1:
+        fail("(d) relation change_history did not grow by one")
+    fact = lien_fact_of(session, out)
+    if fact is None:
+        fail("(d) the retyped row lost its fact")
+        return
+    session.refresh(fact)
+    expected = borde_fact_content(entity_token(ids["V3"], "Lieu V3"), entity_token(ids["P"], "Lieu P"))
+    if fact.content_raw != expected:
+        fail(f"(d) fact content {fact.content_raw!r}, expected {expected!r}")
+    if len(fact.change_history or []) != fact_history_before + 1:
+        fail("(d) fact change_history did not keep the previous content")
+    COUNTS["d"] = 1 + len(out.change_history or [])
+
+
+def check_e_structural(session, world_id, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Fact, Relation, Rencontre
+    from world_engine.relation_orientation import RELATION_GRAPH_EXCLUDED_TYPES, is_social
+
+    n = 0
+    if "borde" not in RELATION_GRAPH_EXCLUDED_TYPES:
+        fail("(e) 'borde' missing from RELATION_GRAPH_EXCLUDED_TYPES")
+    if is_social("borde"):
+        fail("(e) is_social('borde') is True")
+    rows = session.exec(select(Relation).where(Relation.type == "borde")).all()
+    for rel in rows:
+        facts = session.exec(select(Fact).where(Fact.relation_id == rel.id)).all()
+        if len(facts) != 1 or facts[0].default_level != "knows":
+            fail(f"(e) borde row {rel.id} has {len(facts)} fact(s), expected one at 'knows'")
+        n += 1
+    encounters = session.exec(select(Rencontre)).all()
+    location_ids = {ids[k] for k in ("V1", "V2", "V3", "P", "Z", "C")}
+    for row in encounters:
+        ends = {row.entity_lo_id, row.entity_hi_id}
+        if ends & location_ids:
+            fail("(e) an encounter was recorded between locations")
+    for rel_path in ("lore_selectors.py", "day_concordance.py"):
+        text = (SRC / "world_engine" / rel_path).read_text(encoding="utf-8")
+        if 'Relation.type != "connects_to"' in text:
+            fail(f"(e) {rel_path} still excludes connects_to alone")
+        if "Relation.type.not_in(MAP_TOPOLOGY_TYPES)" not in text:
+            fail(f"(e) {rel_path} does not exclude MAP_TOPOLOGY_TYPES")
+        n += 1
+    COUNTS["e"] = n
+
+
+def main() -> int:
+    engine = _fresh_engine()
+    from sqlmodel import Session as DbSession
+
+    with DbSession(engine) as session:
+        world_id, ids = _seed(session)
+        check_a_l1(session, world_id, ids)
+        check_b_derivation(session, world_id, ids)
+        check_c_no_cross_retype(session, world_id, ids)
+        check_d_in_place_retype(session, world_id, ids)
+        check_e_structural(session, world_id, ids)
+
+    for key in ("a", "b", "c", "d", "e"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero rows examined")
+
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_map_links — "
+        f"(a) L1 at write [{COUNTS['a']}], (b) derived type, no duplicate [{COUNTS['b']}], "
+        f"(c) no retype across the pair [{COUNTS['c']}], (d) in-place retype [{COUNTS['d']}], "
+        f"(e) structural split [{COUNTS['e']}]"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Any refusal of a zone as a place (B), any promotion or move (C), the v2.12 index and migration (D: the model's index predicate is NOT touched here), neighbour checkboxes and the room batch dialog (E), graph modes (F).
- Any change to a traversal reader (R-12): `_location_neighbours`, `day_plan`, `day_concordance`'s BFS, `tick_context`, the door readers.
- Offering `borde` in the fiche's relation datalist, or a creator-chosen type.
- Rolling a location up to its zones in a reader (carried forward in the ticket).

## Invariants to defend

- **`connects_to` (now: and `borde`) is map topology, never a social signal** (CLAUDE.md): `borde` joins the tuple every scan uses; the two scans that spelled the literal now exclude both.
- **History is sacred**: a retype goes through `mode="set"`, which snapshots the row; the fact rewrite keeps its previous content.
- **Hard deletes are a closed list**: nothing here deletes a relation.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `known_reachability.py` or `relation_graph.py` fails after the commit.

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

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff plus `tooling/standards/DECISIONS_INDEX.md`.
- `zone_map_links.py` → `PASS: zone_map_links — (a) L1 at write [5], (b) derived type, no duplicate [2], (c) no retype across the pair [2], (d) in-place retype [2], (e) structural split [5]`.
- `relation_orientation.py`, `relation_graph.py`, `known_reachability.py`, `claude_md_contract.py`, `function_length.py`, `single_canon_write.py`, `decisions_index.py` → `PASS`.
- The four named mutations failed as stated.
- `corpus_gate.py` → 130/130.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `ZONES AND VISITABLE PLACES (TICKET-0101) -- \`borde\` AND THE DERIVED LINK TYPE (BRIEF-0101-a, no schema change)` and the CLAUDE.md bullets — in the diff. No schema change (the index is D's).
