# BRIEF — Step "Completion effects: relation_delta, ledger_transfer, role_change" (TICKET-0024, BRIEF-0024-c)

## Context

With the schema (0024-a) and the prerequisite judge (0024-b) live,
completion still has no mechanical footprint. This brief makes the
completion carry its consequences: `goal_change complete` and
`agenda_step_change complete` accept an optional `effects[]` list from a
closed three-type vocabulary, validated and applied atomically in the same
SAVEPOINT by the existing writers. It also lands the two named doctrine
events: the H1 strip (first sanctioned partial application) and K1/L2
(declared roles as closed AI vocabulary, declare-and-occupy).

## Scope IN

1. **Effects contract (shared)** — closed vocabulary, applies to
   `goal_change` (action `complete` only) and `agenda_step_change`
   (action `complete` only; NEVER `fail`, NEVER `abandon`):
   - `relation_delta`: `{"type":"relation_delta", "target_entity_id",
     "value": int, "relation_type": str}` — `value` nonzero,
     `-10 <= value <= 10`. Subject entity is FORCED (see item 3). Applies
     via `write_relation(mode="delta")` (existing clamp 1–100 stands).
   - `ledger_transfer`: `{"type":"ledger_transfer", "from_entity_id",
     "to_entity_id", "amount": int > 0, "reason": str}` — balance guard
     on the payer, exact BRIEF-19 idiom:
     `get_balance(db, from) - amount < 0 -> reject "insufficient balance"`.
     Applies as TWO `write_ledger_entry` calls (debit payer / credit
     payee, mutual `counterparty_id`), both `source_type="tick"` (M1 —
     new documented enum value).
   - `role_change`: `{"type":"role_change", "faction_id", "role": str,
     "declare": bool (optional, default false)}` — subject NPC FORCED
     (item 3). Validation order at APPLY time (canon may have moved since
     the tick): (i) subject has an ACTIVE membership in `faction_id`,
     else reject `role_change: NPC is not an active member of {faction}`
     (I1 — different faction is the same reject); (ii) resolve `role`
     against `faction.role_capacities` keys, exact case-insensitive
     (gathering precedent). Found -> capacity check: count ACTIVE
     memberships in this faction whose true `role` casefold-equals the
     declared key (NEVER `cover_role`); count >= limit -> reject
     `role_change: role {role} is full ({count}/{limit})` — reject, never
     evict. Not found AND `declare` is true -> L2 declare-and-occupy: add
     the key to `role_capacities` with limit `null` via
     `write_faction_role_capacities` (dict REASSIGNMENT), same SAVEPOINT
     as the occupation — a role is never created without a holder. Not
     found and no `declare` -> reject
     `role_change: role {role} is not declared for {faction}` (K1).
     Occupation = `write_membership(mode="close")` on the current row +
     `mode="open"` with the new `role`, preserving `faction_id`,
     `is_primary`, `is_secret`, `cover_role` from the closed row.
     Amend `write_membership`'s docstring: modes are no longer
     "creator CRUD only" — `_apply_mutation`'s `role_change` effect
     (BRIEF-0024-c) is the second sanctioned caller.
2. **Cardinality & atomicity**: `effects` absent or `[]` is legal (A1);
   `len(effects) > 3` -> whole reject
   `too many effects ({n} > 3)` (N1). Any invalid effect -> whole-mutation
   reject (the existing never-raises contract: writers' ValueError caught
   and returned as string; the caller's SAVEPOINT rolls everything back,
   0020 precedent). The ONE exception is item 4 (H1 strip).
3. **Forced subjects (O1/H1 forcing precedent)** — never read from the
   payload: for `goal_change`, the subject is the goal's `npc_id`; for
   `agenda_step_change`, the subject is the agenda's `owner_entity_id`.
   `role_change` is valid ONLY when the subject is a character: on a
   faction-owned agenda step, a `role_change` effect -> whole reject
   `role_change: subject of a faction-owned agenda is not a character`.
   `relation_delta` and `ledger_transfer` are subject-agnostic enough to
   work for faction owners as-is (factions are entities).
4. **H1 strip (bounded partial application)** — in the `goal_change
   complete` branch only, AFTER the 0024-b prerequisite judge has passed:
   remove from `effects` every `relation_delta` whose
   {subject, target_entity_id} pair (either direction) equals the pair of
   a SATISFIED `relation_gte` prerequisite of the same goal. Each strip
   appends `stripped: relation_delta on prerequisite pair {name}` to the
   mutation's notes AND to the goal's `change_history` completion entry.
   Everything else in the mutation applies. Verbatim comment to place at
   the strip site:
   `# H1 (TICKET-0024): the ONLY sanctioned partial application of a`
   `# mutation. Scope: relation_delta on a satisfied relation_gte pair,`
   `# nothing else. Any other invalid element remains a whole reject.`
5. **`no_footprint` tag (A1)**: a `complete` that had no prerequisites and
   applies zero effects (absent, empty, or fully stripped) appends
   `"no_footprint": true` to the completion's `change_history` entry
   (goal) / step's `change_history` entry (agenda step). Cockpit renders
   a small "prose" badge on such history entries.
