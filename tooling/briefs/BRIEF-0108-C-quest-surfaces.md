# BRIEF 0108-C — "Création authors the offers; Journée takes them and pins a day"

Lot: LOT-0108-quest-offers.md (authoritative on conflict)
Depends on: BRIEF-0108-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0108-B's commit). The facts carried below quote `main`'s line
numbers, as the lot does; where A or B moved a line, the anchor here gives where it now is.

- `frontend/src/creation/registry.js:548` -> `  subjectWorklist: Object.freeze({`, the registry's last entry.
- `frontend/src/creation/tabs.js:343` -> `  subjects: {`.
- `frontend/src/creation/mount.js:46` -> `const COMPONENTS = {` ending `subjectWorklist: SubjectWorklist };`.
- `frontend/src/creation/Creation.svelte:252` -> the `creation-subjects` container.
- `frontend/public/creation.css:311` -> `#creation-subjects    { flex: 1; min-height: 0; …`.
- `tooling/verify/checks/page_contract.py:46` -> `TAB_KEYS = [` (15 keys, `subjects` after `evenements`).
- `frontend/src/journee/Journee.svelte:87` -> `onclick={() => planDay(day.id)}`; `frontend/src/journee/journee.svelte.js:72` -> `export async function planDay(id) {`.
- `frontend/src/creation/sheetRequest.svelte.js:30` -> `export async function api(path, options) {`.
- `src/world_engine/cockpit/routes/quests.py:113` -> `@router.get("/api/quests")`; `src/world_engine/quest_reads.py:149` -> `def journee_payload(`.
- `tooling/verify/checks/quests.py:767` -> `    check_qb(engine)`.

## Facts carried

### R-19 — Journée never sees the agenda [M]
Opened: `tooling/verify/checks/day_mutations.py:25-34`, `:332-352` (R7: no
dict built in `routes/day.py` has an `agenda_id`/`step_id` key; `Journee.
svelte` names neither).
Consequence: quest payloads carry `quest_id`/`offer_id` only; `quests.py`
extends R7 to the new modules (QB4, QC3).

### R-21 — a Création island created as such [M]
Opened: `tooling/verify/checks/creation_island.py:1-140` (rules 1-13:
registry `origin: 'new'` with `containerId`, `component`, `createdBy`;
rule 5 tabs <-> registry; rule 9 `loader: null`; rule 11 a routed
`primaryAction` needs `export function primaryAction` in the component;
rule 12 `COMPONENTS`); `frontend/src/creation/registry.js:544-553`
(`subjectWorklist`, `origin: 'new'`); `frontend/src/creation/tabs.js:343-
351` (`subjects`); `frontend/src/creation/mount.js:30-46`;
`frontend/src/creation/Creation.svelte:252`;
`tooling/verify/checks/page_contract.py:46-49` (`TAB_KEYS`);
`tooling/verify/checks/creation_container_sizing.py:17-23` with
`frontend/public/creation.css:311` (a single-container tab needs
`#<id> { flex: 1; min-height: 0 }`).

### R-26 — the frontend build [M]
Opened: `frontend/package.json` (`vite build` then the manifest); a rebuild
of unchanged sources changes only `.build-manifest.json`'s `built_at`
(`frontend_build_fresh.py` passes); `frontend/public/` is copied into
`static/`.

### R-27 — `api()` [M]
Opened: `frontend/src/creation/sheetRequest.svelte.js:30-35` (throws
`Error(detail)` on a non-2xx).

## Contracts

### C-01 — the requirement vocabulary (family contract)
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B, BRIEF-0108-C
Written before its members; re-read after the last (`quest_completed`).

In `src/world_engine/day_plan.py`, literal tuples, in this order:

```python
REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable",
                     "has_met", "faction_member", "skill_rank_gte", "quest_completed")
MODEL_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
ENTITY_TARGET_TYPES = ("relation_gte", "location_reachable", "has_met", "faction_member")
KEY_TARGET_TYPES = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
THRESHOLD_TYPES = ("relation_gte", "resource", "skill_rank_gte")
```

The two CHECK texts, carried byte for byte by `agenda_step_requirement`
(`ck_agenda_step_requirement_type`, `_shape`) and `quest_offer_requirement`
(`ck_quest_offer_requirement_type`, `_shape`):

```
type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')
(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
```

Members (every row has all six columns):

| form | target | threshold | met iff | blocked reason (French) | `_clean_requirement` refuses | model |
|---|---|---|---|---|---|---|
| `knowledge` | key: fact id | -- | the character holds a row on the fact | unchanged | a fact not of the world | yes |
| `relation_gte` | entity | >= 1 | the target's social row toward the character >= threshold (0 if none) | unchanged | an entity not of the world | yes |
| `resource` | key: a label | >= 1 | the character's ledger balance >= threshold | unchanged | -- (label) | yes |
| `location_reachable` | entity | -- | the target is in the character's `connects_to` component | unchanged | an entity not of the world | yes |
| `has_met` | entity | -- | a `rencontre` row of the sorted pair | « il n'a encore jamais rencontré {name} » | an entity not of the world | no |
| `faction_member` | entity: a faction | -- | an active membership, secret included | « il n'appartient pas à {name} » | not a faction of the world | no |
| `skill_rank_gte` | key: base domain or definition id | 1-5 | `held_rank` >= threshold | « sa maîtrise de « {label} » ne suffit pas encore » | an unknown skill; threshold 0 or > 5 | no |
| `quest_completed` | key: quest offer id | -- | a quest of the character from that offer whose agenda is `completed` | « il doit d'abord mener à bien « {title} » » | an offer not of the world | no |

`Verdict.required_label` carries the target's name for `relation_gte` and
the four new forms.

### C-04 — reads and routes
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C

`src/world_engine/quest_reads.py` (reads only):
- `QUEST_STATE_LABELS = {"active": "en cours", "paused": "en cours",
  "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"}`.
- `offer_dict(offer, db)`: `id, giver_entity_id, giver_name, title, summary,
  repeatable, status, eligibility: [req], steps: [{objective, cost, domain,
  requirements: [req]}]`, `req = {type, target_entity_id, target_key,
  threshold}`.
