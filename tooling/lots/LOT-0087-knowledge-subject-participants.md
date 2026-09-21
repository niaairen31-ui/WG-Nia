# LOT -- TICKET-0087 "Knowledge subject as fact participants, and the who_knows_about selector"

Source of authority. On any disagreement between a brief's embedded copy of
an `R-NN` or `C-NN` and this header, the header wins and the brief is
regenerated.

RECON run 2026-09-14 against the working tree at
`Documents/World-genrator` (post-0085, post-0086) and against the production
database at `~/.world_engine/world_engine.db` (`schema_meta.static_version =
v2.03`). Every line number below was read from that tree.

## Objective and cut

Answer "qui sait quoi sur X" on the lore consultation surface, by giving
`knowledge` rows a structured subject and adding one selector that reads it.

The lot stops at the read side of that one question. It does not build the
creator write path for asserted knowledge (TICKET-0085 queue item 5), any
further selector (`location_contents`, `faction_roster`,
`region_locations`), the `situation` chantier, or a viewpoint parameter.

**No schema change.** The structure this ticket needs already exists and is
empty (R-02). `danger_class` is `db_write`, not `migration`.

## Briefs in this lot

- **BRIEF-0087-a** `write-knowledge-subject-participants` -- `write_knowledge`
  accepts `subject_entity_ids` and attaches them to the row's fact through
  the sanctioned writer. Chokepoint only; no caller changes.
- **BRIEF-0087-b** `proposed-subject-entity` -- the `new_knowledge` payload
  carries an optional `subject_entity_id`; the model names it, the apply
  branch re-validates it against the world before it reaches canon.
- **BRIEF-0087-c** `subject-participant-backfill` -- one pass over existing
  `knowledge` facts through the shared resolver, unambiguous matches only,
  plus the coverage report command.
- **BRIEF-0087-d** `creator-subject-binding-surface` -- the creator binds a
  subject to an entity from the entity sheet, and the residue route is
  exposed. The backend participant routes already exist (R-08). *The
  world-scoped residue worklist was cut from this brief by AMENDMENT-0087-2
  and is TICKET-0088's.*
- **BRIEF-0087-e** `who-knows-about-selector` -- the selector, its whitelist
  and description entries, its section formatters, its coverage row, and the
  three check files that must learn its name. *(AMENDMENT-0087-3: under `N1`
  `checks/lore_selectors.py` learns it by derivation, not by an edited
  literal; `lore_isolation.py` R8 needs no edit.)*

## Dependency graph

```
BRIEF-0087-a  ->  BRIEF-0087-b
              ->  BRIEF-0087-c  ->  BRIEF-0087-d
                                ->  TICKET-0088  ->  BRIEF-0087-e
```

*(TICKET-0088 inserted by AMENDMENT-0087-2, code `K3`.)*

*(AMENDMENT-0087-3: TICKET-0088 merged into `main` as `af672f9` (PR #114).
`e` starts from `main` at `2ae232b` or later, on `ticket/0087` fast-forwarded
to it -- code `L1`, R-21.)*

`a` is strictly first: `b`, `c`, `d` and `e` all consume `C-01`.
`b`, `c` and `e` are mutually independent after `a`.
`d` follows `c` because it reuses `C-06`'s residue query.

`e` is ordered last **by decision E2**, not by technical dependency: it
depends only on `a`. Running it earlier would ship a selector that answers
about 14% of entities; E2 chose to close the gap first. An executor that
finds `e` blocked on nothing is not finding a defect.

---

## RECON

### R-01 -- `knowledge` is already anchored to `fact`

Opened: `sqlite_master` on the production database; `src/world_engine/models/canon_knowledge.py`.

Finding: `knowledge` carries `fact_id VARCHAR NOT NULL` with `FOREIGN
KEY(fact_id) REFERENCES fact (id)`, plus `idx_knowledge_fact`. Full column
list: `id`, `entity_id`, `fact_id`, `subject`, `level`, `content`, `source`,
`is_incorrect`, `is_secret`, `share_threshold` (CHECK 1-100), `acquired_at`,
`updated_at`, `session_id`, `change_history`. No `world_id`: world scoping
goes through `entity`. `schema_meta.static_version` is `v2.03`.

Consequence: this ticket is not the chantier's first schema change, and
`knowledge` already has a structured link to a subject-bearing object. The
inbound handover's F1 omitted `fact_id` entirely and put the schema in the
v1.9x range; no claim derived from that finding survives into this lot.

### R-02 -- `fact_participant` exists, is sanctioned, is checked, is uniquely keyed, and is empty

*(Corrected by AMENDMENT-0087-1. The original finding asserted this table had
no uniqueness constraint. It has one. See the amendment for what that cost.)*

Opened: `src/world_engine/writes/facts.py:57-83`; `src/world_engine/models/canon_knowledge.py:112-129`; `tooling/verify/checks/fact_spine.py:1-22`; `sqlite_master` indexes and row counts on the production database.

Finding: `attach_participants(db, *, fact, entity_ids, role=None)` is the
single sanctioned write site for `fact_participant`. It raises `ValueError`
if the fact carries any typed FK, and assigns `position` in list order from
0. Its module docstring states the design intent verbatim: *"A typed fact
already IS the row it points to; `fact_participant` exists only to carry
arity for a free-standing fact."* `fact_spine.py` enforces this by AST scan
plus three DB assertions, each vacuity-guarded.

The model declares two indexes (`canon_knowledge.py:119-122`):

```python
    __table_args__ = (
        Index("idx_fact_participant_unique", "fact_id", "entity_id", unique=True),
        Index("idx_fact_participant_entity", "entity_id"),
    )
```

Both are present in the production database:

```
CREATE UNIQUE INDEX idx_fact_participant_unique ON fact_participant (fact_id, entity_id)
CREATE INDEX        idx_fact_participant_entity ON fact_participant (entity_id)
```

`role` is `Optional[str] = None` (`canon_knowledge.py:128`) and is **not**
part of the unique key. The module comment states the intent:
*"fact_participant (arity for a free-standing fact — never for a typed one;
enforced in code by writes/facts.py, spans two tables so SQLite cannot
express it as a CHECK)"* (`canon_knowledge.py:113-115`). For contrast,
`fact_default` in the same module carries
`idx_fact_default_unique ON (fact_id, scope_type, scope_id)` -- a
three-column unique key that **does** include its discriminator. TICKET-0082
puts a discriminator in a unique key where it wants one; on
`fact_participant` it did not.

Row count in production: **0**.

Consequence: the structure the ticket needs exists, with its chokepoint and
its gate. This is what makes A2 possible and a new column unnecessary. And an
entity participates in a fact at most once, by construction: a participant
already is an aboutness claim, which is why decision J2 drops the role
discriminator. `attach_participants` performs a plain `db.add`, so a second
attach for an existing pair raises `IntegrityError` at commit and aborts the
surrounding transaction -- every caller reads before it writes. The same
constraint guarantees `who_knows_about` can never return one knowledge row
twice for one asked entity.

### R-03 -- every knowledge row hangs off a free-standing fact that copies its own subject

Opened: `src/world_engine/writes/knowledge.py:20-27, 153-168`; joins on the production database.

Finding: `_build_knowledge_update` auto-creates a free-standing fact with
`content = resolved_subject` whenever `fact_id` is omitted
(`writes/knowledge.py:156-163`). Measured: 615 of 615 `knowledge` rows point
at a free-standing fact (`relation_id`, `event_id` and `world_law_id` all
NULL); 312 distinct `fact_id` values; 0 orphans. The `fact` table also holds
56 relation-typed facts, none of them referenced by `knowledge`.

Consequence: two things. The spine carries no subject information today, so
nothing can be read from it before this lot fills it. And a fact is shared by
roughly two knowers on average, which means the subject attaches once per
fact and every knower of that fact inherits it -- 312 attachments cover 615
rows.

### R-04 -- `write_knowledge` is the single create site, and it does not return the fact

Opened: `src/world_engine/writes/knowledge.py:171-211`; `src/world_engine/writes/__init__.py:53, 109-117`.

Finding: `write_knowledge` owns the only `db.add` for `knowledge`
(`knowledge.py:210`) and is the only place a knowledge-bearing fact is
created. The fact is created inside `_build_knowledge_update` and is not
returned to the caller; `write_knowledge` returns the `Knowledge` row only.
`create_fact`, `attach_participants` and `create_fact_default` are all
exported from `writes/__init__.py`.

The same module owns the level vocabulary: `KNOWLEDGE_LEVELS`
(`knowledge.py:44-46`), the ordered `KNOWLEDGE_LEVEL_LADDER`
(`knowledge.py:51-53`) and `knowledge_level_rank(level)`
(`knowledge.py:56-65`), which returns -1 for an unrecognised level so an
invalid level can never satisfy a monotone comparison. `fact_spine.py`
assertion 3 reads `KNOWLEDGE_LEVELS` from this module rather than re-typing
the set.

Consequence: a caller cannot attach participants to the fact
`write_knowledge` just created without re-querying it. The subject
attachment therefore belongs inside `write_knowledge`, which is also what
keeps the single-chokepoint invariant intact. This is `C-01`. And the
ordering `C-04` needs is `knowledge_level_rank`, imported, never a re-typed
ladder.

