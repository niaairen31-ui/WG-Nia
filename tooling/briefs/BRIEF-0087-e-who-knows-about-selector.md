# BRIEF 0087-E — "The who_knows_about selector, and the check that learns its name by reading it"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: BRIEF-0087-a (C-01). Ordered last in the lot by decision E2, not
by technical dependency. An executor finding nothing blocking here is not
finding a defect.
Regenerated after AMENDMENT-0087-1 (code `J2`): no `role` discriminator.
AMENDMENT-0087-2 (code `K3`) placed TICKET-0088 before this brief; it is
merged.
**Regenerated after AMENDMENT-0087-3** (codes `G1`, `L1`, `M1`, `N1`, `P1`):
anchors re-measured on `main` at `2ae232b` (R-28); `coverage` is the first
row (M1); R2 derives its names instead of reading a literal (N1); the
branch start and the PR are specified (L1); no prompt change (P1); the
done-means are rewritten around what `run.py` actually runs (R-22).

## Anchors to confirm (Mini-RECON)

Halt if any has moved. Each is stated from the file that declares it.

- `git merge-base --is-ancestor ticket/0087 origin/main` exits 0 (R-21).
- `src/world_engine/lore_selectors.py:199` -> `SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions")`.
- `src/world_engine/lore_selectors.py:201-209` -> `_SELECTOR_LOOKUPS` maps both names to `SelectorSpec(...)`; `world_factions` is the last entry.
- `src/world_engine/lore_selectors.py:22-39` -> `SelectorSpec` is a frozen dataclass; `context_sections` defaults to `()`.
- `src/world_engine/lore_selectors.py:16, 19` -> `from sqlmodel import Session, select` and `from .models import Character, Entity, Faction, Knowledge, NpcGoal, Relation`.
- `src/world_engine/lore_selectors.py:190-191, 204` -> `entity_dossier` returns `_identity_rows(...)` first; `identity` is its sole `context_sections` entry.
- `src/world_engine/lore_query.py:174-179` -> a row with no `"section"` key raises `ValueError`.
- `src/world_engine/lore_query.py:180-181` -> `truncated = len(result_rows) > spec.row_cap` then `result_rows = result_rows[: spec.row_cap]`.
- `src/world_engine/lore_query.py:183, 192` -> `content_row_count` excludes `context_sections`; `verdict = "answered" if content_row_count else "silent_canon"`.
- `src/world_engine/lore_plan.py:29-37` -> `_SELECTOR_DESCRIPTIONS` holds exactly `entity_dossier` and `world_factions`.
- `src/world_engine/lore_render.py:27-31` -> the section-contract comment ends "Order here is the order rows are grouped for both the model prompt and the template fallback."
- `src/world_engine/lore_render.py:62-69` -> `_SECTION_FORMATTERS` holds exactly `identity`, `relations`, `knowledge`, `memberships`, `goals`, `factions`.
- `src/world_engine/lore_render.py:78-86` -> `_group_rows_by_section` groups with `setdefault` in row order and raises on an unknown section.
- `src/world_engine/writes/knowledge.py:64-74` -> `knowledge_level_rank(level)` returns the ladder index, or -1.
- `src/world_engine/models/canon_knowledge.py:119-128` -> `idx_fact_participant_unique` on `(fact_id, entity_id)`, unique; `world_id` NOT NULL at `:125`; `role: Optional[str] = None` at `:128`.
- `tooling/verify/checks/lore_selectors.py:38` -> `SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}`.
- `tooling/verify/checks/lore_selectors.py:131-148` -> `check_no_dispatch_outside_table` flags any `Name`/`Attribute` in `lore_query.py` whose name is in `SELECTOR_FUNCTION_NAMES`.
- `tooling/verify/checks/lore_selectors.py:39-41` -> `EXPECTED_VERDICTS` holds exactly five values.
- `tooling/verify/checks/lore_isolation.py:148-170` -> R1 forbids `db.add(`, `db.commit(` and `chat(` in `lore_selectors.py` and `lore_query.py`.
- `tooling/verify/checks/lore_isolation.py:173-215` -> R2 requires each `select(` in `lore_selectors.py` to sit under a `.where(` naming `world_id` or `Entity`.
- `tooling/verify/checks/lore_isolation.py:404-434` -> R8 requires `_SELECTOR_DESCRIPTIONS`'s keys to equal `SELECTORS`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`; entries are separated by one blank line.

