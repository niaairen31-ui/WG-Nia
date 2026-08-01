---
id: TICKET-0058
title: Creation surface - entity-authoring spine migration
type: feature
status: exec
created: 2026-07-31
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: large
brief_ids: [BRIEF-0058-a, BRIEF-0058-b, BRIEF-0058-c, BRIEF-0058-d, BRIEF-0058-e, BRIEF-0058-f, BRIEF-0058-g, BRIEF-0058-h, BRIEF-0058-i, BRIEF-0058-j, BRIEF-0058-k, BRIEF-0058-l]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Nous travaillons sur le refactor de l'index. quatrieme ticket de la serie
(ticket 0058)."

Decisions locked in one message after the option blocks: **A1, B2, C2, D1, E1.**

## Clarifications resolved (intake)

**A1 - the seam runs legacy-hosts-Svelte.** `CREATION_TABS`
(`index.html:4274`), the dispatcher `showCreationSubTab` (`index.html:4463`)
and the activation path `_creationActivateTab` (`index.html:4433`) all stay
in the legacy document for the whole of this ticket. A migrated surface
becomes a Svelte ISLAND mounted into the legacy container it already owns,
signalled by a CustomEvent on the legacy document - the exact mechanism
TICKET-0057 proved with `graph:slot` (`index.html:4118-4122`,
`frontend/src/graph/mount.js:129`).

Rejected: shell-owned Creation chrome. It would put a Svelte tab bar and the
legacy tab bar in the tree simultaneously for two tickets, with a
synchronization contract between them - two authorities over one fact, which
is the failure mode this whole workstream exists to end.

Forced by the state of the repository, not chosen: `frontend/src/legacy/registry.js:11`
declares `creation: { retiredBy: 'TICKET-0059' }`. The legacy Creation mount
survives this ticket by prior commitment. A ticket that migrated the chrome
would have had to defeat that registry.

**B2 - the scope is the call closure of `author*`, not the label "spine".**
Measured on `main` this session: `author*` is 107 functions
(`index.html:4751..10133`), and its non-`author*` callers include
`evenementsRenderCreatePanel` / `evenementsSave` / `evenementsSubmitCreate`
(`index.html:5274`, `5306`), `regionCommit` (`index.html:6687`), `batchCommit`
(`index.html:7061`), `npcGoalsBackfillAll` (`index.html:10111`),
`_factionRosterRowHtml` (`index.html:8915`), `_buildRuntimeCreationTabs`
(`index.html:7263`) and the three `creation*` navigation helpers
(`index.html:9359`, `9380`, `9392`).

`evenements` and `region` are both 0059 in the workstream map. They call the
sheet engine. Migrating the engine without them leaves two tabs calling a
function that no longer exists in their scope. So the cut follows the call
graph: this ticket takes the sheet engine plus every caller of it. The
remaining Creation tabs - `competences`, `registre`, `prompts` - plus the
link agent and world CRUD stay with TICKET-0059.

The exact closure is confirmed or corrected by BRIEF-0058-a M4 before any
migration brief executes.

**C2 - the relation graph converges onto the SVG renderer; cytoscape goes.**
`frontend/src/graph/registry.js:16` already declares
`relation_cytoscape: { retiredBy: 'TICKET-0058' }`. The convergence is owed.
The question was HOW: wrapping cytoscape inside `Graph.svelte` as a second
renderer selected by a `layout: 'force'` axis, or implementing force layout
on the single existing SVG renderer and deleting the 435 KB vendored engine
(`src/world_engine/cockpit/vendor/cytoscape-3.34.0.min.js`).

C1 was rejected because it preserves exactly what the lock exists to end:
two engines behind one API is the leaky union type TICKET-0057 named and
refused (TICKET-0057, section E1). "Un graph est un graph" is not satisfied
by one import path over two renderers.

