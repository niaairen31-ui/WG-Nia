# world-engine-schema — CHANGELOG

Append-only history of `world-engine-schema.md`, extracted verbatim
(BRIEF-0001-a, no schema change). Newest entry first. The current
version number lives ONLY in `world-engine-schema.md`
(`Current schema version:` line); this file is the log, never the
source of "what version are we at".

## CHANGELOG

- **v1.72** — Two new tables, `agenda` and `agenda_step` (TICKET-0018,
  BRIEF-0018-a): structured faction intrigues the world tick advances and
  proposes. `agenda`: `id, world_id, owner_entity_id (FK entity.id, A2-ready
  — location/NPC owners deferred), title, status
  (active|completed|failed|abandoned), created_at, updated_at, change_history
  (JSON)` + index `idx_agenda_owner_status (owner_entity_id, status)`.
  `agenda_step`: `id, agenda_id (FK agenda.id), step_order, objective, status
  (pending|active|completed|failed), outcome, visibility_trace, created_at,
  updated_at, change_history (JSON)` + index `idx_agenda_step_agenda
  (agenda_id, step_order)` + a STRUCTURAL partial unique index
  `idx_agenda_step_one_active (agenda_id) WHERE status = 'active'` — at most
  one active step per agenda, enforced by SQLite (the
  `idx_membership_one_primary` precedent), never by discipline. The model
  never addresses a step or agenda by id: it names the agenda by TITLE
  (resolved against a per-call `agendas_index`, FACTION SCOPE ONLY — a
  location scope's index is always empty, A1 doctrine); the active step is
  derived in code. `write_agenda`/`write_agenda_step`/
  `write_agenda_step_status`/`write_agenda_status` (`writes.py`) are the
  ONLY constructors of either table, shared by `_apply_mutation`'s two new
  branches (`agenda_step_change`, `agenda_creation`) and the first dedicated
  non-entity creator-CRUD surface (`GET/POST /api/agendas`,
  `PATCH /api/agendas/{id}`, `PATCH /api/agenda-steps/{id}` — an "Intrigues"
  cockpit panel). Advancement is CODE at apply: `complete` activates the
  next pending step by `step_order`, or completes the agenda when none
  remain; `fail` fails the WHOLE agenda (no per-step branching; creator can
  reactivate via PATCH). `agenda_creation` writes one agenda + its ordered
  steps in a single SAVEPOINT (step 1 born active — the approval/authoring
  act IS the activation); duplicate-guarded by canon-existence (an ACTIVE
  agenda for the same owner + normalized title); `agenda_step_change` needs
  no such guard — its apply-side active-status stale check is strictly
  stronger. The faction-scoped tick briefing gains an `AGENDA EN COURS`
  section (title, active step's objective + visibility_trace, last 2
  completed outcomes). Prompt `pt-world-tick-events` gains an appended
  version enumerating the two agenda types as FACTION-SCOPE ONLY. Delivered
  via `scripts/migrate_v1_72_agenda.py` (new-tables shape) and
  `scripts/apply_ticket_0018_prompt_updates.py` (append-version). Verify
  gains rules 12-14 in `tooling/verify/checks/world_tick.py` (agenda types
  isolated to the scope normalizer; step/agenda/owner ids forced, never
  read from a payload; the partial unique index is structurally present)
  and new `canon_write_policy.txt` entries for the four write helpers plus
  the creator-CRUD `update_agenda_step` route.

- **v1.71** — New table `visit` (append-only, BRIEF-0016-a): `id, world_id,
  player_id, location_id, entered_at, present_npc_ids (JSON)` + composite
  index `idx_visit_player_location (player_id, location_id, entered_at)`.
  Anchors the player's last entry per location. `enter_scene`
  (`cockpit/app.py`) writes a row ONLY inside its existing genuine-transition
  guard (`if not open_g:`); a code-computed diff against the previous row
  (`_compute_return_delta`) — NPCs arrived/departed by set-diff of public
  presence, plus public events since — rides into the existing
  `mj_establishment` entry narration as a new `{changes}` block. Departed
  NPC names resolve from `Entity` without the alive/active filter (their
  absence is public information the player already witnessed); the event
  leg applies the SAME `knowledge_status IN ('public','confirmed')`
  structural filter as the only other Event reader (`context.py`) and is a
  forward-reader (empty until an event producer ships). First visit, or a
  visit with nothing to report, sends no `{changes}` block — the model
  never sees an empty header to embroider on. No backfill: the table is
  born empty, every location counts as a first visit once. Prompt
  `pt-mj-establishment` gains an appended version: the "no NPC named" rule
  is scoped so only NPCs cited in the CHANGEMENTS block may be named.
  Delivered via `scripts/migrate_v1_71_visit.py` (new-table shape) and
  `scripts/apply_ticket_0016_prompt_updates.py` (append-version). New
  verify check `tooling/verify/checks/visit_delta.py`: `visit` is
  append-only and constructed only from `cockpit/app.py`; the delta's Event
  query textually references `knowledge_status`.

- **BRIEF-0017-a** — No schema change. `event` gains its first two
  producers (the table existed since the founding schema, unused). A
  scope-level `world_tick` call (location/faction-scoped invocations only;
  `"npcs"`-scoped never produces one) proposes `event_creation` mutations,
  quota-bounded (`SCOPE_EVENT_QUOTA = 3`, `tick.py`) via a new prompt head
  `pt-world-tick-events` (`usage='world_tick_events'`, world_id NULL).
  `_apply_mutation` (`cockpit/app.py`) implements the `event_creation`
  branch — awakening the analyzer's dormant conversation-sourced channel
  (`analyzer.py:324-330`) at the same time, since both payload generations
  (the tick's closed shape and the analyzer's minimal shape) route through
  the same new `write_event` helper (`writes.py`, the sole `Event(`
  construction site). The model may propose `knowledge_status`
  secret|public only; `confirmed` is creator-reserved, accepted only at
  apply time. Duplicate guard (`_find_applied_duplicate`) is
  canon-existence — same normalized title + `location_id`, same world —
  extended to the conversation-sourced branch too (not just the tick
  branch), so a `--force` re-analysis can't double an event either. Faction
  briefings extend the full-interiority tick exception (raw
  `FactionMembership`, never `read_public_memberships`) to this surface,
  re-logged. Delivered via `scripts/apply_ticket_0017_prompt_updates.py`
  (HEAD-ABSENT branch, the 0014 shape). New verify rules in
  `tooling/verify/checks/world_tick.py` (9-11): `event_creation` never
  enters the per-NPC closed contract; `SCOPE_EVENT_QUOTA` exists and is
  referenced by the emit loop; `location_id` joins the forced-attribution
  field set.

- **BRIEF-0015-a** — No schema change. `npc_move` added to
  `proposed_mutation.mutation_type` (targets `character`, tick-only
  producer; `proposed_mutation.mutation_type` is unconstrained TEXT and
  `tick_id` already exists since v1.70 — no migration). Lifts TICKET-0014's
  L3 movement deferral: a ticked NPC may relocate along the `connects_to`
  graph, radius scaled STRUCTURALLY by the invocation's interval label
  (`INTERVAL_HOP_RADIUS`, `tick.py` — 1 hop for "quelques heures", 3 for
  "quelques jours", the origin's connected component for "quelques
  semaines"). New briefing section `OÙ TU PEUX ALLER`
  (`assemble_tick_context`) lists the reachable candidate set; destination
  resolution reads ONLY that same set (`_normalize_tick_item`), never all
  locations. `analyzer._MUTATION_TYPE_MAP` stays byte-identical — a
  tick-local alias map (`_TICK_TYPE_ALIASES`) carries the extra vocabulary
  so conversation analysis and overhearing can never propose movement.
  `npc_id`/`from_location_id` are forced code-side at emit (rule-3
  pattern); `to_location_id` is resolved against the candidate set.
  Apply side (`_apply_mutation`, `cockpit/app.py`): a stale-from gate
  (`character.current_location_id != payload.from_location_id`) covers
  duplicate re-approval, cross-run tick duplicates, and a manual move since
  the proposal in one canon check, while still allowing a later legitimate
  A->B->A move; the write routes through the new `write_character_location`
  helper (`writes.py`, no `change_history` — `character` has none, the
  mutation row is the audit trail) and `close_open_memberships` closes the
  NPC's open gathering regardless of player co-presence (Nia's locked
  decision). `_find_applied_duplicate`'s tick branch gains a mirror
  `npc_move` clause. Prompt updates delivered via
  `scripts/apply_ticket_0015_prompt_updates.py` (append-version, the
  `pt-world-tick` head already exists since 0014).

- **v1.70** — `proposed_mutation.tick_id` (TEXT, nullable) + index
  `idx_mutation_tick` (TICKET-0014/BRIEF-0014-b). Third `source_type` value
  `world_tick`: both `pass_play_id` and `conversation_id` stay NULL for it —
  `tick_id` is that source's anchor, one UUID per `run_world_tick`
  invocation, shared by every row it writes. New `proposed_by` value
  `local_ai_tick`. Purely additive: `scripts/migrate_v1_70_tick_id.py`
  (idempotent, no backfill — existing rows are born NULL). Read by the
  duplicate-application guard's new tick branch (`_find_applied_duplicate`,
  `cockpit/app.py`) and the review-queue `TICK ·xxxx` badge
  (`_mutation_dict`, `renderCard`).

- **BRIEF-0013-c** — No schema change. `goal_change` added to
  `proposed_mutation.mutation_type` (targets `npc_goal`) — closes the
  TICKET-0013 behaviour loop. Emit side (`analyzer.py`): the model already
  sees the NPC's active goals verbatim via the `TES OBJECTIFS` section
  carried in `injected_context.assembled_context`; `_normalize_to_schema`
  forces `payload.npc_id` to `conv.npc_id` in code (never model-chosen) and
  coerces `action` (`complete`|`abandon`|`create_short`) through a small
  alias map. Apply side (`_apply_mutation`, `cockpit/app.py`): `complete`/
  `abandon` match an ACTIVE goal (either horizon) by exact normalized
  description text via `write_npc_goal_status`; `create_short` always
  inserts a SHORT goal via `write_npc_goal` — horizon is hard-coded, O1
  structural, no payload field can override it. `_find_applied_duplicate`
  gains a `goal_change` branch (same conversation + action + normalized
  goal text) — the opposite asymmetry from `knowledge_change`, which stays
  excluded. Initiative vote (R1, `cockpit/app.py`): `_signal_line` appends
  `, objectif=« … »` (80-char truncation) from each candidate's most
  recent ACTIVE short-term goal — long-term goals never enter the vote.
  Prompt updates delivered via a new one-shot script,
  `scripts/apply_ticket_0013_prompt_updates.py` (mirrors
  `apply_ticket_0012_prompt_rewrite.py`): `pt-npc-dialogue` gains an
  OBJECTIFS directive; `pt-conversation-analysis` gains the GOAL_CHANGE
  rubric + a fifth worked example. `verify/checks/prompt_lean.py` updated
  (5 EXEMPLE markers, 4 rubric headers). TICKET-0013 is now complete;
  TICKET-0014 (world-tick) is the named successor.

- **v1.69** — New table `npc_goal` (NPC interiority — in-scene volition,
  TICKET-0013/BRIEF-0013-a): `id`, `world_id` (FK), `npc_id` (FK entity),
  `description` (NOT NULL, immutable after insert), `horizon` CHECK IN
  ('short','long'), `status` CHECK IN ('active','completed','abandoned')
  DEFAULT 'active', `created_at`, `updated_at`, `change_history` JSON
  DEFAULT '[]'; index `idx_npc_goal_npc_status` on `(npc_id, status)`. A
  changed goal is a closed goal plus a new row — status transitions are
  one-way (`active` -> `completed`|`abandoned`), never reopened. Two new
  `writes.py` helpers are the sole write chokepoints: `write_npc_goal`
  (insert, active) and `write_npc_goal_status` (history-append then
  transition; raises on any transition other than the two allowed ones).
  New creator CRUD: `GET/POST /api/entities/{id}/goals`,
  `POST /api/goals/{id}/status` — NPC characters only (422 on a player
  character or an invalid transition). Character-sheet "Objectifs" block
  (NPC sheets only). New `assemble_npc_context` section `TES OBJECTIFS`
  (`H_GOALS`), placed right after `QUI TU ES`: the most recent active long
  goal + the 2 most recent active shorts (read-side LIMIT, no write-side
  cap), omitted entirely when the NPC has no active goals. N1 structural
  boundary: `assemble_mj_context` never reads `npc_goal` — enforced by a new
  static check, `verify/checks/npc_goal_read.py` (module allowlist + a scan
  asserting zero `NpcGoal`/`"npc_goal"` references inside the MJ block).
  `canon_write_policy.txt` gains `npc_goal` as a canon table with the two new
  helper sites. Migration: `scripts/migrate_v1_69_npc_goal.py` (purely
  additive). Scope OUT this step: the goal generator, the vote signal, the
  `goal_change` mutation type, and the dialogue directive — all BRIEF-0013-b/c.

