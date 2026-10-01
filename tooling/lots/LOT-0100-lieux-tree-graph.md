# LOT — TICKET-0100 "Lieux — in-place tree, « + lot », graph node selection"

## Objective and cut

Nia is building Aestia and reached the Lieux tab. Two things block her: the
location graph cannot connect anything (a node never stays selected, R-01),
and the left panel is a descent view unlike every other tab's list, keyed on
type buckets her world's types never match (R-10, R-11).

The lot fixes the graph primitive and lets a Lieux node open its fiche (A),
moves the room batch trigger out of the descent view into a « + lot » shell
button (B), then replaces the descent view with one tree on the shared list
rows that unfolds in place (C).

It stops before anything about zones: no visitable/zone rule, no `borde`
relation, no promotion dialog, no graph modes — all TICKET-0101. It changes
no endpoint, no table and no write path: every brief is frontend plus one
verify rule.

## Briefs in this lot

- **A — graph node click** (no schema change): `Graph.svelte`'s node `<g>`
  stops its own click (C-01); `consumers/lieux.js` declares `onNodeClick`
  → `selectEntity` (C-02) and rewords its help text; `graph_primitive.py`
  rule 12; the decision entry.
- **B — « + lot »** (no schema change): `CREATION_TABS.lieux` gains a
  `secondaryAction` (C-04); `Sheet.svelte`'s `primaryAction('batch')`
  anchors the room batch on the open location (C-03); the `secondaryAction`
  contract comment in `tabs.js` names the second use; the decision entry.
- **C — the Lieux tree** (no schema change): `EntityList.svelte`'s lieux
  mode becomes one tree on `.author-list-item` rows (C-05) — the descent
  state, its helpers, the typed buckets and « Générer un lot ici » are
  deleted; `frontend/public/creation.css` drops the descent view's rules and
  gains `.lieux-children-btn`; the decision entry.

## Dependency graph

Strictly sequential, A → B → C.

- **B before C is a real dependency.** C deletes « Générer un lot ici », the
  only caller of `openRoomBatch` today (E2); B gives the room batch its new
  trigger first, so no commit of the lot leaves the generator unreachable.
- **A before B is an order chosen, not imposed.** A touches no file B or C
  touches except `ARCHITECTURE_DECISIONS.md`; it runs first because it is
  the defect Nia is blocked on. An executor who finds A independent of B
  and C is not finding a defect.
- Textual chaining makes the order strict anyway: every brief appends an
  entry just above the footer of `tooling/standards/ARCHITECTURE_DECISIONS.md`.

## RECON

