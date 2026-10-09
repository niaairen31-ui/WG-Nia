<!-- slug: interpreter-editor -->
# BRIEF 0112-E — "« Écrire en langage naturel » under every condition of the offer editor -- the creator inserts or discards, her save writes"

Lot: LOT-0112-condition-interpreter.md (authoritative on conflict)
Depends on: BRIEF-0112-D (C-06, C-08)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0112-D's commit).

- `frontend/src/creation/ConditionEditor.svelte:10` -> `let { cond, choices, emptyLabel, addLabel } = $props();`
- `frontend/src/creation/QuestOffers.svelte:137` -> `<ConditionEditor cond={draft.eligibility} {choices} emptyLabel="Tout le monde." addLabel="+ condition" />`
- `frontend/src/creation/questRequirements.js:98` -> `export function conditionDraft(view) {`
- `frontend/src/creation/questRequirements.js:111` -> `export function blankCondition() {`
- `frontend/src/creation/questOffers.svelte.js:118` -> `function draftBody(draft) {`
- `src/world_engine/cockpit/routes/conditions.py:104` -> `@router.post("/api/conditions/interpret")`
- `src/world_engine/cockpit/routes/quests.py:92` -> `eligibility_draft_id: Optional[str] = None`
- No `frontend/src/creation/ConditionInterpreter.svelte` and no `frontend/src/creation/conditionInterpreter.svelte.js` exist.

## Facts carried

### R-11 — the offer API and the editor [M]
Opened: `src/world_engine/cockpit/routes/quests.py:51-58` (`OfferStepBody`),
`:72-84` (`OfferBody`), `:116-137` (`_save_offer`: `node_from_dict` and
`write_quest_offer` inside one `try`, `ValueError` -> rollback and 422, then
`commit`); `src/world_engine/quest_reads.py:61-67` (`condition_view`: tree,
flat rows or None, French lines), `:98-101` (`world_offers`).
`frontend/src/creation/ConditionEditor.svelte:10` (props `cond, choices,
emptyLabel, addLabel`), its locked branch (lines, « Effacer »);
`frontend/src/creation/QuestOffers.svelte:137,160,162` (three
`ConditionEditor`s); `frontend/src/creation/questRequirements.js:32`
(`MONEY_KEY = 'monnaie'`), `:98-109` (`conditionDraft(view)`), `:111-113`
(`blankCondition`), `conditionBody` (locked tree, `all` of the rows, or
null); `frontend/src/creation/questOffers.svelte.js:118-131` (`draftBody`);
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`: throws an
`Error` carrying `detail`).
Consequence: nothing new writes an offer; the proposal's view is
`condition_view`'s shape, so `conditionDraft(view)` inserts it; the save
carries one draft id per condition.

## Contracts

### C-06 — the routes
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`POST /api/conditions/interpret` body `{instruction: str, role: str,
current: dict | null, attempt_id: str | null}`;
`POST /api/conditions/drafts/{draft_id}/resolve` body `{bindings: {ref:
entity_id}}`; `POST /api/conditions/drafts/{draft_id}/decision` body
`{decision: "inserted" | "discarded"}`.
Answer (all three): `{draft_id, outcome, view: {tree, flat, lines} | null,
mentions: [the mentions waiting for a pick: not matched, with choices],
notes: [str], errors: [str]}` -- `view` is `quest_reads.condition_view` of
the proposed tree; the decision's answer carries `draft_id` and the new
`outcome` with empty lists.
Statuses: b-5.

### C-08 — the offer body's draft ids
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`OfferBody.eligibility_draft_id: Optional[str]`;
`OfferStepBody.prerequisite_draft_id`, `.completion_draft_id:
Optional[str]`. `routes/quests._mark_drafts(body, offer_id, world_id, db)`,
called by `_save_offer` after `write_quest_offer` and before `commit`: for
each given id, the condition as written
(`node_to_dict(clean_condition(node_from_dict(raw)))`) goes to
`mark_draft_saved`. Frontend: a condition draft carries `draftId` (null by
default, the inserted proposal's id), sent as those three fields.

## Context

The routes exist (D). This brief gives them a face in the offer editor: under each condition -- who the offer is for, each step's prerequisite and completion -- a sentence box, the proposal read back in French, a pick when a name is ambiguous, then « Insérer dans l'offre » or « Écarter ». An inserted flat condition becomes the editable rows, a nested one the read-only lines; « Enregistrer » sends, per condition, the proposal she inserted.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `frontend/src/creation/conditionInterpreter.svelte.js` (`interpreterState`, `askInterpreter`, `pickNames`, `insertProposal`, `discardProposal`) and `frontend/src/creation/ConditionInterpreter.svelte` (a child component, never an island);
   - `ConditionEditor.svelte`: a `role` prop, renders `<ConditionInterpreter {cond} {role} />`, the locked note says it is edited in natural language;
   - `QuestOffers.svelte`: passes `role` to its three `ConditionEditor`s;
   - `questRequirements.js`: `conditionDraft` and `blankCondition` carry `draftId: null`; `questOffers.svelte.js`: `draftBody` sends the three draft ids (C-08);
   - adds NE1 to `condition_interpreter.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/ConditionEditor.svelte
   - frontend/src/creation/ConditionInterpreter.svelte
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/conditionInterpreter.svelte.js
   - frontend/src/creation/questOffers.svelte.js
   - frontend/src/creation/questRequirements.js
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py

