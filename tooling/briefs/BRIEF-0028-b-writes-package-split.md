<!-- slug: writes-package-split -->
# BRIEF-0028-b — `writes/` package split by canon domain

Ticket: TICKET-0028 | Danger: none as intent — but this brief relocates
EVERY sanctioned canon-write path keyed to `writes.py` (22 closed-list
sites); highest-care brief of the ticket | Blast radius: large |
Depends on: BRIEF-0028-a merged (`main` @ post-a, verify green)

## Context

Decision B1 (locked): `writes.py` (1607 lines / 32 functions,
`baselines/module_budget.json`) converts to a `writes/` package split by
canon domain. RECON arithmetic made the split non-optional: ~440 of its
lines sit in the four baselined functions (`write_faction_role` 144 @
`writes.py:635`, `write_relation` 111 @ `writes.py:236`,
`write_knowledge` 91 @ `writes.py:374`, `delete_world_cascade` 94 @
`writes.py:1496`); in-place decomposition moves lines without removing
them, and I2 forbids re-baselining.

The import surface is small and fully enumerable (RECON, post-a `main`):
`analyzer.py` (`knowledge_level_rank`), `tick_context.py`
(`_find_relation_pair`), `entity_author.py` (`KNOWLEDGE_LEVELS`), and
`cockpit/mutations.py` (16-name import block). A `writes/__init__.py`
re-export freezes all four verbatim.

Two verify artifacts anchor `writes.py` and must be re-keyed under the
relocation-not-broadening precedent (0027-c/-d): the 22 `[ALLOWED_SITES]`
entries in `canon_write_policy.txt`, and `prompt_version.py`'s file
anchor set (`checks/prompt_version.py:47` region lists `writes.py` among
its scanned files — the prompt-write functions move with it).

## Scope IN

1. **Helper inventory first (R7).** Enumerate in execution notes, with
   `file:line`, every helper each domain group calls, inside and outside
   `writes.py`. Helpers used by ONE domain move WITH that domain; only
   genuinely cross-domain helpers enter `_shared.py`.

2. **Package layout** (moved functions keep their names — R7; only NEW
   extractions carved from the four baselined functions take `_write_*`
   or domain-local prefixes):
   - `writes/_shared.py` — closed set, mirrored on `crud/_shared.py`:
     `_clamp` (`writes.py:171`), `_append_history_snapshot`
     (`writes.py:175`). Nothing else enters without a brief.
   - `writes/relations.py` — `write_relation` (decomposed), `_find_relation_pair`.
   - `writes/knowledge.py` — `write_knowledge` (decomposed),
     `_append_knowledge_history`, `knowledge_level_rank`,
     `cap_knowledge_level`, `KNOWLEDGE_LEVELS`.
   - `writes/characters.py` — `write_character_location`,
     `write_skill_tier`, `write_ledger_entry`.
   - `writes/factions.py` — `write_membership`, `write_faction_role`
     (decomposed), `_validate_max_holders`.
   - `writes/config.py` — the governed-config trio: `write_npc_prices`,
     `write_location_subculture`, `write_world_laws`.
   - `writes/goals_agendas.py` — `write_npc_goal`,
     `write_npc_goal_status`, `write_npc_goal_prerequisites`,
     `write_agenda`, `write_agenda_step`, `write_agenda_step_status`,
     `write_agenda_status`, `write_goal_agenda_link`,
     `detach_goal_agenda_link`.
   - `writes/events.py` — `write_event`, `write_event_update`.
   - `writes/prompts.py` — `write_prompt_version`,
     `write_prompt_variables` (non-canon; moved for module hygiene, not
     policy).
   - `writes/worlds.py` — `delete_world_cascade` (decomposed).
   - `writes/__init__.py` — re-exports the ENTIRE former public surface;
     the four importers' import statements are untouched, byte for byte.
   Executor liberty, bounded: two adjacent domain modules may be merged
   if one would land under ~60 lines (R6 anti-fragmentation), recorded
   in execution notes; no module may exceed R5 caps unbaselined.

