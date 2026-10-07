# BRIEF 0109-D — "Quest terms on both surfaces: the editor weighs them, Journée settles from the recap"

Lot: LOT-0109-quest-terms.md (authoritative on conflict)
Depends on: BRIEF-0109-C

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0109-C's commit). The facts carried below quote `main`'s line
numbers, as the lot does; where A, B or C moved a line, the anchor here gives where it now is.

- `src/world_engine/cockpit/routes/quests.py:230` -> `@router.post("/api/quests/{quest_id}/settle")`.
- `src/world_engine/quest_reads.py:160` -> `"settleable": quest.settled_at is None and agenda.status in ("active", "paused", "completed"),`.
- `frontend/src/creation/QuestOffers.svelte:121` -> `<button onclick={() => draft.steps.push(blankStep())}>+ étape</button>`.
- `frontend/src/creation/questOffers.svelte.js:62` -> `function draftBody(draft) {`.
- `frontend/src/journee/quests.svelte.js:62` -> `export function abandonQuest(questId) {`.
- `frontend/src/journee/QuestPanel.svelte:58` -> `{#if quest.open}`.
- `tooling/verify/checks/quest_rewards.py:940` -> `    check_rc(engine)`.
- No `frontend/src/creation/questTerms.js`, `QuestTermRow.svelte` or `frontend/src/journee/SettlementRecap.svelte` exists.

## Facts carried

### R-13 — the 0108 writers and views [M]
Opened: `src/world_engine/writes/quests.py:88-139` (`write_quest_offer`,
full-replace `:118-120`), `:172-198` (`accept_quest`);
`src/world_engine/quest_reads.py:57-71` (`offer_dict`), `:85-104`
(`editor_choices`), `:115-127` (`_steps_view`), `:129-147`
(`player_quests`), `:149-158` (`journee_payload`);
`src/world_engine/cockpit/routes/quests.py:52-60` (`OfferBody`), `:75`
(the one caller of `write_quest_offer` in `src/`).

### R-18 — the surfaces [M]
Opened: `frontend/src/creation/ItemsPanel.svelte:1-40` (read-only);
`frontend/src/creation/Sheet.svelte:818-825` (the panel on a character
only); `frontend/src/creation/sheetRequest.svelte.js:30-35` (`api()`
throws `Error(detail)`); `frontend/src/creation/QuestOffers.svelte:121`,
`questOffers.svelte.js:62-73`; `frontend/src/journee/QuestPanel.svelte:
45-66`, `quests.svelte.js:58-64`;
`tooling/verify/checks/creation_island.py` (unchanged: no new island).

### R-19 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40/1000 per `src/`
module), `tooling/verify/checks/function_length.py:29` (80).
Consequence: four new modules (`holdings.py`, `writes/items.py`,
`writes/quest_terms.py`, `writes/quest_settlement.py`) and three reads
(`quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`); none
over budget.

## Contracts

### C-03 — the currencies (family contract)
Produced by: BRIEF-0109-B   Consumed by: C, D
Written before its members; re-read after the last (`skill`).

`QUEST_TERM_DIRECTIONS = ("cost", "reward")`; `QUEST_TERM_CURRENCIES =
("money", "item", "relation", "fact", "skill")`; `COUNTED_CURRENCIES =
("money", "item", "relation")`; `PERSONAL_CURRENCIES = ("relation", "fact",
"skill")`; `FACT_REWARD_LEVELS` = `KNOWLEDGE_LEVELS` minus `unaware`,
sorted. The counterparty is the term's own entity (an active character or
faction of the world), else the offer's giver.

| currency | target | amount | counterparty | `clean_term` refuses | unit (default) |
|---|---|---|---|---|---|
| `money` | -- | >= 1 | character or faction | amount < 1 | 1 a coin |
| `item` | `item_id` (an item of the world) | >= 1 | character or faction | not an item; amount < 1 | the item's `value` a piece |
| `relation` | -- | 1-99 | a character | amount < 1 or > 99; a faction | 1 a point |
| `fact` | `fact_id` (a fact of the world); reward `level` in `FACT_REWARD_LEVELS` or None | -- | a character | a fact elsewhere; level `unaware`; a faction | 5 |
| `skill` | `skill_key`: cost a skill definition of the world; reward a definition or a base domain | -- | a character | a cost on a base domain; an unknown skill; a faction | 20 |

Every term also refuses a direction or a currency outside the vocabulary
and a counterparty that is not an active character or faction of the world.

