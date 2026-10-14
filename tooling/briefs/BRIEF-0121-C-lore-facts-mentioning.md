<!-- slug: lore-facts-mentioning -->
# BRIEF 0121-C — "The lore searched by its words -- the selector facts_mentioning, its text: argument, and the designer's gathering quest_lore.py (S2, no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `301d178`.

- `src/world_engine/lore_selectors.py:301` -> `SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions", "who_knows_about")`; `:303` `_SELECTOR_LOOKUPS` with three `SelectorSpec(` entries; `class SelectorSpec` fields `fn, arity, row_cap, arg_kinds, context_sections`.
- `src/world_engine/lore_query.py:63` -> `def validate_plan(` whose argument loop accepts `"$world"` (kind `world_id`) or a mention ref (kind `entity_id`) and nothing else.
- `src/world_engine/lore_query.py` -> in `execute_plan`, the line `args = [world_id if a == "$world" else resolutions[a].entity_id for a in call.args]`.
- `src/world_engine/lore_plan.py:32` -> `_SELECTOR_DESCRIPTIONS` with three keys.
- `src/world_engine/lore_render.py:95` -> `_SECTION_FORMATTERS` (an unknown section raises in `_group_rows_by_section`).
- `src/world_engine/facet_reads.py:58` -> `def creator_only_fact_ids(db: Session, fact_ids: Iterable[str]) -> set[str]:`
- `src/world_engine/lore_resolve.py:73` -> `def normalize_surface(text: str) -> str:`; `:143` `def resolve_named(surface_form, category, world_id, db, *, scope)`.
- `src/world_engine/prose_render.py:71` -> `def fact_texts(db: Session, facts: list) -> list[str]:`
- No `src/world_engine/quest_lore.py`, no `tooling/verify/checks/lore_facts_mentioning.py`.

## Facts carried

### R-17 — the lore consultation [M]
Opened: `lore_selectors.py:1-80`, `:235-300` (`entity_dossier`, `who_knows_about`), `:301-315` (`SELECTORS`, `_SELECTOR_LOOKUPS`); `lore_query.py:63-98` (`validate_plan`), `:141-215` (`execute_plan`, verdicts); `lore_plan.py:32-80` (`_SELECTOR_DESCRIPTIONS`, `_coerce_call`); `lore_render.py:95-125` (`_SECTION_FORMATTERS`, unknown section raises); `facet_reads.py:58-63` (`creator_only_fact_ids`); `prose_render.py:63-84` (`fact_text`, `fact_texts`); `lore_resolve.py:73-90` (`normalize_surface`), `:134-175` (`NamedResolution`, `resolve_named`); `tooling/verify/checks/lore_isolation.py:1-60` (R1, R2, R8, R14, R17).
Finding: three selectors, each keyed by an entity or the world; an argument is `$world` or a mention ref, and `validate_plan` accepts only kinds `entity_id` and `world_id`; verdicts `answered`, `silent_canon`, `unknown_entity`, `ambiguous_mention`, `unsupported_selector` (pasted in Gate (c)). A fact nobody names as an entity is unreachable. `who_knows_about` returns one `coverage` row then `knowers` rows, secrets marked.
Consequence: S2 -- a fourth selector with a new argument kind `text`; the designer calls the selector functions directly (no plan model), the consultation surface gains it through the whitelist.

### R-22 — secret, for the prose guard [M]
Opened: `day_plan.py:204-220` (`_anchorable_facts`), `facet_reads.py:58-63`.
Finding: a fact the world holds only on `is_secret` rows is not anchorable; a creator-only fact is listed by `creator_only_fact_ids`.
Consequence: V1's « secret » is: a creator-only fact, or a fact no entity holds on a non-secret row (C-10).

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.


## Contracts

