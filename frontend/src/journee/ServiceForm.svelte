<script>
  /* TICKET-0110 (BRIEF-0110-D, S2). « Demander un service », in Journée's
     own tab: Nia names who helps (and the faction he acts for, if any),
     what he does now -- rewards the player receives, costs paid at once,
     such as a fall of regard -- and what the player will owe, prefilled
     from the coins and items received until she edits it; a motive and
     « transaction secrète ». Sent whole; the server applies the terms and
     writes the debt (writes/debt_sources.py), or refuses with nothing
     written. */
  import QuestTermRow from '../creation/QuestTermRow.svelte';
  import DebtTermRow from '../creation/DebtTermRow.svelte';
  import { blankTerm, TERM_DIRECTIONS } from '../creation/questTerms.js';
  import { serviceState, openService, servicePrefill, addOwed, askService } from './debts.svelte.js';

  let draft = $derived(serviceState.draft);
  let choices = $derived(serviceState.choices);
  // The factions the chosen provider is an active member of (X1).
  let factions = $derived(draft && choices
    ? (choices.factions || []).filter((f) => (choices.members?.[f.id] || []).some((m) => m.id === draft.provider_entity_id))
    : []);

  function setProvider(id) {
    draft.provider_entity_id = id;
    draft.on_behalf_of_id = '';
  }
</script>

<div class="queue-panel" id="journee-service-panel">
  <div class="panel-head">
    <h2>Demander un service</h2>
    {#if !draft}<button onclick={() => openService()}>+ Service</button>{/if}
  </div>
  <div class="queue-body">
    {#if serviceState.done && !draft}<p class="muted">{serviceState.done}</p>{/if}
    {#if draft}
      <label>Qui aide
        <select value={draft.provider_entity_id} onchange={(e) => setProvider(e.target.value)}>
          <option value="">—</option>
          {#each choices?.characters || [] as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
        </select>
      </label>
      {#if factions.length}
        <label>Pour le compte de
          <select bind:value={draft.on_behalf_of_id}>
            <option value="">lui-même</option>
            {#each factions as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
          </select>
        </label>
      {/if}
      {#each Object.entries(TERM_DIRECTIONS) as [direction, label] (direction)}
        <h4>{direction === 'reward' ? 'Ce qu’il fait pour vous' : 'Ce que ça coûte tout de suite'}</h4>
        {#each draft.terms as term, k (k)}
          {#if term.direction === direction}
            <QuestTermRow {term} {choices} onchange={() => servicePrefill()} onremove={() => draft.terms.splice(k, 1)} />
          {/if}
        {/each}
        <button onclick={() => { draft.terms.push(blankTerm(direction)); servicePrefill(); }}>+ {label.toLowerCase()}</button>
      {/each}
      <h4>Ce que vous devrez</h4>
      <div role="group" oninput={() => (draft.owedTouched = true)} onchange={() => (draft.owedTouched = true)}>
        {#each draft.owed as term, k (k)}
          <DebtTermRow {term} {choices} onremove={() => { draft.owedTouched = true; draft.owed.splice(k, 1); }} />
        {/each}
      </div>
      <button onclick={() => addOwed()}>+ terme dû</button>
      <label>Motif <input type="text" bind:value={draft.reason} placeholder="facultatif si quelque chose est dû"></label>
      <label><input type="checkbox" bind:checked={draft.is_secret}> Transaction secrète</label>
      {#if serviceState.error}<div class="r-err">{serviceState.error}</div>{/if}
      <div style="margin-top:8px">
        <button class="btn-send" disabled={serviceState.sending} onclick={() => askService()}>
          {serviceState.sending ? 'Envoi…' : 'Accepter le service'}
        </button>
        <button onclick={() => (serviceState.draft = null)}>Annuler</button>
      </div>
    {/if}
  </div>
</div>

<style>
  label { display: block; margin: 4px 0; }
  input[type="text"] { width: 100%; box-sizing: border-box; }
  h4 { margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
  .muted { color: var(--muted); font-size: 12px; }
  .r-err { color: var(--red); }
</style>