The accepted cost is real and is not hidden: ego/global modes, zoom/pan,
strength buckets, double-tap recentring and the edge panel are
reimplemented, not carried. BRIEF-0058-a M2 inventories them function by
function and M1 measures whether a force simulation is viable at the
observed graph size BEFORE any of it is written. If M1 is REFUTED, C2 is
not constructible and the ticket returns to Nia for a re-decision on
Bloc C - it does not silently fall back to C1.

**D1 - the graph lock learns to pass on zero.** `graph_primitive.py:151`
fails when the registry parses zero entries. `relation_cytoscape` is the
last entry; retiring it in this ticket turns a fail-closed guard into a
false alarm, and does so at precisely the moment the guarantee becomes
total. The rule moves from "prove the declared implementation is present"
to "prove every baselined implementation is gone". Sentinel entries were
rejected as dormant declarations; retiring the check was rejected as
losing the permanent lock.

**E1 - continuous route sync lands here.** TICKET-0056 deferred it by name
(`frontend/src/App.svelte:11-16`, ARCHITECTURE_DECISIONS). It is owed to
this ticket. Under A1 the legacy document keeps the tab bar for two more
tickets, so without sync a deep link degrades on the first click. The
legacy document dispatches a CustomEvent; the shell converts it to
`history.replaceState`. No new direction of control: the same one-way
legacy -> shell signalling `graph:slot` already established.

## Acceptance criteria

### Machine-checkable -> G1 deterministic gate

- [ ] `frontend/src/graph/registry.js` declares zero implementations, and
      `graph_primitive.py` passes on that basis by proving each baselined
      key absent from its locus -> verify/checks/graph_primitive.py
- [ ] No `relGraph*` function declaration remains in `index.html`; the
      tokens are absent in any context, comments included
      -> verify/checks/graph_primitive.py
- [ ] No vendored cytoscape asset and no route serving one
      -> verify/checks/graph_primitive.py, relation_graph.py
- [ ] Every Svelte island mounted into the legacy document is declared in
      `frontend/src/creation/registry.js` and reached through the single
      `island:slot` channel; a second mount mechanism fails the check
      -> verify/checks/creation_island.py
- [ ] `page_contract.py` asserts the tab mechanism against its new locus
      with every TAB_KEYS entry still covered; zero collected entries is a
      failure -> verify/checks/page_contract.py
- [ ] The review component's registry/cascade guarantee holds at its new
      locus -> verify/checks/review_component.py, review_root_fallback.py
- [ ] Return-navigation, event tab and faction roster guarantees hold at
      their new loci -> verify/checks/creation_return_nav.py,
      event_tab.py, faction_roster_panel.py
- [ ] `legacy_mount.py` still passes with `creation` present in the
      registry (this ticket does not retire it)
      -> verify/checks/legacy_mount.py
- [ ] `frontend_build_fresh.py` passes -> verify/checks/frontend_build_fresh.py
- [ ] No `<svg` emitted under `frontend/src/` outside `frontend/src/graph/`
      -> verify/checks/graph_primitive.py rule 6

### Live -> human gate (Nia)

- [ ] The NPC relation graph opens from its on-demand toggle, renders ego
      and global modes, honours the four strength buckets, zooms and pans,
      recentres on double-click, and saves and deletes an edge in global
      mode - with no cytoscape in the tree.
- [ ] Creating an entity type in Constructeur still produces a live sub-tab
      in the same session (TICKET-0046 guarantee), now with a Svelte
      Constructeur.
- [ ] Every entity tab - NPC, PJ, Lieux, Factions, Objets, Artefacts,
      Intrigues, Evenements, plus at least one runtime type - lists,
      selects, opens, edits, saves and creates.
- [ ] Region generation and the room batch generator commit through the
      migrated sheet engine, with their pre-commit graph previews intact.
- [ ] The Review Queue reviews and commits a mutation batch, cascade
      behaviour unchanged.
- [ ] Deep-linking `/creation/<tab>` opens that tab, and clicking a
      different sub-tab rewrites the address bar to match.
- [ ] `competences`, `registre` and `prompts` still work unchanged from the
      legacy document.
