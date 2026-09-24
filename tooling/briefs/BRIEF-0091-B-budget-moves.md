# BRIEF 0091-B — "pure moves for module budgets"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `context.py` 956 lines; `_npc_context_setting` 327-356,
  `_npc_context_company` 449-475, `_mj_context_co_presents` 770-797.
- `link_author.py` 959 lines; `_location_chain_names` 147-161,
  `_npc_sheet` 164-184, callers `:172`, `:235-236`.
- `cockpit/play.py` 997 lines; `_propose_engine_discovery` 964-997,
  imported by `cockpit/play_physical.py:53`.
- `traits.py:74` names `world_engine.context:_npc_context_identity`.
- `schema_reconcile.py:30` defines `static_table_names()`.

## Facts carried

### R-09 — `context.py` readers of moving columns
Opened: `src/world_engine/context.py` [M].
Finding: `_npc_context_identity` (`:231-243`) appends
`npc_char.appearance`, `.backstory`, `.aversion`, `npc_entity.description`
(`:234-241`). `_npc_context_setting` (`:327`) appends
`loc_entity.description` (`:333-334`). `_npc_context_company` (`:449`)
uses `co_char.appearance or co_entity.description` (`:471`).
`_mj_context_location` (`:698`) reads `location_subculture` rows with
`key in _SAFE_SUBCULTURE_KEYS` and `is_hidden == False` (`:704-713`) and
`loc_entity.description` (`:718`). `_mj_context_co_presents` (`:770-798`)
emits `co_entity.description` for public co-presents, `None` when
blindfolded (`:795`). `_SAFE_SUBCULTURE_KEYS = ("values",)` (`:102`).
`context.py:762` is `Event.description`, not an entity — out of scope.
Module: 956 lines, 30 top-level functions.
Consequence: G replaces each read by C-10; the file has 44 lines of
headroom, so B moves the identity/company/setting/MJ-location/MJ-co-presents
helpers out first.

### R-21 — budgets
Opened: AST count of top-level functions and `wc -l` on each file [M]
(pasted in gate (c)).
Finding: `context.py` 956 / 30; `link_author.py` 959 / 36;
`cockpit/crud/entities.py` 904 / 25; `cockpit/play.py` 997 / 28;
`entity_author.py` 846 / 29; `tick_context.py` 736 / 28;
`cockpit/routes/creator.py` 732 / 26; `knowledge_resolve.py` 304 / 10;
`writes/relations.py` 365 / 13; `gathering.py` 494 / 11; `routes/scene.py`
439 / 9; `routes/play.py` 716 / 14; `lore_selectors.py` 265 / 8;
`writes/config.py` 539 / 9; `writes/knowledge.py` 254 / 7; `Sheet.svelte`
774. Caps: 1000 lines, 40 functions (`checks/module_budget.py:57`).
Consequence: B moves code out of the first four before any brief adds to
them.

### R-29 — files and functions pinned by existing gates
Opened: `src/world_engine/traits.py:74`; `tooling/verify/checks/prompt_lean.py:8,28,77`;
`stream_session_readonly.py:12-14`; `json_ui_boundary.py:33`;
`known_reachability.py:315-330`; AST spans of the four budget files [M].
Finding: `traits.py:74` names `reader_callable="world_engine.context:_npc_context_identity"`.
`prompt_lean.py` rule 3 requires `_SAFE_SUBCULTURE_KEYS == ("values",)` in
`context.py`. `stream_session_readonly.py` documents `_join_gathering`
(`cockpit/play.py:901-926`) keeping its signature and its call sites
(`play.py:400`, `routes/scene.py:316`, `routes/play.py:239`).
`json_ui_boundary.py:33` reads the field registry from
`cockpit/crud/entities.py`. `known_reachability.py` lists
`cockpit/crud/entities.py` among modules spelling `"connects_to"`
(`_location_doors_rows`, `:302-347`). Spans: `context.py`
`_npc_context_setting` 327-356, `_npc_context_company` 449-475,
`_mj_context_co_presents` 770-797 (none uses a `context.py` top-level name);
`link_author.py` `_location_chain_names` 147-161 (sole caller `_npc_sheet`),
`_npc_sheet` 164-184 (sole callers `:235-236`); `cockpit/play.py`
`_propose_engine_discovery` 964-997 (uses only `ProposedMutation` among
module names; imported by `play_physical.py:53`); `cockpit/crud/entities.py`
`_create_entity_core` 545-560, `_create_static_entity_core` 563-634 (72
lines), `update_entity` 739-816 (78 lines).
`src/world_engine/schema_reconcile.py:30` defines `static_table_names()`.
Consequence: B moves only the unpinned spans above; `crud/entities.py`
moves nothing and its two long functions gain one-line calls only.

## Contracts

(none — this brief produces and consumes no contract)

## Context

Four files that the lot must edit are within 3 to 44 lines of the
1000-line cap. This brief moves unpinned code out, byte for byte, before any
brief adds to them.

## Scope IN

1. New `src/world_engine/context_describe.py`: move `_npc_context_setting`,
   `_npc_context_company`, `_mj_context_co_presents` from `context.py`
   unchanged, with the imports they need and a module docstring naming
   TICKET-0091 BRIEF-B and "pure move". `context.py` imports the three
   names from `.context_describe`. `_npc_context_identity` and
   `_mj_context_location` stay in `context.py` (R-29).
2. New `src/world_engine/link_sheet.py`: move `_location_chain_names` and
   `_npc_sheet` from `link_author.py` unchanged; `link_author.py` imports
   `_npc_sheet` from `.link_sheet`.
3. New `src/world_engine/cockpit/play_discovery.py`: move
   `_propose_engine_discovery` from `cockpit/play.py` unchanged;
   `cockpit/play_physical.py:53` imports it from `.play_discovery`
   instead of `.play`. `play.py` no longer defines or re-exports it.
4. Proof: record `static_table_names()` before and after; they are equal.

## Scope OUT

- Any change of behaviour, name, signature or docstring content of a moved
  function.
- Moving `_npc_context_identity`, `_mj_context_location`,
  `_SAFE_SUBCULTURE_KEYS`, `_join_gathering`, or anything from
  `cockpit/crud/entities.py` (R-29).
- Every later brief.

## Invariants to defend

None threatened: a pure move. The secret-exclusion clauses inside the
moved functions travel verbatim.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A moved function is named by a check, the policy file or a string
  reference not listed in R-29.
- `static_table_names()` differs before and after.

ADAPT:
- A moved function needs a module-level constant of its origin file that
  another function there also uses: leave the constant in place and import
  it in the new module; report.

REPORT-ONLY:
- The new line counts of the four files.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `static_table_names()` identical before and after (pasted in the
      report).
- [ ] `context.py`, `link_author.py`, `cockpit/play.py` each below 930
      lines.
- [ ] Green: `module_budget.py`, `trait_reader.py`, `prompt_lean.py`,
      `stream_session_readonly.py`, `link_agent_strata.py`,
      `context_disclosure_floor.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

This step needs no doc update (pure move).