### C-04 — the indicative unit
Produced by: BRIEF-0109-B   Consumed by: C, D
`quest_value.DEFAULT_RATES = {rate_money: 1, rate_relation: 1, rate_fact:
5, rate_skill: 20, band_low_pct: 100, band_high_pct: 150}`;
`world_rates(db, world_id)` (a NULL column or no row -> the default);
`term_value(db, term, rates)` (C-03's last column); `offer_value(db,
world_id, terms) -> OfferValue(cost, reward, ratio_pct, band_low_pct,
band_high_pct, verdict)`, `ratio_pct = round(reward * 100 / cost)`; verdict
case table (b-3); `value_dict` adds `verdict_label` (« sans coût »,
« maigre », « équilibrée », « généreuse »).
`writes.upsert_quest_economy(db, *, world_id, values)`: refuses an unknown
column, a value that is not a whole number >= 0, and an effective band
whose low end is above its high end, before any write; None returns a rate
to its default.
`quest_wording.term_line(db, term, giver_id)`: one French line per term
(« Donner 2 × Fourrure de loup à Garde », « La relation de Garde envers
vous monte de 5 », ...).

### C-06 — the measured context (G1)
Produced by: BRIEF-0109-C   Consumed by: D
`quest_settlement_view.settlement_context(db, quest) -> {quest_id, title,
state, settled, steps: [{order, objective, status, outcome, blocked}],
terms: [{direction, line, note}], value, days: [{day_number,
declared_action, rewritten, steps: [{objective, band}]}], pending_reviews,
refusals, can_settle}`. `note` only on a skill reward: « +N point(s) en
« label » », « apprend « label » (Inexpérimenté) », or « déjà Maître en
« label » : rien ». No model call; no `agenda_id`/`step_id`.

### C-07 — routes
Produced by: B and C   Consumed by: D

| route | body | success | refusal |
|---|---|---|---|
| `POST /api/quest-offers`, `PUT /api/quest-offers/{id}` | `OfferBody` + `terms: [TermBody] | null` (null keeps) | `offer_dict` + `terms: [term + line]`, `value` | 422 |
| `POST /api/quest-offers/value` | `{terms: [TermBody]}` | `value_dict` | -- |
| `GET /api/quest-economy` | -- | `{stored, effective, defaults}` | 400 |
| `PUT /api/quest-economy` | the six columns | same as GET | 422 |
| `GET /api/quest-offers/choices` | -- | + `items: [{id, name, value}]`, `fact_levels`, `rates` | 400 |
| `GET /api/quests/{quest_id}/settlement` | -- | C-06 | 404 not his |
| `POST /api/quests/{quest_id}/settle` | -- | `journee_payload` | 404, 409 refusal |

`journee_payload`: each offer gains `terms: [line]`; each quest gains
`terms: [line]`, `settled`, `settleable` (`settled_at` NULL and agenda
`active`/`paused`/`completed`); each step gains `outcome`.

### C-08 — the surfaces
Produced by: BRIEF-0109-D   Consumed by: nothing in this lot
- `frontend/src/creation/questTerms.js`: `TERM_DIRECTIONS`,
  `CURRENCY_FORMS[c] = {label, list, counted, personal}` in C-03's order.
- Création › Quêtes: « Coûts » / « Récompenses » (`QuestTermRow.svelte`),
  the live value and verdict, ⚖ the world's rates.
- Journée: offer and quest term lines; « Déclarer accomplie » under
  `settleable`; `SettlementRecap.svelte` with « Confirmer : quête
  accomplie », disabled while `can_settle` is false.
- Sheets: « Objets » on a character, a faction, a location (what it holds)
  and « Détenu par » on an item; each row's quantity editable, 0 removes.

## Case tables carried (lot, gate output (b))

**b-3 — the value verdict**: cost 0 -> `free`; `ratio_pct < band_low` ->
`meagre`; `ratio_pct > band_high` -> `generous`; otherwise `balanced`.

## Context

The backend is complete (A, B, C). This brief puts it on the two surfaces: in Création › Quêtes, « Coûts » and « Récompenses » rows, the value and its verdict updated as Nia types, and ⚖ the world's rates; in Journée, each offer's and quest's terms, « Déclarer accomplie » on a settleable quest, and the recap it opens, whose « Confirmer » stays disabled while a cost cannot be paid.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `frontend/src/creation/questTerms.js` (`TERM_DIRECTIONS`, `CURRENCY_FORMS` in C-03's order with `counted` and `personal`, `blankTerm`, `termTargetOptions`, `termBody` -- C-08) and `QuestTermRow.svelte`;
   - `questOffers.svelte.js`: the draft's `terms`, `refreshValue` (`POST /api/quest-offers/value`), `loadEconomy`, `saveEconomy`; `QuestOffers.svelte`: « Coûts » / « Récompenses », the value and verdict, the ⚖ rates panel;
   - `frontend/src/journee/quests.svelte.js`: `settling`, `settlement`, `openSettlement`, `settleQuest`; creates `SettlementRecap.svelte`; `QuestPanel.svelte`: term lines, the « accomplie — à régler » / « réglée » badge, « Déclarer accomplie » under `quest.settleable`;
   - adds RD1-RD3 to `quest_rewards.py`;
   - appends the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm ci`, `npm run build`.
4. Commit message: `feat(quests): terms in the offer editor and the Journée recap, « déclarer accomplie » from it (BRIEF-0109-d)`.

````diff
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 21fed19..4171852 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -8,9 +8,12 @@
      questOffers.svelte.js. */
   import { serverState } from '../lib/serverState.svelte.js';
   import QuestRequirementRow from './QuestRequirementRow.svelte';
+  import QuestTermRow from './QuestTermRow.svelte';
   import {
     questOffersState, loadOffers, newDraft, editOffer, saveDraft, blankStep, addRequirement,
+    addTerm, refreshValue, saveEconomy,
   } from './questOffers.svelte.js';
