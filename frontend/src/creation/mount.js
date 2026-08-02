/* TICKET-0058 (BRIEF-0058-d). The island mount seam -- generalises
   frontend/src/graph/mount.js's legacy -> shell CustomEvent shape to
   arbitrary Creation panels, so briefs -e..-j have one way to mount and
   only one.

   Two one-way signals, both legacy -> shell, no function installed on the
   legacy window:
     'island:slot'   -- legacy activated a tab whose body is an island;
                        mount (or reconcile) it.
     'island:action' -- the legacy shell's standard primary-action band was
                        clicked; forward the click to the mounted
                        component's own exported primaryAction().
   The one exception, component -> legacy (a mounted island telling legacy
   its own tab bar needs refreshing) is NOT this file's concern -- it is a
   component-owned CustomEvent on the legacy document itself (see
   Constructeur.svelte's `legacyDoc` prop and index.html's listener),
   because generalising THIS file to relay it would be exactly the
   "shared island base class" the brief scopes out.

   frontend/src/creation/registry.js is the DATA this file's containerId
   resolution is checked against; the actual component classes are
   imported here -- the one file (besides graph/mount.js, a distinct,
   already-established mechanism) permitted to call svelteMount/unmount on
   a legacy-document target for a Creation island. */
import { mount as svelteMount, unmount as svelteUnmount } from 'svelte';
import { legacyContainer } from '../legacy/bridge.js';
import { CREATION_ISLANDS } from './registry.js';
import { creationState } from './state.svelte.js';
import Constructeur from './Constructeur.svelte';
import EntityList from './EntityList.svelte';

const COMPONENTS = { constructeur: Constructeur, entityList: EntityList };

const live = {}; // key -> { node, instance }

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

/** Mounts (or, on a repeat call into the SAME still-live container node,
 *  no-ops) the island registered under `key`. RECON-0058-a M5's finding
 *  drives the shape here exactly: since BRIEF-0058-d also removes the
 *  legacy loader that used to wipe #creation-constructeur's innerHTML on
 *  every tab-enter/world-switch, a repeat 'island:slot' dispatch (which
 *  now fires on EVERY activation, not just the first) finds the same DOM
 *  node still standing and is a no-op -- effectively mount-once. If some
 *  future island's surrounding panel DOES re-emit its markup between
 *  activations, the node-identity check below falls through to a full
 *  remount, the same reconciliation graph/mount.js's mountGraph already
 *  relies on for the identical situation. A failed mount renders a
 *  visible message into the container, never a silent catch. */
export function mountIsland(key) {
  const entry = CREATION_ISLANDS[key];
  const Component = COMPONENTS[key];
  if (!entry || !Component) {
    throw new Error(`creation/mount: unknown island ${JSON.stringify(key)}`);
  }
  const node = legacyContainer(entry.containerId);
  const existing = live[key];
  if (existing && existing.node === node) {
    return;
  }
  if (existing) {
    try {
      svelteUnmount(existing.instance);
    } catch (_err) {
      // Already-detached target; the instance is discarded regardless.
    }
    delete live[key];
  }
  try {
    const instance = svelteMount(Component, { target: node, props: { legacyDoc: node.ownerDocument } });
    live[key] = { node, instance };
  } catch (err) {
    node.innerHTML = `<p style="padding:12px; color:var(--red); font-size:12px;">${escapeHtml(err.message)}</p>`;
  }
}

export function unmountIsland(key) {
  const existing = live[key];
  if (!existing) return;
  try {
    svelteUnmount(existing.instance);
  } catch (_err) {
    // Already-detached target; the instance is discarded regardless.
  }
  delete live[key];
}

/* The legacy -> shell signal, both directions of it: one listener each,
   no function installed on the legacy window. */
export function initCreationMount(legacyDoc) {
  legacyDoc.addEventListener('island:slot', (ev) => {
    const { key, open, tabKey } = ev.detail;
    if (!open) return;
    // BRIEF-0058-e: 'entityList' is one component shared by seven
    // CREATION_TABS entries; tabKey is the only way it learns which of
    // them just activated. Mirrored here (not inside mountIsland, which
    // several islands share) so every island:slot dispatch keeps the
    // store's mirror of the legacy document's own decision current,
    // whether or not that key's mount is a no-op this time. creation_
    // island.py rule 8 confines 'island:slot' listening to this file
    // alone, so EntityList.svelte reacts to these store fields instead
    // of listening for the event itself; the tick increments on every
    // 'entityList' activation so a same-key repeat (e.g. re-entering a
    // tab) still triggers a refetch, matching the old per-activation
    // authorLoadEntityList cadence.
    if (tabKey !== undefined) creationState.activeTabKey = tabKey;
    if (key === 'entityList') creationState.entityListActivationTick += 1;
    try {
      mountIsland(key);
    } catch (err) {
      console.error('creation/mount:', err.message);
    }
  });

  legacyDoc.addEventListener('island:action', (ev) => {
    const { key } = ev.detail;
    const existing = live[key];
    if (existing && typeof existing.instance.primaryAction === 'function') {
      existing.instance.primaryAction();
      return;
    }
    const msg = `creation/mount: island:action fired for ${JSON.stringify(key)} with no mounted primaryAction()`;
    console.error(msg);
    const entry = CREATION_ISLANDS[key];
    if (!entry) return;
    try {
      legacyContainer(entry.containerId).innerHTML =
        `<p style="padding:12px; color:var(--red); font-size:12px;">${escapeHtml(msg)}</p>`;
    } catch (_err) {
      // Container itself missing; nothing to render the refusal into.
    }
  });
}
