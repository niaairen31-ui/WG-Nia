# BRIEF 0110-D — "Journée in three sub-tabs -- a service asked from the day, the player's debts, a quest settled on credit"

Lot: LOT-0110-debts-services.md (authoritative on conflict)
Depends on: BRIEF-0110-C

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0110-C's commit).

- `frontend/src/journee/Journee.svelte:77` -> `<QuestPanel />`
- `frontend/src/journee/Journee.svelte:53` -> `<div class="queue-panel" id="journee-declare-panel">`
- `frontend/src/journee/Journee.svelte:217` -> `</div><!-- #journee-view -->`
- `frontend/src/journee/quests.svelte.js:84` -> `export async function settleQuest(questId) {`
- `frontend/src/journee/SettlementRecap.svelte:53` -> `{questState.busy === questId ? 'Règlement…' : 'Confirmer : quête accomplie'}`
- `frontend/public/creation.css:287` -> `.creation-sub-tab-bar {`
- `frontend/src/creation/debtTerms.js:47` -> `export function owedFromService(terms) {` (C)
- `frontend/src/creation/DebtTermRow.svelte:7` -> `let { term, choices, onremove } = $props();` (C)
- `src/world_engine/quest_settlement_view.py:105` -> `"credit": _credit(db, quest),` (B)
- `tooling/verify/checks/debts.py:1003` -> `check_dc3()` (C)
- No `frontend/src/journee/DebtsPanel.svelte` exists.

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

### C-05 — where a debt comes from (service, credit) and the settlement made reusable
Produced by: BRIEF-0110-B   Consumed by: C-06, C-07
- `writes/quest_settlement.py`: `cost_checks(db, character_id, terms,
  giver_id) -> [(kind, reason)]`, kind `money`, `item` or `other`, the
  reasons `_cost_refusals` gave, in its order; `closed_refusal(db, quest)`;
  `settlement_refusals` = `[closed]` or the reasons of `cost_checks`
  (unchanged output); `apply_term(db, *, world_id, character_id, term,
  giver_id, reason, source_type="quest", amount=None)` (the D table of
  0109; `amount` replaces a money or item term's own); `in_order(terms)`;
  `finish_settlement(db, quest)` (the agenda `completed` when it is not,
  `settled_at`); `settle_quest` = refusals, `apply_term` over `in_order`,
  `finish_settlement`. `canon_write_policy.txt` moves the `quest` site from
  `settle_quest` to `finish_settlement`.
- `writes/debt_sources.py`:
  - `request_service(db, *, character, provider_id, on_behalf_of_id, terms:
    [TermSpec], owed: [DebtTermSpec], reason, is_secret) -> Debt`: case
    table (b-7), nothing written before every check; then `apply_term` over
    `in_order` of the cleaned terms (giver = the provider, `source_type`
    `service`, reason « Service de P »), then `write_debt` (origin
    `service`, `changed_by` `service`).
  - `credit_plan(db, quest) -> CreditPlan(refusals, paid, owed)`: case
    table (b-4).
  - `credit_contact(db, quest, creditor_id, contacts) -> Optional[str]`:
    a character creditor -> None; a faction -> `contacts[creditor]` if set,
    else the offer's contact when the faction is the giver, else None.
  - `settle_quest_on_credit(db, *, quest, contacts, is_secret) -> Quest`:
    `ValueError` on any plan refusal, and « il faut choisir le membre de « F
    » qui porte la dette » for a faction creditor with no contact, before
    any write; every debt prepared (origin `quest`, `origin_quest_id`,
    reason « Quête « title » », the shortfall terms); then `apply_term` over
    `in_order` with `amount = paid` for a money or item cost (skipped when
    0), `finish_settlement`, then each debt written (`changed_by`
    `quest_credit`).
- `writes/quests.py`: `write_quest_offer(..., contact_entity_id=None)`;
  `_check_contact`: a contact on a character giver, or one who is not an
  active character member of the faction giver, raises; the value is
  written as given; `_snapshot` records it.

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

### C-09 — Journée
Produced by: BRIEF-0110-D   Consumed by: nothing in this lot
- `Journee.svelte`: `SUB_TABS = { journee: 'Journée', quetes: 'Quêtes',
  dettes: 'Dettes' }`, the shell's `.creation-sub-tab-bar`; « Journée »
  holds the declaration, `<ServiceForm />` and the days; « Quêtes »
  `<QuestPanel />`; « Dettes » `<DebtsPanel />`.
- `journee/debts.svelte.js`: `GET /api/journee/debts`, repay and forgive
  through C-07, `POST /api/services`; S2's prefill (`servicePrefill`: the
  owed list follows `owedFromService` until it is edited).
