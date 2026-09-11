# BRIEF — Step "The action lexicon: shared resolver and skill_resolution"

## Context

The lexicon already exists, sealed inside the Play surface: `_arbitrate` in
`cockpit/play_physical.py` injects the world's skill names into the arbiter
prompt and clamps the model's answer against them, falling back to `physical`
on any miss. That clamp is the right mechanism in the wrong place — nothing
outside Play can use it, and every miss is thrown away. This step extracts it
into a shared resolver and persists one row per resolution, which turns the
misses into the list of holes Nia can populate (BRIEF-0084-d reads it) and into
the measurable trigger for the deferred alias table.

## Mini-RECON (executor, before any edit)

Two briefs have landed since this was written and `play_physical.py` was not
touched by either, but its line numbers and the surrounding call site must be
confirmed. Run this and **report before editing**; on any mismatch, STOP and
report.

1. Confirm `_arbitrate` still lives in
   `src/world_engine/cockpit/play_physical.py`, report its current signature
   and its return tuple, and report the exact clamp expression that unions the
   base domains with `custom_skill_names`.
2. Report **every call site** of `_arbitrate` and, for each, whether a
   `Conversation` id is in scope at that point. If any call site has no
   conversation in scope, STOP and report — the anchor decision (L1) assumed
   there is exactly one, in Play.
3. Report where `custom_skill_names` is built (the query that lists the world's
   `skill_definition` names) and whether it already carries ids or only names.
4. Report the exact shape of `class Conversation` in
   `src/world_engine/models/ephemeral.py` — its primary key type and whether
   any code path deletes `Conversation` rows.
5. Report how `tooling/verify/checks/day_rewrite.py` enforces append-only, so
   the new check reuses that technique rather than inventing one.
6. Report the current `[CANON_TABLES]` list in `canon_write_policy.txt`, to
   confirm `skill_resolution` must NOT be added to it.

## Scope IN

1. **New model `SkillResolution`** in `src/world_engine/models/pipeline.py`,
   placed immediately after `DayMentionResolution` (same family, same idioms):

   ```python
   # -------------------------------------------------------------------------
   # skill_resolution  (one row per arbiter classification — the action
   # lexicon's audit trail; schema v2.02, TICKET-0084)
   # -------------------------------------------------------------------------
   class SkillResolution(SQLModel, table=True):
       __tablename__ = "skill_resolution"
       __table_args__ = (
           CheckConstraint(
               "verdict IN ('base','matched','unmatched')",
               name="ck_skill_resolution_verdict",
           ),
           CheckConstraint(
               "(verdict <> 'base' OR (base_domain IS NOT NULL AND skill_definition_id IS NULL)) "
               "AND (verdict <> 'matched' OR (skill_definition_id IS NOT NULL AND base_domain IS NULL)) "
               "AND (verdict <> 'unmatched' OR (skill_definition_id IS NULL AND base_domain IS NULL))",
               name="ck_skill_resolution_shape",
           ),
           Index("idx_skill_resolution_world_verdict", "world_id", "verdict"),
           Index("idx_skill_resolution_conversation", "conversation_id"),
       )

       id: str = Field(default_factory=_uuid, primary_key=True)
       world_id: str = Field(foreign_key="world.id", nullable=False)
       conversation_id: str = Field(foreign_key="conversation.id", nullable=False)
       surface_form: str          # what the arbiter returned, verbatim
       verdict: str
       base_domain: Optional[str] = None
       skill_definition_id: Optional[str] = Field(default=None, foreign_key="skill_definition.id")
       created_at: datetime = _created_ts()
   ```

   The three verdicts, stated so the executor does not collapse them:
   - `base` — the arbiter named one of `BASE_SKILL_DOMAINS`. Normal, not a gap.
   - `matched` — the arbiter named a `skill_definition` of this world.
   - `unmatched` — the arbiter named something else and was clamped to the
     `physical` fallback. THIS is a hole in the world.

