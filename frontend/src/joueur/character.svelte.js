/* TICKET-0126 (BRIEF-0126-H, C-14). The character creation screen's state
   and calls. Every URL is a /api/joueur/creation/ path: what the player
   sees of the world comes from those routes (INV-66). The draft is held as
   the server answers it (`draft`, C-13) and edited through `form`; the
   draft's text travels as `story`. A submitted draft is read-only. */

import { joueurState, call, postJson, putJson } from './joueur.svelte.js';

export const characterState = $state({
  open: false,
  catalogue: null,
  draft: null,
  verdict: null,
  designer: null,
  busy: false,
  error: '',
  form: null,
});

function key() {
  return { profile_id: joueurState.profile.id, world_id: joueurState.world.id };
}

function query() {
  return new URLSearchParams(key()).toString();
}

function skillLine(skillKey) {
  return (characterState.catalogue?.skills || []).find((s) => s.skill_key === skillKey);
}

// The editable copy of a draft: one rank per catalogue skill (its player
// rank, else its start rank), its people, factions and knowledge.
function formOf(draft) {
  const rows = Object.fromEntries((draft.skills || []).map((s) => [s.skill_key, s]));
  const ranks = {};
  const justifications = {};
  for (const skill of characterState.catalogue?.skills || []) {
    const row = rows[skill.skill_key];
    ranks[skill.skill_key] = row && row.player_rank !== null ? row.player_rank : skill.start_rank;
    justifications[skill.skill_key] = row?.justification || '';
  }
  return {
    name: draft.name,
    story: draft.story,
    start_location_id: draft.start_location ? draft.start_location.entity_id : '',
    ranks,
    justifications,
    sketches: (draft.sketches || []).map((s) => ({
      id: s.id, name: s.name, role: s.role, sentence: s.sentence, group_label: s.group_label,
      kind: s.kind, skill_key: s.skill_key, existing_entity: s.existing_entity,
    })),
    memberships: (draft.memberships || []).map((m) => ({ faction_id: m.faction_id, role: m.role || '' })),
    knowledge: (draft.knowledge || []).map((k) => ({ id: k.id, level: k.level, content: k.content })),
  };
}

function take(body) {
  characterState.draft = body.draft;
  characterState.verdict = body.verdict;
  characterState.form = body.draft ? formOf(body.draft) : null;
}

// The player ranks the sheet sends: every skill moved from its start rank,
// or carrying a justification.
function chosenSkills() {
  const form = characterState.form;
  return (characterState.catalogue?.skills || [])
    .filter((s) => form.ranks[s.skill_key] !== s.start_rank || form.justifications[s.skill_key].trim())
    .map((s) => ({
      skill_key: s.skill_key,
      rank: form.ranks[s.skill_key],
      justification: form.justifications[s.skill_key] || null,
    }));
}

function payload() {
  const form = characterState.form;
  return {
    ...key(),
    name: form.name,
    story: form.story,
    start_location_id: form.start_location_id || null,
    skills: chosenSkills(),
    sketches: form.sketches.map((s) => ({
      id: s.id || null, name: s.name, role: s.role, sentence: s.sentence, group_label: s.group_label,
      kind: s.kind, skill_key: s.kind === 'master' ? s.skill_key : null,
      existing_entity_id: s.existing_entity ? s.existing_entity.entity_id : null,
    })),
    memberships: form.memberships.filter((m) => m.faction_id)
      .map((m) => ({ faction_id: m.faction_id, role: m.role || null })),
    knowledge: form.knowledge.map((k) => ({ id: k.id || null, level: k.level, content: k.content })),
  };
}

async function run(step) {
  if (characterState.busy) return false;
  characterState.busy = true;
  characterState.error = '';
  try {
    await step();
    return true;
  } catch (e) {
    characterState.error = e.message;
    return false;
  } finally {
    characterState.busy = false;
  }
}

export async function openCreation() {
  if (!joueurState.profile || !joueurState.world) return;
  characterState.open = true;
  characterState.designer = null;
  await run(async () => {
    characterState.catalogue = await call(`/api/joueur/creation/catalogue?${query()}`);
    let body = await call(`/api/joueur/creation/brouillon?${query()}`);
    if (!body.draft) body = await postJson('/api/joueur/creation/brouillon', key());
    take(body);
  });
}

export async function saveDraft() {
  return run(async () => {
    take(await putJson('/api/joueur/creation/brouillon', payload()));
  });
}

export async function verifySkills() {
  if (!characterState.form) return;
  try {
    const skills = chosenSkills().map((s) => ({ skill_key: s.skill_key, rank: s.rank }));
    characterState.verdict = await postJson('/api/joueur/creation/verifier', { ...key(), skills });
  } catch (e) {
    characterState.error = e.message;
  }
}

// The designer reads the saved draft: the player's edits are saved first.
export async function askDesigner() {
  if (!(await saveDraft())) return;
  await run(async () => {
    const body = await postJson('/api/joueur/creation/concepteur', {
      ...key(), attempt_id: crypto.randomUUID(),
    });
    take(body);
    characterState.designer = body.designer;
  });
}

export async function submitDraft() {
  if (!(await saveDraft())) return;
  await run(async () => {
    const body = await postJson('/api/joueur/creation/soumettre', key());
    take(body);
    if (!body.submitted) characterState.error = 'Le personnage ne peut pas encore être soumis.';
  });
}

export function suggestion(skillKey) {
  const row = (characterState.draft?.skills || []).find((s) => s.skill_key === skillKey);
  return row && row.designer_rank !== null ? row : null;
}

export function acceptSuggestion(skillKey) {
  const row = suggestion(skillKey);
  if (!row || !characterState.form || !skillLine(skillKey)) return;
  characterState.form.ranks[skillKey] = row.designer_rank;
  verifySkills();
}

export function acceptAllSuggestions() {
  if (!characterState.form) return;
  for (const skill of characterState.catalogue?.skills || []) {
    const row = suggestion(skill.skill_key);
    if (row) characterState.form.ranks[skill.skill_key] = row.designer_rank;
  }
  verifySkills();
}

export function closeCreation() {
  characterState.open = false;
  characterState.catalogue = null;
  characterState.draft = null;
  characterState.verdict = null;
  characterState.designer = null;
  characterState.form = null;
  characterState.error = '';
}
