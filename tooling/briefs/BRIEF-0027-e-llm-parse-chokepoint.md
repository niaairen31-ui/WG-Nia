<!-- slug: llm-parse-chokepoint -->
# BRIEF-0027-e — Create `llm_parse.py`; migrate all model-output parse sites

Ticket: TICKET-0027 | Danger: none of the named classes, but touches the
only known bug-producing code path (model-output shape drift) | Blast
radius: medium | Depends on: BRIEF-0027-d merged; own branch
`ticket/0027-e`

## Context

R2 (code_standards): all local-model output parsing lives in one module.
Current `TRANSITION_ALLOW` in `llm_parse_chokepoint.py` (merged branch):
`entity_author.py` 7 sites (lines 445, 568, 655, 741, 804, 883, 995),
`app.py` 4 (post-d: re-locate in routers), `analyzer.py` 2,
`region_author.py` 2, `tick.py` 2, `gathering.py` 1, `play_stream.py` 1
— 19 sites. The check enforces emptiness structurally: **the moment
`src/world_engine/llm_parse.py` exists, any remaining TRANSITION_ALLOW
entry is a failure** — so this brief creates the module and empties the
list in the same commit, atomically.

## Scope IN

1. **Inventory (R7).** Per transition site: what shape it expects
   (object/array), its fence/`<think>`-stripping behavior, its failure
   handling (raise/None/fallback), `file:line`. Table in execution notes
   before writing the module.

2. **Module.** `src/world_engine/llm_parse.py`, small surface (target:
   <= 6 public functions), e.g.:
   - `extract_object(raw: str) -> dict` / `extract_array(raw: str) -> list`
     — fence stripping, `<think>` stripping (reuse
     `ollama_client.strip_think`, do not duplicate it), first-balanced
     JSON extraction, `LlmParseError` on failure;
   - `extract_object_or_none(...)` / `extract_array_or_none(...)` for
     callers that currently swallow failures.
   `_extract_json_array` moves here from `analyzer.py` (analyzer imports
   it back or callers repoint — repoint; no re-export shim). The module
   owns **extraction and normalization only**; domain validation (e.g.
   entity_author's field checks, the v1.78 subculture shape validation)
   stays with the callers, unchanged.

3. **Migration.** Repoint all 19 transition sites onto the module; empty
   `TRANSITION_ALLOW`. Per-site behavior preserved exactly: a site that
   returned None on garbage still does; a site that raised still raises
   (map onto `_or_none` vs raising variants accordingly — the inventory
   table drives the mapping).

4. **Permanent list audit.** Re-verify each `PERMANENT_ALLOW` entry
   (`ollama_client.py` transport-frame decode ×3, `crud.py` 1, `app.py`
   1 relocated by stage d) still qualifies as non-model-content JSON;
   reasons refreshed in the check's comments.

5. **Baseline shrink.** `entity_author.py` should drop below R5's
   1000-line cap once its parse boilerplate collapses — if so, delete its
   `module_budget.json` entry; otherwise shrink it. Shrink
   `function_length.json` entries for any migrated function that drops
   <= 80.

## Scope OUT

- Any prompt change; any change to what the models are asked to emit.
- Any validation-logic change (extraction moves, judgment stays).
- Retry/repair logic for malformed output (candidate ticket if wanted).
- Logging changes (stage f).

## Invariants to defend

- "Model proposes, code judges": the chokepoint centralizes parsing, not
  judgment — zero validation semantics move into `llm_parse.py`.
- Broken-output fallbacks preserved verbatim (e.g. gathering's
  broken-output -> solo-gatherings path).
- `llm_parse_chokepoint.py` green with TRANSITION_ALLOW empty; full
  suite green; baselines strictly smaller.
- `llm_parse.py` within R5 caps, no baseline entry.

## Done means

### Machine-checkable
- [ ] `llm_parse_chokepoint.py` green: module exists, transition list
      empty, zero unlisted `json.loads` in `src/`.
- [ ] `harness_say_replay.py` and `harness_mutation_apply.py` replays
      PASS (both pipelines cross migrated parse sites).
- [ ] Authoring smoke on a DB copy: one full entity-author run and one
      region-author run complete with outputs equivalent to a
      pre-migration run on the same recorded model responses (extend the
      record/replay pattern to one authoring path fixture).
- [ ] Full suite green; `module_budget.json` and
      `function_length.json` strictly smaller.

### Live gate (Nia)
- [ ] One live authoring action (create an entity via the cockpit) and
      one live `/say` turn: both complete normally.

## Docs to update

- None (no schema change; R2's rationale already lives in
  code_standards.md).
