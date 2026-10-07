<script>
  /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
     its target from the matching picker list, its threshold when the form
     takes one. `req` is a draft object owned by questOffersState. */
  import { REQUIREMENT_FORMS, targetOptions } from './questRequirements.js';

  let { req, choices, onremove } = $props();

  let form = $derived(REQUIREMENT_FORMS[req.type]);
  let options = $derived(targetOptions(req.type, choices));

  function setType(type) {
    req.type = type;
    req.target_entity_id = '';
    req.target_key = '';
    req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
  }

  function setTarget(value) {
    if (form.column === 'entity') req.target_entity_id = value;
    else req.target_key = value;
  }
</script>

<div class="quest-req">
  <select value={req.type} onchange={(e) => setType(e.target.value)}>
    {#each Object.entries(REQUIREMENT_FORMS) as [type, f] (type)}
      <option value={type}>{f.label}</option>
    {/each}
  </select>
  {#if form.list !== 'money'}
    <select value={form.column === 'entity' ? req.target_entity_id : req.target_key}
            onchange={(e) => setTarget(e.target.value)}>
      <option value="">—</option>
      {#each options as o (o.value)}
        <option value={o.value}>{o.label}</option>
      {/each}
    </select>
  {/if}
  {#if form.threshold}
    <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
           style="width:70px" value={req.threshold ?? ''}
           oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
  {/if}
  <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
</div>

<style>
  .quest-req { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
  .quest-req select { max-width: 260px; }
</style>