- `editor_choices(world_id, db)`: `givers, characters, locations, factions`
  (`{id, name}`), `facts` (`{id, text}`), `skills` (`{key, label}`: the four
  base domains, then the definitions), `offers` (`{id, title}`),
  `giver_types`.
- `available_offers(character, db)`: the open offers whose
  `acceptance_refusal` is None.
- `journee_payload(character, db)`: `{offers: [{offer_id, title, summary,
  giver_name, steps: [objective]}], quests: [{quest_id, offer_id, title,
  giver_name, summary, state, open, steps: [{order, objective, status,
  blocked: [French reason]}]}]}` -- `blocked` only for the active step. No
  `agenda_id` or `step_id` at any depth.
- `pinned_plan(quest_id, character, db) -> Agenda` (C-05).

`src/world_engine/cockpit/routes/quests.py`:

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/quest-offers` | -- | 200 `[offer_dict]` | 400 no active world |
| `GET /api/quest-offers/choices` | -- | 200 `editor_choices` | 400 |
| `POST /api/quest-offers` | `OfferBody` | 201 `offer_dict` | 422 the writer's message |
| `PUT /api/quest-offers/{id}` | `OfferBody` | 200 `offer_dict` | 404 unknown, 422 |
| `GET /api/quests` | -- | 200 `journee_payload` | 400 not one player |
| `POST /api/quests/accept` | `{offer_id}` | 201 `journee_payload` | 404 unknown offer, 409 refusal |
| `POST /api/quests/{quest_id}/abandon` | -- | 200 `journee_payload` | 404 not his quest, 409 refusal |

`OfferBody = {giver_entity_id, title, summary?, repeatable=false,
status="open", eligibility: [req], steps: [{objective, cost, domain?,
requirements: [req]}]}`.

### C-05 — the pin (O1)
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C
`routes/day.py`: `class PlanDayBody(BaseModel): quest_id: Optional[str] =
None`; `plan_day(batch_id, body: Optional[PlanDayBody] = None, db)`. A
non-empty `body.quest_id` -> `quest_reads.pinned_plan(...)` is the selected
plan and `select_plan` is not called; otherwise unchanged. `pinned_plan`
raises `LookupError` (-> 404) when the quest is not the character's,
`ValueError` (-> 409) when its agenda is not `active`/`paused`. The
selected plan then goes through `_reconcile_and_finalize` unchanged.

### C-07 — the surfaces
Produced by: BRIEF-0108-C   Consumed by: nothing in this lot
- `frontend/src/creation/questRequirements.js`: `REQUIREMENT_FORMS[form] =
  { label, list, column: 'entity'|'key', threshold: bool }`, the keys of
  C-01 in its order, `list` one of `facts, characters, money, locations,
  factions, skills, offers`; `MONEY_KEY = 'monnaie'`.
- Création: tab key `quetes`, label « Quêtes », container `creation-quetes`,
  island key `questOffers` (`QuestOffers.svelte`, `origin: 'new'`),
  primary action « + Nouvelle quête ».
- Journée: `QuestPanel.svelte`; `quests.svelte.js`'s `questState = {offers,
  quests, loading, loadError, busy, actionError, pin}`; `planDay(id,
  questId)` sends `{quest_id}` when `questId` is set.

## Context

The backend is complete (A, B). This brief gives it its two surfaces: « Quêtes » in Création, an island created as such, where Nia writes offers (E1), and a « Quêtes » panel in Journée where the player accepts, follows and abandons them (I1, N1) and pins a day to one (O1). The panel names quests; the plan behind each stays invisible.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `frontend/src/creation/questRequirements.js` (C-07's `REQUIREMENT_FORMS`, `MONEY_KEY`), `questOffers.svelte.js`, `QuestOffers.svelte` (exports `primaryAction`), `QuestRequirementRow.svelte`;
   - registers the island: `registry.js` (`questOffers`, `origin: 'new'`, `createdBy: 'TICKET-0108'`), `tabs.js` (`quetes`, « Quêtes », « + Nouvelle quête »), `mount.js` (`COMPONENTS`), `Creation.svelte` (`#creation-quetes`), `frontend/public/creation.css` (`#creation-quetes { flex: 1; min-height: 0; overflow: auto; }`);
   - adds `quetes` to `page_contract.py`'s `TAB_KEYS`;
   - creates `frontend/src/journee/quests.svelte.js` and `QuestPanel.svelte`; in `Journee.svelte`, renders `<QuestPanel />`, « Cette journée avance » above « Émettre le plan », reloads the panel after a plan or a resolution; `planDay(id, questId)` sends `{quest_id}`;
   - adds QC1-QC3 to `quests.py`;
   - appends the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build`.
4. Commit message: `feat(quests): the Quêtes tab and Journée's quest panel, a day pinned to a quest (BRIEF-0108-c)`.

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index 0cf0709..bb1ebaa 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -309,6 +309,7 @@ input.notes::placeholder { color: var(--muted); }
 #creation-prompts     { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-registre    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
+#creation-quetes      { flex: 1; min-height: 0; overflow: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index e955d6a..137c473 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -249,6 +249,8 @@
 
   <!-- ── Sujets sub-tab -- Svelte island created as one (origin 'new'):
        empty by construction ── -->
+  <!-- ── Quêtes sub-tab -- Svelte island (TICKET-0108): empty by construction ── -->
+  <div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>
   <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
 
   <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
