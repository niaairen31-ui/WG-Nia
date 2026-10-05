# LOT — TICKET-0105 "A fact once learned is kept, in the version learned, until the next contact"

## Objective and cut

A fact known through a place, an encounter or a faction is learned by a
contact made after it was written, and kept: leaving the place, the person
or the group forgets nothing (B5, J2). What is kept is the version learned:
when the creator rewrites a fact as a change in the world, whoever knew it
keeps the old text until their next contact with one of the fact's anchors;
a correction reaches everyone at once (G1, N1). Two registries carry the
dates — `passage` (per character and place) and `rencontre.last_at` — and
resolution stays a read. The creator says, at every rewrite, whether it is a
correction or a change (H1). The outfit becomes learnable and visible in
the scene (V1). The Lore dossier marks an old version (K1).

The lot stops before: showing in the dossier what a character knows only by
default, refreshing a stored row that has its own text, any change to the
Lore prompts, and any new Play surface (Mes savoirs reads the readers this
lot versions).

## Briefs in this lot

- **A — schema v2.14**: `passage`, `rencontre.last_at`, `tenue` presets
  `rencontre`, `migrate_v2_14_passage.py`, the world cascade; check
  `fact_learning.py` is created (A1-A2).
- **B — capture the contacts** (no schema change): `passages.py` (sole
  writer, `before_flush` listener), `encounters.record_encounter` moves
  `last_at`, `write_npc_schedule` records its passages (B1-B4).
- **C — the kind of a rewrite** (no schema change): `kind` required on the
  three rewrite functions, every caller names it, `fact_versions.py`,
  `prose_render.fact_texts_at` (C1-C3).
- **D — resolution dated by contact** (no schema change):
  `knowledge_resolve.py` rewritten around `Known(level, as_of)`; the
  existing resolution check follows C1 and B5 (D1-D2).
- **E — the readers give the version known** (no schema change):
  `resolve_default_rows`, `facet_reads.versioned` / `known_fact_texts`,
  day choice, NPC/MJ/tick contexts; the outfit in the scene (E1-E3).
- **F — the creator picks the kind** (no schema change):
  `FacetSpec.edit_kind`, the fiche route and editor, the Lore draft, panel
  and apply; rebuilt `static/` (F1-F3).
- **G — the dossier marks an old version** (no schema change):
  `lore_selectors._stale_label` (G1).

## Dependency graph

Strictly sequential, A → B → C → D → E → F → G.

