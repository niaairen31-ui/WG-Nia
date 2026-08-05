<script>
  /* TICKET-0059 (BRIEF-0059-h commit 4). Faithful port of the Registre tab
     (schema v1.31, BRIEF-18) -- _registreWorldReset/
     _registrePopulateEntityFilter/authorAddLedgerEntry/
     registreToggleAddForm/loadRegistre/_registreRenderTable (index.html,
     now deleted). Global journal, read-only in the sense that no row is
     ever edited or deleted here (History is sacred: the ledger is
     append-only by design) -- authorAddLedgerEntry only appends.

     authorAddLedgerEntry is Registre-owned despite the `author` prefix
     (RECON-0059-a M2 / SUPPLEMENT Amendment 8): its sole caller is this
     tab's own add-form button.

     World reset is driven by serverState.worldId (the -d rule); since
     loader: null now, this same effect does the initial load too,
     replacing the legacy loader/onWorldSwitch pair. The session-id filter
     keeps its oninput-triggered refetch on every keystroke (preserved
     verbatim, not debounced -- a deliberate behaviour, per the brief).

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { serverState } from '../lib/serverState.svelte.js';

  let entities = $state([]);   // {id, name, type}[] -- fetched once per world
  let entitiesLoaded = false;

  let filterEntity = $state('');
  let filterSession = $state('');

  let rows = $state(null); // null = loading
  let loadError = $state('');

  let addFormOpen = $state(false);
  let fEntity = $state('');
  let fAmount = $state('');
  let fCounterparty = $state('');
  let fSource = $state('creator');
  let fReason = $state('');
  let addStatus = $state('');

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  async function populateEntityFilter() {
    if (entitiesLoaded) return;
    try {
      entities = await api('/api/entities');
      entitiesLoaded = true;
    } catch (_err) { /* filter still usable without the entity list */ }
  }

  function entityLabel(id) {
    const e = entities.find((x) => x.id === id);
    return e ? `${e.name} (${e.type})` : shortId(id);
  }

  async function fetchLedger(entityId, sessionId) {
    await populateEntityFilter();
    rows = null;
    loadError = '';
    const params = new URLSearchParams();
    if (entityId) params.set('entity_id', entityId);
    if (sessionId) params.set('session_id', sessionId);
    try {
      rows = await api('/api/ledger' + (params.toString() ? '?' + params.toString() : ''));
    } catch (e) {
      loadError = e.message;
      rows = [];
    }
  }

  export async function loadRegistre() {
    await fetchLedger(filterEntity, filterSession.trim());
  }

  export function primaryAction() {
    addFormOpen = !addFormOpen;
  }

  async function addLedgerEntry() {
    const amount = parseInt(fAmount, 10);
    if (!fEntity) { addStatus = 'Entité requise.'; return; }
    if (!fAmount || isNaN(amount) || amount === 0) { addStatus = 'Montant non-nul requis.'; return; }
    addStatus = '…';
    try {
      await api('/api/ledger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_id: fEntity,
          amount,
          counterparty_id: fCounterparty || null,
          reason: fReason.trim() || null,
          source_type: fSource,
        }),
      });
      fAmount = '';
      fReason = '';
      addStatus = 'Ligne ajoutée.';
      addFormOpen = false;
      await loadRegistre();
    } catch (e) {
      addStatus = e.message;
    }
  }

  function shortId(id) { return id ? id.slice(0, 8) + '…' : ''; }

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  }

  $effect(() => {
    void serverState.worldId;
    entitiesLoaded = false;
    filterEntity = '';
    filterSession = '';
    addFormOpen = false;
    addStatus = '';
    // Explicit '' args here, not the loadRegistre wrapper -- that wrapper
    // reads filterEntity/filterSession, and effect_self_write.py forbids
    // reading a $state binding this same body just assigned, even
    // transitively through a called function. The reset-to-empty intent
    // is identical either way.
    fetchLedger('', '');
  });
</script>

<div class="queue-panel">
  <div class="panel-head">
    <h2>Registre</h2>
    <select bind:value={filterEntity} onchange={loadRegistre} style="max-width:220px">
      <option value="">Toutes les entités</option>
      {#each entities as e (e.id)}
        <option value={e.id}>{e.name} ({e.type})</option>
      {/each}
    </select>
    <input type="text" placeholder="session_id (optionnel)" bind:value={filterSession}
           oninput={loadRegistre} style="max-width:200px">
    <button class="btn-icon" onclick={loadRegistre} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if rows === null}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else if loadError}
      <div class="empty">{loadError}</div>
    {:else if rows.length === 0}
      <div class="empty">Aucune ligne dans le registre.</div>
    {:else}
      <div class="row-table">
        {#each rows as r}
          <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
            <span style="color:var(--muted); font-size:12px; min-width:120px;">{fmtDate(r.created_at)}</span>
            <span style="min-width:140px; font-weight:600;">{entityLabel(r.entity_id)}</span>
            <span style="font-weight:700; color:{r.amount >= 0 ? 'var(--accent)' : 'var(--danger, #c44)'};">{r.amount >= 0 ? '+' : ''}{r.amount}</span>
            <span style="color:var(--muted); font-size:12px; min-width:140px;">{r.counterparty_id ? entityLabel(r.counterparty_id) : ''}</span>
            <span style="font-size:12px; flex:1; min-width:160px;">{r.reason || ''}</span>
            <span class="badge b-other">{r.source_type || ''}</span>
            <span style="color:var(--muted); font-size:11px;">{r.session_id ? shortId(r.session_id) : ''}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
  {#if addFormOpen}
    <div class="field-section" style="border-top:1px solid var(--border); margin-top:8px; padding-top:8px;">
      <div class="field-section-title">Nouvelle ligne (crédit / débit)</div>
      <div class="field-grid">
        <div class="field-row">
          <label for="registre-f-entity">Entité *</label>
          <select id="registre-f-entity" bind:value={fEntity}>
            <option value="">—</option>
            {#each entities as e (e.id)}
              <option value={e.id}>{e.name} ({e.type})</option>
            {/each}
          </select>
        </div>
        <div class="field-row">
          <label for="registre-f-amount">Montant (+ crédit / − débit) *</label>
          <input type="number" id="registre-f-amount" placeholder="ex : 100 ou -15" bind:value={fAmount}>
        </div>
        <div class="field-row">
          <label for="registre-f-counterparty">Contrepartie (optionnel)</label>
          <select id="registre-f-counterparty" bind:value={fCounterparty}>
            <option value="">—</option>
            {#each entities as e (e.id)}
              <option value={e.id}>{e.name} ({e.type})</option>
            {/each}
          </select>
        </div>
        <div class="field-row">
          <label for="registre-f-source">source_type</label>
          <select id="registre-f-source" bind:value={fSource}>
            <option value="creator">creator</option>
            <option value="correction">correction</option>
          </select>
        </div>
        <div class="field-row" style="grid-column:1/-1">
          <label for="registre-f-reason">Reason</label>
          <input type="text" id="registre-f-reason" placeholder="ex : pécule de départ" bind:value={fReason}>
        </div>
      </div>
      <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
        <button class="btn-send" onclick={addLedgerEntry}>+ Ajouter la ligne</button>
        <span style="font-size:12px; color:var(--muted)">{addStatus}</span>
      </div>
    </div>
  {/if}
</div>
