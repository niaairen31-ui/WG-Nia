# BRIEF 0087-E — "The who_knows_about selector, and the checks that must learn its name"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: BRIEF-0087-a (C-01). Ordered last in the lot by decision E2, not
by technical dependency — see the lot header's dependency graph. An executor
finding nothing blocking here is not finding a defect.
Regenerated after AMENDMENT-0087-1 (code `J2`): the `role="subject"`
discriminator is dropped; `fact_participant` is uniquely keyed on
`(fact_id, entity_id)`.

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/lore_selectors.py:199` -> `SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions")`.
- `src/world_engine/lore_selectors.py:201-209` -> `_SELECTOR_LOOKUPS` maps both names to `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections)`.
- `src/world_engine/lore_selectors.py:22-39` -> `SelectorSpec` is a frozen dataclass; `context_sections` defaults to `()`.
- `src/world_engine/lore_selectors.py:139-157` -> `_knowledge_rows` selects `Knowledge` joined to `Entity` on `world_id`, returns `is_secret` on every row, and applies no secrecy filter.
- `src/world_engine/lore_plan.py:29-37` -> `_SELECTOR_DESCRIPTIONS` holds one line per selector, keyed by name.
- `src/world_engine/lore_render.py:62-69` -> `_SECTION_FORMATTERS` holds exactly `identity`, `relations`, `knowledge`, `memberships`, `goals`, `factions`.
- `src/world_engine/lore_render.py:80-86` -> an unknown section raises; it is never skipped.
- `src/world_engine/lore_query.py:174-179` -> a selector row with no `"section"` key raises `ValueError`.
- `src/world_engine/lore_query.py:180-186` -> truncation at `row_cap` is recorded in the trace, not dropped.
- `src/world_engine/lore_query.py:183, 192` -> `content_row_count` excludes `context_sections`; `verdict = "answered" if content_row_count else "silent_canon"`.
- `src/world_engine/writes/knowledge.py:51-65` -> `KNOWLEDGE_LEVEL_LADDER` and `knowledge_level_rank`.
- `tooling/verify/checks/lore_selectors.py:37` -> `SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}` — a hardcoded literal set.
- `src/world_engine/models/canon_knowledge.py:119-122` -> `idx_fact_participant_unique` on `(fact_id, entity_id)`, unique; `role` is `Optional[str] = None` and outside that key.
- `tooling/verify/checks/lore_selectors.py:38-40` -> `EXPECTED_VERDICTS` holds exactly five values.
- `tooling/verify/checks/lore_isolation.py:26-29` -> R8 asserts `_SELECTOR_DESCRIPTIONS`'s key set equals `SELECTORS`.

## Facts carried

**R-12** — adding a selector touches four registries and one hardcoded check
constant:
1. `SELECTORS` and `_SELECTOR_LOOKUPS` (`lore_selectors.py:199-209`).
2. `_SELECTOR_DESCRIPTIONS` (`lore_plan.py:29-37`); `lore_isolation` R8 asserts its key set equals `SELECTORS`.
3. `_SECTION_FORMATTERS` (`lore_render.py:62-69`); an unknown section raises (`lore_render.py:81-85`), guarded by `lore_isolation` R14.
4. `SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}` at `tooling/verify/checks/lore_selectors.py:37` — a **hardcoded literal set**. R2 of that check asserts no selector function name appears in `lore_query.py`. A third selector not added here is simply not covered by R2, silently. This is the TICKET-0086 defect class.

**R-13** — `validate_plan` rejects, before any row is read, a selector outside
`SELECTORS`, an arity mismatch, an unknown mention ref, or an `arg_kinds`
mismatch. `arg_kinds` admits exactly two values: `"entity_id"` (a mention
ref) and `"world_id"` (the literal `"$world"`). `execute_plan` raises
`ValueError` on any row with no `"section"` key, truncates at `row_cap`
recording `truncated` in the trace, and excludes `context_sections` rows from
`content_row_count`, which is what decides `answered` versus `silent_canon`.
R5 of `checks/lore_selectors.py` asserts the verdict literals in
`lore_query.py` equal exactly five values.

**R-11** — `_knowledge_rows` (`lore_selectors.py:139-157`) selects `Knowledge`
joined to `Entity` on `world_id`, with no `is_secret` filter, and returns
`is_secret` as a key on every row. F1b is the existing precedent, not a new
exception.

