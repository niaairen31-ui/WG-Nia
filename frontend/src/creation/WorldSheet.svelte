<script>
  /* TICKET-0124 (BRIEF-0124-J, W1). The « Monde » page: the active world's
     name, description, tone and fundamental laws, read with GET
     /api/worlds/{id} and saved with PUT /api/worlds/{id} (C-02) -- the laws
     every generator's premise carries (world_premise.py). Reloaded whenever
     the active world changes. Its CREATION_ISLANDS entry declares origin
     'new'. No dialog: the outcome shows on the status line. */
  import { serverState, refreshServerState } from '../lib/serverState.svelte.js';

  let name = $state('');
  let description = $state('');
  let tone = $state('');
  let laws = $state([]);
  let status = $state('');
  let loaded = $state(false);
  let loadSeq = 0;

  async function load(worldId) {
    const seq = ++loadSeq;
    loaded = false;
    status = '';
    if (!worldId) return;
    try {
      const res = await fetch(`/api/worlds/${encodeURIComponent(worldId)}`);
      if (!res.ok) throw new Error(`GET /api/worlds/${worldId} -> ${res.status}`);
      const world = await res.json();
      if (seq !== loadSeq) return;
      name = world.name ?? '';
      description = world.description ?? '';
      tone = world.tone ?? '';
      laws = [...(world.laws ?? [])];
      loaded = true;
    } catch (e) {
      if (seq === loadSeq) status = `Erreur : ${e.message}`;
    }
  }

  $effect(() => {
    load(serverState.worldId);
  });

  function moveLaw(i, delta) {
    const j = i + delta;
    if (j < 0 || j >= laws.length) return;
    const next = [...laws];
    [next[i], next[j]] = [next[j], next[i]];
    laws = next;
  }

  function removeLaw(i) {
    laws = laws.filter((_, k) => k !== i);
  }

  async function save() {
    const worldId = serverState.worldId;
    if (!worldId) return;
    status = '…';
    try {
      const res = await fetch(`/api/worlds/${encodeURIComponent(worldId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, tone, laws: laws.map((l) => l.trim()).filter(Boolean) }),
      });
      if (!res.ok) {
        let msg = `PUT /api/worlds/${worldId} -> ${res.status}`;
        try {
          const body = await res.json();
          if (body && typeof body.detail === 'string') msg = body.detail;
        } catch (_err) {
          // response body wasn't JSON -- keep the status-based message
        }
        throw new Error(msg);
      }
      const world = await res.json();
      laws = [...(world.laws ?? [])];
      await refreshServerState();
      status = 'Enregistré.';
    } catch (e) {
      status = `Erreur : ${e.message}`;
    }
  }
</script>

<div style="padding:16px 20px; max-width:860px">
  {#if !serverState.worldId}
    <div class="empty">Aucun monde actif.</div>
  {:else if !loaded}
    <div class="empty">{status || '…'}</div>
  {:else}
    <div class="field-grid">
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-sheet-name">Nom *</label>
        <input type="text" id="world-sheet-name" bind:value={name}>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-sheet-description">Contexte du monde</label>
        <textarea id="world-sheet-description" rows="4" bind:value={description}></textarea>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <label for="world-sheet-tone">Ton et style</label>
        <textarea id="world-sheet-tone" rows="3" placeholder="Registre, genre, conventions de noms…" bind:value={tone}></textarea>
      </div>
      <div class="field-row" style="grid-column:1/-1">
        <span>Lois fondamentales — vraies partout, connues de tous</span>
        {#each laws as _law, i (i)}
          <div style="display:flex; gap:4px; align-items:center; margin-top:4px">
            <input type="text" style="flex:1" bind:value={laws[i]}>
            <button class="btn-ghost" disabled={i === 0} onclick={() => moveLaw(i, -1)} title="Monter">↑</button>
            <button class="btn-ghost" disabled={i === laws.length - 1} onclick={() => moveLaw(i, 1)} title="Descendre">↓</button>
            <button class="btn-ghost" onclick={() => removeLaw(i)} title="Retirer">✕</button>
          </div>
        {/each}
        <button class="btn-ghost" style="margin-top:6px; align-self:flex-start" onclick={() => { laws = [...laws, '']; }}>+ Ajouter une loi</button>
      </div>
    </div>
    <div style="display:flex; gap:8px; align-items:center; margin-top:12px">
      <button class="btn-send" onclick={save}>Enregistrer</button>
      <span style="font-size:12px; color:{status.startsWith('Erreur') ? 'var(--red)' : 'var(--muted)'}">{status}</span>
    </div>
  {/if}
</div>
