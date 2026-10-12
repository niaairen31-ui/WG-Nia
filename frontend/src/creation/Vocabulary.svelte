<script>
  /* TICKET-0114 (BRIEF-0114-B, T3). The « Vocabulaire du monde » island:
     what the world can say grows by data, and the creator keeps it in one
     place -- its states (States.svelte, TICKET-0113, unchanged), its event
     types (EventTypes.svelte) and its sortes (Sortes.svelte), one section
     shown at a time. The tab's « + Nouveau » goes to the section shown. Its
     CREATION_ISLANDS entry declares origin 'new'. */
  import { serverState } from '../lib/serverState.svelte.js';
  import States from './States.svelte';
  import EventTypes from './EventTypes.svelte';
  import Sortes from './Sortes.svelte';
  import { loadVocabulary, vocabState } from './eventVocab.svelte.js';

  const SECTIONS = [
    { key: 'states', label: 'États' },
    { key: 'types', label: "Types d'événements" },
    { key: 'sortes', label: 'Sortes' },
  ];
  let section = $state('states');
  let refs = $state({ states: null, types: null, sortes: null });

  $effect(() => {
    vocabState.typeDraft = null;
    vocabState.sorteDraft = null;
    loadVocabulary(serverState.worldId);
  });

  /** The tab's « + Nouveau » (creation_island.py rule 11). */
  export function primaryAction() {
    refs[section]?.primaryAction();
  }
</script>

<div class="vocabulary">
  <div class="vocab-sections">
    {#each SECTIONS as s (s.key)}
      <button class:active={section === s.key} onclick={() => (section = s.key)}>{s.label}</button>
    {/each}
  </div>
  {#if section === 'states'}
    <States bind:this={refs.states} />
  {:else if section === 'types'}
    <EventTypes bind:this={refs.types} />
  {:else}
    <Sortes bind:this={refs.sortes} />
  {/if}
</div>

<style>
  .vocab-sections { display: flex; gap: 6px; margin-bottom: 10px; }
  .vocab-sections button.active { font-weight: 600; border-bottom: 2px solid var(--accent, #c9a14a); }
</style>
