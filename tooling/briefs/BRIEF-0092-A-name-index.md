# BRIEF 0092-A — "name index and tokenizer regimes"

Lot: LOT-0092-names.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a
few lines is drift, not a STOP — note it and proceed; different content is
always a STOP.

- `prose_tokens.py:82-105` `_build_index` selects `Fact` joined to
  `FactParticipant` with `Fact.facet == "appellation"` and no creator-only
  or scope filter; `:201` `tokenize(db, *, world_id, text, mentions=None)`.
- `facet_reads.py:56` `creator_only_fact_ids(db, fact_ids) -> set[str]`;
  `facet_reads.py:28` imports `knowledge_resolve` at module level.
- `facets.py:38` `FacetSpec("appellation", "identite", "affirmation", "location", ...)`.
- `writes/facets.py:58-67` `_preset_scope`; `:124` and `:252` are the two
  `tokenize(` calls; `:179-182` writes the `creator_meta` knowledge row.
- `checks/fact_facets.py:71` pins the `appellation` tuple with `"location"`.
- `CLAUDE.md:149` reads "  `facet_reads` by query construction; only the Lore dossier opts in. What an NPC".
- `checks/identity_tokens.py:108-133` `_fresh_engine`, `_world`.
- No file `src/world_engine/name_index.py`, no file
  `tooling/verify/checks/name_index.py` or `name_resolution.py`.

## Facts carried

