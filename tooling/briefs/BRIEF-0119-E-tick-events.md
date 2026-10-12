<!-- slug: tick-events -->
# BRIEF 0119-E — "The world tick proposes typed events -- the world's types by code, participants by role and name; never a new type (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-C (C-05)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-D's commit).

- `src/world_engine/tick_normalize.py` -> `def _tick_normalize_scope_event_creation(` building only the untyped shape
- `src/world_engine/tick.py` -> `def _tick_call_scope_model(db: Session, briefing: str, interval_label: str, model: str, host: str) -> list:`
- `scripts/seed_pilot.py` -> `        variables=["event_context", "interval_label"],` for `pt-world-tick-events`
- `src/world_engine/event_analysis.py` -> `def typed_payload(` adding `state_changes` (BRIEF-0119-C's)
- No `src/world_engine/tick_events.py`, no `scripts/apply_ticket_0119_tick_prompt.py`, no `tooling/verify/checks/event_tick.py`.

## Facts carried

### R-05 — Play's typed payload [M]
Opened: `src/world_engine/event_analysis.py` (`analysis_vocabulary` :57,
`AnalysisVocabulary.prompt_values` :52, `typed_payload` :130: `{title,
description, type_id | None, type_name, participants [{role_id, role,
entity_id, sorte_id, sorte_name, secret}], quantity, location_id,
new_type?}`).
Consequence: the tick reuses it whole (E); C adds `state_changes` to it.

### R-07 — the world tick's events [M]
Opened: `src/world_engine/tick_normalize.py` (:431
`_tick_normalize_scope_event_creation`, the untyped shape; :489
`_normalize_scope_event`); `src/world_engine/tick.py` (:305
`_tick_scope_setup` builds `actives_index`; :322 `_tick_call_scope_model`
replaces `{event_context}`, `{interval_label}`; :56 three events per
scope); `scripts/seed_pilot.py` (:1104 / :1130 / :1201 the events prompt,
:3245 its variables); `tooling/verify/checks/world_tick.py` (pins names
inside `_normalize_scope_event`).
Consequence: E types an item in `tick_events.py`, called from
`_normalize_scope_event`; the prompt changes by fragments.

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

### C-07 — the tick's typed item
Produced by: BRIEF-0119-E   Consumed by: (none in this lot)
`tick_events.typed_tick_payload(payload_in, *, title, description,
location_id, roster, actives, vocab, db, world_id, notes) -> dict | None |
UNTYPED`; `_normalize_scope_event(..., vocab=None, world_id="")`;
`setup["vocab"]`; `_tick_call_scope_model(..., vocab=None)`. Seed:
`WORLD_TICK_EVENTS_VARIABLES`, `WORLD_TICK_EVENTS_FRAGMENTS_0119`.

## Context

The world tick still proposes untyped events, typed by their domain at approval (C-06 of 0114). This brief shows it the world's event types and sortes, as Play sees them, and reads its events by code, role and name into Play's typed payload -- its changes pre-filled -- so the review card edits them (D). The tick proposes no new type (A1): it runs unattended.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `tick_events.py` (new, C-07): `typed_tick_payload`, `UNTYPED`;
   - `tick_normalize.py`: `_normalize_scope_event(..., vocab, world_id)` types an `event_creation` through it; `_tick_normalize_scope_event_creation(..., typed)`;
   - `tick.py`: `setup["vocab"] = analysis_vocabulary(...)`; `_tick_call_scope_model` fills `{event_types}` and `{sortes}`;
   - `scripts/seed_pilot.py`: the events prompt's typed shape and lists, `WORLD_TICK_EVENTS_VARIABLES`, `WORLD_TICK_EVENTS_FRAGMENTS_0119`; `scripts/apply_ticket_0119_tick_prompt.py` (new);
   - two docstrings (`event_payloads.py`, `writes/event_types.py`) no longer say the tick is untyped; creates check `event_tick.py` (ET1-ET5); appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/apply_ticket_0119_tick_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/event_payloads.py
   - src/world_engine/tick.py
   - src/world_engine/tick_events.py
   - src/world_engine/tick_normalize.py
   - src/world_engine/writes/event_types.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_tick.py

````diff
diff --git a/scripts/apply_ticket_0119_tick_prompt.py b/scripts/apply_ticket_0119_tick_prompt.py
new file mode 100644
index 0000000..267a871
--- /dev/null
+++ b/scripts/apply_ticket_0119_tick_prompt.py
@@ -0,0 +1,100 @@
+"""One-shot, idempotent delivery of the TICKET-0119 world tick events
+prompt update onto the live DB (BRIEF-0119-E): the scope-level tick reads
+the world's event types -- the `t` list, a new variable `event_types` --
+and its sortes (`sortes`), and names an event's type by code and its
+participants by role and name; it proposes no new type (A1).
+
+Like `apply_ticket_0114_analysis_prompt.py`, it edits the CURRENT version
+of `pt-world-tick-events` fragment by fragment, so an edit the creator made
+in the Prompts tab is kept. The fragments are
+`seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119` (single source: the seed's
+texts hold each new fragment). Per fragment: its new text present ->
+already done (looked for first: an old fragment may stand inside its own
+new text); else its old text present -> replaced; neither -> reported, to
+be edited by hand. The head's variables are first set to the seed's
+(`write_prompt_variables`), since a new version may only use declared
+placeholders.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+
+Run after `migrate_v2_26_event_effects.py`:
+
+    python scripts/apply_ticket_0119_tick_prompt.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0119_tick_prompt.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+from sqlmodel import Session  # noqa: E402
+
+import seed_pilot  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+from world_engine.writes.prompts import write_prompt_variables  # noqa: E402
+
+HEAD_ID = "pt-world-tick-events"
+NOTE = "TICKET-0119 BRIEF-0119-E -- the tick names typed events by code, role and name (A1)"
+
+
+def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
+    """`texts` with every fragment applied where its old text stands; the
+    fragments found in neither form."""
+    out = dict(texts)
+    missing = []
+    for field, old, new in seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119:
+        if new in out[field]:
+            continue
+        if old in out[field]:
+            out[field] = out[field].replace(old, new)
+        else:
+            missing.append(f"{field}: {old[:60]}…")
+    return out, missing
+
+
+def main() -> None:
+    # A fragment's text holds characters a Windows console cannot encode; a
+    # report line must never crash the delivery.
+    sys.stdout.reconfigure(errors="replace")
+    with Session(engine) as session:
+        head = session.get(PromptTemplate, HEAD_ID)
+        if head is None:
+            print(f"{HEAD_ID}: head not found -- nothing to do (the seed creates it)")
+            return
+        write_prompt_variables(session, template_id=head.id,
+                               variables=list(seed_pilot.WORLD_TICK_EVENTS_VARIABLES))
+        current = current_prompt(session, head)
+        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
+                                          "user_template": current.user_template})
+        for line in missing:
+            print(f"{HEAD_ID}: fragment not found, edit by hand -- {line}")
+        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
+            session.commit()
+            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
+            return
+        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
+                                       user_template=texts["user_template"], note=NOTE)
+        session.commit()
+        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 51ee6a9..415fda4 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1128,6 +1128,19 @@ briefing. Never invent identifiers, ids, people, places, or agenda titles
 absent from the briefing.
 
 === event_creation PAYLOAD ===
+  {"title":"…","description":"…",
+   "event_type":"t2",
+   "participants":[{"role":"<a role of the type>","name":"<name from the briefing>"},
+                   {"role":"<a role of the type>","sorte":"<a name from SORTES>"}],
+   "quantity":<int, only when the type counts one>,
+   "location":"<name, faction scope only, optional>"}
+
+"event_type" is the code of one type of TYPES D'ÉVÉNEMENTS (after the
+briefing). Each participant holds one of that type's roles, named exactly
+as listed: a person, place or faction by its NAME as the briefing writes
+it, or an anonymous kind of SORTES ("sorte") when the role accepts one.
+Never invent a type or a code. When no type of the list says what happened,
+use this former shape instead:
   {"title":"…","description":"…",
    "type":"political|magical|criminal|military|social|mystery|other",
    "knowledge_status":"secret|public",
@@ -1202,11 +1215,58 @@ WORLD_TICK_EVENTS_USER_TEMPLATE = """\
 SCOPE BRIEFING:
 {event_context}
 
+TYPES D'ÉVÉNEMENTS (code — nom, rôles) :
+{event_types}
+
+SORTES :
+{sortes}
+
 INTERVALLE ÉCOULÉ : {interval_label}
 
 Report what changed as a JSON array.\
 """
 
+# TICKET-0119 (BRIEF-0119-E, A1, R1): the tick names an event's type by
+# code and its participants by role and name, from the world's types and
+# sortes. The texts above hold each new fragment;
+# scripts/apply_ticket_0119_tick_prompt.py applies the same (field, old,
+# new) triples to the CURRENT version, so an edit the creator made in the
+# Prompts tab is kept (event_tick.py keeps the triples and the texts above
+# equal).
+WORLD_TICK_EVENTS_VARIABLES: tuple[str, ...] = ("event_context", "interval_label", "event_types", "sortes")
+WORLD_TICK_EVENTS_FRAGMENTS_0119: tuple[tuple[str, str, str], ...] = (
+    ("system_prompt",
+     "=== event_creation PAYLOAD ===\n"
+     '  {"title":"…","description":"…",\n'
+     '   "type":"political|magical|criminal|military|social|mystery|other",\n'
+     '   "knowledge_status":"secret|public",\n'
+     '   "involved_entities":["<name from the briefing>", …],\n'
+     '   "location":"<name, faction scope only, optional>"}\n',
+     "=== event_creation PAYLOAD ===\n"
+     '  {"title":"…","description":"…",\n'
+     '   "event_type":"t2",\n'
+     '   "participants":[{"role":"<a role of the type>","name":"<name from the briefing>"},\n'
+     '                   {"role":"<a role of the type>","sorte":"<a name from SORTES>"}],\n'
+     '   "quantity":<int, only when the type counts one>,\n'
+     '   "location":"<name, faction scope only, optional>"}\n'
+     "\n"
+     '"event_type" is the code of one type of TYPES D\'ÉVÉNEMENTS (after the\n'
+     "briefing). Each participant holds one of that type's roles, named exactly\n"
+     "as listed: a person, place or faction by its NAME as the briefing writes\n"
+     'it, or an anonymous kind of SORTES ("sorte") when the role accepts one.\n'
+     "Never invent a type or a code. When no type of the list says what happened,\n"
+     "use this former shape instead:\n"
+     '  {"title":"…","description":"…",\n'
+     '   "type":"political|magical|criminal|military|social|mystery|other",\n'
+     '   "knowledge_status":"secret|public",\n'
+     '   "involved_entities":["<name from the briefing>", …],\n'
+     '   "location":"<name, faction scope only, optional>"}\n'),
+    ("user_template", "SCOPE BRIEFING:\n{event_context}\n",
+     "SCOPE BRIEFING:\n{event_context}\n\nTYPES D'ÉVÉNEMENTS (code — nom, rôles) :\n{event_types}\n\n"
+     "SORTES :\n{sortes}\n"),
+)
+
+
 # BRIEF-47: World-bible generator. usage = "world_generation". Creator-side
 # draft generator for a NEW world's premise — entity_author.generate_world_draft
 # formats this user_template with only {brief} (no {type_fields}: a world
@@ -3242,7 +3302,7 @@ def seed(session: Session) -> None:
         usage="world_tick_events",
         system_prompt=WORLD_TICK_EVENTS_SYSTEM_PROMPT,
         user_template=WORLD_TICK_EVENTS_USER_TEMPLATE,
-        variables=["event_context", "interval_label"],
+        variables=list(WORLD_TICK_EVENTS_VARIABLES),
         destination="local",
     )
 
diff --git a/src/world_engine/event_payloads.py b/src/world_engine/event_payloads.py
index 1b2d662..222a85c 100644
--- a/src/world_engine/event_payloads.py
+++ b/src/world_engine/event_payloads.py
@@ -19,8 +19,8 @@ proposal's payload into that writer's `EventSpec`. Two payload shapes:
   `event_changes.payload_changes` for the writer to clean; and, edited on
   the review card (Y2, BRIEF-0119-D), its own `scopes` -- a list, even
   empty, replaces the type's.
-- untyped (the world tick until TICKET-0119, and every proposal written
-  before): `type` (a former category), `involved_entities`,
+- untyped (a world tick item naming no type of the world -- TICKET-0119,
+  A1 --, and every proposal written before): `type` (a former category), `involved_entities`,
   `knowledge_status`, `location_id`. It is typed by its domain
   (`writes.event_types.ensure_domain_type`, N1), its entities take the one
   role « Impliqué » when that role accepts their type (an entity it does
diff --git a/src/world_engine/tick.py b/src/world_engine/tick.py
index 930a159..cf324ae 100644
--- a/src/world_engine/tick.py
+++ b/src/world_engine/tick.py
@@ -23,6 +23,7 @@ from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
 from .analyzer import load_analysis_prompt
+from .event_analysis import analysis_vocabulary
 from .fact_refs import CodedRefs, knowledge_key
 from .prose_render import fact_texts
 from .models import Agenda, Character, Entity, Fact, FactionMembership, Knowledge, ProposedMutation
@@ -316,16 +317,23 @@ def _tick_scope_setup(db: Session, scope_type: str, scope_id: str, interval_labe
             select(Entity).where(Entity.world_id == setup["world_id"], Entity.status == "active")
         ).all()
     }
+    # TICKET-0119 (BRIEF-0119-E, A1): the world's event types and sortes, read
+    # once per scope call -- shown to the model and used to type its events.
+    setup["vocab"] = analysis_vocabulary(db, setup["world_id"])
     return setup
 
 
-def _tick_call_scope_model(db: Session, briefing: str, interval_label: str, model: str, host: str) -> list:
+def _tick_call_scope_model(db: Session, briefing: str, interval_label: str, model: str, host: str,
+                           vocab: Any = None) -> list:
     events_template = load_analysis_prompt(db, world_id=None, usage="world_tick_events")
     events_version = current_prompt(db, events_template)
+    values = vocab.prompt_values() if vocab is not None else {"event_types": "(aucun)", "sortes": "(aucune)"}
     events_user_message = (
         events_version.user_template
         .replace("{event_context}", briefing)
         .replace("{interval_label}", interval_label)
+        .replace("{event_types}", values["event_types"])
+        .replace("{sortes}", values["sortes"])
     )
     events_llm_messages = [
         {"role": "system", "content": events_version.system_prompt},
@@ -398,7 +406,8 @@ def _tick_normalize_scope_items(
         normalized = _normalize_scope_event(
             raw_item, scope_type=scope_type, scope_id=scope_id, roster=setup["roster"],
             locations=setup["locations_index"], agendas_index=setup["agendas_index"],
-            actives=setup["actives_index"], db=db, notes=event_notes,
+            actives=setup["actives_index"], db=db, notes=event_notes, vocab=setup.get("vocab"),
+            world_id=world_id,
         )
         if normalized is None:
             dropped_events += 1
@@ -432,7 +441,8 @@ def _tick_run_scope_events(
     }
     try:
         setup = _tick_scope_setup(db, scope_type, scope_id, interval_label)
-        event_items = _tick_call_scope_model(db, setup["briefing"], interval_label, model, host)
+        event_items = _tick_call_scope_model(db, setup["briefing"], interval_label, model, host,
+                                             setup.get("vocab"))
     except Exception as exc:  # noqa: BLE001 — degrade-don't-abort (R3), same as the per-NPC loop
         event_notes.append(f"scope event call failed: {exc}")
         event_items = []
diff --git a/src/world_engine/tick_events.py b/src/world_engine/tick_events.py
new file mode 100644
index 0000000..6dbb63c
--- /dev/null
+++ b/src/world_engine/tick_events.py
@@ -0,0 +1,76 @@
+"""The world tick's typed events (TICKET-0119, BRIEF-0119-E; decisions A1,
+M-c and R1 of the conditions series).
+
+The scope-level tick call (`tick._tick_call_scope_model`) shows the model
+the world's event types as Play does -- the coded `t` list, each with its
+roles, and the sortes by name (`event_analysis.analysis_vocabulary`). Its
+`event_creation` names a type by code (`event_type`) and each participant
+by the role it holds: a person, place or faction by its NAME as the
+briefing writes it, or a sorte by name; a quantity when the type counts one.
+
+`typed_tick_payload` reads that into the payload Play's analyzer makes
+(`event_analysis.typed_payload`, fail-closed: an unknown code drops the
+proposal, a participant its type cannot take is left out), its changes
+pre-filled from the type's effects (M-c). A name resolves through the
+scope's roster first, then every active entity of the world; one that does
+not is left out with a note, never guessed. The tick proposes no new type
+(A1): it runs unattended, three events per scope, and its vocabulary would
+drift -- a `new_type` is set aside with a note, and an item naming no
+existing type keeps the former, untyped shape (typed by its domain at
+approval, `event_payloads`).
+
+Reads only; writes nothing.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from .event_analysis import AnalysisVocabulary, typed_payload
+
+# The marker of an item that names no type: the caller keeps its untyped shape.
+UNTYPED = "untyped"
+
+
+def _participants(raw: Any, roster: dict[str, str], actives: dict[str, str], title: str,
+                  notes: list[str]) -> list[dict]:
+    out: list[dict] = []
+    for item in raw if isinstance(raw, list) else []:
+        if not isinstance(item, dict):
+            continue
+        role = str(item.get("role") or "").strip()
+        if str(item.get("sorte") or "").strip():
+            out.append({"role": role, "sorte": str(item["sorte"]).strip()})
+            continue
+        name = str(item.get("name") or "").strip()
+        entity_id = roster.get(name.casefold()) or actives.get(name.casefold())
+        if entity_id is None:
+            notes.append(f"event {title!r}: unresolved participant name {name!r} dropped")
+            continue
+        out.append({"role": role, "entity_id": entity_id})
+    return out
+
+
+def typed_tick_payload(
+    payload_in: dict, *, title: str, description: Optional[str], location_id: Optional[str],
+    roster: dict[str, str], actives: dict[str, str], vocab: Optional[AnalysisVocabulary], db: Session,
+    world_id: str, notes: list[str],
+) -> Any:
+    """The queue's typed payload of one tick item, None to drop it, or
+    `UNTYPED` when it names no existing type (see the module docstring)."""
+    if payload_in.get("new_type") is not None:
+        notes.append(f"event {title!r}: the tick proposes no new type (A1) -- set aside")
+    code = payload_in.get("event_type")
+    if vocab is None or code in (None, "") or isinstance(code, dict):
+        return UNTYPED
+    raw = {
+        "title": title, "description": description, "event_type": code, "location_id": location_id,
+        "participants": _participants(payload_in.get("participants"), roster, actives, title, notes),
+        "quantity": payload_in.get("quantity"),
+    }
+    typed = typed_payload(db, world_id, raw, vocab)
+    if typed is None:
+        notes.append(f"event {title!r}: unknown event type code {code!r} dropped")
+    return typed
diff --git a/src/world_engine/tick_normalize.py b/src/world_engine/tick_normalize.py
index d95e106..ef9440f 100644
--- a/src/world_engine/tick_normalize.py
+++ b/src/world_engine/tick_normalize.py
@@ -27,6 +27,7 @@ from .analyzer import _GOAL_ACTION_MAP, _MUTATION_TYPE_MAP
 from .fact_refs import CodedRefs
 from .models import Agenda, AgendaStep, Character, Entity, Faction, Relation
 from .tick_context import _perceived_target
