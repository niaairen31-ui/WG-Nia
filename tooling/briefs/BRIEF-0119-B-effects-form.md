<!-- slug: effects-form -->
# BRIEF 0119-B — "« Vocabulaire du monde » edits what a type does to the state of the world -- its effects in the type form (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-A (C-01, C-02)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-A's commit).

- `src/world_engine/cockpit/routes/event_types.py` -> `class EventTypeBody(BaseModel):` with no `effects` field
- `src/world_engine/cockpit/routes/event_types.py` -> `def event_vocabulary(` whose answer has no `states` key
- `src/world_engine/event_vocab.py` -> `class EffectView:` (BRIEF-0119-A's)
- `src/world_engine/writes/event_types.py` -> `EFFECT_SYSTEM_KEYS: tuple[str, ...] = ("sys:vital_status", "sys:status")` (BRIEF-0119-A's)
- `frontend/src/creation/EventTypeForm.svelte` -> no `effects`

## Facts carried

### R-01 — the event vocabulary and its writer [M]
Opened: `src/world_engine/models/canon_event.py` (the declaring file:
`EventType`, `EventTypeRole`, `EventTypeRoleType`, `EventTypeScope` :110,
`EventSorte`, `EventParticipant` :143; `EVENT_SCOPE_LEVELS` :53, quoted by
the CHECKs); `src/world_engine/writes/event_types.py` (`EventTypeSpec` :85 --
name, domain, roles, counts_quantity, in_chronicle, participants_secret,
scopes; `clean_event_type` :169; `_write_scopes` :270 deletes and
re-inserts a type's scopes; `write_event_type` :278; `ensure_domain_type`
:364); `src/world_engine/event_vocab.py` (`EventTypeView` :66, `_view`
:107, `type_view` :116).
Finding: a type has no effect; its scopes are the full-replace precedent.
Consequence: A adds `event_type_effect` beside the scopes, written whole by
`_write_effects`, read into `EventTypeView.effects`.

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

### C-03 — the vocabulary's routes
Produced by: BRIEF-0119-B   Consumed by: D, G
`EffectBody(role, attribute, mode="set", value: int | str | None)`;
`EventTypeBody.effects`; `type_dict(...)["effects"]` = `[{role (name),
attribute, mode, value (a role's NAME for an entity state)}]`;
`event_vocabulary(...)["states"]` = `[state_dict]` for the two
`EFFECT_SYSTEM_KEYS` and the world's active definitions: `{key, name, kind,
system, holder_types (None: all), value_types, choices [{value, label}]}`.
Frontend: `vocabState.states`; `typeDraft` / `typeBody` carry `effects`.

## Context

A's effects are stored and cleaned, but nothing edits them. The creator defines a type's effects where she defines the type: « Vocabulaire du monde » (T3 of 0114). The same form serves the interpreter's and the analyzer's proposal cards, so a proposed type may carry effects too.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `cockpit/routes/event_types.py` (C-03): `EffectBody`, `EventTypeBody.effects`, `event_type_spec` reads them, `type_dict` answers `effects` (a role's NAME for an entity state), `state_dict`, `event_vocabulary` answers `states` -- the two `EFFECT_SYSTEM_KEYS` and the world's active definitions;
   - frontend: `eventVocab.svelte.js` (`vocabState.states`, `typeDraft` / `typeBody` carry `effects`), `EventTypeForm.svelte` (the effects block: role, state, value by kind, `devient` / `augmente de`);
   - adds EF6-EF7 to `event_effects.py`; appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/EventTypeForm.svelte
   - frontend/src/creation/eventVocab.svelte.js
   - src/world_engine/cockpit/routes/event_types.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_effects.py

````diff
diff --git a/frontend/src/creation/EventTypeForm.svelte b/frontend/src/creation/EventTypeForm.svelte
index 89900e3..ebe77f0 100644
--- a/frontend/src/creation/EventTypeForm.svelte
+++ b/frontend/src/creation/EventTypeForm.svelte
@@ -7,7 +7,13 @@
      level. `draft` is a `typeDraft` owned by the caller -- the « Vocabulaire
      du monde » tab, or a proposal card (BRIEF-0114-G/H); `vocab` the
      vocabulary lists (`vocabState`). The server refuses taking away what is
-     in use. */
+     in use.
+
+     TICKET-0119 (BRIEF-0119-B, M-c, D3, E1): its effects -- what an event of
+     it does to the state of the world, each « role -> state = value »: a
+     choice of the state, an integer set or added (`'add'`), or the entity of
+     another role (`value_role`, for a state naming an entity). They
+     pre-fill an event's proposal; the creator keeps, edits or drops each. */
   let { draft, vocab } = $props();
 
   function toggle(list, type) {
@@ -25,6 +31,40 @@
   }
 
   const withRole = (kind) => kind === 'rencontre' || kind === 'faction';
+
+  function stateOf(key) {
+    return (vocab.states || []).find((s) => s.key === key) || null;
+  }
+
+  function roleTypes(name) {
+    const role = draft.roles.find((r) => r.name === name);
+    return role ? role.entity_types : [];
+  }
+
+  // The states that apply to an entity the role holds.
+  function statesFor(roleName) {
+    const types = roleTypes(roleName);
+    return (vocab.states || []).filter((s) => s.holder_types === null || s.holder_types.some((t) => types.includes(t)));
+  }
+
+  // value_role: for a state naming an entity, the other roles whose entities it may name.
+  function valueRoles(effect, state) {
+    return draft.roles.filter((r) => r.name && r.name !== effect.role
+      && r.entity_types.some((t) => state.value_types.includes(t)));
+  }
+
+  function addEffect() {
+    const role = draft.roles.find((r) => r.name && r.entity_types.length);
+    if (!draft.effects) draft.effects = [];
+    draft.effects.push({ role: role ? role.name : '', attribute: '', mode: 'set', value: null });
+  }
+
+  function onState(effect) {
+    const state = stateOf(effect.attribute);
+    effect.mode = 'set';
+    effect.value = state && state.kind === 'choice' && state.choices.length ? state.choices[0].value
+      : state && state.kind === 'integer' ? 1 : null;
+  }
 </script>
 
 <div class="etype-form">
@@ -83,6 +123,44 @@
     {#if !draft.scopes.length}<div class="etype-hint">Personne d'autre que les participants.</div>{/if}
     <button onclick={addScope}>+ portée</button>
   </div>
+
+  <div class="etype-block">
+    <span>Ce qu'il change dans le monde (pré-rempli sur chaque événement)</span>
+    {#each draft.effects || [] as effect, k (k)}
+      {@const state = stateOf(effect.attribute)}
+      <div class="etype-line">
+        <select bind:value={effect.role} title="Le rôle dont l'entité change">
+          <option value="">— rôle —</option>
+          {#each draft.roles.filter((r) => r.name && r.entity_types.length) as role, r (r)}
+            <option value={role.name}>{role.name}</option>
+          {/each}
+        </select>
+        <select bind:value={effect.attribute} onchange={() => onState(effect)} title="L'état">
+          <option value="">— état —</option>
+          {#each statesFor(effect.role) as s (s.key)}<option value={s.key}>{s.name}</option>{/each}
+        </select>
+        {#if state && state.kind === 'choice'}
+          <select bind:value={effect.value}>
+            {#each state.choices as c (c.value)}<option value={c.value}>{c.label}</option>{/each}
+          </select>
+        {:else if state && state.kind === 'integer'}
+          <select bind:value={effect.mode}>
+            <option value="set">devient</option>
+            <option value={'add'}>augmente de</option>
+          </select>
+          <input type="number" style="width:70px" bind:value={effect.value}>
+        {:else if state && state.kind === 'entity'}
+          <select bind:value={effect.value} title="value_role : l'entité d'un autre rôle">
+            <option value={null}>— rôle —</option>
+            {#each valueRoles(effect, state) as role, r (r)}<option value={role.name}>{role.name}</option>{/each}
+          </select>
+        {/if}
+        <button class="btn-icon" title="Retirer" onclick={() => draft.effects.splice(k, 1)}>✕</button>
+      </div>
+    {/each}
+    {#if !(draft.effects || []).length}<div class="etype-hint">Aucun état ne change.</div>{/if}
+    <button onclick={addEffect}>+ effet</button>
+  </div>
 </div>
 
 <style>
diff --git a/frontend/src/creation/eventVocab.svelte.js b/frontend/src/creation/eventVocab.svelte.js
index 9267eeb..7882677 100644
--- a/frontend/src/creation/eventVocab.svelte.js
+++ b/frontend/src/creation/eventVocab.svelte.js
@@ -7,7 +7,10 @@
    A name near another's comes back `saved: false` with the near ones: the
    creator opens the existing one or creates anyway (`confirm_near`).
    `typeDraft` / `typeBody` are shared with the journal's sheet and the
-   interpreter's and analyzer's proposal cards (BRIEF-0114-C/G/H). */
+   interpreter's and analyzer's proposal cards (BRIEF-0114-C/G/H). Since
+   TICKET-0119 (BRIEF-0119-B) a type carries its effects -- what an event of
+   it does to the state of the world -- and `states` lists what they may
+   change. */
 import { api } from './sheetRequest.svelte.js';
 
 export const vocabState = $state({
@@ -17,6 +20,7 @@ export const vocabState = $state({
   domains: [],
   scopeKinds: [],
   levels: [],
+  states: [], // TICKET-0119: the states an effect may change, {key, name, kind, system, holder_types, value_types, choices}
   loadError: '',
   typeDraft: null, // typeDraft(), plus `id` when it edits one
   sorteDraft: null, // { id, name }
@@ -31,7 +35,7 @@ export function typeDraft(type) {
   if (!type) {
     return { id: null, name: '', domain: 'other', counts_quantity: false, in_chronicle: true,
              participants_secret: false, roles: [{ id: null, name: '', entity_types: ['character'], accepts_sorte: false }],
-             scopes: [] };
+             scopes: [], effects: [] };
   }
   return {
     id: type.id || null, name: type.name, domain: type.domain, counts_quantity: !!type.counts_quantity,
@@ -40,6 +44,9 @@ export function typeDraft(type) {
       id: r.id || null, name: r.name, entity_types: [...(r.entity_types || [])], accepts_sorte: !!r.accepts_sorte,
     })),
     scopes: (type.scopes || []).map((s) => ({ kind: s.kind, role: s.role || null, level: s.level })),
+    // TICKET-0119 (M-c): what an event of the type does to the state of the world.
+    effects: (type.effects || []).map((e) => ({ role: e.role, attribute: e.attribute, mode: e.mode || 'set',
+                                                value: e.value })),
   };
 }
 
@@ -52,6 +59,8 @@ export function typeBody(draft, confirmNear) {
                                      accepts_sorte: r.accepts_sorte })),
     scopes: draft.scopes.map((s) => ({ kind: s.kind, role: ['rencontre', 'faction'].includes(s.kind) ? s.role : null,
                                        level: s.level })),
+    effects: (draft.effects || []).map((e) => ({ role: e.role, attribute: e.attribute, mode: e.mode || 'set',
+                                                 value: e.value })),
     confirm_near: !!confirmNear,
   };
 }
@@ -96,6 +105,7 @@ export async function loadVocabulary(worldId) {
     vocabState.domains = data.domains;
     vocabState.scopeKinds = data.scope_kinds;
     vocabState.levels = data.levels;
+    vocabState.states = data.states || [];
   } catch (e) {
     vocabState.loadError = e.message;
   }
diff --git a/src/world_engine/cockpit/routes/event_types.py b/src/world_engine/cockpit/routes/event_types.py
index fd874c1..57e53b5 100644
--- a/src/world_engine/cockpit/routes/event_types.py
+++ b/src/world_engine/cockpit/routes/event_types.py
@@ -5,7 +5,9 @@ sanctioned canon-write path:
     GET  /api/event-vocabulary            the active world's event types
                                           (the retired included), its sortes,
                                           and what a type may name: entity
-                                          types, domains, scope kinds, levels
+                                          types, domains, scope kinds, levels,
+                                          and the states its effects may
+                                          change (TICKET-0119)
     POST /api/event-types                 define one type
     PUT  /api/event-types/{id}            save one
     POST /api/event-types/{id}/status     retire or restore one
@@ -25,13 +27,13 @@ Every rule lives in `writes/event_types.py`; what is shown, in
 
 from __future__ import annotations
 
-from typing import Optional
+from typing import Optional, Union
 
 from fastapi import APIRouter, Depends, HTTPException
 from pydantic import BaseModel, Field
 from sqlmodel import Session, func, select
 
-from ...attributes import world_entity_type_labels
+from ...attributes import AttributeView, world_attributes, world_entity_type_labels
 from ...db import get_session
 from ...event_vocab import (
     DOMAIN_LABELS_FR,
@@ -45,6 +47,8 @@ from ...event_vocab import (
 )
 from ...models import EVENT_DOMAINS, EVENT_SCOPE_KINDS, ConditionNode, Event, EventSorte, EventType
 from ...writes.event_types import (
+    EFFECT_SYSTEM_KEYS,
+    EffectSpec,
     EventTypeSpec,
     RoleSpec,
     ScopeSpec,
@@ -81,6 +85,16 @@ class ScopeBody(BaseModel):
     level: str = "knows"
 
 
+class EffectBody(BaseModel):
+    """One effect (M-c, TICKET-0119): `role`, and for an entity state
+    `value`, are role NAMES; `value` is otherwise a choice key or an
+    integer."""
+    role: str
+    attribute: str
+    mode: str = "set"
+    value: Optional[Union[int, str]] = None
+
+
 class EventTypeBody(BaseModel):
     name: str
     domain: str = "other"
@@ -89,6 +103,7 @@ class EventTypeBody(BaseModel):
     in_chronicle: bool = True
     participants_secret: bool = False
     scopes: list[ScopeBody] = Field(default_factory=list)
+    effects: list[EffectBody] = Field(default_factory=list)
     confirm_near: bool = False
 
 
@@ -110,6 +125,7 @@ def event_type_spec(body: EventTypeBody) -> EventTypeSpec:
         counts_quantity=body.counts_quantity, in_chronicle=body.in_chronicle,
         participants_secret=body.participants_secret,
         scopes=tuple(ScopeSpec(s.kind, s.role, s.level) for s in body.scopes),
+        effects=tuple(EffectSpec(e.role, e.attribute, e.value, e.mode) for e in body.effects),
     )
 
 
@@ -129,10 +145,20 @@ def type_dict(db: Session, view: EventTypeView) -> dict:
         "roles": [{"id": r.id, "name": r.name, "entity_types": list(r.entity_types),
                    "accepts_sorte": r.accepts_sorte, "status": r.status} for r in view.roles],
         "scopes": [{"kind": s.kind, "role": names.get(s.role_id), "level": s.level} for s in view.scopes],
+        "effects": [{"role": names.get(e.role_id), "attribute": e.attribute, "mode": e.mode,
+                     "value": names.get(e.value) if e.value_kind == "role" else e.value} for e in view.effects],
         "in_condition": _in_condition(db, view.id), "events": events,
     }
 
 
+def state_dict(view: AttributeView) -> dict:
+    """One state an effect may change, as the type form offers it."""
+    return {"key": view.key, "name": view.name, "kind": view.kind, "system": view.system,
+            "holder_types": list(view.holder_types) if view.holder_types is not None else None,
+            "value_types": list(view.value_types),
+            "choices": [{"value": key, "label": label} for key, label in view.choices]}
+
+
 def sorte_dict(sorte: EventSorte) -> dict:
     return {"id": sorte.id, "name": sorte.name, "status": sorte.status}
 
@@ -151,6 +177,8 @@ def event_vocabulary(db: Session = Depends(get_session)) -> dict:
         "domains": [{"value": d, "label": DOMAIN_LABELS_FR[d]} for d in EVENT_DOMAINS],
         "scope_kinds": [{"value": k, "label": SCOPE_LABELS_FR[k]} for k in EVENT_SCOPE_KINDS],
         "levels": [{"value": v, "label": label} for v, label in LEVEL_LABELS_FR.items()],
+        "states": [state_dict(v) for v in world_attributes(db, world_id)
+                   if not v.system or v.key in EFFECT_SYSTEM_KEYS],
     }
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index cad8eed..88db058 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19513,6 +19513,23 @@ event never makes a `correction`.
 `event_participant`, `attribute_value` and `attribute_change`, so an event
 Lore declares (BRIEF-0119-G) is recorded with every row it wrote.
 
+## « VOCABULAIRE DU MONDE » EDITS WHAT A TYPE DOES TO THE STATE OF THE WORLD (TICKET-0119) -- A TYPE'S EFFECTS IN ITS FORM (BRIEF-0119-b, no schema change)
+
+**The form.** `EventTypeForm` lists a type's effects, each « role -> state
+= value »: the role is one of the type's that holds an entity; the state
+one that applies to an entity the role accepts; the value a choice of the
+state, an integer that the effect sets or adds to (D3), or another role
+whose entity the state may name. The same form serves the tab and the
+proposal cards of TICKET-0114, so a type proposed there may carry effects
+too.
+
+**The routes.** `GET /api/event-vocabulary` lists `states`: the two system
+states an effect may change (E1) and the world's active definitions, each
+with its kind, holder and value types and choices. A type's dict carries
+its `effects`, a role's NAME for an entity state; `EventTypeBody.effects`
+is read into the writer's `EffectSpec`. Every rule stays in
+`writes/event_types.py`; a refused effect is a 422.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_effects.py b/tooling/verify/checks/event_effects.py
index e349307..f8110e3 100644
--- a/tooling/verify/checks/event_effects.py
+++ b/tooling/verify/checks/event_effects.py
@@ -1,6 +1,7 @@
 """G1 check for TICKET-0119 -- what an event type does to the state of the world: its effects, written and read.
 
-BRIEF-0119-A's rules (M-c, C1, D3 and E1 of the conditions series). An effect
+BRIEF-0119-A's rules (M-c, C1, D3 and E1 of the conditions series), and
+BRIEF-0119-B's (the « Vocabulaire du monde » tab edits them). An effect
 only pre-fills an event's proposal; what an approved event writes is
 `event_changes.py`'s.
 
@@ -36,6 +37,18 @@ EF5 -- migration `scripts/migrate_v2_26_event_effects.py`, on a v2.25
    and changes nothing; at v2.25 it creates the table, adds the column and
    index, rebuilds `lore_entry_row` (its CHECK naming `event`), keeps both
    rows, and sets `schema_meta` to v2.26; a second run writes nothing.
+EF6 -- the routes (BRIEF-0119-B, route functions, a world made active).
+   `event_vocabulary` lists `states`: the system states an effect may name
+   and the world's active definitions, each with its kind, holder and value
+   types and choices; a type's dict carries its `effects` (role name, state,
+   mode, value -- a role's NAME for an entity state). A type saved with an
+   effect through `create_event_type` writes it; a refused effect answers
+   422 and writes nothing.
+EF7 -- the form (BRIEF-0119-B, static). `EventTypeForm.svelte` renders the
+   effects (`draft.effects`), offers `add` beside `set`, and names a role for
+   an entity state; `eventVocab.svelte.js`'s `typeDraft` and `typeBody`
+   carry `effects`, and `loadVocabulary` keeps `states`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -50,6 +63,7 @@ import tempfile
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
+FRONT = ROOT / "frontend" / "src" / "creation"
 MIGRATION = ROOT / "scripts" / "migrate_v2_26_event_effects.py"
 
 FAILURES: list[str] = []
@@ -427,6 +441,69 @@ def check_ef5() -> None:
         fail(f"EF5: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
 
 
+# --- EF6, EF7 (BRIEF-0119-B) --------------------------------------------------------
+
+def check_ef6(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.routes import event_types as routes
+    from world_engine.models import EventTypeEffect, World
+
+    with Session(engine) as db:
+        db.get(World, ids["world"]).is_active = True
+        db.commit()
+        listed = routes.event_vocabulary(db)
+        states = {s["key"]: s for s in listed.get("states", [])}
+        if "sys:vital_status" not in states or "sys:status" not in states or "sys:magic_status" in states \
+                or ids["occupe"] not in states:
+            fail(f"EF6: event_vocabulary lists the states {sorted(states)}")
+        elif states[ids["occupe"]].get("value_types") != ["character"] or not states["sys:status"].get("choices"):
+            fail(f"EF6: a state's shape is {states[ids['occupe']]}")
+        usurper = next((t for t in listed["types"] if t["name"] == "Usurper"), None)
+        if usurper is None or usurper.get("effects") != [
+                {"role": "Trône", "attribute": ids["occupe"], "mode": "set", "value": "Usurpateur"}]:
+            fail(f"EF6: « Usurper »'s effects are {usurper and usurper.get('effects')}")
+        body = routes.EventTypeBody(
+            name="Briser", domain="other", roles=[{"name": "Briseur", "entity_types": ["character"]},
+                                                  {"name": "Chose", "entity_types": ["location"]}],
+            effects=[{"role": "Chose", "attribute": "sys:status", "mode": "set", "value": "destroyed"}],
+            confirm_near=True)
+        saved = routes.create_event_type(body, db)
+        count = db.exec(select(func.count()).select_from(EventTypeEffect)).one()
+        if not saved.get("saved") or saved["type"].get("effects") != [
+                {"role": "Chose", "attribute": "sys:status", "mode": "set", "value": "destroyed"}]:
+            fail(f"EF6: create_event_type answered {saved}")
+        bad = routes.EventTypeBody(
+            name="Briser mal", domain="other", roles=[{"name": "Chose", "entity_types": ["location"]}],
+            effects=[{"role": "Chose", "attribute": "sys:magic_status", "mode": "set", "value": "active"}],
+            confirm_near=True)
+        try:
+            routes.create_event_type(bad, db)
+            fail("EF6: an effect on Magie was not refused")
+        except HTTPException as exc:
+            if exc.status_code != 422:
+                fail(f"EF6: a refused effect answered {exc.status_code}")
+        if db.exec(select(func.count()).select_from(EventTypeEffect)).one() != count:
+            fail("EF6: the refused effect wrote a row")
+
+
+def check_ef7() -> None:
+    wanted = {
+        "EventTypeForm.svelte": ("draft.effects", "'add'", "value_role"),
+        "eventVocab.svelte.js": ("effects:", "vocabState.states = data.states"),
+    }
+    for name, needles in wanted.items():
+        path = FRONT / name
+        if not path.exists():
+            fail(f"EF7: {name} is missing")
+            continue
+        text = path.read_text(encoding="utf-8")
+        for needle in needles:
+            if needle not in text:
+                fail(f"EF7: {name} lacks {needle}")
+
+
 def main() -> int:
     _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -441,6 +518,7 @@ def main() -> int:
     rules = (
         ("EF1", check_ef1), ("EF2", ef2), ("EF3", lambda: check_ef3(engine, ids, state["made"])),
         ("EF4", lambda: check_ef4(engine, ids)), ("EF5", check_ef5),
+        ("EF6", lambda: check_ef6(engine, ids)), ("EF7", check_ef7),
     )
     for name, rule in rules:
         try:
@@ -453,7 +531,7 @@ def main() -> int:
         return 1
     print("PASS: event_effects -- v2.26 keeps what an event type does to the state of the world: the role whose "
           "entity changes, the state, and a value of its kind; a state an effect names is never taken away, and "
-          "a change keeps the event that made it")
+          "a change keeps the event that made it; Création edits a type's effects")
     return 0
 
 
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- Writing an event's changes, pre-filling them -- BRIEF-0119-C.
- The event editor and the review card -- BRIEF-0119-D.
- Every later brief of this lot: BRIEF-0119-C, D, E, F, G.

## Invariants to defend

None of CLAUDE.md's invariants is newly threatened: the routes parse and map refusals, every rule stays in `writes/event_types.py` (A). INV-49/INV-50: no new Création tab or island -- `EventTypeForm` is already rendered by the « Vocabulaire du monde » island.

## Decision rights

STOP:
- A route would decide an effect's validity itself instead of `clean_event_type`.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/event_effects.py` -> `PASS`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/creation_island.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (157 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EF6** -- `cockpit/routes/event_types.py event_vocabulary`: `                   if not v.system or v.key in EFFECT_SYSTEM_KEYS],` -> `                   ],`
  - **EF7** -- `frontend/src/creation/eventVocab.svelte.js loadVocabulary`: `    vocabState.states = data.states || [];` -> ``
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated; the static build rebuilt.