### R-01 — the tokenizer's name index, today
Opened: `src/world_engine/prose_tokens.py:1-222` [M].
Finding: `_build_index` (`:82-105`) selects the active entities of the world,
then `select(Fact, FactParticipant.entity_id)` joined on
`FactParticipant.fact_id == Fact.id` where `Fact.world_id == world_id` and
`Fact.facet == "appellation"` (`:88-93`), keeps pairs whose participant is an
active entity, and reads their text through `prose_render.fact_texts`
(`:95`). No creator-only filter and no scope filter exist on that query.
`tokenize(db, *, world_id, text, mentions=None)` (`:201`) builds the index on
every call. `_mention_spans` (`:179-199`) resolves generator mentions with
`resolve_named(name, category, world_id, db)` (`:191`) and accepts only
categories in `_CATEGORY_OF_TYPE.values()` (`:185`); `_CATEGORY_OF_TYPE`
(`:39`) mirrors `lore_resolve._CATEGORY_ENTITY_TYPE`; `_category` (`:174-176`)
names the category of an ambiguous span. Index keys are
`_key_words(surface)` (`:74-75`, through `normalize_surface`).
Consequence: A moves the surface query into `name_index.py` and closes the
creator-only leak there. Keys stay computed in `prose_tokens`.
### R-06 — creator-only facts
Opened: `src/world_engine/facet_reads.py:1-61`; `lore_selectors.py:100-120`;
`tooling/verify/checks/fact_facets.py:30-45`; `CLAUDE.md:146-153` [M].
Finding: creator-only = a stored `knowledge` row on the fact, belonging to
one of the fact's own participants, at `level = 'unaware'` and
`is_secret = 1` (`_creator_only_select`, `:42-53`).
`creator_only_fact_ids(db, fact_ids) -> set[str]` (`:56-61`) returns that
subset in one query. `include_creator_only=True` appears only at
`lore_selectors.py:116` (E7); `fact_facets.py` R7 forbids a non-`False`
`include_creator_only` keyword elsewhere. CLAUDE.md `:147-149` says "only the
Lore dossier opts in".
Consequence: `name_index` excludes creator-only appellations by calling
`creator_only_fact_ids`, never by re-deriving the shape. Its `creator`
regime does not exclude them (N2b); that is a second opt-in and the CLAUDE.md
invariant is amended to name it (A).
### R-07 — the import graph around a name index
Opened: module-level imports of `facet_reads.py:27-30`,
`knowledge_resolve.py:48-54`, `writes/knowledge.py:53-58`,
`prose_tokens.py:32-34`; `tooling/verify/checks/import_cycle.py:1-16`;
scratch probe [P].
Finding: `facet_reads -> knowledge_resolve -> writes.knowledge ->
prose_tokens -> lore_resolve` at module level. Probe [P]: a `name_index.py`
with a module-level `from .facet_reads import creator_only_fact_ids`,
imported by `lore_resolve`, makes importing any of `facet_reads`,
`lore_resolve`, `prose_tokens`, `day_concordance`, `knowledge_resolve` raise
`ImportError` (partially initialized module). With the import inside the
function, all of them import and `import_cycle.py` passes.
`import_cycle.py` (`:1-16`) builds its graph from module-level imports only
and names the function-local import the established idiom for breaking a
cycle.
Consequence: `name_index` imports `facet_reads` inside `surfaces()` only
(C-03), and a check rule forbids the module-level form.
### R-08 — the appellation facet, its preset and its writers
Opened: `src/world_engine/facets.py:30-60`; `writes/facets.py:1-261`;
`writes/facts.py:50-80`; `models/canon_knowledge.py:90-120, 163-192`;
`tooling/verify/checks/fact_facets.py:60-90` [M].
Finding: `FacetSpec("appellation", "identite", "affirmation", "location",
"Appellations", ...)` (`facets.py:38-39`). `_preset_scope`
(`writes/facets.py:58-67`): preset `"location"` gives a location scope only
when `entity.type == "location"`, else `none`; preset `"rencontre"` gives
`ScopeChoice("rencontre", entity.id)`. `add_entity_fact` (`:91-133`) calls
`tokenize` on every content (`:124`) and writes the default at level `knows`
when the scope is not `none` (`:133-137`). `edit_entity_fact` (`:241-255`)
tokenizes new text (`:252`). `create_fact`'s `default_level` defaults to
`"unaware"` (`writes/facts.py:58`). `FactDefault` (`canon_knowledge.py:163-192`)
carries `world_id`, `fact_id`, `scope_type` in world/faction/location/
rencontre, `scope_id`, `level`. `fact_facets.py:71` pins
`("appellation", "identite", "affirmation", "location", ())`.
Consequence: N14b changes one registry field and one check line. N17a reads
"has a scope" as: `fact.default_level != 'unaware'` or a `fact_default` row
with `level != 'unaware'`. Appellations written before this lot keep their
defaults (no backfill, N14b).
### R-09 — tokenizer consumers and fixtures
Opened: enumeration E4; `writes/knowledge.py:160-180`;
`tooling/verify/checks/identity_tokens.py:1-30, 170-245` [M].
Finding: `tokenize` is called at `writes/facets.py:124`, `:252`,
`writes/knowledge.py:173`, and in the fixture `identity_tokens.py:222`.
The fixture writes the appellation "la Rousse" on Maelis with
`add_entity_fact` (`:215`) and expects "La Rousse arrive." to tokenize to
Maelis (`:182`). Check R1 confines the identifier `content_raw` to models,
`writes/*.py`, `prose_render.py`, `knowledge_resolve.py`, migrations; R4
forbids `chat(` and `ollama_client` in `prose_tokens.py`.
Consequence: that fixture case holds after A only if "la Rousse" gets a
scope (N14b gives it `rencontre`) and its own text stays plain (N15b). A and
N14b ship together.
### R-23 — governance files
Opened: `tooling/verify/checks/claude_md_contract.py:60-180`;
`tooling/verify/checks/decisions_index.py:1-30`;
`tooling/glue/gen_decisions_index.py:40-55`; `wc -c CLAUDE.md` [M].
Finding: CLAUDE.md is 35 625 characters of a 38 000 budget, lines at most
100 characters, no `TICKET-\d`/`BRIEF-\d` in the Invariants section.
`decisions_index.py` requires `DECISIONS_INDEX.md` to equal a regeneration
(`python tooling/glue/gen_decisions_index.py`) and new headers to match
`^## .+ \(BRIEF-\d{4}(-[a-z])?..., (schema vX.YY|no schema change)\)$`.
Consequence: each brief appends one decision entry with a strict header and
regenerates the index.
### R-25 — check fixture idioms
Opened: `tooling/verify/checks/identity_tokens.py:108-133`;
`tooling/verify/checks/day_concordance_golden.py:78-150` [M].
Finding: `identity_tokens.py` `_fresh_engine()` (`:108-118`) sets
`WORLD_ENGINE_DATABASE_URL` to a temp SQLite file, purges `world_engine`
modules from `sys.modules`, then `create_db_and_tables()`; `_world(session,
label)` (`:121-133`) adds a `World` and returns an `entity(kind, name)`
factory. `day_concordance_golden.py` builds a `Character` row per NPC or PC
with `id=entity.id, world_id, character_type, current_location_id`
(`:125-145`) and calls `concord` with `Mention(category, surface_form,
kind)` (`:223`).
Consequence: the new checks copy these two helpers (by name and body) and
this `Character` construction; they never touch Nia's DB.

## Contracts

