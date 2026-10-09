<script>
  /* TICKET-0112 (BRIEF-0112-E, IB1). « Écrire en langage naturel » under one
     condition of the offer editor: a sentence, then the proposal read back
     in French -- inserted into the draft or discarded by the creator. The
     requests live in conditionInterpreter.svelte.js. */
  import {
    interpreterState, askInterpreter, pickNames, insertProposal, discardProposal,
  } from './conditionInterpreter.svelte.js';

  let { cond, role } = $props();

  const s = $state(interpreterState());
  let proposal = $derived(s.proposal);
  let picked = $derived(proposal ? proposal.mentions.every((m) => s.picks[m.ref]) : false);
</script>

{#if !s.open}
  <button class="link" onclick={() => { s.open = true; }}>Écrire en langage naturel</button>
{:else}
  <div class="interp">
    <textarea rows="2" placeholder="Ex. : le joueur possède 15 fourrures de loup ou est membre de la Guilde"
              bind:value={s.instruction}></textarea>
    <div class="inline">
      <button disabled={s.busy || !s.instruction.trim()} onclick={() => askInterpreter(s, cond, role)}>
        {proposal ? 'Reformuler' : 'Proposer'}
      </button>
      <button class="link" onclick={() => { s.open = false; }}>Fermer</button>
      {#if s.busy}<span class="muted">Le modèle réfléchit…</span>{/if}
    </div>
    {#if s.error}<p class="err">{s.error}</p>{/if}
    {#if proposal}
      <div class="proposal">
        {#if proposal.view}
          {#each proposal.view.lines as line, i (i)}
            <div style={'padding-left:' + line.depth * 14 + 'px'}>{line.text}</div>
          {/each}
        {/if}
        {#each proposal.mentions as m (m.ref)}
          <label>« {m.name} » :
            <select bind:value={s.picks[m.ref]}>
              <option value="">choisir…</option>
              {#each m.choices as c (c.entity_id)}<option value={c.entity_id}>{c.name} ({c.type})</option>{/each}
            </select>
          </label>
        {/each}
        {#each proposal.notes as note, i (i)}<p class="muted">{note}</p>{/each}
        {#each proposal.errors as error, i (i)}<p class="err">{error}</p>{/each}
        <div class="inline">
          {#if proposal.outcome === 'needs_choice'}
            <button disabled={s.busy || !picked} onclick={() => pickNames(s)}>Appliquer les choix</button>
          {/if}
          {#if proposal.outcome === 'proposed'}
            <button onclick={() => insertProposal(s, cond)}>Insérer dans l'offre</button>
          {/if}
          <button onclick={() => discardProposal(s)}>Écarter</button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .interp { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
  .interp textarea { width: 100%; }
  .proposal { margin-top: 4px; }
  .inline { display: flex; gap: 6px; align-items: center; }
  .link { background: none; border: none; color: var(--accent, inherit); cursor: pointer; padding: 0; }
  .muted { color: var(--muted); font-size: 12px; }
  .err { color: var(--danger, #c33); font-size: 12px; }
</style>
