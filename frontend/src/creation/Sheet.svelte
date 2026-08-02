<script>
  /* TICKET-0058 (BRIEF-0058-f). The entity sheet -- the second island onto
     #creation-editor-area's shared shell (the first, EntityList.svelte, is
     BRIEF-0058-e), mounted into #author-main. Faithful port of
     authorRenderSheet/authorRenderField/authorReadField/_authorSaveSubmit
     (index.html, now deleted) -- the field engine every entity-archetype
     tab (npc/pj/lieux/factions/objets/runtime types) needs, plus the
     "Créations en attente" trigger path (generatePendingCreation).

     CORE ONLY (this brief's scope): render base+ext fields from the
     server-declared spec (GET /api/entity-types, unchanged), read them
     back, save via the existing creator-CRUD endpoint. Every sub-editor
     that hangs off the sheet (roles/subculture/geometry/doors/relations/
     knowledge/pending-knowledge/pending-goals/items/memberships/faction-
     roster/ledger/pricing/goals/disc-details -- brief -g) and the AI
     draft-generate panel (brief -h) stay legacy, unmigrated: this
     component renders the SAME placeholder skeleton authorRenderSheet
     always did (an empty spinner div for an async-loaded panel, or an
     immediate {@html} call into the still-legacy synchronous HTML
     generator for an inline one) and, after its own DOM update flushes,
     fires the same tail of legacy loader calls authorRenderSheet used to
     run inline -- via legacyCall (frontend/src/legacy/bridge.js), a
     generic passthrough to the legacy window. Every one of those legacy
     functions is completely unchanged: they still populate their target
     div by plain document.getElementById(id), which finds it exactly the
     same whether the div was created by an innerHTML write or by Svelte --
     both are real nodes in the same legacy document.

     Two tabs (`intrigues`, `evenements`) and one mode (`pj`'s create panel)
     never used authorRenderSheet at all -- they have their own bespoke,
     hand-rolled sheetRenderer/createPanel (renderAgendaSheet, renderEventSheet
     + evenementsRenderCreatePanel, pjRenderCreatePanel). Per RECON-SUPPLEMENT-
     0058's -f section, evenements stays bridged until brief -j (it depends on
     the field engine too -- see the 'creation:field-render'/'creation:field-
     read' listeners below); the other two are simply unmigrated legacy code
     that still needs somewhere safe to render inside this island's own mount
     root without tearing Svelte's DOM out from under it (RECON-0058-a M5).
     The answer is the SAME "stable leaf, legacy free to mutate its
     innerHTML" idiom the sub-editor placeholders already rely on, just
     sized to the whole container: #author-legacy-sheet-slot is an
     UNCONDITIONALLY rendered sibling of #author-core-sheet (never created/
     destroyed by an {#if}, only display:toggled), so a legacy renderer
     that targets it right after a synchronous 'creation:sheet-legacy-active'
     dispatch always finds it there -- no dependency on Svelte's own update
     timing (flushSync makes the toggle itself synchronous too, belt and
     braces).

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { flushSync, tick } from 'svelte';
  import { creationState } from './state.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import { legacyCall } from '../legacy/bridge.js';
  import { renderFieldHtml, readFieldValue } from './fields.js';
  import { locationTypeOptionLabel, openTemplateModalFor, promptLocationTypeClassification } from './locationType.js';
  import Field from './Field.svelte';
  import GeometryEditor from './GeometryEditor.svelte';
  import DoorsEditor from './DoorsEditor.svelte';
  import RolesEditor from './RolesEditor.svelte';
  import FactionRoster from './FactionRoster.svelte';
  import MembershipsPanel from './MembershipsPanel.svelte';
  import { loadFactionMembersPanel, draftRolesForCreate, resetDraftRoles, factionPanelState } from './factionPanel.svelte.js';
  import { subcultureDraftState, subcultureDraftForCreate, resetSubcultureDraft } from './subcultureDraft.svelte.js';
  import SubcultureEditor from './SubcultureEditor.svelte';
  import PricingEditor from './PricingEditor.svelte';
  import LedgerPanel from './LedgerPanel.svelte';
  import ItemsPanel from './ItemsPanel.svelte';

  let { legacyDoc } = $props();

  const GENERIC_TYPE_BY_TAB = { npc: 'character', pj: 'character', lieux: 'location', factions: 'faction', objets: 'item' };
  const EMPTY_BODY_BY_TAB = {
    intrigues: 'Sélectionnez une intrigue depuis la liste, ou créez-en une nouvelle.',
    evenements: 'Sélectionnez un événement depuis la liste, ou créez-en un nouveau.',
  };
  const EMPTY_TITLE_BY_TAB = {
    intrigues: 'Sélectionner une intrigue',
    evenements: 'Sélectionner un événement',
  };

  let registry = $state(null);

  async function api(path, options) {
    const res = await fetch(path, options);
    if (!res.ok) {
      let msg = `${path} -> ${res.status}`;
      try {
        const body = await res.json();
        if (body && typeof body.detail === 'string') msg = body.detail;
      } catch (_err) {
        // response body wasn't JSON -- keep the status-based message
      }
      throw new Error(msg);
    }
    return res.json();
  }

  async function loadRegistry() {
    try {
      registry = await api('/api/entity-types');
    } catch (e) {
      console.error('creation/Sheet:', e.message);
    }
  }

  // World switch (TICKET-0056 C3, mirrors Constructeur.svelte): the active
  // world is server-authoritative, so this island resets its own selection
  // and refetches its own registry copy reactively rather than being told
  // to by a legacy onWorldSwitch callback (RECON-0058-a M5).
  $effect(() => {
    void serverState.worldId;
    creationState.sheetMode = 'empty';
    creationState.sheetDetail = null;
    creationState.sheetIsNew = false;
    creationState.sheetType = null;
    loadRegistry();
  });

  // A runtime type created via Constructeur.svelte changes what GET
  // /api/entity-types returns without the world changing -- Constructeur
  // already dispatches this event so the legacy tab bar rebuilds
  // (refreshCreationTabs, index.html); Sheet.svelte's own registry copy
  // needs the same refresh, or a brand-new runtime type's sheet would try
  // to read registry.types[newSlug] before it exists.
  legacyDoc.addEventListener('creation:refresh-tabs', () => { loadRegistry(); });

  function resolveTypeForTab(tabKey) {
    return GENERIC_TYPE_BY_TAB[tabKey] || tabKey;
  }

  function enterCreateMode(type) {
    creationState.sheetMode = 'view';
    creationState.sheetIsNew = true;
    creationState.sheetType = type;
    creationState.sheetDetail = {};
  }

  function enterViewMode(detail, type) {
    creationState.sheetMode = 'view';
    creationState.sheetIsNew = false;
    creationState.sheetType = type;
    creationState.sheetDetail = detail;
  }

  /** Called by mount.js's _islandPrimaryAction('entitySheet') when the
   *  standard shell action band ("+ Nouveau") is clicked for a CORE
   *  entity-archetype tab -- pj/intrigues/evenements never route here
   *  (rule 11 pairing keeps their primaryAction legacy, paired with their
   *  own bespoke createPanel). Mirrors creationNewEntity's own draft reset
   *  (the plain "+ Nouveau" idiom every entity tab shared before this
   *  brief), via the same legacy helper so the two paths never drift. */
  export function primaryAction() {
    legacyCall('_authorResetCreateDrafts');
    resetDraftRoles();
    resetSubcultureDraft();
    enterCreateMode(resolveTypeForTab(creationState.activeTabKey));
  }

  legacyDoc.addEventListener('creation:sheet-reset', () => {
    flushSync(() => {
      creationState.sheetMode = 'empty';
      creationState.sheetDetail = null;
      creationState.sheetIsNew = false;
      creationState.sheetType = null;
    });
  });

  legacyDoc.addEventListener('creation:sheet-loading', () => {
    creationState.sheetMode = 'loading';
  });

  legacyDoc.addEventListener('creation:sheet-error', (ev) => {
    flushSync(() => {
      creationState.sheetMode = 'error';
      creationState.sheetErrorMessage = ev.detail.message;
    });
  });

  // authorSelectEntity dispatches this on fetch success for every tab whose
  // registry entry has no bespoke sheetRenderer (i.e. every core type);
  // authorPriceListMutate/authorSaveSubcultureRowsData/authorSaveGeometry/
  // authorSaveDoors (brief -g sub-editors, unmigrated) dispatch the same
  // event to refresh the sheet with their own PUT response, replacing their
  // former direct authorRenderSheet(detail, false, detail.type) call.
  legacyDoc.addEventListener('creation:sheet-detail', (ev) => {
    flushSync(() => { enterViewMode(ev.detail.detail, ev.detail.type); });
  });

  // generatePendingCreation (the "Créations en attente" card's generate
  // button, still legacy) dispatches this instead of the deleted
  // authorRenderSheet({}, true, entityType) -- flushSync so the DOM this
  // creates (author-f-name et al.) exists before generatePendingCreation's
  // own synchronous authorApply*Draft(result) call right after.
  legacyDoc.addEventListener('creation:sheet-create', (ev) => {
    flushSync(() => { enterCreateMode(ev.detail.type); });
  });

  // pj's createPanel, intrigues'/evenements' createPanel+sheetRenderer --
  // all still legacy (rule 11 pairing keeps them off the island-routed
  // primaryAction) -- dispatch this immediately before rendering their own
  // markup into #author-legacy-sheet-slot, so that node exists under
  // "legacy" display before their innerHTML write. creationNewEntity does
  // this for the create-panel path; authorSelectEntity does it for
  // entry.sheetRenderer (intrigues/evenements' view path).
  legacyDoc.addEventListener('creation:sheet-legacy-active', () => {
    flushSync(() => { creationState.sheetMode = 'legacy'; });
  });

  // #author-save-btn's onclick (creationSaveDispatch) dispatches this for
  // every tab with no saveHandler of its own -- evenements keeps its own
  // saveHandler (evenementsSave), never reaching here.
  legacyDoc.addEventListener('creation:sheet-save', () => { saveSheet(); });

  // evenements' still-legacy renderEventSheet/evenementsRenderCreatePanel/
  // evenementsSave/evenementsSubmitCreate reach the ported field engine
  // through these two events (via the small _creationRenderField/
  // _creationReadField wrappers in index.html) instead of the deleted
  // authorRenderField/authorReadField -- the "reverse-direction CustomEvent"
  // RECON-SUPPLEMENT-0058's -f section calls for. Both are synchronous:
  // dispatchEvent() doesn't return until this listener has set detail.html
  // (or detail.value/detail.error).
  legacyDoc.addEventListener('creation:field-render', (ev) => {
    ev.detail.html = renderFieldHtml(ev.detail.field, ev.detail.value, ev.detail.idPrefix, { entities: creationState.entities });
  });
  legacyDoc.addEventListener('creation:field-read', (ev) => {
    try {
      ev.detail.value = readFieldValue(legacyDoc, ev.detail.field, ev.detail.idPrefix);
    } catch (err) {
      ev.detail.error = err.message;
    }
  });

  // The room-batch generator (batchRenderManifestTable, index.html, still
  // legacy until brief -j) reaches the ported location-type helpers the
  // same reverse-bridge way -- BRIEF-0058-g family a.
  legacyDoc.addEventListener('creation:location-type-label', (ev) => {
    ev.detail.label = locationTypeOptionLabel(ev.detail.row);
  });
  legacyDoc.addEventListener('creation:open-location-type-modal', (ev) => {
    openTemplateModalFor(legacyDoc, ev.detail.fieldId, () => {});
  });

  // The AI faction-draft pre-fill (authorApplyFactionDraft, index.html,
  // still legacy -- brief -h) writes its proposed roles into
  // factionPanelState.draftRoles through this same reverse-bridge idiom,
  // since RolesEditor.svelte now owns #author-roles reactively and a raw
  // innerHTML write there would tear the mounted component out (RECON-0058-a
  // M5) -- BRIEF-0058-g family b.
  legacyDoc.addEventListener('creation:apply-faction-roles-draft', (ev) => {
    factionPanelState.draftRoles = ev.detail.rows;
  });

  // authorApplyLocationDraft's equivalent for subcultureDraftState.rows --
  // same idiom, BRIEF-0058-g family c.
  legacyDoc.addEventListener('creation:apply-subculture-draft', (ev) => {
    subcultureDraftState.rows = ev.detail.rows;
  });

  // Sibling header chrome (title/status/save/delete) lives OUTSIDE
  // #author-main -- authorRenderSheet always reached out to it too. Only
  // touched for 'empty'/'view': 'loading'/'error' leave it exactly as
  // authorSelectEntity's spinner/catch branches always did (untouched),
  // and 'legacy' is legacy code's own job (renderEventSheet et al. already
  // set these themselves, unchanged).
  $effect(() => {
    const mode = creationState.sheetMode;
    if (mode !== 'empty' && mode !== 'view') return;
    const titleEl = legacyDoc.getElementById('author-sheet-title');
    const statusEl = legacyDoc.getElementById('author-status');
    const saveBtn = legacyDoc.getElementById('author-save-btn');
    const deleteBtn = legacyDoc.getElementById('author-delete-btn');
    if (mode === 'empty') {
      if (titleEl) titleEl.textContent = EMPTY_TITLE_BY_TAB[creationState.activeTabKey] || 'Sélectionner une entité';
      if (statusEl) statusEl.textContent = '';
      if (saveBtn) saveBtn.style.display = 'none';
      if (deleteBtn) deleteBtn.style.display = 'none';
      return;
    }
    if (!registry) return;
    const type = creationState.sheetType;
    const typeInfo = registry.types[type];
    if (!typeInfo) return;
    if (titleEl) {
      titleEl.textContent = creationState.sheetIsNew
        ? `New ${typeInfo.label}`
        : `${creationState.sheetDetail.name} (${typeInfo.label})`;
    }
    if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = ''; }
    if (saveBtn) saveBtn.style.display = '';
    if (deleteBtn) deleteBtn.style.display = creationState.sheetIsNew ? 'none' : '';
  });

  // The tail authorRenderSheet always ran inline after building its HTML --
  // the async sub-editor loaders, unchanged, targeting the placeholder
  // spinner divs rendered below. tick() waits for Svelte's own DOM update
  // (the divs' creation) before these run their getElementById lookups.
  $effect(() => {
    if (creationState.sheetMode !== 'view' || creationState.sheetIsNew) return;
    const detail = creationState.sheetDetail;
    const type = creationState.sheetType;
    if (!detail || !detail.id) return;
    (async () => {
      await tick();
      if (type === 'character' && creationState.activeTabKey === 'npc') {
        legacyCall('authorLoadGoals', detail.id);
      }
      if (type === 'faction') {
        loadFactionMembersPanel(detail.id);
      }
      if (type === 'location') {
        legacyCall('authorLoadDiscDetails', detail.id);
      }
    })();
  });

  async function saveSheet() {
    if (!registry) return;
    const statusEl = legacyDoc.getElementById('author-status');
    const isNewSave = creationState.sheetIsNew;
    const type = isNewSave ? legacyDoc.getElementById('author-f-type').value : creationState.sheetType;

    const entityData = {};
    const extData = {};
    try {
      for (const field of registry.entity_base_fields) {
        entityData[field.name] = readFieldValue(legacyDoc, field, 'author-f');
      }
      for (const field of (registry.types[type].fields || [])) {
        extData[field.name] = readFieldValue(legacyDoc, field, 'author-x');
      }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = `Invalid JSON: ${e.message}`; }
      return;
    }
    if (isNewSave) entityData.type = type;

    if (type === 'location') {
      const chosenType = (extData.location_type || '').trim();
      if (chosenType) {
        const folded = chosenType.toLowerCase();
        const catalogRow = creationState.locationTypeCatalog.find((r) => r.name.toLowerCase() === folded);
        if (!catalogRow || catalogRow.classification == null) {
          promptLocationTypeClassification(legacyDoc, chosenType, () => submitEntity(isNewSave, type, entityData, extData));
          return;
        }
      }
    }

    await submitEntity(isNewSave, type, entityData, extData);
  }

  /** The actual write + dependent-draft POSTs -- ported _authorSaveSubmit
   *  verbatim, minus the roles/subculture/knowledge/goals DRAFT COLLECTION
   *  itself (brief -g/-h territory, still legacy globals): those are
   *  fetched via legacyCall right before, exactly as authorFactionRolesDraft/
   *  authorLocationSubcultureDraft/pendingDraftKnowledge/pendingDraftGoals
   *  were read in place before. */
  async function submitEntity(isNewSave, type, entityData, extData) {
    const statusEl = legacyDoc.getElementById('author-status');
    const rolesToCreate = (isNewSave && type === 'faction') ? draftRolesForCreate() : [];
    const subcultureRowsToCreate = (isNewSave && type === 'location') ? subcultureDraftForCreate() : [];
    const knowledgeToCreate = (isNewSave && type === 'character') ? legacyCall('_syncPendingKnowledgeFromDom') : [];
    const goalsToCreate = (isNewSave && type === 'character') ? legacyCall('_syncPendingGoalsFromDom') : [];
    const mutationId = isNewSave ? legacyCall('_authorGetPendingCreationMutationId') : null;

    try {
      const body = JSON.stringify({
        entity: entityData,
        extension: extData,
        ...(isNewSave && mutationId ? { mutation_id: mutationId } : {}),
      });
      let detail = isNewSave
        ? await api('/api/entities', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
        : await api(`/api/entities/${encodeURIComponent(creationState.sheetDetail.id)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body });

      if (isNewSave && knowledgeToCreate.length) {
        for (const row of knowledgeToCreate) {
          await api(`/api/entities/${encodeURIComponent(detail.id)}/knowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              subject: row.subject, level: row.level, source: null, share_threshold: 50,
              is_incorrect: false, is_secret: true, content: row.content,
            }),
          });
        }
        detail = await api(`/api/entities/${encodeURIComponent(detail.id)}`);
      }

      if (isNewSave && goalsToCreate.length) {
        for (const goal of goalsToCreate) {
          await api(`/api/entities/${encodeURIComponent(detail.id)}/goals`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(goal),
          });
        }
      }

      if (isNewSave && rolesToCreate.length) {
        for (const row of rolesToCreate) {
          await api(`/api/factions/${encodeURIComponent(detail.id)}/roles`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(row),
          });
        }
      }

      if (isNewSave && subcultureRowsToCreate.length) {
        await api(`/api/entities/${encodeURIComponent(detail.id)}/subculture`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rows: subcultureRowsToCreate }),
        });
        detail = await api(`/api/entities/${encodeURIComponent(detail.id)}`);
      }

      if (isNewSave && mutationId) {
        legacyCall('_authorConsumePendingCreationMutationId');
      }
      if (isNewSave) {
        legacyCall('_authorClearCreateDrafts');
        resetDraftRoles();
        resetSubcultureDraft();
      }

      legacyCall('creationRefreshList');
      legacyCall('_authorNotifySaved', detail.id, detail.type);
      // flushSync: the header-sync $effect below clears #author-status on
      // every 'view' render (matching authorRenderSheet's own unconditional
      // reset) -- without this, its microtask-scheduled run would fire
      // AFTER the 'Saved.' write two lines down and clobber it. Forcing it
      // to run synchronously, right here, restores the same ordering
      // guarantee the original code's single synchronous call stack had.
      flushSync(() => { enterViewMode(detail, detail.type); });
      const st = legacyDoc.getElementById('author-status');
      if (st) { st.className = 'author-status ok'; st.textContent = 'Saved.'; }
      if (creationState.activeTabKey === 'lieux') {
        legacyDoc.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'lieux' } }));
      }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
  }

  const mode = $derived(creationState.sheetMode);
  const isNew = $derived(creationState.sheetIsNew);
  const type = $derived(creationState.sheetType);
  const detail = $derived(creationState.sheetDetail);
  const tabKey = $derived(creationState.activeTabKey);
  const fieldCtx = $derived({
    entities: creationState.entities,
    locationTypeCatalog: creationState.locationTypeCatalog,
    entityId: isNew ? null : (detail && detail.id),
    legacyDoc,
  });
  const showGeneratePanel = $derived(isNew && (
    (type === 'character' && tabKey === 'npc')
    || (type === 'location' && tabKey === 'lieux')
    || (type === 'faction' && tabKey === 'factions')
  ));

  function onTypeSelectChange(ev) {
    creationState.sheetType = ev.currentTarget.value;
  }