- **v1.68** — New table `prompt_version` (append-only prompt text history,
  TICKET-0011/BRIEF-0011-a): `id`, `prompt_template_id` (FK), `version_number`,
  `system_prompt`, `user_template`, `note`, `created_at`; UNIQUE index on
  `(prompt_template_id, version_number)`. "Current" = `MAX(version_number)`
  per head — no pointer column. `prompt_template` drops `system_prompt`,
  `user_template`, `version` (F1) — those columns' text was backfilled into a
  `prompt_version` v1 row per head first
  (`scripts/migrate_v1_68_prompt_version.py`). New sole read accessor
  (`prompt_store.current_prompt`/`get_version`/`list_versions`) and sole
  write shape (`writes.write_prompt_version`, C1 fail-closed placeholder
  validation), wired at every prompt-text consumer. New API:
  `PATCH /api/prompts/{id}/text`, `GET /api/prompts/{id}/versions[/{n}]`,
  `POST /api/prompts/{id}/versions/{n}/restore`. Seed (`upsert_prompt_template`)
  writes v1 only on a virgin head — never touches text again once a version
  exists (S2). The 6 `.format()` call sites (`region_author.py`,
  `entity_author.py`) normalized to the same chained `.replace()` mechanic as
  every other call site (H1) — one substitution mechanism repo-wide. New
  verify check: `verify/checks/prompt_version.py`.

- **BRIEF-0009-a** — No schema change. Write path for the `prompt_template.
  model` column that shipped at v1.67 (BRIEF-0008-a): `PATCH
  /api/prompts/{prompt_id}/model` (fail-closed validation against the live
  Ollama tag list) and `GET /api/ollama/models`. Seeded rows stay `model =
  NULL` (S-null).

- **v1.67** — Additive column: `prompt_template.model TEXT NULL` (BRIEF-0008-a).
  NULL = code decides (the existing per-usage default); non-NULL = creator
  override, consumed by the new `prompt_registry.effective_model(template,
  default)` resolver, now wired at every templated `chat`/`chat_stream` call
  site (`entity_author.py`, `region_author.py`, `analyzer.py`, `gathering.py`,
  `cockpit/app.py`'s conversation-start/join model bindings and the
  establishment-narration call), with one named exemption: the `/say` turn's
  `model = injected.get("model", DEFAULT_MODEL)` call path (`app.py`'s `say`/
  `_stream` and the pass-through helpers they call) — wiring it would encode
  a `template.model` vs `injected_context["model"]` precedence, deferred to
  the write-path chantier. Fixed the stale `usage` enum comment (8 values
  were missing, including `region_manifest_topup`). No write path for `model`
  exists yet; the column is born NULL everywhere and runtime model selection
  is bit-identical to pre-v1.67 behavior. New verify check:
  `verify/checks/prompt_registry.py`.

- **v1.66** — No new tables or columns. Application-layer: Personnage joueur
  create form + BRIEF-52 generate panel gated behind a dedicated `pjCreateOpen`
  toggle and a PJ-specific `+ Nouveau` button (`#pj-create-block`), matching
  the NPC inline collapse-by-default pattern; the skill Fiche (`#skill-main`)
  stays rendered by default. NPC author path and `#creation-new-row` hide-list
  untouched (BRIEF-60).

- **v1.65** — No new tables or columns. Data migration
  (`migrate_v1_65_pc_skill_backfill.py`): backfills the four base `skill`
  rows (`tier=0`, `change_history='[]'`, `skill_definition_id=NULL`) for
  every `character_type='player'` entity missing any of them; covers all
  worlds; idempotent; retrofits PCs predating the create-route seed
  (BRIEF-46) — e.g. `char-player` / Joran Vey. No NPC rows, no
  custom-skill rows, no existing row mutated.

- **v1.64** — No new tables or columns. World-scoped custom skill catalogue
  — authoring + creator CRUD (BRIEF-56), chantier 2 of BRIEF-55. Locked
  decisions: D2-attach-b (standalone author call, not folded into the
  world-bible call), D2-template-b (dedicated `pt-skill-catalogue`
  template, `usage='skill_catalogue'`, `world_id=NULL`), D2-delete-cascade
  (delete is always possible — never `ON DELETE RESTRICT`-blocked — but
  carries no separate `change_history` snapshot of the deletion event; the
  creator-side type-"Oui" confirmation modal is the sole safeguard, same
  idiom as world block deletion), D2-backfill-yes (a new definition
  backfills a tier-0 `skill` row onto every existing player character of
  the world, in the same transaction as the create — keeps the
  catalogue<->PC alignment that the arbiter lookup depends on total).
  `entity_author.generate_skill_catalogue_draft` (standalone sibling to
  `generate_world_draft`/`generate_player_draft`, NOT a `_TYPE_FIELDS`
  entry) proposes `{name, base_domain, description}` rows only — never a
  tier, never a structural id; `_normalize_skill_catalogue` drops nameless
  rows and rows whose `base_domain` doesn't resolve against
  `BASE_SKILL_DOMAINS` (case-insensitive match, no fifth domain invented).
  `POST /api/skill-definitions/generate` (`cockpit/app.py`) delegates only
  to that function, writes nothing. Creator-CRUD dedicated router
  (`cockpit/crud.py`, the `skill`/`discoverable_detail`/`ledger` shape, NOT
  the generic composite entity editor — `skill_definition` has no
  `entity_id`): `GET/POST/PUT/DELETE /api/skill-definitions`, all
  world-scoped via `_world_id(db)`; `POST` validates `base_domain ∈
  BASE_SKILL_DOMAINS` and `UNIQUE(world_id, name)` (409 on conflict) and
  performs the backfill insert in the same transaction; `PUT` re-validates
  the same way and, when `base_domain` changes, also updates the `domain`
  column on every dependent `skill` row so 2d6 bands/CHECK/display stay
  consistent; `DELETE` removes every dependent `skill` row then the
  definition in one transaction. New "Compétences" Création sub-tab
  (`index.html`): AI-generate panel pre-fills an editable draft list
  (accept/edit/discard per row, manual add), plus the existing-definitions
  list (inline rename/re-base/re-word, delete with the type-"Oui" modal).
  Closes the chantier-2 deferral noted in BRIEF-55/v1.63's CHANGELOG entry
  (creator CRUD surface, AI authoring, delete/rename UX, `description`
  reader still N/A for in-play readers — Scope OUT unchanged: no NPC-side
  custom skills, no per-PC subset, no `description` injection into any
  prompt).
- **v1.63** — World-scoped custom skill catalogue, table + both readers
  (BRIEF-55). New table `skill_definition` (world-scoped; `name` + one
  specialised `base_domain`, CHECK against the four base domains;
  `UNIQUE(world_id, name)` — a name is a stable per-world identifier).
  `skill.skill_definition_id` (nullable FK, `ON DELETE RESTRICT`) added:
  NULL for the four base-domain rows, set for a custom-skill row; the
  display name is read by join, never copied — rename-safe by construction.
  Decision 3: the three independently-declared four-literal domain tuples
  (`cockpit/app.py` `_PHYSICAL_DOMAINS`, `cockpit/crud.py` and
  `seed_pilot.py` `SKILL_DOMAINS`) are consolidated into one constant,
  `BASE_SKILL_DOMAINS` (`models.py`), all three now importing it. B1 seed:
  `create_player_character` (`cockpit/app.py`) and the pilot PC seed
  (`seed_pilot.py`) both seed one `skill` row per `skill_definition` of the
  PC's world, flat at `tier=0`, right after the four base-domain rows — the
  model never proposes a tier. Reader A (mechanical, structural/
  deterministic): the arbiter's candidate set is now `BASE_SKILL_DOMAINS`
  plus the active world's `skill_definition.name` values, injected into
  `pt-mj-arbiter` (bumped to v3) via a `{custom_skill_names}` placeholder
  (`"(aucune)"` when the world has none — byte-identical arbiter behavior in
  that case); the domain clamp is widened to match. A returned custom name
  resolves via its `skill_definition.base_domain`: the PC's `skill` row is
  looked up by `skill_definition_id` (not `domain`), its `tier` feeds
  `resolve_physical` keyed on the resolved `base_domain` — the same
  `base_domain` also gates the perception-discovery check, so a
  perception-specialised custom skill still triggers discovery. The
  base-domain lookup path gained `AND skill_definition_id IS NULL` so it
  deterministically excludes custom rows. Reader B (ambiance, probabilistic
  nudge): `assemble_mj_context`/`format_mj_context` (`context.py`) gained a
  `COMPÉTENCES PROPRES À CE MONDE` section listing the active world's custom
  skill names only (no description, no tier, no per-PC data), world-scoped
  at query construction, omitted entirely when the world has none. MJ
  narration only — NPC dialogue is untouched. Pilot fixture: two
  `skill_definition` rows (`Diplomatie`/composure, `Pistage`/perception),
  seeded onto the PC_TEST_2 skill-sheet test character. Scope-OUT (chantier
  2, not built here): no creator CRUD surface, no AI authoring, no delete/
  rename UX beyond the `ON DELETE RESTRICT` floor, no `description` reader,
  no NPC-side custom skills, no per-PC subset (B2). `delete_world_cascade`
  (`writes.py`) gained `skill_definition` in its direct world_id-scoped
  delete list (after the existing subquery-based `skill` delete) so a world
  block deletion still removes every row scoped to it.
- **v1.62** — No new tables or columns. World block deletion (BRIEF-54):
  `DELETE /api/worlds/{world_id}` (`app.py`) hard-deletes a world and every
  row scoped to it — entities, relations, knowledge, ledger, sessions,
  gatherings, conversations, proposed mutations, events, discoverable
  details, and the world row itself — via `delete_world_cascade`
  (`writes.py`), the first delete-side helper in that module and the sole
  documented exception to "History is sacred". The cascade sets `PRAGMA
  defer_foreign_keys = ON` on the transaction before any DELETE so the
  self-referential columns (`location.parent_location_id`,
  `faction.parent_faction_id`, `character.current_location_id`) resolve
  without nulling; `prompt_template` rows are deleted scoped to `world_id`
  only — the 13 global `world_id IS NULL` seeds are untouched — and the
  `user` table is never touched. `_activate_world_core` (`app.py`,
  delete-path only) extracts the existing deactivate-all → flush →
  activate-one logic so the route can re-resolve `is_active` onto a
  survivor without violating `idx_world_one_active`. The route is one
  atomic transaction: deleting the active world re-activates the
  most-recently-created survivor; deleting the last world returns
  `remaining: 0` and the frontend force-opens the existing
  `worldCreateOpen()` creation modal (client-side only — no server-side
  redirect mechanism exists or was added). Frontend: a delete button next to
  `#world-selector` opens a click-away-protected confirm modal (B2′) where
  `Supprimer définitivement` stays disabled until the creator types `Oui`
  exactly.
- **v1.61** — No new tables or columns. Gathering lifecycle reconciliation
  (BRIEF-53): `close_open_memberships` (`gathering.py`) extracts
  `migrate_npc`'s inline B1-repair close (select `gathering_member` rows
  for an entity with `left_at IS NULL`, set `left_at = now`, never delete)
  into a reusable helper — `migrate_npc`'s net behavior is unchanged. The
  creator-CRUD entity editor (`update_entity`, `cockpit/crud.py`) now calls
  it when a `character`'s `current_location_id` actually changes, or when
  `entity.status` transitions away from `"active"`; `delete_entity`'s
  soft-delete calls it unconditionally. Writes no canon (gatherings are not
  canon) — no `_apply_mutation`, no `proposed_mutation`, no
  `change_history`. Defensively, `_active_members` (`cockpit/app.py`),
  `assemble_npc_context`'s H_COMPANY roster query, and
  `assemble_mj_context`'s co-presents query (`context.py`) each gained a
  join to `Character` plus `entity.status='active' AND
  vital_status='alive'`, mirroring `_present_npcs` — an entity-vivacity
  filter layered on top of the unchanged `gathering_member.left_at IS NULL`
  membership predicate, not a replacement of it. Selected columns / return
  shapes of all three reads are unchanged.