## Facts carried

Verbatim from the lot header.

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

### R-11 -- `entity_dossier` already returns secrets to this surface

Opened: `src/world_engine/lore_selectors.py:139-157`.

Finding: `_knowledge_rows` selects `Knowledge` joined to `Entity` on
`world_id`, with no `is_secret` filter, and returns `is_secret` as a key on
every row.

Consequence: F1b is the existing precedent, not a new exception. The MJ
context assembler's structural exclusion (CLAUDE.md, "Secrets are
structurally excluded") governs assembled NPC context and is untouched here.
BRIEF-0087-e must not be read as licence to relax it anywhere else.

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

## Contracts

Produces **C-04** and **C-05**, verbatim from the lot header.

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

## Context

The structure exists (TICKET-0082), the writer exists (BRIEF-0087-a), the
backfill ran (BRIEF-0087-c), and the creator can bind subjects from the entity
sheet (BRIEF-0087-d) and from the « Sujets » tab (TICKET-0088). This brief adds
the reader that justifies all of it: one selector. Coverage grows by adding a
selector, never a question type.

The coverage row is decision D1, and not decoration: on Nia's worlds this
selector sees a minority of knowledge rows, and a partial answer that says it
is partial is the difference between a useful surface and a lie. Every
edit below was run once on a copy of `main` (R-27); the code is copied, not
re-derived.

## Scope IN

1. **Start on `ticket/0087`, fast-forwarded to `main` (L1).** In order:
   1. `git fetch origin`; `git switch ticket/0087`.
   2. `git merge-base --is-ancestor ticket/0087 origin/main` must exit 0.
   3. `git merge --ff-only origin/main`. Then `git rev-parse HEAD` and
      `git rev-parse origin/main` must print the same hash. No merge commit.
   4. `git status --porcelain` lists only the four deposited files:
      `tooling/tickets/AMENDMENT-0087-3-closing-repairs.md`,
      `tooling/tickets/TICKET-0087-knowledge-subject-participants.md`,
      `tooling/lots/LOT-0087-knowledge-subject-participants.md`,
      `tooling/briefs/BRIEF-0087-e-who-knows-about-selector.md`.
   5. Commit exactly those four:
      `chore(pipeline): TICKET-0087 AMENDMENT-0087-3 -- closing repairs deposited, opening BRIEF-0087-e`.
   6. Record the baseline: `python tooling/verify/checks/corpus_gate.py`, with
      `$env:PYTHONPATH = "src"` and `$env:WORLD_ENGINE_ENV = "test"`. Expected
      on `2ae232b`: 111 checks, 111 passed.
   Run this brief through `/brief-exec BRIEF-0087-e`. **Never invoke
   `/pipeline TICKET-0087`** before item 10's PR exists (R-21).

2. **Commit A — R2 reads its names from the code (N1).** In
   `tooling/verify/checks/lore_selectors.py`:
   - Delete line 38, `SELECTOR_FUNCTION_NAMES = {"entity_dossier", "world_factions"}`.
   - Insert this function immediately above `check_no_dispatch_outside_table`:

```python
def _selector_function_names() -> set[str]:
    """R2's subject list, derived from the code it guards: the `fn=` keyword
    of every `SelectorSpec(...)` in `lore_selectors.py`. Never a
    hand-maintained literal -- a selector added without a matching edit here
    would silently fall outside R2 (the TICKET-0086 defect class)."""
    tree = _parse(LORE_SELECTORS_FILE)
    if tree is None:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "SelectorSpec")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "SelectorSpec")
            )
        ):
            continue
        for kw in node.keywords:
            if kw.arg == "fn" and isinstance(kw.value, ast.Name):
                names.add(kw.value.id)
    return names
```

   - Replace the whole of `check_no_dispatch_outside_table` with:

```python
def check_no_dispatch_outside_table() -> None:
    selector_function_names = _selector_function_names()
    if not selector_function_names:
        fail(
            f"lore_selectors R2: {_rel(LORE_SELECTORS_FILE)}: zero `fn=` names read from "
            "SelectorSpec(...) constructions -- vacuous"
        )
        return
    tree = _parse(LORE_QUERY_FILE)
    if tree is None:
        return
    found: set[str] = set()
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name in selector_function_names:
            found.add(name)
    if found:
        fail(
            f"lore_selectors R2: {_rel(LORE_QUERY_FILE)} names selector function(s) {sorted(found)!r} "
            "directly -- dispatch must go only through _SELECTOR_LOOKUPS[...]"
        )
```

   - Replace the R2 paragraph of the module docstring (lines 7-9) with:

