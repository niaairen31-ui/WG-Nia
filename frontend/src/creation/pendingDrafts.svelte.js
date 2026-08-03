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
});

export function resetPendingDrafts() {
  pendingDraftsState.knowledge = [];
  pendingDraftsState.goals = { long: '', shorts: ['', ''] };
}

export function knowledgeForCreate() {
  return pendingDraftsState.knowledge.filter((k) => k.subject && k.content);
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
