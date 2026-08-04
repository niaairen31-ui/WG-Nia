/* TICKET-0059 (BRIEF-0059-c, generalized BRIEF-0059-d). One shared request/
   reload/status cycle, replacing authorRelationRequest/authorKnowledgeRequest/
   authorGoalRequest (index.html, now deleted) -- all three were line-for-line
   the same body against different paths and different refetch targets. Does
   not write DOM itself: the legacy versions ended with an innerHTML write
   into their own container; `reload` is a caller-supplied closure that does
   whatever refetch-and-apply its own data needs (RelationsEditor/
   KnowledgeEditor refetch the whole entity and hand it to Sheet.svelte's
   onSaved/enterViewMode prop; goalsPanel.svelte.js's loadGoals refetches
   goals+agendas and assigns straight to its own module state) -- BRIEF-0059-d
   parameterized the original entity-refetch-only helper onto this shape
   rather than forking a third implementation for goals' different refetch
   target (`/api/entities/{id}/goals` + `/api/agendas`, not the whole entity).

   `reload` is awaited, and only THEN is the status line written --
   Sheet.svelte's header-sync $effect clears #author-status on every 'view'
   re-render, and a caller's own flushSync(enterViewMode) (inside its reload
   closure) forces that effect to run synchronously; writing 'Saved.' before
   reload would be clobbered by it (the exact ordering submitEntity's own
   comment documents, and PricingEditor/DoorsEditor/GeometryEditor/
   SubcultureEditor already call onSaved(data) before their own status write
   for the same reason).

   The status line (#author-status) is Sheet.svelte's own shared header
   element, reached via legacyDoc exactly as those components already do --
   not a new channel. `api` is exported so callers can build their own
   `reload` closures (an entity refetch, a goals+agendas refetch, ...)
   without each re-implementing fetch/error handling. */

export async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export async function sheetRequest(legacyDoc, path, method, body, reload) {
  const statusEl = legacyDoc.getElementById('author-status');
  try {
    const opts = { method };
    if (body !== null) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = body;
    }
    await api(path, opts);
    await reload();
    if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Saved.'; }
    return true;
  } catch (e) {
    if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    return false;
  }
}
