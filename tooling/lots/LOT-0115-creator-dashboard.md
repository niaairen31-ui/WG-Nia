# LOT — TICKET-0115 "The creator's dashboard: every review recorded round by round, who proposed it, the metrics in code, the deferrals she watches, the « Suivi » tab and its export"

## Objective and cut

The conditions series locked a creator dashboard (H1 of TICKET-0111): a
registry of metrics in code, an « Suivi » tab in Création, the acceptance
rate of the MJ's proposals (D1) and the reactivation conditions of what was
deferred. This lot builds it, and first the data it needs:

- the creator's REVIEW is recorded (A3, C1): each review call is a round --
  approve or reject, unit or batch, the status it left, whether she edited
  the payload, every value she changed (H1a), and for a step change the
  verdict its own condition gave before the apply (M2); the producer's
  payload is kept (`original_payload`) the first time an edited one is
  approved;
- WHO PROPOSED it is one closed list (B2): `proposed_by`, held by a check;
  Journée's objective event (0119, no model) becomes `engine`;
- the METRICS are code (H1, D1, E2): a question in French, a computation
  over relational columns only (M1), the codes it watches -- no threshold;
- the DEFERRALS she watches are a registry in code (F2, K2, L): 20 entries,
  each pointing at the passage that declares it;
- the « SUIVI » tab shows both, for every world or one (J1), between two
  real-world days, and EXPORTS the same scope as one JSON document for an
  analysis in Claude Code (I1) -- the JSON signals M1 keeps off the tab.

The lot stops before: Journée proposing a quest (B-b) -- TICKET-0121; a
visible state readable about others (WH3) -- TICKET-0122; the payload made
relational (24c, reached, no ticket); a screen for the JSON signals (M2's
reactivation).

## Briefs in this lot

- **A — v2.27, the review stored** (schema v2.27,
  `BRIEF-0115-A-review-storage.md`): `models/pipeline.py`
  (`ProposedMutation.original_payload`, `MutationReview`,
  `MutationReviewChange`, five tuples), `models/__init__.py`,
  `schema_version.py`, `migrate_v2_27_mutation_reviews.py`; the world
  cascade, the JSON allowlist; check `mutation_reviews.py` (MR1-MR3).
- **B — every review path records its round** (no schema change,
  `BRIEF-0115-B-review-recording.md`): `review_diff.py`,
  `review_verdict.py`, `writes/mutation_reviews.py`,
  `cockpit/routes/mutations.py`; check `review_recording.py` (RD1-RD5).
- **C — one closed list of producers** (no schema change,
  `BRIEF-0115-C-proposal-producers.md`): `proposal_producers.py`,
  `day_events.py`, CLAUDE.md INV-14; check `proposal_producers.py`
  (PP1-PP4).
- **D — the metrics, the deferrals, the export** (no schema change,
  `BRIEF-0115-D-dashboard-registry.md`): `dashboard_metrics.py`,
  `dashboard_deferrals.py`, `dashboard_export.py`,
  `cockpit/routes/dashboard.py`, `cockpit/app.py`; check
  `dashboard_registry.py` (DB1-DB5).
- **E — the « Suivi » tab** (no schema change, `BRIEF-0115-E-suivi-tab.md`):
  `Dashboard.svelte`, `dashboard.svelte.js`, `tabs.js`, `registry.js`,
  `mount.js`, `Creation.svelte`, `creation.css`; the build; check
  `dashboard_tab.py` (DT1-DT3).

## Dependency graph

Strictly sequential, A -> B -> C -> D -> E.

- B writes A's tables (C-01) through its one writer (C-02). D reads A's
  tables and B's rounds (C-01, C-02), C's labels (C-03). E calls D's routes
  (C-04).
- C before D by decision: the metrics group by producer, and the producer
  must be true first.