- **v1.60** — No new tables or columns. PC creation assistant (BRIEF-52):
  creator types a concept → the local author model proposes a draft
  (`entity.description` + `character.appearance`/`backstory` + `knowledge[]`
  only — A1; no `aversion`, `physical_tier`, faction, or starting location) →
  the creator edits the prose inline → accept extends the existing
  `POST /api/characters/player`. New `pt-player-generation` prompt template
  (`usage="player_generation"`) and standalone
  `entity_author.generate_player_draft(brief, db)` — a sibling to
  `generate_world_draft`, not a `_TYPE_FIELDS` entry, writes no canon, never
  calls `_create_entity_core`. New read-only route
  `POST /api/characters/player/generate` (`app.py`, beside
  `POST /api/worlds/generate`, deliberately not on the `crud.py` router).
  `PlayerCharacterCreateBody` gained `description`/`appearance`/`backstory`/
  `knowledge` (optional); PC knowledge rows are written through the
  sanctioned `writes.write_knowledge` helper with `is_secret=False` by
  construction (never `_normalize_knowledge`, which is NPC-only and forces
  `is_secret=True`); an unrecognised `level` defaults to `"rumor"` instead
  of 422ing. The 4-skill seed and the creator-picked starting location are
  untouched (B1/C1). Also closes the H1 structural hardening: the
  `H_COMPANY` co-presence query inside `assemble_npc_context`
  (`context.py`) gained a `Character.character_type != "player"` predicate,
  excluding a PC from any NPC's "AVEC QUI TU TE TROUVES" list by
  construction rather than by every caller's `interlocutor_id` convention —
  behaviorally a no-op today, since the player was already excluded
  downstream at every existing call site.
- **v1.59** — No new tables or columns. Application-layer: Lieux hierarchy
  browse (per-level type grouping, breadcrumb drill), read-only
  `GET /api/locations` (Entity ⋈ Location, all statuses, active-world
  scoped), and `room` added to the creator CRUD `location_type` options
  (BRIEF-51). `location_type` remains free text on the CRUD path; `room` is
  not offered to the generator.
- **v1.58** — World-bible generator (BRIEF-47): one-line seed → AI draft →
  pre-fills the existing "Nouveau monde" create form → unchanged
  `POST /api/worlds` accept. `entity_author.generate_world_draft(brief, db)`
  is a sibling to `generate_entity_draft`, not routed through it (World has
  no `entity_id` FK, so it is not a `_TYPE_FIELDS` entry); `db` is
  read-only there — its only use is the new `pt-world-generation` prompt
  template lookup. The model is prompted for `fundamental_laws` as a JSON
  array of short, world-spanning constraints; the function flattens it in
  Python to a numbered newline-joined string before returning, so the value
  reaching the form (and later the region-manifest reader) is always a flat
  string, never a list/dict. New route `POST /api/worlds/generate`
  (`app.py`, alongside `POST /api/entities/generate`) delegates only to
  `generate_world_draft` — writes nothing. New `index.html` "Générer avec
  l'IA" seed panel lives inside the existing `worldCreateOpen()` modal;
  `worldGenerateDraft()`/`worldApplyDraft()` pre-fill the same
  `world-create-name` / `-description` / `-laws` fields `worldCreateSubmit()`
  already reads — that submit function, `create_world`, and `WorldCreateBody`
  are untouched. No new World column, no edit/PATCH route — set-at-creation
  only. **No schema change** — additive `prompt_template` seed row only
  (`pt-world-generation`, `usage="world_generation"`, seeded via
  `scripts/seed_pilot.py`'s existing idempotent upsert).
- **v1.57** — Create-PC path: `POST /api/characters/player` (name +
  starting location, binds to the creator user, mirrors seed skill seeding)
  + `idx_character_one_pc_per_user_world` partial-unique (one PC per user
  per world, multiplayer-safe). Closes the create-world → generate →
  create-PC → play loop (BRIEF-46). Added `character.world_id TEXT NOT NULL
  REFERENCES world(id)` — denormalized from `entity.world_id` (same pattern
  as `relation.world_id`), needed because SQLite can't index across a join
  to `entity`; backfilled for every existing row. New route validates
  `current_location_id` is a `location` entity in the active world (400, no
  write, on a miss) before any write; creates the entity + `character` row
  + the four `skill` rows (physical, agility, perception, composure) at
  `tier=0` — the same rows the skill sheet and physical-resolution arbiter
  read off any PC. Exactly one `db.commit()`; `IntegrityError` from the
  partial-unique index (a second PC for the same world+user) surfaces as a
  clean `{"ok": false, "error": ...}`, not a 500. Cockpit gains a minimal
  create-PC form (name + starting-location dropdown) on the *Personnage
  joueur* sub-tab; on submit it re-calls `GET /api/bootstrap` so the UI
  picks up the new resolved PC. Migration: `scripts/migrate_v1_57.py`
  (idempotent — adds the column, backfills it, creates both indexes).
  Bugfix folded in: `GET /api/bootstrap` previously raised when the active
  world had no PC yet, which made a freshly created world unable to resolve
  even `world_id` — the create-PC form's location dropdown had nothing to
  scope to. It now catches that case and returns `player_id`/
  `current_location_id` as `null` instead, `world_id` always resolves.
- **v1.56** — De-hardcode `char-player` (BRIEF-45): player character resolved
  via `character_type='player'` scoped to the active world
  (`_player_character_id`); `GET /api/bootstrap` feeds the resolved id to the
  static cockpit JS (no server-side templating added); `analyzer.py`
  player-detection now keys on the resolved id. No schema change.
- **v1.55** — Generic world bootstrap (`POST /api/worlds`, empty
  auto-activated world, fresh UUID) + B2 premise reader: region manifest
  now reads the active world's `description` / `fundamental_laws`
  (previously dormant columns) and composes them with the region brief;
  `region_manifest` template gains `world_description` /
  `world_fundamental_laws` (version bumped). No new tables/columns. Note:
  world premise is public config, not a structural-exclusion exception.
- **v1.54** — Active world selection (BRIEF-43). Added `world.is_active
  BOOLEAN NOT NULL DEFAULT FALSE` and the partial unique index
  `idx_world_one_active` (`CREATE UNIQUE INDEX ... WHERE is_active = TRUE`),
  enforcing at most one active world at a time — same pattern as
  `faction_membership.is_primary`. `_world_id()` (`cockpit/crud.py`) now
  resolves `select(World).where(World.is_active == True)` instead of
  `select(World).first()`, and raises a 400 with the verbatim message
  "No active world. Activate a world before proceeding." if none is active
  — no more "guess the first unordered row." New route `POST
  /api/worlds/{world_id}/activate` (`cockpit/app.py`, not `crud.py` — it
  flips a selection flag, not narrative canon) deactivates every other
  world and activates the target in one transaction, with an explicit
  `db.flush()` between the two steps so the partial-unique index never
  sees two active rows at once; 404 on an unknown id; `{"ok": false,
  "error": ...}` + rollback on any other failure. New `GET /api/worlds`
  lists all worlds with their active flag. `seed_pilot.py` now seeds the
  pilot `"verkhaal"` world with `is_active=True`. Cockpit gains a header
  world-selector dropdown (`index.html`) — selection only, no create/
  delete. Migration: `scripts/migrate_v1_54.py` (idempotent; auto-activates
  the sole world row on a single-world database). Hard prerequisite for
  A1 (several worlds in one DB); until A1 lands, only one world is expected
  to exist.
- **v1.53** — Bugfix: harden the region manifest dedup comparison key,
  `_name_key` (BRIEF-42). **No schema/table/route/canon change.**
  `_dedupe_by_name` (`region_author.py`) deduped NPC/faction/location names
  on `name.strip().lower()` only, so byte-different renderings of the same
  name — apostrophe glyph (`'` U+0027 vs `'` U+2019/U+02BC), inner/
  non-breaking whitespace, Unicode accent-composition (NFC) — both survived
  as separate rows (RECON `RECON-duplicate-npc-name`, verdict H1; H2 — the
  A1 top-up merge and Phase-B re-submit's `_normalize_manifest` re-run —
  ruled out, that wiring was already correct). Fix: new module-level
  `_name_key(name)` (NFC normalize, fold apostrophe variants to `'`,
  collapse inner whitespace, lowercase) replaces the raw key. Behavior
  unchanged: still global-by-name, first-occurrence-wins, drop-later +
  note; the surviving row's stored `name` is still the original,
  unnormalized string. Shared helper, so factions and locations get the
  same hardening.
- **v1.52** — Region review: read-only full-sheet modal, R4a (BRIEF-41).
  **Client-only, no schema/table/route/canon change.** `cockpit/index.html`
  gains a single reusable modal (backdrop + container + swappable body) and
  `regionRenderSheet(type, localId)`, which reads `entry.result.draft`
  (already client-side in `regionDraft` since BRIEF-36) and renders the
  entity's full draft — every existing public field plus the secret block,
  in two labelled sections ("Public" / "Secret — caché en jeu") — with
  `faction_local_id`/`location_local_id` resolved to names. Opened by
  clicking an NPC/location/faction **name** in the review tree (a new
  click target structurally distinct from the existing accept/reject and
  link-confirm buttons). Pure client render: no new endpoint, no change to
  `/api/regions/generate` or `/api/regions/commit`, no fetch issued by the
  modal. Read-only — no inputs, no draft mutation; editing (D1/D2) and
  add-missing (B/C) remain deferred. Secrets are shown by design (the
  creator surface); in-play structural exclusion is enforced elsewhere (the
  accessors) and is untouched by this step.
- **v1.51** — Region NPC top-up clamp, A1 (BRIEF-40). **No schema/table/
  route change.** Adds one new prompt template, `pt-region-manifest-topup`
  (usage `region_manifest_topup`), seeded via `seed_pilot.py`'s existing
  `upsert_prompt_template` path. `region_author.py` gains two module
  constants (`MIN_NPCS_PER_FACTION = 4`, `MIN_FACTIONLESS = 4`, must stay
  in sync with the prose floor in `REGION_MANIFEST_SYSTEM_PROMPT`) and a
  clamp inside `generate_region_manifest` (Phase A): after the Stage-0
  manifest is parsed and normalized, code computes the NPC shortfall
  against the floor and, if non-zero, issues one targeted re-prompt to the
  same `AUTHOR_MODEL` for exactly the missing NPCs, merges them into the
  full manifest, and re-normalizes (never normalizes the partial top-up
  payload alone). One pass only — a residual shortfall is recorded as a
  note, not retried. A top-up failure degrades to a note; the primary
  manifest's success path is never aborted by it. This amends K1 (manifest
  was the *sole* density determinant) to a bounded add-only floor — see
  ARCHITECTURE_DECISIONS.md.
- **v1.50** — Region NPC density floor, prompt-text only (BRIEF-39). **No
  schema/table/route/function change.** The `region_manifest` template's
  `system_prompt` (`pt-region-manifest`, usage `region_manifest`) gains a
  density-floor instruction: at least 4 NPCs per faction and at least 4
  factionless NPCs per region. The floor is steered entirely through the
  Stage-0 prompt — no count-enforcement code was added to
  `region_author.py`. The floor is a soft target, not a guarantee.
- **v1.49** — Region two-phase pipeline, editable manifest checkpoint
  (BRIEF-38). **Application-layer only, no table/column/schema change, no
  canon-write semantics change** — reuses `pt-region-manifest` and the
  entity-generation templates as-is. `region_author.py`'s Stage-0 (the
  model call producing the manifest) is extracted into its own function,
  `generate_region_manifest(brief, db)`, returning
  `{ok, manifest, notes, skipped}` on success and the existing
  `{ok: false, error}` shape verbatim on every failure path (empty brief,
  missing template, template format error, Ollama error, malformed/non-JSON
  manifest) — a mechanical extraction, no behavior change. `generate_region_draft`
  is refactored to take an already-produced **manifest dict** instead of a
  brief; its first action re-runs the existing `_normalize_manifest` on the
  incoming dict and uses the result as authoritative (the client-edited
  manifest is advisory, the server re-derives), then runs Stages 1-3
  unchanged. New cockpit route `POST /api/regions/manifest`
  (`RegionGenerateBody`, Phase A) — writes no canon. `POST
  /api/regions/generate` is repurposed to accept `{manifest: dict}`
  (`RegionBuildBody`) instead of `{brief: str}` and calls the refactored
  Phase B — still writes no canon, response shape unchanged. Scope is C1 —
  one-liner *text* editing only at the checkpoint (no count/add/remove/
  rewiring); persistence is B1 — no draft/manifest store, the edited
  manifest is held client-side and re-sent, mirroring the commit route's
  posture. Cockpit UI: the Région sub-tab's generate trigger now stops at a
  checkpoint screen (`regionRenderManifest` — flat Factions/Lieux/PNJ lists,
  entity name read-only, one-liner editable) before a new "Générer les
  fiches" button (`regionBuild`) advances to the existing review tree
  (`regionRenderTree`, untouched); `regionRestart` now also clears the held
  manifest. The review tree, accept/reject cascade, link confirm/discard,
  and `/api/regions/commit` are all untouched.
