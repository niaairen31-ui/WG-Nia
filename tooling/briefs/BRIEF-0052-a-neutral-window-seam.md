# BRIEF-0052-a — Step "neutral window seam"

## Context

TICKET-0052, decision B1 + I2. `conversation_window.py` owns the played lane's sliding
window; the observed lane (TICKET-0051) has no window at all. Before the observed lane can
share it, the module must stop being conversation-shaped: its primitives operate on
`list[dict]` ollama messages and `_render_older_transcript` labels purely by `role`, with a
docstring that states the list "carries no per-NPC name". The observed lane has names and no
player. This step introduces a lane-neutral line form, moves the primitives onto it, and
leaves the played lane byte-identical. No observation code is touched here.

## Mini-RECON (report before changing anything)

Report findings with `file:line`. Do not fix anything found unless a Scope IN item covers it.

1. `tooling/verify/checks/summary_not_persisted.py` — confirm empirically whether it has a
   vacuous-proof guard. Specifically: if `MODULE` (line 17) points at a path that does not
   exist, does the check FAIL, or does it walk zero functions and print PASS? Run it against a
   deliberately wrong path in a scratch copy and report the observed verdict. Do not assert
   this parenthetically — run it.
2. Confirm the complete importer set of `conversation_window` across `src/`, `scripts/`, and
   `tooling/`. Report every `file:line`. The expected set is `cockpit/play.py:32`,
   `cockpit/crud/prompts.py:19`, `scripts/measure_conversation_window.py:54`,
   `tooling/verify/checks/prompt_registry.py:39`,
   `tooling/verify/checks/summary_not_persisted.py:17`, plus the `call_sites` string at
   `src/world_engine/prompt_registry.py:264`. Report any importer NOT in that list.
3. Report the current line and function counts of `conversation_window.py` (210 lines at
   RECON) against the 40/1000 budget, so the post-change figure can be compared.

If (1) shows the check is NOT vacuous-proof, Scope IN item 6 applies. If it already is,
report that and skip item 6, stating so explicitly.

## Scope IN

1. **Rename the module.** `git mv src/world_engine/conversation_window.py
   src/world_engine/context_window.py`. The rename is a separate commit from the content
   changes, so the diff of item 2 is readable.

2. **Introduce the neutral line form.** In `context_window.py`, above the primitives:

   ```python
   @dataclass(frozen=True)
   class TurnLine:
       """One line of prior scene, lane-neutral (TICKET-0052, I2).

       `role`   -- the ollama role the played lane needs when rebuilding a
                   message list ("user" | "assistant").
       `label`  -- the LITERAL prefix used when rendering this line into a
                   summarization transcript, separator included: "[Joueur]",
                   "[PNJ]", or an NPC name followed by " :". Carrying the
                   separator inside the label is what lets both lanes render
                   byte-identically through one function.
       `content`-- the line text.
       """

       role: str
       label: str
       content: str
   ```

3. **Move the primitives onto `TurnLine`.** Replace the three `list[dict]` primitives with
   neutral equivalents, keeping their semantics exactly:
   - `line_word_count(lines: list[TurnLine]) -> int` — whitespace-split word count over
     `content`. Replaces `history_word_count`.
   - `split_verbatim_tail(lines: list[TurnLine], k: int) -> tuple[list[TurnLine], list[TurnLine]]`
     — unchanged logic, new element type.
   - `render_transcript(lines: list[TurnLine]) -> str` — `"\n".join(f"{ln.label} {ln.content}")`.
     Replaces `_render_older_transcript`, and is now public (the observed lane needs it).
   - `summarize_older_lines(older: list[TurnLine], world_id, db) -> str` — the current
     `summarize_older_turns` body with `render_transcript(older)` substituted in. Keep the
     fail-soft `OllamaError` swallow and the `_log.warning` verbatim; keep `_load_summary_template`
     and `format_summary_note` unchanged.

4. **Adapt the played lane inside `context_window.py`, not in `play.py`.** Add two private
   converters and keep both public played-lane entry points' signatures unchanged:

   ```python
   _PLAYED_LABELS = {"user": "[Joueur]", "assistant": "[PNJ]"}

   def _played_to_lines(npc_history: list[dict]) -> list[TurnLine]: ...
   def _lines_to_played(lines: list[TurnLine]) -> list[dict]: ...
   ```

   `_played_to_lines` maps each message to `TurnLine(role=m["role"],
   label=_PLAYED_LABELS.get(m.get("role"), "[PNJ]"), content=m.get("content", ""))`;
   `_lines_to_played` returns `{"role": ln.role, "content": ln.content}`. The round trip must
   preserve role and content exactly — the `label` is derived, never read back.

   `build_npc_message_list` and `resolve_npc_message_list` keep their exact current
   signatures (`npc_history: list[dict]`, same keyword names, same return type) and convert
   internally. `cockpit/play.py:578` must need NO change beyond the import line.

