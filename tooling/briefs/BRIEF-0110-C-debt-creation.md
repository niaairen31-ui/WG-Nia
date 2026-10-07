# BRIEF 0110-C — "The « Dettes » tab lists and writes the world's debts; a faction offer names its contact"

Lot: LOT-0110-debts-services.md (authoritative on conflict)
Depends on: BRIEF-0110-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0110-B's commit).

- `frontend/src/creation/tabs.js:52` -> `CREATION_TABS (16 static entries + the runtime-tab factory's own`
- `frontend/src/creation/tabs.js:343` -> `quetes: {`
- `frontend/src/creation/Creation.svelte:253` -> `<div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>`
- `frontend/src/creation/mount.js:47` -> `const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers };`
- `frontend/src/creation/registry.js:560` -> `createdBy: 'TICKET-0108',`
- `frontend/public/creation.css:312` -> `#creation-quetes      { flex: 1; min-height: 0; overflow: auto; }`
- `tooling/verify/checks/page_contract.py:48` -> `"competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "quetes", "subjects",`
- `frontend/src/creation/questOffers.svelte.js:118` -> `function draftBody(draft) {`
- `frontend/src/creation/QuestOffers.svelte:107` -> `<label>Donnée par`
- `src/world_engine/cockpit/routes/debts.py:81` -> `@router.get("/api/debts")` (B)
- `src/world_engine/quest_reads.py:131` -> `"members": faction_members(world_id, db),` (B)
- `tooling/verify/checks/debts.py:938` -> `check_db(engine)` (B)
- No `frontend/src/creation/Debts.svelte` exists.

## Facts carried

### R-13 — the surfaces [M]
Opened: `frontend/src/journee/Journee.svelte:1-238` (one view: declare
`:53`, `<QuestPanel />` `:77`, the days); `frontend/src/journee/
quests.svelte.js:84-87` (`settleQuest`); `frontend/src/journee/
SettlementRecap.svelte:52-54`; `frontend/src/creation/QuestTermRow.svelte:
10` (props `term, choices, onremove, onchange`);
`frontend/src/creation/questTerms.js:11-17`, `:36-48`;
`frontend/src/creation/tabs.js:52` (« 16 static entries »), `:343-351`
(the `quetes` entry); `frontend/src/creation/Creation.svelte:253`;
`frontend/src/creation/mount.js:47`; `frontend/src/creation/registry.js:
554-562` (the `questOffers` entry, `origin: 'new'`); `frontend/public/creation.css:287-297` (`.creation-sub-tab-bar`,
`.creation-sub-tab`, loaded for the whole shell by `frontend/index.html:7`),
`:312`; `tooling/verify/checks/page_contract.py:46-50` (`TAB_KEYS`);
`src/world_engine/cockpit/legacy.html:463-468` (Play's sub-tab bar: the
look W-a asks for), `:1759-1781` (« Mes savoirs » reads stored rows only);
`src/world_engine/cockpit/app.py:58`, `:142` (router registration);
`src/world_engine/cockpit/routes/day.py:126` (`_resolve_player_character`).
Consequence: Journée's sub-tabs reuse the shell's sub-tab classes; « Mes
savoirs » is not ported (W-a).

## Contracts

### C-03 — the owed currencies and the debt writer (family contract)
Produced by: BRIEF-0110-B   Consumed by: B (C-04, C-05), C, D
Written before its members; re-read after the last (`skill`).

`DebtTermSpec(currency, item_id=None, fact_id=None, skill_key=None,
amount=None)`. The receiver of a fact or a skill is the creditor, his
contact for a faction (`receiver_of`).

| currency | target | amount | `clean_debt_term` refuses | owed line (`debt_term_line`) | in the fact | value |
|---|---|---|---|---|---|---|
| `money` | -- | >= 1 | amount < 1 | « N pièce(s) » | « N pièce(s) » | N x rate_money |
| `item` | `item_id`, an item of the world | >= 1 | not an item; amount < 1 | « N × name » | « N × [token] » | N x item.value |
| `fact` | `fact_id`, a fact of the world | -- | a fact elsewhere | « le savoir « text » » | « le savoir « text » » | rate_fact |
| `skill` | `skill_key`, a skill definition of the world | -- | a base domain; an unknown skill | « l'enseignement de « label » » | same | rate_skill |

`clean_debt_term` also refuses a currency outside `DEBT_CURRENCIES`.
- `prepare_debt(db, *, world_id, debtor_id, creditor_id, contact_id,
  origin, origin_quest_id=None, reason=None, is_secret=False, terms) ->
  PreparedDebt`: case table (b-1), nothing written. `reason` is stripped,
  empty -> None.
- `write_debt(db, prepared, *, changed_by) -> Debt`: the fact (free,
  `information`, aspect `dette`, `default_level` `unaware`, text
  `debt_fact_text(..., state="open")`), its participants (debtor, creditor,
  contact if any, in that order), the row `open`, its terms in order
  (`term_order` from 1), the parties' knowledge and the faction default
  (b-5). `create_debt(db, *, changed_by, **fields)` is the two in a row.
