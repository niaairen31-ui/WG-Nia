<script>
  /* TICKET-0125 (BRIEF-0125-G, B2). The worlds open to players, each with
     its description and laws. */
  import { joueurState, loadWorlds, openWorld } from './joueur.svelte.js';

  loadWorlds();
</script>

<section class="world-list">
  <h1>Choisir un monde</h1>
  {#if joueurState.error}
    <div class="r-err">{joueurState.error}</div>
  {/if}
  {#if joueurState.worlds.length === 0}
    <p class="muted">Aucun monde n'est ouvert aux joueurs pour l'instant.</p>
  {:else}
    {#each joueurState.worlds as world (world.id)}
      <button class="world-card" onclick={() => openWorld(world)}>
        <h2>{world.name}</h2>
        {#if world.description}
          <p>{world.description}</p>
        {/if}
        {#if world.laws.length > 0}
          <h3>Lois du monde</h3>
          <ul>
            {#each world.laws as law, i (i)}
              <li>{law}</li>
            {/each}
          </ul>
        {/if}
      </button>
    {/each}
  {/if}
</section>

<style>
  .world-card { display: block; width: 100%; text-align: left; margin-bottom: 10px; padding: 10px;
    border: 1px solid var(--border); background: none; font: inherit; color: inherit; cursor: pointer; }
  .world-card h2 { margin: 0 0 6px; font-size: 16px; }
  .world-card h3 { margin: 8px 0 4px; font-size: 13px; }
  .world-card p { white-space: pre-wrap; margin: 0; }
  .world-card ul { margin: 0; padding-left: 18px; }
  .muted { color: var(--muted); }
  .r-err { color: var(--red); }
</style>
