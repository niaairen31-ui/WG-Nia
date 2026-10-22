<script>
  /* TICKET-0124 (BRIEF-0124-I; A2, G2, H1). « Ce que le monde ajoute » on a
     NEW character, location or faction sheet: what the draft's world block
     resolved (draft_world.py) -- its states, its links, the character it
     may be, the entities it calls for. The creator keeps or drops each one
     (the value of a state is changed after the create, in « États »); the
     create sends the kept ones (worldExtrasForCreate). Entities to create
     start unticked (I1). On a germ's draft, « Rattacher » joins the germ to
     the possible same person instead. No dialog. */
  import { pendingDraftsState } from './pendingDrafts.svelte.js';
  import { getPendingCreationMutationId } from './sheetState.svelte.js';
  import { attachGerm } from './tabs.js';

  const TYPE_LABELS = { character: 'personnage', location: 'lieu', faction: 'faction' };

  let attachStatus = $state('');

  const world = $derived(pendingDraftsState.world);
  const empty = $derived(!world.states.length && !world.links.length && !world.sameAs && !world.toCreate.length);

  async function attachSameAs() {
    const mutationId = getPendingCreationMutationId();
    if (!mutationId || !world.sameAs) return;
    attachStatus = '';
    try {
      await attachGerm(mutationId, world.sameAs.entity_id);
      attachStatus = "Rattaché — cette fiche n'est plus nécessaire.";
    } catch (e) {
      attachStatus = `Erreur : ${e.message}`;
    }
  }
</script>

{#if !empty}
  {#if world.states.length}
    <div style="font-size:12px; font-weight:600; margin:4px 0">États</div>
    {#each world.states as s (s.key)}
      <label class="field-row checkbox">
        <input type="checkbox" bind:checked={s.checked}>
        <span>{s.name} : <strong>{s.label}</strong></span>
      </label>
    {/each}
  {/if}

  {#if world.links.length}
    <div style="font-size:12px; font-weight:600; margin:8px 0 4px">Liens</div>
    {#each world.links as l (l.entity_id)}
      <div class="row-card">
        <label class="field-row checkbox">
          <input type="checkbox" bind:checked={l.checked}>
          <span>{l.name}</span>
        </label>
        <input type="text" bind:value={l.type} placeholder="élève, rival…">
        {#if !(l.type || '').trim()}<span style="font-size:11px; color:var(--muted)">type requis</span>{/if}
        {#if l.note}<div style="font-size:12px; color:var(--muted)">{l.note}</div>{/if}
      </div>
    {/each}
  {/if}

  {#if world.sameAs}
    <div class="row-card">
      <div>Peut-être la même personne que {world.sameAs.name}.</div>
      {#if getPendingCreationMutationId()}
        <button class="btn-ghost" onclick={attachSameAs}>Rattacher à {world.sameAs.name}</button>
      {/if}
      {#if attachStatus}<div style="font-size:12px">{attachStatus}</div>{/if}
    </div>
  {/if}

  {#if world.toCreate.length}
    <div style="font-size:12px; font-weight:600; margin:8px 0 4px">À créer ensuite</div>
    {#each world.toCreate as g (g.name)}
      <div class="row-card">
        <label class="field-row checkbox">
          <input type="checkbox" bind:checked={g.checked}>
          <span><strong>{g.name}</strong> ({TYPE_LABELS[g.entity_type] ?? g.entity_type}){g.link_type ? ` — ${g.link_type}` : ''}</span>
        </label>
        {#if g.concept}<div style="font-size:12px; color:var(--muted)">{g.concept}</div>{/if}
      </div>
    {/each}
    <div style="font-size:11px; color:var(--muted)">Coché : un germe l'attend dans « En attente », lié à cette fiche.</div>
  {/if}
{/if}
