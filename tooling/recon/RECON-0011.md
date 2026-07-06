# RECON-0011 — prompt text read/write map for TICKET-0011 (editing + version history)

Read-only report against `main` (tarball snapshot, 2026-07-04). No actions
taken. Current schema version: **v1.67** (world-engine-schema.md:3).

---

## 1. Current `prompt_template` shape (src/world_engine/models.py:780-804)

Columns: `id`, `world_id`, `name`, `usage`, `system_prompt`, `user_template`,
`variables JSON`, `destination`, `model` (v1.67, NULL = code decides),
`version INTEGER DEFAULT 1`, `is_active`, `notes`, `updated_at`.

**Finding — `version` is decorative.** No code path increments it; every row
sits at 1. Under A2 it is superseded by `prompt_version.version_number` and
falls under the F1 drop (`system_prompt`, `user_template`, `version`).

SQLite note for Claude Code: `ALTER TABLE ... DROP COLUMN` requires
SQLite ≥ 3.35; otherwise table-rebuild migration (existing precedent:
scripts/migrate_v1_40_drop_character_faction_id.py).

## 2. Read sites — text consumption is fully decentralized

15 loader functions return `PromptTemplate` ORM objects; text is then read by
attribute access at the call sites. Under A2+F1 every one of these breaks
until rewired through the G1 accessor.

Loaders:
- entity_author.py:95, 104, 113, 122 (`_load_template`, `_load_world_template`, `_load_player_template`, `_load_skill_catalogue_template`)
- region_author.py:51, 60 (`_load_manifest_template`, `_load_manifest_topup_template`)
- analyzer.py:141 (shared usage-parameterized loader)
- gathering.py:40 (`_load_gathering_template`)
- cockpit/app.py:1376, 1601, 1699, 1716, 1733, 1750, 2009, 2051 (npc_dialogue, mj_speaker, mj_initiative, npc_initiative_act, mj_arbiter, mj_establishment, mj_narration, mj_interpret)

Attribute-access consumption (`.system_prompt` / `.user_template`):
- region_author.py:321, 333, 400, 409
- analyzer.py:464-470, 739-745
- entity_author.py:398, 407, 527, 532, 616, 621, 704, 709
- cockpit/app.py:157/163 (via `_npc_dialogue_system_prompt`, def at 1396-1400), 199, 1638-1648, 1825-1833, 1926-1936, 2543, 2570-2572, 2762-2765 (locals captured once per stream loop, then reused at 2909/2930/2951/3285/3431), 3019-3020, 3539
- cockpit/crud.py:1654-1655 (reader detail endpoint)

**Accessor shape recommendation (mechanical, for the brief):** `current_prompt(db, template) -> PromptVersion` (highest `version_number`), plus the loaders keep returning the head. Call sites swap `template.system_prompt` → `version.system_prompt` where `version = current_prompt(db, template)` fetched once next to the existing load. One accessor, one extra local per site, zero behavioral change.

## 3. Existing write paths

- `PATCH /api/prompts/{prompt_id}/model` (cockpit/crud.py, W1 from BRIEF-0009) — writes `model` + `updated_at` only. Untouched by this chantier (B1: model stays on head).
- Seed `upsert_prompt_template` (scripts/seed_pilot.py:125-148) — setattr's text columns directly. **Breaks under F1; collides with append-only under any option — see §5.**
- No other writer. `prompt_template` is pipeline-internal stratum (canon_write_policy not applicable), but the single-write-shape principle applies: new `write_prompt_version(...)` helper in writes.py, sole sanctioned path; PATCH text route and seed both call it.

## 4. Reader API + UI anchors (BRIEF-0008-b, shipped)

