# BRIEF — Step "N1 goal-read accessor + prompt-model fixture repair"

Ticket: TICKET-0067 · Brief: BRIEF-0067-a · Branch: `ticket/0067`

## Context

`corpus_gate.py` (landed by TICKET-0060) exposed three checks red on `main`
that no ticket's Machine section ever executed. Two of them are this brief:
`npc_goal_read.py` (6 failures) and `prompt_model_write.py` (1 failure). The
third, `pipeline_state.py`, belongs to TICKET-0061 and is Scope OUT here.

This brief must land and merge **before TICKET-0061 opens**: 0061's own gate
links `corpus_gate.py`, which cannot pass while these two are red.

Two commits, both isolated, in this order. Neither leaves a gate red between
them.

---

## Mini-RECON — anchors as measured on `main`, 2026-08-20

Every anchor below is a tree-specific claim. **Verify each one locally before
editing.** If any has drifted, STOP and report rather than adapting silently.

| Anchor | Measured |
|---|---|
| `src/world_engine/observation_runner.py:37` | `NpcGoal,` inside the `from .models import (...)` block |
| `src/world_engine/observation_runner.py:126-131` | the `goal_npc_ids = { ... }` set comprehension selecting `NpcGoal` |
| `src/world_engine/observation_runner.py` | 680 lines, 26 functions; does **not** import `observation_reads` |
| `src/world_engine/observation_reads.py` | 216 lines, 14 functions; imports only `.models` (no cycle risk) |
| `src/world_engine/context.py` | **979 / 1000 lines** — do not put the accessor here |
| `tooling/verify/baselines/module_budget.json` | **does not exist**; the cap applies to every module, fail-closed |
| `tooling/verify/checks/npc_goal_read.py:35-56` | `ALLOWED_MODULES` set literal |
| `tooling/verify/checks/npc_goal_read.py:86` | scan scope = `src/**` + `scripts/**` + `tooling/**` |
| `tooling/verify/checks/observation_runner.py:109,134,236,260` | `NpcGoal` import + fixture constructions |
| `tooling/verify/checks/prompt_model_write.py:69-84` | `_fresh_engine()` — purges every `world_engine.*` from `sys.modules`, then re-imports |
| `tooling/verify/checks/prompt_model_write.py:90-96` | the local import block, executed **after** `_fresh_engine()` |
| `tooling/verify/checks/prompt_model_write.py:98-106` | the fixture: head created, `last_updated_at` captured |
| `src/world_engine/writes/prompts.py:44-95` | `write_prompt_version(db, *, template_id, system_prompt, user_template, note=None)` — `db.add(version)`, bumps `head.updated_at`, `db.add(head)`, **returns without committing** |
| `src/world_engine/prompt_store.py:32` | `current_prompt` raises `RuntimeError` on a versionless head, by design |

### Hard STOP conditions

STOP and report; do not proceed, do not work around:

1. **`observation_runner.py` reads any `NpcGoal` field other than
   `npc_id`/`status`** anywhere in the file. The whole design rests on the
   read being a presence probe. If it is not, this brief is wrong.
2. **A second `NpcGoal` reader exists** in `src/` outside
   `npc_goal_read.py`'s allowlist that this brief has not named. The check
   reports every locus; if the failure list differs from the six recorded
   in TICKET-0067, the tree has drifted.
3. **`context.py` has crossed 1000 lines**, or `module_budget.json` now
   exists. Either changes the budget reasoning that placed the accessor.
4. **`write_prompt_version` commits internally** on the live tree (it does
   not, as measured — `writes/prompts.py:95` returns after `db.add(head)`).
   If it does, the fixture's commit sequence below is wrong.
5. **`prompt_model_write.py`'s failure is anything other than the
   versionless-head `RuntimeError`.** A different failure means a different
   defect.
6. Any check outside the ones this brief names goes from green to red.

---

## Scope IN

### Commit 1 — `npc_goal_read.py` back to green

Both halves land together: commit 1 must leave the check green, not
half-green.

**1.1 — Add the accessor to `src/world_engine/observation_reads.py`.**

Placed with the other raw-ORM accessors (after `list_mutation_links`, before
the dict-builder section). Verbatim, including the docstring — the docstring
is the structural record of why this function exists and must not be
paraphrased:

