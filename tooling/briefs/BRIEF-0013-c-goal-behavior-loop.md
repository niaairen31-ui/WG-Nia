# BRIEF — Step "NPC goal behaviour loop" (BRIEF-0013-c)

## Context

BRIEF-0013-a (table + injection + CRUD) and BRIEF-0013-b (generator, three
gates) are closed on branch `ticket/0013` — all anchors below are against
that branch (commits `feat(npc-goals): …` of 2026-07-06). This final step
of TICKET-0013 closes the behaviour loop: goals now INFLUENCE the
initiative vote (R1), EVOLVE through `goal_change` proposals under creator
approval (H1/O1/S1), and the dialogue template tells the NPC to pursue
them (D1).

One structural fact discovered at RECON drives the whole H1 design:
`analyze_window` already feeds the analysis model the NPC's
`assembled_context` (analyzer.py:729-737 — `injected_context.assembled_context`
preferred over the raw blob), which since 0013-a CONTAINS the
`TES OBJECTIFS` section. **The analysis model therefore already sees the
NPC's active goals verbatim.** No new plumbing: the rubric instructs exact
copy of the listed goal text, and the apply side matches on it.

## Scope IN

### 1. Initiative-vote signal (R1)

`src/world_engine/cockpit/app.py`, `_npc_initiative_vote`
(app.py:1918):

- Before building signal lines, ONE batched query (same round-trip
  discipline as the relation batch at app.py:1948-1954): all `NpcGoal`
  rows with `npc_id IN npc_ids`, `horizon == "short"`,
  `status == "active"`, ordered `created_at DESC`; reduce in Python to
  the FIRST (most recent) per `npc_id`.
- `_signal_line` (app.py:1964-1967) appends, when that NPC has one:
  `, objectif=« {text} »` — `text` truncated to 80 characters (add `…`
  when cut). Omitted entirely when none. Long-term goals NEVER enter the
  vote (R1).
- `app.py` is already on the `npc_goal_read.py` allowlist (0013-b); no
  check change needed for this item.

### 2. `goal_change` — emit side (H1)

`src/world_engine/analyzer.py`:

- `VALID_MUTATION_TYPES` (analyzer.py:51-60): add `"goal_change"`.
- `_MUTATION_TYPE_MAP` (alias map, analyzer.py:~80-104): map `"goal"`,
  `"goal_change"`, `"goal_update"`, `"objective"`, `"objective_change"`,
  `"goal_completed"`, `"new_goal"` → `"goal_change"`.
- `_TARGET_TABLE_MAP`: `"goal_change"` → `"npc_goal"`.
- `_normalize_to_schema` (analyzer.py:224): new payload branch for
  `goal_change` producing exactly
  `{"npc_id": conv.npc_id, "action": <a>, "goal": <g>}` where:
  - `<a>` = the model's action coerced through a small alias map
    (`completed`/`done`/`accompli` → `complete`;
    `abandoned`/`given_up`/`abandonné` → `abandon`;
    `new`/`create`/`new_short`/`create_short` → `create_short`); any
    other value → drop the item (return None).
  - `<g>` = first of `goal`, `description`, `content`, trimmed; empty →
    drop the item.
  - **`npc_id` is FORCED to `conv.npc_id` in code** — the model never
    chooses the target NPC (its input only ever contains ONE NPC's
    `TES OBJECTIFS`). Structural, not instructional.

### 3. `goal_change` — apply side (H1/O1/S1)

`src/world_engine/cockpit/app.py`, `_apply_mutation` (app.py:825), new
branch placed after `knowledge_change` (app.py:979), following its
find-then-act posture; add the type to the docstring's implemented list
(app.py:833-857):

- Payload guard: `npc_id`, `action`, `goal` all present, else error
  string.
- Normalize the goal text for matching: casefold + whitespace-collapse.
- `complete` / `abandon`: match against the NPC's **ACTIVE goals, both
  horizons** (O1: the model may close any goal) on normalized
  description equality. Exactly one match →
  `write_npc_goal_status(db, goal=row, new_status="completed"|"abandoned",
  changed_by=f"mutation:{mut.id}")` (writes.py:567). No match → error
  `"goal_change: no active goal matching …"` → Needs attention, nothing
  written (knowledge_change posture).
- `create_short`:
  `write_npc_goal(db, world_id=mut.world_id, npc_id=…,
  description=<goal as proposed, un-normalized>, horizon="short",
  changed_by=f"mutation:{mut.id}")` (writes.py:534). **`horizon` is
  hard-coded `"short"` in the branch — the payload carries no horizon
  field and none is read (O1 structural: the model cannot create a
  long-term goal by any input). S1: no active-count check — a third
  active short is written without complaint; the injection's read-side
  LIMIT is the bound.**
