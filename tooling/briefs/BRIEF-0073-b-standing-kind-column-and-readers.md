# BRIEF — Step "npc_goal.kind, the standing render, and the four readers"

TICKET-0073, brief -b. Depends on BRIEF-0073-a being merged (line budget).

## Context

NPC dialogue drifts toward intrigue because every `npc_goal` row is a volition
aimed at changing a state. There is no representation of what an NPC simply
does — its trade, its pastime, the thing that explains its presence somewhere.

This step adds `npc_goal.kind` (`volition` | `standing`), makes every in-scene
reader filter on it explicitly, and renders standing rows in their own prompt
section framed as a REASON FOR PRESENCE rather than a current action — the M1
decision, taken because `assemble_npc_context` is rebuilt from canon on every
call with no history, so a standing row is stable across a whole scene and a
"what you are doing right now" framing would loop.

No model can author a standing row in this step (E1). Creator CRUD only, and
the Creation-side editor is BRIEF-0073-c.

## Mini-RECON — measured, re-verify before editing

All anchors measured against `main` fetched 2026-08-23, schema v1.90.
Line numbers shift after BRIEF-0073-a in `context.py` only.

**Model**
- **[M]** `NpcGoal` — `src/world_engine/models/canon.py:481`. `__table_args__`
  carries `ck_npc_goal_horizon`, `ck_npc_goal_status`, `idx_npc_goal_npc_status`.
  Columns: `id`, `world_id`, `npc_id`, `description`, `horizon`, `status`,
  `created_at`, `updated_at`, `change_history`.
- **[M]** `models/canon.py` = 974/1000 lines. 26 lines of margin. The additions
  below are ~14 lines. Tight but sufficient — MEASURE after editing.
- **[M]** The header comment at `canon.py:471-480` says "NPC interiority —
  in-scene volition" and "Read ONLY by `assemble_npc_context` and the
  initiative vote (N1)". Both statements become incomplete with this step.

**Write path**
- **[M]** `NPC_GOAL_HORIZONS = frozenset({"short", "long"})` —
  `writes/goals_agendas.py:49`; re-exported via `writes/__init__.py:55`;
  imported by six crud modules (`goals`, `ledger`, `prompts`, `entities`,
  `knowledge`, and one more — enumerate before editing).
- **[M]** `write_npc_goal` — `writes/goals_agendas.py:139`. Keyword-only after
  `db`: `world_id`, `npc_id`, `description`, `horizon`, `changed_by="creator"`.
  Validates `horizon not in NPC_GOAL_HORIZONS -> ValueError`. Inserts with
  `status="active"`, `change_history=[]`.

**The four in-scene readers**
- **[M]** `context.py::_npc_context_goals` (was `:243`) — one `long` query
  LIMIT 1, one `short` query LIMIT 2, renders `[LONG TERME]` / `[COURT TERME]`
  lines under `H_GOALS`.
- **[M]** `tick_context.py::_tick_goals_block:181` — same two queries, no LIMIT,
  plus `_goal_prerequisite_lines` per goal.
- **[M]** `play_initiative.py::_initiative_candidate_data:414` — one query,
  `horizon == "short"` only, collapsed by `goal_by_npc.setdefault(...)` to ONE
  string per NPC, newest first.
- **[M]** `play_initiative.py::_signal_line:446` builds
  `- {name} : relation=..., statut=...{goal_frag}` where `goal_frag` is
  `, objectif=« {text} »` truncated at 80 chars with a trailing ellipsis.
- **[M]** `cockpit/mutations.py::_mutation_goal_change_close:507` selects ALL
  active goals for the NPC (`status == "active"`, no horizon filter) and
  matches by normalized description text. **This is the reader that lets a
  model-proposed `goal_change` reach a standing row.** See Scope IN 6.

**N1 allowlist**
- **[M]** `tooling/verify/checks/npc_goal_read.py` `ALLOWED_MODULES` already
  contains every module this brief edits: `models/canon.py`,
  `models/__init__.py`, `writes/goals_agendas.py`, `context.py`,
  `cockpit/crud/goals.py`, `cockpit/routes/mutations.py`,
  `cockpit/play_initiative.py`, `cockpit/mutations.py`, `tick.py`,
  `tick_context.py`. **No allowlist entry is added by this brief.**

**Migration mechanics — measured empirically, not assumed**
- **[M]** SQLite 3.45.1 accepts a cross-column CHECK inside
  `ALTER TABLE ... ADD COLUMN`. Verified by direct execution against a table
  shaped like `npc_goal` with a pre-existing row: the statement succeeded, the
  existing row took the default, `(standing, short)` was rejected,
  `(standing, long)` accepted, and an out-of-vocabulary kind rejected.
  **No table rebuild is required.**
