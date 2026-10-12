<script>
  /* TICKET-0119 (BRIEF-0119-D; decisions H1, Y2 and M-c of the conditions
     series). The ONE event editor: the journal's sheet (Evenements.svelte),
     the review card of a proposed event (QueueCard.svelte) and Lore's events
     (BRIEF-0119-G) render it on a draft of eventDraft.svelte.js's shape.

     What it edits: the event's type (one of the world's, unless `typeFixed`;
     a type proposed with the event, `draft.newType`, shows its roles and
     stays as proposed), with `withText` its title, description and place;
     its quantity when the type counts; its participants role by role -- an
     entity of a type the role accepts, or a sorte (a new one by name on a
     card) -- each entity keeping the event secret or not (X1; never a player
     character, INV-07: no box is offered, and the server forces it); who
     learns it besides them (the type's scopes, or its own, W1); and what it
     changes in the world (`draft.changes`, M-c): pre-filled from the type's
     effects (« Pré-remplir », POST /api/events/changes), each kept, edited or
     dropped, and new ones added -- an entity, a state that applies to it, a
     value of the state's kind (an integer set or added, D3). `withChanges`
     off (a correction from the journal) hides them: a correction changes no
     state.

     `entities` are the world's ({id, name, type}); `playerCharIds` a Set of
     the player characters' ids. The types, sortes, levels and states come
     from the shared vocabulary store (eventVocab.svelte.js). No scoped
     <style> block: it renders inside the Creation iframe document too. */
  import { vocabState } from './eventVocab.svelte.js';
  import { addParticipantTo, removeParticipantFrom, prefilledChanges } from './eventDraft.svelte.js';

  let {
    draft, entities = [], playerCharIds = null, typeFixed = false, withText = false, withChanges = true,
  } = $props();

  let prefillError = $state('');

  const SCOPE_TYPES = [
    { value: 'world', label: 'tout le monde' }, { value: 'location', label: 'ceux qui passent au lieu' },
    { value: 'rencontre', label: 'ceux qui ont rencontré' }, { value: 'faction', label: 'les membres de la faction' },
  ];

  let type = $derived(vocabState.types.find((t) => t.id === draft.typeId) || null);
  let roles = $derived(draft.newType
    ? (draft.newType.roles || []).map((r) => ({ id: null, name: r.name, entity_types: r.entity_types || [],
                                               accepts_sorte: !!r.accepts_sorte, status: 'active' }))
    : (type ? type.roles.filter((r) => r.status === 'active') : []));
  let counts = $derived(draft.newType ? !!draft.newType.counts_quantity : !!(type && type.counts_quantity));
  let defaultSecret = $derived(draft.newType ? !!draft.newType.participants_secret
    : !!(type && type.participants_secret));
  let activeSortes = $derived(vocabState.sortes.filter((s) => s.status === 'active'));
  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));
  let places = $derived((entities || []).filter((e) => e.type === 'location'));

  const inRole = (p, role) => (role.id ? p.role_id === role.id : !p.role_id && p.role === role.name);
  const isPlayer = (id) => !!(playerCharIds && playerCharIds.has && playerCharIds.has(id));

  function nameOf(id) {
    const e = (entities || []).find((x) => x.id === id);
    return e ? e.name : id;
  }

  function candidates(role) {
    return (entities || []).filter((e) => role.entity_types.includes(e.type));
  }

  function onAdd(role, ev) {
    const value = ev.currentTarget.value;
    ev.currentTarget.value = '';
    if (!value) return;
    const [kind, id] = value.split(':');
    const name = kind === 'sorte' ? (activeSortes.find((s) => s.id === id) || {}).name : nameOf(id);
    addParticipantTo(draft, role, kind, id, name, defaultSecret);
  }

  function onType() {
    // A new type keeps the participants whose role it has, by name.
    const next = vocabState.types.find((t) => t.id === draft.typeId);
    const byName = Object.fromEntries((next ? next.roles : []).filter((r) => r.status === 'active')
      .map((r) => [r.name, r]));
    draft.participants = draft.participants.filter((p) => byName[p.role]).map((p) => ({
      ...p, role_id: byName[p.role].id,
    }));
  }

  function scopeTargets(scopeType) {
    if (scopeType === 'location') return places;
    if (scopeType === 'faction') return (entities || []).filter((e) => e.type === 'faction');
    return entities || [];
  }

  function typeScopeLine() {
    if (!type || !type.scopes.length) return 'les participants seulement';
    return type.scopes.map((s) => `${s.kind}${s.role ? ' ' + s.role : ''} (${levelLabels[s.level] || s.level})`).join(' · ');
  }

  // --- what it changes in the world (M-c) ---
  function stateOf(key) {
    return (vocabState.states || []).find((s) => s.key === key) || null;
  }

  function statesFor(entityId) {
    const e = (entities || []).find((x) => x.id === entityId);
    return (vocabState.states || []).filter((s) => e && (s.holder_types === null || s.holder_types.includes(e.type)));
  }

  function valueEntities(state) {
    return (entities || []).filter((e) => state.value_types.includes(e.type));
  }

  function changeLine(c) {
    const state = stateOf(c.attribute);
    if (!state) return '';
    if (c.mode === 'add') return `${state.name} ${c.value >= 0 ? '+' : ''}${c.value}`;
    if (state.kind === 'choice') return `${state.name} -> ${(state.choices.find((x) => x.value === c.value) || {}).label || c.value}`;
    if (state.kind === 'entity') return `${state.name} -> ${c.value ? nameOf(c.value) : '(aucun)'}`;
    return `${state.name} -> ${c.value}`;
  }

  async function prefill() {
    prefillError = '';
    try {
      const found = await prefilledChanges(draft);
      const have = new Set(draft.changes.map((c) => `${c.entity_id}|${c.attribute}`));
      for (const c of found) if (!have.has(`${c.entity_id}|${c.attribute}`)) draft.changes.push(c);
      if (!found.length) prefillError = "Le type ne change rien pour ces participants.";
    } catch (e) {
      prefillError = e.message;
    }
  }

  function addChange() {
    draft.changes.push({ entity_id: '', attribute: '', mode: 'set', value: null });
  }

  function onChangeState(c) {
    const state = stateOf(c.attribute);
    c.mode = 'set';
    c.value = state && state.kind === 'choice' && state.choices.length ? state.choices[0].value
      : state && state.kind === 'integer' ? 0 : null;
  }