- Duplicate guard: extend `_find_applied_duplicate` (app.py:698) —
  `goal_change` is a duplicate when an APPLIED mutation of the same
  conversation has the same `action` and the same normalized `goal`.
  (Unlike `knowledge_change`, which stays excluded per its documented
  rationale at app.py:731 — record the asymmetry in the guard's
  docstring: repeated legitimate `knowledge_change` steps exist;
  a repeated identical goal event in one window does not.)

### 4. Analysis prompt — rubric, shapes, example

`scripts/seed_pilot.py`, `CONVERSATION_ANALYSIS_SYSTEM_PROMPT`
(seed_pilot.py:232):

- Enum line: append `goal_change` to the `mutation_type` list;
  append `npc_goal` to the `target_table` list.
- Payload shapes block: add, verbatim:

  ```
    goal_change      → {"action":"complete|abandon|create_short","goal":"…"}
  ```

- New rubric, placed after the RESOURCE_CHANGE rubric, verbatim
  (French, matching the most recent rubric's language):

  ```
  === GOAL_CHANGE RUBRIC ===
  goal_change — le bloc NPC CONTEXT peut contenir une section
  « TES OBJECTIFS » listant les objectifs actifs du PNJ. Émets un
  goal_change UNIQUEMENT quand la fenêtre contient une preuve claire
  qu'un de CES objectifs listés est accompli ("action":"complete") ou
  définitivement abandonné ("action":"abandon"), ou que le PNJ forme une
  NOUVELLE intention concrète à court terme ("action":"create_short").
  Recopie le texte de l'objectif EXACTEMENT tel qu'il figure dans
  « TES OBJECTIFS » — jamais de paraphrase. Pour create_short, écris le
  nouvel objectif en UNE phrase commençant par un verbe à l'infinitif.
  Parler d'un objectif, ou progresser sans conclure, ne justifie PAS de
  goal_change. Émets AU PLUS UN goal_change par objectif pour toute la
  fenêtre. N'invente jamais d'objectif absent de la section.
  ```

- New example, appended after EXEMPLE 4, verbatim:

  ```
  === EXEMPLE 5 (un objectif listé est accompli) ===
  NPC CONTEXT (extrait) :
  TES OBJECTIFS
  [COURT TERME] Convaincre le forgeron de réparer la herse avant la foire
  Transcript :
  [PNJ] Alors, c'est entendu ? Elle sera réparée avant la foire ?
  [JOUEUR] Le forgeron a accepté ce matin. C'est réglé.
  [PNJ] Enfin ! Voilà un poids en moins.
  Output:
  [{"mutation_type":"goal_change","target_table":"npc_goal","target_id":null,"payload":{"action":"complete","goal":"Convaincre le forgeron de réparer la herse avant la foire"},"rationale":"Le PNJ apprend que la réparation est acquise — l'objectif listé est accompli."}]
  ```

### 5. Dialogue directive (D1)

`scripts/seed_pilot.py`, `NPC_DIALOGUE_SYSTEM_PROMPT`
(seed_pilot.py:1096): insert one section between ATTITUDE and
DISCRÉTION ET NATUREL, verbatim (final wording — locked here per the
ticket):

```
OBJECTIFS.
Ta fiche liste tes objectifs (« TES OBJECTIFS »). Poursuis-les quand la
scène s'y prête — tu peux solliciter, refuser, marchander ou mettre fin à
l'échange si cela les sert — sans jamais en réciter la liste.
```

### 6. Prompt delivery to the live DB

New one-shot script `scripts/apply_ticket_0013_prompt_updates.py`,
mirroring `scripts/apply_ticket_0012_prompt_rewrite.py` exactly (embeds
NO text of its own; imports the two seed constants; compares against
`current_prompt`; appends via `write_prompt_version` with
`note="TICKET-0013 BRIEF-0013-c"`; idempotent, "unchanged" on re-run).
`TOUCHED_HEADS` = `pt-npc-dialogue`, `pt-conversation-analysis`. Run
order documented in the docstring: seed first, then this script.

### 7. Verify updates

`tooling/verify/checks/prompt_lean.py`:

- Rule 5 updated: CONVERSATION_ANALYSIS_SYSTEM_PROMPT now has exactly
  **5** `=== EXEMPLE` markers, zero `=== EXAMPLE` markers, and **four**
  rubric headers (the three existing + `=== GOAL_CHANGE RUBRIC ===`).
- Rule 1 unchanged (the OBJECTIFS section is an addition, not a
  reintroduction of any removed block) — executor confirms it still
  passes.

No `npc_goal_read.py` change: `analyzer.py` handles plain dicts and must
NOT import `NpcGoal`; the apply branch lives in already-allowlisted
`app.py`. If the executor finds themselves adding `analyzer.py` to the
allowlist, the design is being violated.

### 8. Docs — see "Docs to update".

## Scope OUT

- **TICKET-0014 entirely** — off-screen tick, scoped approval, H2
  (`goal_change` emitted by the tick), pre-authorization. This brief's
  `goal_change` is emitted by `analyze_window` ONLY.
- **Multi-NPC goal attribution** — `npc_id` is structurally
  `conv.npc_id`; proposing goal changes for OTHER NPCs present in the
  window (whose `TES OBJECTIFS` the model never sees) is out, by design,
  until a concrete need exists.
- **Model-side long-term goal creation or horizon field in the payload**
  (O1) — the branch hard-codes `short`; do not "future-proof" a horizon
  key.
- **Any write-side cap or replace semantics on shorts** (S1/S3
  rejected) — no cap, no composite "replace goal X" mutation.
- **Vote prompt template text** — `pt-mj-initiative` is untouched; the
  signal line format is code-side (`_signal_line`), consistent with how
  relation/status signals already work.
- **Injection & CRUD & generator** — a and b shipped them; untouched
  here except as read.
- **F2, N3, player goals** — unchanged deferrals.

## Invariants to defend

- **Model proposes, code judges** — every `goal_change` flows through
  `proposed_mutation` and Nia's approval UI; the apply branch writes
  exclusively via the two `writes.py` chokepoints
  (`changed_by=f"mutation:{mut.id}"` — traceable in `change_history`).
- **O1 structurally** — no payload path can create or re-horizon a
  long-term goal; closure of longs is permitted, creation is not.
- **Model never receives structural IDs** — matching is by exact
  description text the model already sees in `TES OBJECTIFS`; no goal
  ids in any prompt.
- **Seed/text discipline (S2 + 0012 pattern)** — seed constants are the
  single source of prompt text; live delivery only through the
  idempotent apply script and `write_prompt_version`; seed never rewrites
  an existing head's text.
- **Better un-applied than wrongly applied** — unmatched or malformed
  `goal_change` → error string → Needs attention, zero writes.
- **H1 substitution norm** — any new substitution uses chained
  `.replace()`.

## Done means

- [ ] In a scene where a candidate NPC has an active short goal, the vote
  prompt's signal list shows `objectif=« … »` on that candidate only
  (inspect via log or preview); NPCs without shorts show no fragment.
- [ ] `python scripts/seed_pilot.py` then
  `python scripts/apply_ticket_0013_prompt_updates.py` appends one new
  version to each of the two heads; running the apply script again
  reports both "unchanged".
- [ ] A conversation window in which the NPC's listed short goal is
  clearly resolved produces a `goal_change` proposal with the goal text
  copied verbatim; approving it flips the goal to `completed` on the
  sheet, with a `mutation:<id>` entry in `change_history`.
- [ ] A `goal_change` proposal whose goal text matches no active goal
  lands in Needs attention with nothing written.
- [ ] A `create_short` approval adds an active short; a crafted payload
  containing `"horizon":"long"` still creates a SHORT (field ignored).
- [ ] Re-approving an identical `goal_change` in the same conversation is
  blocked by the duplicate guard.
- [ ] `tooling/verify/run.py` fully green, including updated
  `prompt_lean.py` (5 EXEMPLE, 4 rubrics) and unchanged
  `npc_goal_read.py`.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — close the "NPC GOALS" section with the
  behaviour loop: R1 short-only vote signal (code-side, 80-char
  fragment); H1 emit/apply with description-text matching (enabled by
  `analyze_window` already carrying `assembled_context`, hence
  `TES OBJECTIFS`); O1 enforced by hard-coded horizon and forced
  `conv.npc_id`; S1 read-side bound restated at the apply site; duplicate
  -guard asymmetry vs `knowledge_change` (with rationale); D1 final
  directive wording. Mark TICKET-0013 complete; note TICKET-0014
  (world-tick) as the named successor with I1/J1/H2 pre-locked.
- `world-engine-schema.md` / changelog — no schema change; add the
  `goal_change` mutation type to wherever the `proposed_mutation` type
  enumeration is documented (same doc convention as `resource_change`).
- `CLAUDE.md` — untouched.
