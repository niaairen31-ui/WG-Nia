<script>
  /* TICKET-0114 (BRIEF-0114-B, D1, T3). The sortes of the world, in
     « Vocabulaire du monde »: the anonymous kinds -- « loup », « bandit » --
     a role accepting a sorte is filled by, with the event's quantity. One
     sorte added or renamed at a time; a name near another's waits for the
     creator's pick; a sorte is retired (refused while a condition names
     it) or restored, never deleted. State and requests live in
     eventVocab.svelte.js. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    vocabState, newSorteDraft, editSorte, saveSorteDraft, setVocabStatus,
  } from './eventVocab.svelte.js';

  /** The section's « + Nouveau » (Vocabulary.svelte routes it here). */
  export function primaryAction() {
    newSorteDraft();
  }

  function openNear(id) {
    const found = vocabState.sortes.find((s) => s.id === id);
    if (found) editSorte(found);
  }
</script>

<div class="vocab-pane">
  <div class="queue-panel vocab-list">
    <div class="panel-head">
      <h2>Sortes</h2>
      <span>{vocabState.sortes.length}</span>
    </div>
    <div class="queue-body">
      {#if !serverState.worldId}
        <div class="empty">Aucun monde actif.</div>
      {:else if !vocabState.sortes.length}
        <div class="empty">Aucune sorte. Une sorte compte ce qui n'a pas de nom : « 3 loups ».</div>
      {:else}
        {#each vocabState.sortes as sorte (sorte.id)}
          <div class="row-card sorte-row" class:closed={sorte.status !== 'active'}>
            <strong>{sorte.name}</strong>
            {#if sorte.status !== 'active'}<span class="badge b-other">retirée</span>{/if}
            <button onclick={() => editSorte(sorte)}>Renommer</button>
            {#if sorte.status === 'active'}
              <button onclick={() => setVocabStatus(serverState.worldId, 'sorte', sorte.id, 'retired')}>Retirer</button>
            {:else}
              <button onclick={() => setVocabStatus(serverState.worldId, 'sorte', sorte.id, 'active')}>Rétablir</button>
            {/if}
            {#if vocabState.actionError?.id === sorte.id}<div class="r-err">{vocabState.actionError.message}</div>{/if}
          </div>
        {/each}
      {/if}
    </div>
  </div>

  {#if vocabState.sorteDraft}
    <div class="queue-panel vocab-editor">
      <div class="panel-head"><h2>{vocabState.sorteDraft.id ? 'Renommer la sorte' : 'Nouvelle sorte'}</h2></div>
      <div class="queue-body">
        <label>Nom <input type="text" bind:value={vocabState.sorteDraft.name} placeholder="loup, bandit…"></label>
        {#if vocabState.near.length}
          <div class="near">
            <div>Ce nom ressemble à :</div>
            {#each vocabState.near as n (n.id)}
              <button onclick={() => openNear(n.id)}>{n.name} — {n.score} %</button>
            {/each}
            <button class="btn-send" onclick={() => saveSorteDraft(serverState.worldId, true)}>Créer quand même</button>
          </div>
        {/if}
        {#if vocabState.saveError}<div class="r-err">{vocabState.saveError}</div>{/if}
        <div style="margin-top:10px">
          <button class="btn-send" disabled={vocabState.saving} onclick={() => saveSorteDraft(serverState.worldId, false)}>
            {vocabState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
          </button>
          <button onclick={() => (vocabState.sorteDraft = null)}>Annuler</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .vocab-pane { display: flex; gap: 12px; align-items: flex-start; }
  .vocab-list { flex: 1; }
  .vocab-editor { flex: 0 0 360px; }
  .sorte-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .sorte-row .badge { width: auto; }
  .row-card.closed { opacity: 0.6; }
  .r-err { color: var(--red); }
  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
  label input[type="text"] { width: 100%; box-sizing: border-box; }
</style>
