<script>
  /* TICKET-0110 (BRIEF-0110-D, J2, D1). Journée › Dettes: what the player
     owes and what is owed to him -- the other party (a faction's contact
     named), the origin and motive, what is owed line by line, its value
     in the world's unit, its state. An open debt shows why it cannot be
     repaid now, if it cannot, « Rembourser » (all at once) and
     « Remettre » with an optional note. Nothing is ever deleted. */
  import { debtState, loadJourneeDebts, repay, forgive } from './debts.svelte.js';

  let notes = $state({});
  let sections = $derived([
    { title: 'Ce que je dois', list: debtState.owes, other: (d) => d.creditor_name },
    { title: 'Ce qu’on me doit', list: debtState.owed, other: (d) => d.debtor_name },
  ]);
</script>

<div class="queue-panel" id="journee-debt-panel">
  <div class="panel-head">
    <h2>Dettes</h2>
    <button class="btn-icon" onclick={() => loadJourneeDebts()} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if debtState.loadError}<div class="r-err">{debtState.loadError}</div>{/if}
    {#if debtState.actionError}<div class="r-err">{debtState.actionError}</div>{/if}
    {#each sections as section (section.title)}
      <h4>{section.title}</h4>
      {#if section.list.length === 0}<p class="muted">Aucune.</p>{/if}
      {#each section.list as debt (debt.id)}
        <div class="row-card" class:over={debt.status !== 'open'}>
          <strong>{section.other(debt)}</strong>
          {#if debt.contact_name}<span class="muted">(par {debt.contact_name})</span>{/if}
          <span class="badge b-other">{debt.status_label}</span>
          {#if debt.is_secret}<span class="badge b-other">secrète</span>{/if}
          <div class="muted">{debt.origin_label}{debt.reason ? ' — ' + debt.reason : ''} · valeur {debt.value}</div>
          <ul class="terms">
            {#each debt.terms as t, i (i)}<li>{t.line}</li>{/each}
            {#if debt.terms.length === 0}<li>une faveur</li>{/if}
          </ul>
          {#if debt.closed_note}<div class="muted">Note : {debt.closed_note}</div>{/if}
          {#if debt.status === 'open'}
            {#each debt.refusals as reason}<div class="muted">Pas encore : {reason}</div>{/each}
            <div class="inline">
              <button disabled={!debt.repayable || debtState.busy !== null} onclick={() => repay(debt.id)}>
                {debtState.busy === debt.id ? '…' : 'Rembourser'}
              </button>
              <input type="text" placeholder="Note (facultative)" bind:value={notes[debt.id]}>
              <button disabled={debtState.busy !== null} onclick={() => forgive(debt.id, notes[debt.id])}>Remettre</button>
            </div>
          {/if}
        </div>
      {/each}
    {/each}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
  .terms { margin: 2px 0 6px 18px; padding: 0; font-size: 12px; }
  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .over { opacity: 0.7; }
</style>
