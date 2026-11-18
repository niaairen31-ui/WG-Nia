<script>
  /* TICKET-0128 (BRIEF-0128-G, G1, D1, E1). « Ma journée »: the player
     declares what his character does, then reads the narrative once the
     creator published it -- nothing else of the day reaches him. */
  import { joueurState } from './joueur.svelte.js';
  import { dayState, loadPlayerDays, declarePlayerDay } from './day.svelte.js';

  const STATE_LABELS = {
    en_cours: 'en cours…',
    en_attente: 'en attente de la créatrice',
    abandonnee: 'abandonnée',
  };

  $effect(() => {
    void joueurState.character;
    loadPlayerDays();
  });
</script>

<section class="journee">
  <h2>Ma journée</h2>
  {#if dayState.canDeclare}
    <textarea
      bind:value={dayState.declaration}
      rows="4"
      placeholder="Que fait ton personnage aujourd'hui ?"
      disabled={dayState.submitting}
    ></textarea>
    <div>
      <button disabled={dayState.submitting || !dayState.declaration.trim()} onclick={() => declarePlayerDay()}>
        Déclarer
      </button>
    </div>
  {:else if dayState.characterId}
    <p class="muted">Ta journée suit son cours ; la suivante viendra une fois celle-ci publiée.</p>
  {/if}
  {#if dayState.error}<div class="r-err">{dayState.error}</div>{/if}

  {#each dayState.days as d, i (i)}
    <div class="day">
      <h3>Jour {d.day_number}</h3>
      <p class="declaration">{d.declared_action}</p>
      {#if d.state === 'publiee'}
        <p class="narrative">{d.text}</p>
      {:else}
        <p class="muted">{STATE_LABELS[d.state] || d.state}</p>
      {/if}
    </div>
  {/each}
</section>

<style>
  .journee { border-top: 1px solid var(--border); margin-top: 12px; padding-top: 8px; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .day { border-bottom: 1px solid var(--border); padding: 6px 0; }
  .declaration { font-style: italic; }
  .narrative { white-space: pre-wrap; }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
</style>
