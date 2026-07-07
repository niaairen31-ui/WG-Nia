# BRIEF — Step "world-tick runner, guard and cockpit (BRIEF-0014-b-tick-runner-and-guard)"

## Context

BRIEF-0014-a landed the read side on `ticket/0014`: `tick.py` with
`assemble_tick_context` (tick.py:93), the `pt-world-tick` template
(seed_pilot.py:837-905, payload shapes locked: `"other"` for relation
counterpart, `"recipient":"self"|name`, `secret_derived` flag), the N1
allowlist extension, `world_tick.py` rules 1-2, and the preview script.
This chantier makes the tick RUN: the `tick_id` migration (Y2), the
runner + normalizer with forced attribution (E1, O1-mirror), the
`secret_derived` code floor (Z3), the duplicate-guard tick branch (closes
RECON-0014 F2), and the cockpit UI ("Faire avancer le monde", I1/J1/M3,
R3 summary, P1 labels). danger_class: migration — the live deployment
sequence is mandatory in Done means.

## Scope IN

1. **Migration `scripts/migrate_v1_<next>_tick_id.py`** (executor assigns
   the version; expected v1.70; precedent shape
   `scripts/migrate_v1_69_npc_goal.py`): purely additive, idempotent —
   `ALTER TABLE proposed_mutation ADD COLUMN tick_id TEXT NULL` +
   `CREATE INDEX IF NOT EXISTS idx_mutation_tick ON proposed_mutation(tick_id)`.

2. **Model change** — `ProposedMutation` (models.py:556) gains
   `tick_id: Optional[str] = Field(default=None)` and
   `Index("idx_mutation_tick", "tick_id")` in `__table_args__`. Update the
   source comment at models.py:568 to
   `# source: exactly one of these is set` /
   `source_type: str  # pass_play | conversation | world_tick`
   (world_tick sets NEITHER FK; tick_id is its anchor).

3. **Runner `run_world_tick` in `src/world_engine/tick.py`**:
   `run_world_tick(db, npc_ids: list[str], interval_label: str,
   model: str = ollama_client.DEFAULT_MODEL, host: str =
   ollama_client.OLLAMA_HOST) -> dict`.
   - Generates ONE `tick_id = str(uuid4())` for the invocation.
   - Reuses from `.analyzer` (import, do not duplicate — analyzer never
     imports tick, no cycle): `load_analysis_prompt` (generic over
     `usage`, analyzer.py:166), `_extract_json_array`,
     `_content_to_subject_slug`, `_GOAL_ACTION_MAP`.
   - Per NPC, degrade-don't-abort (R3): assemble briefing
     (`assemble_tick_context`), load `usage="world_tick"` template,
     `str.replace` `{tick_context}` and `{interval_label}` into the user
     template, call `ollama_client.chat(..., model=effective_model(
     template, model), format="json")`, extract + parse JSON array.
     Any exception or parse failure for one NPC -> record a note for that
     NPC and continue with the others; NOTHING written for that NPC.
   - Normalize each item (item 4), apply emit-time dedup (item 6), build
     `ProposedMutation` rows: `world_id`, `source_type="world_tick"`,
     `conversation_id=None`, `pass_play_id=None`, `tick_id=tick_id`,
     `mutation_type`, `target_table`, `target_id=None`, `payload`,
     `status="proposed"`, `rationale`, `proposed_by="local_ai_tick"`.
   - ONE transaction per invocation: all surviving rows across all NPCs
     added, single commit at the end. (A failed NPC is a skipped NPC, not
     an aborted tick; a crashed invocation writes nothing.)
   - Returns the R3 summary:
     `{"tick_id": …, "interval": …, "npcs": [{"id", "name", "proposed":
     n, "dropped": n, "notes": [str]}], "total_proposed": n}`.