### C-01 — `NameScope` and the regime family (`src/world_engine/name_index.py`, new)
Produced by: A   Consumed by: A, B, C, D
```python
REGIMES: tuple[str, ...] = ("names_only", "creator", "prose", "perceiver")

@dataclass(frozen=True)
class NameScope:
    regime: str                                   # one of REGIMES
    known_fact_ids: Optional[frozenset[str]] = None
    exclude_entity_id: Optional[str] = None
    # __post_init__ raises ValueError when: regime not in REGIMES;
    # regime == "perceiver" and known_fact_ids is None;
    # regime != "perceiver" and known_fact_ids is not None.

NAMES_ONLY = NameScope("names_only")
CREATOR = NameScope("creator")
PROSE = NameScope("prose")
```
Regime semantics (which appellation facts count; names always count):

| regime | active entity names | appellation of an active entity |
|---|---|---|
| `names_only` | all | none |
| `creator` | all | all, creator-only included |
| `prose` | all | not creator-only AND has a scope |
| `perceiver` | all | not creator-only AND `fact_id in known_fact_ids` |

"Has a scope" (N17a): `fact.default_level != 'unaware'`, or at least one
`fact_default` row for the fact with `level != 'unaware'`.
"Creator-only": the fact id is in `facet_reads.creator_only_fact_ids(db, ids)`.
`exclude_entity_id`, when set, removes that entity's name and all its
appellations, in every regime.
The regime rules live in one module-level dict literal
`_APPELLATION_RULES` keyed exactly by `REGIMES`.
Who may use `CREATOR` (or construct `NameScope("creator", ...)`):
`name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
`writes/facets.py`. Nowhere else.
Error and empty cases: see `__post_init__`.
### C-02 — `NameSurface` (`name_index.py`)
Produced by: A   Consumed by: A, B, D
```python
@dataclass(frozen=True)
class NameSurface:
    text: str               # entity.name, or the appellation rendered by prose_render.fact_texts
    entity_id: str
    entity_name: str        # entity.name, for display
    entity_type: str        # entity.type
    source: str             # "name" | "appellation"
    fact_id: Optional[str]  # None iff source == "name"
