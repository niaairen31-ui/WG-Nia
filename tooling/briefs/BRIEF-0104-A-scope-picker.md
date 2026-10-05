<!-- slug: scope-picker -->
# BRIEF 0104-A — "A Lore scope picks its entity from the whole world"

Lot: LOT-0104-lore-scope-picker.md (authoritative on conflict)
Depends on: nothing in this lot
Commit header for decisions: `(BRIEF-0104-a, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on a branch `ticket/0104` cut from `main`, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `frontend/src/lore/writePanel.svelte.js:31` → `const SCOPE_ENTITY_TYPE = Object.freeze({ faction: 'faction', location: 'location' });`
- `frontend/src/lore/writePanel.svelte.js:130-132` → `export function scopeRefs(scopeType) {` / `  return liveRefs(SCOPE_ENTITY_TYPE[scopeType]);` / `}`.
- `frontend/src/lore/writePanel.svelte.js:134-149` → `export function addKnower(fact, entityId) {`; when the draft holds no `existing` entity with the picked id it pushes one with `status: 'matched', decision: 'existing', action: 'existing', entity_id: picked.id` and a ref built as `k` + `(draft.entities.length + 1)`.
- `frontend/src/lore/WritePanel.svelte:144` → `              <select bind:value={scope.scope_type}>`; `:148` → `                <select bind:value={scope.scope_ref}>`; `:150` lists `scopeRefs(scope.scope_type)`.
- `src/world_engine/lore_write_apply.py:42-44` → `_SCOPE_ENTITY_TYPE` maps `"rencontre": None`; `:104-118` `_validate_scopes` checks every non-`world` scope ref with `_entity_ref(..., _SCOPE_ENTITY_TYPE[scope_type])`.
- `src/world_engine/writes/facets.py:68-69` → `if preset == "rencontre":` / `return ScopeChoice("rencontre", entity.id)`.
- `tooling/verify/checks/lore_write.py` `check_f1` (≈ `:624-640`) → F1b's path set and F1c's `entity_id` rule as quoted in R-07; `main` calls `check_f1()` and no `check_f2`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with the entry `THE LORE USAGE JOURNAL HAS ONE READER (TICKET-0103) -- A JSONL EXPORT (BRIEF-0103-e, no schema change)`, then `---` and `*Co-built with Claude, June 2026.*`.

## Facts carried

### R-01 — the scope list offers only the draft's entities [M]
Opened: `frontend/src/lore/writePanel.svelte.js:31` (`SCOPE_ENTITY_TYPE =
Object.freeze({ faction: 'faction', location: 'location' })`), `:125-128`
(`liveRefs`), `:130-132` (`scopeRefs`); `frontend/src/lore/
WritePanel.svelte:141-156` (the « Qui le sait par défaut » rows).
Finding: the entity select of a non-`world` scope lists
`scopeRefs(scope.scope_type)` = `liveRefs(SCOPE_ENTITY_TYPE[type])`: the
draft's entities whose decision is set and not `text`, of the scope's
type. A text that names no place offers no place. `rencontre` has no key,
so `liveRefs(undefined)` lists every live draft entity, of any type. The
scope type is bound with `bind:value`: switching it keeps a `scope_ref` of
the wrong type, which the server then refuses (R-04).
Consequence: the list must add the world's entities; a type switch must
clear a ref the new type refuses.

### R-02 — the knower picker already adds a world entity to the draft [M]
Opened: `frontend/src/lore/writePanel.svelte.js:134-149` (`addKnower`),
`:106-108` (`worldEntity`), `:66-70` (`loadWorldEntities`), `:86-87`
(`draftNow` awaits `loadWorldEntities()` before the draft request);
`WritePanel.svelte:169-174` (the knower select lists
`writeState.entities` filtered to `character`).
Finding: `addKnower` finds the draft entity `existing` with that
`entity_id`, or pushes one (`ref: k${draft.entities.length + 1}`, `status:
'matched'`, `decision`/`action: 'existing'`, `entity_id`, `name`, `type`
from the world entity). `writeState.entities` is loaded before any draft
is shown.
Consequence: the scope picker reuses that code, extracted as
`existingRef(entityId)`; `addKnower` calls it unchanged in behaviour.

### R-04 — the server already validates every scope ref and type [M]
Opened: `src/world_engine/lore_write_apply.py:39-44` (`SCOPE_TYPES`,
`_SCOPE_ENTITY_TYPE` with `"rencontre": None`), `:72-94`
(`_validate_entities`: an `existing` item needs an active entity of the
proposal's world), `:96-101` (`_entity_ref`: the ref is in the proposal,
and of type `want` when `want` is not None), `:104-118`
(`_validate_scopes`); `src/world_engine/lore_write_draft.py:186-197`
(`_scopes`: a model-proposed scope is kept only if its ref is a draft
entity).
Finding: an `existing` entity added by the panel is validated like any
other; a `location`/`faction` scope must point at a ref of that type; a
`rencontre` scope at any ref. The model can propose scopes only on named
entities.
Consequence: no server change; the model side is out of scope.

### R-05 — `rencontre` is not limited to characters [M]
Opened: `src/world_engine/writes/facets.py:60-70` (`_preset_scope`:
`preset == "rencontre"` → `ScopeChoice("rencontre", entity.id)` whatever
`entity.type`), `src/world_engine/writes/relations.py:222-230`
(`_on_relation_born`: a social relation records an encounter between
`entity_a_id` and `entity_b_id`, types unchecked),
`src/world_engine/encounters.py:118-125` (`acquaintances`: every entity
paired in `rencontre`).
Finding: the creator-side preset already writes `rencontre` scopes on
places, factions and objects (the appellation preset is `rencontre` since
TICKET-0092, N14b), and the registry can pair a character with a
non-character.
Consequence: A1'a — the panel offers every type for `rencontre`;
`SCOPE_ENTITY_TYPE` keeps exactly its two keys.

### R-07 — the checks that read the panel [M]
Opened: `tooling/verify/checks/lore_write.py:624-640` (`check_f1`: F1b the
exact set of `'/api/...'` paths in `writePanel.svelte.js`; F1c
`WritePanel.svelte` has no `entity_id` once `entity.entity_id`,
`c.entity_id` and `entity_id)` are removed), `:665-691` (`main`, the PASS
line); `tooling/verify/checks/lore_usage.py` `check_u11` (static: the
attempt id in `blank()` and the three POSTs; the built bundle carries
`attempt_id`); `tooling/verify/checks/frontend_build_fresh.py:14-17`
(manifest hash of the current `frontend/` sources);
`tooling/verify/checks/effect_self_write.py` (no `$effect` is touched).
Finding: the new markup must name no `entity_id`; the new code may call no
new path; the bundle must be rebuilt.
Consequence: the option values are built in `writePanel.svelte.js`
(`ref:<ref>` / `id:<uuid>`), never in the markup; F2 joins `lore_write.py`
beside F1, the same check that governs the panel.

### R-08 — what the commit sends [M]
Opened: `frontend/src/lore/writePanel.svelte.js:159-175` (`blockers`: a
non-`world` scope without `scope_ref` blocks the commit), `:178-207`
(`toProposal`: an `existing` entity is sent as `{ref, action: 'existing',
entity_id}`; a non-`world` scope is sent as `{...d}` unless its ref is a
dropped « en texte » entity).
Finding: a scope whose `scope_ref` is `undefined` is shown as a blocker
and never sent; a ref added by `existingRef` is sent as an `existing`
entity.
Consequence: clearing `scope_ref` to `undefined` on a type switch is safe.

## Contracts

None cross a brief (one-brief lot). The helper names below are part of the diff and are read by F2 verbatim: `existingRef`, `scopeOptions`, `scopeValue`, `pickScope`, `setScopeType`, `SCOPE_ENTITY_TYPE`.

## Context

In the Lore writing panel, « Qui le sait par défaut » → « Ceux qui sont dans le lieu » lists only the places the text named; a text that names no place offers nothing to pick, and the faction scope has the same defect. Nia locked A1 (pick from the whole world, by type) and A1'a (`rencontre` takes any type, panel only). The server already validates what the panel will send; this brief is frontend only, plus its check and its decision entry. What a `location` default *means* (presence today) is TICKET-0105.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - in `writePanel.svelte.js`, replaces `scopeRefs` with `existingRef` (private: the body `addKnower` had, returning the draft ref), `scopeOptions(scopeType)` (draft live refs of the scope's type as `ref:<ref>`, then every active world entity of that type not already held as `existing`, as `id:<uuid>`, sorted by name with French collation; `rencontre` = any type), `scopeValue(scope)`, `pickScope(scope, value)` and `setScopeType(scope, scopeType)` (clears `scope_ref` for `world`, for a missing ref, or for a ref whose type the new scope refuses); `addKnower` now calls `existingRef`; `SCOPE_ENTITY_TYPE` is unchanged;
   - in `WritePanel.svelte`, the scope-type select calls `setScopeType` on change and the entity select is built from `scopeOptions`, valued by `scopeValue`, and calls `pickScope` on change (no `bind:value` on either);
   - adds rule F2 to `tooling/verify/checks/lore_write.py` (docstring, `check_f2`, its call in `main`, the PASS line);
   - appends the decision entry `A LORE SCOPE PICKS FROM THE WHOLE WORLD (TICKET-0104) -- RENCONTRE TAKES ANY TYPE (BRIEF-0104-a, no schema change)`.
2. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build` (writes `src/world_engine/cockpit/static/`); commit the rebuilt output.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `fix(lore): default scopes pick their entity from the whole world (BRIEF-0104-a)`.

