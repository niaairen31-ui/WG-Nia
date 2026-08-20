---
id: TICKET-0060
title: Observation surface migration — last surface out of the legacy document
type: feature
status: exec
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0060-a, BRIEF-0060-b, BRIEF-0060-c, BRIEF-0060-d, BRIEF-0060-e]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Nous travaillons sur le refactor de l'index. Nous sommes au ticket 0060.
> Fait un RECON avant de me proposer des options et regarde l'état du main et
> des décisions qui ont été prises qui peuvent influencer ce ticket.

Decision block returned after RECON:

> A1, B1, C3 dès que cela sert à rien, on l'enlève, D1, E1, F1 + F3 en ticket
> nommé lorsque le refactor frontend est terminé (ticket 0060 et 0061 fait).
> G1 les live gate sont ok, c'est juste que je ne gaspille pas de tokens à le
> réécrire à Claude Code et que je ne modifie pas les documents manuellement.
> Je le fais toujours et j'interviens s'il y a quelque chose.

## Clarifications resolved (intake)

Grounded by `tooling/recon/RECON-0060-a-observation-surface.result.md`
(report-only, anchored to `main` as fetched 2026-08-20). Findings that shaped
this ticket:

- **Observation is the smallest surface in the workstream.** ≈ 428 lines
  (markup `index.html:612..683`, code `:2834..3189`), 18 functions, longest
  47 lines, one contiguous range. The PART-A2 interleaving cost of the
  workstream map does not apply.
- **Observation renders no graph** — open decision D-A of this ticket in the
  workstream map is answered NO. Not a graph-primitive consumer.
- **`observation_surface.py` is RED on `main`.** TICKET-0059 took Creation
  out of the legacy document; the check still asserts a three-view
  `showObservationView` contract and a `CREATION_TABS` literal in
  `index.html`. TICKET-0059's Machine section does not link it, and
  `verify/run.py` runs only the checks a ticket names, so the guard lapsed in
  silence.
- **`.r-warn` / `.r-err` are unreachable from the legacy document.** Defined
  only at `frontend/public/creation.css:137-138`; `cockpit/index.html`
  dropped that `<link>` (structurally forced by `stylesheet_partition.py`
  rule5). Observation applies them at nine sites. Every Observation error
  message currently renders uncoloured. `stylesheet_partition.py` rule7 does
  not cover this direction: its `APPLIED(F)` domain is `frontend/src` files
  only, and the legacy document is never an applying file.
- **A run can be started against the wrong world.** `WORLD_ID`
  (`index.html:697`) is written once at legacy boot (`:1832`);
  `activateWorldCascade` (`frontend/src/creation/tabs.js:703`) refreshes only
  `serverState`; `observationStartRun` posts `world_id: WORLD_ID`
  (`:2896`); `routes/observation.py:48-59` trusts the client field. After a
  Header world switch, `observation_run` rows and their mutation proposals
  land in the previously active world.

Decisions locked before any artifact was authored:

| Code | Decision |
|---|---|
| **A1** | `observation_surface.py` is repaired FIRST, against the current tree, in its own brief — before any migration. The migration brief then re-homes it onto the Svelte files. Two moves, two separate proofs. |
| **B1** | A corpus-wide gate executes every `tooling/verify/checks/*.py`, fail-closed, with an explicit environment contract so a missing dependency is a hard failure and never a skip. |
| **C3** | `stylesheet_partition.py` rule7's `APPLIED` domain is extended to `cockpit/index.html`, with `REACHABLE(legacy) = shared.css ∪ inline` only. The extension carries a retirement condition, stated in verifiable terms, and is removed once it can no longer catch anything. |
| **D1** | `.r-warn` / `.r-err` move into the Observation component's own scoped `<style>` and are deleted from `creation.css`. No global selector is added. |
| **E1** | Full Svelte templating. The four `innerHTML` string renderers become real templates. No `{@html}` — that is what makes D1 possible. |
| **F1** | The stale-world bug is fixed by the migration: Observation reads `serverState.worldId`, keeps no local latch, reloads on change. |
| **F3** | Server-side hardening (`start_run` derives the active world, stops trusting `body.world_id`) is DEFERRED to a named ticket opened after TICKET-0061 — it is a backend write and therefore an escalation under the frontend-only cross-cutting rule, never a silent edit inside this ticket. |
| **G1** | No upstream gate blocks this ticket. `live-gate` statuses on TICKET-0059/0063/0064/0065/0066 are un-rewritten checkboxes, not un-run gates. |

Brief decomposition (four briefs, sequential; each merges to `main` before the
next opens):

- **BRIEF-0060-a** — repair `observation_surface.py` on today's tree (A1).
  Tooling only, zero product code.
- **BRIEF-0060-b** — the migration: `Observation.svelte` shell-native (E1),
  world-reactive (F1), scoped styles (D1), legacy mount retired, and
  `observation_surface.py` re-homed onto the Svelte files in the same brief so
  no gate is red between commits.