**R-07** — after a complete backfill, "qui sait quoi sur X" has a non-empty
answer for 42 of 297 active entities (14.1%). On Verkhaal, 6 of 57: Maelis
(6 knowers), La Mer Rouge (2), and four with one knower each.

**R-02** — `fact_participant` carries `idx_fact_participant_unique` on
`(fact_id, entity_id)`, unique (`canon_knowledge.py:119-122`), and `role` is
`Optional[str] = None`, outside that key. Under J2 a participant IS the
aboutness claim: there is no discriminator, and the unique key guarantees one
participant row per `(fact, entity)` — so no knowledge row can appear twice in
one answer.

## Contracts

Produces **C-04** and **C-05**, verbatim from the lot header.

### C-04 — selector family contract: `who_knows_about`

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

Returns a flat list of row dicts. Every row carries `"section"`.

`section="knowers"` — zero or more. One per `knowledge` row whose fact carries
a `fact_participant` with `entity_id == <the asked entity>`, **with no role
filter**, the knowing entity being world-scoped at query construction.
`idx_fact_participant_unique` guarantees at most one participant row per
`(fact, entity)`, so no knowledge row can appear twice.
Required keys, every one present on every row:

```
section, knower_entity_id, knower_name, level, content, source,
is_incorrect, is_secret, subject_name
```

Ordered by `knowledge_level_rank(level)` descending
(`writes/knowledge.py:56-65`), then by `knower_name` ascending, so the order
is total and stable.

`section="coverage"` — **exactly one, always, including when there are zero
knowers.** Required keys:

```
section, subject_name, counted_rows, uncounted_rows
```

- `counted_rows` is the number of `knowers` rows before `row_cap` truncation.
- `uncounted_rows` is the number of `knowledge` rows in this world whose fact carries **no participant at all** — the rows this selector structurally cannot see.
- `subject_name` is the asked entity's `name`.

Because `coverage` is declared in `context_sections`, it never counts toward
`content_row_count`, so a target with no knowers yields `silent_canon` and not
a false `answered`.

Error and empty cases: an `entity_id` that does not exist in `world_id` never
reaches this function — `execute_plan` returns `unknown_entity` at mention
resolution first. This function assumes a resolved, world-scoped entity and
does not re-check it.

### C-05 — section formatters for the two new sections

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

## Context

This is the reader that justifies the whole ticket — the structure exists
(TICKET-0082), the writer exists (BRIEF-0087-a), the data has been filled
(BRIEF-0087-c and -d). Coverage grows by adding a selector, never by adding a
question type, so this brief adds exactly one.

The coverage row is decision D1 and is not decoration: on Nia's own worlds
this selector can see about one knowledge row in six, and a partial answer
that says it is partial is the difference between a useful surface and a lie.

## Scope IN

1. **`src/world_engine/lore_selectors.py`** — implement `who_knows_about` per `C-04`. World scoping goes in the `select(...).where(...)`, never post-fetch: `lore_isolation` R2 asserts every `select(` in this module has a world constraint among its `.where(` arguments or joins `Entity` with one.

2. The `knowers` query joins `Knowledge` -> `Fact` on `knowledge.fact_id`, `Fact` -> `FactParticipant` on `fact_id`, and `Knowledge.entity_id` -> `Entity` for the knower's name and world scope. Filter `FactParticipant.entity_id == <asked entity>` and **nothing else** — no role predicate. Counting a TICKET-0082 arity participant as a knower is deliberate under J2: a fact "Maelis conspires with Vance" is about both, and "qui sait quoi sur Maelis" must return it.

3. Apply **no** `is_secret` filter (F1b, R-11). Apply **no** `is_incorrect` filter (F2). Both are returned as keys and marked by the formatter.

4. Order by `knowledge_level_rank(level)` descending, then `knower_name` ascending (F3). Import `knowledge_level_rank` from `writes/knowledge.py` — do not re-type the ladder. If that import would make `lore_selectors.py` import from `writes/`, and `import_cycle.py` or a purity rule forbids it, that is a STOP: R1 forbids `db.add(` and `.commit(` in this module, not an import of a pure ranking function, but the call is the executor's to verify, not to assume.