````diff
diff --git a/frontend/src/creation/ConditionEditor.svelte b/frontend/src/creation/ConditionEditor.svelte
index 8007b6a..4c3acab 100644
--- a/frontend/src/creation/ConditionEditor.svelte
+++ b/frontend/src/creation/ConditionEditor.svelte
@@ -2,12 +2,15 @@
   /* TICKET-0111 (BRIEF-0111-D, T1). One condition of a quest offer: a flat
      condition is edited as a list of requirement rows (`all` of them); a
      nested one is shown by its French lines, read-only, and saved back
-     unchanged -- the interpreter will edit it. `cond` is a draft object
-     owned by questOffersState (conditionDraft in questRequirements.js). */
+     unchanged. `cond` is a draft object owned by questOffersState
+     (conditionDraft in questRequirements.js). TICKET-0112 (BRIEF-0112-E,
+     IB1, T1): both are also written and edited in French, through the
+     interpreter under the condition; `role` is the condition's. */
   import QuestRequirementRow from './QuestRequirementRow.svelte';
+  import ConditionInterpreter from './ConditionInterpreter.svelte';
   import { blankRequirement } from './questRequirements.js';
 
-  let { cond, choices, emptyLabel, addLabel } = $props();
+  let { cond, choices, role, emptyLabel, addLabel } = $props();
 
   function clearLocked() {
     cond.locked = null;
@@ -20,7 +23,7 @@
     {#each cond.lines as line, i (i)}
       <div style={'padding-left:' + line.depth * 14 + 'px'}>{line.text}</div>
     {/each}
-    <p class="muted">Condition imbriquée : elle se modifiera par l'interprète en langage naturel.</p>
+    <p class="muted">Condition imbriquée : elle se modifie en langage naturel.</p>
     <button onclick={() => clearLocked()}>Effacer cette condition</button>
   </div>
 {:else}
@@ -30,6 +33,7 @@
   {/each}
   <button onclick={() => cond.list.push(blankRequirement())}>{addLabel}</button>
 {/if}
+<ConditionInterpreter {cond} {role} />
 
 <style>
   .cond-locked { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
diff --git a/frontend/src/creation/ConditionInterpreter.svelte b/frontend/src/creation/ConditionInterpreter.svelte
new file mode 100644
index 0000000..e74b84f
--- /dev/null
+++ b/frontend/src/creation/ConditionInterpreter.svelte
@@ -0,0 +1,70 @@
+<script>
+  /* TICKET-0112 (BRIEF-0112-E, IB1). « Écrire en langage naturel » under one
+     condition of the offer editor: a sentence, then the proposal read back
+     in French -- inserted into the draft or discarded by the creator. The
+     requests live in conditionInterpreter.svelte.js. */
+  import {
+    interpreterState, askInterpreter, pickNames, insertProposal, discardProposal,
+  } from './conditionInterpreter.svelte.js';
+
+  let { cond, role } = $props();
+
+  const s = $state(interpreterState());
+  let proposal = $derived(s.proposal);
+  let picked = $derived(proposal ? proposal.mentions.every((m) => s.picks[m.ref]) : false);
+</script>
+
+{#if !s.open}
+  <button class="link" onclick={() => { s.open = true; }}>Écrire en langage naturel</button>
+{:else}
+  <div class="interp">
+    <textarea rows="2" placeholder="Ex. : le joueur possède 15 fourrures de loup ou est membre de la Guilde"
+              bind:value={s.instruction}></textarea>
+    <div class="inline">
+      <button disabled={s.busy || !s.instruction.trim()} onclick={() => askInterpreter(s, cond, role)}>
+        {proposal ? 'Reformuler' : 'Proposer'}
+      </button>
+      <button class="link" onclick={() => { s.open = false; }}>Fermer</button>
+      {#if s.busy}<span class="muted">Le modèle réfléchit…</span>{/if}
+    </div>
+    {#if s.error}<p class="err">{s.error}</p>{/if}
+    {#if proposal}
+      <div class="proposal">
+        {#if proposal.view}
+          {#each proposal.view.lines as line, i (i)}
+            <div style={'padding-left:' + line.depth * 14 + 'px'}>{line.text}</div>
+          {/each}
+        {/if}
+        {#each proposal.mentions as m (m.ref)}
+          <label>« {m.name} » :
+            <select bind:value={s.picks[m.ref]}>
+              <option value="">choisir…</option>
+              {#each m.choices as c (c.entity_id)}<option value={c.entity_id}>{c.name} ({c.type})</option>{/each}
+            </select>
+          </label>
+        {/each}
+        {#each proposal.notes as note, i (i)}<p class="muted">{note}</p>{/each}
+        {#each proposal.errors as error, i (i)}<p class="err">{error}</p>{/each}
+        <div class="inline">
+          {#if proposal.outcome === 'needs_choice'}
+            <button disabled={s.busy || !picked} onclick={() => pickNames(s)}>Appliquer les choix</button>
+          {/if}
+          {#if proposal.outcome === 'proposed'}
+            <button onclick={() => insertProposal(s, cond)}>Insérer dans l'offre</button>
+          {/if}
+          <button onclick={() => discardProposal(s)}>Écarter</button>
+        </div>
+      </div>
+    {/if}
+  </div>
+{/if}
+
+<style>
+  .interp { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
+  .interp textarea { width: 100%; }
+  .proposal { margin-top: 4px; }
+  .inline { display: flex; gap: 6px; align-items: center; }
+  .link { background: none; border: none; color: var(--accent, inherit); cursor: pointer; padding: 0; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .err { color: var(--danger, #c33); font-size: 12px; }
+</style>
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 8fa4faa..3b3f56d 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -134,7 +134,7 @@
         </div>
 
         <h4>Proposée à qui remplit</h4>
-        <ConditionEditor cond={draft.eligibility} {choices} emptyLabel="Tout le monde." addLabel="+ condition" />
+        <ConditionEditor cond={draft.eligibility} {choices} role="eligibility" emptyLabel="Tout le monde." addLabel="+ condition" />
 
         <h4>Étapes</h4>
         {#each draft.steps as step, i (i)}
@@ -157,9 +157,9 @@
                       onclick={() => draft.steps.splice(i, 1)}>✕</button>
             </div>
             <div class="muted">Prérequis</div>
-            <ConditionEditor cond={step.prerequisite} {choices} addLabel="+ prérequis de l'étape" />
+            <ConditionEditor cond={step.prerequisite} {choices} role="prerequisite" addLabel="+ prérequis de l'étape" />
             <div class="muted">Objectif atteint quand</div>
-            <ConditionEditor cond={step.completion} {choices}
+            <ConditionEditor cond={step.completion} {choices} role="completion"
                              emptyLabel="Rien de vérifiable : c'est vous qui le déclarez." addLabel="+ condition d'objectif" />
           </div>
         {/each}
diff --git a/frontend/src/creation/conditionInterpreter.svelte.js b/frontend/src/creation/conditionInterpreter.svelte.js
new file mode 100644
index 0000000..47ff319
--- /dev/null
+++ b/frontend/src/creation/conditionInterpreter.svelte.js
@@ -0,0 +1,74 @@
+/* TICKET-0112 (BRIEF-0112-E, IB1, IC1, IG1). The interpreter of one
+   condition of the offer editor: the creator writes it in French, reads the
+   proposal back (its French lines, the notes, the errors), picks a name
+   when one is ambiguous, then inserts it into her draft or discards it.
+   Nothing reaches the offer before her « Enregistrer »: an inserted
+   proposal replaces the condition draft (`conditionDraft`) and leaves its
+   id on it (`cond.draftId`), which the save sends back (IH1). One attempt
+   id per editor, kept across reformulations. */
+import { api } from './sheetRequest.svelte.js';
+import { conditionBody, conditionDraft } from './questRequirements.js';
+
+export function interpreterState() {
+  return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
+           proposal: null, picks: {} };
+}
+
+async function post(path, body) {
+  return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
+}
+
+async function run(state, request) {
+  state.busy = true;
+  state.error = '';
+  try {
+    state.proposal = await request();
+    state.picks = {};
+  } catch (e) {
+    state.error = e.message;
+  } finally {
+    state.busy = false;
+  }
+}
+
+/** A proposal for `cond` from the sentence; the current condition goes along (IC1). */
+export function askInterpreter(state, cond, role) {
+  return run(state, () => post('/api/conditions/interpret', {
+    instruction: state.instruction, role, current: conditionBody(cond), attempt_id: state.attemptId,
+  }));
+}
+
+/** The names the creator picked, one per waiting mention. */
+export function pickNames(state) {
+  return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
+                               { bindings: state.picks }));
+}
+
+async function decide(state, decision) {
+  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision });
+}
+
+/** Insert the proposal into the condition draft (a flat one as rows, a nested one locked). */
+export async function insertProposal(state, cond) {
+  const proposal = state.proposal;
+  try {
+    await decide(state, 'inserted');
+  } catch (e) {
+    state.error = e.message;
+    return;
+  }
+  Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id });
+  state.proposal = null;
+  state.instruction = '';
+  state.open = false;
+}
+
+/** Discard the proposal; the sentence stays, to reformulate. */
+export async function discardProposal(state) {
+  try {
+    if (state.proposal.outcome !== 'refused') await decide(state, 'discarded');
+  } catch (e) {
+    state.error = e.message;
+  }
+  state.proposal = null;
+}
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 5200e59..048138c 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -6,7 +6,8 @@
    value (POST /api/quest-offers/value), and the world's rates. Since
    TICKET-0111 (BRIEF-0111-D): every condition -- the eligibility, each
    step's prerequisite and completion -- is a condition draft, sent as a
-   tree (conditionBody). */
+   tree (conditionBody). Since TICKET-0112 (BRIEF-0112-E, IH1): with the id
+   of the interpreter's proposal inserted into it, which the save marks. */
 import { api } from './sheetRequest.svelte.js';
 import { blankCondition, conditionBody, conditionDraft } from './questRequirements.js';
 import { blankTerm, termBody } from './questTerms.js';
@@ -121,9 +122,11 @@ function draftBody(draft) {
     title: draft.title, summary: draft.summary || null,
     repeatable: draft.repeatable, status: draft.status,
     eligibility: conditionBody(draft.eligibility),
+    eligibility_draft_id: draft.eligibility.draftId || null,
     steps: draft.steps.map((s) => ({
       objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
       prerequisite: conditionBody(s.prerequisite), completion: conditionBody(s.completion),
+      prerequisite_draft_id: s.prerequisite.draftId || null, completion_draft_id: s.completion.draftId || null,
     })),
     terms: draft.terms.map(termBody),
   };
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index 0aa10d7..2040194 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -94,9 +94,10 @@ export function requirementBody(req) {
    tree shown read-only by its French `lines` and sent back unchanged --
    only the interpreter will edit those. */
 
-/** The editor's draft of one condition, from the server's view (`quest_reads.condition_view`). */
+/** The editor's draft of one condition, from the server's view (`quest_reads.condition_view`).
+    TICKET-0112 (IH1): `draftId`, the interpreter's proposal inserted here, if any. */
 export function conditionDraft(view) {
-  if (view && !view.flat) return { list: [], locked: view.tree, lines: view.lines || [] };
+  if (view && !view.flat) return { list: [], locked: view.tree, lines: view.lines || [], draftId: null };
   return {
     list: (view?.flat || []).map((r) => ({
       ...r,
@@ -105,11 +106,12 @@ export function conditionDraft(view) {
     })),
     locked: null,
     lines: [],
+    draftId: null,
   };
 }
 
 export function blankCondition() {
-  return { list: [], locked: null, lines: [] };
+  return { list: [], locked: null, lines: [], draftId: null };
 }
 
 /** The tree a condition draft sends: the locked tree, `all` of the rows, or null. */
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index e340bc4..2f31959 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18633,6 +18633,21 @@ an unparsable reply (502) included; a request refused before the model is
 not. A proposal's attempt id is the editor's, in canonical form, or a
 fresh one (`lore_usage.attempt_id`).
 
+## « ÉCRIRE EN LANGAGE NATUREL » UNDER EVERY CONDITION OF THE OFFER EDITOR (TICKET-0112) -- THE CREATOR INSERTS OR DISCARDS, HER SAVE WRITES (BRIEF-0112-e, no schema change)
+
+**IB1, IG1.** Under each condition of the offer editor -- the
+eligibility, each step's prerequisite and completion -- « Écrire en langage
+naturel » opens a sentence box. The proposal comes back as its French
+lines, its notes and errors; an ambiguous name is picked from its choices;
+the creator then inserts it into her draft or discards it and
+reformulates. An inserted flat condition becomes the editable rows, a
+nested one the read-only lines (T1): every nested condition is now written
+and edited in French. The editor sends the current condition with the
+sentence (IC1). Nothing reaches the offer before « Enregistrer », which
+sends, per condition, the id of the proposal inserted there (IH1).
+Rejected: IB2 (a panel in the Lore shell: detached from the offer it
+changes, and a third reopening of 0085's read-only lock).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index 4b76434..7a94540 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -117,6 +117,19 @@ ND3 -- saving the offer (fixture). An offer saved with its eligibility as
    `saved`, false; an unknown draft id and a `proposed` draft's id leave
    the save whole and the `proposed` draft unmoved.
 
+NE1 -- the editor (BRIEF-0112-E; static). `ConditionEditor.svelte` renders
+   `<ConditionInterpreter {cond} {role} />`; `QuestOffers.svelte` passes
+   `role="eligibility"`, `"prerequisite"` and `"completion"`, one each.
+   `conditionInterpreter.svelte.js` POSTs `/api/conditions/interpret` with
+   `current: conditionBody(cond)` and `attempt_id: state.attemptId`,
+   `/resolve` with the picks and `/decision` with `'inserted'` and
+   `'discarded'`; `insertProposal` records `inserted` before it assigns
+   `conditionDraft(proposal.view)` and `draftId: proposal.draft_id` to the
+   condition. `conditionDraft` and `blankCondition` set `draftId: null`;
+   `questOffers.svelte.js` sends `eligibility_draft_id`,
+   `prerequisite_draft_id` and `completion_draft_id`. The built bundle
+   under `cockpit/static/assets` carries `/api/conditions/interpret`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -1115,6 +1128,50 @@ def check_nd2_nd3(engine, ids) -> None:
         _nd3_save(session, ids, routes, quests, ci, answer["view"]["tree"], answer["draft_id"])
 
 
+# --- NE1 -----------------------------------------------------------------------
+
+FRONT = ROOT / "frontend" / "src" / "creation"
+
+
+def _front(name: str) -> str:
+    path = FRONT / name
+    if not path.exists():
+        fail(f"NE1: frontend/src/creation/{name} is missing")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+def check_ne1() -> None:
+    editor = _front("ConditionEditor.svelte")
+    if "<ConditionInterpreter {cond} {role} />" not in editor:
+        fail("NE1: ConditionEditor.svelte does not render the interpreter with its role")
+    offers = _front("QuestOffers.svelte")
+    for role in ("eligibility", "prerequisite", "completion"):
+        if len(re.findall(r'<ConditionEditor[^>]*role="' + role + '"', offers)) != 1:
+            fail(f"NE1: QuestOffers.svelte does not pass role={role!r} to one ConditionEditor")
+    state = _front("conditionInterpreter.svelte.js")
+    for needle in ("'/api/conditions/interpret'", "current: conditionBody(cond)", "attempt_id: state.attemptId",
+                   "'/resolve'", "bindings: state.picks", "'/decision'", "decide(state, 'discarded')"):
+        if needle not in state:
+            fail(f"NE1: conditionInterpreter.svelte.js lacks {needle!r}")
+    body = state[state.find("export async function insertProposal"):]
+    inserted, assigned = body.find("decide(state, 'inserted')"), body.find(
+        "Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id })")
+    if inserted < 0 or assigned < 0 or assigned < inserted:
+        fail("NE1: insertProposal does not record `inserted` before it fills the condition")
+    requirements = _front("questRequirements.js")
+    if requirements.count("draftId: null") < 3:
+        fail("NE1: conditionDraft and blankCondition do not all set draftId: null")
+    offers_js = _front("questOffers.svelte.js")
+    for key in ("eligibility_draft_id: draft.eligibility.draftId", "prerequisite_draft_id: s.prerequisite.draftId",
+                "completion_draft_id: s.completion.draftId"):
+        if key not in offers_js:
+            fail(f"NE1: questOffers.svelte.js does not send {key.split(':')[0]}")
+    assets = list((SRC / "cockpit" / "static" / "assets").glob("*.js"))
+    if not assets or not any("/api/conditions/interpret" in a.read_text(encoding="utf-8") for a in assets):
+        fail("NE1: the built bundle does not carry /api/conditions/interpret")
+
+
 def main() -> int:
     db_path = _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -1132,6 +1189,7 @@ def main() -> int:
     check_nc3_nc4(engine, nc_ids)
     check_nd1()
     check_nd2_nd3(engine, nc_ids)
+    check_ne1()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -1143,7 +1201,8 @@ def main() -> int:
           "and the name index, validates every leaf, asks once more with the errors, leaves a name to "
           "the creator, never writes a condition, and sends a cost back to the offer's terms; its routes "
           "journal every proposal that reached the model, move it on the creator's pick and decision, and "
-          "saving the offer marks what she inserted saved, as proposed or changed")
+          "saving the offer marks what she inserted saved, as proposed or changed; under every condition "
+          "of the offer editor, a sentence becomes a proposal she inserts or discards")
     return 0
 
 
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit as one commit: `BRIEF-0112-E: the interpreter in the offer editor`.

## Scope OUT

- A registration in `registry.js` or a new Creation tab: the interpreter lives inside the offer editor (IB1; IB2 rejected).
- A visual tree editor (T2 of 0111, rejected).
- A dry-run verdict in the proposal (IG2).
- Editing a proposal before inserting it: insert, then edit the rows (a flat one) or reformulate (IG1).
- Any change to `legacy.html` or Play; any player surface.

## Invariants to defend

**One mount mechanism** -- `ConditionInterpreter.svelte` is a child of `ConditionEditor.svelte`, never registered in `registry.js` (`creation_island.py`). **Creator control is structural** -- inserting changes only the editor's draft; « Enregistrer » writes (NE1: `inserted` recorded before the draft changes). **The built frontend is committed and fresh** (`frontend_build_fresh.py`). **Play is sealed** -- `legacy.html` untouched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `creation_island.py` or `page_contract.py` turns red.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/condition_interpreter.py` -> `PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal of the interpreter, outside any world, its outcome moving one way to « saved »; the interpreter shows the model the language and coded lists, reads its answer back through codes and the name index, validates every leaf, asks once more with the errors, leaves a name to the creator, never writes a condition, and sends a cost back to the offer's terms; its routes journal every proposal that reached the model, move it on the creator's pick and decision, and saving the offer marks what she inserted saved, as proposed or changed; under every condition of the offer editor, a sentence becomes a proposal she inserts or discards`
- `frontend_build_fresh.py`, `creation_island.py`, `page_contract.py`, `conditions.py`, `quests.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`condition_interpreter.py` exits 1 with the rule named):
  - in `frontend/src/creation/ConditionEditor.svelte`, `<ConditionInterpreter {cond} {role} />` -> `(removed)` -> `NE1`
  - in `frontend/src/creation/questOffers.svelte.js`, `    eligibility_draft_id: draft.eligibility.draftId || null,` -> `(removed)` -> `NE1`
  - in `frontend/src/creation/conditionInterpreter.svelte.js`, `    instruction: state.instruction, role, current: conditionBody(cond), attempt_id: state.attemptId,` -> `    instruction: state.instruction, role, attempt_id: state.attemptId,` -> `NE1`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 145/145.
- Live, with Ollama running and Nia's database migrated (TICKET-0112, Live): the six live criteria of the ticket.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry « « ÉCRIRE EN LANGAGE NATUREL » UNDER EVERY CONDITION OF THE OFFER EDITOR (TICKET-0112) -- THE CREATOR INSERTS OR DISCARDS, HER SAVE WRITES (BRIEF-0112-e, no schema change) » -- in the diff. No schema change.