Opened on `main` at `dbd10d0` (merge of PR #130, `ticket/0099`): corpus
129/129 green; `npm run build` byte-reproducible (only the manifest's
`built_at` moves). Then prototyped on a copy (branch `proto/0100`), one
commit per brief, the full corpus green after each (129/129 — the lot adds a
rule to an existing check, no new check). Every behaviour the briefs claim
was driven in headless Chromium against a scratch database shaped like
Aestia (the Secte du Phoenix with four children, one of them with a child of
its own; the Forêt verte; a town; two NPCs). Last, this ticket, this header
and the three briefs were deposited, each brief's diff was extracted from
its own fence and applied in order on a clean `main`: the tree equals the
prototype's, and `run.py --ticket TICKET-0100-lieux-tree-graph` is green.
Findings tagged [M] were measured, [I] inferred from code read in full.

### R-01 — why a node never stays selected [M]
Opened: `frontend/src/graph/Graph.svelte` (whole, 329 lines): `:194-217`
(`handleNodeMouseDown`: `e.stopPropagation()` on the mousedown, then either
`handleNodeClick` at once (force layout, or no `onMoveNode`) or a drag
armed on the window), `:232-249` (`handleMouseUp`: no movement →
`handleNodeClick(nodeId)`), `:251-273` (`handleNodeClick`: with `onConnect`,
the first tap sets `selectedNodeId`, the second connects), `:286-288`
(`handleCanvasClick`: clears `selectedNodeId`), `:290-293` (the `<svg>`
binds `onclick={handleCanvasClick}`), `:314-318` (the node `<g>` binds
`onmousedown` and `ondblclick`, no `onclick`).
Finding: the mousedown's `stopPropagation` stops only the mousedown. The
browser then fires `click` on the node; it bubbles to the `<svg>` and
`handleCanvasClick` clears the selection the press just set. Measured on
`main`: after one click on a Lieux node, every circle's `fill` is
`var(--card)` (none `var(--accent)`); after two clicks on two nodes,
`GET /api/locations/graph` returns zero edges. With an `onclick` that stops
propagation on the `<g>`, the first circle is `var(--accent)` and the edge
is created.
Consequence: the fix belongs to the primitive (C-01), not to a consumer.

### R-02 — the relations graph shares the defect [M]
Opened: `frontend/src/graph/consumers/relations.js:240-258`
(`capabilities(meta)`: global mode with `armed` declares `onConnect`, which
opens « Nouveau lien » in the side panel).
Finding: on `main`, NPC tab → Voir le graphe → Global → Lier → two node
clicks: the side panel shows the node info card (« Relations / Aucune
relation. »), never the form. With C-01: « Nouveau lien / Aldo → Brina ».
Consequence: G1 over G2 (fixing the Lieux consumer only).

### R-03 — how a consumer hears a node click [M]
Opened: `frontend/src/graph/mount.js:168-183` (`svelteMount(Graph, …)`:
`onNodeClick: wrapPlain(caps.onNodeClick)`; `caps` is the consumer object
itself when it exports no `capabilities`, `:166`), `:78-87` (`wrapPlain`:
calls the function, catches and logs, never reloads); `Graph.svelte:251-273`
(`onNodeClick?.(nodeId)` fires on the first tap AND on the second tap,
before `onConnect`).
Consequence: a Lieux `onNodeClick` opens the first node's fiche on the first
tap and the second node's on the second: after a connection, the second
node's fiche is the one open (a locked consequence of G1).

### R-04 — the Lieux consumer [M]
Opened: `frontend/src/graph/consumers/lieux.js` (whole, 57 lines).
Finding: exports `chrome` (title, `helpText` at `:25`), `dashedKinds`,
`load`, `onConnect` (POST `/api/entities/{a}/relations`, type
`connects_to`), `onDeleteEdge`, `onMoveNode` (`:46`). No `onNodeClick`, no
`capabilities`, no import.
Consequence: A adds `onNodeClick` and one import; the four existing
callbacks are untouched.

### R-05 — opening a fiche from outside the list [M]
Opened: `frontend/src/creation/sheetState.svelte.js:109-124`
(`export async function selectEntity(legacyDoc, id)`: GET
`/api/entities/{id}`, sets `sheetMode = 'view'`, `sheetIsNew = false`,
`sheetType = detail.type`, `sheetDetail = detail`, `selectedEntityId = id`,
then dispatches `'creation:selection'` on `legacyDoc`);
`frontend/src/creation/mount.js:91` (every Creation island receives
`legacyDoc: node.ownerDocument` — the shell document since TICKET-0059);
`frontend/src/creation/EntityList.svelte:208-215` (the list calls
`selectEntity(legacyDoc, id)` and listens for `'creation:selection'` on the
same document to highlight the row); `frontend/src/graph/consumers/
relations.js:26` (`import { getSelectedEntityId } from '../../creation/
sheetState.svelte.js'`).
Finding: a graph consumer already imports from `sheetState.svelte.js`;
`graph/mount.js` mounts into the shell `document` (`:121`,
`document.getElementById(containerId)`). Prototype: `import_cycle.py` PASS
with the new import.
Consequence: C-02 calls `selectEntity(document, nodeId)`; the list
highlights the row through its existing listener.

### R-06 — the primitive's lock [M]
Opened: `tooling/verify/checks/graph_primitive.py` (whole, 916 lines on
`main`): rules 1–9 and 11 (no rule 10); `:585-597` (rule 7, a text scan of
`Graph.svelte`), `:600-608` (rule 8), `:611` (`_KEY_RE`), `:834-916`
(`main`: each rule's result joins the final `if FAILURES or …`;
`_report_and_exit(counts)` at `:350-364` prints one PASS line).
Finding: nothing examines a node's click. The check is under
`tooling/verify/`, outside `module_budget.py`'s scope (`src/**/*.py` and
`frontend/src/**`, `module_budget.py:1-25`).
Consequence: A adds rule 12 in the same idiom: a text scan, a count joined
to the PASS line, zero collected is a failure.

