/* TICKET-0057. The mount/teardown registry -- the only code that knows
   HOW a graph consumer's data reaches a legacy container. Consumers stay
   pure fetch/write modules; Graph.svelte stays a pure renderer; this file
   is the seam that wires one to the other inside the legacy document.

   Chrome (head bar, refresh control, help text) is built here, generically,
   from an optional per-consumer `chrome` descriptor -- never inside
   Graph.svelte, whose prop contract carries no title/help text (E1: no
   axis a pilot consumer doesn't exercise). Consumers with their own
   surrounding chrome (the review pre-commit previews, re-emitted by their
   panel's own re-render) simply omit `chrome` and mount straight into the
   given container.

   TICKET-0058 (BRIEF-0058-c) extends this generic layer for the relations
   consumer, the second one to need more than a title: `chrome.controls`
   (buttons/checkboxes rendered in the head bar, each returning a meta
   PATCH that triggers a full remount -- mode/arm/bucket state all live in
   `live[containerId].meta`, never in the consumer's own module scope, so
   a tab re-entry's fresh mount always starts from `consumer.defaultMeta`)
   and `chrome.sidePanel` (a second mount-target column the consumer owns
   directly via `consumer.bindSidePanel(el, helpers)` -- the primitive
   itself never renders an info card or an edit form; those are "consumer-
   owned DOM beside the mount target," per the brief). A consumer may also
   export `capabilities(meta)` instead of static onConnect/onDeleteEdge/...
   fields, when which callbacks are even active depends on view state (the
   relations consumer's global "Lier" arm, or ego's permanent read-only
   posture) -- lieux/review, which never vary, are used directly as their
   own static capability set. */
import { mount as svelteMount, unmount as svelteUnmount } from 'svelte';
import Graph from './Graph.svelte';
import lieux from './consumers/lieux.js';
import review from './consumers/review.js';
import relations from './consumers/relations.js';

const CONSUMERS = { lieux, review, relations };

const live = {}; // containerId -> { node, consumerKey, meta, instance, data }

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function wrapMutator(containerId, fn) {
  if (!fn) return null;
  return async (...args) => {
    try {
      const result = await fn(...args);
      if (result === false) return; // consumer aborted (e.g. confirm() declined, or just opened a form)
      await reloadGraph(containerId);
    } catch (err) {
      console.error('graph/mount:', err.message);
    }
  };
}

/** Like wrapMutator, but the consumer's return value is a META PATCH (or
 *  nothing) rather than a reload signal -- used for interactions that
 *  change VIEW STATE (which node is centred) rather than writing canon:
 *  the ego-mode double-click recentre is the first consumer of this. */
function wrapRemounter(containerId, fn) {
  if (!fn) return null;
  return async (...args) => {
    try {
      const patch = await fn(...args);
      if (patch == null || patch === false) return;
      await remountGraph(containerId, patch);
    } catch (err) {
      console.error('graph/mount:', err.message);
    }
  };
}

/** Plain notification callbacks (node click, edge click) never reload or
 *  remount on their own -- whatever DOM they touch is the consumer's own
 *  side panel, updated synchronously in place. */
function wrapPlain(fn) {
  if (!fn) return null;
  return (...args) => {
    try {
      fn(...args);
    } catch (err) {
      console.error('graph/mount:', err.message);
    }
  };
}

function renderControls(controls, meta) {
  return controls
    .filter((c) => !c.visible || c.visible(meta))
    .map((c) => {
      const label = escapeHtml(c.label(meta));
      if (c.kind === 'checkbox') {
        return `<label style="font-size:11px; font-weight:400; display:flex; align-items:center; gap:4px">
          <input type="checkbox" data-control="${escapeHtml(c.id)}" ${c.checked(meta) ? 'checked' : ''}> ${label}
        </label>`;
      }
      return `<button class="btn-icon" data-control="${escapeHtml(c.id)}">${label}</button>`;
    })
    .join('');
}

function wireControls(node, controls, containerId, meta) {
  controls.forEach((c) => {
    const el = node.querySelector(`[data-control="${c.id}"]`);
    if (!el) return;
    const evt = c.kind === 'checkbox' ? 'change' : 'click';
    el.addEventListener(evt, () => {
      const patch = c.onActivate(meta, c.kind === 'checkbox' ? el.checked : undefined);
      if (patch) remountGraph(containerId, patch).catch((err) => console.error('graph/mount:', err.message));
    });
  });
}