4. **Normalizer `_normalize_tick_item(raw_item, *, npc_id, world_id,
   roster, secret_subjects) -> dict | None` in tick.py.** The tick's
   contract is CLOSED (unlike conversation analysis): `mutation_type`
   must map to exactly `goal_change | relation_change | new_knowledge`
   (accept the same aliases as `analyzer._MUTATION_TYPE_MAP` but drop —
   with a note — anything mapping outside the three; never emit `other`).
   - `goal_change` — action via `_GOAL_ACTION_MAP`, goal text required
     (same field fallbacks as analyzer.py:398-424); unrecognised action
     or empty text -> drop. Payload EXACTLY
     `{"npc_id": <the npc_id parameter>, "action": …, "goal": …}` —
     npc_id FORCED from the parameter, never read from the model payload
     (O1-mirror). `target_table="npc_goal"`.
   - `relation_change` — resolve `payload["other"]` through `roster`;
     unresolved -> drop with note (analyzer.py:380-388 discipline).
     Payload `{"entity_a_id": <the npc_id parameter>, "entity_b_id":
     <resolved id>, "relation_type": payload value or
     "passive_attention", "intensity_delta": int(required, else drop)}`.
     `entity_a_id` FORCED from the parameter. `target_table="relation"`.
   - `new_knowledge` — `recipient` `"self"` -> `entity_id = npc_id`,
     otherwise roster-resolve (unresolved -> drop with note). `subject`:
     given or `_content_to_subject_slug(content)`; `level` default
     `"rumor"`; `content` required (empty -> drop); `source` default
     `"world_tick"`; `is_secret = bool(payload.get("is_secret", False))`
     — passed through UNTOUCHED (decoupling); `secret_derived =
     bool(payload.get("secret_derived", False)) or <Z3 floor, item 5>`.
     `target_table="knowledge"`.
   - `rationale` defaulting as analyzer.py:426-432.

5. **Z3 floor (verbatim mechanics).** Before normalizing an NPC's items,
   build `secret_subjects = { k.subject.casefold() for k in <the ticked
   NPC's Knowledge rows where is_secret> if k.subject }`. The floor
   forces `secret_derived = True` when EITHER the proposal's
   `subject.casefold()` is in `secret_subjects`, OR any element of
   `secret_subjects` appears as a substring of `content.casefold()`.
   The floor NEVER reads or writes `is_secret` — provenance is
   mechanical, confidentiality is dispositional (Z3 decoupling, Nia's
   allies/enemies rule).

6. **Roster + emit-time dedup.**
   - `roster: dict[str, str]` maps `entity.name.casefold()` -> id, built
     from EXACTLY what the briefing names: the ticked NPC itself,
     characters at its `current_location_id` (QUI EST AUTOUR), and the
     targets of its perceived relations (TES RELATIONS). A casefolded
     name carried by two different ids is AMBIGUOUS: remove it from the
     roster (resolution fails -> drop with note; a silent wrong
     attribution is worse than a dropped proposal).
   - Within one NPC's item list, drop-with-note subsequent duplicates:
     `goal_change` keyed `(action, normalized goal text)` — reuse the
     normalization of `_normalize_goal_text` (cockpit/app.py:804; move
     it, or replicate the 3-line helper in tick.py and note the twin);
     `new_knowledge` keyed `(entity_id, subject)`; `relation_change`
     keyed `(entity_a_id, entity_b_id)` keeping the FIRST item (the
     rubric demands one NET change per counterpart; extras are rubric
     violations, not accumulating deltas).

7. **Duplicate-application guard — tick branch (Y2, closes F2).** In
   `_find_applied_duplicate` (cockpit/app.py:700), the early return
   `if not mut.conversation_id: return None` (cockpit/app.py:754) becomes:
   conversation-sourced mutations keep the EXISTING branch byte-identical;
   THEN, when `mut.tick_id` is set, a tick branch runs CANON-EXISTENCE
   checks (revival-safe — see drafting decision 1):
   - `goal_change` with `action == "create_short"` -> duplicate when an
     ACTIVE `NpcGoal` exists for `payload["npc_id"]` whose
     `_normalize_goal_text(description)` equals the proposal's normalized
     goal text. (complete/abandon: NO guard — the apply branch's
     exactly-one-active-match requirement, cockpit/app.py:1050-1060, is
     already the correct gate.)
   - `new_knowledge` -> duplicate when a `Knowledge` row exists with the
     same `(entity_id, subject)`.
   - `relation_change` -> NO guard (accumulating deltas doctrine,
     cockpit/app.py:720-724) — double deltas from a re-run tick are
     visible in the queue and the creator's to judge, never blocked.
   Extend the function docstring with this second scope and its
   asymmetries, in the same explicit style as the existing exclusion
   paragraphs.

8. **Endpoint `POST /api/world-tick`** in `cockpit/app.py` (beside the
   analyzer-facing endpoints — NOT crud.py, RECON-0014 F8). Body:
   `{"scope_type": "npcs" | "location" | "faction",
     "npc_ids": [..] (scope_type=npcs),
     "scope_id": str (location/faction),
     "interval": "quelques heures" | "quelques jours" | "quelques semaines"}`.
   - Scope resolution to NPC ids: `npcs` -> validate each id resolves to
     an NPC character; `location` -> Characters with
     `current_location_id == scope_id`, `character_type == "npc"`,
     `vital_status == "alive"`, entity `status == "active"` (filter
     precedent: gathering co-presence, context.py D1 block); `faction` ->
     entities with an ACTIVE membership (`left_at IS NULL`) of that
     faction, same character filters.
   - Unknown interval value, unknown scope_type, or an EMPTY resolved
     NPC list -> 422 with a clear message; nothing runs.
   - Calls `run_world_tick`, returns its R3 summary as JSON.