### R-07 — the `secondaryAction` seam [M]
Opened: `frontend/src/creation/tabs.js:185-192` (the contract comment:
"a page that creates two kinds of record"), `:228-243` (`lieux`:
`primaryAction` routed through `triggerPrimaryAction('entitySheet')`, no
`secondaryAction`), `:277` (Compétences' `secondaryAction`, variant
`'system'`); `frontend/src/creation/mount.js:134-143`
(`triggerPrimaryAction(key, variant)` → `instance.primaryAction(variant)`);
`frontend/src/creation/Creation.svelte:113-115` (the band renders the
secondary button before the primary one when both exist);
`tooling/verify/checks/creation_island.py:952-982` (rule 11b: two string
literals, the same key as the routed primary, zero paired is a failure);
`frontend/src/creation/Sheet.svelte:214-226` (`primaryAction(variant)`:
resets six drafts, `enterCreateMode(...)`, then `blankRecord(variant)` for
a competences fiche only).
Finding: any variant reaches `Sheet.svelte`, which always enters create
mode today.
Consequence: B adds a `'batch'` variant that returns before the resets
(C-03); rule 11b counts 2 paired.

### R-08 — the room batch and its only trigger [M]
Opened: `frontend/src/creation/roomBatch.svelte.js:52-57`
(`export function openRoomBatch(anchorId, anchorName)`: reset, `open =
true`, anchor id and name); `frontend/src/creation/registry.js:323`
(`batch` island); `frontend/src/creation/Creation.svelte:131`
(`#batch-panel-wrap`); `tabs.js:231` (`lieux.containers` lists
`batch-panel-wrap`); `EntityList.svelte:345` (« Générer un lot ici »,
`openRoomBatch(lieuxParentId, <breadcrumb's last name>)`, disabled at the
root).
Finding: one caller (E2). The panel is visible whenever Lieux is.
Consequence: B gives the generator a second caller before C deletes the
first.

### R-09 — what the fiche holds [M]
Opened: `frontend/src/creation/sheetState.svelte.js:109-124` (as R-05);
`src/world_engine/cockpit/crud/entities.py:229-240` (`_entity_dict`:
`id`, `world_id`, `type`, `name`, `internal_name`, `is_public`, `status`,
two timestamps), `:486-508` (`get_entity` adds `extension`, `relations`,
`knowledge`, and for a location `geometry`, `doors`);
`Sheet.svelte:185-190` (`enterCreateMode`: `sheetIsNew = true`,
`sheetDetail = {}`); `Creation.svelte:219` (`#author-status`);
`Sheet.svelte:447, 482, 505, 509, 526, 615, 635` (every error in the fiche:
`statusEl.className = 'author-status err'; statusEl.textContent = …`).
Finding: a saved location open in the fiche is `sheetType === 'location'`,
`sheetIsNew === false`, `sheetDetail.id`/`.name` set.
Consequence: C-03's anchor test, and its message in the fiche's own status
line, in the fiche's own error idiom.

