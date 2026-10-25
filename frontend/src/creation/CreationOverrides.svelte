<script>
  /* TICKET-0126 (BRIEF-0126-E). The creation overrides of a skill or a
     system fiche, rendered by CompetencesSheet.svelte right after its rank
     thresholds. Blank inherits (the skill, then its system, then the
     world's rules), the inherited value shown in the blank option. A system
     also caps how many of its skills a new character raises above the
     first rank and how many it holds. Every field binds straight to
     creationState.sheetDetail; nothing is written until the shell's Save.
     No scoped <style> block: classes come from frontend/public/creation.css. */
  import { creationState } from './state.svelte.js';
  import { inheritedVisible, inheritedMaxRank } from './creationRules.svelte.js';

  let { record, systems, ranks, rules } = $props();

  function label(n) {
    return ranks?.[n]?.label ?? `rang ${n}`;
  }

  const visibleInherited = $derived(inheritedVisible(record, systems, rules));
  const maxRankInherited = $derived(inheritedMaxRank(record, systems, rules));
  const effectiveVisible = $derived(
    record.visible_at_creation == null ? visibleInherited : !!record.visible_at_creation,
  );
  const heldCapSet = $derived(
    record.kind === 'system' && record.cap_held_at_creation != null && record.cap_held_at_creation !== '',
  );

  function blankOr(value) {
    return value === '' ? null : value;
  }
</script>

<div class="field-section">
  <div class="field-grid">
    <div class="field-row">
      <label for="creation-o-visible">Visible à la création</label>
      <select id="creation-o-visible"
        value={record.visible_at_creation == null ? '' : String(!!record.visible_at_creation)}
        onchange={(e) => { creationState.sheetDetail.visible_at_creation = e.currentTarget.value === '' ? null : e.currentTarget.value === 'true'; }}>
        <option value="">hérité ({visibleInherited === null ? '…' : visibleInherited ? 'oui' : 'non'})</option>
        <option value="true">Oui</option>
        <option value="false">Non</option>
      </select>
    </div>
    <div class="field-row">
      <label for="creation-o-max-rank">Rang maximal à la création</label>
      <select id="creation-o-max-rank"
        value={record.max_rank_at_creation == null ? '' : String(record.max_rank_at_creation)}
        onchange={(e) => { creationState.sheetDetail.max_rank_at_creation = e.currentTarget.value === '' ? null : Number(e.currentTarget.value); }}>
        <option value="">hérité ({maxRankInherited === null ? '…' : label(maxRankInherited)})</option>
        {#each [1, 2, 3, 4, 5] as n (n)}<option value={String(n)}>{label(n)}</option>{/each}
      </select>
    </div>
    {#if record.kind === 'system'}
      <div class="field-row">
        <label for="creation-o-cap-raised">Au plus N compétences montées au-dessus de {label(1)}</label>
        <input id="creation-o-cap-raised" type="number" min="0" step="1" value={record.cap_raised_at_creation ?? ''}
          oninput={(e) => { creationState.sheetDetail.cap_raised_at_creation = blankOr(e.currentTarget.value); }}>
      </div>
      <div class="field-row">
        <label for="creation-o-cap-held">Au plus N compétences détenues</label>
        <input id="creation-o-cap-held" type="number" min="0" step="1" value={record.cap_held_at_creation ?? ''}
          oninput={(e) => { creationState.sheetDetail.cap_held_at_creation = blankOr(e.currentTarget.value); }}>
      </div>
    {/if}
  </div>
  {#if effectiveVisible}
    <div style="font-size:12px; color:var(--muted); margin-top:4px">
      Visible à la création : le joueur lira son nom et sa description tels qu'ils sont écrits.
    </div>
  {/if}
  {#if heldCapSet}
    <div style="font-size:12px; color:var(--muted); margin-top:4px">
      Les compétences ouvertes de ce système sont détenues d'office : un plafond plus bas oblige le joueur à en descendre, et chaque descente lui rend un point.
    </div>
  {/if}
</div>