- **v1.48** — Judgment-link wiring, chantier 3, closes the region loop
  (BRIEF-37). **No schema/table/column change, no new `RELATION_TYPE`** —
  reuses `connects_to`/`controls` and the commit-free `write_relation`
  (v1.31 area). `POST /api/regions/commit` gains **phase 4**, run after
  factions/locations/NPCs (stages 1-3) and before the existing single
  `db.commit()`: for each CONFIRMED `sensed_links` suggestion of the two
  wirable kinds — `connection` (writes `connects_to`, `direction="mutual"`,
  intensity `50`) and `faction` (writes `controls`, `entity_a_id`=faction,
  `entity_b_id`=location, `direction="a_to_b"` mandatory) — resolves the
  named target intra-region first (the local->real id map built this same
  call) then by DB exact-match scoped to the world (S1 — a new region can
  stitch into existing geography), never auto-creating a miss. `parent` /
  `other` `sensed_links` and NPC `shared_with` remain display-only, exactly
  as chantier 2 left them; no secret-membership channel exists yet (Q1), so
  none is wired. `RegionCommitBody` gains `confirmed_links: dict[str, bool]`
  (key `"<location_local_id>#<sensed_links index>"`, default unconfirmed —
  the creator opts links IN, the inverse of entity default-accept). The
  commit response gains `links: {written: [...], unresolved: [...]}`; a
  rejected/uncommitted source or target, or a self-link, writes nothing and
  is recorded as unresolved instead. Cockpit UI: each wirable `sensed_links`
  row in the D1 review tree's location nodes gets a confirm/discard toggle
  (`regionRenderLinkToggles`, `regionConfirmedLinks`); `parent`/`other` rows
  keep rendering as plain read-only notes.
- **v1.47** — Region review + atomic commit, chantier 2 (BRIEF-36). **No
  schema/table/column change, no new canon-write semantics** — reuses the
  commit-free cores added in v1.46. New cockpit route `POST
  /api/regions/commit` (`cockpit/app.py`, outside `crud.py`, same
  neighbourhood as `POST /api/regions/generate` but this route DOES write
  canon): takes a re-sent region draft tree + a raw per-entity accept/reject
  map (both untrusted client-held state, never server-persisted), re-derives
  the accept/reject cascade itself, and calls `_create_entity_core` /
  `_create_knowledge_core` directly in dependency order (factions ->
  locations, root first -> placeable NPCs + their knowledge) against one
  shared session with a single `db.commit()` at the end; any exception rolls
  back the whole batch. Only the structural skeleton is wired
  (`parent_location_id`, primary public `faction_membership`,
  `current_location_id`) — judgment-tier links (`connects_to`/`controls`/
  secret memberships/`shared_with`) stay read-only suggestions, deferred to
  chantier 3. New cockpit UI: a "Région" Création sub-tab (brief -> generate
  -> spatial review tree with per-entity accept/reject -> commit).
- **v1.46** — Commit-boundary seam, pre-step for atomic region commit
  (BRIEF-35). **No schema/table/column change, no canon-write-path semantics
  change** — application-layer only. `create_entity`, `create_knowledge`,
  and `open_entity_membership` (`cockpit/crud.py`) each split into a
  commit-free core (`_create_entity_core`, `_create_knowledge_core`,
  `_open_membership_core`) plus a thin route wrapper owning the single
  `db.commit()`/`db.refresh()`; only *when* the commit fires moves, not
  *what* is written. Single-entity creator-CRUD behaviour is unchanged (one
  commit per click, identical responses, identical 409 on a membership
  conflict); side effect: the character-with-primary-faction create path now
  commits once instead of twice.
- **v1.45** — Region orchestrator, chantier 1 (BRIEF-34). Application-layer
  only: **no new table or column, no canon-write path added**. New module
  `src/world_engine/region_author.py` (`generate_region_draft(brief, db)`)
  composes the existing atomic entity generator
  (`entity_author.generate_entity_draft`) across a four-stage pipeline
  (manifest -> factions -> locations -> NPCs) to turn a free-text creator
  region brief into an ephemeral **region draft** — a tree of per-entity
  drafts plus draft-local id references (`fac-N`/`loc-N`/`npc-N`), never
  persisted, never wired to real entity ids. New cockpit route `POST
  /api/regions/generate` (outside `crud.py`, no canon write, mirrors `POST
  /api/entities/generate`). The only schema-adjacent change is a new
  `prompt_template.usage` value, `region_manifest` (Stage 0's manifest
  template, `pt-region-manifest`, consuming only `{brief}`) — added to the
  `usage` comment enumeration on `prompt_template`. `entity_author.py` /
  `generate_entity_draft` / `_TYPE_FIELDS` are unmodified.
- **v1.44** — Aversion prose field, character live + faction dormant
  (BRIEF-33). New nullable `TEXT` column on both `character` and `faction`:
  `aversion`, the prose dual of `philosophy` — what an entity rejects or
  fears as a concept/category (technology, sunlight, magic, outsiders),
  never a named entity (that belongs to the relation graph). Both are
  creator-CRUD prose config (no `change_history`, written in place, like
  `philosophy`/`backstory`) and both are proposed by the entity generator
  (`entity_author.py`, `_TYPE_FIELDS` for `character` and `faction`).
  Asymmetric reader: `character.aversion` is read into the NPC dialogue
  prompt's `H_IDENTITY` block (`assemble_npc_context`), raw prose, no label
  prefix; `faction.aversion` is stored + proposed but read by NO assembler —
  public-tagged (injectable in principle) but dormant by minimal-first. A
  future faction-posture reader is its own brief and MUST route through
  `read_public_memberships` (the same accessor boundary that excludes
  secret affiliations and true `role`s from prompts) — it must not, as a
  side effect, resurrect `philosophy`/`description`/`internal_structure`
  into prompts. Migration: `scripts/migrate_v1_44_aversion.py`.

- **v1.43** — Faction generator (BRIEF-32). Application-layer only, no
  schema/column change: `entity_author.py` registers `faction` in
  `_TYPE_FIELDS`, reusing the `entity_generation` template unchanged
  (no new prompt template, no `proposed_mutation`). Field partition: `name`,
  `description`, `faction_type` (validated against the enum, falls back to
  `other`), `philosophy`, `internal_structure` are public/proposed;
  `roles` (`[{name,description}]`, ordered by rank, nameless rows dropped)
  is public/proposed into `entity.metadata['roles']` (v1.42 precedent);
  `internal_tensions` and `goals` are creator-only (secret block → typed
  columns, passthrough); `magic_knowledge_level`, `scope`, and
  `parent_faction_id` are never proposed (absent from `_TYPE_FIELDS`, stay
  at form defaults) — same structural-link invariant as
  `parent_location_id` for the location generator (v1.37). Accept path
  reuses the existing composite entity PUT/POST and the existing
  `authorFactionRolesDraft` editor — no new write code.

- **v1.42** — Faction roles vocabulary (BRIEF-31). No schema/column change:
  factions now use `entity.metadata['roles']`, a flat ordered list of
  `{name, description}` (array order = rank), following the
  `metadata.price_list` precedent (v1.33). Creator-CRUD config like
  `scope`/`goals`/`parent_faction_id` — no `change_history`, no
  snapshot. Authored via a structured editor on the faction sheet (no raw
  JSON). The NPC membership panel's free-text `role` input is now a
  `<select>` populated from the member's chosen faction's `roles` (names
  only, stored order) plus an "autre" escape hatch; `faction_membership.role`
  remains a free-text passthrough column — "autre" never writes back to
  `faction.metadata['roles']` (no auto-promotion). New read endpoint
  `GET /api/entities/{faction_id}/roles` (public org vocabulary, no
  secret-filtering). `writes.write_membership` untouched.
- **v1.41** — Cover-role mechanism for double agents (BRIEF-30). New
  nullable column `faction_membership.cover_role` — the prompt-facing
  façade role; the true `role` stays creator-only. `read_public_memberships`
  (`context.py`) now resolves `cover_role ?? role`, so the true role behind
  a cover never crosses the accessor into any prompt (own-context A1 today,
  any future third-party reader for free). No backfill — defaults NULL, so
  every existing membership renders unchanged (`NULL ?? role = role`). Set
  at OPEN time only; changing it is close + reopen, same as `role`. Espionage
  behaviour rides on `goals` prose authored by the creator, never a
  confessable label. Migration: `scripts/migrate_v1_41_cover_role.py`,
  idempotent.
- **v1.40** — Drop `character.faction_id` (BRIEF-28). The four v1.39
  consumers recabled onto `faction_membership` (active `is_primary=TRUE`
  row): `app.py`'s `list_npcs` queries `faction_membership` instead of
  `char.faction_id`; the composite create (`crud.py`'s `POST /api/entities`)
  strips `faction_id` from the `character` row INSERT and, after the entity
  commits, opens a primary membership via `writes.write_membership` when the
  payload carried one — creator authority, not an AI proposal path;
  `scripts/seed_pilot.py`'s five `faction_id=` kwargs replaced by a
  post-create `ensure_primary_membership` call (idempotent open). The
  cockpit's read-only "Faction (legacy)" character field is removed from
  `ENTITY_TYPE_REGISTRY` (the Appartenances sub-block is the only display).
  `entity_author.py` and its `index.html` draft pre-fill are untouched — the
  draft's transient `faction_id` key now flows only into the create-path
  membership write. Migration `scripts/migrate_v1_40_drop_character_faction_id.py`
  drops `idx_character_faction` then the column (`ALTER TABLE character DROP
  COLUMN faction_id`); pre-checks that every historical non-NULL
  `character.faction_id` has a matching `is_primary=TRUE` `faction_membership`
  row before dropping, aborts otherwise. No re-backfill. Scope OUT, unchanged:
  no membership reader wired into any context assembler; `role` / `is_secret`
  still unread; no AI `membership_change` mutation type.
  — *Reader A1: TES AFFILIATIONS (BRIEF-29, application layer, no schema
  change)*: new `read_public_memberships(entity_id, session)` in
  `context.py` — the single structural choke-point for `faction_membership`
  reaching any prompt, filtering `is_secret = FALSE` and `left_at IS NULL`
  in the query itself (no override parameter). `assemble_npc_context`
  injects its result as a "TES AFFILIATIONS" block (own public/active
  memberships, primary first then oldest-joined), placed immediately
  before the existing "TES TARIFS" block; header omitted entirely when the
  list is empty, mirroring the TES TARIFS empty-case idiom. No secret
  self-include — the holder's own secret membership stays out of its own
  prompt; espionage rides on `goals` prose, never a confessable affiliation
  label. `faction_membership` (v1.39) is otherwise unchanged.
- **v1.39** — Faction membership, C1 (BRIEF-27). New table
  `faction_membership` — durable member<->faction roster, the durable
  counterpart to session-ephemeral `gathering_member`: `id`, `world_id`,
  `entity_id`, `faction_id`, `role` (DORMANT), `is_primary`, `is_secret`
  (DORMANT), `joined_at`, `left_at`. Roster predicate, single source: active
  iff `left_at IS NULL`. Two structural guards, partial unique indexes:
  `idx_membership_one_primary` (at most one active primary per member),
  `idx_membership_unique_active` (no duplicate active membership in the
  same faction) — plus `idx_faction_membership_entity` /
  `idx_faction_membership_faction`. Append/close only — close + reopen for
  any role/primary change, no `change_history` column. Backfilled from
  every `character.faction_id` (one `is_primary=TRUE` row each,
  `scripts/migrate_v1_39_faction_membership.py`, idempotent). New
  `writes.write_membership(mode="open"/"close")` — the sole chokepoint,
  creator-CRUD only (no `_apply_mutation` branch this step). Cockpit:
  character sheet's "faction primaire" dropdown replaced by an
  Appartenances sub-block (list/add/close); faction sheet gains a read-only
  roster (secret members shown with badge — creator sees everything).
  `character.faction_id` is **retired-pending-follow-up**, not dropped:
  Scope IN #6's grep gate found consumers beyond the cockpit editor (now
  read-only, relabeled "legacy") and `idx_character_faction` — `app.py`'s
  `list_npcs` (NPC-selector display), `entity_author.py`'s AI-authoring
  assistant (resolves+sets `faction_id` on character creation, BRIEF-24),
  its cockpit pre-fill mirror in `index.html`, and
  `scripts/seed_pilot.py`'s seed data. The column and its index stay; the
  drop is deferred to a follow-up once those consumers migrate to
  `faction_membership`. No assembler reads `faction_membership`, `role`, or
  `is_secret` this step — the first reader and the structural
  `is_secret=FALSE` exclusion it requires are the next, separate brief.
