/* TICKET-0060 (BRIEF-0060-b). Non-render state + API calls for the
   Observation surface -- faithful port of observationLoadLocations/
   observationLocationChanged/observationStartRun/observationStepRun/
   observationRunBeats/observationAbortSequence/observationStopRun/
   observationInjectEvent/observationLoadRunList/observationSelectRun/
   observationRefreshDetail/_obsLoadProposals (index.html, now deleted).
   observationInit, _obsSetSequenceUi and observationOpenPrompt do not
   port here: the first is replaced by reloadForWorld() plus a
   world-reactive $effect (F1, Observation.svelte), the second by direct
   `disabled`/`style:display` bindings in the template, the third by an
   inline same-document call (E1, Observation.svelte) now that Prompts.svelte
   lives in the shell document too.

   observationState is the one seam Observation.svelte renders -- exactly
   the fields listed below, no more, no less. Any dynamic-error message
   the legacy version wrote ad hoc into a container's innerHTML but that
   has no dedicated field here (a locations-load failure, a run-list
   fetch failure, a run-detail fetch failure) degrades to the same empty
   state a zero-result response already renders, rather than growing a
   field the brief did not enumerate. */
import { api } from '../creation/sheetRequest.svelte.js';
import { serverState } from '../lib/serverState.svelte.js';

export const OBS_OUTCOME_LABEL = Object.freeze({
  acted: 'a agi', silence: 'silence', degraded: 'dégradé', event: 'événement',
});

export const observationState = $state({
  locations: [],
  selectedLocationId: '',
  presentNpcs: null,
  presentMessage: 'Sélectionnez un lieu.',
  params: {
    maxBeats: 30,
    quiescence: 5,
    cooldown: 2,
    debtWeight: 1.0,
    propensityMode: 'flat',
    mjNarration: false,
  },
  launchErrors: [],
  activeRunId: null,
  activeRunStatus: '',
  beatCount: 5,
  sequenceRunning: false,
  sequenceAbort: false,
  sequenceProgress: '',
  eventText: '',
  runs: [],
  runsLoading: true,
  selectedRunId: null,
  detail: null,
  beats: [],
  proposals: [],
  proposalsMessage: '',
});

export async function loadLocations() {
  try {
    observationState.locations = await api('/api/locations');
  } catch (_e) {
    observationState.locations = [];
  }
}

export async function selectLocation(locationId) {
  observationState.selectedLocationId = locationId;
  if (!locationId) {
    observationState.presentNpcs = null;
    observationState.presentMessage = 'Sélectionnez un lieu.';
    return;
  }
  try {
    const npcs = await api(`/api/observation/locations/${locationId}/present-npcs`);
    observationState.presentNpcs = npcs;
    observationState.presentMessage = npcs.length ? '' : 'Aucun PNJ présent à cet endroit.';
  } catch (e) {
    observationState.presentNpcs = null;
    observationState.presentMessage = e.message;
  }
}

/** Direct fetch (not api()) -- a 422 readiness-gate refusal carries a
 *  {failures: [...]} detail object, and api()'s generic Error(data.detail)
 *  would collapse that to "[object Object]". The gate's whole point is
 *  showing WHICH condition failed (never a generic "cannot start"), so the
 *  detail is parsed here instead. */
export async function startRun() {
  const locationId = observationState.selectedLocationId;
  if (!locationId) {
    observationState.launchErrors = ['Choisissez un lieu.'];
    return;
  }
  const body = {
    world_id: serverState.worldId,
    location_id: locationId,
    max_beats: observationState.params.maxBeats || 30,
    quiescence_limit: observationState.params.quiescence || 5,
    mj_narration: observationState.params.mjNarration,
    cooldown_beats: observationState.params.cooldown || 0,
    debt_weight: observationState.params.debtWeight || 0,
    propensity_mode: observationState.params.propensityMode,
  };
  observationState.launchErrors = [];
  try {
    const res = await fetch('/api/observation/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const failures = (data.detail && data.detail.failures) || [String(data.detail || res.statusText)];
      observationState.launchErrors = failures.map((f) => `✗ ${f}`);
      return;
    }
    observationState.activeRunId = data.id;
    observationState.activeRunStatus = `${data.id} (${data.status})`;
    await selectRun(data.id);
    await loadRunList();
  } catch (e) {
    observationState.launchErrors = [e.message];
  }
}

export async function stepRun() {
  if (!observationState.activeRunId) return;
  if (observationState.sequenceRunning) return;
  try {
    const result = await api(`/api/observation/runs/${observationState.activeRunId}/step`, { method: 'POST' });
    observationState.activeRunStatus = `${result.run.id} (${result.run.status})`;
    await refreshDetail();
  } catch (e) {
    observationState.launchErrors = [e.message];
  }
}

/* TICKET-0060 (BRIEF-0060-b). Multi-beat sequence (TICKET-0053, A1): X
   consecutive beats driven from the client, one POST /step per beat -- the
   same single-beat path a manual click takes. There is no backend loop
   route by design (routes/observation.py:1-15); this function IS the
   client that docstring describes, not a workaround for it. The stop rule
   is NOT re-derived here: max_beats/quiescence stay server-side -- the loop
   simply exits when the run stops reporting status 'running'. The in-flight
   guard is the first statement; sequenceAbort is checked BETWEEN beats
   only -- a beat in flight always completes, its observation_beat and
   observation_intent rows already being written (history is sacred).
   Stops on the first of: X beats done, the run leaving 'running', a step
   error, an interrupt. */
