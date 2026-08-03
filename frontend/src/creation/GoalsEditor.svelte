<script>
  /* TICKET-0059 (BRIEF-0059-d). Faithful port of the NPC goals in-context
     editor -- authorLoadGoals/authorRenderGoals/authorRenderGoalPrerequisites/
     authorRenderGoalForm (index.html, now deleted) plus their mutation
     family, ported to goalsPanel.svelte.js (state + non-render logic; this
     component owns markup only). No edit/reopen: description is immutable
     after insert, a closed goal is never reopened (a revived goal is a new
     row) -- unchanged from legacy.

     Prerequisites (schema v1.74, TICKET-0024): npc_goal.prerequisites --
     v1 relation_gte only. goalsPanelState.goals supplies the current list
     so a single add/remove never needs a round-trip first, replacing
     authorGoalsCache.

     The agenda link/detach path (attachGoalLink/detachGoalLink) shares its
     endpoints with the Intrigues surface (still legacy, brief -j) --
     untouched here, both callers keep working against the same routes.

     creation:goals-backfilled (EntityList.svelte's backfillNpcGoals) is the
     reverse-bridge coupling RECON-0059-a/SUPPLEMENT Amendment 8 flagged:
     legacy listening to an already-migrated Svelte event. Both ends are
     Svelte now; this component subscribes directly and reloads, cleaning
     the listener up on unmount/entity change -- unlike the legacy top-level
     listener (installed once for the page's lifetime), this component
     mounts and unmounts per NPC selected. */
  import { creationState } from './state.svelte.js';
  import {
    goalsPanelState, loadGoals, goalPrereqRawList, setGoalPrerequisites,
    addGoalPrerequisite, removeGoalPrerequisite, attachGoalLink, detachGoalLink,
    addGoal, setGoalStatus,
  } from './goalsPanel.svelte.js';

  let { entityId, legacyDoc } = $props();

  const HORIZON_LABEL = { long: 'LONG TERME', short: 'COURT TERME' };

  $effect(() => {
    loadGoals(entityId);
    const handler = () => loadGoals(entityId);
    legacyDoc.addEventListener('creation:goals-backfilled', handler);
    return () => legacyDoc.removeEventListener('creation:goals-backfilled', handler);
  });

  const prereqCandidates = $derived((creationState.entities || []).filter((e) => e.type === 'character' || e.type === 'faction'));

  let attachSelection = $state({});
  let prereqTarget = $state({});
  let prereqThreshold = $state({});

  function onAddPrerequisite(goalId) {
    const targetId = prereqTarget[goalId];
    const threshold = Number(prereqThreshold[goalId]);
    if (!targetId || !threshold) return;
    addGoalPrerequisite(legacyDoc, entityId, goalId, targetId, threshold);
  }

  function onAttach(goalId) {
    const agendaId = attachSelection[goalId];
    attachGoalLink(entityId, goalId, agendaId);
  }

  let newHorizon = $state('short');
  let newDescription = $state('');

  async function onAddGoal() {
    await addGoal(legacyDoc, entityId, newHorizon, newDescription);
    newHorizon = 'short';
    newDescription = '';
  }
</script>

{#if goalsPanelState.loadError}
  <div class="empty">{goalsPanelState.loadError}</div>
{:else if goalsPanelState.goals.length === 0}
  <div class="empty">Aucun objectif.</div>
{:else}
  <div class="row-table">
    {#each goalsPanelState.goals as g (g.id)}
      {@const closed = g.status !== 'active'}
      {@const prereqs = g.prerequisites || []}
      <div class="row-card" style={closed ? 'opacity:0.6;' : ''}>
        <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;">
          <span>
            <span class="badge b-other">{HORIZON_LABEL[g.horizon] || g.horizon}</span>
            {g.description}
            {#each (g.links || []) as l}
              <span class="badge b-other" style="margin-left:4px;">
                sert : « {l.agenda_title} »
                <button class="btn-icon" style="padding:0 4px" title="Détacher (réversible)" onclick={() => detachGoalLink(entityId, l.link_id)}>✕</button>
              </span>
            {/each}
          </span>
          <span style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span class="badge {closed ? 'b-rejected' : 'b-equipped'}">{g.status}</span>
            {#if !closed}
              <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={() => setGoalStatus(legacyDoc, entityId, g.id, 'completed')}>Accompli</button>
              <button class="btn-end" style="font-size:12px; padding:3px 8px" onclick={() => setGoalStatus(legacyDoc, entityId, g.id, 'abandoned')}>Abandonné</button>
            {/if}
            {#if !closed && goalsPanelState.activeAgendas.length > 0}
              <span style="display:inline-flex; gap:4px; align-items:center; margin-left:6px;">
                <select bind:value={attachSelection[g.id]} style="font-size:11px;">
                  <option value="">rattacher à…</option>
                  {#each goalsPanelState.activeAgendas as a (a.id)}
                    <option value={a.id}>{a.title}</option>
                  {/each}
                </select>
                <button class="btn-icon" title="Rattacher à l'intrigue choisie" onclick={() => onAttach(g.id)}>+</button>
              </span>
            {/if}
          </span>
        </div>
        {#if prereqs.length || !closed}
          <div style="margin-top:4px; font-size:11px;">
            {#each prereqs as p, i}
              <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px 4px 0 0;">
                relation ≥ {p.threshold} avec {p.target_entity_name}
                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeGoalPrerequisite(legacyDoc, entityId, g.id, i)}>✕</button>
              </span>
            {/each}
            {#if !closed}
              <span style="display:inline-flex; gap:4px; align-items:center; margin-top:2px;">
                <select bind:value={prereqTarget[g.id]} style="font-size:11px;">
                  <option value="">— prérequis : relation ≥ seuil avec —</option>
                  {#each prereqCandidates as e (e.id)}
                    <option value={e.id}>{e.name}</option>
                  {/each}
                </select>
                <input type="number" bind:value={prereqThreshold[g.id]} min="1" max="100" placeholder="seuil" style="width:60px; font-size:11px;">
                <button class="btn-icon" title="Ajouter ce prérequis" onclick={() => onAddPrerequisite(g.id)}>+</button>
              </span>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}

<div class="row-card">
  <div class="field-grid">
    <div class="field-row"><label>Horizon *</label>
      <select bind:value={newHorizon}>
        <option value="short">short</option>
        <option value="long">long</option>
      </select></div>
    <div class="field-row span-2"><label>Description *</label><textarea bind:value={newDescription}></textarea></div>
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={onAddGoal}>Add goal</button>
  </div>
</div>
