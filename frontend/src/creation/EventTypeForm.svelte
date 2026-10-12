<script>
  /* TICKET-0114 (BRIEF-0114-B, B1, C1, D1, W1, X1). One event type as the
     creator edits it: its name and domain; whether it counts a quantity,
     enters the chronicle the models read, and whether its participants keep
     it secret by default; its roles in order -- each accepting entity types
     and, or, a sorte; who learns it besides its participants, each at a
     level. `draft` is a `typeDraft` owned by the caller -- the « Vocabulaire
     du monde » tab, or a proposal card (BRIEF-0114-G/H); `vocab` the
     vocabulary lists (`vocabState`). The server refuses taking away what is
     in use.

     TICKET-0119 (BRIEF-0119-B, M-c, D3, E1): its effects -- what an event of
     it does to the state of the world, each « role -> state = value »: a
     choice of the state, an integer set or added (`'add'`), or the entity of
     another role (`value_role`, for a state naming an entity). They
     pre-fill an event's proposal; the creator keeps, edits or drops each. */
  let { draft, vocab } = $props();

  function toggle(list, type) {
    const at = list.indexOf(type);
    if (at >= 0) list.splice(at, 1);
    else list.push(type);
  }

  function addRole() {
    draft.roles.push({ id: null, name: '', entity_types: ['character'], accepts_sorte: false });
  }

  function addScope() {
    draft.scopes.push({ kind: 'location', role: null, level: 'knows' });
  }

  const withRole = (kind) => kind === 'rencontre' || kind === 'faction';

  function stateOf(key) {
    return (vocab.states || []).find((s) => s.key === key) || null;
  }

  function roleTypes(name) {
    const role = draft.roles.find((r) => r.name === name);
    return role ? role.entity_types : [];
  }

  // The states that apply to an entity the role holds.
  function statesFor(roleName) {
    const types = roleTypes(roleName);
    return (vocab.states || []).filter((s) => s.holder_types === null || s.holder_types.some((t) => types.includes(t)));
  }

  // value_role: for a state naming an entity, the other roles whose entities it may name.
  function valueRoles(effect, state) {
    return draft.roles.filter((r) => r.name && r.name !== effect.role
      && r.entity_types.some((t) => state.value_types.includes(t)));
  }

  function addEffect() {
    const role = draft.roles.find((r) => r.name && r.entity_types.length);
    if (!draft.effects) draft.effects = [];
    draft.effects.push({ role: role ? role.name : '', attribute: '', mode: 'set', value: null });
  }

  function onState(effect) {
    const state = stateOf(effect.attribute);
    effect.mode = 'set';
    effect.value = state && state.kind === 'choice' && state.choices.length ? state.choices[0].value
      : state && state.kind === 'integer' ? 1 : null;
  }
</script>

