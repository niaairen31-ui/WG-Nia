/* TICKET-0056 (D3b). History-API routing owned ENTIRELY by the shell.
   The legacy frame's src is assigned once and never reassigned
   (LegacyFrame.svelte): an iframe navigation would push an entry onto
   this same history stack and make Back replay legacy boots. Every
   surface change is a pushState here plus a direct bridge call -- never
   a frame navigation. */

// Mirrored verbatim in _SHELL_ROUTES (app.py); legacy_mount.py asserts
// the two agree.
export const SHELL_ROUTES = ["/", "/play", "/creation", "/creation/{sub_tab}", "/observation"];

export function parse(pathname) {
  if (pathname === "/" || pathname === "/play") {
    return { surface: "play", subTab: null };
  }
  if (pathname === "/observation") {
    return { surface: "observation", subTab: null };
  }
  if (pathname === "/creation") {
    return { surface: "creation", subTab: null };
  }
  const creationMatch = pathname.match(/^\/creation\/([^/]+)$/);
  if (creationMatch) {
    return { surface: "creation", subTab: creationMatch[1] };
  }
  return { surface: "play", subTab: null };
}

export function navigate(surface, subTab) {
  const path = surface === "creation" && subTab ? `/creation/${subTab}` : `/${surface}`;
  history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

// TICKET-0058 (BRIEF-0058-k). replaceState, never pushState, and no
// popstate dispatch -- both load-bearing: (1) a pushState per sub-tab
// click would make Back walk backwards through sub-tabs one at a time
// instead of leaving Creation; (2) dispatching popstate would re-enter
// applyRoute and drive the legacy document from a signal it just emitted
// itself, an infinite mirror loop.
export function replace(surface, subTab) {
  const path = surface === "creation" && subTab ? `/creation/${subTab}` : `/${surface}`;
  history.replaceState({}, "", path);
}

export function onRoute(handler) {
  const invoke = () => handler(parse(location.pathname));
  window.addEventListener("popstate", invoke);
  invoke();
}
