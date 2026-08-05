/* TICKET-0058 (BRIEF-0058-d, amended -e). The island registry: every
   Creation surface that has moved off the legacy CREATION_TABS renderer
   onto a Svelte component mounted by frontend/src/creation/mount.js.

   Unlike frontend/src/legacy/registry.js and frontend/src/graph/registry.js
   -- both monotonically SHRINKING lists of what remains legacy -- this
   registry GROWS: one entry per surface a brief converges (this pilot,
   then -e..-j), never removed once added. It is the record of what has
   moved, not of what remains.

   BRIEF-0058-e amendment: a registry key may now be declared by MORE THAN
   ONE `CREATION_TABS` entry's `islands: [{ key, containerId }]` list --
   #author-entity-list is one shared mount point serving seven entries
   (npc/pj/lieux/factions/objets/intrigues/evenements) plus every runtime
   type, all rendered by the SAME EntityList.svelte instance. One container,
   one component, many owning tabs -- never three renderers racing for one
   node.

   tooling/verify/checks/creation_island.py cross-references every field
   against index.html and the real filesystem:
     containerId:     legacy element id the component mounts into
     component:       Svelte component filename, relative to this directory
     migratedBy:      the ticket that performed the migration (^TICKET-\d{4}$)
     retiredPrefixes: the legacy function-name prefixes this migration
                      retired; the check proves zero `function <prefix>...(`
                      declarations remain in index.html, in any context, for
                      EVERY prefix in the list */
