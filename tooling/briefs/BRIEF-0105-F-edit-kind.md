<!-- slug: edit-kind -->
# BRIEF 0105-F — "The creator says whether a rewrite corrects or changes the world"

Lot: LOT-0105-fact-learning.md (authoritative on conflict)
Depends on: BRIEF-0105-E
Commit header for decisions: `(BRIEF-0105-f, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0105`, on the tree the previous brief left (for A: cut from `main`), before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/facets.py:34` → `    aspects: tuple[str, ...] = ()   # known aspects, suggestion only`, the last field of `FacetSpec`; `:42` → `FacetSpec("physique", …`; `:44` → `FacetSpec("tenue", "identite", "bloc", "rencontre", "Tenue",` (A).
- `src/world_engine/cockpit/crud/facets.py:42-43` → `class FactContentBody(BaseModel):` / `    content: str`; `:70` → `def list_facets() -> dict:`; `update_entity_fact_content` passes `kind="correction"` (C).
- `src/world_engine/lore_write_apply.py:165` → `        if action == "rewrite":`; the rewrite in `_Writer` passes `kind="correction"` (C).
- `src/world_engine/lore_write_draft.py:251` → `def draft_proposal(`; `:272` → `        fact["ref"] = f"f{index}"`.
- `frontend/src/creation/FactsEditor.svelte:99` → `  function saveBloc(spec) {`; `:109` → `  function saveLine(fact) {`; both PUT `{ content: buffers[…] }`.
- `frontend/src/lore/WritePanel.svelte:129` → `          {#if fact.action !== 'existing'}`; `frontend/src/lore/writePanel.svelte.js:236` → `    if (f.action !== 'existing') out.content = f.content;`.
- `tooling/verify/checks/lore_write.py:320` → `    ("rewrite of a non-bloc fact", lambda p: p["facts"].append(`; the C1c rewrite proposal carries no `kind`.

## Facts carried

### R-10 — the facet registry [M]
Opened: `src/world_engine/facets.py:26-60` (`FacetSpec`; `tenue` presets
`none`, `physique` presets `rencontre`); `src/world_engine/writes/facets.py:
60-70` (`_preset_scope`: `rencontre` scopes the entity itself), `:143`,
`:339` (preset level `knows`); `tooling/verify/checks/fact_facets.py:69-90`
(`EXPECTED_FACETS`, five fields compared).
Finding: an outfit is known by nobody by default. `FacetSpec` is a frozen
dataclass with defaulted trailing fields.
Consequence: V1 changes `tenue`'s preset and its row in `EXPECTED_FACETS`;
F adds `edit_kind` as a defaulted field, outside the compared five.

### R-13 — the editors [M]
Opened: `frontend/src/creation/FactsEditor.svelte:85-115` (`write`,
`saveBloc`, `saveLine`); `src/world_engine/cockpit/crud/facets.py:42-44`
(`FactContentBody`), `:69-79` (`list_facets`), `:115-127`;
`frontend/src/lore/WritePanel.svelte:126-135`;
`frontend/src/lore/writePanel.svelte.js:178-207` (`toProposal`);
`src/world_engine/lore_write_apply.py:160-170, 280-286`;
`src/world_engine/lore_write_draft.py:210-240, 251-280`.
Finding: two surfaces rewrite a fact: the fiche (`PUT
/api/facts/{id}/content`, body `{content}`) and the Lore panel (`rewrite`
of a bloc fact, no facet in the draft item).
Consequence: F adds `kind` to both, preselected from the facet of the
rewritten fact (the draft looks it up).

### R-17 — the checks the lot passes [M]
Opened: `tooling/verify/checks/encounter_registry.py:1-60` (R1-R4);
`knowledge_resolution.py:74-166, 247-352` (tier 2b nearest; C-09 case 4:
the encounter is recorded before the defaults); `lore_write.py:300-400`
(C1c, `_REFUSALS`, the `__f3__` substitution); `world_cascade.py:1-40,
67-120` (W1 coverage, W3 fixture); `fact_facets.py:116-145`;
`function_length.py` (80 lines); `npc_schedule.py`;
`single_canon_write.py`; `claude_md_contract.py` (38 000 characters, 100
per line); `frontend_build_fresh.py`; `effect_self_write.py`.
Finding: C-09 case 4 and tier 2b encode the rules B5 and C1 replace;
`passage` is world-scoped and must be cascaded.
Consequence: D amends the two fixtures (named in its Scope IN); A adds
`passage` to the cascade and its fixture.