</script>

<div id="author-core-sheet" style={mode === 'legacy' ? 'display:none' : ''}>
  {#if mode === 'loading'}
    <div class="empty"><span class="spin">⟳</span></div>
  {:else if mode === 'error'}
    <div class="empty">{creationState.sheetErrorMessage}</div>
  {:else if mode === 'empty'}
    <div class="empty">{EMPTY_BODY_BY_TAB[tabKey] || 'Sélectionnez une entité depuis la liste, ou créez-en une nouvelle.'}</div>
  {:else if mode === 'view'}
    {#if !registry}
      <div class="empty"><span class="spin">⟳</span></div>
    {:else}
      {#if showGeneratePanel}
        {@html legacyCall('authorRenderGeneratePanel')}
      {/if}

      <div class="field-section"><div class="field-section-title">Entity</div><div class="field-grid">
        {#if isNew}
          <div class="field-row"><label for="author-f-type">Type *</label>
            <select id="author-f-type" onchange={onTypeSelectChange}>
              {#each registry.entity_types as t (t)}
                <option value={t} selected={t === type}>{registry.types[t].label}</option>
              {/each}
            </select>
          </div>
        {:else}
          <div class="field-row"><label>Type</label>
            <input type="text" value={registry.types[type].label} disabled></div>
        {/if}
        {#each registry.entity_base_fields as f (f.name)}
          <Field field={f} value={isNew ? undefined : (f.name === 'metadata' ? detail.metadata : detail[f.name])} idPrefix="author-f" ctx={fieldCtx} />
        {/each}
      </div></div>

      <div class="field-section"><div class="field-section-title">{registry.types[type].label}</div><div class="field-grid">
        {#each (registry.types[type].fields || []) as f (f.name)}
          <Field field={f} value={isNew ? undefined : (detail.extension ? detail.extension[f.name] : undefined)} idPrefix="author-x" ctx={fieldCtx} />
        {/each}
      </div></div>

      {#if type === 'faction'}
        <div class="field-section"><div class="field-section-title">Roles</div>
          <div id="author-roles"><RolesEditor {isNew} factionId={isNew ? null : detail.id} /></div>
        </div>
      {/if}

      {#if type === 'location'}
        <div class="field-section"><div class="field-section-title">Subculture</div>
          <div id="author-subculture">
            <SubcultureEditor {isNew} entityId={isNew ? null : detail.id} rows={isNew ? null : detail.subculture_rows}
              {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
          </div>
        </div>
      {/if}

      {#if !isNew && type === 'location'}
        <div class="field-section"><div class="field-section-title">Spatial geometry</div>
          <div id="author-geometry">
            <GeometryEditor entityId={detail.id} geometry={detail.geometry || { bounds_width: null, bounds_height: null, obstacles: [] }}
              {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
          </div>
        </div>
        <div class="field-section"><div class="field-section-title">Portes</div>
          <div id="author-doors">
            <DoorsEditor entityId={detail.id} relations={detail.relations} doors={detail.doors}
              {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
          </div>
        </div>
      {/if}

      {#if !isNew}
        <div class="field-section"><div class="field-section-title">Relations</div>
          <div id="author-relations">{@html legacyCall('authorRenderRelations', detail.relations)}</div>
          {@html legacyCall('authorRenderRelationForm')}
        </div>
        <div class="field-section"><div class="field-section-title">Knowledge</div>
          <div id="author-knowledge">{@html legacyCall('authorRenderKnowledge', detail.knowledge)}</div>
          {@html legacyCall('authorRenderKnowledgeForm')}
        </div>
      {/if}

      {#if isNew && type === 'character' && tabKey === 'npc'}
        <div class="field-section"><div class="field-section-title">Knowledge (créé à l'acceptation)</div>
          <div id="author-pending-knowledge">{@html legacyCall('authorRenderPendingKnowledge')}</div>
        </div>
        <div class="field-section"><div class="field-section-title">Objectifs (créés à l'acceptation)</div>
          <div id="author-pending-goals">{@html legacyCall('authorRenderPendingGoals')}</div>
        </div>
      {/if}

      {#if !isNew && type === 'character'}
        <div class="field-section"><div class="field-section-title">Items</div>
          <div id="author-items"><ItemsPanel entityId={detail.id} /></div>
        </div>
        <div class="field-section"><div class="field-section-title">Appartenances</div>
          <MembershipsPanel entityId={detail.id} {legacyDoc} />
        </div>
      {/if}

      {#if !isNew && type === 'faction'}
        <div class="field-section"><div class="field-section-title">Membres</div>
          <div id="author-faction-roster"><FactionRoster factionId={detail.id} /></div>
        </div>
      {/if}

      {#if !isNew && (type === 'character' || type === 'faction')}
        <div class="field-section"><div class="field-section-title">Solde</div>
          <div id="author-ledger"><LedgerPanel entityId={detail.id} /></div>
        </div>
      {/if}

      {#if !isNew && type === 'character' && tabKey === 'npc'}
        <div class="field-section"><div class="field-section-title">Tarifs</div>
          <PricingEditor entityId={detail.id} prices={detail.prices} {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
        </div>
      {/if}

      {#if !isNew && type === 'character' && tabKey === 'npc'}
        <div class="field-section">
          <div class="field-section-title" style="display:flex; align-items:center; justify-content:space-between;">
            Objectifs
            <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={() => legacyCall('authorBackfillGoals', detail.id)}>Générer les buts</button>
          </div>
          <div id="author-goals"><div class="empty"><span class="spin">⟳</span></div></div>
          {@html legacyCall('authorRenderGoalForm')}
        </div>
      {/if}

      {#if !isNew && type === 'location'}
        <div class="field-section"><div class="field-section-title">Discoverable Details</div>
          <div id="author-disc-list"><div class="empty"><span class="spin">⟳</span></div></div>
          {@html legacyCall('authorRenderDiscDetailForm', detail.id, detail.world_id)}
        </div>
      {/if}
    {/if}
  {/if}
</div>
<div id="author-legacy-sheet-slot" style={mode === 'legacy' ? '' : 'display:none'}></div>