- **[M]** `ALTER TABLE ... ADD COLUMN` is the established idiom in this repo
  (`migrate_v1_16_knowledge_history.py:34`, `migrate_v1_24.py:37`,
  `migrate_v1_38_faction_structure.py:48`, and others).
- **[M]** Migration scripts are idempotent and end in post-checks that
  `raise SystemExit` on a missing constraint — see
  `scripts/migrate_v1_69_npc_goal.py` for the idiom to copy.
- **[M]** Schema version marker: `world-engine-schema.md:3`
  ("Current schema version: v1.90"). Append-only changelog:
  `world-engine-schema-changelog.md` at repo root, newest entry FIRST.
- **[M]** `npc_goal`'s documented DDL block: `world-engine-schema.md:653-675`.

### STOP conditions

1. `models/canon.py` exceeds 1000 lines after the model edit. Do not baseline
   it, do not shorten the comment to fit — stop and escalate; the fix is an
   extraction step, which is not authorized here.
2. The enumeration of `NpcGoal` readers turns out to be larger than the four
   named above. Measure with
   `grep -rn "NpcGoal" --include=*.py src/ | grep -v "^src/world_engine/models/"`
   and reconcile against `ALLOWED_MODULES` before editing. If a fifth in-scene
   reader exists, stop — the check in Scope IN 8 must cover every one of them
   and a missed reader is a silent leak of standing rows into a volition path.
3. `ALTER TABLE npc_goal ADD COLUMN ... CHECK (...)` is rejected by the local
   SQLite build. Stop and escalate; do not fall back to a table rebuild
   without authorization (`npc_goal` is referenced by `goal_prerequisite.goal_id`
   and `goal_agenda_link.goal_id`, and a rebuild is a materially different
   danger class).
4. Any existing `npc_goal` row would violate the new CHECK. It cannot happen
   (every existing row defaults to `volition`), but verify with a count query
   before and after; a non-zero violation count is a STOP.

## Scope IN

1. **Model** (`models/canon.py`, `NpcGoal`). Add:

   ```python
   kind: str = Field(default="volition", sa_column_kwargs={"server_default": text("'volition'")})
   ```

   placed immediately after `horizon`. Add to `__table_args__`:

   ```python
   CheckConstraint("kind IN ('volition','standing')", name="ck_npc_goal_kind"),
   CheckConstraint(
       "kind <> 'standing' OR horizon = 'long'", name="ck_npc_goal_standing_horizon"
   ),
   ```

2. **Amend the model header comment** at `canon.py:471-480`. Replace the two
   sentences that are now incomplete. Verbatim replacement text:

   ```
   # npc_goal  (NPC volition, schema v1.91, BRIEF-0013-a + TICKET-0073)
   #
   # Flat table (F1, no parent_goal_id — see ARCHITECTURE_DECISIONS "Deferred
   # decisions" for the F2 reactivation trigger). description is immutable
   # after insert: a "changed" goal is a closed goal plus a new row. status
   # transitions are one-way (active -> completed|abandoned), never reopened.
   #
   # `kind` (TICKET-0073, G2) splits two natures that share this table:
   #   volition — in-scene volition, aimed at changing a state. Everything
   #              this table held before v1.91.
   #   standing — background volition: an occupation, a trade, a pastime. It
   #              has no terminal state and is never "completed" by play; it
   #              ends only when the creator closes it. Rendered as a reason
   #              for presence (context.py's POURQUOI TU ES ICI), never as a
   #              current action — see M1 in TICKET-0073 for why.
   # `kind='standing'` implies `horizon='long'` (ck_npc_goal_standing_horizon).
   # This CHECK is defence in depth: every in-scene reader filters on `kind`
   # explicitly, and the constraint catches a future reader that forgets to.
   #
   # Read ONLY by assemble_npc_context, the tick briefing, the initiative
   # vote (N1) and _mutation_goal_change_close — assemble_mj_context must
   # never gain a query against this table.
   ```

3. **Write-path vocabulary** (`writes/goals_agendas.py`). Add next to
   `NPC_GOAL_HORIZONS`:

   ```python
   NPC_GOAL_KINDS = frozenset({"volition", "standing"})
   ```

   Re-export from `writes/__init__.py` alongside `NPC_GOAL_HORIZONS`.

