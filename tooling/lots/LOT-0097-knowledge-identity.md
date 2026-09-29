# LOT — TICKET-0097 "Knowledge identity — a knowledge row is who knows which fact"

## Objective and cut

What an entity knows becomes identified by the fact it knows. The dedup key,
every bridge to other tables, every label and every model-facing reference
that ran through the free-text `knowledge.subject` move to the fact: its id
(identity), its content (the label), its participants (aboutness). Models
name a fact only by a code from a coded list the code built. The column is
dropped last (v2.10), once `knowledge_identity.py` K3 shows no reader.

The lot stops before the lore writing path: nothing here lets a creator
attach a character to an existing fact from prose, and the editors only
lose their Subject field (K1).

## Briefs in this lot

- **A — identity** (schema v2.09): unique `(entity_id, fact_id)`,
  `discoverable_detail.fact_id`, `migrate_v2_09_knowledge_identity.py`, the
  pilot seed shares its facts, `knowledge_identity.py` K1-K3; closes 0096.
- **B — the mutation pipeline**: `fact_refs.py` (C-01, C-03); every dedup and
  apply keyed on the fact; M1; N1; H1's apply half. K4.
- **C — overhearing and the tick**: coded lists (L1, Z2), `world_tick.py`
  rule 5 retargeted, `apply_ticket_0097_fact_code_prompts.py`. K5.
- **D — day gates**: the planner's learnable-fact list (D1′a), gates by fact
  id, the day chain's proposals carry `fact_id`, Journée shows the fact.
  `day_plan.py` R26/R28 retargeted. K6.
- **E — play readers**: contexts, Lore dossier, link agent (G1),
  signposts (H1), writers stop naming a subject. `link_agent_strata.py`
  rule 3 retargeted. K7.
- **F — the creator surface**: no Subject field (K1), generators without
  subject, `unbound_facts.py` replaces `subject_resolve.py` (I1), the
  « Sujets » worklist lists facts (J1). K8.
- **G — drop the column** (schema v2.10): `migrate_v2_10_drop_knowledge_subject.py`,
  `write_knowledge` without `subject`, checks' fixtures. K9.

## Dependency graph

Strictly sequential, A → B → C → D → E → F → G.

- B needs A's unique index (the apply guard `_payload_fact` exists to keep
  it from aborting a SAVEPOINT) and A's `discoverable_detail.fact_id`.
- C and D consume B's `fact_refs.py` (C-01, C-03).
- E, F and G each lower `knowledge_identity.py`'s census (K3) created in A;
  the census makes any order other than the written one red, which is the
  point: a brief that removes a reference records it.
- G needs every reader gone (K3 at its final table) — by dependency.
- Each brief's diff applies on the previous brief's tree: they share
  `knowledge_identity.py` (every brief), `apply_ticket_0097_fact_code_prompts.py`
  (C creates it, D and F extend it) and the decision registry. The
  functional split (C before D, E before F) is a choice for review size;
  the textual chaining makes it strict.

## RECON