```python
def npc_ids_with_active_goal(npc_ids: list[str], db: Session) -> set[str]:
    """Which of `npc_ids` currently hold at least one active goal.

    A PRESENCE PROBE, never a content read. The return type is the
    guarantee: a set of NPC ids, so no caller can reach a goal's
    description, horizon or note. `npc_goal` is NPC interiority (N1,
    TICKET-0013) and its CONTENT is read only by
    `context.assemble_npc_context` and the initiative vote. The
    observation runner needs one boolean per NPC — "does this NPC have
    something to act on?" — and nothing else. This accessor is what keeps
    that need from becoming a second reader of the table: an allowlist
    entry for the runner itself would have licensed content reads the
    code does not perform, with nothing to keep it that way.

    Empty `npc_ids` returns an empty set without querying.
    """
    if not npc_ids:
        return set()
    return {
        g.npc_id
        for g in db.exec(
            select(NpcGoal).where(NpcGoal.npc_id.in_(npc_ids), NpcGoal.status == "active")
        ).all()
    }
```

`NpcGoal` joins this module's existing `from .models import (...)` block, in
alphabetical position.

**1.2 — Amend `observation_reads.py`'s module docstring.**

Its opening line currently reads "Read helpers for observation_* tables".
That contract is now widened by one function and must say so — a module
whose stated scope silently stops matching its contents is the same drift
class this ticket repairs. Append a paragraph to the existing docstring
(do not rewrite what is there):

```
`npc_ids_with_active_goal` is the one accessor here that reads OUTSIDE the
observation_* family: `npc_goal`, and only as a presence probe. It lives
here rather than in `context.py` because the observation run precondition
is an observation-domain read, and because this module — not its callers —
is what `npc_goal_read.py`'s allowlist names. See its own docstring for the
N1 reasoning.
```

**1.3 — Rewrite the call site in `src/world_engine/observation_runner.py`.**

- Delete `NpcGoal,` from the `from .models import (...)` block (`:37`).
- Add `from .observation_reads import npc_ids_with_active_goal` in import
  order among the other `.observation_*` imports.
- Replace the set comprehension (`:126-131`) with exactly:

```python
        goal_npc_ids = npc_ids_with_active_goal(npc_ids, db)
```

Nothing else in `_precondition_failures` changes. The failure message text
(`f"NPC {label} has no active goal"`), the ordering of the failure list and
the `if npc_ids:` guard are preserved byte-for-byte — a live gate checks
that message.

Confirm `select` is still used elsewhere in the module before assuming the
import stays (it is, in `_present_npc_ids`), and run `undefined_names.py`.

**1.4 — Two entries in `npc_goal_read.py`'s `ALLOWED_MODULES`.**

Added with their own comments, in the style of the existing entries.
Verbatim:

```python
    # TICKET-0067 (A1). NOT the observation runner: the runner needs a
    # boolean per NPC for a run precondition, and reaching that need
    # through a named accessor here — returning set[str], never NpcGoal
    # rows — keeps the consumer structurally unable to read goal content.
    # The allowlist grows by a READ MODULE, definitionally a reader, never
    # by a consumer.
    "src/world_engine/observation_reads.py",
    # TICKET-0067 (B1). A check fixture, not a reader: this file seeds
    # NpcGoal rows to build its own test corpus. Allowlisted by name, one
    # entry, on the precedent of npc_goal_read.py's own entry above — not
    # as a directory-wide rule, and NOT by narrowing the tooling/ scan,
    # which is what would catch a real reader appearing in tooling/glue/
    # or tooling/pipeline_cockpit/.
    "tooling/verify/checks/observation_runner.py",
```

**1.5 — Red-test each entry.** Remove
`"src/world_engine/observation_reads.py"`, observe FAIL naming that file,
revert. Repeat for the second entry. Record both verdicts in the commit
message.

### Commit 2 — `prompt_model_write.py` back to green

**2.1 — Import the sanctioned write path in the LOCAL import block.**

`_fresh_engine()` deletes every `world_engine.*` module from `sys.modules`
before re-importing, so this import must sit with the other local imports at
`:90-96`, **after** the `_fresh_engine()` call — never at module top level:

