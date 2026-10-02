<!-- slug: placement-guards -->
# BRIEF 0101-B — "Nothing is placed in a zone"

Lot: LOT-0101-zones.md (authoritative on conflict)
Depends on: A (C-01)
Commit header for decisions: `(BRIEF-0101-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- BRIEF-0101-A is committed: `src/world_engine/zone_rules.py` defines `def require_visitable(db: Session, location_id: Optional[str], *, what: str) -> None:` and `class ZoneRefusal(ValueError):`
- `src/world_engine/cockpit/play_stream.py:383` → `def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:`; `:406` → `    char = db.get(Character, player_id)`; `:457` → `    char.current_location_id = location_id`
- `src/world_engine/cockpit/mutations.py:678` → `        return f"npc_move: destination {to_location_id!r} is not an active location in this world"`
- `src/world_engine/cockpit/routes/creator.py:586` → `def _validate_pc_creation(`; `:603` → `            detail="current_location_id must be a location entity in the active world",`
- `src/world_engine/cockpit/routes/play.py:393` → `            detail=f"{body.location_id!r} is not a location of this world",`
- `src/world_engine/writes/config.py:412` → `def write_npc_schedule(`; `:456` → `                "location of this world"`
- `src/world_engine/cockpit/crud/entities.py:336` → `def _build_extension_kwargs(`; `:355` → `            raise HTTPException(422, "Equipping an item requires an owner")`
- `src/world_engine/cockpit/crud/locations.py:131` → `def create_discoverable_detail(`
- `src/world_engine/npc_group_author.py:54` → `def resolve_vocabulary(db: Session, root_location_id: str) -> dict:`; `:208` → `    notes.append("Placement non résolu — replié sur la racine")`
- `src/world_engine/writes/characters.py:48` → `    character.current_location_id = to_location_id`
- the zone bullet A added to `CLAUDE.md` ends with `type is derived from its endpoints (\`link_locations\`), never chosen.`

## Facts carried

### R-08 — placement writes, enumerated [M]
Opened: grep of `current_location_id\s*=[^=]` and `Character(` over `src/`
(E1); the registry `cockpit/crud/entities.py:123-140`; `writes/config.py:
412-490`; `crud/locations.py:130-155`; `npc_agent.py:59-110`;
`npc_group_author.py:54-81, 195-209`.
Finding: three sites assign `character.current_location_id` —
`writes/characters.py:48` (`write_character_location`, called only by
`mutations._mutation_apply_npc_move`, `:680`), `play_stream.py:457`
(`_perform_travel`, `:383`, shared by `routes/play.py:285, 389, 459`), and
`routes/creator.py:675-681` (the PC constructor). The registry declares
three `entity_ref` location fields: `character.current_location_id`
(`:132`), `location.parent_location_id`, `item.location_id` (`:136`), all
coerced in `_build_extension_kwargs` (`:336-356`) on create and update — the
NPC batch commit (`npc_agent.py:205-220`) and every fiche reach it. The
schedule has one writer (`write_npc_schedule`, the sole `NpcSchedule(`).
Discoverable details are created at `create_discoverable_detail` only;
their update never moves them. The NPC batch offers `expanded_location_ids`
(root + descendants) and falls back to the root (`:208-209`).
Consequence: seven guard points (B, C-05); the NPC batch vocabulary keeps
visitable members, and a zone root is no fallback.

### R-17 — the lore guarantee [M]
Opened: `lore_write_apply.py:250-330`; `cockpit/routes/lore_write.py:82-89`.
Finding: the Lore tool writes facts, participants, defaults, knowledge,
memberships and `controls`; its entity creator makes a location without a
parent and an NPC without a location.
Consequence: no B guard reaches it; asking about and writing on a zone stay
open. Held by the live gate.

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

### C-05 — the placement guard sites
Produced by: B   Consumed by: C (the moves land on a visitable child)
| site | refusal |
|---|---|
| `play_stream._travel_refusal` (from `_perform_travel`) | `{"status": "zone_destination", "location_id", "detail"}`, nothing written; `POST /api/travel` → 409 `detail` |
| `mutations._mutation_apply_npc_move` | returns the `ZoneRefusal` text ("Needs attention") |
| `routes/creator._validate_pc_creation` | 409 |
| `crud/entities._require_placement_visitable` (character `current_location_id`, item `location_id`) | 409, only when the value is set and differs from the stored one |
| `writes/config.write_npc_schedule` | `ZoneRefusal` (a `ValueError`; the route maps it to 422) |
| `crud/locations.create_discoverable_detail` | 409 |
| `npc_group_author.resolve_vocabulary` / `_resolve_unit_location` | zones left out; a zone root is no fallback (note « Placement non résolu — la racine est une zone, PNJ sans lieu », location None) |

## Context

B1: every write that places a being refuses a zone; Q1 extends it to items lying somewhere and discoverable details. The RECON enumerated seven such writes (R-08); P1 locked one guard called at each, held by a check that drives every path. Existing data in a zone is reported by D, never re-judged here on an unrelated save.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `play_stream.py`: `_travel_refusal` (unknown/foreign/inactive destination or unknown player → `invalid_destination`; zone → `zone_destination` with `detail`), called first by `_perform_travel`, whose own validation lines move there (the function stays under 80 lines);
   - `routes/play.py`: `POST /api/travel` answers 409 with `detail` on `zone_destination`;
   - `mutations.py`: `npc_move` returns the refusal text;
   - `routes/creator.py`: `_validate_pc_creation` answers 409;
   - `crud/entities.py`: `_PLACEMENT_FIELDS`, `_require_placement_visitable`, called at the end of `_build_extension_kwargs`;
   - `writes/config.py`: `write_npc_schedule` calls `require_visitable`; its docstring is tightened to keep the function at 80 lines;
   - `crud/locations.py`: `create_discoverable_detail` answers 409;
   - `npc_group_author.py`: the vocabulary keeps visitable members; a zone root is no fallback (`Optional[str]`);
   - `CLAUDE.md`: the zone bullet names the guard and `zone_placement.py`;
   - `tooling/verify/checks/zone_placement.py`;
   - the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Named mutations, each run with `python tooling/verify/checks/zone_placement.py`, then restored:
   - in `play_stream.py`, replace `        require_visitable(db, location_id, what="Voyage")` with `        pass` → `FAIL: (a) travel into a zone: {'status': 'ok', …}`;
   - in `crud/entities.py`, delete `    _require_placement_visitable(db, entity_type, ext_kwargs, current)` → `FAIL: (a) fiche, character: a zone was accepted` and `FAIL: (a) fiche, item: a zone was accepted`;
   - in `npc_group_author.py`, delete ` if not is_zone(db, eid)` → `FAIL: (b) the NPC batch vocabulary offers the zone itself`;
   - add to `cockpit/play.py` a function `def _zz(char):` whose body is `    char.current_location_id = None` → `FAIL: (c) a new current_location_id write site, unguarded until named here: world_engine/cockpit/play.py::_zz`.
4. Commit message: `feat(zones): every placement write refuses a zone (BRIEF-0101-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 8eaf778..2e46fd1 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -223,7 +223,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
 - **A location with an active child is a zone, derived, never stored
   (`zone_rules.py`).** Only `connects_to` is traversable and it never
   touches a zone; a link touching a zone is `borde`. A geographic link's
-  type is derived from its endpoints (`link_locations`), never chosen.
+  type is derived from its endpoints (`link_locations`), never chosen. No
+  being, item or discoverable detail is placed in a zone
+  (`require_visitable`, at every placement write) -- `zone_placement.py`.
 - **The `ledger` is append-only.** INSERT-only on both canon-write paths;
   corrections are new compensating lines. No UPDATE/DELETE endpoint or code
   path may touch a `ledger` row.
diff --git a/src/world_engine/cockpit/crud/entities.py b/src/world_engine/cockpit/crud/entities.py
index a2a97ac..c57f027 100644
--- a/src/world_engine/cockpit/crud/entities.py
+++ b/src/world_engine/cockpit/crud/entities.py
@@ -60,6 +60,7 @@ from ...spatial_author import location_type_template
 from ...tick_normalize import _EVENT_TYPES
 from ...traits import checkable_traits, ext_columns_for, form_fields_for
 from ...writes.schema import create_entity_type
+from ...zone_rules import ZoneRefusal, require_visitable
 from ...writes import (
     KNOWLEDGE_LEVELS,
     NPC_GOAL_HORIZONS,
@@ -333,6 +334,30 @@ def _apply_base_fields(db: DbSession, entity: Entity, data: dict) -> None:
         setattr(entity, name, value)
 
 
+# TICKET-0101 (B1/Q1): the registry fields that place a being or an item
+# somewhere -- a zone is refused there, on create and whenever the value
+# changes (an unchanged value already sitting in a zone is reported by the
+# v2.12 migration, never re-judged on an unrelated save).
+_PLACEMENT_FIELDS: dict[str, tuple[str, str]] = {
+    "character": ("current_location_id", "Lieu du personnage"),
+    "item": ("location_id", "Lieu de l'objet"),
+}
+
+
+def _require_placement_visitable(db: DbSession, entity_type: str, ext_kwargs: dict, current: Any) -> None:
+    """409 when a placement field of `entity_type` newly points at a zone."""
+    placement = _PLACEMENT_FIELDS.get(entity_type)
+    if placement is None or placement[0] not in ext_kwargs:
+        return
+    value = ext_kwargs[placement[0]]
+    if not value or value == getattr(current, placement[0], None):
+        return
+    try:
+        require_visitable(db, value, what=placement[1])
+    except ZoneRefusal as exc:
+        raise HTTPException(409, str(exc))
+
+
 def _build_extension_kwargs(
     db: DbSession, entity_type: str, data: dict, *, present_only: bool = False, current: Any = None
 ) -> dict:
@@ -353,6 +378,7 @@ def _build_extension_kwargs(
         owner_id = ext_kwargs["owner_id"] if "owner_id" in ext_kwargs else getattr(current, "owner_id", None)
         if equipped and not owner_id:
             raise HTTPException(422, "Equipping an item requires an owner")
+    _require_placement_visitable(db, entity_type, ext_kwargs, current)
     return ext_kwargs
 
 
diff --git a/src/world_engine/cockpit/crud/locations.py b/src/world_engine/cockpit/crud/locations.py
index c77c809..2238f1b 100644
--- a/src/world_engine/cockpit/crud/locations.py
+++ b/src/world_engine/cockpit/crud/locations.py
@@ -54,6 +54,7 @@ from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
 from ...schedule_reads import unresolved_npcs, where_is, who_is_at
 from ...tick_normalize import _EVENT_TYPES
+from ...zone_rules import ZoneRefusal, require_visitable
 from ...writes import (
     KNOWLEDGE_LEVELS,
     NPC_GOAL_HORIZONS,
@@ -133,8 +134,13 @@ def create_discoverable_detail(
     body: DiscoverableDetailBody,
     db: DbSession = Depends(get_session),
 ) -> dict:
-    """Seed a new discoverable detail on a location (creator direct write)."""
+    """Seed a new discoverable detail on a location (creator direct write).
+    A zone is refused (TICKET-0101, Q1): nobody is ever there to find it."""
     _get_entity(db, location_id)
+    try:
+        require_visitable(db, location_id, what="Détail découvrable")
+    except ZoneRefusal as exc:
+        raise HTTPException(409, str(exc))
     if body.access_level not in ACCESS_LEVELS:
         raise HTTPException(422, f"access_level must be one of {ACCESS_LEVELS}")
     if not (0 <= body.discovery_threshold <= 12):
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index ec37f60..d387aaa 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -68,6 +68,7 @@ from ..writes import (
     write_npc_goal_status,
     write_relation,
 )
+from ..zone_rules import ZoneRefusal, require_visitable
 from .routes import mutations as _routes_mutations
 
 
@@ -676,6 +677,10 @@ def _mutation_apply_npc_move(mut: ProposedMutation, payload: dict, db: Session)
         or destination.world_id != mut.world_id
     ):
         return f"npc_move: destination {to_location_id!r} is not an active location in this world"
+    try:
+        require_visitable(db, to_location_id, what="npc_move")
+    except ZoneRefusal as exc:
+        return str(exc)
 
     write_character_location(db, entity_id=npc_id, to_location_id=to_location_id, mutation_id=mut.id)
     # BRIEF-53 seam: closes the NPC's open gathering_member rows, PLAYER
diff --git a/src/world_engine/cockpit/play_stream.py b/src/world_engine/cockpit/play_stream.py
index d20838a..c32e2f3 100644
--- a/src/world_engine/cockpit/play_stream.py
+++ b/src/world_engine/cockpit/play_stream.py
@@ -29,6 +29,7 @@ from ..models import (
     ProposedMutation,
     PromptTemplate,
 )
+from ..zone_rules import ZoneRefusal, require_visitable
 from .play import (
     ResponseMode,
     _TurnCtx,
@@ -380,19 +381,13 @@ def _scene_response(
     }
 
 
-def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:
-    """Clean location transition for a player. Shared by the creator travel
-    tool and the in-fiction /say travel path. NOT a canon mutation — a state
-    transition (same category as gathering join/migrate); writes no
-    proposed_mutation row. Validates the destination is a location of the
-    player's world; no-ops if already there; otherwise closes open
-    conversations (running analyze_window first), closes the player's open
-    gathering_member rows, updates current_location_id — single commit."""
-    from . import play_physical as _play_physical
-
+def _travel_refusal(player_id: str, location_id: str, db: Session) -> Optional[dict]:
+    """`_perform_travel`'s refusals, nothing written: `invalid_destination`
+    for an unknown, foreign or inactive location or an unknown player;
+    `zone_destination` (with the creator-facing `detail`) for a zone
+    (TICKET-0101, B1). None when the destination is acceptable."""
     player_entity = db.get(Entity, player_id)
     world_id = player_entity.world_id if player_entity else None
-
     dest = db.get(Entity, location_id)
     if (
         dest is None
@@ -400,12 +395,31 @@ def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:
         or world_id is None
         or dest.world_id != world_id
         or dest.status != "active"
+        or db.get(Character, player_id) is None
     ):
         return {"status": "invalid_destination", "location_id": location_id}
+    try:
+        require_visitable(db, location_id, what="Voyage")
+    except ZoneRefusal as exc:
+        return {"status": "zone_destination", "location_id": location_id, "detail": str(exc)}
+    return None
 
+
+def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:
+    """Clean location transition for a player. Shared by the creator travel
+    tool and the in-fiction /say travel path. NOT a canon mutation — a state
+    transition (same category as gathering join/migrate); writes no
+    proposed_mutation row. Validates the destination is a location of the
+    player's world; no-ops if already there; otherwise closes open
+    conversations (running analyze_window first), closes the player's open
+    gathering_member rows, updates current_location_id — single commit.
+    Refusals: `_travel_refusal`."""
+    from . import play_physical as _play_physical
+
+    refusal = _travel_refusal(player_id, location_id, db)
+    if refusal is not None:
+        return refusal
     char = db.get(Character, player_id)
-    if char is None:
-        return {"status": "invalid_destination", "location_id": location_id}
 
     if char.current_location_id == location_id:
         return {"status": "noop", "location_id": location_id}
diff --git a/src/world_engine/cockpit/routes/creator.py b/src/world_engine/cockpit/routes/creator.py
index b369adc..8d996ab 100644
--- a/src/world_engine/cockpit/routes/creator.py
+++ b/src/world_engine/cockpit/routes/creator.py
@@ -49,6 +49,7 @@ from ...writes import (
     write_knowledge,
     write_world_laws,
 )
+from ...zone_rules import ZoneRefusal, require_visitable
 from .. import crud as _crud
 
 router = APIRouter()
@@ -602,6 +603,10 @@ def _validate_pc_creation(body: "PlayerCharacterCreateBody", db: Session) -> tup
             status_code=400,
             detail="current_location_id must be a location entity in the active world",
         )
+    try:
+        require_visitable(db, body.current_location_id, what="Lieu du personnage")
+    except ZoneRefusal as exc:
+        raise HTTPException(status_code=409, detail=str(exc))
 
     creator_user = db.exec(select(User).where(User.role == "creator")).first()
     if creator_user is None:
diff --git a/src/world_engine/cockpit/routes/play.py b/src/world_engine/cockpit/routes/play.py
index f165eed..3b97e9b 100644
--- a/src/world_engine/cockpit/routes/play.py
+++ b/src/world_engine/cockpit/routes/play.py
@@ -392,6 +392,8 @@ def travel(
             status_code=400,
             detail=f"{body.location_id!r} is not a location of this world",
         )
+    if result["status"] == "zone_destination":
+        raise HTTPException(status_code=409, detail=result["detail"])
     return result
 
 
diff --git a/src/world_engine/npc_group_author.py b/src/world_engine/npc_group_author.py
index 0bca835..e4bfafd 100644
--- a/src/world_engine/npc_group_author.py
+++ b/src/world_engine/npc_group_author.py
@@ -22,6 +22,7 @@ import json
 import unicodedata
 from datetime import UTC, datetime
 from pathlib import Path
+from typing import Optional
 
 from fastapi import HTTPException
 from sqlalchemy import delete
@@ -35,6 +36,7 @@ from .models import Entity, Faction, NpcBatch, NpcBatchRow, PromptTemplate, Worl
 from .ollama_client import OllamaError, chat
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
+from .zone_rules import is_zone
 
 JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"
 
@@ -55,8 +57,14 @@ def resolve_vocabulary(db: Session, root_location_id: str) -> dict:
     """Expand `root_location_id` (S1 BFS descent, `link_author.
     expand_location_ids`) into the placement vocabulary available to a batch
     anchored on this region root: the expanded location set and the active
-    world's active faction entities. Read-only, writes nothing."""
-    expanded = sorted(link_author.expand_location_ids(db, [root_location_id]))
+    world's active faction entities. Read-only, writes nothing.
+
+    TICKET-0101 (B1): a zone is never a placement, so the vocabulary keeps
+    the visitable members of the expansion only -- the root itself drops out
+    when it is a zone."""
+    expanded = sorted(
+        eid for eid in link_author.expand_location_ids(db, [root_location_id]) if not is_zone(db, eid)
+    )
 
     location_rows = db.exec(
         select(Entity.id, Entity.name).where(Entity.id.in_(expanded))
@@ -194,10 +202,11 @@ def _line_units(batch: NpcBatch) -> list[tuple[int, int]]:
 
 def _resolve_unit_location(
     batch: NpcBatch, plan: dict[int, list[str | None]], line: dict, line_index: int, ordinal: int, notes: list[str],
-) -> str:
+) -> Optional[str]:
     """Pin > plan > root fallback. A miss (absent slot, or the plan never
     resolved this line) degrades to the root, verbatim-noted — never blocks
-    the unit."""
+    the unit. A root that is a zone (outside the visitable vocabulary,
+    TICKET-0101) is no fallback: the unit gets no location, noted."""
     location_id = line.get("location_id")
     if location_id is not None:
         return location_id
@@ -205,8 +214,12 @@ def _resolve_unit_location(
     resolved = slots[ordinal] if ordinal < len(slots) else None
     if resolved is not None:
         return resolved
+    root_id = batch.scope["root_location_id"]
+    if root_id not in batch.scope.get("expanded_location_ids", []):
+        notes.append("Placement non résolu — la racine est une zone, PNJ sans lieu")
+        return None
     notes.append("Placement non résolu — replié sur la racine")
-    return batch.scope["root_location_id"]
+    return root_id
 
 
 def _resolve_faction_context(db: Session, faction_id: str | None) -> dict | None:
@@ -344,7 +357,7 @@ def run_next_npc(db: Session, batch: NpcBatch) -> dict:
 
     notes: list[str] = []
     location_id = _resolve_unit_location(batch, plan, line, line_index, ordinal, notes)
-    location_entity = db.get(Entity, location_id)
+    location_entity = db.get(Entity, location_id) if location_id else None
     location_name = location_entity.name if location_entity else None
     faction_ctx = _resolve_faction_context(db, line.get("faction_id"))
     other_lines = [l for i, l in enumerate(lines) if i != line_index]
diff --git a/src/world_engine/writes/config.py b/src/world_engine/writes/config.py
index 62871d1..d56f36a 100644
--- a/src/world_engine/writes/config.py
+++ b/src/world_engine/writes/config.py
@@ -62,6 +62,7 @@ from ..models import (
     World,
     WorldLaw,
 )
+from ..zone_rules import require_visitable
 
 
 def write_npc_prices(
@@ -424,9 +425,9 @@ def write_npc_schedule(
     str | None}` — validated all-or-nothing before any write: `phase` in
     `SCHEDULE_PHASES`, no duplicate phase within one payload (defense in
     depth — `idx_npc_schedule_npc_phase` is the structural guard),
-    `location_id` resolves to an ACTIVE location of the same world, and
-    `standing_goal_id`, when present, resolves to an `npc_goal` row
-    belonging to `npc_id` with `kind == "standing"`.
+    `location_id` resolves to an ACTIVE, non-zone location of the same world
+    (zone: `ZoneRefusal`, a `ValueError`), and `standing_goal_id`, when
+    present, is a `kind == "standing"` `npc_goal` row of `npc_id`.
 
     An empty `rows` list is legal and means "this NPC has no schedule" —
     the delete runs, nothing is inserted (B1, sparse table).
@@ -455,6 +456,7 @@ def write_npc_schedule(
                 f"write_npc_schedule: location_id {location_id!r} is not an active "
                 "location of this world"
             )
+        require_visitable(db, location_id, what=f"Horaire ({phase})")
 
         if standing_goal_id is not None:
             # Raw SQL, not the NpcGoal ORM class: N1 (npc_goal_read.py) scopes
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index f27708b..084591b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17502,6 +17502,24 @@ change no line: none can reach a zone.
 **Rejected.** A stored zone flag or per-type setting (A1: derived only).
 Letting the creator pick `borde` (L1: the type follows the endpoints).
 
+## NOTHING IS PLACED IN A ZONE (TICKET-0101) -- ONE GUARD AT EVERY PLACEMENT WRITE (BRIEF-0101-b, no schema change)
+
+**B1, Q1, P1.** `zone_rules.require_visitable` refuses a zone at every
+write that places a being, an item or a discoverable detail: travel
+(`_travel_refusal`, status `zone_destination`, 409 on the creator route),
+`npc_move` apply ("Needs attention"), PC creation, the fiche's character
+location and item location (only when the value changes: data already in
+a zone is reported by v2.12, never re-judged on an unrelated save),
+schedules, and discoverable detail creation. The NPC batch vocabulary keeps
+the visitable members of its expansion; a root that is a zone is no
+fallback. `zone_placement.py` drives each path and pins the three sites
+that assign `current_location_id`.
+
+**Rejected.** P2, funnelling every location write through
+`write_character_location`: invasive for the PC constructor and the
+generic fiche write. Reactivates when a seventh write site appears
+(`zone_placement.py` (c) fails on it).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/zone_placement.py b/tooling/verify/checks/zone_placement.py
new file mode 100644
index 0000000..ac4e286
--- /dev/null
+++ b/tooling/verify/checks/zone_placement.py
@@ -0,0 +1,276 @@
+"""G1 check for TICKET-0101 (BRIEF-0101-B) — nothing is placed in a zone.
+
+DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
+DATABASE_URL set BEFORE any world_engine import), plus one stdlib-`ast`
+walk of `src/`. Every path is driven through its REAL function. Zero
+outcomes in any assertion is a FAIL, never a vacuous pass.
+
+Fixture: zone Z with active child C (visitable), visitable V; a player P at
+V; an NPC N at V; a creator user.
+
+Three assertions:
+  a. Each placement path refuses Z and accepts C, and a refusal writes
+     nothing:
+       travel            `play_stream._perform_travel`  -> `zone_destination`
+       npc_move          `mutations._mutation_apply_npc_move` -> message
+       PC creation       `routes/creator._validate_pc_creation` -> 409
+       fiche, character  `crud/entities._build_extension_kwargs` -> 409
+       fiche, item       `crud/entities._build_extension_kwargs` -> 409
+       schedule          `writes/config.write_npc_schedule` -> `ValueError`
+       detail            `crud/locations.create_discoverable_detail` -> 409
+     A fiche save whose `current_location_id` is UNCHANGED and already Z is
+     accepted (existing data is reported, never re-judged).
+  b. The NPC batch vocabulary (`npc_group_author.resolve_vocabulary`) rooted
+     on Z offers C and not Z.
+  c. P1's reactivation condition, structurally: the sites that assign
+     `character.current_location_id` (an attribute assignment, or a
+     `Character(...)` keyword) are exactly `writes/characters.py::
+     write_character_location`, `cockpit/play_stream.py::_perform_travel`
+     and `cockpit/routes/creator.py::create_player_character`. A seventh
+     site fails here; the registry field path (`crud/entities.py`) is held
+     by (a).
+
+Named mutations: delete the `require_visitable` call in `_perform_travel`
+-> (a) travel; delete `_require_placement_visitable(...)` in
+`_build_extension_kwargs` -> (a) fiche; drop the `is_zone` filter in
+`resolve_vocabulary` -> (b); add `char.current_location_id = x` to any other
+function -> (c).
+"""
+from __future__ import annotations
+
+import ast
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
+
+KNOWN_LOCATION_WRITERS = {
+    "world_engine/writes/characters.py::write_character_location",
+    "world_engine/cockpit/play_stream.py::_perform_travel",
+    "world_engine/cockpit/routes/creator.py::create_player_character",
+}
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
+def _seed(session) -> dict[str, str]:
+    from world_engine.models import Character, Entity, Location, User, World
+
+    world = World(name="Zone Placement", is_active=True)
+    session.add(world)
+    session.commit()
+    ids = {"world": world.id}
+    for label, parent in (("Z", None), ("C", "Z"), ("V", None)):
+        entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
+        session.add(entity)
+        session.flush()
+        session.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
+        session.commit()
+        ids[label] = entity.id
+    user = User(name="creator", role="creator")
+    session.add(user)
+    session.commit()
+    for label, ctype in (("P", "player"), ("N", "npc")):
+        entity = Entity(world_id=world.id, type="character", name=f"Être {label}")
+        session.add(entity)
+        session.flush()
+        session.add(Character(
+            id=entity.id, world_id=world.id, character_type=ctype,
+            user_id=user.id if ctype == "player" else None, current_location_id=ids["V"],
+        ))
+        session.commit()
+        ids[label] = entity.id
+    return ids
+
+
+def _location_of(session, character_id: str) -> str:
+    from world_engine.models import Character
+
+    session.expire_all()
+    return session.get(Character, character_id).current_location_id
+
+
+def _expect_http(label: str, fn, code: int = 409) -> int:
+    from fastapi import HTTPException
+
+    try:
+        fn()
+    except HTTPException as exc:
+        if exc.status_code != code:
+            fail(f"(a) {label}: HTTP {exc.status_code}, expected {code}")
+        return 1
+    fail(f"(a) {label}: a zone was accepted")
+    return 0
+
+
+def _accepts(label: str, fn) -> int:
+    try:
+        fn()
+    except Exception as exc:  # noqa: BLE001 -- any refusal of a visitable place is the failure
+        fail(f"(a) {label}: a visitable location was refused ({exc})")
+        return 0
+    return 1
+
+
+def check_a_paths(session, ids) -> None:
+    from world_engine.cockpit.crud.entities import _build_extension_kwargs
+    from world_engine.cockpit.crud.locations import DiscoverableDetailBody, create_discoverable_detail
+    from world_engine.cockpit.mutations import _mutation_apply_npc_move
+    from world_engine.cockpit.play_stream import _perform_travel
+    from world_engine.cockpit.routes.creator import PlayerCharacterCreateBody, _validate_pc_creation
+    from world_engine.models import Character
+    from world_engine.writes.config import write_npc_schedule
+
+    n = 0
+    result = _perform_travel(ids["P"], ids["Z"], session)
+    if result.get("status") != "zone_destination" or _location_of(session, ids["P"]) != ids["V"]:
+        fail(f"(a) travel into a zone: {result}")
+    else:
+        n += 1
+    result = _perform_travel(ids["P"], ids["C"], session)
+    n += 1 if result.get("status") == "ok" and _location_of(session, ids["P"]) == ids["C"] else 0
+
+    mut = SimpleNamespace(id="check-mut", world_id=ids["world"])
+    message = _mutation_apply_npc_move(mut, {"npc_id": ids["N"], "from_location_id": ids["V"],
+                                            "to_location_id": ids["Z"]}, session)
+    session.rollback()
+    if not message or _location_of(session, ids["N"]) != ids["V"]:
+        fail(f"(a) npc_move into a zone returned {message!r}")
+    else:
+        n += 1
+    message = _mutation_apply_npc_move(mut, {"npc_id": ids["N"], "from_location_id": ids["V"],
+                                            "to_location_id": ids["C"]}, session)
+    session.commit()
+    n += 1 if message is None and _location_of(session, ids["N"]) == ids["C"] else 0
+
+    n += _expect_http("PC creation", lambda: _validate_pc_creation(
+        PlayerCharacterCreateBody(name="Nouveau", current_location_id=ids["Z"]), session))
+    n += _accepts("PC creation", lambda: _validate_pc_creation(
+        PlayerCharacterCreateBody(name="Nouveau", current_location_id=ids["C"]), session))
+
+    npc_row = session.get(Character, ids["N"])
+    n += _expect_http("fiche, character", lambda: _build_extension_kwargs(
+        session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=npc_row))
+    n += _accepts("fiche, character", lambda: _build_extension_kwargs(
+        session, "character", {"current_location_id": ids["V"]}, present_only=True, current=npc_row))
+    n += _expect_http("fiche, item", lambda: _build_extension_kwargs(
+        session, "item", {"name": "x", "location_id": ids["Z"]}))
+    n += _accepts("fiche, item", lambda: _build_extension_kwargs(
+        session, "item", {"name": "x", "location_id": ids["C"]}))
+    already = SimpleNamespace(current_location_id=ids["Z"])
+    n += _accepts("fiche save with an unchanged zone", lambda: _build_extension_kwargs(
+        session, "character", {"current_location_id": ids["Z"]}, present_only=True, current=already))
+
+    try:
+        write_npc_schedule(session, world_id=ids["world"], npc_id=ids["N"],
+                           rows=[{"phase": "matin", "location_id": ids["Z"]}], changed_by="check")
+    except ValueError:
+        n += 1
+    else:
+        fail("(a) schedule: a zone was accepted")
+    session.rollback()
+    n += _accepts("schedule", lambda: write_npc_schedule(
+        session, world_id=ids["world"], npc_id=ids["N"],
+        rows=[{"phase": "matin", "location_id": ids["C"]}], changed_by="check"))
+    session.rollback()
+
+    body = DiscoverableDetailBody(world_id=ids["world"], subject="s", content="c")
+    n += _expect_http("detail", lambda: create_discoverable_detail(ids["Z"], body, session))
+    n += _accepts("detail", lambda: create_discoverable_detail(ids["C"], body, session))
+    if n != 15:
+        fail(f"(a) expected 15 outcomes (7 refusals, 8 acceptances), got {n}")
+    COUNTS["a"] = n
+
+
+def check_b_vocabulary(session, ids) -> None:
+    from world_engine.npc_group_author import resolve_vocabulary
+
+    vocab = resolve_vocabulary(session, ids["Z"])
+    offered = set(vocab["expanded_location_ids"]) | {loc["id"] for loc in vocab["locations"]}
+    if ids["Z"] in offered:
+        fail("(b) the NPC batch vocabulary offers the zone itself")
+    if ids["C"] not in offered:
+        fail("(b) the NPC batch vocabulary lost the zone's visitable child")
+    COUNTS["b"] = len(offered)
+
+
+def _writes_location(node: ast.AST) -> bool:
+    if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
+        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
+        return any(isinstance(t, ast.Attribute) and t.attr == "current_location_id" for t in targets)
+    if isinstance(node, ast.Call):
+        callee = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
+        return callee == "Character" and any(k.arg == "current_location_id" for k in node.keywords)
+    return False
+
+
+def check_c_sites() -> None:
+    found: set[str] = set()
+    for path in sorted((SRC / "world_engine").rglob("*.py")):
+        tree = ast.parse(path.read_text(encoding="utf-8"))
+        rel = path.relative_to(SRC).as_posix()
+        for fn in ast.walk(tree):
+            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
+                continue
+            if any(_writes_location(node) for node in ast.walk(fn)):
+                found.add(f"{rel}::{fn.name}")
+    for site in sorted(found - KNOWN_LOCATION_WRITERS):
+        fail(f"(c) a new current_location_id write site, unguarded until named here: {site}")
+    for site in sorted(KNOWN_LOCATION_WRITERS - found):
+        fail(f"(c) a known write site no longer writes current_location_id: {site}")
+    COUNTS["c"] = len(found)
+
+
+def main() -> int:
+    engine = _fresh_engine()
+    from sqlmodel import Session as DbSession
+
+    with DbSession(engine) as session:
+        ids = _seed(session)
+        check_a_paths(session, ids)
+        check_b_vocabulary(session, ids)
+    check_c_sites()
+
+    for key in ("a", "b", "c"):
+        if not COUNTS.get(key):
+            fail(f"({key}) vacuous-proof: zero outcomes examined")
+
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print(
+        "PASS: zone_placement — "
+        f"(a) every placement path refuses a zone [{COUNTS['a']} outcomes], "
+        f"(b) NPC batch vocabulary visitable only [{COUNTS['b']}], "
+        f"(c) {COUNTS['c']} current_location_id write sites, all named"
+    )
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Moving anything that already sits in a zone (D reports it; Nia corrects through the fiche).
- Promotion (C): a location gaining a child is not refused, it is promoted.
- Funnelling every location write through `write_character_location` (P2, rejected; reactivates on a seventh site, which `zone_placement.py` (c) catches).
- Filtering the fiche's location dropdowns to visitable places (the server refuses; a UI filter is not asked).
- Any change to `_location_neighbours` or the door-gated travel: neither can reach a zone (R-12).

## Invariants to defend

- **Creator-CRUD location edits close gatherings** (CLAUDE.md): untouched — a refused edit writes nothing, an accepted one runs the existing recipe.
- **The lore tool stays open on zones** (R-17): no guard is added to `lore_write_apply`, and its entity creator places nothing.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of Scope IN does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `function_length.py` fails on `_perform_travel` or `write_npc_schedule`.

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
- `zone_placement.py` → `PASS: zone_placement — (a) every placement path refuses a zone [15 outcomes], (b) NPC batch vocabulary visitable only [1], (c) 3 current_location_id write sites, all named`.
- `spatial_door_travel.py`, `origin_guard.py`, `function_length.py`, `single_canon_write.py`, `claude_md_contract.py`, `decisions_index.py` → `PASS`.
- The four named mutations failed as stated.
- `corpus_gate.py` → 131/131.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `NOTHING IS PLACED IN A ZONE (TICKET-0101) -- ONE GUARD AT EVERY PLACEMENT WRITE (BRIEF-0101-b, no schema change)` and the CLAUDE.md bullet — in the diff.
