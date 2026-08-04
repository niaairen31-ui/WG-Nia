/* TICKET-0058 (BRIEF-0058-c). Fetch/write layer for the NPC relation
   ego/global graph -- the last graph consumer to converge onto the
   primitive (frontend/src/graph/registry.js's `relation_cytoscape`,
   retired in this same commit).

   View state (mode/armed/buckets/id) lives ENTIRELY in the meta object
   mount.js patches and remounts with -- never in a module-level `let`
   here -- so a tab re-entry's next fresh mount always starts clean from
   `defaultMeta`, exactly like the legacy `_relGraphReset()` it replaces.
   The one thing this module DOES keep in its own scope is `lastData` (the
   last successfully loaded {nodes, edges, mode, centerId}) and the side
   panel's DOM node: neither is view state a remount should reset, both
   are needed to render the info card/edit form the primitive itself
   never draws.

   Ego mode supplies neither onConnect nor onEdgeClick -- permanently
   display-only by callback absence (capabilities(meta), not a boolean),
   matching relation_graph.py's amended clause 4. Global mode's "Lier"
   arm is itself a meta flag (`armed`), not module state, so it resets to
   off on every remount just like the old code's mode-switch/tab-reset did.

   Ego mode's centerId (below) read the legacy window through legacy/bridge.js's
   getSelectedCharacterId() until TICKET-0059 (BRIEF-0059-e) ported the
   entity sheet's own selection into frontend/src/creation/sheetState.svelte.js
   -- a plain Svelte-to-Svelte import replaces the bridge call. */
import { getSelectedEntityId } from '../../creation/sheetState.svelte.js';

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

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

const DEFAULT_BUCKETS = { 1: true, 2: true, 3: true, 4: true };

function bucketOf(intensity) {
  if (intensity <= 25) return 1;
  if (intensity <= 50) return 2;
  if (intensity <= 75) return 3;
  return 4;
}

let sidePanelEl = null;
let panelHelpers = null; // { reload, remount }
let lastData = { nodes: [], edges: [], mode: 'ego', centerId: null };

function renderEmptyPanel() {
  if (!sidePanelEl) return;
  sidePanelEl.innerHTML = '<div class="empty">Cliquez un nœud pour voir ses informations.</div>';
}

function renderNodeInfo(nodeId) {
  if (!sidePanelEl) return;
  const node = lastData.nodes.find((n) => n.id === nodeId);
  if (!node) { sidePanelEl.innerHTML = '<div class="empty">Nœud introuvable.</div>'; return; }
  const isGlobal = lastData.mode === 'global';
  const centerId = lastData.centerId;
  const rels = isGlobal
    ? lastData.edges.filter((e) => e.entity_a_id === nodeId || e.entity_b_id === nodeId)
    : lastData.edges.filter((e) =>
        (e.entity_a_id === nodeId && e.entity_b_id === centerId) ||
        (e.entity_a_id === centerId && e.entity_b_id === nodeId)
      );
  const relsHtml = rels.length
    ? rels.map((e) => `
        <div style="margin-top:6px">
          <span class="badge b-other" style="font-size:10px">${escapeHtml(e.type)}</span>
          <div style="font-size:11px; color:var(--muted)">intensité ${e.intensity} · ${escapeHtml(e.direction)}</div>
        </div>`).join('')
    : `<div class="empty" style="font-size:11px">${isGlobal ? 'Aucune relation.' : 'Aucune relation directe avec le centre.'}</div>`;
  sidePanelEl.innerHTML = `
    <div style="font-weight:600">${escapeHtml(node.name)}</div>
    <div style="color:var(--muted); font-size:11px">${escapeHtml(node.character_type || '')}</div>
    ${node.description ? `<div style="margin-top:6px; font-size:12px">${escapeHtml(node.description)}</div>` : ''}
    <div style="margin-top:10px; font-weight:600; font-size:11px">${isGlobal ? 'Relations' : 'Relations avec le centre'}</div>
    ${relsHtml}
  `;
}

