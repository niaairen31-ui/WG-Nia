<script>
  /* TICKET-0112 (BRIEF-0112-E, IB1). « Écrire en langage naturel » under one
     condition of the offer editor: a sentence, then the proposal read back
     in French -- inserted into the draft or discarded by the creator. The
     requests live in conditionInterpreter.svelte.js.
     TICKET-0113 (BRIEF-0113-E, WK2): a state the world lacks comes as a
     card -- use the near existing one, or create this one, retouched in
     AttributeDefinitionForm -- confirmed with « Insérer ».
     TICKET-0114 (BRIEF-0114-G, R1): an event type or a sorte the world
     lacks comes as a card too -- use the near one, or create this one now,
     a type retouched in EventTypeForm. */
  import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
  import EventTypeForm from './EventTypeForm.svelte';
  import { loadVocabulary, vocabState } from './eventVocab.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import {
    interpreterState, askInterpreter, pickNames, insertProposal, discardProposal, createVocab,
  } from './conditionInterpreter.svelte.js';

  let { cond, role, unsaved = [], types = [] } = $props();

  const s = $state(interpreterState());
  let proposal = $derived(s.proposal);
  let picked = $derived(proposal
    ? proposal.mentions.every((m) => s.picks[m.ref]) && s.cards.every((c) => c.pick)
      && s.vocab.every((c) => c.pick) : false);

  // EventTypeForm reads the world's entity types and domains.
  $effect(() => {
    if (s.vocab.some((c) => c.kind === 'type') && !vocabState.domains.length) loadVocabulary(serverState.worldId);
  });
</script>

{#if !s.open}
  <button class="link" onclick={() => { s.open = true; }}>Écrire en langage naturel</button>
{:else}
  <div class="interp">
    <textarea rows="2" placeholder="Ex. : le joueur possède 15 fourrures de loup ou est membre de la Guilde"
              bind:value={s.instruction}></textarea>
    <div class="inline">
      <button disabled={s.busy || !s.instruction.trim()} onclick={() => askInterpreter(s, cond, role, unsaved)}>
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
        {#each s.cards as card (card.ref)}
          <div class="card">
            <strong>État à créer : {card.draft.name}</strong>
            {#if card.near.length}
              <div class="muted">Ce nom ressemble à un état existant :</div>
              {#each card.near as n (n.key)}
                <label class="pick"><input type="radio" bind:group={card.pick} value={n.key}>
                  Utiliser « {n.name} »{n.system ? ' (système)' : ''} — {n.score} %</label>
              {/each}
              <label class="pick"><input type="radio" bind:group={card.pick} value="new">
                Créer « {card.draft.name} »</label>
            {/if}
            {#if card.pick === 'new'}
              <AttributeDefinitionForm draft={card.draft} {types} />
            {/if}
          </div>
        {/each}
        {#each s.vocab as card (card.ref)}
          <div class="card">
            <strong>{card.kind === 'type' ? 'Type d’événement' : 'Sorte'} à créer : {card.draft.name}</strong>
            {#if card.pick}
              <div class="muted">✓ {card.choice === 'new' ? 'créé' : 'existant'}</div>
            {:else}
              {#if card.near.length}
                <div class="muted">Ce nom ressemble à {card.kind === 'type' ? 'un type' : 'une sorte'} du monde :</div>
                {#each card.near as n (n.id)}
                  <label class="pick"><input type="radio" bind:group={card.choice} value={n.id}
                         onchange={() => { card.pick = n.id; }}> Utiliser « {n.name} » — {n.score} %</label>
                {/each}
                <label class="pick"><input type="radio" bind:group={card.choice} value="new">
                  Créer « {card.draft.name} »</label>
              {/if}
              {#if card.choice === 'new'}
                {#if card.kind === 'type'}
                  {#if vocabState.domains.length}<EventTypeForm draft={card.draft} vocab={vocabState} />{/if}
                  <div class="muted">Garde le nom des rôles : la condition les nomme.</div>
                {:else}
                  <input type="text" bind:value={card.draft.name}>
                {/if}
                <button disabled={card.busy || !card.draft.name.trim()} onclick={() => createVocab(card)}>
                  Créer {card.kind === 'type' ? 'ce type' : 'cette sorte'}
                </button>
              {/if}
              {#if card.error}<p class="err">{card.error}</p>{/if}
            {/if}
          </div>
        {/each}
        {#each proposal.notes as note, i (i)}<p class="muted">{note}</p>{/each}
        {#each proposal.errors as error, i (i)}<p class="err">{error}</p>{/each}
        <div class="inline">
          {#if proposal.outcome === 'needs_choice'}
            <button disabled={s.busy || !picked} onclick={() => pickNames(s, unsaved)}>Appliquer les choix</button>
          {/if}
          {#if proposal.outcome === 'proposed'}
            <button onclick={() => insertProposal(s, cond, unsaved)}>Insérer dans l'offre</button>
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
  .card { border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; margin: 6px 0; }
  .pick { display: block; margin: 2px 0; }
</style>
