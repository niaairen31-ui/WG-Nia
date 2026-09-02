# BRIEF — Step "Extract Relation and Knowledge into models/canon_knowledge.py"

## Mini-RECON (measured on tarball of `main`, schema v1.97)

- `src/world_engine/models/canon.py` is **987 physical lines** [M].
  `tooling/verify/checks/module_budget.py:58` sets `MAX_LINES = 1000` [M].
  Headroom: **13 lines**. TICKET-0082 adds three tables. It does not fit.
- Precedent exists and is documented in the package docstring
  (`models/__init__.py:9-11`): `canon_faction.py` holds "faction extension
  tables (Faction, FactionRole, FactionMembership), extracted from canon.py
  at TICKET-0048 for the module_budget cap" [M]. This step is the same move
  for the perception stratum.
- `Relation` occupies `canon.py:405-436`; `Knowledge` occupies
  `canon.py:439-473` including its section-header comment block [M].
- `models/__init__.py` "re-exports the ENTIRE former public surface of the
  flat `models.py` ... so every existing `from .models import X` /
  `from world_engine.models import X` in `src/` and `scripts/` resolves
  unchanged" (`models/__init__.py:29-33`) [M].
- `schema_reconcile.static_table_names()` (`src/world_engine/schema_reconcile.py:33`)
  derives the static table set from `SQLModel.metadata` after importing
  `models` — never a hardcoded literal [M]. Moving a class between modules
  inside the package therefore leaves the physical table set unchanged, which
  is what makes this move verifiable rather than merely plausible.

## Context

`canon.py` is 13 lines from its cap. Every later brief in TICKET-0082 adds
schema. Per the standing rule, approaching the cap triggers extraction, not
exemption — and pure-move commits precede logic commits so the module budget
stays honest. This step moves nothing but text.

## Scope IN

1. Create `src/world_engine/models/canon_knowledge.py` with the same header
   style as `canon_faction.py`: module docstring naming the stratum
   (perception: what an entity holds about the world, and the typed links
   between entities), and the same `from __future__ import annotations` /
   import block that `canon_faction.py` uses, reduced to what the moved
   classes actually need.
2. Move the class `Relation` (`canon.py:405-436`) into the new module,
   **byte-identical body** — same `__table_args__`, same CheckConstraint
   name `ck_relation_intensity`, same three indexes, same column order,
   same defaults and `server_default` text.
3. Move the class `Knowledge` together with its preceding section-header
   comment block (`canon.py:438-473`) into the new module, byte-identical.
   The comment `# knowledge  (what each entity knows)` moves with it.
4. Add the module docstring line to the layout list in
   `models/__init__.py:9-11`, in the same format as the `canon_faction.py`
   entry, naming TICKET-0082 and this brief as the reason.
5. Import and re-export `Relation` and `Knowledge` from
   `models/__init__.py` at the same position in the public surface they
   occupy today, so `from .models import Knowledge` and
   `from world_engine.models import Relation` resolve unchanged.
6. Place the new module in the import order documented at
   `models/__init__.py:33-35` immediately after `canon_faction`.
7. Register `canon_knowledge.py` wherever `canon_faction.py` is registered
   for stratum accounting — check `tooling/verify/canon_write_policy.txt`
   and `tooling/verify/checks/schema_partition.py`. If `relation` and
   `knowledge` are listed under a per-module grouping there, update the
   grouping. If the policy file lists table names only and is
   module-agnostic, change nothing and say so in the report.

## Scope OUT

- No new table. `fact`, `fact_participant`, `fact_default` are BRIEF-0082-b.
- No new column. `knowledge.fact_id` is BRIEF-0082-b.
- No change to any column, constraint, index, default or docstring of the
  two moved classes. Not a rename, not a reflow, not a comment improvement,
  not a type-hint modernisation. If something in those bodies looks wrong:
  **REPORT ONLY**.
- Do not move any other class out of `canon.py` "while we are here" — not
  `Door`, not `Event`/`EventEntity`, not `DiscoverableDetail`. The freed
  headroom is sized for this ticket; a larger extraction is its own ticket.
- Do not touch any call site. Every `from .models import ...` in `src/` and
  `scripts/` must keep working through the re-export, untouched.
- Do not renumber, reorder or reformat what remains in `canon.py` around the
  hole left by the move.

## Invariants to defend

- **Schema is authoritative.** This step changes no schema. `static_table_names()`
  must return the same set before and after; if it does not, the move was not pure.
- **History is sacred.** No migration, no data touched.
- **Module budget.** The point of the step. `canon.py` must land materially
  below the cap, not one line under it.
- **No structure without a reader** is not threatened here: no structure is
  added, only relocated.

## Done means

- [ ] `wc -l src/world_engine/models/canon.py` returns a value at or below 920.
- [ ] `src/world_engine/models/canon_knowledge.py` exists and contains exactly
      two `class ... (SQLModel, table=True)` definitions: `Relation` and
      `Knowledge`.
- [ ] `grep -n "class Relation\|class Knowledge" src/world_engine/models/canon.py`
      returns nothing.
- [ ] A diff of the two moved class bodies against their pre-move text is
      empty apart from the file they live in. Paste the diff in the report.
- [ ] `python -c "from world_engine.models import Relation, Knowledge; print(Relation, Knowledge)"`
      succeeds.
- [ ] The set returned by `world_engine.schema_reconcile.static_table_names()`
      is identical pre- and post-move. Capture both, diff them, paste the
      empty diff in the report.
- [ ] `python -m world_engine.schema_reconcile` reports no orphan and no
      missing table against an existing dev database.
- [ ] `tooling/verify/checks/module_budget.py` PASS.
- [ ] `tooling/verify/checks/import_cycle.py` PASS — the new module must not
      introduce a cycle.
- [ ] `tooling/verify/checks/undefined_names.py` PASS.
- [ ] Corpus gate green.
- [ ] `/review-step` and `/close-step` run.
- [ ] Live: the cockpit boots, and one existing NPC's knowledge list renders
      in Creation exactly as before.

## Docs to update

- `models/__init__.py` layout docstring (in Scope IN item 4 — that edit IS
  the doc update for this step).
- No schema changelog entry: the schema version does not move, because the
  schema does not change. If a check demands a version bump for a pure move,
  STOP and report rather than inventing one.

## STOP conditions

- If `canon.py` does not land at or below 920 lines after the move, stop and
  report the number rather than extracting more classes to reach it.
- If `static_table_names()` differs pre/post, stop immediately: the move was
  not pure and something was edited in transit.
- If `canon_write_policy.txt` or `schema_partition.py` turns out to encode
  module paths rather than table names, stop and report the exact lines
  before editing them — that file governs the canon-write chokepoint and is
  not a place to improvise.