9. **Queue surfacing (P1 + Z3 badge).**
   - `_mutation_dict` (cockpit/app.py:678) gains `"tick_id": m.tick_id`.
   - `renderCard` in `cockpit/index.html` (mapped at index.html:2483):
     when `m.source_type === "world_tick"`, render a `TICK ·<first 4
     chars of tick_id>` badge (grouping label — same invocation, same
     suffix); when `m.payload && m.payload.secret_derived === true`,
     render a distinct warning-styled badge with the exact French label
     `dérivé d'un secret` (payload-specific rendering precedent:
     `_renderResourceChangeLegs`, index.html:2509).

10. **Cockpit controls (I1/J1/M3)** — in the analyze-controls cluster
    above the review queue (handler pattern index.html:2400-2418:
    disable-while-running, inline status line, on success
    `setFilterByName('proposed')` + `await loadQueue()`):
    a button `Faire avancer le monde`, a scope-type selector
    (`PNJ(s)` multi-select / `Lieu` select / `Faction` select — populate
    from the entity-list APIs the Création view already calls; if none
    fits a scope type, REPORT, do not invent an endpoint), and an
    interval selector with the three verbatim values from item 8. Status
    line on success: `✓ {total_proposed} propositions (tick {4-char id})`
    plus per-NPC notes when any NPC failed or dropped items.

11. **Verify check extension `tooling/verify/checks/world_tick.py`**
    (rules 1-2 unchanged) — add, stdlib `ast` only, red-tested:
    - Rule 3 (forced attribution): within `tick.py`, no
      `…get("npc_id")` / `…get("entity_a_id")` call anywhere (the model
      payload is never the source of either), AND the identifiers
      `npc_id` / `entity_a_id` appear as dict keys only in dict literals
      whose value node for that key is a `Name` (the parameter), never a
      `Call`/`Subscript` on the raw item.
    - Rule 4 (guard branch): `_find_applied_duplicate` in
      `cockpit/app.py` contains an attribute access `mut.tick_id` (or a
      `tick_id` Name bound from it) — the tick scope exists.
    - Rule 5 (Z3 floor + decoupling): `tick.py` contains a comparison
      against a set built from `Knowledge` rows filtered on `is_secret`,
      and within `_normalize_tick_item` the identifier `is_secret` never
      appears on the LEFT side of an assignment whose right side
      references `secret_subjects` or `secret_derived` (the floor cannot
      set confidentiality).

## Scope OUT

- No automatic trigger, scheduler, or in-game time system (I3 deferred);
  no `last_tick_at` storage (M decision).
- No movement / `status_change` / `event_creation` emission (L3 closed
  set); no widening of the type contract "for robustness".
- No goal hierarchy (`parent_goal_id`, F2) — even when a completed short
  invites "the next step", `create_short` stays flat.
- No pre-authorization or auto-apply of any category (J3 rejected; named
  deferred, creator-declared only).
- No dedicated tick-review screen (P3 rejected); no queue grouping UI
  beyond the badge label.
- No cross-source duplicate guard (conversation-sourced vs tick-sourced
  histories stay independent; only the canon-existence checks above).
- No cap or throttle on scope size (J1: Nia controls volume by scoping).
- No changes to `pt-world-tick` text, `assemble_tick_context` sections,
  or any conversation-pipeline behavior (`analyze_window`,
  `analyze_overhearing`, their guards) beyond the guard branch in item 7.
- `Faction.goals` dialogue injection: still its own deferred chantier.

## Invariants to defend

- **Model proposes, code judges** — the model outputs names and text
  only; `npc_id`/`entity_a_id` forced from the parameter (rule 3);
  horizon remains structurally short-only at apply (untouched 0013 O1
  branch); everything crosses `proposed_mutation` under creator approval.
- **Structural over disciplinary** — F2's guard bypass is closed by a
  code branch keyed on `tick_id` presence, not by creator vigilance; the
  Z3 floor is mechanical; both are AST-verified (rules 3-5).
- **History is sacred** — the guard blocks silent double-writes
  (create_short, new_knowledge) while NEVER blocking accumulating
  relation deltas or legitimate goal revivals (canon-existence, not
  history comparison).
- **No structure without a reader** — `tick_id` ships with BOTH readers:
  the guard branch and the queue badge, this brief.
- **Single canon write** — the tick writes `ProposedMutation` rows only;
  `single_canon_write.py` must pass unchanged.
- **N1** — the runner lives in tick.py (allowlisted); no MJ surface
  touches goals or the briefing; `npc_goal_read.py` byte-identical.
