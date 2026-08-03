/* TICKET-0057 (C1). Every graph implementation that is NOT the primitive,
   enumerated. The list may only SHRINK: one entry is removed by the ticket
   that converges it, and an entry may never be added --
   tooling/verify/checks/graph_primitive.py compares this set against
   tooling/verify/baselines/graph_impls.baseline and refuses any key that
   is not already there. When the last entry goes, "un graph est un graph"
   stops being a claim and becomes a measured fact.

   Modelled on frontend/src/legacy/registry.js (TICKET-0056), which is the
   same shape solving the same problem one level up.

   TICKET-0058 (BRIEF-0058-c): the last entry, `relation_cytoscape`,
   converged onto the primitive here -- GRAPH_IMPLS is now permanently
   empty. Its retirement is recorded, append-only, in
   tooling/verify/baselines/graph_impls.retired; graph_primitive.py's rule
   5b proves its code stays gone, forever, not just unregistered. */
export const GRAPH_IMPLS = Object.freeze({});