2. **New module `src/world_engine/skill_lexicon.py`** — the shared resolver,
   outside `cockpit/`, so a non-Play caller can import it without importing the
   Play surface:

   - `def lexicon_terms(db, *, world_id) -> tuple[str, ...]` — the world's
     `skill_definition` names, ordered, for prompt injection.
   - `def judge(raw: str, *, base_domains, catalogue) -> Verdict` — **pure, no
     DB, no I/O.** Takes the arbiter's raw string and the two closed sets;
     returns a small dataclass carrying `verdict`, `base_domain`,
     `skill_definition_id`, `surface_form` (the raw string, verbatim, always),
     and `effective_domain` (what the caller should use to roll: the base
     domain, the matched skill's `base_domain`, or `"physical"` on
     `unmatched`). Matching is exact after `.strip()` and a lowercase compare
     on base domains only; catalogue names compare exactly as stored. Never
     raises: any input, including empty string and `None`-ish, yields
     `unmatched`.
   - `def record(db, *, world_id, conversation_id, verdict) -> None` — inserts
     one `SkillResolution` row. Insert only: this function contains no
     `.delete()`, no UPDATE, and no `SELECT ... FOR UPDATE`.

   The split is the point: the model proposes (`_arbitrate`), the code judges
   (`judge`), the trail is kept (`record`). Do not merge them.

3. **`cockpit/play_physical.py` calls the resolver instead of clamping
   inline.** `_arbitrate` keeps its job — call the model, parse the JSON — and
   **stops clamping**: it returns the raw domain string the model produced. The
   caller then runs `judge`, uses `effective_domain` for the roll, and calls
   `record`. Observable behaviour must be identical to today for `base` and
   `matched`, and identical to today's fallback for `unmatched` (the turn still
   resolves on `physical`; nothing is refused, nothing is shown to the player).

4. **The failure paths still fall back, and are still recorded.** On bad JSON,
   Ollama error, or timeout, `_arbitrate`'s existing fallback stands; the
   caller records a row with `verdict='unmatched'` and `surface_form` set to
   one of these two exact literals, chosen by cause:

   ```
   __arbiter_error__
   __arbiter_empty__
   ```

   Using a literal rather than NULL keeps `surface_form` NOT NULL and keeps the
   gaps view honest: a run of `__arbiter_error__` means Ollama is sick, not
   that the world has a hole.

5. **`scripts/migrate_v2_02_skill_resolution.py`**, on the shape of
   `migrate_v2_01_skill_system.py`: same fail-closed env preamble, creates the
   table and its two indexes, idempotent per object, creates zero rows.
   Post-check before commit: `SELECT COUNT(*) FROM skill_resolution` returns 0.

6. **`tooling/verify/checks/skill_resolution_append_only.py`** — static, using
   the technique reported by mini-RECON step 5: fails if any `.delete()` or
   UPDATE site under `src/` targets `skill_resolution`; fails if
   `skill_resolution` appears in `canon_write_policy.txt` `[CANON_TABLES]`;
   fails if any row in the dev DB violates the shape CHECK. Vacuous pass (zero
   sites collected AND zero rows) is a FAIL.

7. **`tooling/verify/checks/skill_lexicon_clamp.py`** — a behavioural check on
   `judge` alone, no DB, no model: for a fixed catalogue, asserts that every
   base domain yields `base`, every catalogue name yields `matched`, and a list
   of at least ten hostile inputs (empty string, whitespace, a near-miss of a
   catalogue name differing by one character, a base domain in uppercase, a
   name with a trailing period, JSON fragments, a very long string) all yield
   `unmatched` with `effective_domain == "physical"` and never raise.

## Scope OUT

- **Any refusal.** `unmatched` never blocks a turn, never surfaces to the
  player, never produces an error. D3 was dropped; do not reintroduce it under
  another name.
- **An alias table, fuzzy matching, embeddings, or normalisation beyond
  `.strip()`.** C3b is deferred. Its reactivation condition is now a query on
  this table: `SELECT COUNT(DISTINCT surface_form) FROM skill_resolution WHERE
  verdict='unmatched'` restricted to strings that are near-misses of catalogue
  names. Write the condition into the docs; do not implement the table.
- **Wiring the day chain.** `day_plan.py::_validate_step` keeps accepting only
  `null` or a base domain; `day_resolve.py` is not touched. No
  `pass_play_id` column, no `source_type` column — L1 locked
  `conversation_id` alone, and the day-chain arm is paid for by the ticket that
  needs it.
- **Changing the arbiter prompt's rubric**, beyond what item 3 requires. The
  `{custom_skill_names}` injection stays as it is.
- **Changing `resolve_physical` or any roll math.**
- **Retention, pruning, or aggregation of `skill_resolution`.** It grows
  forever and that is the intent; one row per physical turn is small. No
  cleanup job, no rollup table.
- **The gaps view.** BRIEF-0084-d reads this table; this step does not display
  anything.
- **`world.magic_status`.** BRIEF-0084-e.

