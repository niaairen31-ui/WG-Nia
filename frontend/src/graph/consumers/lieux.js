/* TICKET-0057. Fetch/write layer for the canonical Lieux adjacency graph.
   All three writes go through pre-existing sanctioned endpoints, unchanged
   and unwidened -- the primitive itself (Graph.svelte) never fetches or
   writes; that invariant is what this file exists to preserve. */

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
    helpText: 'Cliquez un nœud pour le sélectionner, puis un second pour le connecter. Glissez pour repositionner. Cliquez un lien pour le supprimer.',
  },
  dashedKinds: [],

  async load() {
    return api('/api/locations/graph');
  },

  async onConnect(a, b) {
    await api(`/api/entities/${encodeURIComponent(a)}/relations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ other_entity_id: b, type: 'connects_to' }),
    });
  },

  async onDeleteEdge(edgeId) {
    if (!confirm('Supprimer cette connexion ?')) return false;
    await api(`/api/relations/${encodeURIComponent(edgeId)}`, { method: 'DELETE' });
  },

  async onMoveNode(nodeId, x, y) {
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