```
R2 (no dispatch outside the table): no selector function name appears
anywhere in `lore_query.py` — every call goes through
`_SELECTOR_LOOKUPS[...]`. The names are read from the `fn=` keyword of every
`SelectorSpec(...)` in `lore_selectors.py`, never from a hand-kept list
(TICKET-0087, BRIEF-0087-e); zero names read is a FAILURE.
```

   The check's PASS line is unchanged. Commit alone:
   `refactor(verify): TICKET-0087 BRIEF-0087-e -- lore_selectors R2 derives selector names from SelectorSpec(fn=...)`.
   Do not derive any other literal in any other check (TICKET-0085 queue item 7).

3. **`src/world_engine/lore_selectors.py` — imports.** Line 16 becomes
   `from sqlmodel import Session, func, select`. Line 19 becomes
   `from .models import Character, Entity, FactParticipant, Faction, Knowledge, NpcGoal, Relation`,
   followed by a new line `from .writes.knowledge import knowledge_level_rank`.
   Import the rank function; never re-type the ladder.

4. **`src/world_engine/lore_selectors.py` — the selector (C-04).** Insert,
   immediately above `SELECTORS`, verbatim:

```python
def who_knows_about(entity_id: str, world_id: str, db: Session) -> list[dict]:
    """Who, in this world, holds knowledge about ONE entity (TICKET-0087,
    BRIEF-0087-e, C-04). One `coverage` row first, always -- first so the
    tail truncation at `row_cap` in `execute_plan` can never drop it -- then
    one `knowers` row per `knowledge` row whose fact carries a
    `fact_participant` for the asked entity, with no role filter (J2).
    Secrets and false beliefs are returned and marked by the renderer
    (F1b, F2); ordered by level rank descending, then knower name (F3)."""
    subject = db.exec(
        select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)
    ).first()
    subject_name = subject.name if subject is not None else None
    pairs = db.exec(
        select(Knowledge, Entity)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .join(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(Entity.world_id == world_id, FactParticipant.entity_id == entity_id)
    ).all()
    uncounted = db.exec(
        select(func.count(Knowledge.id))
        .join(Entity, Entity.id == Knowledge.entity_id)
        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(Entity.world_id == world_id, FactParticipant.id.is_(None))
    ).one()
    knowers = [
        {
            "section": "knowers",
            "knower_entity_id": knower.id,
            "knower_name": knower.name,
            "level": k.level,
            "content": k.content,
            "source": k.source,
            "is_incorrect": k.is_incorrect,
            "is_secret": k.is_secret,
            "subject_name": subject_name,
        }
        for k, knower in pairs
    ]
    knowers.sort(key=lambda r: (-knowledge_level_rank(r["level"]), r["knower_name"] or ""))
    coverage = {
        "section": "coverage",
        "subject_name": subject_name,
        "counted_rows": len(knowers),
        "uncounted_rows": uncounted,
    }
    return [coverage] + knowers
```

   Then `SELECTORS` becomes
   `SELECTORS: tuple[str, ...] = ("entity_dossier", "world_factions", "who_knows_about")`,
   and `_SELECTOR_LOOKUPS` gains, after `world_factions`:

```python
    "who_knows_about": SelectorSpec(
        fn=who_knows_about, arity=2, row_cap=200,
        arg_kinds=("entity_id", "world_id"), context_sections=("coverage",),
    ),
```

   Every filter is in a `.where(`; the sort after the fetch filters nothing.
   No `is_secret` filter (F1b), no `is_incorrect` filter (F2), no role
   predicate (J2).

5. **`src/world_engine/lore_plan.py`** — `_SELECTOR_DESCRIPTIONS` gains, after
   `world_factions`, verbatim (the accents are intended; the two existing
   entries are unaccented, R-25):

```python
    "who_knows_about": (
        "who_knows_about(entity_id, $world) -- qui, dans le monde, détient un "
        "savoir portant sur UNE entité nommée : un connaisseur par ligne, avec "
        "son niveau."
    ),
```

   Nothing else in `lore_plan.py` changes.

6. **`src/world_engine/lore_render.py` (C-05).**
   - Insert, immediately above `_SECTION_FORMATTERS`, verbatim:

