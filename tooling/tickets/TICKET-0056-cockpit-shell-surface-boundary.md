---
id: TICKET-0056
title: Cockpit shell + hard surface boundary (legacy-mount registry, iframe seam, shell routing)
type: feature
status: exec
created: 2026-07-30
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0056-a, BRIEF-0056-b, BRIEF-0056-c, BRIEF-0056-d]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Nous travaillons sur le refactor de l'index. deuxieme ticket de la serie
> (ticket 0056)

Second ticket of the index-split chain (0055 -> 0061) mapped in
`Active_project.md`. Scope as mapped: build the shell and the three-view
router, establish Play / Creation / Observation as distinct mount points, and
give shared top-level state a home. It also pays TICKET-0055's one named
deferral: the legacy-mount registry.

## Clarifications resolved (intake)

Locked as `A2, B1, C3, D3b, D-i(1), D-ii(now), E1, F3, G1`.

- **A2 -- the registry has THREE entries, not one.** `play`, `creation`,
  `observation`, each declaring the legacy show-function it owns, all above a
  SINGLE legacy document loaded once. TICKET-0055's deferral requires a
  registry that shrinks monotonically to exactly one entry (Play) at
  TICKET-0061; a single "the monolith" entry (A1) cannot shrink, it can only
  vanish, and would make the registry a TODO instead of a measurable gate.
  A3 (splitting `index.html` into three physical files now) is refused: RECON
  A2 of the map established that the domains are physically interleaved
  (`author*` spans ~4751..10136, the batch/mutation review cluster sits inside
  the Play scene code at ~2801..3300) and cannot be range-cut.
- **B1 -- one same-origin iframe, and `index.html` stays byte-untouched.**
  The three top views are three `display:none` siblings in ONE document over
  ONE global scope (`index.html:1067` / `:3331-3363`, globals at `:1627-1628`);
  "load only Play's JS" is not constructible -- `esc`, `api`, `genericModal*`,
  `WORLD_ID`, `playerCharIds` are shared. An iframe isolates JS and CSS by
  construction, so the 319 inline handlers and 175 globals keep working with
  zero edits, and the nine index-anchored checks stay green by non-event.
  B2 (same-document injection) is refused: it would merge 175 globals and
  1039 lines of unscoped CSS (element selectors `header`, `body`) into the new
  shell -- importing the debt into the clean surface.
- **B1 needs no `postMessage`.** Shell and legacy are same-origin
  (`127.0.0.1:8000`), so the bridge calls `contentWindow.showCreationView()`
  directly. Zero legacy edit, one direction of control, and the confinement is
  checkable rather than conventional.
- **C3 -- the SERVER stays the authority on world/player; the shell holds a
  mirror.** The active world is server state (`POST
  /api/worlds/{id}/activate`, resolved by `GET /api/bootstrap`,
  `creator.py:379` / `:487`). Neither client half owns it. The shell does NOT
  reimplement the switch cascade: it calls the legacy `activateWorld(worldId)`
  (`index.html:12169-12199`) through the bridge -- one authority for
  `_creationRunWorldSwitchResets()` -- then re-reads `/api/bootstrap` into its
  own store. C1 (store as sole authority) would create a second authority
  facing the server; C2 (legacy stays authoritative, shell passive) would
  leave the shell unexercised for three tickets.
- **C3 corollary -- the mirror must fail LOUD.** `loadBootstrap()`
  (`index.html:3379-3385`) swallows every error (`catch (_) {}`). The shell's
  read must not reproduce that: a failed bootstrap is a visible refusal, not a
  silent null.
- **D3b -- history API with ENUMERATED shell routes, no catch-all.** Measured
  against a catch-all (D3a): the 151 route literals do NOT carry `/api` in
  their text -- `crud/_router.py:12` declares `prefix="/api"` and its modules
  write `@router.get("/entities")`. The prefix is a property of the mounting,
  not of the text, so a catch-all's exclusion list is a convention with a new
  silent failure mode (a future router included without the prefix disappears
  into the shell; `GET /api/entitie` returns 200 HTML instead of 404). D2
  (hash routing) is fail-open in the other direction: `#/creaton` can never be
  a 404. D3b makes a surface typo a real 404 and leaves API 404s intact.
- **D3b's one duplication, paid by a check (D-i(1)).** The surface vocabulary
  exists in `app.py` and in the shell router. `legacy_mount.py` asserts the two
  literals agree -- one vocabulary, two readers, one gate. No separate
  `shell_routes.py`.
- **D-ii -- the sub-tab segment lands NOW.** `/creation/{sub_tab}` from the
  start; retrofitting it at TICKET-0058 would change a URL contract already in
  use. The server enumerates the three SURFACES only and never learns the tab
  vocabulary: the sub-tab segment is opaque server-side and resolved
  client-side against `CREATION_TABS`, preserving `page_contract`'s rule that
  the tab mechanism is asserted structurally and live types are never
  enumerated. Unknown sub-tab falls back to `npc` -- the same fallback
  `activateWorld` already uses (`index.html:12193`), for the same reason (a
  runtime type may have disappeared), not a new behavior.
- **E1 -- the seam flips in this ticket.** `GET /` serves the shell, `GET
  /legacy` serves `index.html`, `GET /shell` is removed. `app.py:235-245`
  wrote `/shell` as "the seam TICKET-0056 renames to `/`". E2 (defer the flip
  to 0060) would leave the shell unexercised in real use until it is too late
  to correct cheaply.