- `GET /api/prompts` (crud.py:1598) — lazy master list, no bodies. Gains nothing structural; `version` field in `_prompt_row_summary` (crud.py:1586) must switch to current version_number via accessor.
- `GET /api/prompts/{id}` (crud.py:1629) — returns `system_prompt`/`user_template` from head columns (1654-1655) → rewire through accessor; extend with version history list (new `GET /api/prompts/{id}/versions` or inline).
- Preview endpoints app.py:123 (`npc_dialogue`) and app.py:167 (`player_narration`) reuse live assemblers + `_npc_dialogue_system_prompt` — fidelity invariant survives automatically once the shared helper reads via the accessor.
- Cockpit UI: tab wiring index.html:3128-3133, detail pane state `promptsCurrentDetail` index.html:3558, detail body container index.html:1360. Edit surface + history list mount in the detail pane.

## 5. ⚠ CONTRADICTION — seed convergence vs. append-only creator edits (arbitration S)

`upsert_prompt_template`'s contract (seed_pilot.py:128-130): "re-seeding must
converge the DB to the latest text." Under versioning, a re-seed after a
creator edit would either silently supersede the edit (new seed version on
top) or must be taught to yield. The ticket's entire point is that the
creator's edit is what runs. Options:

- **S1** — seed appends a new version iff seed text ≠ current version text. Converges wording; a creator edit survives in history but is overridden by the next re-seed. Simplest; violates creator sovereignty.
- **S2** — seed writes v1 only when a head has zero versions; never touches text afterwards. Creator sovereignty absolute; seed wording improvements no longer propagate to an existing DB.
- **S3 (recommended)** — add `source TEXT NOT NULL` (`seed` | `creator`) to `prompt_version`. Seed appends iff text differs AND current version's source = `seed`. A creator edit permanently shields that template from seed reconvergence; seed-only templates keep converging. Two concrete readers for the column: the seed skip rule + history UI attribution ("who wrote this version") — satisfies minimal-first.

## 6. ⚠ RISK — mixed substitution mechanics × creator-edited text (arbitration H)

Two coexisting substitution mechanisms:
- `str.format()` — region_author.py:321, 400; entity_author.py:398, 527, 616, 704 (authoring usages).
- Chained `.replace("{var}", ...)` — analyzer.py:465-467, 740-741; cockpit/app.py:1639-1642, 1791-1794, 1927+, and all play-surface sites.

Seeded play templates already contain literal JSON braces (seed_pilot.py:222-226; 32 occurrences of `{"` in seed) — safe today only because those usages are `.replace()`-consumed. Once the creator can edit ANY template, pasting a JSON example into a `.format()`-consumed authoring template raises `KeyError`/`ValueError` at call time — a crash class the editor makes reachable. C1's save-time validation (simple-identifier placeholders vs. declared `variables`) cannot catch arbitrary literal braces without false-positives on the play templates. Options:

- **H1 (recommended)** — normalize the 6 `.format()` sites to the same chained-`.replace()` mechanic as everywhere else, in this chantier. One substitution mechanism repo-wide; literal braces safe by construction everywhere; C1 stays a clean identifier-membership check. Small, bounded diff (6 sites).
- **H2** — leave `.format()` in place; C1 additionally rejects ANY undeclared brace content for the 6 `.format()`-consumed usages (per-usage validation severity). No call-site diff, but validation grows a mechanism-aware branch and the crash class survives behind it.

## 7. Verify surface

Existing precedents to extend: `tooling/verify/checks/single_canon_write.py`
(static AST attribution of writes), `prompt_model_write.py`,
`prompt_registry.py`. New checks per TICKET-0011 acceptance criteria,
including: no `prompt_version` read outside the accessor module; no
UPDATE/DELETE on `prompt_version`; single write helper.

## 8. Anchors that supersede prior assumptions

- RECON confirms no centralized template fetch exists — G1's cost is the
  full loader/call-site sweep in §2, not a single-point rewire.
- `variables` is a JSON list of names on the head (seed_pilot.py:1223); C1
  validates submitted text against it. B1 keeps it head-resident; note the
  named deferral: editing text that NEEDS a new variable requires a
  variables edit — out of scope, falls under deferred B2 territory.