## Contracts

### C-04 — the kind of a rewrite
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, F, G
`writes.facts.FACT_CHANGE_KINDS = ("correction", "changement")`.
`update_fact_content(db, *, fact, content, changed_by, kind)`,
`update_typed_fact_content(db, *, fact, content, changed_by, kind)`,
`writes.facets.edit_entity_fact(db, *, fact_id, content, changed_by,
kind)`: `kind` required, keyword-only; `ValueError` outside the vocabulary,
before any write. History entry `{"content": <text before>, "changed_by",
"at": <aware ISO>, "kind"}`. An entry without `kind` reads as a
correction.

### C-08 — the kind chosen by the creator
Produced by: BRIEF-0105-F   Consumed by: the creator
`FacetSpec.edit_kind: str = "correction"`; `physique` and `tenue`:
`"changement"`. `GET /api/facets` serves `edit_kind`. `FactContentBody.kind:
Literal["correction", "changement"]`, required. A Lore draft's `rewrite`
item carries `kind` (preset from its fact's facet,
`lore_write_draft._preset_kind`); the proposal's `rewrite` item must carry
one of the two kinds or `ProposalError`.

## Context

Rewrites name their kind (C), and the creator surfaces pass `correction` meanwhile. Nia locked H1: she picks it at every rewrite, preselected by facet — `changement` for what one sees of an entity and can change (physique, outfit), `correction` otherwise. This brief puts the choice in the fiche's facts editor and in the Lore panel's rewrite, and makes both server paths require it.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`, `tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `facets.py`: `FacetSpec.edit_kind: str = "correction"`; `physique` and `tenue` `edit_kind="changement"`; docstring;
   - `cockpit/crud/facets.py`: `FactContentBody.kind: Literal["correction", "changement"]` (required); the route passes `body.kind`; `list_facets` serves `edit_kind`;
   - `lore_write_draft.py`: `_preset_kind(db, fact_id)`; `draft_proposal` puts `kind` on every `rewrite` item;
   - `lore_write_apply.py`: a `rewrite` without a kind in `FACT_CHANGE_KINDS` raises `ProposalError` (« dis si la réécriture est une correction ou un changement dans le monde. »); the writer passes `item["kind"]`;
   - `FactsEditor.svelte`: a `kindPicker` snippet beside each save of an existing fact, preselected by `kindOf(fact)` (the registry's `edit_kind`), sent as `kind` with both PUTs; `WritePanel.svelte`: two radios on a rewrite; `writePanel.svelte.js`: `toProposal` puts `kind` on a rewrite; header comments;
   - `lore_write.py`: C1c's rewrite carries `kind: "changement"` and asserts it in the history; `_REFUSALS` gains « rewrite without kind » and « rewrite of an unknown kind » on the `__bloc__` placeholder, substituted like `__f3__`; the non-bloc refusal carries a kind so it still refuses for its own reason;
   - adds F1-F3 to `fact_learning.py`; appends the decision entry.
2. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build` (writes `src/world_engine/cockpit/static/`); commit the rebuilt output.
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(lore): the creator picks correction or change at every rewrite (BRIEF-0105-f)`.

````diff
diff --git a/frontend/src/creation/FactsEditor.svelte b/frontend/src/creation/FactsEditor.svelte
index af6064d..1638b15 100644
--- a/frontend/src/creation/FactsEditor.svelte
+++ b/frontend/src/creation/FactsEditor.svelte
@@ -19,6 +19,12 @@
      factsDraftState, sent by Sheet.svelte's submitEntity as the create
      body's `facets`. No network write here in create mode.
 
+     TICKET-0105 (BRIEF-0105-F, H1): every rewrite of an existing fact says
+     whether it is a correction (everyone sees the new text) or a change in
+     the world (whoever knew the fact keeps the old text until they see it
+     again). The choice is preselected from the registry's `edit_kind` for
+     the fact's facet and sent as `kind` with PUT /api/facts/{id}/content.
+
      Errors show the route's detail. Creator-only: nothing here renders in
      Play. */
   import { api } from './sheetRequest.svelte.js';
@@ -30,6 +36,7 @@
   let facts = $state([]);
   let buffers = $state({});
   let adds = $state({});
+  let kinds = $state({});
   let error = $state('');
 
   const TYPE_FAMILIES = {
@@ -78,6 +85,12 @@
     return facts.filter((f) => f.facet === name);
   }
 
+  function kindOf(fact) {
+    return kinds[fact.fact_id]
+      ?? (registry || []).find((spec) => spec.name === fact.facet)?.edit_kind
+      ?? 'correction';
+  }
+
   function isHidden(fact) {
     return fact.scopes.length === 0;
   }
@@ -99,7 +112,8 @@
   function saveBloc(spec) {
     const existing = factsOf(spec.name)[0];
     if (existing) {
-      write(`/api/facts/${encodeURIComponent(existing.fact_id)}/content`, 'PUT', { content: buffers[existing.fact_id] });
+      write(`/api/facts/${encodeURIComponent(existing.fact_id)}/content`, 'PUT',
+        { content: buffers[existing.fact_id], kind: kindOf(existing) });
     } else {
       write(`/api/entities/${encodeURIComponent(entityId)}/facts`, 'POST',
         { facet: spec.name, content: adds[spec.name].content });
@@ -107,7 +121,8 @@
   }
 
   function saveLine(fact) {
-    write(`/api/facts/${encodeURIComponent(fact.fact_id)}/content`, 'PUT', { content: buffers[fact.fact_id] });
+    write(`/api/facts/${encodeURIComponent(fact.fact_id)}/content`, 'PUT',
+      { content: buffers[fact.fact_id], kind: kindOf(fact) });
   }
 
   function deleteLine(fact) {
@@ -151,6 +166,14 @@
   }
 </script>
 
+{#snippet kindPicker(fact)}
+  <select title="Nature de la modification" style="font-size:12px" value={kindOf(fact)}
+    onchange={(e) => { kinds[fact.fact_id] = e.currentTarget.value; }}>
+    <option value="correction">Correction</option>
+    <option value="changement">Changement dans le monde</option>
+  </select>
+{/snippet}
+
 {#if error}
   <div class="author-status err" style="margin-bottom:6px">{error}</div>
 {/if}
@@ -178,6 +201,7 @@
             <textarea rows="2" bind:value={adds[spec.name].content}></textarea>
           {/if}
           <div class="row-card-actions" style="margin-top:4px">
+            {#if existing}{@render kindPicker(existing)}{/if}
             <button class="btn-send" onclick={() => saveBloc(spec)}>💾 Enregistrer</button>
           </div>
         {/if}
@@ -206,6 +230,7 @@
               <span style="flex:1; font-size:12px; color:var(--muted)">{fact.aspect || '—'}{isHidden(fact) ? ' · caché' : ''}</span>
             {/if}
             <input type="text" style="flex:3" bind:value={buffers[fact.fact_id]}>
+            {@render kindPicker(fact)}
             <button class="btn-icon" title="Enregistrer" onclick={() => saveLine(fact)}>💾</button>
             <button class="btn-icon" title="Supprimer" onclick={() => deleteLine(fact)}>✕</button>
           </div>
diff --git a/frontend/src/lore/WritePanel.svelte b/frontend/src/lore/WritePanel.svelte
index aeaaa1b..4e65f6d 100644
--- a/frontend/src/lore/WritePanel.svelte
+++ b/frontend/src/lore/WritePanel.svelte
@@ -129,6 +129,14 @@
           {#if fact.action !== 'existing'}
             <textarea bind:value={fact.content} rows="2"></textarea>
           {/if}
+          {#if fact.action === 'rewrite'}
+            <div class="row">
+              <label><input type="radio" checked={fact.kind === 'correction'}
+                onchange={() => (fact.kind = 'correction')} /> Correction</label>
+              <label><input type="radio" checked={fact.kind === 'changement'}
+                onchange={() => (fact.kind = 'changement')} /> Changement dans le monde</label>
+            </div>
+          {/if}
           {#if fact.action === 'create'}
             <select bind:value={fact.facet}>
               {#each draft.facets as f (f.name)}<option value={f.name}>{f.label}</option>{/each}
diff --git a/frontend/src/lore/writePanel.svelte.js b/frontend/src/lore/writePanel.svelte.js
index 888db1c..47677c5 100644
--- a/frontend/src/lore/writePanel.svelte.js
+++ b/frontend/src/lore/writePanel.svelte.js
@@ -9,6 +9,10 @@
    drops the entity and declares the name as a mention, so the tokenizer
    records it in "Noms à lier".
 
+   TICKET-0105 (BRIEF-0105-F, H1): a rewritten fact carries the `kind` the
+   draft preselected from its facet -- a correction, or a change in the
+   world -- and the creator can switch it before committing.
+
    TICKET-0103 (BRIEF-0103-D): `attemptId` names one use of the panel, from
    the text to its commit, for the usage journal. A fresh one comes with
    every blank state (a new text, a world change); every request of the use
@@ -234,6 +238,7 @@ function toProposal() {
     };
     if (f.action !== 'create') out.fact_id = f.fact_id;
     if (f.action !== 'existing') out.content = f.content;
+    if (f.action === 'rewrite') out.kind = f.kind;
     if (f.action === 'create') Object.assign(out, { facet: f.facet, aspect: f.aspect, mentions });
     return out;
   });
diff --git a/src/world_engine/cockpit/crud/facets.py b/src/world_engine/cockpit/crud/facets.py
index ba19be9..ac10f6b 100644
--- a/src/world_engine/cockpit/crud/facets.py
+++ b/src/world_engine/cockpit/crud/facets.py
@@ -9,7 +9,7 @@ writer is a 422; an unknown entity or fact is a 404.
 
 from __future__ import annotations
 
-from typing import Optional
+from typing import Literal, Optional
 
 from fastapi import Depends, HTTPException
 from pydantic import BaseModel
@@ -41,6 +41,8 @@ class EntityFactCreateBody(BaseModel):
 
 class FactContentBody(BaseModel):
     content: str
+    # TICKET-0105 (H1): a correction, or a change in the world.
+    kind: Literal["correction", "changement"]
 
 
 def _fact_dict(fact: Fact, db: DbSession) -> dict:
@@ -73,7 +75,7 @@ def list_facets() -> dict:
         {
             "name": spec.name, "label": spec.label, "family": spec.family,
             "granularity": spec.granularity, "preset": spec.preset,
-            "aspects": list(spec.aspects),
+            "aspects": list(spec.aspects), "edit_kind": spec.edit_kind,
         }
         for spec in FACETS.values() if spec.name in DESCRIPTIVE_FACETS
     ]}
@@ -118,7 +120,7 @@ def update_entity_fact_content(
     _get_fact(db, fact_id)
     try:
         fact = edit_entity_fact(db, fact_id=fact_id, content=body.content, changed_by=CREATED_BY,
-                                kind="correction")
+                                kind=body.kind)
     except ValueError as exc:
         db.rollback()
         raise HTTPException(status_code=422, detail=str(exc))
diff --git a/src/world_engine/facets.py b/src/world_engine/facets.py
index dbbfd84..55c88f0 100644
--- a/src/world_engine/facets.py
+++ b/src/world_engine/facets.py
@@ -8,6 +8,10 @@ statement; `typed` = the fact IS a relation/event/world_law row), the
 default-knowledge preset applied to NEW writing, a French label and a French
 one-line description (UI help and future extractor vocabulary; no check reads
 them), and the known aspects — a suggestion list, never a closed set (Q12d).
+`edit_kind` (TICKET-0105, H1) is the kind preselected when the creator
+rewrites a fact of that facet: `changement` for what one sees of an entity
+and can change in the world (physique, tenue), `correction` otherwise; the
+creator can always pick the other one.
 
 `FACETS` insertion order is the display order. This module imports nothing
 from `models` or `writes`.
@@ -32,6 +36,7 @@ class FacetSpec:
     label: str           # French UI label
     description: str     # one French sentence: what belongs here
     aspects: tuple[str, ...] = ()   # known aspects, suggestion only
+    edit_kind: str = "correction"   # preselected rewrite kind (H1): correction | changement
 
 
 _SPECS = (
@@ -40,9 +45,11 @@ _SPECS = (
     FacetSpec("statut", "identite", "affirmation", "location", "Statuts",
               "Une position sociale, une charge ou un rang que l'entité occupe."),
     FacetSpec("physique", "identite", "bloc", "rencontre", "Physique",
-              "Ce que l'on voit durablement de l'entité : corps, visage, allure."),
+              "Ce que l'on voit durablement de l'entité : corps, visage, allure.",
+              edit_kind="changement"),
     FacetSpec("tenue", "identite", "bloc", "rencontre", "Tenue",
-              "Ce que l'entité porte en ce moment et qui peut changer."),
+              "Ce que l'entité porte en ce moment et qui peut changer.",
+              edit_kind="changement"),
     FacetSpec("description", "identite", "bloc", "public_world", "Description",
               "La présentation générale de l'entité."),
     FacetSpec("reputation", "identite", "affirmation", "location", "Réputation",
diff --git a/src/world_engine/lore_write_apply.py b/src/world_engine/lore_write_apply.py
index 4088735..7e1cc65 100644
--- a/src/world_engine/lore_write_apply.py
+++ b/src/world_engine/lore_write_apply.py
@@ -29,6 +29,7 @@ from .facets import DESCRIPTIVE_FACETS, FACETS
 from .fact_refs import find_held
 from .models import Entity, Fact, FactDefault, FactionMembership, FactParticipant, Relation
 from .writes.facets import ScopeChoice, add_lore_fact, edit_entity_fact
+from .writes.facts import FACT_CHANGE_KINDS
 from .writes.facts import attach_participants, create_fact_default
 from .writes.factions import write_membership
 from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER, write_knowledge
@@ -167,6 +168,9 @@ def _validate_fact(db: Session, world_id: str, refs: dict[str, dict], item: dict
             spec = FACETS.get(fact.facet or "")
             if fact.facet not in DESCRIPTIVE_FACETS or spec is None or spec.granularity != "bloc":
                 raise ProposalError(f"{where} : seul un fait « bloc » se réécrit.")
+            if item.get("kind") not in FACT_CHANGE_KINDS:
+                raise ProposalError(
+                    f"{where} : dis si la réécriture est une correction ou un changement dans le monde.")
     _validate_scopes(refs, item, where)
     _validate_knowers(refs, item, where)
 
@@ -282,7 +286,7 @@ class _Writer:
             fact = self.db.get(Fact, item["fact_id"])
             if item["action"] == "rewrite":
                 edit_entity_fact(self.db, fact_id=fact.id, content=item["content"],
-                                 changed_by=CREATED_BY, kind="correction")
+                                 changed_by=CREATED_BY, kind=item["kind"])
                 self.record("fact", fact.id, "updated")
             self.add_participants(fact, participants)
             self.add_defaults(fact, self.scopes(item))
diff --git a/src/world_engine/lore_write_draft.py b/src/world_engine/lore_write_draft.py
index e6f207e..540e598 100644
--- a/src/world_engine/lore_write_draft.py
+++ b/src/world_engine/lore_write_draft.py
@@ -248,6 +248,13 @@ def _pairs(raw: Any, keys: tuple[str, str], known: set[str]) -> list[dict]:
     return out
 
 
+def _preset_kind(db: Session, fact_id: str) -> str:
+    """The rewrite kind preselected for a fact's facet (TICKET-0105, H1)."""
+    fact = db.get(Fact, fact_id)
+    spec = FACETS.get(fact.facet or "") if fact is not None else None
+    return spec.edit_kind if spec is not None else "correction"
+
+
 def draft_proposal(
     db: Session, world_id: str, statement: str, answers: str = "", exchanges: Exchanges = None,
 ) -> dict:
@@ -270,6 +277,8 @@ def draft_proposal(
                          for raw in _as_list(parsed.get("facts"))) if f is not None]
     for index, fact in enumerate(facts, start=1):
         fact["ref"] = f"f{index}"
+        if fact["action"] == "rewrite":
+            fact["kind"] = _preset_kind(db, fact["fact_id"])
     return {
         "statement": statement.strip(), "answers": answers.strip() or None,
         "entities": entities, "facts": facts,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index a9127eb..1ef5062 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17839,6 +17839,23 @@ absent when blindfolded. Being at the same place is a contact right now
 (O1), so the outfit shown in a scene is the current one; the versions
 matter for whoever is elsewhere.
 
+
+## THE CREATOR SAYS WHETHER A REWRITE CORRECTS OR CHANGES THE WORLD (TICKET-0105) -- PRESELECTED BY FACET (BRIEF-0105-f, no schema change)
+
+**H1.** Both places where the creator rewrites a fact ask the kind. The
+fiche's facts editor shows a « Correction / Changement dans le monde »
+choice beside each save and sends it as `kind` with `PUT
+/api/facts/{id}/content`, whose body now requires it. The Lore writing
+panel shows the same choice on a rewritten fact; the proposal carries it
+and `lore_write_apply` refuses a rewrite without one. The choice is
+preselected from the facet: `FacetSpec.edit_kind`, `changement` for
+`physique` and `tenue` (what one sees of an entity and can change in the
+world), `correction` for every other facet, served by `GET /api/facets` and
+put on a rewrite by the Lore draft.
+
+**Rejected.** H2, no preselection: every outfit change would need a click
+the facet already answers.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/fact_learning.py b/tooling/verify/checks/fact_learning.py
index 880e039..f518073 100644
--- a/tooling/verify/checks/fact_learning.py
+++ b/tooling/verify/checks/fact_learning.py
@@ -97,6 +97,22 @@ E3 -- the outfit in the scene (V1, fixture). A public NPC wearing a `tenue`
    same place: `_mj_context_co_presents` gives its `tenue` text; blindfolded,
    `None`.
 
+F1 -- the preselected kind (BRIEF-0105-F, H1). Every `FACETS` spec has an
+   `edit_kind` in `FACT_CHANGE_KINDS`; exactly `physique` and `tenue`
+   preselect `changement`; `GET /api/facets` serves `edit_kind`;
+   `lore_write_draft._preset_kind` gives a physique fact `changement` and a
+   description fact `correction`, and `draft_proposal` calls it for a
+   rewrite.
+F2 -- the fiche route (fixture). `FactContentBody` refuses a body without
+   `kind` or with another value; `update_entity_fact_content` with
+   `changement` appends a `changement` entry. (A Lore rewrite without
+   `kind` is refused by `lore_write.py` C1d.)
+F3 -- the panels send it (static). `FactsEditor.svelte` sends
+   `kind: kindOf(` with both of its content PUTs and offers both kinds;
+   `WritePanel.svelte` offers both kinds on a rewrite;
+   `writePanel.svelte.js` puts `kind` on a rewrite in `toProposal`; the
+   built bundle carries « Changement dans le monde ».
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -776,6 +792,88 @@ def check_e3(engine) -> None:
             fail(f"E3: blindfolded, the scene shows {blind}")
 
 
+# --- F1-F3 ---------------------------------------------------------------------
+
+def check_f1(engine) -> None:
+    import ast
+
+    from sqlmodel import Session
+
+    from world_engine.cockpit.crud.facets import list_facets
+    from world_engine.facets import FACETS
+    from world_engine.lore_write_draft import _preset_kind
+    from world_engine.writes import add_entity_fact
+    from world_engine.writes.facts import FACT_CHANGE_KINDS
+
+    if any(spec.edit_kind not in FACT_CHANGE_KINDS for spec in FACETS.values()):
+        fail("F1: an edit_kind is outside FACT_CHANGE_KINDS")
+    changes = {name for name, spec in FACETS.items() if spec.edit_kind == "changement"}
+    if changes != {"physique", "tenue"}:
+        fail(f"F1: the facets preselecting changement are {sorted(changes)}")
+    served = {f["name"]: f.get("edit_kind") for f in list_facets()["facets"]}
+    if not served or any(served[n] != FACETS[n].edit_kind for n in served):
+        fail(f"F1: /api/facets serves {served}")
+    with Session(engine) as session:
+        ids = _d_world(session)
+        kinds = {}
+        for facet in ("physique", "description"):
+            fact = add_entity_fact(session, entity_id=ids["A"], facet=facet, content=facet,
+                                   created_by="check")
+            session.flush()
+            kinds[facet] = _preset_kind(session, fact.id)
+        session.rollback()
+    if kinds != {"physique": "changement", "description": "correction"}:
+        fail(f"F1: _preset_kind gives {kinds}")
+    tree = ast.parse((SRC / "lore_write_draft.py").read_text(encoding="utf-8"))
+    draft = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
+                  and n.name == "draft_proposal"), None)
+    if draft is None or not any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_preset_kind"
+                                for n in ast.walk(draft)):
+        fail("F1: draft_proposal does not preselect a rewrite's kind")
+
+
+def check_f2(engine) -> None:
+    from pydantic import ValidationError
+    from sqlmodel import Session
+
+    from world_engine.cockpit.crud.facets import FactContentBody, update_entity_fact_content
+    from world_engine.models import Fact
+    from world_engine.writes import add_entity_fact
+
+    for body in ({"content": "x"}, {"content": "x", "kind": "retcon"}):
+        try:
+            FactContentBody(**body)
+            fail(f"F2: FactContentBody accepted {body}")
+        except ValidationError:
+            pass
+    with Session(engine) as session:
+        ids = _d_world(session)
+        fact = add_entity_fact(session, entity_id=ids["A"], facet="tenue", content="veste",
+                               created_by="check")
+        session.commit()
+        update_entity_fact_content(fact.id, FactContentBody(content="manteau", kind="changement"), session)
+        history = session.get(Fact, fact.id).change_history
+        if not history or history[-1].get("kind") != "changement":
+            fail(f"F2: the fiche route wrote {history}")
+
+
+def check_f3() -> None:
+    root = ROOT / "frontend" / "src"
+    editor = (root / "creation" / "FactsEditor.svelte").read_text(encoding="utf-8")
+    panel = (root / "lore" / "WritePanel.svelte").read_text(encoding="utf-8")
+    state = (root / "lore" / "writePanel.svelte.js").read_text(encoding="utf-8")
+    if editor.count("kind: kindOf(") != 2 or 'value="changement"' not in editor \
+            or 'value="correction"' not in editor:
+        fail("F3: FactsEditor.svelte does not send and offer the kind")
+    if "fact.kind = 'correction'" not in panel or "fact.kind = 'changement'" not in panel:
+        fail("F3: WritePanel.svelte does not offer both kinds on a rewrite")
+    if "if (f.action === 'rewrite') out.kind = f.kind;" not in state:
+        fail("F3: toProposal does not send a rewrite's kind")
+    bundles = list((SRC / "cockpit" / "static" / "assets").glob("*.js"))
+    if not bundles or not any("Changement dans le monde" in b.read_text(encoding="utf-8") for b in bundles):
+        fail("F3: the built bundle does not carry the choice (rebuild the frontend)")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -794,6 +892,9 @@ def main() -> int:
     check_e1(engine)
     check_e2()
     check_e3(engine)
+    check_f1(engine)
+    check_f2(engine)
+    check_f3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -804,7 +905,8 @@ def main() -> int:
           "every rewrite says whether it corrects or changes the world, and the version "
           "known follows the changes alone; a default is learned by a contact after it, kept "
           "after leaving, and dated by the last contact with its anchors; every knower "
-          "reader gives the version known, and the scene shows the outfit")
+          "reader gives the version known, and the scene shows the outfit; both editors make "
+          "the creator say whether a rewrite corrects or changes the world")
     return 0
 
 
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 3b3b960..7e6d7ff 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -31,7 +31,8 @@ C1 -- apply (BRIEF-0098-C, C-02), on a fixture world, through
       and reports the existing knower, participant, membership, default and
       `controls` edge as skipped;
    c. a `rewrite` of a `bloc` fact changes its text, appends the previous
