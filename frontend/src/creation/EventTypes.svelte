<script>
  /* TICKET-0114 (BRIEF-0114-B, B1, C1, W1, T3). The event types of the
     world, in « Vocabulaire du monde »: each with its domain, its roles and
     the types they accept, who learns it, how many events it has; one type
     written or saved through EventTypeForm. A name near another type's is
     not saved until the creator picks: open the existing one, or create
     anyway. A type is retired (refused while a condition names it) or
     restored, never deleted. State and requests live in
     eventVocab.svelte.js. */
  import { serverState } from '../lib/serverState.svelte.js';
  import EventTypeForm from './EventTypeForm.svelte';
  import {
    vocabState, newTypeDraft, editType, saveTypeDraft, setVocabStatus,
  } from './eventVocab.svelte.js';

  /** The section's « + Nouveau » (Vocabulary.svelte routes it here). */
  export function primaryAction() {
    newTypeDraft();
  }

  let typeLabels = $derived(Object.fromEntries(vocabState.entityTypes.map((t) => [t.type, t.label])));
  let scopeLabels = $derived(Object.fromEntries(vocabState.scopeKinds.map((s) => [s.value, s.label])));
  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));

  function roleLine(role) {
    const accepts = role.entity_types.map((t) => typeLabels[t] || t);
    if (role.accepts_sorte) accepts.push('une sorte');
    return `${role.name} (${accepts.join(', ')})`;
  }

  function scopeLine(scope) {
    return `${scopeLabels[scope.kind] || scope.kind}${scope.role ? ' ' + scope.role : ''} : ${levelLabels[scope.level] || scope.level}`;
  }

  function openNear(id) {
    const found = vocabState.types.find((t) => t.id === id);
    if (found) editType(found);
  }
</script>

<div class="vocab-pane">
  <div class="queue-panel vocab-list">
    <div class="panel-head">
      <h2>Types d'événements</h2>
      <span>{vocabState.types.length}</span>
    </div>
    <div class="queue-body">
      {#if !serverState.worldId}
        <div class="empty">Aucun monde actif.</div>
      {:else if vocabState.loadError}
        <div class="empty" style="color:var(--red)">Erreur : {vocabState.loadError}</div>
      {:else if !vocabState.types.length}
        <div class="empty">Aucun type d'événement. « + Nouveau » en crée un.</div>
      {:else}
        {#each vocabState.types as type (type.id)}
          <div class="row-card" class:closed={type.status !== 'active'}>
            <div class="vocab-head">
              <strong>{type.name}</strong>
              <span class="badge b-other">{type.domain_label}</span>
              {#if type.counts_quantity}<span class="badge b-other">quantité</span>{/if}
              {#if type.in_chronicle}<span class="badge b-other">chronique</span>{/if}
              {#if type.participants_secret}<span class="badge b-other">secret</span>{/if}
              {#if type.status !== 'active'}<span class="badge b-other">retiré</span>{/if}
              <span class="muted">{type.events} événement(s)</span>
            </div>
            <div class="muted">Rôles : {type.roles.filter((r) => r.status === 'active').map(roleLine).join(' · ')}</div>
            <div class="muted">Apprennent : {type.scopes.length ? type.scopes.map(scopeLine).join(' · ') : 'les participants seulement'}</div>
            <div class="inline">
              <button onclick={() => editType(type)}>Modifier</button>
              {#if type.status === 'active'}
                <button disabled={type.in_condition} title={type.in_condition ? 'Une condition le nomme' : ''}
                        onclick={() => setVocabStatus(serverState.worldId, 'type', type.id, 'retired')}>Retirer</button>
              {:else}
                <button onclick={() => setVocabStatus(serverState.worldId, 'type', type.id, 'active')}>Rétablir</button>
              {/if}
            </div>
            {#if vocabState.actionError?.id === type.id}<div class="r-err">{vocabState.actionError.message}</div>{/if}
          </div>
        {/each}
      {/if}
    </div>
  </div>

  {#if vocabState.typeDraft}
    <div class="queue-panel vocab-editor">
      <div class="panel-head"><h2>{vocabState.typeDraft.id ? 'Modifier le type' : 'Nouveau type'}</h2></div>
      <div class="queue-body">
        <EventTypeForm draft={vocabState.typeDraft} vocab={vocabState} />
        {#if vocabState.near.length}
          <div class="near">
            <div>Ce nom ressemble à :</div>
            {#each vocabState.near as n (n.id)}
              <button onclick={() => openNear(n.id)}>{n.name} — {n.score} %</button>
            {/each}
            <button class="btn-send" onclick={() => saveTypeDraft(serverState.worldId, true)}>Créer quand même</button>
          </div>
        {/if}
        {#if vocabState.saveError}<div class="r-err">{vocabState.saveError}</div>{/if}
        <div style="margin-top:10px">
          <button class="btn-send" disabled={vocabState.saving} onclick={() => saveTypeDraft(serverState.worldId, false)}>
            {vocabState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
          </button>
          <button onclick={() => (vocabState.typeDraft = null)}>Annuler</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .vocab-pane { display: flex; gap: 12px; align-items: flex-start; }
  .vocab-list { flex: 1; }
  .vocab-editor { flex: 0 0 460px; }
  .vocab-head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .vocab-head .badge { width: auto; }
  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
  .row-card.closed { opacity: 0.6; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
</style>