<div class="etype-form">
  <label>Nom <input type="text" bind:value={draft.name} placeholder="Tuer, Repérer, Pacte…"></label>
  <label>Domaine
    <select bind:value={draft.domain}>
      {#each vocab.domains as d (d.value)}<option value={d.value}>{d.label}</option>{/each}
    </select>
  </label>
  <label class="etype-check"><input type="checkbox" bind:checked={draft.counts_quantity}>
    Compte une quantité (« 3 loups »)</label>
  <label class="etype-check"><input type="checkbox" bind:checked={draft.in_chronicle}>
    Entre dans la chronique que lisent le MJ et le monde</label>
  <label class="etype-check"><input type="checkbox" bind:checked={draft.participants_secret}>
    Par défaut, les participants gardent le secret</label>

  <div class="etype-block">
    <span>Rôles</span>
    {#each draft.roles as role, k (k)}
      <div class="etype-role">
        <div class="etype-line">
          <input type="text" bind:value={role.name} placeholder="tueur, victime, lieu…">
          <button class="btn-icon" title="Retirer le rôle" onclick={() => draft.roles.splice(k, 1)}>✕</button>
        </div>
        <div class="etype-types">
          {#each vocab.entityTypes as t (t.type)}
            <label class="etype-check"><input type="checkbox" checked={role.entity_types.includes(t.type)}
                   onchange={() => toggle(role.entity_types, t.type)}> {t.label}</label>
          {/each}
          <label class="etype-check"><input type="checkbox" bind:checked={role.accepts_sorte}> une sorte</label>
        </div>
      </div>
    {/each}
    <button onclick={addRole}>+ rôle</button>
  </div>

  <div class="etype-block">
    <span>Qui l'apprend, en plus des participants</span>
    {#each draft.scopes as scope, k (k)}
      <div class="etype-line">
        <select bind:value={scope.kind}>
          {#each vocab.scopeKinds as s (s.value)}<option value={s.value}>{s.label}</option>{/each}
        </select>
        {#if withRole(scope.kind)}
          <select bind:value={scope.role}>
            <option value={null}>— rôle —</option>
            {#each draft.roles as role, r (r)}<option value={role.name}>{role.name}</option>{/each}
          </select>
        {/if}
        <select bind:value={scope.level}>
          {#each vocab.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
        </select>
        <button class="btn-icon" title="Retirer" onclick={() => draft.scopes.splice(k, 1)}>✕</button>
      </div>
    {/each}
    {#if !draft.scopes.length}<div class="etype-hint">Personne d'autre que les participants.</div>{/if}
    <button onclick={addScope}>+ portée</button>
  </div>

  <div class="etype-block">
    <span>Ce qu'il change dans le monde (pré-rempli sur chaque événement)</span>
    {#each draft.effects || [] as effect, k (k)}
      {@const state = stateOf(effect.attribute)}
      <div class="etype-line">
        <select bind:value={effect.role} title="Le rôle dont l'entité change">
          <option value="">— rôle —</option>
          {#each draft.roles.filter((r) => r.name && r.entity_types.length) as role, r (r)}
            <option value={role.name}>{role.name}</option>
          {/each}
        </select>
        <select bind:value={effect.attribute} onchange={() => onState(effect)} title="L'état">
          <option value="">— état —</option>
          {#each statesFor(effect.role) as s (s.key)}<option value={s.key}>{s.name}</option>{/each}
        </select>
        {#if state && state.kind === 'choice'}
          <select bind:value={effect.value}>
            {#each state.choices as c (c.value)}<option value={c.value}>{c.label}</option>{/each}
          </select>
        {:else if state && state.kind === 'integer'}
          <select bind:value={effect.mode}>
            <option value="set">devient</option>
            <option value={'add'}>augmente de</option>
          </select>
          <input type="number" style="width:70px" bind:value={effect.value}>
        {:else if state && state.kind === 'entity'}
          <select bind:value={effect.value} title="value_role : l'entité d'un autre rôle">
            <option value={null}>— rôle —</option>
            {#each valueRoles(effect, state) as role, r (r)}<option value={role.name}>{role.name}</option>{/each}
          </select>
        {/if}
        <button class="btn-icon" title="Retirer" onclick={() => draft.effects.splice(k, 1)}>✕</button>
      </div>
    {/each}
    {#if !(draft.effects || []).length}<div class="etype-hint">Aucun état ne change.</div>{/if}
    <button onclick={addEffect}>+ effet</button>
  </div>
</div>

<style>
  .etype-form label { display: block; margin: 4px 0; }
  .etype-form input[type="text"] { width: 100%; box-sizing: border-box; }
  .etype-block { margin: 8px 0; }
  .etype-block > span { display: block; font-size: 12px; color: var(--muted); }
  .etype-role { border-left: 2px solid var(--border, #444); padding-left: 6px; margin: 4px 0; }
  .etype-line { display: flex; gap: 6px; align-items: center; margin: 2px 0; }
  .etype-line input[type="text"] { flex: 1; }
  .etype-types { display: flex; flex-wrap: wrap; }
  .etype-check { display: inline-flex !important; gap: 4px; align-items: center; margin-right: 10px !important; }
  .etype-hint { font-size: 12px; color: var(--muted); }
</style>
