<script>
  /* TICKET-0108 (BRIEF-0108-C). Journée's quests: the offers the player may
     accept (I1, only those he is eligible for) and his quests -- giver,
     state, steps, what the active step still needs, « Abandonner » (N1).
     A quest is shown by its title and objectives; the plan behind it is
     never named here. TICKET-0109 (BRIEF-0109-D): each offer and quest
     lists its costs and rewards; « Déclarer accomplie » opens the measured
     recap (SettlementRecap) and settles from it (D1). TICKET-0111
     (BRIEF-0111-D, M1): the active step shows where its objective stands,
     each line of its completion condition marked ✓, ✗ or ?, with its
     progress (« 3/15 ») -- shown, never acted on. */
  import { questState, loadQuests, acceptOffer, abandonQuest, openSettlement } from './quests.svelte.js';
  import SettlementRecap from './SettlementRecap.svelte';

  let confirming = $state(null);

  function abandon(questId) {
    if (confirming !== questId) { confirming = questId; return; }
    confirming = null;
    abandonQuest(questId);
  }
</script>

<div class="queue-panel" id="journee-quest-panel">
  <div class="panel-head">
    <h2>Quêtes</h2>
    <button class="btn-icon" onclick={() => loadQuests()} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if questState.loadError}<div class="r-err">{questState.loadError}</div>{/if}
    {#if questState.actionError}<div class="r-err">{questState.actionError}</div>{/if}

    <h4>Proposées</h4>
    {#if questState.offers.length === 0}
      <p class="muted">Aucune quête ne vous est proposée pour l'instant.</p>
    {/if}
    {#each questState.offers as offer (offer.offer_id)}
      <div class="row-card">
        <strong>{offer.title}</strong> <span class="muted">— {offer.giver_name || '—'}</span>
        {#if offer.summary}<div>{offer.summary}</div>{/if}
        <ol class="steps">{#each offer.steps as objective}<li>{objective}</li>{/each}</ol>
        {#if offer.terms?.length}<ul class="terms">{#each offer.terms as line}<li>{line}</li>{/each}</ul>{/if}
        <button disabled={questState.busy !== null} onclick={() => acceptOffer(offer.offer_id)}>
          {questState.busy === offer.offer_id ? 'Acceptation…' : 'Accepter'}
        </button>
      </div>
    {/each}

    <h4>Mes quêtes</h4>
    {#if questState.quests.length === 0}<p class="muted">Aucune.</p>{/if}
    {#each questState.quests as quest (quest.quest_id)}
      <div class="row-card" class:over={!quest.open}>
        <strong>{quest.title}</strong>
        <span class="badge b-other">{quest.settled ? 'réglée' : quest.state === 'accomplie' ? 'accomplie — à régler' : quest.state}</span>
        <span class="muted">— {quest.giver_name || '—'}</span>
        <ol class="steps">
          {#each quest.steps as step (step.order)}
            <li class={'step-' + step.status}>
              {step.objective}
              {#if step.status === 'completed'} ✓{/if}
              {#each step.blocked as reason}<div class="muted">Il manque : {reason}</div>{/each}
              {#if step.status === 'active' && step.completion?.length}
                <div class="objective">
                  <span class="muted">Objectif{step.completion_met ? ' atteint' : ''} :</span>
                  {#each step.completion as line, i (i)}
                    <div class={'cl-' + line.state} style={'padding-left:' + line.depth * 14 + 'px'}>
                      {line.mark} {line.text}{#if line.progress} — {line.progress}{/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </li>
          {/each}
        </ol>
        {#if quest.terms?.length}<ul class="terms">{#each quest.terms as line}<li>{line}</li>{/each}</ul>{/if}
        {#if quest.settleable}
          <button disabled={questState.busy !== null} onclick={() => openSettlement(quest.quest_id)}>
            {questState.settling === quest.quest_id ? 'Fermer' : 'Déclarer accomplie'}
          </button>
        {/if}
        {#if quest.open}
          <button disabled={questState.busy !== null} onclick={() => abandon(quest.quest_id)}>
            {confirming === quest.quest_id ? 'Confirmer l’abandon' : 'Abandonner'}
          </button>
        {/if}
        {#if questState.settling === quest.quest_id}<SettlementRecap questId={quest.quest_id} />{/if}
      </div>
    {/each}
  </div>
</div>

<style>
  .r-err { color: var(--red); }
  .muted { color: var(--muted); font-size: 12px; }
  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
  .steps { margin: 4px 0 6px 18px; padding: 0; }
  .step-active { font-weight: 600; }
  .step-completed, .step-failed { color: var(--muted); }
  .over { opacity: 0.7; }
  .terms { margin: 2px 0 6px 18px; padding: 0; font-size: 12px; }
  .objective { font-weight: normal; font-size: 12px; margin: 2px 0; }
  .cl-met { color: var(--green); }
  .cl-unmet { color: var(--muted); }
</style>
