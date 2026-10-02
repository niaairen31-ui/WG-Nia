/* TICKET-0057. Fetch/write layer for the canonical Lieux adjacency graph.
   All three writes go through pre-existing sanctioned endpoints, unchanged
   and unwidened -- the primitive itself (Graph.svelte) never fetches or
   writes; that invariant is what this file exists to preserve.

   TICKET-0100 (BRIEF-0100-a): a node click opens that location's fiche,
   through the same selectEntity the Lieux list calls -- the relations
   consumer already imports from that module (getSelectedEntityId). The
   shell document IS the document every Creation island receives as
   legacyDoc (creation/mount.js passes node.ownerDocument), so `document`
   is passed.

   TICKET-0101 (BRIEF-0101-F, M1): three modes in the head, one per
   `GET /api/locations/graph?mode=` -- « Lieux visitables » (the travel
   map, `connects_to`), « Zones » (`borde`; top-level zones larger through
   the node's own `r`) and « Ego » (the zone open in the fiche and its
   children; a double-click on a child zone recentres; anything else shows
   « Ouvrez une zone. »). Mode and centre live in the mount's meta, the
   relations consumer's pattern (consumers/relations.js: controls,
   capabilities(meta), defaultMeta). Connecting two nodes in any mode posts
   `connects_to`; the server derives `borde` whenever a zone is an end. A
   `borde` edge is drawn dashed. */
import { getSelectedEntityId, selectEntity } from '../../creation/sheetState.svelte.js';

const MODES = [
  { id: 'visitable', label: 'Lieux visitables' },
  { id: 'zones', label: 'Zones' },
  { id: 'ego', label: 'Ego' },
];

let lastNodes = [];

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
  if (res.status === 204) return null;
  return res.json();
}

export default {
  chrome: {
    title: 'Carte des lieux',
    helpText: (meta) => (meta.mode === 'ego'
      ? 'La zone ouverte dans la fiche et ses lieux enfants. Double-cliquez une zone enfant pour la recentrer. Cliquez un nœud pour ouvrir sa fiche, puis un second pour les relier.'
      : 'Cliquez un nœud pour le sélectionner et ouvrir sa fiche, puis un second pour les relier (« borde » dès qu\'une zone est en jeu). Glissez pour repositionner. Cliquez un lien pour le supprimer.'),
    controls: MODES.map((m) => ({
      id: `mode-${m.id}`, kind: 'button',
      label: (meta) => (meta.mode === m.id ? `● ${m.label}` : m.label),
      onActivate: () => ({ mode: m.id, id: null }),
    })),
  },
  dashedKinds: ['borde'],
  defaultMeta: { mode: 'visitable', id: null },

  async load(meta) {
    const mode = meta.mode || 'visitable';
    let path = `/api/locations/graph?mode=${mode}`;
    if (mode === 'ego') {
      const center = meta.id || getSelectedEntityId();
      if (!center) {
        lastNodes = [];
        return { nodes: [], edges: [], emptyText: 'Ouvrez une zone.' };
      }
      path += `&center=${encodeURIComponent(center)}`;
    }
    const data = await api(path);
    lastNodes = data.nodes;
    return { nodes: data.nodes, edges: data.edges, emptyText: data.empty_text };
  },

  capabilities(meta) {
    return {
      onConnect: async (a, b) => {
        await api(`/api/entities/${encodeURIComponent(a)}/relations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ other_entity_id: b, type: 'connects_to' }),
        });
      },
      onDeleteEdge: async (edgeId) => {
        if (!confirm('Supprimer cette connexion ?')) return false;
        await api(`/api/relations/${encodeURIComponent(edgeId)}`, { method: 'DELETE' });
      },
      onNodeClick: (nodeId) => { selectEntity(document, nodeId); },
      onNodeDblClick: meta.mode === 'ego'
        ? (nodeId) => {
          const node = lastNodes.find((n) => n.id === nodeId);
          return node && node.is_zone ? { id: nodeId } : null;
        }
        : null,
      onMoveNode: async (nodeId, x, y) => {
        // coord_x/coord_y are two scalar columns -- no merge discipline needed
        // (TICKET-0025, BRIEF-0025-b; was a JSON read-merge-write).
        const full = await api(`/api/entities/${encodeURIComponent(nodeId)}`);
        const ext = Object.assign({}, full.extension, { coord_x: Math.round(x), coord_y: Math.round(y) });
        await api(`/api/entities/${encodeURIComponent(nodeId)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entity: full, extension: ext }),
        });
      },
    };
  },
};
