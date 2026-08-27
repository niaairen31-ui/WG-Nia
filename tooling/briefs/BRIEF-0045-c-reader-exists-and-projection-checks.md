# BRIEF — Step "trait_reader.py (C1) + projection check"

## Context

TICKET-0045, decision C1: "no structure without a reader" (E2) becomes a
fail-closed verify check, not a documentary note. This brief authors two G1
checks. `trait_reader.py` resolves every trait's declared reader (F1: callable
OR guard-column), tolerating only mutable_by_ai's named deferral.
`trait_registry_projection.py` binds the entity_trait projection (BRIEF-0045-a)
to the registry vocabulary (BRIEF-0045-b) so no orphan/absent trait key can
exist. Both follow the house idiom (FAILURES list, vacuous-proof: zero parsed
criteria is a FAIL, never a silent pass — run.py doctrine).

## Scope IN

1. **New file `tooling/verify/checks/trait_reader.py`.** AST + import idiom.
   Copy the header/report skeleton of tooling/verify/checks/import_cycle.py
   (FAILURES list, `fail`, `_report_and_exit`, `main`, ROOT via parents[3]).
   Behavior:

   a. Import the registry module (`from world_engine import traits`) — this
      check IS permitted to import application code because the registry is
      pure declarations with no side effects (unlike module_budget/import_cycle
      which stay AST-only). If the import itself raises, that is a FAIL naming
      the exception (a malformed TraitDef fails construction here — desired).

   b. `ASSERTIONS = 0`. For each TraitDef in `traits.TRAITS`, increment
      ASSERTIONS and resolve its reader by form:
      - **reader_callable** ("module:function"): import the module, getattr the
        function, assert it is callable. Failure to import, missing attr, or
        non-callable = FAIL naming the trait and the dotted path.
      - **reader_guard** (module_dotted, column_name): import the module, read
        its SOURCE (via `inspect.getsource` or reading the file), and assert
        `column_name` appears in a query-construction filter position. Concrete
        rule: the column name must appear textually adjacent to a comparison
        against False/a filter call — accept a match of the regex
        `<column_name>\s*==\s*False` OR `<column_name>\s*=\s*FALSE` (SQL) within
        the module source. Missing = FAIL naming the trait, module, and column.
        (This is the secretable asymmetry: we prove the exclusion column is
        referenced in a filter, not that a function reads it.)
      - **reader_deferred**: assert the trait key is EXACTLY "mutable_by_ai" and
        the deferred value is EXACTLY "TICKET-0047". Any OTHER trait carrying
        reader_deferred = FAIL naming the trait ("only mutable_by_ai may defer
        its reader"). This is the single named-exception branch.

   c. Mutual-exclusion re-assertion: for each trait, exactly one of the three
      reader fields is non-None (defense in depth against a future edit
      bypassing __post_init__). More/fewer than one = FAIL.

   d. **Vacuous-proof**: after the loop, if ASSERTIONS == 0, FAIL with "zero
      traits examined — parse broken, not repo clean". Also assert
      len(traits.TRAITS) >= 5 (the five canonical traits must all be present;
      a truncated registry is a FAIL, not a pass).

   e. `_report_and_exit`: print one `FAIL: ...` per failure and exit 1; else
      print `PASS: trait_reader — N traits, all readers resolve` and exit 0.

2. **New file `tooling/verify/checks/trait_registry_projection.py`.** DB-backed,
   self-contained fresh temp-file SQLite fixture — copy the fixture idiom of
   tooling/verify/checks/location_type_classified.py verbatim
   (WORLD_ENGINE_DATABASE_URL set to a temp file BEFORE any world_engine
   import, so the check never touches Nia's real DB). Behavior:

   a. Import `traits.trait_keys()` as the closed vocabulary V.

   b. Create the schema in the temp DB (metadata create_all), then assert two
      structural properties over the entity_trait table:
      - **No orphan projection key**: every DISTINCT `trait_key` present in
        entity_trait is a member of V. Any key not in V = FAIL naming the key.
        (On a fresh fixture the table is empty, so this volet is vacuously
        clean — see vacuous-proof below.)
      - **Vocabulary completeness of V itself**: |V| == 5 and V equals the
        canonical set {describable, spatial, knowable, secretable,
        mutable_by_ai}. A registry that dropped or renamed a key fails here
        even with an empty projection table.

   c. **Vacuous-proof**: the completeness volet (b.2) always examines 5 keys, so
      ASSERTIONS is never 0 even against an empty projection — this check
      cannot silently pass on a broken parse. State this in the docstring.

   d. Same FAILURES/report/exit idiom.

3. **Wire both checks into TICKET-0045's Machine-checkable section** via ASCII
   arrows: `-> verify/checks/trait_reader.py` and
   `-> verify/checks/trait_registry_projection.py` (already present in the
   ticket; confirm the arrows parse under run.py's LINK regex).

## Scope OUT

- **Signature checking of readers (C2)** — explicitly deferred at decision
  time. trait_reader.py proves existence/importability + guard-column presence,
  NOT that a callable has a given signature. Do not add parameter-shape
  assertions.
- **Call-graph proof** ("spawn_point is actually invoked by the spatial tick")
  — a stronger form discussed and NOT chosen. Do not build reachability
  analysis; resolution/importability is the C1 contract.
- **traits.py content** — BRIEF-0045-b owns it. This brief only READS it.
- **entity_trait DDL / model** — BRIEF-0045-a. The projection check creates the
  schema in a THROWAWAY temp DB only.
- **describable socle wiring** — BRIEF-0045-d.
- Any write to Nia's real DB. The projection check uses a temp fixture; if the
  fixture idiom cannot be copied cleanly from location_type_classified.py:
  REPORT ONLY, do not point at the real DATABASE_URL.

## Invariants to defend

- **Fail-closed over advisory.** Both checks exit non-zero on any unmet
  criterion; a warning is never emitted in place of a failure. Zero parsed
  criteria is a FAIL (vacuous-proof), enforced explicitly in each check.
- **No structure without a reader (E2), made structural.** trait_reader.py IS
  the mechanization of this doctrine. mutable_by_ai is the single tolerated gap
  and only under its exact name + exact ticket id.
- **Secrets excluded structurally.** The reader_guard branch proves the
  exclusion column lives in a filter position — it must not be satisfiable by a
  mere mention of "secret" in a docstring. Anchor the regex to a comparison
  operator, per Scope IN 1.b.
- **Checks never touch the real DB.** The DB-backed check uses a fresh temp
  fixture, same discipline as spatial_door_travel.py / location_type_classified.py.

## Done means

- [ ] `python tooling/verify/checks/trait_reader.py` exits 0 and prints
      "PASS: trait_reader — 5 traits, all readers resolve".
- [ ] Temporarily breaking spatial's reader_callable to a bogus path makes
      trait_reader.py exit 1 naming spatial and the bad path (revert after).
- [ ] Temporarily setting reader_deferred on `spatial` makes trait_reader.py
      exit 1 with "only mutable_by_ai may defer its reader" (revert after).
- [ ] Temporarily removing the `is_secret == False` filter form from a copy of
      the guard module makes the reader_guard volet FAIL (proves the guard is
      not vacuous). Real context.py untouched.
- [ ] `python tooling/verify/checks/trait_registry_projection.py` exits 0 on a
      fresh temp fixture; renaming a key in traits.py makes it exit 1.
- [ ] `python tooling/verify/run.py --ticket TICKET-0045` parses both arrows
      and includes both checks in the verdict JSON (green once -a/-b landed).
- [ ] /review-step and /close-step run.

## Docs to update

- **This step IS partly the doc update**: the two checks are self-documenting
  (module docstrings state the assertion + vacuous-proof clause, house idiom).
- **CLAUDE.md**: add trait_reader.py and trait_registry_projection.py to the
  verify-check inventory line if such an inventory is maintained there; keep the
  count fresh (was 55 checks at RECON; now 57).
- No schema doc change.