- **F3 -- the registry check reads every field it declares.** `legacy_mount.py`
  asserts: entry set non-empty and a SUBSET of a committed baseline (monotone
  shrink; removing passes, adding fails), every `retiredBy` matching
  `^TICKET-\d{4}$`, every `showFn` present as a top-level function in
  `index.html`, confinement of legacy access to the bridge module, and a single
  frame-`src` assignment site. A `retiredBy` field no check reads would be
  decoration -- "no structure without a reader" applies to the governance
  artifact itself.
- **G1 -- no check is re-homed by this ticket.** Nothing structural moves:
  `index.html` is untouched, so `page_contract`, `review_component`,
  `relation_graph`, `creation_return_nav`, `event_tab`,
  `faction_roster_panel`, `observation_surface`, `review_root_fallback` and
  `schema_0024` stay green where they are. Re-homing happens in the ticket that
  moves the target (cross-cutting rule, PART C of the map). This ticket ADDS
  one check.
- **Correction of an intake claim, recorded.** A byte-equality assertion on
  `index.html` DOES exist and is permanent -- `relation_graph.py:192-206`
  compares each `LIEUX_GRAPH_FUNCTIONS` body against `main` via `git show`. It
  is scoped to the Lieux graph functions, not the whole file. It passes
  trivially here because `index.html` is untouched; it is named so the next
  ticket that edits those functions knows the gate exists.
- **The 3D guard-rail is NOT re-stated here.** The map assigned it to 0056,
  but TICKET-0055's decision entry already re-nailed it ("The 3D guard rail,
  re-nailed"). Restating it would duplicate doctrine. BRIEF-0056-d
  cross-references instead, and flags the map's stale line.
- **The map's "Play preserved as an HTMX island" is factually wrong.**
  `grep -c "hx-"` on `index.html` returns 0; TICKET-0055 already corrected the
  record. Play is a vanilla-JS island. `Active_project.md` is corrected as part
  of BRIEF-0056-d.
- **Renaming `index.html` -> `legacy.html` is OUT.** Three files now share the
  name (`frontend/index.html` the Vite entry, `cockpit/index.html` the legacy
  surface, `cockpit/static/index.html` the build output). The rename touches
  all nine index-anchored checks; it belongs to TICKET-0061, where those checks
  are retired anyway.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The legacy-mount registry is non-empty, is a subset of its committed
      baseline, every entry declares a well-formed `retiredBy` ticket and a
      `showFn` that exists in `index.html`, legacy access is confined to the
      bridge module, the legacy frame has exactly one `src` assignment site,
      and the shell-route vocabulary in `app.py` matches the shell router's;
      all assertions fail vacuously-closed on a missing or empty input
      -> verify/checks/legacy_mount.py
- [ ] The committed frontend build matches a freshly recomputed hash of the
      frontend sources after every brief that edits `frontend/`
      -> verify/checks/frontend_build_fresh.py
- [ ] `index.html` is not touched by this ticket: the Creation page contract
      still holds -> verify/checks/page_contract.py
- [ ] `index.html` is not touched by this ticket: the vendored cytoscape file
      and its GET route survive, and the Lieux graph functions remain
      byte-identical to `main` -> verify/checks/relation_graph.py
- [ ] `index.html` is not touched by this ticket: the review component
      boundary still holds -> verify/checks/review_component.py
- [ ] `index.html` is not touched by this ticket: the observation surface
      anchors still hold -> verify/checks/observation_surface.py
- [ ] `index.html` is not touched by this ticket: the Creation return-crumb
      ordering still holds -> verify/checks/creation_return_nav.py
- [ ] `CLAUDE.md` still satisfies its structural contract after the doctrine
      amendment (section whitelist, 500-line budget, File-structure budget,
      archaeology ban, pointer freshness)
      -> verify/checks/claude_md_contract.py
- [ ] `DECISIONS_INDEX.md` remains consistent with the decision corpus after
      the new entry -> verify/checks/decisions_index.py

### Live  ->  human gate (Nia)

- [ ] `http://127.0.0.1:8000/` renders the shell: shell header (mode tabs +
      world selector) above the legacy cockpit, which behaves exactly as on
      `main` -- Play discussion/historique/savoirs/spatiale, every Creation
      sub-tab, the NPC relation graph, the Lieux graph, the review queue.
- [ ] `http://127.0.0.1:8000/legacy` renders the bare legacy cockpit with its
      own header, unchanged, as an escape hatch.
- [ ] Switching surfaces from the shell header changes the URL
      (`/play`, `/creation/npc`, `/observation`) and does NOT reload the legacy
      frame: the Play transcript scroll position and any open Creation form
      survive a round trip Play -> Creation -> Play.
- [ ] Browser Back / Forward walks the shell's surface history one step at a
      time, never through an iframe load.
- [ ] A cold load of `http://127.0.0.1:8000/creation/lieux` lands directly on
      the Lieux sub-tab with its content rendered (deep-link + readiness wait).
- [ ] A cold load of `http://127.0.0.1:8000/creation/<a runtime entity type
      created from the Constructeur>` lands on that runtime tab -- proving the
      server never needed the tab vocabulary.
- [ ] `http://127.0.0.1:8000/creaton` returns 404; `http://127.0.0.1:8000/api/entitie`
      returns 404 (not HTML). Both checked in the browser network tab.
- [ ] Switching the active world from the shell header re-activates it
      server-side, refreshes the shell selector, and the Creation tabs show the
      new world's rows with no stale row from the previous world.
- [ ] `+ Monde` and `🗑 Monde` from the shell header open the legacy modals and
      complete normally.
- [ ] Red-test of the new gate, run live: adding a fourth entry to
      `LEGACY_MOUNTS` turns `legacy_mount.py` red; removing it turns it green.
      Removing the `creation` entry also leaves it green (monotone shrink).
- [ ] `git status` is clean after `npm run build`.