4. **`write_npc_goal`** gains a keyword-only `kind: str = "volition"`,
   validated fail-closed BEFORE the insert, in the same shape as the existing
   horizon validation:

   ```python
   if kind not in NPC_GOAL_KINDS:
       raise ValueError(f"write_npc_goal: invalid kind {kind!r}")
   if kind == "standing" and horizon != "long":
       raise ValueError("write_npc_goal: kind='standing' requires horizon='long'")
   ```

   The second guard duplicates the CHECK on purpose: it fails at the write
   site with a readable message instead of surfacing as an IntegrityError.

5. **Filter the three rendering readers to `volition`.** Add
   `NpcGoal.kind == "volition"` to the where-clause of every `NpcGoal` select
   in:
   - `context.py::_npc_context_goals` (both queries)
   - `tick_context.py::_tick_goals_block` (both queries)
   - `play_initiative.py::_initiative_candidate_data` (the one query)

   Explicit equality, not `!= "standing"` — the check in Scope IN 8 looks for
   a positive `kind` comparison, and a negative form would silently admit a
   third kind added later.

6. **Filter `_mutation_goal_change_close`'s candidate pool to `volition`**
   (`cockpit/mutations.py:517`). Today it selects every active goal for the
   NPC and matches by normalized description, so a model-proposed
   `goal_change complete` whose text happened to match an occupation could
   close it. Under E1 no model authors standing rows; it must not be able to
   close one either. Add `NpcGoal.kind == "volition"` to that select.

   Its "no active goal matching" error path already handles the miss, so a
   `goal_change` aimed at an occupation now fails cleanly rather than
   silently retiring the NPC's trade.

7. **The standing render in dialogue** (`context.py`).

   a. New section constant, beside the existing `H_*` block:

   ```python
   H_STANDING = "POURQUOI TU ES ICI"
   ```

   b. New sub-assembler, placed next to `_npc_context_goals`:

   ```python
   def _npc_context_standing(npc_id: str, session: Session) -> str:
       """----- 1c. Standing occupation (TICKET-0073, G2/M1) — the single most
       recent active standing goal, rendered as a REASON FOR PRESENCE rather
       than a current action. This briefing carries no scene history and is
       rebuilt on every call, so a "what you are doing right now" framing would
       be re-asserted verbatim at turn 14 and loop against the conversation the
       model already has. The scene owns the gesture; this owns the reason."""
   ```

   One query: `status == "active"`, `kind == "standing"`, ordered by
   `created_at` desc, LIMIT 1. Returns `""` when there is none.

   c. Section body, VERBATIM (the executor copies, it does not paraphrase).
   Line 1 is the description; line 2 is fixed text:

   ```
   {description}
   C'est ta raison d'etre ici, pas une action en cours. Si la scene t'a deja
   ecarte de cette occupation, la scene prime.
   ```

   Render through the existing `_section(H_STANDING, body)` helper, with the
   same trailing-newline treatment `_npc_context_goals` uses.

   NOTE ON ACCENTS: the two fixed lines are French prompt text and MUST carry
   their real accents in the source (`C'est`, `raison d'être`, `scène`,
   `écarté`). They are written unaccented in this brief only because briefs
   are ASCII. Copy them as: `C'est ta raison d'être ici, pas une action en
   cours. Si la scène t'a déjà écarté de cette occupation, la scène prime.`

   d. Call it from `assemble_npc_context`, immediately AFTER the
   `_npc_context_goals` call so the occupation reads below the volitions.

   e. `_goal_provenance_suffix` is NOT applied to a standing row. Provenance
   is about whose intrigue a goal serves; an occupation serves nobody's.

8. **New check** — `tooling/verify/checks/standing_goal.py`. Stdlib `ast`
   only, no DB. Follow the FAILURES / `fail()` / `_report_and_exit` idiom of
   `npc_goal_read.py`. Rules:

   - **R1 (reader filter).** In each of the four reader functions named in
     the mini-RECON, every `select(NpcGoal)` call chain contains a
     `Compare` node whose operands include an `Attribute` with `attr == "kind"`
     on a `Name` `NpcGoal`. Locate the functions by name; a function not found
     is a FAILURE (they may be renamed, and a renamed reader must be
     re-registered here deliberately).
   - **R2 (anti-vacuity).** Zero reader functions located, or zero
     `select(NpcGoal)` calls found across them, is a FAILURE, not a pass.
   - **R3 (constraints present).** `models/canon.py` declares
     `CheckConstraint` nodes named `ck_npc_goal_kind` and
     `ck_npc_goal_standing_horizon`.
   - **R4 (vocabulary).** `NPC_GOAL_KINDS` is assigned in
     `writes/goals_agendas.py` and named in `writes/__init__.py`.
   - **R5 (render separation).** `context.py` assigns `H_STANDING`, and
     `_npc_context_standing` exists and does not reference `H_GOALS`.
   - **R6 (reachability).** `assemble_npc_context` contains a call to
     `_npc_context_standing`, and `_initiative_signal_lines` references the
     standing fragment variable introduced in Scope IN 9. A constant that is
     assigned but never reached renders nothing — R5 alone does not prove
     this.

   Register the check in `corpus_gate.py` following the existing registration
   idiom.

