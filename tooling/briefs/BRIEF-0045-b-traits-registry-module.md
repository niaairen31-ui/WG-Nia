# BRIEF — Step "traits.py registry module (code-source-of-truth)"

## Context

TICKET-0045, decision A1: the trait registry is code, not data. This brief
authors `src/world_engine/traits.py` — the single source of truth for what a
trait IS: its key, its column bundle, its FK spec, and an IMPORTABLE reference
to its reader. Decision E2: every trait carries a real reader; the sole
exception is `mutable_by_ai` (`reader_deferred: TICKET-0047`). Decision F1: the
registry admits TWO reader forms — a positive callable (`reader_callable`) and
a negative-guard column reference (`reader_guard`) — because `secretable`'s
"reader" is a WHERE-clause exclusion, not an accessor. This brief ships the
module and its declarations; the check that RESOLVES these readers is
BRIEF-0045-c.

## Scope IN

1. **New file `src/world_engine/traits.py`.** Module docstring states: trait
   registry, code-source-of-truth (A1), TICKET-0045 BRIEF-0045-b; each trait is
   a bundle (columns + FK + reader); "no structure without a reader" (E2) is
   enforced structurally by trait_reader.py (BRIEF-0045-c); the registry is
   edited only via Claude Code, never hot-editable at runtime.

2. **A frozen dataclass `TraitDef`** with these fields (exact):
   - `key: str` — the projection vocabulary key.
   - `label: str` — human label (French UI label acceptable, e.g. "Descriptible").
   - `checkable: bool` — False only for `describable` (the socle, always
     present, never a palette checkbox — BRIEF-0045-d wires this).
   - `columns: tuple[str, ...]` — the column names this trait's bundle adds to
     an entity_type's ext_ table (declarative record; the runtime DDL that
     emits them is 0044/0046, OUT here). Empty tuple allowed only for a pure
     marker (mutable_by_ai).
   - `fk: str | None` — a "column -> target_table.column" FK spec string, or
     None. ASCII arrow.
   - `reader_callable: str | None` — dotted import path "module:function" the
     check will resolve to a real callable. Mutually exclusive with
     reader_guard.
   - `reader_guard: tuple[str, str] | None` — (module_dotted_path, column_name):
     the check confirms `column_name` appears in a query-construction filter in
     that module. Mutually exclusive with reader_callable.
   - `reader_deferred: str | None` — a TICKET id string; non-None ONLY for
     mutable_by_ai. When set, both reader_callable and reader_guard are None
     and the check tolerates the trait by name.

   Enforce mutual exclusivity in `__post_init__`: exactly one of
   {reader_callable, reader_guard, reader_deferred} is non-None, else raise
   ValueError at import. (This makes a malformed trait fail at module load,
   before the check even runs — structural, not documentary.)

3. **The five trait declarations**, in a module-level `TRAITS: tuple[TraitDef, ...]`,
   anchored to the RECON'd real readers:

   - `describable` — checkable=False; columns=("name", "description");
     fk=None; reader_callable="world_engine.context:_npc_context_identity".
     (Socle; the identity block reads name/description.)
   - `spatial` — checkable=True; columns=("location_id",);
     fk="location_id -> location.id";
     reader_callable="world_engine.placement:spawn_point".
   - `knowable` — checkable=True; columns=() (participation flag; knowledge
     rows live in their own table, not on the ext_ row);
     fk=None;
     reader_callable="world_engine.context:_npc_context_speak".
   - `secretable` — checkable=True; columns=("is_secret",); fk=None;
     reader_guard=("world_engine.context", "is_secret"). (Negative WHERE-clause
     exclusion at query construction — context.py:167,194.)
   - `mutable_by_ai` — checkable=True; columns=(); fk=None;
     reader_deferred="TICKET-0047".

   VERBATIM NOTE to place as a comment directly above the mutable_by_ai
   declaration:
   ```
   # E2 exception, B2(ii): the ONLY trait permitted a deferred reader. Its
   # reader is the canon-write dispatch of TICKET-0047 (write_authorities /
   # ai_proposable, reserved at the socle, schema v1.87). trait_reader.py
   # tolerates this trait by name; no other trait may set reader_deferred.
   ```