```python
def _format_knowers(row: dict) -> str:
    line = f"{row.get('knower_name')} — {row.get('level')} : {row.get('content')}"
    if row.get("is_incorrect"):
        line += " (croyance fausse)"
    if row.get("is_secret"):
        line += " (secret)"
    return line


def _format_coverage(row: dict) -> str:
    return (
        f"{row.get('counted_rows')} ligne(s) comptée(s) sur « {row.get('subject_name')} » ; "
        f"{row.get('uncounted_rows')} ligne(s) de ce monde portent un sujet non résolu "
        "et ne sont pas comptées."
    )
```

   - `_SECTION_FORMATTERS` gains `"knowers": _format_knowers,` then
     `"coverage": _format_coverage,` after `"factions"`.
   - Replace the comment at lines 27-31 (from `# --- the section contract`
     through `...and the template fallback.`) with:

```python
# --- the section contract (BRIEF-0085-d item 2) --------------------------
# The vocabulary is the union of what the shipped selectors emit: identity,
# relations, knowledge, memberships, goals from entity_dossier; factions
# from world_factions (BRIEF-0085-d item 3); coverage, knowers from
# who_knows_about (BRIEF-0087-e). Sections are grouped in the order their
# first row appears in `rows`, for both the model prompt and the template
# fallback -- not in the order of the dict below.
```

   - In `_serialize_rows_by_section`'s docstring, "in the section-contract
     order" becomes "in order of first appearance".

   Commit items 3 to 6 together:
   `feat(lore): TICKET-0087 BRIEF-0087-e -- who_knows_about selector, coverage row first`.

7. **Do not touch `execute_plan`, and do not add a verdict.** The five
   verdicts are closed (R5); `coverage` is a `context_sections` row, first.

8. **Decision record.** Append to `tooling/standards/ARCHITECTURE_DECISIONS.md`,
   immediately before the final `---` line, separated from the previous entry
   by one blank line, keeping the file's existing line endings, verbatim:

```markdown
## WHO_KNOWS_ABOUT DECLARES ITS OWN COVERAGE, AND DECLARES IT FIRST (BRIEF-0087-e, no schema change)

**Decision (TICKET-0087, D1, M1).** The `who_knows_about` selector reports
how much of the world it can see as one `coverage` row in a
`context_sections` section, never as a verdict. The five verdicts are a
closed set asserted by `lore_selectors.py` R5, and a coverage number is not
a verdict: it accompanies both `answered` and `silent_canon`. The row is
emitted first, before any knower, because `execute_plan` truncates a
selector's rows from the tail at `row_cap`; a context row placed last would
be cut exactly when the answer is largest. `entity_dossier`'s `identity`
row already survives for the same reason.

**Rejected.** D2, returning knowers with no coverage statement -- rejected
on doctrine, not on cost: with most knowledge rows still carrying no
subject participant, an answer that does not say it is partial is a lie;
no reactivation condition. M2, exempting `context_sections` rows from
truncation inside `execute_plan` -- it changes the shared executor for a
case no world reaches today; *reactivate when* a selector must emit a
context row after its content rows. M3, leaving `coverage` last -- it makes
"exactly one, always" false above `row_cap - 1` knowers.

**R2 of the selector check reads the code, not a list (N1).**
`lore_selectors.py` R2 forbids naming a selector function in
`lore_query.py`. Its names were a hand-kept literal that a third selector
would silently escape -- measured: with the literal, a direct reference to
`who_knows_about` in `lore_query.py` passed. R2 now reads the `fn=` keyword
of every `SelectorSpec(...)`, vacuity-guarded. Rejected: N2, adding the name
to the literal; the corpus-wide sweep of literal sets stays TICKET-0085
queue item 7.

**Secrets in prose (P1).** Knower lines carry " (secret)" and
" (croyance fausse)" deterministically, in the template fallback and in
the trace. The `lore_rows_to_prose` prompt is not changed, so whether the
model's prose keeps the secret marker is observed, not guaranteed;
*reactivate* a prompt version when a live answer is seen to drop it.
```

   Then `python tooling/glue/gen_decisions_index.py`. Commit both:
   `docs(pipeline): TICKET-0087 BRIEF-0087-e -- close docs (decision record)`.
   No `CLAUDE.md` edit: `CLAUDE.md:441` already covers `lore_*.py`, and the
   "TICKET-0070 rule" does not exist (R-28).

