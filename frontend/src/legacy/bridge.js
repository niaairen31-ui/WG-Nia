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

/* TICKET-0057. The review pre-commit preview derives its {nodes, edges}
   from in-memory drafts already living in the legacy document -- no
   fetch of its own. reviewGraphData is a plain function declaration, so
   the existing callLegacy mechanism reaches it like any other legacy
   entry point; no new confinement-relevant token is introduced. */
export function reviewGraphData(key) {
  return callLegacy('reviewGraphData', key);
}

/* TICKET-0058 (BRIEF-0058-c). The relations consumer's ego mode needs the
   currently-selected NPC at load time, and `authorEntityId` is a bare
   `let` -- never a `window` property (see showCreationTab's note above).
   `authorGetSelectedEntityId` is the one-line function-declaration
   accessor this reaches through; no other state crosses this seam. */
export function getSelectedCharacterId() {
  return callLegacy('authorGetSelectedEntityId');
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