4. **A public accessor `trait_keys() -> tuple[str, ...]`** returning the keys
   in declaration order — this is what scripts/seed_trait_keys.py (BRIEF-0045-a)
   imports to cross-check, and what the projection check imports as the closed
   vocabulary. Single accessor, single source (S-norme).

5. **A public accessor `checkable_traits() -> tuple[TraitDef, ...]`** returning
   only checkable=True traits — the constructor UI (0046) will consume this;
   declared now so the socle/palette split has one authority, but this brief
   ships no UI.

## Scope OUT

- **trait_reader.py and trait_registry_projection.py** — BRIEF-0045-c. This
  brief declares readers as strings; it does NOT author the code that resolves
  them.
- **Emitting the bundle columns as real DDL** — the `columns`/`fk` fields are a
  declarative record consumed by 0044's runtime-DDL writer and the 0046 UI.
  This brief must not call the schema writer or ALTER any ext_ table.
- **describable auto-presence on entity_types** — BRIEF-0045-d. This brief only
  marks it checkable=False.
- **Creating new readers.** Every reader_callable/reader_guard points at code
  that ALREADY EXISTS (RECON-anchored). If any target is found missing at
  authoring time: REPORT ONLY, do not create a stub reader — surface it to Nia.
- **Canon-write, write_authorities population** — TICKET-0047.
- **Derived traits** — deferral D-derived. Do not add a `condition` field to
  TraitDef, however tempting the "portable if size" note.

## Invariants to defend

- **No structure without a reader (E2).** The `__post_init__` mutual-exclusion
  rule is the first line of defense: a trait cannot even be constructed without
  declaring exactly one reader form. mutable_by_ai's reader_deferred is the
  single sanctioned gap, carrying its own verbatim justification.
- **S-norme.** trait_keys() is the ONE vocabulary source. The seed script's
  literal (BRIEF-0045-a) becomes a mere bootstrap the instant this module
  exists and must equal trait_keys().
- **Secrets excluded structurally, never instructionally.** secretable declares
  a reader_guard on the `is_secret` column in context.py — pointing at the
  query-construction filter, NOT at a prose instruction. Do not phrase
  secretable's reader as "the model is told to hide secrets".
- **Structural over disciplinary.** A trait's contract is a dataclass that
  fails construction when malformed — not a docstring convention.

## Done means

- [ ] `python -c "from world_engine import traits; print(traits.trait_keys())"`
      prints exactly ('describable','spatial','knowable','secretable','mutable_by_ai').
- [ ] `python -c "from world_engine.traits import TraitDef; TraitDef(key='x',
      label='x', checkable=True, columns=(), fk=None, reader_callable=None,
      reader_guard=None, reader_deferred=None)"` raises ValueError (zero readers
      rejected at construction).
- [ ] Constructing a TraitDef with two reader forms set raises ValueError.
- [ ] `checkable_traits()` returns four traits; describable is excluded.
- [ ] Every reader_callable dotted path imports to a real callable when
      resolved by hand; secretable's reader_guard module imports and contains
      the `is_secret` filter (spot-checked live; the automated proof is -c).
- [ ] `python scripts/seed_trait_keys.py` (from -a) now imports traits.py and
      asserts key-list equality, passing.
- [ ] /review-step and /close-step run.

## Docs to update

- **CLAUDE.md**: add a standing-convention line under the appropriate section:
  the trait registry is code-source-of-truth (src/world_engine/traits.py);
  traits are added via Claude Code, never hot-edited; every trait declares
  exactly one reader form (callable | guard | deferred); mutable_by_ai is the
  sole reader_deferred exception (TICKET-0047). Keep pointer-fresh.
- **ARCHITECTURE_DECISIONS.md**: append a decision entry — A1 (registry code-
  source-of-truth), E2 (every trait a reader), F1 (two reader forms: callable /
  guard, justified by secretable's negative-clause asymmetry), B2(ii)
  (mutable_by_ai sole deferral), and D-derived as a logged deferral with its
  trigger condition ("when a value-conditioned trait like rideable-if-size is
  first genuinely needed").
- No schema doc change (this brief is code-only, no DDL).
