<script>
  /* TICKET-0074 (BRIEF-0074-b). "La journée de X" -- the T-C1 authoring
     island for npc_schedule, mounted on the NPC sheet after Objectifs (an
     occupation is the reason, a schedule is the where -- they read in that
     order). Four phase rows in SCHEDULE_PHASES order, each a location
     picker plus an optional standing-goal picker fed by this NPC's own
     kind='standing' goals; one Save button writes the whole day,
     full-replace (E1) -- clearing a row's location and saving removes
     that phase. Empty phases render as visibly empty rows, never omitted
     -- the authoring-side counterpart to the F1 read panel's own B1
     guarantee.

     No data prop, unlike DoorsEditor/GeometryEditor/PricingEditor: like
     GoalsEditor, this loads its own data (Sheet.svelte's `detail` never
     carries schedule rows -- confirmed against crud/entities.py's
     get_entity, mini-RECON item 5). */
  import { SCHEDULE_PHASES, PHASE_LABELS } from './schedule.js';
  import { creationState } from './state.svelte.js';
  import { scheduleState, loadSchedule, saveSchedule } from './schedulePanel.svelte.js';

  let { entityId, legacyDoc } = $props();

  let draft = $state(
    Object.fromEntries(SCHEDULE_PHASES.map((phase) => [phase, { location_id: '', standing_goal_id: '' }])),
  );

  $effect(() => {
    loadSchedule(entityId);
  });

  // Reflects the loaded rows into the editable draft in place -- draft's
  // per-phase objects exist from the start (above) so bind:value always
  // has a real property to bind to, even before the fetch resolves.
  $effect(() => {
    for (const phase of SCHEDULE_PHASES) {
      const row = scheduleState.rows.find((r) => r.phase === phase);
      draft[phase].location_id = row?.location_id || '';
      draft[phase].standing_goal_id = row?.standing_goal_id || '';
    }
  });

  const locationOptions = $derived((creationState.entities || []).filter((e) => e.type === 'location'));

  async function onSave() {
    const rows = SCHEDULE_PHASES.map((phase) => ({
      phase,
      location_id: draft[phase].location_id,
      standing_goal_id: draft[phase].standing_goal_id,
    }));
    await saveSchedule(legacyDoc, entityId, rows);
  }
</script>

{#if scheduleState.loadError}
  <div class="empty">{scheduleState.loadError}</div>
{:else}
  <div class="row-table">
    {#each SCHEDULE_PHASES as phase (phase)}
      <div class="row-card">
        <div class="field-grid">
          <div class="field-row"><label>{PHASE_LABELS[phase]}</label>
            <select bind:value={draft[phase].location_id}>
              <option value="">— vide —</option>
              {#each locationOptions as loc (loc.id)}
                <option value={loc.id}>{loc.name}</option>
              {/each}
            </select>
          </div>
          <div class="field-row"><label>Occupation</label>
            <select bind:value={draft[phase].standing_goal_id}>
              <option value="">—</option>
              {#each scheduleState.standingGoals as g (g.id)}
                <option value={g.id}>{g.description}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>
    {/each}
  </div>
  <div class="row-card-actions">
    <button class="btn-send" onclick={onSave}>Save</button>
  </div>
{/if}