/** Global-mode create/edit form -- writes go through the pre-existing
 *  sanctioned relation CRUD routes only, then reload via the helpers
 *  handed to bindSidePanel (never a direct mount.js import: consumers
 *  stay one-way dependents of mount.js, never the reverse). */
function renderEdgeForm(ctx) {
  if (!sidePanelEl) return;
  const isEdit = ctx.mode === 'edit';
  const sourceId = isEdit ? ctx.edge.entity_a_id : ctx.sourceId;
  const targetId = isEdit ? ctx.edge.entity_b_id : ctx.targetId;
  const sourceName = (lastData.nodes.find((n) => n.id === sourceId) || {}).name || sourceId;
  const targetName = (lastData.nodes.find((n) => n.id === targetId) || {}).name || targetId;
  const type = isEdit ? ctx.edge.type : '';
  const intensity = isEdit ? ctx.edge.intensity : 50;
  const direction = isEdit ? ctx.edge.direction : 'mutual';
  const notes = isEdit ? (ctx.edge.notes || '') : '';
  const dirOpt = (v, label) => `<option value="${v}"${direction === v ? ' selected' : ''}>${label}</option>`;

  sidePanelEl.innerHTML = `
    <div style="font-weight:600">${isEdit ? 'Modifier le lien' : 'Nouveau lien'}</div>
    <div style="color:var(--muted); font-size:11px; margin-top:4px">${escapeHtml(sourceName)} → ${escapeHtml(targetName)}</div>
    <label style="display:block; margin-top:8px; font-size:11px">Type
      <input data-f="type" type="text" value="${escapeHtml(type)}" style="width:100%; box-sizing:border-box">
    </label>
    <label style="display:block; margin-top:6px; font-size:11px">Intensité (1-100)
      <input data-f="intensity" type="number" min="1" max="100" value="${escapeHtml(String(intensity))}" style="width:100%; box-sizing:border-box">
    </label>
    <label style="display:block; margin-top:6px; font-size:11px">Direction
      <select data-f="direction" style="width:100%; box-sizing:border-box">
        ${dirOpt('mutual', 'mutual')}${dirOpt('a_to_b', 'a_to_b')}${dirOpt('b_to_a', 'b_to_a')}
      </select>
    </label>
    <label style="display:block; margin-top:6px; font-size:11px">Notes
      <textarea data-f="notes" rows="3" style="width:100%; box-sizing:border-box">${escapeHtml(notes)}</textarea>
    </label>
    <div style="margin-top:10px; display:flex; gap:6px; flex-wrap:wrap">
      <button class="btn-icon" data-a="save">Enregistrer</button>
      ${isEdit ? '<button class="btn-icon" data-a="delete">Supprimer</button>' : ''}
      <button class="btn-icon" data-a="cancel">Annuler</button>
    </div>
  `;
  const field = (name) => sidePanelEl.querySelector(`[data-f="${name}"]`).value;
  sidePanelEl.querySelector('[data-a="save"]').addEventListener('click', async () => {
    const typeVal = field('type').trim();
    if (!typeVal) { alert('Le type est requis.'); return; }
    const body = {
      type: typeVal,
      intensity: Number(field('intensity')),
      direction: field('direction'),
      notes: field('notes'),
    };
    try {
      if (isEdit) {
        await api(`/api/relations/${encodeURIComponent(ctx.edge.id)}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
      } else {
        await api(`/api/entities/${encodeURIComponent(sourceId)}/relations`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ other_entity_id: targetId, ...body }),
        });
      }
      await panelHelpers.reload();
    } catch (err) {
      alert(err.message);
    }
  });
  if (isEdit) {
    sidePanelEl.querySelector('[data-a="delete"]').addEventListener('click', async () => {
      if (!confirm('Supprimer ce lien ?')) return;
      try {
        await api(`/api/relations/${encodeURIComponent(ctx.edge.id)}`, { method: 'DELETE' });
        await panelHelpers.reload();
      } catch (err) {
        alert(err.message);
      }
    });
  }
  sidePanelEl.querySelector('[data-a="cancel"]').addEventListener('click', renderEmptyPanel);
}

export default {
  chrome: {
    title: 'Graphe de relations',
    sidePanel: true,
    helpText: (meta) => (meta.mode === 'global'
      ? 'Molette pour zoomer, glisser pour déplacer. Cliquez un nœud pour ses informations. « Lier » puis cliquez deux nœuds pour créer un lien ; cliquez un lien pour le modifier ou le supprimer.'
      : 'Molette pour zoomer, glisser pour déplacer. Cliquez un nœud pour ses informations, double-cliquez pour le recentrer. Lecture seule — aucune modification de relation depuis ce graphe.'),
    controls: [
      {
        id: 'mode', kind: 'button',
        label: (meta) => (meta.mode === 'global' ? 'Ego' : 'Global'),
        onActivate: (meta) => ({ mode: meta.mode === 'global' ? 'ego' : 'global', armed: false }),
      },
      {
        id: 'arm', kind: 'button',
        visible: (meta) => meta.mode === 'global',
        label: (meta) => (meta.armed ? 'Lier (annuler)' : 'Lier'),
        onActivate: (meta) => ({ armed: !meta.armed }),
      },
      ...[1, 2, 3, 4].map((b) => ({
        id: `bucket-${b}`, kind: 'checkbox',
        label: () => ({ 1: 'Rouge (1-25)', 2: 'Orange (26-50)', 3: 'Bleu (51-75)', 4: 'Vert (76-100)' }[b]),
        checked: (meta) => (meta.buckets || DEFAULT_BUCKETS)[b],
        onActivate: (meta, checked) => ({ buckets: { ...(meta.buckets || DEFAULT_BUCKETS), [b]: checked } }),
      })),
    ],
  },
  layout: 'force',
  defaultMeta: { mode: 'ego', armed: false, buckets: DEFAULT_BUCKETS, id: null },

  bindSidePanel(el, helpers) {
    sidePanelEl = el;
    panelHelpers = helpers;
    renderEmptyPanel();
  },

  async load(meta) {
    const buckets = meta.buckets || DEFAULT_BUCKETS;
    let raw;
    let centerId = null;
    if (meta.mode === 'global') {
      raw = await api('/api/relation-graph');
    } else {
      centerId = meta.id || getSelectedEntityId();
      if (!centerId) {
        lastData = { nodes: [], edges: [], mode: 'ego', centerId: null };
        return { nodes: [], edges: [] };
      }
      raw = await api(`/api/characters/${encodeURIComponent(centerId)}/relation-graph`);
      centerId = raw.center;
    }
    const edges = raw.edges
      .filter((e) => buckets[bucketOf(e.intensity)])
      .map((e) => ({ ...e, entity_a_id: e.source, entity_b_id: e.target }));
    lastData = { nodes: raw.nodes, edges, mode: meta.mode || 'ego', centerId };
    return { nodes: raw.nodes, edges };
  },

  capabilities(meta) {
    if (meta.mode === 'global') {
      return {
        onNodeClick: (nodeId) => renderNodeInfo(nodeId),
        onConnect: meta.armed
          ? (a, b) => { renderEdgeForm({ mode: 'create', sourceId: a, targetId: b }); return false; }
          : null,
        onEdgeClick: (edgeId) => {
          const edge = lastData.edges.find((e) => e.id === edgeId);
          if (edge) renderEdgeForm({ mode: 'edit', edge });
        },
      };
    }
    return {
      onNodeClick: (nodeId) => renderNodeInfo(nodeId),
      onNodeDblClick: (nodeId) => ({ id: nodeId }),
    };
  },
};
