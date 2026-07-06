---
id: TICKET-0012
title: Prompt lean rewrite — resolved facts over conditional instructions, pilot purge
type: feature
status: exec
created: 2026-07-05
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0012-a]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je pense que mes prompts ne sont pas optimisés pour que j'obtienne le
> résultat que je veux, ils sont très longs, ont beaucoup d'instructions et
> d'exemples qui ne sont pas liés directement au contexte de la génération en
> cours (des exemples sur mon monde pilote), on y parle même de magie de façon
> systématique à un endroit. Je pense que les prompts devraient être propres
> et contenir le strict nécessaire. Par exemple au lieu de décrire comment tu
> te comportes en fonction du niveau d'affinité, tu dis qui est là et ton
> comportement lié à ton niveau d'affinité.

## Clarifications resolved (intake)

RECON findings (informal, `main` — anchors verified 2026-07-05):

- **P1** `seed_pilot.py:1077-1102` — `NPC_DIALOGUE_SYSTEM_PROMPT` carries the
  full 5-tier affinity table; the model is asked to read the intensity number
  from its fiche and self-select a tier, while `assemble_npc_context`
  (`context.py:234`) already computes `intensity` in code (and
  `NEUTRAL_INTENSITY = 50`, `context.py:57`, already covers the no-relation
  default the prompt re-explains).
- **P2** `seed_pilot.py:1108` — pricing rules ("RÈGLES DE TARIFICATION") sit
  in the universal system prompt for every NPC; code already gates the tariff
  block itself (`pricing_section`, `context.py:338`, only when `price_list`
  exists).
- **P3** `seed_pilot.py:1103` — "QUESTIONS SUR TES ALLÉGEANCES" hardcodes a
  universal allegiance denial ("tu ne travailles pour personne") that is
  factually wrong for any NPC with a public membership and contradicts the
  TES AFFILIATIONS section.
- **P4** `context.py:205-212` — the atmosphere line
  `"L'atmosphère y est magiquement « {magic_status} »"` (plus attached
  `magic_phenomena`) is injected unconditionally into every NPC context,
  forcing magic vocabulary into every world and every scene.
- **P5** `seed_pilot.py:253,267,326` (`pt-conversation-analysis`) and
  `:397-431` (`pt-mj-narration`), `:532` (`pt-mj-interpretation`) — pilot
  identifiers (`rel-maelis-player`, `npc-maelis`, `npc-senna`, Maelis, Reike,
  Korin, Le Dernier Verre, `local_magic_incidents`) inside `world_id=NULL`
  universal templates; conversation-analysis transcripts in English; 7
  examples where fewer suffice.
- **P6** `seed_pilot.py:950` — a developer synchronization note
  ("doivent rester synchronisées avec MIN_NPCS_PER_FACTION … BRIEF-40")
  is sent to the model as prompt text in `pt-region-manifest`.

Locked decisions:

- **A1** — Code resolves the affinity tier. `context.py` gains a tier →
  directive resolver; the assembled fiche's "COMMENT TU VOIS" section injects
  exactly ONE behavioral directive for the interlocutor (resolved from the
  computed intensity). The 5-tier table and the "assume ~50 if no relation"
  paragraph are removed from `NPC_DIALOGUE_SYSTEM_PROMPT`. Tier directive
  texts live as constants in `context.py` for now.
- **B1** — Pricing rules move out of the universal system prompt and into
  `pricing_section` (`context.py`), rendered only when the NPC has a
  non-empty `price_list`. Same condition as the tariff block itself — a
  relocation, no new logic.
- **C1** — The allegiance-denial paragraph is deleted outright. Public
  memberships (TES AFFILIATIONS) and the `cover_role ?? role` mechanism
  already state structurally what each NPC presents; no universal default
  behavior replaces it.
