# LOT — TICKET-0094 "Concordance H2: the model chooses, the code judges"

## Objective and cut

Today a named mention that fits several entities blocks the day with a 409,
and a named mention that fits nothing exactly becomes a germ, even when it is
a typo of a known name. H2 (locked before 0092) reopens 0075 C1 / 0081 C2
knowingly: the code narrows the candidates, the model chooses one and cites
an excerpt, the code judges the choice. Every call is stored with its reason
(Y3b), including refused ones (X1b), for the review loop K1 (0095).

- **Triggers (Y2b).** A named mention with 2+ candidates at the same rung
  (`ambiguous`), and a named mention with no exact/token hit but with partial
  or near candidates among the character's own name surfaces (`near`). Cast
  (inferred mentions) stays deterministic.
- **Evidence (Y4b).** For each candidate, the facts the character knows about
  it, read through `facet_reads` (creator-only excluded by construction).
- **Judge (Y5c, X2b).** The chosen number is on the list; the excerpt is
  found verbatim (after normalization) — for `ambiguous`, in the chosen
  candidate's facts and in no other candidate's; for `near`, in the
  declaration or the chosen candidate's facts. `0` means "none".
- **Failure (Y5c, Y8a).** One retry on a technical failure only (Ollama
  error, invalid JSON, missing or ill-typed field). Any non-accepted outcome
  falls back to today's behaviour: 409 for `ambiguous`, unmatched (and a germ
  for a person) for `near`.
- **No bound on calls (X3b).** Quality first.
- **Missing prompt (X4a).** The declaration is refused by the coverage guard,
  like every day-chain prompt; at plan time a missing template is a 502.

**Where the lot stops.** Three day-chain categories (Y6b). No review UI (K1,
0095). No change to `resolve_named`, the Lore question, the tokenizer or
`subject_resolve`. Schema v2.07: one new append-only table.

## Briefs in this lot

- **A** `storage-and-near` — closes TICKET-0093's front matter; table
  `day_mention_choice` (model, schema doc v2.07, changelog, constant,
  migration script); `write_day_mention_choices`; W2 extended;
  `lore_resolve.near_in_surfaces` (pure) with `near_candidates` delegating;
  creates both new checks.
- **B** `requests-and-judge` — `day_choice.py` without any model call:
  `choice_requests` (narrowing + evidence), `render_candidates`,
  `parse_answer`, `judge_choice`.
- **C** `the-call` — the `day_mention_choice` prompt (seed head + constants,
  registry, apply script, delivery counts, wired files) and `choose` (call,
  one retry, judge, updated concordance, records).
- **D** `wiring` — the plan route: `choose` between `concord` and
  `emit_germs`; records staged with the rewrite; X1b's own-transaction write
  before the 409; docstrings of 0075/0081 corrected.

## Dependency graph

Strict chain A → B → C → D.

- A before all: both new checks must exist from `exec` on (R-25), and B reads
  `near_in_surfaces`.
- B before C: `choose` calls B's functions.
- C before D: the route calls `choose`.

## RECON

All findings taken on a fresh tarball of `main` after TICKET-0093's merge.
`[M]` measured by opening the named file.

### R-01 — `concord` and the named rungs
Opened: `src/world_engine/day_concordance.py:134-167`, `344-422`
Finding [M]: `concord` builds the perceiver surfaces once
(`name_surfaces(db, world_id, NameScope("perceiver", known_fact_ids=
frozenset(resolve_levels_for_entity(db, character.id))))`), walks
`MATCHING_RUNGS` per mention, and `_classify` returns `MatchedMention` for one
candidate, `AmbiguousMention(candidate_ids=tuple(sorted(...)))` for 2+ on a
named mention, `CastMention` for 2+ on an inferred one. A mention with no hit
is `UnmatchedMention(rungs_tried, candidate_location_id)`. No partial rung, no
near names. The module docstring (lines 34-39) states the C2-partition
"never resolved by picking".
Consequence: `concord` is not modified. H2 runs on its result (`choose`,
C-07). D corrects the docstring to say the pick now happens after `concord`,
in `day_choice.py`.

