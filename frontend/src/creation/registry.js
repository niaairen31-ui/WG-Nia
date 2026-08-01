/* TICKET-0058 (BRIEF-0058-d). The island registry: every Creation surface
   that has moved off the legacy CREATION_TABS renderer onto a Svelte
   component mounted by frontend/src/creation/mount.js.

   Unlike frontend/src/legacy/registry.js and frontend/src/graph/registry.js
   -- both monotonically SHRINKING lists of what remains legacy -- this
   registry GROWS: one entry per surface a brief converges (this pilot,
   then -e..-j), never removed once added. It is the record of what has
   moved, not of what remains.

   tooling/verify/checks/creation_island.py cross-references every field
   against index.html and the real filesystem:
     containerId:   legacy element id the component mounts into
     component:     Svelte component filename, relative to this directory
     migratedBy:    the ticket that performed the migration (^TICKET-\d{4}$)
     retiredPrefix: the legacy function-name prefix this migration retired;
                    the check proves zero `function <prefix>...(`
                    declarations remain in index.html, in any context */
export const CREATION_ISLANDS = Object.freeze({
  constructeur: Object.freeze({
    containerId: 'creation-constructeur',
    component: 'Constructeur.svelte',
    migratedBy: 'TICKET-0058',
    retiredPrefix: 'constructeur',
  }),
});