### C-04 — `facts_mentioning` and the `text:` argument
Produced by: BRIEF-0121-C   Consumed by: C-05, the Lore consultation
`lore_selectors.facts_mentioning(text: str, world_id: str, db: Session) -> list[dict]`. `text` is the words to look for (the argument without its `text:` prefix). A fact of the world matches when every token of `normalize_surface(text)` of length >= 3 (at least one such token, else no row) appears among the tokens of `normalize_surface(<the fact's rendered text>)` -- compared in Python, never in SQL. Rows: one `coverage` row first `{section: "coverage", subject_name: <text>, counted_rows: <n facts>, uncounted_rows: 0}`, then per matching fact, ordered by its rendered text then id, `{section: "mentions", fact_id, content, creator_only: bool, participants: [<names>], knowers: [{knower_entity_id, knower_name, level, is_secret}]}` (knowers by level rank descending then name). Creator-only facts included and marked (the dossier's precedent, INV-01's creator regime). `SelectorSpec(fn=facts_mentioning, arity=2, row_cap=200, arg_kinds=("text", "world_id"), context_sections=("coverage",))`; `SELECTORS` ends `..., "facts_mentioning"`. `validate_plan`: an argument of kind `text` must start `text:` and hold a non-empty rest; `execute_plan` passes the rest. `_SELECTOR_DESCRIPTIONS["facts_mentioning"] = 'facts_mentioning("text:<mots>", $world) -- les faits dont le texte contient ces mots (un sujet qui n\'est pas une entité nommée), avec ceux qui les savent.'`; `lore_render._SECTION_FORMATTERS["mentions"]` renders `« <content> » -- <participants> ; su par <name (level, secret)>, ...`.
Error and empty cases: no token of 3 letters or more -> `[coverage]` only (counted 0) -> `silent_canon`.

### C-05 — the designer's lore gathering
Produced by: BRIEF-0121-C   Consumed by: BRIEF-0121-E
`quest_lore.gather_lore(db, world_id, *, keywords: list[str], names: list[str], entity_ids: tuple[str, ...] = (), lore_entry_id: Optional[str] = None) -> LoreGathering`.
`LoreGathering(fact_ids: tuple[str, ...], entity_ids: tuple[str, ...], lines: tuple[str, ...], empty: bool)`:
- `entity_ids`: `entity_ids` given, then each name of `names` resolved by `lore_resolve.resolve_named(name, "other", world_id, db, scope=CREATOR)` when `matched` (an ambiguous or unmatched name is skipped -- the designer sees what is certain);
- `fact_ids`, in order, de-duplicated: the facts of `facts_mentioning(" ".join(keywords))` (each keyword on its own when the joined call finds nothing), then every fact with a `fact_participant` on each entity of `entity_ids`, then the facts of the `lore_entry_row` rows of `lore_entry_id` whose `row_table = 'fact'`;
- `lines`: one line per fact, `« <text> » -- su par <name> (<level><, secret>), ...` or `« <text> » -- su de personne`, creator-only facts suffixed `(réservé à la créatrice)`;
- `empty`: no fact found.
Reads only. Creator regime: every fact, creator-only included (INV-01, amended by E).


## Context

S2: the consultation reaches only what is attached to a named entity or the
world as a whole. A secret phrased as a fact that only a scholar holds --
« le secret de l'acier noir » -- was unreachable, so the designer would have
asked the creator whether something that already exists exists. This brief
adds a deterministic search by the subject's words, usable by the Lore
question surface (through the whitelist) and by the designer (directly).

## Scope IN

