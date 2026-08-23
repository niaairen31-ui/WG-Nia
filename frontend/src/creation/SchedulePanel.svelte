<script>
  /* TICKET-0074 (BRIEF-0074-b). "Qui est ici, par phase" -- the F1 read
     panel, B1's compensating control: with no coverage check on
     npc_schedule, an empty phase must be visible to the author before a
     player walks into one. Four groups in SCHEDULE_PHASES order, each
     listing the NPCs GET /api/locations/{id}/schedule resolves there
     (source labelled), rendering visibly empty when nobody resolves;
     below them, the unresolved block for the world's CURRENT phase --
     the phase the server marks is_present -- naming NPCs that resolve
     nowhere right now.

     Read-only by construction: this file issues exactly one fetch, no
     method option, an implicit GET -- verify/checks/npc_schedule.py's R9
     asserts no POST/PUT/PATCH/DELETE method literal appears in this
     file's source. Self-contained, unlike ScheduleEditor: a read-only
     panel has no write cycle to share through sheetRequest.svelte.js, so
     it owns its own trivial fetch instead of a companion state module. */
  import { SCHEDULE_PHASES, PHASE_LABELS } from './schedule.js';

  let { entityId } = $props();

  let data = $state(null);
  let loadError = $state('');

  $effect(() => {
    const id = entityId;
    (async () => {
      try {
        const res = await fetch(`/api/locations/${encodeURIComponent(id)}/schedule`);
        if (!res.ok) throw new Error(`GET /api/locations/${id}/schedule -> ${res.status}`);
        data = await res.json();
        loadError = '';
      } catch (e) {
        data = null;
        loadError = e.message;
      }
    })();
  });

  const currentGroup = $derived(data ? data.phases.find((p) => p.phase === data.current_phase) : null);
</script>

{#if loadError}
  <div class="empty">{loadError}</div>
{:else if !data}
  <div class="empty"><span class="spin">⟳</span></div>
{:else}
  <div class="row-table">
    {#each SCHEDULE_PHASES as phase (phase)}
      {@const group = data.phases.find((p) => p.phase === phase)}
      <div class="row-card">
        <div style="font-size:12px; font-weight:600; margin-bottom:4px;">{PHASE_LABELS[phase]}</div>
        {#if !group || group.npcs.length === 0}
          <div class="empty">Personne.</div>
        {:else}
          {#each group.npcs as npc (npc.npc_id)}
            <span class="badge b-other" style="margin:2px 4px 0 0;">{npc.name} <span style="opacity:0.6">({npc.source})</span></span>
          {/each}
        {/if}
      </div>
    {/each}
  </div>
  <div class="row-card">
    <div style="font-size:12px; font-weight:600; margin-bottom:4px;">Non résolus ({PHASE_LABELS[data.current_phase]})</div>
    {#if !currentGroup || currentGroup.unresolved.length === 0}
      <div class="empty">Aucun.</div>
    {:else}
      {#each currentGroup.unresolved as npc (npc.npc_id)}
        <span class="badge b-rejected" style="margin:2px 4px 0 0;">{npc.name}</span>
      {/each}
    {/if}
  </div>
{/if}
