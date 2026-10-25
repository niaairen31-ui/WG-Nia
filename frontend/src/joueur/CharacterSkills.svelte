<script>
  /* TICKET-0126 (BRIEF-0126-H). The skills of the creation screen: one row
     per catalogue skill, its rank among the world's labels, a
     justification, and the designer's proposal to accept. Every rank
     change is judged by the server (`verifier`, INV-67). */
  import {
    characterState, verifySkills, suggestion, acceptSuggestion, acceptAllSuggestions,
  } from './character.svelte.js';

  let { locked = false } = $props();

  function rankLabel(skill, rank) {
    if (skill.requires_master && rank === 0) return 'Non apprise';
    return characterState.catalogue.ranks[rank] ?? String(rank);
  }

  function ranksOf(skill) {
    return Array.from({ length: skill.max_rank + 1 }, (_, r) => r);
  }
</script>

{#if characterState.catalogue && characterState.form}
  {@const form = characterState.form}
  <section class="skills">
    <h3>Compétences</h3>
    <div class="skills-head">
      {#if characterState.verdict}
        <span>Points restants : {characterState.verdict.remaining} / {characterState.verdict.pool}</span>
      {/if}
      <button disabled={locked} onclick={() => acceptAllSuggestions()}>Tout accepter</button>
    </div>
    {#each characterState.catalogue.skills as skill (skill.skill_key)}
      {@const proposed = suggestion(skill.skill_key)}
      <div class="skill-row">
        <div class="skill-name">
          <strong>{skill.name}</strong>
          <span class="skill-system">{skill.system || 'sans système'}</span>
          {#if skill.description}<span class="skill-desc">{skill.description}</span>{/if}
        </div>
        <select bind:value={form.ranks[skill.skill_key]} disabled={locked} onchange={() => verifySkills()}>
          {#each ranksOf(skill) as rank (rank)}
            <option value={rank}>{rankLabel(skill, rank)}</option>
          {/each}
        </select>
        <input
          placeholder="Comment l'as-tu appris ?"
          bind:value={form.justifications[skill.skill_key]}
          disabled={locked}
        />
        {#if proposed}
          <div class="proposal">
            Proposé : {rankLabel(skill, proposed.designer_rank)}{proposed.designer_reason
              ? ` — ${proposed.designer_reason}` : ''}
            <button disabled={locked} onclick={() => acceptSuggestion(skill.skill_key)}>Accepter</button>
          </div>
        {/if}
      </div>
    {/each}
  </section>
{/if}

<style>
  .skills-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px; margin-bottom: 6px; }
  .skill-row { display: grid; grid-template-columns: 1fr auto; gap: 4px 8px; padding: 6px 0;
    border-bottom: 1px solid var(--border); }
  .skill-name { display: flex; flex-wrap: wrap; gap: 6px; align-items: baseline; }
  .skill-system, .skill-desc { font-size: 0.85em; opacity: 0.8; }
  .skill-row input, .proposal { grid-column: 1 / -1; }
  input, select { font: inherit; box-sizing: border-box; }
  input { width: 100%; }
  .proposal { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-style: italic; }
</style>
