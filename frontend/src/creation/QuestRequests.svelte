<script>
  /* TICKET-0121 (BRIEF-0121-G, L1, N1, C-14). « Demandes de quête »: every
     request the days opened, above the review queue -- a child of
     Queue.svelte, never a Création island of its own (INV-50). Each row
     offers what its status allows (C-02's case table, the server
     deciding): « Concevoir », the existence question, « Écrire dans
     Lore », « Mettre de côté », and the way to its proposal's card below.
     Nothing here reaches a model or a player surface. */
  import { serverState } from '../lib/serverState.svelte.js';
  import { queueState, setFilter } from './queue.svelte.js';
  import {
    questRequestsState, loadRequests, loadChoices, designRequest, answerRequest, resumeInLore,
    dropRequest, requestSubject, worldChanged,
  } from './questRequests.svelte.js';

  const TRIGGER_LABEL = Object.freeze({
    route: 'déclaration', blocked: 'étape bloquée', dropped: 'savoir introuvable',
  });
  const STATUS_LABEL = Object.freeze({
    new: 'à concevoir', asking: "question d'existence", writing_lore: 'à écrire dans Lore',
    proposed: 'proposée', covered: 'déjà couverte par :',
  });
  const PROPOSAL_LABEL = Object.freeze({
    proposed: 'en attente de revue', approved: 'approuvée', applied: 'appliquée', rejected: 'rejetée',
  });
  const ENTITY_GROUPS = Object.freeze([
    ['characters', 'Personnages'], ['locations', 'Lieux'], ['factions', 'Factions'], ['items', 'Objets'],
  ]);

  function mayDesign(r) {
    return r.status === 'new' || r.status === 'covered'
      || (r.status === 'proposed' && r.proposal?.status === 'rejected');
  }

  function mayDrop(r) {
    return !(r.status === 'proposed' && ['proposed', 'approved'].includes(r.proposal?.status));
  }

  async function showAlready(id) {
    questRequestsState.inputs[id].already = true;
    try {
      await loadChoices();
    } catch (e) {
      questRequestsState.error = e.message;
    }
  }

  function firstLine(text) {
    return (text || '').split('\n')[0];
  }

  // Declared before the reload, so a world change clears then reloads.
  $effect(() => {
    void serverState.worldId;
    worldChanged();
  });

  $effect(() => {
    void serverState.worldId;
    void queueState.reloadToken;
    loadRequests();
  });
</script>

<div class="quest-requests">
  <div class="panel-head">
    <h2>Demandes de quête ({questRequestsState.requests.length})</h2>
  </div>
  {#if questRequestsState.error}
    <div class="r-err">{questRequestsState.error}</div>
  {/if}
  {#each questRequestsState.requests as r (r.id)}
    {@const busy = !!questRequestsState.busy[r.id]}
    <div class="qr-row">
      <div class="qr-head">
        <strong>Jour {r.day_number ?? '—'}</strong>
        {#if r.character_name}<span>{r.character_name}</span>{/if}
        <span class="qr-tag">{TRIGGER_LABEL[r.trigger] || r.trigger}</span>
        <span class="qr-tag">
          {STATUS_LABEL[r.status] || r.status}
          {#if r.status === 'proposed' && r.proposal}— {PROPOSAL_LABEL[r.proposal.status] || r.proposal.status}{/if}
          {#if r.status === 'covered' && r.offer}{r.offer.title}{/if}
        </span>
      </div>
      <div class="qr-declaration">{firstLine(r.declaration)}</div>
      {#if r.subject}<div class="qr-line">Sujet : {r.subject}</div>{/if}
      {#if r.note}<div class="qr-line">{r.note}</div>{/if}

      {#if r.status === 'asking'}
        {@const box = questRequestsState.inputs[r.id]}
        <div class="qr-ask">
          <div>{requestSubject(r)} existe-t-il dans ce monde ?</div>
          <textarea rows="2" bind:value={box.text} placeholder="Ce que tu en dis (écrit dans Lore)"></textarea>
          <div class="qr-actions">
            <button disabled={busy} onclick={() => answerRequest(r.id, 'exists', box.text, null)}>Oui, il existe</button>
            <button disabled={busy} onclick={() => answerRequest(r.id, 'absent', box.text, null)}>Non, il n'existe pas</button>
            <button disabled={busy} onclick={() => showAlready(r.id)}>Le lore le dit déjà</button>
          </div>
          {#if box.already}
            <div class="qr-actions">
              <select bind:value={box.entityId}>
                <option value="">— l'entité qui le contient —</option>
                {#each ENTITY_GROUPS as [key, label] (key)}
                  <optgroup {label}>
                    {#each questRequestsState.choices?.[key] || [] as e (e.id)}
                      <option value={e.id}>{e.name}</option>
                    {/each}
                  </optgroup>
                {/each}
              </select>
              <button disabled={busy || !box.entityId}
                      onclick={() => answerRequest(r.id, 'already', box.text, box.entityId)}>Concevoir avec elle</button>
            </div>
          {/if}
        </div>
      {/if}

      <div class="qr-actions">
        {#if mayDesign(r)}
          <button disabled={busy} onclick={() => designRequest(r.id)}>{busy ? 'Conception…' : 'Concevoir'}</button>
        {/if}
        {#if r.status === 'writing_lore'}
          <button disabled={busy} onclick={() => resumeInLore(r)}>Écrire dans Lore</button>
        {/if}
        {#if r.proposal}
          <button disabled={busy} onclick={() => setFilter(r.proposal.status)}>Voir la proposition</button>
        {/if}
        {#if mayDrop(r)}
          <button disabled={busy} onclick={() => dropRequest(r.id)}>Mettre de côté</button>
        {/if}
      </div>
    </div>
  {/each}
</div>

<style>
  .quest-requests { margin-bottom: 10px; }
  .qr-row { border: 1px solid var(--border, #444); border-radius: 4px; padding: 6px 8px; margin: 6px 0; }
  .qr-head { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .qr-tag { font-size: 0.85em; opacity: 0.8; }
  .qr-declaration { margin: 4px 0; }
  .qr-line { font-size: 0.9em; opacity: 0.85; }
  .qr-ask { margin: 6px 0; display: flex; flex-direction: column; gap: 4px; }
  .qr-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
</style>
