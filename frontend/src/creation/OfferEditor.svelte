<script>
  /* TICKET-0121 (BRIEF-0121-F, B1). One quest offer's editor -- giver,
     title, summary, « répétable », open/closed, the conditions that decide
     who it is offered to, its steps with what each needs, when its
     objective is reached and when it fails, its costs and rewards and
     their indicative value -- moved out of QuestOffers.svelte so the
     review card of a `quest_offer_creation` proposal edits the very same
     form. A child component, never a Création island. `draft` is owned by
     the caller (questOffersState.draft in « Quêtes », the card's own draft
     in the queue); `onchange` runs when a term changes, so the caller
     recomputes `value`. */
  import ConditionEditor from './ConditionEditor.svelte';
  import QuestTermRow from './QuestTermRow.svelte';
  import { blankStep } from './questOffers.svelte.js';
  import { TERM_DIRECTIONS, blankTerm } from './questTerms.js';
  import { STEP_DOMAINS } from './questRequirements.js';

  let { draft, choices, value, seeds = {}, onchange = () => {} } = $props();

  // TICKET-0110 (X1): a faction giver may name its contact, one of its members.
  let giverMembers = $derived(choices?.members?.[draft.giver_entity_id]);

  function moveStep(index, delta) {
    const steps = draft.steps;
    const target = index + delta;
    if (target < 0 || target >= steps.length) return;
    [steps[index], steps[target]] = [steps[target], steps[index]];
  }

  function addTerm(direction) {
    draft.terms.push(blankTerm(direction));
    onchange();
  }
</script>

<label>Titre <input type="text" bind:value={draft.title}></label>
<label>Donnée par
  <select value={draft.giver_entity_id}
          onchange={(e) => { draft.giver_entity_id = e.target.value; draft.contact_entity_id = ''; }}>
    <option value="">—</option>
    {#each choices?.givers || [] as g (g.id)}<option value={g.id}>{g.name}</option>{/each}
  </select>
</label>
{#if giverMembers}
  <label>Contact de la faction
    <select bind:value={draft.contact_entity_id}>
      <option value="">— à choisir au besoin</option>
      {#each giverMembers as m (m.id)}<option value={m.id}>{m.name}</option>{/each}
    </select>
  </label>
{/if}
<label>Résumé <textarea rows="2" bind:value={draft.summary}></textarea></label>
<div class="inline">
  <label><input type="checkbox" bind:checked={draft.repeatable}> Répétable</label>
  <label>État
    <select bind:value={draft.status}>
      <option value="open">proposée</option>
      <option value="closed">fermée</option>
    </select>
  </label>
</div>

<h4>Proposée à qui remplit</h4>
<ConditionEditor cond={draft.eligibility} {choices} unsaved={draft.unsavedAttributes} role="eligibility" emptyLabel="Tout le monde." addLabel="+ condition" />

<h4>Étapes</h4>
{#each draft.steps as step, i (i)}
  <div class="quest-step">
    <div class="inline">
      <strong>{i + 1}.</strong>
      <input type="text" style="flex:1" placeholder="Objectif" bind:value={step.objective}>
      <label>Coût
        <select bind:value={step.cost}>{#each [1, 2, 3, 4] as c}<option value={c}>{c}</option>{/each}</select>
      </label>
      <label>Jet
        <select bind:value={step.domain}>
          <option value="">aucun</option>
          {#each STEP_DOMAINS as d}<option value={d}>{d}</option>{/each}
        </select>
      </label>
      <button class="btn-icon" title="Monter" onclick={() => moveStep(i, -1)}>↑</button>
      <button class="btn-icon" title="Descendre" onclick={() => moveStep(i, 1)}>↓</button>
      <button class="btn-icon" title="Retirer l'étape" disabled={draft.steps.length === 1}
              onclick={() => draft.steps.splice(i, 1)}>✕</button>
    </div>
    <div class="muted">Prérequis</div>
    <ConditionEditor cond={step.prerequisite} {choices} unsaved={draft.unsavedAttributes} role="prerequisite" addLabel="+ prérequis de l'étape" />
    <div class="muted">Objectif atteint quand</div>
    <ConditionEditor cond={step.completion} {choices} unsaved={draft.unsavedAttributes} role="completion"
                     emptyLabel="Rien de vérifiable : c'est vous qui le déclarez." addLabel="+ condition d'objectif" />
    <div class="muted">Échouée quand (affiché, n'agit jamais)</div>
    <ConditionEditor cond={step.failure} {choices} unsaved={draft.unsavedAttributes} role="failure"
                     emptyLabel="Aucune condition d'échec." addLabel="+ condition d'échec" />
  </div>
{/each}
<button onclick={() => draft.steps.push(blankStep())}>+ étape</button>

{#each Object.entries(TERM_DIRECTIONS) as [direction, label] (direction)}
  <h4>{direction === 'cost' ? 'Coûts (payés en déclarant la quête accomplie)' : 'Récompenses'}</h4>
  {#each draft.terms as term, k (k)}
    {#if term.direction === direction}
      <QuestTermRow {term} {choices} onchange={() => onchange()}
                    onremove={() => draft.terms.splice(k, 1)} />
    {/if}
  {/each}
  <button onclick={() => addTerm(direction)}>+ {label.toLowerCase()}</button>
{/each}

{#if value}
  <div class="value" class:warn={value.verdict === 'meagre' || value.verdict === 'generous'}>
    Valeur indicative : coût {value.cost}, récompense {value.reward}
    {#if value.ratio_pct !== null} — {value.ratio_pct} % (bande {value.band_low_pct}-{value.band_high_pct} %){/if}
    — <strong>{value.verdict_label}</strong>
  </div>
{/if}

<style>
  label { display: block; margin: 4px 0; }
  input[type="text"], textarea { width: 100%; box-sizing: border-box; }
  .inline { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .inline label { display: inline-flex; gap: 4px; align-items: center; }
  .quest-step { border-left: 2px solid var(--border); padding: 4px 0 6px 8px; margin: 6px 0; }
  .muted { color: var(--muted); font-size: 12px; }
  h4 { margin: 12px 0 4px; font-size: 13px; color: var(--muted); }
  .value { margin-top: 10px; font-size: 13px; }
  .value.warn { color: var(--red); }
</style>
