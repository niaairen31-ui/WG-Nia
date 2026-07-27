# BRIEF-0050-e — Step "config editing surface + replay measurement"

## Context

The mechanism works end to end (a-d) but the creator can only tune it via direct DB writes. I2
requires `word_budget`, `verbatim_turns`, and `summary_enabled` to be creator-editable now, and N2
places that editing on the existing prompts surface beside the `conversation_summary` template row
(named deferral D-0050: it moves to a dedicated world-config surface once one exists). This brief
also delivers the empirical piece TICKET-0050 was always going to need: a replay measurement of
where repetition reappears across K and budget values, so the seeded defaults are chosen from data,
not guessed (this is why I2 was taken over I1 — the values are tunable AND measured). It also runs
the K2 probe on `repeat_last_n`.

Mini-RECON required BEFORE wiring (do this first, report anchors):
- Locate the prompts tab render in `src/world_engine/cockpit/index.html` (the list that shows each
  usage + its model override control; search for the model-override PATCH call and the row it sits
  on). Confirm the exact insertion point for the extra fields.
- Confirm the active-world accessor the cockpit already uses (the prompts tab is largely world_id
  NULL templates; the config row is per-world, so the form MUST target the ACTIVE world and label
  which world it edits). Report how the active world id reaches the frontend.
- Locate the existing dry-run / replay harness (the monkeypatched Ollama client pattern from
  BRIEF-0027-b) to reuse for the measurement rather than building a new one. Report its entry
  point.

## Scope IN

1. **Config route** in `src/world_engine/cockpit/crud/prompts.py` (co-located with the prompts
   surface it serves, per N2), or a small sibling `crud/dialogue_config.py` if `prompts.py`
   nears the module budget — REPORT the line count and choose; do not silently push `prompts.py`
   over 1000:
   - `GET /api/conversation-window-config` -> the ACTIVE world's row via
     `load_conversation_window_config(active_world_id, db)` (returns the defaults object shape when
     absent), plus the active world's id/name for the label.
   - `PATCH /api/conversation-window-config` -> body `{word_budget?, verbatim_turns?,
     summary_enabled?}`, calls `upsert_conversation_window_config(db, world_id=active_world_id,
     ...)`, commits, returns the persisted row. Fail-closed on non-positive `word_budget` /
     `verbatim_turns` (surface the 422 from the writer).

2. **Prompts-tab UI** (`cockpit/index.html`), at the insertion point found in mini-RECON, add a
   compact "Fenetre de conversation" panel beside the `conversation_summary` row:
   - a number input for `word_budget`, a number input for `verbatim_turns`, and a checkbox for
     `summary_enabled` (default checked), each wired to `PATCH /api/conversation-window-config`.
   - a label stating which world these apply to (the active world name), because the sibling prompt
     rows are global and this panel is not.
   - relational-only: values are posted as form fields to the route above; NO JSON blob is stored
     client- or server-side for these (json_ui_boundary, CLAUDE.md:327).
   Follow the single-file no-build-step convention; reuse the existing fetch/patch helper the model-
   override control uses.

3. **Replay measurement script** `scripts/measure_conversation_window.py` (a script, not engine
   code — lives in `scripts/`, no module-budget concern): reuse the monkeypatched-Ollama replay
   harness (mini-RECON) to replay a known long conversation (the pilot Verkhaal tavern scene is a
   fine fixture) and, for `verbatim_turns` in {2, 4, 6} crossed with `word_budget` in at least two
   values (e.g. 800, 1200), report the turn index at which a near-duplicate NPC paragraph first
   reappears (a simple similarity heuristic on consecutive NPC replies is sufficient — REPORT the
   heuristic used). Output a small table to stdout and a markdown file
   `tooling/recon/RECON-0050-window-measurement.result.md`. This is measurement ONLY — it changes
   no seeded defaults automatically.

4. **K2 probe.** In the same script (or a clearly separated section), replay one over-budget
   conversation twice with `NPC_DIALOGUE_OPTIONS` `repeat_last_n` at its current 256
   (`ollama_client.py:30`) vs a larger value (e.g. 512), holding K/budget fixed, and report whether
   the larger window measurably reduces repetition. Do NOT change the constant in this brief —
   report a recommendation; a change, if warranted, is a one-line separate commit that Nia approves.

5. **Default reconciliation (conditional).** IF the measurement shows the seeded defaults
   (`word_budget=1200`, `verbatim_turns=6`) are clearly wrong, REPORT the recommended pair and, only
   on Nia's go-ahead, update the two server-defaults + the reader constants
   (`DEFAULT_WORD_BUDGET`, `DEFAULT_VERBATIM_TURNS`) in a separate commit. Absent a clear signal,
   leave them.

## Scope OUT

- Do NOT build a general world-configuration tab — N2 is explicit that this rides the prompts
  surface for now; the migration to a dedicated surface is named deferral D-0050 (future ticket).
- Do NOT make the config global — it is per active world; a NULL-world config row is not a thing.
- Do NOT auto-tune: the measurement script never writes config or changes defaults on its own.
- Do NOT change `repeat_last_n` in this brief (probe + recommend only).
- Do NOT add the config fields as a JSON payload column anywhere.
- Do NOT expand the measurement into a full eval framework — one fixture, the stated grid, a simple
  similarity heuristic, a report. Nothing more.

## Invariants to defend

- **json_ui_boundary** (CLAUDE.md:327): the new form is relational-only, posted to the typed
  columns.
- **single canon-write**: the only writer remains `upsert_conversation_window_config`; the route is
  a thin creator-CRUD caller.
- **index.html is a single file, no build step** (CLAUDE.md:58): the panel follows the existing
  pattern.
- **conditional fixes are narrow**: the default reconciliation and the `repeat_last_n` change are
  each gated on a finding + Nia's approval + a separate commit.

## Done means

- [ ] The prompts tab shows a "Fenetre de conversation" panel labelled with the active world's
      name; editing `word_budget` / `verbatim_turns` / `summary_enabled` there persists (reload
      shows the saved values) and takes effect in the next live over-budget turn.
- [ ] `GET /api/conversation-window-config` on a fresh world returns the defaults object
      (1200 / 6 / true) without creating a row; `PATCH` then creates/updates it.
- [ ] A non-positive `word_budget` PATCH returns 422 and does not write.
- [ ] `python scripts/measure_conversation_window.py` produces the stdout table and
      `tooling/recon/RECON-0050-window-measurement.result.md` with, per (K, budget) cell, the turn
      index of first repetition and a recommended default pair.
- [ ] The K2 probe section reports the 256-vs-larger `repeat_last_n` comparison with a stated
      recommendation; `ollama_client.py:30` is unchanged unless Nia approved a separate commit.
- [ ] `json_ui_boundary.py` and `module_budget.py` PASS; `wc -l` on any touched engine file
      < 1000.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: mark named deferral **D-0050** (config editing migrates to a future
  world-configuration surface) as OPEN, and record the measured default recommendation.
- `CHANGELOG.md`: TICKET-0050 close entry once (e) lands.
- Attach the measurement result file under `tooling/recon/`.
