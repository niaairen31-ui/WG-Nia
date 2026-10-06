<!-- slug: master-lock -->
# BRIEF 0107-B — "A skill may require a master: not held until taught, not rolled until then"

Lot: LOT-0107-npc-skills-masters.md (authoritative on conflict)
Depends on: BRIEF-0107-A
Commit header for decisions: `(BRIEF-0107-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0107`, on the tree BRIEF-0107-A left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/schema_version.py:15` -> `"v2.16"`; `SkillDefinition.requires_master` and `Skill.taught_by_id` exist (`models/canon.py`).
- `src/world_engine/skill_access.py:26` -> `from .models import Skill, SkillDefinition`; `:53` -> `def player_skill(`; `:59` -> `    row = _definition_row(db, player_id, definition.id) or _base_row(db, player_id, definition.base_domain)`.
- `src/world_engine/cockpit/play_physical.py:176` -> `    verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)`; `:183` -> the line beginning `    progress = record_roll(world_id=ctx.world_id,`; `:342` -> `    if resolved_base_domain != "perception" or opposed_npc_id is not None:`; `wc -l` -> 966.
- `src/world_engine/cockpit/play_stream.py:32` -> `from ..zone_rules import ZoneRefusal, require_visitable`; `:243` -> the `_mj_user_physical` docstring « BRIEF-11: `verdict_band` injects the verbatim resolution rubric. ».
- `src/world_engine/cockpit/crud/skills.py:105` -> the `"points_to_next": points_to_next(s.rank, ladder, …)` line of `_skill_dict`; `:152` -> `@router.get("/skills/player-characters")`; `:408` -> `class SkillDefinitionWriteBody(RankPointsBody):`; `:454` -> `    pc_ids = db.exec(`; `:501` -> `    domain_changed = body.base_domain != definition.base_domain`; `wc -l` -> 551.
- `src/world_engine/cockpit/routes/creator.py:618` -> `def _pc_custom_skill_defs(world_id: str, db: Session) -> list[SkillDefinition]:`.
- `CLAUDE.md:313` -> `- **A new \`skill_definition\` backfills a default-rank \`skill\` row onto every`; `wc -c` -> 37 693.
- `writes.write_skill_row` exists; no `/api/skills/learnable` route and no `POST /api/skills` route.

## Facts carried

### R-02 — every PC holds every skill [M]
Opened: `src/world_engine/cockpit/crud/skills.py:454-465`
(`create_skill_definition` backfills every PC), `:501-517`
(`update_skill_definition`); `routes/creator.py:618-621`
(`_pc_custom_skill_defs`: every definition); `CLAUDE.md:313-317` (« the
catalogue<->PC alignment is never partial »).
Consequence: A2 restricts the backfill and the seed to open skills; turning
the flag off backfills; the CLAUDE.md line is rewritten in B.

### R-03 — Play's row lookup and opposition [M]
Opened: `src/world_engine/cockpit/play_physical.py:62-150` (the arbiter is
handed the whole catalogue; `_judge_and_record_domain`), `:152-215`
(`_say_physical_resolve_verdict`: base row, else definition row, else
« Defensive fallback » to the base row `:184`; opposition from
`physical_tier` `:206`); `wc -l` → 998 of 1000.
Consequence: the lookup and the opposition move to `skill_access.py`
(reads only; the file falls to 966), which gains the lock in B.

### R-04 — day steps roll base domains [M]
Opened: `src/world_engine/day_plan.py` (`_validate_step`: a step's
`domain` is a base domain); `src/world_engine/day_resolve.py:165-180`.
Consequence: the lock is Play-only.

### R-07 — the MJ message of a physical turn [M]
Opened: `src/world_engine/cockpit/play_stream.py:239-262`
(`_mj_user_physical`: the verdict block keyed on `verdict_band`, a
`search_rubric` appended); `play_physical.py:296-357` (scene-state writes
on `failure`/`success` only), `:360-424` (`_say_physical_discovery`).
Consequence: a `locked` band moves no scene state; discovery returns the
locked rubric; the MJ message drops the verdict block for it.

### R-10 — the checks the lot passes [M]
Opened: E3; `single_canon_write.py` and `canon_write_policy.txt`;
`page_contract.py` (« Ajouter une compétence » must appear once — the NPC
section is titled « Compétences à donner »); `creation_island.py`;
`effect_self_write.py`; `claude_md_contract.py` (CLAUDE.md 37 647 of 38
000 characters); `skill_progression.py` (TICKET-0106's A2 rebuilds the
skill tables from the current models, so it keeps passing).

## Contracts

### C-02 — the rows a roll reads (`skill_access.py`)
Produced by: BRIEF-0107-A (lock: B)   Consumed by: Play
`RolledSkill(base_domain, row, definition, locked=False)`.
`player_skill(db, player_id, token, definitions_by_name)`: a base domain →
the base row; a definition → its row, else (not `requires_master`) the base
row for its domain; else (B) `locked=True`, row None.
`opposition_modifier(db, npc_id, base_domain, definition) -> int`: the
NPC's row for the definition, else its base row, else `DEFAULT_RANK`;
through `rank_modifier`. (B) `LOCKED_BAND = "locked"`,
`locked_verdict(name) -> Verdict` (dice (0, 0), total 0, `domain` = the
name), `locked_rubric(name) -> str`.

### C-05 — the lock in the catalogue (A2)
Produced by: BRIEF-0107-B   Consumed by: C
`SkillDefinitionWriteBody.requires_master: bool = False`, served by
`_skill_definition_dict`. Create: open → `_backfill_open_skill` (every PC
lacking it, `DEFAULT_RANK`, through C-03); master → nothing. Update: off →
backfill; on → rows kept. `_pc_custom_skill_defs` lists open definitions
only.

### C-06 — Play's locked turn (B1)
Produced by: BRIEF-0107-B   Consumed by: the MJ
`_say_physical_resolve_verdict`: when locked, `locked_verdict(token)`, no
`resolve_physical`, no `record_roll` (`progress` None).
`_say_physical_discovery` returns `locked_rubric(verdict.domain)` first.
`_mj_user_physical` with `LOCKED_BAND`: context, place, action, NPC
reaction, the rubric — no verdict block.

### C-07 — learning (C1)
Produced by: BRIEF-0107-B   Consumed by: C
`GET /api/skills/learnable?character_id=` → `[{domain,
skill_definition_id, name, requires_master, masters: [{id, name}]}]`: a
player's master skills he lacks; an NPC's missing base domains and
definitions. `POST /api/skills` body `{character_id, skill_definition_id |
domain, rank = 0, taught_by_id?}` → the row (C-08 shape) 201; 422 on a
character or definition outside the world, a teacher who is the learner or
not at Maître in that skill; 409 on a skill held. `GET /api/skills` rows
add `requires_master`, `taught_by_id`.

## Context

NPC rows exist and Play reads them through `skill_access` (A). Nia locked A2 (a skill may require a master), B1 (« impossible à lancer ») and C1 (taught by a Maître or granted by the creator, at Inexpérimenté). This brief puts the flag on the catalogue — a master skill backfills nobody and seeds no new PC — locks it in Play, and opens the two routes the fiche uses in C.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `skill_access.py`, adds `LOCKED_BAND`, `RolledSkill.locked`, the lock in `player_skill`, `locked_verdict` and `locked_rubric` (C-02);
   - in `play_physical.py`, rolls nothing for a locked skill, records no point, and returns the rubric from `_say_physical_discovery` (972 lines); in `play_stream.py`, `_mj_user_physical` drops the verdict block for `locked` (C-06);
   - in `crud/skills.py`, `requires_master` on the write body and the dict, `_backfill_open_skill` (through `write_skill_row`) on create and when the flag is turned off (C-05); `requires_master`/`taught_by_id` on sheet rows; `GET /api/skills/learnable`, `POST /api/skills`, `?character_type=` on the character list (C-07, C-08's route);
   - in `routes/creator.py`, `_pc_custom_skill_defs` lists open skills only;
   - rewrites CLAUDE.md's backfill invariant (open skills; the lock);
   - appends the decision entry above the footer;
   - adds B1-B4 to `npc_skills.py`.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(skills): a skill may require a master, locked in Play until taught (BRIEF-0107-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index fee3857..8069681 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -310,9 +310,11 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   no `change_history` snapshot): dependent PC `skill` rows then the
   definition, one transaction. The type-"Oui" modal is the sole safeguard —
   a named exception to "History is sacred", scoped to one row.
-- **A new `skill_definition` backfills a default-rank `skill` row onto every
+- **A new open `skill_definition` backfills a default-rank `skill` row onto every
   existing PC of its world, in the create's own transaction** — the
-  catalogue<->PC alignment is never partial. Renaming touches no `skill`
+  catalogue<->PC alignment of open skills is never partial. A `requires_master`
+  skill is held only once taught (`POST /api/skills`), and `skill_access` locks
+  it in Play until then. Renaming touches no `skill`
   row (FK-by-id); re-basing (`base_domain` change) updates `domain` on
   every dependent `skill` row in the same write.
 - **A `skill_definition.name` can never equal a base-domain literal**
diff --git a/src/world_engine/cockpit/crud/skills.py b/src/world_engine/cockpit/crud/skills.py
index 7e7bab8..d4fce1d 100644
--- a/src/world_engine/cockpit/crud/skills.py
+++ b/src/world_engine/cockpit/crud/skills.py
@@ -53,7 +53,7 @@ from ...models import (
 )
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
-from ...skill_ranks import DEFAULT_RANK, RANK_POINTS_COLUMNS, RANKS, RankStep, points_to_next, skill_owners, world_ladder
+from ...skill_ranks import DEFAULT_RANK, MAX_RANK, RANK_POINTS_COLUMNS, RANKS, RankStep, points_to_next, skill_owners, world_ladder
 from ...tick_normalize import _EVENT_TYPES
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -80,6 +80,7 @@ from ...writes import (
     write_relation,
     upsert_skill_rank,
     write_skill_rank,
+    write_skill_row,
 )
 
 from ._router import router
@@ -103,6 +104,8 @@ def _skill_dict(
         "rank_label": ladder[s.rank].label,
         "xp": s.xp,
         "points_to_next": points_to_next(s.rank, ladder, system=system, definition=definition),
+        "requires_master": bool(definition.requires_master) if definition else False,
+        "taught_by_id": s.taught_by_id,
         "change_history": s.change_history,
         "updated_at": _iso(s.updated_at),
     }
@@ -150,22 +153,116 @@ def update_skill_ranks(body: SkillRanksBody, db: DbSession = Depends(get_session
 
 
 @router.get("/skills/player-characters")
-def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[dict]:
-    """Player characters (`character_type = 'player'`), for the Fiche selector."""
+def list_skill_player_characters(
+    character_type: str = Query("player"), db: DbSession = Depends(get_session),
+) -> list[dict]:
+    """The active world's characters of one type (`player` by default, or
+    `npc` since TICKET-0107), for the Fiche selector."""
+    if character_type not in ("player", "npc"):
+        raise HTTPException(422, "character_type must be 'player' or 'npc'")
     rows = db.exec(
         select(Entity, Character)
         .join(Character, Character.id == Entity.id)
-        .where(Character.character_type == "player")
+        .where(Character.character_type == character_type)
         .where(Character.world_id == _world_id(db))
         .order_by(Entity.name)
     ).all()
     return [{"id": e.id, "name": e.name} for e, _ in rows]
 
 
+def _masters(db: DbSession, world_id: str, *, definition_id: Optional[str], domain: Optional[str]) -> list[dict]:
+    """The characters of the world at Maître in one skill (C1)."""
+    stmt = (
+        select(Entity)
+        .join(Skill, Skill.character_id == Entity.id)
+        .where(Entity.world_id == world_id, Skill.rank == MAX_RANK)
+    )
+    if definition_id is not None:
+        stmt = stmt.where(Skill.skill_definition_id == definition_id)
+    else:
+        stmt = stmt.where(Skill.domain == domain, Skill.skill_definition_id.is_(None))
+    return [{"id": e.id, "name": e.name} for e in db.exec(stmt.order_by(Entity.name)).all()]
+
+
+@router.get("/skills/learnable")
+def list_learnable_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
+    """The skills a character does not hold and may be given (TICKET-0107):
+    for a player, the `requires_master` skills he was never taught (every
+    open skill is held already); for an NPC, every base domain and every
+    definition it holds no row for. Each with the masters who could teach
+    it."""
+    entity = _get_entity(db, character_id)
+    character = db.get(Character, character_id)
+    if character is None:
+        raise HTTPException(422, f"{character_id!r} is not a character")
+    held = db.exec(select(Skill).where(Skill.character_id == character_id)).all()
+    held_definitions = {r.skill_definition_id for r in held if r.skill_definition_id}
+    held_domains = {r.domain for r in held if r.skill_definition_id is None}
+    out: list[dict] = []
+    if character.character_type != "player":
+        for domain in SKILL_DOMAINS:
+            if domain not in held_domains:
+                out.append({"domain": domain, "skill_definition_id": None, "name": domain, "requires_master": False,
+                            "masters": _masters(db, entity.world_id, definition_id=None, domain=domain)})
+    for definition in db.exec(select(SkillDefinition).where(SkillDefinition.world_id == entity.world_id)
+                              .order_by(SkillDefinition.name)).all():
+        if definition.id in held_definitions:
+            continue
+        if character.character_type == "player" and not definition.requires_master:
+            continue
+        out.append({"domain": definition.base_domain, "skill_definition_id": definition.id, "name": definition.name,
+                    "requires_master": definition.requires_master,
+                    "masters": _masters(db, entity.world_id, definition_id=definition.id, domain=None)})
+    return out
+
+
+class SkillGrantBody(BaseModel):
+    character_id: str
+    skill_definition_id: Optional[str] = None
+    domain: Optional[str] = None
+    rank: int = 0
+    taught_by_id: Optional[str] = None
+
+
+@router.post("/skills", status_code=201)
+def grant_skill(body: SkillGrantBody, db: DbSession = Depends(get_session)) -> dict:
+    """Creator grant of one skill row (TICKET-0107, C1): a skill learned, or
+    an NPC's skill. `taught_by_id`, when given, must be another character of
+    the world at Maître in that skill (422 otherwise); none = granted without
+    a master, the creator's bypass. 409 when the character holds it already."""
+    world_id = _world_id(db)
+    entity = _get_entity(db, body.character_id)
+    if entity.world_id != world_id or db.get(Character, body.character_id) is None:
+        raise HTTPException(422, "character_id must be a character of the active world")
+    if body.skill_definition_id is not None:
+        definition = db.get(SkillDefinition, body.skill_definition_id)
+        if definition is None or definition.world_id != world_id:
+            raise HTTPException(422, "skill_definition_id must be a skill of the active world")
+    if body.taught_by_id is not None:
+        masters = _masters(db, world_id, definition_id=body.skill_definition_id, domain=body.domain)
+        if body.taught_by_id == body.character_id or body.taught_by_id not in {m["id"] for m in masters}:
+            raise HTTPException(422, "taught_by_id must be another character at Maître in this skill")
+    held = select(Skill).where(Skill.character_id == body.character_id)
+    held = (held.where(Skill.skill_definition_id == body.skill_definition_id) if body.skill_definition_id
+            else held.where(Skill.domain == body.domain, Skill.skill_definition_id.is_(None)))
+    if db.exec(held).first() is not None:
+        raise HTTPException(409, "This character already holds this skill")
+    try:
+        row = write_skill_row(db, character_id=body.character_id, rank=body.rank, domain=body.domain,
+                              skill_definition_id=body.skill_definition_id, taught_by_id=body.taught_by_id)
+    except ValueError as exc:
+        raise HTTPException(422, str(exc))
+    db.commit()
+    db.refresh(row)
+    system, definition = skill_owners(db, row.skill_definition_id)
+    return _skill_dict(row, world_ladder(db, world_id), definition, system)
+
+
 @router.get("/skills")
 def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
-    """A player character's skill sheet, in fixed domain order, each row with
-    its rank's name and the points it needs to leave that rank."""
+    """A character's skill sheet (a player's, or an NPC's since TICKET-0107),
+    in fixed domain order, each row with its rank's name and the points it
+    needs to leave that rank."""
     entity = _get_entity(db, character_id)
     ladder = world_ladder(db, entity.world_id)
     rows = db.exec(
@@ -389,6 +486,7 @@ def _skill_definition_dict(d: SkillDefinition) -> dict:
         "base_domain": d.base_domain,
         "system_id": d.system_id,
         "description": d.description,
+        "requires_master": d.requires_master,
         **_rank_points(d),
         "updated_at": _iso(d.updated_at),
     }
@@ -410,6 +508,23 @@ class SkillDefinitionWriteBody(RankPointsBody):
     base_domain: str
     system_id: Optional[str] = None
     description: Optional[str] = None
+    # TICKET-0107 (A2): learned only from a master -- no player character
+    # holds a row for it until taught.
+    requires_master: bool = False
+
+
+def _backfill_open_skill(db: DbSession, definition: SkillDefinition) -> None:
+    """A skill open to all (`requires_master` false): every player character
+    of its world that lacks a row for it gets one at `DEFAULT_RANK`, through
+    `write_skill_row` -- the catalogue<->PC alignment of open skills."""
+    holders = set(db.exec(select(Skill.character_id).where(Skill.skill_definition_id == definition.id)).all())
+    for character_id in db.exec(
+        select(Character.id)
+        .where(Character.world_id == definition.world_id)
+        .where(Character.character_type == "player")
+    ).all():
+        if character_id not in holders:
+            write_skill_row(db, character_id=character_id, skill_definition_id=definition.id, rank=DEFAULT_RANK)
 
 
 @router.post("/skill-definitions", status_code=201)
@@ -418,10 +533,11 @@ def create_skill_definition(
 ) -> dict:
     """Add a custom skill to the active world's catalogue (D2-backfill-yes).
 
-    Backfills: inserts a `skill` row at `DEFAULT_RANK` (Initié) for this definition onto every
-    existing player character of the world, in the SAME transaction, so the
-    catalogue<->PC alignment that makes the arbiter lookup total never
-    lapses (BRIEF-55's invariant — every PC always has every world skill).
+    Backfills, for a skill open to all, a `skill` row at `DEFAULT_RANK`
+    (Initié) onto every existing player character of the world, in the SAME
+    transaction (`_backfill_open_skill`): every PC always holds every open
+    skill. A `requires_master` skill backfills nothing -- it is held only
+    once taught (TICKET-0107, A2).
     """
     world_id = _world_id(db)
     name = body.name.strip()
@@ -442,6 +558,7 @@ def create_skill_definition(
         base_domain=body.base_domain,
         system_id=body.system_id,
         description=body.description,
+        requires_master=body.requires_master,
     )
     _set_rank_points(definition, body)
     db.add(definition)
@@ -451,18 +568,8 @@ def create_skill_definition(
         db.rollback()
         raise HTTPException(409, f"A skill named {name!r} already exists in this world")
 
-    pc_ids = db.exec(
-        select(Character.id)
-        .where(Character.world_id == world_id)
-        .where(Character.character_type == "player")
-    ).all()
-    for character_id in pc_ids:
-        db.add(Skill(
-            character_id=character_id,
-            domain=definition.base_domain,
-            rank=DEFAULT_RANK,
-            skill_definition_id=definition.id,
-        ))
+    if not definition.requires_master:
+        _backfill_open_skill(db, definition)
 
     db.commit()
     db.refresh(definition)
@@ -482,6 +589,8 @@ def update_skill_definition(
     resolution for every existing PC `skill` row referencing this
     definition — also updates their `domain` column so the 2d6 bands and
     the base-domain CHECK stay consistent (mirrors the create-time seed).
+    Turning `requires_master` off backfills the open skill onto every PC
+    lacking it; turning it on keeps every row already held (TICKET-0107).
     """
     definition = db.get(SkillDefinition, definition_id)
     if definition is None or definition.world_id != _world_id(db):
@@ -499,6 +608,8 @@ def update_skill_definition(
             raise HTTPException(422, "system_id must reference a skill system of the active world")
 
     domain_changed = body.base_domain != definition.base_domain
+    opened = definition.requires_master and not body.requires_master
+    definition.requires_master = body.requires_master
     definition.name = name
     definition.base_domain = body.base_domain
     definition.system_id = body.system_id
@@ -515,6 +626,9 @@ def update_skill_definition(
             skill.domain = body.base_domain
             skill.updated_at = datetime.now(UTC)
             db.add(skill)
+    if opened:
+        db.flush()
+        _backfill_open_skill(db, definition)
 
     try:
         db.commit()
diff --git a/src/world_engine/cockpit/play_physical.py b/src/world_engine/cockpit/play_physical.py
index 12e927d..d461306 100644
--- a/src/world_engine/cockpit/play_physical.py
+++ b/src/world_engine/cockpit/play_physical.py
@@ -173,14 +173,18 @@ def _say_physical_resolve_verdict(
         if opposed_entity is not None:
             npc_tier = skill_access.opposition_modifier(db, opposed_npc_id, resolved_base_domain, rolled.definition)
 
-    verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
+    if rolled.locked:  # B1: a skill never taught is not rolled
+        verdict = skill_access.locked_verdict(domain)
+    else:
+        verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
     _log.info(
         "Physical verdict: domain=%s dice=%s modifier=%d total=%d band=%s "
         "(player_tier=%d, npc_tier=%d, opposed=%s)",
         verdict.domain, verdict.dice, verdict.modifier, verdict.total,
         verdict.band, player_tier, npc_tier, opposed_npc_id or "none",
     )
-    progress = record_roll(world_id=ctx.world_id, conversation_id=ctx.conv_id, skill_id=skill_row.id if skill_row else None, band=verdict.band)
+    progress = None if rolled.locked else record_roll(
+        world_id=ctx.world_id, conversation_id=ctx.conv_id, skill_id=skill_row.id if skill_row else None, band=verdict.band)
     verdict_sse_line = f"data: {json.dumps({'verdict': {'domain': verdict.domain, 'dice': list(verdict.dice), 'modifier': verdict.modifier, 'total': verdict.total, 'band': verdict.band, 'progress': progress}})}\n\n"
     return resolved_base_domain, verdict, opposed_entity, verdict_sse_line
 
@@ -339,6 +343,8 @@ def _say_physical_discovery(
     content ONLY after selection.
     """
     db = ctx.db
+    if verdict.band == skill_access.LOCKED_BAND:
+        return skill_access.locked_rubric(verdict.domain)
     if resolved_base_domain != "perception" or opposed_npc_id is not None:
         return None
 
diff --git a/src/world_engine/cockpit/play_stream.py b/src/world_engine/cockpit/play_stream.py
index c32e2f3..8d18a55 100644
--- a/src/world_engine/cockpit/play_stream.py
+++ b/src/world_engine/cockpit/play_stream.py
@@ -29,6 +29,7 @@ from ..models import (
     ProposedMutation,
     PromptTemplate,
 )
+from ..skill_access import LOCKED_BAND
 from ..zone_rules import ZoneRefusal, require_visitable
 from .play import (
     ResponseMode,
@@ -240,12 +241,20 @@ def _mj_user_physical(
     context_block: str, inventory_block: str, location_name: str, player_line: str,
     npc_name: str, npc_reply: str, verdict_band: Optional[str], search_rubric: Optional[str],
 ) -> str:
-    """BRIEF-11: `verdict_band` injects the verbatim resolution rubric."""
+    """BRIEF-11: `verdict_band` injects the verbatim resolution rubric. A
+    locked skill (TICKET-0107, B1) rolled nothing: its rubric, carried in
+    `search_rubric`, replaces the verdict block."""
     band = verdict_band or "failure"
     npc_reaction_block = (
         f"{npc_name} réagit :\n{npc_reply}\n\n" if npc_reply else ""
     )
     search_rubric_block = f"\n{search_rubric}\n" if search_rubric else ""
+    if band == LOCKED_BAND:
+        return (
+            f"{context_block}{inventory_block}Lieu : « {location_name} ».\n"
+            f"Mode : résolution physique.\n\nAction du joueur :\n{player_line}\n\n"
+            f"{npc_reaction_block}{search_rubric_block}\nNarration MJ :\n/no_think"
+        )
     return (
         f"{context_block}"
         f"{inventory_block}"
diff --git a/src/world_engine/cockpit/routes/creator.py b/src/world_engine/cockpit/routes/creator.py
index 0e04993..33a8963 100644
--- a/src/world_engine/cockpit/routes/creator.py
+++ b/src/world_engine/cockpit/routes/creator.py
@@ -616,8 +616,13 @@ def _validate_pc_creation(body: "PlayerCharacterCreateBody", db: Session) -> tup
 
 
 def _pc_custom_skill_defs(world_id: str, db: Session) -> list[SkillDefinition]:
+    """The skills a new PC holds: every definition open to all -- a
+    `requires_master` one is held only once taught (TICKET-0107, A2)."""
     return db.exec(
-        select(SkillDefinition).where(SkillDefinition.world_id == world_id)
+        select(SkillDefinition).where(
+            SkillDefinition.world_id == world_id,
+            SkillDefinition.requires_master == False,  # noqa: E712
+        )
     ).all()
 
 
diff --git a/src/world_engine/skill_access.py b/src/world_engine/skill_access.py
index 4fb70b9..fc3f296 100644
--- a/src/world_engine/skill_access.py
+++ b/src/world_engine/skill_access.py
@@ -7,7 +7,9 @@ The player's row: the arbiter named a base domain or a skill definition of
 the world. A base domain reads the player's base row for it
 (`skill_definition_id IS NULL`, CLAUDE.md « Custom skill lookups »). A
 definition reads the player's row for it; when the player has none, the
-roll falls back to his base row for the definition's domain.
+roll falls back to his base row for the definition's domain -- unless the
+definition `requires_master` (TICKET-0107, BRIEF-0107-B, A2/B1): then the
+skill is LOCKED, no row is rolled, and Play rolls no dice (`LOCKED_BAND`).
 
 The opposing NPC's modifier (D1): its row for the same definition, else its
 base row for the roll's base domain, else the rank every character holds in
@@ -24,14 +26,20 @@ from typing import Optional
 from sqlmodel import Session, select
 
 from .models import Skill, SkillDefinition
+from .resolution import Verdict
 from .skill_ranks import DEFAULT_RANK, rank_modifier
 
 
+# The verdict band of a locked skill: no dice, no point (B1).
+LOCKED_BAND = "locked"
+
+
 @dataclass(frozen=True)
 class RolledSkill:
     base_domain: str  # what bands, discovery and the dice key off
-    row: Optional[Skill]  # the player's row rolled; None when he has none at all
+    row: Optional[Skill]  # the player's row rolled; None when he has none at all, or locked
     definition: Optional[SkillDefinition]  # set when the arbiter named a definition
+    locked: bool = False  # a requires_master definition the player was never taught
 
 
 def _base_row(db: Session, character_id: str, domain: str) -> Optional[Skill]:
@@ -56,7 +64,10 @@ def player_skill(db: Session, player_id: str, token: str, definitions_by_name: d
     definition = definitions_by_name.get(token)
     if definition is None:
         return RolledSkill(base_domain=token, row=_base_row(db, player_id, token), definition=None)
-    row = _definition_row(db, player_id, definition.id) or _base_row(db, player_id, definition.base_domain)
+    row = _definition_row(db, player_id, definition.id)
+    if row is None and definition.requires_master:
+        return RolledSkill(base_domain=definition.base_domain, row=None, definition=definition, locked=True)
+    row = row or _base_row(db, player_id, definition.base_domain)
     return RolledSkill(base_domain=definition.base_domain, row=row, definition=definition)
 
 
@@ -66,3 +77,19 @@ def opposition_modifier(db: Session, npc_id: str, base_domain: str, definition:
     if row is None:
         row = _base_row(db, npc_id, base_domain)
     return rank_modifier(row.rank if row is not None else DEFAULT_RANK)
+
+
+def locked_verdict(skill_name: str) -> Verdict:
+    """The verdict of a locked skill (B1): no dice were rolled. `domain`
+    carries the skill's name, for the verdict event and the MJ rubric."""
+    return Verdict(domain=skill_name, dice=(0, 0), modifier=0, total=0, band=LOCKED_BAND)
+
+
+def locked_rubric(skill_name: str) -> str:
+    """The MJ's instruction for a locked skill: the attempt cannot be made."""
+    return (
+        "[COMPÉTENCE NON MAÎTRISÉE]\n"
+        f"Le personnage n'a jamais appris « {skill_name} » : personne ne la lui a enseignée.\n"
+        "Il ne peut pas tenter cette action. Narre qu'il en est incapable (il hésite, ne sait\n"
+        "par où commencer, renonce) ; l'action n'a ni réussite ni échec, et rien ne change autour de lui."
+    )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index c735e76..9f42264 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17996,6 +17996,34 @@ and `skill.taught_by_id` are added here, read from the next brief on.
 same reading as an absent row, through many more writes. Keeping
 `physical_tier` beside the rows: two sources for one modifier.
 
+
+## A SKILL MAY REQUIRE A MASTER (TICKET-0107) -- NOT HELD UNTIL TAUGHT, NOT ROLLED UNTIL THEN (BRIEF-0107-b, no schema change)
+
+**A2.** A skill definition may `require_master`. A player holds no row for
+it until taught: creating such a skill backfills nobody, a new PC is not
+seeded with it, and turning the flag on keeps every row already held.
+Turning it off backfills every PC lacking it -- open skills stay aligned
+with every PC.
+
+**B1.** In Play, the arbiter may still name a skill the player was never
+taught (the lexicon judges against the whole catalogue). `skill_access`
+then reports it locked: no fallback to the base domain, no dice, no point.
+The verdict band is `locked` (dice 0, the skill's name as its domain), the
+MJ receives `locked_rubric` in place of the verdict block, and no scene
+state moves. Play's sealed client prints the band as it prints any other.
+
+**C1.** `POST /api/skills` grants one row: taught by another character at
+Maître in that skill (`taught_by_id`, checked), or granted without a master
+-- the creator's bypass. `GET /api/skills/learnable` lists what a character
+may be given: for a player, the master skills he lacks; for an NPC, every
+skill and base domain it lacks; each with its masters. A skill learned
+starts where the UI sends it -- Inexpérimenté for « Apprendre ».
+
+**Rejected.** A2's alternative A1, locking every custom skill: Nia's world
+keeps open skills. B2, rolling the base domain for a locked skill:
+« impossible à lancer ». Learning through a conversation's proposal (C2):
+deferred to quests.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/npc_skills.py b/tooling/verify/checks/npc_skills.py
index 1007ac3..2efc0fd 100644
--- a/tooling/verify/checks/npc_skills.py
+++ b/tooling/verify/checks/npc_skills.py
@@ -38,6 +38,31 @@ A4 -- the carrure at creation (fixture and static). Creating a character
    (AST); `npc_agent.py` passes `carrure=`; `play_physical.py` calls
    `skill_access.opposition_modifier(` and `skill_access.player_skill(`.
 
+B1 -- the flag (BRIEF-0107-B, fixture, A2). `POST /api/skill-definitions`
+   with `requires_master` gives no player a row and serves the flag; without
+   it, every player gets one at `DEFAULT_RANK`. Turning the flag off
+   (`PUT`) backfills every player lacking the row; turning it on keeps every
+   row held. `_pc_custom_skill_defs` (a new PC's seed) lists no
+   `requires_master` definition.
+B2 -- the lock in Play (fixture, B1). `player_skill` on a `requires_master`
+   definition the player lacks is `locked`, row None, with no fallback to
+   the base row; on one he holds, it is that row. With a minimal turn
+   context, `_say_physical_resolve_verdict` on the locked skill returns the
+   band `locked`, dice (0, 0), the skill's name as `domain`, `progress`
+   None on the verdict event, and writes no `skill_progress` mutation.
+   `_say_physical_discovery` returns `locked_rubric`; `_mj_user_physical`
+   with the band `locked` carries the rubric and no « Résultat mécanique ».
+B3 -- learning (fixture, C1). `GET /api/skills/learnable` lists, for a
+   player, exactly the `requires_master` definitions he lacks, each with its
+   masters (characters at rank 5 in it); for an NPC, its missing base
+   domains and every definition it lacks. `POST /api/skills` with a master
+   writes the row at the given rank with `taught_by_id`; with a non-master,
+   or the learner as his own master, 422; a second time, 409; without a
+   master, the row with `taught_by_id` None; an NPC base domain at rank 4.
+   `GET /api/skills` serves `requires_master` and `taught_by_id`.
+B4 -- documentation (static). CLAUDE.md names `requires_master` and
+   `skill_access`'s lock.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -339,6 +364,153 @@ def check_a4(engine) -> None:
         fail("A4: play_physical.py does not read its rows through skill_access")
 
 
+# --- B1-B4 ---------------------------------------------------------------------
+
+def check_b1(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.crud.skills import (
+        SkillDefinitionWriteBody, create_skill_definition, update_skill_definition,
+    )
+    from world_engine.cockpit.routes.creator import _pc_custom_skill_defs
+    from world_engine.models import Skill
+    from world_engine.skill_ranks import DEFAULT_RANK
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+
+        def holders(definition_id: str) -> list:
+            return sorted((r.character_id, r.rank) for r in session.exec(
+                select(Skill).where(Skill.skill_definition_id == definition_id)).all())
+
+        locked = create_skill_definition(SkillDefinitionWriteBody(
+            name="Alchimie", base_domain="perception", requires_master=True), session)
+        if holders(locked["id"]) or locked.get("requires_master") is not True:
+            fail(f"B1: a requires_master skill gave rows {holders(locked['id'])} / served {locked}")
+        open_ = create_skill_definition(SkillDefinitionWriteBody(name="Course", base_domain="agility"), session)
+        if holders(open_["id"]) != [(ids["pc"], DEFAULT_RANK)]:
+            fail(f"B1: an open skill gave rows {holders(open_['id'])}")
+        update_skill_definition(locked["id"], SkillDefinitionWriteBody(
+            name="Alchimie", base_domain="perception", requires_master=False), session)
+        if holders(locked["id"]) != [(ids["pc"], DEFAULT_RANK)]:
+            fail(f"B1: opening the skill gave rows {holders(locked['id'])}")
+        update_skill_definition(locked["id"], SkillDefinitionWriteBody(
+            name="Alchimie", base_domain="perception", requires_master=True), session)
+        if holders(locked["id"]) != [(ids["pc"], DEFAULT_RANK)]:
+            fail(f"B1: locking the skill again changed rows to {holders(locked['id'])}")
+        seeded = {d.name for d in _pc_custom_skill_defs(ids["world"], session)}
+        if "Alchimie" in seeded or "Course" not in seeded:
+            fail(f"B1: a new PC would be seeded with {sorted(seeded)}")
+
+
+def check_b2(engine) -> None:
+    import json
+    from types import SimpleNamespace
+
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.play_physical import _say_physical_discovery, _say_physical_resolve_verdict
+    from world_engine.cockpit.play_stream import _mj_user_physical
+    from world_engine.models import Conversation, ProposedMutation, Session as GameSession, Skill, SkillDefinition
+    from world_engine.skill_access import locked_rubric, player_skill
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+        magic = SkillDefinition(world_id=ids["world"], name="Magie", base_domain="composure", requires_master=True)
+        rune = SkillDefinition(world_id=ids["world"], name="Rune", base_domain="composure", requires_master=True)
+        session.add(magic)
+        session.add(rune)
+        session.flush()
+        session.add(Skill(character_id=ids["pc"], domain="composure", rank=3, skill_definition_id=rune.id))
+        game = GameSession(world_id=ids["world"], number=1)
+        session.add(game)
+        session.flush()
+        conv = Conversation(world_id=ids["world"], session_id=game.id, player_id=ids["pc"])
+        session.add(conv)
+        session.commit()
+        defs = {"Magie": magic, "Rune": rune}
+        got = player_skill(session, ids["pc"], "Magie", defs)
+        if not got.locked or got.row is not None:
+            fail(f"B2: an untaught master skill read locked={got.locked}, row={got.row}")
+        got = player_skill(session, ids["pc"], "Rune", defs)
+        if got.locked or got.row is None or got.row.rank != 3:
+            fail(f"B2: a taught master skill read locked={got.locked}, row={got.row}")
+        ctx = SimpleNamespace(db=session, conv=SimpleNamespace(player_id=ids["pc"]), world_id=ids["world"],
+                              conv_id=conv.id)
+        base, verdict, _opposed, line = _say_physical_resolve_verdict(ctx, "Magie", None, None, defs)
+        event = json.loads(line[len("data: "):])["verdict"]
+        if (verdict.band, tuple(verdict.dice), verdict.domain, base) != ("locked", (0, 0), "Magie", "composure") \
+                or event.get("progress") is not None:
+            fail(f"B2: the locked roll gave {verdict} / {event}")
+        written = session.exec(select(ProposedMutation).where(ProposedMutation.world_id == ids["world"])).all()
+        if written:
+            fail(f"B2: the locked roll wrote {len(written)} mutation(s)")
+        rubric = _say_physical_discovery(ctx, base, None, verdict)
+        if rubric != locked_rubric("Magie"):
+            fail(f"B2: discovery returned {rubric!r}")
+        text = _mj_user_physical("", "", "Salle", "je lance un sort", "", "", "locked", rubric)
+        if "Résultat mécanique" in text or "COMPÉTENCE NON MAÎTRISÉE" not in text:
+            fail("B2: the MJ message for a locked skill keeps the verdict block or lacks the rubric")
+
+
+def check_b3(engine) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine.cockpit.crud.skills import SkillGrantBody, grant_skill, list_learnable_skills, list_skills
+    from world_engine.models import SkillDefinition
+
+    with Session(engine) as session:
+        ids = _a_world(session)
+        alch = SkillDefinition(world_id=ids["world"], name="Alchimie", base_domain="perception", requires_master=True)
+        session.add(alch)
+        session.commit()
+        ids["escrime"].requires_master = True
+        session.add(ids["escrime"])
+        session.commit()
+        learnable = {e["name"]: [m["id"] for m in e["masters"]] for e in list_learnable_skills(ids["pc"], session)}
+        if learnable != {"Alchimie": []}:
+            fail(f"B3: the player may learn {learnable}")
+        npc = {e["name"] for e in list_learnable_skills(ids["brute"], session)}
+        if npc != {"agility", "perception", "composure", "Alchimie", "escrime", "feu"}:
+            fail(f"B3: the NPC may be given {sorted(npc)}")
+        plain_learn = {e["name"]: [m["id"] for m in e["masters"]] for e in list_learnable_skills(ids["plain"], session)}
+        if plain_learn.get("escrime") != [ids["master"]]:
+            fail(f"B3: escrime's masters are {plain_learn.get('escrime')}")
+
+        def call(**kwargs):
+            try:
+                return grant_skill(SkillGrantBody(**kwargs), session)
+            except HTTPException as exc:
+                session.rollback()
+                return exc.status_code
+
+        if call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id, taught_by_id=ids["brute"]) != 422:
+            fail("B3: a non-master taught")
+        if call(character_id=ids["master"], skill_definition_id=alch.id, taught_by_id=ids["master"]) != 422:
+            fail("B3: a character taught himself")
+        row = call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id, taught_by_id=ids["master"])
+        if not isinstance(row, dict) or (row["rank"], row["taught_by_id"]) != (0, ids["master"]):
+            fail(f"B3: learning from the master gave {row}")
+        if call(character_id=ids["plain"], skill_definition_id=ids["escrime"].id) != 409:
+            fail("B3: a second grant of the same skill was not refused")
+        row = call(character_id=ids["pc"], skill_definition_id=alch.id)
+        if not isinstance(row, dict) or row["taught_by_id"] is not None or row["requires_master"] is not True:
+            fail(f"B3: the creator's grant without a master gave {row}")
+        row = call(character_id=ids["plain"], domain="agility", rank=4)
+        if not isinstance(row, dict) or (row["domain"], row["rank"]) != ("agility", 4):
+            fail(f"B3: an NPC base domain grant gave {row}")
+        sheet = {r["definition_name"]: r for r in list_skills(character_id=ids["plain"], db=session)}
+        if sheet.get("escrime", {}).get("taught_by_id") != ids["master"]:
+            fail(f"B3: GET /api/skills served {sheet.get('escrime')}")
+
+
+def check_b4() -> None:
+    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
+    if "requires_master" not in text or "skill_access" not in text:
+        fail("B4: CLAUDE.md does not name requires_master and skill_access")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -347,13 +519,19 @@ def main() -> int:
     create_db_and_tables()
     check_a3(engine)
     check_a4(engine)
+    check_b1(engine)
+    check_b2(engine)
+    check_b3(engine)
+    check_b4()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: npc_skills -- v2.16 gives NPCs skill rows in place of physical_tier, migrates "
           "every carrure to a physical row from v2.15 only, and an opposing NPC rolls its own "
-          "row for the skill, else its base domain, else Initié")
+          "row for the skill, else its base domain, else Initié; a skill that requires a master "
+          "is held only once taught, cannot be rolled until then, and is taught by a Maître or "
+          "granted by the creator")
     return 0
 
 
````

## Scope OUT

- The fiche UI (C); the « Exige un maître » box (C).
- Learning proposed from a conversation or a day (C2, quests).
- Any change to `legacy.html` (it prints the `locked` band as text).
- Removing a row from a character.
- Every later brief of this lot.

## Invariants to defend

**The Play stream's request session is read-only:** the lock reads only; a locked turn writes no mutation. **Two canon-write paths:** grants and backfills are creator CRUD, through `write_skill_row`. **History is sacred:** turning the flag on deletes no row.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `stream_session_readonly.py`, `single_canon_write.py` or `import_cycle.py` fails.
- `play_physical.py` is not exactly 972 lines after the commit.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `CLAUDE.md` because a neighbouring line moved: replace the backfill invariant's three opening lines by the diff's five by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/npc_skills.py` -> `PASS: npc_skills -- … a skill that requires a master is held only once taught, cannot be rolled until then, and is taught by a Maître or granted by the creator`.
- `stream_session_readonly.py`, `single_canon_write.py`, `import_cycle.py`, `module_budget.py`, `function_length.py`, `skill_progression.py`, `claude_md_contract.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted: in `player_skill`, `    if row is None and definition.requires_master:` -> `    if False:` -> `B2`; in `create_skill_definition`, the two lines `    if not definition.requires_master:` / `        _backfill_open_skill(db, definition)` -> `    _backfill_open_skill(db, definition)` -> `B1`; in `grant_skill`, the line beginning `        if body.taught_by_id == body.character_id or` -> `        if False:` -> `B3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 140/140.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md: the backfill invariant (open skills; `POST /api/skills`; the lock). Decision entry `A SKILL MAY REQUIRE A MASTER (TICKET-0107) -- NOT HELD UNTIL TAUGHT, NOT ROLLED UNTIL THEN (BRIEF-0107-b, no schema change)` — in the diff.
