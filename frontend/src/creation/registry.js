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
      // pendingDrafts.svelte.js. authorRenderGenNotes stays legacy (the
      // AI-generate panel's own notes block, brief -h).
      'authorRenderPendingKnowledge',
      'authorRemovePendingKnowledge',
      'authorRenderPendingGoals',
    ],
  }),
});
