# BRIEF -- Step "Extract door-payload validation" (TICKET-0038, BRIEF-0038-a)

## Context

`write_location_doors` in `src/world_engine/writes/config.py` is 99 physical
lines -- over the 80-line R1 ceiling enforced by `function_length.py`. It landed
that way via BRIEF-0034-a (2026-07-20), after the transition baseline was retired
at TICKET-0028, so it was never baselined and the check now fails on it. The
failure surfaced in TICKET-0037's verify run (7/8) only because that check scans
all of `src/`; 0037 does not touch this file. TICKET-0034 is closed, so the fix
gets its own remediation ticket, on the TICKET-0035 precedent (a dedicated ticket
clears an over-budget unit by splitting it, never by re-baselining).

**This is a pure intra-module extraction. No behavior changes. No canon-write
site moves. No schema, no migration. No new module, no import edge.** The single
measure of success is that the same validation runs from a private helper the
writer calls, and both functions land under 80 lines.

The shape (verified at RECON on `main`, 2026-07-20 push):
- `write_location_doors` (`writes/config.py`, currently `:207-305`) is: signature
  (`db`, keyword-only `world_id`, `location_id`, `doors: list[dict]`,
  `changed_by`) -> `-> list[Door]`; a ~22-line docstring including the verbatim
  NO-GEOMETRY block; a per-item validation loop building
  `clean: list[tuple[str, float, float]]`; a `DELETE FROM door WHERE
  location_id = :location_id`; an insert loop building `Door` rows; `return
  new_doors`.
- The whole length sits in the validation loop plus the docstring. Extracting the
  loop leaves the writer at roughly signature + docstring + one call + delete +
  insert + return (~40 lines), comfortably under 80. The extracted loop
  (init + loop + return) is ~60 lines, also under 80.
- Every name the loop touches -- `math.isfinite`, `select`, `Session`, `Entity`,
  `Relation` -- is already imported at `writes/config.py:1-48`. Because the
  helper lives in the same module, NO import line changes.

## Scope IN

1. **New private helper -- same file, `src/world_engine/writes/config.py`.** Add
   `_validate_doors_payload`, defined IMMEDIATELY ABOVE `write_location_doors`
   (top-down: validate before write). Exact signature:

   ```python
   def _validate_doors_payload(
       db: Session,
       *,
       world_id: str,
       location_id: str,
       doors: list[dict],
   ) -> list[tuple[str, float, float]]:
   ```

   Move the current per-item validation loop of `write_location_doors` into this
   helper VERBATIM -- the `clean` / `seen_targets` initialisation, the
   `for item in doors:` loop with every check in it (non-empty target, no
   self-target, no duplicate target within the payload, finite coords, target is
   an active `location` of this `world_id`, and the B1 `connects_to` double-
   `select` gate reading both column orders), and `clean.append(...)`. End the
   helper with `return clean`. Not a statement is reordered, not an error message
   is reworded, not a comment is dropped. Helper docstring, verbatim:

   ```
   """All-or-nothing validation for a `write_location_doors` payload. Returns
   the cleaned `(target_location_id, x, y)` tuples, or raises `ValueError` on
   the first offending item -- non-empty target, no self-target, no duplicate
   target within one payload, finite coordinates, the target is an active
   location of the same world, and (B1) an active `connects_to` relation
   touches both endpoints. READ ONLY: performs no write. Extracted verbatim
   from `write_location_doors` at TICKET-0038 to hold R1 (80-line ceiling);
   the delete-then-insert stays in the writer.
   """
   ```

2. **`write_location_doors` after removal.** Keep the signature UNCHANGED
   (including `changed_by`, even though unused -- pre-existing, out of scope).
   Keep the full docstring UNCHANGED, including the verbatim NO-GEOMETRY block.
   Replace the removed init + validation loop with a single call:

   ```python
       clean = _validate_doors_payload(
           db, world_id=world_id, location_id=location_id, doors=doors
       )
   ```

   Leave the `DELETE FROM door ...` `db.execute(...)`, the insert loop building
   `Door` rows, and `return new_doors` exactly as they are. `clean` still feeds
   the insert loop with the same `(target_location_id, x, y)` tuples.

3. **Imports -- NO CHANGE.** The helper is intra-module and references only names
   already imported (`math`, `select`, `Session`, `Entity`, `Relation`). Do not
   add, remove, or reorder any import. `pyflakes` (R8 / F821) is the arbiter and
   will name any undefined or newly-unused import.

4. **Canon-write policy -- `tooling/verify/canon_write_policy.txt`. NO CHANGE.**
   `write_location_doors` remains the sanctioned writer (the `DELETE` +
   insert stay in it); `_validate_doors_payload` reads only and is not a write
   site. If execution produces any diff on `canon_write_policy.txt`, something
   moved that should not have -- STOP and REPORT.

5. **Confirm live line numbers before extracting.** The `:207-305` span is from
   the RECON push and will drift. Locate `write_location_doors` and its loop
   afresh in the working tree before moving anything; the selection criterion is
   definitional, not positional: the extracted block is the per-item validation
   loop and its `clean`/`seen_targets` setup, up to and including
   `clean.append(...)` -- nothing after (the `DELETE`, the insert loop, `return`
   stay in the writer).

6. **Docs** (see Docs to update).

## Scope OUT