## Invariants to defend

- **"Model proposes, code judges."** This step's whole shape defends it. If
  `judge` ever needs to call the model, or `_arbitrate` ever needs to know the
  catalogue's semantics, something has gone wrong — STOP and report.
- **Append-only.** `skill_resolution` is written by exactly one function
  (`record`) and never updated or deleted. The new check enforces it
  structurally; do not rely on discipline.
- **`skill_resolution` is NOT canon.** It lives in `pipeline.py`, it is absent
  from `[CANON_TABLES]`, and the two-sanctioned-canon-write-paths doctrine does
  not apply to it — but `single_canon_write.py` must still pass, so confirm the
  new write site is attributable to a non-canon table and not flagged as
  unattributable.
- **Fail-closed on the model.** Every failure mode of the arbiter already falls
  back to `physical`; this step must not introduce a path where an
  unrecognised string reaches the roll unclamped.
- **"Secrets structurally excluded."** `surface_form` stores the arbiter's
  output, which derives from the player's own line. Confirm no secret-bearing
  field can reach it; if the arbiter output could ever carry NPC-private text,
  STOP and report before persisting it.
- **B3 holds.** A world with no magic system owns no magic skill names, so
  `catalogue` is empty of them and `matched` on a magic term is unreachable.
  Exclusion stays structural; do not add a guard that checks for magic by name.

## Done means

- [ ] `python scripts/migrate_v2_02_skill_resolution.py` runs clean, then again
      reporting all objects present, exit 0. `SELECT COUNT(*) FROM
      skill_resolution` returns 0 after both runs.
- [ ] A Play physical turn that classifies as a base domain writes exactly one
      row with `verdict='base'`, `base_domain` set, `skill_definition_id` NULL.
- [ ] A Play physical turn naming a catalogue skill writes exactly one row with
      `verdict='matched'`, `skill_definition_id` set, `base_domain` NULL, and
      the roll uses that skill's tier — same result as before this step.
- [ ] With Ollama stopped, a physical turn still resolves on `physical` and
      writes one row with `surface_form='__arbiter_error__'`.
- [ ] `sqlite3 <db> "SELECT verdict, COUNT(*) FROM skill_resolution GROUP BY
      verdict"` shows all three verdicts after a short live session.
- [ ] An attempted `UPDATE skill_resolution SET verdict='base'` by hand is
      irrelevant to the check — but `python -m
      tooling.verify.checks.skill_resolution_append_only` returns PASS against
      the code.
- [ ] `python -m tooling.verify.checks.skill_lexicon_clamp` returns PASS.
- [ ] In a world with zero `skill_definition` rows, a full Play session runs
      and every row is `base` or `unmatched`; zero `matched`.
- [ ] `pytest`, `no_print_in_src.py`, `undefined_names.py`, `import_cycle.py`,
      `single_canon_write.py` all green.
- [ ] `/review-step` and `/close-step` both run.
- [ ] Commit before touching `play_physical.py` if the extraction is done in
      two passes; otherwise one commit for the whole step.

## Docs to update

- `world-engine-schema-changelog.md` — new entry **v2.02**, TICKET-0084,
  BRIEF-0084-c: the table with its full column list, both CHECK constraints
  quoted, both indexes, the three verdicts and what each means, the migration
  filename, zero rows created.
- `world-engine-schema.md` — bump to v2.02; add the `CREATE TABLE
  skill_resolution` block next to `day_mention_resolution`, with this NOTE,
  verbatim:

  ```
  -- One row per arbiter classification (v2.02, TICKET-0084). APPEND-ONLY: no
  -- UPDATE site, no DELETE site, enforced by
  -- verify/checks/skill_resolution_append_only.py. verdict 'base' = the
  -- arbiter named a base domain; 'matched' = it named a skill_definition of
  -- this world; 'unmatched' = it named neither and was clamped to the
  -- physical fallback -- a hole in the world, read by Creation's gaps view.
  -- 'unmatched' NEVER refuses a turn. Not a canon table.
  ```

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — record C1 and C3a as
  discharged; record the C3b reactivation condition in its final measurable
  form (the `COUNT(DISTINCT surface_form)` query above, with the threshold Nia
  sets at the live gate); record that the day-chain arm of the anchor is
  deliberately absent per L1 and is owed by the day-chain wiring ticket.
- `CLAUDE.md` — name `src/world_engine/skill_lexicon.py` as the single home of
  the action lexicon, and state that Play calls it rather than clamping inline.