1. `lore_selectors.py`: `facts_mentioning(text, world_id, db)` exactly as C-04. Its `select(Fact)` carries `Fact.world_id == world_id` at construction (lore_isolation R2); its knowers come from `Knowledge` joined to `Entity` with `Entity.world_id == world_id`; tokens via `normalize_surface(...).split()`, the 3-letter floor applied to the query's tokens only; texts through `fact_texts` (one render for the whole world's facts). Add it to `SELECTORS` (last) and `_SELECTOR_LOOKUPS` with C-04's `SelectorSpec`.
2. `lore_query.py`: `validate_plan` accepts an argument of kind `text` when it starts `text:` and its rest, stripped, is non-empty -- any other argument for a `text` kind is rejected with « selector X argument Y expects text:<mots> »; a `text:` argument for another kind is rejected. `execute_plan` maps a `text:` argument to its rest. The docstrings name the new kind.
3. `lore_plan.py`: `_SELECTOR_DESCRIPTIONS["facts_mentioning"]` as C-04, verbatim.
4. `lore_render.py`: `_SECTION_FORMATTERS["mentions"]` rendering one row as C-04 (« su de personne » when it has no knower; `secret` after a secret knower's level; `(réservé à la créatrice)` when `creator_only`). The `coverage` formatter already exists and is reused.
5. `src/world_engine/quest_lore.py` (new): `LoreGathering` and `gather_lore` exactly as C-05. Reads only; imports `facts_mentioning` and `resolve_named` (never `lore_plan`, never a model). Its docstring's first sentence for FILE_MAP; it names INV-01's creator regime and states that its only caller is the quest designer (BRIEF-0121-E).
6. New check `tooling/verify/checks/lore_facts_mentioning.py` (fresh temp-file SQLite, rows through the real writers):
   - **LF1** two worlds; in A, facts « Le secret de l'acier noir tient dans la trempe » (known by an NPC `is_secret=True`), « L'acier ordinaire vient du nord » (known by nobody), a creator-only fact naming « acier noir »; in B, a fact « acier noir ». `facts_mentioning("acier noir", A)` returns the coverage row then exactly A's two « acier noir » facts, the secret knower marked, the creator-only fact flagged; nothing of B.
   - **LF2** `facts_mentioning("de la", A)` (no token of 3 letters or more beyond articles) returns the coverage row only, `counted_rows == 0`.
   - **LF3** `validate_plan` accepts `facts_mentioning("text:acier", "$world")`, refuses `("$world", "$world")`, `("text:", "$world")`, and a `text:` argument given to `entity_dossier`; `execute_plan` on the accepted plan answers `answered` with the `mentions` rows.
   - **LF4** `render_template` of that result holds the formatted line (no `ValueError` for the section).
   - **LF5** `gather_lore(keywords=["acier", "noir"], names=[<the NPC's name>], lore_entry_id=<an entry whose rows hold one fact>)` gives the facts in C-05's order without duplicates, the NPC in `entity_ids`, one line per fact; `gather_lore(keywords=["dragon"], names=["Zorglub"])` gives `empty == True` and no entity.
7. `lore_isolation.py` stays green: R8 (descriptions == selectors) by item 3; R2 by item 1; R14 by item 4. No change to the check unless a rule names the selector count literally (ADAPT below).
8. `tooling/standards/ARCHITECTURE_DECISIONS.md`: an entry above the footer, `## THE LORE IS SEARCHED BY ITS WORDS TOO (TICKET-0121) -- facts_mentioning AND THE text: ARGUMENT (BRIEF-0121-c, no schema change)`: S2, why deterministic tokens and not a model (an absence is never explained by a model, INV-58), S3 deferred and watched. Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.

## Scope OUT

- A search by meaning, embeddings, any new dependency (S3, deferred).
- Any change to the Lore question prompt's text (the selector's description line reaches it through `{selectors}`).
- The designer itself (E); the Lore writing panel (G).
- Every later brief of this lot.

## Invariants to defend

- **INV-01** -- `facts_mentioning` returns creator-only facts, as `entity_dossier` does, on a creator surface only: the Lore consultation and the designer. No play assembler, no player route calls it; LF1 asserts the flag so a renderer can mark it.
- **INV-58** -- an empty search is `silent_canon`, rendered by code; no model explains an absence.
- **INV-02** -- untouched: nothing here reaches a play context.

## Decision rights

STOP:
- an anchor does not hold;
- `lore_isolation.py` forbids an import `quest_lore.py` needs (a rule reaching modules outside the consultation's).
ADAPT:
- a lore check counts the selectors literally (« three »): raise it to four, report.
- the Lore question frontend hides a row field the `mentions` row carries: leave it (rows render generically, R-17), report.
REPORT-ONLY:
- how many facts a production world holds (the render cost of one search).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `lore_facts_mentioning.py` PASS (LF1-LF5); `lore_isolation.py`, `lore_resolve.py` checks and every `lore_*` check PASS.
- [ ] Named mutations, red then reverted: drop the `Fact.world_id` filter (LF1, and lore_isolation R2); skip the 3-letter floor (LF2); let `validate_plan` accept a bare string for `text` (LF3); remove the `mentions` formatter (LF4).
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`, regenerated `DECISIONS_INDEX.md`, `FILE_MAP.md`. No schema change.
