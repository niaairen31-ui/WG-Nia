# BRIEF 0089-C — "Dissolve a gathering where it is emptied"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/gathering.py:260-282` -> `close_open_memberships(entity_id,
  db)` sets `left_at = now` on every open row, returns `list(active_rows)`,
  and its docstring states "Does not commit; the caller owns the
  transaction." It contains no `Gathering` write.
- `src/world_engine/gathering.py:285-356` -> `migrate_npc` closes via
  `close_open_memberships`, collects `source_gathering_ids = {row.gathering_id
  for row in active_rows}`, inserts the new member row, commits at `:327`,
  then runs the auto-dissolve loop at `:329-355` and commits at `:356`. The
  loop skips `source_id == target_gathering_id`, requires
  `remaining is None`, requires `source_g.status == "open"`, runs
  `analyze_window(conv.id, db)` on each open conversation inside
  `try/except (Exception, SystemExit)` with
  `_log.exception("analyze_window failed for conversation %s", conv.id)`, then
  sets `status = "dissolved"` and `dissolved_at = now`.
- `migrate_npc` is 72 physical lines against an 80-line cap.
- `src/world_engine/gathering.py:359-401` -> `enter_location` runs its own
  dissolve loop, passing `model=model, host=host` to `analyze_window`.
- `src/world_engine/gathering.py` is 401 lines against a 1000-line cap.
- `analyze_window`'s signature is
  `analyze_window(conversation_id, db, model=ollama_client.DEFAULT_MODEL, host=ollama_client.OLLAMA_HOST)`.
- `tooling/verify/canon_write_policy.txt`'s `[CANON_TABLES]` list contains
  neither `gathering` nor `gathering_member`.

## Facts carried

**R-06 — `close_open_memberships` closes rows and dissolves nothing.** It sets
`left_at = now` on every open row for the entity, never deletes, does not
commit ("the caller owns the transaction"), and contains no `Gathering` write
of any kind. Consequence: every caller of it can leave an open gathering with
zero active members. This is the production defect.

**R-07 — `migrate_npc` carries the auto-dissolve, after its own commit.**
After `db.commit()` at `:327`, it iterates the source gathering ids, skips
`target_gathering_id`, and for each source with no remaining active member:
runs `analyze_window` on every open conversation of that gathering
(`:342-352`, each call wrapped in `try/except (Exception, SystemExit)`), then
sets `status='dissolved'` and `dissolved_at=now`, then commits at `:356`.

**R-25 — `analyze_window` is a no-op without a model call when nothing is
new.** It loads the conversation, calls `_window_unanalyzed_rows`, and returns
`[]` before any model call, marker change or commit when that is empty.

**R-20 — gathering rows are outside the canon-write policy.** The canon table
list names 38 tables and includes neither `gathering` nor `gathering_member`;
line 145 of the policy file states, of another pair of tables, "not durable
world canon -- same posture as gathering/conversation". Consequence: this
brief adds no `[ALLOWED_SITES]` entry and trips no `single_canon_write.py`
rule.

**R-26 — `_perform_travel` moves the player and leaves NPC gatherings alone.**
It closes the player's open conversations, closes the player's own open
`gathering_member` rows, and writes `char.current_location_id`; its comment
states that NPC members are untouched and that `enter_location`'s
dissolve-before-create handles the location when it is next entered.

## Contracts

**C-02 — `dissolve_emptied`**
Produced by: BRIEF-0089-c   Consumed by: BRIEF-0089-c, BRIEF-0089-d, BRIEF-0089-g
Declared in: `src/world_engine/gathering.py`.
Signature: `dissolve_emptied(gathering_ids: Iterable[str], db: Session, model: str = ollama_client.DEFAULT_MODEL, host: str = ollama_client.OLLAMA_HOST) -> list[str]`
Behaviour: for each distinct id, if the gathering exists, has
`status == 'open'`, and has no `GatheringMember` row with `left_at IS NULL`:
run `analyze_window` on each of its open conversations, each call wrapped in
`try/except (Exception, SystemExit)` with `_log.exception`; then set
`status='dissolved'` and `dissolved_at=now`. Commits once at the end.
Return shape: the list of ids actually dissolved, in input order.
Error and empty cases: an empty or exhausted iterable commits and returns
`[]`. An unknown id, a dissolved gathering and a gathering still holding an
active member are each skipped without error. Never raises.

## Context

An NPC moved by the creator has its membership closed and nothing else
happens: the gathering it leaves keeps `status='open'` with zero active
members. That shell is what freezes the location for the rest of the session.
Brief A makes the entry guard ignore shells; this brief stops them being
created. The behaviour already exists, correctly, inside `migrate_npc` -- it
is extracted here so every path that empties a gathering ends it the same way.

## Scope IN

1. In `src/world_engine/gathering.py`, add `dissolve_emptied` implementing
   `C-02`. Place it immediately after `close_open_memberships` and before
   `migrate_npc`. Import `Iterable` from `typing` (the module already imports
   `Any` from there).
2. Build its body from `migrate_npc:329-355`, preserving every predicate and
   every message: the `remaining is None` test, the
   `source_g is not None and source_g.status == "open"` test, the open
   conversation select, the `try/except (Exception, SystemExit)` around
   `analyze_window`, and the exact `_log.exception` format string. Pass
   `model=model, host=host` to `analyze_window`, which is behaviour-identical
   to `migrate_npc`'s bare call because those are `analyze_window`'s own
   defaults, and which lets `enter_location`'s callers keep their override.
3. De-duplicate the ids while preserving input order, so that a caller passing
   the same id twice analyses its conversations once.
4. Commit once at the end, unconditionally, matching `migrate_npc:356`.
5. Give it a docstring stating: a gathering left with no active member is a
   shell -- it stays `open`, it is joinable, and it blocks the entry guard
   from regenerating the location's partition -- so every path that closes
   memberships ends by calling this. Say that it commits, and why (it runs
   after its caller's commit, unlike `close_open_memberships`, which runs
   inside it).
6. Replace `migrate_npc:329-355` with a single call:
   `dissolve_emptied(source_gathering_ids - {target_gathering_id}, db)`, and
   delete the now-duplicated `db.commit()` at `:356` in favour of the one
   inside `dissolve_emptied`. `migrate_npc`'s docstring keeps its
   "Auto-dissolve:" invariant line; extend it to name the helper.

## Scope OUT

- `enter_location`'s own dissolve loop (`:383-399`). It dissolves every open
  gathering at a location whether or not it is empty -- a different rule, and
  the one the "dissolve-before-create lives in the caller" invariant names.
  Do not refactor it to use `dissolve_emptied`.
- Calling `dissolve_emptied` from inside `close_open_memberships`. It was
  considered and rejected: `analyze_window` commits, and calling it from
  inside the creator CRUD's open transaction would commit a half-applied
  sheet edit. The callers call it after their own commit.
- Wiring the creator CRUD call sites. That is brief D, and it depends on
  brief B's line budget.
- `mutations.py`'s `_mutation_apply_npc_move`, which calls
  `close_open_memberships` on the tick path. It is a REPORT-ONLY observation
  here; changing it is not in this lot.
- Closing member rows when `enter_location` dissolves (R-08). Recorded, not
  repaired.
- Every other brief in this lot: A, B, D, E, F, G.

## Invariants to defend

- **Per-NPC uniqueness:** each present NPC belongs to exactly ONE open
  gathering. `migrate_npc`'s behaviour after this extraction must be
  bit-identical: same rows closed, same row inserted, same gatherings
  dissolved, same skip of the target.
- **Dissolve-before-create lives in the caller (`enter_location`), never
  inside `generate_gatherings`.** This brief adds a second, narrower dissolve
  verb; it must not move either dissolve into `generate_gatherings`.
- **History is sacred.** Dissolving sets `status` and `dissolved_at`; it
  deletes no row, and it does not touch `gathering_member.left_at`.

## Decision rights

STOP:
- `migrate_npc`'s dissolve block differs from the anchor in any predicate.
  The extraction would then not be behaviour-preserving and the contract must
  be amended before it is written.
- `close_open_memberships` has acquired a commit.

ADAPT:
- `migrate_npc` exceeds 80 lines after the edit (it should shrink by about
  20): if it somehow grows, extract the idempotent guard into a helper in the
  same module rather than shortening the docstring, and report.
- `Iterable` is already imported: use the existing import and report.

REPORT-ONLY:
- Every other caller of `close_open_memberships` you find, with its file and
  line, and whether it commits afterwards.
- `enter_location` dissolving without closing member rows.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `dissolve_emptied` exists in `gathering.py` with the `C-02` signature.
- [ ] `grep -n 'status = "dissolved"' src/world_engine/gathering.py` returns
      exactly two hits: one inside `dissolve_emptied`, one inside
      `enter_location`. None inside `migrate_npc`.
- [ ] Against a scratch carrier (`WORLD_ENGINE_DATABASE_URL` pointed at a
      throwaway SQLite file, never `~/.world_engine/`): two NPCs in two
      gatherings at one location; `migrate_npc(npc_a, gathering_b)` leaves
      gathering A with `status='dissolved'` and a non-null `dissolved_at`,
      and gathering B holding both NPCs with one open member row each -- the
      same result as before the change.
- [ ] Same carrier: `dissolve_emptied([], db)` returns `[]`;
      `dissolve_emptied(["no-such-id"], db)` returns `[]`;
      `dissolve_emptied([id_of_a_gathering_with_one_active_member], db)`
      returns `[]` and leaves it `open`.
- [ ] `migrate_npc` is at most 72 physical lines.
- [ ] `python tooling/verify/checks/module_budget.py` passes.
- [ ] `python tooling/verify/checks/function_length.py` passes.
- [ ] `python tooling/verify/checks/single_canon_write.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes.
- [ ] `/review-step` then `/close-step`.

## Docs to update

None here. The lifecycle change is recorded once, by brief G, in
`ARCHITECTURE_DECISIONS.md` and in the CLAUDE.md invariant -- after briefs C
and D have both landed, so the registry describes the whole verb set rather
than half of it.
