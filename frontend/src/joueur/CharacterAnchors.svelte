<script>
  /* TICKET-0126 (BRIEF-0126-H). What anchors the character in the world:
     the people of the story (at most eight), the starting place, the
     factions and what the character knows -- each list as the creation
     catalogue offers it (INV-66). */
  import { characterState } from './character.svelte.js';

  let { locked = false } = $props();

  const MAX_PEOPLE = 8;
  const KINDS = [['family', 'Famille'], ['master', 'Maître'], ['faction', 'Faction'], ['other', 'Autre']];
  const LEVELS = [['rumor', 'Rumeur'], ['suspicious', 'Soupçon'], ['partial', 'Partielle'], ['knows', 'Sait']];

  const masterSkills = $derived((characterState.catalogue?.skills || []).filter((s) => s.requires_master));

  function addPerson() {
    characterState.form.sketches.push({
      id: null, name: '', role: '', sentence: '', group_label: '', kind: 'family', skill_key: null,
      existing_entity: null,
    });
  }

  function addMembership() {
    characterState.form.memberships.push({ faction_id: '', role: '' });
  }

  function addKnowledge() {
    characterState.form.knowledge.push({ id: null, level: 'rumor', content: '' });
  }
</script>

{#if characterState.catalogue && characterState.form}
  {@const form = characterState.form}
  <section class="anchors">
    <h3>Personnes de ton histoire</h3>
    {#each form.sketches as person, i (i)}
      <div class="person">
        <input placeholder="Nom" bind:value={person.name} disabled={locked} />
        <input placeholder="Ce qu'elle est pour toi" bind:value={person.role} disabled={locked} />
        <input placeholder="La phrase de ton histoire" bind:value={person.sentence} disabled={locked} />
        <input placeholder="Groupe" bind:value={person.group_label} disabled={locked} />
        <select bind:value={person.kind} disabled={locked}>
          {#each KINDS as [value, label] (value)}
            <option {value}>{label}</option>
          {/each}
        </select>
        {#if person.kind === 'master'}
          <select bind:value={person.skill_key} disabled={locked}>
            <option value={null}>— compétence enseignée —</option>
            {#each masterSkills as skill (skill.skill_key)}
              <option value={skill.skill_key}>{skill.name}</option>
            {/each}
          </select>
        {/if}
        {#if person.existing_entity}
          <span class="existing">
            Personne connue : {person.existing_entity.name || '?'}
            <button disabled={locked} onclick={() => (person.existing_entity = null)}>Délier</button>
          </span>
        {/if}
        <button disabled={locked} onclick={() => form.sketches.splice(i, 1)}>Retirer</button>
      </div>
    {/each}
    <button disabled={locked || form.sketches.length >= MAX_PEOPLE} onclick={addPerson}>Ajouter une personne</button>
    {#if form.sketches.length >= MAX_PEOPLE}
      <span class="hint">8 personnes au plus.</span>
    {/if}

    <label class="field">
      Lieu de départ
      <select bind:value={form.start_location_id} disabled={locked}>
        <option value="">— choisir —</option>
        {#each characterState.catalogue.places as place (place.entity_id)}
          <option value={place.entity_id}>{place.name}</option>
        {/each}
      </select>
    </label>

    <h3>Appartenances</h3>
    {#each form.memberships as membership, i (i)}
      <div class="line">
        <select bind:value={membership.faction_id} disabled={locked}>
          <option value="">— faction —</option>
          {#each characterState.catalogue.factions as faction (faction.entity_id)}
            <option value={faction.entity_id}>{faction.name}</option>
          {/each}
        </select>
        <input placeholder="Rôle" bind:value={membership.role} disabled={locked} />
        <button disabled={locked} onclick={() => form.memberships.splice(i, 1)}>Retirer</button>
      </div>
    {/each}
    <button disabled={locked} onclick={addMembership}>Ajouter une appartenance</button>

    <h3>Ce que tu sais</h3>
    {#each form.knowledge as line, i (i)}
      <div class="line">
        <select bind:value={line.level} disabled={locked}>
          {#each LEVELS as [value, label] (value)}
            <option {value}>{label}</option>
          {/each}
        </select>
        <input placeholder="Ce que tu sais" bind:value={line.content} disabled={locked} />
        <button disabled={locked} onclick={() => form.knowledge.splice(i, 1)}>Retirer</button>
      </div>
    {/each}
    <button disabled={locked} onclick={addKnowledge}>Ajouter une connaissance</button>
  </section>
{/if}

<style>
  .person, .line { display: flex; flex-wrap: wrap; gap: 4px; padding: 6px 0; border-bottom: 1px solid var(--border); }
  .person input { flex: 1 1 160px; }
  .line input { flex: 1 1 200px; }
  input, select { font: inherit; box-sizing: border-box; max-width: 100%; }
  .field { display: flex; flex-direction: column; gap: 4px; margin: 10px 0; }
  .existing { display: flex; gap: 6px; align-items: center; font-style: italic; }
  .hint { margin-left: 6px; font-size: 0.9em; }
</style>