Opened on `main` at `89fc38a` (merge of PR #126, `ticket/0096`), then
prototyped on a copy (branch `proto/0097`): every brief's commit ran the full
corpus green (126/126), mid-lot and final.

### R-01 — `knowledge` (model)
Opened: `src/world_engine/models/canon_knowledge.py:198-235` (declares the table).
Finding: columns `id, entity_id, fact_id (NOT NULL, FK fact), subject (str,
NOT NULL), level, content (SQL name, attr `content_raw`), source,
is_incorrect, is_secret, share_threshold, acquired_at, updated_at,
session_id, change_history`. Indexes: `idx_knowledge_entity(entity_id)`,
`idx_knowledge_subject(subject)` (line 206), `idx_knowledge_fact(fact_id)`
(line 207). No unique index on `(entity_id, fact_id)`.
Consequence: A adds `idx_knowledge_entity_fact` UNIQUE; G drops the subject
index then the column (SQLite refuses `DROP COLUMN` on an indexed column).

### R-02 — the five jobs of `knowledge.subject`
Opened: every file below, at the lines named; enumeration in gate (c).
Finding:
- identity/dedup: `analyzer_transcript._mutation_match_key` (531),
  `tick._tick_npc_dedup_note` (`(entity_id, subject)`, 142),
  `cockpit/routes/mutations._dup_tick_new_knowledge` (166) and the
  conversation-sourced guard (~340), `cockpit/mutations._knowledge_leg_already_applied`
  (~76), `_mutation_apply_knowledge_change` (473-486), the resource leg
  (~739-750), `analyzer._overhearing_existing_keys` (76-104);
- bridges: `scene_format.active_signposts` (`discoverable_detail.subject` ↔
  `knowledge.subject`, 44-65), `cockpit/play_discovery._propose_engine_discovery`
  (36), `day_plan._eval_knowledge` / `_anchorable_subjects` /
  `_held_subjects` (142, 327-352), `day_mutations` (170, 210, 232-246),
  `link_author` (`npc:{id}`: 161, 310, 514, 588), `link_context` (69-110),
  `tick._tick_build_npc_indexes` (`secret_subjects`, 102);
- labels: `context._knowledge_line` / `_mj_knowledge_line` /
  `_mj_context_player_knowledge` (126, 682, 809), `tick_context._knowledge_line`
  (128), `lore_selectors._knowledge_rows` (182), `lore_render._format_knowledge`
  (62), `cockpit/crud/_shared` (`KNOWLEDGE_FIELDS` 222, `_knowledge_dict` 254);
- aboutness: `subject_resolve.py` (whole module), `cockpit/crud/knowledge.list_unresolved_subjects`
  (142), `day_mutations._emit_new_knowledge` (246);
- writers: `writes/knowledge.py` (`write_knowledge`, `apply_knowledge_patch`,
  `upsert_knowledge_row`), `writes/facets._write_creator_meta` (187),
  `writes/relations` (384), `knowledge_resolve.resolve_default_rows` (359),
  `cockpit/crud/knowledge` (create/update), `cockpit/routes/creator` (PC,
  572-629), `cockpit/routes/npc_agent` (224), `entity_author` (55, 213-256),
  `tick_normalize._tick_normalize_new_knowledge` (718).
Consequence: one brief per group; the census K3 pins what is left.

### R-03 — prod data (Nia's machine, 2026-09-28, read-only `mode=ro`)
Opened: Nia's run of `q1b_measure.py` on `~/.world_engine/world_engine.db`.
Finding (verbatim excerpts):
```
== M0 schema version == [(1, 'v2.08', '2026-09-27 21:35:07.202136')]
== M2 subjects split over >1 fact, per world ==
'Nestia': split_subjects=1 rows=20 facts_involved=20
'Verkhaal': split_subjects=1 rows=5 facts_involved=5
'La Dichotomie': split_subjects=1 rows=4 facts_involved=4
'le château de Valdur': split_subjects=1 rows=2 facts_involved=2
  (all four: 'creator_meta')
== M3 facts carrying >1 distinct subject == count: 0
== M4 same entity holds the same subject on >1 row == count: 3
  ('6974bf4a-…', 'Lily', 2) ('ce441cec-…', 'npc:ffd887a6-…', 2) ('fee5dd2f-…', 'Lily', 2)
same entity + same fact on >1 row: 3
== M5 == content == subject 607 ; content != subject 34 (all 'creator_meta')
facet of facts referenced by knowledge: [(None, 291), ('histoire', 34), ('lien', 39)]
== M7 == npc:% subjects: 269 ; creator_meta subjects: 34 ; 'unknown' subjects: 0
== M8 == details: (5, 5) ; detail subjects present as a knowledge subject: 0
== M9 == [('knowledge_change','approved',1), ('new_knowledge','applied',16),
          ('new_knowledge','proposed',5), ('new_knowledge','rejected',2)]
```
Consequence: E1 (a guard, no merge), F1 (three absorptions), G (269 rows'
facts get their participant), H1 (nothing to backfill), N1 (the one approved
`knowledge_change` stays visible, refused at apply).

### R-04 — `fact_participant`, `fact`, `create_fact`, `attach_participants`
Opened: `models/canon_knowledge.py:86-140` (declares both tables),
`writes/facts.py:50-186`.
Finding: `idx_fact_participant_unique(fact_id, entity_id)` UNIQUE (135);
`fact.content` is `content_raw` NOT NULL; `fact.facet` nullable;
`create_fact` requires a `facet` (a `FACETS` key) and refuses a typed facet
on a free fact; `attach_participants` refuses a typed fact.
Consequence: every fact born in this lot uses `facet="information"` through
`create_fact`; `unbound_facts` lists free facts only.

### R-05 — `write_knowledge` fallback
Opened: `writes/knowledge.py:178-240`.
Finding: without `fact_id`, creates a fact with `content = subject or
"unknown"` (216-224), so every overheard or discovered row got its own fact.
Consequence: B changes the content to the row's stored text (M1); G removes
the parameter.

### R-06 — the pilot seed splits two subjects
Opened: `scripts/seed_pilot.py:3403-3450`, a fresh `init_db` + `seed_pilot`.
Finding: `magic_existence` and `magic_awakening` are each held by Reike and
Senna on two facts (13 rows, 11 subjects, 13 facts).
Consequence: A seeds Senna's rows on Reike's facts (`_fact_of`); a test DB
seeded before 0097 is rebuilt, not migrated (v2.09 refuses it, E1).

### R-07 — overhearing
Opened: `analyzer_transcript.py:659-900`, `analyzer.py:76-170`,
`scripts/seed_pilot.py:421-448` (prompt), `prompt_registry.py:148`.
Finding: the classifier receives every subject of the world
(`{subject_list}`), returns `{"subject","speaker"}`; only a speaker's
non-secret row can source a proposal (K2 guard, secret guard).
Consequence: L1's list (the speakers' non-secret facts) is the effective set
already; the placeholder becomes `{fact_list}`.

