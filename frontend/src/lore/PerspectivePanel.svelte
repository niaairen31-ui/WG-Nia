<script>
  /* TICKET-0125 (BRIEF-0125-F, H1-a, H1-b), TICKET-0127 (I1). Lore >
     Perspective: the creator asks a question "as the public" or as any one
     character (« Un personnage », his own secrets shown at her door) and sees
     what that view yields (« Ce que voit le joueur » / « Ce que sait X »)
     beside what was withheld and why (« Retenu »). Read-only: the route
     writes its journal row, nothing else. */
  import {
    perspectiveState, askPerspective, selectPerspectiveCandidate, allPerspectiveChoicesMade,
    confirmPerspective, resetPerspectiveForWorld, loadPerspectiveCharacters,
  } from './perspective.svelte.js';

  let { visible = false } = $props();

  const REASON_LABEL = Object.freeze({
    creator_only: 'réservé à la créatrice',
    not_public: 'pas public',
    entity_not_public: 'entité non publique',
    secret_membership: 'appartenance secrète',
    faction_not_public: 'faction non publique',
    skill_not_visible: 'compétence invisible à la création',
    not_known: 'inconnu de ce personnage',
    entity_unknown: 'entité inconnue de ce personnage',
    membership_unknown: 'appartenance inconnue de ce personnage',
    skill_unknown: 'compétence inconnue de ce personnage',
    false_belief: 'croyance fausse — la vérité',
    stale_version: 'version périmée — le texte actuel',
    concealed: 'su mais caché (porte joueur)',
  });

  let asCharacter = $derived(perspectiveState.perspective === 'character');
  let playerCharacters = $derived(perspectiveState.characters.filter((c) => c.character_type === 'player'));
  let npcCharacters = $derived(perspectiveState.characters.filter((c) => c.character_type !== 'player'));
  let characterName = $derived(
    perspectiveState.characters.find((c) => c.id === perspectiveState.characterId)?.name || '',
  );

  // An event handler, never the reset effect (INV-55).
  function onPerspectiveChange() {
    if (perspectiveState.perspective === 'character' && perspectiveState.characters.length === 0) {
      loadPerspectiveCharacters();
    }
  }

  let rowsBySection = $derived.by(() => {
    const grouped = {};
    for (const row of perspectiveState.result?.rows || []) {
      (grouped[row.section] ||= []).push(row);
    }
    return grouped;
  });

  function rowFields(row) {
    return Object.entries(row).filter(([key]) => key !== 'section');
  }

  // Reads the world only; writes the perspective state (INV-55).
  $effect(() => {
    resetPerspectiveForWorld();
  });
</script>

<div class="queue-panel" id="lore-perspective-panel" style:display={visible ? '' : 'none'}>
  <div class="panel-head">
    <h2>Lore — perspective</h2>
  </div>
  <div class="queue-body">
    <label class="perspective-select">
      Perspective
      <select
        bind:value={perspectiveState.perspective}
        disabled={perspectiveState.asking}
        onchange={onPerspectiveChange}
      >
        <option value="public">Public — ce que tout le monde sait</option>
        <option value="character">Un personnage — ce qu'il sait</option>
      </select>
    </label>
    {#if asCharacter}
      <label class="perspective-select">
        Personnage
        <select bind:value={perspectiveState.characterId} disabled={perspectiveState.asking}>
          <option value="">— choisir —</option>
          <optgroup label="Personnages joueurs">
            {#each playerCharacters as c (c.id)}
              <option value={c.id}>{c.name}</option>
            {/each}
          </optgroup>
          <optgroup label="PNJ">
            {#each npcCharacters as c (c.id)}
              <option value={c.id}>{c.name}</option>
            {/each}
          </optgroup>
        </select>
      </label>
    {/if}
    <textarea
      bind:value={perspectiveState.question}
      rows="4"
      placeholder="Ex : qui est Mara ?"
      disabled={perspectiveState.asking}
    ></textarea>
    {#if perspectiveState.error}
      <div class="r-err">{perspectiveState.error}</div>
    {/if}
    <div>
      <button
        disabled={perspectiveState.asking || !perspectiveState.question.trim()
          || (asCharacter && !perspectiveState.characterId)}
        onclick={() => askPerspective()}
      >
        {perspectiveState.asking ? '⟳ Interrogation…' : 'Interroger'}
      </button>
    </div>

    {#if perspectiveState.result}
      {@const result = perspectiveState.result}
      <section class="perspective-seen">
        <h3>{asCharacter ? `Ce que sait ${characterName}` : 'Ce que voit le joueur'}</h3>
        <p class="answer-prose">{result.answer}</p>
        {#if result.verdict === 'ambiguous_mention'}
          <div class="perspective-candidates">
            {#each Object.entries(result.candidates) as [ref, options] (ref)}
              <div class="candidate-group">
                {#each options as option (option.entity_id)}
                  <label class="candidate-option">
                    <input
                      type="radio"
                      name={'perspective-candidate-' + ref}
                      checked={perspectiveState.selections[ref] === option.entity_id}
                      onchange={() => selectPerspectiveCandidate(ref, option.entity_id)}
                    />
                    {option.name} ({option.type})
                  </label>
                {/each}
              </div>
            {/each}
            <div>
              <button
                disabled={perspectiveState.asking || !allPerspectiveChoicesMade()}
                onclick={() => confirmPerspective()}
              >
                Confirmer
              </button>
            </div>
          </div>
        {/if}
      </section>

      <section class="perspective-withheld">
        <h3>Retenu</h3>
        {#if (result.withheld || []).length === 0}
          <p class="muted">Rien n'a été retenu.</p>
        {:else}
          <ul>
            {#each result.withheld as line, i (i)}
              <li>{line.subject} — {line.content} <span class="muted">({REASON_LABEL[line.reason] || line.reason})</span></li>
            {/each}
          </ul>
        {/if}
      </section>

      <details class="perspective-rows">
        <summary>Lignes rendues</summary>
        {#each Object.entries(rowsBySection) as [section, rows] (section)}
          <h4>{section}</h4>
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

<style>
  .r-err { color: var(--red); }
  textarea { width: 100%; box-sizing: border-box; font: inherit; }
  .perspective-select { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
  .answer-prose { white-space: pre-wrap; }
  .muted { color: var(--muted); font-size: 12px; }
  .perspective-seen h3, .perspective-withheld h3 { margin: 10px 0 4px; font-size: 13px; }
  .perspective-candidates { display: flex; flex-direction: column; gap: 10px; }
  .candidate-group { display: flex; flex-direction: column; gap: 4px; border-top: 1px solid var(--border); padding-top: 8px; }
  .candidate-option { display: flex; align-items: center; gap: 6px; }
  .perspective-withheld ul, .perspective-rows ul { margin: 0; padding-left: 18px; }
  .perspective-rows { border-top: 1px solid var(--border); padding-top: 8px; margin-top: 8px; }
  .perspective-rows h4 { margin: 10px 0 4px; font-size: 12px; color: var(--muted); }
</style>
