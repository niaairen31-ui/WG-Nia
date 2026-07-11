# BRIEF — Step "On-demand graph slots + cytoscape vendoring (contract groundwork)"

## Context

TICKET-0005 locked the slot mechanism as THE extension point for per-tab
auxiliary panels, generalized "only on a second concrete reader"
(ARCHITECTURE_DECISIONS.md:3601, "Graph-as-slot posture"). TICKET-0023's NPC
ego-graph is that second reader — and it arrives with a new requirement both
readers share: Nia wants NO graph permanently displayed. Today slots load
unconditionally on tab activation (`_creationActivateTab`,
`index.html:3452`), so "on-demand" is a contract change, not a component
change.

Separately, the ego-graph must be manipulable (zoom / pan / click / recenter)
and Nia has decided graphs will grow in complexity, so the rendering moves to
a vendored cytoscape.js rather than extending the hand-rolled SVG idiom. This
is the project's FIRST vendored JS dependency: CLAUDE.md forbids new
dependencies without a decision, and no static-file serving path exists
(`index.html` is served inline, `app.py:1868`; no `StaticFiles` anywhere in
`src/`). This brief carries both pieces of groundwork; BRIEF-0023-b builds the
feature on top.

Locked: F1, H1 (ticket); Lieux content byte-untouched.

## Scope IN

1. **Slot contract field `display`** — the `CREATION_TABS` entry-contract
   comment gains one line:

   ```
   //   slots:        [{ id, containerId, loader, onSelect: fn|null,
   //                    display: 'always'|'on_demand' (default 'always') }]
   ```

   Semantics: `'always'` = today's behavior, unchanged, and the default when
   the key is absent (zero-diff for `pj`'s fiche slot and `queue`'s filters
   slot). `'on_demand'` = on tab activation the slot's container stays
   hidden and its `loader` does NOT fire; the standard shell renders one
   toggle button per on_demand slot (label from a new optional
   `toggleLabel` slot field, default "Voir le graphe"); first click shows
   the container and fires `loader`; second click hides it (no unload —
   hide/show only). State (open/closed) is tab-scoped and MUST be covered
   by the tab's `state.onTabEnter` / `onWorldSwitch` resets.

2. **Dispatcher change** — `_creationActivateTab` iterates slots as today
   but branches on slot DATA (`s.display === 'on_demand'`), never on tab
   ids. The toggle button renders in the standard shell band
   (`renderCreationShell`), same fixed position on every tab, mirroring the
   `primaryAction` posture.

3. **Lieux migrates** — `lieux.slots[0]` gains `display: 'on_demand'`,
   `toggleLabel: 'Voir le graphe'`. The graph component itself
   (`graphLoad`, `graphRender`, drag, edge click, `#creation-lieux-graph`
   markup, CSS) is byte-untouched — verify enforces this.

4. **Vendored cytoscape** — `src/world_engine/cockpit/vendor/
   cytoscape-3.x.y.min.js` (exact upstream minified file, version in the
   file name, no modification). One route in the cockpit app:

   ```python
   @app.get("/vendor/{filename}")  # FileResponse, whitelist = the one file
   ```

   Whitelisted filename check (no path traversal), correct
   `application/javascript` media type. No `StaticFiles` mount — that
   generalization waits for a second vendored asset. `index.html` loads it
   with a plain `<script src="/vendor/...">` tag.

5. **ARCHITECTURE_DECISIONS.md entry** — records (a) the cytoscape
   dependency decision (why vendored, why not CDN — offline local cockpit;
   why not extending vanilla SVG — Nia's explicit "graphs will complexify"
   call, including the Lieux graph's own future migration), and (b) the
   `display` slot-contract extension. DECISIONS_INDEX.md row added.

6. **`page_contract.py` extended** — asserts the entry-contract comment
   documents `display`, asserts `lieux` and (after -b) `npc` graph slots
   declare `on_demand`, and keeps all existing assertions green.

## Scope OUT

1. Any use of cytoscape (that is -b; this brief only makes it loadable).
2. Any change to the Lieux graph component or its editor behavior.
3. `StaticFiles` mount, second vendored asset, source maps.
4. Auto-generalizing `on_demand` to non-slot containers.

## Invariants

- A slot without `display` behaves exactly as on `main` — the field's
  absence is a valid, complete state.
- `showCreationSubTab` / `_creationActivateTab` contain no tab-id literals
  (0005 doctrine, verify-enforced).
- The vendor route serves exactly one whitelisted file; any other filename
  is 404.
- Lieux graph component functions byte-identical to `main`.

## Done means

- Lieux tab activation shows NO graph; the shell shows « Voir le graphe » ;
  click shows the existing graph, unchanged; second click hides it; world
  switch closes it.
- `pj` fiche slot and `queue` filters slot behave exactly as before.
- `<script src="/vendor/cytoscape-*.min.js">` loads with HTTP 200 and
  `window.cytoscape` is defined in the cockpit console.
- `/verify` green, including the extended `page_contract.py`.

## Docs to update

- ARCHITECTURE_DECISIONS.md + DECISIONS_INDEX.md (Scope IN 5).
- CLAUDE.md: one line in the page-contract bullet noting the `display` slot
  field, if the section's line budget allows; otherwise the
  ARCHITECTURE_DECISIONS entry suffices.
- No schema changelog (no schema touch).