### R-10 — the Lieux list today [M]
Opened: `frontend/src/creation/EntityList.svelte` (whole, 388 lines):
`:56` (`import { openRoomBatch }`), `:63-68` (`GENERIC_TYPE_BY_TAB`,
`LOCATION_TYPE_ORDER`, `LOCATION_TYPE_LABELS`), `:75-81` (descent state:
`lieuxParentId`, `lieuxBreadcrumb`, `lieuxActiveOnly`), `:176-196`
(`activateTab`: a new Lieux activation resets the descent), `:255-265`
(`lieuxHasActiveDescendant`), `:267-275` (`lieuxChildrenOf`: roots are
locations with no parent or an unknown parent; filtered by
`lieuxActiveOnly`), `:277-306` (`lieuxBuckets`, `lieuxDescend`,
`lieuxJumpTo`), `:322-329` (the flat mode's row:
`.author-list-item`, `.ali-name`, `.ali-meta` « type · status »,
`active`/`inactive` classes), `:331-366` (the lieux markup: checkbox,
breadcrumb, lot button, buckets, `.lieux-node-row` rows with a name button,
a status pill and « N enfants › » that descends).
Consequence: C replaces `:75-81`'s descent pair, `:192-195`, `:277-306` and
`:331-366`; keeps `lieuxActiveOnly`, `lieuxHasActiveDescendant`,
`lieuxChildrenOf` unchanged.

### R-11 — location types belong to each world [M]
Opened: `src/world_engine/models/canon.py:209-230` (`Location.location_type:
Optional[str]`, no constraint), `:246-271` (`LocationTypeCatalog`: one row
per type string per world, unique on `(world_id, name COLLATE NOCASE)`;
types are added one at a time from the picker).
Finding: a world's types are whatever its creator typed (`quartier`,
`bâtiment` in the prototype world). `LOCATION_TYPE_ORDER` matches only the
seven English strings; everything else lands in « Autres ».
Consequence: the buckets go; the type is shown as the row's meta.

