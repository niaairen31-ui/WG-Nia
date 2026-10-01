<script>
  /* TICKET-0099 (BRIEF-0099-b, B1 + E1). The Compétences fiche, rendered
     by Sheet.svelte under `type === 'competences'` inside #author-main --
     the same fiche area every entity tab uses. Sheet.svelte selects this
     branch from sheetType (CLAUDE.md, creation_tab_switch.py); THIS
     component then reads the record's own `kind` (C-01), a field of the
     same sheetDetail that feeds it, never activeTabKey.

     Every input binds straight to creationState.sheetDetail, a fresh C-01
     record the list built for this fiche: nothing reaches the catalogue
     until the shell's Save button, which Sheet.svelte's saveSheet routes to
     saveCompetenceRecord (competences.svelte.js). Delete and "Retirer du
     brouillon" are this fiche's own buttons, as Delete is on the entity
     fiche. The two dialogs are Modal.svelte instances, unchanged from the
     former Competences.svelte (lock O1): the skill delete keeps its type
     "Oui" step (it cascades onto player-character skill rows), the system
     delete shows the server's 409 refusal inline.

     No scoped <style> block: like every other Creation island, classes
     come from frontend/public/creation.css / shared.css. */
  import { creationState } from './state.svelte.js';
  import { creationRefreshList } from './tabs.js';
  import Modal from './Modal.svelte';
  import {
    competencesState, COMPETENCES_DOMAINS, NO_SYSTEM_LABEL, generateDraft,
    discardDraft, deleteSkill, deleteSystem, closeCompetenceSheet,
  } from './competences.svelte.js';

  const rec = $derived(creationState.sheetDetail);

  let genBrief = $state('');
  let genStatus = $state('');
  let genNotes = $state([]);

  let deleteOpen = $state(false);
  let deleteConfirmText = $state('');
  let deleteStatus = $state('');

  async function onGenerate() {
    const brief = genBrief.trim();
    if (!brief) { genStatus = 'Intention requise.'; return; }
    genStatus = 'Génération…';
    genNotes = [];
    try {
      const result = await generateDraft(brief);
      if (!result.ok) { genStatus = result.error; return; }
      genNotes = result.notes;
      genStatus = competencesState.draft.length
        ? 'Brouillon généré — ouvrez chaque proposition dans la liste, relisez-la, puis enregistrez-la.'
        : 'Aucune compétence proposée.';
    } catch (err) {
      genStatus = err.message;
    }
  }

  function onDiscardDraft() {
    discardDraft(rec.draftKey);
    closeCompetenceSheet();
  }

  function openDelete() {
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
      if (rec.kind === 'system') await deleteSystem(rec.id);
      else await deleteSkill(rec.id);
      deleteOpen = false;
      closeCompetenceSheet();
      creationRefreshList();
    } catch (err) {
      deleteStatus = err.message;
    }
  }
</script>

{#if rec && rec.kind === 'assistant'}
  <div class="field-section">
    <div class="field-row">
      <label for="competences-gen-brief">Intention</label>
      <textarea id="competences-gen-brief" rows="3" bind:value={genBrief}
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
  </div>
{:else if rec && rec.kind === 'skill'}
  <div style="display:flex; justify-content:flex-end; gap:8px; margin-bottom:8px;">
    {#if rec.draftKey != null}
      <button class="btn-ghost" onclick={onDiscardDraft}>Retirer du brouillon</button>
    {/if}
    {#if rec.persisted}
      <button class="btn-end" onclick={openDelete}>Supprimer</button>
    {/if}
  </div>
  <div class="field-section">
    <div class="field-grid">
      <div class="field-row">
        <label for="competence-f-name">Nom</label>
        <input id="competence-f-name" type="text" bind:value={creationState.sheetDetail.name}>
      </div>
      <div class="field-row">
        <label for="competence-f-domain">Domaine de base</label>
        <select id="competence-f-domain" bind:value={creationState.sheetDetail.base_domain}>
          {#if !COMPETENCES_DOMAINS.includes(rec.base_domain)}<option value="">— domaine —</option>{/if}
          {#each COMPETENCES_DOMAINS as d}<option value={d}>{d}</option>{/each}
        </select>
      </div>
      <div class="field-row">
        <label for="competence-f-system">Système</label>
        <select id="competence-f-system" onchange={(e) => { creationState.sheetDetail.system_id = e.currentTarget.value || null; }}>
          <option value="" selected={!rec.system_id}>{NO_SYSTEM_LABEL}</option>
          {#each competencesState.systems as sys (sys.id)}
            <option value={sys.id} selected={rec.system_id === sys.id}>{sys.name}</option>
          {/each}
        </select>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="competence-f-description">Description</label>
        <textarea id="competence-f-description" rows="3" bind:value={creationState.sheetDetail.description}></textarea>
      </div>
    </div>
  </div>
{:else if rec && rec.kind === 'system'}
  {#if rec.persisted}
    <div style="display:flex; justify-content:flex-end; margin-bottom:8px;">
      <button class="btn-end" onclick={openDelete}>Supprimer</button>
    </div>
  {/if}
  <div class="field-section">
    <div class="field-grid">
      <div class="field-row">
        <label for="system-f-name">Nom</label>
        <input id="system-f-name" type="text" bind:value={creationState.sheetDetail.name}>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="system-f-description">Description</label>
        <textarea id="system-f-description" rows="3" bind:value={creationState.sheetDetail.description}></textarea>
      </div>
    </div>
    {#if rec.persisted}
      <div style="margin-top:8px; font-size:12px; color:var(--muted)">{rec.skill_count} compétence(s) dans ce système.</div>
    {/if}
  </div>
{/if}

<Modal title={rec && rec.kind === 'system' ? 'Supprimer le système' : 'Supprimer la compétence'}
       open={deleteOpen} dismissOnBackdrop={false} onClose={closeDelete}>
  {#snippet body()}
    {#if rec && rec.kind === 'system'}
      <p>Cette action supprime définitivement le système « {rec.name} ».
      Un système qui contient encore des compétences ne peut pas être supprimé —
      détachez-les ou supprimez-les d'abord.</p>
      <div style="color:var(--red); margin-top:6px;">{deleteStatus}</div>
      <button class="btn-send" style="margin-top:8px" onclick={confirmDelete}>Supprimer</button>
    {:else if rec}
      <p>Cette action supprime définitivement la compétence « {rec.name} » et,
      pour chaque personnage joueur qui la possède, sa ligne de compétence
      correspondante. Elle est irréversible.</p>
      <p>Tapez Oui pour confirmer.</p>
      <input type="text" placeholder="Oui" bind:value={deleteConfirmText}>
      <div style="color:var(--red); margin-top:6px;">{deleteStatus}</div>
      <button class="btn-send" style="margin-top:8px" disabled={deleteConfirmText.trim() !== 'Oui'}
        onclick={confirmDelete}>Supprimer définitivement</button>
    {/if}
  {/snippet}
</Modal>