### R-05 -- the two `new_knowledge` payload producers, and why subjects are not names

Opened: `src/world_engine/analyzer_transcript.py:241-247, 283-301`; `src/world_engine/day_mutations.py:214-259`; `src/world_engine/cockpit/mutations.py:361-398`.

Finding: two producers construct a `new_knowledge` payload.

`analyzer_transcript._build_payload_new_knowledge` sets `subject` to
`_content_to_subject_slug(content)` -- the first five words of the content,
lowercased, non-word characters stripped, joined by underscores, truncated
at 50 characters (`analyzer_transcript.py:241-247`). The model's own
`"subject"` / `"entity"` field is read for a different purpose entirely: to
infer **who learned** the fact (`analyzer_transcript.py:287-293`). The model
is never asked what the knowledge is about.

`day_mutations._emit_new_knowledge` takes `subject` from
`v.required`, a requirement string on an unmet knowledge verdict
(`day_mutations.py:231`).

`ProposedMutation.payload` is a JSON column (`models/pipeline.py:129`), so a
new payload key is not a schema change.

Consequence: the reason 78% of subjects do not resolve is structural, not
accidental -- nothing in either producer ever attempts to name an entity.
This is the finding B2 acts on, and it is why B1 alone was rejected.

### R-06 -- subject resolution rate, measured with the real rungs

Opened: `src/world_engine/lore_resolve.py:42-137`, replayed over the production database.

Finding: replaying `normalize_surface`, `rung_named_exact` and
`rung_named_token` exactly as written, across all three categories of
`_CATEGORY_ENTITY_TYPE`:

| | distinct subjects | knowledge rows |
|---|---|---|
| matched | 69 / 312 (22.1%) | 98 / 615 (15.9%) |
| ambiguous | 0 | 0 |
| unmatched | 243 / 312 (77.9%) | 517 / 615 (84.1%) |

Verkhaal alone: 8 of 36 distinct subjects, 13 of 46 rows.

Match quality on inspection is sound -- `"L'influence des vampires dans les
régions voisines" -> Les Vampires`, `"Vengeance de Lila la Morte" -> Lila la
Morte`, `"Membres de la Maison Royale" -> La Maison Royale`. No false
positive was found in the sample.

Consequence: this is the number BRIEF-0087-c's done-means asserts against.
A backfill fills 98 rows and leaves 517 null.

### R-07 -- the user-facing coverage number

Opened: same replay, aggregated by resolved subject entity.

Finding: after a complete backfill, "qui sait quoi sur X" has a non-empty
answer for **42 of 297 active entities (14.1%)**. On Verkhaal, 6 of 57:
Maelis (6 knowers), La Mer Rouge (2), and four entities with one knower each
(La Commune des Pauvres, La Société des Entrepreneurs, Le quartier
populaire, La Maison des Maitres). 51 Verkhaal entities have no knower at
all.

Consequence: this is what makes D1 load-bearing rather than decorative, and
it is the number the live gate checks against.

### R-08 -- the participant attach/detach routes already exist

Opened: `src/world_engine/cockpit/crud/knowledge.py:218-250`.

Finding: `POST /facts/{fact_id}/participants` and `DELETE
/facts/{fact_id}/participants/{entity_id}` are already implemented
(TICKET-0082, BRIEF-0082-b), calling `attach_participants` for the first.
`_create_knowledge_core` (`crud/knowledge.py:143-171`) documents the
auto-creation fallback and passes no participants.

Consequence: BRIEF-0087-d builds a surface and a residue query, not a
backend. Its blast radius is smaller than it looks.

### R-09 -- zero ambiguity, everywhere

Opened: same replay as R-06, over all eleven worlds.

Finding: not one subject string in the production database resolves to two
or more candidate entities, in any category, in any world.

Consequence: the handover's proposed ambiguity journal has no cases. It is
not in this lot. The `ambiguous` verdict still exists in `C-02` because the
resolver must be total, and because a world authored tomorrow can produce
one -- but no surface is built for it here.

### R-10 -- the creator CRUD, not the analyzer, is the dominant producer

Opened: `knowledge.session_id` and `knowledge.subject` distributions on the production database.

Finding: 12 of 615 knowledge rows carry a `session_id` (the conversation
path). 15 of 310 distinct subjects contain an underscore, the signature of
`_content_to_subject_slug`. 295 rows carry a NULL `source`.

Consequence: B2 improves a path that produced a small minority of existing
rows. The creator path is where coverage actually comes from. This does not
change the locked decision -- it is why E2's ordering puts BRIEF-0087-d
before the selector, and it is flagged to Nia at delivery as drafting
decision 5.

### R-11 -- `entity_dossier` already returns secrets to this surface

Opened: `src/world_engine/lore_selectors.py:139-157`.

Finding: `_knowledge_rows` selects `Knowledge` joined to `Entity` on
`world_id`, with no `is_secret` filter, and returns `is_secret` as a key on
every row.

Consequence: F1b is the existing precedent, not a new exception. The MJ
context assembler's structural exclusion (CLAUDE.md, "Secrets are
structurally excluded") governs assembled NPC context and is untouched here.
BRIEF-0087-e must not be read as licence to relax it anywhere else.

### R-12 -- the selector registration surface is four places, not one

*(Corrected by AMENDMENT-0087-3. The constant sits at `:38`, not `:37`; and
under code `N1` the literal is removed -- R2 derives its names from the
`fn=` keyword of every `SelectorSpec(...)`, so item 4 below describes the
state `BRIEF-0087-e` removes. See R-27.)*

Opened: `src/world_engine/lore_selectors.py:199-209`; `src/world_engine/lore_plan.py:23-40`; `src/world_engine/lore_render.py:27-69`; `tooling/verify/checks/lore_isolation.py:26-29, 404-435`; `tooling/verify/checks/lore_selectors.py:37`.

Finding: adding a selector touches four registries and one hardcoded check
constant.

1. `SELECTORS` tuple and `_SELECTOR_LOOKUPS` dict (`lore_selectors.py:199-209`). `SelectorSpec` fields: `fn`, `arity`, `row_cap`, `arg_kinds`, `context_sections`.
2. `_SELECTOR_DESCRIPTIONS` (`lore_plan.py:29-37`). `lore_isolation` R8 asserts its key set equals `SELECTORS`.
3. `_SECTION_FORMATTERS` (`lore_render.py:62-69`), currently `identity`, `relations`, `knowledge`, `memberships`, `goals`, `factions`. An unknown section raises (`lore_render.py:81-85`), guarded by `lore_isolation` R14.
4. `SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}` at `tooling/verify/checks/lore_selectors.py:38` -- a **hardcoded literal set**. R2 of that check asserts no selector function name appears in `lore_query.py`. A third selector not added here is simply not covered by R2, silently.

Consequence: item 4 is the TICKET-0086 defect class -- a check whose subject
list drifts from the code it guards. BRIEF-0087-e carries it as a Scope IN
item with its own done-means line, not as a nicety.

### R-13 -- what `execute_plan` requires of a selector, and what it forbids

*(Extended by AMENDMENT-0087-3: truncation is a tail slice and does not
spare `context_sections` rows -- last paragraph below.)*

Opened: `src/world_engine/lore_query.py:58-197`; `tooling/verify/checks/lore_selectors.py:1-25`.

Finding: `validate_plan` rejects, before any row is read, a selector outside
`SELECTORS`, an arity mismatch, an unknown mention ref, or an `arg_kinds`
mismatch. `arg_kinds` admits exactly two values: `"entity_id"` (a mention
ref) and `"world_id"` (the literal `"$world"`).

`execute_plan` raises `ValueError` on any returned row with no `"section"`
key (`lore_query.py:174-179`). It truncates at `row_cap` and records
`truncated` in the trace rather than dropping silently
(`lore_query.py:180-186`). Rows in a spec's `context_sections` are excluded
from `content_row_count`, which is what decides `answered` versus
`silent_canon` (`lore_query.py:183, 192`).

R5 of `checks/lore_selectors.py` asserts the set of string literals assigned
to `verdict` in `lore_query.py` equals exactly five values: `answered`,
`ambiguous_mention`, `unknown_entity`, `silent_canon`,
`unsupported_selector`.

Consequence: the coverage report of D1 cannot be a sixth verdict and cannot
be written into the trace by the selector, which has no access to it. It is a
row in a `coverage` section declared in `context_sections` -- which is
exactly the mechanism `context_sections` exists for. This is `C-04`.

*(AMENDMENT-0087-3.)* Truncation is `result_rows[: spec.row_cap]`
(`lore_query.py:180-181`), applied to the selector's whole list before the
`context_sections` count at `:183`. A context row placed last is therefore
cut whenever the selector returns more than `row_cap - 1` content rows.
`entity_dossier` is immune because its only context row is its first:
`_identity_rows(...)` opens the concatenation (`lore_selectors.py:190-191`)
and `identity` is its sole `context_sections` entry (`:204`). Consequence:
`C-04` emits `coverage` first (code `M1`), and `execute_plan` stays
unmodified.

