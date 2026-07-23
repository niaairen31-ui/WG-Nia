# BRIEF -- Step "Extract faction domain to canon_faction.py"

## Context

BRIEF-0044-b's canon.py placement of `EntityType`/`EntityTypeHistory` would
push `canon.py` from 985 -> 1064 lines, tripping `module_budget.py`'s
1000-line cap (PASS -> FAIL). Per doctrine C2 (refactor over exemption) and
the check's own docstring (its baseline is a retired TICKET-0028 transition,
not for new growth), the resolution is a split, not a baseline. This brief is
that split: a move-only extraction of the faction domain into a new
canon-stratum sub-module, landing on `main` before 0044-b resumes. RECON
(live `main`, canon.py at 985) confirmed all external imports resolve through
the `models/` package (zero direct `models.canon` imports), so the move's
external blast radius is nil.

## Scope IN

1. **Create `src/world_engine/models/canon_faction.py`.** Module docstring
   mirroring `canon.py`'s conventions, stating it is a canon-stratum
   sub-module extracted from `canon.py` (TICKET-0048, this brief) to keep
   each file under the module_budget cap; same schema-fidelity conventions as
   `canon.py` (point the reader to that module's docstring). Imports must be
   EXACTLY the set the three moved classes reference -- no more (pyflakes /
   R8 must stay clean, no unused imports):
   ```
   from __future__ import annotations

   from datetime import datetime
   from typing import Optional

   from sqlalchemy import Index, text
   from sqlmodel import Field, SQLModel

   from .canon import _created_ts, _uuid
   ```
   (B1: `_uuid`/`_created_ts` are imported from `.canon`, where they remain
   defined at `canon.py:47-60`. Do NOT redefine them here.)

2. **Move the faction domain block verbatim** from `canon.py` into
   `canon_faction.py`, section-header comments included, bodies byte-for-byte
   unchanged (this is the move-only correctness signal):
   - `Faction` section -- `canon.py:395-430` (header 395-397, class 398-430).
   - `FactionRole` section -- `canon.py:443-472` (multi-line header + class).
   - `FactionMembership` section -- `canon.py:475-515` (multi-line header +
     class), i.e. the contiguous span through the line immediately before the
     `relation` section header at `canon.py:516`.
   Copy the three blocks in their existing order. Do NOT edit any field,
   default, `__tablename__`, `__table_args__`, index, DORMANT comment, or FK.

3. **Remove those same blocks from `canon.py`.** After removal, the `relation`
   section (`canon.py:516+` pre-edit) follows the `location`/geometry region
   directly, with the file's normal one-blank-line-then-`# ---` section
   spacing preserved. `canon.py` drops from 985 to approximately 864 physical
   lines. `_uuid`, `_created_ts`, `BASE_SKILL_DOMAINS`, and every non-faction
   class stay in `canon.py` untouched.

4. **Update `src/world_engine/models/__init__.py`:**
   - Remove `Faction`, `FactionMembership`, `FactionRole` from the
     `from .canon import (...)` block.
   - Add a new import block, placed AFTER the `.canon` block and BEFORE the
     `.ephemeral` block (so table registration order stays canon ->
     canon_faction -> ephemeral -> pipeline; cross-stratum string FKs resolve
     regardless of order, but keep the deterministic sequence):
     ```
     from .canon_faction import (
         Faction,
         FactionMembership,
         FactionRole,
     )
     ```
   - `__all__` stays byte-for-byte unchanged (same names, same order).
   - Extend the module docstring's stratum layout list with a
     `canon_faction.py` line (one line: the faction extension tables,
     extracted from `canon.py` at TICKET-0048 for the module budget). Do NOT
     rewrite the existing docstring history.

5. **Update `CLAUDE.md` File structure** to add a pointer for
   `models/canon_faction.py` (faction extension tables, canon stratum). Fresh
   pointer only -- no archaeology in the File structure section, and the file
   must stay under its 500-line contract ceiling (`claude_md_contract.py`).

6. **Append an `ARCHITECTURE_DECISIONS.md` entry** for TICKET-0048: the first
   sub-split of `canon.py` by domain (one fractal level below the TICKET-0028
   canon/ephemeral/pipeline stratum split), triggered by the module_budget
   tripwire on canon.py; decisions A1 (faction -> canon_faction.py), B1
   (shared helpers imported from `.canon`, `_base.py` deferred), C1
   (EntityType stays in slimmed canon.py; no registry stratum), D (module
   name). Record the B1 deferral trigger explicitly: extract a
   `models/_base.py` only when a SECOND domain extraction needs
   `_uuid`/`_created_ts`. Then regenerate `DECISIONS_INDEX.md` mechanically.

## Scope OUT

- **Do NOT add `EntityType`/`EntityTypeHistory` anywhere.** That is
  BRIEF-0044-b, which resumes AFTER this ticket merges and places both
  classes into the slimmed `canon.py` (decision C1), with the cap green.
- **Do NOT create `models/_base.py`** for the shared helpers (B2 deferred;
  trigger recorded in ARCHITECTURE_DECISIONS.md). `_uuid`/`_created_ts` stay
  in `canon.py`; `canon_faction.py` imports them.
- **Do NOT create a registry/catalog stratum** or move `LocationTypeCatalog`,
  `WorldLaw`, `NpcPrice`, `LocationSubculture`, `Ledger`, or any other table
  (C2 deferred). Exactly one domain moves in this brief.
- **Do NOT extract any other domain** (agenda, spatial geometry, goals,
  skills, items). Further sub-splits happen when the cap next trips -- the
  tripwire is the mechanism, not a prompt to pre-split speculatively.
- **Do NOT add a `module_budget.json` baseline entry** for `canon.py` (or any
  module). The baseline is retired; this ticket is the sanctioned resolution.
- **Do NOT edit any class body, field, default, `__tablename__`, index, FK,
  CHECK, or DORMANT comment.** Move-only. Any refactor/"cleanup" temptation on
  the moved code = REPORT ONLY, separate proposal, not this commit.
- **Do NOT touch `canon_write_policy.txt`** (`[CANON_TABLES]` or
  `[ALLOWED_SITES]`): faction table names and the `writes/factions.py` sites
  are unchanged; the policy keys on table names, not module paths.
- **Do NOT modify any of the 93 external import sites**, and do NOT rename
  `Faction`/`FactionRole`/`FactionMembership` or change their exported names.
- **Do NOT edit any test file.** Zero test-file edits is the correctness
  signal for a move-only change.

## Invariants to defend

- **module_budget is a tripwire, not a nuisance.** This step resolves the
  trip by splitting; it must NOT route around it via a baseline. Post-step
  `canon.py` <= 1000 lines is the whole point.
- **Single canon-write authority (S-norme, `single_canon_write.py`).** The
  AST gate walks `MODELS_DIR`, so faction tables must remain attributable to
  their `__tablename__` from `canon_faction.py`. A move-only change adds no
  write site. Guard: no `.add()`/`.delete()`/raw-SQL introduced.
- **No structure without a reader.** `canon_faction.py`'s reader is the
  package `__init__` re-export feeding the existing 93 sites; nothing new is
  introduced without a consumer.
- **No duplication (S-norme, C2).** Each faction class exists in EXACTLY one
  file after the move. Guard against leaving a stub or a second definition in
  `canon.py`.
- **History is sacred:** untouched -- no data, no writes, no schema change.
  State this explicitly; do not add or drop any `change_history`.
- **CLAUDE.md freshness (`claude_md_contract.py`)** and pointer discipline:
  File structure updated, no archaeology, under 500 lines.

## Done means

- [ ] `src/world_engine/models/canon_faction.py` exists and defines exactly
  `Faction`, `FactionRole`, `FactionMembership` with their section headers;
  class bodies are byte-identical to the pre-move `canon.py` definitions.
- [ ] `canon.py` no longer defines those three classes; `wc -l
  src/world_engine/models/canon.py` reports <= 870 (was 985).
- [ ] `models/__init__.py`: the three names import from `.canon_faction`;
  `git diff` on `__all__` is empty; docstring stratum list gained one
  `canon_faction.py` line.
- [ ] `python -c "from world_engine.models import Faction, FactionRole,
  FactionMembership; print('ok')"` prints `ok`.
- [ ] existing test suite passes with ZERO test-file edits.
- [ ] `python tooling/verify/run.py` -> entire suite green; specifically
  `module_budget` PASS, `single_canon_write` PASS, `claude_md_contract` PASS.
- [ ] virgin-DB `init_db.py` on an empty database creates every table with no
  error; `world-engine-schema.md` needs no edit (no schema change).
- [ ] `/review-step` and `/close-step` run clean (engine code touched).
- [ ] `ARCHITECTURE_DECISIONS.md` has the TICKET-0048 entry;
  `DECISIONS_INDEX.md` regenerated; one commit for the whole step.

## Docs to update

- **`CLAUDE.md`** File structure: add the `models/canon_faction.py` pointer
  (Scope IN 5).
- **`ARCHITECTURE_DECISIONS.md`**: append the TICKET-0048 entry; regenerate
  **`DECISIONS_INDEX.md`** (Scope IN 6).
- **`models/__init__.py`** docstring stratum layout: one added line (Scope
  IN 4).
- **No schema changelog entry and no `schema_version.py` bump** -- this step
  changes zero schema. State the non-change; do not invent a version bump.