### R-08 — the tick
Opened: `tick.py:95-250`, `tick_normalize.py:700-817`, `tick_context.py:126-275`,
`seed_pilot.py:915-975` (prompt), `tooling/verify/checks/world_tick.py:310-392`
(rule 5's implementation).
Finding: `secret_subjects` is a SetComp over `is_secret` rows; the floor
sets `secret_derived` on a subject/substring match; rule 5 requires that
SetComp name, an `in` comparison on it, and no `is_secret` assignment from it.
Consequence: C renames to `secret_fact_ids` (+ `secret_texts`) and retargets
rule 5 in the same commit.

### R-09 — the day chain
Opened: `day_plan.py:78-560`, `day_mutations.py:100-300`,
`day_resolve.py:253-272`, `cockpit/routes/day.py:44-56, 245-262, 545-690`,
`cockpit/day_reconcile_apply.py:156, 200`, `models/config.py:104-146`,
`writes/goals_agendas.py:590-625`, `tooling/verify/checks/day_plan.py:985-1100`.
Finding: the planner never sees a list of learnable subjects; it guesses a
`target_key`, and `anchor_requirements` drops any key that is not an existing
subject; `emit_plan` has three call sites; `Verdict` has no label field;
`requirement_detail_fr` formats `required`; `agenda_step_requirement.target_key`
is free text (CHECK only NOT NULL for knowledge).
Consequence: D builds the list inside `emit_plan` (every call site gets it),
stores fact ids in `target_key`, adds `Verdict.required_label`.

### R-10 — link agent
Opened: `link_author.py:150-320, 500-615, 880-915`, `link_context.py:55-125`,
`tooling/verify/checks/link_agent_strata.py:150-215`.
Finding: the stamp `"subject": f"npc:{other_id}"` is built in one function;
rule 3 requires exactly that shape; `commit_batch` calls
`write_knowledge(db, **row.payload)` and refuses before coherence ran.
Consequence: E stamps `"subject_entity_ids": [other_id]` (a kwarg
`write_knowledge` already takes) and retargets rule 3.

### R-11 — `discoverable_detail`
Opened: `models/canon.py:670-700`, `scene_format.py:17-80`,
`cockpit/play_discovery.py`, `cockpit/mutations._mutation_apply_new_knowledge`.
Finding: `subject` is the detail's own label (`DiscDetailsEditor`); the
discovery proposal copies it; `active_signposts` compares it to
`knowledge.subject`.
Consequence: `detail.subject` stays (not a knowledge key); H1 adds `fact_id`.

### R-12 — the names panel resolver
Opened: `lore_mentions_read.py:55-105`, `lore_resolve.py:143-230`.
Finding: `lookup_surface(db, world_id, surface)` returns `{"surface",
"candidates": [{"id","name","type"}], "near": [{"id","name","type","score"}]}`
over every category under the `creator` regime.
Consequence: F's worklist reuses it (I1); no second resolver.

### R-13 — creator surface
Opened: `frontend/src/creation/{KnowledgeEditor,SubjectWorklist,PendingKnowledgeEditor,QueueCard,PjCreatePanel,LinkAgent,Sheet}.svelte`,
`subjectWorklist.svelte.js`, `pendingDrafts.svelte.js`, `registry.js:542-550`,
`tabs.js:328-336`, `frontend/src/journee/Journee.svelte:151`,
`cockpit/crud/{knowledge,_shared}.py`, `cockpit/routes/{creator,npc_agent}.py`,
`entity_author.py:45-260`, `seed_pilot.py:276-412, 1196-1235`.
Finding: every create path requires a subject; the worklist binds by subject
over `/unresolved-subjects`; the analysis and generation prompts ask for one.
Consequence: F.

### R-14 — foreign keys onto `fact` and `knowledge`
Opened: `SQLModel.metadata` (command below, gate (c)).
Finding: after A, `fact` ← `discoverable_detail.fact_id`, `fact_default`,
`fact_participant`, `knowledge`, `unresolved_mention`; `knowledge` ←
`unresolved_mention.knowledge_id`.
Consequence: v2.09's absorption repoints `unresolved_mention.knowledge_id`
before deleting a duplicate; `world_cascade.py`'s fixture orders
`discoverable_detail` after `fact`.

### R-15 — pre-existing breakage, left as is
Opened: `scripts/seed_test.py`, `scripts/test_context.py`, run on `main`.
Finding: `seed_test.py` fails with `NOT NULL constraint failed:
knowledge.fact_id` on `main` already; `test_context.py` depends on it.
`scripts/apply_ticket_0087_subject_participants.py` imports `subject_resolve`.
Consequence: named deferrals; nothing in the corpus runs them.

## Contract sheet

### C-01 — `fact_refs.text_key`, `knowledge_key`, `find_held`
Produced by: B   Consumed by: B, C, D, E
```python
def text_key(content: Optional[str]) -> str  # first 5 words, lower, \W stripped, "_"-joined, <=50; "unknown" if empty
def knowledge_key(payload: dict) -> tuple[str, str]
    # ("fact", fact_id) when payload["fact_id"] is truthy, else ("text", text_key(payload["content"]))
def find_held(db, entity_id: Optional[str], payload: dict) -> Optional[Knowledge]
    # None when entity_id is falsy; by fact: the row (entity_id, fact_id);
    # by text: the first row of entity_id whose fact text or own text has the key
```

### C-02 — knowledge apply rules (`cockpit/mutations.py`)
Produced by: B   Consumed by: C, D, E
- `new_knowledge`: payload `fact_id` optional; a discovery's detail supplies
  `detail.fact_id`; a fact of another world → error string; a fact the entity
  already holds → error string; no `fact_id` → a new fact from the row's text.
  The first approved discovery sets `detail.fact_id`.
- `knowledge_change`: finds the row by `(entity_id, fact_id)`; no `fact_id`
  → `"knowledge_change: payload must contain entity_id and fact_id"`.
- resource knowledge leg: needs `entity_id` and non-empty `content`; a held
  row (`find_held`) → `"knowledge already held (upgrade-by-purchase deferred)"`.
- window normalization: model `knowledge_change` dropped (N1); `subject` and
  `fact_id` popped from a model `new_knowledge` / resource leg (a subject
  with no content becomes the content).

### C-03 — `fact_refs.code_facts`, `CodedFacts`
Produced by: B   Consumed by: C, D
```python
def code_facts(db, fact_ids: Iterable[str]) -> CodedFacts
    # in order, first occurrence wins, ids without a fact skipped; line "f<n> — <rendered text>"
@dataclass(frozen=True)
class CodedFacts:
    codes: dict[str, str]        # "f1" -> fact id
    lines: tuple[str, ...]
    def resolve(self, code) -> Optional[str]   # tolerates "[F1]", " f1 "; non-str or unknown -> None
    def code_of(self, fact_id) -> Optional[str]
```

### C-04 — overhearing
Produced by: C   Consumed by: nothing later
List: the facts the two possible speakers hold on a non-secret row, NPC
first, each in `Knowledge.id` order. Answer: `[{"fact": "<code>", "speaker":
"player"|"npc"}]`. Proposals carry `fact_id` (and a `knowledge_change` a
display `fact_label`); never `subject`.

### C-05 — tick
Produced by: C   Consumed by: nothing later
`tick_context.tick_knowledge_rows(npc_id, session)` (stored rows by id,
then resolved defaults), `tick_fact_codes(npc_id, session)`; each briefing
knowledge line starts `- [f<n>] `. A `new_knowledge` item may carry
`"source_fact": "<code>"|null`; resolved, the payload gets `fact_id`, and
`secret_derived` is set when that fact is one of the NPC's secret facts or
the content contains a secret fact's rendered text. `is_secret` is never
set from either.

### C-06 — day gates
Produced by: D   Consumed by: nothing later
`learnable_facts(character, db) -> CodedFacts` (anchorable minus held,
ordered by text then id, cap `MAX_LEARNABLE_FACTS_SHOWN = 40`);
`learnable_facts_summary(character_name, learnable) -> str` ("" when empty);
`emit_plan(declaration, character, db, standing_steps_summary="")` returns
knowledge requirements with the code resolved to a fact id, an unknown code
kept as emitted; `Verdict.required_label: Optional[str] = None`, set by
`_eval_knowledge` to the fact's rendered text; `requirement_detail_fr` uses
it. Day proposals carry `fact_id` (+ `fact_label` on a `knowledge_change`).

### C-07 — link agent stamp
Produced by: E   Consumed by: nothing later
Staged knowledge payload: `"subject_entity_ids": [other_id]`, no `subject`.
Canon graph knowledge row: `"about_entity_ids": [sorted participant ids]`.

### C-08 — `GET /api/worlds/{world_id}/unbound-facts`
Produced by: F   Consumed by: F (frontend)
404 on an unknown world. A list, ordered by `knower_count` desc, fact text,
fact id, of:
```
{"fact_id", "fact", "knower_count",
 "excerpt": {"entity_name", "text"} | None,   # first knower by name; text clipped to 120 + "…"
 "candidates": [{"id","name","type"}], "near": [{"id","name","type","score"}]}
```
Only free facts known by an entity of the world and bound to no participant.

### C-09 — migrations
Produced by: A (v2.09), G (v2.10)   Consumed by: `knowledge_identity.py`
- `migrate_v2_09_knowledge_identity.migrate(cursor) -> dict` with keys
  `absorbed` (list of `(entity_id, fact_id, rows_deleted)`), `index_created`,
  `npc_facts` (`{"token","participant","untouched"}` lists of fact ids),
  `detail_column_added`, `gates_rekeyed`, `gates_untouched`; raises `Abort`.
- `migrate_v2_10_drop_knowledge_subject.migrate(cursor) -> bool` (True when
  dropped, False when already gone); raises `Abort`.

## Gate output

### (a) Property trace

| property | finding | declaring file opened |
|---|---|---|
| no unique `(entity_id, fact_id)` on `knowledge` | R-01 | `models/canon_knowledge.py` |
| `idx_knowledge_subject` exists | R-01 | `models/canon_knowledge.py` |
| `fact_participant` unique `(fact_id, entity_id)` | R-04 | `models/canon_knowledge.py` |
| `create_fact` requires a facet, `information` is a free facet | R-04 | `writes/facts.py`, `facets.py` |
| `write_knowledge` makes a fact from the subject | R-05 | `writes/knowledge.py` |
| `_mutation_match_key` keys on subject | R-02 | `analyzer_transcript.py` |
| rule 5 requires the `secret_subjects` SetComp | R-08 | `checks/world_tick.py` (implementation) |
| rule 3 requires the `npc:` f-string stamp | R-10 | `checks/link_agent_strata.py` (implementation) |
| R26/R28 name `_anchorable_subjects`, `held_subjects_summary` | R-09 | `checks/day_plan.py` (implementation) |
| `emit_plan` has three call sites | R-09, (c) | `routes/day.py`, `day_reconcile_apply.py` |
| `commit_batch` refuses before coherence | R-10 | `link_author.py` |
| `lookup_surface` shape | R-12 | `lore_mentions_read.py` |
| `discoverable_detail.subject` is a detail label | R-11 | `models/canon.py` |
| `seed_test.py` already fails | R-15 | run on `main` |
| prompt variables must be declared | prototype | `writes/prompts.py:write_prompt_version` |

### (b) Case tables

`knowledge_key` (K4a):

| payload | key |
|---|---|
| `{"fact_id": "f-9"}` | `("fact","f-9")` |
| `{"fact_id": "f-9", "content": "…"}` | `("fact","f-9")` |
| `{"content": "Le Conseil cache l'un de ses membres."}` | `("text","le_conseil_cache_lun_de")` |
| `{"content": ""}` / `{}` | `("text","unknown")` |

`CodedFacts.resolve` (K5a), list `[two, one, two, missing]`:

| input | result |
|---|---|
| lines | `("f1 — Deux.", "f2 — Un.")` |
| `"f2"` / `"[F1]"` / `" f1 "` | one / two / two |
| `"f3"` / `1` | None / None |
| `code_of(one)` / `code_of(missing)` | `"f2"` / None |

`new_knowledge` apply (K4c, C-02):

| case | outcome |
|---|---|
| no `fact_id`, content | new fact, content = row text |
| `fact_id` of this world, not held | attached |
| same again | "entity already knows fact" |
| `fact_id` of another world | "is not a fact of this world" |
| discovery, detail without fact | new fact; detail.fact_id set |
| discovery, detail with fact | attached to detail.fact_id |

Tick floor (K5c): secret code → `fact_id` set, derived; unknown code →
neither; content containing a secret's text → derived; `is_secret` never
changed.

v2.09 (K2): split subject → Abort, DB unchanged; `creator_meta` split → no
abort; duplicate → survivor = highest level, history carries the other;
`npc:<uuid>` known → participant + token; `npc:<non-uuid>` known →
participant only; unknown id → untouched; gate on a subject with one fact →
rekeyed; other key → untouched; second run → nothing.

v2.10 (K9): before v2.09 → Abort; orphan label → Abort; clean → dropped;
again → False.

### (c) Enumerations

`subject` references per file in `src/world_engine` on `main` (K3's census
function: attribute `.subject`, constant `"subject"`, `subject=` keyword,
`subject` parameter) — 112 in 29 files:
```
analyzer.py 2 · analyzer_transcript.py 13 · cockpit/crud/_shared.py 3 ·
cockpit/crud/knowledge.py 8 · cockpit/crud/locations.py 7 ·
cockpit/mutations.py 11 · cockpit/play_discovery.py 3 · cockpit/routes/creator.py 2 ·
cockpit/routes/day.py 2 · cockpit/routes/mutations.py 6 · cockpit/routes/npc_agent.py 2 ·
context.py 4 · day_mutations.py 4 · day_plan.py 3 · entity_author.py 4 ·
knowledge_resolve.py 1 · link_author.py 5 · link_context.py 4 · lore_render.py 1 ·
lore_selectors.py 2 · models/canon_knowledge.py 1 · scene_format.py 3 ·
subject_resolve.py 4 · tick.py 4 · tick_context.py 1 · tick_normalize.py 2 ·
writes/facets.py 1 · writes/knowledge.py 8 · writes/relations.py 1
```
Census after each brief: A 112 · B 90 · C 76 · D 67 · E 45 · F 22 · G 11.
The final 11 are `cockpit/crud/locations.py` 7 and `cockpit/play_discovery.py` 1
(the detail's own label) and `analyzer_transcript.py` 3 (a model's
`subject` field read as a hint, then popped).

Foreign keys onto `fact` / `knowledge` (R-14):
```
unresolved_mention knowledge_id -> knowledge
fact<- discoverable_detail fact_id   (after A)
fact<- fact_default fact_id
fact<- fact_participant fact_id
fact<- knowledge fact_id
fact<- unresolved_mention fact_id
```

`emit_plan(` call sites (R-09):
```
cockpit/day_reconcile_apply.py:156, 200 ; cockpit/routes/day.py:681
```

`fact_refs` on `main`: `git grep "fact_refs" 89fc38a -- src` → no output
(the module does not exist; B creates it).

### (d) Family contracts

The knowledge-identity family (C-01, C-02) was written before any of its
consumers (overhearing, tick, day, link, worklist) and re-read after the
last (F); the coded-list family (C-03) before C-04, C-05, C-06, re-read after
C-06.

### (e) Checks and the modules that satisfy them

| check | satisfied by | what it forbids that the module needs |
|---|---|---|
| `knowledge_identity.py` (new, A) | models, the two migrations, `fact_refs.py`, the apply branches, `unbound_facts.py` | nothing: K3 pins counts, it does not ban |
| `world_tick.py` rule 5 (retargeted C) | `tick.py`, `tick_normalize.py` | an `is_secret` assignment from the floor: none |
| `link_agent_strata.py` rule 3 (retargeted E) | `link_author._build_knowledge_row` | `item.get(...)` in the stamp: none |
| `day_plan.py` R26/R28 (retargeted D) | `day_plan.py` | a seeded prompt naming `learnable_facts_summary`: none |
| `subject_resolution.py` A1/A2 (retargeted F) | `unbound_facts.py` | direct `resolve_named`/`near_candidates`/`surfaces`/`text(`: none, it calls `lookup_surface` |
| `identity_tokens.py` R1 (passed) | `fact_refs.py` reads text through `prose_render` helpers | `content_raw` outside the allow-list: none |
| `function_length.py` (passed) | `_normalize_tick_item` kept at 80 lines in C | — |
| `module_budget.py` (passed) | largest: `cockpit/mutations.py` 939, `link_author.py` 932, `analyzer_transcript.py` 917 | — |
| `world_cascade.py` (passed) | `discoverable_detail` stays a direct table; fixture row carries `fact_id` | — |
| `claude_md_contract.py` (passed) | File structure kept at 80 lines by merging the `lore_*` line | — |
| `frontend_build_fresh.py` (passed) | D, F rebuild `static/` | — |

## Amendments

(none)