```python
    from world_engine.writes.prompts import write_prompt_version
```

**2.2 — Seed the v1 version, then capture `last_updated_at`.**

Inside the existing `with Session(engine) as session:` block, between
`row_id = row.id` and the `last_updated_at` capture. The ordering is
load-bearing: `write_prompt_version` bumps `head.updated_at`, and every
later assertion in this check compares against `last_updated_at`. Capturing
it before the version write would make those assertions pass on the version
write's own bump instead of the PATCH's.

```python
        # TICKET-0067 (C1). A versionless head is structurally impossible
        # post-migration — prompt_store.current_prompt raises on one, by
        # design — and the PATCH under test summarises the row through it
        # (cockpit/crud/prompts.py:115). Seeded through the sanctioned
        # write path, never a bare Session.add(PromptVersion(...)):
        # prompt_version.py's single-write-shape rule scans src/ plus the
        # migration and would not catch the shortcut here, which is a
        # reason to avoid it, not a licence to use it.
        write_prompt_version(
            session,
            template_id=row_id,
            system_prompt="s",
            user_template="u",
        )
        session.commit()
        session.refresh(row)
        last_updated_at = row.updated_at
```

`write_prompt_version` does not commit (measured, `writes/prompts.py:95`);
the explicit `session.commit()` above is required. The head's declared
`prompt_variable` rows are empty and neither `"s"` nor `"u"` contains a
`{identifier}` placeholder, so C1 validation passes without declaring any
variable — do not add one.

**2.3 — Red-test.** Delete the `write_prompt_version(...)` call, observe the
versionless-head `RuntimeError`, revert. Record the verdict.

---

## Scope OUT

Everything below was discussed during planning. Finding any of it is REPORT
ONLY.

- **`pipeline_state.py`'s three failures** (TICKET-0036/-0048/-0062 carry
  inline comments on their `status:` field). TICKET-0061, decision B2. Do
  not repair them here, not even as a drive-by.
- **The corpus gate itself.** Its environment contract and its linkage as
  standing law are TICKET-0061 (C1/C3). Do not modify `corpus_gate.py`.
- **`context.py`'s 979/1000 budget position.** Report only. Do not split,
  trim or reflow it.
- **The scan-scope asymmetry** between `npc_goal_read.py` (scans `tooling/`)
  and `prompt_version.py` (does not). Report only.
- **The observation run precondition itself.** Whether requiring an active
  goal to start a run is the right rule is not reopened. Behaviour is
  preserved exactly.
- **`npc_goal_read.py`'s duplicate reporting.** Line 129 yields two
  identical failure lines because the rule reports per AST node. Cosmetic,
  report only — do not deduplicate.
- **`observation_reads.py`'s other accessors.** No refactor, no
  reorganisation, no docstring rewrite beyond the appended paragraph in 1.2.
- **Frontend, schema, canon-write paths, mutation gating.** Untouched. If
  any step appears to need one, that is an escalation.

---

## Invariants to defend

- **N1 — `npc_goal` is NPC interiority.** Its CONTENT is read only by
  `assemble_npc_context` and the initiative vote. This brief adds a reader
  of the table's EXISTENCE, and the `set[str]` return type is what makes
  that distinction structural instead of a promise. If the accessor ever
  needs to return rows, that is a doctrine change and a new ticket.
- **Allowlists grow by relocation, not by broadening.**
  `npc_goal_read.py`'s two historical additions were both relocations, and
  its comments say so twice. This brief's two additions are a read module
  and a check fixture — neither is a new consumer. Keep the comments that
  say why.
- **Fail-closed guards never lapse.** Every check this brief touches ends
  stricter or identical, never more tolerant. No rule is deleted, no scan
  narrowed, no vacuous pass introduced.
- **The sanctioned write path is the only write path**, whether or not a
  check happens to scan the file doing the writing.
- **History is sacred.** `ARCHITECTURE_DECISIONS.md` gets one appended
  entry. Nothing existing is edited.

---

## Done means

- [ ] `python tooling/verify/checks/npc_goal_read.py` exits 0.
- [ ] `grep -n "NpcGoal" src/world_engine/observation_runner.py` returns
      nothing.
