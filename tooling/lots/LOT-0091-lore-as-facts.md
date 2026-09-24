# LOT — TICKET-0091 "Lore as facts (G2 + F1)"

## Objective and cut

Every piece of descriptive lore stops living in a prose column and becomes a
`fact` carrying a **facet** (what kind of statement), **participants** (about
whom) and **knowledge** (who knows). The facet vocabulary is a code registry
(`facets.py`) that also declares, per facet, its family, its granularity
(`bloc` = one fact per entity; `affirmation` = one fact per statement), its
default-knowledge preset and its known aspects. Encounters are recorded in a
`rencontre` registry so "known from the first encounter" has a mechanism.
Then (F1) a name written into new canon prose is stored as an identity token
and rendered to the current name at read time; names the server cannot
resolve land on a worklist that Nia clears from a panel in the Lore shell.

This lot stops at: the columns and `location_subculture` are gone (v2.06),
every reader and writer goes through facts, identity tokens are posed on new
writing, and the name-resolution panel exists. It does **not** inject lore
into play prompts beyond today's behaviour (Q13a), does not touch
`knowledge.subject` (Q1b), and does not detect names cited in play (H2).

Run against `main` fetched 2026-09-22 (codeload tarball; TICKET-0090 merged,
`world-engine-schema.md:3` reads `v2.04`). Tags: **[M]** opened in the file
that declares the property; **[C]** carried from an earlier measurement, not
re-measured; **[I]** inferred.

## Briefs in this lot

- **A** `schema-v2-05` — facet/aspect columns, `fact_default` rebuild with
  scope `rencontre`, `rencontre` and `unresolved_mention` tables, the
  `FACETS` registry, the amended fact chokepoint.
- **B** `budget-moves` — pure moves out of `context.py`, `link_author.py`
  and `cockpit/play.py` (R-29: `cockpit/crud/entities.py` moves nothing).
  No behaviour change.
- **C** `encounters` — `encounters.py`, the live write points, the
  schedule/relation points, the one-shot backfill.
- **D** `resolver-and-reads` — resolver tiers (self, rencontre), knowledge
  section filter, `facet_reads.py`.
- **E** `fact-writers` — `writes/facets.py`, create/update cores, creator PC
  route, generators, facts CRUD routes, subculture route.
- **F** `sheet-facts-editor` — frontend: Facts section of the sheet (create
  and edit), generator drafts into it, `SubcultureEditor` retired.
- **G** `play-readers` — context, tick context, gathering partition, link
  agent sheet: columns replaced by facet reads.
- **H** `other-readers` — every remaining reader, including the Lore dossier
  (`facets` section).
