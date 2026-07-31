<!-- slug: island-mount-feasibility -->
# RECON-0057-a — island mount feasibility (result)

Report-only. Executed against a throwaway Svelte 5 probe (scratch files
under `frontend/src/probe/`, a scratch `frontend/index-probe.html`, and a
scratch `frontend/vite.config.probe.js` proxying `/legacy`, `/api`,
`/static`, `/vendor` to the real cockpit backend on port 8000 so the probe
page and the iframed `/legacy` document are same-origin, matching
production). The probe mounted into the live `/legacy` document via
`frameEl.contentDocument.getElementById('creation-lieux-graph')`, driven by
`npm run dev` (`npx vite --config vite.config.probe.js`) against a real
`python scripts/cockpit.py` backend (`WORLD_ENGINE_ENV=test`). All measured
interactions were performed as real `MouseEvent`s dispatched on the live
DOM nodes inside the iframe's own document/window (the Browser pane's
visual compositor was unavailable in this session, so presses/moves/
releases were driven via `dispatchEvent`/`.click()` on the actual elements
rather than OS-level mouse input; this exercises the exact same
`addEventListener`/event-delegation code paths a real drag would, which is
what M1/M2 measure — it does not simulate anything about hit-testing or
coordinates). The probe and its scratch config/harness were deleted before
this brief's commit; the frontend build was regenerated to its committed
state afterward (M6). No production file was modified.

## M1 — event delivery across the frame boundary

Instrumented `EventTarget.prototype.addEventListener` in both the shell
realm (top window, where `main.js` and the compiled Svelte component
modules execute) and the frame realm (the iframe's own window/document)
before mounting a component with a plain `<button onclick={...}>` into
`#creation-lieux-graph`.

Observed listener registrations on mount:
- `frame-realm: click` on `#probe-mount-host` (the `mount()` target node,
  which lives inside the iframe's own document — an ancestor of the
  button).
- `shell-realm: click` on `#document` (the top window's document — an
  additional, separate registration; never invoked by an in-frame event,
  confirmed below).

A real press+release+click cycle (`mousedown`, `mouseup`, `click`,
`bubbles: true`) dispatched on the button, entirely within the frame's own
document, updated the component's `$state` counter (`clicks: 0` ->
`clicks: 1`) while a capture-phase listener added directly to the SHELL's
`document` for the same test did NOT fire. The functioning delegation
listener is the frame-realm one on the `mount()` target, not the
shell-realm one on the global `document`.

