---
id: TICKET-0059
title: Creation periphery migration and legacy mount retirement
type: feature
status: exec   # briefs a-d merged to main via PR #79; e-g executed this PR; -h onward pending
created: 2026-08-03
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: large
brief_ids: [BRIEF-0059-a, BRIEF-0059-b, BRIEF-0059-c, BRIEF-0059-d, BRIEF-0059-e, BRIEF-0059-f, BRIEF-0059-g]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Nous travaillons sur le refactor de l'index. Cinquieme ticket de la serie
(ticket 0059). Les 4 tickets precedents sont merges sur main."

Per the workstream map (`Active project.md`, PART B), TICKET-0059 is
"Creation surface: remaining authoring tabs", and
`frontend/src/legacy/registry.js:11` declares
`creation: { retiredBy: 'TICKET-0059' }`.

## Clarifications resolved (intake)

**A1 - one ticket, one brief chain, the legacy `creation` mount retires here.**

Measured on `main` this session: the Creation residue is ~3980 lines across
~208 top-level functions, plus ~465 lines of Creation chrome. That is
comparable to TICKET-0058's spine (~5000 lines, 12 briefs), not larger.

Rejected: splitting the mount retirement into a later TICKET-0062. It would
require amending `tooling/verify/baselines/legacy_mounts.baseline` and
`frontend/src/legacy/registry.js` to move a committed `retiredBy` forward -
defeating a fail-closed structural declaration for scheduling convenience.
The registry is the authority; the ticket obeys it.

Rejected: promoting `prompts` (31 fns, ~559 lines) out of Creation into its
own top-level surface to shrink this ticket. It is a plausible doctrine
change - `prompts` is creator tooling, not world authoring - but it is an
unsettled design question, and this ticket may not carry one. Recorded as a
named deferral instead (D-0059-prompts-surface).

**B1 - the `legacyCall` anomaly closes before any new surface migrates.**

TICKET-0058 left a measurable seam: 20 call sites in 5 frontend files where a
Svelte component reaches back into the legacy window for HTML strings or
lifecycle helpers. `Sheet.svelte` holds 15 of the 20 - it is a half-migrated
island, a converged component whose Relations / Knowledge / Goals /
Discipline-details sections are still legacy-rendered strings carrying inline
`on*` handlers bound to legacy globals.

This is the only place in the tree where the dependency runs Svelte -> legacy
rather than legacy -> Svelte. It is the structural anomaly, and it is the
largest single residual cluster (42 `author*` functions, ~830 lines). It goes
first.

Rejected: migrating the standalone tabs first to de-risk the chain. Lower
risk per brief, but it leaves the inverted dependency alive across ten briefs
and blocks re-homing `page_contract.py`.

**C1 - the two AI agent surfaces converge on a shared location-tree picker.**

`_npcAgentTreeHtml` (`index.html:~7700`) and `_linkAgentTreeHtml`
(`index.html:~8180`) are near-identical recursive location pickers;
`_npcAgentTreeHtml` emits the CSS class `linkagent-loc-node`, which is
copy-paste evidence, not convergence. One `LocationTree.svelte` is extracted
before either agent migrates, and both consume it. Confirmed or corrected by
BRIEF-0059-a M4.

Rejected: porting each agent with its own tree. That reproduces in Svelte the
accidental divergence this whole workstream exists to end - the same failure
the graph primitive (TICKET-0057) was built to make unconstructible.

**D1 - the tab registry lands at `frontend/src/creation/tabs.js`.**

After the chrome inverts, `CREATION_TABS` becomes a Svelte-side module fed by
the same `authorRegistry` fetch that `_buildRuntimeCreationTabs`
(`index.html:5940`) reads today. The TICKET-0046 dynamic runtime-type tab
factory stays a factory: runtime types still inject tabs at boot, never a
frozen literal list. `page_contract.py` re-anchors onto `tabs.js` plus the
new `Creation.svelte`.

Rejected: a server-provided tab list. It is a backend change, and this
workstream is frontend-only (cross-cutting rule 2).

**E1 - a shrinking, fail-closed `legacy_call.py` baseline gates the whole
ticket.**

Modeled on `legacy_mount.py`: `tooling/verify/baselines/legacy_calls.baseline`
enumerates the permitted `legacyCall` sites. The set may only shrink. It must
reach zero before the `creation` entry may leave `LEGACY_MOUNTS`. Vacuous-proof:
a scan collecting zero frontend files is a failure, not a pass.