- **I** `migration-v2-06` — relocation (L2), drop of the columns and of
  `location_subculture`, duplicate control query (D3b').
- **J** `identity-tokens` — `content_raw`, `prose_render.py`,
  `prose_tokens.py`, tokens on new writing, generator `mentions`.
- **K** `lore-names-panel` — the name-resolution panel in the Lore shell,
  the bounded reopening of the 0085 lock.

## Dependency graph

```
A ──> C ──> D ──┬──> G ──┐
│               └──> H ──┤
├──> E ──> F ────────────┼──> I ──> J ──> K
B ──> C, E, G ───────────┘
```

- A and B have no dependency on each other or on anything in this lot; run
  either first.
- C needs A (table) and B (`play.py` has 3 lines of headroom, R-21).
- D needs A and C (`acquaintances()`, C-07). G needs B and D. H needs D.
  E needs A and B. F needs E.
- I needs C, E, F, G and H: the columns are dropped only once nothing
  reads or writes them.
- **J after I is a locked-decision order, not a dependency** (I2': G2 first,
  F1 second). An executor who finds nothing blocking J before I has not
  found a defect.
- K needs J (`unresolved_mention` is filled by J's writers).
- **The branch is not playable between G/H and I.** Readers read facts from
  G/H on; existing lore becomes facts only when I runs v2.06 (Q9b keeps
  relocation and drop in one migration). Every intermediate "Done means"
  is verified on fixtures; the live gate runs after I, J and K.

## RECON

### R-01 — `fact` declares no facet and no aspect
Opened: `src/world_engine/models/canon_knowledge.py:86-117` [M].
Finding: columns `id, world_id, relation_id, event_id, world_law_id,
content, default_level, created_at, created_by, change_history`. CHECKs
`ck_fact_spine_exclusive` (at most one typed FK) and `ck_fact_default_level`.
Indexes `idx_fact_world`, `idx_fact_relation`, `idx_fact_event`,
`idx_fact_world_law`. No facet, no aspect.
Consequence: v2.05 adds `facet TEXT NULL` and `aspect TEXT NULL` with
`ALTER TABLE ... ADD COLUMN` (no CHECK — Q2a). NULL facet means "predates
TICKET-0091" and is never written again.

### R-02 — `fact_default` closes its scope set with a CHECK
Opened: `src/world_engine/models/canon_knowledge.py:140-180` [M].
Finding: `ck_fact_default_scope_type`: `scope_type IN
('world','faction','location')`; `ck_fact_default_scope_shape`: world has
NULL `scope_id`, the others NOT NULL; `ck_fact_default_level` (six levels);
`idx_fact_default_unique (fact_id, scope_type, scope_id)` unique;
`idx_fact_default_fact`. Columns `id, world_id, fact_id, scope_type,
scope_id, level, created_by` (+ `created_at` per the model tail).
Consequence: adding `rencontre` requires a table rebuild (Q3a). The shape
CHECK already accepts it (`scope_type <> 'world' AND scope_id IS NOT NULL`).

### R-03 — migration precedents, and no rebuild precedent
Opened: `scripts/migrate_v2_00_connects_to_facts.py` …
`migrate_v2_04_oriented_relations.py`; `grep -n "_rebuild\|RENAME"
scripts/migrate_v2_0*.py` [M].
Finding: the grep returns zero lines (pasted in gate (c)). Precedents:
`ALTER TABLE ... ADD COLUMN` (v2.01 `:79`), `ALTER TABLE ... DROP COLUMN`
(v2.03 `:90`), `CREATE INDEX` in one transaction with idempotent guards,
S-numbered steps, report, post-checks and `_converge_schema_meta()` (v2.04
docstring `:1-40`). Version constant `src/world_engine/schema_version.py:15`
`EXPECTED_STATIC_SCHEMA_VERSION = "v2.04"`; doc line
`world-engine-schema.md:3`; changelog newest-first
(`world-engine-schema-changelog.md:16`); agreement enforced by
`checks/schema_version_agreement.py` (changelog `:12-16`).
Consequence: the `fact_default` rebuild in v2.05 is the first of the series.
It follows SQLite's documented 12-step shape (new table, copy, drop, rename,
re-create indexes) inside the script's single transaction, with FKs on
(R-26).

### R-04 — the fact chokepoint
Opened: `src/world_engine/writes/facts.py:1-126` [M].
Finding: `create_fact(db, *, world_id, content, created_by,
default_level="unaware", relation_id=None, event_id=None,
world_law_id=None) -> Fact` (`:39-61`) adds the row. `update_typed_fact_content(db,
*, fact, content, changed_by)` (`:64-77`) appends `{"content",
"changed_by", "at"}` to `change_history` then overwrites. `attach_participants(db,
*, fact, entity_ids, role=None)` (`:80-106`) raises `ValueError` on a typed
fact; `position` from list order. `create_fact_default(db, *, world_id,
fact_id, scope_type, scope_id, level, created_by)` (`:109-126`), no
duplicate check. There is no content-update path for a free fact and no
delete path for a free fact.
Policy: `canon_write_policy.txt:137` `create_fact fact`, `:138`
`attach_participants fact_participant`, `:146` `create_fact_default
fact_default`, `:150` `update_typed_fact_content fact`.
Consequence: A amends `create_fact` (C-02) and adds `update_fact_content`
and `delete_free_fact` (C-03, C-04), each declared in the policy.

### R-05 — every `create_fact` caller
Opened: `grep -rn "create_fact(" src scripts tooling/verify/checks` [M]
(pasted in gate (c)).
Finding: `src/world_engine/writes/knowledge.py:193` (create path of
`_build_knowledge_update`; content = subject label),
`src/world_engine/writes/relations.py:144` (`_birth_typed_fact`),
`scripts/seed_pilot.py:117`, `tooling/verify/checks/fact_spine.py:138`,
`tooling/verify/checks/knowledge_resolution.py:120`. No producer of an
`event_id` or `world_law_id` fact exists.
Consequence: making `facet` required (C-02) forces all five to pass one:
`information` (knowledge path, seed), `lien` (relations), check fixtures
updated in A.

### R-06 — `fact_participant` is unique per (fact, entity)
Opened: `src/world_engine/models/canon_knowledge.py:124-138` [M].
Finding: `idx_fact_participant_unique (fact_id, entity_id)` unique;
`idx_fact_participant_entity (entity_id)`; `role` free text, `position` int.
Consequence: "the entity's facts of facet X" is a join
`fact_participant.entity_id = X` — indexed. `role` never filters
(AMENDMENT-0087-1).

### R-07 — the resolver
Opened: `src/world_engine/knowledge_resolve.py:1-304` [M].
Finding: docstring `:1-33` states the five tiers (stored row; nearest
location default up the parent chain; highest faction default across active
memberships; world default; `fact.default_level`). `_resolve_tiers` (`:93-120`)
is the pure precedence shared by `resolve_knowledge_level` (`:123-175`) and
`resolve_levels_for_entity` (`:178-225`, one pass over every fact of the
world, returns only levels above `unaware`). `resolve_public_level(s)`
(`:228-275`) enter at the world tier. `resolve_default_rows` (`:278-304`)
builds transient `Knowledge` rows for **every** fact resolving above
`unaware`, copying `fact.content` into `subject` and `content`
(`:299-300`), `is_secret=False`.
Consequence: once descriptive facts carry defaults, every reader of
`resolve_default_rows` would receive them as speakable knowledge. D filters
by facet (C-09).

### R-08 — who consumes `resolve_default_rows`
Opened: `grep -rn "resolve_default_rows" src` [M] (pasted in gate (c)).
Finding: `context.py:384` (`_npc_context_speak`), `context.py:732`
(`_mj_context_player_knowledge`), `tick_context.py:252`
(`_tick_knowledge_block`).
Consequence: C-09's facet filter keeps all three unchanged in behaviour.

### R-09 — `context.py` readers of moving columns
Opened: `src/world_engine/context.py` [M].
Finding: `_npc_context_identity` (`:231-243`) appends
`npc_char.appearance`, `.backstory`, `.aversion`, `npc_entity.description`
(`:234-241`). `_npc_context_setting` (`:327`) appends
`loc_entity.description` (`:333-334`). `_npc_context_company` (`:449`)
uses `co_char.appearance or co_entity.description` (`:471`).
`_mj_context_location` (`:698`) reads `location_subculture` rows with
`key in _SAFE_SUBCULTURE_KEYS` and `is_hidden == False` (`:704-713`) and
`loc_entity.description` (`:718`). `_mj_context_co_presents` (`:770-798`)
emits `co_entity.description` for public co-presents, `None` when
blindfolded (`:795`). `_SAFE_SUBCULTURE_KEYS = ("values",)` (`:102`).
`context.py:762` is `Event.description`, not an entity — out of scope.
Module: 956 lines, 30 top-level functions.
Consequence: G replaces each read by C-10; the file has 44 lines of
headroom, so B moves the identity/company/setting/MJ-location/MJ-co-presents
helpers out first.

### R-10 — `tick_context.py` readers
Opened: `src/world_engine/tick_context.py` [M].
Finding: `_tick_identity_block` (`:177`) appends appearance, backstory,
aversion (`:179-184`) and `npc_entity.description` (`:185-186`).
`_tick_affiliations_block` (`:280`) prints faction philosophy,
internal_tensions, aversion, goals (`:302-305`). `_tick_setting_block`
(`:313`) reads `loc_entity.description` (`:322-323`) and the `values`
subculture row, not hidden (`:326-330`). `_tick_destinations_block`
(`:337`) reads `dest_entity.description` (`:343-344`). `_tick_company_block`
(`:350`) uses `other_char.appearance or other_entity.description`
(`:364-365`). `assemble_location_event_context` (`:544`) reads the location
description (`:558-559`) and the `values` row (`:562-566`).
`_tick_faction_identity_block` (`:619`) reads faction description and
philosophy (`:623-629`); `_tick_faction_posture_block` (`:633`) reads goals,
internal_tensions, aversion (`:637-639`). Module: 736 lines, 28 functions.
Consequence: G switches every one; there is headroom.

### R-11 — the remaining readers
Opened: each file below [M].
Finding:
- `gathering.py:96` (`_request_partition`, `:84`): `char.appearance or
  entity.description` in the MJ partition prompt.
- `link_author.py:176-180` (`_npc_sheet`, `:164`): description, appearance,
  backstory, aversion. Module 959 lines, 36 functions.
- `cockpit/routes/creator.py:78` (`_generate_draft_with_l1`, `:57`):
  `faction.goals`; `:309-315` (`generate_agenda`, `:281`): owner
  description + philosophy / backstory; `:669-670`
  (`create_player_character`): `body.appearance`, `body.backstory` (PC
  creation payload).
- `cockpit/crud/goals.py:260` (`_npc_faction_goals`, `:246`):
  `faction.goals`; `:305-306` (`_backfill_one_npc`, `:289`): description,
  backstory.
- `npc_group_author.py:216` (`_resolve_faction_context`, `:210`): faction
  description; `:313` (`_generate_row_goals`, `:304`): `faction.goals`;
  `:389` `_NPC_PLAIN_STR_FIELDS = ("description", "appearance",
  "backstory", "aversion")`.
- `room_batch_author.py:100-113`, `:133` (`_compose_batch_context`, `:93`):
  non-hidden subculture of the anchor (all keys), anchor and sibling
  descriptions.
- `cockpit/play_physical.py:724` (`_build_establishment_narration`,
  `:704`): location description. `:693` is `Event.description` — out.
- `observation_runner.py:123` (`check_run_readiness`, `:84`): requires a
  non-empty `entity.description` for each NPC.
- `cockpit/crud/relations.py:293`: description truncated to 200 chars.
- `lore_candidates.py:57` (`describe_candidates`, `:18`): description.
- `cockpit/crud/entities.py:246` (`_entity_dict`, `:239`): description in
  the sheet payload.
- `lore_selectors.py:60-64` (`world_factions`, `:43`): description,
  philosophy, internal_structure, internal_tensions; `:82`, `:94-96`
  (`_identity_rows`, `:71`): description, appearance, backstory, aversion.
Consequence: H switches each through C-10. `observation_runner`'s
readiness rule becomes "has a `description` fact".

### R-12 — `location_subculture` is keyed prose with a hidden flag
**Corrected by AMENDMENT-0091-02**: the reader list below was a negative
claim with no pasted enumeration; it missed `cockpit/play_physical.py:725-734`,
`cockpit/crud/entity_geometry.py:28,113,143`, the import-only references and
`scripts/seed_pilot.py:246-269,3064`. The complete enumeration is in the
amendment and in gate (c).
Opened: `src/world_engine/models/canon.py:286-300`; `writes/config.py:104-150`;
`grep -rn "write_location_subculture(" src` [M].
Finding: columns `location_id, key, value, is_hidden`;
`idx_location_subculture_key (location_id, key COLLATE NOCASE)` unique.
One writer, `writes/config.py::write_location_subculture` (full-replace,
policy `:30`), one caller `cockpit/crud/entities.py:864`
(`set_location_subculture`, `:857`, `PUT /entities/{id}/subculture`).
`cockpit/crud/agendas.py:71` and `cockpit/crud/entities.py:80` import it
without calling it. Readers: R-09, R-10, R-11 (room batch). Key vocabulary
is free text on the creator side (`frontend/src/creation/SubcultureEditor.svelte:80`,
placeholder "clé (ex : values)").
Consequence: Q12d — each row becomes a `coutume` fact with `aspect` = key
(casefolded), content = value unchanged, participant = the location; a
visible row gets a `location` default at that location, a hidden row gets
none. The table is dropped in v2.06.

### R-13 — the prose columns, where declared
Opened: `models/canon.py:117-142` (`Entity`), `:143-190` (`Character`),
`models/canon_faction.py:22-60` (`Faction`) [M].
Finding: `entity.description` (nullable) and `entity.is_public`;
`character.appearance`, `.backstory`, `.aversion`, `.secrets` (nullable);
`faction.internal_structure`, `.philosophy`, `.internal_tensions`,
`.scope`, `.goals`, `.aversion` (nullable). `faction.goals` carries a
`DORMANT` comment while `tick_context.py:303,637`, `creator.py:78`,
`crud/goals.py:260` and `npc_group_author.py:313` read it (trap: a
docstring is not the code).
Consequence: `faction.scope` stays (mechanic). The other twelve move.

### R-14 — creator write paths into those columns
Opened: `tooling/verify/canon_write_policy.txt`; `cockpit/crud/entities.py`;
`cockpit/routes/creator.py:640-690` [M].
Finding: policy `:89` `creator.py::create_player_character entity character
skill`; `:102` `crud/entities.py::_create_static_entity_core entity
character location faction item`; `:104` `crud/entities.py::update_entity
entity character location faction item`. `ENTITY_BASE_FIELDS`
(`crud/entities.py:116-122`) includes `description`; `_apply_base_fields`
(`:350-355`) `setattr`s each base field. Type field specs
(`:125-210`): character `appearance`, `backstory`, `aversion`, `secrets`
(`:139-142`); faction `internal_structure`, `philosophy`, `aversion`,
`internal_tensions` (`:178-185`). `_build_extension_kwargs` (`:357-375`)
keeps only spec fields and silently drops any other key.
`create_player_character` builds `Entity(description=…)` and
`Character(appearance=…, backstory=…)` directly (`creator.py:655-670`).
Consequence: E moves these fields out of the specs and into a `facets`
payload handled by C-05.

### R-15 — generator paths
Opened: `entity_author.py:45-93`, `:432-505`; `cockpit/routes/npc_agent.py:199-230`;
`cockpit/routes/regions.py:135-225`; `npc_group_author.py:389`;
`frontend/src/creation/generatePanel.svelte.js:44-110` [M].
Finding: `_TYPE_FIELDS` (`entity_author.py:45-93`) is the per-type JSON
guidance injected into the `entity_generation` prompt as `{type_fields}`;
drafts split `public` / `secret` (`:432-505`). Every server-side commit
calls `_crud._create_entity_core(EntityWriteBody(...))`: `npc_agent.py:226`
(maps `creator_meta` to `secrets` as JSON text, `:217`), `regions.py:170`
(factions), `regions.py:223` (locations). `regions.py:207-219` passes a
`subculture` key (with a `hidden` entry from `secret.subculture_hidden`)
into `ext_data`; the location field spec has no `subculture` field, so
`_build_extension_kwargs` drops it — **region-generated subculture is never
persisted today**. The frontend applies drafts into legacy DOM ids
(`generatePanel.svelte.js:44-72`, `setVal(legacyDoc, 'author-x-appearance', …)`)
and subculture rows into `subcultureDraftState` (`:84-110`, the hidden text
as key `hidden`, `is_hidden: true`).
Consequence: E carries generator output as `facets` (C-11); the region
subculture defect is fixed as a side effect and reported.

### R-16 — the sheet frontend
Opened: `frontend/src/creation/Sheet.svelte` (774 lines),
`SubcultureEditor.svelte` (93), `subcultureDraft.svelte.js` (14),
`generatePanel.svelte.js` (140), `sheetState.svelte.js` (141) [M].
Finding: base and type fields are read generically
(`Sheet.svelte:402-406`, `readFieldValue`); knowledge follows the
pending/existing pair `PendingKnowledgeEditor` (`:95`) / `KnowledgeEditor`
(`:104`); `SubcultureEditor` is imported at `:90`. `module_budget.py` R5
applies the 1000-line ceiling to `frontend/src/**/*.svelte|js`.
Consequence: F adds `FactsEditor.svelte` + `factsDraft.svelte.js` on the
same pending/existing pattern; `Sheet.svelte` gains only the mount.

### R-17 — encounter traces and their write points
Opened: `models/ephemeral.py:40-158`; `routes/scene.py:140-300`;
`gathering.py`; `cockpit/play.py:895-925`; `routes/play.py:118-135` [M].
Finding: `visit` (`ephemeral.py:144-158`, `present_npc_ids` JSON `:154`,
append-only per `checks/visit_delta.py` rule 1) is added once, at
`routes/scene.py:153-158` inside `enter_scene` (`:94`). `gathering.session_id` is NOT NULL
(`ephemeral.py:52`). `gathering_member` rows are added at
`gathering.py:254` (`generate_gatherings`, `:191`, one gathering per group,
NPC members), `:394` (`attach_on_arrival`, `:346`, solo gathering),
`:440` (`migrate_npc`, `:403`), `cockpit/play.py:916` (`_join_gathering`,
`:901`, the player). `conversation` (`ephemeral.py:84-100`, `player_id` NOT
NULL, `npc_id` nullable) is created at `routes/scene.py:217` and `:293`
(`npc_id=None`) and `routes/play.py:126` inside `start_conversation` (`:82`,
`npc_id=body.npc_id`).
Consequence: C records encounters at `scene.py` (visit), the four
membership sites (pairs among the gathering's open members), and
`routes/play.py:126`. `scene.py:217/293` carry no NPC and record nothing.

### R-18 — `npc_schedule`
Opened: `models/schedule.py:40-64`; `writes/config.py:462-539` [M].
Finding: one row per `(npc_id, phase)` (`idx_npc_schedule_npc_phase`
unique), `location_id` NOT NULL, no `change_history`; sole writer
`write_npc_schedule` (full replace per NPC, policy `:40`). Prod (Nia,
2026-09-22) [C]: 3 co-present pairs across two worlds, never more than 2
NPCs per `(location, phase)`.
Consequence: Q10a/Q11a — `write_npc_schedule` records a `schedule`
encounter for every other NPC sharing an exact `(location_id, phase)` with
the rows it writes.

### R-19 — `write_relation` and the lien fact
Opened: `writes/relations.py:123-294`; `relation_orientation.py:23-45` [M].
Finding: `write_relation` (`:220-294`) creates then flushes, then
`_birth_typed_fact` (`:133-147`) when `is_new` (`:285-292`). The function
body is about 75 lines (80 is the ceiling). `_endpoint_names` (`:123-130`)
returns the two names. `lien_fact_content(name_a, relation_type, name_b)`
(`relation_orientation.py:33-35`) returns
`f"{name_a} éprouve « {relation_type} » envers {name_b}."`;
`connects_to_fact_content` (`:38-41`). Both typed births pass through
`create_fact(relation_id=…)`.
Consequence: C adds the encounter in a helper called from the `is_new`
branch (not inline, to stay under 80 lines). A tags both typed births with
facet `lien`. J poses tokens in the lien content.

### R-20 — non-canon bookkeeping posture
Opened: `tooling/verify/canon_write_policy.txt:152-159`;
`models/ephemeral.py:136-141`;
`tooling/verify/checks/single_canon_write.py:1-30` [M].
Finding: `single_canon_write.py` gates only tables in `[CANON_TABLES]`;
`visit`, `gathering`, `conversation` and the observation telemetry tables
are deliberately outside it, each with its own chokepoint and, for
observation, its own check (`observation_socle.py`).
Consequence: `rencontre` (derived from play traces and authored state,
never edited by hand) and `unresolved_mention` (a worklist) are non-canon.
Each gets one writer module and a dedicated check (C-06, C-15).

### R-21 — budgets
Opened: AST count of top-level functions and `wc -l` on each file [M]
(pasted in gate (c)).
Finding: `context.py` 956 / 30; `link_author.py` 959 / 36;
`cockpit/crud/entities.py` 904 / 25; `cockpit/play.py` 997 / 28;
`entity_author.py` 846 / 29; `tick_context.py` 736 / 28;
`cockpit/routes/creator.py` 732 / 26; `knowledge_resolve.py` 304 / 10;
`writes/relations.py` 365 / 13; `gathering.py` 494 / 11; `routes/scene.py`
439 / 9; `routes/play.py` 716 / 14; `lore_selectors.py` 265 / 8;
`writes/config.py` 539 / 9; `writes/knowledge.py` 254 / 7; `Sheet.svelte`
774. Caps: 1000 lines, 40 functions (`checks/module_budget.py:57`).
Consequence: B moves code out of `context.py`, `link_author.py` and
`cockpit/play.py` before any brief adds to them (R-29 for what can move).

### R-22 — the Lore surface and its gates
Opened: `tooling/verify/checks/lore_isolation.py:1-60`;
`src/world_engine/lore_render.py:27-113`; `lore_selectors.py:187-265`;
`tooling/verify/checks/lore_selectors.py:5-26`;
`frontend/src/lore/Lore.svelte:1-30`; `cockpit/app.py:130` [M].
Finding: `lore_isolation.py` R1-R16 name only `lore_selectors.py`,
`lore_query.py`, `lore_render.py`, `lore_plan.py`, `lore_prompt.py` and
`cockpit/routes/lore.py` (R6: no `chat(`, no `select(`). `lore_render`'s
`_SECTION_FORMATTERS` (`:87-96`) is the closed section vocabulary; an
unknown section raises (`:99-113`). `entity_dossier` (`:187-199`) returns
identity, relations, knowledge, memberships, goals. `SELECTORS` (`:251`),
`_SELECTOR_LOOKUPS` (`:253-265`); `checks/lore_selectors.py` R6 requires
every `context_sections` string to be an emitted `"section"` literal.
`Lore.svelte` declares itself read-only (`:1-8`) and labels sections in
`SECTION_LABEL` (`:22-29`); 179 lines; `lore.svelte.js` 88 lines.
The Lore router is mounted at `cockpit/app.py:130`.
Consequence: H adds a `facets` section (formatter + label). K adds a
separate route module and panel; R1-R16 stay untouched; a new rule forbids
imports between the panel's modules and the consultation pipeline.

### R-23 — the world-scoped name resolver
Opened: `src/world_engine/lore_resolve.py:1-169` [M].
Finding: `_CATEGORY_ENTITY_TYPE = {"place": "location", "person":
"character", "faction": "faction"}` (`:28`); `normalize_surface(text)`
(`:42`); `rung_named_exact` (`:62`); `rung_named_token` (`:76`);
`resolve_named(surface_form, category, world_id, db) -> NamedResolution`
(`:112`); `validate_binding(entity_id, category, world_id, db)` (`:152`).
No model call; two or more candidates are reported, never picked.
Consequence: J reuses `normalize_surface` and `resolve_named` for
generator `mentions`; K reuses `resolve_named` to recompute candidates and
`validate_binding` before writing a token.

### R-24 — readers of `fact.content` and `knowledge.content`
**Corrected by AMENDMENT-0091-04**: the enumeration below filtered hits by
receiver name and was therefore incomplete; `scene_format.py:71,76` read
`discoverable_detail`, not `Knowledge` (out of scope). Lines have also
shifted since E, G, H and I. The authoritative list is the amendment's,
and BRIEF-J now requires a complete AST enumeration of `.content` before
any edit.
Opened: `grep -rn "\.content\b" src/world_engine` filtered to `Fact` and
`Knowledge` receivers [M] (pasted in gate (c)).
Finding: fact: `knowledge_resolve.py:299-300`, `cockpit/crud/_shared.py:264`,
`writes/facts.py:69,75`, `writes/relations.py:362` (`lien.content`);
knowledge: `context.py:121-122` (`_knowledge_line`), `tick_context.py:126`,
`scene_format.py:71,76`, `lore_selectors.py:155,233`,
`cockpit/crud/_shared.py:255`, `link_context.py:109`,
`writes/knowledge.py:98,178`. `analyzer_transcript.py:779` is a
`conversation_message` row — out. Other `.content` hits in `src/` are
`ctx.content`, `discoverable_detail.content` or message payloads — out.
Checks: `relation_orientation.py:156` compares `fact.content` to
`lien_fact_content`.
Consequence: J renames the model attribute to `content_raw` on both
models (SQL column name unchanged) so every reader is found by the
interpreter, then routes each through C-13.

### R-25 — no JSON column without an allow-list entry
Opened: `tooling/verify/checks/json_ui_boundary.py:1-25` [M].
Finding: volet c fails any `Column(JSON` not named in
`JSON_COLUMN_ALLOWLIST`.
Consequence: `rencontre` and `unresolved_mention` declare no JSON column;
candidates are recomputed at read time (C-16).

### R-26 — check fixtures that build facts
Opened: `tooling/verify/checks/fact_spine.py:1-140`,
`knowledge_resolution.py:78-146`, `known_reachability.py:178-240`,
`relation_orientation.py:150-160` [M]. FK enforcement: `db.py:126` [C].
Finding: `fact_spine.py` asserts (1) no participant on a typed fact, (2) no
knowledge with NULL `fact_id`, (3) level vocabulary, (4) AST: no
`db.add(Fact(...))` / `FactParticipant(...)` outside `writes/facts.py`;
fixture calls `create_fact` at `:138`. `knowledge_resolution.py:120`
calls `create_fact` and `:126-146` `create_fact_default` for the tier
fixture. `known_reachability.py:233` calls `create_fact_default`.
Consequence: A updates the two `create_fact` fixtures with a facet; D
extends `knowledge_resolution.py` with the new tiers; J updates
`relation_orientation.py:156`.

### R-27 — the cockpit has no request authentication
Opened: `grep -rn "Depends(" src/world_engine/cockpit | grep -v get_session`
(empty) [M]; `CLAUDE.md:525` (`http://127.0.0.1:8000`) [M].
Finding: no role check on any route; Creation writes are as open as Lore.
Consequence: K's panel is guarded exactly as Creation is. Route
authentication is a named deferral (ticket > 0091).

### R-28 — prod measurements carried
[C] 2026-09-14: 615 `knowledge` rows over 312 facts; 0087 backfill bound
98 rows / 69 subjects to participants. 2026-09-21: 0 groups of identical
free facts per world. 2026-09-22: see R-18. `entity` and `character` have no
`change_history`.

### R-29 — files and functions pinned by existing gates
Opened: `src/world_engine/traits.py:74`; `tooling/verify/checks/prompt_lean.py:8,28,77`;
`stream_session_readonly.py:12-14`; `json_ui_boundary.py:33`;
`known_reachability.py:315-330`; AST spans of the four budget files [M].
Finding: `traits.py:74` names `reader_callable="world_engine.context:_npc_context_identity"`.
`prompt_lean.py` rule 3 requires `_SAFE_SUBCULTURE_KEYS == ("values",)` in
`context.py`. `stream_session_readonly.py` documents `_join_gathering`
(`cockpit/play.py:901-926`) keeping its signature and its call sites
(`play.py:400`, `routes/scene.py:316`, `routes/play.py:239`).
`json_ui_boundary.py:33` reads the field registry from
`cockpit/crud/entities.py`. `known_reachability.py` lists
`cockpit/crud/entities.py` among modules spelling `"connects_to"`
(`_location_doors_rows`, `:302-347`). Spans: `context.py`
`_npc_context_setting` 327-356, `_npc_context_company` 449-475,
`_mj_context_co_presents` 770-797 (none uses a `context.py` top-level name);
`link_author.py` `_location_chain_names` 147-161 (sole caller `_npc_sheet`),
`_npc_sheet` 164-184 (sole callers `:235-236`); `cockpit/play.py`
`_propose_engine_discovery` 964-997 (uses only `ProposedMutation` among
module names; imported by `play_physical.py:53`); `cockpit/crud/entities.py`
`_create_entity_core` 545-560, `_create_static_entity_core` 563-634 (72
lines), `update_entity` 739-816 (78 lines).
`src/world_engine/schema_reconcile.py:30` defines `static_table_names()`.
Consequence: B moves only the unpinned spans above; `crud/entities.py`
moves nothing and its two long functions gain one-line calls only.

### R-30 — generator review surfaces
Opened: `frontend/src/creation/Region.svelte:119,591-645`;
`frontend/src/creation/npcAgent.svelte.js:303`;
`src/world_engine/npc_group_author.py:389-405`;
`frontend/src/creation/PjCreatePanel.svelte:50-51,96-97,120-121,129,180,184`;
`src/world_engine/cockpit/routes/npc_agent.py:213-217` [M].
Finding: `Region.svelte` binds `pub.subculture` (`:591`),
`sec.subculture_hidden` (`:603`), `pub.philosophy` (`:618`),
`pub.internal_structure` (`:620`), `pub.aversion` (`:641`),
`sec.internal_tensions` (`:645`). The NPC batch review patches one field at
a time (`npcAgent.svelte.js:303`, `{payload_patch: {[field]: value}}`),
validated by `_coerce_npc_patch_value` against `_NPC_PLAIN_STR_FIELDS =
("description", "appearance", "backstory", "aversion")`.
`PjCreatePanel.svelte` holds and posts `appearance` / `backstory`.
`npc_agent.py:217` stores `creator_meta` as JSON text in `secrets`.
Consequence (Q20b): the generator emits facet keys; these three review
surfaces keep one text field per facet, one line per affirmation; the
server splits by line (C-05). Only the sheet's generate panel edits facets
as lists (F).

### R-31 — the crud router and write timestamps
Opened: `src/world_engine/cockpit/crud/_router.py:12`;
`cockpit/crud/__init__.py:8-16,62-97`; `models/ephemeral.py:84-160` [M].
Finding: every `crud/<domain>.py` decorates the single
`router = APIRouter(prefix="/api", tags=["author-crud"])`; `crud/__init__.py`
imports each domain module (a re-export surface, no logic).
`conversation.started_at`, `visit.entered_at`, `gathering_member.joined_at`
/ `left_at`, `relation.created_at`, `npc_schedule.created_at` are the
timestamps available to the backfill.
Consequence: C-12 lives in a new `crud/facets.py` imported by
`crud/__init__.py`; C's backfill orders candidate pairs by those columns.

## Contract sheet

### C-01 — the facet registry (`src/world_engine/facets.py`, new)
Produced by: A   Consumed by: C, D, E, F (through C-12), G, H, I, J
```python
FAMILIES = ("identite", "interiorite", "collectif", "monde")
GRANULARITIES = ("bloc", "affirmation", "typed")
PRESETS = ("none", "world", "public_world", "location", "rencontre", "typed")

@dataclass(frozen=True)
class FacetSpec:
    name: str
    family: str          # in FAMILIES
    granularity: str     # in GRANULARITIES
    preset: str          # in PRESETS — default knowledge for NEW writing
    label: str           # French UI label
    description: str     # one French sentence: what belongs here
    aspects: tuple[str, ...] = ()   # known aspects, suggestion only

FACETS: dict[str, FacetSpec]        # insertion order = display order
DESCRIPTIVE_FACETS: frozenset[str]  # family in identite|interiorite|collectif
KNOWLEDGE_SECTION_FACETS: frozenset[str] = frozenset(
    {"information", "lien", "evenement", "loi"})
TYPED_FACET_BY_FK = {"relation_id": "lien", "event_id": "evenement",
                     "world_law_id": "loi"}

def facet_spec(name: str) -> FacetSpec        # ValueError if unknown
def normalize_aspect(raw: str | None) -> str | None  # strip+casefold; "" -> None
```
Verbatim table (name, family, granularity, preset, aspects):
| name | family | granularity | preset | aspects |
|---|---|---|---|---|
| appellation | identite | affirmation | location | () |
| statut | identite | affirmation | location | () |
| physique | identite | bloc | rencontre | () |
| tenue | identite | bloc | none | () |
| description | identite | bloc | public_world | () |
| reputation | identite | affirmation | location | () |
| histoire | interiorite | affirmation | none | () |
| personnalite | interiorite | affirmation | none | () |
| preference | interiorite | affirmation | none | () |
| aversion | interiorite | affirmation | none | () |
| doctrine | collectif | bloc | world | () |
| organisation | collectif | bloc | none | () |
| tension | collectif | affirmation | none | () |
| visee | collectif | affirmation | none | () |
| coutume | collectif | affirmation | location | ("values",) |
| information | monde | affirmation | none | () |
| lien | monde | typed | typed | () |
| evenement | monde | typed | typed | () |
| loi | monde | typed | typed | () |

Labels (verbatim): appellation "Appellations", statut "Statuts", physique
"Physique", tenue "Tenue", description "Description", reputation
"Réputation", histoire "Histoire", personnalite "Personnalité", preference
"Préférences", aversion "Aversions", doctrine "Doctrine", organisation
"Organisation", tension "Tensions", visee "Visées", coutume "Coutumes",
information "Informations", lien "Liens", evenement "Événements", loi "Lois".
Descriptions (verbatim): appellation "Un nom, surnom ou titre sous lequel
on désigne l'entité." ; statut "Une position sociale, une charge ou un rang
que l'entité occupe." ; physique "Ce que l'on voit durablement de l'entité :
corps, visage, allure." ; tenue "Ce que l'entité porte en ce moment et qui
peut changer." ; description "La présentation générale de l'entité." ;
reputation "Ce qui se dit de l'entité, vrai ou non." ; histoire "Un fait du
passé de l'entité." ; personnalite "Un trait de caractère de l'entité." ;
preference "Une chose que l'entité aime ou recherche." ; aversion "Une chose
que l'entité rejette, craint ou fuit." ; doctrine "Le credo affiché et les
valeurs revendiquées publiquement." ; organisation "La forme d'organisation
du groupe telle qu'on peut la connaître." ; tension "Une fracture, une
rivalité ou une faiblesse interne du groupe." ; visee "Un but que le groupe
poursuit réellement." ; coutume "Un usage, une valeur ou une règle de vie
propre au lieu." ; information "Une information détenue par quelqu'un." ;
lien "Un lien entre deux entités, porté par une relation." ; evenement "Un
événement du monde." ; loi "Une loi du monde." They are UI help and future
extractor vocabulary; no check reads them.
Preset semantics (C-05 applies them): `none` no default; `world` a `world`
default at `knows`; `public_world` a `world` default at `knows` only when
the subject entity `is_public`; `location` a `location` default at `knows`
on the subject itself when the subject is a location, otherwise none unless
the creator picks a location; `rencontre` a `rencontre` default at `knows`
with `scope_id` = the subject; `typed` never used by C-05.
Error cases: `facet_spec` of an unknown name raises `ValueError`.

### C-02 — `create_fact`, amended
Produced by: A   Consumed by: C-05, `writes/knowledge.py`, `writes/relations.py`
```python
def create_fact(db, *, world_id, content, created_by, facet, aspect=None,
                default_level="unaware", relation_id=None, event_id=None,
                world_law_id=None) -> Fact
```
`facet` is keyword-only with **no default**. Raises `ValueError` when:
`facet` is `None` ("NULL facet is reserved for facts predating
TICKET-0091"); `facet` not in `FACETS`; a typed FK is set and `facet` is not
`TYPED_FACET_BY_FK[that FK]`; no typed FK is set and `facet` has granularity
`typed`. `aspect` is stored through `normalize_aspect`. Everything else as
R-04.

### C-03 — `update_fact_content` (new, `writes/facts.py`)
Produced by: A   Consumed by: C-05, C-16
```python
def update_fact_content(db, *, fact, content, changed_by) -> Fact
```
Appends `{"content": <previous>, "changed_by": changed_by, "at": <iso UTC>}`
to `change_history` (same shape as `update_typed_fact_content`), flags it
modified, overwrites the content. Works on free and typed facts.
Declared in the policy (`fact`).

### C-04 — `delete_free_fact` (new, `writes/facts.py`)
Produced by: A   Consumed by: C-05
```python
def delete_free_fact(db, *, fact) -> None
```
Raises `ValueError` if any typed FK is set. Deletes, in this order, the
fact's `knowledge` rows, `fact_default` rows, `fact_participant` rows,
then the fact (FKs on; children before parent). Declared in the policy
(`fact fact_participant fact_default knowledge`), creator-CRUD only.

### C-05 — the entity-fact writer (`src/world_engine/writes/facets.py`, new)
Produced by: E (module), with `add_entity_fact` used by I's migration
logic only as a reference (I writes SQL)   Consumed by: C-12, E's cores, J
```python
@dataclass(frozen=True)
class ScopeChoice:
    scope_type: str            # "none"|"world"|"location"|"faction"|"rencontre"
    scope_id: str | None = None

def add_entity_fact(db, *, entity_id, facet, content, created_by,
                    aspect=None, scope: ScopeChoice | None = None) -> Fact
def write_entity_facets(db, *, entity_id, facets: dict, created_by) -> list[Fact]
def edit_entity_fact(db, *, fact_id, content, changed_by) -> Fact
def remove_entity_fact(db, *, fact_id) -> None
def facts_payload_keys() -> frozenset[str]   # descriptive facet names
```
`add_entity_fact`: facet must be in `DESCRIPTIVE_FACETS` (else
`ValueError`); empty/whitespace content raises; for a `bloc` facet, an
existing fact with this entity as participant, the same facet and the same
aspect raises `ValueError("bloc facet already has a fact")`;
`create_fact(facet=…, aspect=…)`, `attach_participants([entity_id])`, then
the default: `scope` when given (`none` writes nothing; `world` scope_id
None; others require scope_id), else the facet's preset (C-01). Default
level is always `knows`.
`write_entity_facets`: keys must be descriptive facet names or the
special key `creator_meta`; a `bloc` value is a `str`; an `affirmation`
value is a `list[str]` **or a `str`, split into one fact per non-empty
stripped line** (Q20b); `coutume` is a `list[{"aspect": str | None,
"content": str, "hidden": bool}]` where `hidden` means scope `none` and not
hidden means the preset. `creator_meta` (a `str`) becomes one `histoire`
fact with scope `none` plus one `knowledge` row written through
`write_knowledge(entity_id=<the entity>, fact_id=<that fact>,
subject="creator_meta", level="unaware", is_secret=True)` — the entity never
knows the creator's note (same shape as C-18's `character.secrets` row).
Empty strings are skipped. Returns the created facts in input order.
`edit_entity_fact`: refuses a fact whose facet is not descriptive;
delegates to C-03. `remove_entity_fact`: same refusal; delegates to C-04.
All four add rows and never commit.

### C-06 — the `rencontre` table (`models/ephemeral.py`)
Produced by: A   Consumed by: C, D
```python
class Rencontre(SQLModel, table=True):
    __tablename__ = "rencontre"
    # idx_rencontre_pair UNIQUE (entity_lo_id, entity_hi_id)
    # idx_rencontre_hi (entity_hi_id)
    id: str (uuid pk); world_id: str FK world NOT NULL
    entity_lo_id: str FK entity NOT NULL   # min(a, b) as strings
    entity_hi_id: str FK entity NOT NULL   # max(a, b)
    first_at: datetime NOT NULL
    source: str NOT NULL     # in ENCOUNTER_SOURCES
    source_ref: str | None   # id of the visit/gathering/conversation/relation row
ENCOUNTER_SOURCES = ("visit", "gathering", "conversation", "schedule", "relation")
```
One row per unordered pair; the earliest known encounter wins; never
updated, never deleted. No JSON column.

### C-07 — the encounter writer (`src/world_engine/encounters.py`, new)
Produced by: C   Consumed by: D, the live sites
```python
def record_encounter(db, *, world_id, a_id, b_id, source, at=None,
                     source_ref=None) -> Rencontre | None
def record_encounters_among(db, *, world_id, entity_ids, source, at=None,
                            source_ref=None) -> int
def record_gathering_join(db, *, gathering_id, joiner_id) -> int
def acquaintances(db, entity_id) -> set[str]
def have_met(db, a_id, b_id) -> bool
```
`record_encounter`: `a_id == b_id` returns `None`; `source` outside
`ENCOUNTER_SOURCES` raises `ValueError`; an existing pair returns `None`
(idempotent, read guard before add); else adds and returns the row. `at`
defaults to now (UTC). `record_encounters_among`: every unordered pair of
the distinct ids, returns the number of new rows. `record_gathering_join`:
reads the gathering's `world_id`, pairs `joiner_id` with every other member
whose `left_at IS NULL`, source `gathering`, `source_ref` = the gathering
id; returns the number of new rows. `acquaintances`: every entity id paired
with `entity_id` in `rencontre`. The only module that adds a `Rencontre`.

### C-08 — `fact_default` scope `rencontre`
Produced by: A (schema), D (meaning)   Consumed by: C-05, I
`scope_type = 'rencontre'`, `scope_id` = the entity whose acquaintances
know the fact at `level`. Allowed by the rebuilt
`ck_fact_default_scope_type IN ('world','faction','location','rencontre')`.

### C-09 — resolver, amended (`knowledge_resolve.py`)
Produced by: D   Consumed by: C-10, G, H, K
Precedence, most specific first:
1. stored `knowledge` row — wins outright;
2. **self**: the entity is a `fact_participant` of the fact AND
   `fact.facet in DESCRIPTIVE_FACETS` → `knows` (Q6a, Q18a);
3. **rencontre**: a `rencontre` default whose `scope_id` is in
   `acquaintances(entity)` → that level (highest if several);
4. nearest `location` default up the parent chain;
5. highest `faction` default across active memberships;
6. `world` default;
7. `fact.default_level`.
`resolve_knowledge_level` and `resolve_levels_for_entity` apply the same
order; `resolve_public_level(s)` unchanged (they enter at tier 6).
`resolve_default_rows` skips every fact whose `facet in
DESCRIPTIVE_FACETS` (NULL and `KNOWLEDGE_SECTION_FACETS` pass).

### C-10 — facet reads (`src/world_engine/facet_reads.py`, new)
Produced by: D   Consumed by: G, H, K
```python
@dataclass(frozen=True)
class FactRow:
    fact_id: str
    facet: str
    aspect: str | None
    content: str
    created_at: datetime

def facts_of(db, *, entity_id, facets: tuple[str, ...], aspect=None,
             notorious_at_location: str | None = None,
             include_creator_only: bool = False) -> list[FactRow]
def creator_only_fact_ids(db, fact_ids) -> set[str]
def known_facts_of(db, *, perceiver_id, entity_id, facets: tuple[str, ...],
                   aspect=None) -> list[FactRow]
def joined(rows: list[FactRow], sep: str = "\n") -> str | None
```
`facts_of`: facts with `entity_id` as participant and `facet in facets`
(and `aspect == normalize_aspect(aspect)` when given); with
`notorious_at_location`, only facts carrying a `location` default whose
`scope_id` equals it. **Creator-only facts are excluded by query
construction** unless `include_creator_only=True` (AMENDMENT-0091-01): a
fact is creator-only when a stored `knowledge` row on it belongs to one of
its own participants with `level = 'unaware'` and `is_secret = 1` — the
shape C-05 gives `creator_meta` and C-18 gives `character.secrets`.
`include_creator_only=True` is legal only in `lore_selectors.py` (the
creator's dossier). `creator_only_fact_ids`: the subset of `fact_ids` that
are creator-only, one query. Ordered by the order of `facets`, then `created_at`,
then `fact_id`. Empty list when none. `known_facts_of`: `facts_of`
(creator-only facts always excluded, no override) filtered to facts that `resolve_levels_for_entity(perceiver_id)` holds above
`unaware` (one batch call). `joined`: contents joined by `sep`, `None`
for an empty list. After J, `content` is rendered (C-13); before J it is
the raw text.

### C-11 — the entity write payload, amended (`cockpit/crud`)
Produced by: E   Consumed by: F, generators
`EntityWriteBody` gains `facets: dict | None = None` (shape of C-05's
`write_entity_facets`) and, from J, `mentions: list[dict] | None = None`
(`[{"name": str, "category": "place"|"person"|"faction"}]`). The
descriptive fields leave `ENTITY_BASE_FIELDS` (`description`) and the
type specs (`appearance`, `backstory`, `aversion`, `secrets`,
`internal_structure`, `philosophy`, `internal_tensions`). Create cores call
`write_entity_facets` after the entity row is flushed, in the same
transaction. `update_entity` with a non-empty `facets` returns 422 with
detail `"descriptive lore is edited through /api/entities/{id}/facts"`.
The PC-creation body of `create_player_character` loses `description`,
`appearance` and `backstory` and gains the same `facets` field.

### C-12 — facts CRUD routes (`src/world_engine/cockpit/crud/facets.py`, new)
Produced by: E   Consumed by: F
- `GET /api/facets` -> `{"facets": [{"name", "label", "family",
  "granularity", "preset", "aspects"}]}` (descriptive facets only, registry
  order).
- `GET /api/entities/{entity_id}/facts` -> `{"entity_id", "facts":
  [{"fact_id", "facet", "aspect", "content", "scopes": [{"scope_type",
  "scope_id", "level"}], "created_at"}]}`; 404 on unknown entity.
- `POST /api/entities/{entity_id}/facts` body `{"facet", "content",
  "aspect"?: str, "scope"?: {"scope_type", "scope_id"?}}` -> the created
  fact as one element of the GET list; 422 on `ValueError`.
- `PUT /api/facts/{fact_id}/content` body `{"content"}` -> the updated fact;
  404 unknown; 422 non-descriptive.
- `DELETE /api/facts/{fact_id}` -> `{"ok": true}`; 404; 422
  non-descriptive.
Each route commits once. Declared in the policy.

### C-13 — prose render (`src/world_engine/prose_render.py`, new)
Produced by: J   Consumed by: C-10, G, H, K, every fact/knowledge reader
```python
TOKEN_RE = re.compile(r"\[\[e:([0-9a-fA-F-]{36})\|([^\]|]*)\]\]")
def entity_token(entity_id: str, name: str) -> str   # strips "]" and "|" from name
def render(db, text: str | None) -> str | None
def render_many(db, texts: list[str | None]) -> list[str | None]
def fact_text(db, fact) -> str
def knowledge_text(db, k) -> str | None
```
`render`: each token becomes the entity's current `name`; an id with no
entity row becomes the token's stored name; text without tokens is
returned unchanged; `None` stays `None`. `render_many` issues one entity
query for all ids. `fact_text` renders `fact.content_raw`;
`knowledge_text` renders `k.content_raw`. The only module outside
`models/`, `writes/` and `knowledge_resolve.py` that reads `content_raw`.

### C-14 — token posing (`src/world_engine/prose_tokens.py`, new)
Produced by: J   Consumed by: C-05, `writes/knowledge.py`, `writes/relations.py`
```python
@dataclass(frozen=True)
class Unresolved:
    surface: str
    reason: str            # "ambigu" | "inconnu"
    category: str | None   # "place"|"person"|"faction" when known

@dataclass(frozen=True)
class Tokenized:
    text: str
    unresolved: tuple[Unresolved, ...]

def tokenize(db, *, world_id, text, mentions=None) -> Tokenized
```
Index = every active entity `name` of the world plus every `appellation`
fact content, each normalized with `lore_resolve.normalize_surface`.
Longest match first, whole words only, text already inside a token
skipped. A surface naming exactly one entity becomes `entity_token`; a
surface naming two or more stays plain and yields `Unresolved(reason=
"ambigu")`. Each `mentions` entry not found in the text by the index is
resolved with `resolve_named`: one candidate → its first occurrence in the
text is tokenized; zero → `Unresolved("inconnu", category)`; two or more →
`Unresolved("ambigu", category)`. Never calls a model.

### C-15 — `unresolved_mention` (`models/pipeline.py`) and its writer
Produced by: A (table), J (writer `writes/mentions.py`)   Consumed by: K
```python
class UnresolvedMention(SQLModel, table=True):
    __tablename__ = "unresolved_mention"
    # idx_unresolved_mention_world_open (world_id, resolved_at)
    id: str (uuid pk); world_id: str FK world NOT NULL
    fact_id: str | None FK fact
    knowledge_id: str | None FK knowledge
    surface: str NOT NULL
    reason: str NOT NULL          # "ambigu" | "inconnu"
    category: str | None
    created_at: datetime NOT NULL
    resolved_at: datetime | None
    resolved_entity_id: str | None FK entity   # NULL + resolved_at = dismissed
```
Exactly one of `fact_id`, `knowledge_id` is set (guarded in the writer).
No JSON column. Writer functions: `record_unresolved(db, *, world_id,
fact_id=None, knowledge_id=None, items: tuple[Unresolved, ...])`,
`resolve_mention(db, *, mention, entity_id)`, `dismiss_mention(db, *,
mention)`.

### C-16 — the name-resolution panel API (`cockpit/routes/lore_mentions.py`, new)
Produced by: K   Consumed by: K's frontend
- `GET /api/lore/mentions` -> `{"mentions": [{"id", "surface", "reason",
  "category", "excerpt", "owner": {"kind": "fact"|"knowledge", "id"},
  "candidates": [{"id", "name", "type"}]}]}` for the active world, open
  only, oldest first. `excerpt` = up to 80 rendered characters around the
  first plain occurrence of `surface`. Candidates recomputed with
  `resolve_named` (all three categories when `category` is NULL).
- `POST /api/lore/mentions/{id}/resolve` body `{"entity_id"}`: 404 unknown
  or already resolved; 422 when `validate_binding` fails for the category
  (any category when NULL); otherwise replaces the first plain occurrence
  of `surface` in the owner's raw text with `entity_token(entity_id,
  surface)` through `update_fact_content` (fact) or `write_knowledge`
  (knowledge), marks resolved, commits once.
- `POST /api/lore/mentions/{id}/dismiss`: marks resolved with no entity.

### C-17 — migration v2.05 (`scripts/migrate_v2_05_facets_encounters.py`)
Produced by: A   Consumed by: every later brief
One transaction. S1 `ALTER TABLE fact ADD COLUMN facet TEXT`; `ADD COLUMN
aspect TEXT`. S2 facet of typed facts: `lien` where `relation_id` NOT NULL,
`evenement` where `event_id`, `loi` where `world_law_id`; free facts stay
NULL. S3 rebuild `fact_default` with the widened CHECK, rows copied
identically, indexes re-created. S4 `CREATE TABLE rencontre` + indexes.
S5 `CREATE TABLE unresolved_mention` + index. S6 report (counts per
facet, rows copied). S7 post-checks (row count of `fact_default` equal
before/after; no typed fact with NULL facet). S8 `_converge_schema_meta()`
to `v2.05`. Idempotent; a second run prints zeros.

### C-18 — migration v2.06 (`scripts/migrate_v2_06_lore_as_facts.py`)
Produced by: I
One transaction. For each filled column (trimmed non-empty), one fact,
text unchanged (L2), `created_by = 'migrate_v2_06'`, one participant:

| source | facet | aspect | default |
|---|---|---|---|
| `entity.description` | description | — | `world`/`knows` if `entity.is_public` |
| `character.appearance` | physique | — | `rencontre`/`knows`, scope_id = the character |
| `character.backstory` | histoire | — | none |
| `character.aversion` | aversion | — | none |
| `character.secrets` | histoire | — | none, plus one `knowledge` row: entity = the character, `level='unaware'`, `is_secret=1`, `subject='creator_meta'` |
| `faction.philosophy` | doctrine | — | `world`/`knows` |
| `faction.internal_structure` | organisation | — | none |
| `faction.internal_tensions` | tension | — | none |
| `faction.goals` | visee | — | none |
| `faction.aversion` | aversion | — | none |
| `location_subculture` row | coutume | `lower(trim(key))` | `location`/`knows` at `location_id` if `is_hidden = 0`, else none |

Then `ALTER TABLE ... DROP COLUMN` for the twelve columns, `DROP TABLE
location_subculture`, the D3b' control query (groups of free facts with
identical `(world_id, facet, content)` among facts created by this
migration; printed; the script does not merge), report, post-checks (one
fact per filled source cell), `_converge_schema_meta()` to `v2.06`.
Idempotent: a source cell whose fact already exists (`created_by =
'migrate_v2_06'`, same participant, facet, aspect, content) is skipped;
the DROPs are guarded by `PRAGMA table_info` / `sqlite_master`.

## Gate output

### (a) Property trace

| property asserted in the lot | finding | declaring file opened |
|---|---|---|
| `fact` has no facet/aspect column | R-01 | models/canon_knowledge.py |
| `fact_default.scope_type` closed by CHECK to three values | R-02 | models/canon_knowledge.py |
| shape CHECK already admits a non-world scope with scope_id | R-02 | models/canon_knowledge.py |
| no migration rebuilds a table | R-03 | scripts/migrate_v2_0*.py (grep) |
| version constant `v2.04` | R-03 | schema_version.py |
| `create_fact` signature, no facet | R-04 | writes/facts.py |
| `update_typed_fact_content` history shape | R-04 | writes/facts.py |
| no free-fact update/delete path | R-04 | writes/facts.py (whole file) |
| five `create_fact` callers | R-05 | grep over src, scripts, checks |
| `(fact_id, entity_id)` unique on participants | R-06 | models/canon_knowledge.py |
| resolver tier order and default-row construction | R-07 | knowledge_resolve.py |
| three consumers of `resolve_default_rows` | R-08 | grep over src |
| each context/tick reader line | R-09, R-10 | context.py, tick_context.py |
| each remaining reader line | R-11 | each named file |
| gate pins on moved/kept functions | R-29 | traits.py, prompt_lean.py, stream_session_readonly.py, json_ui_boundary.py, known_reachability.py |
| review-surface field bindings | R-30 | Region.svelte, npcAgent.svelte.js, npc_group_author.py, PjCreatePanel.svelte |
| crud router prefix and aggregation | R-31 | crud/_router.py, crud/__init__.py |
| subculture key unique per location, is_hidden | R-12 | models/canon.py |
| single subculture writer and caller | R-12 | writes/config.py + grep |
| prose columns and `faction.scope` | R-13 | models/canon.py, models/canon_faction.py |
| `faction.goals` read despite DORMANT comment | R-13 | tick_context.py, creator.py, crud/goals.py, npc_group_author.py |
| creator write sites and table sets | R-14 | canon_write_policy.txt |
| `_build_extension_kwargs` drops unknown keys | R-14 | cockpit/crud/entities.py |
| region subculture never persisted | R-15 | cockpit/routes/regions.py + cockpit/crud/entities.py |
| generator commits go through `_create_entity_core` | R-15 | npc_agent.py, regions.py |
| sheet pending/existing editor pattern | R-16 | Sheet.svelte |
| encounter write points | R-17 | routes/scene.py, gathering.py, cockpit/play.py, routes/play.py |
| visit append-only | R-17 | checks/visit_delta.py (named rule) |
| schedule uniqueness and sole writer | R-18 | models/schedule.py, writes/config.py |
| `write_relation` birth branch and length | R-19 | writes/relations.py |
| lien content template | R-19 | relation_orientation.py |
| non-canon tables are outside the canon check | R-20 | checks/single_canon_write.py, canon_write_policy.txt |
| line and function counts | R-21 | AST/wc over each file |
| lore gates cover only the named modules | R-22 | checks/lore_isolation.py |
| closed section vocabulary raises | R-22 | lore_render.py |
| `context_sections` rule | R-22 | checks/lore_selectors.py |
| resolver function signatures | R-23 | lore_resolve.py |
| content readers | R-24 | grep over src |
| JSON allow-list | R-25 | checks/json_ui_boundary.py |
| check fixtures calling the writers | R-26 | each named check |
| no route authentication | R-27 | grep over cockpit + CLAUDE.md |

Presupposition sweep: no brief says "follow the existing convention" or
"as elsewhere"; each pattern invoked names its file (pending/existing
editors → R-16; 0087 script precedent → `scripts/apply_ticket_0087_subject_participants.py`,
opened for its name and write call at `:115` only; migration shape →
R-03).

### (b) Case tables

**C-02 `create_fact` validation** (facet × typed FK):
| facet | relation_id | event_id | world_law_id | outcome |
|---|---|---|---|---|
| None | any | any | any | ValueError (reserved) |
| unknown | any | any | any | ValueError |
| lien | set | – | – | ok |
| lien | – | – | – | ValueError (typed facet on free fact) |
| evenement | – | set | – | ok |
| loi | – | – | set | ok |
| information / descriptive | – | – | – | ok |
| information / descriptive | set (any) | | | ValueError (mismatch) |
| evenement | set | – | – | ValueError (mismatch) |

**C-05 preset application** (preset × subject):
| preset | subject | written default |
|---|---|---|
| none | any | none |
| world | any | world/knows |
| public_world | is_public | world/knows |
| public_world | not public | none |
| location | location entity | location/knows at itself |
| location | other entity | none |
| rencontre | any | rencontre/knows at itself |
| typed | — | unreachable: `add_entity_fact` refuses non-descriptive facets |
An explicit `scope` replaces the preset in every row.

**C-09 tiers** (first match wins; each row reachable in D's fixture):
| case | stored | participant & descriptive | acquaintance default | location | faction | world | result |
|---|---|---|---|---|---|---|---|
| 1 | unaware | yes | yes | yes | yes | yes | unaware |
| 2 | – | yes | – | – | – | – | knows |
| 3 | – | participant, facet `information` | – | – | – | – | default_level |
| 4 | – | – | yes (partial) | knows | – | – | partial |
| 5 | – | – | – | knows | – | – | knows |
| 6 | – | – | – | – | rumor | – | rumor |
| 7 | – | – | – | – | – | suspicious | suspicious |
| 8 | – | – | – | – | – | – | default_level |
| 9 | – | – | default exists, not acquainted | – | – | – | default_level |

**C-09 default-row filter**: facet NULL → kept; `information`, `lien`,
`evenement`, `loi` → kept; any of the fifteen descriptive facets → skipped.

**C-14 tokenize outcomes**: surface → 1 entity: token; → 2+: plain +
ambigu; in mentions, not in index, `resolve_named` 1: token at first
occurrence; 0: inconnu; 2+: ambigu; mention name absent from the text:
recorded as inconnu only if `resolve_named` returns 0, else ignored.

**C-16 resolve**: unknown id → 404; resolved → 404; binding invalid → 422;
surface no longer present in raw text → 409 with detail "surface no longer
in text", mention left open; otherwise token written, 200.

**C-18 per source** — the table in C-18 is the case table (one row per
source column, every source reachable from R-13/R-12).

### (c) Enumerations

```
$ grep -n "_rebuild\|RENAME" scripts/migrate_v2_0*.py
(no output)

$ grep -rn "create_fact(\|create_fact_default(\|attach_participants(" src scripts --include=*.py | grep -v "def create_fact\|def attach\|writes/facts.py"
src/world_engine/writes/knowledge.py:147:        attach_participants(db, fact=fact, entity_ids=[entity_id])
src/world_engine/writes/knowledge.py:193:        fact = create_fact(
src/world_engine/writes/relations.py:144:    return create_fact(
src/world_engine/cockpit/crud/knowledge.py:254:        attach_participants(db, fact=fact, entity_ids=[body.entity_id], role=body.role)
src/world_engine/cockpit/crud/knowledge.py:333:    row = create_fact_default(
scripts/apply_ticket_0087_subject_participants.py:115:        attach_participants(db, fact=fact, entity_ids=[entity_id])
scripts/seed_pilot.py:117:            fact = create_fact(

$ grep -ln "create_fact(\|create_fact_default(" tooling/verify/checks/*.py
fact_spine.py  knowledge_resolution.py  known_reachability.py

$ grep -rn "resolve_default_rows" src --include=*.py | grep -v "def resolve"
src/world_engine/tick_context.py:35:    resolve_default_rows,
src/world_engine/tick_context.py:252:    knowledge = knowledge + resolve_default_rows(
src/world_engine/context.py:50:from .knowledge_resolve import resolve_default_rows
src/world_engine/context.py:384:    knowledge = knowledge + resolve_default_rows(
src/world_engine/context.py:732:    knowledge_rows = knowledge_rows + resolve_default_rows(

$ grep -rn "write_location_subculture(" src --include=*.py
./writes/config.py:104:def write_location_subculture(
./cockpit/crud/entities.py:864:        write_location_subculture(

$ grep -rn "Visit(\|Conversation(\|GatheringMember(" src --include=*.py | grep -v "models/\|select("
./cockpit/play.py:916:        db.add(GatheringMember(
./cockpit/routes/scene.py:153:        db.add(Visit(
./cockpit/routes/scene.py:217:    new_conv  = Conversation(
./cockpit/routes/scene.py:293:    conv = Conversation(
./cockpit/routes/play.py:126:    conv = Conversation(
./gathering.py:254:            db.add(GatheringMember(
./gathering.py:394:    db.add(GatheringMember(
./gathering.py:440:    db.add(GatheringMember(

$ grep -rn "Depends(" src/world_engine/cockpit --include=*.py | grep -v get_session
(no output)

Budgets (lines / top-level functions):
context.py 956 30 | link_author.py 959 36 | cockpit/crud/entities.py 904 25
cockpit/play.py 997 28 | entity_author.py 846 29 | tick_context.py 736 28
knowledge_resolve.py 304 10 | writes/relations.py 365 13 | gathering.py 494 11
cockpit/routes/scene.py 439 9 | cockpit/routes/play.py 716 14
lore_selectors.py 265 8 | cockpit/routes/creator.py 732 26
writes/config.py 539 9 | writes/knowledge.py 254 7 | Sheet.svelte 774
```

Readers of the moving columns (the `.attr` enumeration behind R-09 to
R-11; `entity_author.py` and `crud/entities.py` field specs are writers):
```
$ grep -rn "\.appearance\b\|\.backstory\b\|\.secrets\b\|\.philosophy\b\|\.internal_structure\b\|\.internal_tensions\b\|\.aversion\b" src/world_engine --include=*.py | grep -v models/
tick_context.py:179,180,181,182,183,184,302,304,305,364,628,629,638,639
lore_selectors.py:62,63,64,94,95,96
cockpit/crud/goals.py:306
cockpit/routes/creator.py:309,314
gathering.py:96
link_author.py:178,179,180
context.py:234,235,236,237,238,239,471
```
AST enumeration of attribute access on the moving names (outside `models/`):
```
tick_context.py:179-184 npc_char.appearance/backstory/aversion
tick_context.py:302-305 faction.philosophy/goals/internal_tensions/aversion
tick_context.py:364 other_char.appearance
tick_context.py:628-629 faction.philosophy ; :637-639 faction.goals/internal_tensions/aversion
lore_selectors.py:62-64 faction.philosophy/internal_structure/internal_tensions
lore_selectors.py:94-96 character.appearance/backstory/aversion
npc_group_author.py:313 faction.goals
gathering.py:96 char.appearance
link_author.py:178-180 character.appearance/backstory/aversion
context.py:234-239 npc_char.appearance/backstory/aversion ; :471 co_char.appearance
cockpit/crud/goals.py:260 faction.goals ; :306 char.backstory
cockpit/routes/creator.py:78 faction.goals ; :309 faction.philosophy ; :314 character.backstory
cockpit/routes/creator.py:669-670 body.appearance / body.backstory
```
Every reference to the subculture table, its writer, its row helper and its
allow-list (AMENDMENT-0091-02; models excluded):
```
$ grep -rn "LocationSubculture\|location_subculture\|subculture_rows\|_SAFE_SUBCULTURE_KEYS\|_location_subculture_rows" src tooling/verify frontend/src scripts
readers:   context.py:348-351 (now context_describe.py), :706-713 ; tick_context.py:326-329, :562-565
           room_batch_author.py:100-113 ; cockpit/play_physical.py:725-734
payload:   cockpit/crud/entities.py:266-273, :517, :719, :805, :877 ; cockpit/crud/entity_geometry.py:28, :113, :143
           cockpit/crud/__init__.py:69, :82, :93
writer:    writes/config.py:104-150 ; writes/__init__.py:50 ; scripts/seed_pilot.py:29, :246-269, :3064
allow-list: context.py:102 ; entity_author.py:24, :67, :270-281 ; cockpit/play_physical.py:20
            cockpit/routes/mutations.py:45 ; tooling/verify/checks/prompt_lean.py:76-77
imports only: cockpit/crud/{ledger,prompts,goals,knowledge,factions,skills,events,agendas,relations,locations,entities}.py
              (LocationSubculture + write_location_subculture) ; cockpit/routes/mutations.py:74
policy/docs: canon_write_policy.txt:5, :30 ; checks/single_canon_write.py:71,76
frontend:  Sheet.svelte:477, :672 ; SubcultureEditor.svelte ; subcultureDraft.svelte.js
```
Entity `.description` receivers were enumerated by receiver name and each
hit classified (R-09, R-11); `Event`, `NpcGoal`, `FactionRole`,
`SkillDefinition` and `World` receivers are out of scope.

### (d) Family contracts
- Writers family (C-02, C-03, C-04, C-05, C-07, C-15 writer): written before
  members; re-read after C-15 — each takes `db` first, keyword-only after,
  adds without committing, raises `ValueError` on refusal. ✔
- Readers family (C-09, C-10, C-13): re-read after C-13 — each is a read,
  never `db.add`, `None`/empty handled explicitly. ✔
- Routes family (C-12, C-16): re-read — each commits once, 404/422 shapes
  identical, `ValueError` → 422. ✔

### (e) Check satisfaction

Gates proposed by this lot:
- `checks/fact_facets.py` (A, extended in D and E). Rules: R1 `FACETS`
  matches the C-01 table exactly (names, family, granularity, preset,
  aspects); R2 every `create_fact(` call in `src/` and `scripts/` passes a
  `facet=` keyword; R3 a `create_fact(` whose `facet=` is a descriptive
  literal or a non-literal appears only in `writes/facets.py`; R4 fixture:
  C-02's case table; R5 fixture: bloc guard refuses a second fact (E);
  R6 fixture: `resolve_default_rows` skips descriptive facts (D);
  R7 AST: a keyword `include_creator_only` whose value is not the literal
  `False` appears only in `lore_selectors.py`; R8 fixture: a creator-only
  fact is absent from `facts_of` and `known_facts_of`, present with
  `include_creator_only=True` (AMENDMENT-0091-01, landed in G).
  Satisfied by: `facets.py`, `writes/facts.py`, `writes/facets.py`,
  `writes/knowledge.py` (literal `information`), `writes/relations.py`
  (literal `lien`), `scripts/seed_pilot.py` (literal `information`).
  Needs nothing the check forbids: the knowledge and relation paths pass
  literals outside the descriptive set.
- `checks/encounter_registry.py` (C). R1 AST: no `Rencontre(` outside
  `encounters.py` and `scripts/apply_ticket_0091_encounters.py`; R2 no
  `.delete(` / `UPDATE rencontre` / `DELETE FROM rencontre` anywhere in
  `src/`; R3 each named live function calls one of `record_encounter`,
  `record_encounters_among`, `record_gathering_join`:
  `routes/scene.py::enter_scene` (`:94`), `gathering.py::generate_gatherings`,
  `gathering.py::migrate_npc`, `cockpit/play.py::_join_gathering` (stays in
  `play.py`, R-29), `routes/play.py::start_conversation` (`:82`), `writes/config.py::write_npc_schedule`,
  `writes/relations.py` birth helper; R4 fixture: idempotent pair, self
  pair ignored. Satisfied by `encounters.py` plus those call sites.
- `checks/lore_as_facts.py` (I). R1 AST: no `ast.Attribute` whose `attr`
  is one of `appearance`, `backstory`, `secrets`, `philosophy`,
  `internal_structure`, `internal_tensions`, `aversion`, `goals` anywhere in
  `src/` outside `models/` (the AST enumeration in (c) shows every current
  receiver is a `Character`/`Faction` row or the PC-creation `body`, which E
  replaces by `facets`); R2 identifier `LocationSubculture` absent from
  `src/`; R3 the twelve columns absent from the model classes (AST of
  `models/`); R4 identifier `_SAFE_SUBCULTURE_KEYS` absent. Satisfied by E,
  G and H having switched every reader and writer, and by E's PC body
  change.
- `checks/identity_tokens.py` (J). R1 identifier `content_raw` appears only
  in `models/canon_knowledge.py`, `writes/*.py`, `prose_render.py`,
  `knowledge_resolve.py`, `scripts/migrate_*.py`; R2 fixture: render of a
  token, of a renamed entity, of a deleted entity (fallback), of plain
  text; R3 fixture: C-14 case table; R4 `prose_tokens.py` contains no
  `chat(`. Satisfied by `prose_render.py`, `prose_tokens.py`,
  `writes/mentions.py`.
- `lore_isolation.py` R17 (K): `cockpit/routes/lore_mentions.py` and
  `lore_mentions_read.py` import none of `lore_selectors`, `lore_query`,
  `lore_plan`, `lore_render`, `lore_prompt`; and those five import
  neither. Satisfied by K's two modules.

Gates this lot must pass, and the module that satisfies each:
- `single_canon_write.py`: every new canon write site declared —
  `writes/facts.py::update_fact_content fact`,
  `writes/facts.py::delete_free_fact fact fact_participant fact_default knowledge`,
  the `writes/facets.py` functions only call chokepoints (no `.add` of their
  own), `cockpit/crud/facets.py` routes call C-05 only, K's route calls
  C-03 / `write_knowledge`. Removal of `write_location_subculture` from the
  policy in I.
- `fact_spine.py`: fixture updated in A (facet `information`).
- `knowledge_resolution.py`: extended in D (C-09 table).
- `relation_orientation.py`: `:156` updated in J (compares rendered text).
- `module_budget.py`: B creates the headroom (R-21, R-29).
- `prompt_lean.py`: rule 3 pins `_SAFE_SUBCULTURE_KEYS == ("values",)` in
  `context.py` (R-29); I replaces it by an assertion on
  `FACETS["coutume"].aspects == ("values",)`.
- `trait_reader.py` / `traits.py:74`: `_npc_context_identity` stays in
  `context.py` (R-29).
- `stream_session_readonly.py`: `_join_gathering` keeps its place and
  signature (R-29).
- `function_length.py`: `write_relation` gets a helper, not inline lines
  (R-19).
- `json_ui_boundary.py`: no JSON column added (R-25).
- `visit_delta.py`: C adds no UPDATE/DELETE on `visit`.
- `lore_selectors.py` R6: H emits `"section": "facets"` in
  `lore_selectors.py`.
- `schema_version_agreement.py`: A and I bump constant, doc and changelog
  together.
- `frontend_build_fresh.py` + `static_asset_freshness.py`: F and K rebuild
  and commit the bundle.
- `corpus_gate.py`: every brief.

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0091-05 | J | `scripts/seed_pilot.py::upsert_knowledge` reads and writes raw knowledge content outside `writes/`; moved into `writes/knowledge.py::upsert_knowledge_row` (seed text not tokenized); seed customs compare rendered text; readers in `scripts/` and checks listed. | J |
| AMENDMENT-0091-04 | J | R-24 incomplete (receiver-name filter): four readers missed (`crud/facets.py`, `context.py` PC knowledge, two in `link_author.py`), one false positive (`scene_format.py`), anchors shifted by E/G/H/I. The `link_author.py` merge-and-write moves into `writes/knowledge.py` (option b). | J |
| AMENDMENT-0091-03 | I | Item 3 told the seed to write every custom as not hidden; the seed's `Dernier Verre` has a hidden entry, which would have received a `location` default (hidden-custom trap). The entry's own `is_hidden` now decides, as in C-18. | I |
| AMENDMENT-0091-02 | H | R-12 missed a subculture reader (`play_physical.py:725-734`), two `subculture_rows` sites (`entity_geometry.py:113,143`), a re-export, import-only references and the seed writer; H and I anchors drifted after E. | H, I |
| AMENDMENT-0091-01 | G | C-10 `facts_of` read `histoire` without excluding the creator's note (C-05 `creator_meta`, C-18 `character.secrets`); G's tick identity and link sheet leaked it into prompts, and H's agenda and goal backfill would have too. C-10 now excludes creator-only facts by query construction; opt-in only in `lore_selectors.py`; `fact_facets.py` R7-R8. | D (copy, already landed), G, H |