new file mode 100644
index 0000000..21fed19
--- /dev/null
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -0,0 +1,148 @@
+<script>
+  /* TICKET-0108 (BRIEF-0108-C, E1). The « Quêtes » island: the world's
+     quest offers and one offer's editor -- giver, title, summary,
+     « répétable », open/closed, the conditions that decide who it is
+     offered to, and its steps with what each needs. Its CREATION_ISLANDS
+     entry declares origin 'new'. Saving sends the whole offer; an accepted
+     quest keeps its own copy (writes/quests.py). State and requests live in
+     questOffers.svelte.js. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import QuestRequirementRow from './QuestRequirementRow.svelte';
+  import {
+    questOffersState, loadOffers, newDraft, editOffer, saveDraft, blankStep, addRequirement,
+  } from './questOffers.svelte.js';
+  import { STEP_DOMAINS } from './questRequirements.js';
+
+  $effect(() => {
+    questOffersState.draft = null;
+    loadOffers(serverState.worldId);
+  });
+
+  /** The tab's « + Nouvelle quête » (creation_island.py rule 11). */
+  export function primaryAction() {
+    newDraft();
+  }
+
+  let draft = $derived(questOffersState.draft);
+  let choices = $derived(questOffersState.choices);
+
+  function moveStep(index, delta) {
+    const steps = draft.steps;
+    const target = index + delta;
+    if (target < 0 || target >= steps.length) return;
+    [steps[index], steps[target]] = [steps[target], steps[index]];
+  }
+</script>
+
+<div class="quest-offers">
+  <div class="queue-panel quest-list">
+    <div class="panel-head">
+      <h2>Quêtes proposées</h2>
+      <span>{questOffersState.offers.length}</span>
+      <button class="btn-icon" onclick={() => loadOffers(serverState.worldId)} title="Rafraîchir">↻</button>
+    </div>
+    <div class="queue-body">
+      {#if !serverState.worldId}
+        <div class="empty">Aucun monde actif.</div>
+      {:else if questOffersState.loadError}
+        <div class="empty" style="color:var(--red)">Erreur : {questOffersState.loadError}</div>
+      {:else if questOffersState.offers.length === 0}
+        <div class="empty">Aucune quête. « + Nouvelle quête » pour en écrire une.</div>
+      {:else}
+        {#each questOffersState.offers as offer (offer.id)}
+          <div class="row-card" class:selected={draft?.id === offer.id} onclick={() => editOffer(offer)}>
+            <strong>{offer.title}</strong>
+            <span class="badge b-other">{offer.status === 'open' ? 'proposée' : 'fermée'}</span>
+            {#if offer.repeatable}<span class="badge b-other">répétable</span>{/if}
+            <div class="muted">par {offer.giver_name || '—'} · {offer.steps.length} étape(s)</div>
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+
+  {#if draft}
+    <div class="queue-panel quest-editor">
+      <div class="panel-head">
+        <h2>{draft.id ? 'Modifier la quête' : 'Nouvelle quête'}</h2>
+      </div>
+      <div class="queue-body">
+        <label>Titre <input type="text" bind:value={draft.title}></label>
+        <label>Donnée par
+          <select bind:value={draft.giver_entity_id}>
+            <option value="">—</option>
+            {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
+          </select>
+        </label>
+        <label>Résumé <textarea rows="2" bind:value={draft.summary}></textarea></label>
+        <div class="inline">
+          <label><input type="checkbox" bind:checked={draft.repeatable}> Répétable</label>
+          <label>État
+            <select bind:value={draft.status}>
+              <option value="open">proposée</option>
+              <option value="closed">fermée</option>
+            </select>
+          </label>
+        </div>
+
+        <h4>Proposée à qui remplit</h4>
+        {#if draft.eligibility.length === 0}<p class="muted">Tout le monde.</p>{/if}
+        {#each draft.eligibility as req, i (i)}
+          <QuestRequirementRow {req} {choices} onremove={() => draft.eligibility.splice(i, 1)} />
+        {/each}
+        <button onclick={() => addRequirement(draft.eligibility)}>+ condition</button>
+
+        <h4>Étapes</h4>
+        {#each draft.steps as step, i (i)}
+          <div class="quest-step">
+            <div class="inline">
+              <strong>{i + 1}.</strong>
+              <input type="text" style="flex:1" placeholder="Objectif" bind:value={step.objective}>
+              <label>Coût
+                <select bind:value={step.cost}>{#each [1, 2, 3, 4] as c}<option value={c}>{c}</option>{/each}</select>
+              </label>
+              <label>Jet
+                <select bind:value={step.domain}>
+                  <option value="">aucun</option>
+                  {#each STEP_DOMAINS as d}<option value={d}>{d}</option>{/each}
+                </select>
+              </label>
+              <button class="btn-icon" title="Monter" onclick={() => moveStep(i, -1)}>↑</button>
+              <button class="btn-icon" title="Descendre" onclick={() => moveStep(i, 1)}>↓</button>
+              <button class="btn-icon" title="Retirer l'étape" disabled={draft.steps.length === 1}
+                      onclick={() => draft.steps.splice(i, 1)}>✕</button>
+            </div>
+            {#each step.requirements as req, j (j)}
+              <QuestRequirementRow {req} {choices} onremove={() => step.requirements.splice(j, 1)} />
+            {/each}
+            <button onclick={() => addRequirement(step.requirements)}>+ prérequis de l'étape</button>
+          </div>
+        {/each}
+        <button onclick={() => draft.steps.push(blankStep())}>+ étape</button>
+
+        {#if questOffersState.saveError}<div class="r-err">{questOffersState.saveError}</div>{/if}
+        <div style="margin-top:10px">
+          <button class="btn-send" disabled={questOffersState.saving} onclick={() => saveDraft(serverState.worldId)}>
+            {questOffersState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
+          </button>
+        </div>
+      </div>
+    </div>
+  {/if}
+</div>
+
+<style>
+  .quest-offers { display: flex; gap: 12px; align-items: flex-start; }
+  .quest-list { flex: 0 0 300px; }
+  .quest-editor { flex: 1; }
+  .quest-editor label { display: block; margin: 4px 0; }
+  .quest-editor input[type="text"], .quest-editor textarea { width: 100%; box-sizing: border-box; }
+  .inline { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
+  .inline label { display: inline-flex; gap: 4px; align-items: center; }
+  .quest-step { border-left: 2px solid var(--border); padding: 4px 0 6px 8px; margin: 6px 0; }
+  .row-card { cursor: pointer; }
+  .row-card.selected { background: rgba(106, 176, 255, 0.15); }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+  h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
+</style>
diff --git a/frontend/src/creation/QuestRequirementRow.svelte b/frontend/src/creation/QuestRequirementRow.svelte
new file mode 100644
index 0000000..3cab2b1
--- /dev/null
+++ b/frontend/src/creation/QuestRequirementRow.svelte
@@ -0,0 +1,51 @@
+<script>
+  /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
+     its target from the matching picker list, its threshold when the form
+     takes one. `req` is a draft object owned by questOffersState. */
+  import { REQUIREMENT_FORMS, targetOptions } from './questRequirements.js';
+
+  let { req, choices, onremove } = $props();
+
+  let form = $derived(REQUIREMENT_FORMS[req.type]);
+  let options = $derived(targetOptions(req.type, choices));
+
+  function setType(type) {
+    req.type = type;
+    req.target_entity_id = '';
+    req.target_key = '';
+    req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
+  }
+
+  function setTarget(value) {
+    if (form.column === 'entity') req.target_entity_id = value;
+    else req.target_key = value;
+  }
+</script>
+
+<div class="quest-req">
+  <select value={req.type} onchange={(e) => setType(e.target.value)}>
+    {#each Object.entries(REQUIREMENT_FORMS) as [type, f] (type)}
+      <option value={type}>{f.label}</option>
+    {/each}
+  </select>
+  {#if form.list !== 'money'}
+    <select value={form.column === 'entity' ? req.target_entity_id : req.target_key}
+            onchange={(e) => setTarget(e.target.value)}>
+      <option value="">—</option>
+      {#each options as o (o.value)}
+        <option value={o.value}>{o.label}</option>
+      {/each}
+    </select>
+  {/if}
+  {#if form.threshold}
+    <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
+           style="width:70px" value={req.threshold ?? ''}
+           oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
+  {/if}
+  <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
+</div>
+
+<style>
+  .quest-req { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
+  .quest-req select { max-width: 260px; }
+</style>
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 9fc7679..5b50e10 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -42,8 +42,9 @@ import QueueFilters from './QueueFilters.svelte';
 import Queue from './Queue.svelte';
 import QueueBatchBar from './QueueBatchBar.svelte';
 import SubjectWorklist from './SubjectWorklist.svelte';
+import QuestOffers from './QuestOffers.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
new file mode 100644
index 0000000..d6b5ff9
--- /dev/null
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -0,0 +1,92 @@
+/* TICKET-0108 (BRIEF-0108-C). State and requests of the « Quêtes » island
+   (QuestOffers.svelte): the world's offers, the editor's picker lists, and
+   one draft being edited. Saving sends the whole offer (PUT replaces its
+   steps and requirements, writes/quests.py::write_quest_offer). */
+import { api } from './sheetRequest.svelte.js';
+import { blankRequirement, requirementBody } from './questRequirements.js';
+
+export const questOffersState = $state({
+  offers: [],
+  choices: null,
+  loading: false,
+  loadError: '',
+  draft: null, // { id|null, giver_entity_id, title, summary, repeatable, status, eligibility, steps }
+  saving: false,
+  saveError: '',
+});
+
+export function blankStep() {
+  return { objective: '', cost: 1, domain: '', requirements: [] };
+}
+
+export function newDraft() {
+  questOffersState.saveError = '';
+  questOffersState.draft = {
+    id: null, giver_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
+    eligibility: [], steps: [blankStep()],
+  };
+}
+
+export function editOffer(offer) {
+  questOffersState.saveError = '';
+  questOffersState.draft = {
+    id: offer.id, giver_entity_id: offer.giver_entity_id, title: offer.title, summary: offer.summary || '',
+    repeatable: offer.repeatable, status: offer.status,
+    eligibility: offer.eligibility.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
+    steps: offer.steps.map((s) => ({
+      objective: s.objective, cost: s.cost, domain: s.domain || '',
+      requirements: s.requirements.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
+    })),
+  };
+}
+
+export function addRequirement(list) {
+  list.push(blankRequirement());
+}
+
+export async function loadOffers(worldId) {
+  if (!worldId) { questOffersState.offers = []; questOffersState.choices = null; return; }
+  questOffersState.loading = true;
+  questOffersState.loadError = '';
+  try {
+    const [offers, choices] = await Promise.all([api('/api/quest-offers'), api('/api/quest-offers/choices')]);
+    questOffersState.offers = offers;
+    questOffersState.choices = choices;
+  } catch (e) {
+    questOffersState.loadError = e.message;
+  } finally {
+    questOffersState.loading = false;
+  }
+}
+
+function draftBody(draft) {
+  return {
+    giver_entity_id: draft.giver_entity_id, title: draft.title, summary: draft.summary || null,
+    repeatable: draft.repeatable, status: draft.status,
+    eligibility: draft.eligibility.map(requirementBody),
+    steps: draft.steps.map((s) => ({
+      objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
+      requirements: s.requirements.map(requirementBody),
+    })),
+  };
+}
+
+export async function saveDraft(worldId) {
+  const draft = questOffersState.draft;
+  if (!draft) return;
+  questOffersState.saving = true;
+  questOffersState.saveError = '';
+  try {
+    const saved = await api(draft.id ? '/api/quest-offers/' + draft.id : '/api/quest-offers', {
+      method: draft.id ? 'PUT' : 'POST',
+      headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify(draftBody(draft)),
+    });
+    await loadOffers(worldId);
+    editOffer(saved);
+  } catch (e) {
+    questOffersState.saveError = e.message;
+  } finally {
+    questOffersState.saving = false;
+  }
+}
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
new file mode 100644
index 0000000..89a9a9c
--- /dev/null
+++ b/frontend/src/creation/questRequirements.js
@@ -0,0 +1,54 @@
+/* TICKET-0108 (BRIEF-0108-C). The eight requirement forms as the offer
+   editor shows them: a French label, the picker list its target comes
+   from (a key of GET /api/quest-offers/choices, or 'money'), whether that
+   target is an entity (`target_entity_id`) or a key (`target_key`), and
+   whether it takes a threshold. Mirrors `day_plan.REQUIREMENT_TYPES`,
+   `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `THRESHOLD_TYPES` across
+   the network boundary -- kept equal by `quests.py` (QC1), never by hand
+   alone. */
+
+export const REQUIREMENT_FORMS = {
+  knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
+  relation_gte: { label: 'Est apprécié de (≥)', list: 'characters', column: 'entity', threshold: true },
+  resource: { label: 'Possède au moins (monnaie)', list: 'money', column: 'key', threshold: true },
+  location_reachable: { label: 'Peut atteindre le lieu', list: 'locations', column: 'entity', threshold: false },
+  has_met: { label: 'A rencontré', list: 'characters', column: 'entity', threshold: false },
+  faction_member: { label: 'Est membre de', list: 'factions', column: 'entity', threshold: false },
+  skill_rank_gte: { label: 'Compétence au rang (≥)', list: 'skills', column: 'key', threshold: true },
+  quest_completed: { label: 'A accompli la quête', list: 'offers', column: 'key', threshold: false },
+};
+
+// `resource`'s key is a label: one currency per world (the ledger has no
+// currency column), so the editor always sends this one.
+export const MONEY_KEY = 'monnaie';
+
+export const STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure'];
+
+export function blankRequirement() {
+  return { type: 'has_met', target_entity_id: '', target_key: '', threshold: null };
+}
+
+/** The (value, label) options of a form's picker, from the editor's choices. */
+export function targetOptions(form, choices) {
+  if (!choices) return [];
+  switch (REQUIREMENT_FORMS[form]?.list) {
+    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
+    case 'skills': return choices.skills.map((s) => ({ value: s.key, label: s.label }));
+    case 'offers': return choices.offers.map((o) => ({ value: o.id, label: o.title }));
+    case 'characters': return choices.characters.map((c) => ({ value: c.id, label: c.name }));
+    case 'locations': return choices.locations.map((c) => ({ value: c.id, label: c.name }));
+    case 'factions': return choices.factions.map((c) => ({ value: c.id, label: c.name }));
+    default: return [];
+  }
+}
+
+/** The request body of one requirement row: only the columns its form uses. */
+export function requirementBody(req) {
+  const form = REQUIREMENT_FORMS[req.type];
+  return {
+    type: req.type,
+    target_entity_id: form.column === 'entity' ? (req.target_entity_id || null) : null,
+    target_key: form.list === 'money' ? MONEY_KEY : form.column === 'key' ? (req.target_key || null) : null,
+    threshold: form.threshold ? (req.threshold === '' || req.threshold === null ? null : Number(req.threshold)) : null,
+  };
+}
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index 6f23028..82203f2 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -551,4 +551,12 @@ export const CREATION_ISLANDS = Object.freeze({
     origin: 'new',
     createdBy: 'TICKET-0088',
   }),
+  // TICKET-0108 (BRIEF-0108-C, E1): the quest offers the creator authors --
+  // created directly as an island, no legacy predecessor.
+  questOffers: Object.freeze({
+    containerId: 'creation-quetes',
+    component: 'QuestOffers.svelte',
+    origin: 'new',
+    createdBy: 'TICKET-0108',
+  }),
 });
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 840ca1e..0ee6d29 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -49,7 +49,7 @@
    sheet.
 
    `_creationRunWorldSwitchResets` does NOT port: every `onWorldSwitch` in
-   CREATION_TABS (15 static entries + the runtime-tab factory's own
+   CREATION_TABS (16 static entries + the runtime-tab factory's own
    template) is `null` (measured, not assumed — grep `onWorldSwitch:` over
    this file), so its `Object.values(...).forEach` loop is vacuous; its one
    real remaining effect (`creationReturnTo = null`) folds directly into
@@ -340,6 +340,15 @@ export const CREATION_TABS = {
     createPanel: null,
     primaryAction: { label: '+ Nouvel événement', handler: () => triggerPrimaryAction('entitySheet') },
   },
+  quetes: {
+    label: 'Quêtes',
+    archetype: 'bespoke',
+    containers: ['creation-quetes'],
+    loader: null,
+    state: { onTabEnter: null, onWorldSwitch: null },
+    islands: [{ key: 'questOffers', containerId: 'creation-quetes' }],
+    primaryAction: { label: '+ Nouvelle quête', handler: () => triggerPrimaryAction('questOffers') },
+  },
   subjects: {
     label: 'Sujets',
     archetype: 'bespoke',
diff --git a/frontend/src/journee/Journee.svelte b/frontend/src/journee/Journee.svelte
index 5ab58b4..271106c 100644
--- a/frontend/src/journee/Journee.svelte
+++ b/frontend/src/journee/Journee.svelte
@@ -8,13 +8,16 @@
      Once submitted, a declaration is never editable here: no edit control,
      no delete control, and `declared_action` has no update path anywhere
      in the backend (writes/pipeline.py). No agenda data is fetched,
-     rendered or referenced anywhere in this surface (Scope OUT). */
+     rendered or referenced anywhere in this surface (Scope OUT): quests
+     (TICKET-0108) are shown by their own title, steps and `quest_id`. */
   import { serverState } from '../lib/serverState.svelte.js';
   import { navigate } from '../lib/router.js';
   import {
     journeeState, selectedDay, loadDays, selectDay, submitDeclaration, reloadForWorld,
     planDay, resolveDay,
   } from './journee.svelte.js';
+  import QuestPanel from './QuestPanel.svelte';
+  import { questState, loadQuests, openQuests } from './quests.svelte.js';
 
   let { active = false } = $props();
 
@@ -29,7 +32,20 @@
   $effect(() => {
     void serverState.worldId;
     reloadForWorld();
+    questState.pin = '';
+    loadQuests();
   });
+
+  // A plan or a resolution moves a quest's steps: re-read the panel after either.
+  async function plan(id) {
+    await planDay(id, questState.pin);
+    await loadQuests();
+  }
+
+  async function resolve(id) {
+    await resolveDay(id);
+    await loadQuests();
+  }
 </script>
 
 <div class="app-view" id="journee-view" style:display={active ? '' : 'none'}>
@@ -58,6 +74,8 @@
     </div>
   </div>
 
+  <QuestPanel />
+
   <div class="queue-panel" id="journee-list-panel">
     <div class="panel-head">
       <h2>Jours précédents</h2>
@@ -84,11 +102,19 @@
           <p>{day.declared_action}</p>
 
           {#if day.status === 'submitted'}
-            <button disabled={journeeState.planning} onclick={() => planDay(day.id)}>
+            {#if openQuests().length > 0}
+              <label class="quest-pin">Cette journée avance
+                <select bind:value={questState.pin} disabled={journeeState.planning}>
+                  <option value="">— le jeu choisit —</option>
+                  {#each openQuests() as q (q.quest_id)}<option value={q.quest_id}>la quête « {q.title} »</option>{/each}
+                </select>
+              </label>
+            {/if}
+            <button disabled={journeeState.planning} onclick={() => plan(day.id)}>
               {journeeState.planning ? '⟳ Émission du plan…' : 'Émettre le plan'}
             </button>
           {:else if day.status === 'resolving'}
-            <button disabled={journeeState.resolving} onclick={() => resolveDay(day.id)}>
+            <button disabled={journeeState.resolving} onclick={() => resolve(day.id)}>
               {journeeState.resolving ? '⟳ Résolution…' : 'Résoudre la journée'}
             </button>
           {/if}
@@ -208,4 +234,5 @@
   .muted { color: var(--muted); font-size: 12px; }
   .gains-list { list-style: none; padding: 0; margin: 0; }
   .gains-list li { padding: 2px 0; }
+  .quest-pin { display: block; margin: 6px 0; font-size: 13px; }
 </style>
diff --git a/frontend/src/journee/QuestPanel.svelte b/frontend/src/journee/QuestPanel.svelte
new file mode 100644
index 0000000..937cb09
--- /dev/null
+++ b/frontend/src/journee/QuestPanel.svelte
@@ -0,0 +1,76 @@
+<script>
+  /* TICKET-0108 (BRIEF-0108-C). Journée's quests: the offers the player may
+     accept (I1, only those he is eligible for) and his quests -- giver,
+     state, steps, what the active step still needs, « Abandonner » (N1).
+     A quest is shown by its title and objectives; the plan behind it is
+     never named here. */
+  import { questState, loadQuests, acceptOffer, abandonQuest } from './quests.svelte.js';
+
+  let confirming = $state(null);
+
+  function abandon(questId) {
+    if (confirming !== questId) { confirming = questId; return; }
+    confirming = null;
+    abandonQuest(questId);
+  }
+</script>
+
+<div class="queue-panel" id="journee-quest-panel">
+  <div class="panel-head">
+    <h2>Quêtes</h2>
+    <button class="btn-icon" onclick={() => loadQuests()} title="Rafraîchir">↻</button>
+  </div>
+  <div class="queue-body">
+    {#if questState.loadError}<div class="r-err">{questState.loadError}</div>{/if}
+    {#if questState.actionError}<div class="r-err">{questState.actionError}</div>{/if}
+
+    <h4>Proposées</h4>
+    {#if questState.offers.length === 0}
+      <p class="muted">Aucune quête ne vous est proposée pour l'instant.</p>
+    {/if}
+    {#each questState.offers as offer (offer.offer_id)}
+      <div class="row-card">
+        <strong>{offer.title}</strong> <span class="muted">— {offer.giver_name || '—'}</span>
+        {#if offer.summary}<div>{offer.summary}</div>{/if}
+        <ol class="steps">{#each offer.steps as objective}<li>{objective}</li>{/each}</ol>
+        <button disabled={questState.busy !== null} onclick={() => acceptOffer(offer.offer_id)}>
+          {questState.busy === offer.offer_id ? 'Acceptation…' : 'Accepter'}
+        </button>
+      </div>
+    {/each}
+
+    <h4>Mes quêtes</h4>
+    {#if questState.quests.length === 0}<p class="muted">Aucune.</p>{/if}
+    {#each questState.quests as quest (quest.quest_id)}
+      <div class="row-card" class:over={!quest.open}>
+        <strong>{quest.title}</strong>
+        <span class="badge b-other">{quest.state}</span>
+        <span class="muted">— {quest.giver_name || '—'}</span>
+        <ol class="steps">
+          {#each quest.steps as step (step.order)}
+            <li class={'step-' + step.status}>
+              {step.objective}
+              {#if step.status === 'completed'} ✓{/if}
+              {#each step.blocked as reason}<div class="muted">Il manque : {reason}</div>{/each}
+            </li>
+          {/each}
+        </ol>
+        {#if quest.open}
+          <button disabled={questState.busy !== null} onclick={() => abandon(quest.quest_id)}>
+            {confirming === quest.quest_id ? 'Confirmer l’abandon' : 'Abandonner'}
+          </button>
+        {/if}
+      </div>
+    {/each}
+  </div>
+</div>
+
+<style>
+  .r-err { color: var(--red); }
+  .muted { color: var(--muted); font-size: 12px; }
+  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
+  .steps { margin: 4px 0 6px 18px; padding: 0; }
+  .step-active { font-weight: 600; }
+  .step-completed, .step-failed { color: var(--muted); }
+  .over { opacity: 0.7; }
+</style>
diff --git a/frontend/src/journee/journee.svelte.js b/frontend/src/journee/journee.svelte.js
index 8c68ca8..2b58132 100644
--- a/frontend/src/journee/journee.svelte.js
+++ b/frontend/src/journee/journee.svelte.js
@@ -69,12 +69,16 @@ export function selectDay(id) {
   loadDayDetail(id);
 }
 
-export async function planDay(id) {
+/** O1 (TICKET-0108): `questId` pins the day to one open quest -- no plan
+ *  selection; '' or null lets the day choose, as before. */
+export async function planDay(id, questId) {
   journeeState.planning = true;
   journeeState.planError = '';
   journeeState.reconciliation = null;
   try {
-    const result = await api('/api/day/' + id + '/plan', { method: 'POST' });
+    const result = await api('/api/day/' + id + '/plan', questId
+      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ quest_id: questId }) }
+      : { method: 'POST' });
     journeeState.reconciliation = result.reconciliation || null;
     await loadDays();
     await loadDayDetail(id);
diff --git a/frontend/src/journee/quests.svelte.js b/frontend/src/journee/quests.svelte.js
new file mode 100644
index 0000000..f556b66
--- /dev/null
+++ b/frontend/src/journee/quests.svelte.js
@@ -0,0 +1,64 @@
+/* TICKET-0108 (BRIEF-0108-C). State and requests of Journée's quest panel
+   (QuestPanel.svelte) and of the day's pin (O1). GET /api/quests carries
+   the offers the player may accept (I1) and his quests -- named by
+   `quest_id`/`offer_id` only, never by the plan behind them (the plan stays
+   invisible here, as in the rest of Journée). */
+import { api } from '../creation/sheetRequest.svelte.js';
+
+export const questState = $state({
+  offers: [],
+  quests: [],
+  loading: false,
+  loadError: '',
+  busy: null, // the offer_id or quest_id being acted on
+  actionError: '',
+  pin: '', // O1: the quest_id the next planned day advances, '' = the day chooses
+});
+
+export function openQuests() {
+  return questState.quests.filter((q) => q.open);
+}
+
+function apply(payload) {
+  questState.offers = payload.offers;
+  questState.quests = payload.quests;
+  if (questState.pin && !openQuests().some((q) => q.quest_id === questState.pin)) questState.pin = '';
+}
+
+export async function loadQuests() {
+  questState.loading = true;
+  questState.loadError = '';
+  try {
+    apply(await api('/api/quests'));
+  } catch (e) {
+    questState.loadError = e.message;
+    questState.offers = [];
+    questState.quests = [];
+  } finally {
+    questState.loading = false;
+  }
+}
+
+async function act(key, path, body) {
+  questState.busy = key;
+  questState.actionError = '';
+  try {
+    apply(await api(path, {
+      method: 'POST',
+      headers: { 'Content-Type': 'application/json' },
+      body: body ? JSON.stringify(body) : undefined,
+    }));
+  } catch (e) {
+    questState.actionError = e.message;
+  } finally {
+    questState.busy = null;
+  }
+}
+
+export function acceptOffer(offerId) {
+  return act(offerId, '/api/quests/accept', { offer_id: offerId });
+}
+
+export function abandonQuest(questId) {
+  return act(questId, '/api/quests/' + questId + '/abandon', null);
+}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index d5277fa..c7abc80 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18110,6 +18110,28 @@ abandoned plan); otherwise the agenda becomes `abandoned`, nothing deleted.
 **Rejected.** Accepting through a mutation in the review queue: Nia is the
 one accepting; the queue would ask her to approve her own click.
 
+
+## QUESTS ON TWO SURFACES (TICKET-0108) -- CRÉATION AUTHORS THE OFFERS, JOURNÉE TAKES THEM AND PINS A DAY (BRIEF-0108-c, no schema change)
+
+**E1.** « Quêtes » is a Création tab, an island created as such (origin
+`new`): the offers listed, one offer edited whole -- giver, title, summary,
+« répétable », open or closed, the conditions that decide who it is
+offered to, the steps (objective, cost, roll) with their own
+requirements. The editor's eight forms mirror `day_plan`'s vocabulary and
+its three shape groups across the network boundary (`questRequirements.js`,
+kept equal by `quests.py` QC1).
+
+**I1, N1, O1.** Journée shows a « Quêtes » panel: the offers the player is
+eligible for, with « Accepter », and his quests -- state, steps, what the
+active step still needs, « Abandonner » (asked twice). Above « Émettre le
+plan », « Cette journée avance » pins the day to an open quest, or lets the
+day choose. The panel names quests and offers only; the plan behind a
+quest stays invisible, as in the rest of Journée.
+
+**Rejected.** Offers authored in Journée: Journée is the player's surface;
+the creator's tools live in Création. The pin as a separate button per
+quest: one choice per day, made where the day is planned.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/page_contract.py b/tooling/verify/checks/page_contract.py
index 42edf59..fb088d6 100644
--- a/tooling/verify/checks/page_contract.py
+++ b/tooling/verify/checks/page_contract.py
@@ -45,7 +45,8 @@ REGISTRE_SVELTE = CREATION_SRC / "Registre.svelte"
 
 TAB_KEYS = [
     "npc", "pj", "lieux", "factions", "objets",
-    "competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "subjects", "queue", "prompts",
+    "competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "quetes", "subjects",
+    "queue", "prompts",
 ]
 
 
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index b5a6167..a547dcf 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -67,6 +67,21 @@ QB4 -- what the player sees (fixture and static). `journee_payload` and the
    `quest_reads.pinned_plan(` in the branch that does not call
    `select_plan(`.
 
+QC1 -- the editor's mirror (BRIEF-0108-C, static). `frontend/src/creation/
+   questRequirements.js`'s `REQUIREMENT_FORMS` has exactly the keys of
+   `day_plan.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
+   `ENTITY_TARGET_TYPES`, with `column: 'key'` `KEY_TARGET_TYPES`, with
+   `threshold: true` `THRESHOLD_TYPES`.
+QC2 -- the « Quêtes » tab (static). `tabs.js`'s `quetes` entry mounts the
+   `questOffers` island in `creation-quetes` and routes « + Nouvelle quête »
+   through `triggerPrimaryAction('questOffers')`; `QuestOffers.svelte`
+   exports `primaryAction`; `questOffers.svelte.js` creates with `POST
+   /api/quest-offers` and saves with `PUT /api/quest-offers/`.
+QC3 -- Journée (static). `QuestPanel.svelte` and `quests.svelte.js` contain
+   neither `agenda_id` nor `step_id`; `Journee.svelte` renders
+   `<QuestPanel` and plans with `planDay(id, questState.pin)`;
+   `journee.svelte.js` sends `quest_id` in the plan request's body.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -757,6 +772,70 @@ def check_qb(engine) -> None:
         check_qb4(session, ids)
 
 
+# --- QC --------------------------------------------------------------------------
+
+FRONTEND = ROOT / "frontend" / "src"
+
+
+def _read(rel: str) -> str:
+    path = FRONTEND / rel
+    if not path.is_file():
+        fail(f"QC: {rel} not found")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+def check_qc1() -> None:
+    from world_engine import day_plan
+
+    text = _read("creation/questRequirements.js")
+    forms = dict(re.findall(r"^\s+(\w+): \{ label: '[^']*', list: '\w+', (column: '\w+', threshold: \w+) \},$",
+                            text, re.M))
+    if not forms:
+        fail("QC1: REQUIREMENT_FORMS holds zero forms")
+        return
+    if list(forms) != list(day_plan.REQUIREMENT_TYPES):
+        fail(f"QC1: REQUIREMENT_FORMS keys {list(forms)} != REQUIREMENT_TYPES")
+    groups = {
+        "column: 'entity'": tuple(day_plan.ENTITY_TARGET_TYPES), "column: 'key'": tuple(day_plan.KEY_TARGET_TYPES),
+        "threshold: true": tuple(day_plan.THRESHOLD_TYPES),
+    }
+    for marker, expected in groups.items():
+        found = tuple(form for form, spec in forms.items() if marker in spec)
+        if found != expected:
+            fail(f"QC1: the forms with {marker} are {found}, expected {expected}")
+
+
+def check_qc2() -> None:
+    tabs = _read("creation/tabs.js")
+    entry = re.search(r"\n  quetes: \{(.*?)\n  \},", tabs, re.S)
+    body = entry.group(1) if entry else ""
+    for needle in ("{ key: 'questOffers', containerId: 'creation-quetes' }",
+                   "triggerPrimaryAction('questOffers')"):
+        if needle not in body:
+            fail(f"QC2: tabs.js's quetes entry lacks {needle}")
+    if "export function primaryAction" not in _read("creation/QuestOffers.svelte"):
+        fail("QC2: QuestOffers.svelte exports no primaryAction")
+    state = _read("creation/questOffers.svelte.js")
+    for needle in ("'/api/quest-offers/' + draft.id", "draft.id ? 'PUT' : 'POST'"):
+        if needle not in state:
+            fail(f"QC2: questOffers.svelte.js lacks {needle}")
+
+
+def check_qc3() -> None:
+    for rel in ("journee/QuestPanel.svelte", "journee/quests.svelte.js"):
+        text = _read(rel)
+        for token in ("agenda_id", "step_id"):
+            if token in text:
+                fail(f"QC3: {rel} names {token}")
+    journee = _read("journee/Journee.svelte")
+    for needle in ("<QuestPanel", "planDay(id, questState.pin)"):
+        if needle not in journee:
+            fail(f"QC3: Journee.svelte lacks {needle}")
+    if "JSON.stringify({ quest_id: questId })" not in _read("journee/journee.svelte.js"):
+        fail("QC3: journee.svelte.js does not send quest_id in the plan body")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_qa1()
@@ -765,6 +844,9 @@ def main() -> int:
     create_db_and_tables()
     check_qa3(engine)
     check_qb(engine)
+    check_qc1()
+    check_qc2()
+    check_qc3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -774,7 +856,8 @@ def main() -> int:
           "and judges what the target feels, encounters, memberships, ranks and completed quests; "
           "an offer is validated whole and saved whole, accepted only when eligible as a paused "
           "plan with its steps, once unless repeatable, abandoned unless a step awaits review, "
-          "pinned to a day, and shown to the player without an agenda or step id")
+          "pinned to a day, and shown to the player without an agenda or step id; the editor "
+          "mirrors the vocabulary, the « Quêtes » tab and Journée's panel are wired")
     return 0
 
 
````

## Scope OUT

- Any backend file: every route this brief calls exists (B).
- Showing ineligible offers greyed (I2, rejected) or offers on contact (I3, deferred to TICKET-0069).
- A quest in Play (`legacy.html` stays sealed).
- Costs, rewards and « déclarer accomplie » in the panel (TICKET-0109).
- Rank labels in the threshold field of « Compétence au rang » (it shows 1-5).
- Every later ticket of the series.

## Invariants to defend

**Play is sealed:** no change to `legacy.html` or the Play surface. **The player never sees the agenda:** `QuestPanel.svelte` and `quests.svelte.js` name neither `agenda_id` nor `step_id` (QC3); `Journee.svelte` keeps day_mutations' R7. **One mount mechanism:** the island mounts through `mount.js` only (creation_island rules 6, 12, 13). **The built frontend matches its sources:** rebuilt in this commit.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT cases below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `frontend/src/creation/registry.js` or `mount.js` because another island was registered last: add `questOffers` after it by hand, with the diff's fields.

REPORT-ONLY:
- Timing of the corpus run.
- `npm ci` engine warnings (`EBADENGINE`); the pre-existing Svelte warning on `<option value="">`.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quests.py` -> `PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, and judges what the target feels, encounters, memberships, ranks and completed quests; an offer is validated whole and saved whole, accepted only when eligible as a paused plan with its steps, once unless repeatable, abandoned unless a step awaits review, pinned to a day, and shown to the player without an agenda or step id; the editor mirrors the vocabulary, the « Quêtes » tab and Journée's panel are wired`.
- `creation_island.py`, `page_contract.py`, `creation_container_sizing.py`, `creation_return_nav.py`, `observation_surface.py`, `day_mutations.py`, `module_budget.py`, `frontend_build_fresh.py`, `decisions_index.py`, `pipeline_state.py` -> `PASS`.
- Mutation tests, each red then reverted: in `questRequirements.js`, `  has_met: { label: 'A rencontré', list: 'characters', column: 'entity', threshold: false },` -> the same line with `column: 'key'` -> `QC1`; in `Journee.svelte`, `    await planDay(id, questState.pin);` -> `    await planDay(id);` -> `QC3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 141/141.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `QUESTS ON TWO SURFACES (TICKET-0108) -- CRÉATION AUTHORS THE OFFERS, JOURNÉE TAKES THEM AND PINS A DAY (BRIEF-0108-c, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
