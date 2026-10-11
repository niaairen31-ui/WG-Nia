<script>
  /* TICKET-0113 (BRIEF-0113-C, WA3, WB2, WC1, WH1). One attribute
     definition as the creator edits it: its name, its kind (a choice among
     labels, an integer, another entity), the entity types it applies to,
     for an entity the types its value may name, its labels and default, and
     whether it is hidden from the player (off by default). `draft` is a
     `definitionDraft` owned by the caller -- the « États » island, or the
     interpreter's proposal card (BRIEF-0113-E); `types` the world's
     `{type, label}` list. A kind is fixed once the attribute is in use: the
     server refuses the change (WJ2). */
  let { draft, types } = $props();
  const group = 'attr-default-' + Math.random().toString(36).slice(2);

  function toggle(list, type) {
    const at = list.indexOf(type);
    if (at >= 0) list.splice(at, 1);
    else list.push(type);
  }

  function removeChoice(k) {
    const [gone] = draft.choices.splice(k, 1);
    if (gone && gone.label === draft.defaultLabel) draft.defaultLabel = draft.choices[0]?.label || '';
  }
</script>

<div class="attr-form">
  <label>Nom <input type="text" bind:value={draft.name} placeholder="Maudit, Ouvert, Occupé par…"></label>
  <label>Sorte
    <select bind:value={draft.kind}>
      <option value="choice">Un choix parmi des libellés</option>
      <option value="integer">Un nombre entier</option>
      <option value="entity">Une autre entité</option>
    </select>
  </label>
  <div class="attr-types">
    <span>S'applique à</span>
    {#each types as t (t.type)}
      <label class="attr-check"><input type="checkbox" checked={draft.holder_types.includes(t.type)}
             onchange={() => toggle(draft.holder_types, t.type)}> {t.label}</label>
    {/each}
  </div>
  {#if draft.kind === 'entity'}
    <div class="attr-types">
      <span>Peut nommer</span>
      {#each types as t (t.type)}
        <label class="attr-check"><input type="checkbox" checked={draft.value_types.includes(t.type)}
               onchange={() => toggle(draft.value_types, t.type)}> {t.label}</label>
      {/each}
    </div>
    <div class="attr-hint">Par défaut : aucune.</div>
  {:else if draft.kind === 'integer'}
    <label>Valeur par défaut <input type="number" bind:value={draft.defaultInteger} style="width:90px"></label>
  {:else}
    <div class="attr-choices">
      <span>Libellés (le défaut est coché)</span>
      {#each draft.choices as c, k (k)}
        <div class="attr-choice">
          <input type="radio" name={group} checked={c.label === draft.defaultLabel}
                 onchange={() => (draft.defaultLabel = c.label)} title="Valeur par défaut">
          <input type="text" value={c.label} oninput={(e) => {
            if (draft.defaultLabel === c.label) draft.defaultLabel = e.target.value;
            c.label = e.target.value;
          }}>
          <button class="btn-icon" title="Retirer" onclick={() => removeChoice(k)}>✕</button>
        </div>
      {/each}
      <button onclick={() => draft.choices.push({ id: null, label: '' })}>+ libellé</button>
    </div>
  {/if}
  <label class="attr-check"><input type="checkbox" bind:checked={draft.is_hidden}>
    Caché au joueur (une condition sur cet état ne le montre jamais)</label>
</div>

<style>
  .attr-form label { display: block; margin: 4px 0; }
  .attr-form input[type="text"] { width: 100%; box-sizing: border-box; }
  .attr-types, .attr-choices { margin: 6px 0; }
  .attr-types > span, .attr-choices > span { display: block; font-size: 12px; color: var(--muted); }
  .attr-check { display: inline-flex !important; gap: 4px; align-items: center; margin-right: 10px !important; }
  .attr-choice { display: flex; gap: 6px; align-items: center; margin: 2px 0; }
  .attr-choice input[type="text"] { flex: 1; }
  .attr-hint { font-size: 12px; color: var(--muted); }
</style>
