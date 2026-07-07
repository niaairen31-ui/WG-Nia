# BRIEF — Step "world-tick context builder and prompt (BRIEF-0014-a-tick-context-and-prompt)"

## Context

TICKET-0014 lets the world advance off-screen: a manual, scoped cockpit
action asks the gameplay model what each NPC in scope did during a
creator-chosen interval, and the answers land as `proposed_mutation` rows
(C2, I1, J1). This first chantier builds the READ side and the prompt: a
new module `src/world_engine/tick.py` with the full-interiority briefing
builder (K2/T1), the `pt-world-tick` template delivered through the 0013
prompt pattern, the N1 allowlist extension, a new structural check, and a
creator-facing preview script as the builder's first reader. The runner,
normalization, `tick_id` migration (Y2), and cockpit UI are BRIEF-0014-b.

## Scope IN

1. **New module `src/world_engine/tick.py`** containing
   `assemble_tick_context(npc_id: str, session: Session) -> str`.
   Raises ValueError when `npc_id` is not an NPC character (same guard
   shape as `assemble_npc_context`, context.py:197-200). Sections, in
   order, each via the same `_section(title, body)` convention as
   context.py:103 (import it or replicate the 3-line helper locally —
   replicate, to keep tick.py free of context.py imports):

   - `QUI TU ES` — name, appearance, backstory, aversion, entity
     description (same composition as context.py:210-221).
   - `TES OBJECTIFS` — ALL active goals, both horizons, newest first,
     long-terms first; lines `[LONG TERME] …` / `[COURT TERME] …`. No
     read-side cap: the dialogue LIMIT was the S1 prompt-size bound; the
     tick decides what advanced and must see everything active.
   - `CE QUE TU SAIS` — ALL knowledge rows of the NPC ordered by id,
     rendered as the dialogue `_knowledge_line` does (context.py:107-112),
     with rows where `is_secret` is true prefixed exactly `[SECRET] `.
     No share_threshold gating, no is_secret exclusion: there is no
     interlocutor. T1 conscious exception — see Invariants.
   - `TES RELATIONS` — every relation edge where the NPC perceives a
     target (`_perceived_target` logic, context.py:114-121), one line per
     target: `- {name} : {relation_type} ({intensity}/100)` followed by
     the rendered perception sentence (same wording source as
     `_render_perception`, context.py:123-129).
   - `TES AFFILIATIONS` — the NPC's ACTIVE memberships
     (`left_at IS NULL`) read DIRECTLY from FactionMembership (NOT via
     `read_public_memberships`): TRUE `role` (never `cover_role`),
     secret memberships included and prefixed exactly
     `[AFFILIATION SECRÈTE] `. For each distinct faction, append an
     indented posture block from the Faction row, one line per non-empty
     field, labels verbatim: `Philosophie : `, `Buts : ` (Faction.goals —
     its second reader after the 0013 generator input), `Tensions
     internes : `, `Aversion : `.
   - `OÙ TU TE TROUVES` — location entity name + description +
     `subculture` values (same composition as context.py:246-266, minus
     the player-condition injection, which is scene-specific).
   - `QUI EST AUTOUR` — characters with `current_location_id` equal to
     the NPC's, excluding the NPC itself: `- {name} : {appearance or
     entity description or "(pas de description)"}`. Public description
     only — other NPCs' interiority never enters this briefing.

   The briefing ends with the anti-invention boundary, verbatim:
   `Tu ne sais que ce qui est écrit ci-dessus. N'invente aucune personne,
   aucun lieu, aucun fait au-delà de ce contexte.`

2. **N1 allowlist extension** — add `src/world_engine/tick.py` to
   `ALLOWED_MODULES` in `tooling/verify/checks/npc_goal_read.py:31-39`.
   No other change to that check; rule 2 (MJ boundary) stays byte-identical.

3. **New check `tooling/verify/checks/world_tick.py`** (stdlib `ast`
   only, same shape as npc_goal_read.py). This brief lands rules 1-2;
   BRIEF-0014-b extends it with rules 3-5 (forced attribution, tick_id
   guard branch, secret_derived floor):
   - Rule 1: the identifier `assemble_tick_context` may appear only in
     `src/world_engine/tick.py`, `src/world_engine/cockpit/app.py`, and
     `scripts/preview_tick_context.py`. Rationale: the MJ boundary check
     scans for `NpcGoal`/`"npc_goal"`, which an indirect call to the tick
     builder would evade (RECON-0014 F6).
   - Rule 2: `src/world_engine/context.py` and
     `src/world_engine/gathering.py` contain NO reference to the
     identifier `assemble_tick_context` anywhere.
   Register the check wherever existing checks are discovered by the
   harness (mirror how npc_goal_read.py was registered in 0013).

4. **Prompt template `pt-world-tick`** — seed constants in
   `scripts/seed_pilot.py` (single source of prompt text, S2: seed writes
   v1 on virgin heads only), spec registered like `pt-npc-goals`
   (seed_pilot.py:1448 precedent), `usage="world_tick"`, `model=NULL`
   (Q1: the runner passes `ollama_client.DEFAULT_MODEL`; NULL keeps the
   per-template override available). Text verbatim:

   System prompt:
   ```
   You advance ONE NPC's life off-screen in an RPG world. You receive the
   NPC's private briefing (identity, goals, knowledge, relations,
   affiliations, location, who is around) and an elapsed interval. Decide
   what this NPC plausibly DID during that interval, acting on its goals
   and on what it knows — then report the world-state changes.

   Output: a JSON array only. No prose. No markdown fences. Start with [,
   end with ]. A quiet interval is a legitimate answer: output exactly []

   Every element must have these EXACT 5 keys — no other keys allowed:
     "mutation_type"  (string) — goal_change | relation_change | new_knowledge
     "target_table"   (string) — npc_goal | relation | knowledge
     "target_id"      (null)   — always null
     "payload"        (object) — see shapes below
     "rationale"      (string) — one line: what the NPC did that caused this change

   Reference people by NAME exactly as written in the briefing. Never
   invent identifiers, ids, or people absent from the briefing.

   Payload shapes:
     goal_change      -> {"action":"complete|abandon|create_short","goal":"…"}
     relation_change  -> {"other":"<name from the briefing>","relation_type":"…","intensity_delta":<signed int>}
     new_knowledge    -> {"recipient":"self" | "<name>","subject":"<short_slug>","level":"rumor|partial|knows","content":"…","source":"…","is_secret":true|false,"secret_derived":true|false}

   === GOAL_CHANGE RULES ===
   For "complete"/"abandon": copy the goal text EXACTLY as it appears in
   TES OBJECTIFS — never paraphrase. Emit one ONLY when the interval
   plausibly finished or definitively killed that goal; progress without
   conclusion is NOT a goal_change. For "create_short": one sentence
   starting with an infinitive verb. AT MOST ONE goal_change per listed
   goal.

   === RELATION_CHANGE RULES ===
   AT MOST ONE relation_change per counterpart for the ENTIRE interval —
   the NET effect, never per-event increments. Keep |intensity_delta|
   proportionate: minor courtesy 1-3, meaningful gesture or admission 4-8,
   serious betrayal, rescue, or attack 9-15. Routine coexistence, ordinary
   work, or mere proximity is NOT a relation_change.

   === NEW_KNOWLEDGE RULES ===
   "recipient":"self" when the NPC LEARNED something during the interval;
   "<name>" when the NPC TOLD that person something. Set
   "secret_derived":true when the information comes from a [SECRET] item
   in your briefing. Whether the knowledge is secret FOR THE RECIPIENT is
   a separate judgment: set "is_secret" by intent — a confidence shared
   discreetly stays secret; information wielded openly against an enemy
   does not. Never copy [SECRET]/[AFFILIATION SECRÈTE] markers into
   "content".

   === SCALE ===
   The elapsed interval is «{interval_label}». Scale ambition to it: a few
   hours move one small step; a few days allow a meeting, an errand, a
   discovery; a few weeks may close a short-term goal. Stay inside the
   briefing.
   ```

   User template:
   ```
   NPC BRIEFING:
   {tick_context}

   INTERVALLE ÉCOULÉ : {interval_label}

   Report what changed as a JSON array.
   ```

5. **One-shot idempotent delivery script**
   `scripts/apply_ticket_0014_prompt_updates.py` — 0013 pattern
   (`apply_ticket_0013_prompt_updates.py` precedent), writing the
   `pt-world-tick` head + v1 through `write_prompt_version` when absent;
   no-op when the head already exists with identical text.

6. **Preview reader** `scripts/preview_tick_context.py` — CLI taking
   `--npc <id>` (and optional `--db` like sibling scripts), printing the
   assembled briefing to stdout. This is the builder's concrete reader
   for this brief and the live-gate instrument for T1 review.

## Scope OUT

- The tick RUNNER: endpoint, model call, JSON extraction, normalization
  (E1/O1 forced attribution), emit-time dedup, `secret_derived` code
  floor (Z3), R3 summary — all BRIEF-0014-b.
- The `tick_id` migration (Y2), the duplicate-guard tick branch, queue
  labels/badges, `_mutation_dict` changes — BRIEF-0014-b (structure ships
  with its readers).
- Cockpit UI: scope selector, interval selector, the button — BRIEF-0014-b.
- Any movement/`status_change` emission (deferred at L3).
- Any automatic trigger or in-game time system (I3 deferred); any
  `last_tick_at` storage (rejected at M).
- Goal hierarchy `parent_goal_id` (F2) — even if "next step after a
  completed short" is tempting inside the rubric, do not introduce
  parentage; create_short stays flat.
- Pre-authorization / auto-apply of any proposal category (J3 rejected;
  named deferred decision, creator-declared only).
- No change to `assemble_npc_context`, `assemble_mj_context`,
  `read_public_memberships`, or any existing prompt template.
- No `Faction.goals` injection into DIALOGUE prompts (separate deferred
  chantier); the tick briefing read is its only new reader here.

## Invariants to defend

- **Secrets structurally excluded** — this brief creates a DELIBERATE,
  logged exception: the tick briefing includes the NPC's own `is_secret`
  knowledge and secret memberships with true roles (T1). The invariant is
  re-anchored structurally, not waived: (a) the briefing is consumed only
  by the tick model call and the creator preview script — never rendered
  to player or MJ surfaces; (b) `world_tick.py` rules 1-2 confine the
  builder's call sites by AST; (c) all output crosses `proposed_mutation`
  under creator approval (C2). Log it in ARCHITECTURE_DECISIONS.md.
- **N1 (npc_goal read boundary)** — tick.py joins the allowlist;
  `assemble_mj_context` remains untouched and the MJ-block scan
  byte-identical.
- **No structure without a reader** — `assemble_tick_context` ships with
  `preview_tick_context.py`; `pt-world-tick` ships with the apply script
  and its v1 version row. No table or column in this brief.
- **Model proposes, code judges** — the template hands out NO structural
  IDs (names only, E1); enforcement lands in -b, but the prompt contract
  is fixed here and -b's normalizer MUST match these payload shapes.
- **History is sacred / single canon write** — this brief writes no canon
  world data; prompt delivery goes through `write_prompt_version` only.

## Done means

- [ ] `python scripts/preview_tick_context.py --npc <existing NPC id>`
      prints a briefing containing, in order: QUI TU ES, TES OBJECTIFS,
      CE QUE TU SAIS, TES RELATIONS, TES AFFILIATIONS, OÙ TU TE TROUVES,
      QUI EST AUTOUR, and the verbatim boundary line.
- [ ] For an NPC holding a secret knowledge row: the row appears prefixed
      `[SECRET] `; for an NPC with a secret membership or a cover_role:
      the TRUE role appears and the membership is prefixed
      `[AFFILIATION SECRÈTE] `.
- [ ] For an NPC with more than 3 active goals: ALL of them appear (no
      dialogue-side cap).
- [ ] `--npc` pointing at a player character or unknown id exits with a
      clear error, nothing printed.
- [ ] `python tooling/verify/checks/npc_goal_read.py` -> PASS with
      tick.py allowlisted.
- [ ] `python tooling/verify/checks/world_tick.py` -> PASS (rules 1-2);
      moving a call to `assemble_tick_context` into context.py locally
      makes it FAIL (spot-check, then revert).
- [ ] `python tooling/verify/checks/single_canon_write.py` -> PASS
      unchanged.
- [ ] `python scripts/apply_ticket_0014_prompt_updates.py` run twice on a
      copy of the live DB: first run writes the `pt-world-tick` head + v1;
      second run reports no-op. `usage="world_tick"` resolvable via the
      `load_analysis_prompt(db, world_id, usage=...)` loader shape.
- [ ] Live delivery (no migration in this brief): `python backup.py` ->
      `python scripts/apply_ticket_0014_prompt_updates.py` on the live DB.
- [ ] /review-step and /close-step run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — new append-only WORLD TICK section logging
  C2, I1, J1, K2, L3, M3, P1, Q1, R3, T1 (amended: full interiority,
  logged exception to secret exclusion, scoped to the creator-gated tick
  surface), Y2, E1, Z3 (decoupled: provenance tag mechanical, is_secret
  dispositional — never coupled), and the J3/F2/I3 deferrals restated.
- `world-engine-schema-changelog.md` — no schema change this brief; note
  the new `usage="world_tick"` template if template usages are catalogued
  there (mirror what 0013 did for `pt-npc-goals`).
- `CLAUDE.md` — one line: `src/world_engine/tick.py` is the sole
  tick-briefing surface; its call sites are allowlisted by
  `verify/checks/world_tick.py`.

---

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **English-bodied prompt** for `pt-world-tick` (French only in quoted
   markers/labels and `{interval_label}` values) — mirrors
   pt-conversation-analysis. Output content will be French because the
   briefing is French.
2. **All active goals in the tick briefing** (no 1-long+2-shorts cap):
   the dialogue cap was a prompt-size bound (S1), not doctrine; the tick
   must see everything active to judge what advanced.
3. **Marker wording locked**: `[SECRET] `, `[AFFILIATION SECRÈTE] `, and
   the section headers as listed — -b's Z3 floor and the queue badge will
   reference these exact strings.
4. **Payload shapes locked in -a** (template ships here): `"other"` for
   relation counterpart, `"recipient":"self"|name` for knowledge. -b's
   normalizer is bound to these.
5. **tick.py does not import from context.py** (helper replicated): keeps
   the tick surface self-contained and the world_tick.py AST rules simple.
