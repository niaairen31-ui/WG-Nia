# BRIEF — Step "shell chrome + world/player state as a server mirror"

## MINI-RECON — run before executing this brief

Report-only. Confirm empirically; on any failure STOP and escalate.

```bash
git log --oneline -3                       # BRIEF-0056-a is the tip
ls frontend/src/ frontend/src/legacy/
grep -n "async function activateWorld" -A 6 src/world_engine/cockpit/index.html
grep -n "_creationRunWorldSwitchResets" src/world_engine/cockpit/index.html
grep -n "async function loadWorldSelector" -A 6 src/world_engine/cockpit/index.html
grep -n "function worldCreateOpen\|function worldDeleteOpen" src/world_engine/cockpit/index.html
grep -rn '"/api/worlds"\|"/api/bootstrap"' src/world_engine/cockpit/routes/creator.py
grep -n "<header>" -A 14 src/world_engine/cockpit/index.html | head -20
python tooling/verify/checks/legacy_mount.py
```

Assertions that must hold:

1. BRIEF-0056-a has landed: `registry.js`, `bridge.js`, `LegacyFrame.svelte`,
   `App.svelte` exist; `legacy_mount.py` is green.
2. `index.html` defines top-level `activateWorld(worldId)`,
   `_creationRunWorldSwitchResets()`, `loadWorldSelector()`,
   `worldCreateOpen()`, `worldDeleteOpen()`.
3. `activateWorld` POSTs `/api/worlds/{id}/activate`, then calls
   `loadWorldSelector()`, then `await _creationRunWorldSwitchResets()`, then
   re-renders the Creation view. **If that ORDER differs from this
   description, escalate** — this brief delegates the whole cascade to it
   precisely because it is one authority.
4. `GET /api/bootstrap` and `GET /api/worlds` exist in `routes/creator.py`.
5. The legacy `<header>` element carries the mode tabs, `#world-selector`, and
   the two world buttons.

## Context

BRIEF-0056-a gave the shell a legacy frame and a bridge, and no chrome: the
legacy header is still the only way to switch surfaces or worlds. This step
moves the chrome up into the shell and gives shared top-level state a home,
without creating a second authority over it. The active world is SERVER state
(`POST /api/worlds/{id}/activate`); the shell holds a mirror of it and
delegates the switch cascade to the one function that already owns it.

## Scope IN

1. **`frontend/src/lib/serverState.svelte.js`** — the mirror. A Svelte 5 rune
   store exposing `worldId`, `playerId`, `worlds` (the `/api/worlds` list),
   and `error`. One loader, `refreshServerState()`, which reads
   `GET /api/bootstrap` then `GET /api/worlds`.

   **It must fail LOUD.** Verbatim comment above the loader:

   ```js
   /* TICKET-0056 (C3). The SERVER is the authority on the active world; this
      store is a MIRROR, never a second source of truth. Deliberate contrast
      with the legacy loadBootstrap() (index.html), which swallows every error
      in `catch (_) {}` and leaves WORLD_ID null with no visible symptom: a
      failed read here sets `error` and the shell renders a refusal banner.
      Fail-closed over advisory. */
   ```

   A failed fetch sets `error` to the message and leaves the previous values
   untouched; it never resolves to nulls silently.

2. **`frontend/src/Header.svelte`** — the shell header. Renders, left to right:
   the title block, the three mode-tab buttons (`Play`, `Création`,
   `Observation`), the world `<select>`, `+ Monde`, `🗑 Monde`, and the
   `127.0.0.1 · local only` badge. Visual parity with the legacy header is the
   target; reuse the same labels verbatim.

   - Mode tabs call `showSurface(key)` from the bridge and mark the active one.
     In this brief the active surface is component state; BRIEF-0056-c replaces
     that with the router as the single source. Leave a one-line comment
     saying exactly that.
   - The world `<select>` is populated from the store's `worlds`, with the
     active one selected and labelled `${name} (actif)` — same shape as
     `loadWorldSelector`.
   - `+ Monde` and `🗑 Monde` call the legacy `worldCreateOpen()` /
     `worldDeleteOpen()` through the bridge. Their modals render INSIDE the
     frame. This is deliberate and transitional: re-implementing those two
     modals in Svelte is TICKET-0059's world-CRUD work, not this ticket's.
   - If `error` is set, render a visible refusal band above everything with the
     message; do not render a world selector built on stale data without it.

3. **Bridge additions** (`frontend/src/legacy/bridge.js`, still the only module
   allowed near the legacy window):
   - `callLegacy(fnName, ...args)` — internal generic invoker used by the
     exported wrappers; throws if the function is absent on the legacy window.
   - `activateWorldViaLegacy(worldId)` — calls the legacy
     `activateWorld(worldId)` and awaits it.
   - `openWorldCreate()` / `openWorldDelete()` — the two modal openers.
   - `hideLegacyHeader()` — injects, into the legacy document's `<head>`, a
     single `<style id="shell-injected">header { display: none !important; }</style>`,
     idempotently (no-op if the id already exists). Verbatim comment:

     ```js
     /* TICKET-0056: the legacy header is SUPPRESSED, not deleted -- index.html
        is byte-untouched by this ticket. Injecting one scoped style into the
        frame document is reversible, confined to this module, and covered by
        legacy_mount.py's confinement assertion. */
     ```