9. **Verify.** `python -m tooling.verify.run --ticket TICKET-0087-knowledge-subject-participants`
   must print `"green": true` over the 12 checks of the repaired Machine
   section (R-22). Commit the verdict file:
   `chore(pipeline): TICKET-0087 verify green`.

10. **Open the PR — `/pipeline` Step 3's own commands (L1).** Set `status:
    live-gate` in TICKET-0087's front matter and nothing else; commit
    `chore(pipeline): TICKET-0087 status -> live-gate, opening PR`. Then
    `git push origin ticket/0087`, then
    `gh pr create --base main --head ticket/0087 --title "TICKET-0087: Knowledge subject as fact participants, and the who_knows_about selector"`
    with a body holding the ticket id, `BRIEF-0087-e`, and the verdict JSON
    in a fenced block. Report the PR URL. Never push to `main`; never merge.

## Scope OUT

- **`execute_plan`, and any exemption of context rows from truncation** (M2, rejected).
- **The `lore_rows_to_prose` and `lore_question_to_plan` prompts**, their seeds and their versions (P1). The planner's JSON example keeps naming `entity_dossier`.
- **`frontend/src/lore/`**, including `SECTION_LABEL`: the trace shows `knowers` and `coverage` under their raw keys (R-23). TICKET-0085's read-only lock stands.
- **`_group_rows_by_section`'s grouping rule.** Only the comment and one docstring phrase change.
- **The participant routes**: `D-0087-attach-duplicate` and `D-0087-attach-cross-world` are named deferrals, not repairs.
- **Any second selector** (`location_contents`, `faction_roster`, `region_locations`), one ticket each.
- **A viewpoint parameter.** The surface answers as the creator.
- **A write path.** `lore_selectors.py` and `lore_query.py` stay free of `db.add(`, `db.commit(` and `chat(` (`lore_isolation` R1).
- **Any other literal set in any other check** (TICKET-0085 queue item 7).
- **`entity_dossier`**, its `knowledge` section and its unmarked secrets.
- **The three dedup guards**, `knowledge.subject`, `NAMED_RUNGS`, `_MENTION_CATEGORIES`.
- **`CLAUDE.md`.**
- **S-4 and `reset_test.py`.** Never run `scripts/reset_test.py`; the probe uses its own temp file.
- **The production database.** Nothing in this brief reads or writes it.

## Invariants to defend

- **Exclusion is structural, never instructional.** This selector returns secrets by construction because this is the creator's surface and `entity_dossier` already does (R-11). It must not become reachable from any NPC or MJ context assembler; if a shared helper would let it, that is a STOP.
- **The MJ context assembler's perception boundary.** Untouched; nothing here edits an assembler.
- **World scoping at query construction** (`lore_isolation` R2). Every filter in a `.where(`.
- **The model never sees canon at planning time** (`lore_isolation` R5). `lore_plan.py` gains a description and nothing else.
- **Fail-closed over advisory.** The coverage row is unconditional and first, so no answer can silently look complete, and R2's derived set fails on zero names.
- **No structure without a reader.** This brief is `fact_participant`'s reader on the consultation surface.

## Decision rights

**STOP:**
- Any anchor above has moved, including the ancestry check of item 1.
- `git merge --ff-only origin/main` refuses, or `git status --porcelain` shows anything beyond the four deposited files.
- Any check named in Done means fails after the verbatim edits and the failure is not fixed by correcting a transcription error against this brief.
- The edits require touching `execute_plan`, a verdict, a prompt, or any file outside Scope IN.
- `corpus_gate.py`'s baseline is not 111 of 111 on the fast-forwarded branch, for a reason other than S-4.

**ADAPT:**
- `corpus_gate.py` or `day_mutations.py` reports `CRASH` naming `WORLD_ENGINE_ENV` (S-4): set `$env:WORLD_ENGINE_ENV = "test"`, re-run, report.
- `corpus_gate.py` discovers a count other than 111 because a check landed on `main` after `2ae232b`: record the new count as the baseline if every check passes, report.
- `git merge --ff-only` is not pre-allowed and asks for approval: that prompt is expected; proceed on Nia's approval.
- The ADR file uses CRLF in the working tree: write the entry with CRLF, report.

**REPORT-ONLY:**
- On Nia's production database, the numbers her live gate shows for Maelis on Verkhaal: `counted_rows`, `uncounted_rows`, and the « Sujets » tab's line count for Verkhaal, which should equal `uncounted_rows`.
- Whether the model's prose keeps the " (secret)" and « croyance fausse » markers on the `answered` path (P1).
- Any question phrasing during the live test that the planner fails to route to `who_knows_about`.
- Any other check file observed to carry a hand-maintained literal set of the same shape: the file and the constant; change nothing.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `git rev-parse HEAD` equalled `git rev-parse origin/main` before the deposit commit, and the deposit commit holds exactly the four files of item 1.
- [ ] The baseline `corpus_gate.py` line is recorded in the report, before any edit.
- [ ] `grep -n "SELECTOR_FUNCTION_NAMES" tooling/verify/checks/lore_selectors.py` prints nothing, and `python tooling/verify/checks/lore_selectors.py` prints its PASS line.
- [ ] Named mutation, R2: append a line `_probe = who_knows_about` to `src/world_engine/lore_query.py`, run `python tooling/verify/checks/lore_selectors.py`, observe `FAIL: lore_selectors R2: src/world_engine/lore_query.py names selector function(s) ['who_knows_about'] directly`, remove the line, observe PASS. Quote both outputs; commit neither state.
- [ ] Named mutation, vacuity: in `src/world_engine/lore_selectors.py`, temporarily replace each of the three `fn=` keywords with `fn_=`, run `python tooling/verify/checks/lore_selectors.py`, observe `FAIL: lore_selectors R2: src/world_engine/lore_selectors.py: zero `fn=` names read from SelectorSpec(...) constructions -- vacuous`, restore the file byte for byte (`git checkout -- src/world_engine/lore_selectors.py` if it is committed at that point), observe PASS. Quote both outputs; commit neither state.
- [ ] The probe below, saved **outside the repository** (e.g. `$env:TEMP\probe_0087e.py`) and run from the repository root with `$env:PYTHONPATH = "src"`, prints `PROBE PASS -- 0 failure(s)` and exits 0. It creates its own temp-file database and never touches another.
- [ ] `python -m tooling.verify.run --ticket TICKET-0087-knowledge-subject-participants` prints `"green": true` with 12 checks, each `PASS`: `fact_spine`, `subject_resolution`, `lore_selectors`, `lore_isolation`, `single_canon_write`, `import_cycle`, `undefined_names`, `module_budget`, `function_length`, `decisions_index`, `pipeline_state`, `corpus_gate`.
- [ ] `corpus_gate.py`'s line reads the baseline count discovered, executed and passed.
- [ ] The PR is open from `ticket/0087` onto `main`, and TICKET-0087 reads `status: live-gate`.
- [ ] `/review-step` and `/close-step` ran for commits A, the selector commit and the docs commit.

Probe, verbatim:

```python
"""BRIEF-0087-e done-means probe. Not committed. Fresh temp-file SQLite,
set before any world_engine import; never the real database."""
import os, sys, tempfile
os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/probe.db"
sys.path.insert(0, "src")
from world_engine.db import create_db_and_tables, engine
create_db_and_tables()
from sqlmodel import Session
from world_engine.models import Entity, World
from world_engine.writes import attach_participants, create_fact, write_knowledge
from world_engine.lore_query import LorePlan, PlanCall, PlanMention, execute_plan
from world_engine.lore_render import render_template
from world_engine.subject_resolve import unresolved_subjects

FAILS = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)

def ask(s, name, world_id):
    plan = LorePlan(mentions=(PlanMention("m1", name, "person"),),
                    calls=(PlanCall("who_knows_about", ("m1", "$world")),))
    return execute_plan(plan, world_id, s)

with Session(engine) as s:
    w, w2 = World(name="Probe", is_active=True), World(name="Elsewhere")
    s.add(w); s.add(w2); s.commit(); s.refresh(w); s.refresh(w2)
    def ent(name, world_id=None):
        e = Entity(world_id=world_id or w.id, type="character", name=name)
        s.add(e); s.commit(); s.refresh(e); return e.id
    maelis, vance, alone = ent("Maelis"), ent("Vance"), ent("Solitaire")
    bran, anya, cole, dara = (ent(n) for n in ("Bran", "Anya", "Cole", "Dara"))
    stranger = ent("Etranger", w2.id)
    k = write_knowledge(s, entity_id=bran, subject="Complot de Maelis", level="rumor",
                        content="c1", subject_entity_ids=[maelis]); s.commit()
    write_knowledge(s, entity_id=anya, subject="Complot de Maelis", level="knows", content="c2",
                    fact_id=k.fact_id, is_secret=True, is_incorrect=True); s.commit()
    f = create_fact(s, world_id=w.id, content="Maelis conspire avec Vance", created_by="probe"); s.commit()
    attach_participants(s, fact=f, entity_ids=[maelis, vance], role="conspirator"); s.commit()
    write_knowledge(s, entity_id=cole, subject="conspiration", level="knows", content="c3", fact_id=f.id); s.commit()
    write_knowledge(s, entity_id=dara, subject="rumeur libre", level="rumor", content="c4"); s.commit()
    write_knowledge(s, entity_id=dara, subject="autre rumeur", level="partial", content="c5"); s.commit()
    write_knowledge(s, entity_id=stranger, subject="ailleurs", level="rumor", content="c6"); s.commit()

    r = ask(s, "Maelis", w.id)
    secs = [row["section"] for row in r.rows]
    check(r.verdict == "answered", f"Maelis verdict is answered ({r.verdict})")
    check(secs == ["coverage", "knowers", "knowers", "knowers"], f"coverage first, then 3 knowers ({secs})")
    keys = {"section", "knower_entity_id", "knower_name", "level", "content", "source",
            "is_incorrect", "is_secret", "subject_name"}
    check(all(set(row) == keys for row in r.rows[1:]), "every knowers row carries exactly the nine C-04 keys")
    check(set(r.rows[0]) == {"section", "subject_name", "counted_rows", "uncounted_rows"},
          "the coverage row carries exactly the four C-04 keys")
    check([row["knower_name"] for row in r.rows[1:]] == ["Anya", "Cole", "Bran"],
          "rank descending, then name ascending (Anya, Cole at knows; Bran at rumor)")
    check(any(row["knower_name"] == "Cole" for row in r.rows[1:]),
          "a participant carrying role='conspirator' counts as a knower (J2)")
    residue = sum(x["row_count"] for x in unresolved_subjects(w.id, s))
    check(r.rows[0]["uncounted_rows"] == residue == 2,
          f"uncounted_rows equals the worklist's line count for this world ({r.rows[0]['uncounted_rows']} / {residue})")
    prose = render_template(r).prose
    check("Anya — knows : c2 (croyance fausse) (secret)" in prose, "both markers, false belief first")
    check(prose.startswith("3 ligne(s) comptée(s) sur « Maelis » ; 2 ligne(s) de ce monde"),
          "the coverage line renders first, verbatim")

    r2 = ask(s, "Solitaire", w.id)
    check(r2.verdict == "silent_canon", f"an entity with no knower is silent_canon ({r2.verdict})")
    check([row["section"] for row in r2.rows] == ["coverage"] and r2.rows[0]["counted_rows"] == 0,
          "and returns exactly one coverage row, counted_rows 0")

    f2 = create_fact(s, world_id=w.id, content="Vance est riche", created_by="probe"); s.commit()
    attach_participants(s, fact=f2, entity_ids=[vance]); s.commit()
    for i in range(205):
        write_knowledge(s, entity_id=ent(f"K{i:03d}"), subject="richesse", level="knows",
                        content="x", fact_id=f2.id)
    s.commit()
    r3 = ask(s, "Vance", w.id)
    secs3 = [row["section"] for row in r3.rows]
    check(r3.trace[-1]["truncated"] is True and len(r3.rows) == 200, "206 knowers: truncated at row_cap")
    check(secs3[0] == "coverage" and secs3.count("coverage") == 1 and secs3.count("knowers") == 199,
          "coverage survives truncation: 1 coverage + 199 knowers")
    check(r3.rows[0]["counted_rows"] == 206, f"counted_rows states the full count ({r3.rows[0]['counted_rows']})")

print("PROBE", "FAIL" if FAILS else "PASS", f"-- {len(FAILS)} failure(s)")
sys.exit(1 if FAILS else 0)
```

Live (Nia, on her machine, production database, after the PR is open):
"qui sait quoi sur Maelis" on Verkhaal answers with her knowers, each with a
level, and the folded trace shows the `coverage` row first; an entity with
no knower answers « Le canon ne détient rien sur ce point. » with the
`coverage` row in the trace; a secret knower's line carries « (secret) » in
the trace and in the template fallback. These are TICKET-0087's live
criteria, read under R-24 and P1.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: the entry of item 8, and `DECISIONS_INDEX.md` regenerated.
- `CLAUDE.md`: none (R-28).
- No schema changelog entry. No version bump.
