<script>
  /* TICKET-0059 (BRIEF-0059-i commit 1). Faithful port of the Prompts tab --
     prompts.svelte.js's own header lists the ported functions. Rendering +
     the dirty-guard call sites live here; prompts.svelte.js holds the
     non-render state and API calls. ConversationWindowConfig.svelte is a
     CHILD of this component (one island per container, lock I1) -- its
     `#cw-config-panel` renders above the Prompts panel, same position as
     the legacy markup, and its loadConfig() is called from this
     component's own reload() so the "child loads when the parent loads"
     coupling survives the port intact.

     Highlighted {token} spans render as real <mark> markup over segments
     from prompts.svelte.js's highlightSegments(), never {@html} -- no XSS
     sink, and no need for an esc() import since every other value here is
     plain Svelte text interpolation (auto-escaped).

     World reset is driven by serverState.worldId (the -d rule every
     migrated island follows) -- since loader: null now, this same effect
     calls prompts.svelte.js's worldReset() for both the initial mount and
     every world switch (which itself calls loadList(), which calls cw's
     loadConfig()), replacing the legacy loader/onWorldSwitch/forced-
     showCreationSubTab three-times-over refetch with one path. The
     refresh icon calls loadList() directly instead (matching the legacy
     refresh button, which called promptsLoadList() and not
     _promptsWorldReset()).

     No draft-persistence doctrine (index.html's former module comment,
     BRIEF-0011-b): nothing on this surface writes to storage, and nothing
     survives a reload or a prompt/world switch -- commit 2 carries this
     forward into the edit-mode state it introduces.

     Cross-surface touch (BRIEF-0059-i, not otherwise in scope): the
     Observation lane's (TICKET-0051) observationOpenPrompt used to call
     promptsLoadList/promptsSelectDetail directly; -i deletes both, so it
     now dispatches 'creation:open-prompt' on the legacy document instead.
     See the pendingOpenId/listReady block below for the listener.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { serverState } from '../lib/serverState.svelte.js';
  import ConversationWindowConfig from './ConversationWindowConfig.svelte';
  import {
    promptsState, loadList, worldReset, selectDetail, changeModel, extractTokens, highlightSegments,
  } from './prompts.svelte.js';

  let { legacyDoc } = $props();

  let cwRef;
  let detailBodyEl;
  let modelSelectValue = $state('');

  function reload() {
    loadList(() => cwRef?.loadConfig());
  }

  // Observation lane cross-link (index.html's observationOpenPrompt,
  // TICKET-0051) -- a one-way CustomEvent carrying an intent, not a
  // command. Registered here at component init (synchronous, runs during
  // mount()) rather than inside an $effect, so the listener is live before
  // observationOpenPrompt's synchronous dispatchEvent call that follows
  // showCreationSubTab('prompts') -- an $effect would still be pending at
  // that point. `listReady` distinguishes "no load has settled yet" (cold
  // mount: wait for doWorldReset's own load to finish) from "already
  // loaded" (warm re-navigation: apply immediately) -- usages.length can't
  // serve as that signal, since a world with zero prompt templates is a
  // legitimate settled-empty state, not an unsettled one.
  let pendingOpenId = $state(null);
  let listReady = false;

  legacyDoc.addEventListener('creation:open-prompt', (ev) => {
    pendingOpenId = ev.detail.templateId;
    if (listReady) applyPendingOpen();
  });

  function applyPendingOpen() {
    if (pendingOpenId === null) return;
    const id = pendingOpenId;
    pendingOpenId = null;
    onSelectPrompt(id);
  }

  async function doWorldReset() {
    listReady = false;
    await worldReset(() => cwRef?.loadConfig());
    listReady = true;
    applyPendingOpen();
  }

  $effect(() => {
    void serverState.worldId;
    doWorldReset();
  });

  $effect(() => {
    modelSelectValue = promptsState.currentDetail?.model || '';
  });

  function usagesBySurface(surface) {
    return promptsState.usages.filter((u) => (u.surface === surface) || (surface === 'authoring' && u.surface !== 'play'));
  }

  function modelAbsent(model) {
    return !!model && !!promptsState.ollamaModels && !promptsState.ollamaModels.includes(model);
  }

  // The pending-open path (applyPendingOpen) also routes through this same
  // function -- once commit 2 adds the X1 dirty guard to selectDetail, the
  // Observation-lane cross-link inherits it automatically, with nothing to
  // bypass, per the same principle as every other selectDetail call site.
  async function onSelectPrompt(promptId) {
    await selectDetail(promptId);
    detailBodyEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function onModelChange(promptId) {
    const prevValue = promptsState.currentDetail?.model || '';
    promptsState.modelError = '';
    try {
      await changeModel(promptId, modelSelectValue);
    } catch (e) {
      promptsState.modelError = e.message;
      modelSelectValue = prevValue;
    }
  }

  function driftTokens(d) {
    const declared = new Set(Array.isArray(d.variables) ? d.variables : []);
    const actual = new Set([...extractTokens(d.system_prompt), ...extractTokens(d.user_template)]);
    return {
      missingFromDeclared: [...actual].filter((t) => !declared.has(t)),
      missingFromText: [...declared].filter((t) => !actual.has(t)),
    };
  }
</script>

<ConversationWindowConfig bind:this={cwRef} />

<div class="queue-panel">
  <div class="panel-head">
    <h2>Prompts</h2>
    <button class="btn-icon" onclick={reload} title="Rafraîchir">↻</button>
  </div>
  <div class="queue-body">
    <div>
      {#if promptsState.usages.length === 0 && promptsState.listError}
        <div class="empty">{promptsState.listError}</div>
      {:else if promptsState.usages.length === 0}
        <div class="empty">Aucun prompt enregistré.</div>
      {:else}
        {#each ['play', 'authoring'] as surface}
          {@const rows = usagesBySurface(surface)}
          {#if rows.length}
            <div class="field-section-title" style="margin-top:10px">{surface === 'play' ? 'Play' : 'Création'}</div>
            <div class="row-table">
              {#each rows as u}
                <div class="row-card" style="gap:6px;">
                  <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px;">
                    <span style="font-weight:700;">{u.usage}</span>
                    <span class="badge b-other" title="Modèle effectif pour le monde actif">{u.effective_model || '—'}</span>
                  </div>
                  <div class="row-table">
                    {#each (u.rows || []) as r}
                      <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between;
                                                    flex-wrap:wrap; gap:6px; cursor:pointer; {r.id === promptsState.selectedId ? 'border-color:var(--accent)' : ''}"
                           onclick={() => onSelectPrompt(r.id)}>
                        <span style="font-weight:600; min-width:140px;">{r.name}</span>
                        <span class="badge b-other">v{r.version}</span>
                        <span class="badge {r.is_active ? 'b-other' : ''}" style="{r.is_active ? '' : 'opacity:.5'}">{r.is_active ? 'actif' : 'inactif'}</span>
                        <span class="badge b-other">{r.world_id ? 'monde' : 'global'}</span>
                        {#if r.id === u.effective_id}
                          <span class="badge b-other" style="border-color:var(--accent); color:var(--accent)">effectif</span>
                        {/if}
                        {#if r.model}
                          <span class="badge b-other" title="override">{r.model}</span>
                        {/if}
                        {#if modelAbsent(r.model)}
                          <span class="badge b-other" style="border-color:#c33; color:#c33;" title="Ce modèle n'est plus installé dans Ollama">⚠ modèle absent</span>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        {/each}
      {/if}
    </div>
    <div bind:this={detailBodyEl} style="border-top:1px solid var(--border); padding-top:12px;">
      {#if !promptsState.selectedId}
        <div class="empty">Sélectionnez un prompt dans la liste ci-dessus.</div>
      {:else if promptsState.detailError}
        <div class="empty">{promptsState.detailError}</div>
      {:else if !promptsState.currentDetail}
        <div class="empty"><span class="spin">⟳</span></div>
      {:else}
        {@const d = promptsState.currentDetail}
        {@const drift = driftTokens(d)}
        <div class="field-section-title">{d.name} <span style="font-weight:400; color:var(--muted)">({d.usage})</span></div>
        <div style="font-size:12px; color:var(--muted); margin-bottom:8px;">
          v{d.version} · {d.is_active ? 'actif' : 'inactif'} · {d.world_id ? 'monde' : 'global'} ·
          {#if d.is_effective}<b style="color:var(--accent)">effectif</b>{:else}masqué par {d.shadowed_by ? d.shadowed_by.slice(0, 8) + '…' : ''}{/if}
        </div>
        <div class="field-section-title">Modèle</div>
        {#if promptsState.ollamaError}
          <div class="empty" style="text-align:left; border:1px solid var(--border); border-radius:var(--radius); padding:8px; margin-bottom:8px; color:#c33;">
            ⚠ {promptsState.ollamaError}
          </div>
          <div style="font-size:12px; color:var(--muted); margin-bottom:8px;">
            modèle effectif : <b>{d.effective_model}</b>{d.model ? ` (override : ${d.model})` : ''}
          </div>
        {:else}
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
            <select bind:value={modelSelectValue} onchange={() => onModelChange(d.id)}>
              <option value="">Défaut ({d.default_model || '—'})</option>
              {#each (promptsState.ollamaModels || []) as m}
                <option value={m}>{m}</option>
              {/each}
              {#if modelAbsent(d.model)}
                <option value={d.model} disabled>⚠ {d.model} (absent)</option>
              {/if}
            </select>
            {#if modelAbsent(d.model)}
              <span class="badge b-other" style="border-color:#c33; color:#c33;">⚠ modèle absent</span>
            {/if}
            <span style="color:#c33; font-size:12px;">{promptsState.modelError}</span>
          </div>
          <div style="font-size:12px; color:var(--muted); margin-bottom:8px;">
            modèle effectif : <b>{d.effective_model}</b>
          </div>
        {/if}
        <div class="field-section-title">Call sites</div>
        <ul style="margin:0 0 10px 18px; font-size:12px;">
          {#each (d.call_sites || []) as s}<li><code>{s}</code></li>{/each}
        </ul>
        <div style="display:flex; align-items:center; justify-content:space-between;">
          <div class="field-section-title" style="margin:0">System prompt</div>
        </div>
        <pre style="white-space:pre-wrap; font-size:12px; background:var(--card); border:1px solid var(--border);
                    border-radius:var(--radius); padding:8px; max-height:220px; overflow-y:auto;">{#each highlightSegments(d.system_prompt) as seg}{#if seg.isToken}<mark>{seg.text}</mark>{:else}{seg.text}{/if}{/each}</pre>
        <div class="field-section-title">User template</div>
        <pre style="white-space:pre-wrap; font-size:12px; background:var(--card); border:1px solid var(--border);
                    border-radius:var(--radius); padding:8px; max-height:220px; overflow-y:auto;">{#each highlightSegments(d.user_template) as seg}{#if seg.isToken}<mark>{seg.text}</mark>{:else}{seg.text}{/if}{/each}</pre>
        {#if drift.missingFromDeclared.length || drift.missingFromText.length}
          <div class="empty" style="text-align:left; border:1px solid var(--border); border-radius:var(--radius); padding:8px;">
            {#if drift.missingFromDeclared.length}
              <div>Présents dans le texte, absents de <code>variables</code> : {drift.missingFromDeclared.join(', ')}</div>
            {/if}
            {#if drift.missingFromText.length}
              <div>Déclarés dans <code>variables</code>, absents du texte : {drift.missingFromText.join(', ')}</div>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
