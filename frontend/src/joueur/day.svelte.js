/* TICKET-0128 (BRIEF-0128-G). The player's days: he declares, then reads
   what the creator published. Only /api/joueur/ (PSH2); imports stay in
   this folder (PSH3). */

import { joueurState, call, postJson } from './joueur.svelte.js';

export const DAY_POLL_MS = 5000;

export const dayState = $state({
  days: [],
  canDeclare: false,
  characterId: null,
  declaration: '',
  loading: false,
  submitting: false,
  error: '',
});

let pollTimer = null;

function apply(body) {
  dayState.days = body.days;
  dayState.canDeclare = body.can_declare;
  dayState.characterId = body.character_id;
  if (pollTimer !== null) clearTimeout(pollTimer);
  pollTimer = null;
  if (dayState.days.some((d) => d.state === 'en_cours')) {
    pollTimer = setTimeout(() => {
      pollTimer = null;
      loadPlayerDays();
    }, DAY_POLL_MS);
  }
}

export async function loadPlayerDays() {
  const profile = joueurState.profile;
  const world = joueurState.world;
  if (!profile || !world) {
    apply({ days: [], can_declare: false, character_id: null });
    return;
  }
  dayState.loading = true;
  dayState.error = '';
  try {
    const body = await call('/api/joueur/journee?profile_id=' + encodeURIComponent(profile.id)
      + '&world_id=' + encodeURIComponent(world.id));
    if (joueurState.world === world) apply(body);
  } catch (e) {
    dayState.error = e.message;
  } finally {
    dayState.loading = false;
  }
}

export async function declarePlayerDay() {
  const text = dayState.declaration.trim();
  if (!text || !joueurState.profile || !joueurState.world) return;
  dayState.submitting = true;
  dayState.error = '';
  try {
    const body = await postJson('/api/joueur/journee/declarer', {
      profile_id: joueurState.profile.id,
      world_id: joueurState.world.id,
      declared_action: text,
    });
    dayState.declaration = '';
    apply(body);
  } catch (e) {
    dayState.error = e.message;
  } finally {
    dayState.submitting = false;
  }
}
