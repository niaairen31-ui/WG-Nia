---
id: TICKET-0067
title: Two red guards on main — the N1 goal-read breach and the prompt-model fixture drift
type: bug
status: live-gate
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0067-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> B2 et j'exécuterai le ticket de bug (0067) en premier.

> G1

> Rédige le brief du ticket 0067

Decision block returned after RECON:

> A1, B1, C1

## Clarifications resolved (intake)

Surfaced by running `tooling/verify/checks/corpus_gate.py` (TICKET-0060,
BRIEF-0060-d) with every dependency installed, against `main` as fetched
2026-08-20. Two of the three failures it reports are genuine and belong
here; the third (`pipeline_state.py`) goes to TICKET-0061 by decision B2.

- **`npc_goal_read.py` is RED with 6 failures.** One locus is product code:
  `src/world_engine/observation_runner.py:129` selects `NpcGoal` inside
  `_precondition_failures`, outside the N1 allowlist. Four are check
  fixtures: `tooling/verify/checks/observation_runner.py:109,134,236,260`
  seed `NpcGoal` rows to build its test corpus.

- **The product read is a PRESENCE PROBE, not a content read.** It computes
  `{g.npc_id for g in ... status == "active"}` and uses it only to emit
  `"NPC {label} has no active goal"` as a run precondition. No
  `description`, `horizon` or any interiority field is touched. That is
  what makes A2 (simply allowlisting the runner) the wrong shape: an
  allowlist entry would license content reads the code does not currently
  perform and nothing would keep it that way.

- **The guard lapsed the same way `observation_surface.py` did.**
  `npc_goal_read.py` is linked by the Machine sections of TICKET-0013,
  -0014, -0015, -0020 and -0048. `TICKET-0051` and `TICKET-0053` — which
  authored `observation_runner.py` — link it **zero times** (measured), and
  `verify/run.py` runs only what a ticket names. Second instance of the
  pattern; the corpus gate is what made it visible.

- **`prompt_model_write.py` is RED, deterministically and independently of
  any machine.** Its fixture (`:98-106`) creates a `PromptTemplate` head
  with no `prompt_version` row. The PATCH under test summarises the row
  through `_prompt_row_summary` (`cockpit/crud/prompts.py:115`) →
  `prompt_store.current_prompt` (`prompt_store.py:32`), which raises by
  design on a versionless head. The check builds its own temp-file DB
  (`_fresh_engine()`, `:69-84`), so this is a fixture that never followed
  the prompt-versioning work — not an environment artifact and not a
  product defect.

- **`context.py` cannot host the accessor.** 979 lines against
  `module_budget.py`'s 1000-line cap, and
  `tooling/verify/baselines/module_budget.json` **does not exist** — the
  check treats a missing baseline as an empty exemption set and enforces
  the cap on every module, fail-closed. 21 lines of headroom is not a
  place to add a documented accessor inside a ticket whose purpose is
  returning guards to green.

- **`observation_reads.py` is the right layer and has the room.** 216 lines
  / 14 functions. It is already the observation domain's declared read
  module ("reads go through this one"), and its docstring already records
  its own governed relationship to an allowlist
  (`observation_socle.py`'s model-identifier rule). `observation_socle.py`
  rule 6 constrains the reverse direction only (no `Observation*` identifier
  in `context.py`/`tick*.py`), so nothing there is disturbed.

Decisions locked before any artifact was authored:

| Code | Decision |
|---|---|
| **A1** | The presence probe moves behind a **named read accessor** returning `set[str]` of NPC ids. `observation_runner.py` stops naming `NpcGoal` entirely. The return type is the structural guarantee: no caller can reach a goal's content, so the accessor cannot silently become a second content reader. The allowlist grows by one entry — a READ MODULE, definitionally a reader — never by a consumer. |
| **B1** | `tooling/verify/checks/observation_runner.py` is allowlisted by name, one entry, with the precedent already in place (`tooling/verify/checks/npc_goal_read.py` is itself allowlisted). Not a directory-wide rule (B2), not a narrowed scan scope (B3) — `tooling/` scanning is what would catch a real reader appearing in `tooling/glue/` or `tooling/pipeline_cockpit/`. |
| **C1** | The prompt fixture seeds its v1 row through `writes.prompts.write_prompt_version`, the sanctioned write path. Not a bare `Session.add(PromptVersion(...))`: `prompt_version.py`'s single-write-shape rule scans `src/` plus the migration and would not catch it in `tooling/` — exploiting a check's blind spot inside the ticket that returns checks to green is the wrong move regardless of whether it is detected. |
| **Gate linkage** | This ticket links `npc_goal_read.py` AND `prompt_model_write.py` in its own Machine-checkable section. The lapse that produced this ticket must not recur on the ticket repairing it. The corpus-wide fix (TICKET-0061, C1/C3) lands after this one. |

## Scope OUT

- **`pipeline_state.py`'s three failures** (TICKET-0036/-0048/-0062 inline
  comments on `status:`) — TICKET-0061, decision B2.
