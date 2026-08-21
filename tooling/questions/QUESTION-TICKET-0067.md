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
