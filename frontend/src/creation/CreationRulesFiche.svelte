<script>
  /* TICKET-0126 (BRIEF-0126-E). The 'creation' record's fiche, rendered by
     CompetencesSheet.svelte: the world's character-creation rules. Every
     input binds straight to creationState.sheetDetail (a fresh record built
     by creationRulesRecord); nothing is written until the shell's Save,
     which saveCompetenceRecord routes to saveCreationRules.

     `ranks` is the world's ladder (competencesState.ranks), passed in as a
     prop so this file imports nothing from competences.svelte.js. No scoped
     <style> block: classes come from frontend/public/creation.css. */
  import { creationState } from './state.svelte.js';

  let { ranks } = $props();

  const rec = $derived(creationState.sheetDetail);

  function label(n) {
    return ranks?.[n]?.label ?? `rang ${n}`;
  }
</script>

<div class="field-section">
  <div class="field-grid">
    <div class="field-row">
      <label for="creation-f-pool">Réserve de points</label>
      <input id="creation-f-pool" type="number" min="0" step="1" bind:value={creationState.sheetDetail.pool}>
    </div>
    <div class="field-row">
      <label for="creation-f-max-rank">Rang maximal à la création</label>
      <select id="creation-f-max-rank" bind:value={creationState.sheetDetail.max_rank}>
        {#each [1, 2, 3, 4, 5] as n (n)}<option value={n}>{label(n)}</option>{/each}
      </select>
    </div>
    <div class="field-row">
      <label for="creation-f-masters">Compétences qui exigent un maître (au plus)</label>
      <input id="creation-f-masters" type="number" min="0" step="1"
        bind:value={creationState.sheetDetail.max_master_skills}>
    </div>
    <div class="field-row checkbox">
      <input id="creation-f-visible" type="checkbox" bind:checked={creationState.sheetDetail.skills_visible}>
      <label for="creation-f-visible">Compétences visibles à la création par défaut</label>
    </div>
  </div>
</div>

<div class="field-section">
  <div class="field-grid">
    {#each rec.costs as cost, i (cost.rank)}
      <div class="field-row">
        <label for="creation-f-cost-{cost.rank}">Coût pour atteindre {label(cost.rank)}</label>
        <input id="creation-f-cost-{cost.rank}" type="number" min="0" step="1"
          bind:value={creationState.sheetDetail.costs[i].cost}>
      </div>
    {/each}
  </div>
  <div style="font-size:12px; color:var(--muted); margin-top:4px">
    Descendre une compétence détenue à {label(0)} rend le coût de {label(1)}.
  </div>
</div>

<div class="field-section">
  <div class="field-grid">
    {#each rec.caps as cap, i (cap.rank)}
      <div class="field-row">
        <label for="creation-f-cap-{cap.rank}">Plafond au rang {label(cap.rank)}</label>
        <input id="creation-f-cap-{cap.rank}" type="number" min="0" step="1" placeholder="aucun"
          bind:value={creationState.sheetDetail.caps[i].cap}>
      </div>
    {/each}
  </div>
</div>
