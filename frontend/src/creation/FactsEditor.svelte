<script>
  /* TICKET-0091 (BRIEF-0091-F). The sheet's descriptive-lore editor: one
     block per facet of the registry (GET /api/facets, loaded once) whose
     family fits the entity type -- character: identite + interiorite;
     faction: identite + collectif; location: identite + coutume; any other
     type (item, runtime types): description and appellation (TICKET-0092,
     BRIEF-0092-e). Labels come from the
     registry, never from this file.

     EXISTING entity: the facts are read from GET /api/entities/{id}/facts
     and every write is immediate, through the C-12 routes -- a bloc facet is
     one textarea, saved with POST when it has no fact yet, else PUT
     /api/facts/{id}/content; an affirmation facet is one line per fact,
     edited (PUT), deleted (DELETE) or added (POST). A coutume line carries
     an aspect (registry aspects as a datalist) and a "caché" toggle, which
     maps to scope {"scope_type": "none"} -- no default knowledge.

     NEW entity: the same blocks write into factsDraft.svelte.js's shared
     factsDraftState, sent by Sheet.svelte's submitEntity as the create
     body's `facets`. No network write here in create mode.

     Errors show the route's detail. Creator-only: nothing here renders in
     Play. */
  import { api } from './sheetRequest.svelte.js';
  import { factsDraftState } from './factsDraft.svelte.js';

  let { isNew, entityId, entityType } = $props();

  let registry = $state(null);
  let facts = $state([]);
  let buffers = $state({});
  let adds = $state({});
  let error = $state('');

  const TYPE_FAMILIES = {
    character: ['identite', 'interiorite'],
    faction: ['identite', 'collectif'],
    location: ['identite'],
  };

  const shownFacets = $derived.by(() => {
    if (!registry) return [];
    const families = TYPE_FAMILIES[entityType];
    return registry.filter((f) => (families
      ? families.includes(f.family) || (entityType === 'location' && f.name === 'coutume')
      : f.name === 'description' || f.name === 'appellation'));
  });

  async function loadRegistry() {
    try {
      const facets = (await api('/api/facets')).facets;
      adds = Object.fromEntries(facets.map((f) => [f.name, blankAdd()]));
      registry = facets;
    } catch (e) {
      error = e.message;
    }
  }

  async function loadFacts(id) {
    try {
      const data = await api(`/api/entities/${encodeURIComponent(id)}/facts`);
      facts = data.facts;
      buffers = Object.fromEntries(data.facts.map((f) => [f.fact_id, f.content]));
      for (const name of Object.keys(adds)) adds[name] = blankAdd();
      error = '';
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => { loadRegistry(); });

  $effect(() => {
    if (!isNew && entityId) loadFacts(entityId);
  });

  function factsOf(name) {
    return facts.filter((f) => f.facet === name);
  }

  function isHidden(fact) {
    return fact.scopes.length === 0;
  }

  async function write(path, method, body) {
    try {
      const opts = { method };
      if (body) {
        opts.headers = { 'Content-Type': 'application/json' };
        opts.body = JSON.stringify(body);
      }
      await api(path, opts);
      await loadFacts(entityId);
    } catch (e) {
      error = e.message;
    }
  }

  function saveBloc(spec) {
    const existing = factsOf(spec.name)[0];
    if (existing) {
      write(`/api/facts/${encodeURIComponent(existing.fact_id)}/content`, 'PUT', { content: buffers[existing.fact_id] });
    } else {
      write(`/api/entities/${encodeURIComponent(entityId)}/facts`, 'POST',
        { facet: spec.name, content: adds[spec.name].content });
    }
  }

  function saveLine(fact) {
    write(`/api/facts/${encodeURIComponent(fact.fact_id)}/content`, 'PUT', { content: buffers[fact.fact_id] });
  }

  function deleteLine(fact) {
    write(`/api/facts/${encodeURIComponent(fact.fact_id)}`, 'DELETE', null);
  }

  function addLine(spec) {
    const draft = adds[spec.name];
    const body = { facet: spec.name, content: draft.content };
    if (spec.name === 'coutume') {
      if ((draft.aspect || '').trim()) body.aspect = draft.aspect.trim();
      if (draft.hidden) body.scope = { scope_type: 'none' };
    }
    write(`/api/entities/${encodeURIComponent(entityId)}/facts`, 'POST', body);
  }

  function blankAdd() {
    return { content: '', aspect: '', hidden: false };
  }

  // Create mode: factsDraftState.facets[name] is a string (bloc), a
  // string list (affirmation) or a {aspect, content, hidden} list (coutume).
  function draftList(name) {
    const value = factsDraftState.facets[name];
    return Array.isArray(value) ? value : [];
  }

  function draftAdd(name) {
    const row = name === 'coutume' ? { aspect: '', content: '', hidden: false } : '';
    factsDraftState.facets[name] = [...draftList(name), row];
  }

  function draftRemove(name, i) {
    factsDraftState.facets[name] = draftList(name).filter((_, idx) => idx !== i);
  }

  function draftSetLine(name, i, value) {
    const list = [...draftList(name)];
    list[i] = value;
    factsDraftState.facets[name] = list;
  }
</script>

{#if error}
  <div class="author-status err" style="margin-bottom:6px">{error}</div>
{/if}
{#if !registry}
  <div class="empty"><span class="spin">⟳</span></div>
{:else}
  {#each shownFacets as spec (spec.name)}
    <div class="field-row" style="margin-bottom:8px">
      <label>{spec.label}</label>
      {#if spec.aspects.length}
        <datalist id="facet-aspects-{spec.name}">
          {#each spec.aspects as a}<option value={a}></option>{/each}
        </datalist>
      {/if}

      {#if spec.granularity === 'bloc'}
        {#if isNew}
          <textarea rows="2" value={factsDraftState.facets[spec.name] || ''}
            oninput={(e) => factsDraftState.facets[spec.name] = e.currentTarget.value}></textarea>
        {:else}
          {@const existing = factsOf(spec.name)[0]}
          {#if existing}
            <textarea rows="2" bind:value={buffers[existing.fact_id]}></textarea>
          {:else}
            <textarea rows="2" bind:value={adds[spec.name].content}></textarea>
          {/if}
          <div class="row-card-actions" style="margin-top:4px">
            <button class="btn-send" onclick={() => saveBloc(spec)}>💾 Enregistrer</button>
          </div>
        {/if}

      {:else if isNew}
        {#each draftList(spec.name) as line, i}
          <div style="display:flex; gap:6px; align-items:center; margin-bottom:4px">
            {#if spec.name === 'coutume'}
              <input type="text" list="facet-aspects-coutume" placeholder="aspect" style="flex:1" bind:value={line.aspect}>
              <input type="text" style="flex:3" bind:value={line.content}>
              <label style="display:flex; align-items:center; gap:4px; font-size:12px">
                <input type="checkbox" bind:checked={line.hidden}> caché</label>
            {:else}
              <input type="text" style="flex:1" value={line}
                oninput={(e) => draftSetLine(spec.name, i, e.currentTarget.value)}>
            {/if}
            <button class="btn-icon" title="Supprimer" onclick={() => draftRemove(spec.name, i)}>✕</button>
          </div>
        {/each}
        <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={() => draftAdd(spec.name)}>+ Ajouter</button>

      {:else}
        {#each factsOf(spec.name) as fact (fact.fact_id)}
          <div style="display:flex; gap:6px; align-items:center; margin-bottom:4px">
            {#if spec.name === 'coutume'}
              <span style="flex:1; font-size:12px; color:var(--muted)">{fact.aspect || '—'}{isHidden(fact) ? ' · caché' : ''}</span>
            {/if}
            <input type="text" style="flex:3" bind:value={buffers[fact.fact_id]}>
            <button class="btn-icon" title="Enregistrer" onclick={() => saveLine(fact)}>💾</button>
            <button class="btn-icon" title="Supprimer" onclick={() => deleteLine(fact)}>✕</button>
          </div>
        {/each}
        <div style="display:flex; gap:6px; align-items:center">
          {#if spec.name === 'coutume'}
            <input type="text" list="facet-aspects-coutume" placeholder="aspect" style="flex:1" bind:value={adds[spec.name].aspect}>
          {/if}
          <input type="text" placeholder="Nouvelle ligne" style="flex:3" bind:value={adds[spec.name].content}>
          {#if spec.name === 'coutume'}
            <label style="display:flex; align-items:center; gap:4px; font-size:12px">
              <input type="checkbox" bind:checked={adds[spec.name].hidden}> caché</label>
          {/if}
          <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={() => addLine(spec)}>+ Ajouter</button>
        </div>
      {/if}
    </div>
  {/each}
{/if}