- **v1.38** — Faction structure & resources (BRIEF-26). Three new `faction`
  columns — `parent_faction_id` (containment tree, mirror of
  `location.parent_location_id`), `scope` (descriptive scale label, NOT
  derived from tree depth), `goals` (prose) — plus `idx_faction_parent`.
  All three are DORMANT: placed-but-unread, the `equipped` pattern; no
  assembler or guard reads them. `controls` added to `RELATION_TYPES`
  (`crud.py`): controller (faction or any entity) → controlled asset,
  `direction='a_to_b'`, structurally isolated like `connects_to` (verbatim
  guard comment, every world-wide relation scan must exclude both). Faction
  treasury surfaced via the existing `ledger` + `GET/POST .../ledger`
  endpoints — zero schema, zero new route, creator-direct only; the
  character-only "Solde" cockpit block now also renders on the faction
  sheet. Cockpit Factions editor gains the three new fields (parent
  dropdown excludes self; full cycle detection deferred — nothing traverses
  the tree). Membership (roster, ranks, secret affiliation — C1) remains
  the next, separate step; `character.faction_id` untouched.
- **v1.37** — No new tables or columns. Application-layer: AI
  entity-authoring assistant extended to `location` (BRIEF-25).
  `_TYPE_FIELDS` gains the `location` key in `entity_author.py`;
  `pt-entity-generation`'s `{type_fields}` rendering covers `location` (the
  existing template row is reused, no new row created). `subculture`
  public/hidden segregation enforced structurally in the parser: the public
  region is filtered against the LIVE `_SAFE_SUBCULTURE_KEYS` constant
  (imported from `context.py`, never hardcoded), and `"hidden"` is reachable
  only from the model's `secret.subculture_hidden` field — the same
  intra-JSON doctrine as the `public`/`secret` block split. `location_type`
  validated against its enum (default `"other"` + note); `access_level`
  validated against its enum but left BLANK on a miss (never defaulted to a
  permissive value). `magic_status`/`coordinates`/`parent_location_id`/
  `connects_to`/`discoverable_detail` are all out of generation scope —
  the generator never proposes or writes any of them; a sensed parent,
  neighbour, or controlling faction surfaces only as a display-only
  `sensed_links` note. No `knowledge` rows are generated for locations.
  Création → Lieux gains the same one-shot generate affordance as NPC.
- **v1.36** — No new tables or columns. Application-layer: AI
  entity-authoring assistant (NPC). New module `entity_author.py`
  (`generate_entity_draft`, writes no canon); new template
  `pt-entity-generation` (`usage='entity_generation'`); new cockpit route
  `POST /api/entities/generate` (outside `crud.py`, no canon write); Création
  → NPC gains a one-shot generate affordance pre-filling the existing author
  form. `prompt_template.usage` comment gains `entity_generation`.
- **v1.35** — Activated `discoverable_detail.discovery_threshold` (no
  migration; column present since v1.26). Explicit perception searches now
  filter revelation candidates by `discovery_threshold <= roll total
  (2d6 + modifier)` via a fourth `.where()` clause in `_stream()`. Default 0
  preserves prior behaviour (any partial/success reveals). All candidates
  above threshold collapse into the existing `[FOUILLE INFRUCTUEUSE]` path —
  no new rubric, no leak of gated content. Doctrine refined: `partial` never
  withholds a reached detail but may fail to reach a higher-threshold one.
- **v1.34** — No new tables or columns. Infra: default DB path relocated out
  of the git working tree to an absolute `~/.world_engine/world_engine.db`
  (env override `WORLD_ENGINE_DATABASE_URL` preserved, top precedence);
  `db.py` now guarantees the carrier directory exists (`mkdir`) before any
  connection. Rationale: 2026-06-19 incident — a gitignored `.db` at the repo
  root was destroyed out-of-application; "history is sacred" protects rows,
  not the carrier file.
