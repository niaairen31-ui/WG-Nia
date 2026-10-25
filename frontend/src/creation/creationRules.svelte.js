/* TICKET-0126 (BRIEF-0126-E). The world's character-creation rules and the
   per-system / per-skill creation overrides, for Création > Compétences.

   A fourth record kind, 'creation', sits beside 'ranks' in the list and
   edits the world's rules (GET/PUT /api/creation-rules): the pool, the cost
   to reach each rank, the cap per rank, the highest rank at creation, the
   number of master skills and whether skills are visible by default. A
   system carries four overrides, a skill the first two; null inherits --
   the skill, then its system, then the world.

   This file imports nothing from competences.svelte.js: that one imports
   from here, never the other way round. */

export const CREATION_RECORD_ID = 'creation';

export const creationRulesState = $state({ rules: null });

const OVERRIDE_KEYS = ['visible_at_creation', 'max_rank_at_creation', 'cap_raised_at_creation', 'cap_held_at_creation'];
const SKILL_OVERRIDE_KEYS = OVERRIDE_KEYS.slice(0, 2);
const INTEGER_ERROR = 'Un coût, un plafond ou la réserve est un nombre entier, au moins 0.';

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

/** An input's value: an integer >= 0; blank is null when `blank` allows it. */
function intValue(value, { blank = false } = {}) {
  if (value === null || value === undefined || value === '') {
    if (blank) return null;
    throw new Error(INTEGER_ERROR);
  }
  const n = Number(value);
  if (!Number.isInteger(n) || n < 0) throw new Error(INTEGER_ERROR);
  return n;
}

export async function loadCreationRules() {
  creationRulesState.rules = await api('/api/creation-rules');
}

/** The 'creation' record (C-01): a fresh copy of the rules, so editing the
 *  fiche changes nothing until Save. */
export function creationRulesRecord() {
  const rules = creationRulesState.rules;
  return {
    kind: 'creation', persisted: true, id: CREATION_RECORD_ID,
    pool: rules?.pool ?? null,
    costs: (rules?.costs ?? []).map((c) => ({ rank: c.rank, cost: c.cost })),
    caps: (rules?.caps ?? []).map((c) => ({ rank: c.rank, cap: c.cap })),
    max_rank: rules?.max_rank ?? null,
    max_master_skills: rules?.max_master_skills ?? null,
    skills_visible: !!rules?.skills_visible,
  };
}

export async function saveCreationRules(record) {
  const body = {
    pool: intValue(record.pool),
    costs: record.costs.map((c) => ({ rank: c.rank, cost: intValue(c.cost) })),
    caps: record.caps.map((c) => ({ rank: c.rank, cap: intValue(c.cap, { blank: true }) })),
    max_rank: intValue(record.max_rank),
    max_master_skills: intValue(record.max_master_skills),
    skills_visible: !!record.skills_visible,
  };
  creationRulesState.rules = await api('/api/creation-rules', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  return creationRulesRecord();
}

/** The four override fields of a system or skill row; null when absent. */
export function creationOverrides(row) {
  const overrides = {};
  for (const key of OVERRIDE_KEYS) overrides[key] = row?.[key] ?? null;
  return overrides;
}

/** The overrides a save sends: four for a system, two for a skill; blanks null. */
export function creationOverridesBody(record) {
  const keys = record.kind === 'system' ? OVERRIDE_KEYS : SKILL_OVERRIDE_KEYS;
  const body = {};
  for (const key of keys) {
    const value = record[key];
    if (key === 'visible_at_creation') body[key] = value === null || value === undefined || value === '' ? null : !!value;
    else body[key] = intValue(value, { blank: true });
  }
  return body;
}

/** The visibility a blank override inherits: a skill reads its system's when
 *  set, then the world's `skills_visible`; a system reads the world's. */
export function inheritedVisible(record, systems, rules) {
  if (record.kind === 'skill' && record.system_id) {
    const sys = systems.find((s) => s.id === record.system_id);
    if (sys && sys.visible_at_creation != null) return !!sys.visible_at_creation;
  }
  return rules ? !!rules.skills_visible : null;
}

/** The highest rank at creation a blank override inherits, same cascade. */
export function inheritedMaxRank(record, systems, rules) {
  if (record.kind === 'skill' && record.system_id) {
    const sys = systems.find((s) => s.id === record.system_id);
    if (sys && sys.max_rank_at_creation != null) return sys.max_rank_at_creation;
  }
  return rules ? rules.max_rank : null;
}