- Textual chaining makes the order strict anyway: every brief appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md` above its footer.

## RECON

Opened on `main` at `947432a` (merge of PR #147, `ticket/0119`), schema
v2.26, ticket number 0115 (Nia's). `main` ran the full corpus green: 162/162
(`WORLD_ENGINE_ENV=test`). Then prototyped on a branch: each brief's commit
ran its own checks and its neighbours' green, every named mutation of every
brief turned its check red on its rule, and the five diffs were replayed on
a clean `main` (identical tree). The full corpus at the last commit: 167
checks, all green but `lore_usage.py`, which timed out at 16-17 s -- the
same on `main` in the same container, a pre-existing timing (REPORT-ONLY).
The tab was rendered in Chromium on a scratch database: metrics, deferrals,
world filter and export download all as specified. Findings tagged [M] were
measured. Line numbers are `main`'s.

### R-01 — approving overwrites the producer's payload [M]
Opened: `src/world_engine/cockpit/routes/mutations.py`
(`_approve_apply_edited_payload` :539 replaces `mut.payload` with the
body's; `approve_mutation` :631 calls it before anything else);
`frontend/src/creation/QueueCard.svelte:171` (`approveMutation` always sends
the payload; since 0119 a typed event is sent through `payloadFromDraft`,
`eventDraft.svelte.js:155`, which writes every key of its form,
`description: null` and a participant's `secret: null` included).
Consequence: A keeps the producer's payload and B diffs before against
after, an empty value equal to an absent one.

### R-02 — the four review paths and their exits [M]
Opened: `src/world_engine/cockpit/routes/mutations.py`: `reject_mutation`
:508 (one commit); `_approve_entity_creation_shortcircuit` :552 (two exits,
both `approved`); `_approve_apply_and_commit` :597 (applied, or `approved`
with `[apply error]`); `_batch_approve` :678 (same two exits, per row);
`_batch_reject` :730. `src/world_engine/cockpit/skill_progress.py:101`
calls `_approve_apply_and_commit(mut, db, now)` for the auto-applied roll
(INV-15).
Consequence: eight exits, eight `record_review` calls; `call` optional on
`_approve_apply_and_commit`, None for the roll (nobody reviewed it).

### R-03 — a step's condition and its bindings [M]
Opened: `src/world_engine/conditions.py` (`for_step` :152, `evaluate` :397,
`read_condition` :512, `and_path_leaves` :229);
`src/world_engine/day_plan.py:130` (`plan_bindings`: the doer is a
`Character`; no quest, no giver); `src/world_engine/cockpit/mutations.py:790`
(`_mutation_apply_agenda_step_change`: `complete` | `fail`, the step must be
`active`). `src/world_engine/cockpit/routes/day.py:303` (the day's NPC: the
first `relation_gte` reached through `all`, Q1).
Consequence: B judges `completion` for `complete`, `failure` for `fail`,
before the apply; a faction owner is `not_judged`. D's Q2 metric reuses
`and_path_leaves`.

### R-04 — the producers [M]
Opened: every `ProposedMutation(` of `src/world_engine` (13 sites: `tick.py`
×2 `local_ai_tick`; `analyzer_transcript.py` ×3 `local_ai_window` /
`local_ai_overhearing`; `day_mutations.py` ×3 and `day_concordance.py`
`local_ai`; `day_events.py:124` `local_ai` -- no model, Bt1 of 0119;
`play_discovery.py`, `play_stream.py` `engine`; `skill_progress.py`
`SKILL_PROGRESS_PROPOSED_BY` :46 `engine_roll`) and
`observation_runner.py:607` (`mutation.proposed_by = OBSERVED_PROPOSED_BY`,
`observation_writes.py:31`). CLAUDE.md INV-14 :194 names the engine's two.
Production (Nia, 2026-10-12): `local_ai_tick`, `local_ai`,
`local_ai_overhearing`, `local_ai_window`, `observed_scene`, `engine` -- no
legacy value seen.
Consequence: C lists seven live producers and four legacy ones; the check
resolves module constants.

### R-05 — the JSON boundary [M]
Opened: `tooling/verify/checks/json_ui_boundary.py` (`ProposedMutation.payload`
:47, « First structured UI consumer must relationalize » :46;
`ConditionDraft.payload` :119, « the rate reads the relational `outcome` and
`saved_as_proposed` »); `src/world_engine/writes/condition_drafts.py:49`
(`PAYLOAD_KEYS`: notes, errors, vocabulary live in JSON);
`src/world_engine/condition_interpreter.py:118` (`UNSUPPORTED_NOTES_FR`:
the « coût », « forme inexistante » kinds exist only in the notes' text).
Consequence (M1): the tab reads no JSON column; IA2, A2 and the missing
label are « mesurable dans l'export ». The 24c finding: the card has edited
the payload field by field since 0119 with no check noticing.

### R-06 — the interpreter's journal and the other relational sources [M]
Opened: `src/world_engine/models/pipeline.py:455` (`ConditionDraft`:
`outcome`, `saved_as_proposed`, `world_ref`, `created_at` -- no FK, outlives
its world); `models/config.py:166` (`ConditionNode`: `op`, `form`,
`parent_id`); `models/ephemeral.py:170` (`Rencontre`); `models/pipeline.py`
`SkillResolution` (`verdict` in `base`, `matched`, `unmatched`).
Consequence: D's metrics read these columns only.

### R-07 — the lists this lot extends [M]
Opened: `src/world_engine/writes/worlds.py:83` (`_DIRECT_WORLD_SCOPED_DELETES`
ends with `"event_type_effect",`); `tooling/verify/checks/world_cascade.py:201`
(the fixture's `observation_mutation_link`, after `proposed_mutation`);
`src/world_engine/schema_version.py:15` (v2.26); `world-engine-schema.md:3`
and `:1603` (`### \`event\``, after `proposed_mutation`'s notes);
`src/world_engine/cockpit/app.py:62`, `:150` (the last router);
`frontend/src/creation/tabs.js:381` (`queue:` after `subjects`),
`registry.js:578`, `mount.js:49`, `Creation.svelte:261`,
`frontend/public/creation.css:314`.

### R-08 — the deferral candidates [M]
Opened: `tooling/standards/ARCHITECTURE_DECISIONS.md` (19 671 lines; 232
paragraphs matching « deferred / named deferral / reactivat* » in 150
sections) and the tickets 0111-0119. 121 candidates were classified
chat-side; Nia kept 20 (Objective). Each anchor below was matched exactly
once in its file on `main` (whitespace folded).

### R-09 — fifteen seconds per check [M]
Prototype timings: `mutation_reviews.py` 6.9 s (three subprocess runs of
the migration), `review_recording.py` 3.6 s, `proposal_producers.py` 2.4 s,
`dashboard_registry.py` 3.6 s, `dashboard_tab.py` < 0.1 s.

## Contract sheet

### C-01 — v2.27
Produced by: BRIEF-0115-A   Consumed by: B, D
`proposed_mutation.original_payload` (JSON, nullable). `mutation_review`
(`world_id`, `mutation_id`, `round` >= 1 unique per mutation, `action` in
`REVIEW_ACTIONS = ("approve", "reject")`, `via` in `REVIEW_VIAS = ("unit",
"batch")`, `status_after` in `REVIEW_STATUSES = ("applied", "approved",
"rejected")` -- `rejected` exactly when `reject` --, `edited` only on a unit
approve, `step_verdict` NULL or in `STEP_VERDICTS = ("met", "unmet",
"unknown", "none", "not_judged")`, `reviewed_at`; indexes
`idx_mutation_review_round` (unique), `idx_mutation_review_world`).
`mutation_review_change` (`world_id`, `review_id`, `path` unique per
review, `field`, `kind` in `REVIEW_CHANGE_KINDS = ("added", "removed",
"changed")`, `before_value` NULL when added, `after_value` NULL when
removed; indexes `idx_mutation_review_change_path` (unique),
`idx_mutation_review_change_field`). Both cascade with their world.

### C-02 — recording a review
Produced by: BRIEF-0115-B   Consumed by: D
`writes.mutation_reviews.ReviewCall(action, via, before_payload,
step_verdict=None)`; `record_review(db, mutation, call) -> MutationReview`
after the status is set, before the commit; never commits.
`review_diff.diff_payloads(before, after) -> list[PayloadChange(path,
field, kind, before_value, after_value)]`, `field_of(path)`,
`IGNORED_KEYS`, `NATURAL_KEYS`, `ORDERED_LISTS`.
`review_verdict.step_verdict(db, mutation_type, payload) -> str | None`.
`_approve_apply_and_commit(mut, db, now, call=None)`.

### C-03 — producers
Produced by: BRIEF-0115-C   Consumed by: D, (0121)
`proposal_producers.PRODUCERS: dict[value, (kind, label_fr)]` -- kinds in
`PRODUCER_KINDS = ("model", "engine", "auto")`; `LEGACY_PRODUCERS`;
`producer_label(value)`, `producer_kind(value)`; `UNKNOWN_PRODUCER_FR`. A new
producer adds its entry here in the brief that writes it.

### C-04 — the dashboard's routes
Produced by: BRIEF-0115-D   Consumed by: E
`GET /api/dashboard?world=all|<id>&since=YYYY-MM-DD&until=YYYY-MM-DD` ->
`{worlds: [{id, name}], scope, metrics: [{key, title, question, watches,
dated, note, rows: [{group, label, value, of}]}], deferrals: [{code, ticket,
deferred, condition, source, metric, status, follow_up}]}`;
`GET /api/dashboard/export` (same query) -> an attachment, JSON
`{format: "wg-nia-dashboard-export/1", exported_at, scope, proposals,
interpreter, metrics, deferrals}`. 422 on a bad date, `since` after
`until`, an unknown world. `dashboard_metrics.Scope(world_ids, since,
until)` (naive UTC, `until` excluded), `METRICS`, `compute_metrics`;
`dashboard_deferrals.DEFERRALS`, `EXPORT`, `DEFERRAL_STATUSES`,
`deferral_dicts()`; `dashboard_export.build_export(db, scope)`.

## Gate output

(a) Property trace -- one line per property the briefs assert about `main`:
- approving replaces the payload before anything is applied -> R-01,
  `routes/mutations.py:539`, `:631`.
- the card sends every key of its form -> R-01, `eventDraft.svelte.js:155`.
- eight review exits; the roll calls `_approve_apply_and_commit` -> R-02.
- `plan_bindings` binds a `Character` doer; the applier needs an active
  step -> R-03, `day_plan.py:130`, `cockpit/mutations.py:790`.
- thirteen constructors, one reassignment, Journée's event `local_ai` ->
  R-04.
- the payload and the drafts' payload are allowlisted as never rendered ->
  R-05, `json_ui_boundary.py:46-47`, `:119`.
- the cascade's last direct table, the fixture's position -> R-07.

(b) Case tables.

A review call (C-01, C-02, RD2-RD4):

| path | action | via | status_after | edited | changes |
|---|---|---|---|---|---|
| approve, applied | approve | unit | applied | diff not empty | the diff |
| approve, apply error | approve | unit | approved | diff not empty | the diff |
| approve, entity_creation parked or colliding | approve | unit | approved | diff not empty | the diff |
| reject | reject | unit | rejected | false | none |
| batch approve, applied / error | approve | batch | applied / approved | false | none |
| batch reject | reject | batch | rejected | false | none |
| the roll (INV-15) | -- | -- | -- | -- | no row |

A step's verdict (C-02, RD4):

| proposal | verdict |
|---|---|
| not `agenda_step_change` | NULL |
| `complete`, completion met / unmet / unknown | met / unmet / unknown |
| `fail`, failure met / unmet / unknown | met / unmet / unknown |
| no such condition | none |
| no step id, unknown step, other action, faction owner, unreadable tree | not_judged |

A diff (C-02, RD1):

| list | paired by |
|---|---|
| `participants` | role name (else role id) |
| `state_changes` | entity, state |
| `scopes` | kind, target |
| `roles` | name |
| `effects` | type |
| `steps` | position |
| plain values (`involved_entities`, `entity_types`) | as a set |
| any other list of objects | position |

The deferral registry (C-04, DB1) -- Nia's 20:

| code | ticket | metric | status |
|---|---|---|---|
| D2 | 0111 | event_reviews | open |
| M2 | 0111 | step_verdicts | open |
| A1 | 0119 | tick_retyped | open |
| Q2 | 0111 | steps_without_day_npc | open |
| absence | 0114 | absence_leaves | open |
| A2 | 0111 | export | open |
| F2 | 0111 | -- | open |
| IA2 | 0112 | export | open |
| ID1b | 0112 | -- | open |
| libellé | 0113 | export | open |
| effets/sorte | 0119 | -- | open |
| WH3 | 0113 | -- | reached, TICKET-0122 |
| payload | 0025 | -- | reached |
| A1'b | 0104 | rencontre_pairs | open |
| P2 | 0101 | -- | open |
| C3b | 0084 | lexicon_gaps | open |
| A2 (îlots) | 0088 | -- | open |
| A3 (îlots) | 0088 | -- | open |
| D-0088-rule6-alias | 0088 | -- | open |
| D-0088-rule11-unrouted | 0088 | -- | open |

(c) Enumerations: every `ProposedMutation(` of the package (R-04, 13) and
every `.proposed_by =` (1) -- PP1 recounts them at each run.

(d) Every family contract (C-01's tuples, C-02's exits, C-03's kinds, C-04's
metrics) was written before its members and re-read after the last: tick.

(e) Gates proposed and the module satisfying each: `mutation_reviews.py` ->
`models/pipeline.py`, `migrate_v2_27_mutation_reviews.py`,
`schema_version.py`; `review_recording.py` -> `review_diff.py`,
`review_verdict.py`, `writes/mutation_reviews.py`, `routes/mutations.py`;
`proposal_producers.py` -> `proposal_producers.py`, `day_events.py`;
`dashboard_registry.py` -> `dashboard_metrics.py`, `dashboard_deferrals.py`,
`dashboard_export.py`, `routes/dashboard.py`; `dashboard_tab.py` -> the
tab's files. Gates merely passed, retargeted in the brief that moves their
subject: `world_cascade.py` (A), `json_ui_boundary.py` (A); held by an
invariant whose marker changes: INV-14 (C, `[no check]` -> enforced by
`proposal_producers.py`).

## Docs to update (chat-side, Nia's project)

- `SERIE-conditions.md`: 0115 done (with this lot), the registry's 20
  entries, M1, 0122 reserved.
- The brief-generation protocol: a deferral Nia names with an approved
  condition is added to `dashboard_deferrals.DEFERRALS` by the brief that
  writes its decision entry (L).

## Amendments

(none)