3. **Decompose the four baselined functions** into <= 80-line functions
   along existing seams. Pure moves + mechanical parameter-passing;
   history-append semantics, SAVEPOINT usage, and validation order are
   frozen.

4. **Policy re-keying.** All 22 `writes.py::fn` entries in
   `canon_write_policy.txt` re-key to `writes/<domain>.py::fn`, with a
   dated comment block mirroring the 0027-c/-d wording: same relocated
   paths, same count of sanctioned canon-write paths, not a broadening.
   NEW extractions inside the sanctioned functions must not introduce
   new direct canon-write sites: the ORM write statements stay inside
   the listed functions (extract pure computation, not writes) — OR, if
   a write statement must move into an extraction, that extraction is
   added to the closed list in the same commit and the count delta is
   justified line-by-line in the PR description (escalation to Nia if
   the count grows).

5. **Check re-anchor.** `checks/prompt_version.py` scanned-file set:
   `writes.py` -> `writes/prompts.py`. Assertions verbatim, anchor only;
   recorded fail-closed proof (temporarily plant a violating
   `PROMPT_VERSION` string in `writes/prompts.py`, observe FAIL, remove).

6. **Baseline shrink.** Remove the four `writes.py` function entries and
   the `writes.py` module entry. Residual after this brief: 22 function
   entries, 2 module entries.

## Scope OUT

- `models.py` (stage c), `entity_author.py` (stage d), remaining R1
  residual (stage e), deletions (stage f).
- Any change to write semantics, validation rules, history snapshots, or
  the five ungoverned config tables' governance status.
- Any change to `cockpit/mutations.py` beyond zero (its import block is
  frozen by the `__init__` re-export).
- No new canon-write capability, no closed-list broadening.

## Invariants to defend

- Sanctioned canon-write path count UNCHANGED (`single_canon_write.py`
  green; policy-file diff shows pure re-keying).
- History is sacred: every `_append_history_snapshot` /
  `_append_knowledge_history` call site survives the move verbatim.
- All-or-nothing atomicity: SAVEPOINT structure in the movers untouched.
- Import surface frozen: the four importers' statements byte-identical.
- R3: new modules use the logging preamble; zero `print()`.
- Full suite green; baselines strictly smaller; shrink-only respected.

## Done means

### Machine-checkable
- [ ] `harness_mutation_apply.py` replay PASS post-split (its manifest
      covers `write_relation`, `write_knowledge`, `write_faction_role`
      via the mutation appliers — verify the manifest actually names
      them; if not, extend fixtures FIRST, per the vacuous-proof rule).
- [ ] `delete_world_cascade` deterministic proof (model-free): scripted
      world-delete against a DB copy, before/after per-table row-count
      diff identical pre- and post-refactor, recorded in execution notes.
- [ ] `single_canon_write.py` green; policy diff = pure re-key + dated
      comment; site count unchanged (or escalated).
- [ ] `prompt_version.py` re-anchored with recorded fail-closed proof.
- [ ] `module_budget.py` green: `writes.py` entry removed; every
      `writes/` module within caps unbaselined.
- [ ] `function_length.py` green: four entries removed; every function
      in `writes/` <= 80 lines.
- [ ] `undefined_names.py`, `no_print_in_src.py`, full suite green.

### Live gate (Nia)
- [ ] One mutation approval of each relocated applier-reachable kind
      (relation, knowledge, faction_role) from the cockpit queue:
      identical behavior, history rows appended as before.
- [ ] One world deletion on a throwaway world: full cascade, no orphans.

## Docs to update

- `canon_write_policy.txt` (the re-keying IS the doc).
- `TICKET-0028` front-matter: append `BRIEF-0028-b` to `brief_ids`.
- Nothing in `code_standards.md` (R5's `writes/` tripwire paragraph
  already describes this split prospectively; the closure edit is -f's).
