<script>
  /* TICKET-0113 (BRIEF-0113-C, WI1, WJ2, WK2). The « États » island: the
     attributes of the world -- the system ones first, read where they live
     and never edited here -- and one definition written or saved through
     AttributeDefinitionForm. A name near another attribute's is not saved
     until the creator picks: open the existing one, or create anyway. A
     definition is retired (refused while a condition names it) or
     restored, never deleted. Its CREATION_ISLANDS entry declares origin
     'new'. State and requests live in attributes.svelte.js. */
  import { serverState } from '../lib/serverState.svelte.js';
  import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
  import {
    statesState, loadAttributes, newAttributeDraft, editAttribute, saveAttributeDraft, setAttributeStatus,
  } from './attributes.svelte.js';

  $effect(() => {
    statesState.draft = null;
    loadAttributes(serverState.worldId);
  });

  /** The tab's « + Nouvel état » (creation_island.py rule 11). */
  export function primaryAction() {
    newAttributeDraft();
  }

  const KINDS = { choice: 'choix', integer: 'nombre', entity: 'entité' };

  let typeLabels = $derived(Object.fromEntries(statesState.entityTypes.map((t) => [t.type, t.label])));

  function typesOf(list) {
    return list === null ? 'toute entité' : list.map((t) => typeLabels[t] || t).join(', ');
  }

  function openNear(key) {
    const attr = statesState.attributes.find((a) => a.key === key);
    if (attr && !attr.system) editAttribute(attr);
    else statesState.draft = null;
  }
</script>

<div class="states">
  <div class="queue-panel state-list">
    <div class="panel-head">
      <h2>États du monde</h2>
      <span>{statesState.attributes.length}</span>
      <button class="btn-icon" onclick={() => loadAttributes(serverState.worldId)} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if !serverState.worldId}
        <div class="empty">Aucun monde actif.</div>
      {:else if statesState.loadError}
        <div class="empty" style="color:var(--red)">Erreur : {statesState.loadError}</div>
      {:else}
        {#each statesState.attributes as attr (attr.key)}
          <div class="row-card" class:closed={attr.status !== 'active'}>
            <div class="state-head">
              <strong>{attr.name}</strong>
              <span class="badge b-other">{KINDS[attr.kind]}</span>
              {#if attr.system}<span class="badge b-other">système</span>{/if}
              {#if attr.hidden}<span class="badge b-other">caché</span>{/if}
              {#if attr.status !== 'active'}<span class="badge b-other">retiré</span>{/if}
            </div>
            <div class="muted">S'applique à : {typesOf(attr.holder_types)}
              {#if attr.kind === 'entity'} · nomme : {typesOf(attr.value_types)}{/if}</div>
            {#if attr.choices.length}
              <div class="muted">{attr.choices.map((c) => c.label + (c.value === attr.default ? ' (défaut)' : '')).join(' · ')}</div>
            {:else if attr.kind === 'integer'}
              <div class="muted">Défaut : {attr.default}</div>
            {/if}
            {#if !attr.system}
              <div class="inline">
                <button onclick={() => editAttribute(attr)}>Modifier</button>
                {#if attr.status === 'active'}
                  <button disabled={attr.in_condition} title={attr.in_condition ? 'Une condition le nomme' : ''}
                          onclick={() => setAttributeStatus(serverState.worldId, attr.key, 'retired')}>Retirer</button>
                {:else}
                  <button onclick={() => setAttributeStatus(serverState.worldId, attr.key, 'active')}>Rétablir</button>
                {/if}
              </div>
            {/if}
            {#if statesState.actionError?.key === attr.key}<div class="r-err">{statesState.actionError.message}</div>{/if}
          </div>
        {/each}
      {/if}
    </div>
  </div>

  {#if statesState.draft}
    <div class="queue-panel state-editor">
      <div class="panel-head"><h2>{statesState.draft.key ? 'Modifier l’état' : 'Nouvel état'}</h2></div>
      <div class="queue-body">
        <AttributeDefinitionForm draft={statesState.draft} types={statesState.entityTypes} />
        {#if statesState.near.length}
          <div class="near">
            <div>Ce nom ressemble à :</div>
            {#each statesState.near as n (n.key)}
              <button onclick={() => openNear(n.key)}>{n.name}{n.system ? ' (système)' : ''} — {n.score} %</button>
            {/each}
            <button class="btn-send" onclick={() => saveAttributeDraft(serverState.worldId, true)}>Créer quand même</button>
          </div>
        {/if}
        {#if statesState.saveError}<div class="r-err">{statesState.saveError}</div>{/if}
        <div style="margin-top:10px">
          <button class="btn-send" disabled={statesState.saving} onclick={() => saveAttributeDraft(serverState.worldId, false)}>
            {statesState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
          </button>
          <button onclick={() => (statesState.draft = null)}>Annuler</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .states { display: flex; gap: 12px; align-items: flex-start; }
  .state-list { flex: 1; }
  .state-editor { flex: 0 0 420px; }
  .state-head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .state-head .badge { width: auto; }
  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
  .row-card.closed { opacity: 0.6; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
</style>
