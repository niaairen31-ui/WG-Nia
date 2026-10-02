<script>
  /* TICKET-0101 (BRIEF-0101-E, K): "creating any child of a zone -- the
     zone's neighbours are offered as checkboxes". Shown in a NEW location's
     fiche. The parent is the fiche's own `parent_location_id` select
     (#author-x-parent_location_id, read like every field at save); this
     component listens to it, lists that parent's neighbours, and records
     the ticked ones in neighbourDraft.svelte.js. A visitable neighbour
     becomes a `connects_to`, a zone a `borde` -- decided by the server. */
  import { onMount } from 'svelte';
  import { neighbourDraftState, toggleNeighbour, resetNeighbourDraft, loadNeighbours } from './neighbourDraft.svelte.js';

  let { legacyDoc } = $props();

  let neighbours = $state([]);
  let parentChosen = $state(false);

  async function refresh(select) {
    resetNeighbourDraft();
    parentChosen = !!(select && select.value);
    neighbours = parentChosen ? await loadNeighbours(select.value) : [];
  }

  onMount(() => {
    const select = legacyDoc.getElementById('author-x-parent_location_id');
    if (!select) return undefined;
    const onChange = () => refresh(select);
    select.addEventListener('change', onChange);
    refresh(select);
    return () => select.removeEventListener('change', onChange);
  });
</script>

{#if !parentChosen}
  <div style="font-size:12px; color:var(--muted)">Choisissez un lieu parent pour proposer ses voisins.</div>
{:else if neighbours.length === 0}
  <div style="font-size:12px; color:var(--muted)">Le lieu parent n'a aucun voisin.</div>
{:else}
  <div style="font-size:12px; color:var(--muted); margin-bottom:4px">Cochez les voisins du parent qui touchent aussi ce lieu.</div>
  {#each neighbours as n (n.id)}
    <label style="display:flex; gap:6px; align-items:center; font-size:12px">
      <input type="checkbox" checked={neighbourDraftState.ids.includes(n.id)}
        onchange={(e) => toggleNeighbour(n.id, e.currentTarget.checked)}>
      {n.name}{n.is_zone ? ' (zone : lien « borde »)' : ''}
    </label>
  {/each}
{/if}
