<script>
  // TICKET-0128 (BRIEF-0128-E, Y1): while the day worker runs, the header
  // says so -- the plan holds the database's write lock for its duration.
  import { onMount } from 'svelte';
  import { api } from './creation/sheetRequest.svelte.js';

  let running = $state(null);
  let queued = $state(0);

  async function poll() {
    try {
      const etat = await api('/api/day-runs/etat');
      running = etat.running;
      queued = etat.queued;
    } catch (_e) {
      running = null;
      queued = 0;
    }
  }

  onMount(() => {
    poll();
    const timer = setInterval(poll, 5000);
    return () => clearInterval(timer);
  });
</script>

{#if running}
  <span class="phase-indicator day-run-banner">
    Journée en calcul… (Jour {running.day_number} — {running.character_name}, {running.world_name})
    {#if queued > 0}+ {queued} en attente{/if}
  </span>
{/if}