- **BRIEF-0060-c** — extend rule7's `APPLIED` domain to the legacy document
  (C3), with its retirement condition.
- **BRIEF-0060-d** — the corpus gate (B1) and its environment contract.

Two items remain open and MUST be settled before BRIEF-0060-b is authored:

1. The file cut for the Svelte surface (single component vs component +
   `observation.svelte.js` state module vs a run-detail sub-component).
2. Whether the legacy document's own two-view `showPlayView` contract needs a
   check of its own once `observation_surface.py` leaves `index.html`, or
   whether that belongs to TICKET-0061.

Resolved during intake, no longer open: `Prompts.svelte`'s `legacyDoc` prop is
supplied by `frontend/src/creation/mount.js:91` as `node.ownerDocument`, and
Creation's containers live in the shell document since TICKET-0059 — so that
prop already resolves to the shell document. Post-migration Observation may
dispatch `creation:open-prompt` on its own `document` and `Prompts.svelte`
will hear it. The cross-document hop through `App.svelte:44-49,56` collapses.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `observation_surface.py` passes on the pre-migration tree with no
      product-code change, and each repaired rule is red-tested (mutate the
      asserted condition, observe FAIL, revert)  -> verify/checks/observation_surface.py
- [ ] After migration, `observation_surface.py` anchors on the Svelte
      surface, still asserts the four outcome literals with `.b-silence` and
      `.b-degraded` resolving to different class bodies, still asserts the
      pinned-parameter and template-pinning readers, still forbids a batch
      route, and its vacuous-proof guard still FAILS on zero  -> verify/checks/observation_surface.py
- [ ] `LEGACY_MOUNTS` contains exactly one entry (`play`), every `showFn`
      still resolves in the legacy document, legacy access stays confined to
      `bridge.js`, and the two shell-route lists still agree  -> verify/checks/legacy_mount.py
- [ ] The bridge export census is unchanged and within its shrinking
      baseline  -> verify/checks/legacy_call.py
- [ ] The three sheets remain disjoint, both documents still link
      `shared.css`, `creation.css` remains unlinked from the legacy document,
      built copies are byte-fresh, and rule7 reports zero stranded selectors
      for `frontend/src` applying files AND for `cockpit/index.html`  -> verify/checks/stylesheet_partition.py
- [ ] `.r-warn` and `.r-err` are absent from `creation.css` and from every
      global sheet, and Observation's error text still resolves a colour  -> verify/checks/stylesheet_partition.py
- [ ] Every new frontend module is within the 1000-line cap  -> verify/checks/module_budget.py
- [ ] No new function exceeds 80 lines outside the baseline  -> verify/checks/function_length.py
- [ ] The committed build output under `cockpit/static/` matches its sources  -> verify/checks/frontend_build_fresh.py
- [ ] No graph implementation appears in the migrated surface; the registry
      and its baseline are unchanged  -> verify/checks/graph_primitive.py
- [ ] Creation's registry, page contract and island wiring are untouched by
      the migration  -> verify/checks/page_contract.py
- [ ] The island registry is unchanged — Observation is shell-native, not a
      Creation island  -> verify/checks/creation_island.py
- [ ] No `100vh` literal is introduced and the shell height chain still
      resolves through `#app` and `.shell-layout`  -> verify/checks/shell_height_chain.py
- [ ] A corpus gate exists that discovers and executes every sibling check,
      excludes only itself, fails closed on a missing dependency rather than
      skipping, and reports every red it finds  -> verify/checks/corpus_gate.py
- [ ] The corpus gate is red-tested: a deliberately broken check is detected,
      and a check made unimportable by a removed dependency FAILS rather than
      passing  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] The Observation mode-tab renders the surface inside the shell document;
      the legacy iframe is hidden for this surface and visible only for Play.
- [ ] `/observation` loads Observation directly on a cold boot, and browser
      Back/Forward moves between Play, Creation and Observation without
      replaying a legacy boot.
- [ ] The launch panel populates the location select, shows present NPCs on
      selection, and shows the no-NPC warning **in colour** for an empty
      location.
- [ ] A start-run validation failure renders **in colour** in the launch
      status area.
- [ ] Start a run, take one beat, run a multi-beat sequence, interrupt it
      mid-sequence, and stop the run — the sequence-progress indicator and the
      abort button behave as they did before the migration.
- [ ] Inject an event mid-run; it appears in the transcript.
- [ ] The transcript distinguishes `acted` / `silence` / `degraded` / `event`
      at a glance, and `degraded` never looks like `silence`.
- [ ] The run-detail panel shows the pinned arbitration parameters and the
      per-usage template id/version; the proposals panel is read-only.
- [ ] Open a prompt from the run detail: the shell navigates to
      Creation → Prompts with that template selected, both on a cold Prompts
      tab and on a warm re-navigation.
- [ ] **Switch the active world in the Header, then start a run: the run is
      created in the NEWLY active world**, and the location select has
      reloaded for that world.
- [ ] Play is unaffected: its mode-tab, its four sub-tabs, the scene view and
      the spatial canvas all behave as before.
