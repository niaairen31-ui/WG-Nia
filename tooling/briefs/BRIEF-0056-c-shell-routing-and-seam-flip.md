# BRIEF — Step "enumerated shell routing (D3b) + seam flip (E1)"

## MINI-RECON — run before executing this brief

Report-only. Confirm empirically; on any failure STOP and escalate.

```bash
git log --oneline -3                       # BRIEF-0056-b is the tip
grep -n "def serve_ui\|def serve_shell\|def serve_legacy\|app.mount" src/world_engine/cockpit/app.py
grep -c 'app.include_router' src/world_engine/cockpit/app.py
grep -rn 'prefix="/api"' src/world_engine/cockpit/crud/_router.py
grep -n "function showCreationSubTab" -A 8 src/world_engine/cockpit/index.html
grep -n "CREATION_TABS\[currentCreationSubTab\] ? currentCreationSubTab : 'npc'" src/world_engine/cockpit/index.html
grep -n "^const CREATION_TABS\|^let CREATION_TABS\|CREATION_TABS = {" src/world_engine/cockpit/index.html | head -3
grep -n "creationInit\b" src/world_engine/cockpit/index.html | head -5
python tooling/verify/checks/legacy_mount.py && python tooling/verify/checks/page_contract.py
```

Assertions that must hold:

1. `app.py` has `serve_ui` (`/`), `serve_shell` (`/shell`), `serve_legacy`
   (`/legacy`), and the `/static` mount; routers are all included BEFORE any
   of those route definitions.
2. `crud/_router.py` declares `prefix="/api"` — i.e. its route literals do NOT
   carry `/api` in their text. **This is the fact that kills the catch-all
   (D3a) and justifies enumeration.** If it has changed, escalate.
3. `showCreationSubTab(tab)` early-returns into `creationInit()` when the
   registry is not loaded, and `CREATION_TABS` is a top-level registry object.
   **The readiness wait in this brief exists because of that early return** —
   if it is gone, escalate rather than silently dropping the wait.
4. The `'npc'` fallback expression exists in `activateWorld`. This brief reuses
   the same fallback; if it is gone, escalate.
5. `legacy_mount.py` and `page_contract.py` are green before any edit.

## Context

The shell has chrome and a legacy frame, but no URL: a surface switch is
invisible to the address bar, nothing is deep-linkable, and Back does nothing.
This step gives the shell a real route table — enumerated on both sides, never
a catch-all — and flips the seam TICKET-0055 built: `GET /` becomes the shell,
`GET /legacy` stays the escape hatch, `GET /shell` disappears.

## Scope IN

1. **`app.py` — the enumerated shell route table.** Delete `serve_ui` and
   `serve_shell`. Add, AFTER every `include_router` call and after the
   `/static` mount, verbatim:

   ```python
   # TICKET-0056 (D3b). The shell's SURFACE vocabulary, enumerated. Never a
   # catch-all: the 151 API route literals do not carry "/api" in their text
   # (crud/_router.py declares prefix="/api" at mount time), so a
   # catch-all's exclusion list would be a convention, and a future router
   # included without that prefix would vanish into the shell silently. With
   # enumeration, GET /creaton is a real 404 and GET /api/entitie stays a
   # real 404.
   #
   # The server enumerates SURFACES only and never learns the sub-tab
   # vocabulary: {sub_tab} is opaque here and resolved client-side against
   # CREATION_TABS, so a runtime entity type (TICKET-0046) becomes
   # deep-linkable with no change to this file.
   #
   # This literal is mirrored by SHELL_ROUTES in frontend/src/lib/router.js;
   # tooling/verify/checks/legacy_mount.py asserts the two agree.
   _SHELL_ROUTES = ("/", "/play", "/creation", "/creation/{sub_tab}", "/observation")


   def _serve_shell() -> str:
       return (_STATIC_DIR / "index.html").read_text(encoding="utf-8")


   for _shell_path in _SHELL_ROUTES:
       app.add_api_route(
           _shell_path, _serve_shell, methods=["GET"], response_class=HTMLResponse
       )
   ```

   `serve_legacy` (`GET /legacy`) and `serve_vendor_file` are unchanged.

2. **`frontend/src/lib/router.js`** — the mirror literal and the parsing. It
   exports `SHELL_ROUTES` written as the SAME five strings in the SAME order
   (the check compares them as literals, so any reformatting of one side must
   be matched on the other), plus:

   - `parse(pathname)` -> `{ surface, subTab }`. `/` maps to
     `{ surface: 'play', subTab: null }`. `/creation/<x>` yields
     `subTab: '<x>'`. An unmatched path is not this module's problem — the
     server 404s before the shell loads.
   - `navigate(surface, subTab)` -> builds the path, `history.pushState`.
   - `onRoute(handler)` -> registers the `popstate` listener and invokes the
     handler once for the initial location.

   Verbatim comment at the top:

   ```js
   /* TICKET-0056 (D3b). History-API routing owned ENTIRELY by the shell.
      The legacy frame's src is assigned once and never reassigned
      (LegacyFrame.svelte): an iframe navigation would push an entry onto
      this same history stack and make Back replay legacy boots. Every
      surface change is a pushState here plus a direct bridge call -- never
      a frame navigation. */
   ```