export async function runBeats() {
  if (!observationState.activeRunId || observationState.sequenceRunning) return;
  const parsed = Number(observationState.beatCount);
  const total = Number.isFinite(parsed) && parsed >= 1 ? Math.floor(parsed) : 1;

  observationState.sequenceRunning = true;
  observationState.sequenceAbort = false;

  let executed = 0;
  let note = '';
  try {
    for (let i = 0; i < total; i++) {
      if (observationState.sequenceAbort) {
        note = `interrompu après ${executed} beat(s)`;
        break;
      }
      observationState.sequenceProgress = `beat ${i + 1}/${total}…`;
      let result;
      try {
        result = await api(`/api/observation/runs/${observationState.activeRunId}/step`, { method: 'POST' });
      } catch (e) {
        observationState.launchErrors = [e.message];
        note = `arrêté sur erreur après ${executed} beat(s)`;
        break;
      }
      executed++;
      observationState.activeRunStatus = `${result.run.id} (${result.run.status})`;
      await refreshDetail({ proposals: false });
      if (result.run.status !== 'running') {
        note = `run fermé (${result.run.stop_reason || result.run.status}) après ${executed} beat(s)`;
        break;
      }
    }
  } finally {
    observationState.sequenceRunning = false;
    observationState.sequenceProgress = note || `${executed}/${total} beat(s)`;
    await refreshDetail();
    await loadRunList();
  }
}

/** D2: raises the flag only. The beat in flight completes and persists --
 *  a cancelled request would abandon a beat whose observation_beat and
 *  observation_intent rows are already being written (history is sacred). */
export function abortSequence() {
  if (!observationState.sequenceRunning) return;
  observationState.sequenceAbort = true;
  observationState.sequenceProgress = 'interruption après ce beat…';
}

export async function stopRun() {
  if (!observationState.activeRunId) return;
  observationState.sequenceAbort = true; // D3: closing the run also ends any sequence.
  try {
    const run = await api(`/api/observation/runs/${observationState.activeRunId}/stop`, { method: 'POST' });
    observationState.activeRunStatus = `${run.id} (${run.status})`;
    await refreshDetail();
    await loadRunList();
  } catch (e) {
    observationState.launchErrors = [e.message];
  }
}

export async function injectEvent() {
  if (!observationState.activeRunId) return;
  const text = observationState.eventText.trim();
  if (!text) return;
  try {
    await api(`/api/observation/runs/${observationState.activeRunId}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    observationState.eventText = '';
    await refreshDetail();
  } catch (e) {
    observationState.launchErrors = [e.message];
  }
}

export async function loadRunList() {
  observationState.runsLoading = true;
  try {
    observationState.runs = await api('/api/observation/runs');
  } catch (_e) {
    observationState.runs = [];
  } finally {
    observationState.runsLoading = false;
  }
}

export async function selectRun(runId) {
  observationState.selectedRunId = runId;
  await refreshDetail();
}

/** `proposals:false` is used per beat inside a sequence (TICKET-0053, F1):
 *  produce_run_proposals runs ONCE after the run closes
 *  (observation_runner.py:616-621), so polling /proposals per beat is a
 *  guaranteed-empty GET. The sequence calls this once more, with proposals,
 *  when it ends. */
export async function refreshDetail({ proposals = true } = {}) {
  if (!observationState.selectedRunId) return;
  try {
    const run = await api(`/api/observation/runs/${observationState.selectedRunId}`);
    observationState.detail = run;
    observationState.beats = run.beats;
  } catch (_e) {
    observationState.detail = null;
    observationState.beats = [];
  }
  if (proposals) await loadProposals(observationState.selectedRunId);
}

/** Proposals (F3 visibility): read-only here, reached through
 *  observation_mutation_link -- never through /api/mutations, which
 *  structurally excludes these rows. No approve/reject in this brief. */
export async function loadProposals(runId) {
  try {
    const proposals = await api(`/api/observation/runs/${runId}/proposals`);
    observationState.proposals = proposals;
    observationState.proposalsMessage = proposals.length ? '' : 'Aucune proposition produite par ce run.';
  } catch (e) {
    observationState.proposals = [];
    observationState.proposalsMessage = e.message;
  }
}

/* TICKET-0060 (BRIEF-0060-b, F1). The legacy surface read a WORLD_ID global
   written once at document boot (index.html:1832) and never refreshed by
   activateWorldCascade (creation/tabs.js:703) -- so a run started after a
   Header world switch was created in the PREVIOUSLY active world, and its
   mutation proposals with it. Nothing here caches a world: startRun reads
   serverState.worldId at call time, and this function is driven by an
   effect on that same field. The server still trusts the client's
   world_id (routes/observation.py:48-59); hardening that is TICKET-0060
   decision F3, deferred to its own ticket after TICKET-0061. */
export async function reloadForWorld() {
  observationState.selectedLocationId = '';
  observationState.presentNpcs = null;
  observationState.presentMessage = 'Sélectionnez un lieu.';
  observationState.launchErrors = [];
  observationState.activeRunId = null;
  observationState.activeRunStatus = '';
  observationState.selectedRunId = null;
  observationState.detail = null;
  observationState.beats = [];
  observationState.proposals = [];
  observationState.proposalsMessage = '';
  await loadLocations();
  await loadRunList();
}
