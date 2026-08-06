<script>
  /* TICKET-0059 (BRIEF-0059-j commit 1). Faithful port of renderAgendaSheet/
     _intriguesRenderStep/_intriguesRenderLinkedGoal (index.html, now
     deleted) -- intrigues' bespoke, non-entity sheet (`agenda` carries no
     ENTITY_TYPE_REGISTRY row, so it never used Sheet.svelte's own
     registry.types[type] shape). Mutation logic (status/step/link) lives
     in intrigues.svelte.js; this component owns markup only, mirroring
     Evenements.svelte's own split off eventDraft.svelte.js.

     Rendered by Sheet.svelte inside its own 'view' mode when
     creationState.activeTabKey === 'intrigues', gated on tabKey exactly
     like evenements -- not a registry.types[type] lookup. No save/delete:
     the API surface is frozen to status transitions and link detach,
     unchanged from the legacy renderer's own doc comment.

     detachLink shares its endpoint with the entity sheet's own goals
     editor (GoalsEditor.svelte's detachGoalLink) -- both surfaces
     legitimately act on the same /api/goal-agenda-links/{id}/detach
     route; see this brief's own note for why they stay unmerged.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { setAgendaStatus, detachLink, setStepStatus } from './intrigues.svelte.js';

  let { agenda } = $props();
</script>

<div class="field-section">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
    <div><strong>{agenda.title}</strong>
      <span class="badge b-other" title={agenda.owner_type === 'character' ? 'Intrigue personnelle' : 'Intrigue de faction'}>
        {agenda.owner_type === 'character' ? 'personnelle' : 'faction'}
      </span>
      <span style="color:var(--muted); font-size:12px;">({agenda.owner_name})</span>
    </div>
    <div style="display:flex; gap:6px; align-items:center;">
      <span class="badge b-{agenda.status}">{agenda.status}</span>
      {#if agenda.status === 'active'}
        <button class="btn-icon" title="Abandonner l'intrigue"
          onclick={() => setAgendaStatus(agenda.id, 'abandoned', (agenda.linked_goals || []).length)}>⏸</button>
      {/if}
      {#if agenda.status === 'abandoned' || agenda.status === 'failed'}
        <button class="btn-icon" title="Réactiver l'intrigue" onclick={() => setAgendaStatus(agenda.id, 'active', 0)}>▶</button>
      {/if}
    </div>
  </div>
</div>

<div class="field-section">
  <div class="field-section-title">Étapes</div>
  {#each agenda.steps as s (s.id)}
    <div class="row-card" style="flex-direction:row; align-items:flex-start; justify-content:space-between; gap:6px; margin:4px 0;">
      <div style="flex:1; min-width:160px;">
        <span style="font-size:12px; color:var(--muted);">#{s.step_order}</span>
        <span>{s.objective}</span>
        {#if s.visibility_trace}<div style="font-size:11px; color:var(--muted);">trace : {s.visibility_trace}</div>{/if}
        {#if s.outcome}<div style="font-size:11px; color:var(--muted);">résultat : {s.outcome}</div>{/if}
      </div>
      <span class="badge b-{s.status}">{s.status}</span>
      <div>
        {#if s.status === 'active'}
          <button class="btn-icon" title="Terminer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'completed')}>✓</button>
          <button class="btn-icon" title="Échouer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'failed')}>✗</button>
        {:else if s.status === 'pending'}
          <button class="btn-icon" title="Activer l'étape" onclick={() => setStepStatus(agenda.id, s.id, 'active')}>▶</button>
        {/if}
      </div>
    </div>
  {/each}
</div>

{#if (agenda.linked_goals || []).length > 0}
  <div class="field-section">
    <div class="field-section-title">Objectifs liés ({agenda.linked_goals.length})</div>
    {#each agenda.linked_goals as l (l.link_id)}
      <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; gap:6px; margin:4px 0;">
        <span style="flex:1; min-width:160px;">
          {l.goal_description}
          <span style="font-size:11px; color:var(--muted);"> — {l.npc_name}</span>
          <span class="badge {l.goal_status !== 'active' ? 'b-rejected' : 'b-equipped'}">{l.goal_status}</span>
        </span>
        <button class="btn-icon" title="Détacher (réversible — le lien peut être rattaché plus tard)"
          onclick={() => detachLink(agenda.id, l.link_id)}>✕</button>
      </div>
    {/each}
  </div>
{/if}