5. Emit the `coverage` row **unconditionally**, as the last row, even when `knowers` is empty. `uncounted_rows` counts `knowledge` rows in `world_id` whose fact has **no participant at all** — a `NOT EXISTS` against `fact_participant` with no role predicate, world-scoped through the join to `entity`.

6. Register in `SELECTORS` and `_SELECTOR_LOOKUPS` exactly as `C-04` specifies.

7. **`src/world_engine/lore_plan.py`** — add one `_SELECTOR_DESCRIPTIONS` entry, in the existing French one-line style of the other two:

   ```
   "who_knows_about": (
       "who_knows_about(entity_id, $world) -- qui, dans le monde, détient un "
       "savoir portant sur UNE entité nommée : un connaisseur par ligne, avec "
       "son niveau."
   ),
   ```

   Verbatim. The executor copies it.

8. **`src/world_engine/lore_render.py`** — add the two `_SECTION_FORMATTERS` entries per `C-05`, with their message text verbatim. Place them after `factions` so the section-contract order reads identity, relations, knowledge, memberships, goals, factions, knowers, coverage.

9. **`tooling/verify/checks/lore_selectors.py:37`** — add `"who_knows_about"` to `SELECTOR_FUNCTION_NAMES`. Without this edit, R2 silently stops covering the new selector. This is a Scope IN item with its own done-means line precisely because it is the failure TICKET-0086 just fixed elsewhere.

10. While in that check file, look at whether `SELECTOR_FUNCTION_NAMES` could be derived from `SELECTORS` by the same AST read R1 already performs, instead of being a hand-maintained literal. If it can, do it, in a **separate commit** from the rest of this brief. If it cannot without weakening R2, leave the literal and REPORT-ONLY what blocks it. Do not attempt the same derivation anywhere else in the check corpus — that is TICKET-0085 queue item 7 and is out of scope here.

11. **Do not add a verdict.** R5 of the check asserts exactly five. The coverage report is a row in a `context_sections` section, which is the mechanism that exists for exactly this.

## Scope OUT

- **Any second selector.** `location_contents`, `faction_roster`, `region_locations` are one ticket each, by the chantier's own rule.
- **A viewpoint parameter.** The surface answers as the creator, always.
- **A write path.** `lore_selectors.py` and `lore_query.py` stay free of `db.add(` and `.commit(` (R1/R4).
- **The audit of check files for bare-identifier matching.** Item 10 fixes at most the one constant this brief touches. The corpus-wide sweep is TICKET-0085 queue item 7.
- **The honest offline message** — `/api/lore/ask` returning 503 with Ollama stopped. TICKET-0085 queue item 8.
- **`entity_dossier`.** Its `knowledge` section keeps returning `subject` as free text; it is not rewritten to use participants.
- **The dedup guard**, in all three forms.
- **Trace persistence.** TICKET-0085 locked the trace as displayed and foldable, not persisted. The coverage row is part of the returned rows, not a stored artefact.
- **`knowledge.subject`**, its type, index, and every existing read of it.
- **Widening `NAMED_RUNGS`** or changing `_MENTION_CATEGORIES`.

## Invariants to defend

- **Exclusion is structural, never instructional.** This selector returns secrets by construction because this is the creator's surface and `entity_dossier` already does (R-11). It must not become reachable from any NPC or MJ context assembler. If a shared helper would let it, that is a STOP.
- **The MJ context assembler is scoped to the player's perception boundary** (`CLAUDE.md:168-171`). Untouched. Nothing in this brief edits an assembler.
- **World scoping at query construction** (`lore_isolation` R2). Every filter goes in `.where(`, never after the fetch.
- **The model never sees canon at planning time** (R5). `lore_plan.py` gains a description string and nothing else.
- **Fail-closed over advisory.** A selector row without a `"section"` key raises. The coverage row is emitted unconditionally, so a zero-knower answer can never silently look like a complete one.
- **No structure without a reader.** This brief is the reader. After it, `fact_participant` has one.

## Decision rights

**STOP:**
- Any anchor above has moved.
- Importing `knowledge_level_rank` from `writes/knowledge.py` into `lore_selectors.py` fails `import_cycle.py`, or is forbidden by a purity rule the executor finds in `lore_isolation.py`.
- Adding the `coverage` section forces a sixth verdict in `lore_query.py`, or `execute_plan` cannot be left unmodified.
- `lore_selectors.py` crosses the 1000-line cap, or `who_knows_about` cannot be kept under 80 lines without a helper that `lore_isolation` R2 would then have to inspect separately.
- The `uncounted_rows` count cannot be computed world-scoped at query construction.

