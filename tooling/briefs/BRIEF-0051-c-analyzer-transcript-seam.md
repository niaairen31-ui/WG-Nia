# BRIEF — Step "analyzer transcript seam"

## Context

TICKET-0051 decision R1. An observed run must produce the SAME proposals a
played scene would, judged by the SAME code — otherwise step 3 measures a copy
of the game rather than the game.

RECON established that is impossible today. Both entry points are bound to
`conversation` by signature and by internals:

- `analyze_window(conversation_id, db, ...)` — `analyzer.py:894`. Loads the
  `Conversation` (`:918`), reads `ConversationMessage` rows via
  `_window_unanalyzed_rows` (`:762`), and advances `conv.last_analyzed_turn`
  (`:937`).
- `analyze_overhearing(player_line, npc_line, conversation_id, db, ...)` —
  `analyzer.py:679`. `_overhearing_eligible_receivers` (`:443-456`) derives
  receivers from `conv.gathering_id` and `conv.player_id`.

There is no transcript-shaped seam to adapt to. This brief creates one.

**This is a hot canon-adjacent path.** Commit before starting. This brief lands
alone, with a full-tree verify after. It is a pure refactor: no behaviour
changes for played scenes, and no observation code is written here.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate rather than adapting the design.

1. **Conversation-bound reads in the window path.** For each of
   `_window_unanalyzed_rows` (`:762`), `_window_build_transcript` (`:777`),
   `_window_injected_context_str` (`:785`), `_window_call_model` (`:797`),
   `_window_covered_keys` (`:833`), `_window_build_mutations` (`:853`): report
   every field of `Conversation` it touches and every table it queries.
   This determines exactly where the seam falls.
2. **Same for the overhearing path** — `_overhearing_eligible_receivers`
   (`:443`), `_overhearing_subject_set` (`:459`), `_overhearing_classify`
   (`:470`), `_overhearing_parse_classifications` (`:495`),
   `_overhearing_existing_keys` (`:514`), `_overhearing_mutation_for_receiver`
   (`:545`), `_overhearing_build_mutations` (`:622`).
3. **`last_analyzed_turn` semantics** — every reader and writer of the marker
   across `src/`. The seam must NOT move the marker; it stays a
   conversation-only concern.
4. **`proposed_by` vocabulary** — every value written anywhere in `src/`, and
   whether the column is nullable.
5. **Module budget** — line and function counts for `analyzer.py`
   (941/1000 and 33/40 at RECON time) BEFORE and projected AFTER extraction.
   Report the projected figure before writing; if the extraction would leave
   `analyzer.py` still above either cap, STOP and escalate.
6. **Import-cycle risk** — what `analyzer.py` currently imports, and whether a
   new sibling module can be imported by it without a cycle.
7. **Existing callers** of `analyze_window` and `analyze_overhearing` across
   `src/` — every one must keep compiling unchanged.

## Scope IN

### 1. New module `src/world_engine/analyzer_transcript.py`

R7 domain-prefixed. Holds the conversation-agnostic core.

Two public functions:

```python
def analyze_transcript(
    transcript: str,
    world_id: str,
    injected_context: str,
    covered_keys: set,
    db: Session,
    model: str = ...,
    host: str = ...,
) -> list[ProposedMutation]:
    """Judge an ordered transcript and return UN-PERSISTED proposals."""
```

```python
def analyze_overheard_lines(
    speaker_line: str,
    listener_line: str,
    receiver_ids: set[str],
    world_id: str,
    existing_keys: tuple[set, set],
    db: Session,
    model: str = ...,
    host: str = ...,
) -> list[ProposedMutation]:
    """Bystander knowledge pass over an EXPLICIT receiver set."""
```

Both return un-persisted objects. **Neither commits, neither writes any
marker.** Persistence and marker advancement stay with the caller — that is
the whole point of the seam, and it keeps the single-canon-write posture
unchanged.

Move into this module the helpers the mini-RECON reports as
conversation-agnostic (expected: `_window_build_transcript`,
`_window_call_model`, `_window_build_mutations`, `_overhearing_classify`,
`_overhearing_parse_classifications`, `_overhearing_mutation_for_receiver`,
`_overhearing_build_mutations`). Anything the mini-RECON finds to be
conversation-bound STAYS in `analyzer.py` — do not force a move by threading a
`Conversation` through the new module.

### 2. `analyzer.py` becomes a thin conversation-bound wrapper

`analyze_window` keeps its exact signature and behaviour. It now:
resolves the conversation, gathers the unanalyzed rows, builds the transcript
and covered keys, calls `analyze_transcript`, then persists, advances
`conv.last_analyzed_turn`, and commits — exactly as today.

