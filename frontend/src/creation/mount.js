/* TICKET-0058 (BRIEF-0058-d). The island mount seam -- generalises
   frontend/src/graph/mount.js's legacy -> shell CustomEvent shape to
   arbitrary Creation panels, so briefs -e..-j have one way to mount and
   only one.

   TICKET-0059 (BRIEF-0059-l commit 1, item 5). Creation stopped living in
   the legacy iframe: its containers are children of Creation.svelte's own
   template now, in the SAME document this module runs in, so 'island:slot'
   / 'island:action' are no longer a cross-document signal -- they are
   ordinary same-document function calls. `activateIsland`/
   `triggerPrimaryAction` below replace both dispatches; nothing here talks
   to itself across an event bus any more. Container resolution moved from
   `legacyContainer(id)` (the iframe document) to `document.getElementById(id)`
   (this module's own global `document`, which IS the shell document Creation
   .svelte renders into).

   `mutations:proposed` is the one signal that stays cross-document
   (initCreationMount(legacyDoc) below): it originates in Play, which is
   still legacy.

   frontend/src/creation/registry.js is the DATA this file's containerId
   resolution is checked against; the actual component classes are
   imported here -- the one file (besides graph/mount.js, a distinct,
   already-established mechanism) permitted to call svelteMount/unmount on
   a Creation island. */
import { mount as svelteMount, unmount as svelteUnmount } from 'svelte';
import { CREATION_ISLANDS } from './registry.js';
import { creationState } from './state.svelte.js';
import { setFilter } from './queue.svelte.js';
import Constructeur from './Constructeur.svelte';
import EntityList from './EntityList.svelte';
import Sheet from './Sheet.svelte';
import Region from './Region.svelte';
import RoomBatch from './RoomBatch.svelte';
import NpcAgent from './NpcAgent.svelte';
import LinkAgent from './LinkAgent.svelte';
import Artefacts from './Artefacts.svelte';
import Competences from './Competences.svelte';
import Registre from './Registre.svelte';
import Prompts from './Prompts.svelte';
import PjSkillFiche from './PjSkillFiche.svelte';
import QueueFilters from './QueueFilters.svelte';
import Queue from './Queue.svelte';
import QueueBatchBar from './QueueBatchBar.svelte';

const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, competences: Competences, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar };

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
  const node = document.getElementById(entry.containerId);
  if (!node) {
    throw new Error(`creation/mount: no element #${entry.containerId} in the document`);
  }
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

/** Replaces the old 'island:slot' dispatch (BRIEF-0059-l item 5): mirrors
 *  the activation into creationState the same way the event listener used
 *  to, then mounts. 'entityList' is one component shared by seven
 *  CREATION_TABS entries; tabKey is the only way it learns which of them
 *  just activated -- mirrored here (not inside mountIsland, which several
 *  islands share) so every activation keeps the store's mirror of the
 *  active tab current, whether or not that key's mount is a no-op this
 *  time. The tick increments on EVERY 'entityList' activation so a
 *  same-key repeat (e.g. re-entering a tab) still triggers a refetch,
 *  matching the old per-activation authorLoadEntityList cadence. */
export function activateIsland(key, tabKey) {
  if (tabKey !== undefined) creationState.activeTabKey = tabKey;
  if (key === 'entityList') creationState.entityListActivationTick += 1;
  try {
    mountIsland(key);
  } catch (err) {
    console.error('creation/mount:', err.message);
  }
}

/** Replaces the old 'island:action' dispatch (BRIEF-0059-l item 5): the
 *  standard shell band's primaryAction button forwards its click to the
 *  mounted component's own exported primaryAction(), by direct call. */
export function triggerPrimaryAction(key) {
  const existing = live[key];
  if (existing && typeof existing.instance.primaryAction === 'function') {
    existing.instance.primaryAction();
    return;
  }
  const msg = `creation/mount: triggerPrimaryAction fired for ${JSON.stringify(key)} with no mounted primaryAction()`;
  console.error(msg);
  const entry = CREATION_ISLANDS[key];
  if (!entry) return;
  try {
    document.getElementById(entry.containerId).innerHTML =
      `<p style="padding:12px; color:var(--red); font-size:12px;">${escapeHtml(msg)}</p>`;
  } catch (_err) {
    // Container itself missing; nothing to render the refusal into.
  }
}

/* The one remaining legacy -> shell signal: 'mutations:proposed' still
   crosses the iframe boundary because Play, its source, is still legacy
   (BRIEF-0059-k). */
export function initCreationMount(legacyDoc) {
  // BRIEF-0059-k: Play's analyzeConv states a fact ('mutations:proposed')
  // instead of commanding the Review Queue's own filter (setFilterByName/
  // loadQueue, both retired by this brief). Registered here, not inside
  // queue.svelte.js, because that module is evaluated at app boot -- before
  // legacyDoc exists -- while this function only runs once the legacy
  // iframe has actually loaded (App.svelte's onLegacyReady).
  legacyDoc.addEventListener('mutations:proposed', () => {
    setFilter('proposed');
  });
}