- **Any behavior change.** No function body logic is edited -- not a reorder, not
  a reworded `ValueError`, not a "while I'm here" tidy. `git diff` must read as:
  the loop deleted from `write_location_doors`, appearing unchanged inside
  `_validate_doors_payload`, plus the one call line and the two new signatures/
  docstring. Anything else: REPORT.
- **Touching `write_location_doors`' docstring or the NO-GEOMETRY block** -- it
  stays on the writer, verbatim. Option B2 (moving the rationale out) was
  considered and rejected at intake; do not resurrect it.
- **Removing or "using" the unused `changed_by` parameter** -- pre-existing
  condition, not this ticket's business. REPORT if you think it should be
  addressed; do not touch it here.
- **Factoring the B1 `connects_to` double-`select` into a shared reader** -- the
  function's own comment records it as deliberately the fourth `connects_to`
  reader (decision D1 of BRIEF-19 stands). No deduplication. It moves into the
  helper as-is.
- **Adding a write-time geometry check** -- forbidden by the function's own
  NO-GEOMETRY note; the read-time fallback in `spatial_doors.py::resolve_spawn`
  is the enforcement point. Named because the executor is working inside this
  exact function.
- **Extracting or editing the other four `write_*` functions** in this module
  (`write_npc_prices`, `write_location_subculture`, `write_world_laws`,
  `write_location_obstacles`) -- untouched.
- **Splitting `config.py` into more files** -- it is nowhere near the module cap.
- **Re-adding a `function_length.json` (or any) baseline** -- the extraction is
  the mechanism; an exemption is the anti-pattern.

## Invariants to defend

- **Extraction is not broadening.** The count of sanctioned canon-write sites is
  unchanged: `write_location_doors` stays the sole writer, the delete-then-insert
  stays in it, and `_validate_doors_payload` performs no write.
  `single_canon_write.py` must be green with a ZERO-line diff on
  `canon_write_policy.txt`.
- **`function_length` is the point of this ticket.** Both functions must land
  <= 80 physical lines by construction. If the extracted helper alone lands over
  80 (unexpected), that is a finding to REPORT, not to baseline around and not to
  silently split again.
- **The B1 `connects_to` gate semantics are unchanged** -- both column orders are
  read exactly as before (mirroring `play.py`'s `_location_neighbours`), and a
  target with no active edge is still rejected before any write.
- **`pyflakes` F821 (R8) clean** -- no undefined name, no unused import, after
  the move. (No import block change is expected; if the check names one,
  something was mis-copied -- REPORT.)
- **`module_budget` holds** -- `config.py` gains one def; it must stay under
  1000 lines / 40 defs (it is far under).

## Done means

- [ ] `function_length.py` green on `src/world_engine/writes/config.py`;
      `write_location_doors` and `_validate_doors_payload` each <= 80 lines.
- [ ] Full verify suite green with NO baseline file added and NO entry added to
      any baseline.
- [ ] `single_canon_write.py` green with a ZERO-line diff on
      `tooling/verify/canon_write_policy.txt`.
- [ ] `module_budget.py` green on `writes/config.py`.
- [ ] `undefined_names.py` (R8 / pyflakes) clean on `writes/config.py`.
- [ ] `git diff` inspection: validation loop moved verbatim into the helper;
      `write_location_doors` calls it; no validation logic, no `DELETE`, no
      insert, and no docstring changed; the public signature is unchanged.
- [ ] `python -c "from world_engine.writes import config"` imports clean.
- [ ] Live check (danger class none; no migration): authoring a door to a
      valid actively-`connects_to` target inserts the `door` row; a target with
      no active `connects_to` edge is rejected with the same `ValueError`
      message; a duplicate target within one payload is still rejected.
- [ ] `ticket/0037` rebased onto `main` reports verify 8/8 (the
      `write_location_doors` failure gone).
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` / changelog: **no schema change** -- no entry, no
  version bump. Say so explicitly in the close note.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append a short TICKET-0038
  block -- `write_location_doors`' per-item validation extracted to the private
  read-only `_validate_doors_payload` to hold R1 (80-line ceiling);
  extraction-not-broadening (canon-write site count unchanged); sibling to
  TICKET-0035's module-budget remediation, and like it a dedicated ticket rather
  than a baseline re-add; plus the process finding that the function landed at 99
  via BRIEF-0034-a without `function_length` blocking the 0034 merge -- record
  the gate-gap question for follow-up.
- `CLAUDE.md`: no module-map change (the helper is a private, intra-module
  addition). No new standing rule expected; REPORT if execution reveals one.
- No change to `canon_write_policy.txt` (Scope IN 4).

---

**Drafting decisions made (flag for reversal before sending):**

1. **`type: bug`, not `feature`.** Divergence from TICKET-0035's `feature`
   typing: 0035 pre-empted a violation before it landed (headroom for an
   in-flight brief), whereas here the violation is already on `main`, which reads
   as a conformance bug. Flip to `feature` if you want parity with 0035.
2. **Helper name `_validate_doors_payload`** -- verb-first, matching the file's
   own `write_location_doors` / `write_world_laws` naming rather than a strict
   R7 domain-first form (e.g. `_location_doors_validate_payload`, which reads
   heavier). Rename at will; the brief references the name in three places.
3. **Helper placed immediately ABOVE `write_location_doors`** (validate-then-
   write reading order). Below works identically at runtime if you prefer the
   public function first.
4. **Helper docstring wording is mine** (the verbatim block in Scope IN 1). Trim
   or reword before sending if it says more than you want frozen.
