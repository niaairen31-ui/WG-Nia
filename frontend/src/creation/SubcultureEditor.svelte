<script>
  /* TICKET-0058 (BRIEF-0058-g, family c). Faithful port of the location
     subculture editor (TICKET-0025, BRIEF-0025-b) --
     authorRenderSubcultureEditor/authorAddSubcultureRow/authorRemoveSubcultureRow/
     authorSaveSubcultureRows/authorSaveSubcultureRowsData (index.html, now
     deleted). `location_subculture` rows, full-replace via
     PUT /api/entities/{id}/subculture.

     NEW location: rows held in subcultureDraft.svelte.js's shared
     subcultureDraftState (was the authorLocationSubcultureDraft global),
     read directly by Sheet.svelte's submitEntity at creation time -- no
     network calls here, "Enregistrer" stays a no-op exactly as the
     original's isNew branch was (it only ever re-synced the same draft it
     was about to re-render, never a PUT).

     EXISTING location: adding a row is LOCAL ONLY (no PUT, matching
     authorAddSubcultureRow(false) which only ever read+re-rendered);
     removing a row PUTs immediately (subculture-row-delete precedent); the
     save button PUTs the current full row set. Empty-key rows are dropped
     before the PUT, same as the legacy `clean` filter. */
  import { subcultureDraftState } from './subcultureDraft.svelte.js';

  let { isNew, entityId, rows: initialRows, legacyDoc, onSaved } = $props();

  let rows = $state([]);

  $effect(() => {
    if (!isNew) rows = (initialRows || []).map((r) => ({ ...r }));
  });

  function addRow() {
    if (isNew) {
      subcultureDraftState.rows = [...subcultureDraftState.rows, { key: '', value: '', is_hidden: false }];
    } else {
      rows = [...rows, { key: '', value: '', is_hidden: false }];
    }
  }

  function removeRow(i) {
    if (isNew) {
      subcultureDraftState.rows = subcultureDraftState.rows.filter((_, idx) => idx !== i);
    } else {
      rows = rows.filter((_, idx) => idx !== i);
      save();
    }
  }

  function noopSave() {
    // isNew's "Enregistrer" -- the original had nothing to PUT to (the
    // entity doesn't exist yet); kept for parity, does nothing.
  }

  async function save() {
    const statusEl = legacyDoc.getElementById('author-status');
    const clean = rows.filter((r) => (r.key || '').trim());
    try {
      const res = await fetch(`/api/entities/${encodeURIComponent(entityId)}/subculture`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: clean }),
      });
      const data = await res.json().catch(() => ({ detail: res.statusText }));
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onSaved(data);
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Subculture mise à jour.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }

  const displayRows = $derived(isNew ? subcultureDraftState.rows : rows);
</script>

<div>
  {#if displayRows.length === 0}
    <div class="empty">Aucune entrée.</div>
  {:else}
    {#each displayRows as row, i}
      <div class="field-row" style="flex-direction:row; gap:8px; align-items:center; margin-bottom:6px">
        <input type="text" bind:value={row.key} placeholder="clé (ex : values)" style="flex:1">
        <input type="text" bind:value={row.value} placeholder="valeur" style="flex:2">
        <label style="display:flex; align-items:center; gap:4px; font-size:12px">
          <input type="checkbox" bind:checked={row.is_hidden}> caché
        </label>
        <button class="btn-icon" onclick={() => removeRow(i)} title="Supprimer">✕</button>
      </div>
    {/each}
  {/if}
</div>
<div class="row-card-actions" style="margin-top:6px; gap:8px">
  <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={addRow}>+ Ajouter</button>
  <button class="btn-send" onclick={isNew ? noopSave : save}>💾 Enregistrer</button>
</div>