Rejected: a flat ban on `legacyCall` landed at the end of the ticket. It
protects nothing during the ten briefs of transition, which is exactly when
a new call site would be added.

**Ordering consequence.** The Creation chrome cannot invert until every
Creation pane is Svelte. A shell-owned tab bar driving legacy panes across
the iframe boundary would put chrome and panes on opposite sides - two
authorities over one surface, strictly worse than today, and the arrangement
TICKET-0058 explicitly rejected. The chrome is therefore the last migration
brief, not an early one.

## Brief chain

Report-only plan. Each brief carries its own mini-RECON with a hard
stop-and-escalate rule; brief `-a` may re-cut anything below.

| Brief | Step | Approx. residue closed |
|---|---|---|
| `-a` | periphery closure mini-RECON (report only) | - |
| `-b` | `legacy_call.py` check + baseline seeded at 20 | seal only |
| `-c` | Sheet sub-editors: relations + knowledge | ~230 ln |
| `-d` | Sheet sub-editors: goals + discipline details | ~400 ln |
| `-e` | residual `legacyCall` sites outside Sheet; baseline -> 0 | ~200 ln |
| `-f` | `LocationTree.svelte` extraction + npcAgent island | ~460 ln |
| `-g` | linkAgent island | ~420 ln |
| `-h` | `competences` + `registre` + `artefacts` tabs | ~250 ln |
| `-i` | `prompts` tab | ~560 ln |
| `-j` | `intrigues` bespoke sheet + `pj`/`pc`/`skill` slot | ~630 ln |
| `-k` | Review Queue + mutation review + world CRUD | ~380 ln |
| `-l` | chrome inversion, mount retirement, check re-homing | ~465 ln |
| `-m` | doctrine seal + docs | - |

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `legacy_call.py` exists, is fail-closed and vacuous-proof, and its
      baseline shrinks monotonically across the chain  ->  verify/checks/legacy_call.py
- [ ] `legacy_calls.baseline` is empty at ticket close, and `legacy_call.py`
      refuses any `legacyCall(` occurrence under `frontend/src/creation/`  ->  verify/checks/legacy_call.py
- [ ] `LEGACY_MOUNTS` no longer contains `creation`; `legacy_mounts.baseline`
      shrinks to `observation` + `play`  ->  verify/checks/legacy_mount.py
- [ ] Zero `function <prefix>...(` declarations remain in `index.html` for
      every prefix retired by this ticket's island entries  ->
      verify/checks/creation_island.py
- [ ] `page_contract.py` asserts the tab contract against
      `frontend/src/creation/tabs.js` and `Creation.svelte`, not
      `index.html`, and still forbids a static `#ctab-` outside the frozen
      `TAB_KEYS`  ->  verify/checks/page_contract.py
- [ ] `creation_return_nav.py`, `faction_roster_panel.py`,
      `review_component.py` re-anchored off `index.html`, each in the same
      commit as the surface it guards  ->  respective checks
- [ ] Exactly one recursive location-tree renderer exists under
      `frontend/src/`  ->  verify/checks/location_tree.py
- [ ] `SHELL_ROUTES` in `router.js` and `_SHELL_ROUTES` in `app.py` still
      agree  ->  verify/checks/legacy_mount.py
- [ ] `npm run build` output is fresh  ->  verify/checks/frontend_build_fresh.py
- [ ] No backend file under `src/world_engine/` outside `cockpit/app.py`
      route registration is modified by this ticket  ->  reviewed at `-m`

### Live  ->  human gate (Nia)

- [ ] Every Creation sub-tab opens, renders and saves: npc, pj, lieux,
      factions, objets, competences, region, constructeur, artefacts,
      registre, intrigues, evenements, queue, prompts - plus at least one
      runtime entity type created via Constructeur.
- [ ] Deep-link `/creation/<sub_tab>` cold-loads onto the right tab for
      every tab above; browser Back leaves Creation rather than walking
      sub-tabs.
- [ ] Relations, knowledge, goals and discipline-details editors on an NPC
      sheet each add, edit and delete a row, with the status line reporting
      correctly.
- [ ] NPC agent and link agent each launch, pause, retry and commit a batch;
      both location pickers behave identically.
- [ ] A world switch resets every tab's state with no stale rows from the
      previous world.
- [ ] The relation graph and the lieux graph both still open from their
      tabs.
- [ ] Review Queue still applies and rejects a proposed mutation.
- [ ] World create and world delete still work from the shell header.