- **The corpus gate's environment contract** (C3) and linking the corpus
  gate as standing law (C1) — TICKET-0061.
- **`context.py`'s 979/1000 budget position.** Reported here, repaired
  nowhere: it is a pre-existing condition this ticket routes around rather
  than inherits. It deserves its own ticket.
- **The scan-scope asymmetry.** `npc_goal_read.py` scans `tooling/`;
  `prompt_version.py` (`_iter_py_files`) scans `src/` plus the migration
  only. Two checks, the same class of doctrine, opposite scopes. Report
  only.
- **The observation run precondition itself** (A3). Whether requiring an
  active goal to start a run is the right product rule is not reopened
  here; its behaviour is preserved byte-for-byte.
- **Frontend, schema, canon-write paths.** Untouched.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `NpcGoal` appears nowhere in `src/world_engine/observation_runner.py`
      — not in its imports, not in its body  -> verify/checks/npc_goal_read.py
- [ ] The allowlist grows by exactly two entries
      (`src/world_engine/observation_reads.py`,
      `tooling/verify/checks/observation_runner.py`) and the check exits 0,
      red-tested by removing each entry in turn  -> verify/checks/npc_goal_read.py
- [ ] The MJ boundary rule and the D1 dialogue-provenance rule are
      unchanged and still pass  -> verify/checks/npc_goal_read.py
- [ ] `prompt_model_write.py` exits 0 against its own fresh temp DB, on a
      tree with no `~/.world_engine/world_engine.db`  -> verify/checks/prompt_model_write.py
- [ ] `prompt_version.py` still exits 0 — no `PromptVersion` constructor
      reaches `Session.add` outside `write_prompt_version`  -> verify/checks/prompt_version.py
- [ ] `observation_runner.py`, `observation_socle.py`, `observation_metrics.py`
      and `json_ui_boundary.py` all still exit 0  -> verify/checks/observation_runner.py
- [ ] No import cycle is introduced  -> verify/checks/import_cycle.py
- [ ] Every touched module stays within 1000 lines and 40 functions  -> verify/checks/module_budget.py
- [ ] The new accessor is under 80 lines  -> verify/checks/function_length.py
- [ ] No unused import remains after `NpcGoal` leaves the runner  -> verify/checks/undefined_names.py

### Live  ->  human gate (Nia)

- [ ] An observation run started against a location with two NPCs both
      holding an active goal launches exactly as before.
- [ ] A run started against a location where one NPC has no active goal is
      refused with the same message text as before
      (`NPC {name} has no active goal`).
- [ ] The Prompts tab still saves a model on a template and still displays
      its version number.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended entry: why
  the presence probe became an accessor rather than an allowlist entry
  (the return type as the structural guarantee); the two allowlist
  additions and their distinct rationales; the second instance of the
  lapsed-guard pattern and its cross-reference to TICKET-0061's corpus
  gate; the two report-only findings (`context.py`'s budget position, the
  scan-scope asymmetry).
- `tooling/standards/DECISIONS_INDEX.md` — regenerated mechanically.
- `CLAUDE.md` — **no change.** Measured: it carries zero mentions of
  `npc_goal` or `NpcGoal`. The N1 doctrine lives in `npc_goal_read.py`'s
  docstring and in TICKET-0013. Do not add one; the file has one line of
  headroom against its 500-line cap.
- No schema changelog entry: `schema_version_touched: none`.

## Amendment (D1, escalated during BRIEF-0067-a commit 2, resolved by Nia)

