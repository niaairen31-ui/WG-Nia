<script>
  /* TICKET-0125 (BRIEF-0125-G). One open world: its name, description and
     laws, and « Ce que tout le monde sait » -- the public perspective, answer
     only (INV-66). « Créer mon personnage » opens the creation screen
     (TICKET-0126, BRIEF-0126-H). */
  import {
    joueurState, openWorld, askSavoir, selectSavoirCandidate, allSavoirChoicesMade, confirmSavoir,
  } from './joueur.svelte.js';
  import { characterState, openCreation } from './character.svelte.js';
  import CharacterCreation from './CharacterCreation.svelte';
</script>

{#if joueurState.world}
  {@const world = joueurState.world}
  <section class="world-page">
    <button onclick={() => openWorld(null)}>Retour aux mondes</button>
    <h1>{world.name}</h1>
    {#if world.description}
      <p class="world-description">{world.description}</p>
    {/if}
    {#if world.laws.length > 0}
      <h3>Lois du monde</h3>
      <ul>
        {#each world.laws as law, i (i)}
          <li>{law}</li>
        {/each}
      </ul>
    {/if}

    {#if characterState.open}
      <CharacterCreation />
    {:else}
      <div>
        <button onclick={() => openCreation()}>Créer mon personnage</button>
      </div>
    {/if}

    <section class="savoir">
      <h2>Ce que tout le monde sait</h2>
      <textarea
        bind:value={joueurState.question}
        rows="3"
        placeholder="Ex : qui gouverne la ville ?"
        disabled={joueurState.asking}
      ></textarea>
      <div>
        <button disabled={joueurState.asking || !joueurState.question.trim()} onclick={() => askSavoir()}>
          {joueurState.asking ? '⟳ Recherche…' : 'Demander'}
        </button>
      </div>
      {#if joueurState.error}
        <div class="r-err">{joueurState.error}</div>
      {/if}
      {#if joueurState.result}
        {@const result = joueurState.result}
        <p class="answer-prose">{result.answer}</p>
        {#if result.verdict === 'ambiguous_mention'}
          {#each Object.entries(result.candidates) as [ref, options] (ref)}
            <div class="candidate-group">
              {#each options as option (option.entity_id)}
                <label class="candidate-option">
                  <input
                    type="radio"
                    name={'savoir-candidate-' + ref}
                    checked={joueurState.selections[ref] === option.entity_id}
                    onchange={() => selectSavoirCandidate(ref, option.entity_id)}
                  />
                  {option.name} ({option.type})
                </label>
              {/each}
            </div>
          {/each}
          <button disabled={joueurState.asking || !allSavoirChoicesMade()} onclick={() => confirmSavoir()}>
            Confirmer
          </button>
        {/if}
      {/if}
    </section>
  </section>
{/if}

<style>
  .world-description, .answer-prose { white-space: pre-wrap; }
  .world-page ul { padding-left: 18px; }
  .savoir { border-top: 1px solid var(--border); margin-top: 12px; padding-top: 8px; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .candidate-group { display: flex; flex-direction: column; gap: 4px; margin: 6px 0; }
  .candidate-option { display: flex; align-items: center; gap: 6px; }
  .r-err { color: var(--red); }
</style>
