<script>
  /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
     its target from the matching picker list, its threshold when the form
     takes one. `req` is a draft object owned by questOffersState.
     TICKET-0111: its subject first (P1), its value when the form compares
     to one. TICKET-0113: an `attribute` compares to what its attribute's
     kind takes -- a label, an integer (« ou plus »), or an entity (or anyone). */
  import { REQUIREMENT_FORMS, attributeOf, attributeTargets, subjectOptions, targetOptions,
           valueOptions } from './questRequirements.js';

  let { req, choices, onremove } = $props();

  let form = $derived(REQUIREMENT_FORMS[req.type]);
  let options = $derived(targetOptions(req.type, choices));
  let values = $derived(valueOptions(req.type, choices));
  let attr = $derived(req.type === 'attribute' ? attributeOf(req.target_key, choices) : null);

  function setType(type) {
    req.type = type;
    req.target_entity_id = '';
    req.target_key = '';
    req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
    req.value = '';
  }

  function setTarget(value) {
    if (form.column === 'entity') req.target_entity_id = value;
    else req.target_key = value;
    if (req.type === 'attribute') {
      const next = attributeOf(value, choices);
      req.value = '';
      req.target_entity_id = '';
      req.threshold = next && next.kind === 'integer' ? 1 : null;
    }
  }
</script>

<div class="quest-req">
  <select value={req.subject || 'role:doer'} title="Qui la condition juge"
          onchange={(e) => { req.subject = e.target.value; }}>
    {#each subjectOptions(choices, req) as o (o.value)}
      <option value={o.value}>{o.label}</option>
    {/each}
  </select>
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
  {#if form.values}
    <select value={req.value ?? ''} onchange={(e) => { req.value = e.target.value; }}>
      <option value="">—</option>
      {#each values as v (v.value)}
        <option value={v.value}>{v.label}</option>
      {/each}
    </select>
  {/if}
  {#if attr && attr.kind === 'choice'}
    <select value={req.value ?? ''} onchange={(e) => { req.value = e.target.value; }}>
      <option value="">—</option>
      {#each attr.choices as c (c.value)}
        <option value={c.value}>{c.label}</option>
      {/each}
    </select>
  {:else if attr && attr.kind === 'integer'}
    <input type="number" style="width:70px" title="ou plus" value={req.threshold ?? ''}
           oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
    <span class="quest-req-hint">ou plus</span>
  {:else if attr && attr.kind === 'entity'}
    <select value={req.target_entity_id ?? ''} onchange={(e) => { req.target_entity_id = e.target.value; }}>
      <option value="">— quelqu’un —</option>
      {#each attributeTargets(attr, choices) as o (o.value)}
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
  .quest-req-hint { font-size: 12px; opacity: 0.7; }
</style>