-      one to `change_history`, and records `updated`;
+      one to `change_history` with the proposal's `kind` (TICKET-0105), and
+      records `updated`;
    d. every row of `_REFUSALS` raises `ProposalError` before any write:
       the row counts of every recorded table are unchanged;
    e. a proposal refused by a write site (a second `bloc` fact on the same
@@ -318,7 +319,11 @@ _REFUSALS = (
     ("same scope twice", lambda p: p["facts"][0]["defaults"].append({"scope_type": "world"})),
     ("fact of another world", lambda p: p["facts"][3].update(fact_id="nope")),
     ("rewrite of a non-bloc fact", lambda p: p["facts"].append(
-        {"ref": "f9", "action": "rewrite", "fact_id": "__f3__", "content": "x"})),
+        {"ref": "f9", "action": "rewrite", "fact_id": "__f3__", "content": "x", "kind": "correction"})),
+    ("rewrite without kind (TICKET-0105)", lambda p: p["facts"].append(
+        {"ref": "f9", "action": "rewrite", "fact_id": "__bloc__", "content": "x"})),
+    ("rewrite of an unknown kind", lambda p: p["facts"].append(
+        {"ref": "f9", "action": "rewrite", "fact_id": "__bloc__", "content": "x", "kind": "retcon"})),
     ("membership of a location", lambda p: p["memberships"][0].update(entity_ref="e2")),
     ("control of a faction", lambda p: p["controls"][0].update(location_ref="e3")),
     ("nothing to write", lambda p: [p.update(facts=[], memberships=[], controls=[])]),
