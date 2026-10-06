<!-- slug: roll-earns-a-point -->
# BRIEF 0106-B — "A roll earns a point: auto-applied in Play, given at a day step's approval"

Lot: LOT-0106-skill-progression.md (authoritative on conflict)
Depends on: BRIEF-0106-A
Commit header for decisions: `(BRIEF-0106-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0106`, on the tree BRIEF-0106-A left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/skill_ranks.py` exists and defines `MAX_RANK`, `skill_points_to_next`, `world_ladder`; `src/world_engine/schema_version.py:15` → `"v2.15"`.
- `src/world_engine/writes/characters.py:28` → `from ..skill_ranks import RANKS`; `:56` → `def write_skill_rank(`; `:96` → `def write_ledger_entry(`; no `write_skill_progress` anywhere.
- `src/world_engine/cockpit/play_physical.py:54` → `from .play_discovery import _propose_engine_discovery`; `:195` → `    player_tier = skill_ranks.rank_modifier(skill_row.rank) if skill_row else 0`; `:214` → the line beginning `    verdict_sse_line = f"data: {json.dumps({'verdict': {'domain': verdict.domain,` and ending `'band': verdict.band}})}\n\n"`; `wc -l` → 996.
- `src/world_engine/cockpit/mutations.py:74` → `from .routes import mutations as _routes_mutations`; `:827` → `def _mutation_apply_agenda_step_change(`; `:866` → `    new_status = "completed" if action == "complete" else "failed"`.
- `src/world_engine/cockpit/routes/mutations.py:441` → `    from .. import mutations as _mutations`; `:465` → `        "agenda_delegation": _mutations._mutation_apply_agenda_delegation,`; `:600` → `def _approve_apply_and_commit(mut: ProposedMutation, db: Session, now: datetime) -> dict:`; `:395` → `    - resource_change (BRIEF-19): its money leg accumulates exactly like`.
- No `src/world_engine/cockpit/skill_progress.py`; no `skill_progress` string under `src/`.
- `tooling/verify/canon_write_policy.txt:25` → `src/world_engine/writes/characters.py::write_skill_rank        skill`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md:455` → `> state. Any extension of this category is a creator decision, recorded here.`
- `CLAUDE.md:196` → `- **\`proposed_by='engine'\` deterministic proposals**`.
- `tooling/verify/checks/skill_progression.py:395` → `def main() -> int:`; `:403` → `    check_a4()`.

## Facts carried

### R-04 — the Play stream is read-only [M]
Opened: `tooling/verify/checks/stream_session_readonly.py:1-80` (rules 1-3:
no write on, and no delegation of, the request session `ctx.db`);
`src/world_engine/cockpit/play_physical.py:137-150` (`skill_lexicon.record`
on its own `Session(engine)`, the precedent).
Consequence: `record_roll` takes ids, never `ctx.db`, and opens its own
session.

### R-05 — `play_physical.py` at its cap [M]
Opened: `tooling/verify/checks/module_budget.py:56-59` (`MAX_LINES = 1000`);
`wc -l src/world_engine/cockpit/play_physical.py` → 996;
`play_physical.py:18` (`from .. import llm_parse, ollama_client,
skill_lexicon`), `:54` (`from .play_discovery import ...`), `:152-215`
(`_say_physical_resolve_verdict`, `:195` the tier read, `:214` the verdict
event line).
Consequence: A changes two lines in place (imports joined to `:18`); B adds
two (one import, one call) — 998 lines. Any other growth is a STOP.

### R-06 — a day writes no canon until approved [M]
Opened: `src/world_engine/day_resolve.py:1-56` (module docstring: REPLAY
re-rolls, V1 no canon), `:165-177` (`_step_player_tier`), `:206-228`;
`src/world_engine/day_mutations.py:106-145` (`_step_action`: a blocked step
emits no `agenda_step_change`; failure → `fail`, else `complete`);
`src/world_engine/cockpit/mutations.py:827-884`
(`_mutation_apply_agenda_step_change`: stale guard `step.status ==
"active"`, then status writes).
Finding: every emitted `agenda_step_change` whose step has a `domain` was
rolled; replays re-propose, and the stale guard applies one per step.
Consequence: the day's point is granted inside that applier, from
`step.domain`, never at the roll and never from the payload.

### R-07 — the dispatcher and the approval path [M]
Opened: `src/world_engine/cockpit/routes/mutations.py:420-470`
(`_apply_mutation`, lazy `from .. import mutations as _mutations`,
`appliers` dict), `:600-630` (`_approve_apply_and_commit`: SAVEPOINT, status
`applied` + `applied_at`, else `approved` with the error in
`creator_notes`), `:300-400` (`_find_applied_duplicate`: types without a
branch fall through unguarded, the docstring lists them);
`src/world_engine/models/pipeline.py:99-144` (`ProposedMutation`).
Consequence: `skill_progress` joins the `appliers` dict and the docstring's
accumulating list; `record_roll` reuses `_approve_apply_and_commit`.

### R-08 — auto-applied mutations [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:439-456` (four
conditions; `item_update` the sole, dormant member; « Any extension of this
category is a creator decision, recorded here. »); `:1134-1135` and
`CLAUDE.md:196-198` (`proposed_by='engine'` proposals are never
auto-applied); `CLAUDE.md:163-164` (two canon-write paths).
Consequence: Q1 is recorded in that section; the tag is `engine_roll`,
never `engine`; one CLAUDE.md invariant names it.

### R-09 — sanctioned canon writes [M]
Opened: `tooling/verify/canon_write_policy.txt:1-7` (`[CANON_TABLES]`),
`:24` (`write_skill_tier skill`), the `crud/skills.py` entries;
`tooling/verify/checks/single_canon_write.py:1-60, 180-206`.
Consequence: `write_skill_tier` is renamed `write_skill_rank`;
`write_skill_progress` and `upsert_skill_rank` are new allowed sites;
`skill_rank` joins `[CANON_TABLES]`.

### R-10 — Play is sealed [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md:12263-12267` (A3:
`legacy.html` byte-untouched); `tooling/verify/checks/module_budget.py:61-65`
(`LEGACY_DOCUMENT_LINE_CEILING = 2762`, fails on growth and on shrinkage);
`src/world_engine/cockpit/legacy.html:1269-1273` (stores `token.verdict`),
`:1408-1421` (`_appendVerdict` reads `domain, dice, modifier, total,
band`).
Finding: an extra key on the verdict object is ignored by the client.
Consequence: Y1b — `progress` rides on the verdict event; `legacy.html` is
not in any diff.

## Contracts

### C-02 — the ladder (`skill_ranks.py`)
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-B, C, D
`RANKS = (0..5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`, `RANK_MODIFIERS =
(-1, 0, 1, 2, 2, 3)`, `DEFAULT_RANK_LABELS = ("Inexpérimenté", "Initié",
"Apprenti", "Confirmé", "Expert", "Maître")`, `DEFAULT_POINTS_TO_NEXT = (5,
10, 20, 40, 80)`, `TIER_TO_RANK = {-1: 0, 0: 1, 1: 2, 2: 3}`,
`RANK_POINTS_COLUMNS` (index = rank left). `RankStep(rank, label,
points_to_next)` frozen. `rank_modifier(rank) -> int` (`ValueError` outside
0-5). `default_ladder() -> tuple[RankStep, ...]`. `world_ladder(db,
world_id) -> tuple[RankStep, ...]` (six, index = rank; rows over defaults;
never writes). `points_to_next(rank, ladder, *, system=None,
definition=None) -> Optional[int]` (definition's column, else system's,
else the ladder's; None at MAX_RANK). `skill_owners(db, skill_definition_id)
-> (system | None, definition | None)`. `skill_points_to_next(db, *,
world_id, rank, skill_definition_id) -> Optional[int]`.

### C-05 — the points writer
Produced by: BRIEF-0106-B   Consumed by: BRIEF-0106-B (C-06, C-07)
`writes.write_skill_progress(db, *, skill_id, world_id, points, changed_by)
-> SkillProgress(rank_before, rank, xp, points_to_next)`. `points` a
non-zero int (`ValueError` otherwise, and on an unknown row, before any
write). Gain: `xp += points`; if `xp >=` the current rank's threshold (C-02)
the rank rises by one and `xp = 0` (at most one rank per call); at MAX_RANK
points accumulate. Loss: below 0, the rank falls by one and `xp =
threshold(lower rank) + remainder` (so -1 undoes a +1 that ranked up); at
rank 0 `xp` stops at 0. History `{rank, xp, changed_at, by}` appended only
when the rank moves. Caller commits.

### C-06 — the `skill_progress` mutation (family: auto-applied mutations)
Produced by: BRIEF-0106-B   Consumed by: Play, the review cockpit
Payload `{"skill_id": str, "points": int != 0, "band": str | None}`,
`target_table="skill"`, `target_id=skill_id`, `proposed_by="engine_roll"`
(`skill_progress.SKILL_PROGRESS_PROPOSED_BY`), `source_type="conversation"`.
Applier `cockpit/skill_progress.apply_skill_progress(mut, payload, db) ->
Optional[str]` (error string on a missing id, zero/non-int points, unknown
row; else C-05 with `changed_by="mutation:<id>"`). `record_roll(*,
world_id, conversation_id, skill_id, band) -> Optional[dict]`: None for
`skill_id` None, an unknown row, a Maître, an apply refused, or any
exception (logged, swallowed); else one mutation applied through
`routes/mutations._approve_apply_and_commit` on its own session, and
`{skill, rank, rank_label, ranked_up, xp, points_to_next}`. Play's verdict
event carries it as `verdict.progress` (None when nothing earned).

### C-07 — the day's point
Produced by: BRIEF-0106-B   Consumed by: `_mutation_apply_agenda_step_change`
`cockpit/skill_progress.grant_step_roll(db, *, step, owner_id, world_id,
mutation_id) -> None`: nothing when `step.domain` is None, the owner has no
base row for it (`skill_definition_id IS NULL`), or the row is at MAX_RANK;
else C-05 with 1 point. Called for `complete` and `fail`, after the stale
guard, before the status writes.

## Context

The rank and its points exist (A). Nia locked one point per roll, failures included, with no cap (M2, N2), to the skill row rolled (S1), and an automatic rank-up at the threshold (K1). In Play the point is an auto-applied mutation — she extended the ARCHITECTURE category for it (Q1). A day's dice are replayable, so its point is given when she approves the step. Play stays sealed (Y1b): the point rides on the verdict event, unseen there until Play's migration.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - adds `SkillProgress` and `write_skill_progress` to `writes/characters.py` (C-05), exported by `writes`; allow-lists it in `canon_write_policy.txt`;
   - creates `src/world_engine/cockpit/skill_progress.py` (C-06, C-07): `apply_skill_progress`, `record_roll` (own session, `routes.mutations._approve_apply_and_commit` imported inside the function), `grant_step_roll`;
   - adds `"skill_progress"` to `_apply_mutation`'s appliers (lazy import beside `_mutations`) and to `_find_applied_duplicate`'s docstring list of accumulating types;
   - in `cockpit/mutations.py`, imports `grant_step_roll` and calls it in `_mutation_apply_agenda_step_change` just before `new_status = …`, with one docstring sentence;
   - in `play_physical.py`, imports `record_roll` and calls it right after the dice, putting the result on the verdict event as `progress` (two lines added: 998);
   - adds one CLAUDE.md invariant under the `proposed_by='engine'` one;
   - inserts the extension paragraph right after the « Auto-applied mutations » blockquote, and appends the decision entry above the footer;
   - adds B1-B4 to `skill_progression.py`.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(skills): a roll earns a point, auto-applied in Play, given at a day step's approval (BRIEF-0106-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index ec6cff5..ed10391 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -196,6 +196,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
 - **`proposed_by='engine'` deterministic proposals**
   (`_propose_engine_injury`, `_propose_engine_discovery`) follow the same
   review queue as AI proposals — never auto-applied.
+- **`skill_progress` is the one live auto-applied mutation:** a roll's point
+  (`proposed_by='engine_roll'`) applied through `_apply_mutation` at proposal time;
+  `write_skill_progress` moves the rank -- enforced by `skill_progression.py`.
 - **Constraint gating is structural, not instructional:** gagged/restrained/
   blindfolded effects are enforced in Python before any model call
   (`_stream` in `app.py`). Blindfolded exclusion is a data exclusion in
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index 7e9f2a3..46c78d2 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -72,6 +72,7 @@ from ..writes import (
 from ..writes.zone_promotion import promotion_preview
 from ..zone_rules import ZoneRefusal, require_visitable
 from .routes import mutations as _routes_mutations
+from .skill_progress import grant_step_roll
 
 
 def _knowledge_leg_already_applied(
@@ -828,7 +829,8 @@ def _mutation_apply_agenda_step_change(mut: ProposedMutation, payload: dict, db:
     """Stale guard (0014 doctrine, canon-existence): the step must still be
     the ACTIVE one. Completion effects (TICKET-0024, BRIEF-0024-c) —
     `complete` only, never `fail`. Subject is FORCED to the agenda's owner;
-    a role_change effect on a faction-owned agenda is a whole reject."""
+    a role_change effect on a faction-owned agenda is a whole reject. The
+    step's roll earns its point either way (`grant_step_roll`, TICKET-0106)."""
     step_id = payload.get("step_id")
     action = payload.get("action")
     if not step_id or action not in ("complete", "fail"):
@@ -863,6 +865,7 @@ def _mutation_apply_agenda_step_change(mut: ProposedMutation, payload: dict, db:
         if not effects:
             extra_history["no_footprint"] = True
 
+    grant_step_roll(db, step=step, owner_id=agenda.owner_entity_id, world_id=mut.world_id, mutation_id=mut.id)
     new_status = "completed" if action == "complete" else "failed"
     write_agenda_step_status(
         db, step=step, status=new_status, outcome=payload.get("outcome"), mutation_id=mut.id,
diff --git a/src/world_engine/cockpit/play_physical.py b/src/world_engine/cockpit/play_physical.py
index 1bdd2b0..5c61036 100644
--- a/src/world_engine/cockpit/play_physical.py
+++ b/src/world_engine/cockpit/play_physical.py
@@ -52,6 +52,7 @@ from .play import (
     _npc_dialogue_system_prompt,
 )
 from .play_discovery import _propose_engine_discovery
+from .skill_progress import record_roll
 
 _log = logging.getLogger(__name__)
 
@@ -211,7 +212,8 @@ def _say_physical_resolve_verdict(
         verdict.domain, verdict.dice, verdict.modifier, verdict.total,
         verdict.band, player_tier, npc_tier, opposed_npc_id or "none",
     )
-    verdict_sse_line = f"data: {json.dumps({'verdict': {'domain': verdict.domain, 'dice': list(verdict.dice), 'modifier': verdict.modifier, 'total': verdict.total, 'band': verdict.band}})}\n\n"
+    progress = record_roll(world_id=ctx.world_id, conversation_id=ctx.conv_id, skill_id=skill_row.id if skill_row else None, band=verdict.band)
+    verdict_sse_line = f"data: {json.dumps({'verdict': {'domain': verdict.domain, 'dice': list(verdict.dice), 'modifier': verdict.modifier, 'total': verdict.total, 'band': verdict.band, 'progress': progress}})}\n\n"
     return resolved_base_domain, verdict, opposed_entity, verdict_sse_line
 
 
diff --git a/src/world_engine/cockpit/routes/mutations.py b/src/world_engine/cockpit/routes/mutations.py
index e25a3d0..0052edf 100644
--- a/src/world_engine/cockpit/routes/mutations.py
+++ b/src/world_engine/cockpit/routes/mutations.py
@@ -392,6 +392,8 @@ def _find_applied_duplicate(
       the monotone re-check inside _apply_mutation ("level already >=
       proposed") is the correct guard, not an identity-based duplicate
       check.
+    - skill_progress (TICKET-0106): one point per roll, accumulating like
+      relation_change -- two rolls in one conversation earn two points.
     - resource_change (BRIEF-19): its money leg accumulates exactly like
       relation_change — two genuine purchases in one conversation must
       both apply. Its knowledge leg IS idempotent, but that guard lives
@@ -439,6 +441,7 @@ def _apply_mutation(mut: ProposedMutation, db: Session) -> Optional[str]:
     endpoint short-circuits before this function ever sees that type.
     """
     from .. import mutations as _mutations
+    from .. import skill_progress as _skill_progress
 
     # ── Duplicate guard ───────────────────────────────────────────────────────
     # Must run before any write.  If an equivalent mutation was already applied
@@ -463,6 +466,7 @@ def _apply_mutation(mut: ProposedMutation, db: Session) -> Optional[str]:
         "agenda_step_change": _mutations._mutation_apply_agenda_step_change,
         "agenda_creation": _mutations._mutation_apply_agenda_creation,
         "agenda_delegation": _mutations._mutation_apply_agenda_delegation,
+        "skill_progress": _skill_progress.apply_skill_progress,
     }
     applier = appliers.get(mut.mutation_type)
     if applier is None:
diff --git a/src/world_engine/cockpit/skill_progress.py b/src/world_engine/cockpit/skill_progress.py
new file mode 100644
index 0000000..08c611c
--- /dev/null
+++ b/src/world_engine/cockpit/skill_progress.py
@@ -0,0 +1,129 @@
+"""A roll earns a skill point (TICKET-0106, BRIEF-0106-B, decisions H1, K1, M2,
+N2, Q1, S1, Y1b).
+
+Every roll of the player earns one point (M2: success, partial or failure
+alike -- one learns from failing too), with no cap (N2). Reaching the
+threshold of the current rank moves the skill up one rank, automatically
+(K1: the threshold half; trials with extra requirements come with quests).
+
+Two carriers, both inside `_apply_mutation` (Q1):
+
+- Play. `record_roll` runs right after the dice, on a session of its own
+  (the stream's request session is read-only, `stream_session_readonly.py`):
+  it writes one `skill_progress` mutation, `proposed_by='engine_roll'`, and
+  applies it at once through `routes/mutations._approve_apply_and_commit`
+  -- an AUTO-APPLIED mutation (ARCHITECTURE_DECISIONS.md, "Auto-applied
+  mutations": reversible by a `skill_progress` of -1 point, creates and
+  destroys nothing, touches no relation or knowledge, recorded `applied`
+  and visible in the review cockpit). The point goes to the row that was
+  rolled (S1): the custom skill when the arbiter named one. A skill at
+  Maître earns nothing more: no mutation is written. A failure here is
+  logged and swallowed -- a point must never break a turn. The result rides
+  on the verdict event as `progress` (Y1b: Play is sealed, its client does
+  not show it yet).
+- A day. A day's dice are replayable and write no canon (`day_resolve.py`);
+  the point is given when Nia APPROVES the step's `agenda_step_change`,
+  complete or fail alike, by `grant_step_roll`, called from that applier:
+  the step's `domain` names the base skill rolled, read from the step,
+  never from the payload.
+"""
+
+from __future__ import annotations
+
+import logging
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from ..db import engine
+from ..models import AgendaStep, ProposedMutation, Skill, SkillDefinition, World
+from ..skill_ranks import MAX_RANK, skill_points_to_next, world_ladder
+from ..writes import write_skill_progress
+
+_log = logging.getLogger(__name__)
+
+SKILL_PROGRESS_PROPOSED_BY = "engine_roll"
+ROLL_POINTS = 1
+
+
+def apply_skill_progress(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
+    """`_apply_mutation`'s applier for `skill_progress`: payload
+    `{"skill_id": str, "points": non-zero int, "band": str | None}`. Returns
+    an error string, never raises."""
+    skill_id = payload.get("skill_id")
+    points = payload.get("points")
+    if not skill_id or not isinstance(points, int) or isinstance(points, bool) or points == 0:
+        return "skill_progress: payload must contain skill_id and a non-zero integer points"
+    if db.get(Skill, skill_id) is None:
+        return f"skill_progress: skill {skill_id!r} not found"
+    write_skill_progress(db, skill_id=skill_id, world_id=mut.world_id, points=points,
+                         changed_by=f"mutation:{mut.id}")
+    return None
+
+
+def _progress_payload(db: Session, skill: Skill, world_id: str, rank_before: int) -> dict:
+    definition = db.get(SkillDefinition, skill.skill_definition_id) if skill.skill_definition_id else None
+    ladder = world_ladder(db, world_id)
+    return {
+        "skill": definition.name if definition else skill.domain,
+        "rank": skill.rank,
+        "rank_label": ladder[skill.rank].label,
+        "ranked_up": skill.rank > rank_before,
+        "xp": skill.xp,
+        "points_to_next": skill_points_to_next(db, world_id=world_id, rank=skill.rank,
+                                               skill_definition_id=skill.skill_definition_id),
+    }
+
+
+def record_roll(*, world_id: str, conversation_id: str, skill_id: Optional[str], band: str) -> Optional[dict]:
+    """One auto-applied `skill_progress` for a Play roll. Returns the skill's
+    new state (`skill`, `rank`, `rank_label`, `ranked_up`, `xp`,
+    `points_to_next`), or None when nothing was earned: no row rolled, a
+    Maître, an apply refused, or any error (logged)."""
+    if skill_id is None:
+        return None
+    try:
+        with Session(engine) as db:
+            skill = db.get(Skill, skill_id)
+            if skill is None or skill.rank >= MAX_RANK or db.get(World, world_id) is None:
+                return None
+            rank_before = skill.rank
+            mut = ProposedMutation(
+                world_id=world_id, source_type="conversation", conversation_id=conversation_id,
+                mutation_type="skill_progress", target_table="skill", target_id=skill_id,
+                payload={"skill_id": skill_id, "points": ROLL_POINTS, "band": band},
+                rationale=f"jet ({band}) : +{ROLL_POINTS} point", proposed_by=SKILL_PROGRESS_PROPOSED_BY,
+            )
+            db.add(mut)
+            db.flush()
+            from .routes.mutations import _approve_apply_and_commit
+            result = _approve_apply_and_commit(mut, db, datetime.now(UTC))
+            if result.get("status") != "applied":
+                _log.warning("skill_progress %s not applied: %s", mut.id, result.get("error"))
+                return None
+            db.refresh(skill)
+            return _progress_payload(db, skill, world_id, rank_before)
+    except Exception:  # a point must never break a turn
+        _log.exception("skill_progress: recording the roll on skill %s failed", skill_id)
+        return None
+
+
+def grant_step_roll(db: Session, *, step: AgendaStep, owner_id: str, world_id: str, mutation_id: str) -> None:
+    """The point of an approved day step's roll: the owner's base skill row
+    for `step.domain` (`skill_definition_id IS NULL`). Nothing when the step
+    had no roll (no domain), the owner has no such row (a faction, an NPC),
+    or the skill is at Maître."""
+    if step.domain is None:
+        return
+    skill = db.exec(
+        select(Skill).where(
+            Skill.character_id == owner_id,
+            Skill.domain == step.domain,
+            Skill.skill_definition_id.is_(None),
+        )
+    ).first()
+    if skill is None or skill.rank >= MAX_RANK:
+        return
+    write_skill_progress(db, skill_id=skill.id, world_id=world_id, points=ROLL_POINTS,
+                         changed_by=f"mutation:{mutation_id}")
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index c615207..0fd3720 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -50,7 +50,9 @@ _find_relation_pair`, etc.) is untouched, byte for byte, by this split.
 from __future__ import annotations
 
 from ._shared import _append_history_snapshot, _clamp
-from .characters import write_character_location, write_ledger_entry, write_skill_rank
+from .characters import (
+    SkillProgress, write_character_location, write_ledger_entry, write_skill_progress, write_skill_rank,
+)
 from .config import (
     upsert_conversation_window_config,
     upsert_location_type,
@@ -149,6 +151,8 @@ __all__ = [
     "create_fact_default",
     "attach_participants",
     "write_skill_rank",
+    "write_skill_progress",
+    "SkillProgress",
     "write_ledger_entry",
     "write_membership",
     "write_event",
diff --git a/src/world_engine/writes/characters.py b/src/world_engine/writes/characters.py
index 7c1c469..a78604a 100644
--- a/src/world_engine/writes/characters.py
+++ b/src/world_engine/writes/characters.py
@@ -9,6 +9,10 @@ none of these three functions were baselined.
   (history is sacred on this path too) and restarting its points at 0
   (U2). The sole write shape for a creator's rank edit (TICKET-0106,
   BRIEF-0106-A; formerly `write_skill_tier`).
+- `write_skill_progress(...)`           : add points to a `skill` row and
+  move its rank when a threshold is crossed (TICKET-0106, BRIEF-0106-B).
+  The sole write shape for points; called by the `skill_progress` applier
+  and the day step's roll, both inside `_apply_mutation`.
 - `write_ledger_entry(...)`             : pure INSERT into the append-only
   `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
   new compensating line. The single chokepoint for ledger writes, shared by
@@ -18,6 +22,7 @@ none of these three functions were baselined.
 
 from __future__ import annotations
 
+from dataclasses import dataclass
 from datetime import UTC, datetime
 from typing import Optional
 
@@ -25,7 +30,7 @@ from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session
 
 from ..models import Character, Ledger, Skill
-from ..skill_ranks import RANKS
+from ..skill_ranks import MAX_RANK, RANKS, skill_points_to_next
 
 
 def write_character_location(
@@ -93,6 +98,74 @@ def write_skill_rank(
     return skill
 
 
+@dataclass(frozen=True)
+class SkillProgress:
+    rank_before: int
+    rank: int
+    xp: int
+    points_to_next: Optional[int]  # None at MAX_RANK
+
+
+def write_skill_progress(
+    db: Session,
+    *,
+    skill_id: str,
+    world_id: str,
+    points: int,
+    changed_by: str,
+) -> SkillProgress:
+    """Add `points` (non-zero, may be negative) to a `skill` row's `xp`.
+    Caller adds the row to the session.
+
+    Gaining: when `xp` reaches the points needed to leave the current rank
+    (`skill_ranks.skill_points_to_next`), the rank rises by one and `xp`
+    restarts at 0 (U2) -- at most one rank per call. At MAX_RANK the points
+    still accumulate. Losing (the inverse of a gain): below 0, the rank falls
+    by one and `xp` becomes that lower rank's threshold minus the remainder,
+    so -1 exactly undoes a +1 that ranked up; at rank 0 `xp` stops at 0.
+    `change_history` gets the previous rank and points only when the rank
+    moves -- a point alone is audited by the mutation that carried it.
+    `ValueError` on zero points or an unknown row, before any write.
+    """
+    if not isinstance(points, int) or isinstance(points, bool) or points == 0:
+        raise ValueError(f"write_skill_progress: points must be a non-zero integer, got {points!r}")
+    skill = db.get(Skill, skill_id)
+    if skill is None:
+        raise ValueError(f"write_skill_progress: skill {skill_id!r} not found")
+
+    def threshold(rank: int) -> Optional[int]:
+        return skill_points_to_next(db, world_id=world_id, rank=rank, skill_definition_id=skill.skill_definition_id)
+
+    rank_before, xp_before = skill.rank, skill.xp
+    rank, xp = rank_before, xp_before + points
+    needed = threshold(rank)
+    if points > 0 and needed is not None and xp >= needed:
+        rank, xp = rank + 1, 0
+    elif xp < 0 and rank > 0:
+        rank -= 1
+        xp = max(0, (threshold(rank) or 1) + xp)
+    xp = max(0, xp)
+
+    if rank != rank_before:
+        history = list(skill.change_history or [])
+        history.append({
+            "rank": rank_before,
+            "xp": xp_before,
+            "changed_at": datetime.now(UTC).isoformat(),
+            "by": changed_by,
+        })
+        skill.change_history = history
+        sa_attrs.flag_modified(skill, "change_history")
+    skill.rank = rank
+    skill.xp = xp
+    skill.updated_at = datetime.now(UTC)
+    db.add(skill)
+    return SkillProgress(
+        rank_before=rank_before, rank=rank, xp=xp,
+        points_to_next=None if rank >= MAX_RANK else threshold(rank),
+    )
+
+
 def write_ledger_entry(
     db: Session,
     *,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 46781b0..301933e 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -454,6 +454,15 @@ fails, only the canon writes roll back; the mutation-row update (status,
 > functional, ready for reactivation if combat design later needs an in-hand
 > state. Any extension of this category is a creator decision, recorded here.
 
+**Extension -- `skill_progress` (TICKET-0106, Q1, Nia 2026-10-05).** A Play
+roll's point is the category's second member, and its only live one: one
+point on the skill row rolled (`proposed_by='engine_roll'`, never the
+reviewed `'engine'` tag), applied at proposal time through `_apply_mutation`
+by `cockpit/skill_progress.record_roll`. It meets all four conditions: a
+`skill_progress` of -1 point undoes it, rank included; it creates and
+destroys nothing; it touches no relation and no knowledge; it is recorded
+`applied` and listed with the applied mutations.
+
 ### The "Needs attention" tab
 
 `status = 'approved'` is an **exception bucket**, not a success state. A
@@ -17902,6 +17911,39 @@ modifier: a Maître against an untrained NPC could almost never fail. T2,
 widening `tier` to 0..5: a misleading name forever. Override rows in a
 separate table: a cleared override would be a hard delete.
 
+
+## A ROLL EARNS A POINT (TICKET-0106) -- AUTO-APPLIED IN PLAY, GIVEN AT A DAY STEP'S APPROVAL (BRIEF-0106-b, no schema change)
+
+**M2, N2, S1.** Every roll of the player earns one point on the skill row
+that was rolled -- the custom skill when the arbiter named one -- whatever
+the band (one learns from failing too), with no cap. A Maître earns nothing
+more: no mutation is written for it.
+
+**Q1, K1.** In Play the point is a `skill_progress` mutation, auto-applied
+(see "Auto-applied mutations"). `writes.write_skill_progress` is its sole
+write shape: when the points reach the current rank's threshold
+(`skill_ranks.points_to_next`), the rank rises by one and the points restart
+at 0; a negative amount undoes it exactly. The row's `change_history`
+records a rank move only -- each point is audited by the mutation that
+carried it. A failure while recording is logged and swallowed: a point
+never breaks a turn.
+
+**A day.** A day's dice are replayable and write no canon, so its points
+are given when Nia approves the step's `agenda_step_change` -- complete or
+fail -- by `grant_step_roll`, which reads the base skill from the step's
+own `domain`, never from the payload. A faction's or an NPC's step earns
+nothing: they have no skill rows.
+
+**Y1b.** Play is sealed (TICKET-0061, A3): the point rides on the verdict
+event as `progress`, which `legacy.html` ignores until Play's migration
+(TICKET-0069). Until then it is seen on the PC's fiche, in the day's
+account, and among the applied mutations.
+
+**Rejected.** Q2, a proposal per roll for review: the queue would fill with
+single points. Q3, a direct write outside `_apply_mutation`: a third canon
+write path. Y1a, a line-neutral edit of `_appendVerdict`: it would break
+the seal for one function.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index da7eb25..6e07a71 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -23,6 +23,8 @@ src/world_engine/writes/knowledge.py::write_knowledge          knowledge
 src/world_engine/writes/characters.py::write_ledger_entry      ledger
 src/world_engine/writes/factions.py::write_membership          faction_membership
 src/world_engine/writes/characters.py::write_skill_rank        skill
+# TICKET-0106, BRIEF-0106-B: write_skill_progress adds a roll's points to a skill row and moves its rank at a threshold; called only from inside _apply_mutation (the skill_progress applier and the agenda_step_change applier).
+src/world_engine/writes/characters.py::write_skill_progress    skill
 src/world_engine/writes/goals_agendas.py::write_npc_goal       npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_status npc_goal
 src/world_engine/writes/goals_agendas.py::write_npc_goal_prerequisites npc_goal
diff --git a/tooling/verify/checks/skill_progression.py b/tooling/verify/checks/skill_progression.py
index 10380d9..14d857a 100644
--- a/tooling/verify/checks/skill_progression.py
+++ b/tooling/verify/checks/skill_progression.py
@@ -42,6 +42,33 @@ A4 -- no tier left (AST and static). No `.tier` attribute and no `tier=`
    `PjSkillFiche.svelte` and `cockpit/crud/skills.py` do not contain the
    word `tier`; `play_physical.py` calls `rank_modifier(`.
 
+B1 -- the points writer (BRIEF-0106-B, fixture, the default ladder). On a
+   rank-1 row at 8 points: +1 -> rank 1, 9; +1 -> rank 2, 0, one history
+   entry {rank 1, xp 9}; -1 -> rank 1, 9 (the rank-up undone), one more
+   entry; a rank-0 row at 0 points, -1 -> 0, 0, no entry; a rank-5 row, +1
+   -> rank 5, one more point; a custom row whose system sets
+   `points_to_rank_2 = 2`, at rank 1 and 1 point, +1 -> rank 2, 0; points 0
+   -> `ValueError`, nothing written.
+B2 -- a Play roll (fixture). `record_roll` on a rank-1 row writes exactly
+   one `skill_progress` mutation, `status='applied'`,
+   `proposed_by='engine_roll'`, payload {skill_id, points 1, band}, with an
+   `applied_at`, and the row gains one point; it returns the new state
+   (`rank_label`, `xp`, `points_to_next`, `ranked_up` False). The roll that
+   reaches the threshold returns `ranked_up` True. On a rank-5 row, on no
+   row (`skill_id` None) and on an unknown id it returns None and writes no
+   mutation. `_apply_mutation` refuses a payload with 0 points.
+B3 -- a day step (fixture). A PC's agenda with an active `physical` step:
+   approving its `agenda_step_change` (`complete`) through `_apply_mutation`
+   gives the PC's base `physical` row one point; a `fail` on the next step
+   gives one more; a step without a domain gives none; a faction-owned
+   agenda's step gives none and fails nothing.
+B4 -- wiring (static). `_apply_mutation` dispatches `skill_progress` to
+   `skill_progress.apply_skill_progress`; `play_physical.py` calls
+   `record_roll(` and puts `progress` on the verdict event;
+   `_mutation_apply_agenda_step_change` calls `grant_step_roll(`; CLAUDE.md
+   names `skill_progress` as auto-applied; `ARCHITECTURE_DECISIONS.md`'s
+   "Auto-applied mutations" section names it.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -55,6 +82,7 @@ import sqlite3
 import subprocess
 import sys
 import tempfile
+from typing import Optional
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
@@ -392,6 +420,185 @@ def check_a4() -> None:
         fail("A4: play_physical.py does not call rank_modifier(")
 
 
+# --- B1-B4 ---------------------------------------------------------------------
+
+def _b_world(session) -> dict:
+    from world_engine.models import (
+        Character, Conversation, Entity, Session as GameSession, Skill, SkillDefinition, SkillSystem, World,
+    )
+
+    world = World(name="Ranks B", is_active=False)
+    session.add(world)
+    session.flush()
+    pc = Entity(world_id=world.id, type="character", name="Millys")
+    faction = Entity(world_id=world.id, type="faction", name="Secte")
+    session.add(pc)
+    session.add(faction)
+    session.flush()
+    session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
+    system = SkillSystem(world_id=world.id, name="Lame", points_to_rank_2=2)
+    session.add(system)
+    session.flush()
+    definition = SkillDefinition(world_id=world.id, name="Escrime", base_domain="physical", system_id=system.id)
+    session.add(definition)
+    game = GameSession(world_id=world.id, number=1)
+    session.add(game)
+    session.flush()
+    conv = Conversation(world_id=world.id, session_id=game.id, player_id=pc.id)
+    session.add(conv)
+    rows = {}
+    for key, domain, rank, xp, def_id in (("physical", "physical", 1, 8, None), ("agility", "agility", 0, 0, None),
+                                          ("perception", "perception", 5, 3, None),
+                                          ("custom", "physical", 1, 1, definition.id)):
+        row = Skill(character_id=pc.id, domain=domain, rank=rank, xp=xp, skill_definition_id=def_id)
+        session.add(row)
+        rows[key] = row
+    session.commit()
+    return {"world": world.id, "pc": pc.id, "faction": faction.id, "conv": conv.id,
+            **{k: r.id for k, r in rows.items()}}
+
+
+def check_b1(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Skill
+    from world_engine.writes import write_skill_progress
+
+    with Session(engine) as session:
+        ids = _b_world(session)
+
+        def step(key: str, points: int) -> tuple:
+            write_skill_progress(session, skill_id=ids[key], world_id=ids["world"], points=points, changed_by="check")
+            session.commit()
+            row = session.get(Skill, ids[key])
+            return row.rank, row.xp, len(row.change_history)
+
+        table = (("physical", 1, (1, 9, 0)), ("physical", 1, (2, 0, 1)), ("physical", -1, (1, 9, 2)),
+                 ("agility", -1, (0, 0, 0)), ("perception", 1, (5, 4, 0)), ("custom", 1, (2, 0, 1)))
+        for key, points, want in table:
+            got = step(key, points)
+            if got != want:
+                fail(f"B1: {key} {points:+d} gave (rank, xp, history) {got}, want {want}")
+        history = session.get(Skill, ids["physical"]).change_history
+        entry = history[0] if history else {}
+        if (entry.get("rank"), entry.get("xp")) != (1, 9):
+            fail(f"B1: the rank-up history entry is {entry}")
+        try:
+            write_skill_progress(session, skill_id=ids["agility"], world_id=ids["world"], points=0, changed_by="check")
+            fail("B1: zero points accepted")
+        except ValueError:
+            pass
+
+
+def check_b2(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.cockpit.skill_progress import record_roll
+    from world_engine.models import ProposedMutation, Skill
+
+    with Session(engine) as session:
+        ids = _b_world(session)
+
+    def mutations() -> list:
+        with Session(engine) as session:
+            return session.exec(select(ProposedMutation).where(
+                ProposedMutation.mutation_type == "skill_progress",
+                ProposedMutation.world_id == ids["world"])).all()
+
+    got = record_roll(world_id=ids["world"], conversation_id=ids["conv"], skill_id=ids["physical"], band="failure")
+    rows = mutations()
+    if len(rows) != 1:
+        fail(f"B2: one roll wrote {len(rows)} skill_progress mutation(s)")
+    else:
+        mut = rows[0]
+        if (mut.status, mut.proposed_by, mut.payload, mut.applied_at is None) != (
+                "applied", "engine_roll", {"skill_id": ids["physical"], "points": 1, "band": "failure"}, False):
+            fail(f"B2: the mutation is {mut.status}/{mut.proposed_by}/{mut.payload}/{mut.applied_at}")
+    if not got or (got.get("rank_label"), got.get("xp"), got.get("points_to_next"), got.get("ranked_up")) != (
+            "Initié", 9, 10, False):
+        fail(f"B2: record_roll returned {got}")
+    got = record_roll(world_id=ids["world"], conversation_id=ids["conv"], skill_id=ids["physical"], band="success")
+    if not got or (got.get("rank_label"), got.get("ranked_up")) != ("Apprenti", True):
+        fail(f"B2: the threshold roll returned {got}")
+    for skill_id in (ids["perception"], None, "no-such-skill"):
+        if record_roll(world_id=ids["world"], conversation_id=ids["conv"], skill_id=skill_id, band="partial") is not None:
+            fail(f"B2: record_roll on {skill_id!r} returned a state")
+    if len(mutations()) != 2:
+        fail(f"B2: {len(mutations())} mutations after two earning rolls")
+    with Session(engine) as session:
+        if session.get(Skill, ids["perception"]).xp != 3:
+            fail("B2: a Maître row gained a point")
+        bad = ProposedMutation(world_id=ids["world"], source_type="conversation", conversation_id=ids["conv"],
+                               mutation_type="skill_progress", payload={"skill_id": ids["physical"], "points": 0})
+        if not _apply_mutation(bad, session):
+            fail("B2: _apply_mutation accepted 0 points")
+
+
+def check_b3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.models import Agenda, AgendaStep, ProposedMutation, Skill
+
+    with Session(engine) as session:
+        ids = _b_world(session)
+        plan = Agenda(world_id=ids["world"], owner_entity_id=ids["pc"], title="Journée")
+        intrigue = Agenda(world_id=ids["world"], owner_entity_id=ids["faction"], title="Intrigue")
+        session.add(plan)
+        session.add(intrigue)
+        session.flush()
+        steps = [AgendaStep(agenda_id=plan.id, step_order=n, objective=f"o{n}", status=status, domain=domain)
+                 for n, status, domain in ((1, "active", "physical"), (2, "pending", "physical"),
+                                           (3, "pending", None))]
+        steps.append(AgendaStep(agenda_id=intrigue.id, step_order=1, objective="f", status="active", domain="physical"))
+        for st in steps:
+            session.add(st)
+        session.commit()
+
+        def approve(step, action: str) -> Optional:
+            mut = ProposedMutation(world_id=ids["world"], source_type="pass_play", mutation_type="agenda_step_change",
+                                   payload={"step_id": step.id, "action": action, "outcome": "o"})
+            error = _apply_mutation(mut, session)
+            session.commit()
+            return error
+
+        def xp() -> tuple:
+            row = session.get(Skill, ids["physical"])
+            session.refresh(row)
+            return row.rank, row.xp
+
+        for step, action, want in ((steps[0], "complete", (1, 9)), (steps[1], "fail", (2, 0))):
+            error = approve(step, action)
+            if error or xp() != want:
+                fail(f"B3: approving {action} gave {xp()}, error {error!r}, want {want}")
+        session.get(AgendaStep, steps[2].id).status = "active"
+        session.commit()
+        before = xp()
+        if approve(steps[2], "complete") or xp() != before:
+            fail(f"B3: a step without a domain moved the skill to {xp()}")
+        if approve(steps[3], "complete") or xp() != before:
+            fail(f"B3: a faction step moved the skill to {xp()}")
+
+
+def check_b4() -> None:
+    routes = (SRC / "cockpit" / "routes" / "mutations.py").read_text(encoding="utf-8")
+    if '"skill_progress": _skill_progress.apply_skill_progress' not in routes:
+        fail("B4: _apply_mutation does not dispatch skill_progress")
+    play = (SRC / "cockpit" / "play_physical.py").read_text(encoding="utf-8")
+    if "record_roll(" not in play or "'progress': progress" not in play:
+        fail("B4: play_physical.py does not record the roll on the verdict event")
+    if "grant_step_roll(" not in (SRC / "cockpit" / "mutations.py").read_text(encoding="utf-8"):
+        fail("B4: the agenda_step_change applier does not call grant_step_roll(")
+    if "skill_progress" not in (ROOT / "CLAUDE.md").read_text(encoding="utf-8"):
+        fail("B4: CLAUDE.md does not name skill_progress")
+    decisions = (ROOT / "tooling" / "standards" / "ARCHITECTURE_DECISIONS.md").read_text(encoding="utf-8")
+    start = decisions.find("### Auto-applied mutations")
+    end = decisions.find("\n### ", start + 1)
+    if start < 0 or "skill_progress" not in decisions[start:end]:
+        fail("B4: the Auto-applied mutations section does not name skill_progress")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -401,13 +608,18 @@ def main() -> int:
     create_db_and_tables()
     check_a3(engine)
     check_a4()
+    check_b1(engine)
+    check_b2(engine)
+    check_b3(engine)
+    check_b4()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: skill_progression -- v2.15 gives a skill a rank (0-5) and points in place of "
           "its tier, keeps every former tier's roll, lets a world, a system and a skill set "
-          "the points of each rank, and migrates from v2.14 only")
+          "the points of each rank, and migrates from v2.14 only; every roll earns a point, "
+          "auto-applied in Play and given at a day step's approval, and a threshold moves the rank")
     return 0
 
 
````

## Scope OUT

- Any change to `legacy.html` or to how Play shows the verdict (Y1b; TICKET-0069).
- A cap on points per conversation or per day (N2).
- A point from an NPC's roll, or for an NPC (I1).
- Rank trials with requirements (K1's quest half).
- Points for a blocked day step, or from the step change's payload.
- Showing points on the fiche or in the day's account (D); editing thresholds (C).
- Every later brief of this lot.

## Invariants to defend

**Two canon-write paths:** both points go through `_apply_mutation` — the Play one auto-applied under the four documented conditions, the day one inside an approved step change; `write_skill_progress` is called from nowhere else. **`proposed_by='engine'` is never auto-applied:** the tag is `engine_roll`. **The Play stream's request session is read-only:** `record_roll` takes ids and opens its own session. **History is sacred:** every point is an `applied` mutation row; a rank move is archived on the row.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `stream_session_readonly.py`, `single_canon_write.py` or `import_cycle.py` fails.
- `play_physical.py` is not exactly 998 lines after the commit.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand (the extension paragraph still goes right after the « Auto-applied mutations » blockquote), then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- The regenerated `DECISIONS_INDEX.md` shifting many line numbers (the extension paragraph sits mid-file).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/skill_progression.py` → `PASS: skill_progression -- … every roll earns a point, auto-applied in Play and given at a day step's approval, and a threshold moves the rank`.
- `stream_session_readonly.py`, `single_canon_write.py`, `import_cycle.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `day_mutations.py`, `effects_vocab.py`, `claude_md_contract.py`, `decisions_index.py` → `PASS`.
- Mutation tests, each red then reverted: in `write_skill_progress`, `        rank, xp = rank + 1, 0` → `        rank, xp = rank, xp` → `B1`, `B2`, `B3`; `SKILL_PROGRESS_PROPOSED_BY = "engine_roll"` → `"engine"` → `B2`; in `record_roll`, `            if skill is None or skill.rank >= MAX_RANK or db.get(World, world_id) is None:` → `            if skill is None or db.get(World, world_id) is None:` → `B2`; the `grant_step_roll(db, step=step, …)` call replaced by `pass` → `B3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 139/139.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md: one invariant (`skill_progress` is the one live auto-applied mutation). ARCHITECTURE_DECISIONS: the « Auto-applied mutations » extension paragraph and the entry `A ROLL EARNS A POINT (TICKET-0106) -- AUTO-APPLIED IN PLAY, GIVEN AT A DAY STEP'S APPROVAL (BRIEF-0106-b, no schema change)` — all in the diff.
