<script>
  /* TICKET-0085 (BRIEF-0085-e). Lore's own shell-native surface -- a sibling
     of Play/Création/Observation/Journée, mounted the same way as
     Journee.svelte/Observation.svelte: always mounted from App.svelte,
     `active` only toggles this root's own visibility, no legacy bridge call.

     Read-only surface: no editing control, no "corriger", no link into the
     CRUD forms (Scope OUT) -- the assertion path is a later ticket.
     Bounded reopening (TICKET-0091, BRIEF-0091-K, Q17d): the "Noms à lier"
     tab (NamesPanel.svelte) binds or dismisses plain names in canon prose;
     the question view and the consultation pipeline stay read-only. */
  import { serverState } from '../lib/serverState.svelte.js';
  import NamesPanel from './NamesPanel.svelte';
  import {
    loreState, askLore, selectCandidate, allAmbiguitiesResolved, confirmResolution,
    reloadForWorld,
  } from './lore.svelte.js';

  let { active = false } = $props();

  let loreTab = $state('question');

  const RENDERER_LABEL = Object.freeze({
    model: 'rédigé par le modèle',
    template: 'modèle indisponible — réponse déterministe',
  });

  const SECTION_LABEL = Object.freeze({
    identity: 'Identité',
    facets: 'Faits',
    relations: 'Relations',
    knowledge: 'Connaissances',
    memberships: 'Appartenances',
    goals: 'Objectifs',
    factions: 'Factions',
  });

  // Trace entries come in two shapes from lore_query.py's execute_plan --
  // a mention entry (surface_form/verdict/rung/entity_id) and a call entry
  // (selector/args/row_count/truncated) -- distinguished by which key is
  // present, never by position.
  let mentionTrace = $derived((loreState.result?.trace || []).filter((t) => 'surface_form' in t));
  let callTrace = $derived((loreState.result?.trace || []).filter((t) => 'selector' in t));

  // Display names are sourced client-side from the payload (item 4): a
  // mention's entity_id is looked up against the `identity` rows already in
  // `rows`, never a second request. Falls back to the surface form when
  // there is no entity_id (the unmatched/ambiguous case).
  let identityNameById = $derived(
    Object.fromEntries(
      (loreState.result?.rows || [])
        .filter((r) => r.section === 'identity')
        .map((r) => [r.entity_id, r.name])
    )
  );

  function mentionLabel(entry) {
    if (entry.entity_id && identityNameById[entry.entity_id]) return identityNameById[entry.entity_id];
    return entry.surface_form;
  }

  // Rows grouped by their "section" key (every row carries one) -- no
  // selector is special-cased (item 4).
  let rowsBySection = $derived.by(() => {
    const grouped = {};
    for (const row of loreState.result?.rows || []) {
      (grouped[row.section] ||= []).push(row);
    }
    return grouped;
  });

  function rowFields(row) {
    return Object.entries(row).filter(([key]) => key !== 'section');
  }

  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });
</script>

<div class="app-view" id="lore-view" style:display={active ? '' : 'none'}>
  <div class="lore-tabs">
    <button class:active={loreTab === 'question'} onclick={() => (loreTab = 'question')}>Question</button>
    <button class:active={loreTab === 'names'} onclick={() => (loreTab = 'names')}>Noms à lier</button>
  </div>
  {#if loreTab === 'names'}
    <NamesPanel visible={active} />
  {/if}
  <div class="queue-panel" id="lore-ask-panel" style:display={loreTab === 'question' ? '' : 'none'}>
    <div class="panel-head">
      <h2>Lore — poser une question</h2>
    </div>
    <div class="queue-body">
      <textarea
        bind:value={loreState.question}
        rows="4"
        placeholder="Ex : est-ce que Mara connaît Corvin ?"
        disabled={loreState.asking}
      ></textarea>
      {#if loreState.askError}
        <div class="r-err">{loreState.askError}</div>
      {/if}
      <div>
        <button disabled={loreState.asking || !loreState.question.trim()} onclick={() => askLore()}>
          {loreState.asking ? '⟳ Interrogation…' : 'Poser la question'}
        </button>
      </div>

      {#if loreState.result}
        {@const result = loreState.result}
        <div class="lore-answer">
          <p class="answer-prose">{result.answer}</p>
          {#if RENDERER_LABEL[result.renderer]}
            <p class="muted renderer-label">{RENDERER_LABEL[result.renderer]}</p>
          {/if}
        </div>

        {#if result.verdict === 'ambiguous_mention'}
          <div class="lore-candidates">
            {#each Object.entries(result.candidates) as [ref, options] (ref)}
              <div class="candidate-group">
                {#each options as option (option.id)}
                  <label class="candidate-option">
                    <input
                      type="radio"
                      name={'lore-candidate-' + ref}
                      checked={loreState.selections[ref] === option.id}
                      onchange={() => selectCandidate(ref, option.id)}
                    />
                    {option.name} ({option.type}) — {option.description || '(sans description)'}
                    {#if option.location_name}
                      — {option.location_name}
                    {/if}
                  </label>
                {/each}
              </div>
            {/each}
            <div>
              <button disabled={loreState.asking || !allAmbiguitiesResolved()} onclick={() => confirmResolution()}>
                Confirmer
              </button>
            </div>
          </div>
        {/if}

        <details class="lore-trace">
          <summary>Trace</summary>
          {#if mentionTrace.length > 0}
            <h4>Mentions résolues</h4>
            <ul>
              {#each mentionTrace as entry}
                <li>« {mentionLabel(entry)} » — {entry.verdict}{entry.rung ? ` (${entry.rung})` : ''}</li>
              {/each}
            </ul>
          {/if}
          {#if callTrace.length > 0}
            <h4>Appels</h4>
            <ul>
              {#each callTrace as entry}
                <li>
                  {entry.selector}({entry.args.join(', ')}) — {entry.row_count} ligne(s){entry.truncated ? ' (tronqué)' : ''}
                </li>
              {/each}
            </ul>
          {/if}
          {#each Object.entries(rowsBySection) as [section, rows] (section)}
            <h4>{SECTION_LABEL[section] || section}</h4>
            <ul>
              {#each rows as row, i (i)}
                <li>{rowFields(row).map(([k, v]) => `${k}: ${v}`).join(', ')}</li>
              {/each}
            </ul>
          {/each}
        </details>
      {/if}
    </div>
  </div>
</div><!-- #lore-view -->

<style>
  .r-err { color: var(--red); }
  .lore-tabs { display: flex; gap: 6px; margin-bottom: 8px; }
  .lore-tabs button.active { font-weight: 600; }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .answer-prose { white-space: pre-wrap; }
  .muted { color: var(--muted); font-size: 12px; }
  .renderer-label { margin-top: 4px; }
  .lore-candidates { display: flex; flex-direction: column; gap: 10px; }
  .candidate-group { display: flex; flex-direction: column; gap: 4px; border-top: 1px solid var(--border); padding-top: 8px; }
  .candidate-option { display: flex; align-items: center; gap: 6px; }
  .lore-trace { border-top: 1px solid var(--border); padding-top: 8px; }
  .lore-trace h4 { margin: 10px 0 4px; font-size: 12px; color: var(--muted); }
  .lore-trace ul { margin: 0; padding-left: 18px; }
</style>
