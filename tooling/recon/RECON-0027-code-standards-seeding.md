<!-- slug: code-standards-seeding -->
# RECON-0027 — Code standards SEEDING review

Report-only. Fetched: `main` tarball via codeload, 2026-07-13, schema v1.79
(TICKET-0026 at live-gate). Inputs per the seeding protocol: codebase +
`tooling/improvement/bug_log.jsonl` + ticket history (TICKET-0001..0026,
47 briefs).

## 1. Volume and shape

- Python `src/`: 18175 lines, 363 functions across 18 modules.
- Frontend: `src/world_engine/cockpit/index.html` 8834 lines, 2 script
  blocks, ~7375 JS lines, 346 JS functions.
- Largest modules: `cockpit/app.py` 6180l/103f/42 routes (27 POST, 13 GET,
  1 DELETE, 1 PATCH), `cockpit/crud.py` 2932l/109f, `tick.py` 1803l/20f,
  `writes.py` 1607l/32f, `models.py` 1188l, `entity_author.py` 1062l.

## 2. Emergent norms (already held, unwritten)

- Return type annotations: 359/363 functions.
- Zero bare `except:`; 14 `except Exception` sites, concentrated at route
  bodies (`cockpit/app.py`: 11) and loop boundaries (`tick.py`: 2,
  `gathering.py`: 1).
- Zero TODO/FIXME/XXX/HACK markers.
- ORM discipline: `select()` used everywhere (app.py 79, crud.py 42,
  tick.py 33, context.py 20); raw `text()` confined to `writes.py` (20,
  chokepoint helpers) and `models.py` (60, DDL/indexes).
- SAVEPOINT usage: 14 `begin_nested`/SAVEPOINT sites, 18 rollback sites,
  consistent with the mutation-atomicity doctrine.

## 3. Risk zone A — monolith concentration

Function length distribution: 26 functions > 100 lines, 66 > 50.

- `src/world_engine/cockpit/app.py:3843` `say` — 1130 lines, containing a
  nested 958-line generator `_stream` (`app.py:4013`). Grown by accretion:
  every Play-mode ticket (0013..0016, 0020, 0024) touched it.
- `src/world_engine/cockpit/app.py:1470` `_apply_mutation` — 682 lines,
  one branch per mutation type in a single body.
- `src/world_engine/tick.py:1383` `run_world_tick` — 421 lines.
- `src/world_engine/cockpit/app.py:651` `commit_region` — 264 lines.
- `src/world_engine/cockpit/app.py:969` `_find_applied_duplicate` — 256
  lines.
- `src/world_engine/context.py:221` `assemble_npc_context` — 267 lines.
- `src/world_engine/analyzer.py:449` `analyze_overhearing` — 260 lines.

No structural bound exists on function or module size; `page_contract.py`
governs the frontend registry but nothing bounds `app.py`/`crud.py` growth.

## 4. Risk zone B — duplicated LLM-output parsing

- Shared helper exists: `src/world_engine/analyzer.py:195`
  `_extract_json_array`, imported by `tick.py:32` and used at
  `tick.py:1463` and `tick.py:1683`, plus `analyzer.py:530` and
  `analyzer.py:812`.
- `src/world_engine/entity_author.py` bypasses it entirely: 7 independent
  parse sites with local `JSONDecodeError` handling at lines 446, 569, 656,
  742, 805, 884, 996.
- `region_author.py` (2 sites) and `ollama_client.py` (1) also parse
  locally.
- Total `json.loads` in `src/`: 24 call sites across 8 modules.
- Failure precedent: the only `bug_log.jsonl` entry (2026-07-03,
  `context.py:214-218`) is exactly this class — model-output shape drift
  (`subculture["values"]` list vs string) crashing a consumer. Corrected by
  BRIEF-0025-d (v1.78 validation pass rejected 37/42 location blobs), but
  the log entry still reads `status: "open"`.

## 5. Risk zone C — logging inconsistency

- `logging` used only in `cockpit/app.py:34,133` and `gathering.py:23,35`.
- 38 `print()` call sites in `src/`, nearly all in `analyzer.py` (e.g.
  183, 542, 547, 550, 804, 810, 816, 817) — invisible to log capture
  during live play.
- French strings in `src/` violate the English-only convention:
  `analyzer.py:804` ("Analyse en cours...").

## 6. Risk zone D — frontend outside governance

- `cockpit/index.html` is ~45% of project volume; only the registry
  contract is checked (`tooling/verify/checks/page_contract.py`). No size,
  naming, or state conventions exist for its 346 JS functions.

## 7. Existing enforcement surface (for new checks to join)

- 25 fail-closed checks in `tooling/verify/checks/`; established patterns
  this seeding reuses: named allow-lists (`json_ui_boundary.py`), contract
  line budgets (`claude_md_contract.py`), chokepoint enforcement
  (`single_canon_write.py`). `tooling/verify/baselines/` exists.

## 8. Housekeeping observed

- `tooling/improvement/bug_log.jsonl` single entry status flag stale (see
  section 4).

No actions taken. Findings feed `code_standards.md` v1 and TICKET-0027.
