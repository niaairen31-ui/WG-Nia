<script>
  /* TICKET-0109 (BRIEF-0109-D). One cost or reward of a quest offer: its
     currency, its target, its amount when the currency counts one, the
     knowledge level of a fact reward, and its counterparty (empty = the
     giver; a relation, a fact or a skill needs a character there). `term`
     is a draft object owned by questOffersState; `onchange` re-reads the
     offer's indicative value. */
  import { CURRENCY_FORMS, termTargetOptions } from './questTerms.js';

  let { term, choices, onremove, onchange } = $props();

  let form = $derived(CURRENCY_FORMS[term.currency]);
  let options = $derived(termTargetOptions(term.currency, choices));
  let targetKey = $derived(term.currency === 'item' ? 'item_id' : term.currency === 'fact' ? 'fact_id' : 'skill_key');

  function set(field, value) {
    term[field] = value;
    onchange();
  }

  function setCurrency(currency) {
    term.currency = currency;
    term.item_id = '';
    term.fact_id = '';
    term.skill_key = '';
    term.level = '';
    term.amount = CURRENCY_FORMS[currency].counted ? 1 : null;
    onchange();
  }
</script>

<div class="quest-term">
  <select value={term.currency} onchange={(e) => setCurrency(e.target.value)}>
    {#each Object.entries(CURRENCY_FORMS) as [currency, f] (currency)}
      <option value={currency}>{f.label}</option>
    {/each}
  </select>
  {#if form.list}
    <select value={term[targetKey]} onchange={(e) => set(targetKey, e.target.value)}>
      <option value="">—</option>
      {#each options as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
    </select>
  {/if}
  {#if form.counted}
    <input type="number" min="1" style="width:70px" value={term.amount ?? ''}
           oninput={(e) => set('amount', e.target.value === '' ? null : Number(e.target.value))}>
  {/if}
  {#if term.currency === 'fact' && term.direction === 'reward'}
    <select value={term.level} onchange={(e) => set('level', e.target.value)}>
      <option value="">knows</option>
      {#each (choices?.fact_levels || []).filter((l) => l !== 'knows') as l}<option value={l}>{l}</option>{/each}
    </select>
  {/if}
  <select value={term.counterparty_entity_id} title={form.personal ? 'Un personnage' : 'Le donneur, ou un autre'}
          onchange={(e) => set('counterparty_entity_id', e.target.value)}>
    <option value="">le donneur</option>
    {#each (form.personal ? choices?.characters : choices?.givers) || [] as g (g.id)}
      <option value={g.id}>{g.name}</option>
    {/each}
  </select>
  <button class="btn-icon" title="Retirer" onclick={() => { onremove(); onchange(); }}>✕</button>
</div>

<style>
  .quest-term { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
  .quest-term select { max-width: 240px; }
</style>
