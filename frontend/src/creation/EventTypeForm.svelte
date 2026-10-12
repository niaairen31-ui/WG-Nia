<script>
  /* TICKET-0114 (BRIEF-0114-B, B1, C1, D1, W1, X1). One event type as the
     creator edits it: its name and domain; whether it counts a quantity,
     enters the chronicle the models read, and whether its participants keep
     it secret by default; its roles in order -- each accepting entity types
     and, or, a sorte; who learns it besides its participants, each at a
     level. `draft` is a `typeDraft` owned by the caller -- the « Vocabulaire
     du monde » tab, or a proposal card (BRIEF-0114-G/H); `vocab` the
     vocabulary lists (`vocabState`). The server refuses taking away what is
     in use. */
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