Executing commit 2's `write_prompt_version` fixture fix let
`prompt_model_write.py`'s `main()` run to completion for the first time,
unmasking a second, independent, previously-invisible failure in the same
check file: `check_seed_model_free`'s `re.search(r"\bmodel\s*=", ...)`
matched three comments in `scripts/seed_pilot.py` (`:2206`, `:2227`,
`:2339`) documenting the `model=NULL (Q1)` invariant — not any actual
`model=` assignment. It was masked on `main` because
`check_write_path_and_list_route()` used to crash with an uncaught
`RuntimeError` before `main()` ever reached its `if FAILURES:` print
block. See `tooling/questions/QUESTION-TICKET-0067.md` for the full
escalation and Nia's decision (option A: repair now, as a separate third
commit).

Additional Machine-checkable criterion, landed by commit 3:

- [x] `check_seed_model_free` parses `scripts/seed_pilot.py`'s AST (never
      greps raw text) for a `model=` keyword argument on any
      `upsert_prompt_template(...)` call or a `.model =` attribute
      assignment, with a vacuous-proof guard (`seeded == 0` fails) —
      red-tested by injecting `model=` at one call site (FAIL naming that
      line) and by renaming `upsert_prompt_template` throughout (FAIL on
      the vacuous-proof guard), both reverted  ->
      verify/checks/prompt_model_write.py

## Escalations

### E-01 — archived — QUESTION-TICKET-0067.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0067.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0067
Trigger: D1-c
## Context
BRIEF-0067-a commit 2 wires `prompt_model_write.py`'s fixture to seed a v1
`prompt_version` row via `write_prompt_version` (Scope IN 2.1/2.2), exactly
as specified. That repair works: the versionless-head `RuntimeError` no
longer fires.

Fixing that crash lets `main()` (tooling/verify/checks/prompt_model_write.py:222)
run to completion for the first time, because `check_write_path_and_list_route()`
used to abort with an *uncaught* exception before `main()` ever reached its
`if FAILURES: print(...)` block. That masked whatever `check_seed_model_free()`
(lines 63-66) had already appended to the shared `FAILURES` list earlier in
the same run.

With the crash gone, that masked failure now prints:

```
FAIL: scripts/seed_pilot.py sets a `model=` value on a prompt_template row — S-null violated
```

It is a false positive. `check_seed_model_free`'s regex is `\bmodel\s*=`
applied to the whole file text (not AST-aware, no comment stripping). It
matches three comments documenting `model=NULL` (Q1) at
`scripts/seed_pilot.py:2206`, `:2227`, `:2339` — none of them assign
`model=` on any actual `PromptTemplate(...)` construction. Grepping the
file confirms these are the only three matches and all three are inside
`#` comments.

