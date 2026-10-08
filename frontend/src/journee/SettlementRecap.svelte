<script>
  /* TICKET-0109 (BRIEF-0109-D, D1/G1). What « déclarer accomplie » shows
     before Nia decides: the measured context of one quest (its steps and
     their outcomes, the days that advanced it, the step changes still
     awaiting review, its terms and their value) and why it cannot be
     settled now, if it cannot. Nothing here is a verdict: she decides. The
     quest is named by its quest_id only. TICKET-0110 (A2): when coins or
     items are all that is lacking, « Régler à crédit » shows what would be
     owed to whom -- a faction creditor's member to pick, its contact
     preselected -- and settles with the rest as debts. TICKET-0111 (M1):
     each step's completion condition, judged line by line -- measured, never
     a verdict: Nia still decides. */
  import { questState, settleQuest, settleOnCredit } from './quests.svelte.js';
  import { loadJourneeDebts } from './debts.svelte.js';

  let { questId } = $props();

  let ctx = $derived(questState.settlement);
  let contacts = $state({});
  let creditSecret = $state(false);

  function contactOf(debt) {
    return contacts[debt.creditor_id] ?? debt.contact_id ?? '';
  }

  async function onCredit() {
    const chosen = Object.fromEntries((ctx.credit.debts || []).filter((d) => d.is_faction && contactOf(d))
      .map((d) => [d.creditor_id, contactOf(d)]));
    await settleOnCredit(questId, chosen, creditSecret);
    await loadJourneeDebts();
  }
</script>

<div class="recap">
  {#if questState.settlementError}
    <div class="r-err">{questState.settlementError}</div>
  {:else if !ctx}
    <div class="empty"><span class="spin">⟳</span></div>
  {:else}
    <h5>Étapes</h5>
    <ol>
      {#each ctx.steps as step (step.order)}
        <li>{step.objective} — {step.status}{#if step.outcome} <span class="muted">({step.outcome})</span>{/if}
          {#each step.completion || [] as line, i (i)}
            <div class="muted" style={'padding-left:' + line.depth * 14 + 'px'}>
              {line.mark} {line.text}{#if line.progress} — {line.progress}{/if}
            </div>
          {/each}
        </li>
      {/each}
    </ol>

    <h5>Journées qui l'ont avancée</h5>
    {#if ctx.days.length === 0}<p class="muted">Aucune.</p>{/if}
    {#each ctx.days as day (day.day_number)}
      <div class="day">
        <strong>Jour {day.day_number}</strong> — {day.declared_action}
        {#if day.rewritten && day.rewritten !== day.declared_action}<div class="muted">lu : {day.rewritten}</div>{/if}
        {#each day.steps as s}<div class="muted">{s.objective} : {s.band}</div>{/each}
      </div>
    {/each}
    {#if ctx.pending_reviews > 0}
      <p class="r-err">{ctx.pending_reviews} changement(s) d'étape attendent encore la revue.</p>
    {/if}

    <h5>Ce qui sera appliqué</h5>
    {#if ctx.terms.length === 0}<p class="muted">Aucun coût ni récompense.</p>{/if}
    <ul>
      {#each ctx.terms as t}
        <li><span class="badge b-other">{t.direction === 'cost' ? 'coût' : 'récompense'}</span> {t.line}
          {#if t.note}<span class="muted"> — {t.note}</span>{/if}</li>
      {/each}
    </ul>
    <p class="muted">Valeur indicative : coût {ctx.value.cost}, récompense {ctx.value.reward} — {ctx.value.verdict_label}</p>

    {#each ctx.refusals as reason}<div class="r-err">Impossible : {reason}</div>{/each}
    <button class="btn-send" disabled={!ctx.can_settle || questState.busy !== null} onclick={() => settleQuest(questId)}>
      {questState.busy === questId ? 'Règlement…' : 'Confirmer : quête accomplie'}
    </button>

    {#if ctx.credit?.possible}
      <h5>Régler à crédit</h5>
      <p class="muted">Vous payez ce que vous avez ; le reste devient une dette.</p>
      {#each ctx.credit.debts as debt (debt.creditor_id)}
        <div class="credit">
          <strong>Envers {debt.creditor_name}</strong> : {debt.lines.join(', ')}
          {#if debt.is_faction}
            <label>Lié à
              <select value={contactOf(debt)} onchange={(e) => (contacts[debt.creditor_id] = e.target.value)}>
                <option value="">— un membre</option>
                {#each debt.members as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
              </select>
            </label>
          {/if}
        </div>
      {/each}
      <label><input type="checkbox" bind:checked={creditSecret}> Transaction secrète</label>
      <button disabled={questState.busy !== null} onclick={() => onCredit()}>Confirmer : régler à crédit</button>
    {/if}
  {/if}
</div>

<style>
  .recap { border-left: 2px solid var(--border); margin: 6px 0; padding: 4px 0 4px 8px; }
  h5 { margin: 8px 0 2px; font-size: 12px; color: var(--muted); }
  ol, ul { margin: 2px 0 4px 18px; padding: 0; }
  .day { margin: 2px 0 4px; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  .credit { margin: 2px 0 4px; }
  .credit label { display: inline-flex; gap: 4px; margin-left: 8px; }
</style>
