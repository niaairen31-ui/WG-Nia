<script>
  /* TICKET-0128 (BRIEF-0128-F, C1, C′2): a resolved day waits for the
     creator -- she reads it, may rewrite the narrative, and publishes it
     once none of its proposals awaits her review. The narrator's text
     stays kept; the player reads the published one. */
  import { dayRunsState, publish } from './dayRuns.svelte.js';
</script>

<div class="queue-panel" id="journee-publish-panel">
  <div class="panel-head">
    <h2>À publier</h2>
  </div>
  <div class="queue-body">
    {#if dayRunsState.toPublishError}<div class="r-err">{dayRunsState.toPublishError}</div>{/if}
    {#if dayRunsState.actionError}<div class="r-err">{dayRunsState.actionError}</div>{/if}
    {#if dayRunsState.toPublish.length === 0}
      <div class="empty">Rien à publier.</div>
    {:else}
      <p class="muted">Le texte du narrateur reste gardé ; le joueur lira ce texte-ci.</p>
      {#each dayRunsState.toPublish as d (d.batch_id)}
        <div class="publish-row">
          <div><span class="badge b-other">Jour {d.day_number} — {d.character_name}</span></div>
          <p class="muted">{d.declared_action}</p>
          <textarea rows="8" bind:value={dayRunsState.drafts[d.batch_id]}
                    disabled={dayRunsState.busy === d.batch_id}></textarea>
          {#if d.pending_proposals > 0}
            <div class="r-err">{d.pending_proposals} proposition(s) de cette journée à revoir d'abord</div>
          {/if}
          <button
            disabled={d.pending_proposals > 0 || dayRunsState.busy === d.batch_id
              || !(dayRunsState.drafts[d.batch_id] || '').trim()}
            onclick={() => publish(d.batch_id)}
          >Publier</button>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; white-space: pre-wrap; }
  .publish-row { padding: 8px 0; border-bottom: 1px solid var(--border); }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
</style>