### R-02 — `ConcordanceResult` shapes
Opened: `src/world_engine/day_concordance.py:96-131`; `src/world_engine/day_extract.py:41-46`
Finding [M]: `MatchedMention(mention, entity_id, rung)`,
`AmbiguousMention(mention, candidate_ids)`, `UnmatchedMention(mention,
rungs_tried, candidate_location_id=None)`, `ConcordanceResult(matched, cast,
ambiguous, unmatched, skipped_rungs)`, all frozen;
`Mention(category, surface_form, kind, role_hint=None)`.
Consequence: `choose` returns a new `ConcordanceResult` via
`dataclasses.replace`, never mutates one.

### R-03 — the plan route
Opened: `src/world_engine/cockpit/routes/day.py:36`, `480-499`
(`_extract_and_concord`), `502-516` (`_write_declaration_rewrite`), `612-675`
(`plan_day`)
Finding [M]: `_extract_and_concord` runs the three `extract_*`, `concord`,
then `emit_germs(concordance_result.unmatched, ...)` and `db.add`s the germs
(staged). `plan_day` wraps it in `try/except LlmParseError` → 502
`"day extraction failed: ..."`; then `if concordance_result.ambiguous:` →
409 `_ambiguous_detail(...)` with nothing committed; then writes the rewrite,
selects/emits the plan, and returns. `routes/day.py` is 963 lines, 27
top-level functions; `plan_day` is 64 lines, `_extract_and_concord` 20.
Consequence: `choose` goes between `concord` and `emit_germs` (a chosen
person must not also become a germ). The 409 branch gains X1b's write (C-08).
Growth budget: about 12 lines.

### R-04 — rewrite trace writer and reader
Opened: `src/world_engine/writes/pipeline.py:40-46`, `200-260`;
`src/world_engine/day_rewrite.py:72-147`
Finding [M]: `write_day_rewrite` validates every resolution dict, then builds
`DayRewrite`, flushes, then `DayMentionResolution` children; no commit.
`resolutions()` emits matched rows with `"rung": mm.rung`; `_reconstruct`
rebuilds `MatchedMention` from any stored `rung` string. No code validates
the rung value.
Consequence: an accepted choice becomes a `MatchedMention` with
`rung="model_choice"` and flows through the trace unchanged (Y3b). No change
to these two modules except the new writer (C-02) in `writes/pipeline.py`.

### R-05 — `day_mention_resolution` declaration
Opened: `src/world_engine/models/pipeline.py:146-203`; `world-engine-schema.md:993-1029`
Finding [M]: category CHECK `('place','person','faction')`; verdict CHECK
`('matched','cast','unmatched')`; `rung` has no CHECK; the doc's NOTE says an
ambiguity is never stored because the route 409s first.
Consequence: no rebuild needed (R-04). The new table sits right after it in
both files.

