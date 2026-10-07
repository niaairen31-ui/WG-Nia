<script>
  /* TICKET-0108 (BRIEF-0108-C, E1). The « Quêtes » island: the world's
     quest offers and one offer's editor -- giver, title, summary,
     « répétable », open/closed, the conditions that decide who it is
     offered to, and its steps with what each needs. Its CREATION_ISLANDS
     entry declares origin 'new'. Saving sends the whole offer; an accepted
     quest keeps its own copy (writes/quests.py). State and requests live in
     questOffers.svelte.js. */
  import { serverState } from '../lib/serverState.svelte.js';
  import QuestRequirementRow from './QuestRequirementRow.svelte';
  import {
    questOffersState, loadOffers, newDraft, editOffer, saveDraft, blankStep, addRequirement,
  } from './questOffers.svelte.js';
  import { STEP_DOMAINS } from './questRequirements.js';

  $effect(() => {
    questOffersState.draft = null;
    loadOffers(serverState.worldId);
  });

  /** The tab's « + Nouvelle quête » (creation_island.py rule 11). */
  export function primaryAction() {
    newDraft();
  }

  let draft = $derived(questOffersState.draft);
  let choices = $derived(questOffersState.choices);

  function moveStep(index, delta) {
    const steps = draft.steps;
    const target = index + delta;
    if (target < 0 || target >= steps.length) return;
    [steps[index], steps[target]] = [steps[target], steps[index]];
  }
</script>

<div class="quest-offers">
  <div class="queue-panel quest-list">
    <div class="panel-head">
      <h2>Quêtes proposées</h2>
      <span>{questOffersState.offers.length}</span>
      <button class="btn-icon" onclick={() => loadOffers(serverState.worldId)} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if !serverState.worldId}
        <div class="empty">Aucun monde actif.</div>
      {:else if questOffersState.loadError}
        <div class="empty" style="color:var(--red)">Erreur : {questOffersState.loadError}</div>
      {:else if questOffersState.offers.length === 0}
        <div class="empty">Aucune quête. « + Nouvelle quête » pour en écrire une.</div>
      {:else}
        {#each questOffersState.offers as offer (offer.id)}
          <div class="row-card" class:selected={draft?.id === offer.id} onclick={() => editOffer(offer)}>
            <strong>{offer.title}</strong>
            <span class="badge b-other">{offer.status === 'open' ? 'proposée' : 'fermée'}</span>
            {#if offer.repeatable}<span class="badge b-other">répétable</span>{/if}
            <div class="muted">par {offer.giver_name || '—'} · {offer.steps.length} étape(s)</div>
          </div>
        {/each}
      {/if}
    </div>
  </div>

  {#if draft}
    <div class="queue-panel quest-editor">
      <div class="panel-head">
        <h2>{draft.id ? 'Modifier la quête' : 'Nouvelle quête'}</h2>
      </div>
      <div class="queue-body">
        <label>Titre <input type="text" bind:value={draft.title}></label>
        <label>Donnée par
          <select bind:value={draft.giver_entity_id}>
            <option value="">—</option>
            {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
          </select>
        </label>
        <label>Résumé <textarea rows="2" bind:value={draft.summary}></textarea></label>
        <div class="inline">
          <label><input type="checkbox" bind:checked={draft.repeatable}> Répétable</label>
          <label>État
            <select bind:value={draft.status}>
              <option value="open">proposée</option>
              <option value="closed">fermée</option>
            </select>
          </label>
        </div>

        <h4>Proposée à qui remplit</h4>
        {#if draft.eligibility.length === 0}<p class="muted">Tout le monde.</p>{/if}
        {#each draft.eligibility as req, i (i)}
          <QuestRequirementRow {req} {choices} onremove={() => draft.eligibility.splice(i, 1)} />
        {/each}
        <button onclick={() => addRequirement(draft.eligibility)}>+ condition</button>

        <h4>Étapes</h4>
        {#each draft.steps as step, i (i)}
          <div class="quest-step">
            <div class="inline">
              <strong>{i + 1}.</strong>
              <input type="text" style="flex:1" placeholder="Objectif" bind:value={step.objective}>
              <label>Coût
                <select bind:value={step.cost}>{#each [1, 2, 3, 4] as c}<option value={c}>{c}</option>{/each}</select>
              </label>
              <label>Jet
                <select bind:value={step.domain}>
                  <option value="">aucun</option>
                  {#each STEP_DOMAINS as d}<option value={d}>{d}</option>{/each}
                </select>
              </label>
              <button class="btn-icon" title="Monter" onclick={() => moveStep(i, -1)}>↑</button>
              <button class="btn-icon" title="Descendre" onclick={() => moveStep(i, 1)}>↓</button>
              <button class="btn-icon" title="Retirer l'étape" disabled={draft.steps.length === 1}
                      onclick={() => draft.steps.splice(i, 1)}>✕</button>
            </div>
            {#each step.requirements as req, j (j)}
              <QuestRequirementRow {req} {choices} onremove={() => step.requirements.splice(j, 1)} />
            {/each}
            <button onclick={() => addRequirement(step.requirements)}>+ prérequis de l'étape</button>
          </div>
        {/each}
        <button onclick={() => draft.steps.push(blankStep())}>+ étape</button>

        {#if questOffersState.saveError}<div class="r-err">{questOffersState.saveError}</div>{/if}
        <div style="margin-top:10px">
          <button class="btn-send" disabled={questOffersState.saving} onclick={() => saveDraft(serverState.worldId)}>
            {questOffersState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .quest-offers { display: flex; gap: 12px; align-items: flex-start; }
  .quest-list { flex: 0 0 300px; }
  .quest-editor { flex: 1; }
  .quest-editor label { display: block; margin: 4px 0; }
  .quest-editor input[type="text"], .quest-editor textarea { width: 100%; box-sizing: border-box; }
  .inline { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .inline label { display: inline-flex; gap: 4px; align-items: center; }
  .quest-step { border-left: 2px solid var(--border); padding: 4px 0 6px 8px; margin: 6px 0; }
  .row-card { cursor: pointer; }
  .row-card.selected { background: rgba(106, 176, 255, 0.15); }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
</style>