### R-12 — entity status values [M]
Opened: `src/world_engine/models/canon.py:133-135` (`Entity.status: str`,
default `'active'`, no CHECK); `src/world_engine/cockpit/crud/entities.py:112`
(`ENTITY_STATUSES = ("active", "inactive", "destroyed", "missing")`, the
fiche's choices).
Finding: four values offered, none enforced. The old Lieux rows dimmed
every non-`active` status (`:357`); the flat list strikes only `inactive`
(`:324`).
Consequence: C keeps the Lieux behaviour: any status but `active` takes the
`inactive` row class, and the status is printed in the meta line.

### R-13 — the rows the tree reads [M]
Opened: `src/world_engine/cockpit/crud/locations.py:264-284`
(`GET /api/locations`: every location of the active world, every status,
each `{id, name, parent_location_id, location_type, status}`);
`EntityList.svelte:100` (`creationState.locationTree = locations`).
Consequence: C-05 needs no new fetch.

### R-14 — the one recursive location tree [M]
Opened: `tooling/verify/checks/location_tree.py` (implementation `:94-137`:
a `.svelte` file other than `LocationTree.svelte` fails when it contains
BOTH the token `linkagent-loc-node` AND a self-recursive render — a
`{#snippet NAME(…)}` calling `{@render NAME(` inside itself, or
`<svelte:self`); `frontend/src/creation/LocationTree.svelte:47-69` (props
`locations` and `row`; every node rendered as a `<label>` inside
`.linkagent-loc-node`, always fully expanded).
Finding: the primitive has no folded state and renders labelled controls,
not list rows. A recursive snippet in `EntityList.svelte` without the token
would pass the check while duplicating exactly what it exists to prevent.
Consequence: C flattens the tree iteratively (C-05) and renders one
`{#each}`; no recursion, no token.

### R-15 — the list row the other tabs use [M]
Opened: `frontend/public/creation.css:217-226` (`.author-list-item`:
`padding: 9px 14px`, left border, `.active` highlighted, `.inactive`
struck and faded; `.ali-name`, `.ali-meta`);
`frontend/src/creation/CompetencesList.svelte:52-90` (record rows:
`role="button" tabindex="0"`, `onclick`, `onkeydown` on Enter; a child row
indented with `style="padding-left:28px"` at `:77`).
Consequence: C's rows are that markup; depth sets `padding-left` to
`14 + 16 × depth` px (14 px is the class's own left padding).

### R-16 — the descent view's CSS [M]
Opened: `frontend/public/creation.css:228-282` (`.lieux-browse-head`,
`.lieux-breadcrumb` and its `.lb-*`, `.lieux-bucket-head`,
`.lieux-node-row` and its `.ali-name-btn`/`.dimmed`, `.lieux-status-pill`,
`.lieux-descend-btn`); `tooling/verify/checks/stylesheet_partition.py:385-399`
(rule 6: `static/creation.css` must byte-match the `frontend/public/` copy;
the build copies it, measured).
Finding: enumeration E1 — every one of those classes is used by
`EntityList.svelte` alone, except `.lieux-bucket-head`, also used by
`CompetencesList.svelte`; none in `legacy.html` or `static/index.html`.
Consequence: C deletes the rules only `EntityList.svelte` used and no longer
applies, keeps `.lieux-browse-head` and `.lieux-bucket-head`, adds
`.lieux-children-btn`. Measured on the prototype: renaming that class on its
button leaves `stylesheet_partition.py` green (rule 7 covers only names the
legacy inline sheet also uses), so C's named mutation targets rule 6, and
the gap is carried forward on the ticket.

### R-17 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:14-17` (`STRICT_HEADER`:
`^## .+ \(BRIEF-\d{4}(-[a-z])?…, (schema v\d+\.\d+|no schema change)\)$`);
`tooling/standards/ARCHITECTURE_DECISIONS.md:17424-17426` (the footer
`---` / `*Co-built with Claude, June 2026.*`), `:17407-17421` (TICKET-0099's
G1 entry, whose last paragraph records G2's reactivation: "when a second
tab asks for a second button"); `tooling/glue/gen_decisions_index.py`
(regenerates `DECISIONS_INDEX.md`).
Consequence: each brief appends one entry above the footer and regenerates
the index; B's entry records that G2's condition fired and how it was
answered.

### R-18 — the build [M]
Opened: `frontend/package.json` (`build`: `vite build && node
scripts/write-manifest.mjs`); `tooling/verify/checks/frontend_build_fresh.py:1-25`
(the manifest's source hash must match `frontend/src/` and the root files).
Finding: on `main`, a rebuild changes only `.build-manifest.json`'s
`built_at`. Node 22 was used for the prototype (`package.json` asks
≥ 24.18; `npm ci` warns only); the bundle hash matched `main`'s.
Consequence: every brief rebuilds and stages `src/world_engine/cockpit/static/`.

### R-19 — Svelte warnings [M]
Opened: the prototype's `npm run build` output before and after C (E3).
Finding: C removes `EntityList.svelte`'s breadcrumb warnings and adds none;
the remaining `EntityList.svelte` warnings are the flat and record rows'
pre-existing ones.
Consequence: REPORT-ONLY for any warning on a file the brief does not touch.

### R-20 — CLAUDE.md [M]
Opened: `CLAUDE.md:351-368` (Création invariants: registry entry, island
mount, the ONE graph primitive, `sheetType` selects the fiche's branch,
container sizing, `$effect` self-write).
Consequence: named per brief under "Invariants to defend"; none is amended.

## Contract sheet

### C-01 — a node's click stays on the node
Produced by: A   Consumed by: every graph consumer (lieux, relations, review)
In `Graph.svelte`, every node `<g>` that declares `onmousedown=` also
declares `onclick={(e) => e.stopPropagation()}`. The press itself is still
handled on mousedown/mouseup (R-01); the canvas's `handleCanvasClick` still
clears the selection on a click on the empty canvas. Held by
`graph_primitive.py` rule 12: every `<g …>` opening tag declaring
`onmousedown=` declares an `onclick={…}` whose value contains
`stopPropagation()`; zero such tags collected is a failure.

### C-02 — the Lieux node click
Produced by: A   Consumed by: nothing in this lot (Nia, live)
`consumers/lieux.js` exports `onNodeClick(nodeId)` →
`selectEntity(document, nodeId)`, imported from
`'../../creation/sheetState.svelte.js'`. Fires on both taps of a connection
(R-03). Help text: « Cliquez un nœud pour le sélectionner et ouvrir sa
fiche, puis un second pour le connecter. Glissez pour repositionner.
Cliquez un lien pour le supprimer. »

### C-03 — `Sheet.svelte`'s `primaryAction(variant)` (family)
Produced by: TICKET-0099 (none, `'system'`), B (`'batch'`)   Consumed by: B
| variant | effect |
|---|---|
| none | resets the six drafts, `enterCreateMode(<tab's type>)`; a competences fiche gets `blankRecord()` |
| `'system'` | same; a competences fiche gets `blankRecord('system')` |
| `'batch'` | returns BEFORE the resets: the fiche is untouched. When `sheetType === 'location'`, `!sheetIsNew` and `sheetDetail.id`: `openRoomBatch(sheetDetail.id, sheetDetail.name \|\| '')`. Otherwise `#author-status` gets class `author-status err` and the text `BATCH_NEEDS_LOCATION` = « Ouvrez un lieu pour y générer un lot. » |
Written before B's member; re-read after it.

### C-04 — Lieux' `secondaryAction`
Produced by: B   Consumed by: `Creation.svelte` (band), `creation_island.py` rule 11b
`CREATION_TABS.lieux.secondaryAction = { label: '+ lot', handler: () =>
triggerPrimaryAction('entitySheet', 'batch') }`, declared right after
`lieux.primaryAction`. The band renders « + lot » then « + Nouveau ».

### C-05 — the Lieux tree
Produced by: C   Consumed by: C (markup)
`lieuxExpanded`: a `$state` `Set` of location ids, replaced (never mutated
in place) by `lieuxToggleExpanded(id)`; reset to an empty `Set` on a new
Lieux activation (where the descent pair was reset). Kept across list
refreshes.
`lieuxVisibleRows()` → `[{ loc, depth, childCount, expanded }]`, preorder:
the roots of `lieuxChildrenOf(null)` (unchanged, R-10), then, under each
row whose id is in `lieuxExpanded`, its `lieuxChildrenOf(id)` at `depth +
1`; siblings sorted by `name.localeCompare` at every level; a `seen` set
skips an id met twice (a parent cycle). `childCount` is
`lieuxChildrenOf(id).length`, so « Actifs seulement » filters it too.
Row: `.author-list-item`, `active` when `loc.id === selectedEntityId`,
`inactive` when `loc.status !== 'active'`, `padding-left: 14 + 16 × depth`
px, `role="button" tabindex="0"`, click/Enter → `onSelectEntity(loc.id)`.
`.ali-name` = name; `.ali-meta` = `location_type || '—'` « · » `status`,
then, when `childCount > 0`, `<button class="lieux-children-btn">` « N
enfant(s) › » folded or « … ⌄ » unfolded, whose click stops propagation and
toggles. Empty → « Aucun lieu. ».

## Gate output

### (a) Property trace
| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| a node press is handled on mousedown/mouseup | R-01 | `Graph.svelte:194-249` |
| the `<svg>` clears selection on click | R-01 | `Graph.svelte:286-293` |
| the node `<g>` has no `onclick` | R-01 | `Graph.svelte:314-318` |
| `onNodeClick` fires on both taps | R-03 | `Graph.svelte:251-273` |
| a consumer's `onNodeClick` is wrapped plain | R-03 | `graph/mount.js:78-87, 166-183` |
| the Lieux consumer has no `onNodeClick` | R-04 | `consumers/lieux.js` (whole) |
| `selectEntity(legacyDoc, id)` loads and selects | R-05 | `sheetState.svelte.js:109-124` |
| islands receive the shell document | R-05 | `creation/mount.js:91` |
| a graph consumer already imports `sheetState` | R-05 | `consumers/relations.js:26` |
| `graph_primitive.py` has no click rule | R-06 | `graph_primitive.py` (whole) |
| `tooling/` is outside the module budget | R-06 | `module_budget.py:1-25` |
| rule 11b: two literals, same key, non-vacuous | R-07 | `creation_island.py:952-982` |
| `triggerPrimaryAction` forwards the variant | R-07 | `creation/mount.js:134-143` |
| `primaryAction(variant)` always enters create mode | R-07 | `Sheet.svelte:214-226` |
| the band renders secondary then primary | R-07 | `Creation.svelte:113-118` |
| `openRoomBatch(anchorId, anchorName)` | R-08 | `roomBatch.svelte.js:52-57` |
| its one caller is the descent view | R-08, E2 | `EntityList.svelte:345` |
| a saved location's detail has `id`, `name` | R-09 | `crud/entities.py:229-240, 486-508` |
| create mode sets `sheetIsNew` and `{}` | R-09 | `Sheet.svelte:185-190` |
| the fiche's error idiom on `#author-status` | R-09 | `Sheet.svelte:447…635` |
| roots: no parent or an unknown parent | R-10 | `EntityList.svelte:267-275` |
| location types are per-world strings | R-11 | `models/canon.py:209-271` |
| statuses: four offered, none enforced | R-12 | `models/canon.py:133`, `crud/entities.py:112` |
| `/api/locations` returns type and status | R-13 | `crud/locations.py:264-284` |
| location_tree fails token + recursion only | R-14 | `location_tree.py` (implementation) |
| the shared row markup | R-15 | `creation.css:217-226`, `CompetencesList.svelte:52-90` |
| static CSS must equal the public copy | R-16 | `stylesheet_partition.py:385-399` |
| decision header pattern and footer | R-17 | `decisions_index.py:14-17`, `ARCHITECTURE_DECISIONS.md:17424` |
| G2's recorded reactivation condition | R-17 | `ARCHITECTURE_DECISIONS.md:17420-17421` |

Presupposition sweep: no brief says "follow the convention" without naming
the file and lines. Every "as" names its source: the fiche's error idiom
(`Sheet.svelte:482`), the record row (`CompetencesList.svelte:52-90`), the
Compétences `secondaryAction` (`tabs.js:277`).

### (b) Case tables

**A node press, before and after C-01** (Lieux: `onConnect` and
`onMoveNode` present; relations global armed: `onConnect`, force layout):
| gesture | `main` | after A |
|---|---|---|
| 1st click on node X | selected on mouseup, cleared by the bubbling click → nothing selected | X selected (accent), X's fiche opens (Lieux) |
| 2nd click on node Y ≠ X | first-tap path again (nothing was selected) | Y's fiche opens, `onConnect(X, Y)`, graph reloads |
| 2nd click on X itself | — | selection cleared, nothing connected (`a === nodeId`) |
| click on Y already linked to X | — | Y's fiche opens, nothing connected (undirected dedup) |
| drag a node (moved > 5 px) | moved, saved | unchanged: `onMoveNode`, no tap |
| click on an edge | delete prompt | unchanged (edges stop their own click) |
| click on empty canvas | clears selection | unchanged |

**C-03 variants × fiche state:**
| variant | fiche | result |
|---|---|---|
| none / `'system'` | any | create mode (unchanged) |
| `'batch'` | saved location | room batch opens, anchored on it; fiche unchanged |
| `'batch'` | location in create mode | message, nothing opens |
| `'batch'` | empty (no fiche) | message, nothing opens |
| `'batch'` | non-location | unreachable: « + lot » exists on Lieux only |

**C-05 rows:**
| row | children (after the filter) | in `lieuxExpanded` | shows |
|---|---|---|---|
| any | 0 | — | name, « type · status », no button |
| any | n > 0 | no | « n enfant(s) › »; children hidden |
| any | n > 0 | yes | « n enfant(s) ⌄ »; children at depth + 1 below it |
| status `active` | — | — | normal |
| status ≠ `active` | — | — | `inactive` class (struck, faded); hidden under « Actifs seulement » unless an active descendant |
| parent unknown to the list | — | — | a root (R-10) |
| parent cycle A↔B | — | — | neither is a root, so neither shows (as on `main`); `seen` keeps an unfolded cycle finite |

**Rule 12:**
| node `<g>` | verdict |
|---|---|
| `onmousedown` + `onclick` calling `stopPropagation()` | pass |
| `onmousedown`, no `onclick` | FAIL |
| `onmousedown` + `onclick` not calling it | FAIL |
| no `onmousedown` | not examined |
| zero examined in the file | FAIL (vacuous) |

### (c) Enumerations

E1 — files using each class of the descent view's CSS (outside built
assets), on `main`:
```
lieux-browse-head: frontend/src/creation/EntityList.svelte
lieux-breadcrumb:  frontend/src/creation/EntityList.svelte
lb-seg / lb-sep / lb-current: frontend/src/creation/EntityList.svelte
lieux-bucket-head: frontend/src/creation/EntityList.svelte frontend/src/creation/CompetencesList.svelte
lieux-node-row / ali-name-btn / dimmed: frontend/src/creation/EntityList.svelte
lieux-status-pill / lieux-descend-btn: frontend/src/creation/EntityList.svelte
legacy.html and static/index.html: 0 occurrences of each
```

E2 — `git grep -n "openRoomBatch" main -- frontend/src`:
```
frontend/src/creation/EntityList.svelte:56:  import { openRoomBatch } from './roomBatch.svelte.js';
frontend/src/creation/EntityList.svelte:345:      <button class="btn-icon" onclick={() => openRoomBatch(lieuxParentId, …)}>Générer un lot ici</button>
frontend/src/creation/RoomBatch.svelte:21:     roomBatch.svelte.js's openRoomBatch(anchorId, anchorName), a plain   (comment)
frontend/src/creation/roomBatch.svelte.js:52:export function openRoomBatch(anchorId, anchorName) {
```
After B: plus `Sheet.svelte` (import and call). After C: the two
`EntityList.svelte` lines are gone.

E3 — `EntityList.svelte` lines carrying a Svelte warning in `npm run
build`: before C `208:2, 324:6 ×2, 338:6 ×2, 341:8 ×2, 374:6 ×2, 389:6 ×2`;
after C `204:2, 322:6 ×2, 361:6 ×2, 376:6 ×2` — the same flat, intrigues
and evenements rows and the listener, shifted; the breadcrumb's two pairs
gone; none on the new rows.

E4 — node `<g>` tags in `Graph.svelte` declaring `onmousedown=`: one
(`:314`). Rule 12 after A: `1 node click(s) contained`.

E5 — `secondaryAction` entries in `CREATION_TABS`: after B, two —
`competences` (`'system'`) and `lieux` (`'batch'`).

### (d) Families
✓ C-03 (`primaryAction` variants) written with its two existing members
before B's `'batch'`, re-read after it: `'batch'` is the only variant that
opens no record, so it returns before the draft resets.

### (e) Gates and the module that satisfies each
| gate | status | satisfied by |
|---|---|---|
| `graph_primitive.py` rule 12 | proposed (A) | `Graph.svelte`'s node `<g onclick>` |
| `graph_primitive.py` rules 1–9, 11 | passed (A) | unchanged; the consumer gains a callback, not an engine |
| `import_cycle.py` | passed (A) | `lieux.js` → `sheetState.svelte.js`, which imports nothing from `graph/` |
| `creation_island.py` rule 11b | passed (B), 2 paired | `tabs.js` `lieux.secondaryAction` |
| `page_contract.py` | passed (B, C) | no tab-specific branch in `Creation.svelte`; the band renders `activeEntry` |
| `creation_tab_switch.py` | passed (B) | `Sheet.svelte` branches on the variant, then on `sheetType` |
| `location_tree.py` | passed (C) | `EntityList.svelte`: iterative flattening, no recursion, no token |
| `stylesheet_partition.py` | passed (C) | `frontend/public/creation.css` + rebuild |
| `effect_self_write.py` | passed (A, B, C) | no `$effect` added |
| `module_budget.py` (frontend) | passed | `EntityList.svelte` 386 lines, `Sheet.svelte` 843 |
| `frontend_build_fresh.py` | passed (A, B, C) | rebuild per brief |
| `decisions_index.py` | passed (A, B, C) | one strict header per brief + regenerated index |

## Amendments
