# QUESTION — TICKET-0111
Trigger: D1-a
## Context
BRIEFs 0111-A, -B, -C are committed (verify checks and corpus gate 144/144 green at each step).
BRIEF-0111-D's embedded diff applies cleanly, its checks pass (conditions, quests, quest_rewards,
debts, creation_island, page_contract, frontend_build_fresh, module_budget, function_length,
decisions_index) and the frontend is rebuilt. It is applied in the working tree but NOT committed.
Stopped before commit because of the brief's own rule: a finding that touches an invariant is a
STOP even if unlisted.
The finding: `quest_reads._steps_view` (the player's quest payload, read by `player_quests` and the
settlement recap) now returns `"completion": verdict_lines(db, completion)`. For a `knowledge` leaf,
`condition_text._target` renders the fact through `prose_render.fact_text` (no scope filter). So a
creator-authored completion such as « Le personnage connaît « <fact> » » shows the fact's full text to
the player, even when the player does not know that fact — it may be an NPC secret or the creator's
note. This touches "Secrets are structurally excluded" / "the player never learns what the character
is not meant to know". Noted ATTENTION at /review-step for B and C; D is where it becomes reachable.
## Question
Should a `knowledge` leaf shown in a player-facing completion line reveal the fact's text only when the
player already holds a Knowledge row on it, and otherwise show a neutral phrase (« quelque chose à
apprendre »)?
## Options
A. Yes — filter by query construction in the player path (`_steps_view` only; creator views and the
   Lore dossier keep full text). Adds a small change to D's diff, then commit and continue.
B. No — the creator's completion text is deliberately player-visible; accept as is.
C. Forbid `knowledge` leaves in a `completion` condition at write time.
## Response