</script>

{#if withText}
  <div class="field-section"><div class="field-section-title">Événement</div>
    <label style="display:block">Titre <input type="text" style="width:100%" bind:value={draft.title}></label>
    <label style="display:block">Description
      <textarea rows="2" style="width:100%; resize:vertical" bind:value={draft.description}></textarea></label>
    <label style="display:block">Lieu
      <select bind:value={draft.locationId}>
        <option value={null}>— aucun —</option>
        {#each places as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
      </select>
    </label>
  </div>
{/if}

<div class="field-section"><div class="field-section-title">Type</div>
  {#if draft.newType}
    <strong>{draft.newType.name}</strong>
    <span class="badge b-other">nouveau type — validé avec l'événement</span>
  {:else}
    <select id="event-f-type_id" bind:value={draft.typeId} disabled={typeFixed} onchange={onType}>
      <option value="">— choisir un type —</option>
      {#each vocabState.types.filter((t) => t.status === 'active' || t.id === draft.typeId) as t (t.id)}
        <option value={t.id}>{t.name} ({t.domain_label})</option>
      {/each}
    </select>
    {#if typeFixed}<span style="color:var(--muted); font-size:12px;"> Le type d'un événement ne change pas.</span>{/if}
  {/if}
  {#if counts}
    <label style="display:block; margin-top:6px">Quantité
      <input id="event-f-quantity" type="number" min="1" style="width:90px" bind:value={draft.quantity}>
    </label>
  {/if}
</div>

{#if roles.length}
  <div class="field-section"><div class="field-section-title">Participants</div>
    {#each roles as role (role.id || role.name)}
      <div style="margin:4px 0">
        <strong>{role.name}</strong>
        {#each draft.participants as p, i (i)}
          {#if inRole(p, role)}
            <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
              {p.sorte_id || p.sorte_name ? 'sorte : ' : ''}{p.name || p.sorte_name || '« inconnu »'}
              {#if !p.sorte_id && !p.sorte_name && p.entity_id && !isPlayer(p.entity_id)}
                <label title="Il garde le secret"><input type="checkbox" bind:checked={p.secret}> secret</label>
              {/if}
              {#if !p.saved}
                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeParticipantFrom(draft, i)}>✕</button>
              {/if}
            </span>
          {/if}
        {/each}
        <select onchange={(ev) => onAdd(role, ev)}>
          <option value="">— ajouter —</option>
          {#each candidates(role) as e (e.id)}<option value={'entity:' + e.id}>{e.name}</option>{/each}
          {#if role.accepts_sorte}
            {#each activeSortes as s (s.id)}<option value={'sorte:' + s.id}>sorte : {s.name}</option>{/each}
          {/if}
        </select>
      </div>
    {/each}
  </div>

  <div class="field-section"><div class="field-section-title">Qui l'apprend, en plus des participants</div>
    <label><input type="checkbox" bind:checked={draft.customScopes}> Choisir pour cet événement</label>
    {#if !draft.customScopes}
      <div style="color:var(--muted); font-size:12px;">Celle du type : {typeScopeLine()}</div>
    {:else}
      {#each draft.scopes as scope, k (k)}
        <div style="display:flex; gap:6px; align-items:center; margin:2px 0">
          <select bind:value={scope.scope_type} onchange={() => (scope.scope_id = null)}>
            {#each SCOPE_TYPES as st (st.value)}<option value={st.value}>{st.label}</option>{/each}
          </select>
          {#if scope.scope_type !== 'world'}
            <select bind:value={scope.scope_id}>
              <option value={null}>— choisir —</option>
              {#each scopeTargets(scope.scope_type) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
            </select>
          {/if}
          <select bind:value={scope.level}>
            {#each vocabState.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
          </select>
          <button class="btn-icon" title="Retirer" onclick={() => draft.scopes.splice(k, 1)}>✕</button>
        </div>
      {/each}
      {#if !draft.scopes.length}<div style="color:var(--muted); font-size:12px;">Personne d'autre.</div>{/if}
      <button onclick={() => draft.scopes.push({ scope_type: 'world', scope_id: null, level: 'knows' })}>+ portée</button>
    {/if}
  </div>
{/if}

{#if withChanges && (roles.length || draft.changes.length)}
  <div class="field-section"><div class="field-section-title">Ce qu'il change dans le monde</div>
    {#each draft.changes as c, k (k)}
      {@const state = stateOf(c.attribute)}
      <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:2px 0">
        <select bind:value={c.entity_id}>
          <option value="">— entité —</option>
          {#each entities || [] as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
        </select>
        <select bind:value={c.attribute} onchange={() => onChangeState(c)}>
          <option value="">— état —</option>
          {#each statesFor(c.entity_id) as s (s.key)}<option value={s.key}>{s.name}</option>{/each}
        </select>
        {#if state && state.kind === 'choice'}
          <select bind:value={c.value}>
            {#each state.choices as x (x.value)}<option value={x.value}>{x.label}</option>{/each}
          </select>
        {:else if state && state.kind === 'integer'}
          <select bind:value={c.mode}>
            <option value="set">devient</option>
            <option value="add">augmente de</option>
          </select>
          <input type="number" style="width:70px" bind:value={c.value}>
        {:else if state && state.kind === 'entity'}
          <select bind:value={c.value}>
            <option value={null}>— personne —</option>
            {#each valueEntities(state) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
          </select>
        {/if}
        <span style="font-size:12px; color:var(--muted)">{changeLine(c)}</span>
        <button class="btn-icon" title="Retirer" onclick={() => draft.changes.splice(k, 1)}>✕</button>
      </div>
    {/each}
    {#if !draft.changes.length}<div style="color:var(--muted); font-size:12px;">Aucun état ne change.</div>{/if}
    <div style="display:flex; gap:6px; margin-top:4px">
      {#if !draft.newType && draft.typeId}<button onclick={prefill}>Pré-remplir depuis le type</button>{/if}
      <button onclick={addChange}>+ changement</button>
    </div>
    {#if prefillError}<div style="font-size:12px; color:var(--muted)">{prefillError}</div>{/if}
  </div>
{/if}
