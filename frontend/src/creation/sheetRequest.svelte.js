/* TICKET-0059 (BRIEF-0059-c). One shared request/refresh/status cycle,
   replacing authorRelationRequest and authorKnowledgeRequest (index.html,
   now deleted) -- the two were line-for-line the same body against
   different paths. Does not write DOM for the row list itself: the legacy
   versions ended with
   document.getElementById('author-relations'/'author-knowledge').innerHTML
   = ...; this hands the refreshed detail to the caller's onSaved (Sheet.svelte's
   own flushSync(enterViewMode) prop, same as every other sub-editor) and
   lets reactivity render it.

   onSaved is invoked, and only THEN is the status line written -- Sheet.svelte's
   header-sync $effect clears #author-status on every 'view' re-render, and
   flushSync forces that effect to run synchronously as part of onSaved's own
   call; writing 'Saved.' before onSaved would be clobbered by it (the exact
   ordering submitEntity's own comment documents). PricingEditor/DoorsEditor/
   GeometryEditor/SubcultureEditor all call onSaved(data) before their own
   status write for the same reason.

   The status line (#author-status) is Sheet.svelte's own shared header
   element, reached via legacyDoc exactly as those components already do --
   not a new channel. */

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({ detail: res.statusText }));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

export async function sheetRequest(legacyDoc, entityId, path, method, body, onSaved) {
  const statusEl = legacyDoc.getElementById('author-status');
  try {
    const opts = { method };
    if (body !== null) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = body;
    }
    await api(path, opts);
    const detail = await api(`/api/entities/${encodeURIComponent(entityId)}`);
    onSaved(detail);
    if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Saved.'; }
    return detail;
  } catch (e) {
    if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    return null;
  }
}