6. **Tick normalization** (`tick.py`, both `_normalize_tick_item` branches
   and the faction-scope `_normalize_scope_event` `agenda_step_change`
   branch): accept optional `effects` list; resolve names -> ids in code
   (model never emits ids): `target`/`from`/`to`/`counterparty` names
   against a world roster index (alive/active characters + active
   factions, `casefold` exact — the 0022-b `build_world_roster`
   precedent), `faction` name against active factions. Unresolved name or
   malformed effect -> DROP the single effect with a note at normalize
   time (pre-canon, cheap); the completion survives — apply-time (item 2)
   stays whole-reject because canon is at stake there. Cap enforcement
   (N1) at normalize time too: keep the first 3, note the excess.
7. **Prompt directive** — `scripts/apply_ticket_0024_prompt_updates.py`
   via `write_prompt_version` (never touching text in place), extending
   the `world_tick` template's mutation rubric: when proposing a
   completion, the model MAY attach up to 3 effects; vocabulary and
   payload shapes with names-not-ids; one French example per type; state
   that purely narrative completions need no effects. Keep it lean —
   shapes and one line of guidance, no tier tables.
8. **Verify checks** (`tooling/verify/checks/`): `effects_vocab.py`,
   `role_closed_vocab.py`, `effects_ledger_source.py`,
   `h1_strip_bounded.py` (static: the strip branch exists only inside the
   goal_change complete path), `schema_0024.py` shared with -a.

## Scope OUT

- NO `membership_change` (join/leave a faction as an effect) — I1
  deferral, the adhesion must pre-exist via creator CRUD.
- NO effect types beyond the three (no `knowledge_grant`, no
  `item_transfer`, no `event_creation` as effect) — B1, second concrete
  case rule.
- NO effects on `fail`/`abandon`; NO agenda-LEVEL effects when the last
  step auto-completes the agenda (effects attach to the step only).
- NO role uniqueness beyond capacity counting; NO eviction/vacancy system
  (C2-full deferred).
- NO creator-set limits at declare time (L2: newborn roles are always
  unlimited; limits are Nia's, via the 0024-a editor).
- NO conversation-analyzer path for effects: the analyzer's `goal_change`
  aliases stay as they are; effects arrive from the TICK paths only in
  v1. (The apply branch will still validate effects if present regardless
  of origin — the gate is shared — but no analyzer prompt solicits them.)
- Do not touch the H2 direction: no whole-reject on double-count; H1
  strip is the locked decision.

## Invariants to defend

- **All-or-nothing / SAVEPOINT (0020)**: threatened by design — H1 is a
  named exception, strictly scoped (item 4 verbatim comment +
  ARCHITECTURE_DECISIONS full record). Everything else stays whole.
- **Model proposes, code judges / no structural IDs from the model**:
  normalization resolves every name; forced subjects; closed vocabularies
  (effect types, declared roles).
- **History is sacred**: role change = close+reopen (never in-place);
  ledger stays pure-insert; strips and `no_footprint` are recorded, not
  silent.
- **JSON reassignment rule**: `role_capacities` update on declare.
- **Exclusion is structural**: capacity counting and role resolution read
  true `role` but NOTHING here injects true roles into any prompt —
  prompt-facing surfaces keep routing through `read_public_memberships`
  (`cover_role ?? role`). The effects rubric never lists existing roles.

## Done means

- [ ] Tick-proposed `goal_change complete` with `relation_delta` +5 toward a named NPC: on approval, relation intensity rises 5 (clamped), `change_history` snapshot present
- [ ] `ledger_transfer` 30 from an NPC with balance 20 -> Needs attention, `insufficient balance`; nothing written (goal still active)
- [ ] Valid `ledger_transfer` -> two ledger rows, mutual counterparties, both `source_type='tick'`
- [ ] `role_change` to "Conseiller" with capacity 6 and 6 active holders -> reject `is full (6/6)`
- [ ] `role_change` with `declare:true` to a new role -> faction editor shows the role with empty limit; NPC's old membership row closed, new row holds the role; both in one approval
- [ ] `role_change` naming a faction the NPC is not in -> reject `not an active member`
- [ ] Goal with satisfied `relation_gte` prerequisite + a `relation_delta` on the same pair + a valid `ledger_transfer`: delta stripped (note visible), transfer applied, goal completed
- [ ] 4 effects at normalize time -> 3 kept, note on the excess
- [ ] Completion with no effects -> applies, history entry tagged `no_footprint`, badge visible
- [ ] `agenda_step_change complete` on a faction-owned agenda with `relation_delta` faction->faction applies; with `role_change` -> reject `subject ... is not a character`
- [ ] All new verify checks green; `/review-step` and `/close-step` pass

**Live deployment sequence (danger_class: db_write + prompt):**
backup -> no migration (columns shipped in -a) -> no seed changes ->
`scripts/apply_ticket_0024_prompt_updates.py`.

## Docs to update

- `world-engine-schema.md`: `ledger.source_type` enum gains `tick`;
  `role_capacities` DORMANT note flips to "read by `_apply_mutation`
  role_change effect (BRIEF-0024-c)"; changelog vX.YY.
- `ARCHITECTURE_DECISIONS.md`: full record "H1 strip — first sanctioned
  partial application of a mutation: exact scope, why (anti-double-count
  on prerequisite pairs), and the rule that any widening of partial
  application requires its own decision record". Second record: "K1/L2 —
  declared roles are a closed AI vocabulary; declare-and-occupy is
  atomic; a role never exists without a holder."
- `CLAUDE.md`: one line under standing conventions: "Completion effects
  (TICKET-0024): closed vocabulary, forced subjects, H1 strip is the only
  partial application."
