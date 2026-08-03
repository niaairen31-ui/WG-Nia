/* TICKET-0058 (BRIEF-0058-i, closed by BRIEF-0058-j). The generic
   accept/reject review-tree component (TICKET-0041, BRIEF-0041-a), ported
   verbatim off index.html. Knows NOTHING about the world model: no
   location, no faction, no draft, no sensed_link. A consumer registers a
   descriptor under a key and Review.svelte (the Svelte-native rendering
   half) drives the render from it.

   Two consumers: `region` (frontend/src/creation/Region.svelte, BRIEF-0058-i)
   and `batch` (frontend/src/creation/RoomBatch.svelte, BRIEF-0058-j) --
   both Svelte-native now, both render via <Review>, neither reaches this
   module through the legacy window any more. BRIEF-0058-j retired the
   whole string-building render half and the legacy-window installer that
   used to expose it there: once `batch` converged, nothing called any of
   it any more -- "no structure without a reader" applies to a generic
   component's own exports exactly as it does to a legacy caller.

   DESCRIPTOR CONTRACT
     key               registry key, e.g. 'region' | 'batch'
     nodes             [{ id, name, subtitle, parentId, description, notes[] }]
     accepted          plain map id -> bool. ABSENT or true means accepted
                       (default-accept).
     fallbackParentId  where an orphaned node re-attaches, or null.
     reparentedLabel   badge text shown on a re-attached node
     graph             { consumer, mountId, extraEdges(acceptedIds, nodeById) }
     onToggleAccept(id)  consumer mutates its own accepted map
     onOpenSheet(id)      consumer opens its own full sheet */

const REVIEW_DESCRIPTORS = {};

export function reviewRegister(key, descriptor) { REVIEW_DESCRIPTORS[key] = descriptor; }
export function reviewDescriptor(key) { return REVIEW_DESCRIPTORS[key]; }

/** Re-derive the server's cascade, client-side, for display only. PURE. */
export function reviewCascade(descriptor) {
  const acceptedIds = new Set(descriptor.nodes.filter(n => (descriptor.accepted[n.id] !== false)).map(n => n.id));
  const fallbackParentId = descriptor.fallbackParentId;

  const effectiveParent = {};
  for (const n of descriptor.nodes) {
    const p = n.parentId;
    if (p == null) { effectiveParent[n.id] = null; continue; }
    if (acceptedIds.has(p)) { effectiveParent[n.id] = p; continue; }
    effectiveParent[n.id] = (fallbackParentId && acceptedIds.has(fallbackParentId) && fallbackParentId !== n.id) ? fallbackParentId : null;
  }

  return { acceptedIds, effectiveParent };
}

export function reviewGraphData(key) {
  const d = reviewDescriptor(key);
  const cascade = reviewCascade(d);
  const nodes = d.nodes.filter(n => cascade.acceptedIds.has(n.id)).map(n => ({ id: n.id, name: n.name }));

  const hierEdges = [];
  for (const n of d.nodes) {
    if (!cascade.acceptedIds.has(n.id)) continue;
    const parent = cascade.effectiveParent[n.id];
    if (parent != null) hierEdges.push({ id: `h-${n.id}`, entity_a_id: parent, entity_b_id: n.id, kind: 'hierarchy' });
  }

  const nodeById = new Map(d.nodes.map(n => [n.id, n]));
  const extraEdges = d.graph.extraEdges(cascade.acceptedIds, nodeById);

  return { nodes, edges: [...hierEdges, ...extraEdges] };
}