9. **The initiative fragment** (`play_initiative.py`, N1 decision).

   `_initiative_candidate_data` gains a SECOND query and returns a THIRD
   value: `standing_by_npc: dict[str, str]`, built from `status == "active"`,
   `kind == "standing"`, newest first, one per NPC via `setdefault`.

   It must NOT join the existing `goal_by_npc` pool: that dict is collapsed to
   one string per NPC, so admitting the occupation there would silently
   suppress either it or the short goal by creation date.

   `_initiative_signal_lines` gains a matching parameter and appends a second
   fragment after `goal_frag`, same 80-char truncation with ellipsis:

   ```python
   standing_frag = f", ici pour=« {text} »"
   ```

   Producing, for example:

   ```
   - Doran : relation=mefiant (38/100), statut=actif, objectif=« ... », ici pour=« ... »
   ```

   Update the one call site of each function. This fragment matters most for
   `distant_lines` (non-members, who can only intervene by approaching): an
   NPC held by its post reads differently from one at leisure in its own room.

10. **Migration** — `scripts/migrate_v1_91_npc_goal_kind.py`, idempotent,
    following `scripts/migrate_v1_69_npc_goal.py`'s shape:

    - If `kind` is already a column of `npc_goal`, print and exit 0.
    - Otherwise execute, as one statement:
      ```sql
      ALTER TABLE npc_goal ADD COLUMN kind TEXT NOT NULL DEFAULT 'volition'
        CHECK (kind IN ('volition','standing')
               AND (kind <> 'standing' OR horizon = 'long'))
      ```
      NOTE: SQLite has no `ADD CONSTRAINT`. Both CHECKs ride on the ADD COLUMN
      statement as a single column-level expression; the model declares them
      as two named constraints so a fresh `create_all` produces the same
      semantics under readable names. This asymmetry is intentional and must
      be stated in a comment in the migration script.
    - Post-checks that `raise SystemExit` on failure: the column exists; a
      `SELECT COUNT(*) FROM npc_goal WHERE kind NOT IN ('volition','standing')`
      returns 0; a `SELECT COUNT(*) FROM npc_goal WHERE kind='standing' AND horizon<>'long'`
      returns 0.
    - Run `scripts/backup.py` before the ALTER, per the standing convention for
      `danger_class: migration`.

## Scope OUT

- **The Creation-side editor.** `GoalWriteBody`, `create_goal`, `_goal_dict`,
  `GoalsEditor.svelte`, `goalsPanel.svelte.js` — all BRIEF-0073-c. This brief
  ends at the write function and the readers. The API will still reject a
  `kind` it does not accept yet; that is expected between -b and -c.
- **`generate_npc_goals`** (`entity_author.py:770`). The authoring model does
  not emit standing goals in v1 (E1). Do not extend its prompt, its parser, or
  its template.
- **A `schedule_change` mutation type, an auto-approve whitelist, and any
  mutation vocabulary change.** Deferred to TICKET-0074 brief -b, and only
  once a real proposer exists.
- **The `npc_schedule` table, `where_is`, `who_is_at`, the Creation location
  panel, and `npc_schedule.standing_goal_id`.** All TICKET-0074. In particular
  do NOT add a location column, a phase column, or any temporal field to
  `npc_goal` — the schedule is a separate table and this row must not
  anticipate it.
- **The L1 concordance trigger** (render the occupation only when the NPC's
  schedule row for the current phase matches its current location). It needs
  the schedule table. In THIS step the standing section renders whenever the
  NPC has an active standing row, unconditionally. That is deliberate: it is
  the widest form, which is what the M1 hypothesis needs in order to be
  falsifiable in a live session.
- **`assemble_mj_context`.** N1 stands: the MJ never reads `npc_goal`, of any
  kind. Do not add a query, and do not "surface the occupation to the MJ for
  narration".
- **Changing `_goal_provenance_suffix` or the prerequisite machinery.**
  Standing rows get neither.
- **Reopening or editing goal rows.** `description` stays immutable after
  insert; a changed occupation is a closed row plus a new one.
