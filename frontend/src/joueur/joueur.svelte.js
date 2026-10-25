/* TICKET-0125 (BRIEF-0125-G, C-14). The player shell's state and fetch
   helpers. Every URL here is a /api/joueur/ path: the player shell never
   calls a creator route and imports nothing outside frontend/src/joueur/
   (INV-66). The chosen profile is a choice, not a login: its {id, name}
   is remembered under localStorage `wg-joueur-profile` and travels in the
   request body. */

import { closeCreation } from './character.svelte.js';

const PROFILE_KEY = 'wg-joueur-profile';

export const joueurState = $state({
  profile: null,
  profiles: [],
  worlds: [],
  world: null,
  question: '',
  asking: false,
  error: '',
  result: null,
  selections: {},
  attemptId: '',
});

export async function call(url, options = {}) {
  const response = await fetch(url, options);
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    const detail = body && typeof body.detail === 'string' ? body.detail : `Erreur ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

export function postJson(url, payload) {
  return call(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function putJson(url, payload) {
  return call(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function clearQuestion() {
  joueurState.question = '';
  joueurState.error = '';
  joueurState.result = null;
  joueurState.selections = {};
  joueurState.attemptId = '';
}

export async function loadProfiles() {
  joueurState.error = '';
  try {
    joueurState.profiles = await call('/api/joueur/profils');
  } catch (e) {
    joueurState.error = e.message;
  }
}

export async function createProfile(name) {
  joueurState.error = '';
  try {
    const profile = await postJson('/api/joueur/profils', { name });
    await loadProfiles();
    chooseProfile(profile);
  } catch (e) {
    joueurState.error = e.message;
  }
}

export function chooseProfile(p) {
  joueurState.profile = p ? { id: p.id, name: p.name } : null;
  joueurState.world = null;
  clearQuestion();
  try {
    if (joueurState.profile) {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(joueurState.profile));
    } else {
      localStorage.removeItem(PROFILE_KEY);
    }
  } catch {
    // Storage unavailable: the choice holds for this page only.
  }
}

// A remembered profile is kept only if the server still lists it.
export async function restoreProfile() {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null');
  } catch {
    saved = null;
  }
  await loadProfiles();
  const known = saved && joueurState.profiles.find((p) => p.id === saved.id);
  joueurState.profile = known ? { id: known.id, name: known.name } : null;
}

export async function loadWorlds() {
  joueurState.error = '';
  try {
    joueurState.worlds = await call('/api/joueur/mondes');
  } catch (e) {
    joueurState.error = e.message;
  }
}

export function openWorld(w) {
  joueurState.world = w;
  clearQuestion();
  closeCreation();
}

export async function askSavoir() {
  const question = joueurState.question.trim();
  if (!question || joueurState.asking || !joueurState.profile || !joueurState.world) return;
  joueurState.asking = true;
  joueurState.error = '';
  joueurState.attemptId = crypto.randomUUID();
  try {
    joueurState.result = await postJson('/api/joueur/savoir/ask', {
      profile_id: joueurState.profile.id,
      world_id: joueurState.world.id,
      question,
      attempt_id: joueurState.attemptId,
    });
    joueurState.selections = {};
  } catch (e) {
    joueurState.error = e.message;
  } finally {
    joueurState.asking = false;
  }
}

export function selectSavoirCandidate(ref, entityId) {
  joueurState.selections = { ...joueurState.selections, [ref]: entityId };
}

export function allSavoirChoicesMade() {
  const result = joueurState.result;
  if (!result || result.verdict !== 'ambiguous_mention') return false;
  const refs = Object.keys(result.candidates || {});
  return refs.length > 0 && refs.every((ref) => joueurState.selections[ref]);
}

export async function confirmSavoir() {
  const result = joueurState.result;
  if (!result || joueurState.asking) return;
  joueurState.asking = true;
  joueurState.error = '';
  try {
    joueurState.result = await postJson('/api/joueur/savoir/resolve', {
      profile_id: joueurState.profile.id,
      world_id: joueurState.world.id,
      plan: result.plan,
      bindings: { ...joueurState.selections },
      question: joueurState.question,
      attempt_id: joueurState.attemptId,
    });
    joueurState.selections = {};
  } catch (e) {
    joueurState.error = e.message;
  } finally {
    joueurState.asking = false;
  }
}
