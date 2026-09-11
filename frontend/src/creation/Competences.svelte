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
     renders inside the legacy iframe document.

     TICKET-0084 (BRIEF-0084-b): the skill_system reader. The systems list
     (create/rename/describe/delete) is its own field-section, above the
     assistant; the catalogue below groups by system via
     groupSkillsBySystem (competences.svelte.js) -- a client-side join of
     two flat lists, never a nested endpoint. A second Modal instance
     carries the system delete refusal (409 while skills remain attached),
     same inline-error-in-modal idiom as the skill-definition delete above,
     no type-"Oui" step: unlike that cascade, a system delete never touches
     a second table.

     TICKET-0084 (BRIEF-0084-d): the "Trous du lexique" gaps reader, its
     own read-only field-section between the assistant and the catalogue --
     no create/edit affordance of its own (LedgerPanel.svelte's pattern).
     A gap click calls addGapDraftRow, which reuses the draft/Accepter path
     above; the panel itself never calls a write endpoint. */
  import { serverState } from '../lib/serverState.svelte.js';
  import Modal from './Modal.svelte';
  import {
    competencesState, COMPETENCES_DOMAINS, NO_SYSTEM_LABEL, resetCompetences, addManualRow,
    discardDraftRow, generateDraft, acceptDraftRow, loadList, saveRow, deleteDefinition,
    loadSystems, createSystem, saveSystem, deleteSystem, groupSkillsBySystem,
    loadGaps, addGapDraftRow,
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

  let newSystemName = $state('');
  let newSystemDescription = $state('');
  let newSystemStatus = $state('');
  let systemRowStatus = $state({});

  let deleteSystemOpen = $state(false);
  let deleteSystemId = $state(null);
  let deleteSystemName = $state('');
  let deleteSystemStatus = $state('');

  const groupedSkills = $derived(groupSkillsBySystem(competencesState.rows, competencesState.systems));

  $effect(() => {
    void serverState.worldId;
    resetCompetences();
    genBrief = '';
    genStatus = '';
    genNotes = [];
    draftStatus = {};
    rowStatus = {};
    newSystemName = '';
    newSystemDescription = '';
    newSystemStatus = '';
    systemRowStatus = {};
    loadList();
    loadSystems();
    loadGaps();
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
      await saveRow(row.id, row.name.trim(), row.base_domain, row.system_id, row.description);
      rowStatus = { ...rowStatus, [row.id]: 'Enregistré.' };
    } catch (err) {
      rowStatus = { ...rowStatus, [row.id]: err.message };
    }
  }

  async function onCreateSystem() {
    const name = newSystemName.trim();
    if (!name) { newSystemStatus = 'Nom requis.'; return; }
    newSystemStatus = '…';
    try {
      await createSystem(name, newSystemDescription || null);
      newSystemName = '';
      newSystemDescription = '';
      newSystemStatus = '';
    } catch (err) {
      newSystemStatus = err.message;
    }
  }

  async function onSaveSystem(sys) {
    if (!sys.name || !sys.name.trim()) { systemRowStatus = { ...systemRowStatus, [sys.id]: 'Nom requis.' }; return; }
    systemRowStatus = { ...systemRowStatus, [sys.id]: '…' };
    try {
      await saveSystem(sys.id, sys.name.trim(), sys.description);
      systemRowStatus = { ...systemRowStatus, [sys.id]: 'Enregistré.' };
    } catch (err) {
      systemRowStatus = { ...systemRowStatus, [sys.id]: err.message };
    }
  }

  function openDeleteSystem(id, name) {
    deleteSystemId = id;
    deleteSystemName = name;
    deleteSystemStatus = '';
    deleteSystemOpen = true;
  }

  function closeDeleteSystem() {
    deleteSystemOpen = false;
  }

  async function confirmDeleteSystem() {
    deleteSystemStatus = '…';
    try {
      await deleteSystem(deleteSystemId);
      deleteSystemOpen = false;
    } catch (err) {
      deleteSystemStatus = err.message;
    }
  }

  function onGapClick(surfaceForm) {
    addGapDraftRow(surfaceForm);
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
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
    <div class="field-section-title">Systèmes de compétences</div>
    {#if competencesState.systemsError}
      <div class="empty">{competencesState.systemsError}</div>
    {:else if competencesState.systems.length === 0}
      <div class="empty">Aucun système — le catalogue reste groupé sous « {NO_SYSTEM_LABEL} ».</div>
    {:else}
      {#each competencesState.systems as sys (sys.id)}
        <div class="field-grid" style="border-bottom:1px solid var(--border); padding:8px 0;">
          <div class="field-row">
            <label>Nom</label>
            <input type="text" bind:value={sys.name}>
          </div>
          <div class="field-row" style="grid-column:1/-1">
            <label>Description</label>
            <textarea rows="2" bind:value={sys.description}></textarea>
          </div>
          <div style="grid-column:1/-1; display:flex; gap:8px; align-items:center;">
            <span style="font-size:11px; color:var(--muted)">{sys.skill_count} compétence(s)</span>
            <button class="btn-send" onclick={() => onSaveSystem(sys)}>Enregistrer</button>
            <button class="btn-end" onclick={() => openDeleteSystem(sys.id, sys.name)}>Supprimer</button>
            <span class="author-status">{systemRowStatus[sys.id] || ''}</span>
          </div>
        </div>
      {/each}
    {/if}
    <div class="field-grid" style="margin-top:6px;">
      <div class="field-row">
        <label>Nouveau système — nom</label>
        <input type="text" bind:value={newSystemName}>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label>Description</label>
        <textarea rows="2" bind:value={newSystemDescription}></textarea>
      </div>
      <div style="grid-column:1/-1; display:flex; gap:8px; align-items:center;">
        <button class="btn-send" onclick={onCreateSystem}>+ Ajouter un système</button>
        <span class="author-status">{newSystemStatus}</span>
      </div>
    </div>
  </div>
  <div class="field-section" style="margin:0; padding:10px 14px; border-top:1px solid var(--border)">
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
                <option value="">— domaine —</option>
                {#each COMPETENCES_DOMAINS as d}<option value={d}>{d}</option>{/each}
              </select>
            </div>
            <div class="field-row">
              <label>Système</label>
              <select onchange={(e) => { row.system_id = e.currentTarget.value || null; }}>
                <option value="" selected={!row.system_id}>{NO_SYSTEM_LABEL}</option>
                {#each competencesState.systems as sys (sys.id)}
                  <option value={sys.id} selected={row.system_id === sys.id}>{sys.name}</option>
                {/each}
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
  <div class="field-section" style="margin:0; padding:10px 14px; border-top:1px solid var(--border)">
    <div class="field-section-title">Trous du lexique</div>
    {#if competencesState.gapsError}
      <div class="empty">{competencesState.gapsError}</div>
    {:else if competencesState.gaps.length === 0}
      <div class="empty">Aucun trou détecté — tout ce que l'arbitre a nommé est déjà dans le catalogue.</div>
    {:else}
      <div class="row-table">
        {#each competencesState.gaps as gap (gap.surface_form)}
          <div class="row-card" role="button" tabindex="0"
            style="flex-direction:row; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px; cursor:pointer;"
            onclick={() => onGapClick(gap.surface_form)}
            onkeydown={(e) => { if (e.key === 'Enter') onGapClick(gap.surface_form); }}>
            <span style="font-weight:600;">{gap.surface_form}</span>
            <span class="badge b-other">{gap.count}</span>
            <span style="font-size:11px; color:var(--muted);">{fmtDate(gap.last_seen)}</span>
          </div>
        {/each}
      </div>
    {/if}
    {#if competencesState.arbiterFailures.error > 0 || competencesState.arbiterFailures.empty > 0}
      <div style="margin-top:8px; font-size:12px; color:var(--muted);">
        Échecs de l'arbitre (hors lexique) : {competencesState.arbiterFailures.error} erreur(s), {competencesState.arbiterFailures.empty} réponse(s) vide(s)
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
      {#each groupedSkills as group (group.system?.id ?? '__none__')}
        <div class="field-section-title">
          {group.system ? group.system.name : NO_SYSTEM_LABEL}
          {#if group.system?.description}
            <span style="font-size:11px; font-weight:normal; color:var(--muted)"> — {group.system.description}</span>
          {/if}
        </div>
        {#if group.skills.length === 0}
          <div class="empty">Aucune compétence.</div>
        {:else}
          {#each group.skills as row (row.id)}
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
              <div class="field-row">
                <label>Système</label>
                <select onchange={(e) => { row.system_id = e.currentTarget.value || null; }}>
                  <option value="" selected={!row.system_id}>{NO_SYSTEM_LABEL}</option>
                  {#each competencesState.systems as sys (sys.id)}
                    <option value={sys.id} selected={row.system_id === sys.id}>{sys.name}</option>
                  {/each}
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

<Modal title="Supprimer le système" open={deleteSystemOpen} dismissOnBackdrop={false} onClose={closeDeleteSystem}>
  {#snippet body()}
    <p>Cette action supprime définitivement le système « {deleteSystemName} ».
    Un système qui contient encore des compétences ne peut pas être supprimé —
    détachez-les ou supprimez-les d'abord.</p>
    <div style="color:var(--red); margin-top:6px;">{deleteSystemStatus}</div>
    <button class="btn-send" style="margin-top:8px" onclick={confirmDeleteSystem}>Supprimer</button>
  {/snippet}
</Modal>