+  import { TERM_DIRECTIONS } from './questTerms.js';
   import { STEP_DOMAINS } from './questRequirements.js';
 
   $effect(() => {
@@ -25,6 +28,20 @@
 
   let draft = $derived(questOffersState.draft);
   let choices = $derived(questOffersState.choices);
+  let value = $derived(questOffersState.value);
+
+  // TICKET-0109 (E1): the world's rates; '' = the code's default.
+  const RATE_LABELS = {
+    rate_money: 'Pièce', rate_relation: 'Point de relation', rate_fact: 'Fait', rate_skill: 'Compétence',
+    band_low_pct: 'Bande basse (%)', band_high_pct: 'Bande haute (%)',
+  };
+  let showEconomy = $state(false);
+  let economyDraft = $state({});
+  function openEconomy() {
+    const stored = questOffersState.economy?.stored || {};
+    economyDraft = Object.fromEntries(Object.keys(RATE_LABELS).map((k) => [k, stored[k] ?? '']));
+    showEconomy = !showEconomy;
+  }
 
   function moveStep(index, delta) {
     const steps = draft.steps;
@@ -39,9 +56,24 @@
     <div class="panel-head">
       <h2>Quêtes proposées</h2>
       <span>{questOffersState.offers.length}</span>
+      <button class="btn-icon" onclick={() => openEconomy()} title="Unité indicative du monde">⚖</button>
       <button class="btn-icon" onclick={() => loadOffers(serverState.worldId)} title="Rafraîchir">↻</button>
     </div>
     <div class="queue-body">
+      {#if showEconomy}
+        <div class="economy">
+          <strong>Unité indicative</strong>
+          <p class="muted">Ce que vaut chaque terme, en unités ; vide = défaut. Un objet vaut sa propre valeur.</p>
+          {#each Object.entries(RATE_LABELS) as [key, label] (key)}
+            <label>{label}
+              <input type="number" min="0" style="width:70px" bind:value={economyDraft[key]}
+                     placeholder={String(questOffersState.economy?.defaults?.[key] ?? '')}>
+            </label>
+          {/each}
+          {#if questOffersState.economyError}<div class="r-err">{questOffersState.economyError}</div>{/if}
+          <button onclick={() => saveEconomy(economyDraft)}>Enregistrer les taux</button>
+        </div>
+      {/if}
       {#if !serverState.worldId}
         <div class="empty">Aucun monde actif.</div>
       {:else if questOffersState.loadError}
@@ -52,6 +84,7 @@
         {#each questOffersState.offers as offer (offer.id)}
           <div class="row-card" class:selected={draft?.id === offer.id} onclick={() => editOffer(offer)}>
             <strong>{offer.title}</strong>
+            {#if offer.value && offer.value.verdict !== 'free'}<span class="badge b-other">{offer.value.verdict_label}</span>{/if}
             <span class="badge b-other">{offer.status === 'open' ? 'proposée' : 'fermée'}</span>
             {#if offer.repeatable}<span class="badge b-other">répétable</span>{/if}
             <div class="muted">par {offer.giver_name || '—'} · {offer.steps.length} étape(s)</div>
@@ -120,6 +153,25 @@
         {/each}
         <button onclick={() => draft.steps.push(blankStep())}>+ étape</button>
 
+        {#each Object.entries(TERM_DIRECTIONS) as [direction, label] (direction)}
+          <h4>{direction === 'cost' ? 'Coûts (payés en déclarant la quête accomplie)' : 'Récompenses'}</h4>
+          {#each draft.terms as term, k (k)}
+            {#if term.direction === direction}
+              <QuestTermRow {term} {choices} onchange={() => refreshValue()}
+                            onremove={() => draft.terms.splice(k, 1)} />
+            {/if}
+          {/each}
+          <button onclick={() => addTerm(direction)}>+ {label.toLowerCase()}</button>
+        {/each}
+
+        {#if value}
+          <div class="value" class:warn={value.verdict === 'meagre' || value.verdict === 'generous'}>
+            Valeur indicative : coût {value.cost}, récompense {value.reward}
+            {#if value.ratio_pct !== null} — {value.ratio_pct} % (bande {value.band_low_pct}-{value.band_high_pct} %){/if}
+            — <strong>{value.verdict_label}</strong>
+          </div>
+        {/if}
+
         {#if questOffersState.saveError}<div class="r-err">{questOffersState.saveError}</div>{/if}
         <div style="margin-top:10px">
           <button class="btn-send" disabled={questOffersState.saving} onclick={() => saveDraft(serverState.worldId)}>
@@ -145,4 +197,8 @@
   .muted { color: var(--muted); font-size: 12px; }
   .r-err { color: var(--red); }
   h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
+  .economy { border: 1px solid var(--border); padding: 6px 8px; margin-bottom: 8px; }
+  .economy label { display: inline-flex; gap: 4px; align-items: center; margin: 2px 8px 2px 0; }
+  .value { margin-top: 10px; font-size: 13px; }
+  .value.warn { color: var(--red); }
 </style>
diff --git a/frontend/src/creation/QuestTermRow.svelte b/frontend/src/creation/QuestTermRow.svelte
new file mode 100644
index 0000000..77542d9
--- /dev/null
+++ b/frontend/src/creation/QuestTermRow.svelte
@@ -0,0 +1,67 @@
+<script>
+  /* TICKET-0109 (BRIEF-0109-D). One cost or reward of a quest offer: its
+     currency, its target, its amount when the currency counts one, the
+     knowledge level of a fact reward, and its counterparty (empty = the
+     giver; a relation, a fact or a skill needs a character there). `term`
+     is a draft object owned by questOffersState; `onchange` re-reads the
+     offer's indicative value. */
+  import { CURRENCY_FORMS, termTargetOptions } from './questTerms.js';
+
+  let { term, choices, onremove, onchange } = $props();
+
+  let form = $derived(CURRENCY_FORMS[term.currency]);
+  let options = $derived(termTargetOptions(term.currency, choices));
+  let targetKey = $derived(term.currency === 'item' ? 'item_id' : term.currency === 'fact' ? 'fact_id' : 'skill_key');
+
+  function set(field, value) {
+    term[field] = value;
+    onchange();
+  }
+
+  function setCurrency(currency) {
+    term.currency = currency;
+    term.item_id = '';
+    term.fact_id = '';
+    term.skill_key = '';
+    term.level = '';
+    term.amount = CURRENCY_FORMS[currency].counted ? 1 : null;
+    onchange();
+  }
+</script>
+
+<div class="quest-term">
+  <select value={term.currency} onchange={(e) => setCurrency(e.target.value)}>
+    {#each Object.entries(CURRENCY_FORMS) as [currency, f] (currency)}
+      <option value={currency}>{f.label}</option>
+    {/each}
+  </select>
+  {#if form.list}
+    <select value={term[targetKey]} onchange={(e) => set(targetKey, e.target.value)}>
+      <option value="">—</option>
+      {#each options as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
+    </select>
+  {/if}
+  {#if form.counted}
+    <input type="number" min="1" style="width:70px" value={term.amount ?? ''}
+           oninput={(e) => set('amount', e.target.value === '' ? null : Number(e.target.value))}>
+  {/if}
+  {#if term.currency === 'fact' && term.direction === 'reward'}
+    <select value={term.level} onchange={(e) => set('level', e.target.value)}>
+      <option value="">knows</option>
+      {#each (choices?.fact_levels || []).filter((l) => l !== 'knows') as l}<option value={l}>{l}</option>{/each}
+    </select>
+  {/if}
+  <select value={term.counterparty_entity_id} title={form.personal ? 'Un personnage' : 'Le donneur, ou un autre'}
+          onchange={(e) => set('counterparty_entity_id', e.target.value)}>
+    <option value="">le donneur</option>
+    {#each (form.personal ? choices?.characters : choices?.givers) || [] as g (g.id)}
+      <option value={g.id}>{g.name}</option>
+    {/each}
+  </select>
+  <button class="btn-icon" title="Retirer" onclick={() => { onremove(); onchange(); }}>✕</button>
+</div>
+
+<style>
+  .quest-term { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
+  .quest-term select { max-width: 240px; }
+</style>
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index d6b5ff9..7d95376 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -1,9 +1,12 @@
 /* TICKET-0108 (BRIEF-0108-C). State and requests of the « Quêtes » island
    (QuestOffers.svelte): the world's offers, the editor's picker lists, and
    one draft being edited. Saving sends the whole offer (PUT replaces its
-   steps and requirements, writes/quests.py::write_quest_offer). */
+   steps and requirements, writes/quests.py::write_quest_offer). Since
+   TICKET-0109 (BRIEF-0109-D): its costs and rewards, their live indicative
+   value (POST /api/quest-offers/value), and the world's rates. */
 import { api } from './sheetRequest.svelte.js';
 import { blankRequirement, requirementBody } from './questRequirements.js';
+import { blankTerm, termBody } from './questTerms.js';
 
 export const questOffersState = $state({
   offers: [],
@@ -13,6 +16,9 @@ export const questOffersState = $state({
   draft: null, // { id|null, giver_entity_id, title, summary, repeatable, status, eligibility, steps }
   saving: false,
   saveError: '',
+  value: null, // the draft's indicative value (cost, reward, ratio_pct, verdict_label)
+  economy: null, // { stored, effective, defaults }
+  economyError: '',
 });
 
 export function blankStep() {
@@ -23,8 +29,9 @@ export function newDraft() {
   questOffersState.saveError = '';
   questOffersState.draft = {
     id: null, giver_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
-    eligibility: [], steps: [blankStep()],
+    eligibility: [], steps: [blankStep()], terms: [],
   };
+  refreshValue();
 }
 
 export function editOffer(offer) {
@@ -37,7 +44,55 @@ export function editOffer(offer) {
       objective: s.objective, cost: s.cost, domain: s.domain || '',
       requirements: s.requirements.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
     })),
+    terms: (offer.terms || []).map((t) => ({
+      direction: t.direction, currency: t.currency, counterparty_entity_id: t.counterparty_entity_id || '',
+      item_id: t.item_id || '', fact_id: t.fact_id || '', skill_key: t.skill_key || '', amount: t.amount,
+      level: t.level || '',
+    })),
   };
+  questOffersState.value = offer.value || null;
+}
+
+export function addTerm(direction) {
+  questOffersState.draft.terms.push(blankTerm(direction));
+  refreshValue();
+}
+
+/** The draft's indicative value, recomputed by the server (C1). */
+export async function refreshValue() {
+  const draft = questOffersState.draft;
+  if (!draft) return;
+  try {
+    questOffersState.value = await api('/api/quest-offers/value', {
+      method: 'POST', headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify({ terms: draft.terms.map(termBody) }),
+    });
+  } catch (_e) {
+    questOffersState.value = null;
+  }
+}
+
+export async function loadEconomy() {
+  try {
+    questOffersState.economy = await api('/api/quest-economy');
+    questOffersState.economyError = '';
+  } catch (e) {
+    questOffersState.economyError = e.message;
+  }
+}
+
+/** E1: `stored` values, '' = the code's default. */
+export async function saveEconomy(stored) {
+  const body = Object.fromEntries(Object.entries(stored).map(([k, v]) => [k, v === '' || v === null ? null : Number(v)]));
+  try {
+    questOffersState.economy = await api('/api/quest-economy', {
+      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
+    });
+    questOffersState.economyError = '';
+    await refreshValue();
+  } catch (e) {
+    questOffersState.economyError = e.message;
+  }
 }
 
 export function addRequirement(list) {
@@ -52,6 +107,7 @@ export async function loadOffers(worldId) {
     const [offers, choices] = await Promise.all([api('/api/quest-offers'), api('/api/quest-offers/choices')]);
     questOffersState.offers = offers;
     questOffersState.choices = choices;
+    await loadEconomy();
   } catch (e) {
     questOffersState.loadError = e.message;
   } finally {
@@ -68,6 +124,7 @@ function draftBody(draft) {
       objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
       requirements: s.requirements.map(requirementBody),
     })),
+    terms: draft.terms.map(termBody),
   };
 }
 
diff --git a/frontend/src/creation/questTerms.js b/frontend/src/creation/questTerms.js
new file mode 100644
index 0000000..7226570
--- /dev/null
+++ b/frontend/src/creation/questTerms.js
@@ -0,0 +1,48 @@
+/* TICKET-0109 (BRIEF-0109-D). The five currencies of a quest term as the
+   offer editor shows them: a French label, the picker its target comes from
+   (a key of GET /api/quest-offers/choices, or none), whether it counts an
+   amount, and whether its counterparty must be a character. Mirrors
+   `models.QUEST_TERM_CURRENCIES`, `writes.quest_terms.COUNTED_CURRENCIES`
+   and `PERSONAL_CURRENCIES` across the network boundary -- kept equal by
+   `quest_rewards.py` (RD1). */
+
+export const TERM_DIRECTIONS = { cost: 'Coût', reward: 'Récompense' };
+
+export const CURRENCY_FORMS = {
+  money: { label: 'Monnaie', list: null, counted: true, personal: false },
+  item: { label: 'Objet', list: 'items', counted: true, personal: false },
+  relation: { label: 'Relation', list: null, counted: true, personal: true },
+  fact: { label: 'Fait', list: 'facts', counted: false, personal: true },
+  skill: { label: 'Compétence', list: 'skills', counted: false, personal: true },
+};
+
+export function blankTerm(direction) {
+  return { direction, currency: 'money', counterparty_entity_id: '', item_id: '', fact_id: '',
+           skill_key: '', amount: 1, level: '' };
+}
+
+/** The (value, label) options of a currency's target picker. */
+export function termTargetOptions(currency, choices) {
+  if (!choices) return [];
+  switch (CURRENCY_FORMS[currency]?.list) {
+    case 'items': return choices.items.map((i) => ({ value: i.id, label: `${i.name} (valeur ${i.value})` }));
+    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
+    case 'skills': return choices.skills.map((s) => ({ value: s.key, label: s.label }));
+    default: return [];
+  }
+}
+
+/** The request body of one term: only the columns its currency uses. */
+export function termBody(term) {
+  const form = CURRENCY_FORMS[term.currency];
+  return {
+    direction: term.direction,
+    currency: term.currency,
+    counterparty_entity_id: term.counterparty_entity_id || null,
+    item_id: term.currency === 'item' ? (term.item_id || null) : null,
+    fact_id: term.currency === 'fact' ? (term.fact_id || null) : null,
+    skill_key: term.currency === 'skill' ? (term.skill_key || null) : null,
+    amount: form.counted ? (term.amount === '' || term.amount === null ? null : Number(term.amount)) : null,
+    level: term.currency === 'fact' && term.direction === 'reward' ? (term.level || null) : null,
+  };
+}
diff --git a/frontend/src/journee/QuestPanel.svelte b/frontend/src/journee/QuestPanel.svelte
index 937cb09..87f23dd 100644
--- a/frontend/src/journee/QuestPanel.svelte
+++ b/frontend/src/journee/QuestPanel.svelte
@@ -3,8 +3,11 @@
      accept (I1, only those he is eligible for) and his quests -- giver,
      state, steps, what the active step still needs, « Abandonner » (N1).
      A quest is shown by its title and objectives; the plan behind it is
-     never named here. */
-  import { questState, loadQuests, acceptOffer, abandonQuest } from './quests.svelte.js';
+     never named here. TICKET-0109 (BRIEF-0109-D): each offer and quest
+     lists its costs and rewards; « Déclarer accomplie » opens the measured
+     recap (SettlementRecap) and settles from it (D1). */
+  import { questState, loadQuests, acceptOffer, abandonQuest, openSettlement } from './quests.svelte.js';
+  import SettlementRecap from './SettlementRecap.svelte';
 
   let confirming = $state(null);
 
@@ -33,6 +36,7 @@
         <strong>{offer.title}</strong> <span class="muted">— {offer.giver_name || '—'}</span>
         {#if offer.summary}<div>{offer.summary}</div>{/if}
         <ol class="steps">{#each offer.steps as objective}<li>{objective}</li>{/each}</ol>
+        {#if offer.terms?.length}<ul class="terms">{#each offer.terms as line}<li>{line}</li>{/each}</ul>{/if}
         <button disabled={questState.busy !== null} onclick={() => acceptOffer(offer.offer_id)}>
           {questState.busy === offer.offer_id ? 'Acceptation…' : 'Accepter'}
         </button>
@@ -44,7 +48,7 @@
     {#each questState.quests as quest (quest.quest_id)}
       <div class="row-card" class:over={!quest.open}>
         <strong>{quest.title}</strong>
-        <span class="badge b-other">{quest.state}</span>
+        <span class="badge b-other">{quest.settled ? 'réglée' : quest.state === 'accomplie' ? 'accomplie — à régler' : quest.state}</span>
         <span class="muted">— {quest.giver_name || '—'}</span>
         <ol class="steps">
           {#each quest.steps as step (step.order)}
@@ -55,11 +59,18 @@
             </li>
           {/each}
         </ol>
+        {#if quest.terms?.length}<ul class="terms">{#each quest.terms as line}<li>{line}</li>{/each}</ul>{/if}
+        {#if quest.settleable}
+          <button disabled={questState.busy !== null} onclick={() => openSettlement(quest.quest_id)}>
+            {questState.settling === quest.quest_id ? 'Fermer' : 'Déclarer accomplie'}
+          </button>
+        {/if}
         {#if quest.open}
           <button disabled={questState.busy !== null} onclick={() => abandon(quest.quest_id)}>
             {confirming === quest.quest_id ? 'Confirmer l’abandon' : 'Abandonner'}
           </button>
         {/if}
+        {#if questState.settling === quest.quest_id}<SettlementRecap questId={quest.quest_id} />{/if}
       </div>
     {/each}
   </div>
@@ -73,4 +84,5 @@
   .step-active { font-weight: 600; }
   .step-completed, .step-failed { color: var(--muted); }
   .over { opacity: 0.7; }
+  .terms { margin: 2px 0 6px 18px; padding: 0; font-size: 12px; }
 </style>
diff --git a/frontend/src/journee/SettlementRecap.svelte b/frontend/src/journee/SettlementRecap.svelte
new file mode 100644
index 0000000..15fbcb8
--- /dev/null
+++ b/frontend/src/journee/SettlementRecap.svelte
@@ -0,0 +1,65 @@
+<script>
+  /* TICKET-0109 (BRIEF-0109-D, D1/G1). What « déclarer accomplie » shows
+     before Nia decides: the measured context of one quest (its steps and
+     their outcomes, the days that advanced it, the step changes still
+     awaiting review, its terms and their value) and why it cannot be
+     settled now, if it cannot. Nothing here is a verdict: she decides. The
+     quest is named by its quest_id only. */
+  import { questState, settleQuest } from './quests.svelte.js';
+
+  let { questId } = $props();
+
+  let ctx = $derived(questState.settlement);
+</script>
+
+<div class="recap">
+  {#if questState.settlementError}
+    <div class="r-err">{questState.settlementError}</div>
+  {:else if !ctx}
+    <div class="empty"><span class="spin">⟳</span></div>
+  {:else}
+    <h5>Étapes</h5>
+    <ol>
+      {#each ctx.steps as step (step.order)}
+        <li>{step.objective} — {step.status}{#if step.outcome} <span class="muted">({step.outcome})</span>{/if}</li>
+      {/each}
+    </ol>
+
+    <h5>Journées qui l'ont avancée</h5>
+    {#if ctx.days.length === 0}<p class="muted">Aucune.</p>{/if}
+    {#each ctx.days as day (day.day_number)}
+      <div class="day">
+        <strong>Jour {day.day_number}</strong> — {day.declared_action}
+        {#if day.rewritten && day.rewritten !== day.declared_action}<div class="muted">lu : {day.rewritten}</div>{/if}
+        {#each day.steps as s}<div class="muted">{s.objective} : {s.band}</div>{/each}
+      </div>
+    {/each}
+    {#if ctx.pending_reviews > 0}
+      <p class="r-err">{ctx.pending_reviews} changement(s) d'étape attendent encore la revue.</p>
+    {/if}
+
+    <h5>Ce qui sera appliqué</h5>
+    {#if ctx.terms.length === 0}<p class="muted">Aucun coût ni récompense.</p>{/if}
+    <ul>
+      {#each ctx.terms as t}
+        <li><span class="badge b-other">{t.direction === 'cost' ? 'coût' : 'récompense'}</span> {t.line}
+          {#if t.note}<span class="muted"> — {t.note}</span>{/if}</li>
+      {/each}
+    </ul>
+    <p class="muted">Valeur indicative : coût {ctx.value.cost}, récompense {ctx.value.reward} — {ctx.value.verdict_label}</p>
+
+    {#each ctx.refusals as reason}<div class="r-err">Impossible : {reason}</div>{/each}
+    <button class="btn-send" disabled={!ctx.can_settle || questState.busy !== null} onclick={() => settleQuest(questId)}>
+      {questState.busy === questId ? 'Règlement…' : 'Confirmer : quête accomplie'}
+    </button>
+  {/if}
+</div>
+
+<style>
+  .recap { border-left: 2px solid var(--border); margin: 6px 0; padding: 4px 0 4px 8px; }
+  h5 { margin: 8px 0 2px; font-size: 12px; color: var(--muted); }
+  ol, ul { margin: 2px 0 4px 18px; padding: 0; }
+  .day { margin: 2px 0 4px; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+</style>
diff --git a/frontend/src/journee/quests.svelte.js b/frontend/src/journee/quests.svelte.js
index f556b66..5ad3a14 100644
--- a/frontend/src/journee/quests.svelte.js
+++ b/frontend/src/journee/quests.svelte.js
@@ -13,6 +13,10 @@ export const questState = $state({
   busy: null, // the offer_id or quest_id being acted on
   actionError: '',
   pin: '', // O1: the quest_id the next planned day advances, '' = the day chooses
+  // TICKET-0109 (D1, G1): the recap shown before « déclarer accomplie ».
+  settling: null, // quest_id whose recap is open
+  settlement: null, // GET /api/quests/{id}/settlement
+  settlementError: '',
 });
 
 export function openQuests() {
@@ -62,3 +66,22 @@ export function acceptOffer(offerId) {
 export function abandonQuest(questId) {
   return act(questId, '/api/quests/' + questId + '/abandon', null);
 }
+
+/** G1: open (or close) the measured recap of one quest. */
+export async function openSettlement(questId) {
+  if (questState.settling === questId) { questState.settling = null; return; }
+  questState.settling = questId;
+  questState.settlement = null;
+  questState.settlementError = '';
+  try {
+    questState.settlement = await api('/api/quests/' + questId + '/settlement');
+  } catch (e) {
+    questState.settlementError = e.message;
+  }
+}
+
+/** D1: apply the quest's terms at once; the server refuses an unpayable cost. */
+export async function settleQuest(questId) {
+  await act(questId, '/api/quests/' + questId + '/settle', null);
+  if (!questState.actionError) questState.settling = null;
+}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index f9781ca..379deb1 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18213,6 +18213,28 @@ awaiting review, and the refusals. No model is asked.
 exists. A mutation in the review queue (D2 of the series): Nia would
 approve her own click.
 
+
+## QUEST TERMS ON BOTH SURFACES (TICKET-0109) -- THE EDITOR WEIGHS THEM LIVE, JOURNÉE SETTLES FROM THE RECAP (BRIEF-0109-d, no schema change)
+
+**Création › Quêtes.** The offer editor gains « Coûts » and « Récompenses »:
+one row per term (currency, target, amount, a fact reward's level,
+counterparty -- « le donneur » by default, a character for a relation, a
+fact or a skill). Its total in the indicative unit is recomputed by the
+server at every change (`POST /api/quest-offers/value`) and shown with the
+band's verdict; the list marks each offer « maigre », « équilibrée » or
+« généreuse ». ⚖ opens the world's rates, each empty field at the code's
+default. The five currencies mirror the server's across the network
+boundary (`questTerms.js`, kept equal by `quest_rewards.py` RD1).
+
+**Journée › Quêtes.** Offers and quests list their terms. A quest not yet
+settled, open or completed by its steps, offers « Déclarer accomplie »: it
+opens the measured recap and its « Confirmer » button, disabled while a
+cost cannot be paid. A completed quest still to settle reads « accomplie —
+à régler »; a settled one, « réglée ». No agenda or step id is named.
+
+**Rejected.** Computing the value in the browser: a second implementation
+of the rates to keep in step; the server already has them.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/quest_rewards.py b/tooling/verify/checks/quest_rewards.py
index ca22710..ef2c4a0 100644
--- a/tooling/verify/checks/quest_rewards.py
+++ b/tooling/verify/checks/quest_rewards.py
@@ -87,6 +87,20 @@ RC3 -- what Nia sees (fixture and static). `settlement_context` gives the
    409 on a refusal; `journee_payload` marks the quest `settled`, not
    `settleable`, with its term lines.
 
+RD1 -- the editor's mirror (BRIEF-0109-D, static). `frontend/src/creation/
+   questTerms.js`'s `CURRENCY_FORMS` has exactly the keys of
+   `QUEST_TERM_CURRENCIES`, in order; its forms with `counted: true` are
+   `COUNTED_CURRENCIES`, with `personal: true` `PERSONAL_CURRENCIES`;
+   `TERM_DIRECTIONS` has the keys of `QUEST_TERM_DIRECTIONS`.
+RD2 -- the editor (static). `questOffers.svelte.js` sends `terms:
+   draft.terms.map(termBody)`, reads `/api/quest-offers/value` and
+   `/api/quest-economy`; `QuestOffers.svelte` renders `<QuestTermRow`.
+RD3 -- Journée (static). `quests.svelte.js` reads `'/settlement'` and posts
+   `'/settle'`; `QuestPanel.svelte` shows « Déclarer accomplie » under
+   `quest.settleable` and renders `<SettlementRecap`; the recap's confirm
+   button is `disabled={!ctx.can_settle`; none of the three names
+   `agenda_id` or `step_id`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -929,6 +943,63 @@ def _keys(value) -> set:
     return set()
 
 
+# --- RD --------------------------------------------------------------------------
+
+FRONTEND = ROOT / "frontend" / "src"
+
+
+def _read(rel: str) -> str:
+    path = FRONTEND / rel
+    if not path.is_file():
+        fail(f"RD: {rel} not found")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+def check_rd1() -> None:
+    import re
+
+    from world_engine.models import QUEST_TERM_CURRENCIES, QUEST_TERM_DIRECTIONS
+    from world_engine.writes.quest_terms import COUNTED_CURRENCIES, PERSONAL_CURRENCIES
+
+    text = _read("creation/questTerms.js")
+    forms = dict(re.findall(r"^  (\w+): \{ label: '[^']*', list: [^,]+, (counted: \w+, personal: \w+) \},$", text, re.M))
+    if list(forms) != list(QUEST_TERM_CURRENCIES):
+        fail(f"RD1: CURRENCY_FORMS keys {list(forms)} != {QUEST_TERM_CURRENCIES}")
+    for marker, expected in (("counted: true", COUNTED_CURRENCIES), ("personal: true", PERSONAL_CURRENCIES)):
+        found = tuple(c for c, spec in forms.items() if marker in spec)
+        if found != tuple(expected):
+            fail(f"RD1: the currencies with {marker} are {found}, expected {tuple(expected)}")
+    directions = re.search(r"TERM_DIRECTIONS = \{([^}]*)\}", text)
+    keys = re.findall(r"(\w+):", directions.group(1)) if directions else []
+    if tuple(keys) != tuple(QUEST_TERM_DIRECTIONS):
+        fail(f"RD1: TERM_DIRECTIONS keys {keys}")
+
+
+def check_rd2() -> None:
+    state = _read("creation/questOffers.svelte.js")
+    for needle in ("terms: draft.terms.map(termBody)", "'/api/quest-offers/value'", "'/api/quest-economy'"):
+        if needle not in state:
+            fail(f"RD2: questOffers.svelte.js lacks {needle}")
+    if "<QuestTermRow" not in _read("creation/QuestOffers.svelte"):
+        fail("RD2: QuestOffers.svelte renders no QuestTermRow")
+
+
+def check_rd3() -> None:
+    state, panel, recap = (_read("journee/quests.svelte.js"), _read("journee/QuestPanel.svelte"),
+                           _read("journee/SettlementRecap.svelte"))
+    for needle, text, where in (("'/settlement'", state, "quests.svelte.js"), ("'/settle'", state, "quests.svelte.js"),
+                                ("{#if quest.settleable}", panel, "QuestPanel.svelte"),
+                                ("<SettlementRecap", panel, "QuestPanel.svelte"),
+                                ("disabled={!ctx.can_settle", recap, "SettlementRecap.svelte")):
+        if needle not in text:
+            fail(f"RD3: {where} lacks {needle}")
+    for name, text in (("quests.svelte.js", state), ("QuestPanel.svelte", panel), ("SettlementRecap.svelte", recap)):
+        for token in ("agenda_id", "step_id"):
+            if token in text:
+                fail(f"RD3: {name} names {token}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_ra1()
@@ -938,6 +1009,9 @@ def main() -> int:
     check_ra3(engine)
     check_rb(engine)
     check_rc(engine)
+    check_rd1()
+    check_rd2()
+    check_rd3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -947,7 +1021,8 @@ def main() -> int:
           "keeps every holding, its history, and zones empty; an offer's terms are validated whole, "
           "copied to the quest that accepts it, and valued in the world's indicative unit against "
           "its band; « déclarer accomplie » shows the measured context, refuses an unpayable cost "
-          "with no write, and applies every cost then every reward at once")
+          "with no write, and applies every cost then every reward at once; the editor mirrors the "
+          "currencies and Journée settles from the recap")
     return 0
 
 
````

## Scope OUT

- Any backend file: every route this brief calls exists (B, C).
- A « Déclarer échouée » button (D-fail2); a way to force an unpayable settlement (D2).
- A model's opinion in the recap (G1).
- Terms in Play (`legacy.html` stays sealed).
- A new Création island or tab (the « Quêtes » island exists since 0108).
- Every later ticket of the series.

## Invariants to defend

**Play is sealed:** no change to `legacy.html` or the Play surface. **The player never sees the agenda:** `QuestPanel.svelte`, `SettlementRecap.svelte` and `quests.svelte.js` name neither `agenda_id` nor `step_id`. **One mount mechanism:** no new island; `QuestTermRow` and `SettlementRecap` are children. **The built frontend matches its sources:** rebuilt in this commit. **Python judges:** the editor's verdict and the recap's « can settle » come from the server; the frontend only mirrors the currencies (RD1).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quest_rewards.py` -> `PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, migrates owners and places to holdings from v2.17 only, drops equipped, and one writer keeps every holding, its history, and zones empty; an offer's terms are validated whole, copied to the quest that accepts it, and valued in the world's indicative unit against its band; « déclarer accomplie » shows the measured context, refuses an unpayable cost with no write, and applies every cost then every reward at once; the editor mirrors the currencies and Journée settles from the recap`.
- `quests.py`, `creation_island.py`, `page_contract.py`, `day_mutations.py`, `module_budget.py`, `frontend_build_fresh.py`, `pipeline_state.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted: in `questTerms.js`, `  fact: { label: 'Fait', list: 'facts', counted: false, personal: true },` -> the same line with `personal: false` -> `RD1`; in `SettlementRecap.svelte`, `disabled={!ctx.can_settle || questState.busy !== null}` -> `disabled={questState.busy !== null}` -> `RD3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 142/142.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `QUEST TERMS ON BOTH SURFACES (TICKET-0109) -- THE EDITOR WEIGHS THEM LIVE, JOURNÉE SETTLES FROM THE RECAP (BRIEF-0109-d, no schema change)` — in the diff. No schema change, no CLAUDE.md change.