````diff
diff --git a/frontend/src/lore/WritePanel.svelte b/frontend/src/lore/WritePanel.svelte
index 7ecfbab..aeaaa1b 100644
--- a/frontend/src/lore/WritePanel.svelte
+++ b/frontend/src/lore/WritePanel.svelte
@@ -7,7 +7,8 @@
   import { serverState } from '../lib/serverState.svelte.js';
   import {
     writeState, ENTITY_TYPES, SCOPE_TYPES, LEVELS, reloadForWorld, askQuestions, makeDraft,
-    pickExisting, refLabel, liveRefs, scopeRefs, addKnower, addDefault, removeAt, blockers,
+    pickExisting, refLabel, liveRefs, scopeOptions, scopeValue, pickScope, setScopeType,
+    addKnower, addDefault, removeAt, blockers,
     commit, restart, loadEntries, worldEntity,
   } from './writePanel.svelte.js';
 
@@ -141,13 +142,13 @@
           <div>Qui le sait par défaut :</div>
           {#each fact.defaults as scope, si (si)}
             <div class="row">
-              <select bind:value={scope.scope_type}>
+              <select value={scope.scope_type} onchange={(e) => setScopeType(scope, e.currentTarget.value)}>
                 {#each SCOPE_TYPES as s (s.value)}<option value={s.value}>{s.label}</option>{/each}
               </select>
               {#if scope.scope_type !== 'world'}
-                <select bind:value={scope.scope_ref}>
-                  <option value={undefined}>— choisir —</option>
-                  {#each scopeRefs(scope.scope_type) as e (e.ref)}<option value={e.ref}>{refLabel(e.ref)}</option>{/each}
+                <select value={scopeValue(scope)} onchange={(e) => pickScope(scope, e.currentTarget.value)}>
+                  <option value="">— choisir —</option>
+                  {#each scopeOptions(scope.scope_type) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
                 </select>
               {/if}
               <button onclick={() => removeAt(fact.defaults, si)}>×</button>
diff --git a/frontend/src/lore/writePanel.svelte.js b/frontend/src/lore/writePanel.svelte.js
index a76d57b..888db1c 100644
--- a/frontend/src/lore/writePanel.svelte.js
+++ b/frontend/src/lore/writePanel.svelte.js
@@ -127,13 +127,16 @@ export function liveRefs(type) {
     && e.decision !== 'text' && (!type || e.type === type));
 }
 
-export function scopeRefs(scopeType) {
-  return liveRefs(SCOPE_ENTITY_TYPE[scopeType]);
-}
-
-export function addKnower(fact, entityId) {
+/* TICKET-0104 (BRIEF-0104-A, A1, A1'a). A scope picks its entity from the
+   whole world, not only from the entities the text named: the entities of
+   the draft first (a new one included), then every active entity of the
+   world of the scope's type that the draft does not hold yet. `rencontre`
+   has no entry in SCOPE_ENTITY_TYPE: any type, like the preset
+   (writes/facets.py). A world entity picked here joins the draft as
+   'existing', by the same path as a knower (`existingRef`). */
+function existingRef(entityId) {
   const picked = worldEntity(entityId);
-  if (!picked) return;
+  if (!picked) return undefined;
   const draft = writeState.draft;
   let entity = draft.entities.find((e) => e.decision === 'existing' && e.entity_id === picked.id);
   if (!entity) {
@@ -143,8 +146,44 @@ export function addKnower(fact, entityId) {
     };
     draft.entities.push(entity);
   }
-  if (!fact.knowers.some((k) => k.entity_ref === entity.ref)) {
-    fact.knowers.push({ entity_ref: entity.ref, level: 'knows', is_secret: false, is_incorrect: false });
+  return entity.ref;
+}
+
+export function scopeOptions(scopeType) {
+  const want = SCOPE_ENTITY_TYPE[scopeType];
+  const inDraft = liveRefs(want);
+  const held = new Set(inDraft.filter((e) => e.decision === 'existing').map((e) => e.entity_id));
+  const world = (writeState.entities || [])
+    .filter((e) => (!want || e.type === want) && !held.has(e.id))
+    .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
+  return [
+    ...inDraft.map((e) => ({ value: `ref:${e.ref}`, label: refLabel(e.ref) })),
+    ...world.map((e) => ({ value: `id:${e.id}`, label: e.name })),
+  ];
+}
+
+export function scopeValue(scope) {
+  return scope.scope_ref ? `ref:${scope.scope_ref}` : '';
+}
+
+export function pickScope(scope, value) {
+  if (value.startsWith('ref:')) scope.scope_ref = value.slice(4);
+  else if (value.startsWith('id:')) scope.scope_ref = existingRef(value.slice(3));
+  else scope.scope_ref = undefined;
+}
+
+export function setScopeType(scope, scopeType) {
+  scope.scope_type = scopeType;
+  const want = SCOPE_ENTITY_TYPE[scopeType];
+  const entity = (writeState.draft?.entities || []).find((e) => e.ref === scope.scope_ref);
+  if (scopeType === 'world' || !entity || (want && entity.type !== want)) scope.scope_ref = undefined;
+}
+
+export function addKnower(fact, entityId) {
+  const ref = existingRef(entityId);
+  if (!ref) return;
+  if (!fact.knowers.some((k) => k.entity_ref === ref)) {
+    fact.knowers.push({ entity_ref: ref, level: 'knows', is_secret: false, is_incorrect: false });
   }
 }
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index e22049a..d93c90b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17696,6 +17696,32 @@ the export, in a Claude Code session, never in the application.
 analysis has shown which measures deserve a screen; its first UI consumer
 relationalizes the JSON columns (D2).
 
+
+## A LORE SCOPE PICKS FROM THE WHOLE WORLD (TICKET-0104) -- RENCONTRE TAKES ANY TYPE (BRIEF-0104-a, no schema change)
+
+**A1.** In the Lore writing panel, « Qui le sait par défaut » picks the
+entity of a `location` or `faction` scope among the draft's entities first
+(a new one included), then among every active entity of the world of that
+type. Before, it offered only the entities the text named: a text naming no
+place left « Ceux qui sont dans le lieu » with nothing to choose. A world
+entity picked for a scope joins the draft as `existing`, by the same helper
+(`existingRef`) a knower uses, so the server's validation is unchanged:
+`lore_write_apply._validate_scopes` already checks every scope's ref and its
+type.
+
+**A1'a.** A `rencontre` scope takes an entity of any type. The preset
+(`writes/facets.py::_preset_scope`) already gives an appellation of a place,
+a faction or an object a `rencontre` scope on its own entity, and a social
+relation records an encounter whatever the types of its two ends
+(`writes/relations.py::_on_relation_born`). Changing the scope type clears a
+picked entity whose type the new scope refuses.
+
+**Rejected.** A1'b, `rencontre` limited to characters in the panel and on
+the server: the `rencontre` scope of a non-character appellation could no
+longer be written from the Lore tool. Reactivates if a production
+measurement shows no `rencontre` pair involving anything but two
+characters.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index f929b8f..3b3b960 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -80,6 +80,17 @@ F1 -- panel (BRIEF-0098-F), static:
    c. `WritePanel.svelte` lists the facets it offers from `draft.facets`
       (served from `FACETS`), never from a literal list, and offers no free
       text field for an entity id.
+F2 -- scope picker (TICKET-0104, BRIEF-0104-A, A1 / A1'a), static, in
+   `frontend/src/lore/writePanel.svelte.js` and `WritePanel.svelte`:
+   a. `scopeOptions` reads `writeState.entities` (the world's entities) and
+      `liveRefs(` (the draft's): a scope is never limited to what the text
+      named;
+   b. the key set of `SCOPE_ENTITY_TYPE` is exactly {faction, location} --
+      `rencontre` takes any type, like the preset in `writes/facets.py`;
+   c. `addKnower` and `pickScope` both call `existingRef(`: one path adds a
+      world entity to the draft;
+   d. `WritePanel.svelte` calls `scopeOptions(`, `pickScope(` and
+      `setScopeType(`, and no longer names `scopeRefs`.
 C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
    `chat(`, no `.commit(`, and import neither `ollama_client` nor any
    `cockpit` module; `lore_write_draft.py` contains no `db.add(`, no
@@ -640,6 +651,26 @@ def check_f1() -> None:
         fail("F1c: WritePanel.svelte exposes an entity id outside a picker")
 
 
+def check_f2() -> None:
+    lore = ROOT / "frontend" / "src" / "lore"
+    state = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
+    start = state.find("export function scopeOptions(")
+    body = state[start:state.find("\n}\n", start)] if start >= 0 else ""
+    if "writeState.entities" not in body or "liveRefs(" not in body:
+        fail("F2a: scopeOptions does not offer both the world's and the draft's entities")
+    keys = re.search(r"SCOPE_ENTITY_TYPE = Object\.freeze\(\{([^}]*)\}\)", state)
+    if keys is None or set(re.findall(r"(\w+):", keys.group(1))) != {"faction", "location"}:
+        fail("F2b: SCOPE_ENTITY_TYPE keys are not exactly {faction, location}")
+    for name in ("export function addKnower(", "export function pickScope("):
+        at = state.find(name)
+        if at < 0 or "existingRef(" not in state[at:state.find("\n}\n", at)]:
+            fail(f"F2c: {name.split()[-1]} does not go through existingRef(")
+    panel = (lore / "WritePanel.svelte").read_text(encoding="utf-8")
+    if not all(f"{n}(" in panel for n in ("scopeOptions", "pickScope", "setScopeType")) \
+            or "scopeRefs" in panel:
+        fail("F2d: WritePanel.svelte does not use the world-wide scope picker")
+
+
 def check_d2() -> None:
     import re as _re
 
@@ -678,6 +709,7 @@ def main() -> int:
     check_e1()
     check_e2()
     check_f1()
+    check_f2()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -687,7 +719,7 @@ def main() -> int:
           "writes all or nothing, each row recorded, existing rows skipped; the draft "
           "names things by name and code only and resolves both in code; the routes are "
           "thin, guarded, and write canon only on commit; the panel lives in the Lore shell's "
-          "'Écrire' tab")
+          "'Écrire' tab, and its scopes pick from the whole world")
     return 0
 
 
````

## Scope OUT

- Any server change: `lore_write_apply.py`, `lore_write_draft.py`, the routes. The server already validates the refs and types the panel sends (R-04).
- Limiting `rencontre` to characters, in the panel or on the server (A1'b, rejected).
- What the model may propose as a scope (`lore_write_draft._scopes` keeps named entities only).
- Marking zones in the list, or any new field on `/api/entities`.
- Searching or filtering inside the select; grouping options by type.
- The fiche's own fact-default editor (`cockpit/crud/knowledge.py`) and any other panel.
- Learning on visit, keeping knowledge, fact versions: TICKET-0105.

## Invariants to defend

**A lore statement commits whole or not at all, through `lore_write_apply.apply_proposal`;** entities are confirmed by the creator: a world entity reaches the proposal only because she picked it from a list, as an `existing` item the server re-validates (R-04). **Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the same body:** no `$effect` is touched (`effect_self_write.py`). The built `static/` must match the sources (`frontend_build_fresh.py`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `lore_write.py` F1 fails (a request path was added, or `entity_id` appears in `WritePanel.svelte` markup).
- `npm run build` fails.
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- The built bundle's file name differs from the prototype's: expected (content hash); commit whatever `npm run build` wrote.

REPORT-ONLY:
- Timing of the corpus run.
- `npm` audit, deprecation or engine notices.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt files under `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/lore_write.py` → `PASS: lore_write -- … the panel lives in the Lore shell's 'Écrire' tab, and its scopes pick from the whole world`.
- `lore_usage.py`, `frontend_build_fresh.py`, `decisions_index.py`, `effect_self_write.py` → `PASS`.
- Mutation tests, each red then reverted: in `writePanel.svelte.js`, (1) make `scopeOptions` read `([])` instead of `(writeState.entities || [])` → `F2a`; (2) add `rencontre: 'character'` to `SCOPE_ENTITY_TYPE` → `F2b`; (3) in `addKnower`, replace `existingRef(entityId)` with `worldEntity(entityId)?.id` → `F2c`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A LORE SCOPE PICKS FROM THE WHOLE WORLD (TICKET-0104) -- RENCONTRE TAKES ANY TYPE (BRIEF-0104-a, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