- [ ] `ALLOWED_MODULES` contains exactly two new entries, each carrying its
      comment.
- [ ] Both red-tests recorded in the commit message: removing each new
      allowlist entry produces a FAIL naming that file; both reverted.
- [ ] `python tooling/verify/checks/prompt_model_write.py` exits 0 on a tree
      with no `~/.world_engine/world_engine.db`.
- [ ] Red-test recorded: deleting the `write_prompt_version(...)` call
      reproduces the versionless-head `RuntimeError`; reverted.
- [ ] `prompt_version.py`, `observation_runner.py`, `observation_socle.py`,
      `observation_metrics.py`, `json_ui_boundary.py`, `import_cycle.py`,
      `module_budget.py`, `function_length.py` and `undefined_names.py` all
      exit 0.
- [ ] `python tooling/verify/checks/corpus_gate.py` reports exactly ONE
      remaining failure — `pipeline_state.py` — and no others. Anything else
      is a regression this brief introduced.
- [ ] Two commits on `ticket/0067`, in the order above, each green on its
      own.
- [ ] `/review-step` and `/close-step` run.

---

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended entry
  covering: the presence-probe-vs-content-read distinction and why the
  return type carries it; the two allowlist additions and their distinct
  rationales (read module / check fixture); the second instance of the
  lapsed-guard pattern, cross-referenced to TICKET-0061's corpus gate
  rather than restated; the two report-only findings.
- `tooling/standards/DECISIONS_INDEX.md` — regenerated mechanically.
- `CLAUDE.md` — **no change.** It carries zero mentions of `npc_goal` or
  `NpcGoal` (measured). The N1 doctrine lives in `npc_goal_read.py`'s
  docstring and TICKET-0013. Adding a line would spend the file's last
  line of headroom against its 500-line cap.
- No schema changelog entry.

---

## Amendment — Commit 3 (D1, escalated, Nia's decision recorded in
QUESTION-TICKET-0067.md)

Commit 2 as specified (Scope IN 2.1/2.2) is correct and landed unchanged.
Running it revealed that `check_seed_model_free`
(`tooling/verify/checks/prompt_model_write.py:63-66`) had an independent,
previously-masked false positive: `re.search(r"\bmodel\s*=", seed_text)`
over the whole file matched three comments in `scripts/seed_pilot.py`
(`:2206`, `:2227`, `:2339`) documenting the `model=NULL (Q1)` invariant,
not any actual assignment. Masked on `main` by
`check_write_path_and_list_route()`'s uncaught `RuntimeError`, which
aborted `main()` before its `if FAILURES:` print block — commit 2's own
fix is what let this surface.

**Commit 3 — `check_seed_model_free` parses, never greps.**

Replaces the function body with an `ast.walk` over `scripts/seed_pilot.py`:
fails on a `model=` keyword argument to any `upsert_prompt_template(...)`
call, or a `.model =` attribute assignment; also fails if zero
`upsert_prompt_template(...)` calls are found (`seeded == 0` — a
vacuous-proof guard, so a shape change in the seeding code can never make
this rule pass by finding nothing to inspect). `import ast` added; `re`
stays (still used by `check_no_second_resolver` at `:59`).

Rejected anchors (measured on this tree): a `PromptTemplate(` construction
— zero exist, 29 `upsert_prompt_template(...)` calls exist instead, whose
`**head_fields` is the actual path a `model=` would take, so that anchor
would match nothing and pass forever. Stripping `#` comments before
scanning — still a raw-text scan over 3257 lines holding 64 triple-quoted
prompt bodies, re-tripped by any future prompt text containing the
characters `model=`.

Red-tests (both reverted after verifying):
- `model="llama3.1:8b"` injected into the `pt-npc-dialogue`
  `upsert_prompt_template(...)` call (`scripts/seed_pilot.py:1743`) ->
  FAIL naming that exact line.
- `upsert_prompt_template` renamed throughout `seed_pilot.py` -> FAIL on
  the vacuous-proof guard.

`prompt_model_write.py` is red between commits 2 and 3 — not a
regression; it was red before commit 1, and commit 3 is what turns it
green.
