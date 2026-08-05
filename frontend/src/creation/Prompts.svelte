<script>
  /* TICKET-0059 (BRIEF-0059-i, all three commits). Faithful port of the
     Prompts tab -- prompts.svelte.js's own header lists the ported
     functions. Rendering + the dirty-guard call sites live here;
     prompts.svelte.js holds the non-render state and API calls.
     ConversationWindowConfig.svelte is a
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
     survives a reload or a prompt/world switch -- the edit-mode drafts
     commit 2 introduces are plain $state in prompts.svelte.js, never
     persisted, cleared by resetEditState on every prompt/world switch.

     The X1 dirty guard (confirmDiscard) lives inside worldReset/
     selectDetail/cancelEdit themselves (prompts.svelte.js), matching the
     legacy shape exactly -- and matching this tree's ACTUAL call sites,
     not the brief's prose (which named three more; verified false against
     this codebase, see prompts.svelte.js's header). changeModel and the
     history functions never called the guard in the legacy code and don't
     gain it here -- a faithful port reproduces the code, not a summary of
     it. Since applyPendingOpen (below) routes through the same
     selectDetail/onSelectPrompt path, the Observation-lane cross-link
     inherits the guard for free.

     History (V1) stays lazy: historyVersions is null (not fetched) until
     the "Historique" row is first expanded, cached until a save/restore
     invalidates it. The preview panel's entity selectors are fetched via
     an $effect keyed on promptsState.currentDetail (`untrack`-wrapped for
     everything past that one deliberate read -- see the same lesson
     worldReset's own effect already paid for above; reading
     creationState.playerCharIds unwrapped here would make THIS effect
     re-fire on an unrelated tab's entity-list refresh).

     Cross-surface touch (BRIEF-0059-i, not otherwise in scope): the
     Observation lane's (TICKET-0051) observationOpenPrompt used to call
     promptsLoadList/promptsSelectDetail directly; -i deletes both, so it
     now dispatches 'creation:open-prompt' on the legacy document instead.
     See the pendingOpenId/listReady block below for the listener.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { untrack } from 'svelte';
  import { serverState } from '../lib/serverState.svelte.js';
  import { creationState } from './state.svelte.js';
  import ConversationWindowConfig from './ConversationWindowConfig.svelte';
  import {
    promptsState, loadList, worldReset, selectDetail, changeModel, extractTokens, highlightSegments,
    enterEditMode, cancelEdit, editInput, saveEdit, undeclaredTokens,
    toggleHistory, selectHistoryVersion, restoreVersion,
    fetchPreviewEntities, runAssembledPreview,
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

  // untrack is load-bearing, not decorative: worldReset() calls
  // confirmDiscard(), which reads promptsState.editDirty synchronously
  // before its first await. Svelte's effect dependency tracking captures
  // ANY $state read that happens synchronously during an effect's run,
  // through arbitrarily deep synchronous call chains -- so without
  // untrack, this effect would ALSO subscribe to editDirty. saveEdit and
  // cancelEdit both write editDirty = false on success, which would then
  // re-fire this effect and re-run worldReset -> loadList, wiping
  // selectedId/currentDetail right after a save or cancel. Caught live:
  // saving an edit reset the whole pane to "no prompt selected".
  $effect(() => {
    void serverState.worldId;
    untrack(doWorldReset);
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

  function fmtDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  }

  let previewEntities = $state({ npcs: [], pcs: [] });
  let previewPcId = $state('');
  let previewNpcId = $state('');
  let previewOutput = $state(null); // null | { error } | { body }
  let previewLoading = $state(false);

  $effect(() => {
    const d = promptsState.currentDetail;
    untrack(() => {
      previewPcId = '';
      previewNpcId = '';
      previewOutput = null;
      if (d && d.dry_run_capable) {
        fetchPreviewEntities(creationState.playerCharIds).then((r) => { previewEntities = r; });
      } else {
        previewEntities = { npcs: [], pcs: [] };
      }
    });
  });

  async function onRunPreview(usage) {
    previewLoading = true;
    previewOutput = await runAssembledPreview(usage, previewPcId, previewNpcId);
    previewLoading = false;
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
        {#if promptsState.editMode}
          {@const undeclared = undeclaredTokens(d, promptsState.editDraftSystem, promptsState.editDraftUser)}
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div class="field-section-title" style="margin:0">System prompt</div>
          </div>
          <textarea rows="8" style="width:100%; font-size:12px; font-family:monospace;"
            value={promptsState.editDraftSystem}
            oninput={(e) => editInput('system', e.target.value)}></textarea>
          <div class="field-section-title">User template</div>
          <textarea rows="8" style="width:100%; font-size:12px; font-family:monospace;"
            value={promptsState.editDraftUser}
            oninput={(e) => editInput('user', e.target.value)}></textarea>
          <div class="field-row" style="margin-top:8px;">
            <label for="prompts-edit-note">Note (optionnel)</label>
            <input type="text" id="prompts-edit-note" value={promptsState.editDraftNote}
              oninput={(e) => editInput('note', e.target.value)}>
          </div>
          {#if undeclared.length}
            <div style="color:#c33; font-size:12px; margin-top:4px;">Sera rejeté : {undeclared.map((t) => '{' + t + '}').join(', ')}</div>
          {/if}
          {#if promptsState.saveError}
            <div style="color:#c33; font-size:12px; margin-top:6px;">{promptsState.saveError}</div>
          {/if}
          <div style="display:flex; gap:8px; align-items:center; margin-top:8px;">
            <button class="btn-send" onclick={() => saveEdit(d.id)}>Enregistrer</button>
            <button class="btn-end" onclick={cancelEdit}>Annuler</button>
          </div>
        {:else}
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div class="field-section-title" style="margin:0">System prompt</div>
            <button class="btn-send" onclick={enterEditMode}>Éditer</button>
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

        <div class="field-section-title" style="margin-top:14px; display:flex; align-items:center; justify-content:space-between; cursor:pointer;"
             onclick={() => toggleHistory(d.id)}>
          <span>Historique</span>
          <span style="font-weight:400; color:var(--muted); font-size:12px;">{promptsState.historyExpanded ? 'Masquer' : 'Afficher'}</span>
        </div>
        {#if promptsState.historyExpanded}
          {#if promptsState.historyError}
            <div class="empty" style="color:#c33;">{promptsState.historyError}</div>
          {:else if !promptsState.historyVersions}
            <div class="empty"><span class="spin">⟳</span></div>
          {:else if promptsState.historyVersions.length === 0}
            <div class="empty">Aucune version.</div>
          {:else}
            <div class="row-table" style="margin-top:6px;">
              {#each promptsState.historyVersions as v}
                <div class="row-card" style="flex-direction:row; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:6px; cursor:pointer;
                                              {v.version_number === promptsState.historySelectedVersion ? 'border-color:var(--accent)' : ''}"
                     onclick={() => selectHistoryVersion(d.id, v.version_number)}>
                  <span class="badge b-other">v{v.version_number}</span>
                  <span style="color:var(--muted); font-size:12px;">{fmtDate(v.created_at)}</span>
                  <span style="font-size:12px; flex:1;">{v.note || ''}</span>
                  {#if v.is_current}
                    <span class="badge b-other" style="border-color:var(--accent); color:var(--accent)">current</span>
                  {/if}
                </div>
              {/each}
            </div>
            {#if promptsState.historySelectedVersion != null}
              {#if !promptsState.historyVersionDetail}
                {#if promptsState.restoreError}
                  <div class="empty" style="color:#c33;">{promptsState.restoreError}</div>
                {:else}
                  <div class="empty"><span class="spin">⟳</span></div>
                {/if}
              {:else}
                {@const v = promptsState.historyVersionDetail}
                {@const nextVersion = d.version + 1}
                <div style="border-top:1px solid var(--border); margin-top:8px; padding-top:8px;">
                  <div class="field-section-title">v{v.version_number} · {fmtDate(v.created_at)}{v.note ? ` · ${v.note}` : ''}</div>
                  <pre style="white-space:pre-wrap; font-size:12px; background:var(--card); border:1px solid var(--border);
                              border-radius:var(--radius); padding:8px; max-height:180px; overflow-y:auto;">{#each highlightSegments(v.system_prompt) as seg}{#if seg.isToken}<mark>{seg.text}</mark>{:else}{seg.text}{/if}{/each}</pre>
                  <pre style="white-space:pre-wrap; font-size:12px; background:var(--card); border:1px solid var(--border);
                              border-radius:var(--radius); padding:8px; max-height:180px; overflow-y:auto;">{#each highlightSegments(v.user_template) as seg}{#if seg.isToken}<mark>{seg.text}</mark>{:else}{seg.text}{/if}{/each}</pre>
                  {#if !v.is_current}
                    <button class="btn-send" onclick={() => restoreVersion(d.id, v.version_number)}>Restore v{v.version_number} as new v{nextVersion}</button>
                  {/if}
                  {#if promptsState.restoreError}
                    <div style="color:#c33; font-size:12px; margin-top:6px;">{promptsState.restoreError}</div>
                  {/if}
                </div>
              {/if}
            {/if}
          {/if}
        {/if}

        {#if d.dry_run_capable}
          <div class="field-section-title" style="margin-top:10px">Preview assemblée</div>
          <div class="field-grid">
            {#if d.usage === 'npc_dialogue'}
              <div class="field-row">
                <label for="prompts-preview-npc">NPC</label>
                <select id="prompts-preview-npc" bind:value={previewNpcId}>
                  <option value="">—</option>
                  {#each previewEntities.npcs as e}<option value={e.id}>{e.name}</option>{/each}
                </select>
              </div>
              <div class="field-row">
                <label for="prompts-preview-pc">Interlocuteur (PJ)</label>
                <select id="prompts-preview-pc" bind:value={previewPcId}>
                  <option value="">—</option>
                  {#each previewEntities.pcs as e}<option value={e.id}>{e.name}</option>{/each}
                </select>
              </div>
            {:else if d.usage === 'player_narration'}
              <div class="field-row">
                <label for="prompts-preview-pc">Personnage joueur</label>
                <select id="prompts-preview-pc" bind:value={previewPcId}>
                  <option value="">—</option>
                  {#each previewEntities.pcs as e}<option value={e.id}>{e.name}</option>{/each}
                </select>
              </div>
            {/if}
          </div>
          <div style="margin:8px 0;">
            <button class="btn-send" onclick={() => onRunPreview(d.usage)}>Preview assemblée</button>
          </div>
          <div>
            {#if previewLoading}
              <div class="empty"><span class="spin">⟳</span></div>
            {:else if previewOutput?.error}
              <div class="empty">{previewOutput.error}</div>
            {:else if previewOutput?.body}
              <pre style="white-space:pre-wrap; font-size:12px; background:var(--card);
                border:1px solid var(--border); border-radius:var(--radius); padding:8px;
                max-height:340px; overflow-y:auto;">{previewOutput.body}</pre>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
