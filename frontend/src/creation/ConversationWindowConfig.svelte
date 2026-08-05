<script>
  /* TICKET-0059 (BRIEF-0059-i commit 1). Faithful port of cwLoadConfig/
     _cwRenderConfig/cwPatchField (index.html, now deleted) -- the
     conversation-window config panel.

     TICKET-0050 (BRIEF-0050-e) -- per-active-world config, edited here (N2)
     beside conversation_summary until a dedicated world-configuration
     surface exists (named deferral D-0050).

     Child component of Prompts.svelte, not a second island (one island per
     container) -- Prompts.svelte holds a `bind:this` reference and calls
     this component's exported loadConfig() whenever ITS OWN load fires
     (initial mount, world switch, manual refresh), preserving the legacy
     coupling where promptsLoadList() called cwLoadConfig() every time.

     Relational-only: each field is PATCHed individually to
     /api/conversation-window-config -- no JSON blob (json_ui_boundary).
     cwPatchField's write cadence (one PATCH per field change, no debounce)
     is reproduced verbatim -- Scope OUT forbids "improving" it.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */

  let config = $state(null); // null = loading
  let loadError = $state('');
  let patchError = $state('');

  async function api(path, options) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  export async function loadConfig() {
    config = null;
    loadError = '';
    try {
      config = await api('/api/conversation-window-config');
    } catch (e) {
      loadError = e.message;
    }
  }

  async function patchField(field, value) {
    patchError = '';
    const body = {};
    body[field] = (field === 'summary_enabled') ? value : parseInt(value, 10);
    try {
      config = await api('/api/conversation-window-config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    } catch (e) {
      patchError = e.message;
    }
  }
</script>

<div class="queue-panel" id="cw-config-panel">
  <div class="panel-head">
    <h2>Fenêtre de conversation</h2>
    <button class="btn-icon" onclick={loadConfig} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    {#if config === null}
      {#if loadError}
        <div class="empty">{loadError}</div>
      {:else}
        <div class="empty"><span class="spin">⟳</span></div>
      {/if}
    {:else}
      <div style="font-size:12px; color:var(--muted); margin-bottom:8px;">
        Monde actif : <b>{config.world_name}</b>
      </div>
      <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-end;">
        <label style="display:flex; flex-direction:column; gap:2px; font-size:12px;">
          Budget de mots
          <input type="number" min="1" value={config.word_budget}
                 onchange={(e) => patchField('word_budget', e.target.value)} style="width:100px;">
        </label>
        <label style="display:flex; flex-direction:column; gap:2px; font-size:12px;">
          Tours verbatim (K)
          <input type="number" min="1" value={config.verbatim_turns}
                 onchange={(e) => patchField('verbatim_turns', e.target.value)} style="width:100px;">
        </label>
        <label style="display:flex; align-items:center; gap:6px; font-size:12px;">
          <input type="checkbox" checked={config.summary_enabled}
                 onchange={(e) => patchField('summary_enabled', e.target.checked)}>
          Résumé activé
        </label>
      </div>
      <div style="color:#c33; font-size:12px; margin-top:6px;">{patchError}</div>
    {/if}
  </div>
</div>
