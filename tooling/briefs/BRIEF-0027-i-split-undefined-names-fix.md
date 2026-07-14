<!-- slug: split-undefined-names-fix -->
# BRIEF-0027-i — Fix undefined names from the -d split; add `undefined_names.py` check

Ticket: TICKET-0027 | Danger: none (imports + one new check; no logic
change) | Blast radius: small fix, large restored surface | CORRECTIVE
for BRIEF-0027-d | Own branch `ticket/0027-i`

## Context

BRIEF-0027-d's split left 80 undefined-name sites (pyflakes F821, `main`
@ 169dbc3): shared private helpers stayed in one domain module while
their callers moved to siblings without imports. Python resolves names at
call time, so imports succeed, the route table is set-identical (109
routes, verified), no dynamic-route shadowing exists (verified) — and
every handler touching a missing name 500s at request time. This is why
the live gate broke on both play and creation. No verify check covers
this class; the sorted route-table proof cannot see it by design.

Findings (representative, full list = pyflakes output at execution):
- `crud/*`: `_iso`, `_world_id` (live in `crud/entities.py:88,258`),
  `_get_entity`, `_list_relations` / `_list_knowledge`
  (`crud/relations.py:121`, sibling), `RELATION_FIELDS` /
  `KNOWLEDGE_FIELDS` / `EVENT_FIELDS` — used across `agendas`, `events`,
  `factions`, `goals`, `skills`, `knowledge`, `locations`, `prompts`,
  `relations`, `entities`.
- `routes/play.py`: `_log` (206, 356) never defined there;
  `_load_mj_interpret_template`, `_interpret_mode` (487, 500) live in
  `play_physical.py:744,764`, not imported.

## Scope IN

1. **Re-home the genuinely shared crud helpers** into
   `src/world_engine/cockpit/crud/_shared.py`: `_iso`, `_world_id`,
   `_get_entity`, `_list_relations`, `_list_knowledge`, and the
   `*_FIELDS` constants (exact closed set = execution inventory). This is
   not a catch-all (R6): it is package-private, a closed enumerated set
   of cross-domain accessors, with a header stating additions require a
   brief. Every crud domain module imports what it uses from `._shared`;
   `entities.py`/`relations.py` stop hosting them.
2. **`routes/play.py`**: add `_log = logging.getLogger(__name__)` at
   module top; import `_load_mj_interpret_template` and `_interpret_mode`
   from `..play_physical`. Audit the remaining routes/ and cockpit
   modules for the same pattern (pyflakes drives; fix every F821).
3. **New check `tooling/verify/checks/undefined_names.py`** (promotion:
   this class just shipped through every gate): run pyflakes
   programmatically over `src/`, fail on any undefined-name report.
   Fail-closed: zero files scanned or pyflakes unavailable = FAILURE.
   Add `pyflakes` to dev requirements. Register R8 (enforced) in
   `code_standards.md` section 2 with this failure mode as rationale
   (verbatim text in execution notes, Nia signs at review).
4. **Mandatory harness re-runs**: `harness_say_replay.py` AND
   `harness_mutation_apply.py` replay on the fixed branch, results in the
   execution log. If the say fixtures do not traverse
   `_interpret_mode`/`play.py:206,356`, record ONE additional reference
   turn that does (record on pre--d commit `5b5f237`, replay on the fixed
   branch) so the gap that let -d through is closed in the fixtures too.
5. Update `ARCHITECTURE_DECISIONS.md` with the R8 promotion record +
   regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- Any logic, signature, or route change; any further decomposition.
- Retrofitting a route-order/shadowing check (none exists today as a
  hazard — noted as a promotion candidate only).

## Invariants to defend

- Pure re-homing: helper bodies byte-identical, only their module and the
  import lines change.
- R6 holds: `_shared.py` stays a closed set (header rule), not a util
  drawer.
- Full suite green including the new `undefined_names.py`; baselines
  untouched or smaller.

## Done means

### Machine-checkable
- [ ] `python -m pyflakes src/` reports zero undefined names;
      `undefined_names.py` green and proven fail-closed (temporary F821
      injection goes red; removed; logged).
- [ ] Both harness replays PASS on the fixed branch; the play fixtures
      demonstrably cover `_interpret_mode` (coverage note in log).
- [ ] Route-table set + shadowing audit unchanged (109 routes, zero
      shadow pairs).
- [ ] Full suite green; `decisions_index.py` green after the R8 record.

### Live gate (Nia)
- [ ] Play: one `/say` round-trip streams and persists.
- [ ] Creation: create one character and one location through the
      cockpit; edit one relation; all succeed.

## Docs to update

- `code_standards.md` (R8, Scope IN 3), `ARCHITECTURE_DECISIONS.md` +
  `DECISIONS_INDEX.md` (Scope IN 5), dev requirements (pyflakes).
