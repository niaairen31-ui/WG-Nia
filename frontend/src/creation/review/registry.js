/* TICKET-0058 (BRIEF-0058-i, per RECON-SUPPLEMENT-0058's re-scope). The
   generic accept/reject review-tree component (TICKET-0041, BRIEF-0041-a),
   ported verbatim off index.html. Knows NOTHING about the world model: no
   location, no faction, no draft, no sensed_link. A consumer registers a
   descriptor under a key and the component drives the render from it.

   Two consumers exist this brief: `region` (frontend/src/creation/Region.svelte,
   now Svelte-native -- it uses Review.svelte for the tree, not the
   string-building reviewNode/reviewTree below) and `batch` (the room batch
   generator, still legacy inside index.html until BRIEF-0058-j). Because
   `batch` keeps calling reviewRegister/reviewCascade/reviewTree/reviewIsAccepted/
   reviewToggleAccept/reviewNotes/reviewOpenSheet/reviewToggleGraph/reviewGraphData
   as bare globals from its own legacy script, installLegacyReviewBridge below
   injects this exact module's functions onto the legacy window at boot
   (frontend/src/creation/mount.js's initCreationMount) -- ONE implementation,
   reachable from both realms, not a duplicate. This bridge is a temporary
   scaffold: BRIEF-0058-j removes it once batch's own descriptor moves here
   too and no legacy caller survives.

   DESCRIPTOR CONTRACT (unchanged from index.html's original doc block)
     key               registry key, e.g. 'region'
     nodes             [{ id, name, subtitle, parentId, description,
                          notes[], extras }]
                       `extras` is a pre-rendered HTML string owned by the
                       consumer -- meaningful only to the string-based
                       reviewNode/reviewTree render below (batch). A Svelte
                       consumer (region) renders its own tree via
                       Review.svelte instead and does not depend on this
                       shape for `extras`.
     accepted          plain map id -> bool. ABSENT or true means accepted
                       (default-accept).
     fallbackParentId  where an orphaned node re-attaches, or null.
     reparentedLabel   badge text shown on a re-attached node
     graphOpen         bool, graph pane currently open
     graph             { consumer, mountId, extraEdges(acceptedIds, nodeById) }
     onToggleAccept(id)  consumer mutates its own accepted map
     onToggleGraph()     consumer mutates its own open flag
     onOpenSheet(id)      consumer opens its own full sheet
     onRender()           consumer re-renders itself fully */

function esc(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

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

export function reviewIsAccepted(key, id) {
  return reviewDescriptor(key).accepted[id] !== false;
}

export function reviewToggleAccept(key, id) {
  const d = reviewDescriptor(key);
  d.onToggleAccept(id);
  d.onRender();
}

export function reviewNotes(notes) {
  if (!notes.length) return '';
  return '<div style="margin-top:4px">' + notes.map(n =>
    `<div style="font-size:11px; color:var(--muted)">· ${esc(n)}</div>`
  ).join('') + '</div>';
}

export function reviewOpenSheet(key, id) {
  reviewDescriptor(key).onOpenSheet(id);
}

export function reviewNode(key, node, cascade, childrenByParent) {
  const d = reviewDescriptor(key);
  const accepted = reviewIsAccepted(key, node.id);
  const reparented = node.parentId != null && cascade.effectiveParent[node.id] !== node.parentId;
  const children = childrenByParent[node.id] || [];
  return `
    <div class="review-node ${accepted ? '' : 'review-rejected'}">
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap">
        <span style="font-weight:600" class="review-name-link" onclick="reviewOpenSheet('${esc(key)}','${esc(node.id)}')">${esc(node.name)}</span>
        <span style="font-size:11px; color:var(--muted)">${esc(node.subtitle || '')}</span>
        ${reparented ? `<span class="badge b-other" style="font-size:10px">${esc(d.reparentedLabel)}</span>` : ''}
        <button class="btn-icon" onclick="reviewToggleAccept('${esc(key)}','${esc(node.id)}')" style="margin-left:auto">
          ${accepted ? 'Rejeter' : 'Accepter'}</button>
      </div>
      ${node.description ? `<div style="font-size:12px; color:var(--muted)">${esc(node.description)}</div>` : ''}
      ${reviewNotes(node.notes)}
      ${node.extras}
      ${children.length ? `<div class="review-children">${children.map(c => reviewNode(key, c, cascade, childrenByParent)).join('')}</div>` : ''}
    </div>`;
}

export function reviewTree(key, cascade) {
  const d = reviewDescriptor(key);
  if (!d.nodes.length) return '<div class="empty">Aucun element propose.</div>';
  const childrenByParent = {};
  for (const n of d.nodes) {
    const p = cascade.effectiveParent[n.id];
    if (p == null) continue;
    (childrenByParent[p] = childrenByParent[p] || []).push(n);
  }
  // BRIEF-0033-c: parent reassignment can set a second location's
  // parent_local_id to null (root fallback, matching the commit's None ->
  // no-parent resolution) — render every top-level location, not just the
  // first found, so a reparented-to-root location stays visible.
  const roots = d.nodes.filter(n => cascade.effectiveParent[n.id] == null);
  if (!roots.length) return '<div class="empty">Aucun element racine dans le brouillon.</div>';
  return roots.map(root => reviewNode(key, root, cascade, childrenByParent)).join('');
}

export function reviewToggleGraph(key) {
  const d = reviewDescriptor(key);
  d.onToggleGraph();
  d.onRender();
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

const LEGACY_BRIDGE_FNS = {
  reviewRegister, reviewDescriptor, reviewCascade, reviewIsAccepted,
  reviewToggleAccept, reviewNotes, reviewOpenSheet, reviewNode, reviewTree,
  reviewToggleGraph, reviewGraphData,
};

/** Installs this module's own functions onto the legacy iframe's window, so
 *  the room batch generator (still legacy, BRIEF-0058-j) keeps calling
 *  reviewRegister/reviewCascade/... as bare globals with zero code change on
 *  its side. Same object identity either way -- REVIEW_DESCRIPTORS is one
 *  module-level singleton regardless of which realm calls into it, so this
 *  is not a second implementation, just a second door onto the same room. */
export function installLegacyReviewBridge(win) {
  Object.assign(win, LEGACY_BRIDGE_FNS);
}