**ADAPT:**
- `FactParticipant` is not currently imported in `lore_selectors.py`: add it to the existing `from .models import ...` line, proceed, report.
- `lore_isolation` R2's world-constraint detection does not recognise the shape of the `NOT EXISTS` subquery: restructure the query so the constraint is visible where R2 looks, proceed, report. Do not weaken R2.
- The section-contract comment block at `lore_render.py:27-32` names the vocabulary in prose: update it to include the two new sections, proceed, report.
- `SelectorSpec`'s `context_sections` needs its R6 vocabulary match: the string `"coverage"` must appear as a `"section"` literal in `lore_selectors.py`, which emitting the row already satisfies; confirm and report.
- Item 10's derivation is possible: do it in its own commit, proceed, report.

**REPORT-ONLY:**
- The measured `counted_rows` / `uncounted_rows` for Verkhaal after the selector exists.
- Any other check file in `tooling/verify/checks/` observed to carry a hand-maintained literal set of the same shape. Note the file and the constant; change nothing.
- Any question phrasing during manual testing that the planner fails to route to `who_knows_about`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `SELECTORS`, `_SELECTOR_LOOKUPS` and `_SELECTOR_DESCRIPTIONS` each hold exactly three names, including `who_knows_about`.
- [ ] `SELECTOR_FUNCTION_NAMES` in `tooling/verify/checks/lore_selectors.py` holds all three names.
- [ ] `_SECTION_FORMATTERS` holds eight entries, ending with `knowers` and `coverage`.
- [ ] On Verkhaal, `who_knows_about(<Maelis id>, "verkhaal", db)` returns 6 `knowers` rows plus exactly 1 `coverage` row, and the verdict from `execute_plan` is `answered`.
- [ ] Every returned `knowers` row carries all nine keys of `C-04`; a missing key is caught by `execute_plan`'s section guard only for `section`, so this is asserted directly.
- [ ] The `knowers` rows are ordered by level rank descending; two rows at the same level are ordered by `knower_name` ascending.
- [ ] For an entity with no knower, the result is exactly 1 `coverage` row, `counted_rows == 0`, and the verdict is `silent_canon` — not `answered`, and not an empty silence.
- [ ] `uncounted_rows` for Verkhaal equals the count of that world's knowledge rows whose fact has no `fact_participant` row at all, verified by an independent SQL query.
- [ ] A knowledge row with `is_secret = TRUE` appears in the output and its rendered line ends with " (secret)".
- [ ] A knowledge row with `is_incorrect = TRUE` appears and its rendered line contains " (croyance fausse)".
- [ ] A row that is both renders the false-belief marker before the secret marker.
- [ ] A fact carrying a participant with a non-NULL role contributes a `knowers` row exactly as one with a NULL role does — J2 makes this the intended behaviour, and a selector that filtered it out would be the defect.
- [ ] No knowledge row appears twice in one answer, which `idx_fact_participant_unique` guarantees structurally.
- [ ] `python tooling/run.py` — `lore_selectors.py`, `lore_isolation.py`, `lore_resolve.py`, `fact_spine.py`, `module_budget.py`, `function_length.py`, `import_cycle.py`, `undefined_names.py`, `corpus_gate.py` all PASS.
- [ ] Removing `"who_knows_about"` from `SELECTOR_FUNCTION_NAMES` and re-running the check demonstrates R2 no longer covers it — run once to prove the line matters, then restore.
- [ ] Asking "qui sait quoi sur Maelis" through `/api/lore/ask` returns prose naming her knowers, and the folded trace shows the coverage line.
- [ ] `/review-step` and `/close-step` run; engine code is touched.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: one entry for D1 — `who_knows_about` reports its own coverage as a `context_sections` row rather than a verdict, with the reason (the five verdicts are a closed set asserted by R5, and a coverage number is not a verdict). Record the rejected alternative (D2, silent return) with no reactivation condition: it was rejected on doctrine, not on cost.
- `CLAUDE.md`: the symbol-location line for `who_knows_about`, per the TICKET-0070 rule.
- No schema changelog entry. No version bump.
