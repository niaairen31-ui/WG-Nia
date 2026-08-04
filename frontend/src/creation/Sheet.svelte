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
     roster/ledger/pricing/goals/disc-details -- brief -g) stays legacy,
     unmigrated: this component renders the SAME placeholder skeleton authorRenderSheet
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

     One tab (`intrigues`) and one mode (`pj`'s create panel) never used
     authorRenderSheet at all -- they have their own bespoke, hand-rolled
     sheetRenderer/createPanel (renderAgendaSheet, pjRenderCreatePanel) and
     stay unmigrated legacy code that still needs somewhere safe to render
     inside this island's own mount root without tearing Svelte's DOM out
     from under it (RECON-0058-a M5). The answer is the SAME "stable leaf,
     legacy free to mutate its innerHTML" idiom the sub-editor placeholders
     already rely on, just sized to the whole container:
     #author-legacy-sheet-slot is an UNCONDITIONALLY rendered sibling of
     #author-core-sheet (never created/destroyed by an {#if}, only
     display:toggled), so a legacy renderer that targets it right after a
     synchronous 'creation:sheet-legacy-active' dispatch always finds it
     there -- no dependency on Svelte's own update timing (flushSync makes
     the toggle itself synchronous too, belt and braces).

     `evenements` converged onto real Svelte state (TICKET-0058, BRIEF-0058-j,
     per RECON-SUPPLEMENT-0058's -j re-scope): it is not an entity-archetype
     tab (`event` carries no ENTITY_TYPE_REGISTRY row), so it renders via its
     own <Evenements> component, gated on `tabKey === 'evenements'` rather
     than a `registry.types[type]` lookup, and saves through its own
     saveEventSheet -- /api/events, never /api/entities. The reverse-
     direction 'creation:field-render'/'creation:field-read' bridge brief -f
     stood up for its still-legacy renderer is gone with it: <Evenements>
     reaches Field.svelte/fields.js by plain import, the same way every
     other tab already does.

     No scoped <style> block: like every other Creation island, this
     renders inside the legacy iframe document. */
  import { flushSync, tick } from 'svelte';
  import { creationState } from './state.svelte.js';
  import { serverState } from '../lib/serverState.svelte.js';
  import { legacyCall } from '../legacy/bridge.js';
  import { readFieldValue } from './fields.js';
  import { promptLocationTypeClassification } from './locationType.js';
  import Field from './Field.svelte';
  import GeometryEditor from './GeometryEditor.svelte';
  import DoorsEditor from './DoorsEditor.svelte';
  import RolesEditor from './RolesEditor.svelte';
  import FactionRoster from './FactionRoster.svelte';
  import MembershipsPanel from './MembershipsPanel.svelte';
  import { loadFactionMembersPanel, draftRolesForCreate, resetDraftRoles } from './factionPanel.svelte.js';
  import { subcultureDraftForCreate, resetSubcultureDraft } from './subcultureDraft.svelte.js';
  import SubcultureEditor from './SubcultureEditor.svelte';
  import PricingEditor from './PricingEditor.svelte';
  import LedgerPanel from './LedgerPanel.svelte';
  import ItemsPanel from './ItemsPanel.svelte';
  import { resetPendingDrafts, knowledgeForCreate, goalsForCreate } from './pendingDrafts.svelte.js';
  import PendingKnowledgeEditor from './PendingKnowledgeEditor.svelte';
  import PendingGoalsEditor from './PendingGoalsEditor.svelte';
  import { resetGeneratePanel, applyGeneratedDraft } from './generatePanel.svelte.js';
  import GeneratePanel from './GeneratePanel.svelte';
  import { resetEventDraft, eventDraftState } from './eventDraft.svelte.js';
  import Evenements from './Evenements.svelte';
  import RelationsEditor from './RelationsEditor.svelte';
  import KnowledgeEditor from './KnowledgeEditor.svelte';
  import GoalsEditor from './GoalsEditor.svelte';
  import { backfillGoals } from './goalsPanel.svelte.js';
  import DiscDetailsEditor from './DiscDetailsEditor.svelte';
  import { resetCreateDrafts, getPendingCreationMutationId, consumePendingCreationMutationId, setPendingCreationMutationId, notifySaved, selectEntity, deleteEntity } from './sheetState.svelte.js';

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
   *  entity-archetype tab OR evenements (BRIEF-0058-j: evenements is
   *  island-routed too now) -- pj/intrigues never route here (rule 11
   *  pairing keeps their primaryAction legacy, paired with their own
   *  bespoke createPanel). Mirrors creationNewEntity's own draft reset (the
   *  plain "+ Nouveau" idiom every entity tab shared before this brief),
   *  via the same legacy helper so the two paths never drift. */
  export function primaryAction() {
    resetCreateDrafts();
    resetDraftRoles();
    resetSubcultureDraft();
    resetPendingDrafts();
    resetGeneratePanel();
    resetEventDraft();
    enterCreateMode(resolveTypeForTab(creationState.activeTabKey));
  }

  legacyDoc.addEventListener('creation:sheet-reset', () => {
    resetCreateDrafts();
    flushSync(() => {
      creationState.sheetMode = 'empty';
      creationState.sheetDetail = null;
      creationState.sheetIsNew = false;
      creationState.sheetType = null;
    });
  });

  // authorPriceListMutate/authorSaveSubcultureRowsData/authorSaveGeometry/
  // authorSaveDoors (brief -g sub-editors, unmigrated) dispatch this to
  // refresh the sheet with their own PUT response, replacing their former
  // direct authorRenderSheet(detail, false, detail.type) call.
  legacyDoc.addEventListener('creation:sheet-detail', (ev) => {
    flushSync(() => { enterViewMode(ev.detail.detail, ev.detail.type); });
  });

  // TICKET-0059 (BRIEF-0059-e): the entity sheet's own loader,
  // sheetState.svelte.js's selectEntity, writes creationState directly
  // instead of round-tripping through 'creation:sheet-loading'/'creation:
  // sheet-error' -- those two existed only for authorSelectEntity to
  // dispatch-then-listen back into this same island, which is pointless now
  // that the loader itself is Svelte. This is the reverse-bridge counterpart
  // for the two still-legacy callers (creationOpenEntityFrom,
  // creationReturnToOrigin) that can't reach selectEntity by import.
  legacyDoc.addEventListener('creation:select-entity', (ev) => {
    selectEntity(legacyDoc, ev.detail.id);
  });

  // generatePendingCreation (the "Créations en attente" card's generate
  // button, still legacy) dispatches this instead of the deleted
  // authorRenderSheet({}, true, entityType) -- flushSync so the DOM this
  // creates (author-f-name et al.) exists before generatePendingCreation's
  // 'creation:apply-generated-draft' dispatch right after (BRIEF-0058-h,
  // below).
  legacyDoc.addEventListener('creation:sheet-create', (ev) => {
    flushSync(() => { enterCreateMode(ev.detail.type); });
    // generatePendingCreation (still legacy, germ realization) carries the
    // pending mutation id in this same event's detail now -- a bare `let`
    // can't be written from across the legacy boundary any more.
    if (ev.detail.mutationId) setPendingCreationMutationId(ev.detail.mutationId);
  });

  // pj's createPanel, intrigues' createPanel+sheetRenderer -- both still
  // legacy (rule 11 pairing keeps them off the island-routed primaryAction)
  // -- dispatch this immediately before rendering their own markup into
  // #author-legacy-sheet-slot, so that node exists under "legacy" display
  // before their innerHTML write. creationNewEntity does this for the
  // create-panel path; creationSelectRecord does it for entry.sheetRenderer
  // (intrigues' view path).
  legacyDoc.addEventListener('creation:sheet-legacy-active', () => {
    flushSync(() => { creationState.sheetMode = 'legacy'; });
  });

  // creationSelectRecord dispatches this for a non-entity, non-legacy
  // record tab -- evenements is the one caller since BRIEF-0058-j (intrigues
  // still has a bespoke sheetRenderer and never reaches here). Mirrors
  // 'creation:sheet-detail' exactly, just keyed by tabId instead of a
  // fetched entity's own .type.
  legacyDoc.addEventListener('creation:record-detail', (ev) => {
    flushSync(() => { enterViewMode(ev.detail.record, ev.detail.tabId); });
  });

  // #author-save-btn's onclick (creationSaveDispatch) dispatches this for
  // every tab with no saveHandler of its own.
  legacyDoc.addEventListener('creation:sheet-save', () => { saveSheet(); });

  // creationNewEntity (pj/intrigues' own "+ Nouveau", still legacy) used to
  // call _authorResetCreateDrafts() directly; that function is now
  // resetCreateDrafts() in sheetState.svelte.js, unreachable from across the
  // legacy boundary as a bare call -- this is the reverse-bridge dispatch it
  // fires instead (BRIEF-0059-e).
  legacyDoc.addEventListener('creation:reset-create-drafts', () => { resetCreateDrafts(); });

  // generatePendingCreation (index.html, still legacy -- germ realization,
  // "Créations en attente", is out of this brief's scope) reaches the ported
  // applyGeneratedDraft this same reverse-bridge way, dispatched right after
  // 'creation:sheet-create' (above) has flushSync'd the create-mode DOM into
  // existence -- BRIEF-0058-h. This is the ONE apply implementation for both
  // callers: GeneratePanel.svelte's own "Générer" click reaches it via a
  // plain import instead, no event needed, since it already runs as real JS.
  legacyDoc.addEventListener('creation:apply-generated-draft', (ev) => {
    applyGeneratedDraft(legacyDoc, ev.detail.entityType, ev.detail.result);
  });

  // Sibling header chrome (title/status/save) lives OUTSIDE #author-main --
  // authorRenderSheet always reached out to it too. Delete is no longer
  // part of this header band (TICKET-0059, BRIEF-0059-e): it moved into
  // this component's own template, rendered/hidden declaratively off the
  // same isNew/type conditions this effect used to imperatively toggle it
  // with. Only touched for 'empty'/'view': 'loading'/'error' leave it
  // exactly as the old loader's spinner/catch branches always did
  // (untouched), and 'legacy' is legacy code's own job (renderAgendaSheet
  // et al. already set these themselves, unchanged).
  $effect(() => {
    const mode = creationState.sheetMode;
    if (mode !== 'empty' && mode !== 'view') return;
    const titleEl = legacyDoc.getElementById('author-sheet-title');
    const statusEl = legacyDoc.getElementById('author-status');
    const saveBtn = legacyDoc.getElementById('author-save-btn');
    if (mode === 'empty') {
      if (titleEl) titleEl.textContent = EMPTY_TITLE_BY_TAB[creationState.activeTabKey] || 'Sélectionner une entité';
      if (statusEl) statusEl.textContent = '';
      if (saveBtn) saveBtn.style.display = 'none';
      return;
    }
    const isNewSheet = creationState.sheetIsNew;
    // evenements (BRIEF-0058-j): `event` carries no ENTITY_TYPE_REGISTRY
    // row, so there is no typeInfo.label to read -- title comes straight
    // off the record, and save is hidden on create (the inline "+ Créer
    // l'événement" button is the create-time submit, matching every other
    // bespoke createPanel's own posture). Delete never shows for events (C3,
    // no event delete surface exists) -- by construction, since the
    // template's delete button lives outside this branch entirely.
    if (creationState.activeTabKey === 'evenements') {
      if (titleEl) titleEl.textContent = isNewSheet ? 'Nouvel événement' : (creationState.sheetDetail.title || '');
      if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = ''; }
      if (saveBtn) saveBtn.style.display = isNewSheet ? 'none' : '';
      return;
    }
    if (!registry) return;
    const type = creationState.sheetType;
    const typeInfo = registry.types[type];
    if (!typeInfo) return;
    if (titleEl) {
      titleEl.textContent = isNewSheet
        ? `New ${typeInfo.label}`
        : `${creationState.sheetDetail.name} (${typeInfo.label})`;
    }
    if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = ''; }
    if (saveBtn) saveBtn.style.display = '';
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
      if (type === 'faction') {
        loadFactionMembersPanel(detail.id);
      }
    })();
  });

  async function saveSheet() {
    if (creationState.activeTabKey === 'evenements') { await saveEventSheet(); return; }
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

  /** evenements' save (BRIEF-0058-j) -- one function for both the header
   *  Save button (view mode, PUT) and <Evenements>'s own inline "+ Créer
   *  l'événement" button (create mode, POST), unlike the legacy pair
   *  evenementsSave/evenementsSubmitCreate: the two only ever differed in
   *  HTTP verb/target and a title-required check, both expressed here as
   *  one isNewSave branch, same posture as submitEntity above. No delete
   *  path exists (C3) and no dependent-draft POSTs are needed (event has
   *  none). */
  async function saveEventSheet() {
    if (!registry) return;
    const statusEl = legacyDoc.getElementById('author-status');
    const isNewSave = creationState.sheetIsNew;

    const body = {};
    try {
      for (const field of registry.event_fields) {
        body[field.name] = readFieldValue(legacyDoc, field, 'event-f');
      }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = `Invalid: ${e.message}`; }
      return;
    }
    if (isNewSave && (!body.title || !body.title.trim())) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = 'Titre requis.'; }
      return;
    }
    body.involved_entities = eventDraftState.involved.map((c) => c.id);

    if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = isNewSave ? '…' : 'Saving…'; }
    try {
      const saved = isNewSave
        ? await api('/api/events', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : await api(`/api/events/${encodeURIComponent(creationState.sheetDetail.id)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

      legacyCall('creationRefreshList');
      flushSync(() => { enterViewMode(saved, 'evenements'); });
      legacyDoc.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: saved.id } }));
      const st = legacyDoc.getElementById('author-status');
      if (st) { st.className = 'author-status ok'; st.textContent = 'Saved.'; }
    } catch (e) {
      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
    }
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
    const knowledgeToCreate = (isNewSave && type === 'character') ? knowledgeForCreate() : [];
    const goalsToCreate = (isNewSave && type === 'character') ? goalsForCreate() : [];
    const mutationId = isNewSave ? getPendingCreationMutationId() : null;

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
        // TICKET-0059 (BRIEF-0059-e): the original _authorConsumePendingCreationMutationId
        // did both halves as one legacyCall; the id-clear half is ported
        // (consumePendingCreationMutationId above), but the germ-realization
        // list's own refresh (loadPendingCreations) is still legacy -- a
        // new, baselined bridge-reach site, same order as before.
        consumePendingCreationMutationId();
        legacyCall('loadPendingCreations');
      }
      if (isNewSave) {
        resetGeneratePanel();
        resetDraftRoles();
        resetSubcultureDraft();
        resetPendingDrafts();
      }

      legacyCall('creationRefreshList');
      notifySaved(legacyDoc, detail.id);
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

  /** index.html's authorDelete, ported (TICKET-0059, BRIEF-0059-e): a soft
   *  delete via the same POST /api/entities/{id}/delete endpoint, same
   *  confirmation text verbatim, same creationRefreshList + re-select
   *  sequence. The confirmation text stays unchanged -- history is sacred
   *  (relations/knowledge are preserved, and this is reversible). */
  async function deleteSheetEntity() {
    if (!creationState.sheetDetail || !creationState.sheetDetail.id) return;
    if (!confirm('Set this entity to inactive (soft delete)? Relations and knowledge are preserved, and this is reversible.')) return;
    const id = creationState.sheetDetail.id;
    const statusEl = legacyDoc.getElementById('author-status');
    try {
      await deleteEntity(id);
      legacyCall('creationRefreshList'); // TICKET-0058 (BRIEF-0058-e): see regionCommit's identical comment; a third baselined call site (this island already had two)
      await selectEntity(legacyDoc, id);
      if (statusEl) { statusEl.className = 'author-status ok'; statusEl.textContent = 'Marked inactive.'; }
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
    {:else if tabKey === 'evenements'}
      <Evenements {legacyDoc} {isNew} event={detail} entities={creationState.entities}
        eventFields={registry.event_fields} onSave={saveSheet} />
    {:else}
      {#if !isNew}
        <div style="display:flex; justify-content:flex-end; margin-bottom:8px;">
          <button class="btn-end" id="author-delete-btn" onclick={deleteSheetEntity}>Delete</button>
        </div>
      {/if}

      {#if showGeneratePanel}
        <GeneratePanel {legacyDoc} {type} />
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
          <RelationsEditor relations={detail.relations} entityId={detail.id} entities={creationState.entities}
            typeOptions={registry.relation_fields.find((f) => f.name === 'type').options || []}
            {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
        </div>
        <div class="field-section"><div class="field-section-title">Knowledge</div>
          <KnowledgeEditor knowledge={detail.knowledge} entityId={detail.id}
            levelOptions={registry.knowledge_fields.find((f) => f.name === 'level').options}
            {legacyDoc} onSaved={(d) => flushSync(() => enterViewMode(d, d.type))} />
        </div>
      {/if}

      {#if isNew && type === 'character' && tabKey === 'npc'}
        <div class="field-section"><div class="field-section-title">Knowledge (créé à l'acceptation)</div>
          <div id="author-pending-knowledge">
            <PendingKnowledgeEditor levelOptions={registry.knowledge_fields.find((f) => f.name === 'level').options} />
          </div>
        </div>
        <div class="field-section"><div class="field-section-title">Objectifs (créés à l'acceptation)</div>
          <div id="author-pending-goals"><PendingGoalsEditor /></div>
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
            <button class="btn-ghost" style="font-size:12px; padding:3px 8px" onclick={() => backfillGoals(legacyDoc, detail.id)}>Générer les buts</button>
          </div>
          <GoalsEditor entityId={detail.id} {legacyDoc} />
        </div>
      {/if}

      {#if !isNew && type === 'location'}
        <div class="field-section"><div class="field-section-title">Discoverable Details</div>
          <DiscDetailsEditor entityId={detail.id} worldId={detail.world_id} />
        </div>
      {/if}
    {/if}
  {/if}
</div>
<div id="author-legacy-sheet-slot" style={mode === 'legacy' ? '' : 'display:none'}></div>
