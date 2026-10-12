<!-- slug: day-events -->
# BRIEF 0119-F — "Journée proposes the event a completed step's objective names -- day_events.py, nothing invented (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-C (C-05)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-E's commit).

- `src/world_engine/day_mutations.py` -> `EMITTED_MUTATION_TYPES: tuple[str, ...] = (` naming five types, `"new_knowledge",` the last
- `src/world_engine/day_mutations.py` -> `def _step_action(outcome: StepOutcome) -> Optional[str]:`
- `src/world_engine/conditions.py` -> `def _since(spec: RequirementSpec, bindings: Bindings) -> tuple[Optional[datetime], Optional[str]]:` and no `leaf_since`
- `tooling/verify/checks/day_mutations.py` -> `EXPECTED_EMITTED_MUTATION_TYPES = (` naming five
- `src/world_engine/cockpit/routes/mutations.py` -> `def _find_event_duplicate(` comparing title and place
- No `src/world_engine/day_events.py`, no `tooling/verify/checks/event_day.py`.

## Facts carried

### R-08 — Journée's emission [M]
Opened: `src/world_engine/day_mutations.py` (:91 five
`EMITTED_MUTATION_TYPES`; :107 `_step_action` -- `complete` on success or
partial, None when blocked; :287 `_EMITTERS`); `tooling/verify/checks/
day_mutations.py:93` (R1/R13 pin the five); `src/world_engine/
cockpit/routes/day.py` (`_finalize_resolution` adds every emitted row; R12:
resolving refuses while a step change is proposed); `src/world_engine/
conditions.py` (`Bindings` :86, `for_step` :152, `and_path_leaves` :229,
`_since` :456 private); `src/world_engine/day_plan.py:130`
(`plan_bindings`); `src/world_engine/condition_forms.py:476`
(`counted_events`); `src/world_engine/cockpit/routes/mutations.py:125`
(`_find_event_duplicate`: a conversation-less event is a duplicate by title
and place).
Consequence: F adds `day_events.py` as the sixth emitter, a public
`conditions.leaf_since`, and puts the day's number in the title.

## Contracts

