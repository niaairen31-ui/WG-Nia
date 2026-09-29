<script>
  /* TICKET-0088 (BRIEF-0088-b), re-aimed by TICKET-0097 (BRIEF-0097-f, I1/J1).
     The « Sujets » worklist: every fact of the active world that someone
     knows and no fact_participant binds yet, with a one-action bind per
     fact. A card shows the fact's text, the first knower's version of it
     and how many entities know it (J1), then the Lore resolver's candidates
     and near names -- the resolver never picks. Its CREATION_ISLANDS entry
     declares origin 'new'. State and requests live in
     subjectWorklist.svelte.js; the empty and error states below are part of
     what the list means. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    subjectState, loadFacts, suggestedEntityId, selectedEntityId, selectEntity, bindFact,
  } from './subjectWorklist.svelte.js';

  $effect(() => {
    loadFacts(serverState.worldId);
  });

  let busy = $derived(subjectState.bindingFact !== null);

  function entityLabel(id) {
    const e = subjectState.entities.find((x) => x.id === id);
    return e ? `${e.name} (${e.type})` : '';
  }
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Sujets non résolus</h2>
    <span>{subjectState.rows.length} fait(s)</span>
    <button class="btn-icon" disabled={busy} onclick={() => loadFacts(serverState.worldId)} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if !serverState.worldId}
      <div class="empty">Aucun monde actif.</div>
    {:else if subjectState.loading && subjectState.rows.length === 0}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if subjectState.loadError}
      <div class="empty" style="color:var(--red)">Erreur : {subjectState.loadError}</div>
    {:else if subjectState.rows.length === 0}
      <div class="empty-ok">✓ Tous les faits connus de ce monde ont un sujet.</div>
    {:else}
      {#each subjectState.rows as row (row.fact_id)}
        <div class="row-card">
          <div><strong>{row.fact}</strong></div>
          {#if row.excerpt}
            <div style="font-size:12px;">« {row.excerpt.text} » — {row.excerpt.entity_name}</div>
          {/if}
          <div style="font-size:12px; color:var(--muted);">{row.knower_count} personnage(s) le savent</div>
          <div style="font-size:12px;">
            {#if suggestedEntityId(row)}
              Suggestion : {entityLabel(suggestedEntityId(row))}
            {:else if row.candidates.length > 1}
              Plusieurs candidats : {row.candidates.map((c) => c.name).join(', ')}
            {:else if row.near.length > 0}
              Noms proches : {row.near.map((c) => `${c.name} (${c.score})`).join(', ')}
            {:else}
              Aucune suggestion
            {/if}
          </div>
          <div class="row-card-actions">
            <select value={selectedEntityId(row)} disabled={busy}
                    onchange={(e) => selectEntity(row.fact_id, e.target.value)}>
              <option value="">—</option>
              {#each subjectState.entities as ent (ent.id)}
                <option value={ent.id}>{ent.name} ({ent.type})</option>
              {/each}
            </select>
            <button class="btn-send" disabled={busy || !selectedEntityId(row)} onclick={() => bindFact(row)}>
              {subjectState.bindingFact === row.fact_id ? 'Liaison…' : 'Lier'}
            </button>
          </div>
          {#if subjectState.bindErrors[row.fact_id]}
            <div style="color:var(--red); font-size:12px;">{subjectState.bindErrors[row.fact_id]}</div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>
