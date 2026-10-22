/* TICKET-0058 (BRIEF-0058-g, family e). Shared draft state for the
   "créé à l'acceptation" pending knowledge/goals panels on a NEW npc sheet
   -- was the pendingDraftKnowledge/pendingDraftGoals globals (index.html,
   now deleted). Read directly by Sheet.svelte's submitEntity via
   knowledgeForCreate()/goalsForCreate() at creation time.

   pendingDraftNotes stayed a separate, untouched legacy global at the time
   this family landed: it belonged to the AI-generate panel's own "Notes de
   l'assistant" block (authorRenderGenNotes/#entity-gen-notes), the
   generate/draft path Scope OUT reserved for brief -h -- out of this
   family's scope despite appearing in the brief's family list (an M7
   approximation bleeding two unrelated "notes"/"pending" concepts
   together), reported rather than acted on at the time. Brief -h has since
   ported it to generatePanelState (generatePanel.svelte.js). */
export const pendingDraftsState = $state({
  knowledge: [],
  goals: { long: '', shorts: ['', ''] },
  // TICKET-0107 (E1): the generator's carrure (-1..2), sent as the create
  // body's `carrure`; the server makes it the NPC's physical skill row.
  carrure: null,
  // TICKET-0124 (BRIEF-0124-I, C-14): the draft's world block as the server
  // resolved it (draft_world.py) -- each list item carries `checked`; the
  // create sends the checked ones (worldExtrasForCreate).
  world: { states: [], links: [], sameAs: null, toCreate: [] },
});

export function resetPendingDrafts() {
  pendingDraftsState.knowledge = [];
  pendingDraftsState.goals = { long: '', shorts: ['', ''] };
  pendingDraftsState.carrure = null;
  pendingDraftsState.world = { states: [], links: [], sameAs: null, toCreate: [] };
}

/** The create body's `states`, `relations` and `germs` (C-09), from the
 *  checked items only; a link without a type is not sent. */
export function worldExtrasForCreate() {
  const w = pendingDraftsState.world;
  return {
    states: w.states.filter((s) => s.checked).map((s) => ({ key: s.key, value: s.value })),
    relations: w.links
      .filter((l) => l.checked && (l.type || '').trim())
      .map((l) => ({ other_entity_id: l.entity_id, type: l.type.trim(), notes: l.note || null })),
    germs: w.toCreate
      .filter((g) => g.checked)
      .map((g) => ({ name: g.name, entity_type: g.entity_type, concept: g.concept, link_type: g.link_type })),
  };
}

export function carrureForCreate() {
  return pendingDraftsState.carrure;
}

export function knowledgeForCreate() {
  return pendingDraftsState.knowledge.filter((k) => k.content && k.content.trim());
}

export function goalsForCreate() {
  const entries = [];
  const g = pendingDraftsState.goals;
  if (g.long.trim()) entries.push({ description: g.long.trim(), horizon: 'long' });
  for (const s of g.shorts) {
    if (s && s.trim()) entries.push({ description: s.trim(), horizon: 'short' });
  }
  return entries;
}
