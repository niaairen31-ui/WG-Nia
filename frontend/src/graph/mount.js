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
   given container. */
import { mount as svelteMount, unmount as svelteUnmount } from 'svelte';
import Graph from './Graph.svelte';
import { legacyContainer } from '../legacy/bridge.js';
import lieux from './consumers/lieux.js';

const CONSUMERS = { lieux };

const live = {}; // containerId -> { node, consumerKey, meta, instance }

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
      if (result === false) return; // consumer aborted (e.g. confirm() declined)
      await reloadGraph(containerId);
    } catch (err) {
      console.error('graph/mount:', err.message);
    }
  };
}

async function renderInto(containerId, consumerKey, meta) {
  const consumer = CONSUMERS[consumerKey];
  if (!consumer) {
    throw new Error(`graph/mount: unknown consumer ${JSON.stringify(consumerKey)}`);
  }
  const node = legacyContainer(containerId);
  node.innerHTML = '';

  let data;
  try {
    data = await consumer.load(meta);
  } catch (err) {
    // Fail-closed over advisory: a failed load renders a visible message,
    // never a silent catch (mirrors the legacy graphLoad() red-text path).
    node.innerHTML = `<p style="padding:12px; color:var(--red); font-size:12px;">${escapeHtml(err.message)}</p>`;
    live[containerId] = { node, consumerKey, meta, instance: null };
    return;
  }

  let mountTarget = node;
  if (consumer.chrome) {
    node.innerHTML = `
      <div class="lieux-graph-head">
        <span>${escapeHtml(consumer.chrome.title)}</span>
        <button class="btn-icon" type="button" title="Rafraîchir">↻</button>
      </div>
      <div class="graph-mount-target"></div>
      <p style="padding:4px 14px 6px; font-size:11px; color:var(--muted)">${escapeHtml(consumer.chrome.helpText)}</p>
    `;
    mountTarget = node.querySelector('.graph-mount-target');
    node.querySelector('button.btn-icon').addEventListener('click', () => reloadGraph(containerId));
  }

  const instance = svelteMount(Graph, {
    target: mountTarget,
    props: {
      nodes: data.nodes,
      edges: data.edges,
      dashedKinds: consumer.dashedKinds || [],
      onConnect: wrapMutator(containerId, consumer.onConnect),
      onDeleteEdge: wrapMutator(containerId, consumer.onDeleteEdge),
      onMoveNode: consumer.onMoveNode || null,
    },
  });
  live[containerId] = { node, consumerKey, meta, instance };
}

export async function mountGraph(containerId, consumerKey, meta = {}) {
  const node = legacyContainer(containerId);
  const existing = live[containerId];
  if (existing) {
    if (existing.node === node) {
      throw new Error(`graph/mount: ${containerId} already has a live graph instance`);
    }
    // The surrounding panel re-emitted its markup (BRIEF-0057-a M8) --
    // the old DOM node, and the instance mounted into it, are already
    // gone. Nothing to unmount; just discard the stale bookkeeping.
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

/* The legacy -> shell signal: one direction of control, no function
   installed on the legacy window. Legacy dispatches CustomEvents on its
   own document; this is the sole listener. */
export function initGraphMount(legacyDoc) {
  legacyDoc.addEventListener('graph:slot', (ev) => {
    const { consumer, containerId, open, key } = ev.detail;
    if (!open) return;
    mountGraph(containerId, consumer, key ? { key } : {}).catch((err) => {
      console.error('graph/mount:', err.message);
    });
  });
  legacyDoc.addEventListener('graph:invalidate', (ev) => {
    const { consumer } = ev.detail;
    Object.keys(live).forEach((containerId) => {
      if (live[containerId].consumerKey === consumer) {
        reloadGraph(containerId).catch((err) => console.error('graph/mount:', err.message));
      }
    });
  });
}
