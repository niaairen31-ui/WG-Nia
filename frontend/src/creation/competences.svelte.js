/* TICKET-0059 (BRIEF-0059-h commit 3). Non-render state + API calls for the
   Compétences tab -- faithful port of _competencesWorldReset/
   competencesGenerateDraft/_competencesDomainOptions/competencesRenderDraft/
   competencesDiscardDraftRow/competencesAcceptDraftRow/
   competencesAddManualRow/competencesLoadList/_competencesRenderTable/
   competencesSaveRow (index.html, now deleted). AI draft proposes
   {name, base_domain, description}; the creator accepts each row
   individually (creator-CRUD POST), never a bulk silent write -- Model
   proposes, code judges.

   TICKET-0084 (BRIEF-0084-b): `skill_system` reader. Grouping the
   catalogue by system happens client-side (groupSkillsBySystem below),
   from two flat lists -- never a nested endpoint response
   (json_ui_boundary). BRIEF-0084-d: the read-only gaps reader, fetched
   alongside, never written to by this view.

   TICKET-0099 (BRIEF-0099-b, B1): the tab lives on the shared editor area
   now -- EntityList.svelte renders CompetencesList.svelte in its record
   mode, Sheet.svelte renders CompetencesSheet.svelte under
   `type === 'competences'`. Everything the list hands to the sheet is a
   RECORD (C-01): a fresh object built by the factories below, never a row
   of this store, so editing a fiche changes nothing until Save.
   `persisted` is the one fact that decides POST vs PUT, the "Nouvelle"
   title and whether Delete shows -- never sheetIsNew, which a draft opened
   from the list does not carry. */
import { serverState } from '../lib/serverState.svelte.js';

export const competencesState = $state({
  draft: [],   // proposed rows awaiting Save: {key, name, base_domain, system_id, description}
  rows: [],    // existing world-scoped skill_definition rows
  systems: [], // existing world-scoped skill_system rows
  gaps: [],    // distinct unmatched surface forms, most frequent first
  arbiterFailures: { error: 0, empty: 0 },
  gapsError: '',
  draftWorldId: null, // the world `draft` belongs to; a world switch empties it
});

export const COMPETENCES_DOMAINS = ['physical', 'agility', 'perception', 'composure'];

// Exact label, both as the ungrouped catalogue's group header and as the
// skill fiche's no-system dropdown option (BRIEF-0084-b Scope IN items
// 3-4) -- one literal, never retyped.
export const NO_SYSTEM_LABEL = 'Sans système';

export const ASSISTANT_RECORD_ID = 'assistant';

let nextDraftKey = 1;

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/* ── C-01 record factories ─────────────────────────────────────────────── */

export function skillRecord(row) {
  return {
    kind: 'skill', persisted: true, id: row.id, draftKey: null,
    name: row.name, base_domain: row.base_domain, system_id: row.system_id ?? null,
    description: row.description ?? '',
  };
}

export function systemRecord(sys) {
  return {
    kind: 'system', persisted: true, id: sys.id,
    name: sys.name, description: sys.description ?? '', skill_count: sys.skill_count ?? 0,
  };
}

export function draftRecord(d) {
  return {
    kind: 'skill', persisted: false, id: `draft:${d.key}`, draftKey: d.key,
    name: d.name ?? '', base_domain: d.base_domain ?? '', system_id: d.system_id ?? null,
    description: d.description ?? '',
  };
}

export function assistantRecord() {
  return { kind: 'assistant', persisted: false, id: ASSISTANT_RECORD_ID };
}

/** The blank record the shell's primary action opens (Sheet.svelte's
 *  primaryAction). */
export function blankRecord() {
  return {
    kind: 'skill', persisted: false, id: null, draftKey: null,
    name: '', base_domain: 'physical', system_id: null, description: '',
  };
}

/** The fiche title, read by Sheet.svelte's header effect. */
export function competenceSheetTitle(record) {
  if (!record) return '';
  if (record.kind === 'assistant') return 'Assistant de compétences';
  if (record.kind === 'system') return record.persisted ? record.name : 'Nouveau système';
  return record.persisted ? record.name : 'Nouvelle compétence';
}

/* ── Loading (C-02) ─────────────────────────────────────────────────────── */

/** EntityList.svelte's record-mode fetch for this tab. Throws when the
 *  catalogue itself cannot load; the gaps reader keeps its own error field
 *  so a telemetry failure never blanks the list. */
export async function loadCatalogue() {
  if (competencesState.draftWorldId !== serverState.worldId) {
    competencesState.draft = [];
    competencesState.draftWorldId = serverState.worldId;
  }
  const [rows, systems] = await Promise.all([
    api('/api/skill-definitions'),
    api('/api/skill-systems'),
  ]);
  competencesState.rows = rows;
  competencesState.systems = systems;
  await loadGaps();
}