export const CREATION_ISLANDS = Object.freeze({
  constructeur: Object.freeze({
    containerId: 'creation-constructeur',
    component: 'Constructeur.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefixes: ['constructeur'],
  }),
  entityList: Object.freeze({
    containerId: 'author-entity-list',
    component: 'EntityList.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefixes: [
      'creationRenderEntityList',
      'authorRenderEntityList',
      'authorLoadEntityList',
      'renderLieuxBrowse',
      'lieuxHasActiveDescendant',
      'lieuxChildrenOf',
      'lieuxDescend',
      'lieuxJumpTo',
      'lieuxToggleActiveOnly',
      'renderIntriguesListRows',
      'renderEvenementsListRows',
    ],
  }),
  // BRIEF-0058-f: #author-main's mount point -- the second 'islands' entry
  // onto the same seven CREATION_TABS entries entityList already declares
  // (npc/pj/lieux/factions/objets/intrigues/evenements) plus every runtime
  // type. Sheet.svelte owns the container unconditionally (a stable leaf
  // inside it, #author-legacy-sheet-slot, is what pj's create panel and
  // intrigues'/evenements' bespoke sheetRenderer still render into -- see
  // Sheet.svelte's own header comment); only the CORE field engine
  // (authorRenderSheet/authorRenderField/authorReadField/_authorSaveSubmit)
  // is actually retired here.
  entitySheet: Object.freeze({
    containerId: 'author-main',
    component: 'Sheet.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefixes: [
      'authorRenderSheet',
      'authorRenderField',
      'authorReadField',
      '_authorSaveSubmit',
      'authorTypeChanged',
      'authorNewEntity',
      // BRIEF-0058-g family a: geometry + doors sub-editors, and the Lieux
      // create/save flow -- ported to GeometryEditor.svelte/DoorsEditor.svelte/
      // locationType.js, mounted/called from this same #author-main island.
      'authorGeometryDetectItem',
      'authorRenderGeometryEditor',
      'authorAddGeometryRow',
      'authorRemoveGeometryRow',
      'authorSaveGeometry',
      'authorRenderDoorsEditor',
      'authorSaveDoors',
      'authorRemoveOrphanDoor',
      '_authorLocationTypeOptionLabel',
      '_authorOpenTemplateModalFor',
      '_authorPromptLocationTypeClassification',
      '_authorClassifyLocationType',
      // BRIEF-0058-g family b: faction roles, memberships, roster -- ported
      // to RolesEditor.svelte/RoleRow.svelte/FactionRoster.svelte/
      // MembershipsPanel.svelte/factionPanel.svelte.js.
      'authorRenderRolesEditor',
      'authorAddRoleRow',
      'authorRemoveRoleRow',
      'authorMoveRoleRow',
      'authorLoadFactionMembersPanel',
      'authorLoadFactionRoles',
      'authorRenderExistingRolesEditor',
      'authorCreateFactionRole',
      'authorUpdateFactionRole',
      'authorRenameFactionRole',
      'authorMoveFactionRole',
      'authorDeleteFactionRole',
      'authorDeclareFactionRole',
      'authorRenderMembershipForm',
      'authorMembershipFactionChanged',
      'authorMembershipRoleSelectChanged',
      'authorAddMembership',
      'authorCloseMembership',
      'authorLoadFactionRoster',
      'authorRenderFactionRoster',
      'authorRenderFactionMemberAddForm',
      'authorFactionMemberRoleSelectChanged',
      'authorFactionMemberAddPrefill',
      'authorAddFactionMember',
      'authorMemberRoleEditStart',
      'authorMemberRoleEditCancel',
      'authorMemberRoleEditSubmit',
      'authorLoadMemberships',
      'authorRenderMemberships',
      // BRIEF-0058-g family c: Tarifs (npc_price) + location subculture --
      // ported to PricingEditor.svelte/SubcultureEditor.svelte/
      // subcultureDraft.svelte.js.
      'authorRenderPricing',
      'authorSavePriceEntry',
      'authorDeletePriceEntry',
      'authorAddPriceEntry',
      'authorPriceListMutate',
      'authorRenderSubcultureEditor',
      'authorAddSubcultureRow',
      'authorRemoveSubcultureRow',
      'authorSaveSubcultureRows',
      // BRIEF-0058-g family d: read-only ledger + items sections -- ported
      // to LedgerPanel.svelte/ItemsPanel.svelte. authorAddLedgerEntry
      // belongs to the untouched Registre tab, not this island.
      'authorLoadLedger',
      'authorRenderLedger',
      'authorLoadItems',
      'authorRenderItems',
      // BRIEF-0058-g family e: pending knowledge/goals draft panels --
      // ported to PendingKnowledgeEditor.svelte/PendingGoalsEditor.svelte/
      // pendingDrafts.svelte.js.
      'authorRenderPendingKnowledge',
      'authorRemovePendingKnowledge',
      'authorRenderPendingGoals',
      // BRIEF-0058-h: the AI-generate draft panel -- ported to
      // GeneratePanel.svelte/generatePanel.svelte.js.
      'authorRenderGeneratePanel',
      'authorGenerateEntity',
      'authorApplyCharacterDraft',
      'authorApplyLocationDraft',
      'authorApplyFactionDraft',
      'authorRenderGenNotes',
      // BRIEF-0058-j: evenements -- the last bespoke, still-legacy sheet --
      // converges onto Evenements.svelte/eventDraft.svelte.js, reached
      // through this same #author-main island (a tabKey === 'evenements'
      // gate, not a registry-types-by-type lookup: `event` carries no
      // ENTITY_TYPE_REGISTRY row).
      'evenements',
      '_evenementsRenderChips',
      'loadEventsList',
      'renderEventSheet',
      // BRIEF-0059-c: relations in-context editor -- ported to
      // RelationsEditor.svelte, sharing sheetRequest.svelte.js with the
      // knowledge editor below.
      'authorRenderRelations',
      'authorRenderRelationForm',
      'authorAddRelation',
      'authorUpdateRelation',
      'authorDeleteRelation',
      'authorRelationRequest',
      'RELATION_DIRECTIONS',
      // BRIEF-0059-c: knowledge in-context editor -- ported to
      // KnowledgeEditor.svelte, sharing sheetRequest.svelte.js with the
      // relations editor above.
      'authorRenderKnowledge',
      'authorRenderKnowledgeForm',
      'authorAddKnowledge',
      'authorUpdateKnowledge',
      'authorDeleteKnowledge',
      'authorKnowledgeRequest',
      // BRIEF-0059-d: goals in-context editor -- ported to
      // GoalsEditor.svelte/goalsPanel.svelte.js, reusing sheetRequest.svelte.js.
      // _goalPrereqRawList (index.html) is not author*-prefixed but is
      // exclusively used by this family (RECON-0059-a M2 / SUPPLEMENT
      // Amendment 8) -- named here so rule 7 still proves it gone.
      'authorLoadGoals',
      'authorRenderGoals',
      'authorRenderGoalPrerequisites',
      '_goalPrereqRawList',
      'authorAddGoalPrerequisite',
      'authorRemoveGoalPrerequisite',
      'authorSetGoalPrerequisites',
      'authorAttachGoalLink',
      'authorDetachGoalLink',
      'authorRenderGoalForm',
      'authorAddGoal',
      'authorSetGoalStatus',
      'authorBackfillGoals',
      'authorGoalRequest',
      // BRIEF-0059-d: discoverable-details in-context editor -- ported to
      // DiscDetailsEditor.svelte (self-contained, never touched the shared
      // #author-status line, so no sheetRequest.svelte.js dependency).
      'authorLoadDiscDetails',
      'authorRenderDiscDetails',
      'authorRenderDiscDetailRow',
      'authorRenderDiscDetailForm',
      'authorAddDiscDetail',
      'authorDeleteDiscDetail',
      'authorResetDiscDetail',
      'authorEditDiscDetail',
      'authorSaveDiscDetail',
      // BRIEF-0059-e commit 1: entity-sheet state ownership, create-draft +
      // pending-mutation lifecycle -- ported to sheetState.svelte.js.
      // authorSelectEntity/authorGetSelectedEntityId (commit 2) and
      // authorDelete (commit 3) are added in their own commits, each
      // independently passing rule 7 (Invariants: fail-closed guards never
      // lapse between this brief's three commits).
      '_authorResetCreateDrafts',
      '_authorGetPendingCreationMutationId',
      '_authorConsumePendingCreationMutationId',
      '_authorNotifySaved',
      // BRIEF-0059-e commit 2: selection -- ported to sheetState.svelte.js's
      // selectEntity/getSelectedEntityId.
      'authorSelectEntity',
      'authorGetSelectedEntityId',
      // BRIEF-0059-e commit 3: soft delete -- ported to Sheet.svelte's
      // deleteSheetEntity/sheetState.svelte.js's deleteEntity; the delete
      // button moved out of the static legacy header into the component.
      'authorDelete',
    ],
  }),
  // BRIEF-0058-i (per RECON-SUPPLEMENT-0058's re-scope): region generation
  // -- brief form, manifest checkpoint, draft review/commit, and its own
  // parallel sheet editor -- ported wholesale to Region.svelte, alongside
  // the generic review-tree component itself (frontend/src/creation/review/
  // registry.js + Review.svelte). The room batch generator (lieux tab)
  // converged the same way in BRIEF-0058-j (below) -- both consumers reach
  // the shared review component through Review.svelte now, never the
  // legacy-window bridge (retired).
  region: Object.freeze({
    containerId: 'creation-region',
    component: 'Region.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefixes: ['region', '_region', '_sheetField', '_sheetListSection', '_sheetEntityOptions'],
  }),
  // BRIEF-0058-j (per RECON-SUPPLEMENT-0058's re-scope): the room batch
  // generator -- manifest checkpoint, draft review/commit -- ported
  // wholesale to RoomBatch.svelte/roomBatch.svelte.js, the review
  // component's second consumer. Lives inside the `lieux` tab's own
  // #batch-panel-wrap container (declared alongside creation-editor-area in
  // CREATION_TABS.lieux.containers), mounted on every 'lieux' activation but
  // rendering nothing until EntityList.svelte's "Générer un lot ici" opens it.
  batch: Object.freeze({
    containerId: 'batch-panel-wrap',
    component: 'RoomBatch.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefixes: ['batch', '_batchNodeName'],
  }),
  // BRIEF-0059-f: the NPC group agent panel -- ported to NpcAgent.svelte/
  // npcAgent.svelte.js, LocationTree.svelte's first consumer. Landed across
  // two commits (npcAgent.svelte.js's own header explains the split);
  // commit 3 grew this list with the run-loop/review functions'
  // identifiers, the same way entitySheet's own retiredPrefixes grew across
  // BRIEF-0059-e's three commits. npcAgentToggle/npcAgentOpen are the two
  // survivors (chrome, not migrated) and are deliberately absent here.
  npcAgent: Object.freeze({
    containerId: 'npcagent-panel',
    component: 'NpcAgent.svelte',
    migratedBy: 'TICKET-0059',
    retiredPrefixes: [
      'npcAgentReset',
      'npcAgentCheckOpenBatch',
      'npcAgentRenderLauncher',
      '_npcAgentTreeHtml',
      'npcAgentSelectRoot',
      'npcAgentPreviewRoot',
      'npcAgentAddLine',
      'npcAgentRemoveLine',
      'npcAgentEditLine',
      '_npcAgentLineTotal',
      '_npcAgentLineRowHtml',
      '_npcAgentPaintLauncher',
      'npcAgentLaunch',
      '_npcAgentRefreshRows',
      'npcAgentRunOne',
      'npcAgentRunLoop',
      'npcAgentPause',
      'npcAgentRetryRun',
      'npcAgentLoadBatch',
      '_npcAgentGroupRows',
      '_npcAgentRowHtml',
      '_npcAgentGroupHtml',
      'npcAgentEditField',
      'npcAgentToggleReject',
      'npcAgentCommit',
      'npcAgentAbandon',
      'npcAgentGenerateLinks',
      '_npcAgentPaintReview',
    ],
  }),
  // BRIEF-0059-g: the NPC link agent panel -- ported to LinkAgent.svelte/
  // linkAgent.svelte.js, LocationTree.svelte's second consumer (checkbox +
  // ancestor-inheritance row, per Amendment 1's row-snippet seam). Landed
  // across two commits (linkAgent.svelte.js's own header explains the
  // split); commit 2 grew this list with the run-loop/review/coherence
  // functions' identifiers, the same shape npcAgent's own retiredPrefixes
  // grew across BRIEF-0059-f. linkAgentToggle/linkAgentOpen are the two
  // survivors (chrome, not migrated) and are deliberately absent here.
  // BRIEF-0059-h commit 2: the Artefacts tab -- ported wholesale to
  // Artefacts.svelte, following region's own "archetype: 'bespoke' with an
  // island slot" precedent exactly. Read-only, one function, no legacyCall
  // sites to prune.
  artefacts: Object.freeze({
    containerId: 'creation-artefacts',
    component: 'Artefacts.svelte',
    migratedBy: 'TICKET-0059',
    retiredPrefixes: ['loadCreationArtefacts', 'CREATION_ARTEFACTS_NOTICE'],
  }),
  // BRIEF-0059-h commit 3: the Compétences tab -- ported to
  // Competences.svelte + competences.svelte.js, Modal.svelte's second
  // consumer (delete-confirmation dialog, lock O1).
  competences: Object.freeze({
    containerId: 'creation-competences',
    component: 'Competences.svelte',
    migratedBy: 'TICKET-0059',
    retiredPrefixes: [
      '_competencesWorldReset', 'competencesGenerateDraft',
      '_competencesDomainOptions', 'competencesRenderDraft',
      'competencesDiscardDraftRow', 'competencesAcceptDraftRow',
      'competencesAddManualRow', 'competencesLoadList',
      '_competencesRenderTable', 'competencesSaveRow',
      'competencesDeleteOpen', 'competencesDeleteConfirm',
      'COMPETENCES_DOMAINS',
    ],
  }),
  // BRIEF-0059-h commit 4: the Registre (global ledger) tab -- ported
  // wholesale to Registre.svelte. authorAddLedgerEntry closes here, not
  // with the entity sheet's own read-only LedgerPanel.svelte (RECON-0059-a
  // M2 / SUPPLEMENT Amendment 8: its sole caller is this tab's own
  // add-form button).
  registre: Object.freeze({
    containerId: 'creation-registre',
    component: 'Registre.svelte',
    migratedBy: 'TICKET-0059',
    retiredPrefixes: [
      '_registreWorldReset', '_registrePopulateEntityFilter',
      'authorAddLedgerEntry', 'registreToggleAddForm', 'loadRegistre',
      '_registreRenderTable', '_registreEntitiesLoaded',
    ],
  }),
  linkAgent: Object.freeze({
    containerId: 'linkagent-panel',
    component: 'LinkAgent.svelte',
    migratedBy: 'TICKET-0059',
    retiredPrefixes: [
      'linkAgentReset',
      'linkAgentCheckOpenBatch',
      'linkAgentRenderLauncher',
      '_linkAgentIsChecked',
      '_linkAgentTreeHtml',
      'linkAgentToggleLocation',
      '_linkAgentPaintLauncher',
      'linkAgentPreviewRoster',
      'linkAgentLaunch',
      'linkAgentRunLoop',
      'linkAgentPause',
      'linkAgentRetry',
      'linkAgentLoadBatch',
      '_linkAgentNpcName',
      '_linkAgentGroupRows',
      '_linkAgentRelationRowHtml',
      '_linkAgentKnowledgeRowHtml',
      '_linkAgentNoLinksRowHtml',
      '_linkAgentPairGroupHtml',
      'linkAgentEditField',
      'linkAgentToggleReject',
      '_linkAgentFindingHtml',
      'linkAgentRunCoherence',
      'linkAgentApplyFinding',
      'linkAgentCommit',
      '_linkAgentPaintReview',
    ],
  }),
});