**Plain `onclick={...}` works with no special form.** Svelte 5's `mount()`
delegates click handling to a listener attached on the mount `target`
itself (which lives in whatever document the target belongs to — the
frame's, here), not exclusively to the module-scope global `document`. A
`use:` action doing a manual `node.addEventListener('click', ...)` was also
built and tested as a fallback candidate and also works, but is not needed:
plain `onclick={}` is sufficient.

VERDICT: CONFIRMED - a plain Svelte 5 `onclick={...}` handler fires correctly for a real in-frame click, because `mount()` delegates to the mount target's own (frame) document, not only to the shell's global document.

## M2 — drag listeners (LOAD-BEARING)

Three candidate hosts for `mousemove`/`mouseup`, registered from an
`onmousedown={...}` handler on the target node, `e.target` being the
in-frame node:

- **(a) `window`** (captured as the bareword `window` at module scope —
  the SHELL's window): a real `mousedown` (in-frame) + two `mousemove` +
  one `mouseup`, all dispatched on the frame's own document, produced
  `moves: 0, upped: false`. Confirmed dead end, as expected — the frame's
  internal events never reach the shell window/document (verified
  separately: a capture-phase listener manually added to the shell
  document did not fire for an in-frame dispatch either; iframe document
  trees are isolated for event propagation).
- **(b) `node.ownerDocument.defaultView`** (the frame's own window,
  resolved from the actual DOM node): full press-move-release delivered
  correctly — `moves: 2, upped: true`. **This is the form brief -b
  specifies**, and it works.
- **(c) `node.ownerDocument`** (the frame's own document): also delivered
  correctly — `moves: 2, upped: true`. Functionally equivalent to (b) for
  this purpose.

The `mousedown` that starts the drag is delivered the same way M1's click
is (a frame-realm delegated listener on the mount target), so no fix is
needed there either — a plain `onmousedown={...}` on the draggable node
works.

VERDICT: CONFIRMED - hosts (b) node.ownerDocument.defaultView and (c) node.ownerDocument both deliver a complete real press-move-release sequence; host (a) window correctly never fires for an in-frame drag. A1 stands; no escalation.

## M3 — styling

**(a) CSS custom properties on attribute-styled SVG.** A `<circle>` with
`fill="var(--card)"` and `stroke="var(--border)"` as raw attributes,
mounted inside the frame, resolved to `fill: rgb(33, 38, 45)` (computed
style) — a real color, matching the legacy stylesheet's `--card` value, not
the literal string `"var(--card)"` and not black/transparent. The circle
was visually distinguishable from its own `background:#111` container.
Variables resolve correctly against the legacy document's own stylesheet
for attribute-styled SVG mounted from the shell.

**(b) Where a Svelte scoped `<style>` block lands.** A probe component
carried a `<style>.probe-scoped-target { color: rgb(255,0,128); ... }</style>`
scoped block. After mount, the generated `<style class="s-...">` tag was
found in the **SHELL's** `document.head` (1 match) and was **absent** from
the frame's `document.head` (0 matches). The computed color of the scoped
element inside the frame was the legacy default text color
(`rgb(201, 209, 217)`, i.e. the legacy `--text` value), not the scoped pink
— confirming the scoped rule never applied inside the frame. Brief -b's
"no `<style>` block in the primitive" rule is confirmed **belt-and-braces,
not load-bearing**: the CSS genuinely cannot reach the frame at all (it
lands in the shell's head, where nothing in the frame can see it), so the
rule prevents a silently-dead style block, not a leak.

**(c) Legacy classes on mounted markup.** A mounted element carrying
`class="lieux-graph-head"` and a child `class="btn-icon"` produced computed
styles (`display`, `padding`, `text-transform` for the head;
`padding`/`border` for the button) identical to a genuine pre-existing
`.lieux-graph-head` element already in the legacy static markup. Legacy
classes apply to mounted markup as expected — attribute/class-based styling
is unaffected by the frame boundary; only Svelte's own scoped-CSS injection
is.

VERDICT: CONFIRMED - CSS variables resolve correctly on attribute-styled SVG, legacy classes apply to mounted markup, and a Svelte scoped <style> block lands only in the shell's head (never the frame's) and is confirmed inert inside the frame, empirically.

## M4 — `page_contract.py` vs a nested slot object

Scratch copy of `index.html` (outside the tree, in the session scratchpad).
`CREATION_TABS.lieux.slots[0]` was changed from:

```
slots: [{ id: 'graph', containerId: 'creation-lieux-graph', loader: graphLoad, onSelect: null,
          display: 'on_demand', toggleLabel: 'Voir le graphe' }],
```

to (added `graph: { consumer: 'lieux' }`):

```
slots: [{ id: 'graph', containerId: 'creation-lieux-graph', loader: graphLoad, onSelect: null,
          display: 'on_demand', toggleLabel: 'Voir le graphe', graph: { consumer: 'lieux' } }],
```

Run via a driver script that imports `page_contract` and repoints its
module-level `INDEX_HTML` constant at the scratch copy (the check has no
CLI path argument), then calls `page_contract.main()` directly.

```
PASS: page_contract — CREATION_TABS registry, generic dispatcher, no
duplicate Lieux create button, PJ on the entity archetype, standard shell +
primaryAction on every entry
EXIT CODE: 0
```

`page_contract.py`'s slot parser (`_slot_objects` / `_bracket_block` /
`_slot_by_container`, `page_contract.py:43-85`) is a proper brace-depth
scanner, not a naive regex split — it correctly captures the WHOLE slot
object (nested braces included) as one balanced string, so a nested
`graph: { ... }` object does not confuse it, and the existing
`containerId`/`display: 'on_demand'` substring checks still match inside
that captured string.

VERDICT: CONFIRMED - page_contract.py PASSES unchanged against a nested `graph: { consumer: 'lieux' }` object inside the lieux graph slot; the brace-balanced parser is robust to this nesting. Not a breaking case for brief -b to work around.

## M5 — `review_component.py` vs the deletion of `reviewGraphRender`

Scratch copy of `index.html`: deleted `function reviewGraphRender(key) { ... }`
(the full body, `index.html:6249-6273`) and its two call sites,
`if (regionLocGraphOpen) reviewGraphRender('region');` (`index.html:6699`)
and `if (batchGraphOpen) reviewGraphRender('batch');` (`index.html:7158`).
Run the same way as M4 (driver script repointing `review_component.INDEX_HTML`).

```
FAIL: rule2: 'reviewGraphRender' defined 0 time(s), expected exactly 1
FAIL: rule3/rule7: _braced_function returned empty for 'reviewGraphRender' (unbalanced braces or matched only in a comment)
EXIT CODE: 1
```

Rule 2 fires exactly as the brief expected. Rule 6 (the reverse-boundary
check, `review_component.py:142-151`) does **not** fire — with both call
sites also deleted, no function outside the component references a
`review*` symbol, so there is nothing for rule 6 to catch. One rule fired
beyond the expected rule 2: **rule 3** also fails, because its loop
(`review_component.py:98-114`) iterates every name in `GENERICS` (which
still statically lists `'reviewGraphRender'`, unchanged by the scratch
edit) and calls `_braced_function(html, 'reviewGraphRender')`, which
returns `''` for a function that no longer exists — the empty-body branch
at `review_component.py:104-107` reports this as a rule3/rule7-labeled
failure.

VERDICT: CONFIRMED - deleting reviewGraphRender + its two call sites fails review_component.py with rule2 (defined 0 times) exactly as expected, PLUS rule3's empty-body guard (not previously called out) fires for the same reason; rule 6 does not fire since no external reference remains.

## M6 — build/verify sequence for new frontend sources

With the M1-M3 probe's scratch files present under `frontend/src/probe/`
(6 files: `main.js` + 5 `.svelte` components) plus scratch
`frontend/index-probe.html` and `frontend/vite.config.probe.js` at the
frontend root:

```powershell
cd frontend
npm run build
cd ..
python tooling/verify/checks/frontend_build_fresh.py
```

leaves the check green:

```
PASS: frontend_build_fresh — 18 source file(s), 1 output asset(s), manifest hash matches
```

`git status` on `src/world_engine/cockpit/static/` after that build showed
**only** `.build-manifest.json` changed (`source_hash` updated); the
bundled `index-*.js`/`index-*.css` asset filenames and content were
byte-identical to before, because nothing in the real build's entry graph
(`frontend/index.html` + `frontend/src/main.js`, unmodified) imports the
scratch files — Vite's default single-entry build only follows references
reachable from that entry, so unreferenced scratch modules under
`frontend/src/` are never bundled.

This is a real interaction to flag for future frontend work: `git status`
of the build DIRECTORY looked clean of source-level "leakage", but
`frontend_build_fresh.py`'s source hash (`frontend_build_fresh.py:70`,
`FRONTEND_SRC.rglob("*")`) hashes **every file under `frontend/src/` at any
depth**, regardless of whether anything imports it — so merely adding an
unreferenced scratch/dead file under `frontend/src/` and forgetting to run
`npm run build` afterward would fail this check (stale manifest), even
though the actual served bundle would be unaffected. `npm run build` (which
runs `vite build && node scripts/write-manifest.mjs`) always re-derives the
manifest from the current source tree, so running it after any
`frontend/src/` change — including adding a new primitive file — is what
keeps the check green; there is no separate "verify" step beyond re-running
the build.

`app.py`'s `_check_frontend_build_on_startup` (`app.py:208-220`) only
checks that `static/` is a directory containing at least one `**/*.js` file
— trivially satisfied both before and after, unaffected by any of this.

Cleanup performed: scratch files removed, `npm run build` re-run to
regenerate `static/` from the committed source tree (confirmed
byte-identical `source_hash` to the pre-existing committed manifest; only
the manifest's `built_at` timestamp differed, restored via
`git checkout -- src/world_engine/cockpit/static/.build-manifest.json`).

VERDICT: CONFIRMED - `npm run build` then `python tooling/verify/checks/frontend_build_fresh.py` is the exact sequence that stays green after adding new frontend/src files; the manifest hashes the whole frontend/src tree regardless of what's actually bundled, so any src addition requires a rebuild to stay fresh, and app.py's boot guard is unaffected either way.

## M7 — dead-symbol confirmation

Grep of all 8 symbols across `index.html`, cross-referenced against the 13
functions this ticket deletes (`graphAutoPlace`, `graphRender`,
`graphNodeMD`, `_graphMouseMove`, `_graphMouseUp`, `_graphMoveSVGNode`,
`graphNodeClick`, `graphEdgeClick`, `graphCanvasClick`, `graphCreateEdge`,
`graphPersistPos`, `graphLoad`, `reviewGraphRender`) plus each symbol's own
declaration line (also scheduled for deletion, separately, as one of the "4
constants" / "4 globals"):

| Symbol | Lines | Inside/outside the 13 (or own declaration) |
|---|---|---|
| `GRAPH_W` | 10454 (decl), 10467, 10522 | all inside (decl + `graphAutoPlace` + `graphNodeMD`) |
| `GRAPH_H` | 10455 (decl), 10467 | all inside (decl + `graphAutoPlace`) |
| `NODE_R` | 10456 (decl), 6266, 6267, 10502, 10504, 10557 | all inside (decl + `reviewGraphRender` + `graphRender` + `_graphMoveSVGNode`) |
| `DRAG_THRESHOLD` | 10457 (decl), 10533 | all inside (decl + `_graphMouseMove`) |
| `graphData` | 4209, 10459 (decl), 10481, 10482, 10485, 10559, 10578, 10623, 10634 | **10 of 11 inside** (decl + `graphRender`/`_graphMoveSVGNode`/`graphNodeClick`/`graphPersistPos`/`graphLoad`); **line 4209 is OUTSIDE** — `_lieuxWorldReset()` (`index.html:4204-4212`), not one of the 13 |
| `graphSelectedNodeId` | 10460 (decl), 10496, 10569, 10570, 10574, 10575, 10596 | all inside (decl + `graphRender`/`graphNodeClick`/`graphCanvasClick`) |
| `_graphDrag` | 10461 (decl), 10518, 10530, 10531, 10532, 10533, 10543, 10544, 10545 | all inside (decl + `graphNodeMD`/`_graphMouseMove`/`_graphMouseUp`) |
| `_graphPlaced` | 10462 (decl), 10482, 10483, 10495, 10517, 10625, 10626 | all inside (decl + `graphRender`/`graphNodeMD`/`graphPersistPos`) |

**Contradicts the ticket's RECON claim.** `TICKET-0057-graph-primitive.md`
states "RECON confirms this is attainable: every use of ... `graphData` ...
sits inside the 13 functions being deleted." One occurrence does not:
`graphData = null;` at `index.html:4209`, inside `_lieuxWorldReset()`
(`index.html:4204-4212`) — the Lieux tab's world-switch reset handler,
called from `CREATION_TABS.lieux.state.onWorldSwitch`, not one of the 13
functions and not scheduled for deletion. Deleting the `let graphData`
declaration per the ticket's GONE rule without also touching this line
would leave `_lieuxWorldReset()` referencing an undeclared identifier.

VERDICT: REFUTED - seven of the eight symbols have zero occurrences outside the 13 functions (plus their own declarations), but `graphData` has one: `index.html:4209` inside `_lieuxWorldReset()`. Brief -b's deletion list must additionally handle this line (report only, no action taken here).

## M8 — container survival across a review re-render

Tested directly against the running `/legacy` app (no shell/probe
involved — this measures the legacy code's own re-render behavior).
`regionDraft`/`regionAccepted`/`regionConfirmedLinks`/`regionLocGraphOpen`
are top-level `let` bindings in the classic (non-module) script, so they
are not reachable as `window` properties from outside (confirmed —
assigning `frameEl.contentWindow.regionDraft = ...` silently created an
unrelated `window` property and had no effect; `frameEl.contentWindow.eval(...)`,
which runs in the frame's shared global/script scope, correctly read and
wrote the real bindings). Seeded a minimal two-location `regionDraft` this
way, set `regionLocGraphOpen = true`, then called the real
`regionRenderAll()` twice via `eval`, tagging the `#region-lieux-graph-svg`
node with a marker property (`__probeMarker`) between calls.

```json
{"renderErr": null, "sameNodeIdentity": false, "markerSurvivedOnAfter": false, "svgAfterExists": true}
```

The `#region-lieux-graph-svg` node is a **different DOM node object** after
the second `regionRenderAll()` call — the marker property did not survive.
Both `regionRenderAll` (`index.html:6655-6700`) and `batchRenderAll`
(`index.html:7098-7159`) share the identical mechanism: `root.innerHTML =`
a full template literal that includes the graph `<svg>` markup
(`index.html:6669` / `index.html:7128`), which by DOM semantics destroys
and reparses every descendant of `root` on every call — this was directly
observed for `regionRenderAll`, and `batchRenderAll`'s source is the same
`root.innerHTML = \`...<svg id="batch-lieux-graph-svg" ...>...\`` shape
against a different root/id, so the same destroy-and-recreate mechanism
applies there by construction, not by a separate live test.

VERDICT: CONFIRMED - the graph container's DOM node identity does NOT survive a regionRenderAll/batchRenderAll re-render; both replace their entire subtree via root.innerHTML on every call. Brief -c's re-mount strategy must re-mount the Svelte island after every re-render, never assume the container persists.

## Escalation

M2 did not refute A1 — hosts (b) and (c) both deliver a complete
press-move-release sequence. No escalation.