This is a second, independent, previously-invisible defect in the same
check file this brief already touches — not named anywhere in
TICKET-0067 or BRIEF-0067-a, and not something the mini-RECON could have
measured (it never ran far enough to surface it). The brief's own Hard
STOP condition 5 anticipates exactly this shape of discovery
("A different failure means a different defect... STOP and report; do
not proceed, do not work around") and I'm honoring it rather than
patching the regex as a drive-by.

Commit 1 (`npc_goal_read.py`) is done and committed
(`c5a76ac` on `ticket/0067`). Commit 2's `write_prompt_version` wiring is
staged in the working tree but not yet committed, pending this decision.

## Question
Should this brief's scope grow by one line item — repairing
`check_seed_model_free`'s false positive so `prompt_model_write.py` can
exit 0 as this ticket's acceptance criteria require — or should that
repair be deferred to its own ticket, leaving `prompt_model_write.py`
red for now (which would break this ticket's stated Done-means and
corpus_gate.py's expected "exactly one remaining failure" count)?

## Options
A. Fix `check_seed_model_free` now, inside BRIEF-0067-a commit 2 (same
   file the brief already touches): narrow the regex so it only matches
   a `model=` keyword argument/assignment in actual code — e.g. anchor
   it against a `PromptTemplate(` construction, or strip `#` comment
   text before scanning. Record it as a third, explicitly-named repair
   in the commit message and this ticket's Machine section, same
   discipline as the other two.
B. Defer to a new ticket (next id via `tooling/glue/next_id.py`). This
   brief's commit 2 lands only the `write_prompt_version` fix and
   accepts that `prompt_model_write.py` stays red until the new ticket
   lands — which means this ticket's own acceptance criteria and
   `corpus_gate.py`'s "exactly one remaining failure" bullet cannot be
   met as written; both would need amending.
C. Something else Nia specifies.

## Response
Decision: A — repair it here, as a THIRD commit, not folded into commit 2.

Your escalation is correct behavior and STOP condition 5 was the right call. The diagnosis is right too: it is a false positive, and the three matches at `scripts/seed_pilot.py:2206,:2227,:2339` are comments documenting the very invariant the rule enforces.

One correction to the options you proposed. Anchoring the regex against a `PromptTemplate(` construction would be a fail-open. Measured on this tree: `seed_pilot.py` contains zero literal `PromptTemplate(...)` constructions and 29 `upsert_prompt_template(...)` calls, whose signature is `(session, id, *, system_prompt, user_template, **head_fields)` — `**head_fields` is exactly the path a `model=` would take. That anchor would match nothing and pass forever. Stripping `#` comments is also rejected: it stays a grep over 3 257 lines holding 64 triple-quoted prompt bodies, so any future prompt text containing the characters `model=` re-trips it.

Parse it. Same discipline `legacy_mount.py` and `static_asset_freshness.py` state for their own AST reads. Replace `check_seed_model_free` (`tooling/verify/checks/prompt_model_write.py:63-66`) with exactly this, and add `import ast` to the module's import block (`re` stays — it is still used at `:59`):

```python
def check_seed_model_free() -> None:
    """S-null (Q1): the seed never sets a model on a prompt_template head.

    TICKET-0067 (D1). This rule was `re.search(r"\bmodel\s*=", seed_text)`
    over the whole file. `seed_pilot.py` is 3257 lines holding 64
    triple-quoted prompt bodies, and three comments (:2206, :2227, :2339)
    record the invariant in the words `model=NULL (Q1)` — so the comments
    documenting the rule tripped the rule. Parsed, never grepped.

    Anchoring on a `PromptTemplate(` construction was rejected: this file
    has ZERO of them and 29 `upsert_prompt_template(...)` calls, whose
    `**head_fields` is how a `model=` would actually arrive. That anchor
    would match nothing and pass forever.
    """
    try:
        tree = ast.parse(SEED.read_text(encoding="utf-8"), filename=str(SEED))
    except SyntaxError as exc:
        fail(f"{SEED}: SyntaxError: {exc}")
        return

    seeded = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "upsert_prompt_template":
                seeded += 1
            for kw in node.keywords:
                if kw.arg == "model":
                    fail(
                        f"scripts/seed_pilot.py:{node.lineno} passes a `model=` "
                        "keyword argument — S-null violated"
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "model":
                    fail(
                        f"scripts/seed_pilot.py:{node.lineno} assigns `.model` "
                        "— S-null violated"
                    )

    if seeded == 0:
        fail(
            "scripts/seed_pilot.py: zero upsert_prompt_template(...) calls "
            "parsed — the seeding shape changed and this scan proves nothing"
        )
```

The `seeded == 0` clause is the vacuous-proof guard: a rule that passes because it found nothing to inspect is the flaw this whole ticket exists to close.

Commit structure. Commit 2 lands the `write_prompt_version` wiring alone, as specified — commit it now. The S-null repair is commit 3, on its own. The brief protocol requires a conditional fix discovered during execution to take a separate commit, and the two defects deserve two records: "the fixture followed the versioning" and "the S-null rule stopped grepping comments" are different findings. `prompt_model_write.py` being red between commits 2 and 3 is not a regression — it was red before commit 1, and this ticket is what turns it green.

Two red-tests to run and record in commit 3's message:

1. Add `model="llama3.1:8b"` to any `upsert_prompt_template(...)` call → FAIL naming that line. Revert. (Verified: fires at the injected line.)
2. Rename `upsert_prompt_template` throughout `seed_pilot.py` → FAIL on the vacuous guard. Revert. (Verified.)

No change to the brief's Done means. With commit 3 landed, `corpus_gate.py` reports exactly one remaining failure — `pipeline_state.py` — as the brief already states. Verified end-to-end on a simulated tree.

TICKET-0067's Machine-checkable section and BRIEF-0067-a will receive an appended amendment recording this third repair. Appended, not rewritten — do not edit either artifact's existing text.
~~~~
