<script>
  /* TICKET-0059 (BRIEF-0059-c). Faithful port of the relations in-context
     editor -- authorRenderRelations/authorRenderRelationForm/
     authorAddRelation/authorUpdateRelation/authorDeleteRelation
     (index.html, now deleted). Field semantics, defaults and the delete
     confirmation are ported verbatim (RECON-0059-a M2); sheetRequest.svelte.js
     replaces authorRelationRequest, the shared request/refresh/status cycle
     it shared line-for-line with the knowledge editor's own request fn.

     TICKET-0090 (BRIEF-0090-d). The direction vocabulary and the per-row
     visibility flag are gone: a social relation is always the perceiver's
     own row, read as `perceiver → type → target` identically
     from either sheet. Whether the target knows is its own control
     (`PUT /api/relations/{id}/target-knows`). "Réciproque" on the add form
     writes two independent rows, each edited apart. Structural rows
     (`is_social === false`) keep the plain `other (type)` heading and carry
     no knows control. */
  import { sheetRequest, api } from './sheetRequest.svelte.js';

  let { relations, entityId, entities, typeOptions, legacyDoc, onSaved } = $props();

  const candidates = $derived((entities || []).filter((e) => e.id !== entityId));
  const sheetName = $derived(((entities || []).find((e) => e.id === entityId) || {}).name || entityId);

  let rows = $state([]);
  $effect(() => {
    rows = (relations || []).map((r) => ({
      id: r.id,
      other_entity_name: r.other_entity_name,
      other_entity_type: r.other_entity_type,
      perceiver_id: r.perceiver_id,
      perceiver_name: r.perceiver_name,
      target_id: r.target_id,
      target_name: r.target_name,
      sheet_side: r.sheet_side,
      is_social: r.is_social,
      target_knows: r.target_knows,
      type: r.type,
      intensity: r.intensity,
      notes: r.notes ?? '',
    }));
  });

  let newOther = $state('');
  let newType = $state('');
  let newIntensity = $state(50);
  let newReciprocal = $state(false);
  let newNotes = $state('');
  const newOtherName = $derived((candidates.find((e) => e.id === newOther) || {}).name || '…');

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
      intensity: Number(row.intensity),
      notes: row.notes || null,
    });
    await sheetRequest(legacyDoc, `/api/relations/${encodeURIComponent(row.id)}`, 'PUT', body, reloadEntity);
  }

  async function setTargetKnows(row, knows) {
    const body = JSON.stringify({ knows });
    await sheetRequest(legacyDoc, `/api/relations/${encodeURIComponent(row.id)}/target-knows`, 'PUT', body, reloadEntity);
  }

  async function deleteRow(id) {
    if (!confirm('Permanently delete this relation?')) return;
    await sheetRequest(legacyDoc, `/api/relations/${encodeURIComponent(id)}`, 'DELETE', null, reloadEntity);
  }

  async function addRow() {
    const body = JSON.stringify({
      other_entity_id: newOther,
      type: newType,
      intensity: Number(newIntensity),
      notes: newNotes || null,
      reciprocal: newReciprocal,
    });
    const ok = await sheetRequest(legacyDoc, `/api/entities/${encodeURIComponent(entityId)}/relations`, 'POST', body, reloadEntity);
    if (ok) {
      newType = '';
      newIntensity = 50;
      newReciprocal = false;
      newNotes = '';
    }
  }
</script>

{#snippet endName(id, name)}
  {#if id === entityId}<span class="badge b-other">{name}</span>{:else}{name}{/if}
{/snippet}

{#if !relations || relations.length === 0}
  <div class="empty">No relations.</div>
{:else}
  <div class="row-table">
    {#each rows as row (row.id)}
      <div class="row-card">
        <div class="field-grid">
          <div class="field-row span-2"><label>Relation</label>
            {#if row.is_social}
              <div>{@render endName(row.perceiver_id, row.perceiver_name)} → {row.type} →
                {@render endName(row.target_id, row.target_name)} (intensité {row.intensity})</div>
            {:else}
              <div>{row.other_entity_name} ({row.type})</div>
            {/if}</div>
          <div class="field-row"><label>Type</label>
            <input type="text" bind:value={row.type}></div>
          <div class="field-row"><label>Intensity (1-100)</label>
            <input type="number" min="1" max="100" bind:value={row.intensity}></div>
          {#if row.is_social}
            <div class="field-row checkbox">
              <input type="checkbox" id={`rel-knows-${row.id}`} checked={row.target_knows}
                onchange={(ev) => setTargetKnows(row, ev.currentTarget.checked)}>
              <label for={`rel-knows-${row.id}`}>{row.target_name} le sait</label></div>
          {/if}
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
    <div class="field-row span-2"><label>Relation</label>
      <div>{sheetName} → {newType || '…'} → {newOtherName}</div></div>
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
    <div class="field-row"><label>Intensity (1-100)</label>
      <input type="number" min="1" max="100" bind:value={newIntensity}></div>
    <div class="field-row checkbox">
      <input type="checkbox" id="rel-new-reciprocal" bind:checked={newReciprocal}>
      <label for="rel-new-reciprocal">Réciproque (crée deux relations)</label></div>
    <div class="field-row span-2"><label>Notes</label><textarea bind:value={newNotes}></textarea></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={addRow}>Add relation</button>
  </div>
</div>