### R-14 -- the resolver's contract, and the category it requires

Opened: `src/world_engine/lore_resolve.py:28-33, 103-137`.

Finding: `resolve_named(surface_form, category, world_id, db) ->
NamedResolution(verdict, entity_id, candidate_ids, rung, rungs_tried)`.
`verdict` is one of `matched`, `ambiguous`, `unmatched`; there is no fourth
and no casting branch. `category` is mandatory and is looked up in
`_CATEGORY_ENTITY_TYPE = {"place": "location", "person": "character",
"faction": "faction"}` -- a `KeyError` on anything else.
`NAMED_RUNGS = ("named_exact", "named_token")`; `named_alias` is
deliberately absent.

`rung_named_token` matches when the entity's normalized name tokens are a
**subset** of the surface tokens and at least one is three characters or
longer (`lore_resolve.py:88-93`).

Consequence: a `knowledge.subject` string arrives with no category, so
`resolve_named` cannot be called as the inbound handover described. The
three categories must be walked and reconciled. That reconciliation is one
behaviour used by three briefs, so it is written once, as `C-02`. Entity
types outside those three -- production holds `item` (1) and `magic` (1) --
are unreachable by any rung, by construction.

### R-15 -- invariants this lot stands closest to

Opened: `CLAUDE.md:143-145, 146-152, 157-167, 168-171`.

Finding, verbatim where it matters:

- *"`new_knowledge` / `status_change` are idempotent facts: identity-based dedup (`entity_id` + `subject`; `entity_id`) via `_mutation_match_key`, same conversation required."* (`CLAUDE.md:143-145`)
- *"Two canon-write paths for rows: `_apply_mutation`, creator CRUD."* (`CLAUDE.md:157-158`)
- *"Commit before touching any canon-writing path."* (`CLAUDE.md:163`)
- The MJ context assembler's perception boundary (`CLAUDE.md:168-171`).

Consequence: the dedup guard keeps matching on `entity_id` + `subject`, in
every brief, without exception -- A1 was rejected precisely so this stays
untouched. It is named in Scope OUT of every brief in this lot.

### R-16 -- two script conventions in `scripts/`, and this lot uses only one

Opened: `scripts/` enumerated in full.

Finding: two naming families coexist. `migrate_v<MAJOR>_<NN>_<slug>.py` for
DDL passes -- the highest is `migrate_v2_03_drop_world_magic_status.py`,
matching `schema_meta.static_version = v2.03` exactly. And
`apply_ticket_<NNNN>_<slug>.py` for data and prompt passes that carry no DDL
-- `apply_ticket_0076_day_prompt_seed.py`,
`apply_ticket_0077_plan_select_seed.py`,
`apply_ticket_0078_narration_seed.py`. Measurement scripts take a bare verb
name: `measure_conversation_window.py`, `observation_metrics.py`,
`preview_tick_context.py`.

`scripts/backup.py` exists, with the 2-file rotation the project already
relies on before a production write.

Consequence: every script in this lot takes an `apply_ticket_0087_*` name.
None takes a `migrate_` name, because none carries DDL, and a `migrate_`
name would imply a version bump that is not happening.

### R-17 -- the creator surfaces this lot touches, and the one it must not

Opened: `frontend/src/` enumerated in full; `frontend/src/creation/KnowledgeEditor.svelte:1-133`.

Finding: the Svelte 5 tree holds five shells --
`creation/`, `graph/`, `journee/`, `lore/`, `observation/` -- plus
`legacy/` and `lib/`.

`creation/KnowledgeEditor.svelte` is the per-entity knowledge editor, a
faithful port of the legacy in-context editor (TICKET-0059, BRIEF-0059-c).
It receives `{ knowledge, entityId, levelOptions, legacyDoc, onSaved }`
(`:10`), renders one card per row over `subject`, `level`, `source`,
`share_threshold`, `is_incorrect`, `is_secret`, `content`, and writes through
`sheetRequest(legacyDoc, url, method, body, reloadEntity)` from the shared
`creation/sheetRequest.svelte.js` (`:8, :38-54`). `reloadEntity` re-fetches
`/api/entities/{entityId}` and calls `onSaved` (`:34-36`). It carries no fact
and no participant field today. `deleteRow` guards with `confirm()` (`:52`);
`saveRow` does not.

`lore/Lore.svelte` and `lore/lore.svelte.js` are the TICKET-0085 consultation
surface. Build output is committed and guarded by `frontend_build_fresh.py`
and `static_asset_freshness.py`; `creation_island.py` and
`json_ui_boundary.py` guard the shell boundary.

Consequence: the subject-binding surface has an obvious host in
`KnowledgeEditor.svelte` and an obvious request cycle to copy. It must not go
in `lore/`: TICKET-0085 locked that surface read-only for its first
perimeter, so a bind action there would break a locked decision, not merely
sit oddly. This is what fixes BRIEF-0087-d's placement without a coin flip.

### R-18 -- prompts live in the database, versioned, never edited in place

Opened: `src/world_engine/prompt_registry.py`; `scripts/apply_ticket_0078_narration_seed.py` as the shape precedent.

Finding: prompt templates are stored as a `prompt_template` head with
`prompt_version` rows. `current_prompt()` is the sole read accessor and
`write_prompt_version` the sole write shape. `prompt_registry.py` owns the
registry of known templates; `prompt_coverage.py`, `prompt_lean.py`,
`prompt_version.py` and `prompt_model_write.py` are its G1 checks. Prompt
changes ship as `apply_ticket_<NNNN>_*` scripts, not as edits to a file.
TICKET-0079 established that prompt templates carry no examples, because
examples tint NPC vocabulary.

Consequence: BRIEF-0087-b's prompt change is a new `prompt_version` row
written by a script, with no example values, and the previous version stays
intact.

### R-19 -- the three dedup guards, named so no brief touches them

Opened: `src/world_engine/cockpit/routes/mutations.py:255-291, 294-331`; `src/world_engine/cockpit/mutations.py:73-108`.

Finding: three distinct duplicate guards cover `new_knowledge`.
`_find_applied_duplicate_conversation_sourced` keys on `conversation_id` +
`entity_id` + `subject` (`routes/mutations.py:294-311`).
`_find_applied_duplicate_tick_sourced` dispatches to `_dup_tick_new_knowledge`
for tick-sourced rows (`routes/mutations.py:281-282`).
`_knowledge_leg_already_applied` scans applied `new_knowledge` and
`resource_change` rows for a matching `entity_id` + `subject`
(`cockpit/mutations.py:73-108`), and carries a documented one-directional
accepted gap recorded in `ARCHITECTURE_DECISIONS.md`
(`cockpit/mutations.py:85-90`).

Consequence: all three are named in the Scope OUT of every brief that works
near them. Decision A1 was rejected precisely so none of them changes, and
"make it consistent while nearby" is the exact temptation Scope OUT exists to
close.

### R-20 -- `CREATION_ISLANDS` is a migration ledger with no greenfield path

*(Added by AMENDMENT-0087-2. Measured during the escalation that produced it,
and recorded here so TICKET-0088 inherits it rather than re-deriving it.)*

Opened: `frontend/src/creation/registry.js`; `tooling/verify/checks/creation_island.py:44-70, 107, 229-248, 332-337`; `frontend/src/creation/Creation.svelte`; `frontend/src/creation/Queue.svelte`.

Finding: every Creation surface mounts through `CREATION_ISLANDS` and
`mount.js`, the only sanctioned mechanism (rule 6). Rule 2 (`:246-248`)
requires each entry to declare a non-empty `retiredPrefixes` list; rule 7
(`:332-337`) proves each prefix matches zero `function <prefix>...(`
declarations in `src/world_engine/cockpit/legacy.html` (`INDEX_HTML`,
`:107` -- the docstring still says `index.html`, the code does not). Rule 4
requires each `containerId` to exist as an element id in `Creation.svelte`;
rule 5 requires a matching `CREATION_TABS` declaration; rule 9 requires that
entry to carry `loader: null` and `state.onWorldSwitch: null`.

The registry holds 16 entries. Enumerated `migratedBy` values:

```
TICKET-0058 x 5   (constructeur, entityList, entitySheet, region, batch)
TICKET-0059 x 10  (npcAgent, artefacts, competences, registre, prompts,
                   linkAgent, pjSkillFiche, queueFilters, queue, queueBatchBar)
```

Nothing has been added since the frontend migration series. `registry.js`'s
own header states the purpose: *"one entry per surface a brief converges ...
It is the record of what has moved, not of what remains."*

A child component of a registered island needs no entry of its own --
`QueueCard.svelte`, `ConversationWindowConfig.svelte` (named "as its child"
in the `prompts` entry comment) and `KnowledgeEditor.svelte` all prove it.
`Queue.svelte` is the world-scoped panel precedent: `$effect` on
`serverState.worldId`, a refresh button, a `panel-head`.

Consequence: a greenfield Creation panel has no provenance to declare and no
honest way to satisfy rule 2. This is a frontend-seam gap, not a
knowledge-subject problem, and it is why BRIEF-0087-d item 5 was deferred
rather than forced. TICKET-0088 owns it.