- **Any change to `horizon`'s vocabulary.** G1 was rejected; `NPC_GOAL_HORIZONS`
  stays `{short, long}`.

## Invariants to defend

- **N1 goal-read doctrine.** No new module reads `NpcGoal`; `ALLOWED_MODULES`
  gains no entry. `assemble_mj_context` gains no query. Rule 2's window is
  unaffected — `_npc_context_standing` goes near `_npc_context_goals`, far
  above `assemble_mj_context`. If the new function lands below it, the check
  fires; that is the check working.
- **Fail-closed and vacuous-proof.** R2 in the new check exists because a
  scan that locates zero readers and reports success is a silent failure, not
  a pass.
- **Structural over disciplinary.** The CHECK constraints are in the table,
  not in a comment. The `kind` filters are in the queries, not in a rule that
  a future reader is asked to remember.
- **History is sacred.** Purely additive migration. No existing row is
  rewritten beyond taking the column default; no row is deleted.
- **Model proposes, code judges.** This step gives the model nothing new to
  propose, and closes the one path (Scope IN 6) by which an existing mutation
  type could have reached a standing row.
- **No structure without a reader.** `kind` ships with four filters, one
  prompt section and one initiative fragment in this same brief.

## Done means

- [ ] `python scripts/backup.py` run, then
      `python scripts/migrate_v1_91_npc_goal_kind.py` completes with all
      post-checks passing; running it a second time prints the already-present
      message and exits 0.
- [ ] `sqlite3 ~/.world_engine/world_engine.db ".schema npc_goal"` shows the
      `kind` column with both CHECK expressions.
- [ ] Every pre-existing `npc_goal` row returns `kind = 'volition'`.
- [ ] Inserting `(kind='standing', horizon='short')` directly via sqlite3 is
      rejected by the CHECK; `(kind='standing', horizon='long')` is accepted.
- [ ] `wc -l src/world_engine/models/canon.py` returns at most 1000.
- [ ] `python tooling/verify/checks/standing_goal.py` exits green, and exits
      RED when a `kind` filter is temporarily removed from any one of the four
      readers (verify the check actually bites, one reader at a time, then
      restore).
- [ ] `python tooling/verify/checks/npc_goal_read.py` exits green.
- [ ] `python tooling/verify/checks/module_budget.py` exits green.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits green.
- [ ] With a standing row inserted by hand for one NPC, the prompt inspection
      route shows a `POURQUOI TU ES ICI` section for that NPC carrying the
      description and the two fixed sentences, and the section is absent for
      an NPC with no standing row.
- [ ] That same NPC's standing row does NOT appear under `TES OBJECTIFS`, and
      does not appear in the tick briefing's goal block.
- [ ] In a live scene with that NPC present, the initiative signal line for it
      carries an `ici pour=« ... »` fragment alongside `objectif=`.
- [ ] A `goal_change complete` proposal whose text matches the standing row's
      description is rejected with the "no active goal matching" error.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- **`world-engine-schema.md`:** bump line 3 to `v1.91`. Update the `npc_goal`
  DDL block (currently lines 653-675) with the `kind` column and both CHECKs,
  and amend the prose above it, which currently says the table is read only by
  `assemble_npc_context` and the initiative vote.
- **`world-engine-schema-changelog.md`:** new entry at the TOP, in the
  established voice:

  > **v1.91** — Added `npc_goal.kind` (TEXT NOT NULL DEFAULT 'volition',
  > CHECK `kind IN ('volition','standing')` and CHECK
  > `kind <> 'standing' OR horizon = 'long'`). `standing` rows are background
  > volition — an occupation, a trade, a pastime — with no terminal state,
  > authored by creator CRUD only. Every in-scene reader now filters on `kind`
  > explicitly: the dialogue goal block, the tick briefing and the initiative
  > vote render `volition` only, and `_mutation_goal_change_close` can no
  > longer match a standing row, so no model-proposed `goal_change` can close
  > an occupation. Standing rows render in their own dialogue section
  > (`POURQUOI TU ES ICI`) as a reason for presence rather than a current
  > action, and add a separate `ici pour=` fragment to the initiative signal
  > line. Purely additive: existing rows take the default.

- **`ARCHITECTURE_DECISIONS.md`:** a short entry for G2 (why a discriminator
  rather than a second table — G3 rejected) and for M1 (why the section is
  framed as presence rather than action, with M2 and M3 named as rejected and
  M2's reactivation condition recorded: *the live gate shows the NPC looping
  on its occupation across a long scene*).
- **`CLAUDE.md`:** nothing.