- `ServiceForm.svelte`: who helps; « Pour le compte de » among the
  factions he is a member of; « Ce qu’il fait pour vous » / « Ce que ça
  coûte tout de suite » (`QuestTermRow`); « Ce que vous devrez »
  (`DebtTermRow`); motive; secrecy; « Accepter le service ».
- `DebtsPanel.svelte`: « Ce que je dois », « Ce qu’on me doit »; an open
  debt shows its refusals (« Pas encore : … »), « Rembourser » (disabled
  unless `repayable`) and « Remettre » with a note.
- `quests.svelte.js`: `settleOnCredit(questId, contacts, isSecret)`;
  `SettlementRecap.svelte`: under `ctx.credit?.possible`, « Régler à
  crédit »: each creditor and its lines, a member picker for a faction
  (its contact preselected), secrecy, « Confirmer : régler à crédit »;
  Journée's debts are re-read after it.

## Case tables carried (lot, gate output (b))

**b-4 — `credit_plan`** (the quest's cost terms, in order):

| condition | result |
|---|---|
| quest settled, or its agenda missing, failed, abandoned | refused: `closed_refusal` |
| any `other` cost check (a fact unknown, a skill not Maître, the counterparty holds it) | refused: those reasons |
| a money cost | pay = min(amount, money left of max(0, balance)); the rest owed to its counterparty, else the giver |
| an item cost | pay = min(amount, that item left of what he holds); the rest owed likewise |
| nothing owed | refused: « rien à régler à crédit : la quête peut être déclarée accomplie » |
| otherwise | `paid` per cost term, `owed` per creditor, in term order |

## Context

Création has its debts (C). Journée becomes three sub-tabs, like Play's (W-a): « Journée » with « Demander un service » (S2), « Quêtes » as it was, « Dettes » with the player's debts. The recap of « Déclarer accomplie » gains « Régler à crédit » (A2).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
and the built `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `frontend/src/journee/debts.svelte.js`, `DebtsPanel.svelte`, `ServiceForm.svelte` (C-09);
   - `Journee.svelte`: `SUB_TABS`, the shell's `.creation-sub-tab-bar`, the three panels; the debts re-read with the world;
   - `quests.svelte.js`: `settleOnCredit`; `SettlementRecap.svelte`: « Régler à crédit »;
   - adds DD1-DD3 to `debts.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/journee/DebtsPanel.svelte
   - frontend/src/journee/Journee.svelte
   - frontend/src/journee/ServiceForm.svelte
   - frontend/src/journee/SettlementRecap.svelte
   - frontend/src/journee/debts.svelte.js
   - frontend/src/journee/quests.svelte.js
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/debts.py
2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(debts): Journée in three sub-tabs -- a service asked from the day, the player's debts, a quest settled on credit (BRIEF-0110-d)`.

````diff
diff --git a/frontend/src/journee/DebtsPanel.svelte b/frontend/src/journee/DebtsPanel.svelte
new file mode 100644
index 0000000..518b16a
--- /dev/null
+++ b/frontend/src/journee/DebtsPanel.svelte
@@ -0,0 +1,63 @@
+<script>
+  /* TICKET-0110 (BRIEF-0110-D, J2, D1). Journée › Dettes: what the player
+     owes and what is owed to him -- the other party (a faction's contact
+     named), the origin and motive, what is owed line by line, its value
+     in the world's unit, its state. An open debt shows why it cannot be
+     repaid now, if it cannot, « Rembourser » (all at once) and
+     « Remettre » with an optional note. Nothing is ever deleted. */
+  import { debtState, loadJourneeDebts, repay, forgive } from './debts.svelte.js';
+
+  let notes = $state({});
+  let sections = $derived([
+    { title: 'Ce que je dois', list: debtState.owes, other: (d) => d.creditor_name },
+    { title: 'Ce qu’on me doit', list: debtState.owed, other: (d) => d.debtor_name },
+  ]);
+</script>
+
+<div class="queue-panel" id="journee-debt-panel">
+  <div class="panel-head">
+    <h2>Dettes</h2>
+    <button class="btn-icon" onclick={() => loadJourneeDebts()} title="Rafraîchir">↻</button>
+  </div>
+  <div class="queue-body">
+    {#if debtState.loadError}<div class="r-err">{debtState.loadError}</div>{/if}
+    {#if debtState.actionError}<div class="r-err">{debtState.actionError}</div>{/if}
+    {#each sections as section (section.title)}
+      <h4>{section.title}</h4>
+      {#if section.list.length === 0}<p class="muted">Aucune.</p>{/if}
+      {#each section.list as debt (debt.id)}
+        <div class="row-card" class:over={debt.status !== 'open'}>
+          <strong>{section.other(debt)}</strong>
+          {#if debt.contact_name}<span class="muted">(par {debt.contact_name})</span>{/if}
+          <span class="badge b-other">{debt.status_label}</span>
+          {#if debt.is_secret}<span class="badge b-other">secrète</span>{/if}
+          <div class="muted">{debt.origin_label}{debt.reason ? ' — ' + debt.reason : ''} · valeur {debt.value}</div>
+          <ul class="terms">
+            {#each debt.terms as t, i (i)}<li>{t.line}</li>{/each}
+            {#if debt.terms.length === 0}<li>une faveur</li>{/if}
+          </ul>
+          {#if debt.closed_note}<div class="muted">Note : {debt.closed_note}</div>{/if}
+          {#if debt.status === 'open'}
+            {#each debt.refusals as reason}<div class="muted">Pas encore : {reason}</div>{/each}
+            <div class="inline">
+              <button disabled={!debt.repayable || debtState.busy !== null} onclick={() => repay(debt.id)}>
+                {debtState.busy === debt.id ? '…' : 'Rembourser'}
+              </button>
+              <input type="text" placeholder="Note (facultative)" bind:value={notes[debt.id]}>
+              <button disabled={debtState.busy !== null} onclick={() => forgive(debt.id, notes[debt.id])}>Remettre</button>
+            </div>
+          {/if}
+        </div>
+      {/each}
+    {/each}
+  </div>
+</div>
+
+<style>
+  .r-err { color: var(--red); }
+  .muted { color: var(--muted); font-size: 12px; }
+  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
+  .terms { margin: 2px 0 6px 18px; padding: 0; font-size: 12px; }
+  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
+  .over { opacity: 0.7; }
+</style>
diff --git a/frontend/src/journee/Journee.svelte b/frontend/src/journee/Journee.svelte
index 271106c..ec87cb7 100644
--- a/frontend/src/journee/Journee.svelte
+++ b/frontend/src/journee/Journee.svelte
@@ -9,7 +9,11 @@
      no delete control, and `declared_action` has no update path anywhere
      in the backend (writes/pipeline.py). No agenda data is fetched,
      rendered or referenced anywhere in this surface (Scope OUT): quests
-     (TICKET-0108) are shown by their own title, steps and `quest_id`. */
+     (TICKET-0108) are shown by their own title, steps and `quest_id`.
+
+     TICKET-0110 (BRIEF-0110-D, W-a): three sub-tabs, like Play's --
+     « Journée » (declare, ask a service, the days), « Quêtes » (the quest
+     panel, moved as is) and « Dettes » (what the player owes and is owed). */
   import { serverState } from '../lib/serverState.svelte.js';
   import { navigate } from '../lib/router.js';
   import {
@@ -17,10 +21,16 @@
     planDay, resolveDay,
   } from './journee.svelte.js';
   import QuestPanel from './QuestPanel.svelte';
+  import DebtsPanel from './DebtsPanel.svelte';
+  import ServiceForm from './ServiceForm.svelte';
   import { questState, loadQuests, openQuests } from './quests.svelte.js';
+  import { loadJourneeDebts, serviceState } from './debts.svelte.js';
 
   let { active = false } = $props();
 
+  const SUB_TABS = { journee: 'Journée', quetes: 'Quêtes', dettes: 'Dettes' };
+  let subTab = $state('journee');
+
   function goToPlay() {
     navigate('play');
   }
@@ -34,6 +44,9 @@
     reloadForWorld();
     questState.pin = '';
     loadQuests();
+    serviceState.draft = null;
+    serviceState.choices = null;
+    loadJourneeDebts();
   });
 
   // A plan or a resolution moves a quest's steps: re-read the panel after either.
@@ -50,6 +63,16 @@
 
 <div class="app-view" id="journee-view" style:display={active ? '' : 'none'}>
 
+  <div class="creation-sub-tab-bar">
+    {#each Object.entries(SUB_TABS) as [key, label] (key)}
+      <button class="creation-sub-tab" class:active={subTab === key} onclick={() => (subTab = key)}>{label}</button>
+    {/each}
+  </div>
+
+  <div style:display={subTab === 'quetes' ? '' : 'none'}><QuestPanel /></div>
+  <div style:display={subTab === 'dettes' ? '' : 'none'}><DebtsPanel /></div>
+
+  <div style:display={subTab === 'journee' ? '' : 'none'}>
   <div class="queue-panel" id="journee-declare-panel">
     <div class="panel-head">
       <h2>Journée — déclarer une action</h2>
@@ -74,7 +97,7 @@
     </div>
   </div>
 
-  <QuestPanel />
+  <ServiceForm />
 
   <div class="queue-panel" id="journee-list-panel">
     <div class="panel-head">
@@ -214,6 +237,8 @@
     </div>
   </div>
 
+  </div><!-- the « Journée » sub-tab -->
+
 </div><!-- #journee-view -->
 
 <style>
diff --git a/frontend/src/journee/ServiceForm.svelte b/frontend/src/journee/ServiceForm.svelte
new file mode 100644
index 0000000..74d2f2e
--- /dev/null
+++ b/frontend/src/journee/ServiceForm.svelte
@@ -0,0 +1,85 @@
+<script>
+  /* TICKET-0110 (BRIEF-0110-D, S2). « Demander un service », in Journée's
+     own tab: Nia names who helps (and the faction he acts for, if any),
+     what he does now -- rewards the player receives, costs paid at once,
+     such as a fall of regard -- and what the player will owe, prefilled
+     from the coins and items received until she edits it; a motive and
+     « transaction secrète ». Sent whole; the server applies the terms and
+     writes the debt (writes/debt_sources.py), or refuses with nothing
+     written. */
+  import QuestTermRow from '../creation/QuestTermRow.svelte';
+  import DebtTermRow from '../creation/DebtTermRow.svelte';
+  import { blankTerm, TERM_DIRECTIONS } from '../creation/questTerms.js';
+  import { serviceState, openService, servicePrefill, addOwed, askService } from './debts.svelte.js';
+
+  let draft = $derived(serviceState.draft);
+  let choices = $derived(serviceState.choices);
+  // The factions the chosen provider is an active member of (X1).
+  let factions = $derived(draft && choices
+    ? (choices.factions || []).filter((f) => (choices.members?.[f.id] || []).some((m) => m.id === draft.provider_entity_id))
+    : []);
+
+  function setProvider(id) {
+    draft.provider_entity_id = id;
+    draft.on_behalf_of_id = '';
+  }
+</script>
+
+<div class="queue-panel" id="journee-service-panel">
+  <div class="panel-head">
+    <h2>Demander un service</h2>
+    {#if !draft}<button onclick={() => openService()}>+ Service</button>{/if}
+  </div>
+  <div class="queue-body">
+    {#if serviceState.done && !draft}<p class="muted">{serviceState.done}</p>{/if}
+    {#if draft}
+      <label>Qui aide
+        <select value={draft.provider_entity_id} onchange={(e) => setProvider(e.target.value)}>
+          <option value="">—</option>
+          {#each choices?.characters || [] as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
+        </select>
+      </label>
+      {#if factions.length}
+        <label>Pour le compte de
+          <select bind:value={draft.on_behalf_of_id}>
+            <option value="">lui-même</option>
+            {#each factions as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
+          </select>
+        </label>
+      {/if}
+      {#each Object.entries(TERM_DIRECTIONS) as [direction, label] (direction)}
+        <h4>{direction === 'reward' ? 'Ce qu’il fait pour vous' : 'Ce que ça coûte tout de suite'}</h4>
+        {#each draft.terms as term, k (k)}
+          {#if term.direction === direction}
+            <QuestTermRow {term} {choices} onchange={() => servicePrefill()} onremove={() => draft.terms.splice(k, 1)} />
+          {/if}
+        {/each}
+        <button onclick={() => { draft.terms.push(blankTerm(direction)); servicePrefill(); }}>+ {label.toLowerCase()}</button>
+      {/each}
+      <h4>Ce que vous devrez</h4>
+      <div role="group" oninput={() => (draft.owedTouched = true)} onchange={() => (draft.owedTouched = true)}>
+        {#each draft.owed as term, k (k)}
+          <DebtTermRow {term} {choices} onremove={() => { draft.owedTouched = true; draft.owed.splice(k, 1); }} />
+        {/each}
+      </div>
+      <button onclick={() => addOwed()}>+ terme dû</button>
+      <label>Motif <input type="text" bind:value={draft.reason} placeholder="facultatif si quelque chose est dû"></label>
+      <label><input type="checkbox" bind:checked={draft.is_secret}> Transaction secrète</label>
+      {#if serviceState.error}<div class="r-err">{serviceState.error}</div>{/if}
+      <div style="margin-top:8px">
+        <button class="btn-send" disabled={serviceState.sending} onclick={() => askService()}>
+          {serviceState.sending ? 'Envoi…' : 'Accepter le service'}
+        </button>
+        <button onclick={() => (serviceState.draft = null)}>Annuler</button>
+      </div>
+    {/if}
+  </div>
+</div>
+
+<style>
+  label { display: block; margin: 4px 0; }
+  input[type="text"] { width: 100%; box-sizing: border-box; }
+  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+</style>
diff --git a/frontend/src/journee/SettlementRecap.svelte b/frontend/src/journee/SettlementRecap.svelte
index 15fbcb8..fd8c617 100644
--- a/frontend/src/journee/SettlementRecap.svelte
+++ b/frontend/src/journee/SettlementRecap.svelte
@@ -4,12 +4,29 @@
      their outcomes, the days that advanced it, the step changes still
      awaiting review, its terms and their value) and why it cannot be
      settled now, if it cannot. Nothing here is a verdict: she decides. The
-     quest is named by its quest_id only. */
-  import { questState, settleQuest } from './quests.svelte.js';
+     quest is named by its quest_id only. TICKET-0110 (A2): when coins or
+     items are all that is lacking, « Régler à crédit » shows what would be
+     owed to whom -- a faction creditor's member to pick, its contact
+     preselected -- and settles with the rest as debts. */
+  import { questState, settleQuest, settleOnCredit } from './quests.svelte.js';
+  import { loadJourneeDebts } from './debts.svelte.js';
 
   let { questId } = $props();
 
   let ctx = $derived(questState.settlement);
+  let contacts = $state({});
+  let creditSecret = $state(false);
+
+  function contactOf(debt) {
+    return contacts[debt.creditor_id] ?? debt.contact_id ?? '';
+  }
+
+  async function onCredit() {
+    const chosen = Object.fromEntries((ctx.credit.debts || []).filter((d) => d.is_faction && contactOf(d))
+      .map((d) => [d.creditor_id, contactOf(d)]));
+    await settleOnCredit(questId, chosen, creditSecret);
+    await loadJourneeDebts();
+  }
 </script>
 
 <div class="recap">
@@ -52,6 +69,26 @@
     <button class="btn-send" disabled={!ctx.can_settle || questState.busy !== null} onclick={() => settleQuest(questId)}>
       {questState.busy === questId ? 'Règlement…' : 'Confirmer : quête accomplie'}
     </button>
+
+    {#if ctx.credit?.possible}
+      <h5>Régler à crédit</h5>
+      <p class="muted">Vous payez ce que vous avez ; le reste devient une dette.</p>
+      {#each ctx.credit.debts as debt (debt.creditor_id)}
+        <div class="credit">
+          <strong>Envers {debt.creditor_name}</strong> : {debt.lines.join(', ')}
+          {#if debt.is_faction}
+            <label>Lié à
+              <select value={contactOf(debt)} onchange={(e) => (contacts[debt.creditor_id] = e.target.value)}>
+                <option value="">— un membre</option>
+                {#each debt.members as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
+              </select>
+            </label>
+          {/if}
+        </div>
+      {/each}
+      <label><input type="checkbox" bind:checked={creditSecret}> Transaction secrète</label>
+      <button disabled={questState.busy !== null} onclick={() => onCredit()}>Confirmer : régler à crédit</button>
+    {/if}
   {/if}
 </div>
 
@@ -62,4 +99,6 @@
   .day { margin: 2px 0 4px; }
   .muted { color: var(--muted); font-size: 12px; }
   .r-err { color: var(--red); }
+  .credit { margin: 2px 0 4px; }
+  .credit label { display: inline-flex; gap: 4px; margin-left: 8px; }
 </style>
diff --git a/frontend/src/journee/debts.svelte.js b/frontend/src/journee/debts.svelte.js
new file mode 100644
index 0000000..a414b0d
--- /dev/null
+++ b/frontend/src/journee/debts.svelte.js
@@ -0,0 +1,118 @@
+/* TICKET-0110 (BRIEF-0110-D). State and requests of Journée's debts:
+   « Dettes » (DebtsPanel.svelte) -- what the player owes and what is owed
+   to him, GET /api/journee/debts, each open one with its refusals -- and
+   « Demander un service » (ServiceForm.svelte, S2), POST /api/services.
+   Repaying and forgiving go through the creator's routes, the same rules
+   (writes/debts.py). A debt is named by its own id, never by a plan. */
+import { api } from '../creation/sheetRequest.svelte.js';
+import { blankDebtTerm, debtTermBody, owedFromService } from '../creation/debtTerms.js';
+import { termBody } from '../creation/questTerms.js';
+
+export const debtState = $state({
+  owes: [],
+  owed: [],
+  loading: false,
+  loadError: '',
+  busy: null, // the debt id being acted on
+  actionError: '',
+});
+
+export const serviceState = $state({
+  choices: null,
+  draft: null, // { provider_entity_id, on_behalf_of_id, terms, owed, owedTouched, reason, is_secret }
+  sending: false,
+  error: '',
+  done: '',
+});
+
+function applyDebts(payload) {
+  debtState.owes = payload.owes;
+  debtState.owed = payload.owed;
+}
+
+export async function loadJourneeDebts() {
+  debtState.loading = true;
+  debtState.loadError = '';
+  try {
+    applyDebts(await api('/api/journee/debts'));
+  } catch (e) {
+    debtState.loadError = e.message;
+    debtState.owes = [];
+    debtState.owed = [];
+  } finally {
+    debtState.loading = false;
+  }
+}
+
+async function act(id, path, body) {
+  debtState.busy = id;
+  debtState.actionError = '';
+  try {
+    await api('/api/debts/' + id + path, {
+      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
+    });
+    await loadJourneeDebts();
+  } catch (e) {
+    debtState.actionError = e.message;
+  } finally {
+    debtState.busy = null;
+  }
+}
+
+export function repay(id) {
+  return act(id, '/repay');
+}
+
+export function forgive(id, note) {
+  return act(id, '/forgive', { note: note || null });
+}
+
+export async function openService() {
+  serviceState.error = '';
+  serviceState.done = '';
+  serviceState.draft = {
+    provider_entity_id: '', on_behalf_of_id: '', terms: [], owed: [], owedTouched: false, reason: '',
+    is_secret: false,
+  };
+  if (!serviceState.choices) {
+    try {
+      serviceState.choices = await api('/api/quest-offers/choices');
+    } catch (e) {
+      serviceState.error = e.message;
+    }
+  }
+}
+
+/** S2: until Nia edits it, what is owed follows what is received. */
+export function servicePrefill() {
+  const draft = serviceState.draft;
+  if (draft && !draft.owedTouched) draft.owed = owedFromService(draft.terms);
+}
+
+export function addOwed() {
+  serviceState.draft.owedTouched = true;
+  serviceState.draft.owed.push(blankDebtTerm());
+}
+
+export async function askService() {
+  const draft = serviceState.draft;
+  if (!draft) return;
+  serviceState.sending = true;
+  serviceState.error = '';
+  try {
+    applyDebts(await api('/api/services', {
+      method: 'POST', headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify({
+        provider_entity_id: draft.provider_entity_id, on_behalf_of_id: draft.on_behalf_of_id || null,
+        terms: draft.terms.map(termBody), owed: draft.owed.map(debtTermBody),
+        reason: draft.reason || null, is_secret: draft.is_secret,
+      }),
+    }));
+    serviceState.draft = null;
+    serviceState.done = 'Service rendu : la dette est inscrite dans « Dettes ».';
+  } catch (e) {
+    serviceState.error = e.message;
+  } finally {
+    serviceState.sending = false;
+  }
+}
diff --git a/frontend/src/journee/quests.svelte.js b/frontend/src/journee/quests.svelte.js
index 5ad3a14..dc2b42a 100644
--- a/frontend/src/journee/quests.svelte.js
+++ b/frontend/src/journee/quests.svelte.js
@@ -85,3 +85,10 @@ export async function settleQuest(questId) {
   await act(questId, '/api/quests/' + questId + '/settle', null);
   if (!questState.actionError) questState.settling = null;
 }
+
+/** A2 (TICKET-0110): what the player lacks of coins or items becomes a
+ *  debt per creditor; `contacts` names a faction creditor's member. */
+export async function settleOnCredit(questId, contacts, isSecret) {
+  await act(questId, '/api/quests/' + questId + '/settle-on-credit', { contacts, is_secret: isSecret });
+  if (!questState.actionError) questState.settling = null;
+}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index b11a979..5309ace 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18330,6 +18330,33 @@ faction », its members to pick from; changing the giver clears it (X1).
 remitted and written anew, never rewritten (J2).
 
 
+## JOURNÉE IN THREE SUB-TABS (TICKET-0110) -- A SERVICE IS ASKED FROM THE DAY, DEBTS HAVE THEIR OWN TAB, A QUEST SETTLES ON CREDIT (BRIEF-0110-d, no schema change)
+
+**W-a.** Journée gains a sub-tab bar, like Play's: « Journée » (declare an
+action, « Demander un service », the days), « Quêtes » (the quest panel,
+moved as is) and « Dettes ». « Mes savoirs » is not ported: done right it
+reads resolved knowledge and its versions, and gets its own ticket.
+
+**« Dettes ».** What the player owes and what is owed to him: the other
+party, a faction's contact, the origin and motive, what is owed, its
+value, its state. An open debt shows why it cannot be repaid yet (a fact
+he does not know, a skill he is not Maître in, coins he lacks),
+« Rembourser » and « Remettre » with a note.
+
+**S2 in the day.** « Demander un service »: who helps (and the faction he
+acts for, among his own), what he does now -- the quest term rows, rewards
+and immediate costs -- and what the player will owe, prefilled with the
+coins and items received until Nia edits it; a motive; secrecy.
+
+**A2 in the recap.** When coins or items are all that is lacking, the recap
+of « Déclarer accomplie » adds « Régler à crédit »: what would be owed to
+whom, a faction's member to pick (its contact preselected), secrecy, and
+« Confirmer : régler à crédit ».
+
+**Rejected.** Porting « Mes savoirs » from Play as it is (W-b): it reads
+stored rows only and would show less than the player knows.
+
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
index 615b250..0237f63 100644
--- a/tooling/verify/checks/debts.py
+++ b/tooling/verify/checks/debts.py
@@ -102,6 +102,21 @@ DC3 -- the offer's contact (static). `questOffers.svelte.js` loads and sends
    `contact_entity_id`; `QuestOffers.svelte` offers the giver's
    `choices.members` and clears the contact when the giver changes.
 
+DD1 -- Journée's three sub-tabs (BRIEF-0110-D, static, W-a).
+   `Journee.svelte`'s `SUB_TABS` is exactly « Journée », « Quêtes »,
+   « Dettes »; `<QuestPanel` renders under `quetes`, `<DebtsPanel` under
+   `dettes`, `<ServiceForm` and the declaration under `journee`.
+DD2 -- the debts and the service (static). `debts.svelte.js` reads `GET
+   /api/journee/debts`, posts `/api/services`, `/repay` and `/forgive`;
+   `ServiceForm.svelte` renders `<QuestTermRow` and `<DebtTermRow` and
+   prefills what is owed (`servicePrefill`) from `owedFromService`, which
+   keeps the money and item rewards only; none of the three files, nor
+   `DebtsPanel.svelte`, names `agenda_id` or `step_id`.
+DD3 -- « régler à crédit » (static). `quests.svelte.js` posts
+   `/settle-on-credit` with `contacts` and `is_secret`;
+   `SettlementRecap.svelte` shows it under `ctx.credit?.possible` and calls
+   `settleOnCredit(`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -988,6 +1003,53 @@ def check_dc3() -> None:
             fail(f"DC3: QuestOffers.svelte lacks {needle}")
 
 
+# --- DD --------------------------------------------------------------------------
+
+def check_dd1() -> None:
+    view = _read("journee/Journee.svelte")
+    tabs = re.search(r"const SUB_TABS = \{([^}]*)\};", view)
+    if tabs is None or re.findall(r"(\w+): '([^']+)'", tabs.group(1)) != [
+            ("journee", "Journée"), ("quetes", "Quêtes"), ("dettes", "Dettes")]:
+        fail(f"DD1: SUB_TABS is {tabs.group(1) if tabs else None}")
+    for needle in ("<div style:display={subTab === 'quetes' ? '' : 'none'}><QuestPanel /></div>",
+                   "<div style:display={subTab === 'dettes' ? '' : 'none'}><DebtsPanel /></div>"):
+        if needle not in view:
+            fail(f"DD1: Journee.svelte lacks {needle}")
+    journee = view.split("<div style:display={subTab === 'journee' ? '' : 'none'}>", 1)
+    if len(journee) != 2 or "<ServiceForm />" not in journee[1] or 'id="journee-declare-panel"' not in journee[1]:
+        fail("DD1: the « Journée » sub-tab does not hold the declaration and the service form")
+
+
+def check_dd2() -> None:
+    state = _read("journee/debts.svelte.js")
+    for needle in ("api('/api/journee/debts')", "api('/api/services', {", "'/repay'", "'/forgive'"):
+        if needle not in state:
+            fail(f"DD2: debts.svelte.js lacks {needle}")
+    form = _read("journee/ServiceForm.svelte")
+    for needle in ("<QuestTermRow", "<DebtTermRow", "servicePrefill()"):
+        if needle not in form:
+            fail(f"DD2: ServiceForm.svelte lacks {needle}")
+    if "owedFromService(draft.terms)" not in state:
+        fail("DD2: what is owed is not prefilled from the service's terms")
+    terms = _read("creation/debtTerms.js")
+    if "t.direction === 'reward' && (t.currency === 'money' || t.currency === 'item')" not in terms:
+        fail("DD2: owedFromService does not keep the money and item rewards only")
+    for rel in ("journee/debts.svelte.js", "journee/ServiceForm.svelte", "journee/DebtsPanel.svelte"):
+        text = _read(rel)
+        if "agenda_id" in text or "step_id" in text:
+            fail(f"DD2: {rel} names an agenda or a step")
+
+
+def check_dd3() -> None:
+    state = _read("journee/quests.svelte.js")
+    if "'/settle-on-credit', { contacts, is_secret: isSecret }" not in state:
+        fail("DD3: quests.svelte.js does not post the credit settlement with its contacts")
+    recap = _read("journee/SettlementRecap.svelte")
+    for needle in ("{#if ctx.credit?.possible}", "settleOnCredit("):
+        if needle not in recap:
+            fail(f"DD3: SettlementRecap.svelte lacks {needle}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_da1a()
@@ -1001,6 +1063,9 @@ def main() -> int:
     check_dc1()
     check_dc2()
     check_dc3()
+    check_dd1()
+    check_dd2()
+    check_dd3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -1013,7 +1078,8 @@ def main() -> int:
           "forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; "
           "« régler à crédit » pays what the player has and owes the rest per creditor; the surfaces "
           "read every debt without an agenda or step id; Création mirrors the owed currencies, lists "
-          "every debt in « Dettes », writes one by hand, and names a faction offer's contact")
+          "every debt in « Dettes », writes one by hand, and names a faction offer's contact; Journée has "
+          "its three sub-tabs, asks a service, repays and forgives, and settles a quest on credit")
     return 0
 
 
````

## Scope OUT

- Any Python file but `debts.py`; any Création file.
- « Mes savoirs » in Journée.
- Changing the quest panel's behavior: it moves under « Quêtes » as is.
- The relation's change at borrowing and repayment (E -- its own ticket, with a calendar).
- The erosion of an unpaid debt (H1): no world time exists.
- Settling a debt « otherwise » (C3), a partial repayment (D2), a debt proposed by the model.
- Porting « Mes savoirs » into Journée; rank trials (TICKET-0111); any change to `legacy.html` or Play.
- Any change to the day-chain prompts, and to any prompt but `pt-npc-link-pair`'s type list.

## Invariants to defend

**The player never sees the agenda:** no Journée file names an `agenda_id` or `step_id` (`quests.py` QC3, `debts.py` DD2). **Play is sealed:** `legacy.html` is untouched; Journée borrows the shell's sub-tab classes, not Play's.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `quests.py` QC3 turns red (the quest panel or the day pin changed).

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/debts.py` -> `PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and no_debt_to for the creator alone, judges an open debt toward a character or a faction, and retires the relation type debt; a debt is validated whole, written with its fact known by both parties (secret as it is, a faction's members when it is not), repaid at once or forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; « régler à crédit » pays what the player has and owes the rest per creditor; the surfaces read every debt without an agenda or step id; Création mirrors the owed currencies, lists every debt in « Dettes », writes one by hand, and names a faction offer's contact; Journée has its three sub-tabs, asks a service, repays and forgives, and settles a quest on credit`
- `quests.py`, `frontend_build_fresh.py`, `module_budget.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`debts.py` exits 1 with the rule named): in `frontend/src/journee/Journee.svelte`, `  <div style:display={subTab === 'quetes' ? '' : 'none'}><QuestPanel /></div>` -> `(removed)` -> `DD1`; in `frontend/src/creation/debtTerms.js`, `.filter((t) => t.direction === 'reward' && (t.currency === 'money' || t.currency === 'item'))` -> `.filter((t) => t.direction === 'reward')` -> `DD2`; in `frontend/src/journee/SettlementRecap.svelte`, `{#if ctx.credit?.possible}` -> `{#if false}` -> `DD3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 143/143.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `JOURNÉE IN THREE SUB-TABS (TICKET-0110) -- A SERVICE IS ASKED FROM THE DAY, DEBTS HAVE THEIR OWN TAB, A QUEST SETTLES ON CREDIT (BRIEF-0110-d, no schema change)` -- in the diff. No schema change.