- **Z3 decoupling** — the floor forces provenance only; `is_secret`
  flows model -> payload -> `write_knowledge` untouched (rule 5 enforces).

## Done means

- [ ] Migration run twice on a COPY of the live DB: first run adds
      `tick_id` + index; second run no-ops. `PRAGMA table_info` shows the
      column; `PRAGMA index_list` shows `idx_mutation_tick`.
- [ ] `POST /api/world-tick` with `scope_type="location"` on a location
      holding >=2 NPCs returns an R3 summary and writes proposals whose
      rows have `source_type="world_tick"`, `proposed_by="local_ai_tick"`,
      a shared `tick_id`, NULL conversation_id/pass_play_id.
- [ ] Queue: those proposals carry the `TICK ·xxxx` badge; two proposals
      from the same invocation show the same suffix.
- [ ] A tick on an NPC holding a `[SECRET]` knowledge row, where the model
      propagates it: the proposal shows the `dérivé d'un secret` badge;
      flipping `is_secret` in the payload is independent of the badge
      (approve one with is_secret=false, badge still shown).
- [ ] Re-run the SAME scope+interval; approve a duplicate `create_short`
      and a duplicate `new_knowledge` -> both blocked to Needs attention
      with the guard's message; approve a repeated `relation_change` ->
      applies (accumulates), never blocked.
- [ ] Revival is NOT blocked: abandon an applied tick-created short via
      creator CRUD, re-run a tick proposing the same text, approve ->
      applies as a NEW row.
- [ ] Unknown interval, unknown scope_type, or empty resolved scope ->
      422, no model call, nothing written.
- [ ] With Ollama stopped for one NPC mid-scope (or a forced exception in
      a spot-check), the summary shows that NPC's note and the other
      NPCs' proposals land — one commit, no partial-NPC rows.
- [ ] `python tooling/verify/checks/world_tick.py` -> PASS (rules 1-5);
      red tests: locally read `raw_item.get("npc_id")` in the normalizer
      -> rule 3 FAILS; locally remove the `mut.tick_id` branch -> rule 4
      FAILS; locally assign `is_secret` from the floor -> rule 5 FAILS;
      revert all.
- [ ] `python tooling/verify/checks/npc_goal_read.py` and
      `python tooling/verify/checks/single_canon_write.py` -> PASS
      unchanged.
- [ ] Live deployment sequence (danger_class migration, standing rule):
      `python backup.py` -> `python scripts/migrate_v1_<next>_tick_id.py`
      -> `python scripts/apply_ticket_0014_prompt_updates.py` (no-op
      re-run, sequence consistency) -> live browser test of the four
      queue/guard criteria above.
- [ ] /review-step and /close-step run (engine code + migration touched).

## Docs to update

- `world-engine-schema-changelog.md` — v1.<next> entry: `tick_id` on
  `proposed_mutation` (nullable, indexed), third `source_type` value
  `world_tick`, both FKs NULL for that source.
- `ARCHITECTURE_DECISIONS.md` — append to the WORLD TICK section: Y2 as
  implemented (canon-existence guard for tick-sourced create_short /
  new_knowledge; revival-safe; relation_change never guarded), the closed
  type contract of the tick path, and the Z3 floor mechanics + decoupling.
- `CLAUDE.md` — one line: tick-sourced `proposed_mutation` rows have
  `source_type="world_tick"`, NULL FKs, mandatory `tick_id`; the
  duplicate guard's tick branch is canon-existence-based and must never
  be extended to relation_change.

---

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **Y2 refinement — canon-existence instead of tick_id-keyed history
   comparison.** RECON -b found that a re-run gets a NEW tick_id, so a
   guard comparing applied rows WITHIN one tick_id would miss exactly the
   cross-run duplicates F2 is about, while an UNBOUNDED history
   comparison would block legitimate goal revivals (a revived goal is a
   new row, 0013 doctrine). Implemented: `tick_id` presence selects the
   branch; the duplicate test asks the CANON ("does this active goal /
   this knowledge row already exist?"), which is re-run-proof AND
   revival-safe. `tick_id`'s value keeps its second reader (queue badge).
2. **Closed type contract**: tick items outside the L3 trio are dropped
   with a note, never proposed as `other`.
3. **One transaction per invocation**: per-NPC model failures degrade
   (R3), but surviving proposals commit together; a crashed invocation
   writes nothing.
4. **Ambiguous names** (two entities, same casefolded name) are removed
   from the roster -> resolution fails -> drop with note.
5. **Roster = exactly what the briefing names**: self + co-located +
   relation targets. No faction-mate expansion.
6. **UI placement**: tick controls join the analyze cluster above the
   review queue; interval values are the three verbatim French labels.
