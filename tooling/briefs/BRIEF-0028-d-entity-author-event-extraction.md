<!-- slug: entity-author-event-extraction -->
# BRIEF-0028-d — `event_author.py` extraction + entity_author decomposition

Ticket: TICKET-0028 | Danger: none — behavior-preserving refactor of
authoring (draft-generation) paths; drafts are proposals, never canon |
Blast radius: medium | Depends on: BRIEF-0028-c merged (`main` @
post-c, verify green)

## Context

Decision H1 (locked): `entity_author.py` (1055 lines / 28 functions,
over the R5 line cap by 55) sheds its event/agenda authoring domain
into a new `event_author.py`, and its three baselined functions are
decomposed in place. In-place decomposition alone cannot close the gap
(the three baselined functions total 318 lines — decomposition moves
lines, it does not remove them); extraction follows the F1 gesture:
flat module, domain cut, orchestrators stay put.

Structural map (post-a `main`, re-verify at RECON):
`generate_event_draft` 118 (`entity_author.py:938-1055`),
`generate_agenda_draft` 77 (`entity_author.py:830-906`) — the event/
agenda domain sits contiguous at the tail of the module; the three
baselined functions are `generate_entity_draft` 119
(`entity_author.py:408-526`), `generate_event_draft` 118 (moves AND
decomposes), `generate_player_draft` 81 (`entity_author.py:608-688`).

Harness state (RECON): `scripts/harness_entity_author_replay.py`
covers `generate_entity_draft` and the region pipeline
(`generate_region_manifest` + `generate_region_draft`, transitively
`generate_entity_draft` + `generate_npc_goals`). It does NOT cover
`generate_event_draft`, `generate_agenda_draft`,
`generate_player_draft`, `generate_world_draft`,
`generate_skill_catalogue_draft`. Per the vacuous-proof rule, fixtures
extend BEFORE the refactor for every function this brief touches.

## Scope IN

1. **Helper inventory first (R7).** Enumerate, `file:line`, every
   private helper the event/agenda pair calls and every helper the
   three baselined functions call; classify each as moves-with-event-
   domain / stays / shared. A helper used by BOTH domains stays in
   `entity_author.py` and is imported by `event_author.py` (no
   duplication, no `_shared` module for a two-file split).

2. **Harness extension FIRST** (separate commit, before any move):
   - Add fixtures to `harness_entity_author_replay.py` covering
     `generate_event_draft`, `generate_agenda_draft`, and
     `generate_player_draft` (record against a REAL model on a DB
     copy, same mechanics as existing modes).
   - Manifest names every traversed function; replay refuses PASS if
     the manifest does not cover all of: entity, region pair,
     npc_goals, event, agenda, player.
   - Self-validate: replay PASS on pre-refactor `main`.

3. **Extraction.** Create `src/world_engine/event_author.py`: move
   `generate_event_draft`, `generate_agenda_draft`, and their
   event/agenda-only helpers (per item 1 inventory). Moved functions
   keep their names (R7); imports of the movers across `src/` are
   re-pointed (RECON census of importers in execution notes — expected:
   cockpit routes/creator or crud; enumerate, don't assume).

4. **Decomposition.** `generate_entity_draft`, `generate_event_draft`
   (now in `event_author.py`), `generate_player_draft` decomposed to
   <= 80-line functions along existing seams (prompt assembly / model
   call / parse via `llm_parse` / normalization / result shaping).
   NEW extractions take domain prefixes (`_entity_*` / `_event_*` /
   `_player_*`). Pure moves + mechanical parameter passing; prompts
   byte-identical, normalization semantics frozen.

5. **Baseline shrink.** Remove the three `entity_author.py` function
   entries and the `entity_author.py` module entry (both files must
   land within caps unbaselined). Residual after this brief: 19
   function entries, 0 module entries — `module_budget.json` is EMPTY
   (file deleted at -f, not here).

## Scope OUT

- The remaining 19 R1 entries (stage e), deletions (stage f).
- Any prompt change, draft-schema change, or normalization tightening;
  candidates logged.
- `generate_world_draft` / `generate_skill_catalogue_draft` /
  `generate_npc_goals` beyond zero edits (they stay, un-decomposed —
  none is baselined).
- `region_author.py` (its two baselined functions are stage e's).
- Harness fixture coverage for world/skill-catalogue drafts (not
  touched, not required — coverage follows the refactor, not
  completionism).

## Invariants to defend

- Model proposes, code judges: authoring modules produce drafts only;
  zero canon writes in either file (`single_canon_write.py` green,
  neither file is an allowed site).
- R2: all model-output parsing stays through `llm_parse`
  (`llm_parse_chokepoint.py` green, no new parse sites in
  `event_author.py`).
- Prompt-registry anchors: if any `PromptSpec.call_sites` names an
  entity_author function that moves, the anchor re-keys in the same
  commit under the relocation precedent, with fail-closed proof (RECON
  the registry before moving; do not assume the tick result
  generalizes).
- R3 logging preamble in the new module; zero `print()`; French
  interval labels are DATA.
- Full suite green; baselines strictly smaller; shrink-only.

## Done means

### Machine-checkable
- [ ] Extended harness self-validation: replay PASS pre-refactor with
      manifest covering entity, region pair, npc_goals, event, agenda,
      player.
- [ ] Replay PASS post-refactor: empty diff on draft outputs for all
      fixtures.
- [ ] `module_budget.py` green with an EMPTY baseline; both files
      within caps unbaselined.
- [ ] `function_length.py` green: three entries removed; every function
      in both files <= 80 lines.
- [ ] `llm_parse_chokepoint.py`, `single_canon_write.py`,
      `prompt_registry.py`, `no_print_in_src.py`,
      `undefined_names.py`, full suite green.
- [ ] Importer census recorded; zero import edits beyond the movers'
      re-points.

### Live gate (Nia)
- [ ] One entity draft, one event draft, one agenda draft, one player
      draft generated from the cockpit: indistinguishable from
      pre-refactor output shape and flow.

## Docs to update

- `TICKET-0028` front-matter: append `BRIEF-0028-d`.
- Nothing else; -f owns the doctrine edit.