- B writes the registries A creates.
- D reads A's registries as B fills them, and C's `fact_versions.utc`.
- E calls D's `resolve_known_for_entity` and C's `fact_texts_at`.
- F passes the kinds C requires; C passes `correction` meanwhile.
- G calls D's `resolve_knowledge` and C's `fact_is_stale`.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/fact_learning.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`.
- A creates `fact_learning.py` because every Machine arrow of the ticket
  must resolve from `brief` status on (`pipeline_state.py`).

## RECON

Opened on `main` at `e1097b5` (merge of PR #135, `ticket/0104`), schema
v2.13. Then prototyped on a copy (branch `proto/0105`): every brief's commit
ran the full corpus green (137/137 on `main`, 138/138 from A on, with
`WORLD_ENGINE_ENV=test`), and the seven diffs replayed in order on a clean
worktree of `main` reproduce the prototype tree exactly (generated files —
the decision index and the built frontend — regenerated). Findings tagged
[M] were measured.

### R-01 — where a character's place is written [M]
Opened: enumeration E1; `src/world_engine/writes/characters.py:28-50`
(`write_character_location`); `src/world_engine/cockpit/play_stream.py:471`;
`src/world_engine/cockpit/routes/creator.py:680-686`;
`src/world_engine/cockpit/crud/entities.py:344-347` (`_PLACEMENT_FIELDS`),
`:642`, `:805`; `src/world_engine/models/canon.py:143-168` (`Character`:
`world_id`, `current_location_id`).
Finding: six paths write `current_location_id` — travel (direct
assignment), the tick's NPC move and zone promotion (through
`write_character_location`), PC creation (constructor keyword), and the
fiche and batch creators (`ext_model(**ext_kwargs)` and `setattr`). No raw
SQL writes it. `Character` carries its own `world_id`.
Consequence: one `before_flush` listener sees every one of them, including
the two no static scan can (P1); it reads the attribute history for the
place left.

### R-02 — the encounter registry [M]
Opened: `src/world_engine/models/ephemeral.py:156-183` (`Rencontre`,
`ENCOUNTER_SOURCES`); `src/world_engine/encounters.py:1-132`; enumeration
E2.
Finding: one row per unordered pair; `record_encounter` returns `None` and
writes nothing when the pair exists (`:57-58`); `first_at` is the earliest
encounter. Seven live sites call the three recorders: scene visit,
gathering creation and migration, conversation start, gathering join,
schedule co-presence, social relation birth (`writes/relations.py:222-230`).
Consequence: `last_at` is added; an existing pair's `last_at` moves forward
on every source but `relation` (L1). `record_encounter`'s return contract is
kept.

### R-03 — schedules name places without moving anyone [M]
Opened: `src/world_engine/models/schedule.py:32-60` (`NpcSchedule`);
`src/world_engine/writes/config.py:413-512` (`write_npc_schedule`: DELETE at
`:478`, `_record_schedule_encounters` at `:491`);
`src/world_engine/schedule_reads.py:116-161` (`where_is`, `who_is_at`:
position computed at read time).
Finding: a schedule never writes `current_location_id`; an NPC "at the forge
each evening" is never placed there. `write_npc_schedule` is at the
80-line ceiling, and `npc_schedule.py` requires its DELETE inside it;
`single_canon_write.py` allows `npc_schedule` writes only from it.
Consequence: the schedule's passages are recorded by a helper called before
the DELETE (old rows still readable), which also records the encounters;
read time treats schedule places and slot co-presence as a contact right
now.

### R-04 — visits [M]
Opened: `src/world_engine/models/ephemeral.py:134-154` (`Visit`, plain
`DateTime` `entered_at`); `src/world_engine/cockpit/routes/scene.py:150-160`.
Finding: a `visit` row is written only when a player enters a scene; it is
append-only.
Consequence: the migration backfills a player's passage from the latest
`entered_at` per place; nothing else reads `visit` here.

### R-05 — resolution on `main` [M]
Opened: `src/world_engine/knowledge_resolve.py:1-363`.
Finding: seven tiers — stored row, self (participant of a descriptive
fact), `rencontre` (any acquaintance, no date), `location` (current place
and ancestors, NEAREST wins), `faction` (ACTIVE memberships, highest),
`world`, `fact.default_level`. `resolve_default_rows` builds transient rows
with the fact's current text. Resolution never writes.
Consequence: D replaces tiers 3-5 with dated contacts (B5, C1, J2) and adds
`as_of`; the public-floor functions keep tiers 6-7 only.

### R-06 — fact rewrites [M]
Opened: `src/world_engine/writes/facts.py:105-157` (`update_fact_content`,
`update_typed_fact_content`: history entry `{content, changed_by, at}`,
`at` an aware ISO string); `src/world_engine/writes/facets.py:363-377`
(`edit_entity_fact`, which calls `update_fact_content` even when the text
is unchanged); `src/world_engine/writes/relations.py:233-262`
(`_refresh_lien_content`, `_refresh_map_content`); enumeration E3.
Finding: seven call sites, none naming what the rewrite is.
Consequence: `kind` becomes a required keyword of all three functions;
each caller names it (U1); C passes `correction` from the two creator
surfaces until F.

### R-07 — fact deletion [M]
Opened: `src/world_engine/writes/facts.py:121-139` (`delete_free_fact`).
Finding: it deletes the fact's knowledge, defaults and participants, then
the fact.
Consequence: I1 holds as is; nothing in this lot touches deletion.

### R-08 — who reads a fact as someone knows it [M]
Opened: enumeration E4; `src/world_engine/facet_reads.py:108-123`
(`known_facts_of`); `src/world_engine/day_choice.py:77-101`;
`src/world_engine/context.py:125-137` (`_row_fact_texts`,
`_knowledge_line`), `:352-380`, `:680-697`;
`src/world_engine/tick_context.py:262-290`;
`src/world_engine/context_describe.py:55-127`.
Finding: the text of a fact reaches a holder through: default rows
(`resolve_default_rows`), `known_facts_of` (self identity, co-present
physique), day-choice evidence (`facts_of` filtered by the known ids), and
the fallback label of a stored row with no text of its own (NPC speak
block, MJ player knowledge, tick briefing). `day_concordance` and
`tick_context._reachable_locations` read ids and levels only.
Consequence: E versions exactly these; the id/level readers need nothing.

### R-09 — a stored row's own text [M]
Opened: `src/world_engine/models/canon_knowledge.py:199-239` (`Knowledge`:
nullable `content`, `updated_at`); `src/world_engine/lore_write_apply.py:
252-264` (Lore knowers are written without text);
`src/world_engine/prose_render.py:62-77`.
Finding: a row with its own text renders it; a row without falls back to
its fact's text.
Consequence: only the fallback is versioned; a row's own text is the
holder's version and is never rewritten.

### R-10 — the facet registry [M]
Opened: `src/world_engine/facets.py:26-60` (`FacetSpec`; `tenue` presets
`none`, `physique` presets `rencontre`); `src/world_engine/writes/facets.py:
60-70` (`_preset_scope`: `rencontre` scopes the entity itself), `:143`,
`:339` (preset level `knows`); `tooling/verify/checks/fact_facets.py:69-90`
(`EXPECTED_FACETS`, five fields compared).
Finding: an outfit is known by nobody by default. `FacetSpec` is a frozen
dataclass with defaulted trailing fields.
Consequence: V1 changes `tenue`'s preset and its row in `EXPECTED_FACETS`;
F adds `edit_kind` as a defaulted field, outside the compared five.

### R-11 — the outfit has no play reader [M]
Opened: enumeration E5; `src/world_engine/context_describe.py:55-127`
(`_npc_context_company`: `physique`, `description`;
`_mj_context_co_presents`: `description`, `physique`);
`src/world_engine/context.py:839-846` (MJ co-present line).
Finding: `tenue` is read nowhere outside the registry and the creator
editors.
Consequence: E adds it to both scene descriptions (V1).

### R-12 — the Lore dossier and its renderer [M]
Opened: `src/world_engine/lore_selectors.py:174-192` (`_knowledge_rows`),
`:237-275` (`who_knows_about`); `src/world_engine/lore_render.py:61-63,
78-84`; `scripts/seed_pilot.py:1796-1798` (the prompt's `is_incorrect`
rule); `tooling/verify/checks/lore_isolation.py` R2 (every `select(` in
`lore_selectors.py` is world-scoped).
Finding: both selectors list stored rows only; `content` is the row's own
text, `None` when it has none; the template prints `content`.
Consequence: G fills `content` with the marked old version for a stale row
without text, through resolver calls (no new `select(`), the prompt
unchanged (T1).

### R-13 — the editors [M]
Opened: `frontend/src/creation/FactsEditor.svelte:85-115` (`write`,
`saveBloc`, `saveLine`); `src/world_engine/cockpit/crud/facets.py:42-44`
(`FactContentBody`), `:69-79` (`list_facets`), `:115-127`;
`frontend/src/lore/WritePanel.svelte:126-135`;
`frontend/src/lore/writePanel.svelte.js:178-207` (`toProposal`);
`src/world_engine/lore_write_apply.py:160-170, 280-286`;
`src/world_engine/lore_write_draft.py:210-240, 251-280`.
Finding: two surfaces rewrite a fact: the fiche (`PUT
/api/facts/{id}/content`, body `{content}`) and the Lore panel (`rewrite`
of a bloc fact, no facet in the draft item).
Consequence: F adds `kind` to both, preselected from the facet of the
rewritten fact (the draft looks it up).

### R-14 — the date of facts created by the v2.06 migration [M]
Opened: enumeration E6; `src/world_engine/models/canon.py:54-59`
(`_created_ts`: default `datetime.now(UTC)`).
Finding: the v2.06 migration sets no `created_at`; the facts and defaults it
created carry the migration's date, later than many encounters.
Consequence: Q1 — existing encounters are dated with the v2.14 migration's
time, taken after its own new defaults.

### R-15 — datetimes [M]
Opened: `src/world_engine/models/canon.py:54-59` (plain `DateTime`
columns); the installed `sqlmodel/sql/sqltypes.py` (`UTCDateTime`, used for
fields annotated `datetime` without `sa_column`: refuses a naive value on
write, returns aware UTC); `requirements.txt` (`sqlmodel>=0.0.16`).
Finding: `first_at` (and the new `last_at` fields) are plain annotations,
so their type depends on the installed SQLModel; `created_at`,
`entered_at`, `updated_at` read back naive.
Consequence: every comparison goes through `fact_versions.utc` (a naive
value is UTC); writers and fixtures use aware datetimes.

### R-16 — where raw fact text may be read [M]
Opened: `tooling/verify/checks/identity_tokens.py:7-14, 56-63` (R1:
`content_raw` only in `models/canon_knowledge.py`, `writes/*.py`,
`prose_render.py`, `knowledge_resolve.py`, migrations).
Consequence: `fact_versions.py` takes the history and the current text as
arguments; `prose_render.fact_texts_at` / `fact_is_stale` pass them.

### R-17 — the checks the lot passes [M]
Opened: `tooling/verify/checks/encounter_registry.py:1-60` (R1-R4);
`knowledge_resolution.py:74-166, 247-352` (tier 2b nearest; C-09 case 4:
the encounter is recorded before the defaults); `lore_write.py:300-400`
(C1c, `_REFUSALS`, the `__f3__` substitution); `world_cascade.py:1-40,
67-120` (W1 coverage, W3 fixture); `fact_facets.py:116-145`;
`function_length.py` (80 lines); `npc_schedule.py`;
`single_canon_write.py`; `claude_md_contract.py` (38 000 characters, 100
per line); `frontend_build_fresh.py`; `effect_self_write.py`.
Finding: C-09 case 4 and tier 2b encode the rules B5 and C1 replace;
`passage` is world-scoped and must be cascaded.
Consequence: D amends the two fixtures (named in its Scope IN); A adds
`passage` to the cascade and its fixture.

### R-18 — the migration pattern [M]
Opened: `scripts/migrate_v2_13_lore_usage.py` (env guard, refusal below the
previous version, idempotent DDL, post-checks, `schema_meta` convergence);
`scripts/migrate_v2_12_zone_borde.py:60-130` (data steps through
`writes/`); `tooling/verify/checks/lore_usage.py:240-300` (U2: a
previous-shaped database, refusal, shape equality, second run).
Consequence: `migrate_v2_14_passage.py` and A2 follow both, by name.

### R-19 — production measurement (Nia, 2026-10-05)
`fact_default` 540 rows (world 328, rencontre 167, location 43, faction 2);
79 of 1,660 facts with history; 647 knowledge rows, 42 without text;
`rencontre` 223 (relation 166, gathering 31, visit 21, schedule 3,
conversation 2); 32 visits; 157 characters placed; 13 schedule rows; one
`tenue`, no default.
Consequence: the 43 place defaults change meaning (kept after leaving); the
migration's backfill covers the 157 placements so nobody loses a fact.

## Contract sheet

### C-01 — the registries (schema v2.14)
Produced by: BRIEF-0105-A   Consumed by: BRIEF-0105-B, D
`passage(id TEXT PK, world_id FK world NOT NULL, entity_id FK entity NOT
NULL, location_id FK entity NOT NULL, last_at DATETIME NOT NULL)`, UNIQUE
`idx_passage_entity_location(entity_id, location_id)`, index
`idx_passage_location(location_id)`; model `Passage` in
`models/ephemeral.py`, exported by `models`. `rencontre.last_at DATETIME`
nullable in SQL, `Optional[datetime]` in the model. Both cascaded with the
world (`_DIRECT_WORLD_SCOPED_DELETES`).
Error and empty cases: the migration refuses below v2.13; leaves no NULL
`last_at`.

### C-02 — passages
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D (through C-01), E
`passages.record_passage(db, *, world_id, entity_id, location_id, at=None)
-> Passage`: creates the pair's row or moves `last_at` forward to `at`
(default now, UTC), never back; finds a pending row of the same flush.
`passages.record_passages(db, *, world_id, entity_id, location_ids,
at=None) -> None`: each distinct place. `passages.listener_registered() ->
bool`. The `before_flush` listener on `sqlalchemy.orm.Session` records, for
every `Character` new with a place or whose `current_location_id` changed,
the place entered and the place left, at the flush's time; `db.py` imports
`passages` at module end. `write_npc_schedule` records the passages of every
place its old and new rows name. No function commits.
Error and empty cases: a character without place records nothing.

### C-03 — the last contact of an encounter
Produced by: BRIEF-0105-B   Consumed by: BRIEF-0105-D
`encounters.record_encounter(...)` unchanged signature and return (new row
or `None`). A new row has `last_at = first_at = at`. An existing pair's
`last_at` moves forward to `at` unless `source == "relation"`; never back.

### C-04 — the kind of a rewrite
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, F, G
`writes.facts.FACT_CHANGE_KINDS = ("correction", "changement")`.
`update_fact_content(db, *, fact, content, changed_by, kind)`,
`update_typed_fact_content(db, *, fact, content, changed_by, kind)`,
`writes.facets.edit_entity_fact(db, *, fact_id, content, changed_by,
kind)`: `kind` required, keyword-only; `ValueError` outside the vocabulary,
before any write. History entry `{"content": <text before>, "changed_by",
"at": <aware ISO>, "kind"}`. An entry without `kind` reads as a
correction.

### C-05 — the version known
Produced by: BRIEF-0105-C   Consumed by: BRIEF-0105-D, E, G
`fact_versions.utc(value) -> datetime` (naive = UTC).
`fact_versions.version_text(history, current, as_of) -> str`: `as_of` None
→ `current`; else the `content` of the first `changement` entry whose `at`
is after `as_of`, else `current`. Pure.
`prose_render.fact_texts_at(db, pairs: list[(Fact, as_of)]) -> list[str]`
(rendered, one entity query); `prose_render.fact_is_stale(fact, as_of) ->
bool`.

### C-06 — resolution dated by contact
Produced by: BRIEF-0105-D   Consumed by: BRIEF-0105-E, G
`knowledge_resolve.Known(level: str, as_of: Optional[datetime])` (frozen).
`resolve_knowledge(db, entity_id, fact_id) -> Known` (total; unknown fact →
`Known("unaware", None)`); `resolve_known_for_entity(db, entity_id) ->
dict[fact_id, Known]` (above `unaware` only); `resolve_knowledge_level` and
`resolve_levels_for_entity` keep their signatures and return levels.
Rules: tiers 1-7 as in the module docstring; tiers 3-5 need a contact with
the scope at or after the default's `created_at` (rencontre: met; location:
the place or a place inside it; faction: membership open, or closed after);
contact right now: the current place and its ancestors, schedule places and
their ancestors, an entity at the same current place, an entity sharing a
schedule slot, an active membership; highest level per tier. `as_of`:
`None` for a fact with a `world` default, for tier 2, tiers 6-7; otherwise
the latest contact with any anchor (participants, non-world scope ids) and,
for a stored row, its `updated_at` if later.
Error and empty cases: unknown entity → `{}` from the batch.

### C-07 — the knower readers (family contract)
Produced by: BRIEF-0105-E   Consumed by: Play, ticks, day choice
A reader that shows a fact as one holder knows it renders
`version_text(...)` at that holder's `as_of` (C-06): `resolve_default_rows`
(rows' `content_raw`), `facet_reads.known_facts_of` (through
`facet_reads.versioned(db, rows, known) -> list[FactRow]`), day choice
evidence (`versioned`), and the fallback label of a stored row with no text
(`facet_reads.known_fact_texts(db, perceiver_id, facts) -> list[str]`, used
by `context._row_fact_texts` and `tick_context._tick_knowledge_block`). A
row with its own text is never rewritten. The scene's co-present lines
carry the known `tenue` (NPC context: with the physique; MJ context: key
`tenue`, `None` when blindfolded).
Members, re-read after the last: the five readers above, and BRIEF-0105-G's
dossier rows, which apply the same `as_of` to mark rather than replace.

### C-08 — the kind chosen by the creator
Produced by: BRIEF-0105-F   Consumed by: the creator
`FacetSpec.edit_kind: str = "correction"`; `physique` and `tenue`:
`"changement"`. `GET /api/facets` serves `edit_kind`. `FactContentBody.kind:
Literal["correction", "changement"]`, required. A Lore draft's `rewrite`
item carries `kind` (preset from its fact's facet,
`lore_write_draft._preset_kind`); the proposal's `rewrite` item must carry
one of the two kinds or `ProposalError`.

### C-09 — the dossier's old-version mark
Produced by: BRIEF-0105-G   Consumed by: the Lore renderer
In `entity_dossier` (section `knowledge`) and `who_knows_about` (section
`knowers`), a row whose own text is `None` and whose holder knows an older
version gets `content = "<old> (version ancienne — actuelle : <current>)"`
(both rendered); otherwise unchanged.

## Gate output

### (a) Property trace

| Property the lot asserts | Finding | Declaring file opened |
|---|---|---|
| six paths write a place, two through `**ext_kwargs`/`setattr`; no raw SQL | R-01 | `writes/characters.py`, `play_stream.py`, `routes/creator.py`, `crud/entities.py`, E1 |
| `Character.world_id` exists | R-01 | `models/canon.py` |
| `rencontre` one row per pair, earliest wins, writer returns None on an existing pair | R-02 | `models/ephemeral.py`, `encounters.py` |
| seven live encounter sites | R-02 | E2, `encounter_registry.py` (LIVE_SITES) |
| a schedule never writes a place; DELETE must stay in `write_npc_schedule` | R-03 | `writes/config.py`, `schedule_reads.py`, `npc_schedule.py`, `single_canon_write.py` |
| `visit` written on scene entry only, `entered_at` plain DateTime | R-04 | `models/ephemeral.py`, `routes/scene.py` |
| tiers on main: rencontre undated, location nearest, faction active only | R-05 | `knowledge_resolve.py` |
| history entry shape; seven rewrite call sites | R-06 | `writes/facts.py`, E3 |
| deletion removes knowledge | R-07 | `writes/facts.py` |
| the knower readers, and the id-only readers | R-08 | `facet_reads.py`, `day_choice.py`, `context.py`, `tick_context.py`, `context_describe.py`, E4 |
| Lore knowers carry no text; fallback label | R-09 | `models/canon_knowledge.py`, `lore_write_apply.py`, `context.py` |
| `tenue` presets none; preset level `knows`; check compares five fields | R-10 | `facets.py`, `writes/facets.py`, `fact_facets.py` |
| `tenue` has no play reader | R-11 | E5, `context_describe.py`, `context.py` |
| dossier rows are stored rows; template prints `content`; R2 world-scoped selects | R-12 | `lore_selectors.py`, `lore_render.py`, `lore_isolation.py` (R2 implementation) |
| two rewrite surfaces, no facet on a Lore rewrite item | R-13 | `FactsEditor.svelte`, `crud/facets.py`, `WritePanel.svelte`, `writePanel.svelte.js`, `lore_write_apply.py`, `lore_write_draft.py` |
| v2.06 facts dated by their migration | R-14 | E6, `models/canon.py` |
| aware/naive datetimes depend on the column declaration | R-15 | `models/canon.py`, `sqlmodel/sql/sqltypes.py` |
| raw text perimeter | R-16 | `identity_tokens.py` (R1 implementation `_allowed`) |
| checks encoding the replaced rules | R-17 | `knowledge_resolution.py`, `lore_write.py`, `world_cascade.py` |
| migration and migration-check pattern | R-18 | `migrate_v2_13_lore_usage.py`, `migrate_v2_12_zone_borde.py`, `lore_usage.py` (U2) |

Presuppositions: no brief says « follow the existing convention »; each
pattern reused is named with its file (the v2.13 migration, the
`lore_usage.py` U2 rule, the `lore_write.py` growing-check precedent, the
`encounters.py` sole-writer precedent, the `addKnower`-free UI).

### (b) Case tables

**Resolution, tiers 3-5** (C-06; D1 rows):

| Scope | Contact | Default written | Result |
|---|---|---|---|
| location L | passage L at t1 | t2 | not known (D1a) |
| location M | passage M at t1, gone since | t0 | known, kept (D1b) |
| location zone Z | passage in a child of Z at t1 | t0 | known (D1c) |
| two places | both passed | t0 | highest level (D1d) |
| rencontre A | met A at t1 | t2 / t0 | not known / known (D1e) |
| faction F | left at t1 | t0 / t2 | known / not known (D1f) |
| faction F | active | any | known (D1f) |
| rencontre B | never met, same current place | t3 | known (D1g, O1) |
| rencontre S | never met, same schedule slot | t3 | known (D1g, L1) |
| location | current place or an ancestor of it | any | known (C-09 case 5) |

**`as_of`** (C-06; D2): world default → None; own descriptive fact → None;
stored row → max(`updated_at`, anchors); otherwise the latest anchor
contact.

**Version known** (C-05; C3): history correction t1, changement t2 ("v1"),
correction t3, changement t4 ("v2b"), current "v3", an entry without kind at
t5.

| as_of | known |
|---|---|
| before t1, between t1 and t2 | v1 |
| between t2 and t4 | v2b |
| after t4 | v3 |
| None | v3 |
| naive, between t2 and t3 | v2b |

**Rewrite kinds by caller** (C-04, U1):

| Caller | kind |
|---|---|
| `writes/mentions.py::bind_mention` | correction |
| `writes/relations.py::_refresh_map_content` | correction |
| `writes/relations.py::_refresh_lien_content` | changement |
| `cockpit/crud/facets.py::update_entity_fact_content` | `correction` (C), `body.kind` (F) |
| `lore_write_apply.py` rewrite | `correction` (C), `item["kind"]` (F) |
| `writes/facets.py::edit_entity_fact` | its own `kind` argument |

**Contacts recorded** (C-02, C-03):

| Event | `passage` | `rencontre.last_at` |
|---|---|---|
| character created with a place | place | — |
| place changed (any path) | old and new place | — |
| schedule written | every old and new place | schedule co-presence pairs |
| scene visit, gathering, conversation | — (placement covers it) | moved forward |
| social relation born | — | created if new; never moved |

### (c) Enumerations

```
--- E1 writes of current_location_id under src/ (assignment, constructor keyword, generic paths)
$ grep -rn "current_location_id\s*=[^=]" src --include=*.py | grep -v "/models/"
src/world_engine/writes/characters.py:48:    character.current_location_id = to_location_id
src/world_engine/lore_selectors.py:98:                current_location_id=character.current_location_id,
src/world_engine/cockpit/play_stream.py:471:    char.current_location_id = location_id
src/world_engine/cockpit/routes/creator.py:685:            current_location_id=body.current_location_id,
$ grep -rn "write_character_location(\|setattr(ext, key, value)\|ext_model(id=entity.id, \*\*ext_kwargs)" src --include=*.py
src/world_engine/writes/zone_promotion.py:167:        write_character_location(db, entity_id=being["id"], to_location_id=child_id)
src/world_engine/writes/characters.py:5:- `write_character_location(...)`      : write a character's
src/world_engine/writes/characters.py:28:def write_character_location(
src/world_engine/cockpit/mutations.py:707:    write_character_location(db, entity_id=npc_id, to_location_id=to_location_id, mutation_id=mut.id)
src/world_engine/cockpit/crud/entities.py:642:    ext_row = ext_model(id=entity.id, **ext_kwargs)
src/world_engine/cockpit/crud/entities.py:805:            setattr(ext, key, value)
$ grep -rn "current_location_id" src --include=*.py | grep -i "update \|insert "
src/world_engine/cockpit/crud/entities.py:649:    # (e.g. character.current_location_id) and may try to insert the
(raw SQL writes: none)
```
(`lore_selectors.py:98` is a keyword in a read; `crud/entities.py:649` a
comment.)

```
--- E2 encounter writers and their call sites
$ grep -rn "record_encounter\(s_among\)\?(\|record_gathering_join(" src --include=*.py | grep -v "def "
src/world_engine/writes/config.py:510:            record_encounter(
src/world_engine/writes/relations.py:227:        record_encounter(
src/world_engine/cockpit/play.py:921:        record_gathering_join(db, gathering_id=gathering_id, joiner_id=conv.player_id)
src/world_engine/cockpit/routes/scene.py:158:            record_encounter(db, world_id=world_id, a_id=player_id, b_id=npc_id,
src/world_engine/cockpit/routes/play.py:148:    record_encounter(
src/world_engine/gathering.py:271:        record_encounters_among(
src/world_engine/gathering.py:461:    record_gathering_join(db, gathering_id=target_gathering_id, joiner_id=npc_id)
src/world_engine/encounters.py:86:        if record_encounter(
src/world_engine/encounters.py:110:        if record_encounter(

--- E3 fact rewrite call sites (src, scripts, tooling)
$ grep -rn "update_fact_content(\|update_typed_fact_content(\|edit_entity_fact(" src scripts tooling --include=*.py | grep -v "def "
src/world_engine/lore_write_apply.py:284:                edit_entity_fact(self.db, fact_id=fact.id, content=item["content"],
src/world_engine/writes/mentions.py:110:        update_fact_content(db, fact=owner, content=new_text, changed_by=changed_by)
src/world_engine/writes/facets.py:373:        return update_fact_content(db, fact=fact, content=fact.content_raw, changed_by=changed_by)
src/world_engine/writes/facets.py:377:    return update_fact_content(db, fact=fact, content=tokens.text, changed_by=changed_by)
src/world_engine/writes/relations.py:243:    update_typed_fact_content(
src/world_engine/writes/relations.py:258:    update_typed_fact_content(
src/world_engine/cockpit/crud/facets.py:120:        fact = edit_entity_fact(db, fact_id=fact_id, content=body.content, changed_by=CREATED_BY)

--- E4 readers of the resolver and of known_facts_of
$ grep -rn "resolve_knowledge_level(\|resolve_levels_for_entity(\|resolve_default_rows(\|known_facts_of(" src --include=*.py | grep -v "def "
src/world_engine/facet_reads.py:122:    known = resolve_levels_for_entity(db, perceiver_id)
src/world_engine/knowledge_resolve.py:348:    levels = resolve_levels_for_entity(db, entity_id)
src/world_engine/day_concordance.py:379:        "perceiver", known_fact_ids=frozenset(resolve_levels_for_entity(db, character.id)),
src/world_engine/tick_context.py:273:    return knowledge + resolve_default_rows(session, npc_id, {k.fact_id for k in knowledge})
src/world_engine/tick_context.py:469:        return resolve_levels_for_entity(db, knower_id)
src/world_engine/day_choice.py:100:    known = resolve_levels_for_entity(db, character.id)
src/world_engine/context_describe.py:77:        seen = known_facts_of(
src/world_engine/context_describe.py:120:            "physique": None if blindfolded else joined(known_facts_of(
src/world_engine/context.py:248:    lines.extend(row.content for row in known_facts_of(
src/world_engine/context.py:362:    knowledge = knowledge + resolve_default_rows(
src/world_engine/context.py:687:    knowledge_rows = knowledge_rows + resolve_default_rows(

--- E5 the tenue facet outside the registry
$ grep -rn '"tenue"' src --include=*.py | grep -v src/world_engine/facets.py
(none)

--- E6 created_at in the v2.06 migration
$ grep -n "created_at" scripts/migrate_v2_06_lore_as_facts.py
(none)
```

The fallback-label readers (stored rows with no text) are the callers of
`context._row_fact_texts` (`context.py:378`, `:696`) and the facts list of
`tick_context._tick_knowledge_block` (`:286`), read in R-08.

### (d) Family contracts

C-07 (the knower readers) was written before its five members and re-read
after BRIEF-0105-G's dossier rows were specified: G applies the same
`as_of` (C-06) and the same version rule (C-05), and marks instead of
replacing because the dossier is the creator's view.

### (e) Gates and the modules that satisfy them

| Gate | Module that satisfies it | What it needs that the gate forbids |
|---|---|---|
| `fact_learning.py` A1-G1 (proposed) | the modules each brief names | nothing |
| `knowledge_resolution.py` (passed, amended in D) | `knowledge_resolve.py` | the old nearest/undated fixtures — amended by name |
| `encounter_registry.py` R1-R4 (passed) | `encounters.py` sets `last_at` by attribute, no `update(` | nothing; docstring amended in B |
| `function_length.py` (passed) | `writes/config.py`: the contacts helper keeps `write_npc_schedule` at its length | a new helper, specified in B |
| `npc_schedule.py`, `single_canon_write.py` (passed) | DELETE stays in `write_npc_schedule` | the helper reads only, called before it |
| `identity_tokens.py` R1 (passed) | `fact_versions.py` takes text as arguments; raw read stays in `prose_render.py` | specified in C |
| `lore_isolation.py` R2 (passed) | `lore_selectors._stale_label` calls the resolver, no new `select(` | nothing |
| `world_cascade.py` W1/W3 (passed) | `writes/worlds.py` lists `passage`; fixture row added | specified in A |
| `fact_facets.py` R1 (passed) | `EXPECTED_FACETS` row for `tenue` | specified in A |
| `lore_write.py` C1c/C1d (passed) | proposals carry `kind`; new refusal rows | specified in F |
| `claude_md_contract.py` (passed) | two CLAUDE.md lines under 100 characters | nothing |
| `frontend_build_fresh.py`, `lore_usage.py` U11c (passed) | rebuilt `static/` in F | a rebuild |
| `schema_version_agreement.py`, `schema_partition.py` (passed) | constant, header and changelog at v2.14 | specified in A |

Named mutations run on the prototype, each red then reverted: listener
detached → B2, B3; `relation` moves `last_at` → B4; tier date condition
removed → D1a, D1e-late, D1f-late; anchors emptied → D2; `known_facts_of`
unversioned → E1, E2.

## Amendments

(none)