3. **Bridge addition — `showCreationTab(tabId)`**, the deep-link path, with the
   readiness wait and a LOUD failure:

   ```js
   /* TICKET-0056 (D-ii). showCreationSubTab() early-returns into
      creationInit() when the Creation registry is not loaded yet
      (ARCHITECTURE_DECISIONS, TICKET-0054), so a cold deep-link fired before
      the legacy boot completes would silently do nothing. Hence the bounded
      wait -- and a THROW on timeout, never a resolve-anyway. The unknown-tab
      fallback to 'npc' is not new: it is the same fallback activateWorld()
      already uses when a runtime type has disappeared (index.html). */
   ```

   Behavior: `showSurface('creation')`, then
   `whenLegacyReady(() => win.authorRegistry, { timeoutMs: 10000 })`, then
   `win.showCreationSubTab(win.CREATION_TABS?.[tabId] ? tabId : 'npc')`.
   On timeout, the caller renders a visible failure band (reuse the refusal
   band from BRIEF-0056-b).

4. **Wire the shell to the router.** `App.svelte` becomes the single place that
   maps a route to a bridge call: `onRoute(({surface, subTab}) => surface ===
   'creation' && subTab ? showCreationTab(subTab) : showSurface(surface))`.
   `Header.svelte`'s mode tabs now call `navigate(...)` instead of
   `showSurface(...)` directly, and the active tab is derived from the current
   route, not from component state — remove the placeholder state and the
   comment BRIEF-0056-b left there.

   Creation sub-tab clicks happen INSIDE the legacy frame and do not update the
   URL. That is accepted and explicit: the URL is authoritative on entry
   (deep-link), not continuously synchronized. Verbatim comment in `App.svelte`:

   ```js
   /* TICKET-0056: the URL is authoritative on ENTRY, not continuously
      synchronized. A sub-tab clicked inside the legacy frame does not
      rewrite the address bar -- doing so would require the legacy document
      to call out to the shell, i.e. an edit to index.html, which this ticket
      refuses. Continuous sync arrives with the Creation surface itself
      (TICKET-0058). */
   ```

5. **`legacy_mount.py` — assertion 7, the vocabulary agreement (D-i(1)).**
   Extend the existing check, do not create a second file. Parse `_SHELL_ROUTES`
   from `app.py` **by AST** (locate the module-level assignment, read the tuple
   of string constants — never by regex, same discipline as
   `single_canon_write.py`), parse `SHELL_ROUTES` from `router.js` by regex over
   the array literal, and compare as ORDERED lists. Vacuous-proof: either side
   parsing to zero entries is a FAILURE. Failure message:
   `shell route vocabulary diverges -- app.py has [...] , router.js has [...]`.
   Extend the PASS line with `, N shell route(s) agreed`.

6. **Rebuild and commit** the build output.

## Scope OUT

- **Any catch-all route**, any `{full_path:path}`, any exclusion-prefix logic.
  D3a was refused on structural grounds; do not reintroduce it as a
  "convenience fallback for unknown shell paths".
- **A `/creation/{sub_tab}` server-side validation.** The sub-tab segment is
  opaque to `app.py`. Never enumerate live entity types server-side — that is
  precisely what `page_contract` forbids the tab mechanism from doing.
- **Continuous URL synchronization** from inside the legacy frame (see the
  verbatim comment). It would require editing `index.html`.
- **Sub-tab routes for Play or Observation.** Only `/creation/{sub_tab}` gets a
  sub-segment; Play's four sub-tabs and Observation's panels are out.
- **A separate `shell_routes.py` check.** D-i(1) locked: it lives inside
  `legacy_mount.py`.
- **Hash routing**, or any fallback to it.
- **Removing `GET /legacy`.** It is the escape hatch and it stays until
  TICKET-0061.
- **Editing `index.html`.**
- Doctrine and docs: BRIEF-0056-d.

## Invariants to defend

- **Fail-closed over advisory.** Enumeration over catch-all is this brief's
  whole reason for existing; a 404 must stay a 404 on both sides.
- **`page_contract`'s rule that live types are never enumerated** — the server
  must not learn the tab vocabulary.
- **One vocabulary, two readers, one gate** (no structure without a reader):
  the duplication between `app.py` and `router.js` is only acceptable because
  assertion 7 reads both.
- **Single frame-`src` assignment** — assertion 6 must stay green: routing
  changes must never be implemented by navigating the iframe.
- **Frontend-only scope.** The backend change is the route table and nothing
  else.

## Done means

- [ ] `git diff origin/main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `app.py` contains no `serve_ui`, no `serve_shell`, and no catch-all
      route; `_SHELL_ROUTES` has exactly the five entries.
- [ ] `python tooling/verify/checks/legacy_mount.py` prints the PASS line
      including `5 shell route(s) agreed`.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` green;
      `page_contract.py`, `review_component.py`, `relation_graph.py`,
      `observation_surface.py`, `creation_return_nav.py` green.
- [ ] **Red-test, run live:** change one string in `_SHELL_ROUTES` (e.g.
      `/observation` -> `/observations`) -> `legacy_mount.py` red on
      assertion 7 with both lists printed; reverted.
- [ ] **Live routing:**
      - `http://127.0.0.1:8000/` renders the shell on Play.
      - clicking Création changes the URL to `/creation` without reloading the
        frame; clicking back to Play returns, and the Play transcript scroll
        position AND any text typed into the Creation form are still there
        (proof the frame was never re-navigated).
      - Back / Forward walk the surface history one step at a time.
      - cold load of `/creation/lieux` lands on Lieux with content rendered.
      - cold load of `/creation/<runtime entity type from the Constructeur>`
        lands on that runtime tab.
      - cold load of `/creation/does-not-exist` lands on `npc` (fallback), no
        console error.
      - `/creaton` returns 404; `/api/entitie` returns 404 with a JSON body
        (checked in the network tab, not just visually).
      - `/legacy` still renders the bare legacy cockpit.
      - `/shell` now returns 404.
- [ ] `/review-step` and `/close-step` run (engine code touched: `app.py`).

## Docs to update

None in this brief — batched into BRIEF-0056-d, which is written against the
finished shape.
