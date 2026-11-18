<script>
  // TICKET-0128 (BRIEF-0128-C, A1): the « PJ actif » selector, beside the
  // world selector. Several PCs and none chosen: the cockpit asks for one.
  import { serverState } from './lib/serverState.svelte.js';
  import { activePcState, loadActivePc, chooseActivePc } from './lib/activePc.svelte.js';

  $effect(() => {
    void serverState.worldId;
    loadActivePc();
  });

  const unchosen = $derived(activePcState.characters.length > 1 && !activePcState.chosen);
</script>

<label class="phase-indicator" for="active-pc-selector">PJ actif</label>
<select
  id="active-pc-selector"
  title="Le personnage joueur pour lequel agit le cockpit"
  disabled={activePcState.characters.length === 0}
  onchange={(event) => chooseActivePc(event.target.value)}
>
  {#if activePcState.characters.length === 0}
    <option value="" disabled selected>Aucun PJ</option>
  {:else}
    {#if unchosen}
      <option value="" selected>— Choisissez le PJ actif —</option>
    {/if}
    {#each activePcState.characters as c (c.id)}
      <option value={c.id} selected={!unchosen && c.id === activePcState.activeId}>{c.name}</option>
    {/each}
  {/if}
</select>
{#if activePcState.error}
  <span class="active-pc-error">{activePcState.error}</span>
{/if}

<style>
  .active-pc-error { color: var(--danger, #c33); font-size: 12px; }
</style>
