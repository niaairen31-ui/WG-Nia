<script>
  /* TICKET-0110 (BRIEF-0110-C, J2, C2, X1). The « Dettes » island: every
     debt of the world -- who owes whom, why, what, its indicative value,
     its state -- and a debt written by hand (any debtor, a character or a
     faction creditor, a faction's contact, a motive, secrecy, what is
     owed). An open debt can be repaid (all at once, D1) or forgiven with a
     note; a debt is never edited nor deleted. Its CREATION_ISLANDS entry
     declares origin 'new'. State and requests live in debts.svelte.js. */
  import { serverState } from '../lib/serverState.svelte.js';
  import DebtTermRow from './DebtTermRow.svelte';
  import { blankDebtTerm } from './debtTerms.js';
  import {
    debtsState, loadDebts, newDebtDraft, saveDebtDraft, repayDebt, forgiveDebt,
  } from './debts.svelte.js';

  $effect(() => {
    debtsState.draft = null;
    loadDebts(serverState.worldId);
  });

  /** The tab's « + Nouvelle dette » (creation_island.py rule 11). */
  export function primaryAction() {
    newDebtDraft();
  }

  let draft = $derived(debtsState.draft);
  let choices = $derived(debtsState.choices);
  let factionIds = $derived(new Set((choices?.factions || []).map((f) => f.id)));
  let creditorIsFaction = $derived(draft ? factionIds.has(draft.creditor_entity_id) : false);
  let members = $derived(draft && creditorIsFaction ? (choices?.members?.[draft.creditor_entity_id] || []) : []);
  let notes = $state({});

  function setCreditor(id) {
    draft.creditor_entity_id = id;
    draft.contact_entity_id = '';
  }
</script>

<div class="debts">
  <div class="queue-panel debt-list">
    <div class="panel-head">
      <h2>Dettes du monde</h2>
      <span>{debtsState.debts.length}</span>
      <button class="btn-icon" onclick={() => loadDebts(serverState.worldId)} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if !serverState.worldId}
        <div class="empty">Aucun monde actif.</div>
      {:else if debtsState.loadError}
        <div class="empty" style="color:var(--red)">Erreur : {debtsState.loadError}</div>
      {:else if debtsState.debts.length === 0}
        <div class="empty">Aucune dette. « + Nouvelle dette » pour en écrire une.</div>
      {:else}
        {#each debtsState.debts as debt (debt.id)}
          <div class="row-card" class:closed={debt.status !== 'open'}>
            <strong>{debt.debtor_name} → {debt.creditor_name}</strong>
            {#if debt.contact_name}<span class="muted">(par {debt.contact_name})</span>{/if}
            <span class="badge b-other">{debt.status_label}</span>
            {#if debt.is_secret}<span class="badge b-other">secrète</span>{/if}
            <div class="muted">{debt.origin_label}{debt.reason ? ' — ' + debt.reason : ''} · valeur {debt.value}</div>
            <ul>
              {#each debt.terms as t, i (i)}<li>{t.line}</li>{/each}
              {#if debt.terms.length === 0}<li>une faveur</li>{/if}
            </ul>
            {#if debt.closed_note}<div class="muted">Note : {debt.closed_note}</div>{/if}
            {#if debt.status === 'open'}
              <div class="inline">
                <button onclick={() => repayDebt(serverState.worldId, debt.id)}>Rembourser</button>
                <input type="text" placeholder="Note (facultative)" bind:value={notes[debt.id]}>
                <button onclick={() => forgiveDebt(serverState.worldId, debt.id, notes[debt.id])}>Remettre</button>
              </div>
            {/if}
            {#if debtsState.actionError?.id === debt.id}<div class="r-err">{debtsState.actionError.message}</div>{/if}
          </div>
        {/each}
      {/if}
    </div>
  </div>

  {#if draft}
    <div class="queue-panel debt-editor">
      <div class="panel-head"><h2>Nouvelle dette</h2></div>
      <div class="queue-body">
        <label>Débiteur
          <select bind:value={draft.debtor_entity_id}>
            <option value="">—</option>
            {#each choices?.characters || [] as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
          </select>
        </label>
        <label>Créancier
          <select value={draft.creditor_entity_id} onchange={(e) => setCreditor(e.target.value)}>
            <option value="">—</option>
            {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
          </select>
        </label>
        {#if creditorIsFaction}
          <label>Contact (un membre)
            <select bind:value={draft.contact_entity_id}>
              <option value="">—</option>
              {#each members as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
            </select>
          </label>
        {/if}
        <label>Motif <input type="text" bind:value={draft.reason} placeholder="facultatif"></label>
        <label><input type="checkbox" bind:checked={draft.is_secret}> Transaction secrète</label>
        <h4>Ce qui est dû</h4>
        {#each draft.terms as term, k (k)}
          <DebtTermRow {term} {choices} onremove={() => draft.terms.splice(k, 1)} />
        {/each}
        <button onclick={() => draft.terms.push(blankDebtTerm())}>+ terme</button>
        {#if debtsState.saveError}<div class="r-err">{debtsState.saveError}</div>{/if}
        <div style="margin-top:10px">
          <button class="btn-send" disabled={debtsState.saving} onclick={() => saveDebtDraft(serverState.worldId)}>
            {debtsState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
          </button>
          <button onclick={() => (debtsState.draft = null)}>Annuler</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .debts { display: flex; gap: 12px; align-items: flex-start; }
  .debt-list { flex: 1; }
  .debt-editor { flex: 0 0 380px; }
  .debt-editor label { display: block; margin: 4px 0; }
  .debt-editor input[type="text"] { width: 100%; box-sizing: border-box; }
  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
  .row-card.closed { opacity: 0.7; }
  .row-card ul { margin: 4px 0 0 18px; padding: 0; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
</style>