`analyze_overhearing` keeps its exact signature and behaviour. It computes the
receiver set from `conv.gathering_id` / `conv.player_id` as today, then calls
`analyze_overheard_lines` with that set.

**Public behaviour must be byte-identical.** Same proposals, same
`proposed_by` values, same failure modes (parse failure returns `[]` WITHOUT
advancing the marker; overhearing failures never surface to the player).

### 3. Docstring on the new module, verbatim

```
"""Conversation-agnostic analysis core (TICKET-0051, BRIEF-0051-c).

Extracted from analyzer.py so that a played scene and an OBSERVED scene are
judged by the same code. The caller supplies the transcript and the receiver
set; this module never resolves a Conversation, never reads
ConversationMessage, never advances last_analyzed_turn, and never commits.
It returns un-persisted ProposedMutation objects.

Rationale for the seam: an observed run writes no conversation rows at all
(TICKET-0051 decision A3), so it cannot pass a conversation_id. Duplicating
the judge instead would let the observed path and the played path drift, and
observation exists precisely to draw conclusions about the played path.
"""
```

### 4. Verify check `tooling/verify/checks/analyzer_seam.py`

- **Rule 1** (AST): `analyzer_transcript.py` contains no reference to
  `Conversation`, `ConversationMessage`, `conversation_id`, `player_id`,
  `gathering_id`, or `last_analyzed_turn`. The seam is enforced, not
  documented.
- **Rule 2** (AST): `analyzer_transcript.py` contains no `db.commit()` and no
  `session.commit()`.
- **Rule 3** (AST): `analyze_window` and `analyze_overhearing` still exist in
  `analyzer.py` with unchanged parameter names and defaults.
- **Rule 4**: `analyzer.py` and `analyzer_transcript.py` are each within
  40 functions / 1000 lines.
- **Rule 5, vacuous-proof guard**: if the AST walk collected zero functions
  from either module, FAIL.

### 5. Behavioural regression evidence

Before the change, on the test DB (`WORLD_ENGINE_ENV`, `seed_test.py`), run
`analyze_window` on a seeded conversation and capture the resulting proposals.
After the change, repeat and diff. Record the comparison in the step result.
A refactor of the canon-proposal path is not "done" on a green check alone.

## Scope OUT

- **Any observation code.** No `observation_*` import, no runner, no beat.
  This module ships with its only caller being `analyzer.py` itself. The
  observed caller arrives in BRIEF-0051-e.
- **Any change to proposal semantics.** Same mutation types, same anti-inflation
  rubric, same `proposed_by` values, same monotone knowledge ladder. If the
  refactor tempts a "small improvement", it is out of scope — report it.
- **`last_analyzed_turn`.** Stays in `analyzer.py`. The new module must not
  know it exists.
- **The single-canon-write policy.** No new write path; the new module writes
  nothing at all.
- **Prompt templates.** `pt-conversation-analysis` and the overhearing
  template are untouched.
- **`context.py`** (BRIEF-0051-b) and the socle (BRIEF-0051-a): no dependency
  either way.

## Invariants to defend

- **Model extracts, code judges.** Unchanged and unweakened: the seam moves
  where the judge is called from, never who judges.
- **Single canon-write authority.** `proposed_mutation` remains the sole gate
  for AI-proposed changes. The new module produces un-persisted objects only.
- **No structure without a reader.** The new module's reader is `analyzer.py`
  from day one; BRIEF-0051-e adds the second.
- **R5 / R7.** New module is domain-prefixed and both modules end under cap.
  The projected count is reported BEFORE writing (mini-RECON item 5).
- **History is sacred.** No behaviour change to what gets proposed or applied.

## Done means

- [ ] Mini-RECON item 5 reported the projected post-extraction line counts
      before any code was written, and both land under 1000 / 40.
- [ ] `python tooling/verify/checks/analyzer_seam.py` exits 0 with non-zero
      collected-function counts.
- [ ] The before/after `analyze_window` proposal diff on the test DB is empty,
      and the diff is recorded in the step result.
- [ ] `grep -rn "conversation" src/world_engine/analyzer_transcript.py`
      returns nothing (case-insensitive).
- [ ] Every existing caller of `analyze_window` / `analyze_overhearing`
      compiles unchanged; `grep` output for those callers is recorded.
- [ ] A live played turn still produces proposals in the Review Queue.
- [ ] Full-tree verify passes, including `import_cycle` and `module_budget`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: subsection under the TICKET-0051 section recording
R1 — the RECON evidence that the conversation binding was structural, why a
duplicate judge was rejected, and the rule that the seam returns un-persisted
objects and never commits. `DECISIONS_INDEX.md` entry.
`tooling/standards/code_standards.md` unchanged. `world-engine-schema.md`
unchanged (no schema change). `CLAUDE.md` unchanged.