@@ -370,13 +375,14 @@ def check_c1() -> None:
             fail(f"C1b: a second apply skipped {second.skipped}, expected the existing rows")
         rewrite = {"statement": "Maëlle a changé.", "entities": [], "facts": [
             {"ref": "f1", "action": "rewrite", "fact_id": ids["bloc"],
-             "content": "Une passeuse devenue célèbre."}]}
+             "content": "Une passeuse devenue célèbre.", "kind": "changement"}]}
         res = lwa.apply_proposal(db, ids["world"], rewrite, _creator(db, ids["world"]))
         db.commit()
         bloc = db.get(Fact, ids["bloc"])
         rows = db.exec(__import__("sqlmodel").select(LoreEntryRow).where(
             LoreEntryRow.entry_id == res.entry_id)).all()
         if ("célèbre" not in fact_text(db, bloc) or not bloc.change_history
+                or bloc.change_history[-1].get("kind") != "changement"
                 or [(r.row_table, r.action) for r in rows] != [("fact", "updated")]):
             fail("C1c: the bloc rewrite did not update in place with history and one row")
         for label, mutate in _REFUSALS:
@@ -385,6 +391,8 @@ def check_c1() -> None:
             for item in proposal.get("facts") or []:
                 if item.get("fact_id") == "__f3__":
                     item["fact_id"] = f3.id if f3 else "nope"
