<script>
  /* TICKET-0128 (BRIEF-0128-E, L1, M1, Z1): the days the worker could not
     finish, each with its stage and reason -- « Relancer » sends it back to
     the stage that failed, « Abandonner » gives it up. */
  import { dayRunsState, relaunch, abandon } from './dayRuns.svelte.js';
</script>

<div class="queue-panel" id="journee-failures-panel">
  <div class="panel-head">
    <h2>Journées en échec</h2>
  </div>
  <div class="queue-body">
    {#if dayRunsState.failuresError}<div class="r-err">{dayRunsState.failuresError}</div>{/if}
    {#if dayRunsState.actionError}<div class="r-err">{dayRunsState.actionError}</div>{/if}
    {#if dayRunsState.failures.length === 0}
      <div class="empty">Aucune journée en échec.</div>
    {:else}
      {#each dayRunsState.failures as f (f.batch_id)}
        <div class="failure-row">
          <div><span class="badge b-other">Jour {f.day_number} — {f.character_name}</span>
            {f.stage_label} · {f.code_label}</div>
          <div class="muted">{f.reason}</div>
          <div class="failure-actions">
            <button disabled={dayRunsState.busy === f.batch_id} onclick={() => relaunch(f.batch_id)}>Relancer</button>
            <button disabled={dayRunsState.busy === f.batch_id} onclick={() => abandon(f.batch_id)}>Abandonner</button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; white-space: pre-wrap; }
  .failure-row { padding: 6px 0; border-bottom: 1px solid var(--border); }
  .failure-actions { display: flex; gap: 6px; margin-top: 4px; }
</style>