- `debt_fact_text(db, *, debtor_id, creditor_id, contact_id, terms, reason,
  state, note=None)`: with `D`, `C`, `K` the parties' tokens, `via` = «
  (par l'entremise de K) » or nothing, `tail` = « : owed » + « — reason »
  if any, `owed` = the terms' fact phrases joined by « , » or « une
  faveur »: `open` -> « D doit à C{via}{tail}. »; `settled` -> « D a réglé
  sa dette envers C{via}{tail}. »; `forgiven` -> « C a fait grâce à D de sa
  dette{via}{tail}. » + « (note) » if any.
- `is_active_member(db, character_id, faction_id) -> bool` (R-11).
- Constants: `DEBT_FACT_LEVEL = "knows"`, `DEBT_FACT_ASPECT = "dette"`,
  `DEBT_SOURCE = "dette"`, `DEBT_LEDGER_SOURCE = "debt"`,
  `STALE_RELATION_SETTING = {"fact": "debt_fact_relation", "skill":
  "debt_skill_relation"}`.

### C-06 — what the surfaces read
Produced by: BRIEF-0110-B   Consumed by: C, D
- `debt_reads.debt_dict(debt, db)` keys, always all present: `id,
  debtor_id, debtor_name, creditor_id, creditor_name, contact_id,
  contact_name, origin, origin_label` (« service », « création », « quête
  « title » »)`, reason, is_secret, status, status_label` (« due »,
  « réglée », « remise »)`, created_at, closed_at, closed_note, terms`
  (`[{currency, item_id, fact_id, skill_key, amount, line}]`)`, value` (the
  sum of `term_value` at the world's rates). No agenda or step id.
- `world_debts(world_id, db)`: every debt, open first, then most recent.
- `player_debts(character, db)`: `{owes, owed}` -- the debts he is debtor
  of, creditor of -- each with `refusals` (C-04, empty when closed) and
  `repayable`.
- `quest_reads.offer_dict` gains `contact_entity_id`, `contact_name`;
  `editor_choices` gains `members: {faction_id: [{id, name}]}` (active
  character members, by name).
- `quest_settlement_view.settlement_context` gains `credit: {possible,
  refusals, debts: [{creditor_id, creditor_name, is_faction, lines,
  contact_id, members}]}` (`contact_id` from `credit_contact(…, {})`).

### C-07 — routes
Produced by: BRIEF-0110-B   Consumed by: C, D

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/debts` | -- | `[debt_dict]` | 400 no world |
| `POST /api/debts` | `{debtor_entity_id, creditor_entity_id, contact_entity_id, reason, is_secret, terms: [{currency, item_id, fact_id, skill_key, amount}]}` | 201 `debt_dict` (origin `creator`) | 422 |
| `POST /api/debts/{id}/repay` | -- | `debt_dict` | 404 other world, 409 refusal |
| `POST /api/debts/{id}/forgive` | `{note}` | `debt_dict` | 404, 409 closed |
| `GET /api/journee/debts` | -- | `player_debts` | 400 |
| `POST /api/services` | `{provider_entity_id, on_behalf_of_id, terms: [TermBody], owed: [owed term], reason, is_secret}` | 201 `player_debts` | 422 |
| `POST /api/quests/{id}/settle-on-credit` | `{is_secret, contacts: {faction_id: member_id}}` | `journee_payload` | 404 not his, 409 refusal |
| `POST`/`PUT /api/quest-offers…` | `OfferBody` + `contact_entity_id` | `offer_dict` | 422 |

`routes/debts.py` is registered after `routes/quests.py` in `app.py`.

### C-08 — Création
Produced by: BRIEF-0110-C   Consumed by: D (`DebtTermRow`, `debtTerms.js`)
- `frontend/src/creation/debtTerms.js`: `DEBT_CURRENCY_FORMS` in
  `DEBT_CURRENCIES`' order (`money` and `item` counted), `blankDebtTerm`,
  `debtTargetOptions` (skills: definitions only), `debtTermBody`,
  `owedFromService(terms)` (the money and item rewards, as owed terms).
- `DebtTermRow.svelte` (props `term, choices, onremove`).
- « Dettes » tab (`dettes`, container `creation-dettes`, island `debts`,
  origin `new`, « + Nouvelle dette ») -> `Debts.svelte` /
  `debts.svelte.js`: the list (C-06), « Rembourser », « Remettre » with a
  note, the editor (debtor, creditor, a faction's contact among
  `choices.members`, motive, « Transaction secrète », owed terms). No PUT,
  no DELETE.
- `QuestOffers.svelte`: « Contact de la faction » when the giver has
  members; changing the giver clears it; `questOffers.svelte.js` loads
  and sends `contact_entity_id`.

## Context

The routes exist (B). Création gains « Dettes »: every debt of the world, a debt written by hand, « Rembourser » and « Remettre ». The offer editor lets a faction giver name its contact (X1).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
and the built `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `frontend/src/creation/debtTerms.js`, `DebtTermRow.svelte`, `Debts.svelte`, `debts.svelte.js` (C-08);
   - registers the `dettes` tab: `tabs.js`, `Creation.svelte`, `mount.js`, `registry.js` (origin `new`), `frontend/public/creation.css`, `page_contract.py`'s `TAB_KEYS`;
   - `questOffers.svelte.js` and `QuestOffers.svelte`: the offer's contact;
   - adds DC1-DC3 to `debts.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/public/creation.css
   - frontend/src/creation/Creation.svelte
   - frontend/src/creation/DebtTermRow.svelte
   - frontend/src/creation/Debts.svelte
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/debtTerms.js
   - frontend/src/creation/debts.svelte.js
   - frontend/src/creation/mount.js
   - frontend/src/creation/questOffers.svelte.js
   - frontend/src/creation/registry.js
   - frontend/src/creation/tabs.js
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/debts.py
   - tooling/verify/checks/page_contract.py
2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(debts): the Dettes tab lists and writes the world's debts; a faction offer names its contact (BRIEF-0110-c)`.

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index bb1ebaa..30e1fe4 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -310,6 +310,7 @@ input.notes::placeholder { color: var(--muted); }
 #creation-registre    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-quetes      { flex: 1; min-height: 0; overflow: auto; }
+#creation-dettes      { flex: 1; min-height: 0; overflow: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index 137c473..b974531 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -251,6 +251,8 @@
        empty by construction ── -->
   <!-- ── Quêtes sub-tab -- Svelte island (TICKET-0108): empty by construction ── -->
   <div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>
+  <!-- ── Dettes sub-tab -- Svelte island (TICKET-0110): empty by construction ── -->
+  <div id="creation-dettes" style:display={containerVisible('creation-dettes') ? '' : 'none'}></div>
   <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
 
   <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
diff --git a/frontend/src/creation/DebtTermRow.svelte b/frontend/src/creation/DebtTermRow.svelte
new file mode 100644
index 0000000..f6523b7
--- /dev/null
+++ b/frontend/src/creation/DebtTermRow.svelte
@@ -0,0 +1,44 @@
+<script>
+  /* TICKET-0110 (BRIEF-0110-C). One owed term of a debt: its currency, its
+     target, its amount when the currency counts one. `term` is a draft
+     object its owner keeps (Création › Dettes, Journée's service form). */
+  import { DEBT_CURRENCY_FORMS, debtTargetOptions } from './debtTerms.js';
+
+  let { term, choices, onremove } = $props();
+
+  let form = $derived(DEBT_CURRENCY_FORMS[term.currency]);
+  let options = $derived(debtTargetOptions(term.currency, choices));
+  let targetKey = $derived(term.currency === 'item' ? 'item_id' : term.currency === 'fact' ? 'fact_id' : 'skill_key');
+
+  function setCurrency(currency) {
+    term.currency = currency;
+    term.item_id = '';
+    term.fact_id = '';
+    term.skill_key = '';
+    term.amount = DEBT_CURRENCY_FORMS[currency].counted ? 1 : null;
+  }
+</script>
+
+<div class="debt-term">
+  <select value={term.currency} onchange={(e) => setCurrency(e.target.value)}>
+    {#each Object.entries(DEBT_CURRENCY_FORMS) as [currency, f] (currency)}
+      <option value={currency}>{f.label}</option>
+    {/each}
+  </select>
+  {#if form.list}
+    <select value={term[targetKey]} onchange={(e) => (term[targetKey] = e.target.value)}>
+      <option value="">—</option>
+      {#each options as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
+    </select>
+  {/if}
+  {#if form.counted}
+    <input type="number" min="1" style="width:70px" value={term.amount ?? ''}
+           oninput={(e) => (term.amount = e.target.value === '' ? null : Number(e.target.value))}>
+  {/if}
+  <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
+</div>
+
+<style>
+  .debt-term { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
+  .debt-term select { max-width: 240px; }
+</style>
diff --git a/frontend/src/creation/Debts.svelte b/frontend/src/creation/Debts.svelte
new file mode 100644
index 0000000..1af9e4b
--- /dev/null
+++ b/frontend/src/creation/Debts.svelte
@@ -0,0 +1,135 @@
+<script>
+  /* TICKET-0110 (BRIEF-0110-C, J2, C2, X1). The « Dettes » island: every
+     debt of the world -- who owes whom, why, what, its indicative value,
+     its state -- and a debt written by hand (any debtor, a character or a
+     faction creditor, a faction's contact, a motive, secrecy, what is
+     owed). An open debt can be repaid (all at once, D1) or forgiven with a
+     note; a debt is never edited nor deleted. Its CREATION_ISLANDS entry
+     declares origin 'new'. State and requests live in debts.svelte.js. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import DebtTermRow from './DebtTermRow.svelte';
+  import { blankDebtTerm } from './debtTerms.js';
+  import {
+    debtsState, loadDebts, newDebtDraft, saveDebtDraft, repayDebt, forgiveDebt,
+  } from './debts.svelte.js';
+
+  $effect(() => {
+    debtsState.draft = null;
+    loadDebts(serverState.worldId);
+  });
+
+  /** The tab's « + Nouvelle dette » (creation_island.py rule 11). */
+  export function primaryAction() {
+    newDebtDraft();
+  }
+
+  let draft = $derived(debtsState.draft);
+  let choices = $derived(debtsState.choices);
+  let factionIds = $derived(new Set((choices?.factions || []).map((f) => f.id)));
+  let creditorIsFaction = $derived(draft ? factionIds.has(draft.creditor_entity_id) : false);
+  let members = $derived(draft && creditorIsFaction ? (choices?.members?.[draft.creditor_entity_id] || []) : []);
+  let notes = $state({});
+
+  function setCreditor(id) {
+    draft.creditor_entity_id = id;
+    draft.contact_entity_id = '';
+  }
+</script>
+
+<div class="debts">
+  <div class="queue-panel debt-list">
+    <div class="panel-head">
+      <h2>Dettes du monde</h2>
+      <span>{debtsState.debts.length}</span>
+      <button class="btn-icon" onclick={() => loadDebts(serverState.worldId)} title="Rafraîchir">↻</button>
+    </div>
+    <div class="queue-body">
+      {#if !serverState.worldId}
+        <div class="empty">Aucun monde actif.</div>
+      {:else if debtsState.loadError}
+        <div class="empty" style="color:var(--red)">Erreur : {debtsState.loadError}</div>
+      {:else if debtsState.debts.length === 0}
+        <div class="empty">Aucune dette. « + Nouvelle dette » pour en écrire une.</div>
+      {:else}
+        {#each debtsState.debts as debt (debt.id)}
+          <div class="row-card" class:closed={debt.status !== 'open'}>
+            <strong>{debt.debtor_name} → {debt.creditor_name}</strong>
+            {#if debt.contact_name}<span class="muted">(par {debt.contact_name})</span>{/if}
+            <span class="badge b-other">{debt.status_label}</span>
+            {#if debt.is_secret}<span class="badge b-other">secrète</span>{/if}
+            <div class="muted">{debt.origin_label}{debt.reason ? ' — ' + debt.reason : ''} · valeur {debt.value}</div>
+            <ul>
+              {#each debt.terms as t, i (i)}<li>{t.line}</li>{/each}
+              {#if debt.terms.length === 0}<li>une faveur</li>{/if}
+            </ul>
+            {#if debt.closed_note}<div class="muted">Note : {debt.closed_note}</div>{/if}
+            {#if debt.status === 'open'}
+              <div class="inline">
+                <button onclick={() => repayDebt(serverState.worldId, debt.id)}>Rembourser</button>
+                <input type="text" placeholder="Note (facultative)" bind:value={notes[debt.id]}>
+                <button onclick={() => forgiveDebt(serverState.worldId, debt.id, notes[debt.id])}>Remettre</button>
+              </div>
+            {/if}
+            {#if debtsState.actionError?.id === debt.id}<div class="r-err">{debtsState.actionError.message}</div>{/if}
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+
+  {#if draft}
+    <div class="queue-panel debt-editor">
+      <div class="panel-head"><h2>Nouvelle dette</h2></div>
+      <div class="queue-body">
+        <label>Débiteur
+          <select bind:value={draft.debtor_entity_id}>
+            <option value="">—</option>
+            {#each choices?.characters || [] as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
+          </select>
+        </label>
+        <label>Créancier
+          <select value={draft.creditor_entity_id} onchange={(e) => setCreditor(e.target.value)}>
+            <option value="">—</option>
+            {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
+          </select>
+        </label>
+        {#if creditorIsFaction}
+          <label>Contact (un membre)
+            <select bind:value={draft.contact_entity_id}>
+              <option value="">—</option>
+              {#each members as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
+            </select>
+          </label>
+        {/if}
+        <label>Motif <input type="text" bind:value={draft.reason} placeholder="facultatif"></label>
+        <label><input type="checkbox" bind:checked={draft.is_secret}> Transaction secrète</label>
+        <h4>Ce qui est dû</h4>
+        {#each draft.terms as term, k (k)}
+          <DebtTermRow {term} {choices} onremove={() => draft.terms.splice(k, 1)} />
+        {/each}
+        <button onclick={() => draft.terms.push(blankDebtTerm())}>+ terme</button>
+        {#if debtsState.saveError}<div class="r-err">{debtsState.saveError}</div>{/if}
+        <div style="margin-top:10px">
+          <button class="btn-send" disabled={debtsState.saving} onclick={() => saveDebtDraft(serverState.worldId)}>
+            {debtsState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
+          </button>
+          <button onclick={() => (debtsState.draft = null)}>Annuler</button>
+        </div>
+      </div>
+    </div>
+  {/if}
+</div>
+
+<style>
+  .debts { display: flex; gap: 12px; align-items: flex-start; }
+  .debt-list { flex: 1; }
+  .debt-editor { flex: 0 0 380px; }
+  .debt-editor label { display: block; margin: 4px 0; }
+  .debt-editor input[type="text"] { width: 100%; box-sizing: border-box; }
+  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
+  .row-card.closed { opacity: 0.7; }
+  .row-card ul { margin: 4px 0 0 18px; padding: 0; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+  h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
+</style>
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index d1df013..440f493 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -28,6 +28,8 @@
 
   let draft = $derived(questOffersState.draft);
   let choices = $derived(questOffersState.choices);
+  // TICKET-0110 (X1): a faction giver may name its contact, one of its members.
+  let giverMembers = $derived(draft ? choices?.members?.[draft.giver_entity_id] : null);
   let value = $derived(questOffersState.value);
 
   // TICKET-0109 (E1): the world's rates; '' = the code's default.
@@ -105,11 +107,20 @@
       <div class="queue-body">
         <label>Titre <input type="text" bind:value={draft.title}></label>
         <label>Donnée par
-          <select bind:value={draft.giver_entity_id}>
+          <select value={draft.giver_entity_id}
+                  onchange={(e) => { draft.giver_entity_id = e.target.value; draft.contact_entity_id = ''; }}>
             <option value="">—</option>
             {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
           </select>
         </label>
+        {#if giverMembers}
+          <label>Contact de la faction
+            <select bind:value={draft.contact_entity_id}>
+              <option value="">— à choisir au besoin</option>
+              {#each giverMembers as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
+            </select>
+          </label>
+        {/if}
         <label>Résumé <textarea rows="2" bind:value={draft.summary}></textarea></label>
         <div class="inline">
           <label><input type="checkbox" bind:checked={draft.repeatable}> Répétable</label>
diff --git a/frontend/src/creation/debtTerms.js b/frontend/src/creation/debtTerms.js
new file mode 100644
index 0000000..2dd791d
--- /dev/null
+++ b/frontend/src/creation/debtTerms.js
@@ -0,0 +1,51 @@
+/* TICKET-0110 (BRIEF-0110-C). The four currencies of an owed term as the
+   debt editors show them (Création › Dettes, Journée's service form): a
+   French label, the picker its target comes from (a key of GET
+   /api/quest-offers/choices, or none), and whether it counts an amount.
+   Mirrors `models.DEBT_CURRENCIES` across the network boundary -- kept
+   equal by `debts.py` (DC1). No relation: regard is not repaid (T1). A
+   skill is taught, so it is a skill definition, never a base domain. */
+import { STEP_DOMAINS } from './questRequirements.js';
+
+export const DEBT_CURRENCY_FORMS = {
+  money: { label: 'Monnaie', list: null, counted: true },
+  item: { label: 'Objet', list: 'items', counted: true },
+  fact: { label: 'Fait à transmettre', list: 'facts', counted: false },
+  skill: { label: 'Compétence à enseigner', list: 'skills', counted: false },
+};
+
+export function blankDebtTerm() {
+  return { currency: 'money', item_id: '', fact_id: '', skill_key: '', amount: 1 };
+}
+
+/** The (value, label) options of an owed term's target picker. */
+export function debtTargetOptions(currency, choices) {
+  if (!choices) return [];
+  switch (DEBT_CURRENCY_FORMS[currency]?.list) {
+    case 'items': return choices.items.map((i) => ({ value: i.id, label: i.name }));
+    case 'facts': return choices.facts.map((f) => ({ value: f.id, label: f.text }));
+    case 'skills': return choices.skills.filter((s) => !STEP_DOMAINS.includes(s.key))
+      .map((s) => ({ value: s.key, label: s.label }));
+    default: return [];
+  }
+}
+
+/** The request body of one owed term: only the columns its currency uses. */
+export function debtTermBody(term) {
+  const form = DEBT_CURRENCY_FORMS[term.currency];
+  return {
+    currency: term.currency,
+    item_id: term.currency === 'item' ? (term.item_id || null) : null,
+    fact_id: term.currency === 'fact' ? (term.fact_id || null) : null,
+    skill_key: term.currency === 'skill' ? (term.skill_key || null) : null,
+    amount: form.counted ? (term.amount === '' || term.amount === null ? null : Number(term.amount)) : null,
+  };
+}
+
+/** S2: what a service gives the player now, prefilled as what he will owe
+ *  -- its money and items received; Nia changes the list freely. */
+export function owedFromService(terms) {
+  return terms
+    .filter((t) => t.direction === 'reward' && (t.currency === 'money' || t.currency === 'item'))
+    .map((t) => ({ ...blankDebtTerm(), currency: t.currency, item_id: t.item_id || '', amount: t.amount ?? 1 }));
+}
diff --git a/frontend/src/creation/debts.svelte.js b/frontend/src/creation/debts.svelte.js
new file mode 100644
index 0000000..0aef255
--- /dev/null
+++ b/frontend/src/creation/debts.svelte.js
@@ -0,0 +1,85 @@
+/* TICKET-0110 (BRIEF-0110-C). State and requests of the « Dettes » island
+   (Debts.svelte): every debt of the world, the pickers' lists (the quest
+   editor's choices, members included), one draft written by hand, and a
+   remission's note. A debt is written whole (POST /api/debts), repaid
+   (POST …/repay) or forgiven (POST …/forgive) -- never edited, never
+   deleted (writes/debts.py). */
+import { api } from './sheetRequest.svelte.js';
+import { blankDebtTerm, debtTermBody } from './debtTerms.js';
+
+export const debtsState = $state({
+  debts: [],
+  choices: null,
+  loading: false,
+  loadError: '',
+  draft: null, // { debtor_entity_id, creditor_entity_id, contact_entity_id, reason, is_secret, terms }
+  saving: false,
+  saveError: '',
+  actionError: '', // a refused repayment or remission, by debt id: { id, message }
+});
+
+export function newDebtDraft() {
+  debtsState.saveError = '';
+  debtsState.draft = {
+    debtor_entity_id: '', creditor_entity_id: '', contact_entity_id: '', reason: '', is_secret: false,
+    terms: [blankDebtTerm()],
+  };
+}
+
+export async function loadDebts(worldId) {
+  if (!worldId) { debtsState.debts = []; debtsState.choices = null; return; }
+  debtsState.loading = true;
+  debtsState.loadError = '';
+  try {
+    const [debts, choices] = await Promise.all([api('/api/debts'), api('/api/quest-offers/choices')]);
+    debtsState.debts = debts;
+    debtsState.choices = choices;
+  } catch (e) {
+    debtsState.loadError = e.message;
+  } finally {
+    debtsState.loading = false;
+  }
+}
+
+export async function saveDebtDraft(worldId) {
+  const draft = debtsState.draft;
+  if (!draft) return;
+  debtsState.saving = true;
+  debtsState.saveError = '';
+  try {
+    await api('/api/debts', {
+      method: 'POST', headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify({
+        debtor_entity_id: draft.debtor_entity_id, creditor_entity_id: draft.creditor_entity_id,
+        contact_entity_id: draft.contact_entity_id || null, reason: draft.reason || null,
+        is_secret: draft.is_secret, terms: draft.terms.map(debtTermBody),
+      }),
+    });
+    debtsState.draft = null;
+    await loadDebts(worldId);
+  } catch (e) {
+    debtsState.saveError = e.message;
+  } finally {
+    debtsState.saving = false;
+  }
+}
+
+async function act(worldId, id, path, body) {
+  debtsState.actionError = '';
+  try {
+    await api('/api/debts/' + id + path, {
+      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
+    });
+    await loadDebts(worldId);
+  } catch (e) {
+    debtsState.actionError = { id, message: e.message };
+  }
+}
+
+export function repayDebt(worldId, id) {
+  return act(worldId, id, '/repay');
+}
+
+export function forgiveDebt(worldId, id, note) {
+  return act(worldId, id, '/forgive', { note: note || null });
+}
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 5b50e10..55aba56 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -43,8 +43,9 @@ import Queue from './Queue.svelte';
 import QueueBatchBar from './QueueBatchBar.svelte';
 import SubjectWorklist from './SubjectWorklist.svelte';
 import QuestOffers from './QuestOffers.svelte';
+import Debts from './Debts.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 7d95376..464efbc 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -13,7 +13,7 @@ export const questOffersState = $state({
   choices: null,
   loading: false,
   loadError: '',
-  draft: null, // { id|null, giver_entity_id, title, summary, repeatable, status, eligibility, steps }
+  draft: null, // { id|null, giver_entity_id, contact_entity_id, title, summary, repeatable, status, eligibility, steps }
   saving: false,
   saveError: '',
   value: null, // the draft's indicative value (cost, reward, ratio_pct, verdict_label)
@@ -28,7 +28,7 @@ export function blankStep() {
 export function newDraft() {
   questOffersState.saveError = '';
   questOffersState.draft = {
-    id: null, giver_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
+    id: null, giver_entity_id: '', contact_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
     eligibility: [], steps: [blankStep()], terms: [],
   };
   refreshValue();
@@ -37,7 +37,8 @@ export function newDraft() {
 export function editOffer(offer) {
   questOffersState.saveError = '';
   questOffersState.draft = {
-    id: offer.id, giver_entity_id: offer.giver_entity_id, title: offer.title, summary: offer.summary || '',
+    id: offer.id, giver_entity_id: offer.giver_entity_id, contact_entity_id: offer.contact_entity_id || '',
+    title: offer.title, summary: offer.summary || '',
     repeatable: offer.repeatable, status: offer.status,
     eligibility: offer.eligibility.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
     steps: offer.steps.map((s) => ({
@@ -117,7 +118,8 @@ export async function loadOffers(worldId) {
 
 function draftBody(draft) {
   return {
-    giver_entity_id: draft.giver_entity_id, title: draft.title, summary: draft.summary || null,
+    giver_entity_id: draft.giver_entity_id, contact_entity_id: draft.contact_entity_id || null,
+    title: draft.title, summary: draft.summary || null,
     repeatable: draft.repeatable, status: draft.status,
     eligibility: draft.eligibility.map(requirementBody),
     steps: draft.steps.map((s) => ({
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index 82203f2..337d20c 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -559,4 +559,12 @@ export const CREATION_ISLANDS = Object.freeze({
     origin: 'new',
     createdBy: 'TICKET-0108',
   }),
+  // TICKET-0110 (BRIEF-0110-C, J2): every debt of the world, and a debt
+  // written by hand -- created directly as an island, no legacy predecessor.
+  debts: Object.freeze({
+    containerId: 'creation-dettes',
+    component: 'Debts.svelte',
+    origin: 'new',
+    createdBy: 'TICKET-0110',
+  }),
 });
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 0ee6d29..68cf084 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -49,7 +49,7 @@
    sheet.
 
    `_creationRunWorldSwitchResets` does NOT port: every `onWorldSwitch` in
-   CREATION_TABS (16 static entries + the runtime-tab factory's own
+   CREATION_TABS (17 static entries + the runtime-tab factory's own
    template) is `null` (measured, not assumed — grep `onWorldSwitch:` over
    this file), so its `Object.values(...).forEach` loop is vacuous; its one
    real remaining effect (`creationReturnTo = null`) folds directly into
@@ -349,6 +349,15 @@ export const CREATION_TABS = {
     islands: [{ key: 'questOffers', containerId: 'creation-quetes' }],
     primaryAction: { label: '+ Nouvelle quête', handler: () => triggerPrimaryAction('questOffers') },
   },
+  dettes: {
+    label: 'Dettes',
+    archetype: 'bespoke',
+    containers: ['creation-dettes'],
+    loader: null,
+    state: { onTabEnter: null, onWorldSwitch: null },
+    islands: [{ key: 'debts', containerId: 'creation-dettes' }],
+    primaryAction: { label: '+ Nouvelle dette', handler: () => triggerPrimaryAction('debts') },
+  },
   subjects: {
     label: 'Sujets',
     archetype: 'bespoke',
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 3602aa3..b11a979 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18309,6 +18309,27 @@ relation at borrowing and repayment (E): it waits for a calendar, in its own
 ticket.
 
 
+## THE WORLD'S DEBTS IN CRÉATION (TICKET-0110) -- « DETTES » LISTS AND WRITES THEM, A FACTION OFFER NAMES ITS CONTACT (BRIEF-0110-c, no schema change)
+
+**Création › Dettes.** A new island lists every debt of the world: who owes
+whom (a faction's contact named), its origin and motive, what is owed line
+by line, its value in the world's unit, its state, secrecy and a
+remission's note. An open debt has « Rembourser » (all at once, its
+refusals shown) and « Remettre » with an optional note. « + Nouvelle dette »
+writes one by hand: any character as debtor, a character or a faction as
+creditor -- a faction asks for its contact among its members -- a motive,
+« transaction secrète », and the owed terms: money, items, a fact to
+transmit, a skill to teach (`debtTerms.js`, kept equal to
+`DEBT_CURRENCIES` by `debts.py` DC1). A debt is never edited nor deleted
+from here.
+
+**Création › Quêtes.** An offer given by a faction shows « Contact de la
+faction », its members to pick from; changing the giver clears it (X1).
+
+**Rejected.** Editing a debt's terms after the fact: a bargain is
+remitted and written anew, never rewritten (J2).
+
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
index c1f71e1..615b250 100644
--- a/tooling/verify/checks/debts.py
+++ b/tooling/verify/checks/debts.py
@@ -87,6 +87,21 @@ DB5 -- what the surfaces read (fixture and route functions). `debt_dict`
    settlement context's `credit` names the creditor, the lines owed and the
    preselected contact.
 
+DC1 -- the owed currencies' mirror (BRIEF-0110-C, static).
+   `frontend/src/creation/debtTerms.js`'s `DEBT_CURRENCY_FORMS` has exactly
+   the keys of `models.DEBT_CURRENCIES`, in order; money and items count,
+   facts and skills do not; its skill picker leaves out the base domains.
+DC2 -- the « Dettes » tab (static). `tabs.js`'s `dettes` entry mounts the
+   `debts` island in `creation-dettes` and routes « + Nouvelle dette »
+   through `triggerPrimaryAction('debts')`; `Debts.svelte` exports
+   `primaryAction` and renders `<DebtTermRow`; `debts.svelte.js` reads
+   `GET /api/debts`, writes with `POST /api/debts`, and calls `/repay` and
+   `/forgive`; it never sends a `PUT` or a `DELETE` (a debt is never edited
+   nor deleted).
+DC3 -- the offer's contact (static). `questOffers.svelte.js` loads and sends
+   `contact_entity_id`; `QuestOffers.svelte` offers the giver's
+   `choices.members` and clears the contact when the giver changes.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -926,6 +941,53 @@ def check_db(engine) -> None:
         _db5_credit_context(session, ids)
 
 
+# --- DC --------------------------------------------------------------------------
+
+def check_dc1() -> None:
+    from world_engine.models import DEBT_CURRENCIES
+
+    text = _read("creation/debtTerms.js")
+    forms = dict(re.findall(r"^\s+(\w+): \{ label: '[^']+', list: [^,]+, counted: (true|false) \},$", text, re.M))
+    if not forms:
+        fail("DC1: DEBT_CURRENCY_FORMS holds zero currencies")
+        return
+    if tuple(forms) != tuple(DEBT_CURRENCIES):
+        fail(f"DC1: DEBT_CURRENCY_FORMS keys {list(forms)} != DEBT_CURRENCIES {list(DEBT_CURRENCIES)}")
+    if {k for k, v in forms.items() if v == "true"} != {"money", "item"}:
+        fail(f"DC1: the counted currencies are {forms}")
+    if "!STEP_DOMAINS.includes(s.key)" not in text:
+        fail("DC1: the skill picker offers the base domains")
+
+
+def check_dc2() -> None:
+    tabs = _read("creation/tabs.js")
+    entry = re.search(r"\n  dettes: \{(.*?)\n  \},", tabs, re.S)
+    body = entry.group(1) if entry else ""
+    for needle in ("{ key: 'debts', containerId: 'creation-dettes' }", "triggerPrimaryAction('debts')"):
+        if needle not in body:
+            fail(f"DC2: tabs.js's dettes entry lacks {needle}")
+    island = _read("creation/Debts.svelte")
+    for needle in ("export function primaryAction()", "<DebtTermRow"):
+        if needle not in island:
+            fail(f"DC2: Debts.svelte lacks {needle}")
+    state = _read("creation/debts.svelte.js")
+    for needle in ("api('/api/debts')", "api('/api/debts', {", "'/repay'", "'/forgive'"):
+        if needle not in state:
+            fail(f"DC2: debts.svelte.js lacks {needle}")
+    if re.search(r"method: '(PUT|DELETE)'", state):
+        fail("DC2: debts.svelte.js edits or deletes a debt")
+
+
+def check_dc3() -> None:
+    state = _read("creation/questOffers.svelte.js")
+    if state.count("contact_entity_id") < 3 or "contact_entity_id: draft.contact_entity_id || null" not in state:
+        fail("DC3: questOffers.svelte.js does not load and send the offer's contact")
+    editor = _read("creation/QuestOffers.svelte")
+    for needle in ("choices?.members?.[draft.giver_entity_id]", "draft.contact_entity_id = ''"):
+        if needle not in editor:
+            fail(f"DC3: QuestOffers.svelte lacks {needle}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_da1a()
@@ -936,6 +998,9 @@ def main() -> int:
     check_da1c(engine)
     check_da3(engine)
     check_db(engine)
+    check_dc1()
+    check_dc2()
+    check_dc3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -947,7 +1012,8 @@ def main() -> int:
           "both parties (secret as it is, a faction's members when it is not), repaid at once or "
           "forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; "
           "« régler à crédit » pays what the player has and owes the rest per creditor; the surfaces "
-          "read every debt without an agenda or step id")
+          "read every debt without an agenda or step id; Création mirrors the owed currencies, lists "
+          "every debt in « Dettes », writes one by hand, and names a faction offer's contact")
     return 0
 
 
diff --git a/tooling/verify/checks/page_contract.py b/tooling/verify/checks/page_contract.py
index fb088d6..c77b0be 100644
--- a/tooling/verify/checks/page_contract.py
+++ b/tooling/verify/checks/page_contract.py
@@ -45,7 +45,8 @@ REGISTRE_SVELTE = CREATION_SRC / "Registre.svelte"
 
 TAB_KEYS = [
     "npc", "pj", "lieux", "factions", "objets",
-    "competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "quetes", "subjects",
+    "competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "quetes", "dettes",
+    "subjects",
     "queue", "prompts",
 ]
 
````

## Scope OUT

- Any Python file but `tooling/verify/checks/page_contract.py` and `debts.py`; any Journée file (D).
- Editing or deleting a debt from the tab.
- The relation's change at borrowing and repayment (E -- its own ticket, with a calendar).
- The erosion of an unpaid debt (H1): no world time exists.
- Settling a debt « otherwise » (C3), a partial repayment (D2), a debt proposed by the model.
- Porting « Mes savoirs » into Journée; rank trials (TICKET-0111); any change to `legacy.html` or Play.
- Any change to the day-chain prompts, and to any prompt but `pt-npc-link-pair`'s type list.
- Every later brief of this lot.

## Invariants to defend

**One mount mechanism:** the island is registered in `registry.js` and mounted by `mount.js` only (`creation_island.py`). **Play is sealed:** `legacy.html` is untouched. **History is sacred:** the tab has no edit or delete of a debt.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `creation_island.py` or `page_contract.py` turns red.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).
- Svelte a11y warnings during the build on `QuestOffers.svelte:90`, `Journee.svelte`'s day rows, `PjSkillFiche.svelte`, `PjCreatePanel.svelte` and `Graph.svelte` (pre-existing); npm's `EBADENGINE` notice on a Node older than 24.18.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/debts.py` -> `PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and no_debt_to for the creator alone, judges an open debt toward a character or a faction, and retires the relation type debt; a debt is validated whole, written with its fact known by both parties (secret as it is, a faction's members when it is not), repaid at once or forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; « régler à crédit » pays what the player has and owes the rest per creditor; the surfaces read every debt without an agenda or step id; Création mirrors the owed currencies, lists every debt in « Dettes », writes one by hand, and names a faction offer's contact`
- `creation_island.py`, `page_contract.py`, `quests.py`, `quest_rewards.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`debts.py` exits 1 with the rule named): in `frontend/src/creation/debtTerms.js`, `  item: { label: 'Objet', list: 'items', counted: true },` -> `the same line, then `  relation: { label: 'Relation', list: null, counted: true },`` -> `DC1`; in `frontend/src/creation/tabs.js`, `    islands: [{ key: 'debts', containerId: 'creation-dettes' }],` -> `    islands: [],` -> `DC2`; in `frontend/src/creation/questOffers.svelte.js`, `contact_entity_id: draft.contact_entity_id || null,` -> `(removed)` -> `DC3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 143/143.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE WORLD'S DEBTS IN CRÉATION (TICKET-0110) -- « DETTES » LISTS AND WRITES THEM, A FACTION OFFER NAMES ITS CONTACT (BRIEF-0110-c, no schema change)` -- in the diff. No schema change.
