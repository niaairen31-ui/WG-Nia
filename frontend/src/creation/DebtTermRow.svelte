<script>
  /* TICKET-0110 (BRIEF-0110-C). One owed term of a debt: its currency, its
     target, its amount when the currency counts one. `term` is a draft
     object its owner keeps (Création › Dettes, Journée's service form). */
  import { DEBT_CURRENCY_FORMS, debtTargetOptions } from './debtTerms.js';

  let { term, choices, onremove } = $props();

  let form = $derived(DEBT_CURRENCY_FORMS[term.currency]);
  let options = $derived(debtTargetOptions(term.currency, choices));
  let targetKey = $derived(term.currency === 'item' ? 'item_id' : term.currency === 'fact' ? 'fact_id' : 'skill_key');

  function setCurrency(currency) {
    term.currency = currency;
    term.item_id = '';
    term.fact_id = '';
    term.skill_key = '';
    term.amount = DEBT_CURRENCY_FORMS[currency].counted ? 1 : null;
  }
</script>

<div class="debt-term">
  <select value={term.currency} onchange={(e) => setCurrency(e.target.value)}>
    {#each Object.entries(DEBT_CURRENCY_FORMS) as [currency, f] (currency)}
      <option value={currency}>{f.label}</option>
    {/each}
  </select>
  {#if form.list}
    <select value={term[targetKey]} onchange={(e) => (term[targetKey] = e.target.value)}>
      <option value="">—</option>
      {#each options as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
    </select>
  {/if}
  {#if form.counted}
    <input type="number" min="1" style="width:70px" value={term.amount ?? ''}
           oninput={(e) => (term.amount = e.target.value === '' ? null : Number(e.target.value))}>
  {/if}
  <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
</div>

<style>
  .debt-term { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
  .debt-term select { max-width: 240px; }
</style>