4. **The world-switch flow (C3), implemented exactly this way and no other:**

   ```
   shell <select> onchange
     -> bridge.activateWorldViaLegacy(id)      // ONE authority for the cascade:
                                               //   POST activate, legacy selector,
                                               //   _creationRunWorldSwitchResets(),
                                               //   Creation re-render
     -> await refreshServerState()             // re-read the server, refresh the mirror
   ```

   The shell **must not** POST `/api/worlds/{id}/activate` itself, and must not
   reimplement any reset. Verbatim comment at the call site:

   ```js
   /* TICKET-0056 (C3). The shell does NOT own the world-switch cascade. It
      delegates to the legacy activateWorld(), which is the single place that
      knows every world-scoped reset (_creationRunWorldSwitchResets), then
      re-reads the server. Duplicating the POST here would create a second
      writer for one server-side fact. When Creation migrates (TICKET-0058/59),
      the cascade moves WITH it -- it is not re-derived here in advance. */
   ```

5. **`App.svelte` layout** — header on top, frame filling the rest. The frame's
   `height: 100vh` from BRIEF-0056-a becomes `height: calc(100vh - <header
   height>)` via a CSS custom property set on the layout container, so no magic
   number is repeated. On mount: `mountLegacy(frameEl)` -> await load ->
   `hideLegacyHeader()` -> `refreshServerState()`.

6. **Rebuild and commit** the build output.

## Scope OUT

- **Routing of any kind.** No URL reading or writing, no `pushState`, no
  `popstate`, no deep links. The active surface is component state here and
  becomes router-derived in BRIEF-0056-c. Do not "prepare" the router.
- **The seam flip.** `/` still serves legacy; `/shell` still serves the shell.
  Test this brief at `/shell`.
- **Re-implementing the world create/delete modals** in Svelte. They stay
  legacy modals opened through the bridge.
- **Re-implementing `_creationRunWorldSwitchResets`**, or any part of the
  reset cascade, or the `CREATION_TABS` fallback logic, in the shell.
- **Migrating the Play sub-tab bar or the Creation sub-tab bar** into the shell
  header. Only the three TOP-LEVEL surfaces are shell chrome; sub-tabs stay
  inside the legacy document until their surface migrates.
- **Editing `index.html`** — including to add an id or a class that would make
  header suppression easier. Inject the style from the bridge instead.
- **Reproducing `loadBootstrap`'s silent-catch pattern.**
- Doctrine, docs, `ARCHITECTURE_DECISIONS.md`: BRIEF-0056-d.

## Invariants to defend

- **Single authority over server state.** One writer for the active world (the
  server, driven by the legacy cascade); the shell store is a read mirror. This
  is the frontend transposition of the canon-write doctrine, and the temptation
  here is exactly the one the doctrine names: a second, more convenient writer.
- **Fail-closed over advisory.** A failed bootstrap renders a refusal, not a
  degraded-but-usable header.
- **`index.html` byte-untouched.**
- **Confinement.** Every new legacy touch goes through `bridge.js`;
  `legacy_mount.py` assertion 5 stays green without amendment.
- **Frontend-only scope.** No backend change at all in this brief.

## Done means

- [ ] `git diff origin/main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `git diff origin/main -- src/world_engine/` shows changes under
      `cockpit/static/` only (the build output) plus BRIEF-0056-a's `app.py`
      route.
- [ ] `python tooling/verify/checks/legacy_mount.py` green, unchanged file.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` green.
- [ ] **Live at `http://127.0.0.1:8000/shell`:**
      - one header only (the shell's); the legacy header is not visible.
      - the three mode tabs switch surfaces; the active tab is marked.
      - the world selector lists every world with the active one marked
        `(actif)`.
      - switching world: the selector updates, and a Creation tab that showed
        the previous world's rows now shows the new world's rows with no stale
        entry.
      - `+ Monde` opens the legacy create-world modal inside the frame and a
        world can be created end to end; `🗑 Monde` opens the delete modal.
      - the frame fills the viewport under the header with no double
        scrollbar and no clipped content at the bottom of Play's transcript.
- [ ] **Refusal red-test, run live:** stop the API mid-session (or point
      `refreshServerState` at a bad path once), reload `/shell`, and confirm a
      visible refusal band appears rather than an empty selector. Reverted.
- [ ] `http://127.0.0.1:8000/` still renders the untouched legacy cockpit with
      its own header.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None in this brief — batched into BRIEF-0056-d.