+                elif item.get("fact_id") == "__bloc__":
+                    item["fact_id"] = ids["bloc"]
             before = _counts(db)
             try:
                 lwa.apply_proposal(db, ids["world"], proposal, _creator(db, ids["world"]))
````

## Scope OUT

- Asking the kind on a deletion (I1: deleting is a correction).
- A kind on creating a fact (a new fact has no previous version).
- Any other facet preselecting `changement`.
- Showing a fact's history in the fiche.
- Rewrites made by code (U1, done in C).
- Every later brief of this lot.

## Invariants to defend

**A lore statement commits whole or not at all:** a rewrite without kind is refused before any write (`lore_write.py` C1d). **History is sacred:** both paths still append before overwriting. **Inside a `$effect` body, a `$state` binding assigned there must not be read afterwards in the same body:** `kinds` is assigned in an event handler only. The built `static/` must match the sources.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.
- `lore_write.py` F1 fails (a new request path, or `entity_id` in `WritePanel.svelte` markup).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- The built bundle's file name differs from the prototype's: expected (content hash); commit whatever `npm run build` wrote.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `npm` audit, deprecation or engine notices.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt files under `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/fact_learning.py` → `PASS: fact_learning -- … both editors make the creator say whether a rewrite corrects or changes the world`.
- `lore_write.py`, `lore_usage.py`, `fact_facets.py`, `frontend_build_fresh.py`, `effect_self_write.py` → `PASS`.
- Mutation test: in `facets.py`, drop `edit_kind="changement"` from `tenue` → `F1`; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 138/138.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE CREATOR SAYS WHETHER A REWRITE CORRECTS OR CHANGES THE WORLD (TICKET-0105) -- PRESELECTED BY FACET (BRIEF-0105-f, no schema change)` — in the diff.