5. **Update every anchor found in mini-RECON (2).** `cockpit/play.py:32`,
   `cockpit/crud/prompts.py:19`, `scripts/measure_conversation_window.py:54`,
   `tooling/verify/checks/prompt_registry.py:39` (WIRED_FILES),
   `tooling/verify/checks/summary_not_persisted.py:17` (MODULE), and the `call_sites` tuple at
   `src/world_engine/prompt_registry.py:264` (`"src/world_engine/context_window.py:_load_summary_template"`).
   Plus any importer mini-RECON reported outside the expected set.

6. **Conditional, only if mini-RECON (1) shows the check is not vacuous-proof.** Add to
   `summary_not_persisted.py`, before any AST walk:

   ```python
   if not MODULE.exists():
       FAILURES.append(f"vacuous-proof: MODULE not found at {MODULE}")
   ```

   and a guard that fails if zero functions were walked. Red-test it by pointing `MODULE` at a
   nonexistent path and confirming a FAIL verdict. **Separate commit**, message prefixed
   `fix(verify):`. If mini-RECON (1) shows it is already vacuous-proof, do nothing and say so.

7. **Module docstring.** Update the header of `context_window.py`: it is now the shared window
   seam for both the played and observed lanes (TICKET-0052, B1/I2), still read + compute only
   (C1 — the summary is ephemeral, never persisted). Keep the existing sentence about
   `DEFAULT_WORD_BUDGET` / `DEFAULT_VERBATIM_TURNS` / `DEFAULT_SUMMARY_ENABLED` agreeing with
   `models/config.py` and `scripts/migrate_v1_89_conversation_window_config.py`.

## Scope OUT

- **Any observation code.** No `observation_*` module is opened in this brief. The observed
  lane's adapter is BRIEF-0052-b.
- **Renaming the table or the config functions.** `conversation_window_config`,
  `load_conversation_window_config`, and `upsert_conversation_window_config` keep their names
  (C1 — a table rename is a migration with no reader). Do not "finish the rename".
- **Changing any default value.** `word_budget=1200`, `verbatim_turns=6`,
  `summary_enabled=True` are untouched. E1 stands: no composite trigger, no lane-specific
  budget, no `OR beats > K`.
- **Touching `repeat_last_n` / `repeat_penalty`** (`ollama_client.py:30`). That is
  D-0052-repetition, a separate workstream fed by F1's measurement. Do not "improve" it here,
  even if the beat-8 hypothesis looks obviously right.
- **Changing the played lane's prompt shape or message order.** `[system, summary note,
  *verbatim_K, scene tail]` (H1 of TICKET-0050) is unchanged.
- **`context.py`.** `assemble_scene_tail` is reused as-is in BRIEF-0052-b. `context.py` is at
  979 lines against a 1000 hard cap; adding to it triggers an extraction ticket. Do not.
- **Deleting `scripts/measure_conversation_window.py`** or rewriting it beyond the import
  path.

## Invariants to defend

- **Single canon-write authority.** This module writes nothing. `summary_not_persisted.py`
  is the structural guarantee that the summary stays an ephemeral prompt artifact; the rename
  must not orphan it — which is precisely why item 6 exists.
- **No structure without a reader.** `TurnLine` ships with two readers in this brief (the
  played converters) and a third in -b. `role` is read by `_lines_to_played`; `label` is read
  by `render_transcript`. If either field ends up unread, say so rather than shipping it.
- **Fail-closed over advisory.** A verify check anchored on a path that no longer exists must
  fail, never pass quietly. That is the whole of item 6.

## Done means

- [ ] Mini-RECON findings (1)-(3) reported with `file:line`, including the OBSERVED verdict of
      the wrong-path run in (1), not an assertion about it.
- [ ] `src/world_engine/conversation_window.py` does not exist; `context_window.py` does.
- [ ] `grep -rn "conversation_window" src/ scripts/ tooling/` returns only
      `conversation_window_config` / `load_conversation_window_config` /
      `upsert_conversation_window_config` occurrences — no bare module reference remains.
- [ ] `python -m tooling.verify.run` is green, including `prompt_registry` and
      `summary_not_persisted`.
- [ ] If item 6 applied: `summary_not_persisted.py` red-tested — pointing `MODULE` at a
      nonexistent path produces a FAIL, and the verdict text is pasted into the report.
- [ ] Live: a played conversation runs normally. Below budget, the NPC answers as before.
      Above budget (either a long conversation or `word_budget` temporarily lowered on the
      prompts surface and restored after), the summary note appears and the NPC still answers.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `CLAUDE.md`: one line — the sliding window lives in `context_window.py` and is shared by
  the played and observed lanes; it is read + compute only.
- No schema changelog entry (no schema change).
- `ARCHITECTURE_DECISIONS.md`: nothing yet. The section lands in BRIEF-0052-c, once the
  observed lane actually consumes the seam.
