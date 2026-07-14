<!-- slug: apply-mutation-decomposition -->
# BRIEF-0027-c — Decompose `_apply_mutation` into per-type appliers

Ticket: TICKET-0027 | Danger: touches the AI canon-write path (pure move,
no write-logic change intended) | Blast radius: medium | Depends on:
PR #32 merged; own branch `ticket/0027-c`

## Context

`cockpit/app.py:1470` `_apply_mutation` is 682 lines: one body dispatching
~12+ mutation types (`relation_change`, `new_knowledge`, `status_change`,
`item_update`, `knowledge_change`, `goal_change`, `npc_move`,
`event_creation`, `resource_change`, `agenda_step_change`,
`agenda_creation`, `agenda_delegation`, ... — enumerate exhaustively at
execution). It is a sanctioned canon-write site named by
`single_canon_write.py` / `canon_write_policy.txt`. Unlike `say`, applying
a stored proposal involves **no model call**, so behavior capture is fully
deterministic.

## Scope IN

1. **Inventory (R7).** List every mutation type branch and every
   `writes.py` helper it calls, `file:line`, in the execution notes,
   before moving anything.

2. **Harness: `scripts/harness_mutation_apply.py`** (disposable, deleted
   at stage g; sibling of `harness_say_replay.py`, DB-copy discipline
   identical — never the live DB). Record mode: on a DB copy, apply one
   stored (or synthesized-and-inserted) proposal per mutation type;
   capture per-type before/after row dumps of touched tables, volatile
   fields normalized. Replay mode: fresh copy, re-apply the same
   proposals, diff write-sets against fixtures. Record on pre-refactor
   branch point; replay must PASS pre- and post-refactor. Include one
   deliberately failing proposal to fixture the SAVEPOINT all-or-nothing
   rollback (post-failure row dump identical to pre-apply dump).

3. **Decomposition.** New domain module
   `src/world_engine/cockpit/mutations.py`: one
   `_mutation_apply_<type>()` per branch, each <= 80 lines (R1), shared
   pre/post logic in `_mutation_*` helpers. `_apply_mutation` remains in
   `app.py` for now as a thin dispatcher <= 80 lines (route move is
   stage d). Pure moves: no write reordering, no validation change, no
   new write path — every DB write still flows through the same
   `writes.py` helpers.

4. **Governance relocation.** Update `single_canon_write.py` sanctioned
   sites and `canon_write_policy.txt` to name the new locations. This is
   an entry *relocation*, never a broadening: the closed list must end
   with the same number of sanctioned write paths (dispatcher +
   appliers replacing the single site counts as the relocated
   `_apply_mutation` path, documented as such in the policy file).

5. **Baseline shrink.** Remove `_apply_mutation` (682) from
   `baselines/function_length.json`; shrink `app.py`'s
   `module_budget.json` entry to new measured values; `mutations.py`
   fits R5 caps with no baseline entry (split by sub-domain if not).

## Scope OUT

- Route split (stage d), `llm_parse.py` (stage e), logging (stage f).
- Any change to `writes.py` or to proposal *generation*.
- Any fix or behavior improvement found en route: log as candidate
  ticket in execution notes.

## Invariants to defend

- Single canon-write path: closed list relocated, not extended;
  `single_canon_write.py` green with zero unsanctioned writers.
- All-or-nothing SAVEPOINT semantics per proposal, proven by the failing
  fixture.
- History append-only; no destructive mutation introduced.
- Full verify suite green; baselines strictly smaller.

## Done means

### Machine-checkable
- [ ] Harness replay PASS pre-refactor (self-validation) and
      post-refactor: empty write-set diff for every mutation type, and
      the failing-proposal fixture shows zero residual writes.
- [ ] `function_length.py` green, `_apply_mutation` debaselined; every
      function in `mutations.py` <= 80 lines.
- [ ] `module_budget.py` green; `single_canon_write.py` green with the
      relocated closed list; full suite green.

### Live gate (Nia)
- [ ] Approve three representative proposals live (`relation_change`,
      `new_knowledge`, `npc_move`): applied state visible in the cockpit
      as before.
- [ ] One deliberately invalid proposal rejects cleanly, nothing
      partially written.

## Docs to update

- `canon_write_policy.txt` (relocated entries, Scope IN 4). No schema
  docs, no decision record (procedure-preserving move).