### C-05 — pre-fill and payload keys
Produced by: BRIEF-0119-C (D adds `scopes`)   Consumed by: D-G
`event_changes.type_changes(db, world_id, view, [(role_id, entity_id)]) ->
[{entity_id, attribute, mode, value}]` (each entity in the effect's role;
an entity state takes the first entity of its value role, or is left out);
`change_line(db, world_id, change) -> str | None` (« Porte : Ouvert ->
oui », « Garnison : Alerte +1 »); `payload_changes(raw) ->
tuple[StateChangeSpec]`. A typed `event_creation` payload carries
`state_changes`; the applier adds `applied_changes` (the system changes) to
an approved payload; D: `scopes` `[{scope_type, scope_id, level}]` (a list,
even empty, replaces the type's).

### C-08 — Journée's objective event
Produced by: BRIEF-0119-F   Consumed by: (TICKET-0121)
`day_events.emit_objective_events(outcome, pass_play, character, world_id,
db) -> list[ProposedMutation]` (`_EMITTERS["event_creation"]`);
`conditions.leaf_since(spec, bindings)`. Title: « objective — jour N ».

## Context

A quest step's objective may be an event (« Chasse : Brakk en chasseur, 3 loups »). When Journée resolves the step as completed, it proposes that very event beside the step change (Bt1): every key from the completion leaf, nothing invented, no model. It is the foundation of TICKET-0121, where the planner writes such objectives.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `day_events.py` (new, C-08): `emit_objective_events` -- the `event` leaves under `all`, on `doer`, not met; role, filters, place, what is lacking, pre-filled changes, the title « objective — jour N »;
   - `day_mutations.py`: `event_creation` the sixth of `EMITTED_MUTATION_TYPES` and `_EMITTERS`; `conditions.py`: `leaf_since`, public;
   - `tooling/verify/checks/day_mutations.py`: six types, `day_events.py` in the day chain; creates check `event_day.py` (EJ1-EJ3); appends the decision entry above the footer.
   The files it touches, exactly:
   - src/world_engine/conditions.py
   - src/world_engine/day_events.py
   - src/world_engine/day_mutations.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/day_mutations.py
   - tooling/verify/checks/event_day.py

````diff
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index ae0bebe..ef1bc60 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -461,6 +461,12 @@ def _since(spec: RequirementSpec, bindings: Bindings) -> tuple[Optional[datetime
     return (at, None) if at is not None else (None, _SINCE_UNBOUND_FR[spec.since])
 
 
+def leaf_since(spec: RequirementSpec, bindings: Bindings) -> tuple[Optional[datetime], Optional[str]]:
+    """F1 for a reader outside the evaluation (TICKET-0119, `day_events`):
+    when an `event` leaf starts counting, or why it cannot."""
+    return _since(spec, bindings)
+
+
 def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
     evaluator = _EVALUATORS.get(spec.type)
     if evaluator is None:
diff --git a/src/world_engine/day_events.py b/src/world_engine/day_events.py
new file mode 100644
index 0000000..3c92484
--- /dev/null
+++ b/src/world_engine/day_events.py
@@ -0,0 +1,128 @@
+"""Journée proposes the event a completed step's objective names (TICKET-0119,
+BRIEF-0119-F; decisions Bt1, M-c and V1 of the conditions series).
+
+A quest step's objective may be an event: « Chasse : Brakk, en chasseur, 3
+loups ». When the day resolves such a step as completed (the dice band
+`success` or `partial`, `day_mutations._step_action`), the step's
+completion condition already says what has to have happened -- so Journée
+proposes that very event, beside the step's `agenda_step_change`, both
+reviewed by the creator (V1: proposing, never applying). Nothing is
+invented and no model is asked: every key comes from the leaf.
+
+For each `event` leaf of the step's completion reached through `all` only
+(Q1: a leaf under `any`, `not` or `at_least` is not guaranteed) whose
+subject is the one who acts (`doer`), and which is not met yet:
+
+- its type is the leaf's (active; a retired one proposes nothing);
+- the character fills the leaf's role, or the type's first active role
+  accepting a character when the leaf says « any role » (none: nothing);
+- each filter of the leaf fills its role (an entity, or a sorte);
+- its place is the leaf's place, when it is an active location;
+- its quantity, when the type counts one, is what the leaf still lacks
+  (its threshold minus what is already counted in its window, at least 1);
+- its changes are pre-filled from the type's effects (M-c), its title is
+  the step's objective and the day's number (« Chasser trois loups — jour
+  4 »: the approval's duplicate guard compares titles and places, and a
+  step may need several days), its description the step's outcome line.
+
+`emit_objective_events(outcome, pass_play, character, world_id, db)` is
+`day_mutations._EMITTERS["event_creation"]`. Reads only; the rows it
+returns are added by the caller (`routes/day._finalize_resolution`).
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session
+
+from .condition_forms import counted_events
+from .conditions import and_path_leaves, for_step, leaf_since, read_condition
+from .day_plan import plan_bindings
+from .day_resolve import StepOutcome, outcome_line
+from .event_changes import type_changes
+from .event_vocab import EVENT_FORM, EventTypeView, role_accepts, type_view
+from .models import AgendaStep, Batch, Character, Entity, PassPlay, ProposedMutation
+
+
+def _role_id(view: EventTypeView, role_id: Optional[str]) -> Optional[str]:
+    if role_id:
+        role = view.role(role_id)
+        return role.id if role is not None and role.status == "active" else None
+    first = next((r for r in view.active_roles() if role_accepts(r, "character")), None)
+    return first.id if first is not None else None
+
+
+def _place(db: Session, world_id: str, entity_id: Optional[str]) -> Optional[str]:
+    place = db.get(Entity, entity_id) if entity_id else None
+    if place is None or place.world_id != world_id or place.type != "location" or place.status != "active":
+        return None
+    return place.id
+
+
+def _payload(db: Session, world_id: str, view: EventTypeView, req, character: Character, step: AgendaStep,
+             outcome: StepOutcome, quantity: Optional[int], title: str) -> Optional[dict]:
+    role_id = _role_id(view, req.value)
+    if role_id is None:
+        return None
+    participants = [{"role_id": role_id, "role": view.role(role_id).name, "entity_id": character.id,
+                     "sorte_id": None, "sorte_name": None, "secret": None}]
+    for f in req.filters:
+        role = view.role(f.role_id)
+        if role is None or role.status != "active":
+            continue
+        participants.append({"role_id": role.id, "role": role.name, "entity_id": f.entity_id,
+                             "sorte_id": f.sorte_id, "sorte_name": None, "secret": None})
+    return {
+        "title": title, "description": outcome_line(outcome), "type_id": view.id,
+        "type_name": view.name, "participants": participants, "quantity": quantity,
+        "location_id": _place(db, world_id, req.target_entity_id),
+        "state_changes": type_changes(db, world_id, view, [(p["role_id"], p["entity_id"]) for p in participants]),
+    }
+
+
+def emit_objective_events(
+    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
+) -> list[ProposedMutation]:
+    """The events a completed step's objective names (see the module
+    docstring), each one `event_creation` at `status='proposed'`."""
+    from .day_mutations import _step_action
+
+    if _step_action(outcome) != "complete":
+        return []
+    step = db.get(AgendaStep, outcome.agenda_step_id)
+    completion = read_condition(db, role="completion", agenda_step_id=outcome.agenda_step_id)
+    if step is None or completion is None:
+        return []
+    bindings = for_step(plan_bindings(step.agenda_id, character, db), step)
+    batch = db.get(Batch, pass_play.batch_id)
+    title = f"{step.objective} — jour {batch.day_number}" if batch is not None else step.objective
+    mutations: list[ProposedMutation] = []
+    for req in and_path_leaves(completion):
+        if req.type != EVENT_FORM or req.subject_role != "doer":
+            continue
+        view = type_view(db, req.target_key)
+        if view is None or view.world_id != world_id or view.status != "active":
+            continue
+        since_at, unbound = leaf_since(req, bindings)
+        counted = 0 if unbound else sum(q or 1 for _e, _f, q in counted_events(db, req, character.id, since_at))
+        lacking = (req.threshold or 1) - counted
+        if lacking <= 0:
+            continue
+        payload = _payload(db, world_id, view, req, character, step, outcome,
+                           lacking if view.counts_quantity else None, title)
+        if payload is None:
+            continue
+        mutations.append(ProposedMutation(
+            world_id=world_id,
+            source_type="pass_play",
+            pass_play_id=pass_play.id,
+            mutation_type="event_creation",
+            target_table="event",
+            payload=payload,
+            status="proposed",
+            proposed_by="local_ai",
+            rationale=(f"step {outcome.step_order} ({outcome.objective}) completed -- its objective is the event "
+                       f"« {view.name} »"),
+        ))
+    return mutations
diff --git a/src/world_engine/day_mutations.py b/src/world_engine/day_mutations.py
index c842a2b..591d188 100644
--- a/src/world_engine/day_mutations.py
+++ b/src/world_engine/day_mutations.py
@@ -75,6 +75,11 @@ DELIBERATE duplicate of `cockpit/mutations.py`'s `_knowledge_already_
 applied`, not a call into it: that guard is conversation-scoped and scans
 APPLIED rows, a different question with a different key from "is this
 fact already sitting in the open review queue for this world."
+
+`event_creation` (TICKET-0119, BRIEF-0119-F, Bt1): a completed step whose
+completion condition names an event the character has to have lived
+proposes that event, exactly as the condition's leaf describes it
+(`day_events.emit_objective_events`) -- nothing invented, no model asked.
 """
 
 from __future__ import annotations
@@ -84,12 +89,14 @@ from typing import Callable, Optional
 from sqlmodel import Session, select
 
 from .conditions import and_path_leaves, read_condition
+from .day_events import emit_objective_events
 from .day_resolve import BLOCKED_BAND, StepOutcome, outcome_line
 from .models import Character, Fact, PassPlay, ProposedMutation
 from .prose_render import fact_text
 
 EMITTED_MUTATION_TYPES: tuple[str, ...] = (
     "knowledge_change", "relation_change", "agenda_step_change", "entity_creation", "new_knowledge",
+    "event_creation",
 )
 
 # The rendezvous deepens a pre-existing knowledge row to this level on a
@@ -290,6 +297,9 @@ _EMITTERS: dict[str, Callable[[StepOutcome, PassPlay, Character, str, Session],
     "relation_change": _emit_relation_change,
     "entity_creation": _emit_entity_creation,
     "new_knowledge": _emit_new_knowledge,
+    # TICKET-0119 (BRIEF-0119-F, Bt1): a completed step whose objective is an
+    # event proposes that event (`day_events.py`).
+    "event_creation": emit_objective_events,
 }
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 35b6b16..825915f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19606,6 +19606,31 @@ shape beside the former one, the two lists after the briefing), delivered by
 `apply_ticket_0119_tick_prompt.py` fragment by fragment: the creator's
 edits are kept.
 
+## JOURNÉE PROPOSES THE EVENT A COMPLETED STEP'S OBJECTIVE NAMES (TICKET-0119) -- `day_events.py`, NOTHING INVENTED (BRIEF-0119-f, no schema change)
+
+**Bt1.** A quest step's objective may be an event (« Chasse : Brakk en
+chasseur, 3 loups »). When the day resolves the step as completed, its
+completion condition already says what has to have happened, so Journée
+proposes that very event beside the step's `agenda_step_change` -- both
+reviewed by the creator (V1). No model is asked: every key comes from the
+leaf. This is the foundation TICKET-0121 builds on (Journée proposing a
+quest, B-b): the planner will write such objectives.
+
+**Which leaves.** An `event` leaf of the completion reached through `all`
+only (Q1), on the one who acts (`doer`), not met yet. The character fills
+the leaf's role (« any role »: the type's first role accepting a
+character), each filter fills its role, the leaf's place is the event's
+when it is an active location, and when the type counts a quantity the
+event carries what the leaf still lacks in its window. Its changes are
+pre-filled from the type's effects (M-c).
+
+**The title.** The step's objective and the day's number: the approval's
+duplicate guard compares titles and places, and a step may take several
+days.
+
+**Replay.** `resolve_day` already refuses while the standing agenda holds a
+proposed step change (BB1), so a day is never proposed twice.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/day_mutations.py b/tooling/verify/checks/day_mutations.py
index bc65cb2..20591d3 100644
--- a/tooling/verify/checks/day_mutations.py
+++ b/tooling/verify/checks/day_mutations.py
@@ -5,7 +5,8 @@ text only, no DB — same FAILURES/fail()/`_parse`/`_rel` idiom as
 
 R1 (bijection, corrected vocabulary): `EMITTED_MUTATION_TYPES` in
 `day_mutations.py` equals `("knowledge_change", "relation_change",
-"agenda_step_change", "entity_creation")` exactly, and `_EMITTERS`'s key
+"agenda_step_change", "entity_creation", "new_knowledge", "event_creation")`
+exactly, and `_EMITTERS`'s key
 set equals it, both directions (the `_SOURCE_LOOKUPS` precedent,
 `schedule_reads.py`).
 R2: `"npc_move"` appears nowhere in `day_mutations.py`, `day_resolve.py` or
@@ -52,7 +53,8 @@ type/status, raises a 409, and is actually called from `resolve_day`.
 
 R13 (BRIEF-0078-c, D3): `_EMITTERS`' key set equals `EMITTED_MUTATION_TYPES`
 in both directions (re-asserts R1 now that the vocabulary is five-valued)
-and is exactly five-valued.
+and is exactly six-valued since TICKET-0119 (BRIEF-0119-F: `event_creation`,
+a completed step's objective event, `day_events.py`).
 R14: `_emit_new_knowledge` exists; its body references `BLOCKED_BAND` and
 returns early (`outcome.band != BLOCKED_BAND` -> `[]`) when the band does
 not match; it references `_BLOCKED_LEAD_LEVEL` and contains no bare
@@ -86,12 +88,16 @@ DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
 MUTATIONS_ROUTE_FILE = SRC / "cockpit" / "routes" / "mutations.py"
 JOURNEE_SVELTE_FILE = FRONTEND_SRC / "journee" / "Journee.svelte"
 
+DAY_EVENTS_FILE = SRC / "day_events.py"
+
 DAY_CHAIN_FILES = (
     DAY_MUTATIONS_FILE, DAY_RESOLVE_FILE, DAY_PLAN_FILE, DAY_CONCORDANCE_FILE, DAY_EXTRACT_FILE,
+    DAY_EVENTS_FILE,
 )
 
 EXPECTED_EMITTED_MUTATION_TYPES = (
     "knowledge_change", "relation_change", "agenda_step_change", "entity_creation", "new_knowledge",
+    "event_creation",
 )
 REMOVED_MUTATION_TYPES = ("resource_change", "agenda_creation")
 
@@ -182,8 +188,8 @@ def check_bijection() -> None:
             f"day_mutations R1: _EMITTERS keys {sorted(set(emitters_keys))!r} do not match "
             f"EMITTED_MUTATION_TYPES {sorted(set(constant_tuple))!r}"
         )
-    if len(constant_tuple) != 5:
-        fail(f"day_mutations R13: EMITTED_MUTATION_TYPES has {len(constant_tuple)} entries, expected 5")
+    if len(constant_tuple) != 6:
+        fail(f"day_mutations R13: EMITTED_MUTATION_TYPES has {len(constant_tuple)} entries, expected 6")
 
 
 def check_npc_move_absent() -> None:
diff --git a/tooling/verify/checks/event_day.py b/tooling/verify/checks/event_day.py
new file mode 100644
index 0000000..7021f2c
--- /dev/null
+++ b/tooling/verify/checks/event_day.py
@@ -0,0 +1,238 @@
+"""G1 check for TICKET-0119 -- Journée proposes the event a completed step's objective names.
+
+BRIEF-0119-F's rules (Bt1, M-c and V1 of the conditions series).
+
+EJ1 -- the proposal (fixture). A step whose completion is « Chasse, Brakk
+   as Chasseur, 3, a Proie filter on the sorte Loup, in the Forêt, since the
+   step », resolved `success` with one wolf already counted since the step
+   began, proposes one `event_creation` at `status='proposed'`,
+   `source_type='pass_play'`: its type, Brakk in the role Chasseur, the
+   sorte in Proie, the quantity still lacking (2), the Forêt, the step's
+   objective and the day's number as its title, and the type's effect pre-filled in
+   `state_changes`.
+EJ2 -- nothing invented (fixture). Nothing is proposed for: a `failure` or
+   `blocked` band; a leaf already met; a leaf under `any`; a leaf on the
+   giver rather than the one who acts; a step with no completion. (A
+   condition never names a retired type: retiring one is refused while a
+   condition names it, `event_journal.py` EA3.) A leaf saying « any role » takes the type's first role
+   accepting a character.
+EJ3 -- wiring (static). `day_mutations._EMITTERS["event_creation"]` is
+   `emit_objective_events`; `day_events.py` constructs `ProposedMutation`
+   with `status="proposed"` only and calls no writer (`writes` is not
+   imported).
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+
+
+def _fixture(engine) -> dict:
+    from datetime import UTC, datetime, timedelta
+
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Batch, Character, Entity, Location, PassPlay, Session as PlaySession, World
+    from world_engine.writes.attributes import DefinitionSpec, write_attribute_definition
+    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        world = World(name="Journée", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("brakk", "character", "Brakk"), ("odo", "character", "Odo"),
+                                ("foret", "location", "Forêt")):
+            row = Entity(world_id=world.id, type=kind, name=name)
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "brakk" else "npc")
+                   if kind == "character" else Location(id=row.id))
+        fatigue = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Fatigue", kind="integer", holder_types=("character",), default=0))
+        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Chasse", counts_quantity=True,
+            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True)),
+            effects=(EffectSpec("Chasseur", fatigue.id, 1, "add"),)))
+        ids.update(chasse=chasse.id, fatigue=fatigue.id,
+                   loup=write_sorte(db, world_id=world.id, name="Loup").id)
+        for role in type_view(db, chasse.id).roles:
+            ids[role.name] = role.id
+        play = PlaySession(world_id=world.id, number=1)
+        db.add(play)
+        db.flush()
+        batch = Batch(session_id=play.id, day_number=4)
+        db.add(batch)
+        db.flush()
+        pass_play = PassPlay(batch_id=batch.id, session_id=play.id, character_id=ids["brakk"], declared_action="a")
+        db.add(pass_play)
+        db.flush()
+        ids["pass_play"], ids["session"] = pass_play.id, play.id
+        ids["started"] = datetime.now(UTC) - timedelta(hours=1)
+        db.commit()
+    return ids
+
+
+def _step(db, ids: dict, tree_dict) -> str:
+    from world_engine.conditions import node_from_dict
+    from world_engine.models import Agenda, AgendaStep
+    from world_engine.writes.conditions import write_condition
+
+    agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["brakk"], title="t", status="active")
+    db.add(agenda)
+    db.flush()
+    step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="Chasser trois loups", status="active",
+                      started_at=ids["started"])
+    db.add(step)
+    db.flush()
+    if tree_dict is not None:
+        write_condition(db, world_id=ids["world"], role="completion", tree=node_from_dict(tree_dict),
+                        agenda_step_id=step.id)
+    db.commit()
+    return step.id
+
+
+def _leaf(ids: dict, **fields) -> dict:
+    leaf = {"op": "leaf", "type": "event", "subject_role": "doer", "target_key": ids["chasse"],
+            "value": ids["Chasseur"], "threshold": 3, "target_entity_id": ids["foret"], "since": "step",
+            "filters": [{"role_id": ids["Proie"], "sorte_id": ids["loup"]}]}
+    leaf.update(fields)
+    return leaf
+
+
+def _emit(db, ids: dict, step_id: str, band: str = "success") -> list:
+    from world_engine.day_events import emit_objective_events
+    from world_engine.day_resolve import StepOutcome
+    from world_engine.models import Character, PassPlay
+
+    outcome = StepOutcome(agenda_step_id=step_id, step_order=1, objective="Chasser trois loups", domain=None,
+                          verdict=None, band=band, requirement_verdicts=(), canon_ids=())
+    return emit_objective_events(outcome, db.get(PassPlay, ids["pass_play"]), db.get(Character, ids["brakk"]),
+                                 ids["world"], db)
+
+
+def check_ej1(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.writes.events import EventSpec, ParticipantSpec, write_event
+
+    with Session(engine) as db:
+        step_id = _step(db, ids, _leaf(ids))
+        write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
+            type_id=ids["chasse"], title="Un loup", quantity=1, location_id=ids["foret"], participants=(
+                ParticipantSpec(ids["Chasseur"], entity_id=ids["brakk"]),
+                ParticipantSpec(ids["Proie"], sorte_id=ids["loup"]))))
+        db.commit()
+        rows = _emit(db, ids, step_id)
+        payload = rows[0].payload if len(rows) == 1 else {}
+        got = (len(rows), rows[0].status if rows else None, rows[0].source_type if rows else None,
+               payload.get("type_id"), [(p["role_id"], p["entity_id"], p["sorte_id"]) for p in
+                                        payload.get("participants", [])],
+               payload.get("quantity"), payload.get("location_id"), payload.get("title"),
+               payload.get("state_changes"))
+        want = (1, "proposed", "pass_play", ids["chasse"],
+                [(ids["Chasseur"], ids["brakk"], None), (ids["Proie"], None, ids["loup"])], 2, ids["foret"],
+                "Chasser trois loups — jour 4",
+                [{"entity_id": ids["brakk"], "attribute": ids["fatigue"], "mode": "add", "value": 1}])
+        if got != want:
+            fail(f"EJ1: the proposal is {got}")
+
+
+def check_ej2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as db:
+        cases = {
+            "a failure": (_leaf(ids), "failure"),
+            "a blocked step": (_leaf(ids), "blocked"),
+            "a leaf already met": (_leaf(ids, threshold=1, since="always"), "success"),
+            "a leaf under any": ({"op": "any", "children": [_leaf(ids), _leaf(ids, threshold=9)]}, "success"),
+            "a leaf on the giver": (_leaf(ids, subject_role="giver"), "success"),
+            "no completion": (None, "success"),
+        }
+        for label, (tree, band) in cases.items():
+            step_id = _step(db, ids, tree)
+            rows = _emit(db, ids, step_id, band)
+            if rows:
+                fail(f"EJ2: {label} proposed {[r.payload for r in rows]}")
+        step_id = _step(db, ids, _leaf(ids, value=None, filters=[], target_entity_id=None, since="always",
+                                       threshold=9))
+        rows = _emit(db, ids, step_id)
+        roles = [p["role_id"] for p in rows[0].payload["participants"]] if len(rows) == 1 else None
+        if roles != [ids["Chasseur"]]:
+            fail(f"EJ2: an « any role » leaf gave roles {roles}")
+
+
+def check_ej3() -> None:
+    tree = ast.parse((SRC / "day_mutations.py").read_text(encoding="utf-8"))
+    emitters = next((n.value for n in ast.walk(tree) if isinstance(n, ast.AnnAssign)
+                     and isinstance(n.target, ast.Name) and n.target.id == "_EMITTERS"), None)
+    found = None
+    if isinstance(emitters, ast.Dict):
+        for key, value in zip(emitters.keys, emitters.values):
+            if isinstance(key, ast.Constant) and key.value == "event_creation" and isinstance(value, ast.Name):
+                found = value.id
+    if found != "emit_objective_events":
+        fail(f"EJ3: _EMITTERS['event_creation'] is {found}")
+    events = ast.parse((SRC / "day_events.py").read_text(encoding="utf-8"))
+    built = 0
+    for node in ast.walk(events):
+        if isinstance(node, ast.ImportFrom) and node.module and "writes" in node.module:
+            fail(f"EJ3: day_events.py imports {node.module}")
+        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
+            built += 1
+            status = next((k.value for k in node.keywords if k.arg == "status"), None)
+            if not (isinstance(status, ast.Constant) and status.value == "proposed"):
+                fail("EJ3: day_events.py builds a ProposedMutation not at status 'proposed'")
+    if built == 0:
+        fail("EJ3: day_events.py builds no ProposedMutation")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    for name, rule in (("EJ1", lambda: check_ej1(engine, ids)), ("EJ2", lambda: check_ej2(engine, ids)),
+                       ("EJ3", check_ej3)):
+        try:
+            rule()
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_day -- a completed step whose objective is an event proposes that event, as its leaf says "
+          "it: its type, the one who acts in his role, its filters, its place, what is still lacking, its changes "
+          "pre-filled; nothing else is invented")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- Journée proposing a quest, its planner writing objectives and proposing types (B-b) -- TICKET-0121.
- An event for a failed step (its failure condition): nothing is proposed.
- Every later brief of this lot: BRIEF-0119-G.

## Invariants to defend

V1 of 0075 (the day chain proposes, never applies): `day_events.py` builds rows at `status='proposed'` only and imports no writer (EJ3, `day_mutations.py` R3/R4). BB1: a day is never resolved twice while its step change is in review, so its event is never proposed twice.

## Decision rights

STOP:
- The emitter would apply or write anything, or call a model.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/event_day.py` -> `PASS`.
- `python tooling/verify/checks/day_mutations.py` -> `PASS`.
- `python tooling/verify/checks/day_plan.py` -> `PASS`.
- `python tooling/verify/checks/conditions.py` -> `PASS`.
- `python tooling/verify/checks/event_conditions.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (161 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EJ1** -- `day_events.py emit_objective_events`: `        lacking = (req.threshold or 1) - counted` -> `        lacking = req.threshold or 1`
  - **EJ2** -- `day_events.py emit_objective_events`: `        if req.type != EVENT_FORM or req.subject_role != "doer":` -> `        if req.type != EVENT_FORM:`
  - **EJ3** -- `day_mutations.py _EMITTERS`: `    "event_creation": emit_objective_events,` -> `    "event_creation": lambda *a: [],`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
