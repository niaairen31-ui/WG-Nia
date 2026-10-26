<script>
  /* TICKET-0126 (BRIEF-0126-H). The character creation frame: name and
     story, the skills, the people and anchors, then the designer and the
     submission. Everything shown comes from /api/joueur/creation/ (INV-66);
     a submitted draft is read-only (C1). A returned draft is the
     player's again, with the creator's note; once accepted, the screen
     names his character (TICKET-0129, BRIEF-0129-G). */
  import CharacterSkills from './CharacterSkills.svelte';
  import CharacterAnchors from './CharacterAnchors.svelte';
  import {
    characterState, saveDraft, askDesigner, submitDraft, closeCreation,
  } from './character.svelte.js';

  const locked = $derived(characterState.draft && characterState.draft.status === 'submitted');
</script>

<section class="creation">
  <div class="creation-head">
    <h2>Créer mon personnage</h2>
    <button onclick={() => closeCreation()}>Fermer</button>
  </div>

  {#if characterState.error}
    <div class="r-err">{characterState.error}</div>
  {/if}

  {#if characterState.characterName}
    <p>Ton personnage {characterState.characterName} a été accepté dans ce monde.</p>
  {:else if characterState.form}
    {@const form = characterState.form}
    {#if locked}
      <p class="locked">Soumis à la créatrice — en attente de sa revue.</p>
    {/if}
    {#if characterState.draft.status === 'returned'}
      <div class="returned">
        <p>Renvoyé par la créatrice.</p>
        <p class="note">{characterState.draft.creator_note}</p>
      </div>
    {/if}
    <label class="field">
      Nom
      <input bind:value={form.name} disabled={locked || characterState.busy} />
    </label>
    <label class="field">
      Ton histoire
      <textarea bind:value={form.story} rows="6" disabled={locked || characterState.busy}></textarea>
    </label>

    <CharacterSkills {locked} />
    <CharacterAnchors {locked} />

    <div class="actions">
      <button disabled={locked || characterState.busy} onclick={() => saveDraft()}>Enregistrer</button>
      <button disabled={locked || characterState.busy} onclick={() => askDesigner()}>
        {characterState.busy ? '⟳ …' : 'Demander au concepteur'}
      </button>
      <button disabled={locked || characterState.busy} onclick={() => submitDraft()}>
        Soumettre mon personnage
      </button>
    </div>

    {#if characterState.designer}
      {@const designer = characterState.designer}
      {#if designer.notes.length > 0}
        <ul class="designer-notes">
          {#each designer.notes as note, i (i)}
            <li>{note}</li>
          {/each}
        </ul>
      {/if}
      {#if designer.violations.length > 0}
        <ul class="r-err">
          {#each designer.violations as v, i (i)}
            <li>Concepteur : {v.message}</li>
          {/each}
        </ul>
      {/if}
    {/if}

    {#if characterState.verdict && characterState.verdict.violations.length > 0}
      <ul class="violations">
        {#each characterState.verdict.violations as v, i (i)}
          <li>{v.message}</li>
        {/each}
      </ul>
    {/if}
  {:else if characterState.busy}
    <p>⟳ Chargement…</p>
  {/if}
</section>

<style>
  .creation { border-top: 1px solid var(--border); margin-top: 12px; padding-top: 8px; }
  .creation-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .field { display: flex; flex-direction: column; gap: 4px; margin: 6px 0; }
  input, textarea { font: inherit; box-sizing: border-box; width: 100%; }
  .actions { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
  .locked { font-style: italic; }
  .returned { border-left: 3px solid var(--border); padding-left: 8px; }
  .note { white-space: pre-wrap; }
  .violations, .r-err { color: var(--red); }
  ul { padding-left: 18px; }
</style>
