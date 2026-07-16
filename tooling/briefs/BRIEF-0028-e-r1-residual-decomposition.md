<!-- slug: r1-residual-decomposition -->
# BRIEF-0028-e — In-place decomposition of the remaining R1 residual

Ticket: TICKET-0028 | Danger: none — behavior-preserving decomposition
across analyzer, context, routes, and play paths | Blast radius: medium
(wide but shallow) | Depends on: BRIEF-0028-d merged (`main` @ post-d,
verify green)

## Context

After stages b–d, `baselines/function_length.json` holds the 19
remaining entries, spread across 10 modules (authoritative list = the
baseline file at execution time; regenerate at RECON — the census below
is orientation, not authority):

- `analyzer.py`: `analyze_overhearing` 256, `_normalize_to_schema` 180,
  `analyze_window` 149
- `context.py`: `assemble_npc_context` 267, `assemble_mj_context` 161
- `routes/regions.py`: `commit_region` 271 (live 264 — shrink-only
  drift already observed at RECON, baseline value intentionally stale)
- `routes/mutations.py`: `_find_applied_duplicate` 256,
  `approve_mutation` 106, `batch_review_mutations` 97
- `routes/play.py`: `scene_join` 163, `world_tick_endpoint` 81
- `play_stream.py`: `_npc_initiative_vote` 117, `_build_mj_user` 114
- `region_author.py`: `generate_region_draft` 157, `_normalize_manifest` 91
- `cockpit/mutations.py`: `_apply_completion_effects` 150
- `routes/creator.py`: `create_player_character` 108
- `play_physical.py`: `_arbitrate` 87
- `crud/goals.py`: `backfill_npc_goals` 84

No structural relocation in this brief: every function is decomposed IN
its current module, along existing seams. That is what makes a single
wide brief safe — 19 independent, shallow, mechanically similar edits.

## Scope IN

1. **Per-module helper inventory (R7)** before each module's edits, in
   execution notes with `file:line`; reuse existing helpers, new
   extractions take domain-local prefixes, moved nothing (in-place
   brief).

2. **Decompose all 19 functions** to <= 80 lines: pure extraction +
   mechanical parameter passing. Frozen per path:
   - Route functions: route contracts frozen — method, path, request/
     response shape, status codes. Pair the sorted set-equality
     route-contract proof with the shadowing audit and
     `undefined_names.py` (the -i precedent: set-equality alone is
     blind to ordering and runtime name resolution).
   - `analyzer.py` / `region_author.py` normalizers: fail-closed
     semantics frozen — every rejection path rejects identically; all
     value types handled before (booleans, `list[str]`) handled after.
   - `_apply_completion_effects`, `approve_mutation`,
     `batch_review_mutations`: SAVEPOINT structure and effect ordering
     frozen; no ORM write statement leaves a closed-list function (same
     rule as -b item 4).
   - `context.py` assemblers: secrets exclusion is structural — the
     query-level filtering moves intact inside extractions; no
     extraction may convert a query-level exclusion into a
     post-fetch filter.
   - `scene_join`, `_perform_travel`-adjacent code: gathering invariant
     (one open gathering per present NPC) untouched.

3. **Harness discipline.** Before decomposing any function on a
   model-calling path, check the four harness manifests: if the
   function is NAMED in a manifest, replay must PASS post-edit; if it
   is on a model path but NOT named (expected: `analyze_overhearing`,
   `analyze_window`, `_npc_initiative_vote`, `_build_mj_user`,
   `generate_region_draft` is named via the entity_author harness —
   verify), extend the nearest harness's fixtures FIRST so the manifest
   names it, self-validate pre-edit, then decompose. Model-free
   functions get before/after deterministic fixtures only where the
   executor judges the seam risky; record the judgment either way.

4. **Baseline shrink to EMPTY.** All 19 entries removed. Residual after
   this brief: 0 function entries, 1 module entry (`entity_author.py`
   if stage d left it — expected 0 after d; whichever file is nonempty,
   this brief empties `function_length.json`). The files themselves are
   deleted at -f, not here.

## Scope OUT

- Any module split or relocation (b/c/d own those).
- Any behavior change, prompt change, contract change; candidates
  logged.
- Baseline FILE deletion, harness deletion, `code_standards.md` edits
  (-f).
- The advisory frontend rules (F1–F3) and the 8,834-line frontend.

## Invariants to defend

- Route contracts frozen (set-equality + shadowing audit +
  `undefined_names.py`).
- Secrets excluded at query construction level — non-negotiable; audit
  each `context.py` extraction against this explicitly in the PR.
- Fail-closed normalizers stay fail-closed; French interval labels are
  DATA.
- Canon-write closed list untouched; `single_canon_write.py` green.
- Full suite green; `function_length.json` empty; shrink-only respected
  throughout.

## Done means

### Machine-checkable
- [ ] `function_length.py` green with an EMPTY baseline; every function
      in `src/` <= 80 lines.
- [ ] Route-contract proof: sorted set-equality pre/post + zero-pair
      shadowing scan + `undefined_names.py` green.
- [ ] Every harness whose manifest names a touched function: replay
      PASS post-edit; every manifest extension self-validated pre-edit.
- [ ] Full suite (30 checks) green.

### Live gate (Nia)
- [ ] One scene entry + `/say` with NPC initiative firing, one window
      analysis, one region commit, one mutation batch review, one goal
      backfill — each unchanged.

## Docs to update

- `TICKET-0028` front-matter: append `BRIEF-0028-e`.
- Nothing else; doctrine edits are -f's.