/** Read-only: GET /api/skill-gaps only, never a write (BRIEF-0084-d). */
export async function loadGaps() {
  competencesState.gapsError = '';
  try {
    const data = await api('/api/skill-gaps');
    competencesState.gaps = data.gaps || [];
    competencesState.arbiterFailures = data.arbiter_failures || { error: 0, empty: 0 };
  } catch (e) {
    competencesState.gapsError = e.message;
  }
}

/** Groups the flat skill-definition list under the flat system list,
 *  client-side (json_ui_boundary: no nested endpoint response). System
 *  groups are ordered by name and always rendered, even with zero skills
 *  (a system just created must be visible before it holds anything).
 *  Skills with no system, or whose system_id matches no live system, land
 *  in a trailing NO_SYSTEM_LABEL group -- rendered only when non-empty. */
export function groupSkillsBySystem(rows, systems) {
  const bySystem = new Map();
  for (const sys of [...systems].sort((a, b) => a.name.localeCompare(b.name))) {
    bySystem.set(sys.id, { system: sys, skills: [] });
  }
  const unassigned = [];
  for (const row of [...rows].sort((a, b) => a.name.localeCompare(b.name))) {
    const bucket = row.system_id ? bySystem.get(row.system_id) : undefined;
    if (bucket) bucket.skills.push(row);
    else unassigned.push(row);
  }
  const groups = [...bySystem.values()];
  if (unassigned.length) groups.push({ system: null, skills: unassigned });
  return groups;
}

/* ── Drafts (C-03) ──────────────────────────────────────────────────────── */

/** Returns {ok:false, error} | {ok:true, notes}. The proposed rows REPLACE
 *  the current drafts (unchanged since BRIEF-0059-h); each gets a key. The
 *  assistant knows nothing of skill_system: every row starts with none. */
export async function generateDraft(brief) {
  const result = await api('/api/skill-definitions/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ brief }),
  });
  if (!result.ok) return { ok: false, error: result.error };
  competencesState.draft = (result.draft.skills || []).map((s) => ({
    ...s, key: nextDraftKey++, system_id: s.system_id ?? null,
  }));
  return { ok: true, notes: result.notes || [] };
}

/** A gap click (BRIEF-0084-d item 4): name prefilled from surface_form,
 *  base_domain and system_id left unset -- Nia chooses deliberately.
 *  Creates nothing; returns the draft's record for the caller to open. */
export function addGapDraft(surfaceForm) {
  const d = { key: nextDraftKey++, name: surfaceForm, base_domain: '', system_id: null, description: '' };
  competencesState.draft.push(d);
  return draftRecord(d);
}

export function discardDraft(key) {
  competencesState.draft = competencesState.draft.filter((d) => d.key !== key);
}

/* ── Writes (C-04) ──────────────────────────────────────────────────────── */

function requireName(record) {
  const name = (record.name || '').trim();
  if (!name) throw new Error('Nom requis.');
  return name;
}

async function saveSkill(record) {
  const name = requireName(record);
  if (!COMPETENCES_DOMAINS.includes(record.base_domain)) throw new Error('Domaine de base requis.');
  const body = JSON.stringify({
    name, base_domain: record.base_domain, system_id: record.system_id || null,
    description: record.description || '',
  });
  const saved = record.persisted
    ? await api(`/api/skill-definitions/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
    : await api('/api/skill-definitions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
  if (record.draftKey != null) discardDraft(record.draftKey);
  return skillRecord(saved);
}

async function saveSystem(record) {
  const name = requireName(record);
  const body = JSON.stringify({ name, description: record.description || null });
  const saved = await api(`/api/skill-systems/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body });
  return systemRecord(saved);
}

/** Saves the open fiche's record; returns the saved record (C-01). Throws
 *  Error with a French message on a refused or failed write. */
export async function saveCompetenceRecord(record) {
  if (record.kind === 'skill') return saveSkill(record);
  if (record.kind === 'system') return saveSystem(record);
  throw new Error('Rien à enregistrer.');
}

/** D2-delete-cascade: dependent PC `skill` rows then the definition, in one
 *  transaction, server-side. No separate history snapshot (locked). */
export async function deleteSkill(id) {
  await api(`/api/skill-definitions/${id}`, { method: 'DELETE' });
}

/** D2b-delete-refuse: the server is fail-closed (409) while any
 *  skill_definition still carries this system_id. */
export async function deleteSystem(id) {
  await api(`/api/skill-systems/${id}`, { method: 'DELETE' });
}

/** Back to the empty fiche after a delete or a discarded draft (C-05).
 *  Sheet.svelte owns the sheet quintet (state.svelte.js), so this only
 *  signals: 'creation:record-closed' is Sheet's own listener, and
 *  'creation:selection' with no id is EntityList's -- the same two-event
 *  shape creationSelectRecord (tabs.js) uses to open a record.
 *  'creation:sheet-reset' is not reused: its dispatch is confined to
 *  tabs.js (creation_tab_switch.py rule 3). */
export function closeCompetenceSheet() {
  document.dispatchEvent(new CustomEvent('creation:record-closed'));
  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
}
