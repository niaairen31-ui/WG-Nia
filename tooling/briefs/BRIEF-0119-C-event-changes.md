<!-- slug: event-changes -->
# BRIEF 0119-C — "An event writes what it changes in the world, all or none -- its type pre-fills the changes; record_event, write_system_state (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-A (C-01, C-02), BRIEF-0119-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-B's commit).

- `src/world_engine/writes/events.py` -> `def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:` and `class EventSpec:` with no `changes`
- `src/world_engine/cockpit/mutations.py` -> `        write_event(db, world_id=mut.world_id, spec=spec, created_by=f"mutation:{mut.id}")` inside `_mutation_apply_event_creation`
- `src/world_engine/gathering.py` -> `def close_open_memberships(entity_id: str, db: Session) -> list[GatheringMember]:`
- `src/world_engine/event_analysis.py` -> `def typed_payload(` returning no `state_changes`
- `src/world_engine/writes/attributes.py` -> `def write_attribute_value(` taking `event_id` (BRIEF-0119-A's)
- No `src/world_engine/writes/entity_states.py`, no `src/world_engine/event_changes.py`, no `tooling/verify/checks/event_changes.py`.

## Facts carried

### R-02 — the state of the world and its writer [M]
Opened: `src/world_engine/models/canon_attribute.py` (`AttributeChange`
:123 -- value before and after, `kind`, `changed_by`, `changed_at` :141;
no `event_id`); `src/world_engine/attributes.py` (`SYSTEM_ATTRIBUTES` :83:
`sys:vital_status` -- characters, alive/dead/missing/unknown --,
`sys:status` -- every entity, active/inactive/destroyed/missing --,
`sys:magic_status` -- locations; `attribute_view` :167, `world_attributes`
:190, `current_value` :245); `src/world_engine/writes/attributes.py`
(`_clean_update` :195 keeps a choice a value or a condition holds;
`set_attribute_status` :280 refuses retiring while a condition names it;
`write_attribute_value` :338 -- `correction` or `changement`, an unchanged
value writes nothing; :30 « a system attribute is never written here »).
Consequence: A gives `attribute_change` its `event_id` and extends the
in-use guards to effects; system states need their own writer (R-03).

### R-03 — who writes the vital state and the status [M]
Opened: `src/world_engine/cockpit/crud/entities.py` (:138 the
`vital_status` field of the character form; `update_entity` writes it by
`setattr`; :829 an entity leaving `active` closes its gathering seats --
INV-25); `src/world_engine/cockpit/mutations.py:434`
(`_mutation_apply_status_change` sets `entity.status`, closes nothing);
`src/world_engine/gathering.py:283` (`close_open_memberships`, never
commits; `gathering` imports `analyzer`, which imports `writes`).
Enumeration (c-1 below): no play path writes `vital_status`.
Consequence: C adds `writes/entity_states.write_system_state`, which closes
the seats (importing `gathering` inside the function), and never reactivates
a location (a zone promotion is the fiche's, TICKET-0101).

### R-04 — the journal's writer and the applier [M]
Opened: `src/world_engine/writes/events.py` (`EventSpec` :82;
`clean_event` :218; `_knows` :250 and `_add_participants` :267 return
nothing; `write_event` :288 returns the event; `write_event_update` :310);
`src/world_engine/event_payloads.py` (`_typed` :88 reads `type_id` /
`new_type`, participants, quantity, place -- no scopes, no changes;
`spec_from_payload` :132); `src/world_engine/cockpit/mutations.py:694`
(`_mutation_apply_event_creation` -> `write_event`);
`src/world_engine/cockpit/routes/mutations.py:597`
(`_approve_apply_and_commit`: one savepoint, an applier's error string rolls
it back).
Consequence: C writes the changes inside `write_event` (one writer, F1) and
returns every row (`record_event`) for Lore; D reads a card's `scopes`.

### R-05 — Play's typed payload [M]
Opened: `src/world_engine/event_analysis.py` (`analysis_vocabulary` :57,
`AnalysisVocabulary.prompt_values` :52, `typed_payload` :130: `{title,
description, type_id | None, type_name, participants [{role_id, role,
entity_id, sorte_id, sorte_name, secret}], quantity, location_id,
new_type?}`).
Consequence: the tick reuses it whole (E); C adds `state_changes` to it.

### R-10 — the lists this lot extends [M]
Opened: `tooling/verify/canon_write_policy.txt` (one line per writer);
`tooling/verify/checks/single_canon_write.py` (docstring: the named
full-replace deletes); `src/world_engine/writes/worlds.py:65`
(`_DIRECT_WORLD_SCOPED_DELETES`, :82 the event tables) and
`tooling/verify/checks/world_cascade.py` (W1/W3: every world table in the
list and the fixture); `tooling/verify/checks/attributes.py:123` (AA1/AA6 pin
`attribute_change`'s columns); `src/world_engine/schema_version.py:15`
(v2.25); `.claude/rules/gatherings.md` (INV-25).

## Contracts

### C-02 — a type's effects (writer and reads)
Produced by: BRIEF-0119-A   Consumed by: B, C
`writes.event_types.EffectSpec(role, attribute, value, mode="set")` -- `role`
a role's NAME; `attribute` a definition id or a system key; `value` a choice
key, an integer, or (entity state) another role's NAME;
`EventTypeSpec.effects`; `EFFECT_SYSTEM_KEYS = ("sys:vital_status",
"sys:status")`; `MAX_EFFECTS = 8`. Refused (`ValueError`): an unknown or
retired state, a system state outside `EFFECT_SYSTEM_KEYS`, a role holding
no entity, a state applying to no entity type the role accepts, a value not
of the state's kind, `add` on a non-integer, an entity value naming the
same role or a role the state may not name, one role and state twice.
`event_vocab.EffectView(role_id, attribute, mode, value_kind ("choice" |
"integer" | "role"), value, position)`, `effect_view(row)`,
`EventTypeView.effects`. `write_attribute_value(..., event_id=None)` -- an
`event_id` only on a `changement`. A definition an effect names is not
retired, its kind does not change, its choice an effect names stays.

### C-04 — an event's changes (the journal's writer)
Produced by: BRIEF-0119-C   Consumed by: D-G
`writes.events.StateChangeSpec(entity_id, attribute, value, mode="set")`;
`EventSpec.changes` (default `()`); `WrittenEvent(event, fact, rows [(table,
id, "created" | "updated")], system_changes [{entity_id, attribute, before,
after}])`; `record_event(db, *, world_id, spec, created_by) ->
WrittenEvent`; `write_event` = `record_event(...).event`. Cleaning (all or
nothing): an active state an event may change, an entity of the world it
applies to (a vital state on a character), a value of its kind (`add` on an
integer; an entity value of a type the state names, or None), one state of
one entity once, never a location made active again; a correction
(`write_event_update`) carrying a change is refused. A definition's change:
`write_attribute_value(kind="changement", event_id=event.id)`, `add` summed
on the current value. `writes.entity_states.write_system_state(db, *,
world_id, entity_id, key, value) -> (before, after) | None` --
`SYSTEM_STATE_KEYS`; closes the seats of an entity leaving `active` or a
character leaving `alive`.

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

## Context

An event now writes what it changes (M-c): its type's effects, made concrete on its participants, pre-fill its changes; the creator keeps, edits or drops each; the journal's one writer writes them with the event, all or none (F1). A world's state changes as a `changement` naming its event; the vital state and the status (E1) through a new commit-free writer that leaves gatherings like the creator's CRUD (INV-25). Play's proposals carry their changes from this brief on.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `writes/events.py` (C-04): `StateChangeSpec`, `EventSpec.changes`, `WrittenEvent`, `_clean_change(s)`, `_apply_changes`, `record_event` (`write_event` its thin form); `_knows`, `_add_participants`, `_write_scopes` return what they wrote; a correction carrying a change is refused;
   - `writes/entity_states.py` (new): `write_system_state`, `SYSTEM_STATE_KEYS`; `event_changes.py` (new, C-05): `type_changes`, `change_line`, `payload_changes`;
   - `event_payloads.py` reads `state_changes`; `cockpit/mutations.py`'s applier calls `record_event` and keeps `applied_changes`; `event_analysis.typed_payload` pre-fills `state_changes`; `cockpit/crud/events.py`: `StateChangeBody`, `EventBody.state_changes`;
   - `writes/__init__.py` exports; `canon_write_policy.txt` (`record_event` replaces `write_event`'s line; `write_system_state`); `.claude/rules/gatherings.md` INV-25 names an event's state change;
   - creates check `event_changes.py` (EM1-EM6); appends the decision entry above the footer.
   The files it touches, exactly:
   - .claude/rules/gatherings.md
   - src/world_engine/cockpit/crud/events.py
   - src/world_engine/cockpit/mutations.py
   - src/world_engine/event_analysis.py
   - src/world_engine/event_changes.py
   - src/world_engine/event_payloads.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/entity_states.py
   - src/world_engine/writes/events.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/event_changes.py

````diff
diff --git a/.claude/rules/gatherings.md b/.claude/rules/gatherings.md
index 821cbef..d426ac6 100644
--- a/.claude/rules/gatherings.md
+++ b/.claude/rules/gatherings.md
@@ -18,6 +18,7 @@ paths:
   never inside `generate_gatherings`. [no check]
 - **INV-25** Creator-CRUD edits that change a character's
   `current_location_id`, or set an entity's `status` to a non-active value,
+  and an event's change of a status or vital state (`write_system_state`),
   close that entity's open `gathering_member` rows via
   `close_open_memberships` (gatherings are not canon — no `_apply_mutation`,
   no `change_history`). A location change also attaches the entity to the
diff --git a/src/world_engine/cockpit/crud/events.py b/src/world_engine/cockpit/crud/events.py
index d9e9804..07e9268 100644
--- a/src/world_engine/cockpit/crud/events.py
+++ b/src/world_engine/cockpit/crud/events.py
@@ -7,7 +7,9 @@ by role (an entity or a sorte, each entity keeping it secret or not, X1),
 and who learns it besides them (its fact's scopes, the type's by default,
 W1). `POST /api/events` writes one, `PUT /api/events/{id}` corrects one --
 its type stays and no participant is taken away -- both through
-`writes.events`; every refusal is a 422.
+`writes.events`; every refusal is a 422. Since TICKET-0119 (BRIEF-0119-C,
+M-c) a new event carries its `state_changes` -- what it changes in the
+world, written with it, all or none; a correction carries none.
 
 `_event_dict` is what the journal shows: the participants with their role
 and their secret (read from their own knowledge row), the scopes with what
@@ -16,7 +18,7 @@ they name.
 
 from __future__ import annotations
 
-from typing import Optional
+from typing import Optional, Union
 
 from fastapi import Depends, HTTPException
 from pydantic import BaseModel, Field
@@ -29,6 +31,7 @@ from ...writes.events import (
     EventScopeSpec,
     EventSpec,
     ParticipantSpec,
+    StateChangeSpec,
     event_fact,
     write_event,
     write_event_update,
@@ -100,6 +103,15 @@ class EventScopeBody(BaseModel):
     level: str = "knows"
 
 
+class StateChangeBody(BaseModel):
+    """One change of a new event (M-c): `value` a choice key, an integer,
+    an entity id, or None."""
+    entity_id: str
+    attribute: str
+    mode: str = "set"
+    value: Optional[Union[int, str]] = None
+
+
 class EventBody(BaseModel):
     title: str
     description: Optional[str] = None
@@ -109,6 +121,7 @@ class EventBody(BaseModel):
     participants: list[ParticipantBody] = Field(default_factory=list)
     # None: the type's scopes (W1); a list, even empty: exactly these.
     scopes: Optional[list[EventScopeBody]] = None
+    state_changes: list[StateChangeBody] = Field(default_factory=list)
 
 
 def event_spec(body: EventBody) -> EventSpec:
@@ -118,6 +131,7 @@ def event_spec(body: EventBody) -> EventSpec:
         participants=tuple(ParticipantSpec(p.role_id, p.entity_id, p.sorte_id, p.secret) for p in body.participants),
         scopes=None if body.scopes is None else tuple(EventScopeSpec(s.scope_type, s.scope_id, s.level)
                                                        for s in body.scopes),
+        changes=tuple(StateChangeSpec(c.entity_id, c.attribute, c.value, c.mode) for c in body.state_changes),
     )
 
 
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index 012a4c7..1ceb544 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -60,7 +60,6 @@ from ..writes import (
     write_agenda_step,
     write_agenda_step_status,
     write_character_location,
-    write_event,
     write_faction_role,
     write_goal_agenda_link,
     write_knowledge,
@@ -70,6 +69,7 @@ from ..writes import (
     write_npc_goal_status,
     write_relation,
 )
+from ..writes.events import record_event
 from ..writes.zone_promotion import promotion_preview
 from ..zone_rules import ZoneRefusal, require_visitable
 from .routes import mutations as _routes_mutations
@@ -696,15 +696,22 @@ def _mutation_apply_event_creation(mut: ProposedMutation, payload: dict, db: Ses
     analyzer) or untyped (the world tick, earlier proposals) -- is read into
     an `EventSpec` (`event_payloads.spec_from_payload`) and written by the
     journal's one writer, its fact, scopes and participants' knowledge with
-    it. Any refusal of the writer is "Needs attention", nothing written."""
+    it. Any refusal of the writer is "Needs attention", nothing written.
+    Since TICKET-0119 (BRIEF-0119-C, M-c) its `state_changes` are written
+    with it, all or none (F1); a system state it changed keeps its before
+    and after in the payload (`applied_changes`), since its column keeps no
+    history."""
     if not payload.get("title"):
         return "event_creation: payload must contain title"
     session_id, batch_id = provenance(db, mut)
     try:
         spec = spec_from_payload(db, mut.world_id, payload, session_id=session_id, batch_id=batch_id)
-        write_event(db, world_id=mut.world_id, spec=spec, created_by=f"mutation:{mut.id}")
+        written = record_event(db, world_id=mut.world_id, spec=spec, created_by=f"mutation:{mut.id}")
     except ValueError as exc:
         return f"event_creation: {exc}"
+    if written.system_changes:
+        mut.payload = {**payload, "applied_changes": written.system_changes}
+        db.add(mut)
     return None
 
 
diff --git a/src/world_engine/event_analysis.py b/src/world_engine/event_analysis.py
index a8c67a0..eb5ad63 100644
--- a/src/world_engine/event_analysis.py
+++ b/src/world_engine/event_analysis.py
@@ -19,6 +19,11 @@ it is created with the event. A payload with neither `event_type` nor
 `new_type` is the former, untyped shape (`event_payloads` types it by its
 domain).
 
+Since TICKET-0119 (BRIEF-0119-C, M-c), a payload of an existing type
+carries its `state_changes`: its type's effects made concrete on its
+participants (`event_changes.type_changes`), which the creator keeps, edits
+or drops on the card. A proposed type has no effects yet.
+
 Reads only; writes nothing.
 """
 
@@ -30,6 +35,7 @@ from typing import Any, Optional
 
 from sqlmodel import Session
 
+from .event_changes import type_changes
 from .event_proposals import type_definition, type_spec
 from .event_vocab import EventTypeView, role_accepts, world_event_types, world_sortes
 from .fact_refs import CodedRefs, code_refs
@@ -159,4 +165,7 @@ def typed_payload(db: Session, world_id: str, payload: dict, vocab: AnalysisVoca
     }
     if definition is not None:
         out["new_type"] = definition
+    else:
+        out["state_changes"] = type_changes(db, world_id, vocab.types[type_id],
+                                            [(p["role_id"], p["entity_id"]) for p in participants])
     return out
diff --git a/src/world_engine/event_changes.py b/src/world_engine/event_changes.py
new file mode 100644
index 0000000..6e93d11
--- /dev/null
+++ b/src/world_engine/event_changes.py
@@ -0,0 +1,90 @@
+"""What an event's type proposes it changes in the world (TICKET-0119,
+BRIEF-0119-C; decisions M-c, D3 and E1 of the conditions series).
+
+An event type declares its effects (`event_type_effect`, « Ouvrir : Cible
+-> Ouvert = oui »). When an event of it is proposed -- by Play's analyzer,
+the world tick, Journée, Lore or the creator's own journal -- its effects
+are made concrete on the event's participants and PRE-FILL the event's
+changes, which the creator keeps, edits or drops before the event is
+written (`writes.events`, F1: one refused and nothing is written).
+
+- `type_changes(db, world_id, view, participants)` : the changes a type's
+  effects make on `participants` -- (role id, entity id or None) pairs --
+  as payload dicts `{entity_id, attribute, mode, value}`: one per entity in
+  the effect's role (a sorte changes nothing: there is no one to change);
+  an entity state takes the first entity in its value role, and is left
+  out when that role has none.
+- `change_line(db, world_id, change)` : one change in French, for a card --
+  « Porte : Ouvert -> oui », « Garnison : Alerte + 1 », « Ivo : État vital
+  -> mort »; None when the change names nothing the world has.
+- `payload_changes(raw)` : a payload's `state_changes` read into the
+  writer's `StateChangeSpec`s (the writer cleans them).
+
+Reads only; writes nothing.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Iterable, Optional
+
+from sqlmodel import Session
+
+from .attributes import applies_to, attribute_view, value_label
+from .event_vocab import EventTypeView
+from .models import Entity
+from .writes.events import StateChangeSpec
+
+
+def type_changes(db: Session, world_id: str, view: Optional[EventTypeView],
+                 participants: Iterable[tuple[Optional[str], Optional[str]]]) -> list[dict]:
+    """The changes `view`'s effects make on `participants` (see the module
+    docstring), in the order of its effects."""
+    if view is None:
+        return []
+    held: dict[str, list[str]] = {}
+    for role_id, entity_id in participants:
+        if role_id and entity_id and entity_id not in held.setdefault(role_id, []):
+            held[role_id].append(entity_id)
+    out: list[dict] = []
+    for effect in view.effects:
+        state = attribute_view(db, world_id, effect.attribute)
+        if state is None or state.status != "active":
+            continue
+        value = effect.value
+        if effect.value_kind == "role":
+            named = held.get(effect.value) or []
+            if not named:
+                continue
+            value = named[0]
+        for entity_id in held.get(effect.role_id, []):
+            entity = db.get(Entity, entity_id)
+            if entity is None or not applies_to(state, entity.type):
+                continue
+            if any(c["entity_id"] == entity_id and c["attribute"] == state.key for c in out):
+                continue
+            out.append({"entity_id": entity_id, "attribute": state.key, "mode": effect.mode, "value": value})
+    return out
+
+
+def change_line(db: Session, world_id: str, change: dict) -> Optional[str]:
+    """One change, in French (see the module docstring)."""
+    state = attribute_view(db, world_id, change.get("attribute"))
+    entity = db.get(Entity, change.get("entity_id")) if isinstance(change.get("entity_id"), str) else None
+    if state is None or entity is None or entity.world_id != world_id:
+        return None
+    if change.get("mode") == "add":
+        value = change.get("value")
+        sign = "+" if isinstance(value, int) and value >= 0 else ""
+        return f"{entity.name} : {state.name} {sign}{value}"
+    return f"{entity.name} : {state.name} -> {value_label(db, state, change.get('value'))}"
+
+
+def payload_changes(raw: Any) -> tuple[StateChangeSpec, ...]:
+    """A payload's `state_changes`, as the writer reads them; a malformed
+    item is kept as it is for the writer to refuse, never dropped."""
+    out = []
+    for item in raw if isinstance(raw, list) else []:
+        item = item if isinstance(item, dict) else {}
+        out.append(StateChangeSpec(entity_id=item.get("entity_id"), attribute=item.get("attribute"),
+                                   value=item.get("value"), mode=item.get("mode") or "set"))
+    return tuple(out)
diff --git a/src/world_engine/event_payloads.py b/src/world_engine/event_payloads.py
index 84d1110..e8b6bd8 100644
--- a/src/world_engine/event_payloads.py
+++ b/src/world_engine/event_payloads.py
@@ -13,7 +13,10 @@ proposal's payload into that writer's `EventSpec`. Two payload shapes:
   then under that name is used instead), its participants naming its roles
   by `role`; a participant's `sorte_name` is a sorte the world lacked,
   written likewise (`write_sorte`) unless it exists by then. All inside the
-  applier's savepoint: refused, nothing is written.
+  applier's savepoint: refused, nothing is written. Since TICKET-0119 a
+  typed payload carries its `state_changes` (M-c) -- pre-filled from its
+  type's effects, edited by the creator on the card -- read by
+  `event_changes.payload_changes` for the writer to clean.
 - untyped (the world tick until TICKET-0119, and every proposal written
   before): `type` (a former category), `involved_entities`,
   `knowledge_status`, `location_id`. It is typed by its domain
@@ -39,6 +42,7 @@ from typing import Optional
 
 from sqlmodel import Session
 
+from .event_changes import payload_changes
 from .event_proposals import type_spec
 from .event_vocab import role_accepts, type_view, world_event_types, world_sortes
 from .lore_resolve import normalize_surface
@@ -107,7 +111,7 @@ def _typed(db: Session, world_id: str, payload: dict) -> EventSpec:
         type_id=str(type_id), title=str(payload.get("title") or ""),
         description=payload.get("description"), location_id=payload.get("location_id") or None,
         quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
-        participants=tuple(participants),
+        participants=tuple(participants), changes=payload_changes(payload.get("state_changes")),
     )
 
 
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index f1ce798..e881527 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -36,7 +36,8 @@ Layout, by canon domain:
                           `agenda_step`/`goal_agenda_link`.
     events.py           — the event journal: `event`, `event_participant`,
                           its fact, scopes and participants' knowledge:
-                          `clean_event`, `write_event`, `write_event_update`
+                          `clean_event`, `write_event`, `record_event`
+                          (TICKET-0119: with its changes), `write_event_update`
                           (TICKET-0114, BRIEF-0114-C).
     prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                           moved for module hygiene, not policy).
@@ -102,7 +103,17 @@ from .config import (
     write_npc_schedule,
     write_world_laws,
 )
-from .events import EventScopeSpec, EventSpec, ParticipantSpec, clean_event, event_fact_text, write_event, write_event_update
+from .events import (
+    EventScopeSpec,
+    EventSpec,
+    ParticipantSpec,
+    StateChangeSpec,
+    clean_event,
+    event_fact_text,
+    record_event,
+    write_event,
+    write_event_update,
+)
 from .facts import (
     attach_participants,
     create_fact,
@@ -241,6 +252,8 @@ __all__ = [
     "write_ledger_entry",
     "write_membership",
     "write_event",
+    "record_event",
+    "StateChangeSpec",
     "write_prompt_version",
     "delete_world_cascade",
     "WorldDeleteRefused",
diff --git a/src/world_engine/writes/entity_states.py b/src/world_engine/writes/entity_states.py
new file mode 100644
index 0000000..1e7f2c0
--- /dev/null
+++ b/src/world_engine/writes/entity_states.py
@@ -0,0 +1,74 @@
+"""The writer of the system states an event may change (TICKET-0119,
+BRIEF-0119-C; decision E1 of the conditions series): `character.vital_status`
+(`sys:vital_status`) and `entity.status` (`sys:status`), the two columns
+`writes.event_types.EFFECT_SYSTEM_KEYS` names.
+
+- `write_system_state(db, *, world_id, entity_id, key, value)` : set one
+  entity's system state, or `ValueError` -- the key is one of the two, the
+  value one of its stored values (`attributes.SYSTEM_ATTRIBUTES`), the
+  entity one of the world's (a character for the vital state). An
+  unchanged value writes nothing and returns None; otherwise
+  `(before, after)`. An entity leaving `active`, or a character leaving
+  `alive`, leaves the gatherings it sat in (`gathering.close_open_memberships`
+  -- INV-25's repair, the creator CRUD's own; a gathering it empties is
+  ignored by the entry guard until it dissolves, INV-26). A location is never
+  made `active` again here: that may promote its parent into a zone, which
+  only its fiche confirms (TICKET-0101) -- refused.
+
+These columns keep no history table: the reason of a change is the event
+that made it, and its fact. Called only by `writes.events` (an event's
+changes). Never commits.
+"""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlmodel import Session
+
+from ..attributes import system_attribute
+from ..models import Character, Entity
+
+SYSTEM_STATE_KEYS: tuple[str, ...] = ("sys:vital_status", "sys:status")
+
+
+def write_system_state(
+    db: Session, *, world_id: str, entity_id: str, key: str, value: str,
+) -> Optional[tuple[str, str]]:
+    """Set `key` of `entity_id` to `value` (see the module docstring)."""
+    spec = system_attribute(key)
+    if spec is None or key not in SYSTEM_STATE_KEYS:
+        raise ValueError(f"{key!r} is not a state an event changes")
+    if value not in dict(spec.values):
+        raise ValueError(f"{value!r} is no value of « {spec.name} »")
+    entity = db.get(Entity, entity_id)
+    if entity is None or entity.world_id != world_id:
+        raise ValueError(f"unknown entity {entity_id!r}")
+    if key == "sys:vital_status":
+        character = db.get(Character, entity_id)
+        if character is None:
+            raise ValueError(f"« {entity.name} » has no vital state")
+        before = character.vital_status
+        if before == value:
+            return None
+        character.vital_status = value
+        db.add(character)
+        leaves = before == "alive"
+    else:
+        before = entity.status
+        if before == value:
+            return None
+        if entity.type == "location" and value == "active":
+            raise ValueError(f"« {entity.name} » is made active again from its fiche, never by an event")
+        entity.status = value
+        leaves = before == "active"
+    entity.updated_at = datetime.now(UTC)
+    db.add(entity)
+    db.flush()
+    if leaves:
+        # Imported here: `gathering` reaches the analyzers, which import `writes`.
+        from ..gathering import close_open_memberships
+
+        close_open_memberships(entity_id, db)
+    return before, value
diff --git a/src/world_engine/writes/events.py b/src/world_engine/writes/events.py
index 5516f63..51d10ef 100644
--- a/src/world_engine/writes/events.py
+++ b/src/world_engine/writes/events.py
@@ -18,11 +18,27 @@ series). The one writer of `event` and `event_participant`.
   participants, its fact (`fact.event_id`, facet `evenement`, its title then
   its description -- `event_fact_text`), the fact's scopes
   (`fact_default`) and one `knowledge` row at `knows` for each character
-  taking part (K-a), secret as said. Returns the event, flushed.
+  taking part (K-a), secret as said -- then its CHANGES to the state of the
+  world (M-c, TICKET-0119). Returns the event, flushed. `record_event` does
+  the same and returns every row it wrote (`WrittenEvent`), for a caller
+  that records them (Lore) or keeps a system change's before and after
+  (the applier).
 - `write_event_update(db, *, event, spec, changed_by)` : a correction from
   the journal -- title, description, place, quantity; a participant added;
   a participant's secret changed (his knowledge row); the scopes replaced
-  whole. The fact's text is rewritten as a `correction` when it changed.
+  whole. The fact's text is rewritten as a `correction` when it changed. A
+  correction changes no state (L1: the event already did, or never did).
+
+An event's changes (`StateChangeSpec`, TICKET-0119, F1) are what the
+creator kept of its type's effects, edited or added: each names an entity
+of the world, a state that applies to it -- one of the world's active
+definitions, or `État vital` / `Statut` (E1) --, and a value of the state's
+kind (`add` for an integer, D3; an entity of a type the state may name, or
+none). One refused and the whole event is refused: nothing is written. A
+definition's change is a `changement` naming the event
+(`writes.attributes.write_attribute_value`); a system state is written by
+`writes.entity_states.write_system_state`, which keeps no history -- the
+event and its fact are the reason.
 
 The two producers -- the creator's journal (`cockpit/crud/events.py`) and
 `_apply_mutation`'s `event_creation` (a model's proposal, reviewed by the
@@ -32,14 +48,16 @@ proposal's payload into an `EventSpec`. None of these functions commits.
 
 from __future__ import annotations
 
-from dataclasses import dataclass, replace
+from dataclasses import dataclass, field, replace
 from typing import Optional
 
 from sqlalchemy import text
 from sqlmodel import Session, select
 
+from ..attributes import applies_to, attribute_view, current_value, stored_value
 from ..event_vocab import EventTypeView, role_accepts, type_view
 from ..models import (
+    EVENT_EFFECT_MODES,
     Character,
     Entity,
     Event,
@@ -48,6 +66,9 @@ from ..models import (
     Fact,
     Knowledge,
 )
+from .attributes import write_attribute_value
+from .entity_states import write_system_state
+from .event_types import EFFECT_SYSTEM_KEYS
 from .facts import create_fact, create_fact_default, update_typed_fact_content
 from .knowledge import knowledge_level_rank, write_knowledge
 
@@ -78,6 +99,18 @@ class EventScopeSpec:
     level: str
 
 
+@dataclass(frozen=True)
+class StateChangeSpec:
+    """One change an event makes to the state of the world (M-c): `entity_id`'s
+    `attribute` (a definition id or a system key) takes `value` -- a choice
+    key, an integer (set, or added when `mode` is `add`), an entity id, or
+    None (an entity state left empty)."""
+    entity_id: str
+    attribute: str
+    value: object
+    mode: str = "set"
+
+
 @dataclass(frozen=True)
 class EventSpec:
     type_id: str
@@ -89,6 +122,18 @@ class EventSpec:
     scopes: Optional[tuple[EventScopeSpec, ...]] = None  # None: the type's (W1)
     session_id: Optional[str] = None
     batch_id: Optional[str] = None
+    changes: tuple[StateChangeSpec, ...] = ()
+
+
+@dataclass
+class WrittenEvent:
+    """Every row one `record_event` wrote: (id, `created` | `updated`) per
+    table, and the system states it changed (`entity_id`, `attribute`,
+    `before`, `after`), which keep no history of their own."""
+    event: Event
+    fact: Fact
+    rows: list[tuple[str, str, str]] = field(default_factory=list)  # (table, id, action)
+    system_changes: list[dict] = field(default_factory=list)
 
 
 def event_fact_text(title: str, description: Optional[str]) -> str:
@@ -215,6 +260,52 @@ def _clean_scope(db: Session, world_id: str, scope: EventScopeSpec) -> EventScop
     return scope
 
 
+def _clean_change_value(db: Session, world_id: str, view, change: StateChangeSpec) -> object:
+    if change.mode not in EVENT_EFFECT_MODES:
+        raise ValueError(f"unknown change mode {change.mode!r}")
+    if change.mode == "add" and view.kind != "integer":
+        raise ValueError(f"« {view.name} » is not a number: a change sets it")
+    if view.kind == "integer":
+        if not isinstance(change.value, int) or isinstance(change.value, bool):
+            raise ValueError(f"« {view.name} » takes an integer")
+        return change.value
+    if view.kind == "choice":
+        if change.value not in dict(view.choices):
+            raise ValueError(f"{change.value!r} is no value of « {view.name} »")
+        return change.value
+    if change.value is None:
+        return None
+    named = db.get(Entity, change.value) if isinstance(change.value, str) else None
+    if named is None or named.world_id != world_id or named.type not in view.value_types:
+        raise ValueError(f"« {view.name} » names no {change.value!r}")
+    return named.id
+
+
+def _clean_change(db: Session, world_id: str, change: StateChangeSpec) -> StateChangeSpec:
+    view = attribute_view(db, world_id, change.attribute) if isinstance(change.attribute, str) else None
+    if view is None or view.status != "active" or (view.system and view.key not in EFFECT_SYSTEM_KEYS):
+        raise ValueError(f"{change.attribute!r} is no state an event changes")
+    entity = db.get(Entity, change.entity_id) if isinstance(change.entity_id, str) else None
+    if entity is None or entity.world_id != world_id:
+        raise ValueError(f"unknown entity {change.entity_id!r}")
+    if not applies_to(view, entity.type):
+        raise ValueError(f"« {view.name} » does not apply to « {entity.name} »")
+    if view.key == "sys:vital_status" and db.get(Character, entity.id) is None:
+        raise ValueError(f"« {entity.name} » has no vital state")
+    value = _clean_change_value(db, world_id, view, change)
+    if view.key == "sys:status" and entity.type == "location" and value == "active" and entity.status != "active":
+        raise ValueError(f"« {entity.name} » is made active again from its fiche, never by an event")
+    return StateChangeSpec(entity_id=entity.id, attribute=view.key, value=value, mode=change.mode)
+
+
+def _clean_changes(db: Session, world_id: str, changes) -> tuple[StateChangeSpec, ...]:
+    cleaned = tuple(_clean_change(db, world_id, c) for c in changes)
+    keys = [(c.entity_id, c.attribute) for c in cleaned]
+    if len(set(keys)) != len(keys):
+        raise ValueError("one state of one entity is changed twice")
+    return cleaned
+
+
 def clean_event(db: Session, world_id: str, spec: EventSpec, event: Optional[Event] = None) -> EventSpec:
     """`spec` as it will be written, its scopes made concrete; raises
     `ValueError` on any violation. Writes nothing."""
@@ -235,9 +326,12 @@ def clean_event(db: Session, world_id: str, spec: EventSpec, event: Optional[Eve
         scopes = _type_scopes(db, view, location_id, participants)
     else:
         scopes = _merged(_clean_scope(db, world_id, s) for s in spec.scopes)
+    if event is not None and spec.changes:
+        raise ValueError("a correction of an event changes no state")
     description = (spec.description or "").strip() or None
     return replace(spec, title=title, description=description, location_id=location_id,
-                   quantity=_clean_quantity(view, spec.quantity), participants=participants, scopes=scopes)
+                   quantity=_clean_quantity(view, spec.quantity), participants=participants, scopes=scopes,
+                   changes=_clean_changes(db, world_id, spec.changes))
 
 
 # --- writing -------------------------------------------------------------------
@@ -247,47 +341,84 @@ def _participant_rows(db: Session, event_id: str) -> list[EventParticipant]:
                         .order_by(EventParticipant.position, EventParticipant.id)).all())
 
 
-def _knows(db: Session, entity_id: str, fact_id: str, secret: bool, changed_by: str) -> None:
+def _knows(db: Session, entity_id: str, fact_id: str, secret: bool, changed_by: str) -> Optional[tuple]:
     """K-a: a character taking part knows the event -- his row written at
-    `knows`, or raised to it, his `is_secret` set as said (X1)."""
+    `knows`, or raised to it, his `is_secret` set as said (X1). Returns
+    (`knowledge`, its id, `created` | `updated`), or None for a non-character."""
     if db.get(Character, entity_id) is None:
-        return
+        return None
     row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
     if row is None:
-        write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=PARTICIPANT_LEVEL, is_secret=secret,
-                        source=EVENT_SOURCE, changed_by=changed_by)
-        return
+        made = write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=PARTICIPANT_LEVEL, is_secret=secret,
+                               source=EVENT_SOURCE, changed_by=changed_by)
+        db.flush()
+        return "knowledge", made.id, "created"
     level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(PARTICIPANT_LEVEL) \
         else PARTICIPANT_LEVEL
     write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
                     is_incorrect=row.is_incorrect, is_secret=secret, share_threshold=row.share_threshold,
                     session_id=row.session_id, changed_by=changed_by)
+    return "knowledge", row.id, "updated"
 
 
-def _add_participants(db: Session, event: Event, participants, fact_id: str, changed_by: str) -> None:
+def _add_participants(db: Session, event: Event, participants, fact_id: str, changed_by: str) -> list[tuple]:
     rows = _participant_rows(db, event.id)
     have = {(r.role_id, r.entity_id, r.sorte_id) for r in rows}
     position = len(rows)
+    written: list[tuple] = []
     for p in participants:
         if _key(p) not in have:
-            db.add(EventParticipant(world_id=event.world_id, event_id=event.id, role_id=p.role_id,
-                                    entity_id=p.entity_id, sorte_id=p.sorte_id, position=position))
+            row = EventParticipant(world_id=event.world_id, event_id=event.id, role_id=p.role_id,
+                                   entity_id=p.entity_id, sorte_id=p.sorte_id, position=position)
+            db.add(row)
+            db.flush()
+            written.append(("event_participant", row.id, "created"))
             position += 1
         if p.entity_id is not None:
-            _knows(db, p.entity_id, fact_id, bool(p.secret), changed_by)
+            known = _knows(db, p.entity_id, fact_id, bool(p.secret), changed_by)
+            if known is not None:
+                written.append(known)
+    return written
 
 
-def _write_scopes(db: Session, world_id: str, fact_id: str, scopes, created_by: str) -> None:
+def _write_scopes(db: Session, world_id: str, fact_id: str, scopes, created_by: str) -> list[tuple]:
     """The fact's scopes replaced whole (the full-replace shape)."""
     db.execute(text("DELETE FROM fact_default WHERE fact_id = :fid"), {"fid": fact_id})
+    written: list[tuple] = []
     for scope in scopes:
-        create_fact_default(db, world_id=world_id, fact_id=fact_id, scope_type=scope.scope_type,
-                            scope_id=scope.scope_id, level=scope.level, created_by=created_by)
-
-
-def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:
-    """C-01: the event, its participants, its fact, the fact's scopes and
-    the participants' knowledge, from a cleaned spec."""
+        row = create_fact_default(db, world_id=world_id, fact_id=fact_id, scope_type=scope.scope_type,
+                                  scope_id=scope.scope_id, level=scope.level, created_by=created_by)
+        db.flush()
+        written.append(("fact_default", row.id, "created"))
+    return written
+
+
+def _apply_changes(db: Session, world_id: str, event: Event, changes, changed_by: str, out: WrittenEvent) -> None:
+    """The event's changes to the state of the world (M-c)."""
+    for change in changes:
+        view = attribute_view(db, world_id, change.attribute)
+        entity = db.get(Entity, change.entity_id)
+        if view.system:
+            done = write_system_state(db, world_id=world_id, entity_id=entity.id, key=view.key, value=change.value)
+            if done is not None:
+                out.system_changes.append({"entity_id": entity.id, "attribute": view.key,
+                                           "before": done[0], "after": done[1]})
+            continue
+        value = change.value
+        if change.mode == "add":
+            value = (current_value(db, view, entity).raw or 0) + change.value
+        held = stored_value(db, view.key, entity.id) is not None
+        made = write_attribute_value(db, world_id=world_id, definition_id=view.key, entity_id=entity.id,
+                                     value=value, kind="changement", changed_by=changed_by, event_id=event.id)
+        if made is not None:
+            out.rows.append(("attribute_value", made.value_id, "updated" if held else "created"))
+            out.rows.append(("attribute_change", made.id, "created"))
+
+
+def record_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> WrittenEvent:
+    """C-01: the event, its participants, its fact, the fact's scopes, the
+    participants' knowledge and its changes, from a cleaned spec; every row
+    written, returned."""
     clean = clean_event(db, world_id, spec)
     event = Event(world_id=world_id, type_id=clean.type_id, title=clean.title, description=clean.description,
                   location_id=clean.location_id, quantity=clean.quantity, session_id=clean.session_id,
@@ -297,10 +428,17 @@ def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str)
     fact = create_fact(db, world_id=world_id, content=event_fact_text(clean.title, clean.description),
                        created_by=created_by, facet="evenement", event_id=event.id)
     db.flush()
-    _add_participants(db, event, clean.participants, fact.id, created_by)
-    _write_scopes(db, world_id, fact.id, clean.scopes, created_by)
+    out = WrittenEvent(event=event, fact=fact, rows=[("event", event.id, "created"), ("fact", fact.id, "created")])
+    out.rows += _add_participants(db, event, clean.participants, fact.id, created_by)
+    out.rows += _write_scopes(db, world_id, fact.id, clean.scopes, created_by)
+    _apply_changes(db, world_id, event, clean.changes, created_by, out)
     db.flush()
-    return event
+    return out
+
+
+def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:
+    """`record_event`, for a caller that needs only the event."""
+    return record_event(db, world_id=world_id, spec=spec, created_by=created_by).event
 
 
 def event_fact(db: Session, event_id: str) -> Optional[Fact]:
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 88db058..b1ed3a9 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19530,6 +19530,34 @@ its `effects`, a role's NAME for an entity state; `EventTypeBody.effects`
 is read into the writer's `EffectSpec`. Every rule stays in
 `writes/event_types.py`; a refused effect is a 422.
 
+## AN EVENT WRITES WHAT IT CHANGES IN THE WORLD, ALL OR NONE (TICKET-0119) -- ITS TYPE PRE-FILLS THE CHANGES; `record_event`, `write_system_state` (BRIEF-0119-c, no schema change)
+
+**M-c.** An event carries its CHANGES (`EventSpec.changes`, a payload's
+`state_changes`): each names an entity of the world, a state that applies
+to it, and a value of the state's kind. They are PRE-FILLED from its type's
+effects (`event_changes.type_changes`: each entity in the effect's role; a
+sorte changes nothing; an entity state takes the first entity of its value
+role), and the creator keeps, edits or drops them. Play's typed proposal
+carries them from this brief on; the tick, Journée and Lore follow.
+
+**F1.** One change refused and the whole event is refused: nothing is
+written -- in the applier's savepoint, the journal's route, Lore's
+transaction. A correction of an event changes no state (L1): the event
+already did, or never did.
+
+**The writes.** A definition's change is a `changement` naming its event
+(`write_attribute_value`); an integer `add` is added to the current value
+(D3). A system state is written by `writes.entity_states.write_system_state`
+(E1): a location is never made active again by an event (its fiche asks
+about a zone promotion, TICKET-0101), and an entity leaving `active`, or a
+character leaving `alive`, leaves its gatherings (INV-25's repair). Those
+columns keep no history: the approved proposal keeps their before and after
+(`applied_changes`), so a later history table can recover every change an
+event made.
+
+**`record_event`.** The journal's writer returns every row it wrote, for
+Lore to record them (INV-57); `write_event` stays its thin form.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index f88c348..f4e4b74 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -82,6 +82,8 @@ src/world_engine/writes/event_types.py::_write_roles           event_type_role e
 src/world_engine/writes/event_types.py::_write_scopes          event_type_scope
 # TICKET-0119, BRIEF-0119-A: _write_effects replaces a type's effects whole (an effect only pre-fills a proposal; nothing holds it). Same callers as write_event_type.
 src/world_engine/writes/event_types.py::_write_effects         event_type_effect
+# TICKET-0119, BRIEF-0119-C: write_system_state sets the two system states an event may change -- character.vital_status and entity.status (E1) -- for writes/events.py's changes only: an approved event_creation, the journal, Lore.
+src/world_engine/writes/entity_states.py::write_system_state   character entity
 src/world_engine/writes/event_types.py::set_event_type_status  event_type
 src/world_engine/writes/event_types.py::write_sorte            event_sorte
 src/world_engine/writes/event_types.py::set_sorte_status       event_sorte
@@ -93,7 +95,8 @@ src/world_engine/writes/event_types.py::set_sorte_status       event_sorte
 # INSERTs into entity_type / entity_type_history are row writes and are
 # allow-listed here.
 src/world_engine/writes/schema.py::create_entity_type          entity_type entity_type_history
-src/world_engine/writes/events.py::write_event                 event
+# TICKET-0119, BRIEF-0119-C: record_event is write_event's body, returning every row it wrote (write_event now calls it).
+src/world_engine/writes/events.py::record_event                event
 src/world_engine/writes/events.py::write_event_update           event
 # TICKET-0114, BRIEF-0114-C: the journal -- _add_participants adds an event's participants (never takes one away; their knowledge goes through write_knowledge, allow-listed above), _write_scopes replaces an event's fact's scopes whole (the full-replace shape; each row through create_fact_default). Creator CRUD and _apply_mutation's event_creation.
 src/world_engine/writes/events.py::_add_participants           event_participant
diff --git a/tooling/verify/checks/event_changes.py b/tooling/verify/checks/event_changes.py
new file mode 100644
index 0000000..c6d552c
--- /dev/null
+++ b/tooling/verify/checks/event_changes.py
@@ -0,0 +1,392 @@
+"""G1 check for TICKET-0119 -- what an event changes in the world: pre-filled from its type, written with it, all or none.
+
+BRIEF-0119-C's rules (M-c, D3, E1 and F1 of the conditions series);
+`event_effects.py` holds what a type declares.
+
+EM1 -- the pre-fill (fixture). `type_changes` makes « Ouvrir »'s effect
+   Cible -> Ouvert = oui concrete on the door in the role Cible; a sorte in
+   that role changes nothing; « Usurper »'s Trône -> Occupé par takes the
+   first entity in the role Usurpateur, and is left out when that role holds
+   none; « Être repéré »'s Garnison -> Alerte + 1 keeps its mode.
+EM2 -- the writer (fixture). `record_event` with three changes writes the
+   event, then « Ouvert » of the door as a `changement` naming the event, the
+   guild's « Alerte » added twice by two events (0 -> 1 -> 2), and Ivo's
+   `État vital` -> `dead` on his character row, returned in
+   `system_changes` with its before (`alive`); its `rows` name the event,
+   its fact, each `attribute_value` and `attribute_change` it wrote.
+EM3 -- all or nothing (fixture). Each refused with no event, fact or
+   change written: an unknown state, `Magie`, a state that does not apply
+   to the entity, a value not one of the state's choices, `add` on a
+   choice, an entity value of a type the state may not name, one state of
+   one entity twice, a vital state on a location, a location made active
+   again, and a correction (`write_event_update`) carrying a change.
+EM4 -- the system states (static and fixture). `writes/entity_states.py`'s
+   `write_system_state` calls `close_open_memberships`; an entity made
+   `destroyed` has its open `gathering_member` row closed (`left_at` set).
+EM5 -- the approved proposal (fixture, `_apply_mutation`). A typed
+   `event_creation` whose `state_changes` name Ivo's vital state writes the
+   event and kills him, and its payload gains `applied_changes` with
+   before and after; one whose change is refused answers `event_creation:`
+   and writes no event and no change.
+EM6 -- the producers pre-fill (fixture). Play's `typed_payload` of an
+   « Ouvrir » proposal carries the door's change in `state_changes`; a
+   proposal of a NEW type carries none. The journal's `create_event`
+   writes a body's `state_changes`; `update_event` with one answers 422.
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
+    from sqlmodel import Session
+
+    from world_engine.attributes import attribute_view
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Faction, Location, World
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
+    from world_engine.writes.event_types import (
+        EffectSpec,
+        EventTypeSpec,
+        RoleSpec,
+        write_event_type,
+        write_sorte,
+    )
+
+    with Session(engine) as db:
+        world = World(name="Changements", is_active=True)
+        db.add(world)
+        db.flush()
+        w = world.id
+        ids = {"world": w}
+        for key, kind, name in (("millys", "character", "Millys"), ("ivo", "character", "Ivo"),
+                                ("ysa", "character", "Ysa"), ("porte", "location", "Porte du caveau"),
+                                ("cour", "location", "Cour"), ("ruine", "location", "Ruine"),
+                                ("guilde", "faction", "Garnison")):
+            entity = Entity(world_id=w, type=kind, name=name, status="inactive" if key == "ruine" else "active")
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=w, character_type="npc"))
+            elif kind == "location":
+                db.add(Location(id=entity.id))
+            else:
+                db.add(Faction(id=entity.id))
+        ouvert = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
+            name="Ouvert", kind="choice", holder_types=("location",),
+            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
+        occupe = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
+            name="Occupé par", kind="entity", holder_types=("location",), value_types=("character",)))
+        alerte = write_attribute_definition(db, world_id=w, spec=DefinitionSpec(
+            name="Alerte", kind="integer", holder_types=("faction",), default=0))
+        db.flush()
+        choices = {label: key for key, label in attribute_view(db, w, ouvert.id).choices}
+        ids.update(ouvert=ouvert.id, occupe=occupe.id, alerte=alerte.id, oui=choices["oui"], non=choices["non"])
+        ids["loup"] = write_sorte(db, world_id=w, name="Loup").id
+        types = {
+            "ouvrir": EventTypeSpec(name="Ouvrir", roles=(
+                RoleSpec("Ouvreur", ("character",)), RoleSpec("Cible", ("location",), accepts_sorte=True)),
+                effects=(EffectSpec("Cible", ouvert.id, choices["oui"]),)),
+            "usurper": EventTypeSpec(name="Usurper", roles=(
+                RoleSpec("Usurpateur", ("character",)), RoleSpec("Trône", ("location",))),
+                effects=(EffectSpec("Trône", occupe.id, "Usurpateur"),)),
+            "reperer": EventTypeSpec(name="Être repéré", roles=(
+                RoleSpec("Intrus", ("character",)), RoleSpec("Garnison", ("faction",))),
+                effects=(EffectSpec("Garnison", alerte.id, 1, "add"),)),
+            "tuer": EventTypeSpec(name="Tuer", roles=(
+                RoleSpec("Tueur", ("character",)), RoleSpec("Victime", ("character",))),
+                effects=(EffectSpec("Victime", "sys:vital_status", "dead"),)),
+        }
+        for key, spec in types.items():
+            type_id = write_event_type(db, world_id=w, spec=spec).id
+            ids[key] = type_id
+            for role in type_view(db, type_id).roles:
+                ids[f"{key}:{role.name}"] = role.id
+        db.commit()
+    return ids
+
+
+def _counts(db) -> tuple[int, ...]:
+    from sqlmodel import func, select
+
+    from world_engine.models import AttributeChange, AttributeValue, Event, Fact
+
+    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (Event, Fact, AttributeValue,
+                                                                              AttributeChange))
+
+
+def _spec(ids: dict, type_key: str, title: str, participants, changes=()):
+    from world_engine.writes.events import EventSpec, ParticipantSpec, StateChangeSpec
+
+    return EventSpec(type_id=ids[type_key], title=title,
+                     participants=tuple(ParticipantSpec(role_id=ids[f"{type_key}:{r}"], entity_id=e, sorte_id=s)
+                                        for r, e, s in participants),
+                     changes=tuple(StateChangeSpec(*c) for c in changes))
+
+
+def check_em1(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_changes import type_changes
+    from world_engine.event_vocab import type_view
+
+    w = ids["world"]
+    with Session(engine) as db:
+        got = (
+            type_changes(db, w, type_view(db, ids["ouvrir"]), [(ids["ouvrir:Ouvreur"], ids["millys"]),
+                                                              (ids["ouvrir:Cible"], ids["porte"])]),
+            type_changes(db, w, type_view(db, ids["ouvrir"]), [(ids["ouvrir:Cible"], None)]),
+            type_changes(db, w, type_view(db, ids["usurper"]), [(ids["usurper:Usurpateur"], ids["ysa"]),
+                                                               (ids["usurper:Trône"], ids["cour"])]),
+            type_changes(db, w, type_view(db, ids["usurper"]), [(ids["usurper:Trône"], ids["cour"])]),
+            type_changes(db, w, type_view(db, ids["reperer"]), [(ids["reperer:Garnison"], ids["guilde"])]),
+        )
+    want = (
+        [{"entity_id": ids["porte"], "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}],
+        [],
+        [{"entity_id": ids["cour"], "attribute": ids["occupe"], "mode": "set", "value": ids["ysa"]}],
+        [],
+        [{"entity_id": ids["guilde"], "attribute": ids["alerte"], "mode": "add", "value": 1}],
+    )
+    if got != want:
+        fail(f"EM1: the pre-filled changes are {got}")
+
+
+def check_em2(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.attributes import attribute_view, current_value
+    from world_engine.models import AttributeChange, Character, Entity
+    from world_engine.writes.events import record_event
+
+    w = ids["world"]
+    with Session(engine) as db:
+        written = record_event(db, world_id=w, created_by="check", spec=_spec(
+            ids, "tuer", "Millys ouvre et tue", [("Tueur", ids["millys"], None), ("Victime", ids["ivo"], None)],
+            [(ids["porte"], ids["ouvert"], ids["oui"]), (ids["guilde"], ids["alerte"], 1, "add"),
+             (ids["ivo"], "sys:vital_status", "dead")]))
+        record_event(db, world_id=w, created_by="check", spec=_spec(
+            ids, "reperer", "Repéré", [("Intrus", ids["millys"], None)], [(ids["guilde"], ids["alerte"], 1, "add")]))
+        db.commit()
+        changes = db.exec(select(AttributeChange).where(AttributeChange.event_id == written.event.id)).all()
+        door = current_value(db, attribute_view(db, w, ids["ouvert"]), db.get(Entity, ids["porte"])).raw
+        alert = current_value(db, attribute_view(db, w, ids["alerte"]), db.get(Entity, ids["guilde"])).raw
+        if door != ids["oui"] or alert != 2 or len(changes) != 2 or any(c.kind != "changement" for c in changes):
+            fail(f"EM2: door {door}, alert {alert}, the event's changes {[(c.kind, c.after_integer) for c in changes]}")
+        if db.get(Character, ids["ivo"]).vital_status != "dead" or written.system_changes != [
+                {"entity_id": ids["ivo"], "attribute": "sys:vital_status", "before": "alive", "after": "dead"}]:
+            fail(f"EM2: Ivo's vital state is {db.get(Character, ids['ivo']).vital_status}, "
+                 f"system changes {written.system_changes}")
+        tables = sorted({table for table, _id, _action in written.rows})
+        if tables != ["attribute_change", "attribute_value", "event", "event_participant", "fact", "knowledge"]:
+            fail(f"EM2: the rows written name {tables}")
+
+
+def check_em3(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Event
+    from world_engine.writes.events import record_event, write_event_update
+
+    w = ids["world"]
+    door = [("Ouvreur", ids["millys"], None), ("Cible", ids["porte"], None)]
+    refused = (
+        ("an unknown state", [(ids["porte"], "nope", ids["oui"])]),
+        ("Magie", [(ids["porte"], "sys:magic_status", "active")]),
+        ("a state that does not apply", [(ids["millys"], ids["ouvert"], ids["oui"])]),
+        ("a value not a choice", [(ids["porte"], ids["ouvert"], "peut-être")]),
+        ("add on a choice", [(ids["porte"], ids["ouvert"], ids["oui"], "add")]),
+        ("an entity value of the wrong type", [(ids["cour"], ids["occupe"], ids["guilde"])]),
+        ("one state twice", [(ids["porte"], ids["ouvert"], ids["oui"]), (ids["porte"], ids["ouvert"], ids["non"])]),
+        ("a vital state on a location", [(ids["porte"], "sys:vital_status", "dead")]),
+        ("a location made active again", [(ids["ruine"], "sys:status", "active")]),
+    )
+    with Session(engine) as db:
+        for label, changes in refused:
+            before = _counts(db)
+            try:
+                record_event(db, world_id=w, created_by="check", spec=_spec(ids, "ouvrir", label, door, changes))
+                fail(f"EM3: {label} was not refused")
+            except ValueError:
+                pass
+            db.rollback()
+            if _counts(db) != before:
+                fail(f"EM3: {label} was refused but wrote rows")
+        event = db.exec(select(Event).where(Event.world_id == w)).first()
+        before = _counts(db)
+        try:
+            write_event_update(db, event=event, changed_by="check", spec=_spec(
+                ids, "tuer", event.title, [("Tueur", ids["millys"], None), ("Victime", ids["ivo"], None)],
+                [(ids["porte"], ids["ouvert"], ids["non"])]))
+            fail("EM3: a correction carrying a change was not refused")
+        except ValueError:
+            pass
+        db.rollback()
+        if _counts(db) != before:
+            fail("EM3: the refused correction wrote rows")
+
+
+def check_em4(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Gathering, GatheringMember, Session as PlaySession
+    from world_engine.writes.events import record_event
+
+    tree = ast.parse((SRC / "writes" / "entity_states.py").read_text(encoding="utf-8"))
+    func = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "write_system_state"), None)
+    calls = {n.func.id for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} \
+        if func else set()
+    if "close_open_memberships" not in calls:
+        fail("EM4: write_system_state does not call close_open_memberships")
+    w = ids["world"]
+    with Session(engine) as db:
+        play = PlaySession(world_id=w, number=1)
+        db.add(play)
+        db.flush()
+        gathering = Gathering(world_id=w, session_id=play.id, location_id=ids["porte"])
+        db.add(gathering)
+        db.flush()
+        member = GatheringMember(gathering_id=gathering.id, entity_id=ids["ysa"])
+        db.add(member)
+        db.commit()
+        record_event(db, world_id=w, created_by="check", spec=_spec(
+            ids, "ouvrir", "Ysa part", [("Ouvreur", ids["ysa"], None)], [(ids["ysa"], "sys:status", "missing")]))
+        db.commit()
+        left = db.exec(select(GatheringMember).where(GatheringMember.id == member.id)).first()
+        if left is None or left.left_at is None:
+            fail("EM4: an entity made missing keeps its open gathering membership")
+
+
+def _mutation(db, world_id: str, payload: dict):
+    from world_engine.models import ProposedMutation
+
+    mut = ProposedMutation(world_id=world_id, source_type="world_tick", tick_id="t", mutation_type="event_creation",
+                           target_table="event", payload=payload, status="approved")
+    db.add(mut)
+    db.flush()
+    return mut
+
+
+def check_em5(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.models import Character, Event
+
+    w = ids["world"]
+    with Session(engine) as db:
+        db.get(Character, ids["ivo"]).vital_status = "alive"
+        db.commit()
+        mut = _mutation(db, w, {"title": "Millys tue Ivo", "type_id": ids["tuer"], "participants": [
+            {"role_id": ids["tuer:Tueur"], "entity_id": ids["millys"]},
+            {"role_id": ids["tuer:Victime"], "entity_id": ids["ivo"]}],
+            "state_changes": [{"entity_id": ids["ivo"], "attribute": "sys:vital_status", "mode": "set",
+                               "value": "dead"}]})
+        error = _apply_mutation(mut, db)
+        db.commit()
+        if error or db.get(Character, ids["ivo"]).vital_status != "dead" or mut.payload.get("applied_changes") != [
+                {"entity_id": ids["ivo"], "attribute": "sys:vital_status", "before": "alive", "after": "dead"}]:
+            fail(f"EM5: an approved kill gave {error!r}, payload {mut.payload.get('applied_changes')}")
+        before = _counts(db)
+        bad = _mutation(db, w, {"title": "Mal", "type_id": ids["tuer"], "participants": [],
+                                "state_changes": [{"entity_id": ids["porte"], "attribute": "sys:magic_status",
+                                                   "value": "active"}]})
+        with db.begin_nested():
+            answer = _apply_mutation(bad, db)
+        db.rollback()
+        if not (answer or "").startswith("event_creation:") or _counts(db) != before:
+            fail(f"EM5: a refused change answered {answer!r}, counts {before} -> {_counts(db)}")
+        if db.exec(select(Event).where(Event.title == "Mal")).first() is not None:
+            fail("EM5: a refused change wrote its event")
+
+
+def check_em6(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine.attributes import attribute_view, current_value
+    from world_engine.cockpit.crud import events as crud
+    from world_engine.event_analysis import analysis_vocabulary, typed_payload
+    from world_engine.models import Entity
+
+    w = ids["world"]
+    with Session(engine) as db:
+        vocab = analysis_vocabulary(db, w)
+        code = vocab.codes.code_of(ids["ouvrir"])
+        typed = typed_payload(db, w, {"title": "La porte cède", "event_type": code, "participants": [
+            {"role": "Ouvreur", "entity_id": ids["millys"]}, {"role": "Cible", "entity_id": ids["cour"]}]}, vocab)
+        if not typed or typed.get("state_changes") != [
+                {"entity_id": ids["cour"], "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}]:
+            fail(f"EM6: Play's typed payload carries {typed and typed.get('state_changes')}")
+        fresh = typed_payload(db, w, {"title": "x", "new_type": {"name": "Briser", "roles": [
+            {"name": "Briseur", "for": ["character"]}]}, "participants": [
+            {"role": "Briseur", "entity_id": ids["millys"]}]}, vocab)
+        if not fresh or "state_changes" in fresh:
+            fail(f"EM6: a new type's payload is {fresh}")
+        body = crud.EventBody(title="Ouvrir la cour", type_id=ids["ouvrir"], participants=[
+            {"role_id": ids["ouvrir:Cible"], "entity_id": ids["cour"]}],
+            state_changes=[{"entity_id": ids["cour"], "attribute": ids["ouvert"], "value": ids["oui"]}])
+        made = crud.create_event(body, db)
+        state = current_value(db, attribute_view(db, w, ids["ouvert"]), db.get(Entity, ids["cour"]))
+        if state.raw != ids["oui"] or state.is_default:
+            fail(f"EM6: the journal's state_changes wrote {state}")
+        try:
+            crud.update_event(made["id"], body, db)
+            fail("EM6: update_event with a change was not refused")
+        except HTTPException as exc:
+            if exc.status_code != 422:
+                fail(f"EM6: update_event with a change answered {exc.status_code}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    rules = (
+        ("EM1", lambda: check_em1(engine, ids)), ("EM2", lambda: check_em2(engine, ids)),
+        ("EM3", lambda: check_em3(engine, ids)), ("EM4", lambda: check_em4(engine, ids)),
+        ("EM5", lambda: check_em5(engine, ids)), ("EM6", lambda: check_em6(engine, ids)),
+    )
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_changes -- an event's type pre-fills what it changes in the world; an event writes its "
+          "changes with it, all or none, each naming it; the vital state and the status are written by their own "
+          "writer, closing a gathering seat, and an approved proposal keeps their before and after")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- The editor and the review card that show and edit the changes -- BRIEF-0119-D.
- The tick's, Journée's and Lore's pre-fill -- BRIEF-0119-E, F, G.
- A history table for the system states: `applied_changes` keeps what one needs.
- Dissolving a gathering an event emptied (the CRUD does it after its commit; INV-26: the entry guard ignores it).
- Every later brief of this lot: BRIEF-0119-D, E, F, G.

## Invariants to defend

INV-25: an entity leaving `active`, or a character leaving `alive`, through an event leaves its gatherings -- `write_system_state` calls `close_open_memberships` (EM4). INV-08: every write goes through `writes/` and the policy file names `write_system_state` (`character`, `entity`). INV-33's one-branch-one-table: the applier branch still calls ONE writer, `record_event`, which owns its tables (0114's precedent). INV-07: unchanged -- a PC participant's knowledge stays unsecret. INV-10: a state's history is appended by `write_attribute_value`.

## Decision rights

STOP:
- A change would be written outside `writes/events.py` (`record_event`) or a system column outside `writes/entity_states.py`.
- Importing `gathering` at the top of a `writes/` module (the import cycle R-03 names).
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
- `python tooling/verify/checks/event_changes.py` -> `PASS`.
- `python tooling/verify/checks/event_writes.py` -> `PASS`.
- `python tooling/verify/checks/event_analyzer.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/gathering_lifecycle.py` -> `PASS`.
- `python tooling/verify/checks/claude_md_contract.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (158 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EM1** -- `event_changes.py type_changes`: `            value = named[0]` -> `            value = None`
  - **EM2** -- `writes/events.py _apply_changes`: `            value = (current_value(db, view, entity).raw or 0) + change.value` -> `            value = change.value`
  - **EM3** -- `writes/events.py _clean_changes`: `        raise ValueError("one state of one entity is changed twice")` -> `        pass`
  - **EM4** -- `writes/entity_states.py write_system_state`: `        leaves = before == "active"` -> `        leaves = False`
  - **EM5** -- `cockpit/mutations.py _mutation_apply_event_creation`: `    if written.system_changes:` -> `    if False:`
  - **EM6** -- `event_analysis.py typed_payload`: `        out["state_changes"] = type_changes(` -> `        out["_unused"] = type_changes(`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS and `.claude/rules/gatherings.md` (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
