/* TICKET-0057 (C1). Every graph implementation that is NOT the primitive,
   enumerated. The list may only SHRINK: one entry is removed by the ticket
   that converges it, and an entry may never be added --
   tooling/verify/checks/graph_primitive.py compares this set against
   tooling/verify/baselines/graph_impls.baseline and refuses any key that
   is not already there. When the last entry goes, "un graph est un graph"
   stops being a claim and becomes a measured fact.

   Modelled on frontend/src/legacy/registry.js (TICKET-0056), which is the
   same shape solving the same problem one level up. */
export const GRAPH_IMPLS = Object.freeze({
  relation_cytoscape: Object.freeze({
    engine: 'cytoscape',
    locus: 'src/world_engine/cockpit/index.html',
    fnPrefix: 'relGraph',
    retiredBy: 'TICKET-0058',
  }),
});
