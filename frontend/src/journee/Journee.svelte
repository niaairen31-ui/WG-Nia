<script>
  /* TICKET-0075 (BRIEF-0075-a). Journée's own shell-native surface -- a
     sibling of Play/Création/Observation, mounted the same way as
     Observation.svelte (M10 precedent): always mounted from App.svelte,
     `active` only toggles this root's own visibility, no legacy bridge
     call.

     Once submitted, a declaration is never editable here: no edit control,
     no delete control, and `declared_action` has no update path anywhere
     in the backend (writes/pipeline.py). No agenda data is fetched,
     rendered or referenced anywhere in this surface (Scope OUT). */
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    journeeState, selectedDay, loadDays, selectDay, submitDeclaration, reloadForWorld,
  } from './journee.svelte.js';

  let { active = false } = $props();

  // Mirrors writes/pipeline.py's MAX_DECLARATION_CHARS -- no shared source
  // across the network boundary, so the two are kept in step by hand.
  const MAX_DECLARATION_CHARS = 4000;

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });
</script>

<div class="app-view" id="journee-view" style:display={active ? '' : 'none'}>

  <div class="queue-panel" id="journee-declare-panel">
    <div class="panel-head">
      <h2>Journée — déclarer une action</h2>
    </div>
    <div class="queue-body">
      <textarea
        bind:value={journeeState.declaration}
        maxlength={MAX_DECLARATION_CHARS}
        rows="6"
        placeholder="Que fait votre personnage aujourd'hui ?"
        disabled={journeeState.submitting}
      ></textarea>
      <div class="char-count">{journeeState.declaration.length} / {MAX_DECLARATION_CHARS}</div>
      {#if journeeState.submitError}
        <div class="r-err">{journeeState.submitError}</div>
      {/if}
      <div style="margin-top:8px">
        <button disabled={journeeState.submitting || !journeeState.declaration.trim()} onclick={() => submitDeclaration()}>
          Déclarer
        </button>
      </div>
    </div>
  </div>

  <div class="queue-panel" id="journee-list-panel">
    <div class="panel-head">
      <h2>Jours précédents</h2>
      <button class="btn-icon" onclick={() => loadDays()} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      {#if journeeState.daysLoading}
        <div class="empty"><span class="spin">⟳</span></div>
      {:else if journeeState.days.length === 0}
        <div class="empty">Aucun jour déclaré.</div>
      {:else}
        {#each journeeState.days as d (d.id)}
          <div class="day-row" class:selected={journeeState.selectedId === d.id} onclick={() => selectDay(d.id)}>
            <span class="badge b-other">Jour {d.day_number}</span>
            <span class="target-ref">{d.status}</span>
          </div>
        {/each}
      {/if}

      {#if selectedDay()}
        {@const day = selectedDay()}
        <div class="day-detail">
          <h3>Jour {day.day_number} — {day.status}</h3>
          <p>{day.declared_action}</p>
        </div>
      {/if}
    </div>
  </div>

</div><!-- #journee-view -->

<style>
  .r-err { color: var(--red); }
  .char-count { font-size: 12px; color: var(--muted); margin-top: 4px; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .day-row {
    display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer;
  }
  .day-row.selected { background: rgba(106, 176, 255, 0.15); }
  .day-detail {
    margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px;
    white-space: pre-wrap;
  }
</style>
