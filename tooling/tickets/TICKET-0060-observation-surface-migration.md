---
id: TICKET-0060
title: Observation surface migration — last surface out of the legacy document
type: feature
status: live-gate
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

### Live  ->  human gate (Nia)

- [ ] A corpus gate (`tooling/verify/checks/corpus_gate.py`) exists that
      discovers and executes every sibling check, excludes only itself,
      fails closed on a missing dependency rather than skipping, and
      reports every red it finds. Re-homed here (QUESTION-TICKET-0060,
      Nia's response): this ticket's own `/verify` cannot assert the
      corpus is green — that is TICKET-0067's job — so this criterion is
      human-verified against the execution report's red-test transcripts
      and the diff, not a deterministic exit code.
- [ ] The corpus gate is red-tested: a deliberately broken check is
      detected; a check made unimportable by a removed dependency reports
      `ENVIRONMENT` and FAILs rather than passing or skipping; the
      coverage proof independently re-globs after the run (not reusing
      the discovery list) and catches both a newly-added always-green
      check and an artificially narrowed discovery glob, naming the
      missed file; a second self-exclusion match FAILs; the gate
      terminates with itself absent from its own executed set.

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

## Escalations

### E-01 — archived — QUESTION-TICKET-0060.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0060.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0060
Trigger: D1-d
## Context

BRIEF-0060-d (the corpus gate, B1) is implemented, red-tested (five
transcripts: broken check caught, unimportable check reports ENVIRONMENT
rather than skipping, coverage proof independently re-globs and catches
both a trivial addition and an artificially narrowed discovery, self-
exclusion asserted exactly one, no recursion), and committed in two
commits (`tooling/verify/checks/corpus_gate.py`; docs). It works exactly
as designed: it discovers all 83 sibling checks, executes every one, and
proves coverage.

Three of those 83 are genuinely red on this tree, all pre-existing and
unrelated to this ticket's Observation migration:

- `npc_goal_read.py` — `NpcGoal` imported/referenced outside its allowlist
  in `src/world_engine/observation_runner.py` and in
  `tooling/verify/checks/observation_runner.py`.
- `pipeline_state.py` — three ticket files (`TICKET-0036`, `TICKET-0048`,
  `TICKET-0062`) carry a `status:` value with a trailing inline comment
  that fails the front-matter enum parse.
- `prompt_model_write.py` — the local dev DB's `npc_dialogue`
  `prompt_template` row has zero `prompt_version` rows; the check's own
  live `TestClient` round-trip hits `prompt_store.current_prompt`'s
  fail-closed `RuntimeError`. Needs a migration/seed step against this
  tree's dev DB, not a code fix provable from the gate alone.

BRIEF-0060-d's own Scope OUT item 1 is explicit: "Do not fix anything the
gate finds... A brief that both builds a gate and repairs whatever the
gate finds has no reviewable boundary." Its Done-means explicitly
anticipated this outcome: "Every red the gate finds is listed, classified,
and left unfixed, with an explicit escalation line naming what a
follow-up ticket would need to cover" — this file is that escalation
line.

Because TICKET-0060's own Machine-checkable section links `corpus_gate.py`
(as its own acceptance criteria require), and `corpus_gate.py` is
structurally red for reasons outside this ticket's brief perimeter,
`/verify` for TICKET-0060 is red and — per V1 — stays red under a retry:
`retry_count` was set to 1 and `/verify` re-run with zero code changes
(no in-scope fix existed to attempt, per Scope OUT above); the verdict is
byte-identical on both runs modulo timestamp:

```
"corpus_gate.py": FAIL — "SUMMARY: 3 check(s) failed (0 environment, 0 timeout, 3 other)"
```

(All eleven other linked checks — observation_surface, legacy_mount,
legacy_call, stylesheet_partition, module_budget, function_length,
frontend_build_fresh, graph_primitive, page_contract, creation_island,
shell_height_chain — PASS on both runs.)

## Question

Given `corpus_gate.py` is correct and behaves exactly as specified, but
its correctness necessarily surfaces three genuine, pre-existing,
out-of-brief-scope failures that keep TICKET-0060's own `/verify` red:
how do you want this ticket to close?

## Options

A. Open a follow-up ticket (or three, one per failing check) now to fix
   `npc_goal_read.py`'s finding, the three malformed ticket-status lines,
   and the dev DB's missing `npc_dialogue` prompt_version seed. Land that
   first; TICKET-0060's `/verify` then goes green on its own and proceeds
   to PR normally, with no change to this ticket's scope.

B. Open TICKET-0060's PR now with `/verify` red, and record in the PR body
   that the single failing check (`corpus_gate.py`) is red only because it
   correctly surfaces three pre-existing, unrelated defects — pointing at
   this QUESTION file and the `ARCHITECTURE_DECISIONS.md` record as the
   evidence trail. This is a deliberate exception to PR1's "green verdict"
   norm, decided here rather than assumed.

C. Drop `corpus_gate.py`'s arrow from TICKET-0060's own Machine-checkable
   section — its acceptance criteria are about the check's own behavior
   (already proven by the five red-test transcripts), not about this
   ticket's gate being green — and let `/verify` pass on the eleven
   checks that remain linked. `corpus_gate.py` stays committed and
   correct; wiring it into a ticket's own gate is deferred until the three
   pre-existing reds are cleared by a follow-up ticket.

## Response
Stopping the chain was correct. The D1-d escalation fired exactly as
intended and nothing here is a defect in the execution: `corpus_gate.py`
is correct, the five red tests prove it, and the three findings are
real.

The answer is none of A, B or C. The fault is upstream of all three.

**What is actually wrong.** `tooling/verify/run.py` does not evaluate the
text of an acceptance criterion. A `-> verify/checks/X.py` arrow means one
thing: X must exit 0 for this ticket to verify green. TICKET-0060 carries
two arrows to `corpus_gate.py`. Their criterion text says the gate
exists, excludes only itself, fails closed on a missing dependency, and
is red-tested. But the arrow asserts something else entirely — that the
corpus is green — which was never TICKET-0060's job and which
`BRIEF-0060-d`'s own Scope OUT item 1 explicitly forbids bringing about.
So the ticket demanded, through its wiring, the exact thing its brief
prohibited. That is a ticket-authoring error, not an execution problem,
and it is why no confined retry could resolve it.

Why not B: a documented exception to a fail-closed gate is a
disciplinary safeguard, not a structural one — safeguards hold by
construction, not by a well-argued PR body. It would set the precedent
that a green verdict is negotiable in writing, exactly the erosion
`corpus_gate.py` exists to make impossible.

Why not C as written: dropping the arrow and deferring the wiring leaves
`corpus_gate.py` referenced by no ticket at all — never executed,
invisible when it breaks. That is the `observation_surface.py` lapse of
TICKET-0059, reproduced on the very tool built to prevent it. The
instinct behind C is right; the deferral is what makes it wrong.

**Do this.**

1. Correct TICKET-0060's wiring, then close it. In
   `tooling/tickets/TICKET-0060-observation-surface-migration.md`, strike
   both `corpus_gate.py` arrows from `### Machine-checkable` and move the
   two criteria verbatim into `### Live -> human gate (Nia)`. They are
   human-verified criteria: the evidence is the five red-test transcripts
   and the diff, not a deterministic exit code. `/verify` then runs the
   remaining eleven checks. They are green. TICKET-0060 closes normally
   and the frontend refactor proceeds to TICKET-0061. Nothing in
   `corpus_gate.py` changes — do not weaken it, do not add an exclusion,
   do not soften `ENVIRONMENT` to a warning.

2. Open TICKET-0067 — clear the corpus. Sole machine-checkable criterion:

   - [ ] Every check in tooling/verify/checks/ exits 0  -> verify/checks/corpus_gate.py

   That ticket cannot close until the corpus is green, so the gate is
   wired to the one ticket whose job it actually is — a re-homing, not a
   deferral. Scope: the three findings, three confined commits, one
   brief.

   - `pipeline_state.py` — three ticket files (0036, 0048, 0062) with
     trailing comments on their `status:` values. Strip the comments. Do
     not relax the parser to tolerate them: the frontmatter contract is
     the thing being asserted.
   - `npc_goal_read.py` — the `NpcGoal` reference in
     `observation_runner.py`, in both the src and checks copies. Decide
     which of two things is true and say which: the read is legitimate
     and the allowlist is incomplete, or the read is a genuine boundary
     violation. Do not add an allowlist entry to silence a violation.
   - `prompt_model_write.py` — zero `prompt_version` rows for
     `npc_dialogue`. Triage this one before designing a fix, and report
     the measurement. The question is whether the check asserts code or
     data. If it asserts a seeded database, then either the dev
     environment needs a seed step 0067 supplies, or the check is
     environment-bearing and must declare that dependency the way
     `corpus_gate.py`'s contract expects. Both are legitimate answers;
     guessing between them is not. If this one turns out larger than a
     confined commit, split it into its own ticket and let 0067 land the
     other two — but say so before starting, not partway through.

3. Make the wiring structural, in the same ticket. `pipeline_state.py`
   already validates ticket files and is already being touched. Extend it
   with one rule: every ticket's `### Machine-checkable` section must
   link `corpus_gate.py`. That converts "remember to wire the gate into
   future tickets" from a convention into a check. Without it, the corpus
   drifts again the first time someone forgets an arrow — the failure
   this ticket series has now hit three times, at three different
   levels. Vacuity guard: zero ticket files discovered is a FAIL, not a
   pass. Red-test it: a ticket file without the arrow must FAIL.

**Sequencing.** TICKET-0060 closes first, on eleven green checks.
TICKET-0067 opens immediately after and is the first ticket to carry the
`corpus_gate.py` arrow under its own new rule.

`QUESTION-TICKET-0060.md` stays in the tree as the record. It is the
escalation working, not a problem that needed avoiding.
~~~~
