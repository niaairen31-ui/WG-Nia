# BRIEF — Step "v1.78 subculture shape correction" (BRIEF-0025-d)

## Context

migrate_v1_78 (BRIEF-0025-b) has never applied on the live DB: its fail-closed
validation pass rejects 37 of 42 locations with a non-NULL `subculture` blob,
because BRIEF-0025-b's RECON mischaracterized the real shape as "flat dict of
string/number values". A read-only census of the live DB (2026-07-13, all 52
locations, 11 distinct shapes) establishes the actual shape: a flat dict over
a fixed 4-key vocabulary — `hidden` (always str, always the secret slice) plus
`values` / `magic_phenomena` / `nexus_link`, each appearing as str, bool, or
list[str]. No nested dicts exist anywhere. The data is sound; the migration's
validation and coercion are what must change. Locked decisions: A1 (fix the
migration, zero data edits), B1 (purely representational coercion to text, no
editorial decisions inside the migration). Until this lands, the live gate for
TICKET-0025 is blocked (`location.coord_x` missing -> /api/locations 500).

## Scope IN

1. `scripts/migrate_v1_78_dedicated_json_columns.py` — widen the read-only
   validation for `location.subculture`: a non-NULL blob passes iff it is a
   flat dict whose every value is `str | bool | int | float | list[str]`.
   Anything else (nested dict, list containing a non-str item, any other
   type, non-dict top level) still aborts fail-closed, listing the offending
   location ids, nothing written. Update the docstring's validation section
   to state this rule.
2. Same file — coercion of each value into `location_subculture.value`
   (TEXT), purely representational (B1):
   - str -> unchanged
   - bool -> `"true"` / `"false"`
   - int / float -> `str(value)`
   - list[str] -> `", ".join(items)`; an empty list produces NO row
   No value is dropped or rewritten for semantic reasons: `false` migrates
   as `"false"`, `["none"]` migrates as `"none"`.
3. Same file — reword the validation-abort epilogue so it no longer says
   "Resolve in the live UI, then re-run" (the locations UI is unreachable
   before this very migration applies). Use: "Fix the listed rows directly
   in the database or correct this migration, then re-run."
4. Same file — update the module docstring's shape description (item c) to
   reflect the censused vocabulary and the B1 coercion table verbatim from
   item 2 above.

## Scope OUT

- NO edits to the 37 subculture blobs themselves (A2 rejected — the data is
  the source of truth, the validator was wrong).
- NO semantic cleanup during migration (B2 rejected): do not drop `false`,
  `["none"]`, or any other value; editorial cleanup happens later in the UI.
- NO schema change to `location_subculture` (B3 rejected): the unique index
  `(location_id, key COLLATE NOCASE)` stays; no per-list-item rows.
- NO change to the table-existence idempotency guards of v1.77/v1.78/v1.79.
  The guard-by-table-existence anti-pattern (create_all can pre-create the
  guard table and silently skip a migration) is real but is a separate
  corrective brief spanning all migrations + a CLAUDE.md convention — do not
  fix it here.
- NO re-run or modification of migrate_v1_77 / migrate_v1_79 (both already
  applied on the live DB).
- NO handling of duplicate locations or test worlds found during the census
  ('Le manoir du plus puissant' x2, 'La Salle des Archives' x2, 'csvsvsav',
  ...): Nia deletes the affected world herself; report only if encountered.
- NO changes to tooling/verify checks in this brief.

## Invariants to defend

- **Fail-closed migrations / history is sacred**: the widened validation
  must remain fail-closed for genuinely unexpected shapes; the single
  all-or-nothing transaction and the SQLite >= 3.35 guard are untouched;
  abort still writes nothing and lists ids.
- **Exclusion is structural**: the `hidden` key -> `is_hidden = 1` mapping is
  unchanged — the secret slice lands structurally separated from public keys,
  never cohabiting in one blob again.
- **Migrations make no editorial decisions** (B1, analog of "model proposes,
  code judges"): coercion is representational only; any judgment about
  content stays with the creator, post-migration, in the UI.

## Done means

Danger class `migration` — live deployment sequence is part of acceptance:

- [ ] `python scripts/backup.py` run before migrating
- [ ] `python scripts/migrate_v1_78_dedicated_json_columns.py` applies
      cleanly on the live DB (prints the applied message, no abort)
- [ ] `location` has `coord_x` / `coord_y`; `location.coordinates`,
      `location.subculture`, `world.fundamental_laws` columns are gone
- [ ] every location that had a non-NULL subculture blob has >= 1
      `location_subculture` row; rows with key `hidden` have `is_hidden = 1`,
      all others `is_hidden = 0`
- [ ] spot-check 'Le Dernier Verre' (`loc-dernier-verre`): 4 rows, keys
      `values` / `hidden` / `magic_phenomena` / `nexus_link`, only `hidden`
      flagged `is_hidden = 1`
- [ ] spot-check list coercion — 'Les Jardins de la Côte'
      (`afdca665-b5f8-42ad-b8ee-42e4883c8891`): `values` row value is
      exactly `wealth, status`
- [ ] spot-check bool coercion — 'Zone Industrielle de Nordlac'
      (`094894d1-d5be-419b-a86c-65c9df06b9f3`): `magic_phenomena` row value
      is exactly `true`
- [ ] `python scripts/seed_pilot.py` completes without error
- [ ] full verify suite passes (except the known orphan npc_dialogue head,
      repaired separately by `repair_orphan_prompt_heads.py` — out of scope
      here)
- [ ] live smoke: cockpit up, `GET /api/locations` returns 200, a location
      detail page opens and shows its subculture entries
- [ ] /review-step and /close-step run (engine-adjacent script touched)

## Docs to update

- `world-engine-schema-changelog.md`: amend/annotate the v1.78 entry — the
  subculture source shape is the censused 4-key vocabulary with
  str | bool | list[str] values, coerced to text representationally (B1);
  cite BRIEF-0025-d.
- `ARCHITECTURE_DECISIONS.md`: append an entry — "Migration coercion is
  representational, never editorial (B1, BRIEF-0025-d): migrations may
  change representation (bool -> text, list -> joined text) but never drop
  or rewrite values on semantic grounds; content judgment belongs to the
  creator post-migration." Also record that migration validators must be
  grounded in a census of live data, not assumed shapes.
- `CLAUDE.md`: no change in this brief (the guard anti-pattern convention
  belongs to its own corrective brief).
