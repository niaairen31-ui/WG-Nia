<script>
  /* TICKET-0113 (BRIEF-0113-C, WC1, WD1, WE1). An entity's states on its
     sheet: every attribute that applies to its type -- the system ones
     read-only (their own fields on the sheet keep them) --, its value or
     « (défaut) », and its history. A value is changed through PUT
     /api/entities/{id}/states/{key}, and the creator says each time whether
     it is a correction (it was always so) or a change (the world changed):
     neither is preselected (WD1). */
  import { api } from './sheetRequest.svelte.js';

  let { entityId } = $props();

  let states = $state([]);
  let entities = $state([]);
  let loadError = $state('');
  let editing = $state(null); // { key, value, kind }
  let saveError = $state('');
  let open = $state({});

  async function load() {
    try {
      const rows = await api(`/api/entities/${encodeURIComponent(entityId)}/states`);
      states = rows;
      if (rows.some((s) => s.kind === 'entity')) {
        entities = (await api('/api/quest-offers/choices')).entities || [];
      }
      loadError = '';
    } catch (e) {
      loadError = e.message;
    }
  }

  $effect(() => {
    if (entityId) load();
  });

  function edit(state) {
    saveError = '';
    editing = { key: state.key, value: state.raw ?? '', kind: '' };
  }

  async function save(state) {
    if (!editing.kind) { saveError = 'Choisis : correction ou changement.'; return; }
    const value = state.kind === 'integer' ? Number(editing.value) : editing.value || null;
    try {
      states = await api(`/api/entities/${encodeURIComponent(entityId)}/states/${encodeURIComponent(state.key)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value, kind: editing.kind }),
      });
      editing = null;
      saveError = '';
    } catch (e) {
      saveError = e.message;
    }
  }
</script>

{#if loadError}
  <div class="r-err">{loadError}</div>
{:else if states.length === 0}
  <div class="muted">Aucun état ne s'applique à cette entité. Création › États pour en définir.</div>
{:else}
  {#each states as state (state.key)}
    <div class="state-row">
      <strong>{state.name}</strong>
      {#if state.hidden}<span class="badge b-other">caché</span>{/if}
      <span>{state.label}</span>
      {#if state.is_default}<span class="muted">(défaut)</span>{/if}
      {#if state.system}
        <span class="muted">— système, modifiable dans les champs de la fiche</span>
      {:else if editing?.key === state.key}
        <div class="state-edit">
          {#if state.kind === 'choice'}
            <select bind:value={editing.value}>
              {#each state.choices as c (c.value)}<option value={c.value}>{c.label}</option>{/each}
            </select>
          {:else if state.kind === 'integer'}
            <input type="number" bind:value={editing.value} style="width:90px">
          {:else}
            <select bind:value={editing.value}>
              <option value="">— aucune —</option>
              {#each entities.filter((e) => state.value_types.includes(e.type)) as e (e.id)}
                <option value={e.id}>{e.name}</option>
              {/each}
            </select>
          {/if}
          <label><input type="radio" bind:group={editing.kind} value="correction"> Correction</label>
          <label><input type="radio" bind:group={editing.kind} value="changement"> Changement</label>
          <button class="btn-send" onclick={() => save(state)}>OK</button>
          <button onclick={() => { editing = null; saveError = ''; }}>Annuler</button>
          {#if saveError}<div class="r-err">{saveError}</div>{/if}
        </div>
      {:else}
        <button onclick={() => edit(state)}>Modifier</button>
      {/if}
      {#if state.history.length}
        <button class="btn-icon" title="Historique" onclick={() => (open[state.key] = !open[state.key])}>🕘</button>
      {/if}
      {#if open[state.key]}
        <ul class="state-history">
          {#each state.history as h, i (i)}
            <li>{h.changed_at.slice(0, 16).replace('T', ' ')} — {h.kind} : {h.before} → {h.after}</li>
          {/each}
        </ul>
      {/if}
    </div>
  {/each}
{/if}

<style>
  .state-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 4px 0; }
  .state-edit { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; width: 100%; }
  .state-history { width: 100%; margin: 2px 0 4px 18px; padding: 0; font-size: 12px; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); width: 100%; }
</style>
