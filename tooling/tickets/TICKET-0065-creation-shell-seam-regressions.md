---
id: TICKET-0065
title: Creation shell seam regressions — graph mount document + shell height chain
type: bug
status: exec
created: 2026-08-19
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0065-a, BRIEF-0065-b]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Voila une capture d'écran de la partie création, NPC de mon nouveau Frontend.
> Avant les NPC existant dans mon monde étais listé a gauche et je pouvais
> scroll down. et lorsque je clique sur un NPC, j'ai la possibilité de le
> modifié. (même chose pour tous les autres entités. De plus, je n'ai pas
> l'impression que les graphs fonctionne encore. Est-ce que je suis mieux de
> terminer la série de ticket (ticket 0060 et 0061) avant de m'attaqué a ce
> problème. Ne prend pas mes commentaires comme une liste exhaustive des
> problèmes. Je veux que tu me dise ce qui est la cause la plus probable de mes
> soucies. Fait un RECON complet avant de me répondre.

## Clarifications resolved (intake)

RECON was run against `main` as fetched this session (tarball). Three findings.
Two are real defects owned by this ticket; the third turned out to be a
delivery-layer problem and is now TICKET-0066.

**F1 — the graph mount seam dispatches and listens on two different
documents.** After TICKET-0059 moved Creation out of the legacy iframe, every
`graph:slot` / `graph:invalidate` dispatch fires on the SHELL document, while
the only listeners are registered on the LEGACY document:

| Site | Document |
|---|---|
| `frontend/src/creation/tabs.js:365` — dispatch `graph:slot` | shell (`document`) |
| `frontend/src/creation/tabs.js:192` — dispatch `graph:invalidate` | shell (`document`) |
| `frontend/src/creation/mount.js:91` — `props: { legacyDoc: node.ownerDocument }` | shell (containers are Creation.svelte's own children) |
| → `Region.svelte:200`, `RoomBatch.svelte:238,265`, `Sheet.svelte:551`, `linkAgent.svelte.js:340` | shell (via that prop) |
| `frontend/src/App.svelte:54` — `initGraphMount(legacyDocument())` | **legacy iframe** |
| `frontend/src/graph/mount.js:246,253` — `legacyDoc.addEventListener(...)` | **legacy iframe** |

Nothing listens on the shell document, so no graph ever mounts. Even if the
event were heard, `graph/mount.js:122` and `:193` resolve the container via
`legacyContainer(id)` (`frontend/src/legacy/bridge.js:61` →
`legacyWindow().document.getElementById`), which throws for
`#relgraph-mount`, `#creation-lieux-graph`, `#region-graph-mount` and
`#batch-graph-mount` — all children of `Creation.svelte` now. Scope is wider
than reported: the Region and RoomBatch pre-commit review previews are dead
too, not only the NPC relation graph and the Lieux graph.

Root cause is recorded in the code itself. `frontend/src/creation/mount.js:11-15`
documents that container resolution moved from `legacyContainer(id)` to
`document.getElementById(id)` at BRIEF-0059-l, and `:23` names
`graph/mount.js` as "a distinct, already-established mechanism" — an explicit
exclusion whose premise (Creation lives in the iframe) was invalidated by a
later commit in the same merge train, with no check assuming the governance
burden. Same failure shape as the three inference-not-measurement claims
already logged during TICKET-0059.

**F2 — the shell gives Creation no height.** Every height source in the shell
document:

- `frontend/public/shared.css:11` — `html, body { height:100%; overflow:hidden }`
- `frontend/src/LegacyFrame.svelte:29` — `iframe { height: calc(100vh - var(--header-height)) }`
- `frontend/src/App.svelte:76-78` — `.shell-layout { --header-height: 56px }` and nothing else
- `#app` (`frontend/index.html:10`) — no rule anywhere

`body` is a full-height flex column, but `#app` is a flex item with
`flex: 0 1 auto` (content height) and `.shell-layout` is a plain block. So
`#creation-view.app-view { flex:1; min-height:0 }` (`shared.css:41`) and
`#creation-editor-area.layout { flex:1; min-height:0 }` (`creation.css:299,335`)
have no flex parent with a definite height. The viewport-height column ending
in a scrollable `.conv-list` — which worked when `.app-view` was a direct child
of the legacy `body` — is severed by the two wrapper elements the shell
introduced. Play and Observation are unaffected because the iframe sizes
itself off `100vh` explicitly; Creation is the only surface that depended on
the inherited chain and the only one nobody gave one back.

**F3 — RESOLVED at intake, not a defect in this repo: browser heuristic
caching of the two unhashed stylesheets.** The originally reported symptom (the
entity list rendering full-width with no grid, no `.panel-head` band, and
`+ Nouveau` drawn as a default UA button) was NOT reproducible from `main`.
Everything on disk was verified correct: the committed bundle ships
`containers:["creation-editor-area"]`, `panel-head`, `btn-send`, `conv-list`,
`sidebar-head`, `right-col`, `transcript-panel`; the SERVED
`static/shared.css` carries `.app-view`:41, `.sidebar-head`:42, `.conv-list`:56,
`.transcript-panel`:61, `.panel-head`:68, `.panel-head h2`:77, `.btn-send`:205
and the SERVED `static/creation.css` carries `.layout`:299, `.sidebar`:306,
`.right-col`:313; both files parse clean (final brace depth 0, no BOM, no
zero-width or nbsp characters, no recovery-triggering error); `_SHELL_ROUTES`
is enumerated and never a catch-all so nothing shadows the `/static` mount;
and `/legacy` was ruled out because `cockpit/index.html` contains zero
occurrences of `author-entity-list`, `creation-sub-tab` or `id="creation-view"`
and therefore cannot render that list at all.

The cause is the delivery layer. `shared.css` and `creation.css` carry STABLE
filenames by design — they live in Vite's `publicDir` and are copied unhashed
so that `cockpit/index.html` can `<link>` them by fixed path — while the
bundle and its scoped CSS are content-hashed. `src/world_engine/cockpit/app.py:91`
mounts them through `StaticFiles`, which sends `etag` and `last-modified` but
no `Cache-Control`, so the browser applies HEURISTIC freshness and reuses the
cached copy without contacting the server at all. When TICKET-0063/0064 moved
rules out of `cockpit/index.html`'s inline `<style>` into those two files, the
browser took the new JS (hashed name forces a fetch) and kept the old
stylesheets. A post-0059 bundle rendered its DOM against pre-0063 stylesheets —
which is exactly the selective pattern observed: `.creation-sub-tab-bar`,
`.row-card`, `.btn-ghost`, `.btn-icon` and `.author-list-item` already existed
in the cached copies, while `.layout`, `.sidebar`, `.panel-head`, `.conv-list`
and `.btn-send` did not yet.

Confirmed empirically: a server restart changed nothing (the browser was asking
the server nothing), and a single `Ctrl+F5` — which adds `Cache-Control:
no-cache` to the document request AND its subresources — restored the grid
immediately and permanently. A stale-server or stale-build hypothesis is
falsified by that outcome; only a browser-cache hypothesis survives it.

This ticket does NOT fix that. G1: it becomes **TICKET-0066**, since the fix
lives in `app.py` and is outside this ticket's declared frontend-only scope.
The reader that justified opening it now exists: a real session lost to a
symptom that presented as a layout defect.

**Locked decisions (A1, B1, C1, D1, E1, G1).** One ticket covering F1 and F2,
since both are the same class of TICKET-0059 fallout. Graph mount moves fully
onto the shell document, mirroring what `creation/mount.js` already did. A
single-document rule lands in `graph_primitive.py` with the fix. The height
chain is restored on `#app` / `.shell-layout` and the iframe's
`calc(100vh - …)` is replaced by `flex:1`, leaving one height authority instead
of two. F3 was verified locally (E1) and split out as TICKET-0066 (G1).

**Sequencing.** This ticket opens BEFORE TICKET-0060. TICKET-0060's first open
decision ("does Observation render a graph today") is unanswerable against a
dead mount seam, and TICKET-0061 deletes the legacy document — which would turn
a silent no-op into a thrown error buried in the decommission diff, against
PART C rule 1 of the workstream map (0061 is a seal, not where migration
happens). B1 also removes `graph/mount.js` from the legacy-reach surface,
shrinking what 0061 has to unwind. TICKET-0066 is independent of both and can
land in any order.

**E1 gate — RUN AND PASSED.** `git fetch` / `git status` / `git log`, then
`npm --prefix frontend run build`, then a prod-server restart: no change. Then
`Ctrl+F5`: the two-column grid returned and the entity sheet became reachable
again, while the entity list still does not scroll and no graph mounts. That is
branch 1 of the recorded prediction — F2 and F1 confirmed as the two remaining
defects, F3 confirmed as a delivery-layer problem. Both briefs are executable
as written.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] Zero `legacyContainer` references remain under `frontend/src/graph/`  -> verify/checks/graph_primitive.py
- [ ] `legacyContainer` is absent from `frontend/src/legacy/bridge.js` (no reader left)  -> verify/checks/legacy_mount.py
- [ ] Every `mountId`/`containerId` declared in a `graph: { ... }` spec resolves against the shell document, and no `graph:` event is dispatched on a document other than the one `initGraphMount` listens on  -> verify/checks/graph_primitive.py (new rule 11)
- [ ] Rule 11 is vacuous-proof: zero mount targets collected is a FAILURE  -> verify/checks/graph_primitive.py
- [ ] Zero `100vh` literals under `frontend/` — one height authority  -> verify/checks/shell_height_chain.py
- [ ] `.shell-layout` declares `display:flex`, `flex-direction:column` and a definite height  -> verify/checks/shell_height_chain.py
- [ ] `stylesheet_partition` still PASSES (rule7 coverage unbroken by the new rules)  -> verify/checks/stylesheet_partition.py
- [ ] `legacy_call`, `legacy_mount`, `creation_island`, `page_contract`, `frontend_build_fresh` all still PASS  -> existing checks
- [ ] `frontend_build_fresh` PASSES after `npm run build` — committed bundle matches source  -> verify/checks/frontend_build_fresh.py

### Live  ->  human gate (Nia)

Run every live criterion after a `Ctrl+F5`, until TICKET-0066 lands.

- [ ] Création > NPC: the entity list renders in a 300px left column with a visible right border
- [ ] Création > NPC: the list scrolls independently; the shell band and sub-tab bar stay fixed
- [ ] Création > NPC: clicking an NPC opens its editable sheet in the right column
- [ ] Création > NPC > "Voir le graphe": the relation graph mounts and renders
- [ ] Création > Lieux: the Lieux graph slot mounts and renders, drag-to-place still persists positions
- [ ] Création > Région: the pre-commit location graph preview mounts and renders
- [ ] Création > Lieux > room batch: the pre-commit batch graph preview mounts and renders
- [ ] Play and Observation still fill the viewport below the header, unchanged
- [ ] Switching Play -> Création -> Observation -> Création leaves no scroll or sizing artifact
- [ ] Browser console is free of `legacy/bridge: no element #...` errors across all four graph surfaces

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: a new entry recording that the graph mount seam
  is single-document (shell) as of this ticket, that `legacyContainer` is
  retired, and that the shell owns exactly one height authority.
- `CLAUDE.md`: only if the graph-primitive line asserts the iframe-mount
  premise; BRIEF-0065-b verifies and amends if so.
- `graph_primitive.py`'s own module docstring: rule 8's stated rationale ("the
  component renders inside the legacy iframe document, where Svelte injects
  scoped CSS into the SHELL's head") becomes factually false once the graph
  mounts in the shell. The rule is kept; its rationale is restated.
