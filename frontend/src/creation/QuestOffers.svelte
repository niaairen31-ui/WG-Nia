<script>
  /* TICKET-0108 (BRIEF-0108-C, E1). The « Quêtes » island: the world's
     quest offers and one offer's editor -- giver, title, summary,
     « répétable », open/closed, the conditions that decide who it is
     offered to, and its steps with what each needs and -- TICKET-0111
     (M1) -- when its objective is reached. Its CREATION_ISLANDS
     entry declares origin 'new'. Saving sends the whole offer; an accepted
     quest keeps its own copy (writes/quests.py). State and requests live in
     questOffers.svelte.js. TICKET-0121 (BRIEF-0121-F): the editor itself
     is OfferEditor.svelte, shared with the queue's review card. */
  import { serverState } from '../lib/serverState.svelte.js';
  import OfferEditor from './OfferEditor.svelte';
  import {
    questOffersState, loadOffers, newDraft, editOffer, saveDraft, refreshValue, saveEconomy,
  } from './questOffers.svelte.js';

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
  let value = $derived(questOffersState.value);

  // TICKET-0109 (E1): the world's rates; '' = the code's default.
  // TICKET-0110: the two debt settings, in relation points.
  const RATE_LABELS = {
    rate_money: 'Pièce', rate_relation: 'Point de relation', rate_fact: 'Fait', rate_skill: 'Compétence',
    band_low_pct: 'Bande basse (%)', band_high_pct: 'Bande haute (%)',
    debt_fact_relation: 'Dette : fait déjà su (relation −)',
    debt_skill_relation: 'Dette : compétence déjà connue (relation −)',
  };
  let showEconomy = $state(false);
  let economyDraft = $state({});
  function openEconomy() {
    const stored = questOffersState.economy?.stored || {};
    economyDraft = Object.fromEntries(Object.keys(RATE_LABELS).map((k) => [k, stored[k] ?? '']));
    showEconomy = !showEconomy;
  }
</script>

<div class="quest-offers">
  <div class="queue-panel quest-list">
    <div class="panel-head">
      <h2>Quêtes proposées</h2>
      <span>{questOffersState.offers.length}</span>
      <button class="btn-icon" onclick={() => openEconomy()} title="Unité indicative du monde">⚖</button>
      <button class="btn-icon" onclick={() => loadOffers(serverState.worldId)} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if showEconomy}
        <div class="economy">
          <strong>Unité indicative</strong>
          <p class="muted">Ce que vaut chaque terme, en unités ; vide = défaut. Un objet vaut sa propre valeur.</p>
          {#each Object.entries(RATE_LABELS) as [key, label] (key)}
            <label>{label}
              <input type="number" min="0" style="width:70px" bind:value={economyDraft[key]}
                     placeholder={String(questOffersState.economy?.defaults?.[key] ?? '')}>
            </label>
          {/each}
          {#if questOffersState.economyError}<div class="r-err">{questOffersState.economyError}</div>{/if}
          <button onclick={() => saveEconomy(economyDraft)}>Enregistrer les taux</button>
        </div>
      {/if}
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
            {#if offer.value && offer.value.verdict !== 'free'}<span class="badge b-other">{offer.value.verdict_label}</span>{/if}
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
        <OfferEditor {draft} {choices} {value} onchange={refreshValue} />

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
  .row-card { cursor: pointer; }
  .row-card.selected { background: rgba(106, 176, 255, 0.15); }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
  .economy { border: 1px solid var(--border); padding: 6px 8px; margin-bottom: 8px; }
  .economy label { display: inline-flex; gap: 4px; align-items: center; margin: 2px 8px 2px 0; }
</style>