```
Text is never normalized here; callers normalize (`lore_resolve.normalize_surface`).
### C-03 — `surfaces` (`name_index.py`)
Produced by: A   Consumed by: A (`prose_tokens`), B (`lore_resolve`,
`day_concordance`), D (`writes/facets.record_appellation`)
Signature: `surfaces(db: Session, world_id: str, scope: NameScope) -> tuple[NameSurface, ...]`
Behaviour:
1. Active entities of `world_id` (`Entity.status == "active"`), minus
   `scope.exclude_entity_id`: one `source="name"` surface each.
2. Unless the regime is `names_only`: every `fact` with
   `Fact.world_id == world_id` and `Fact.facet == "appellation"`, joined to
   its `fact_participant`, whose participant is one of the entities kept in
   step 1; filtered per C-01's table; text through
   `prose_render.fact_texts`; a surface whose text is empty or None is
   skipped.
3. Order: names first, by `entity_id`; then appellations by
   `(entity_id, fact_id)`.
Every `select(` in the module has `world_id` among the names of its
`.where(` call. `creator_only_fact_ids` is imported inside `surfaces`, never
at module level (R-07). No `db.add(`, `.commit(`, `chat(`.
Error and empty cases: a world with no active entity returns `()`.
### C-08 — `tokenize`, amended (`prose_tokens.py`)
Produced by: A (scope), B (mention path)   Consumed by: A (`writes/facets`),
`writes/knowledge.py:173` (unchanged call)
Signature:
`tokenize(db, *, world_id, text, mentions=None, scope: NameScope = PROSE) -> Tokenized`
Raises `ValueError` when `scope.regime` is not `"prose"` or `"names_only"`.
The index is built from `name_index.surfaces(db, world_id, scope)`; keys and
matching are unchanged. From B on, `_mention_spans` passes the same `scope`
to `resolve_named`. Callers for an appellation's own text pass
`NameScope("names_only", exclude_entity_id=<owner id>)` (N15b):
- `add_entity_fact` with `facet == "appellation"`: owner = `entity_id`.
- `edit_entity_fact` on a fact whose `facet == "appellation"`: owner = the
  fact's participant when it has exactly one; `NameScope("names_only")` with
  no exclusion otherwise.
Every other call keeps `PROSE`.

## Context

TICKET-0091 made every descriptive statement a fact; appellations exist but
only the tokenizer reads them, and it reads all of them, creator-only ones
included (R-01). This brief puts every name surface behind one index with
four regimes (N1c, N2b) and rebuilds the tokenizer on it. Everything else in
the lot reads names through this module.

## Scope IN

1. Create `src/world_engine/name_index.py` implementing C-01, C-02, C-03
   exactly: `REGIMES`, `NameScope` (with the `__post_init__` checks),
   `NAMES_ONLY`, `CREATOR`, `PROSE`, `NameSurface`, the module-level dict
   literal `_APPELLATION_RULES` keyed exactly by `REGIMES` (each value a
   small function or a tuple of flags — your choice, but one entry per
   regime and no regime handled outside it), and `surfaces(db, world_id,
   scope)`. `from .facet_reads import creator_only_fact_ids` goes **inside**
   `surfaces`, with a comment citing the cycle `facet_reads ->
   knowledge_resolve -> writes.knowledge -> prose_tokens -> lore_resolve`
   (R-07). Text of appellations through `prose_render.fact_texts`, never
   `content_raw`. Every `select(` carries `world_id` in its `.where(`.
   Module docstring names TICKET-0092, N1c, N2b, N17a.
2. `src/world_engine/prose_tokens.py`: `_build_index(db, world_id, scope)`
   builds its index from `name_index.surfaces(db, world_id, scope)` — for
   each surface, `key = _key_words(s.text)`, `entry.ids.add(s.entity_id)`,
   `entry.full.add(_full_words(s.text))` (the loop at `:97-104` today) — and
   `info` from the `source == "name"` surfaces
   (`entity_id -> (entity_name, entity_type)`). The direct `select(Entity)`
   and `select(Fact, FactParticipant.entity_id)` in `_build_index` are
   removed. `tokenize` gains `scope: NameScope = PROSE` per C-08 and raises
   `ValueError` for any other regime than `prose` or `names_only`. The
   `_mention_spans` call to `resolve_named` is left as it is (B changes it).
   Update the module docstring's description of the index (names plus
   appellations **that have a scope and are not creator-only**).
3. `src/world_engine/writes/facets.py`, per C-08:
   - `add_entity_fact`: pass `scope=NameScope("names_only",
     exclude_entity_id=entity_id)` to `tokenize` when `facet ==
     "appellation"`, else `scope=PROSE`. Name the local variable
     `name_scope` (the function already has a parameter called `scope`).
   - `edit_entity_fact`: when `fact.facet == "appellation"`, read the fact's
     participant ids (`select(FactParticipant.entity_id).where(
     FactParticipant.fact_id == fact.id)`); exactly one -> exclude it;
     otherwise `NameScope("names_only")`. Other facets: `PROSE`.
4. `src/world_engine/facets.py:38`: the `appellation` preset
   `"location"` becomes `"rencontre"` (N14b). Nothing else in the spec
   changes.
5. `tooling/verify/checks/fact_facets.py:71`: the pinned tuple becomes
   `("appellation", "identite", "affirmation", "rencontre", ())`.
6. `CLAUDE.md`: replace line 149 and line 150 (currently
   "  `facet_reads` by query construction; only the Lore dossier opts in. What an NPC" and
   "  knows-but-conceals lives in `knowledge` rows with `is_secret = TRUE`,")
   with these five lines, verbatim:
   ```
     `facet_reads` by query construction; only the Lore dossier opts in, plus the
     `creator` regime of `name_index` for name resolution (Lore question, names
     panel). Token posing never indexes a creator-only or unscoped appellation.
     What an NPC knows-but-conceals lives in `knowledge` rows with
     `is_secret = TRUE`,
   ```
7. New check `tooling/verify/checks/name_index.py`, stdlib `ast` plus
   fixtures, FAILURES/`fail()` idiom, every rule vacuity-guarded:
   - R1 purity: `name_index.py` contains no `db.add(`, `.commit(`, `chat(`.
   - R2 world scoping: every `select(` call in `name_index.py` is the
     receiver of a `.where(` whose argument names include `world_id`; zero
     `select(` calls fails.
   - R3 regime bijection: the `REGIMES` tuple literal equals the key set of
     the `_APPELLATION_RULES` dict literal.
   - R4 lazy exclusion: no module-level `import`/`from` of `facet_reads` in
     `name_index.py`, and at least one call to `creator_only_fact_ids(`
     inside a function body.
   - R5 creator confinement: across `src/world_engine/**/*.py`, the Name
     `CREATOR` imported from `name_index`, and any `NameScope(` call whose
     first argument is the literal `"creator"`, occur only in
     `name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
     `writes/facets.py`. Finding none outside is the pass; the scan must
     have parsed at least one file.
   - F1 regimes: copy `_fresh_engine` and `_world` from
     `checks/identity_tokens.py:108-133` (R-25). Build the fixture of LOT
     Gate output (b) "Regimes": entity Q active; appellations on Q through
     `add_entity_fact`: a1 with `scope=ScopeChoice("rencontre", Q.id)`, a2
     with `scope=ScopeChoice("none")`, a3 with `scope=ScopeChoice("world")`
     then made creator-only with the call shape of `writes/facets.py:179-182`
     (`write_knowledge(db, entity_id=Q.id, fact_id=a3.id,
     subject="creator_meta", level="unaware", is_secret=True,
     changed_by="check")`); entity X with `status="inactive"` and appellation
     a4 (world). Assert, with exact set equality on
     `(source, entity_id, fact_id)`, the five rows of that table, using
     `NameScope("perceiver", known_fact_ids=frozenset({a2.id, a3.id}))` for
     the perceiver row. Assert `NameScope("perceiver")` and
     `NameScope("creator", known_fact_ids=frozenset())` and
     `NameScope("nope")` raise `ValueError`.
   - F2 tokenizer, each case in its own `_world`:
     (i) appellation "le Masque" on Q made creator-only as in F1:
     `tokenize(... text="Le Masque parle.")` returns the text unchanged;
     (ii) appellation "le Masque" on Q with `ScopeChoice("none")`: unchanged;
     (iii) appellation "la reine" on Y through `add_entity_fact` with no
     explicit scope: "la reine arrive." becomes Y's token + " arrive.";
     (iv) with (iii) in place, `add_entity_fact` of the appellation
     "la reine" on Q, then rename Y to "Ysolde": `prose_render.fact_text`
     of Q's new fact is "la reine" (stored plain — N15b);
     (v) appellation "la fille du vieil Aldric" on Q, then rename Aldric to
     "Aldo": its `fact_text` is "la fille du vieil Aldo";
     (vi) that fresh appellation on the character Q has exactly one
     `fact_default` row, `scope_type == "rencontre"`, `scope_id == Q.id`
     (N14b).
7b. New check `tooling/verify/checks/name_resolution.py`, created here so the
   ticket's acceptance arrow resolves from the first brief on
   (`pipeline_state.py` fails on an arrow to a missing check). Same
   helpers (R-25). One case, G0: in a fresh world, a character "Maelis Varn"
   resolves with today's signature `resolve_named("Maelis Varn", "person",
   world.id, session)` to `matched` via `named_exact`. B rewrites G0 for the
   new signature and adds the lot's cases.
8. `ARCHITECTURE_DECISIONS.md`: append an entry with the header
   `## NAME INDEX (TICKET-0092) -- ONE SOURCE FOR EVERY NAME SURFACE (BRIEF-0092-a, no schema change)`
   recording C-01's table, N15b, N17a, N14b (no backfill) and the lazy
   import; regenerate `DECISIONS_INDEX.md` with
   `python tooling/glue/gen_decisions_index.py`.

## Scope OUT

- `lore_resolve.py`, its rungs and every `resolve_named` caller (B). The
  tokenizer's mention path keeps its current `resolve_named` call until B.
- New categories (C). Near names (B, D). Any route or frontend (D, E).
- A backfill giving a scope to existing appellations (N14b: none).
- `day_concordance.py` (B).

## Invariants to defend

- "Secrets are structurally excluded" (CLAUDE.md:146-153): this brief
  amends its wording by Scope IN 6 exactly, and adds a second opt-in only
  for the `creator` regime. Any other change to that invariant is a STOP.
- "Commit before touching any canon-writing path": `writes/facets.py` is
  one. Commit before item 3.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- `import_cycle.py` fails with the function-local import in place.
- F2's "la Rousse"-style expectations cannot be met without tokenizing an
  appellation's own text.

ADAPT:
- `identity_tokens.py` R3 fails only on the "la Rousse" case: re-read it
  after item 4 (the preset gives it a scope); if it still fails, STOP.
- The CLAUDE.md replacement exceeds a 100-character line: re-wrap the same
  words, report.

REPORT-ONLY:
- The count of `appellation` facts with no scope, if you can measure it on
  a fixture — never on Nia's DB.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/name_index.py` and
      `python tooling/verify/checks/name_resolution.py` print PASS.
- [ ] `pipeline_state.py` passes with TICKET-0092 deposited.
- [ ] Green: `identity_tokens.py`, `fact_facets.py`, `import_cycle.py`,
      `claude_md_contract.py`, `decisions_index.py`, `module_budget.py`,
      `function_length.py`, `single_canon_write.py`.
- [ ] `grep -n "select(" src/world_engine/prose_tokens.py` returns nothing.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`CLAUDE.md` (Scope IN 6), `ARCHITECTURE_DECISIONS.md` +
`DECISIONS_INDEX.md` (Scope IN 8). No schema changelog entry.
