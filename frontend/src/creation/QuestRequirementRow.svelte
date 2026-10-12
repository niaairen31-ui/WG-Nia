<script>
  /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
     its target from the matching picker list, its threshold when the form
     takes one. `req` is a draft object owned by questOffersState.
     TICKET-0111: its subject first (P1), its value when the form compares
     to one. TICKET-0113: an `attribute` compares to what its attribute's
     kind takes -- a label, an integer (« ou plus »), or an entity (or anyone).
     TICKET-0114 (BRIEF-0114-E): an `event` takes the subject's role (or any),
     a count, a place, a window, and filters on the type's other roles. */
  import { EVENT_WINDOWS, REQUIREMENT_FORMS, attributeOf, attributeTargets, eventTypeOf, fillerOptions,
           subjectOptions, targetOptions, valueOptions } from './questRequirements.js';

  let { req, choices, onremove } = $props();

  let form = $derived(REQUIREMENT_FORMS[req.type]);
  let options = $derived(targetOptions(req.type, choices));
  let values = $derived(valueOptions(req.type, choices));
  let attr = $derived(req.type === 'attribute' ? attributeOf(req.target_key, choices) : null);
  let evType = $derived(req.type === 'event' ? eventTypeOf(req.target_key, choices) : null);

  function roleOf(roleId) {
    return evType?.roles.find((r) => r.id === roleId) || null;
  }

  function addFilter() {
    req.filters = [...(req.filters || []), { role_id: '', filler: '' }];
  }

  function setType(type) {
    req.type = type;
    req.target_entity_id = '';
    req.target_key = '';
    req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
    req.value = '';
    req.since = 'always';
    req.filters = [];
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
    if (req.type === 'event') {
      req.value = '';
      req.filters = [];
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
  {#if evType}
    <select value={req.value ?? ''} title="Son rôle dans l’événement"
            onchange={(e) => { req.value = e.target.value; }}>
      <option value="">— n’importe quel rôle —</option>
      {#each evType.roles as r (r.id)}
        <option value={r.id}>{r.name}</option>
      {/each}
    </select>
  {/if}
  {#if form.threshold}
    <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
           style="width:70px" value={req.threshold ?? ''}
           oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
    {#if req.type === 'event'}<span class="quest-req-hint">fois ou plus</span>{/if}
  {/if}
  {#if req.type === 'event'}
    <select value={req.target_entity_id ?? ''} title="Où"
            onchange={(e) => { req.target_entity_id = e.target.value; }}>
      <option value="">— n’importe où —</option>
      {#each choices?.locations || [] as l (l.id)}
        <option value={l.id}>{l.name}</option>
      {/each}
    </select>
    <select value={req.since || 'always'} title="Depuis quand"
            onchange={(e) => { req.since = e.target.value; }}>
      {#each Object.entries(EVENT_WINDOWS) as [since, label] (since)}
        <option value={since}>{label}</option>
      {/each}
    </select>
  {/if}
  <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
</div>
{#if evType}
  <div class="quest-req-filters">
    {#each req.filters || [] as f, i (i)}
      <div class="quest-req">
        <span class="quest-req-hint">avec</span>
        <select value={f.role_id} onchange={(e) => { f.role_id = e.target.value; f.filler = ''; }}>
          <option value="">— rôle —</option>
          {#each evType.roles.filter((r) => r.id !== req.value) as r (r.id)}
            <option value={r.id}>{r.name}</option>
          {/each}
        </select>
        <select value={f.filler} onchange={(e) => { f.filler = e.target.value; }}>
          <option value="">—</option>
          {#each fillerOptions(roleOf(f.role_id), choices) as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
        <button class="btn-icon" title="Retirer le filtre"
                onclick={() => { req.filters = req.filters.filter((_, j) => j !== i); }}>✕</button>
      </div>
    {/each}
    <button class="btn-ghost" onclick={addFilter}>+ filtrer sur un autre rôle</button>
  </div>
{/if}

<style>
  .quest-req { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
  .quest-req select { max-width: 260px; }
  .quest-req-hint { font-size: 12px; opacity: 0.7; }
  .quest-req-filters { margin-left: 24px; }
</style>
