<script>
  /* TICKET-0060 (BRIEF-0060-b). Observation's own shell-native surface --
     a sibling of Play/Création, never a Creation sub-tab (P1, TICKET-0051).
     App.svelte drives this component directly (commit 3), exactly the
     Creation.svelte precedent: always mounted, `active` only toggles this
     root's own visibility.

     E1 -- full Svelte templating. The four legacy string renderers
     (_obsRenderRunDetail/_obsRenderTranscript/_obsRenderIntents/
     _obsLoadProposals's render half) become real markup below; every
     ${esc(...)} disappears because Svelte interpolation escapes on its
     own. No {@html} anywhere in this file -- that is what makes D1's
     scoped <style> block below actually apply to this content. */
  import { serverState } from '../lib/serverState.svelte.js';
  import { navigate } from '../lib/router.js';
  import {
    observationState, OBS_OUTCOME_LABEL, loadRunList, selectLocation, startRun,
    stepRun, runBeats, abortSequence, stopRun, injectEvent, selectRun,
    refreshDetail, reloadForWorld,
  } from './observation.svelte.js';

  let { active = false } = $props();

  function openPrompt(templateId) {
    navigate('creation', 'prompts');
    document.dispatchEvent(new CustomEvent('creation:open-prompt', { detail: { templateId } }));
  }

  /* F1 -- the world is read, never cached. No onMount load, no
     `initialized` flag, no load-on-first-activation: this effect fires at
     shell boot (Observation is always mounted) and again on every Header
     world switch, calling reloadForWorld() (observation.svelte.js) both
     times. Cost accepted: two reads at boot even if never visited, same
     as Creation.svelte. */
  $effect(() => {
    void serverState.worldId;
    reloadForWorld();
  });
</script>