### R-21 -- where `e` starts: the base, the branch, and why `/pipeline` cannot start it

*(Added by AMENDMENT-0087-3. RECON of 2026-09-21 against `origin/main` at
`2ae232b`, read from GitHub: tarball verified with `git get-tar-commit-id`,
history from a blobless clone.)*

Opened: `git log origin/main`, `origin/ticket/0087`; `git diff --name-only ced51c1 2ae232b`; `.claude/commands/pipeline.md`, `.claude/commands/brief-exec.md`, `.claude/settings.json`, `.claude/hooks/block-main-push.ps1`; history of `tooling/tickets/TICKET-0087-*.md` and `TICKET-0088-*.md`. [M]

Finding:
- `main` is `2ae232b` (merge of PR #115, TICKET-0089). TICKET-0087 a-d merged as `994c9b2` (PR #113), TICKET-0088 as `af672f9` (PR #114). `origin/ticket/0087` is still `ced51c1`, an ancestor of `main`.
- Between `ced51c1` and `2ae232b`, **no file this brief edits or anchors changed**: no `lore_*.py`, `writes/knowledge.py`, `models/canon_knowledge.py`, `subject_resolve.py`, `checks/lore_*.py`, `import_cycle.py`, `run.py`. The relevant changes are `CLAUDE.md`, `ARCHITECTURE_DECISIONS.md`, `creation_island.py`, `page_contract.py`, and the new `gathering_lifecycle.py`.
- `/pipeline` Step 0 derives status by precedence; rule 1 is "`ticket/NNNN` is merged into `main` -> `done`" (`pipeline.md:13`), and `done` stops (`:38`). Rule 2 needs a green verdict **and** a PR for the branch (`:14-19`). Rule 4, "brief file(s) exist -> eligible for `exec`" (`:22-23`), runs `/brief-exec` "for each brief in suffix order" (`:58-59`).
- `/brief-exec` step 1 creates or switches to `ticket/<NNNN>` (`brief-exec.md:7`).
- Pre-allowed commands include `git merge origin/main:*`, `git push origin ticket/*`, `gh pr create:*`, `python -m tooling.verify.run:*` (`settings.json`). `block-main-push.ps1` denies any `git push` whose command names `main` or `master`.
- TICKET-0087's front matter was committed once, at deposit (`382d0b0`, `status: brief`); no `/pipeline` run ever wrote it, and PR #113 was opened by hand. TICKET-0088 went `brief` -> `live-gate` in one commit when its PR opened (`54dab3f`).

Consequence: `/pipeline TICKET-0087` would answer `done` today and, once `e` has commits but no open PR, would replay `a` to `d`. Under code `L1`, `e` runs on `ticket/0087` fast-forwarded to `origin/main`, through `/brief-exec` alone; the PR is opened with `/pipeline` Step 3's own commands. The guard "no `/pipeline TICKET-0087` before the PR exists" is disciplinary; making Step 0 structural for a re-opened ticket is not this lot.

### R-22 -- what `run.py` runs, and what TICKET-0087's gate actually ran

*(Added by AMENDMENT-0087-3. This is S-1 of the TICKET-0088 decision RECON.)*

Opened: `tooling/verify/run.py`; `tooling/verify/checks/pipeline_state.py:42-56, 89-114`; `tooling/verify/results/TICKET-0087-knowledge-subject-participants.json`; `CLAUDE.md:83-84, 535-538`. [M]

Finding: `run.py` lives at `tooling/verify/run.py`; there is no `tooling/run.py`. It reads `tooling/tickets/<arg>.md` (`:30`), so `--ticket` takes the full slug. `LINK.search` (`:10, :20`) keeps the **first** arrow of each Machine line; a check linked twice runs once (`seen`, `:14, :21`); a check's recorded message is its last output line (`:60`). `run.py`'s own `machine_checks` on TICKET-0087 returns exactly:

```
['fact_spine.py', 'subject_resolution.py', 'lore_isolation.py', 'lore_selectors.py', 'single_canon_write.py', 'module_budget.py']
```

`function_length.py`, second arrow on its line, never runs; `corpus_gate.py` is not linked, although `CLAUDE.md:83-84` requires every ticket to link it. The recorded verdict (2026-09-15 17:02 UTC) lists those six checks and no other. `pipeline_state.py` requires the 11 front-matter fields, one `### Machine` then one `### Live` header, and every arrow to resolve to an existing check file; it does not enforce the `corpus_gate.py` link.

Consequence: TICKET-0087's Machine section is repaired to one arrow per line with `corpus_gate.py` linked (AMENDMENT-0087-3), and `BRIEF-0087-e`'s done-means name `python -m tooling.verify.run --ticket TICKET-0087-knowledge-subject-participants`, never `tooling/run.py`.

### R-23 -- rows render in order of first appearance, not in `_SECTION_FORMATTERS` order

*(Added by AMENDMENT-0087-3.)*

Opened: `src/world_engine/lore_render.py:27-31, 62-69, 72-112`; `frontend/src/lore/Lore.svelte:22-29, 55-63, 133-161`. [M]

Finding: `_group_rows_by_section` builds its dict with `setdefault` while walking `rows` (`:78-86`), and both `_serialize_rows_by_section` (model prompt) and `render_template` (fallback) iterate that dict. Sections therefore appear in the order their first row appears. The comment at `:30-31` ("Order here is the order rows are grouped") does not describe the code. `Lore.svelte` groups the folded trace the same way (`:57-63`) and labels sections from a six-entry `SECTION_LABEL` (`:22-29`), falling back to the raw key (`:154`).

Consequence: under `M1` the `coverage` line is rendered, prompted and traced before the knowers. The position of the two new `_SECTION_FORMATTERS` entries is documentation only. `BRIEF-0087-e` rewrites the comment from the code. `Lore.svelte` is not touched: the trace shows `knowers` and `coverage` under their raw keys.

### R-24 -- `silent_canon` prose for this selector names no entity

*(Added by AMENDMENT-0087-3.)*

Opened: `src/world_engine/lore_render.py:126-127, 155-164`; `src/world_engine/cockpit/routes/lore.py:76-93`. [M]

Finding: `_render_silent_canon` looks for an `identity` row and, finding none, renders `_SILENT_CANON_WITHOUT_ENTITY`, "Le canon ne détient rien sur ce point." The route returns `rows` and `trace` beside the prose (`:85-93`), and the folded trace lists every row.

Consequence: for an entity with no knower the prose is the entity-less sentence; the `coverage` row is present in `rows` and in the folded trace. TICKET-0087's live criterion ("`silent_canon` with the coverage row present, never an empty silence") is met there. No renderer change.

### R-25 -- the planner sees the selector through its description; the prose prompt says nothing of secrets

*(Added by AMENDMENT-0087-3.)*

Opened: `src/world_engine/lore_plan.py:25-40, 73-94`; `scripts/seed_pilot.py:1744-1774, 1783-1806`. [M]

Finding: `draft_plan` replaces `{selectors}` in the `lore_question_to_plan` user template with `_render_selectors()`, one line per `_SELECTOR_DESCRIPTIONS` entry; the seeded user template carries `{selectors}`. So a description entry is sufficient for the planner to see the selector. The seeded system prompt's JSON shape shows `entity_dossier` as its one example call. `lore_plan.py` contains no non-ASCII character today. The `lore_rows_to_prose` system prompt tells the model how to render an `is_incorrect` row and says nothing about secrets.

Consequence: no prompt edit (code `P1`). The " (secret)" suffix is guaranteed in the formatted line, so in the template fallback, and in the trace (`is_secret: true`); whether the model's prose keeps it is observed and reported, not guaranteed. The planner's routing is a REPORT-ONLY.

### R-26 -- the participant attach route, and its two callers

*(Added by AMENDMENT-0087-3. The route findings are LOT-0088 R-25 and R-26 [C]; the callers and the column were re-measured.)*

Opened: `src/world_engine/models/canon_knowledge.py:117-129` [M]; `grep -rlE "/api/facts/.*/participants" frontend/src` [M]; LOT-0088 R-25, R-26 [C].

Finding: `POST /api/facts/{fact_id}/participants` resolves the entity for existence only, with no world check, and calls `attach_participants`, whose plain `db.add` has no read before it; a duplicate `(fact_id, entity_id)` raises `IntegrityError` at commit, uncaught, HTTP 500. `FactParticipant.world_id` is `NOT NULL` (`:125`) and is stamped from the fact. The grep lists exactly `frontend/src/creation/KnowledgeEditor.svelte` and `frontend/src/creation/subjectWorklist.svelte.js`; both post only for facts they have just read to carry no participant, and both pick from world-filtered entity lists.

Consequence: the route's two gaps are unreachable from the UI and are recorded as named deferrals `D-0087-attach-duplicate` and `D-0087-attach-cross-world` (see "Named deferrals"). TICKET-0087's Machine criterion "every writer of `fact_participant` reads before it writes" overstated what `subject_resolution.py` proves (its A4 exercises `write_knowledge`, `:252-270`); it is restated.

### R-27 -- the selector, prototyped on a throwaway copy of `main`

*(Added by AMENDMENT-0087-3. Measured by running code on a copy of `2ae232b`, never on the real tree or database. [E])*

Opened: a copy of the tree with the exact edits of `BRIEF-0087-e` Scope IN items 3 to 7 applied; Python 3.12, `requirements-dev.txt`, `WORLD_ENGINE_ENV=test`; a fresh temp-file SQLite fixture built through `write_knowledge`, `create_fact` and `attach_participants`.

Finding:
- Baseline on the untouched copy: `PASS: corpus_gate — 111 check(s) discovered, 111 executed, 111 passed`. With the edits: the same line, 111 of 111.
- Individually green with the edits: `lore_selectors`, `lore_isolation` (R2 accepts all three new `select(` chains: each `.where(` names `Entity` and `world_id`), `import_cycle` (the module-level `from .writes.knowledge import knowledge_level_rank` closes no cycle), `undefined_names`, `fact_spine` (its rule 4 scans `db.add(`/`sa_insert` of `Fact`/`FactParticipant`, never a `select(`), `function_length` (`who_knows_about` is 46 lines), `module_budget` (`lore_selectors.py` 262 lines, `lore_render.py` 260), `single_canon_write`, `subject_resolution`, `npc_goal_read`, `known_reachability`.
- Behaviour on the fixture: the coverage row comes first; knowers sort by rank, then name; a knower of an arity fact carrying `role="conspirator"` is counted; an entity with no knower yields exactly one row, `coverage`, verdict `silent_canon`; `uncounted_rows` equals the sum of `row_count` over `unresolved_subjects(world_id, db)` and excludes the other world; 206 knowers on one entity give `truncated: true`, `row_count: 200`, one `coverage` row first, 199 knowers, `counted_rows: 206`.
- Named mutation for `N1`: a direct reference to `who_knows_about` written into `lore_query.py` **passes** R2 under the literal set, and fails it under the derived set with `lore_selectors R2: src/world_engine/lore_query.py names selector function(s) ['who_knows_about'] directly`.

Consequence: every contract in this lot is satisfiable by the module `BRIEF-0087-e` specifies, with `execute_plan` unmodified, and the code in the brief is the code that was run.

### R-28 -- anchors re-measured on `main`, and what they cost

*(Added by AMENDMENT-0087-3: open point O-2.)*

Opened: each file below, on `2ae232b`. [M]

| anchor | as drafted | on `main` |
|---|---|---|
| `SELECTORS` | `lore_selectors.py:199` | `:199` |
| `_SELECTOR_LOOKUPS` | `:201-209` | `:201-209` |
| `SelectorSpec`, `context_sections=()` | `:22-39` | `:22-39` |
| `_knowledge_rows`, no secrecy filter | `:139-157` | `:139-157` |
| `from .models import ...` | not anchored | `:19`, no `FactParticipant` |
| `_SELECTOR_DESCRIPTIONS` | `lore_plan.py:29-37` | `:29-37` |
| `_SECTION_FORMATTERS` | `lore_render.py:62-69` | `:62-69` |
| unknown section raises | `:80-86` | `:81-85` |
| section guard | `lore_query.py:174-179` | `:174-179` |
| truncation | `:180-186` | slice `:180-181`, trace `:184-186` |
| `content_row_count`, verdict | `:183, 192` | `:183, 192` |
| `KNOWLEDGE_LEVEL_LADDER` / `knowledge_level_rank` | `writes/knowledge.py:51-65` | `:59-61` / `:64-74` |
| `idx_fact_participant_unique`, `role` | `canon_knowledge.py:119-122` | `:119-122`, `role` `:128` |
| `SELECTOR_FUNCTION_NAMES` | `checks/lore_selectors.py:37` | `:38` |
| `EXPECTED_VERDICTS` | `:38-40` | `:39-41` |
| R2 dispatch rule | not anchored | `check_no_dispatch_outside_table`, `:131-148` |
| `lore_isolation` R8 | `:26-29` (docstring) | implementation `:404-434` |
| `lore_isolation` R1 purity | "R1 forbids `db.add(`/`.commit(`" | `:148-170`: `db.add(`, `db.commit(`, `chat(` |
| `lore_isolation` R2 | docstring | `:173-215` |

The "TICKET-0070 rule" the brief's docs section invoked does not exist: TICKET-0070 is `paused` with no brief, and `CLAUDE.md:441` already covers `lore_*.py` as "resolver/selectors/plan".

Consequence: `BRIEF-0087-e`'s anchors are regenerated from this table, each on the file that declares the property; R1 is named with its check file; the `CLAUDE.md` edit is dropped.

---

## Contract sheet

### C-01 -- `write_knowledge(..., subject_entity_ids=None)`

Produced by: BRIEF-0087-a   Consumed by: BRIEF-0087-b, c, d

Signature, the existing one with one added keyword-only parameter:

```python
def write_knowledge(
    db: Session, *, mode: str = "update", knowledge_id: Optional[str] = None,
    entity_id: Optional[str] = None, subject: Optional[str] = None,
    level: Optional[str] = None, content: Optional[Any] = None,
    source: Optional[Any] = None, is_incorrect: bool = False,
    is_secret: bool = False, share_threshold: int = 50,
    session_id: Optional[str] = None, changed_by: str = "creator_crud",
    fact_id: Optional[str] = None,
    subject_entity_ids: Optional[list[str]] = None,
) -> Knowledge
```

*(Amended by AMENDMENT-0087-1, code J2: no `role` argument; idempotency is per
`(fact_id, entity_id)`.)*

Behaviour: on a create (`knowledge_id is None`, `mode != "level_change"`),
after the fact is resolved -- attached via `fact_id` or auto-created -- every
id in `subject_entity_ids` is attached to that fact through
`attach_participants(db, fact=fact, entity_ids=[...])`.

- **No `role` argument is passed.** `attach_participants`'s default (`None`)
  stands. `role` keeps its TICKET-0082 meaning -- free text describing *how*
  an entity participates -- and is never a filter, never a marker, and never
  written by this path.
- Idempotent per `(fact_id, entity_id)`, which is what
  `idx_fact_participant_unique` enforces. An id already present on that fact
  **under any role, or none** is skipped. The guard is a read before the
  write, and it is mandatory rather than defensive: `attach_participants`
  does a plain `db.add`, so a collision raises `IntegrityError` at commit and
  aborts the surrounding transaction.
- Ignored entirely when `knowledge_id` is set, and when `mode="level_change"`.
  Passing it in either case is not an error and changes nothing.
- `None` and `[]` both mean "no subject" and are the default. Behaviour with
  the parameter absent is byte-for-byte the behaviour before this lot.
- Validation is the caller's. `write_knowledge` does not re-check that the
  ids are active entities of the fact's world; `attach_participants` still
  raises on a typed fact.

Error and empty cases: `attach_participants` raises `ValueError` on a typed
fact -- unreachable on this path, since every fact `write_knowledge` touches
on a create is free-standing (R-03), but not defended against here.

### C-02 -- `subject_resolve.resolve_subject(subject, world_id, db)`

Produced by: BRIEF-0087-a   Consumed by: BRIEF-0087-b, c, d

New module `src/world_engine/subject_resolve.py`. It imports
`lore_resolve.resolve_named` and `_CATEGORY_ENTITY_TYPE`; it never re-implements
a rung and never calls a model.

```python
@dataclass(frozen=True)
class SubjectResolution:
    verdict: str                      # "matched" | "ambiguous" | "unmatched"
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]    # sorted; empty on unmatched
    category: Optional[str]           # the category that matched; None otherwise

def resolve_subject(subject: str, world_id: str, db: Session) -> SubjectResolution
```

Return shape, every case:

- Walks the three categories of `_CATEGORY_ENTITY_TYPE` in sorted key order,
  calling `resolve_named(subject, category, world_id, db)` for each.
- Exactly one distinct `entity_id` across all `matched` categories, and no
  category returned `ambiguous` -> `matched`, with `entity_id` set,
  `candidate_ids` the one-tuple, and `category` the matching category.
- Two or more distinct matched ids, or any category `ambiguous` ->
  `ambiguous`, `entity_id` None, `candidate_ids` the sorted union of every
  candidate seen, `category` None.
- No category matched -> `unmatched`, `entity_id` None, `candidate_ids` `()`,
  `category` None.
- An empty or whitespace-only `subject` -> `unmatched`. Never a rung call.

The function never picks between candidates. Ambiguity rises; it is not
resolved.

### C-03 -- the `new_knowledge` payload key `subject_entity_id`

Produced by: BRIEF-0087-b   Consumed by: BRIEF-0087-b only

`ProposedMutation.payload` gains one optional key on `mutation_type ==
"new_knowledge"`:

```
"subject_entity_id": "<entity id>" | null | absent
```

- Absent and `null` are identical and mean "no subject". Every payload
  written before this lot is therefore valid unchanged.
- The value is untrusted input, whether it came from the model or from a
  client. `_mutation_apply_new_knowledge` re-looks it up: it must name an
  `entity` row with `status = "active"` and `world_id == mut.world_id`.
- A value failing that check is a returned error string from the apply
  branch -- the same shape as the branch's existing
  `"new_knowledge: payload must contain entity_id (or set target_id)"` --
  so the mutation stays unapplied and visible in the queue. It is never
  dropped, and never written as a null subject.
- `payload["subject"]` keeps its exact current meaning and its exact current
  role in `_mutation_match_key`. The dedup key does not change.

### C-04 -- selector family contract: `who_knows_about`

Produced by: BRIEF-0087-e   Consumed by: BRIEF-0087-e

This is the family contract for selector rows. It is written before the
member and re-read after it, per the protocol's step 2.

```python
def who_knows_about(entity_id: str, world_id: str, db: Session) -> list[dict]
```

Registered as:

```python
"who_knows_about": SelectorSpec(
    fn=who_knows_about, arity=2, row_cap=200,
    arg_kinds=("entity_id", "world_id"), context_sections=("coverage",),
)
```

Returns a flat list of row dicts. Every row carries `"section"` (R-13).

*(Amended by AMENDMENT-0087-1, code J2: no role filter on the join;
`uncounted_rows` counts facts with no participant at all.)*

*(Amended by AMENDMENT-0087-3, code M1: the `coverage` row is the FIRST row,
not the last, so `execute_plan`'s tail truncation can never drop it (R-13);
the knowers join goes `Knowledge.fact_id -> FactParticipant.fact_id`
directly, with no `Fact` join, since neither side needs a `fact` column;
`uncounted_rows` is defined as an outer join and equals the sum of `C-06`'s
`row_count` for the same world (R-27).)*

`section="knowers"` -- zero or more. One per `knowledge` row whose fact
carries a `fact_participant` with `entity_id == <the asked entity>`, **with no
role filter**, the knowing entity being world-scoped at query construction.
`idx_fact_participant_unique` guarantees at most one participant row per
`(fact, entity)`, so no knowledge row can appear twice. Required keys, every
one present on every row:

```
section, knower_entity_id, knower_name, level, content, source,
is_incorrect, is_secret, subject_name
```

Ordered by `knowledge_level_rank(level)` descending
(`writes/knowledge.py:64-74`), then by `knower_name` ascending, so the order
is total and stable. The sort runs in Python after the fetch; it filters
nothing, so world scoping stays at query construction.

`section="coverage"` -- **exactly one, always, including when there are zero
knowers, and always the first row returned.** Required keys:

```
section, subject_name, counted_rows, uncounted_rows
```

- `counted_rows` is the number of `knowers` rows before `row_cap` truncation.
- `uncounted_rows` is the number of `knowledge` rows in this world whose fact
  carries **no participant at all** -- the rows this selector structurally
  cannot see. Computed as a count over `Knowledge` joined to `Entity`,
  outer-joined to `FactParticipant` on `fact_id`, where
  `Entity.world_id == world_id` and `FactParticipant.id IS NULL` -- the same
  shape as `C-06`, so it equals the sum of `C-06`'s `row_count` for that
  world.
- `subject_name` is the asked entity's `name`.

Because `coverage` is declared in `context_sections`, it never counts toward
`content_row_count`, so a target with no knowers yields `silent_canon` and
not a false `answered` (R-13). Because it is first, a selector returning
`row_cap` or more knowers keeps it: `execute_plan` keeps `coverage` plus the
first `row_cap - 1` knowers, records `truncated: true`, and `counted_rows`
still states the full count.

Error and empty cases: an `entity_id` that does not exist in `world_id`
never reaches this function -- `execute_plan` returns `unknown_entity` at
mention resolution first. This function assumes a resolved, world-scoped
entity and does not re-check it.

### C-05 -- section formatters for the two new sections

Produced by: BRIEF-0087-e   Consumed by: BRIEF-0087-e

`lore_render._SECTION_FORMATTERS` gains two entries, matching the existing
one-line style of `_format_knowledge` (`lore_render.py:45-47`):

```
"knowers"  -> "<knower_name> — <level> : <content>" 
              + " (croyance fausse)" when is_incorrect
              + " (secret)" when is_secret
"coverage" -> "<counted_rows> ligne(s) comptée(s) sur « <subject_name> » ; 
              <uncounted_rows> ligne(s) de ce monde portent un sujet non résolu 
              et ne sont pas comptées."
```

Both markers are suffixes on the same line, in that order: false belief
first, secret second, so a row that is both reads deterministically. The
literal wording above is verbatim; the executor copies it.

*(AMENDMENT-0087-3: the position of the two entries in the dict is
documentation only -- sections render in order of first appearance in the
rows (R-23), so `coverage` renders before `knowers`.)*

### C-06 -- the unresolved residue query

Produced by: BRIEF-0087-c   Consumed by: BRIEF-0087-c, d

```python
def unresolved_subjects(world_id: str, db: Session) -> list[dict]
```

*(Amended by AMENDMENT-0087-1, code J2: "no participant at all", not "no
`role="subject"` participant".)*

Lives in `subject_resolve.py` beside `C-02`. One row per distinct
`knowledge.subject` in `world_id` whose fact carries **no participant at
all**. Required keys:

```
subject, fact_ids (tuple, sorted), row_count, resolution (SubjectResolution)
```

`resolution` is `C-02`'s verdict for that subject, computed once per distinct
subject, never once per row. Ordered by `row_count` descending, then
`subject` ascending.

This is the one query behind both the backfill's report and the creator
surface's worklist, so the two can never disagree about what is unresolved.

---

## Gate output

### (a) Unverified symbol -- tick, after one repair

Run once, it failed: five briefs named symbols absent from the RECON --
`KnowledgeEditor.svelte` and `sheetRequest.svelte.js` (BRIEF-0087-d),
`prompt_registry` / `current_prompt` / `write_prompt_version` (BRIEF-0087-b),
`knowledge_level_rank` (BRIEF-0087-e), `scripts/backup.py` (BRIEF-0087-c),
and the three dedup guards named in every Scope OUT. R-17, R-18 and R-19 were
added and R-04 and R-16 extended in response. Re-run passes.

Every symbol named across the five briefs now appears in a finding above:
`knowledge` and its columns (R-01), `fact_participant` / `attach_participants`
/ `fact_spine.py` (R-02), `create_fact` and the auto-creation fallback
(R-03), `write_knowledge` / `writes/__init__.py` / `KNOWLEDGE_LEVELS` /
`KNOWLEDGE_LEVEL_LADDER` / `knowledge_level_rank` (R-04),
`_build_payload_new_knowledge` / `_content_to_subject_slug` /
`_emit_new_knowledge` / `ProposedMutation.payload` /
`_mutation_apply_new_knowledge` (R-05), `crud/knowledge.py` participant
routes and `_create_knowledge_core` (R-08), `_knowledge_rows` (R-11),
`SELECTORS` / `_SELECTOR_LOOKUPS` / `SelectorSpec` /
`_SELECTOR_DESCRIPTIONS` / `_SECTION_FORMATTERS` / `SELECTOR_FUNCTION_NAMES`
(R-12), `validate_plan` / `execute_plan` / `context_sections` / `row_cap` /
the five verdicts (R-13), `resolve_named` / `NamedResolution` /
`_CATEGORY_ENTITY_TYPE` / `NAMED_RUNGS` / `normalize_surface` /
`rung_named_token` (R-14), the CLAUDE.md invariants and `_mutation_match_key`
(R-15), the two script conventions and `backup.py` (R-16),
`KnowledgeEditor.svelte` / `sheetRequest.svelte.js` / `reloadEntity` /
`Lore.svelte` / `frontend_build_fresh.py` / `static_asset_freshness.py` /
`creation_island.py` / `json_ui_boundary.py` (R-17), `prompt_registry` /
`current_prompt` / `write_prompt_version` / `prompt_coverage.py` /
`prompt_lean.py` / `prompt_version.py` / `prompt_model_write.py` (R-18), the
three dedup guards and the accepted gap (R-19).

`import_cycle.py`, `undefined_names.py`, `module_budget.py`,
`function_length.py`, `single_canon_write.py` and `corpus_gate.py` are named
only in done-means lines as gates to run, never as code a brief asserts a
fact about; they are covered by gate (e) below rather than by a finding.

**Re-run at AMENDMENT-0087-1, and the check failed a second time.** It had
passed on a lot whose anchor asserted, falsely, that `fact_participant` has
no uniqueness constraint -- because the *symbol* appeared in R-02 while the
*property* was never traced. `idx_fact_participant_unique`,
`idx_fact_participant_entity` and `FactParticipant.role` are now in R-02,
read from `models/canon_knowledge.py:112-129` rather than from the module
that writes the table.

This check is therefore tightened for the rest of this lot, and proposed as a
`brief-generation-protocol.md` §5(a) amendment to be decided separately:
every **property** an anchor asserts must trace to a finding that opened the
file where that property is *declared*. A table constraint traces to the
model module, never to a writer. A finding about a writer does not license a
claim about a schema.

**Re-run at AMENDMENT-0087-3, with the declaring-file rule of the amended
protocol.** Every property `BRIEF-0087-e` asserts now traces to a finding
that opened the file declaring it:

| property | finding | declaring file opened |
|---|---|---|
| selector registries, `SelectorSpec` fields | R-12, R-28 | `lore_selectors.py` |
| tail truncation, section guard, verdict rule | R-13, R-28 | `lore_query.py` |
| grouping order, formatter vocabulary, unknown-section raise | R-23, R-28 | `lore_render.py` |
| silent-canon prose without identity | R-24 | `lore_render.py` |
| description injection into the planner | R-25 | `lore_plan.py`, `seed_pilot.py` |
| level ladder and rank | R-04, R-28 | `writes/knowledge.py` |
| unique key, `role`, `world_id` on `fact_participant` | R-02, R-26, R-28 | `models/canon_knowledge.py` |
| R2 dispatch rule and its literal | R-12, R-27, R-28 | `checks/lore_selectors.py` implementation |
| R1 purity, R2 world scoping, R8 | R-28 | `checks/lore_isolation.py` implementation |
| `fact_spine` rule 4 scope | R-27 | `checks/fact_spine.py` implementation |
| module-level import edges | R-27 | `checks/import_cycle.py` |
| what `run.py` runs | R-22 | `tooling/verify/run.py` |
| how `e` can start | R-21 | `pipeline.md`, `brief-exec.md`, `settings.json` |

Removed rather than traced: "the TICKET-0070 rule" (R-28: no such rule),
"the existing French one-line style" of `_SELECTOR_DESCRIPTIONS` (R-25: the
existing two are unaccented ASCII; the verbatim text stands on its own), and
"R1 forbids `db.add(`" without a check name (R-28).

### (b) Unwalked rule -- case table for `who_knows_about`

| input class | rows returned | `content_row_count` | verdict |
|---|---|---|---|
| mention does not resolve | selector never runs | -- | `unknown_entity` |
| mention ambiguous | selector never runs | -- | `ambiguous_mention` |
| selector not in whitelist | selector never runs | -- | `unsupported_selector` |
| resolved entity, no subject participant anywhere | 1 coverage | 0 | `silent_canon` |
| resolved entity, 1 <= N <= 199 knowers | 1 coverage, then N knowers | N | `answered` |
| resolved entity, N >= 200 knowers | 1 coverage, then the first 199 knowers; `truncated: true`; `counted_rows` = N | 199 | `answered` |
| knower row `is_secret` | included, suffix " (secret)" | counts | `answered` |
| knower row `is_incorrect` | included, suffix " (croyance fausse)" | counts | `answered` |
| knower row both | included, both suffixes, false belief first | counts | `answered` |
| the asked entity is a TICKET-0082 arity participant on a knowledge-bearing fact | included as a knower row | counts | `answered` |
| the asked entity participates twice on one fact | impossible: `idx_fact_participant_unique` | -- | -- |

*(Re-walked at AMENDMENT-0087-3.)* The row the table first stated,
"N > 200 -> 200 knowers + 1 coverage", was unreachable: with `coverage`
last, the tail slice at `lore_query.py:180-181` cut it (R-13). With
`coverage` first, every row above was run on a fixture (R-27), including
N = 206.

Every outcome is reachable and every one is correct. The `silent_canon` row
is the one that would have been unreachable had `coverage` been left out of
`context_sections` -- which is why it is in it. The last two rows were added
by AMENDMENT-0087-1: under J2 an arity participant counts, deliberately, and
the unique key is what makes a duplicated knower row impossible rather than
merely unlikely.

Case table for `C-01`'s parameter *(re-walked at AMENDMENT-0087-1)*:

| call shape | effect |
|---|---|
| create, `subject_entity_ids=None` or `[]` | pre-lot behaviour exactly |
| create, one id | one participant row on the new fact, `role` left NULL |
| create, id already attached to that fact under any role, or none | no second row, no `IntegrityError` |
| create, explicit `fact_id`, ids given | attached to that existing fact |
| create, same id twice in one `subject_entity_ids` list | one row: the guard runs per id, in order |
| update (`knowledge_id` set), ids given | ignored, no write, no error |
| `mode="level_change"`, ids given | ignored, no write, no error |

### (c) Unenumerated generalization -- enumerations pasted

**Every universal claim in this lot traces to one of these.**

Subject resolution, replaying `lore_resolve` over production (R-06):

```
matched            subjects=  69 ( 22.1%)  rows=  98 ( 15.9%)
ambiguous          subjects=   0 (  0.0%)  rows=   0 (  0.0%)
unmatched          subjects= 243 ( 77.9%)  rows= 517 ( 84.1%)
TOTAL              subjects= 312           rows= 615
```

Per world, distinct subjects matched / total:

```
Silka  9/46   Manoir des ténèbres 4/38   Verkhaal 8/36   Kha'Zix 3/35
Nestia 9/32   Nebula des Éclats 11/29    Les Ténèbres de Valnir 14/27
le château de Valdur 5/27   Le Manoir 4/25   La Dichotomie 2/17
```

Answerable targets after backfill (R-07):

```
Nebula des Éclats       9 / 26   (34.6%)
Verkhaal                6 / 57   (10.5%)
Silka                   6 / 45   (13.3%)
le château de Valdur    4 / 20   (20.0%)
Manoir des ténèbres     4 / 27   (14.8%)
Les Ténèbres de Valnir  3 / 32   ( 9.4%)
Le Manoir               3 / 17   (17.6%)
Kha'Zix                 3 / 23   (13.0%)
Nestia                  3 / 31   ( 9.7%)
La Dichotomie           1 / 19   ( 5.3%)
TOTAL                  42 / 297  (14.1%)
```

Verkhaal targets, with knower counts:

```
Maelis                        6    La Mer Rouge                  2
La Commune des Pauvres        1    La Société des Entrepreneurs  1
Le quartier populaire         1    La Maison des Maitres         1
```

Indexes on `fact_participant` and its two sibling tables, enumerated from
`sqlite_master` on production *(added at AMENDMENT-0087-1 -- their absence
from the first pass is what let the false anchor through)*:

```
fact_participant  sqlite_autoindex_fact_participant_1   (pk)
fact_participant  idx_fact_participant_entity           ON (entity_id)
fact_participant  idx_fact_participant_unique  UNIQUE   ON (fact_id, entity_id)

fact              sqlite_autoindex_fact_1               (pk)
fact              idx_fact_world                        ON (world_id)
fact              idx_fact_relation                     ON (relation_id)
fact              idx_fact_event                        ON (event_id)
fact              idx_fact_world_law                    ON (world_law_id)

fact_default      sqlite_autoindex_fact_default_1       (pk)
fact_default      idx_fact_default_fact                 ON (fact_id)
fact_default      idx_fact_default_unique      UNIQUE   ON (fact_id, scope_type, scope_id)

knowledge         idx_knowledge_entity                  ON (entity_id)
knowledge         idx_knowledge_subject                 ON (subject)
knowledge         idx_knowledge_fact                    ON (fact_id)
```

Fact spine population (R-03):

```
knowledge rows                615
distinct fact_id              312
distinct subject              310
knowledge -> free-standing    615   (relation/event/world_law: 0)
fact_participant rows           0
fact_default rows               0
fact rows total               368   (free-standing 312, relation-typed 56)
```

Producer distribution (R-10):

```
knowledge rows with session_id           12 / 615
distinct subjects containing "_"         15 / 310
knowledge rows with NULL source         295 / 615
```

Ticket numbering (TICKET-0087 is free): `tooling/tickets/` enumerated, highest
deposited id is `TICKET-0086-verify-check-drift.md`. Full listing runs
`TICKET-0001` through `TICKET-0086` with 0002, 0047, 0068 absent.

Selector registry, current state (R-12):

```
SELECTORS                  = ("entity_dossier", "world_factions")
_SELECTOR_DESCRIPTIONS     = {"entity_dossier", "world_factions"}
_SECTION_FORMATTERS        = {identity, relations, knowledge, memberships, goals, factions}
SELECTOR_FUNCTION_NAMES    = {"entity_dossier", "world_factions"}   # checks/lore_selectors.py:37
EXPECTED_VERDICTS          = {answered, ambiguous_mention, unknown_entity,
                              silent_canon, unsupported_selector}
```

Added at AMENDMENT-0087-3 -- `run.py`'s own parser on TICKET-0087 before
the repair (R-22):

```
['fact_spine.py', 'subject_resolution.py', 'lore_isolation.py', 'lore_selectors.py', 'single_canon_write.py', 'module_budget.py']
```

Callers of the participant routes under `frontend/src` (R-26):

```
$ grep -rlE "/api/facts/.*/participants" frontend/src
frontend/src/creation/subjectWorklist.svelte.js
frontend/src/creation/KnowledgeEditor.svelte
```

Corpus on a copy of `2ae232b`, before and after the brief's edits (R-27):

```
PASS: corpus_gate — 111 check(s) discovered, 111 executed, 111 passed
PASS: corpus_gate — 111 check(s) discovered, 111 executed, 111 passed
```

### (d) Un-rederived contract -- tick

`C-04` is the selector family contract. It was written before
`who_knows_about` was specified and re-read after `C-05` was added; both new
sections carry the `section` key and both have a formatter, which is the
failure mode the re-read exists to catch. `C-02` and `C-06` are the resolver
family: written once in `subject_resolve.py`, consumed verbatim by three
briefs, never re-described.

### (e) Unsatisfiable check -- modules named

- `verify/checks/fact_spine.py` -- satisfied by `writes/facts.py`, unchanged. The lot adds participant rows only to free-standing facts, which is assertion 1's pass condition.
- `verify/checks/lore_isolation.py` R8 / R14 -- satisfied by `lore_plan.py` and `lore_render.py` gaining their entries in BRIEF-0087-e. Both are pure registry edits; neither module needs anything the check forbids.
- `verify/checks/lore_selectors.py` R1/R2/R3/R6 -- satisfied by `lore_selectors.py`, **provided `SELECTOR_FUNCTION_NAMES` at line 37 gains `who_knows_about`**. Without that edit R2 passes vacuously for the new selector. This is the one check in the lot that a blunt reading would leave silently uncovered. *(Superseded by AMENDMENT-0087-3, code `N1`: R2 derives its names from the `fn=` keyword of every `SelectorSpec(...)`, so no edit of a literal can be forgotten; satisfied by `lore_selectors.py` declaring `fn=who_knows_about`, R-27.)*
- `verify/checks/creation_island.py` -- **this is the entry that should have caught BRIEF-0087-d item 5 at drafting.** Gate (e) asks, for every G1 gate a brief must pass, which module satisfies it and what that module needs which the check forbids. Item 5 required `creation_island.py` to pass and named no such module, because none can exist today: rule 2 demands a migration provenance a greenfield panel does not have (R-20). The answer gate (e) prescribes -- *specify the module the lot does not yet have* -- is TICKET-0088. Deferring item 5 is that answer, taken one ticket out.
- **New check `verify/checks/subject_resolution.py`** -- required by two acceptance criteria that no existing check covers: that `subject_resolve.py` reaches canon only through `lore_resolve` rungs and contains no `chat(`, and that an out-of-world `subject_entity_id` is refused at apply. It needs a DB fixture (the second assertion is behavioural), which the `fact_spine.py` idiom already provides: fresh temp-file SQLite, `WORLD_ENGINE_DATABASE_URL` set before any `world_engine` import, vacuity-guarded, never touching the real database. It is specified in BRIEF-0087-b. Placing it in its own file rather than extending `fact_spine.py` follows the standing rule: when a blunt check would have to make an exception, the legitimate thing moves to its own file.
- `verify/checks/frontend_build_fresh.py` and `static_asset_freshness.py` -- satisfied by BRIEF-0087-d running the build and committing its output, which is the project's existing contract for a frontend change (R-17). `creation_island.py` and `json_ui_boundary.py` are satisfied by keeping the new panel inside the Creation shell's existing conventions; a panel that reached into another shell would fail them, which is the structural reason the placement is not free.
- *(AMENDMENT-0087-3.)* `verify/checks/import_cycle.py` -- satisfied by `lore_selectors.py` importing `knowledge_level_rank` at module level; no edge back from `writes/` to `lore_*` exists (R-27). `verify/checks/decisions_index.py` -- satisfied by `BRIEF-0087-e`'s ADR header in the strict form and a regenerated `DECISIONS_INDEX.md`. `verify/checks/pipeline_state.py` -- satisfied by TICKET-0087's repaired Machine section, whose every arrow names an existing check. `verify/checks/corpus_gate.py` -- satisfied by the whole tree; measured 111 of 111 with the brief's edits (R-27).
- `verify/checks/single_canon_write.py`, `module_budget.py`, `function_length.py` -- satisfied by the existing modules. `lore_selectors.py` is 210 lines and `writes/knowledge.py` 212; neither approaches the 1000-line cap, and no function in this lot approaches 80 lines.

## Named deferrals

*(Section added by AMENDMENT-0087-3, code `G1`.)*

- **D-0087-attach-duplicate** (S-2). `POST /api/facts/{fact_id}/participants` does not read before it writes, so a duplicate `(fact_id, entity_id)` answers HTTP 500 (R-26). Unreachable from the two callers, which post only for facts they have just read to carry no participant. *Reactivate when* `grep -rlE "/api/facts/.*/participants" frontend/src` lists a file other than `frontend/src/creation/KnowledgeEditor.svelte` and `frontend/src/creation/subjectWorklist.svelte.js`.
- **D-0087-attach-cross-world** (S-3). The same route checks that the entity exists, not that it belongs to the fact's world (R-26). Unreachable from both callers, whose pickers are world-filtered. Fixing the route was option `G2`, rejected with this condition. *Reactivate when*
  `SELECT COUNT(*) FROM fact_participant fp JOIN entity e ON e.id = fp.entity_id WHERE e.world_id <> fp.world_id`
  returns more than 0 on the production database.

## Amendments

### AMENDMENT-0087-1 -- `fact_participant` is keyed `(fact_id, entity_id)`; the role discriminator is dropped

Raised by Claude Code as a STOP on a Mini-RECON anchor while opening
BRIEF-0087-a, before any code was touched. Decided by Nia, code `J2`.
Full text: `tooling/tickets/AMENDMENT-0087-1-participant-unique-key.md`.

BRIEF-0087-a's anchor asserted that `FactParticipant` has no uniqueness
constraint. It has `idx_fact_participant_unique` on `(fact_id, entity_id)`,
unique, added at TICKET-0082 and predating this RECON. The claim was wrong,
not stale: R-02 was traced from `writes/facts.py` while the anchor asserted a
property of `models/canon_knowledge.py`, whose indexes were never listed.

Under J2 the `role="subject"` discriminator is dropped entirely. A
participant is an aboutness claim; `who_knows_about` matches any participant
row for the asked entity. `role` keeps its TICKET-0082 meaning as free text
and is never a filter. Deferred with a grep-verifiable reactivation
condition: a discriminator returns the first time a fact carries a
participant that is not a subject of the knowledge attached to it.

Amended here: **R-02** (corrected in place, with the index enumeration),
**C-01** (no `role` argument; idempotency per `(fact_id, entity_id)`; the
read-before-write guard is mandatory, not defensive), **C-04** (no role
filter; `uncounted_rows` counts facts with no participant at all), **C-06**
(same clause). Gate checks (a), (b) and (c) re-run; (d) and (e) unchanged.
All five briefs regenerated.

No measured number changed: the 98-row / 42-entity baseline never depended on
`role`.

### AMENDMENT-0087-2 -- the residue worklist is deferred to TICKET-0088

Raised by Claude Code as a STOP on BRIEF-0087-d Scope IN item 5, with items
1-4 committed and green. Decided by Nia, code `K3`.
Full text: `tooling/tickets/AMENDMENT-0087-2-residue-worklist-deferred.md`.

Item 5 told the executor to "follow the existing panel conventions of the
Creation shell ... where an existing panel already does the thing, copy it".
No such convention exists for a greenfield panel: `CREATION_ISLANDS` is a
migration-provenance ledger whose 16 entries all carry `migratedBy:
TICKET-0058` or `TICKET-0059`, and `creation_island.py` rule 2 demands a
non-empty `retiredPrefixes` that a surface with no legacy predecessor cannot
honestly supply (R-20). Inventing one would be the check-gaming R-12 names.

Rejected: K2, landing the worklist as a child section of `Queue.svelte` --
that component's header calls its empty states *"the surface's meaning, not
decoration"*, and a second unrelated list degrades it permanently to save one
ticket. Rejected: K4, the Lore shell -- it would reopen TICKET-0085's
read-only lock.

Amended here: **R-20** added; the dependency graph gains TICKET-0088 between
BRIEF-0087-d and BRIEF-0087-e; the brief list entry for `d` is corrected;
gate (e) is restated around the check that should have caught this.
BRIEF-0087-d regenerated; BRIEF-0087-e gains an ordering line only.

`GET /api/worlds/{world_id}/unresolved-subjects` and `C-06` both stand: the
route keeps BRIEF-0087-c's report as a live reader and TICKET-0088's panel as
a named second one.

### AMENDMENT-0087-3 -- closing repairs before `e`: the Machine section, the coverage row, R2's literal, the start

Decided by Nia: `G1` (TICKET-0088 decision session, 2026-09-16; deposit
clause amended by `H1`, 2026-09-17), then `L1`, `M1`, `N1`, `P1`
(2026-09-21). Full text:
`tooling/tickets/AMENDMENT-0087-3-closing-repairs.md`.

Amended here: the dependency graph note; **R-12** (line `:38`; literal
removed under `N1`); **R-13** (tail truncation); **R-21 to R-28** added;
**C-04** (`coverage` first, join shape, `uncounted_rows` definition);
**C-05** (order note); gate (a) re-run as a property trace, (b) case table
re-walked, (c) three enumerations, (e) restated; **Named deferrals**
section added with `D-0087-attach-duplicate` and
`D-0087-attach-cross-world`. TICKET-0087's Machine section repaired.
BRIEF-0087-e regenerated. BRIEF-0087-a to -d untouched: executed and merged.
