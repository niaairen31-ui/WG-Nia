<script>
  /* TICKET-0059 (BRIEF-0059-l commit 3). World create + delete in one file,
     not two (WorldCreate.svelte/WorldDelete.svelte): the two are two states
     of the same world-lifecycle concern, and worldDeleteConfirm's
     zero-remaining path opens the create modal directly (worldCrud.svelte.js)
     -- the same "one file, related states" precedent Region.svelte/
     RoomBatch.svelte already set for generation+review and manifest+commit.

     Mounted once in App.svelte, a sibling of Header/LegacyFrame/Creation --
     available regardless of the active surface (Header's "+ Monde"/"🗑 Monde"
     buttons are always visible), unlike the Creation-only islands mount.js
     manages. Modal.svelte's third and fourth consumers now (after
     Competences' delete confirm and LocationTypeModal). */
  import Modal from './Modal.svelte';
  import {
    worldCrudState, closeWorldCreateModal, worldGenerateDraft, worldCreateSubmit,
    closeWorldDeleteModal, worldDeleteConfirm,
  } from './worldCrud.svelte.js';
</script>

<Modal title="Nouveau monde" open={worldCrudState.createOpen} dismissOnBackdrop={false} onClose={closeWorldCreateModal}>
  {#snippet body()}
    <div class="field-section" style="border:1px solid var(--border); border-radius:6px; padding:10px; margin-bottom:12px;">
      <div class="field-section-title">Générer avec l'IA</div>
      <textarea rows="2" style="width:100%; resize:vertical" bind:value={worldCrudState.genBrief}
        placeholder="Intention en une phrase, ex. : « Un monde post-rupture magique où la mémoire se monnaie »"></textarea>
      <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
        <button class="btn-send" onclick={worldGenerateDraft}>Générer</button>
        <span style="font-size:12px; color:var(--muted)">{worldCrudState.genStatus}</span>
      </div>
      {#if worldCrudState.genNotes.length}
        <div style="margin-top:8px; font-size:12px; color:var(--muted)">
          Notes de l'assistant :
          {#each worldCrudState.genNotes as n}<div>• {n}</div>{/each}
        </div>
      {/if}
    </div>
    <div class="field-grid">
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-create-name">Nom *</label>
        <input type="text" id="world-create-name" placeholder="Nom du monde" bind:value={worldCrudState.createName}>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-create-description">Contexte du monde (description, optionnel)</label>
        <textarea id="world-create-description" rows="3" placeholder="Genre, ton, géographie générale…" bind:value={worldCrudState.createDescription}></textarea>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-create-laws">Lois fondamentales (contraintes absolues, optionnel)</label>
        <textarea id="world-create-laws" rows="3" placeholder="Ex. « La magie n'existe pas dans ce monde. »" bind:value={worldCrudState.createLaws}></textarea>
      </div>
    </div>
    <div style="color:var(--red); margin-top:6px;">{worldCrudState.createStatus}</div>
    <button class="btn-send" style="margin-top:8px" onclick={worldCreateSubmit}>Créer et activer</button>
  {/snippet}
</Modal>

<Modal title="Supprimer le monde" open={worldCrudState.deleteOpen} dismissOnBackdrop={false} onClose={closeWorldDeleteModal}>
  {#snippet body()}
    <p>Cette action supprime définitivement le monde « {worldCrudState.deleteWorldName} » et tout
    son contenu (entités, relations, historique, sessions). Elle est irréversible.</p>
    <p>Tapez Oui pour confirmer.</p>
    <input type="text" placeholder="Oui" bind:value={worldCrudState.deleteConfirmText}>
    <div style="color:var(--red); margin-top:6px;">{worldCrudState.deleteStatus}</div>
    <button class="btn-send" style="margin-top:8px" disabled={worldCrudState.deleteConfirmText.trim() !== 'Oui'}
      onclick={worldDeleteConfirm}>Supprimer définitivement</button>
  {/snippet}
</Modal>