<div class="app-view" id="observation-view" style:display={active ? '' : 'none'}>

  <!-- ── Launch ── -->
  <div class="queue-panel" id="obs-launch-panel">
    <div class="panel-head">
      <h2>Scène observée — lancer</h2>
      <button class="btn-icon" onclick={() => loadRunList()} title="Rafraîchir les runs">↻</button>
    </div>
    <div class="queue-body">
      <div>
        <label>Lieu
          <select value={observationState.selectedLocationId} onchange={(e) => selectLocation(e.currentTarget.value)}>
            <option value="">— choisir —</option>
            {#each observationState.locations as l (l.id)}
              <option value={l.id}>{l.name}</option>
            {/each}
          </select>
        </label>

        {#if observationState.presentNpcs === null}
          {#if observationState.presentMessage === 'Sélectionnez un lieu.'}
            <div class="empty">{observationState.presentMessage}</div>
          {:else}
            <div><span class="r-err">{observationState.presentMessage}</span></div>
          {/if}
        {:else if observationState.presentNpcs.length === 0}
          <div><span class="r-warn">{observationState.presentMessage}</span></div>
        {:else}
          <div><strong>PNJ présents ({observationState.presentNpcs.length}) :</strong> {observationState.presentNpcs.map((n) => n.name).join(', ')}</div>
        {/if}

        <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:8px">
          <label>Beats max <input type="number" bind:value={observationState.params.maxBeats} min="1" style="width:70px"></label>
          <label>Quiescence <input type="number" bind:value={observationState.params.quiescence} min="1" style="width:70px"></label>
          <label>Cooldown <input type="number" bind:value={observationState.params.cooldown} min="0" style="width:70px"></label>
          <label>Poids dette <input type="number" bind:value={observationState.params.debtWeight} step="0.1" style="width:70px"></label>
          <label>Propension
            <select bind:value={observationState.params.propensityMode}>
              <option value="flat">flat</option>
              <option value="relation_weighted">relation_weighted</option>
            </select>
          </label>
          <label><input type="checkbox" bind:checked={observationState.params.mjNarration}> Narration MJ</label>
        </div>
        <div style="margin-top:10px">
          <button onclick={() => startRun()}>▶ Démarrer</button>
        </div>
        <div>
          {#each observationState.launchErrors as err}
            <div class="r-err">{err}</div>
          {/each}
        </div>
      </div>

      {#if observationState.activeRunId}
        <div style="margin-top:14px; border-top:1px solid var(--border); padding-top:10px">
          <span>Run en cours : <strong>{observationState.activeRunStatus || '—'}</strong></span>
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:6px">
            <button disabled={observationState.sequenceRunning} onclick={() => stepRun()}>⏭ Un beat</button>
            <label>Suite <input type="number" bind:value={observationState.beatCount} min="1" style="width:60px"></label>
            <button disabled={observationState.sequenceRunning} onclick={() => runBeats()}>⏩ Faire X beats</button>
            {#if observationState.sequenceRunning}
              <button onclick={() => abortSequence()}>⏸ Interrompre</button>
            {/if}
            <span class="target-ref">{observationState.sequenceProgress}</span>
            <button onclick={() => stopRun()}>⏹ Arrêter</button>
            <input type="text" bind:value={observationState.eventText} placeholder="Texte de l'événement injecté…" style="flex:1; min-width:200px">
            <button disabled={observationState.sequenceRunning} onclick={() => injectEvent()}>⚡ Injecter</button>
          </div>
        </div>
      {/if}

      <div style="margin-top:14px; border-top:1px solid var(--border); padding-top:10px">
        <h3 style="margin:0 0 6px">Runs précédents</h3>
        <div>
          {#if observationState.runsLoading}
            <div class="empty"><span class="spin">⟳</span></div>
          {:else if observationState.runs.length === 0}
            <div class="empty">Aucun run pour ce monde.</div>
          {:else}
            {#each observationState.runs as r (r.id)}
              <div style="display:flex; align-items:center; gap:8px; padding:4px 0; cursor:pointer" onclick={() => selectRun(r.id)}>
                <span class="badge b-other">{r.status}</span>
                <span>{r.location_name || r.location_id}</span>
                <span class="target-ref">{r.beat_count} beat(s)</span>
                <span class="target-ref">{r.started_at || ''}</span>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </div><!-- #obs-launch-panel -->

  <!-- ── Transcript + run detail + proposals (selected run) ── -->
  <div class="queue-panel" id="obs-detail-panel" style:display={observationState.selectedRunId ? '' : 'none'}>
    <div class="panel-head">
      <h2>Run <span>{observationState.selectedRunId || ''}</span></h2>
      <button class="btn-icon" onclick={() => refreshDetail()} title="Rafraîchir">↻</button>
    </div>
    <div class="queue-body">
      <!-- render:run-detail -->
      {#if observationState.detail}
        {@const run = observationState.detail}
        <div style="display:flex; gap:16px; flex-wrap:wrap">
          <span class="badge b-other">{run.status}</span>
          {#if run.stop_reason}<span class="badge b-other">stop: {run.stop_reason}</span>{/if}
          <span>{run.location_name || run.location_id}</span>
        </div>
        <div style="margin-top:8px; display:flex; gap:14px; flex-wrap:wrap; font-size:12px; color:var(--muted)">
          <span>cooldown_beats={run.cooldown_beats}</span>
          <span>debt_weight={run.debt_weight}</span>
          <span>propensity_mode={run.propensity_mode}</span>
          <span>mj_narration={run.mj_narration}</span>
          <span>model={run.model}</span>
        </div>
        <div style="margin-top:8px">
          {#each run.templates as t}
            <div>
              <span class="target-ref">{t.usage}</span>
              <a href="#" onclick={(e) => { e.preventDefault(); openPrompt(t.template_id); }}>v{t.version}</a>
            </div>
          {/each}
        </div>
      {/if}
      <!-- /render:run-detail -->

      <h3 style="margin:14px 0 6px">Transcript</h3>
      <!-- render:transcript -->
      <div>
        {#if !observationState.beats || !observationState.beats.length}
          <div class="empty">Aucun beat.</div>
        {:else}
          {#each observationState.beats as b (b.beat_index)}
            <details style="border-bottom:1px solid var(--border); padding:4px 0">
              <summary style="cursor:pointer; display:flex; gap:8px; align-items:center">
                <span class="target-ref">#{b.beat_index}</span>
                <span class="badge b-{b.outcome}">{OBS_OUTCOME_LABEL[b.outcome] || b.outcome}</span>
                <span>{b.actor_name ? b.actor_name + ' — ' : ''}{b.line || ''}</span>
              </summary>
              {#if b.mj_narration}
                <div style="font-style:italic; color:var(--muted); margin:4px 0 0 20px">{b.mj_narration}</div>
              {/if}
              <div style="margin:6px 0 0 20px">
                <!-- render:intents -->
                {#if !b.intents || !b.intents.length}
                  <div class="empty">Aucun candidat (événement).</div>
                {:else}
                  {#each b.intents as i}
                    <div style="font-size:12px; padding:3px 0; border-top:1px dashed var(--border)">
                      <strong>{i.npc_name}</strong>
                      <span class="badge b-other">{i.call_status}</span>
                      {#if i.selected}<span class="badge b-acted">sélectionné</span>{/if}
                      {#if !i.selected}<span class="target-ref">raison (dérivée) : {i.not_selected_reason || ''}</span>{/if}
                      <div style="color:var(--muted)">
                        act={i.act} urgency={i.urgency ?? '—'} propensity={i.propensity.toFixed(2)}
                        cooldown_active={i.cooldown_active} debt_score={i.debt_score.toFixed(2)}
                        final_score={i.final_score.toFixed(2)}
                      </div>
                      {#if i.why}<div>« {i.why} »</div>{/if}
                    </div>
                  {/each}
                {/if}
                <!-- /render:intents -->
              </div>
            </details>
          {/each}
        {/if}
      </div>
      <!-- /render:transcript -->

      <h3 style="margin:14px 0 6px">Propositions produites (F3 — jamais dans la file de revue)</h3>
      <!-- render:proposals -->
      <div>
        {#if !observationState.proposals || !observationState.proposals.length}
          <div class="empty">{observationState.proposalsMessage || 'Aucune proposition.'}</div>
        {:else}
          {#each observationState.proposals as p}
            <div style="padding:4px 0; border-bottom:1px solid var(--border)">
              <span class="badge b-{p.mutation_type}">{p.mutation_type}</span>
              <span class="target-ref">{p.target_table}{p.beat_id ? ' · beat ' + p.beat_id.slice(0, 8) : ''}</span>
              <div>{p.rationale || ''}</div>
            </div>
          {/each}
        {/if}
      </div>
      <!-- /render:proposals -->
    </div>
  </div><!-- #obs-detail-panel -->

</div><!-- #observation-view -->

<style>
  /* TICKET-0060 (BRIEF-0060-b, D1). These two rules lived in
     frontend/public/creation.css, which cockpit/index.html stopped linking
     when TICKET-0059 retired the Creation mount -- stylesheet_partition.py
     rule5 ties that link's lifetime to LEGACY_MOUNTS.creation, so the
     removal was structurally forced. Observation kept applying both
     classes from inside that document, at nine sites, and every error
     message rendered uncoloured. They are Observation's only two exclusive
     rules and have no consumer under frontend/src, so they belong in this
     component's scoped block rather than in any global sheet: no selector
     is added to the partition, and rule7's SCOPED(F) term covers them.
     Commit 4 deletes them from creation.css. */
  .r-warn { color: var(--yellow); }
  .r-err  { color: var(--red); }
</style>