- **D3** — The magic atmosphere line is removed from `assemble_npc_context`
  entirely (the `atmo` construction and the `magic_phenomena` read attached
  to it). The `values` subculture line stays — independent, non-magical.
  Magic ambience, where a creator wants it, flows through location
  descriptions or knowledge rows (creator prose), never code-imposed.
- **E1** — Universal-template examples are rewritten world-neutral: generic
  names/ids (`npc-a`, `rel-a-player`, "la tenancière", "le garde"),
  transcripts in French. `pt-conversation-analysis` example count reduced
  from 7 to 4: one `relation_change`, one `new_knowledge`, one empty
  multi-turn window, one `resource_change`. All three rubrics (sign,
  anti-inflation, resource_change) are KEPT — they correct observed model
  errors. `pt-mj-narration` and `pt-mj-interpretation` examples neutralized
  the same way.
- **F1** — The 4/4 synchronization parenthesis leaves the
  `REGION_MANIFEST_SYSTEM_PROMPT` text and becomes a Python comment above
  the constant. The density floor itself (the two "au moins 4" rules) stays
  in the prompt.
- **G1 (sequencing)** — TICKET-0012 executes strictly AFTER TICKET-0011 is
  closed. Consequence (S2, locked in 0011): the seed never touches text on
  existing heads, so on Nia's live DB the rewrites MUST land as new
  `prompt_version` rows through the 0011 write path — history preserved,
  current texts retrievable. The seed constants in `seed_pilot.py` are ALSO
  updated to the clean texts so a virgin database gets them as v1. Both
  paths, same final text.

Drafting decisions embedded (flagged per protocol):

1. Affinity tier texts become `context.py` constants — creator editability
   of tier wording is explicitly deferred (named in Scope OUT of the brief
   and in `ARCHITECTURE_DECISIONS.md`), accepted trade-off: resolved
   behavior is mechanics, not creator content, until a concrete need says
   otherwise.
2. Dual-path delivery (live DB via versioning API + virgin DB via seed v1)
   is a direct consequence of S2, not a new decision — but the brief must
   spell out both, or exec will update only the seed and the live DB keeps
   the old text forever.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `NPC_DIALOGUE_SYSTEM_PROMPT` (seed constant) contains none of:
      "ATTITUDE SELON LA RELATION", "RÈGLES DE TARIFICATION",
      "QUESTIONS SUR TES ALLÉGEANCES"  -> verify/checks/prompt_lean.py
- [ ] `context.py` contains no occurrence of "magiquement"; the affinity
      directive resolver exists and is called by `assemble_npc_context`
      -> verify/checks/prompt_lean.py
- [ ] Pricing rules text is emitted only inside `pricing_section`'s
      `price_list` branch  -> verify/checks/prompt_lean.py
- [ ] No `world_id=NULL` seed prompt constant contains any pilot identifier:
      "maelis", "reike", "senna", "korin", "Dernier Verre", "verkhaal"
      (case-insensitive)  -> verify/checks/prompt_lean.py
- [ ] `REGION_MANIFEST_SYSTEM_PROMPT` contains no "synchronis" and no
      "BRIEF-"  -> verify/checks/prompt_lean.py
- [ ] `CONVERSATION_ANALYSIS_SYSTEM_PROMPT` contains exactly 4
      "=== EXAMPLE" markers and all 3 rubric headers
      -> verify/checks/prompt_lean.py

### Live  ->  human gate (Nia)
- [ ] Cockpit prompt preview for a NON-seller NPC shows no pricing rules;
      for a seller NPC, rules + tariffs appear together.
- [ ] An NPC with a public affiliation, asked who they work for, answers
      consistently with TES AFFILIATIONS (no reflexive denial).
- [ ] Low-intensity (<30) and high-intensity (>75) test conversations show
      clearly distinct NPC dispositions (tier resolution works end-to-end).
- [ ] MJ/NPC narration over several turns in a non-magical framing never
      volunteers magic ambience.
- [ ] On the live DB, each touched template head shows the rewrite as a new
      version row with the prior text intact in history.