async function renderInto(containerId, consumerKey, meta) {
  const consumer = CONSUMERS[consumerKey];
  if (!consumer) {
    throw new Error(`graph/mount: unknown consumer ${JSON.stringify(consumerKey)}`);
  }
  const node = document.getElementById(containerId);
  if (!node) {
    throw new Error(`graph/mount: no element #${containerId} in the shell document`);
  }
  node.innerHTML = '';

  const effectiveMeta = { ...(consumer.defaultMeta || {}), ...meta };

  let data;
  try {
    data = await consumer.load(effectiveMeta);
  } catch (err) {
    // Fail-closed over advisory: a failed load renders a visible message,
    // never a silent catch (mirrors the legacy graphLoad() red-text path).
    node.innerHTML = `<p style="padding:12px; color:var(--red); font-size:12px;">${escapeHtml(err.message)}</p>`;
    live[containerId] = { node, consumerKey, meta: effectiveMeta, instance: null, data: null };
    return;
  }

  let mountTarget = node;
  let sidePanel = null;
  if (consumer.chrome) {
    const helpText = typeof consumer.chrome.helpText === 'function'
      ? consumer.chrome.helpText(effectiveMeta)
      : consumer.chrome.helpText;
    const controlsHtml = renderControls(consumer.chrome.controls || [], effectiveMeta);
    node.innerHTML = `
      <div class="lieux-graph-head">
        <span>${escapeHtml(consumer.chrome.title)}</span>
        ${controlsHtml}
        <button class="btn-icon" data-control="_refresh" title="Rafraîchir" style="${controlsHtml ? '' : 'margin-left:auto'}">↻</button>
      </div>
      <div style="display:flex; gap:0">
        <div class="graph-mount-target" style="flex:1"></div>
        ${consumer.chrome.sidePanel
          ? '<div class="graph-side-panel" style="width:220px; flex-shrink:0; padding:10px; font-size:12px; border-left:1px solid var(--border)"></div>'
          : ''}
      </div>
      <p style="padding:4px 14px 6px; font-size:11px; color:var(--muted)">${escapeHtml(helpText || '')}</p>
    `;
    mountTarget = node.querySelector('.graph-mount-target');
    sidePanel = node.querySelector('.graph-side-panel');
    node.querySelector('button[data-control="_refresh"]').addEventListener('click', () => reloadGraph(containerId));
    wireControls(node, consumer.chrome.controls || [], containerId, effectiveMeta);
  }

  const caps = typeof consumer.capabilities === 'function' ? consumer.capabilities(effectiveMeta) : consumer;

  const instance = svelteMount(Graph, {
    target: mountTarget,
    props: {
      nodes: data.nodes,
      edges: data.edges,
      dashedKinds: consumer.dashedKinds || [],
      layout: consumer.layout || 'positional',
      onConnect: wrapMutator(containerId, caps.onConnect),
      onDeleteEdge: wrapMutator(containerId, caps.onDeleteEdge),
      onEdgeClick: wrapPlain(caps.onEdgeClick),
      onMoveNode: caps.onMoveNode || null,
      onNodeClick: wrapPlain(caps.onNodeClick),
      onNodeDblClick: wrapRemounter(containerId, caps.onNodeDblClick),
    },
  });
  live[containerId] = { node, consumerKey, meta: effectiveMeta, instance, data };

  if (sidePanel && consumer.bindSidePanel) {
    consumer.bindSidePanel(sidePanel, {
      reload: () => reloadGraph(containerId),
      remount: (patch) => remountGraph(containerId, patch),
    });
  }
}

export async function mountGraph(containerId, consumerKey, meta = {}) {
  const node = document.getElementById(containerId);
  if (!node) {
    throw new Error(`graph/mount: no element #${containerId} in the shell document`);
  }
  const existing = live[containerId];
  if (existing) {
    // Either the same node (a fresh open after the panel was hidden and
    // shown again -- BRIEF-0058-c: on-demand slots never destroy their
    // container, only toggle display:none) or the surrounding panel
    // re-emitted its markup (BRIEF-0057-a M8) and the old DOM node is
    // already gone. Either way the previous Svelte instance is torn down
    // explicitly so it is never left orphaned, mounted or not.
    if (existing.instance) {
      try {
        svelteUnmount(existing.instance);
      } catch (_err) {
        // Already-detached target; the instance is discarded regardless.
      }
    }
    delete live[containerId];
  }
  await renderInto(containerId, consumerKey, meta);
}

export function unmountGraph(containerId) {
  const existing = live[containerId];
  if (!existing) return;
  if (existing.instance) svelteUnmount(existing.instance);
  delete live[containerId];
}

export async function reloadGraph(containerId) {
  const existing = live[containerId];
  if (!existing) return;
  const { consumerKey, meta } = existing;
  unmountGraph(containerId);
  await mountGraph(containerId, consumerKey, meta);
}

/** Remounts with `meta` patched -- the seam for any view-state change that
 *  needs fresh data (ego recentre, mode switch, arm toggle, bucket
 *  filter): mode/armed/buckets all live in the patched meta object, never
 *  in a consumer's own module-scoped variables, so a tab re-entry's next
 *  fresh mount always starts clean from `consumer.defaultMeta`. */
export async function remountGraph(containerId, metaPatch = {}) {
  const existing = live[containerId];
  if (!existing) return;
  const { consumerKey, meta } = existing;
  unmountGraph(containerId);
  await mountGraph(containerId, consumerKey, { ...meta, ...metaPatch });
}

/* TICKET-0065 (BRIEF-0065-b). One document, one bus. Creation stopped
   living in the legacy iframe at TICKET-0059, which moved every graph
   mount target into the shell document and every dispatcher onto it --
   but this listener stayed on the legacy document, so no graph mounted
   at all. There is no cross-document signal left here: dispatchers and
   listeners are both `document`, and graph_primitive.py rule 11 holds
   that identity structurally. */
export function initGraphMount() {
  document.addEventListener('graph:slot', (ev) => {
    const { consumer, containerId, open, key } = ev.detail;
    if (!open) return;
    mountGraph(containerId, consumer, key ? { key } : {}).catch((err) => {
      console.error('graph/mount:', err.message);
    });
  });
  document.addEventListener('graph:invalidate', (ev) => {
    const { consumer, meta: metaPatch } = ev.detail;
    Object.keys(live).forEach((containerId) => {
      if (live[containerId].consumerKey === consumer) {
        const p = metaPatch ? remountGraph(containerId, metaPatch) : reloadGraph(containerId);
        p.catch((err) => console.error('graph/mount:', err.message));
      }
    });
  });
}
