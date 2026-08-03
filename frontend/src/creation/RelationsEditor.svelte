<script>
  /* TICKET-0059 (BRIEF-0059-c). Faithful port of the relations in-context
     editor -- authorRenderRelations/authorRenderRelationForm/
     authorAddRelation/authorUpdateRelation/authorDeleteRelation
     (index.html, now deleted). Field semantics, defaults and the delete
     confirmation are ported verbatim (RECON-0059-a M2); sheetRequest.svelte.js
     replaces authorRelationRequest, the shared request/refresh/status cycle
     it shared line-for-line with the knowledge editor's own request fn.

     RELATION_DIRECTIONS is a closed, frozen vocabulary -- never re-derived
     from the registry, never free text. */
  import { sheetRequest, api } from './sheetRequest.svelte.js';

  const RELATION_DIRECTIONS = ['mutual', 'a_to_b', 'b_to_a'];

  let { relations, entityId, entities, typeOptions, legacyDoc, onSaved } = $props();

  const candidates = $derived((entities || []).filter((e) => e.id !== entityId));

  let rows = $state([]);
  $effect(() => {
    rows = (relations || []).map((r) => ({
      id: r.id,
      other_entity_name: r.other_entity_name,
      other_entity_type: r.other_entity_type,
      type: r.type,
      direction: r.direction,
      intensity: r.intensity,
      visible_to_b: r.visible_to_b,
      notes: r.notes ?? '',
    }));
  });

  let newOther = $state('');
  let newType = $state('');
  let newDirection = $state('mutual');
  let newIntensity = $state(50);
  let newVisibleToB = $state(true);
  let newNotes = $state('');

  $effect(() => {
    if (candidates.length && !candidates.some((e) => e.id === newOther)) {
      newOther = candidates[0].id;
    }
  });

  async function reloadEntity() {
    onSaved(await api(`/api/entities/${encodeURIComponent(entityId)}`));
  }

  async function saveRow(row) {
    const body = JSON.stringify({
      type: row.type,
      direction: row.direction,
      intensity: Number(row.intensity),
      visible_to_b: row.visible_to_b,
      notes: row.notes || null,
    });
    await sheetRequest(legacyDoc, `/api/relations/${encodeURIComponent(row.id)}`, 'PUT', body, reloadEntity);
  }

  async function deleteRow(id) {
    if (!confirm('Permanently delete this relation?')) return;
    await sheetRequest(legacyDoc, `/api/relations/${encodeURIComponent(id)}`, 'DELETE', null, reloadEntity);
  }

  async function addRow() {
    const body = JSON.stringify({
      other_entity_id: newOther,
      type: newType,
      direction: newDirection,
      intensity: Number(newIntensity),
      visible_to_b: newVisibleToB,
      notes: newNotes || null,
    });
    const ok = await sheetRequest(legacyDoc, `/api/entities/${encodeURIComponent(entityId)}/relations`, 'POST', body, reloadEntity);
    if (ok) {
      newType = '';
      newDirection = 'mutual';
      newIntensity = 50;
      newVisibleToB = true;
      newNotes = '';
    }
  }
</script>

{#if !relations || relations.length === 0}
  <div class="empty">No relations.</div>
{:else}
  <div class="row-table">
    {#each rows as row (row.id)}
      <div class="row-card">
        <div class="field-grid">
          <div class="field-row"><label>With</label>
            <input type="text" value={`${row.other_entity_name} (${row.other_entity_type})`} disabled></div>
          <div class="field-row"><label>Type</label>
            <input type="text" bind:value={row.type}></div>
          <div class="field-row"><label>Direction</label>
            <select bind:value={row.direction}>
              {#each RELATION_DIRECTIONS as d}
                <option value={d}>{d}</option>
              {/each}
            </select></div>
          <div class="field-row"><label>Intensity (1-100)</label>
            <input type="number" min="1" max="100" bind:value={row.intensity}></div>
          <div class="field-row checkbox">
            <input type="checkbox" id={`rel-vis-${row.id}`} bind:checked={row.visible_to_b}>
            <label for={`rel-vis-${row.id}`}>Visible to B</label></div>
          <div class="field-row span-2"><label>Notes</label>
            <textarea bind:value={row.notes}></textarea></div>
        </div>
        <div class="row-card-actions">
          <button class="btn-ghost" onclick={() => saveRow(row)}>Save</button>
          <button class="btn-end" onclick={() => deleteRow(row.id)}>Delete</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<div class="row-card">
  <div class="field-grid">
    <div class="field-row"><label>With</label>
      <select bind:value={newOther}>
        {#each candidates as e (e.id)}
          <option value={e.id}>{e.name} ({e.type})</option>
        {/each}
      </select></div>
    <div class="field-row"><label>Type *</label>
      <input type="text" bind:value={newType} list="rel-new-type-dl">
      <datalist id="rel-new-type-dl">
        {#each (typeOptions || []) as o}
          <option value={o}></option>
        {/each}
      </datalist></div>
    <div class="field-row"><label>Direction</label>
      <select bind:value={newDirection}>
        {#each RELATION_DIRECTIONS as d}
          <option value={d}>{d}</option>
        {/each}
      </select></div>
    <div class="field-row"><label>Intensity (1-100)</label>
      <input type="number" min="1" max="100" bind:value={newIntensity}></div>
    <div class="field-row checkbox">
      <input type="checkbox" id="rel-new-vis" bind:checked={newVisibleToB}>
      <label for="rel-new-vis">Visible to B</label></div>
    <div class="field-row span-2"><label>Notes</label><textarea bind:value={newNotes}></textarea></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={addRow}>Add relation</button>
  </div>
</div>
