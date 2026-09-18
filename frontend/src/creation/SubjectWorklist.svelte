<script>
  /* TICKET-0088 (BRIEF-0088-b). The subject worklist: every knowledge
     subject of the active world that no fact_participant binds yet, with a
     one-action bind per subject. Its CREATION_ISLANDS entry declares
     origin 'new' -- a surface created as an island, with no legacy
     predecessor. State and requests live in subjectWorklist.svelte.js;
     the empty and error states below are part of what the list means. */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    subjectState, loadSubjects, suggestedEntityId, selectedEntityId, selectEntity, bindSubject,
  } from './subjectWorklist.svelte.js';

  $effect(() => {
    loadSubjects(serverState.worldId);
  });

  let busy = $derived(subjectState.bindingSubject !== null);
  let lineTotal = $derived(subjectState.rows.reduce((n, r) => n + r.row_count, 0));

  function entityLabel(id) {
    const e = subjectState.entities.find((x) => x.id === id);
    return e ? `${e.name} (${e.type})` : '';
  }
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Sujets non résolus</h2>
    <span>{subjectState.rows.length} sujet(s) · {lineTotal} ligne(s)</span>
    <button class="btn-icon" disabled={busy} onclick={() => loadSubjects(serverState.worldId)} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if !serverState.worldId}
      <div class="empty">Aucun monde actif.</div>
    {:else if subjectState.loading && subjectState.rows.length === 0}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if subjectState.loadError}
      <div class="empty" style="color:var(--red)">Erreur : {subjectState.loadError}</div>
    {:else if subjectState.rows.length === 0}
      <div class="empty-ok">✓ Aucun sujet non résolu dans ce monde.</div>
    {:else}
      {#each subjectState.rows as row (row.subject)}
        <div class="row-card">
          <div><strong>{row.subject}</strong></div>
          <div style="font-size:12px;">{row.row_count} ligne(s) · {row.fact_ids.length} fait(s)</div>
          <div style="font-size:12px;">
            {#if suggestedEntityId(row)}
              Suggestion : {entityLabel(suggestedEntityId(row))}
            {:else if row.resolution && row.resolution.verdict === 'ambiguous'}
              Ambigu : {row.resolution.candidate_ids.length} candidat(s)
            {:else}
              Aucune suggestion
            {/if}
          </div>
          <div class="row-card-actions">
            <select value={selectedEntityId(row)} disabled={busy}
                    onchange={(e) => selectEntity(row.subject, e.target.value)}>
              <option value="">—</option>
              {#each subjectState.entities as ent (ent.id)}
                <option value={ent.id}>{ent.name} ({ent.type})</option>
              {/each}
            </select>
            <button class="btn-send" disabled={busy || !selectedEntityId(row)} onclick={() => bindSubject(row)}>
              {subjectState.bindingSubject === row.subject ? 'Liaison…' : 'Lier'}
            </button>
          </div>
          {#if subjectState.bindErrors[row.subject]}
            <div style="color:var(--red); font-size:12px;">{subjectState.bindErrors[row.subject]}</div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>
