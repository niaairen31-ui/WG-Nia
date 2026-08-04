/* TICKET-0056 (B1). The sole module permitted to reach into the legacy
   document. Shell and legacy are same-origin, so surface switching is a
   direct call on the legacy window -- no postMessage, one direction of
   control. legacy_mount.py confines `contentWindow` / `legacy-frame`
   tokens to this file and LegacyFrame.svelte. */
import { LEGACY_MOUNTS } from './registry.js';

let frame = null;

function legacyWindow() {
  if (!frame) {
    throw new Error('legacy/bridge: mountLegacy(frameEl) has not been called yet');
  }
  return frame.contentWindow;
}

export function mountLegacy(frameEl) {
  frame = frameEl;
  return new Promise((resolve) => {
    frame.addEventListener('load', () => resolve(), { once: true });
  });
}

function callLegacy(fnName, ...args) {
  const win = legacyWindow();
  const fn = win[fnName];
  if (typeof fn !== 'function') {
    throw new Error(`legacy/bridge: ${fnName} is not a function on the legacy window`);
  }
  return fn.apply(win, args);
}

export function showSurface(key) {
  const entry = LEGACY_MOUNTS[key];
  if (!entry) {
    throw new Error(`legacy/bridge: unknown surface key ${JSON.stringify(key)}`);
  }
  callLegacy(entry.showFn);
}

export async function activateWorldViaLegacy(worldId) {
  await callLegacy('activateWorld', worldId);
}

export function openWorldCreate() {
  callLegacy('worldCreateOpen');
}

export function openWorldDelete() {
  callLegacy('worldDeleteOpen');
}

/* TICKET-0056: the legacy header is SUPPRESSED, not deleted -- index.html
   is byte-untouched by this ticket. Injecting one scoped style into the
   frame document is reversible, confined to this module, and covered by
   legacy_mount.py's confinement assertion. */
export function hideLegacyHeader() {
  const doc = legacyWindow().document;
  if (doc.getElementById('shell-injected')) return;
  const style = doc.createElement('style');
  style.id = 'shell-injected';
  style.textContent = 'header { display: none !important; }';
  doc.head.appendChild(style);
}

/* TICKET-0056 (D-ii). showCreationSubTab() early-returns into
   creationInit() when the Creation registry is not loaded yet
   (ARCHITECTURE_DECISIONS, TICKET-0054), so a cold deep-link fired before
   the legacy boot completes would silently do nothing. Hence the bounded
   wait -- and a THROW on timeout, never a resolve-anyway. The unknown-tab
   fallback to 'npc' is not new: it is the same fallback activateWorld()
   already uses when a runtime type has disappeared (index.html).

   Readiness and tab-existence are read from the DOM, not from
   `authorRegistry` / `CREATION_TABS` directly: those are `let`/`const`
   bindings at the legacy script's top level, and a let/const declaration
   is never reflected as a `window` property (unlike a function
   declaration or `var`) -- verified live, `'CREATION_TABS' in win` is
   false. `#creation-shell-title` starts empty in the static markup and is
   set by renderCreationShell(), called only from inside
   _creationActivateTab() after creationInit()'s registry fetch resolves --
   an equivalent, DOM-only readiness signal. Every CREATION_TABS entry,
   static or runtime (TICKET-0046), renders a matching #ctab-<key> button
   by construction (page_contract.py), so DOM presence substitutes for the
   otherwise-invisible CREATION_TABS lookup. */
export async function showCreationTab(tabId) {
  showSurface('creation');
  const win = legacyWindow();
  const doc = win.document;
  await whenLegacyReady(
    () => doc.getElementById('creation-shell-title')?.textContent !== '',
    { timeoutMs: 10000 }
  );
  const resolvedTab = doc.getElementById('ctab-' + tabId) ? tabId : 'npc';
  callLegacy('showCreationSubTab', resolvedTab);
}

/* TICKET-0057. The graph primitive renders as an ISLAND inside the
   legacy document (Creation is a legacy mount until TICKET-0059, and
   TICKET-0056 deferred continuous route sync to TICKET-0058 -- the
   shell cannot know which sub-tab is active, so a shell-side graph
   pane is not constructible). This export hands out a node from the
   legacy document; the `contentWindow` token stays confined to this
   file, so legacy_mount.py assertion 5 is unchanged. */
export function legacyContainer(id) {
  const el = legacyWindow().document.getElementById(id);
  if (!el) {
    throw new Error(`legacy/bridge: no element #${id} in the legacy document`);
  }
  return el;
}

export function legacyDocument() {
  return legacyWindow().document;
}

/* TICKET-0058 (BRIEF-0058-e). The entity-list island's row click needs to
   trigger creationSelectRecord (non-entity record rows: intrigues,
   evenements) -- stays a legacy dispatcher by design (A1 keeps the tab
   mechanism legacy for this ticket), routing to either a still-legacy
   sheetRenderer (intrigues) or a 'creation:record-detail' dispatch
   Sheet.svelte renders natively. An entity row's own selectEntity
   (TICKET-0058, BRIEF-0058-e) and the relations graph consumer's
   getSelectedCharacterId (BRIEF-0058-c) both converged onto
   frontend/src/creation/sheetState.svelte.js (TICKET-0059, BRIEF-0059-e) --
   plain Svelte-to-Svelte imports now, no legacy window involved. */
export function selectRecord(tabId, record) {
  return callLegacy('creationSelectRecord', tabId, record);
}

/* TICKET-0058 (BRIEF-0058-f). Generic passthrough for the sheet's still-legacy
   sub-editor generators (roles/subculture/geometry/doors/relations/knowledge/
   pending-knowledge/pending-goals/pricing/membership-form/disc-detail-form/
   goal-form/generate-panel — all Scope OUT, brief -g/-h) and loaders
   (authorLoadItems/Ledger/Memberships/Goals/FactionMembersPanel/DiscDetails,
   authorMembershipFactionChanged) Sheet.svelte calls after rendering its own
   skeleton — exactly the tail authorRenderSheet used to run inline, just
   invoked from across the shell/legacy boundary instead of in the same
   function body. Every one of these stays a plain, unmigrated legacy
   function; nothing about their own behavior changes. */
export function legacyCall(fnName, ...args) {
  return callLegacy(fnName, ...args);
}

export function whenLegacyReady(predicate, { timeoutMs = 5000 } = {}) {
  const win = legacyWindow();
  return new Promise((resolve, reject) => {
    const start = Date.now();
    function poll() {
      let ok;
      try {
        ok = predicate(win);
      } catch (err) {
        reject(err);
        return;
      }
      if (ok) {
        resolve();
        return;
      }
      if (Date.now() - start >= timeoutMs) {
        reject(new Error('legacy/bridge: whenLegacyReady timed out'));
        return;
      }
      setTimeout(poll, 50);
    }
    poll();
  });
}