+from .tick_events import UNTYPED, typed_tick_payload
 
 _log = logging.getLogger(__name__)
 
@@ -431,12 +432,21 @@ def _tick_normalize_scope_entity_creation(
 def _tick_normalize_scope_event_creation(
     payload_in: dict, rationale: str, *, scope_type: str, scope_id: str,
     roster: dict[str, str], locations: dict[str, str], notes: list[str],
+    typed: Any = UNTYPED,
 ) -> dict | None:
-    """The default shape (TICKET-0017, BRIEF-0017-a)."""
+    """The default shape (TICKET-0017, BRIEF-0017-a). Since TICKET-0119
+    (BRIEF-0119-E) an item naming one of the world's types arrives `typed`
+    (`tick_events.typed_tick_payload`); None drops it; `UNTYPED` keeps the
+    former shape below."""
     title = str(payload_in.get("title") or "").strip()
     if not title:
         notes.append("dropped event_creation: empty title")
         return None
+    if typed is None:
+        return None
+    if typed != UNTYPED:
+        return {"mutation_type": "event_creation", "target_table": "event", "target_id": None,
+                "payload": typed, "rationale": rationale}
 
     description = payload_in.get("description")
     description = str(description).strip() or None if description else None
@@ -497,6 +507,8 @@ def _normalize_scope_event(
     actives: dict[str, str],
     db: Session,
     notes: list[str],
+    vocab: Any = None,
+    world_id: str = "",
 ) -> dict | None:
     """Map one raw model item to the scope-level schema, or None to drop it
     (TICKET-0017, BRIEF-0017-a; grown to four types TICKET-0018/0019,
@@ -516,7 +528,10 @@ def _normalize_scope_event(
     agendas of the faction (empty for a location scope). `actives` is
     name.casefold() -> id for EVERY active entity of the world, any type —
     the entity_creation collision guard. `notes` is the caller's shared
-    notes list — parse-time drops and clamps are appended to it.
+    notes list — parse-time drops and clamps are appended to it. `vocab`
+    (TICKET-0119, BRIEF-0119-E): the world's event vocabulary, read once per
+    scope call; an `event_creation` naming one of its types is typed through
+    `tick_events.typed_tick_payload`.
     """
     if not isinstance(raw_item, dict):
         notes.append(f"dropped scope item: not a dict — {raw_item!r}")
@@ -543,9 +558,17 @@ def _normalize_scope_event(
     if raw_mutation_type == "entity_creation":
         return _tick_normalize_scope_entity_creation(payload_in, rationale, actives=actives, notes=notes)
 
+    title = str(payload_in.get("title") or "").strip()
+    location_id = scope_id if scope_type == "location" else locations.get(
+        str(payload_in.get("location") or "").strip().casefold())
+    typed = typed_tick_payload(
+        payload_in, title=title, description=str(payload_in.get("description") or "").strip() or None,
+        location_id=location_id, roster=roster, actives=actives, vocab=vocab, db=db, world_id=world_id,
+        notes=notes,
+    ) if title else UNTYPED
     return _tick_normalize_scope_event_creation(
         payload_in, rationale, scope_type=scope_type, scope_id=scope_id,
-        roster=roster, locations=locations, notes=notes,
+        roster=roster, locations=locations, notes=notes, typed=typed,
     )
 
 
diff --git a/src/world_engine/writes/event_types.py b/src/world_engine/writes/event_types.py
index 8816d75..40a01e0 100644
--- a/src/world_engine/writes/event_types.py
+++ b/src/world_engine/writes/event_types.py
@@ -32,7 +32,8 @@ decisions B1, C1, D1, N1 and W1 of the conditions series): the one writer of
 - `ensure_domain_type(db, *, world_id, domain)` : the type made from a
   domain (N1) -- « Social », one role « Impliqué » accepting every entity
   type of the world -- found by its name, created when the world has none.
-  It types what still arrives untyped (the world tick until TICKET-0119).
+  It types what still arrives untyped (a world tick item naming no type,
+  TICKET-0119).
 
 None of these functions commits.
 """
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 9e45119..35b6b16 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19582,6 +19582,30 @@ on the draft's participants (`event_changes.type_changes`, the one
 pre-fill) and puts each change in French; the editor's « Pré-remplir »
 merges them into the draft's changes. It reads only.
 
+## THE WORLD TICK PROPOSES TYPED EVENTS -- THE WORLD'S TYPES BY CODE, PARTICIPANTS BY ROLE AND NAME; NEVER A NEW TYPE (TICKET-0119) -- `tick_events.py` (BRIEF-0119-e, no schema change)
+
+**R1 in the tick.** The scope-level tick call shows the model the world's
+event types as Play does (`analysis_vocabulary`, read once per scope call:
+the coded `t` list with each type's roles, the sortes by name). Its
+`event_creation` names a type by code and each participant by the role it
+holds -- a person, place or faction by its NAME as the briefing writes it,
+a sorte by name. `tick_events.typed_tick_payload` resolves a name through
+the scope's roster, then every active entity of the world; a name nobody
+bears is left out with a note, never guessed. The payload is Play's
+(`event_analysis.typed_payload`), fail-closed the same way, its changes
+pre-filled from its type's effects (M-c); the review card edits it (Y2).
+
+**A1.** The tick proposes no new type: it runs unattended, three events per
+scope, and its vocabulary would drift. A `new_type` is set aside with a
+note; an item naming no type of the world keeps the former untyped shape,
+typed by its domain at approval (N1). Reactivation: the dashboard (0115)
+shows the creator retyping the tick's domain-typed events often.
+
+**Prompt.** Two fragments of `WORLD_TICK_EVENTS_FRAGMENTS_0119` (the typed
+shape beside the former one, the two lists after the briefing), delivered by
+`apply_ticket_0119_tick_prompt.py` fragment by fragment: the creator's
+edits are kept.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_tick.py b/tooling/verify/checks/event_tick.py
new file mode 100644
index 0000000..06f5820
--- /dev/null
+++ b/tooling/verify/checks/event_tick.py
@@ -0,0 +1,336 @@
+"""G1 check for TICKET-0119 -- the world tick proposes typed events: the world's types by code, participants by role and name; never a new type.
+
+BRIEF-0119-E's rules (A1, M-c and R1 of the conditions series).
+
+ET1 -- the prompt (static and fixture). The seed's tick events texts hold
+   each new fragment of `WORLD_TICK_EVENTS_FRAGMENTS_0119` exactly once; the
+   head's variables (`WORLD_TICK_EVENTS_VARIABLES`) are exactly the user
+   template's placeholders, `event_types` and `sortes` among them.
+   `apply_ticket_0119_tick_prompt.py`, on a head holding the former texts
+   and variables, writes one version equal to the seed's with its
+   variables; a second run is unchanged; on a head the creator edited where
+   a fragment stood, her edit is kept and the fragment reported.
+ET2 -- the call (fixture). `_tick_call_scope_model`, its model call
+   replaced, sends a user message holding the coded type line of « Chasse »
+   and the sorte « Loup », and no placeholder left.
+ET3 -- typed items (fixture, `_normalize_scope_event` on a location
+   scope). An item naming « Chasse » by code, its hunter by name (a roster
+   member) and its prey by sorte, with a quantity, becomes a typed
+   `event_creation`: the type's id, the hunter's entity id in his role, the
+   sorte by id, the quantity, the scope as its place, and the type's
+   effects pre-filled in `state_changes`; a participant named by an active
+   entity outside the roster is kept; a name nobody bears is left out with
+   a note; an unknown code drops the item with a note.
+ET4 -- never a new type (fixture). An item with a `new_type` and no
+   `event_type` keeps the former untyped shape (`type`,
+   `knowledge_status`, `involved_entities`) with a note -- no `new_type` in
+   its payload; an item with neither keeps the untyped shape too.
+ET5 -- wiring (static). `tick._tick_scope_setup` reads
+   `analysis_vocabulary` once into `setup["vocab"]`, which the scope call and
+   the normalizer receive; `tick_events.py` imports nothing from `writes`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import re
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+SCRIPT = ROOT / "scripts" / "apply_ticket_0119_tick_prompt.py"
+HEAD = "pt-world-tick-events"
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
+    sys.path.insert(0, str(ROOT / "scripts"))
+
+
+# --- ET1 -----------------------------------------------------------------------
+
+def _texts() -> dict[str, str]:
+    import seed_pilot
+
+    return {"system_prompt": seed_pilot.WORLD_TICK_EVENTS_SYSTEM_PROMPT,
+            "user_template": seed_pilot.WORLD_TICK_EVENTS_USER_TEMPLATE}
+
+
+def _former_texts() -> dict[str, str]:
+    import seed_pilot
+
+    texts = _texts()
+    for field, old, new in seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119:
+        texts[field] = texts[field].replace(new, old)
+    return texts
+
+
+def _prompt_db(texts: dict[str, str]) -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import PromptTemplate
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(PromptTemplate(id=HEAD, name="tick events", usage="world_tick_events", world_id=None,
+                              destination="local"))
+        db.flush()
+        write_prompt_variables(db, template_id=HEAD, variables=["event_context", "interval_label"])
+        write_prompt_version(db, template_id=HEAD, note="former", **texts)
+        db.commit()
+    eng.dispose()
+    return db_path
+
+
+def _run(db_path: str):
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, select
+
+    from world_engine.models import PromptTemplate, PromptVariable
+    from world_engine.prompt_store import current_prompt
+
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
+                            cwd=str(ROOT), timeout=60)
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as db:
+        version = current_prompt(db, db.get(PromptTemplate, HEAD))
+        state = (version.version_number, version.system_prompt, version.user_template,
+                 set(db.exec(select(PromptVariable.name)).all()))
+    eng.dispose()
+    return result, state
+
+
+def check_et1() -> None:
+    import seed_pilot
+
+    texts = _texts()
+    fragments = seed_pilot.WORLD_TICK_EVENTS_FRAGMENTS_0119
+    if not fragments:
+        fail("ET1: WORLD_TICK_EVENTS_FRAGMENTS_0119 is empty")
+    for field, _old, new in fragments:
+        if texts[field].count(new) != 1:
+            fail(f"ET1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
+    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
+    if used != set(seed_pilot.WORLD_TICK_EVENTS_VARIABLES) or not {"event_types", "sortes"} <= used:
+        fail(f"ET1: variables {seed_pilot.WORLD_TICK_EVENTS_VARIABLES}, template {sorted(used)}")
+    seed = (texts["system_prompt"], texts["user_template"])
+    result, state = _run(_prompt_db(_former_texts()))
+    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
+            or state[3] != set(seed_pilot.WORLD_TICK_EVENTS_VARIABLES):
+        fail(f"ET1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
+             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
+    db_path = _prompt_db(_former_texts())
+    _run(db_path)
+    again, state = _run(db_path)
+    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
+        fail(f"ET1: a second run: {again.stdout.strip()[-200:]}")
+    edited = _former_texts()
+    _field, lost, _new = fragments[0]
+    edited["system_prompt"] = edited["system_prompt"].replace(lost, "(retouché à la main)")
+    result, state = _run(_prompt_db(edited))
+    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[1] \
+            or "{event_types}" not in state[2]:
+        fail(f"ET1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")
+
+
+# --- fixture -------------------------------------------------------------------
+
+def _world(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, PromptTemplate, World
+    from world_engine.writes.attributes import DefinitionSpec, write_attribute_definition
+    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    import seed_pilot
+
+    with Session(engine) as db:
+        world = World(name="Tick", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("foret", "location", "Forêt"), ("brakk", "character", "Brakk"),
+                                ("ysa", "character", "Ysa")):
+            row = Entity(world_id=world.id, type=kind, name=name)
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Character(id=row.id, world_id=world.id, character_type="npc", current_location_id=None)
+                   if kind == "character" else Location(id=row.id))
+        fatigue = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Fatigue", kind="integer", holder_types=("character",), default=0))
+        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Chasse", counts_quantity=True,
+            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True)),
+            effects=(EffectSpec("Chasseur", fatigue.id, 1, "add"),)))
+        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
+        ids["chasse"], ids["fatigue"] = chasse.id, fatigue.id
+        for role in type_view(db, chasse.id).roles:
+            ids[role.name] = role.id
+        db.add(PromptTemplate(id=HEAD, name="tick events", usage="world_tick_events", world_id=None,
+                              destination="local"))
+        db.flush()
+        write_prompt_variables(db, template_id=HEAD, variables=list(seed_pilot.WORLD_TICK_EVENTS_VARIABLES))
+        write_prompt_version(db, template_id=HEAD, note="seed", **_texts())
+        db.commit()
+    return ids
+
+
+def check_et2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import ollama_client, tick
+    from world_engine.event_analysis import analysis_vocabulary
+
+    sent: list = []
+
+    def fake_chat(messages, **_kwargs):
+        sent.append(messages)
+        return "[]"
+
+    real = tick.ollama_client.chat
+    tick.ollama_client.chat = fake_chat
+    try:
+        with Session(engine) as db:
+            vocab = analysis_vocabulary(db, ids["world"])
+            tick._tick_call_scope_model(db, "BRIEF", "trois jours", ollama_client.DEFAULT_MODEL, "h", vocab)
+    finally:
+        tick.ollama_client.chat = real
+    user = sent[0][1]["content"] if sent else ""
+    if "Chasse" not in user or "Loup" not in user or "t1" not in user or re.search(r"\{[a-z_]+\}", user):
+        fail(f"ET2: the tick's user message is {user[-300:]!r}")
+
+
+def _normalize(db, ids: dict, item: dict, notes: list):
+    from world_engine.event_analysis import analysis_vocabulary
+    from world_engine.tick_normalize import _normalize_scope_event
+
+    return _normalize_scope_event(
+        item, scope_type="location", scope_id=ids["foret"], roster={"brakk": ids["brakk"]}, locations={},
+        agendas_index={}, actives={"brakk": ids["brakk"], "ysa": ids["ysa"]}, db=db, notes=notes,
+        vocab=analysis_vocabulary(db, ids["world"]), world_id=ids["world"])
+
+
+def check_et3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.event_analysis import analysis_vocabulary
+
+    with Session(engine) as db:
+        code = analysis_vocabulary(db, ids["world"]).codes.code_of(ids["chasse"])
+        notes: list = []
+        item = {"mutation_type": "event_creation", "rationale": "r", "payload": {
+            "title": "La chasse", "event_type": code, "quantity": 3, "participants": [
+                {"role": "Chasseur", "name": "Brakk"}, {"role": "Chasseur", "name": "Ysa"},
+                {"role": "Chasseur", "name": "Personne"}, {"role": "Proie", "sorte": "Loup"}]}}
+        out = _normalize(db, ids, item, notes)
+        payload = out["payload"] if out else {}
+        got = (payload.get("type_id"), payload.get("quantity"), payload.get("location_id"),
+               [(p["role_id"], p["entity_id"], p["sorte_id"]) for p in payload.get("participants", [])],
+               payload.get("state_changes"))
+        want = (ids["chasse"], 3, ids["foret"],
+                [(ids["Chasseur"], ids["brakk"], None), (ids["Chasseur"], ids["ysa"], None),
+                 (ids["Proie"], None, ids["loup"])],
+                [{"entity_id": ids["brakk"], "attribute": ids["fatigue"], "mode": "add", "value": 1},
+                 {"entity_id": ids["ysa"], "attribute": ids["fatigue"], "mode": "add", "value": 1}])
+        if out is None or out["mutation_type"] != "event_creation" or got != want:
+            fail(f"ET3: a typed item gave {got}")
+        if not any("Personne" in n for n in notes):
+            fail(f"ET3: an unresolved name left no note: {notes}")
+        notes = []
+        dropped = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
+            "title": "Inconnue", "event_type": "t99", "participants": []}}, notes)
+        if dropped is not None or not any("t99" in n for n in notes):
+            fail(f"ET3: an unknown code gave {dropped}, notes {notes}")
+
+
+def check_et4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as db:
+        notes: list = []
+        out = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
+            "title": "Un pacte", "new_type": {"name": "Pacte", "roles": [{"name": "Partie", "for": ["character"]}]},
+            "type": "political", "knowledge_status": "secret", "involved_entities": ["Brakk"]}}, notes)
+        payload = out["payload"] if out else {}
+        if "new_type" in payload or payload.get("type") != "political" or payload.get("involved_entities") != [
+                ids["brakk"]] or not any("A1" in n for n in notes):
+            fail(f"ET4: a new type gave {payload}, notes {notes}")
+        plain = _normalize(db, ids, {"mutation_type": "event_creation", "payload": {
+            "title": "Une rumeur", "type": "social", "knowledge_status": "public", "involved_entities": []}}, [])
+        if not plain or plain["payload"].get("type") != "social" or "type_id" in plain["payload"]:
+            fail(f"ET4: an untyped item gave {plain}")
+
+
+def check_et5() -> None:
+    source = (SRC / "tick.py").read_text(encoding="utf-8")
+    tree = ast.parse(source)
+    setup = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_tick_scope_setup"),
+                 None)
+    body = ast.get_source_segment(source, setup) if setup else ""
+    if body.count('setup["vocab"] = analysis_vocabulary(db, setup["world_id"])') != 1:
+        fail("ET5: _tick_scope_setup does not read the vocabulary once")
+    if 'setup.get("vocab")' not in source or source.count('setup.get("vocab")') < 2:
+        fail("ET5: the scope call and the normalizer do not both receive setup['vocab']")
+    events = ast.parse((SRC / "tick_events.py").read_text(encoding="utf-8"))
+    for node in ast.walk(events):
+        if isinstance(node, ast.ImportFrom) and node.module and "writes" in node.module:
+            fail(f"ET5: tick_events.py imports {node.module}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    try:
+        check_et1()
+    except Exception as exc:  # a crash is a failure, never a pass
+        fail(f"ET1: crashed -- {type(exc).__name__}: {exc}")
+    try:
+        ids = _world(engine)
+    except Exception as exc:  # a crash is a failure, never a pass
+        fail(f"ET2-ET4: the fixture crashed -- {type(exc).__name__}: {exc}")
+        ids = None
+    for name, rule in (("ET2", check_et2), ("ET3", check_et3), ("ET4", check_et4)):
+        if ids is None:
+            break
+        try:
+            rule(engine, ids)
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    check_et5()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_tick -- the world tick shows the model the world's event types and sortes, reads its events "
+          "by code, role and name into typed proposals with their changes pre-filled, never proposes a new type, "
+          "and its prompt is delivered fragment by fragment")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

2. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
3. Run the checks below, then the full corpus.

## Scope OUT

- The tick proposing a new type (A1, rejected for the tick; reactivation in the ticket).
- The per-NPC tick (it proposes no event).
- Delivering the prompt to Nia's database: she runs `apply_ticket_0119_tick_prompt.py` after the merge (the ticket's live gate).
- Every later brief of this lot: BRIEF-0119-F, G.

## Invariants to defend

INV-34: tick rows keep `source_type='world_tick'`, `proposed_by='local_ai_tick'` and their `tick_id`; nothing applies them. INV-48: prompt text changes only as a new `prompt_version`, through the delivery script, the creator's edits kept. INV-19: the call still resolves its model through `effective_model`. INV-22: a type is named by a code from a coded list; code resolves it.

## Decision rights

STOP:
- The tick would write vocabulary (a type or a sorte) itself.
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
- `python tooling/verify/checks/event_tick.py` -> `PASS`.
- `python tooling/verify/checks/world_tick.py` -> `PASS`.
- `python tooling/verify/checks/event_analyzer.py` -> `PASS`.
- `python tooling/verify/checks/prompt_registry.py` -> `PASS`.
- `python tooling/verify/checks/prompt_lean.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (160 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **ET1** -- `scripts/seed_pilot.py`: `WORLD_TICK_EVENTS_VARIABLES: tuple[str, ...] = ("event_context", "interval_label", "event_types", "sortes")` -> `WORLD_TICK_EVENTS_VARIABLES: tuple[str, ...] = ("event_context", "interval_label", "event_types")`
  - **ET2** -- `tick.py _tick_call_scope_model`: `        .replace("{sortes}", values["sortes"])` -> `(the line removed)`
  - **ET3** -- `tick_events.py _participants`: `        entity_id = roster.get(name.casefold()) or actives.get(name.casefold())` -> `        entity_id = roster.get(name.casefold())`
  - **ET4** -- `tick_events.py typed_tick_payload`: `    if payload_in.get("new_type") is not None:` -> `    if False:`
  - **ET5** -- `tick.py _tick_scope_setup`: `    setup["vocab"] = analysis_vocabulary(db, setup["world_id"])` -> `    setup["vocab"] = None`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
