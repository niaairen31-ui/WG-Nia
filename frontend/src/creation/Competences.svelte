<script>
  /* TICKET-0059 (BRIEF-0059-h commit 3). Faithful port of the Compétences
     tab -- competences.svelte.js's own header lists the ported functions.
     Rendering + the delete-confirmation dialog (Modal.svelte, lock O1) live
     here; competences.svelte.js holds the non-render state and API calls.

     World reset is driven by serverState.worldId (the -d rule every
     migrated island follows) -- since loader: null now, this same effect
     also does the initial + every-world-switch loadList() fetch, replacing
     the legacy loader/onWorldSwitch pair.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { serverState } from '../lib/serverState.svelte.js';
  import Modal from './Modal.svelte';
  import {
    competencesState, COMPETENCES_DOMAINS, resetCompetences, addManualRow,
    discardDraftRow, generateDraft, acceptDraftRow, loadList, saveRow, deleteDefinition,
  } from './competences.svelte.js';

  let genBrief = $state('');
  let genStatus = $state('');
  let genNotes = $state([]);
  let draftStatus = $state({});
  let rowStatus = $state({});

  let deleteOpen = $state(false);
  let deleteId = $state(null);
  let deleteName = $state('');
  let deleteConfirmText = $state('');
  let deleteStatus = $state('');

  $effect(() => {
    void serverState.worldId;
    resetCompetences();
    genBrief = '';
    genStatus = '';
    genNotes = [];
    draftStatus = {};
    rowStatus = {};
    loadList();
  });

  export function primaryAction() {
    addManualRow();
  }

  async function onGenerate() {
    const brief = genBrief.trim();
    if (!brief) { genStatus = 'Intention requise.'; return; }
    genStatus = 'Génération…';
    try {
      const result = await generateDraft(brief);
      if (!result.ok) { genStatus = result.error; return; }
      genNotes = result.notes;
      genStatus = competencesState.draft.length
        ? 'Brouillon généré — relisez, éditez puis acceptez chaque compétence.'
        : 'Aucune compétence proposée.';
    } catch (err) {
      genStatus = err.message;
    }
  }

  function onDiscard(i) {
    discardDraftRow(i);
    draftStatus = {};
  }

  async function onAccept(i) {
    const row = competencesState.draft[i];
    if (!row.name || !row.name.trim()) { draftStatus = { ...draftStatus, [i]: 'Nom requis.' }; return; }
    draftStatus = { ...draftStatus, [i]: '…' };
    try {
      await acceptDraftRow(i);
      draftStatus = {};
    } catch (err) {
      draftStatus = { ...draftStatus, [i]: err.message };
    }
  }

  async function onSaveRow(row) {
    if (!row.name || !row.name.trim()) { rowStatus = { ...rowStatus, [row.id]: 'Nom requis.' }; return; }
    rowStatus = { ...rowStatus, [row.id]: '…' };
    try {
      await saveRow(row.id, row.name.trim(), row.base_domain, row.description);
      rowStatus = { ...rowStatus, [row.id]: 'Enregistré.' };
    } catch (err) {
      rowStatus = { ...rowStatus, [row.id]: err.message };
    }
  }

  function openDelete(id, name) {
    deleteId = id;
    deleteName = name;
    deleteConfirmText = '';
    deleteStatus = '';
    deleteOpen = true;
  }

  function closeDelete() {
    deleteOpen = false;
  }

  async function confirmDelete() {
    deleteStatus = '…';
    try {
      await deleteDefinition(deleteId);
      deleteOpen = false;
    } catch (err) {
      deleteStatus = err.message;
    }
  }
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Compétences propres au monde</h2>
    <button class="btn-icon" onclick={loadList} title="Rafraîchir">↻</button>
  </div>
  <div class="field-section" style="margin:0; padding:10px 14px">
    <div class="field-row" style="margin:0">
      <label for="competences-gen-brief">Intention (pour l'assistant)</label>
      <textarea id="competences-gen-brief" rows="2" bind:value={genBrief}
        placeholder="Ex. un monde maritime où la navigation et le troc comptent autant que le combat"></textarea>
    </div>
    <div style="display:flex; gap:10px; align-items:center; margin-top:6px">
      <button class="btn-send" onclick={onGenerate}>Générer le brouillon</button>
      <span class="author-status">{genStatus}</span>
    </div>
    {#if genNotes.length}
      <div style="margin-top:8px; font-size:12px; color:var(--muted)">Notes de l'assistant :
        {#each genNotes as n}<div>• {n}</div>{/each}
      </div>
    {/if}
    {#if competencesState.draft.length}
      <div style="margin-top:10px">
        <div class="field-section-title">Brouillon proposé</div>
        {#each competencesState.draft as row, i}
          <div class="field-grid" style="border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:6px;">
            <div class="field-row">
              <label>Nom</label>
              <input type="text" bind:value={row.name}>
            </div>
            <div class="field-row">
              <label>Domaine de base</label>
              <select bind:value={row.base_domain}>
                {#each COMPETENCES_DOMAINS as d}<option value={d}>{d}</option>{/each}
              </select>
            </div>
            <div class="field-row" style="grid-column:1/-1">
              <label>Description</label>
              <textarea rows="2" bind:value={row.description}></textarea>
            </div>
            <div style="grid-column:1/-1; display:flex; gap:8px;">
              <button class="btn-send" onclick={() => onAccept(i)}>Accepter</button>
              <button class="btn-icon" onclick={() => onDiscard(i)} title="Retirer du brouillon">✕</button>
              <span class="author-status">{draftStatus[i] || ''}</span>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
  <div class="queue-body" style="border-top:1px solid var(--border)">
    {#if competencesState.loading}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if competencesState.loadError}
      <div class="empty">{competencesState.loadError}</div>
    {:else if competencesState.rows.length === 0}
      <div class="empty">Aucune compétence propre à ce monde — proposez-en une avec l'assistant, ou ajoutez-en une manuellement.</div>
    {:else}
      {#each competencesState.rows as row (row.id)}
        <div class="field-grid" style="border-bottom:1px solid var(--border); padding:8px 0;">
          <div class="field-row">
            <label>Nom</label>
            <input type="text" bind:value={row.name}>
          </div>
          <div class="field-row">
            <label>Domaine de base</label>
            <select bind:value={row.base_domain}>
              {#each COMPETENCES_DOMAINS as d}<option value={d}>{d}</option>{/each}
            </select>
          </div>
          <div class="field-row" style="grid-column:1/-1">
            <label>Description</label>
            <textarea rows="2" bind:value={row.description}></textarea>
          </div>
          <div style="grid-column:1/-1; display:flex; gap:8px; align-items:center;">
            <button class="btn-send" onclick={() => onSaveRow(row)}>Enregistrer</button>
            <button class="btn-end" onclick={() => openDelete(row.id, row.name)}>Supprimer</button>
            <span class="author-status">{rowStatus[row.id] || ''}</span>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<Modal title="Supprimer la compétence" open={deleteOpen} dismissOnBackdrop={false} onClose={closeDelete}>
  {#snippet body()}
    <p>Cette action supprime définitivement la compétence « {deleteName} » et,
    pour chaque personnage joueur qui la possède, sa ligne de compétence
    correspondante. Elle est irréversible.</p>
    <p>Tapez Oui pour confirmer.</p>
    <input type="text" placeholder="Oui" bind:value={deleteConfirmText}>
    <div style="color:var(--red); margin-top:6px;">{deleteStatus}</div>
    <button class="btn-send" style="margin-top:8px" disabled={deleteConfirmText.trim() !== 'Oui'}
      onclick={confirmDelete}>Supprimer définitivement</button>
  {/snippet}
</Modal>