### R-06 — rungs, near names and the normalizer
Opened: `src/world_engine/lore_resolve.py:1-56`, `70-86`, `90-122`, `183-214`
Finding [M]: `rung_named_partial(surface_form, category, name_surfaces)` is
pure (surface tokens all ≥3 chars and a subset of the name's tokens).
`near_candidates(surface_form, world_id, db, *, scope, exclude_ids)` raises
`ValueError` unless `scope.regime == "creator"`, reads
`surfaces(db, world_id, scope)`, keeps per entity the best surface with
`difflib` ratio ≥ `NEAR_RATIO` (0.8) or a shared 3+ token, scores
half-up to 0-100, sorts `(-score, name.casefold(), entity_id)`, returns at
most `NEAR_LIMIT` (5) `NearCandidate(entity_id, name, entity_type, surface,
score)`, every category. `normalize_surface` casefolds, strips accents, drops
up to three leading article tokens, splits on whitespace and apostrophes,
joins with single spaces; punctuation stays attached to tokens.
Consequence: A extracts the loop into pure `near_in_surfaces` (C-03);
`near_candidates` keeps its guard and output exactly. B calls
`rung_named_partial` and `near_in_surfaces` on the perceiver surfaces and
filters by category itself. The judge reuses `normalize_surface`, after
stripping edge punctuation from the excerpt.

### R-07 — checks pinning the resolver
Opened: `tooling/verify/checks/name_resolution.py:1-45`;
`tooling/verify/checks/name_index.py:17-30`; `tooling/verify/checks/lore_resolve.py:1-20`
Finding [M]: G2 checks `near_candidates` scores (Maelys→83, reine→63/59),
`exclude_ids`, and that `scope=PROSE` raises. G5 checks a generator mention
"Varn" stays unresolved outside `creator` (tokenizer). name_index R5 confines
`CREATOR`; R6 requires a `scope=` keyword on every `resolve_named` /
`near_candidates` call. lore_resolve R1 forbids `db.add(`, `.commit(`,
`chat(` in `lore_resolve.py`.
Consequence: `near_in_surfaces` takes surfaces, not a scope; R6 does not
apply to it. `day_choice.py` never names `CREATOR` and never calls
`resolve_named` or `near_candidates`. G2 and G5 must stay green unchanged.

### R-08 — the evidence reader
Opened: `src/world_engine/facet_reads.py:1-124`; `src/world_engine/facets.py:78`;
`src/world_engine/knowledge_resolve.py:220-231`
Finding [M]: `facts_of(db, *, entity_id, facets, ...)` returns `FactRow(fact_id,
facet, aspect, content, created_at)`, content rendered through
`prose_render.fact_texts`, creator-only facts excluded in the query, ordered by
`facets` order then `created_at`. `known_facts_of` calls
`resolve_levels_for_entity(db, perceiver_id)` on every call.
`resolve_levels_for_entity(db, entity_id) -> dict[fact_id, level]` for facts
above `unaware`. `FACETS: dict[str, FacetSpec]` is the registry.
Consequence: B reads each candidate's facts with
`facts_of(db, entity_id=cid, facets=tuple(FACETS))` and filters them with ONE
`resolve_levels_for_entity(db, character.id)` call per `choice_requests` —
the same filter `known_facts_of` applies, without one level resolution per
candidate. Nothing outside the character's known set is ever assembled
(abliterated model: structural exclusion, never an instruction).

### R-09 — the chat call and its failures
Opened: `src/world_engine/ollama_client.py:39`, `66-70`, `88-131`;
`src/world_engine/llm_parse.py:21-22`, `44-60`;
`src/world_engine/day_plan_select.py:33-48`, `84-110`
Finding [M]: `chat(...)` raises `OllamaError(RuntimeError)` on HTTP error,
unreachable host, timeout (`OSError`) or a body error; returns the content with
the think block stripped. `extract_object` raises `LlmParseError(ValueError)`.
`day_plan_select` loads its template with a `usage == ...,
is_active == True` query preferring the world's row then the global one,
raises `LlmParseError("...: no active prompt_template for usage=...")` when
absent, reads `current_prompt`, appends `"\n/no_think"`, calls
`chat(..., model=effective_model(template, ollama_client.DEFAULT_MODEL),
host=ollama_client.OLLAMA_HOST, format="json", ...)`.
Consequence: C copies that loader and call shape. Technical failure =
`OllamaError` or `LlmParseError` from the call or `parse_answer` (Y8a). The
missing-template raise happens before the first call and is never retried.

### R-10 — prompt plumbing gates
Opened: `src/world_engine/prompt_registry.py:55-61`, `317-351`;
`src/world_engine/prompt_coverage.py:38-50`;
`tooling/verify/checks/prompt_registry.py:29-42`, `74-79`;
`tooling/verify/checks/day_prompt_delivery.py:1-76`, `182-183`, `488`;
`scripts/seed_pilot.py:2117-2217`; `scripts/apply_ticket_0077_plan_select_seed.py`
Finding [M]:
- `DAY_CHAIN_USAGES` includes every usage whose call site matches
  `^src/world_engine/day_[a-z_]+\.py$`, minus `day_feasibility`.
- `prompt_registry` check: bijection with `usage = "..."` lines of
  `seed_pilot.py`; `WIRED_FILES` (lines 29-42) lists the modules whose `chat(`
  must use `effective_model(`.
- `day_prompt_delivery`: 16 constants, 9 heads (`EXPECTED_HEAD_IDS`, literal
  `!= 9`); R6 classifies each `day_*.py` "no active prompt_template" message
  as `Raise`/`Return`, and the `Raise` set must equal `DAY_CHAIN_USAGES`.
- `DAY_PROMPT_HEADS` closes at line 2217, last head `pt-day-plan-select`
  (2208); `DAY_PLAN_SELECT_USER_TEMPLATE` at 2117.
- The 0077 script loops `DAY_PROMPT_HEADS` through `upsert_prompt_template`
  (idempotent), embeds no text.

Consequence: C adds `"day_mention_choice"` (call site
`src/world_engine/day_choice.py:choose`), which makes it a day-chain usage
refused at declaration when missing (X4a) with no edit to `prompt_coverage`.
Counts become 18 / 10. `day_choice.py` joins `WIRED_FILES`. The apply script
copies the 0077 one.

### R-11 — day-chain structural checks
Opened: `tooling/verify/checks/day_concordance.py:1-50`, `74`, `292-317`;
`tooling/verify/checks/day_rewrite.py:1-24`, `42-43`
Finding [M]: day_concordance R1 forbids `chat(` in `day_concordance.py`; R4
forbids `Entity(` / `Character(` / `NpcSchedule(` in extract/concordance/
plan; `EXPECTED_RUNGS` pins `MATCHING_RUNGS`. day_rewrite W2: no attribute
assignment on, and no `db.delete(` of, a `_TRACKED_MODELS = {"DayRewrite",
"DayMentionResolution"}` instance, vacuity-guarded by requiring a
construction of each; W6: `routes/day.py` calls each `extract_*` exactly
once.
Consequence: the model call lives in `day_choice.py` (R1 untouched).
`"model_choice"` is a stored rung, not a `MATCHING_RUNGS` entry
(`EXPECTED_RUNGS` untouched). A adds `"DayMentionChoice"` to
`_TRACKED_MODELS`. W6 stays true.

### R-12 — schema governance
Opened: `src/world_engine/schema_version.py`; `tooling/verify/checks/schema_version_agreement.py:1-30`;
`tooling/verify/checks/schema_partition.py:1-40`; `world-engine-schema-changelog.md:1-16`;
`scripts/migrate_v2_02_skill_resolution.py`; `src/world_engine/db.py:149-154`;
`src/world_engine/cockpit/app.py:195-210`
Finding [M]: the constant `EXPECTED_STATIC_SCHEMA_VERSION = "v2.06"`, the doc
header `Current schema version: v2.06` and the newest changelog entry
(`- **v2.06** — ...`) must agree. The boot guard refuses to start when
`schema_meta.static_version` differs. `migrate_v2_02_skill_resolution.py` is
the additive-table precedent: env guard, raw `CREATE TABLE` + indexes if
absent, post-check zero rows, converge `schema_meta`, idempotent.
`create_db_and_tables` runs `SQLModel.metadata.create_all`.
Consequence: A bumps all three to v2.07 in one commit and ships
`scripts/migrate_v2_07_day_mention_choice.py` (Nia runs it on prod before
starting the cockpit).

### R-13 — models export and canon-write policy
Opened: `src/world_engine/models/__init__.py:98-110`;
`tooling/verify/checks/single_canon_write.py:1-12`
Finding [M]: pipeline models are re-exported from `models/__init__.py`. The
canon-write check ignores non-canon tables and fails on an unattributable
write site.
Consequence: `DayMentionChoice` is exported there; its only write site is
`writes/pipeline.py::write_day_mention_choices`, constructed with the model
class (attributable).

### R-14 — the render chokepoint
Opened: `src/world_engine/facet_reads.py:95-104`
Finding [M]: `facts_of` renders `content` through `fact_texts` (one entity
query).
Consequence: fact text reaches the prompt only through `facts_of`; no raw
`Fact.text` read in `day_choice.py`.

### R-15 — the rung pinning in the frontend
Opened: `grep -rn "named_exact\|rung" frontend/src`
Finding [M]: only `frontend/src/lore/Lore.svelte:172` displays a rung, for
the Lore trace. The Journée view shows no rung.
Consequence: no frontend change; `frontend_build_fresh` untouched.

### R-16 — measurements carried from 0093's diagnostic
Opened: TICKET-0093 diagnostic report (prod read-only, 2026-09-25)
Finding [X]: no stored ambiguity; zero `appellation` facts in 13 worlds.
Consequence: at first, H2 acts mainly through `near`; the live gate
exercises both triggers on purpose-built data.

### R-17 — TICKET-0093 front matter
Opened: `tooling/tickets/TICKET-0093-day-narration-judge.md:1-14`
Finding [M]: `status: live-gate` (line 5), `current_brief:` empty (12). Nia
reports 0093 passed.
Consequence: A sets `status: done`, in its own commit.

### R-18 — CLAUDE.md
Opened: `grep -n -i "concord\|ambigu\|model call" CLAUDE.md`
Finding [M]: no invariant says the concordance never calls a model or never
picks; line 439 (file map) says `day_rewrite.py ... no model call`.
Consequence: no CLAUDE.md invariant edit. D adds one file-map line for
`day_choice.py` right after line 438, if the character budget allows (35.8k
of 38k, lines ≤ 100 chars); otherwise REPORT-ONLY.

## Contract sheet

Family first: **choice records** — one shape: written by C-02, built only by
`record_of` (C-06), collected by C-07, passed through by D. Written here
once; re-read after C-07.

### C-01 — table `day_mention_choice` / model `DayMentionChoice`
Produced by: A   Consumed by: C-02, K1 (0095)
DDL:
```sql
CREATE TABLE day_mention_choice (
  id                 TEXT PRIMARY KEY,
  world_id           TEXT NOT NULL REFERENCES world(id),
  pass_play_id       TEXT NOT NULL REFERENCES pass_play(id),
  category           TEXT NOT NULL CHECK (category IN ('place','person','faction')),
  surface_form       TEXT NOT NULL,
  trigger            TEXT NOT NULL CHECK (trigger IN ('ambiguous','near')),
  candidate_ids      TEXT NOT NULL,   -- JSON array, display order
  evidence_fact_ids  TEXT NOT NULL,   -- JSON array, facts shown to the model
  verdict            TEXT NOT NULL CHECK (verdict IN ('accepted','rejected','declined','failed')),
  chosen_entity_id   TEXT REFERENCES entity(id),
  excerpt            TEXT,
  reason             TEXT,
  verdict_detail     TEXT,
  attempts           INTEGER NOT NULL CHECK (attempts IN (1, 2)),
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'accepted' OR chosen_entity_id IS NOT NULL)
    AND (verdict NOT IN ('declined','failed') OR chosen_entity_id IS NULL)
  )
);
CREATE INDEX idx_day_mention_choice_pass ON day_mention_choice(pass_play_id);
CREATE INDEX idx_day_mention_choice_world_verdict ON day_mention_choice(world_id, verdict);
```
Append-only (W2). Non-canon.

### C-02 — `write_day_mention_choices`
Produced by: A   Consumed by: D
Signature: `def write_day_mention_choices(db: Session, *, world_id: str,
pass_play_id: str, records: list[dict]) -> list[DayMentionChoice]` in
`src/world_engine/writes/pipeline.py`.
Record keys (the family shape, every key required):
`category, surface_form, trigger, candidate_ids (list[str]),
evidence_fact_ids (list[str]), verdict, chosen_entity_id (str|None),
excerpt (str|None), reason (str|None), verdict_detail (str|None),
attempts (int)`.
Behaviour: validate every record first (category, trigger, verdict in their
sets; attempts in (1, 2); accepted ⇒ chosen set; declined/failed ⇒ chosen
None; the two lists are lists of str); any violation raises `ValueError`
with nothing built. Then construct one row per record (lists stored with
`json.dumps`), `db.add_all`, return them. No flush, no commit.
Empty `records` → `[]`, nothing added.

### C-03 — `near_in_surfaces`
Produced by: A   Consumed by: B (C-05), `near_candidates`
Signature: `def near_in_surfaces(surface_form: str, name_surfaces:
Sequence[NameSurface], *, exclude_ids: frozenset[str] = frozenset()) ->
tuple[NearCandidate, ...]` in `lore_resolve.py`. Pure.
Behaviour: exactly the body of today's `near_candidates` after its regime
guard, iterating `name_surfaces` instead of `surfaces(db, world_id, scope)`.
`near_candidates` becomes: the regime guard, then
`return near_in_surfaces(surface_form, surfaces(db, world_id, scope),
exclude_ids=exclude_ids)`.

### C-04 — `Candidate` and `ChoiceRequest`
Produced by: B   Consumed by: C-05, C-06, C-07
```python
@dataclass(frozen=True)
class Candidate:
    entity_id: str
    name: str                 # entity.name
    facts: tuple[str, ...]    # rendered contents, known to the character
    fact_ids: tuple[str, ...] # same order as facts

@dataclass(frozen=True)
class ChoiceRequest:
    mention: Mention
    trigger: str              # "ambiguous" | "near"
    candidates: tuple[Candidate, ...]  # display order, numbered from 1
```

### C-05 — `choice_requests`
Produced by: B   Consumed by: C-07
Signature: `def choice_requests(result: ConcordanceResult, character:
Character, db: Session) -> tuple[ChoiceRequest, ...]`.
Behaviour:
1. `ambiguous`: one request per `AmbiguousMention`, candidates in
   `candidate_ids` order.
2. `near`: for each `UnmatchedMention` with `mention.kind == "named"`: ids
   from `rung_named_partial(surface, category, surfaces)` (sorted), then
   ids from `near_in_surfaces(surface, surfaces)` whose
   `category_of_type(entity_type) == category` in their order, duplicates
   dropped, first `MAX_CANDIDATES` (8) kept; a request only if non-empty.
   `surfaces` is built once, with the exact `NameScope("perceiver", ...)` of
   R-01.
3. Evidence: `known = resolve_levels_for_entity(db, character.id)` once; per
   candidate `facts_of(db, entity_id=cid, facets=tuple(FACETS))` filtered to
   `fact_id in known`, first `MAX_FACTS_PER_CANDIDATE` (12) kept; `name` from
   `db.get(Entity, cid).name` (a missing entity is dropped).
Order: all `ambiguous` requests, then all `near`, each in result order.
Empty result → `()`.

### C-06 — `render_candidates`, `parse_answer`, `judge_choice`
Produced by: B   Consumed by: C-07
- `render_candidates(request: ChoiceRequest) -> str`: per candidate
  `f"{i}. {name}"`, then either `"   Ce que le personnage sait :"` followed by
  one `"   - {fact}"` line per fact, or
  `"   Le personnage ne sait rien de plus sur lui."`; candidates separated by
  a blank line.
- `parse_answer(raw: str) -> dict`: `llm_parse.extract_object(raw)`;
  requires `choix` an `int` (not `bool`), `extrait` a `str`, `raison` a
  `str`; otherwise `LlmParseError("day_choice: <field> missing or ill-typed")`.
  Returns `{"choix", "extrait", "raison"}`.
- `judge_choice(request, answer, declaration: str) -> ChoiceVerdict`, pure:
  `ChoiceVerdict(verdict: str, entity_id: Optional[str], excerpt:
  Optional[str], reason: Optional[str], detail: Optional[str])`.
  Rules in order:
  1. `choix == 0` → `declined`, entity None.
  2. `choix` outside `1..len(candidates)` → `rejected`, entity None,
     detail `"candidate out of range"`.
  3. `e = normalize_surface(excerpt.strip(" \t\n\"'«»“”.,;:!?…"))`; `len(e) < 3`
     → `rejected`, detail `"excerpt too short"`.
  4. `ambiguous`: `e` must be a substring of
     `normalize_surface(" ".join(chosen.facts))` and of no other candidate's
     joined facts; else `rejected`, detail `"excerpt not in the chosen
     candidate's facts"` or `"excerpt does not single out the chosen
     candidate"`.
  5. `near`: `e` must be a substring of `normalize_surface(declaration)` or
     of the chosen candidate's joined facts; else `rejected`, detail
     `"excerpt not found"`.
  6. otherwise `accepted`, entity = chosen id.
  `excerpt` and `reason` are the answer's, stripped, `None` when empty, on
  every verdict; `entity_id` is set on `accepted` and on a `rejected` whose
  number was in range.
- `record_of(request, verdict: ChoiceVerdict, attempts: int) -> dict`: the
  family shape of C-02; `chosen_entity_id` is `None` for `declined`;
  `evidence_fact_ids` flattens every candidate's `fact_ids` in display order.
  A `failed` record is `record_of(request, ChoiceVerdict("failed", None,
  None, None, <last error text>), 2)`.

### C-07 — `choose`
Produced by: C   Consumed by: D
Signature: `def choose(result: ConcordanceResult, declaration: str, character:
Character, db: Session) -> ChoiceOutcome`;
`ChoiceOutcome(result: ConcordanceResult, records: tuple[dict, ...])`.
Behaviour: `requests = choice_requests(result, character, db)`; none →
`ChoiceOutcome(result, ())` with no template read. Else load the
`day_mention_choice` template once (missing → `LlmParseError("day_choice: no
active prompt_template for usage='day_mention_choice'")`, never retried).
Per request: up to 2 attempts of {render user message, `chat`,
`parse_answer`}; `OllamaError`/`LlmParseError` on attempt 1 → attempt 2; on
attempt 2 → verdict `failed`. Otherwise `judge_choice`. Accepted: the
mention leaves `ambiguous` (or `unmatched`) and joins `matched` as
`MatchedMention(mention, entity_id, rung="model_choice")`, appended after the
existing matched. Every request yields exactly one record (C-02 shape;
`evidence_fact_ids` = every candidate's `fact_ids`, flattened in display
order; `verdict_detail` = the judge's detail or the last technical error
text for `failed`).

### C-08 — route wiring
Produced by: D   Consumed by: live play
- `_extract_and_concord` returns `(concordance_result, germ_ids, records)`:
  `outcome = choose(concord(...), pass_play.declared_action, character, db)`
  before `emit_germs(outcome.result.unmatched, ...)`.
- `plan_day`: if `concordance_result.ambiguous`: `db.rollback()`;
  `write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play.id,
  records=list(records))`; `db.commit()`; raise the existing 409. Else, right
  after `_write_declaration_rewrite(...)`: `write_day_mention_choices(...)`
  staged in the plan's transaction.
- The 502 wrapper around `_extract_and_concord` is unchanged (a missing
  template surfaces as `"day extraction failed: day_choice: no active
  prompt_template ..."`).

## Gate output

### (a) Property trace

| Property | Finding | Declaring file opened |
|---|---|---|
| perceiver surfaces built in `concord`; classify rules | R-01 | `day_concordance.py` |
| dataclass fields of concordance results and `Mention` | R-02 | `day_concordance.py`, `day_extract.py` |
| where germs are emitted; 409 and 502 branches; sizes | R-03 | `cockpit/routes/day.py` |
| rung never validated; trace writer/reader shape | R-04 | `writes/pipeline.py`, `day_rewrite.py` |
| resolution CHECKs; `rung` unconstrained | R-05 | `models/pipeline.py` |
| partial rung, near algorithm, normalizer | R-06 | `lore_resolve.py` |
| G2/G5, R5/R6, lore_resolve R1 content | R-07 | the three checks |
| `facts_of` excludes creator-only; levels reader | R-08 | `facet_reads.py`, `knowledge_resolve.py`, `facets.py` |
| chat failure types; loader and call idiom | R-09 | `ollama_client.py`, `llm_parse.py`, `day_plan_select.py` |
| coverage derivation; delivery counts; wired files; head list | R-10 | `prompt_coverage.py`, the two checks, `seed_pilot.py`, 0077 script |
| R1/R4/`EXPECTED_RUNGS`; W2/W6 | R-11 | `checks/day_concordance.py`, `checks/day_rewrite.py` |
| version triple and boot guard; migration idiom | R-12 | `schema_version.py`, the two checks, `app.py`, v2.02 script |
| models export; non-canon ignored | R-13 | `models/__init__.py`, `checks/single_canon_write.py` |
| fact text rendered in `facts_of` | R-14 | `facet_reads.py` |
| no Journée rung display | R-15 | `frontend/src` grep |
| 0093 status line | R-17 | `TICKET-0093-...md` |
| no CLAUDE.md invariant on the concordance | R-18 | `CLAUDE.md` |

Presuppositions: every "copy" names its file (0077 script, v2.02 migration,
`day_plan_select` loader, `identity_tokens` fixture helpers of 0093-A).

### (b) Case tables

**(b1) Triggers (C-05):**

| concord outcome | kind | partial/near hits | request |
|---|---|---|---|
| matched | any | — | none |
| cast | inferred | — | none (Y2b) |
| ambiguous | named | — | `ambiguous`, its candidates |
| unmatched | named | ≥1 in category | `near` |
| unmatched | named | 0 | none |
| unmatched | inferred | — | none |

**(b2) Judge (C-06), per trigger:**

| answer | ambiguous | near |
|---|---|---|
| `choix` 0 | declined | declined |
| out of range | rejected | rejected |
| excerpt < 3 chars normalized | rejected | rejected |
| excerpt only in declaration | rejected | accepted |
| excerpt in chosen facts, also in another's | rejected | accepted |
| excerpt in chosen facts only | accepted | accepted |
| excerpt nowhere | rejected | rejected |

**(b3) Outcome → behaviour (C-07/C-08):**

| trigger | verdict | concordance | route |
|---|---|---|---|
| ambiguous | accepted | → matched `model_choice` | plan proceeds |
| ambiguous | rejected/declined/failed | stays ambiguous | rollback, records committed, 409 |
| near | accepted | → matched `model_choice` | plan proceeds, no germ |
| near | rejected/declined/failed | stays unmatched | plan proceeds, germ if person |

**(b4) Attempts:**

| attempt 1 | attempt 2 | verdict | attempts |
|---|---|---|---|
| parsed | — | judge's | 1 |
| technical failure | parsed | judge's | 2 |
| technical failure | technical failure | failed | 2 |

### (c) Enumerations

```
$ grep -rn "near_candidates(" --include=*.py src tooling | grep -v "def near_candidates"
src/world_engine/lore_query.py:134:  near_candidates(surface_form, world_id, db, scope=CREATOR)
src/world_engine/lore_mentions_read.py:90:  near_candidates(surface, world_id, db, scope=CREATOR, exclude_ids=exclude)
tooling/verify/checks/name_resolution.py:166, 178  (G2)
$ grep -rn "concord(" --include=*.py src | grep -v "def concord"
src/world_engine/day_resolve.py:394        (docstring)
src/world_engine/cockpit/routes/day.py:493 (the only runtime call)
src/world_engine/day_rewrite.py:4          (docstring)
$ grep -rn "\.ambiguous" --include=*.py src
src/world_engine/cockpit/routes/day.py:449, 648, 649
src/world_engine/day_rewrite.py:44 (render raises on non-empty), 78 (docstring)
(lore.py / lore_render.py use `ambiguous_mentions`, another type)
$ grep -rn "\.rung\b" --include=*.py src/world_engine | grep -v "scope\."
lore_query.py:119 (Lore trace, other type); routes/day.py:427, 437 (response);
day_rewrite.py:87, 94, 115, 118 (copy through) — no comparison to a set
$ grep -n -i "concord\|ambigu\|model call" CLAUDE.md
198, 203, 317 (unrelated model-call rules); 438-439 file map
```
Consequences: `near_candidates` keeps its two callers and G2 unchanged;
`concord` has one runtime caller, so wiring `choose` after it covers play;
`render` raising on a non-empty `ambiguous` stays true because D 409s before
calling it; the stored rung is copied, never checked (R-04). CLAUDE.md line
438 ("never authors") stays true — `choose` picks among existing entities.

### (d) Contracts
Family "choice records" written first (C-02 keys), re-read after C-07: the
only builder is `record_of`, which emits exactly those eleven keys (verified
on a prototype: accepted after a retry, failed after two technical
failures). ✔

### (e) Gates and satisfying modules

| Gate | Satisfied by | Needs vs forbids |
|---|---|---|
| `day_mention_choice_store.py` (new) | `DayMentionChoice`, `write_day_mention_choices` (A) | temp-SQLite fixture only |
| `day_choice.py` (new check) | A: `near_in_surfaces`; B: `choice_requests`, `judge_choice`, `parse_answer`, `render_candidates`; C: `choose` with `ollama_client.chat` monkeypatched; D: static route rules | no Ollama, no prod DB |
| `day_concordance.py` R1/R4 | model call in `day_choice.py` only | nothing |
| `day_rewrite.py` W2 (extended) | writer constructs `DayMentionChoice`; no update/delete | nothing |
| `prompt_registry.py`, `day_prompt_delivery.py` | C's seed + registry + counts | nothing |
| `name_resolution.py` G2/G5 | `near_candidates` output unchanged | nothing |
| `schema_version_agreement.py`, `schema_partition.py` | A's triple bump + changelog entry | nothing |
| `single_canon_write.py` | non-canon table, attributable site | nothing |
| `module_budget.py`, `function_length.py` | route +~12 lines (963→~975); `day_choice.py` new | nothing |
| `import_cycle.py` | `day_choice` imports `facet_reads` at module level; nothing imports `day_choice` but the route | verified in B's Done means |
| `decisions_index.py`, `pipeline_state.py`, `corpus_gate.py` | per brief | nothing |

## Amendments

(none)