- **v1.33** — No new tables or columns. Pricing layer. New documented
  convention `entity.metadata.price_list` (`{tag: int}`, base-unit integers)
  marking a seller's firm catalogue — same metadata-config category as
  `physical_tier`/`coordinates` (no `change_history`; the sale audit trail is
  the ledger). `assemble_npc_context` injects a verbatim "TES TARIFS" block
  for any NPC with a non-empty `price_list` (the seller's own list only —
  never another entity's, never `assemble_mj_context`/player perception),
  serving as both firm catalogue and the reference scale for uncatalogued
  quotes. `npc_dialogue` bumped (+pricing rubric: catalogue prices firm and
  universal; uncatalogued items priced by the NPC on the catalogue's scale,
  relation-modulated, one price, no haggling; sell only what you have).
  Cockpit "Tarifs" editor (Création → NPC), creator-direct read-merge-write
  on `metadata` (no clobber, no `proposed_mutation`). `seed_pilot.py` seeds
  Maelis Vorne a starter `price_list`. **Pricing writes no canon** — a quote
  is free dialogue; the concluded exchange is a `resource_change` (step 2)
  through the checkpoint. *Deferred:* haggling/negotiation; relation-modulated
  catalogue prices; structured pricing call; Claude-routing for high-stakes
  quotes; ledger-driven pricing dataset; price→entity linkage; automatic
  price evolution (inflation/scarcity); NPC purchasing/inventories; per-world
  currency display name.
- **v1.32** — No new tables or columns. Application-layer: `resource_change`,
  the 6th implemented `proposed_mutation.mutation_type` (alongside
  `relation_change`, `new_knowledge`, `knowledge_change`, `status_change`,
  `item_update`). Two-leg payload — a mandatory monetary leg (`entity_id`,
  signed `amount` in base unit, `counterparty_id`, `reason`) and an OPTIONAL
  `knowledge` leg (fresh acquisition only). Owned by `analyze_window`
  (`proposed_by='local_ai_window'`); `pt-conversation-analysis` bumped to v4
  with a verbatim rubric (record only a STATED, concluded exchange that moves
  the PLAYER's balance — A1; never infer a price — that is step 3; never for
  NPC↔NPC money). `_apply_mutation` gains the branch: both legs in one
  SAVEPOINT (atomic), money via `writes.write_ledger_entry`
  (`source_type='conversation'`), knowledge via `writes.write_knowledge`.
  Guards: non-negative balance (read via `ledger.get_balance`) → Needs
  attention; knowledge-leg block-whole guard → Needs attention if the buyer
  already holds the subject (upgrade-by-purchase deferred) or an equivalent
  knowledge was already applied this conversation (scanning both applied
  `new_knowledge` and applied `resource_change` knowledge legs).
  `resource_change` is EXCLUDED from write-time dedup and from
  `_find_applied_duplicate` — the money leg accumulates like
  `relation_change`; knowledge-leg idempotency is enforced at apply only.
  **Known accepted gap (documented, not closed):** guard 4c is
  one-directional — a `resource_change` knowledge leg applied before a
  colliding `new_knowledge` (same conversation/entity/subject) is not caught,
  since the `new_knowledge` guard is deliberately left unextended; narrow
  (player-sells-to-an-overhearing-NPC only) and caught by creator review.
  **Deliberate exception:** this is the only apply branch that writes two
  canon tables. *Deferred:* knowledge_change leg (upgrade-by-purchase);
  pricing / `metadata.price_list` (step 3); tracked NPC purses (A2/A3);
  automation/auto-approval; ledger-as-pricing-dataset.
- **v1.31** — Economy foundation: `ledger` (append-only, currency only).
  New table `ledger` (`id`, `world_id` REFERENCES `world(id)`, `entity_id`
  REFERENCES `entity(id)`, `amount INTEGER NOT NULL` — signed, world base
  unit, `counterparty_id` REFERENCES `entity(id)` — filled but not
  double-written (decision A1), `reason`, `source_type` —
  creator | correction | conversation | pass_play (last two reserved for
  step 2), `conversation_id`, `pass_play_id`, `session_id`, `created_at`).
  Indexes `idx_ledger_entity`, `idx_ledger_session`. Balance =
  `SUM(amount)` per `entity_id` — no stored balance, no `CHECK`. **Ledger is
  append-only: INSERT-only on both canon-write paths; corrections are new
  compensating lines, never edits/deletes.** Single shared INSERT helper
  `writes.write_ledger_entry`; reads in `ledger.py`
  (`get_balance`, `list_entries`). Creator-direct writes via `crud.py`
  (`POST /api/ledger`, `GET /api/entities/{id}/ledger`, `GET /api/ledger`),
  god-mode (no non-negative guard). Cockpit: read-only "Registre" sub-tab +
  per-character balance block, creator-mode only. Amounts in the world base
  unit; the tiered display scale (e.g. 1 or = 100 argent = 10000 bronze) is
  a display + per-world-config concern, NOT storage. *Deferred:* AI-detected
  `resource_change` mutation + double-table info purchase (step 2); pricing
  / `metadata.price_list` (step 3); tracked NPC purses (A2/A3); explicit
  favors via a future `resource_type` column (zero-migration
  `ALTER … DEFAULT 'currency'`); ledger-as-pricing-dataset.
- **v1.30** — Signpost layer + scene-establishing narration on entry
  (BRIEF-17). File jumps v1_26 → v1_30: the intervening schema versions
  (v1.27 UI shell, v1.28 connects_to, v1.29 travel) required no DDL.
  New column `discoverable_detail.signpost_group TEXT` (nullable; NULL = no
  cluster) + `idx_discoverable_signpost_group` index. Both the `ambient`
  panel row and its grouped `hidden` content rows carry the SAME
  `signpost_group` value (D1: one signpost groups N contents, each content
  in exactly one group — no N↔N, deferred as D2). The `ambient` read path,
  DORMANT since v1.26, is now ACTIVE — but only via a code-side silence
  predicate (`active_signposts`, context.py), never by an assembler, and
  only its `content` (see the narrowed `discoverable_detail` NOTE above).
  E1: a signpost panel falls silent once the player holds a `knowledge` row
  (any level) for EVERY hidden subject in its cluster; partial knowledge
  still narrates. New entry-narration call in `enter_scene` (app.py):
  a single non-streamed `chat()` MJ call (`pt-mj-establishment`, new usage
  `mj_establishment`), fired on EVERY entry (G1 — no change-detection, that
  is G2, deferred), reading `entity.description` + the allow-listed
  `_SAFE_SUBCULTURE_KEYS` subculture slice + `active_signposts(...)`'s
  surviving content. Names no NPCs (J1). Wrapped in `try/except` — a failed
  or skipped call never blocks scene entry. `_scene_response` gains one field,
  `establishment: str | None`. Cockpit Lieux discoverable-details editor
  (C1): rows sharing a `signpost_group` render together under a group
  header with per-row ambient/hidden badges; `signpost_group` is editable on
  create and edit, round-trips through the CRUD endpoints. Deferrals: N↔N
  (D2), the pickable-object/`item` layer, G2 change-cadence, NPC-naming at
  entry (J2), `discovery_threshold` activation, opposed search, per-character
  discovery state — all unchanged from BRIEF-13.

- **v1.29** — No new tables or columns. Application-layer: `ResponseMode` gains
  `travel`; `pt-mj-interpretation` bumped to v6 (travel mode added, decision-rule
  reordered to `join > dialogue > physical > travel > npc_reaction > scene`;
  `reference` now also carries the player's destination words for travel).
  `_perform_travel(player_id, location_id, db)` extracted as a shared helper
  (creator travel tool + new in-fiction path); now rejects inactive destinations
  (C-a). `_location_neighbours(location_id, db)` added — reads `connects_to`
  relations for a single location, excludes inactive neighbours; distinct from
  `GET /api/locations/graph`, no shared code (decision D1). New in-fiction picker
  callback `POST /api/conversations/{conv_id}/travel` (neighbour-restricted, body
  `{"location_id": str}`; distinct from the creator `POST /api/travel`). `restrained`
  gating tuple extended to include `travel` (decision E1). Travel is a state
  transition, NOT a canon mutation — no new `mutation_type`, no `proposed_mutation`
  row is written. Deferrals: arrival narration / step C; conflict→neighbours gate;
  multi-hop; directed edges B2; edge distance/time; graph-endpoint code dedup.
  Frontend completion (BRIEF-16b, no schema bump): cockpit `index.html` handles
  `traveled` SSE (scene-view reset, mirroring the Voyager control) and
  `travel_candidates` SSE (picker → `POST /api/conversations/{id}/travel` →
  scene-view reset, mirroring the `join_candidates` picker).

- **v1.28** — No new tables or columns. Introduces the `connects_to` relation
  convention (location↔location map adjacency: `direction='mutual'`,
  `intensity=50` is a meaningless structural default that MUST NOT be read as a
  social signal — structurally isolated, no gameplay consumer reads it).
  `location.coordinates` is used for the first time, as `{x,y}` SVG node
  positions persisted via the existing entity PUT (read-merge-write,
  coordinates-only). New read-only creator endpoint `GET /api/locations/graph`
  (active-location nodes + their `connects_to` edges). `connects_to` added to
  `RELATION_TYPES` (suggestion list). Cockpit Lieux sub-tab gains a hand-rolled
  SVG adjacency editor: view, drag-to-position, click-to-connect,
  click-to-delete-edge, add-location. Frontend + one read route + one
  suggestion-list addition; no migration. Travel (consumption of the graph) is
  deferred to Step B.

- **v1.27** — No new tables or columns. Cockpit reorganized into a two-mode
  Play / Création shell (frontend only, `index.html`): Play gains Discussion /
  Historique / Mes savoirs sub-tabs; the review queue moves out of Play into
  Création; the Fiche relocates under Création → Personnage joueur; entity
  editors split into NPC / Personnage joueur / Lieux / Factions / Objets /
  Artefacts sub-tabs; Objets surfaces the existing `item` editor; Artefacts is
  a read-only scaffold pending backend support. No schema migration.

- **v1.26** — Explicit search (perception) + discoverable details (BRIEF-13).
  New table `discoverable_detail` (`id`, `world_id` REFERENCES `world(id)`,
  `location_id` REFERENCES `entity(id)`, `subject TEXT NOT NULL` — short tag
  e.g. `"lettre_innommee"`, `content TEXT NOT NULL` — what the player learns,
  `access_level TEXT NOT NULL DEFAULT 'hidden'` — `ambient | hidden` (ambient
  is DORMANT this brief: reserved for passive on-entry reveal, no code reads
  it yet), `discovery_threshold INTEGER NOT NULL DEFAULT 0 CHECK (BETWEEN 0
  AND 12)` — DORMANT this brief: minimum 2d6 total for reveal, reserved so
  "some info is better hidden than other" can be activated later without a
  migration; same philosophy as `knowledge.share_threshold`, `discovered
  BOOLEAN NOT NULL DEFAULT FALSE` — flips TRUE when the engine-proposed
  `new_knowledge` is APPLIED by the creator, not at propose time).
  Indexes: `idx_discoverable_location ON discoverable_detail(location_id)`,
  `idx_discoverable_world ON discoverable_detail(world_id)`.
  **NOTE: this table is NEVER read by any context assembler.** Undiscovered
  content lives only in a table no prompt ever touches; content reaches a model
  only via the explicit post-selection injection on a partial/success
  perception search (`_stream()`, `domain="perception"`, `opposed_npc_id=None`).
  Discovery flows through the existing `new_knowledge` / `_apply_mutation`
  pipeline — no new canon-write path. The `discovered` flip is a benign
  side-effect inside the already-sanctioned `_apply_mutation`, wrapped in its
  SAVEPOINT. `pt-mj-interpretation` bumped to v5: `physical` mode extended to
  include explicit search intent; distinguishing test added verbatim: *"chercher
  activement quelque chose de précis (un objet, un indice, un passage) =
  physical ; simplement observer l'ambiance sans rien chercher de précis =
  scene."* Migration: `python scripts/migrate_v1_26.py`.
  **Deferred (recorded for activation):** passive perception on location entry
  (`access_level='ambient'` — schema present, no code reads it); `discovery_threshold`
  activation (schema present, never compared against roll total); NPC opposition
  to a search (a named NPC blocking or hiding information); per-character
  discovery state (solo `discovered` bool — multiplayer per-player state deferred).

- **v1.25** — Contested-attempt penalty for constraint-gated turns (no schema
  change). Gagged-speech and escape-from-restraint attempts now resolve at
  `npc_tier = 1` (fixed difficulty) instead of 0. At `player_tier = 0` this
  shifts failure probability from 41 % to 58 %, making a gated attempt harder
  than a normal unopposed roll — the "contested resolution" design intent. Both
  gated cases share a single fixed tier as a pilot simplification: a gag
  (object) and a grip (person) are mechanically distinct resistances, but
  provenance (the captor's entity ID and tier) is not yet stored in
  `scene_state.constraints` (which remains `list[str]`). **Deferred
  refinement:** escape should eventually roll against the captor's
  `physical_tier`, read from `entity.metadata_`, once constraint provenance is
  captured in `scene_state` (e.g. `constraints: [{"type": "restrained",
  "source_id": "<entity_id>"}]`). The "highest-tier NPC in the gathering"
  heuristic is explicitly rejected as false certainty: the strongest NPC
  present is not necessarily the captor.

- **v1.24** — Scene constraints: scene_state, gating, condition ladder (BRIEF-12).
  New column `conversation.scene_state JSON NOT NULL DEFAULT '{}'`. Structure:
  `{constraints: ["gagged"|"restrained"|"blindfolded"], condition:
  "unharmed"|"bruised"|"injured"|"neutralized", frozen: false, history: []}`.
  **NOTE: `scene_state` is EPHEMERAL combat/constraint state, scoped to the
  conversation. It is cleared when the conversation closes. It is NOT canon: a
  durable consequence (lasting injury, capture, death) must go through
  `proposed_mutation`. Same philosophy as `gathering`: free play inside the
  scene, controlled consequences outside it.**
  Constraint effects enforced in code before model calls:
  `gagged` → dialogue mode rejected, re-routed to contested physical
  (composure domain, `npc_tier=0`); `restrained` → any physical/scene/
  npc_reaction mode becomes an escape attempt (physical domain); success
  removes the constraint. `blindfolded` → `assemble_mj_context` structurally
  excludes `location.description` and `co_presents[].description` (data
  exclusion, never instruction). Condition `neutralized` sets `frozen=True`.
  Frozen scene: `/say` yields a fixed French MJ message, zero model calls;
  creator panel can unfreeze. Condition ladder `unharmed→bruised→injured→
  neutralized` moved only by code on `violent=True` physical verdicts:
  failure degrades one step (partial never degrades condition — complication
  band, not damage band); `neutralized` auto-sets `frozen=True`.
  Reaching `injured` or `neutralized` auto-proposes a `status_change` with
  `proposed_by='engine'` (new value for `ProposedMutation.proposed_by`).
  `scene_state` writes archive the previous state snapshot to `history[]`
  before each change (history is sacred). Arbiter template `pt-mj-arbiter`
  bumped to v2: now returns four fields — `domain`, `opposed_npc_id`,
  `applies_constraint` (restrained|gagged|blindfolded|null), `violent`
  (bool). Condition injected into NPC and MJ context when not `unharmed`.
  Creator cockpit gains a scene_state panel: read + direct edit
  (constraints, condition, frozen); edits archive to `history[]`. Migration:
  `python scripts/migrate_v1_24.py`.

- **v1.23** — Arbiter phase + Python dice for physical resolution (BRIEF-11).
  No new tables or columns. Adds `ResponseMode.physical` to the `/say`
  interpretation modes (`pt-mj-interpretation` bumped to v4): a physical
  attempt whose outcome is uncertain — climbing, grabbing, dodging, forcing,
  sneaking, resisting. New template `pt-mj-arbiter` (`usage='mj_arbitration'`,
  `world_id=NULL`, upsert) — a non-streaming JSON classification call,
  `/no_think`, fired only for `physical` turns, that returns
  `{"domain": "physical|agility|perception|composure", "opposed_npc_id": "<name
  or null>"}`; the model classifies ONLY, never rolls, never decides outcomes,
  and falls back to `domain="physical"`, `opposed_npc_id=null` on any failure.
  New module `resolution.py`: pure-Python `resolve_physical(domain,
  player_tier, npc_tier=0) -> Verdict` —
  `roll = randint(1,6) + randint(1,6) + player_tier - npc_tier`, banded
  `<=6 failure`, `7-9 partial`, `>=10 success`. `player_tier` comes from the
  player's `skill.tier` for the classified domain (schema v1.22); `npc_tier`
  comes from `entity.metadata.physical_tier` of `opposed_npc_id` (key
  documented in v1.22, default 0 when absent — now actually read for the
  first time). The verdict is logged (audit) and sent to the player as an SSE
  event `data: {"verdict": {...}}` before narration, same pattern as
  `npc_raw`. **Player-roll rule**: the roll always belongs to the player —
  when an NPC initiates a physical action against the player, we do not roll
  the NPC's attempt, we roll the player's response (dodge, resist, endure)
  with the NPC tier as opposition. One mechanic, one code path, one audit
  point. For opposed physical turns, the targeted NPC is called exactly like
  `npc_reaction` (one-shot wordless reaction, `npc` row written canonically,
  so `analyze_window` keeps proposing `relation_change` as usual); unopposed
  physical turns behave like `scene` (no NPC call, no `npc` row). MJ narration
  for `physical` is constrained by the verdict band via a verbatim rubric
  ("Tu narres les conséquences ; tu ne rejuges JAMAIS le résultat", with a
  canon-boundary clause — at most neutralized/constrained, never killed,
  permanently injured, or durably captured by this narration). The resolution
  path writes zero canon — no new `relation`/`knowledge`/`entity` writes; the
  canon boundary above is enforced both at the prompt level (rubric) and
  structurally (no write path exists). Deferred, nothing implemented this
  step: NPC↔NPC physical acts arising from Tier-3 initiative continue to be
  narrated by tier comparison, no roll — accepted design, see
  "Deferred decisions" in `ARCHITECTURE_DECISIONS.md`.
- **v1.22** — Player skill sheet foundation (BRIEF-10). New table `skill`
  (`character_id` REFERENCES `entity(id)`, `domain` — physical | agility |
  perception | composure, `tier` INTEGER NOT NULL DEFAULT 0 CHECK BETWEEN -1
  AND 2, `change_history` JSON DEFAULT '[]', `created_at`/`updated_at`), plus
  `idx_skill_character`. Verbatim NOTE under the table: skill rows exist ONLY
  for player characters in this phase — an NPC's physical capability is a
  single tier in `entity.metadata` (key `physical_tier`, -1..2, default 0 when
  absent, read in a later step — not added to any NPC metadata yet); social
  abilities (persuasion, deception, charm) are NEVER skill domains — a
  standing design guard, not a deferral. Application layer: `seed_pilot.py`
  seeds a new test player character (id `char-pc-test-2`, name from the
  `SKILL_SHEET_PC_NAME` constant, placeholder `"PC_TEST_2"`) with four `skill`
  rows, all `tier = 0`. The cockpit gains a "Fiche" view: a creator-mode
  inline editor (tier `-1..2` per domain, direct write to the `skill` row —
  **no `proposed_mutation`**, same rule as all creator-mode editing — appends
  the previous `{"tier", "changed_at", "by": "creator"}` to `change_history`
  and bumps `updated_at` on every change) and a player-mode read-only
  rendering of the same view. No dice, no arbiter, no `ResponseMode.physical`,
  no `skill_change` mutation type, no automatic skill progression — skills
  evolve only by creator edit until a later step. See "Physical layer — skill
  sheet" in `ARCHITECTURE_DECISIONS.md`. Deferred: automatic skill progression
  (a future `skill_change` mutation type), numeric HP, opposed rolls, NPC
  skill rows, passive perception, scene description on location entry (MJ
  establishes the scene — backlog).
- **v1.21** — Window analysis replaces per-turn analysis and the two-tier
  final pass (BRIEF-09). Adds `conversation.last_analyzed_turn INTEGER NOT
  NULL DEFAULT 0` — the high-water mark for `analyze_window`
  (`turn_order <= last_analyzed_turn` already analyzed; 0 = never analyzed).
  `analyze_single_turn` and `analyze_conversation` (the old final pass, which
  filtered out `relation_change`) are removed; a single `analyze_window`
  function now owns all three mutation types (`relation_change`,
  `new_knowledge`/`knowledge_change`, `status_change`), tagged
  `proposed_by='local_ai_window'`. It reads only unanalyzed `player`/`npc`
  `conversation_message` rows (`turn_order > last_analyzed_turn`), is a no-op
  (no model call, no marker change, no commit) when there is nothing new, and
  on success persists every surviving proposal AND advances
  `last_analyzed_turn` atomically in one transaction; on JSON parse failure it
  logs a warning and returns without advancing the marker so the next trigger
  retries those turns. Write-time dedup against existing `proposed` rows
  (via `_mutation_match_key`, idempotent types only) avoids re-proposing a
  `new_knowledge`/`status_change` already flagged by `analyze_overhearing` for
  the same window — `relation_change` is never deduped (accumulating type).
  Fires automatically at three scene-boundary triggers — conversation close
  (`POST /api/conversations/{id}/end`, `POST /api/travel`), player location
  transition (`enter_scene`, for any conversation left open at the previous
  location), and gathering dissolution (`enter_location` and `migrate_npc` in
  `gathering.py`) — plus the manual cockpit **Analyze** button
  (`POST /api/conversations/{id}/analyze`), which now returns
  `{"status": "nothing_new"}` when there are no unanalyzed turns.
  `--force` semantics changed: deletes only `status='proposed'` rows for the
  conversation and resets `last_analyzed_turn` to 0, then re-runs over the
  full transcript — reviewed rows (`applied`/`approved`/`rejected`) are never
  deleted (history is sacred); re-analyzing the full transcript may re-propose
  relation deltas that were already applied, so force re-proposals must be
  reviewed manually. `_normalize_to_schema` is hardened for multi-NPC windows:
  the old `npc_entity_id`/`conv.npc_id` default for an unresolved
  `relation_change.entity_a_id` is removed — if either `entity_a_id` or
  `entity_b_id` cannot be resolved from the model's output, the item is
  skipped and logged rather than attributed to a window-level default.
  `pt-conversation-analysis` is bumped to `version=3`, adding an
  anti-inflation rubric: at most one `relation_change` per ordered entity
  pair per window (the net effect across the window, not a sum of per-turn
  deltas), and routine/cordial exchanges are not by themselves grounds for a
  `relation_change`. `proposed_mutation.proposed_by` gains `local_ai_window`;
  `local_ai` and `local_ai_immediate` are documented as legacy — no longer
  produced, historical rows preserved.

- **v1.20** — Possession-only check + NPC reaction to refused gestures
  (BRIEF-08, D2a.1). No new tables or columns. `pt-mj-interpretation`
  (bumped to `version=3`) drops `equip_action` from its JSON output and
  prompt instructions — extraction is `mode` + `used_object` only. The
  `{item_list}` variable (`context.format_item_list_for_interpretation`, now
  identical to `format_inventory_line`) drops the equip-state annotation:
  "Objets du joueur : Dague." The `/say` flow's possession check is now
  binary: `used_object` owned by the player → pass; not owned or
  `unknown_object` → refused; `item.equipped` is no longer read by the check,
  and the equip-toggle step (`_auto_apply_item_update`, the `item_update`
  producer) is removed entirely. A refused turn no longer skips the NPC
  phase: it runs as a normal dialogue turn with a one-shot `[GESTE RATÉ]`
  system instruction telling the responding NPC what it just witnessed; the
  NPC's reply is persisted as a normal `npc` row. The MJ's one-shot
  `[ACTION REFUSÉE]` instruction is updated to integrate that NPC reaction
  "comme pour un tour normal". Per-turn analysis (`analyze_single_turn`) runs
  on refused turns like any other turn (a threatening or ridiculous failed
  gesture may legitimately produce a `relation_change`). `pt-mj-narration`
  (bumped to `version=4`) replaces the D1 "RÈGLES SUR LES OBJETS" wording:
  drawing, stowing, or otherwise manipulating a possessed item is free
  narration — only possessing an item that's used matters. `{inventory_line}`
  drops the Équipé/Sur soi split too: "Objets du joueur : dague."
  **Dormant machinery, untouched**: `item.equipped` stays in the schema
  (cockpit-only — no gameplay path reads or writes it); `item_update` remains
  an implemented `_apply_mutation` branch with no active producer; the
  cockpit equipped toggle stays functional, reactivatable if the combat
  chantier needs an in-hand state. See "Auto-applied mutations" in
  `ARCHITECTURE_DECISIONS.md`.
- **v1.19** — Possession check + auto-applied equip toggle (BRIEF-07). No new
  tables or columns. `proposed_mutation.mutation_type` gains `item_update`
  (the equip toggle) and `proposed_mutation.proposed_by` gains
  `interpretation` (mutations produced by the `/say` interpretation phase;
  currently only `item_update`). Application layer: `pt-mj-interpretation`
  (bumped to `version=2`) now also extracts `used_object` (canonical item
  name the player physically uses this turn, `null`, or `"unknown_object"`)
  and `equip_action` (`"draw"` | `"stow"` | `null`), reading a new
  `{item_list}` template variable (`context.format_item_list_for_interpretation`
  — "Objets du joueur : Dague (équipé)."). The `/say` flow then judges
  possession in code against canon `item` rows: an equip toggle that changes
  state writes and immediately self-applies an `item_update`
  `proposed_mutation` (`proposed_by='interpretation'`, `status='applied'`,
  fully visible in the cockpit); a redundant toggle is a silent no-op (no
  row); an unowned/`unknown_object` action, or a `used_object` that remains
  unequipped after the toggle (unless the toggle was itself a `"stow"`), is
  refused — the MJ receives a one-shot `[ACTION REFUSÉE]` system instruction
  (not persisted) and the turn is forced to `scene` mode, skipping the NPC
  phase (no `npc` row written). The inventory line
  (`context.format_inventory_line`) is read after the toggle, so the same
  turn's narration reflects it. `_apply_mutation` gains the `item_update`
  branch (verifies `item.owner_id IS NOT NULL` per the schema CHECK, sets
  `item.equipped`, same SAVEPOINT pattern). `item_update` is excluded from
  `_find_applied_duplicate` — it is a state transition, redundancy is already
  prevented at proposal time, and a legitimate draw→stow→draw sequence must
  apply each time. On any interpretation failure, falls back to
  `ResponseMode.dialogue` with `used_object = null, equip_action = null` — no
  check, no toggle, turn proceeds normally. See "Auto-applied mutations" in
  `ARCHITECTURE_DECISIONS.md`.
- **v1.18** — Object permanence, static possession (BRIEF-06). New `item`
  entity type (added to the documented `entity.type` values) and a new
  extension table `item` (`owner_id`, `location_id`, `equipped`,
  `condition`, CHECK `NOT equipped OR owner_id IS NOT NULL`), with
  `idx_item_owner` and `idx_item_location`. The three-states NOTE (equipped /
  carried-stowed / lying-in-location, never deletion) is recorded under the
  table. Application layer: `seed_pilot.py` seeds one `Dague` item
  (`owner_id = char-player`, `equipped = TRUE`). The MJ narration context gains
  a per-turn, non-snapshotted inventory line (`{inventory_line}`, schema
  `context.format_inventory_line`) — "Équipé : … . Sur soi : … ." — read fresh
  from `item` at every turn, injected into `pt-mj-narration` (bumped to
  `version=3`), whose system prompt gains the verbatim "RÈGLES SUR LES OBJETS"
  arbitration rules (ambient props vs tracked items, in-fiction refusal). The
  cockpit's entity-author flow gains `item` as a creatable/editable type
  (owner/location pickers, equipped toggle, condition; CHECK enforced
  server-side), and the character entity sheet gains a read-only Items
  section. All in-game item mutations (transfer, creation, equip toggle) are
  deferred to D2 — see `ARCHITECTURE_DECISIONS.md`.
- **v1.17** — No new tables or columns. Application-layer: `knowledge_change`
  is now implemented in `_apply_mutation` (cockpit `app.py`) — the fourth
  implemented mutation type alongside `relation_change`, `new_knowledge`, and
  `status_change`.
  Finds the `knowledge` row by `entity_id` + `subject` (never creates — that
  is `new_knowledge`'s job); guards, in order: (a) row not found → "Needs
  attention" with note `knowledge row not found`; (b) monotone re-check at
  apply time — current `level` >= payload `to_level` → "Needs attention"
  with note `level already >= proposed`. On success, appends the row's
  previous state via `_append_knowledge_history(row, "apply_mutation")`
  (v1.16 helper), then updates `level`, `source`, and `updated_at`.
  `knowledge_change` is deliberately ABSENT from `_find_applied_duplicate`:
  unlike `new_knowledge`/`status_change` (idempotent facts), successive
  legitimate upgrades in one conversation (e.g. `rumor → partial`, then
  `partial → knows`) must both apply — the monotone check at apply time is
  the correct guard, not an identity-based duplicate check.
  — **Deterministic level ladder** (decision E): `unaware < rumor <
  suspicious < partial < knows < fully_understands`. Two new shared helpers
  in `writes.py`: `knowledge_level_rank` (ladder position, -1 if
  unrecognised) and `cap_knowledge_level` (clamp to at most `knows` by
  default).
  — **Detection at both per-turn sites**, payload shape `{entity_id,
  subject, from_level, to_level, source}` with `source` in
  `"overheard:{conversation_id}:{speaker_id}"` or
  `"affirmed:{conversation_id}:{speaker_id}"` form (the latter new
  alongside `overheard:` from v1.15):
  - `analyze_overhearing` (Tier 4): a receiver who already holds a row on
    the overheard subject now gets a `knowledge_change` proposal (instead of
    being skipped outright) when the computed level — one step below the
    speaker's, floored at `rumor` — is strictly higher than the receiver's
    existing level (monotone); proposal-dedup (k) extended to
    `knowledge_change`. Plain acquisitions (`new_knowledge`, no existing
    row) are unchanged.
  - `analyze_single_turn` (per-turn pass): a normalized `new_knowledge` item
    whose target entity already holds a row on the subject is converted to
    `knowledge_change` (direct affirmation) — two-party speaker resolution
    (receiver = player → speaker = the turn's responding NPC; receiver = NPC
    → speaker = the player), K2 guard (speaker holds no row → drop), secret
    guard (speaker's row `is_secret` → drop), target level = speaker's row
    level capped at `knows` via `cap_knowledge_level` (model-proposed level
    ignored; `fully_understands` never granted by hearsay), monotone (target
    <= receiver's existing level → drop). Plain acquisitions (receiver holds
    no row) are untouched — no K2 retrofit there, out of scope.
- **v1.16** — Added `knowledge.change_history` (JSON DEFAULT '[]'), an exact
  mirror of `relation.change_history`. CRUD debt fix (same class as the
  retroactive `relation` fix in v1.11): `writes.write_knowledge` now appends
  the row's previous state — `level`, `content`, `source`, `is_incorrect`,
  `updated_at`, plus `changed_by` (`"creator_crud"` | `"apply_mutation"`) and
  `changed_at` — to `change_history` via the new `_append_knowledge_history`
  helper before any in-place update. Existing rows start with `[]`; no
  backfill (past edits are unrecoverable). Row creation and deletion are
  unaffected. The helper is shared and ready for `knowledge_change` apply
  support, which arrives in the following step (not implemented here).
- **v1.15** — No new tables or columns. Comment-level changes only:
  documented `local_ai_overhearing` as a third AI source tag on
  `proposed_mutation.proposed_by` (Tier 4 overhearing pass — bystanders
  acquire knowledge from a turn, acquisition-only, never level upgrades) and
  `overhearing_classification` in the `prompt_template.usage` list. Deferred
  decision: **E3-general upgrade rule** (`knowledge_change` apply + upgrade
  detection) is the next step; speaker-level cap at `knows` for direct
  affirmation belongs to that step.
- **v1.14** — No new tables or columns. Application-layer **cockpit batch
  review** (`POST /api/mutations/batch-review`, cockpit `app.py`): the review
  queue gains per-row checkboxes (rendered only for `status = 'proposed'`
  rows) plus a "select all / none" toggle and "Approve selected" / "Reject
  selected" buttons. The endpoint processes the selected ids sequentially,
  re-checking each row's status (`!= 'proposed'` → skipped, never touched —
  history is sacred), and routes approve through the existing
  `_apply_mutation` (same SAVEPOINT, duplicate guard, and "Needs attention"
  fallback as unit approve) and reject through the same field updates as unit
  reject. Processed rows get the literal `batch-review` marker appended to
  `creator_notes`. Returns verdict counts (`applied` / `needs_attention` /
  `skipped`, or `rejected` / `skipped`). Deferred decision: payload editing in
  batch is deliberately excluded — editing means unit review.
- **v1.13** — No new tables or columns. Application-layer **creator travel
  control** (`POST /api/travel`, cockpit `app.py`): a clean location
  transition for the player — closes any open `conversation` (status →
  `closed`, `ended_at` set), closes the player's open `gathering_member`
  row(s) (`left_at` set; NPC members untouched), then updates
  `character.current_location_id`, all in one transaction. No-op if the
  destination equals the current location; rejected (400, no state change)
  if the destination is not a `location` entity of the player's world. Does
  not call `generate_gatherings` / `enter_location` — the existing
  scene-entry transition-detection flow remains the sole owner of gathering
  generation. Narrative travel (`travel` response mode, adjacency model) is
  out of scope, deferred to E2.
- **v1.12** — No new tables or columns. Three application-layer changes
  (BRIEF-03-assembler-prompts, scope D-b3):
  — **Sign rubric for `relation_change`**: `pt-conversation-analysis`
  (`usage='conversation_analysis'`, used by both `analyze_conversation` and
  `analyze_single_turn`) gains an explicit sign rubric — hostility, violence,
  threats, discovered deception, and humiliation are always NEGATIVE; physical
  contact is judged by intent (an embrace warms, a shove or brawl is
  NEGATIVE); helping, defending, gift-giving, and shared danger are POSITIVE
  — plus contrastive mini-examples. Bumped to `version=2`, delivered via
  `seed_pilot.py` upsert (the template moved from `get_or_create` to
  `upsert_prompt_template`).
  — **`relevance_hint` reserved parameter**: `assemble_npc_context` and the
  new `assemble_mj_context` both accept an optional `relevance_hint: str |
  None = None`, accepted and currently ignored. Deferred-decision note: a
  future relevance-selection stage may only NARROW the security-scoped
  context, never widen it — inert until context size measurably hurts.
  — **MJ context assembler** (`assemble_mj_context` in `context.py`): a new,
  deterministic, scoped context for the MJ narration layer — the player's
  perception boundary. Three static parts (location name/description +
  allow-listed `subculture` ambiance, excluding `magic_status`; the player
  character's own `knowledge` rows; up to 5 most recent `event` rows with
  `knowledge_status IN ('public','confirmed')`, location-matched first) plus
  one dynamic part (co-present NPCs' public name + description, read fresh
  from the gathering roster — `gathering_member` with `left_at IS NULL`).
  Structural exclusions (by query construction): no NPC `knowledge`, no
  `character.secrets`, no `entity.internal_name`, no `is_public = FALSE`
  entities, no `secret`/`rumor` events. The static parts are snapshotted
  under a new `"mj"` key in `conversation.injected_context` at conversation
  start (alongside the existing NPC snapshot, unchanged in shape) — the
  baseline a future bleed auditor compares MJ narration against. Wired into
  `pt-mj-narration` (bumped to `version=2`, new `{mj_context}` variable) and
  `_build_mj_user` (all three modes: `dialogue`, `npc_reaction`, `scene`); the
  MJ system prompt gains an anti-invention rule scoped to the provided
  context, mirroring `npc_dialogue`'s rule.
- **v1.11** — No new tables or columns. Retroactive documentation (per
  BRIEF-01-tooling-v2 audit) of the **Author CRUD** (`cockpit/crud.py`,
  shipped just before this entry): a second sanctioned canon-write path —
  direct, state-setting creator edits to `character`/`faction`/`location`
  (composite entity + extension row, soft delete) and in-context
  `relation`/`knowledge` editors (hard delete), with no `proposed_mutation`
  checkpoint. Shares `writes.write_relation`/`write_knowledge` with
  `_apply_mutation` so clamping/validation cannot diverge. **Fix included**:
  `write_relation(mode="set")` (CRUD relation edits) now appends the previous
  state to `change_history` before overwriting — history is sacred on both
  write paths — via a shared `_append_history_snapshot` helper extracted from
  `mode="delta"`; `_apply_mutation`'s behavior is unchanged. See
  `ARCHITECTURE_DECISIONS.md`, "Author CRUD — the second sanctioned
  canon-write path".
- **v1.10** — No new tables or columns. Doc-level change only: documented the
  `character.secrets` / `knowledge.is_secret` boundary convention (NOTE under
  the `character` table — `secrets` is creator meta-narrative, never read by
  any context assembler; concealment is modeled via `knowledge.is_secret`,
  excluded by the assembler) and the two-sanctioned-canon-write-paths rule
  (`_apply_mutation` for AI proposals after creator approval, and the creator
  CRUD for direct creator authority — no other path may write canon). Added
  project tooling: a permanent `## Invariants (verified at every review)`
  section in `CLAUDE.md`, plus `/close-step` and `/review-step` commands.
- **v1.9** — No new tables or columns. Application-layer change only: NPC
  initiative — bystander NPCs can act spontaneously without being addressed
  (Tier 3, C1–C3; full rationale in `ARCHITECTURE_DECISIONS.md`).
  — **C1**: a per-turn vote (`pt-mj-initiative`, `usage='mj_initiative'`)
  decides whether one bystander acts (cadence E1: at most one per turn),
  using each candidate's `relation` signal toward the player and `entity.status`.
  — **C2**: the chosen NPC's act (`pt-npc-initiative-act`,
  `usage='npc_initiative_act'`) is a `{"act_text", "move"}` JSON object;
  `move=true` triggers `migrate_npc` (Tier 1 primitive) before narration —
  not a canon mutation, same as forming/dissolving a gathering. Both new
  templates seeded with `world_id=NULL`, upsert.
  — **C3**: the candidate pool widens from the player's gathering to every
  open gathering at the location; a non-member winner has `move=true` forced
  structurally. New `prompt_template.usage` values: `mj_initiative`,
  `npc_initiative_act`.
- **v1.8** — Multi-NPC scenes, Tier 1 (migration only — generation, name
  resolution, and the multi-participant `/say` flow are later steps). Two new
  tables and one relaxed column:
  — `gathering`: an ephemeral social cluster attached to a `session`
    (`location_id`, MJ-generated `label`, `status` open|dissolved). Its only
    durable trace in canon is the `proposed_mutation` rows it produces —
    **forming or dissolving a gathering is not itself a canon mutation.**
  — `gathering_member`: the roster, doubling as a conversation's participant
    list. Earshot = `left_at IS NULL`; rows are never deleted, only closed off.
  — `conversation.npc_id` relaxed from `NOT NULL` to nullable: it now names an
    optional seed/focus NPC; participants are derived from the gathering
    roster instead. Added `conversation.gathering_id` (the cluster present).
  — Five new indexes: `idx_gathering_location`, `idx_gathering_session`,
    `idx_gathering_member_group`, `idx_gathering_member_entity`,
    `idx_conversation_gathering`.
  Application-layer invariants recorded for the steps that build on this
  migration (see `ARCHITECTURE_DECISIONS.md` for the full rationale):
  **A2** — the MJ returns names, not ids; the code resolves them against the
  entities present, and a name that doesn't resolve is dropped and logged, never
  guessed. **B1** — partitioning into gatherings happens once, in full, at
  entry: every present NPC lands in exactly one gathering (a lone NPC forms a
  solo gathering of one), preserving the invariant that a present NPC always
  belongs to exactly one open gathering — a location may hold several
  simultaneous open gatherings, one per cluster. **C1** — gatherings are
  generated once at entry; no spontaneous reshuffling mid-scene.
  — *Tier 1, step 2 (application layer, no schema change)*: `gathering.py`
  implements the A2/B1 contracts above as two deliberately separate functions —
  `generate_gatherings` (loads the present NPCs, asks the MJ to partition them
  via the new `pt-mj-gathering` template, resolves names to entity ids,
  completes the partition, writes `gathering`/`gathering_member` rows; never
  raises, falls back to an all-solo partition on any failure) and
  `enter_location` (the single-player caller: dissolves the location's open
  gatherings for the session, then regenerates — see the function's docstring
  for why dissolution must live in the caller, not the core). New template:
  `pt-mj-gathering` (`usage='mj_gathering'`, `world_id=NULL`, upsert). Seeded
  by `seed_pilot.py`, which also gained two NPCs (Bryn, Korin) so the pilot
  tavern has five present NPCs to exercise clustering.
  — *Tier 1, step 3 — closes the tier (application layer, no schema change)*:
  the `/say` flow gains a fourth interpretation mode, **`join`** — the player's
  intent to settle with an open gathering. While ungrouped, `join` takes
  priority over the other three modes ("parler n'a pas de cible tant qu'on n'a
  pas rejoint"); the model is given the player's `gathering_status` and a
  free-text `reference` to the named group, resolved against the open
  gatherings' rosters by the same A2 contract (exact match against present
  names/labels; ambiguous or unresolved → the cockpit lists the open
  gatherings and the player picks — reusing the new C2 target selector, see
  below). Joining inserts one `gathering_member` row (`left_at=NULL`) and
  anchors `conversation.gathering_id`; like forming one, **joining a gathering
  is not a canon mutation** — no `proposed_mutation` row is produced.
  The NPC phase generalises from a single fixed NPC to a **selected
  responder**: contract **A3 (hybrid speaker selection)** — an explicitly
  targeted NPC always answers; an address to "the group" triggers one MJ call
  (`pt-mj-speaker`, `usage='mj_speaker_selection'`, new template) that picks
  exactly one active member to respond (cadence **B1bis**: exactly one
  responder per turn, no PNJ↔PNJ exchange — that stays Tier 3). The cockpit
  gains a **C2** target selector ("groupe" / a named NPC) next to the `/say`
  field, populated from the joined gathering's active roster — distinct from
  the existing **C1** ("generated once at entry; no reshuffling"); the label
  collision is deliberate disambiguation, not a renumbering. Context assembly
  gains contract **D1 (mutual awareness)**: `assemble_npc_context` now accepts
  a `gathering_id` and injects an "AVEC QUI TU TE TROUVES EN CE MOMENT" section
  naming co-present members and their public description — simple co-presence,
  no relation-based modulation (that stays a later refinement). New template:
  `pt-mj-speaker`. The `pt-mj-interpretation` template and its `ResponseMode`
  enum gain `join`; `_interpret_mode` now returns `(mode, reference)`.
- **v1.7** — No new tables or columns. Application-layer change only:
  the `/say` flow gains a **mode-routing interpretation phase** (phase 0)
  that classifies the player's input into `dialogue` | `npc_reaction` | `scene`
  before calling the NPC. Consequences:
  — `scene` turns skip the NPC call entirely; no `npc` row is written;
    the MJ narrates the environment without any NPC involvement.
  — `npc_reaction` turns call the NPC with a one-shot wordless-reaction
    instruction; the NPC produces a gesture, not speech; the MJ renders it
    in third-person prose with no quoted dialogue.
  — `dialogue` turns are unchanged (the prior behavior).
  New template: `pt-mj-interpretation` (`usage='mj_interpretation'`,
  `world_id=NULL`, upsert). Seeded by `seed_pilot.py`.
  The `prompt_template` usage column comment is updated to include
  `mj_interpretation`. The `conversation_message` turn_order note is updated:
  N+1 is absent for scene turns.
- **v1.6** — No new tables or columns. Comment-level changes only:
  (1) `conversation_message.speaker` now documents three values: `player` |
  `npc` | `mj`. `mj` rows are the MJ narration (presentation layer); `player`
  and `npc` remain the canonical truth the analysis reads.
  (2) `proposed_mutation.proposed_by` now documents `local_ai_immediate` as a
  second AI source tag, used by the per-turn analysis that fires after each turn
  (owns all `relation_change` proposals).
  Application-layer changes: `relation_change` removed from the duplicate-apply
  guard (`_find_applied_duplicate`) because relation deltas accumulate — two
  independent events must both apply. The final-pass analysis now filters out
  `relation_change` (owned by per-turn flags). Both guards continue to protect
  the idempotent types (`new_knowledge`, `status_change`).
- **v1.5** — No new tables or columns. The creator review cockpit
  (`src/world_engine/cockpit/`) implements the full approve → apply pipeline,
  making the `proposed_mutation` lifecycle operational end-to-end. Two
  application-layer invariants are now enforced in code:
  (1) `--force` re-analysis never deletes reviewed rows (`applied`, `approved`,
  `rejected`) — only `proposed` rows are replaceable.
  (2) `_apply_mutation` runs a duplicate guard before any canon write: if an
  equivalent mutation was already applied for the same conversation (matched on
  `entity_id` + `subject` for `new_knowledge`; unordered entity pair +
  `relation_type` for `relation_change`), the new proposal is blocked and
  surfaced in the "Needs attention" review bucket rather than silently doubling
  the effect.
- **v1.4** — No new tables or columns. Added `conversation_analysis` to the documented `prompt_template.usage` values (the column is TEXT — the value was already valid, this is a doc-only update). The post-conversation analysis pipeline (`analyze_conversation.py` + `analyzer.py`) is now implemented; see `ARCHITECTURE_DECISIONS.md` for the circuit description.
- **v1.3** — Added `knowledge.share_threshold` (INTEGER DEFAULT 50, CHECK 1–100): the minimum NPC→interlocutor relation intensity required to share a non-secret knowledge row in conversation; ignored when `is_secret = TRUE`. Recorded the convention that an absent NPC→interlocutor relation is treated as neutral (50) by the assembler.
- **v1.2** — Added `conversation`, `conversation_message`, and `proposed_mutation` for live sessions and the unified mutation pipeline. Removed `pass_play.local_proposal`. Documented the role-toggle rule on `user`. Added `npc_dialogue` to prompt usages. Changed `relation.intensity` to a 1–100 scale (default 50 = neutral) with a clamp-on-apply rule. Added `updated_at` to `entity` and `knowledge`. Added an INDEXES section for frequent lookups. Schema translated to English.
- **v1.1** — Initial local-phase schema.
