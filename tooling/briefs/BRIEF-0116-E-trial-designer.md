<!-- slug: trial-designer -->
# BRIEF 0116-E — "« Concevoir » on a rank trial: the designer proposes it, Nia confirms it"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: BRIEF-0116-C (the `rank` term, `_term`), BRIEF-0116-D (the trial request, `covering_trial_offer`, `trial_subject`)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/writes/quest_requests.py` -> `TRIAL_TRIGGER = "trial"`, `open_trial_request` (D landed); `src/world_engine/quest_requests.py` -> `covering_trial_offer`, `trial_subject` (D landed).
- `src/world_engine/quest_designer.py:36-51` -> `SUBJECT_USAGE`, `DESIGN_USAGE`, `MAX_GIVER_SUGGESTIONS`, `DESIGNER_UNAVAILABLE_MESSAGE`, `OUTCOMES = ("offer", "covered", "unknown")`, `ROLES`, `EXISTENCE_FR`, `NO_STEP_FR`, and `RANK_TERM_FR` (C); `:83-88` `_design_call(db, values, exchanges)`; `:106-113` `_design_values`; `:249-285` `_payload`; `:295-304` `design`; `:307-361` `_design`, its offer path from `notes: list[str] = []` to `return DesignResult("proposed", mutation, payload["notes"])`, the proposal built `source_type="pass_play", pass_play_id=request.pass_play_id`.
- `src/world_engine/cockpit/quest_offer_save.py:139-167` -> `apply_offer_proposal`, its first refusal « La demande de quête de cette proposition est introuvable. ».
- `src/world_engine/cockpit/crud/skills.py:172-184` -> `_masters(db, world_id, *, definition_id, domain) -> list[dict]`; its calls at `:205`, `:214`, `:241`.
- `src/world_engine/skill_access.py:28-30` -> imports `BASE_SKILL_DOMAINS, Skill, SkillDefinition`, `Verdict`, `DEFAULT_RANK, rank_modifier` (and C-02's additions from B).
- `src/world_engine/prompt_registry.py:311-317` -> `"quest_design": PromptSpec(... call_sites=("src/world_engine/quest_designer.py:_design_call",), default_model=_author_model)`.
- `scripts/seed_pilot.py:2351-2422` -> `QUEST_DESIGN_PREAMBLE` (`:2351`), `QUEST_DESIGN_POSTAMBLE` (`:2401`), `_quest_design_system_prompt` (`:2415`) (the slice « FEUILLES. » .. « CONDITION ACTUELLE. »); `:2424-2462` `QUEST_DESIGN_USER_TEMPLATE`; `:2464-2486` `QUEST_DESIGNER_PROMPT_HEADS`; `:3515` its seed loop.
- `scripts/apply_ticket_0121_designer_prompts.py` -> the CREATE-HEAD script looping `seed_pilot.QUEST_DESIGNER_PROMPT_HEADS`.
- `tooling/verify/checks/quest_designer.py:68-80` -> its `Stub` routes `system.startswith("Tu prépares une quête")` to `subject`, anything else to `design`; `:268-278` QD2's exact key set.

## Facts carried

### R-11 — the designer and its applier [M]
Opened: `src/world_engine/quest_designer.py:1-361` (`SUBJECT_USAGE`, `DESIGN_USAGE`, `OUTCOMES` `:43`, `_design_call` `:83-88`, `_design_values` `:106-113`, `_term` `:206-236`, `_payload` `:249-285`, `design` `:295-304`, `_design` `:307-361`); `src/world_engine/cockpit/quest_offer_save.py:139-167` (`apply_offer_proposal`); `src/world_engine/quest_lore.py` (`gather_lore(db, world_id, *, keywords, names, entity_ids=(), lore_entry_id=None)`, C-05 of 0121).
Finding: `_design` runs `quest_subject`, `gather_lore`, the existence check (`asking`), one `quest_design` call, its `covered`/`unknown` answers, then the offer path (steps, `_settle`, one retry with the errors, notes, `_payload`, the proposal `source_type="pass_play", pass_play_id=request.pass_play_id`, `move_request(proposed)`); 55 lines. `_term` drops an unknown currency with a note. `_payload` sets `repeatable: False` and exactly C-10's keys. `apply_offer_proposal` refuses a request missing or not this proposal's, no giver, unconfirmed flags, pending conditions, a refused save; it then writes through `save_offer_body` and moves the request.
Consequence: `_design` dispatches a `trial` request to its own path; the offer path is extracted unchanged into `_offer` for both; the applier gains one refusal for a trial whose terms lost the rank reward.

### R-12 — prompts [M]
Opened: `src/world_engine/prompt_registry.py:300-317`; `scripts/seed_pilot.py:2320-2486`, `:3515`; `scripts/apply_ticket_0121_designer_prompts.py:1-55`; `tooling/verify/checks/prompt_registry.py` docstring (rule 1: usages seeded in `seed_pilot.py` == registry keys; rule 2: each call site's `def` exists).
Finding: a usage is a registry entry, a seed head and a CREATE-HEAD script relying on `upsert_prompt_template`'s idempotence (S2).
Consequence: `quest_trial` (its own system prompt, the design's user template and variables), `QUEST_TRIAL_PROMPT_HEADS`, its seed loop line and `apply_ticket_0116_trial_prompt.py`.

### R-13 — a proposal's source and the queue [M]
Opened: `src/world_engine/models/pipeline.py:98-150` (`ProposedMutation`: no CHECK, `source_type` free text, three nullable sources); `src/world_engine/cockpit/routes/mutations.py:250-286`, `:366-402` (`_find_applied_duplicate`: no `conversation_id` -> the tick branch, which returns None without a `tick_id`), `:106-123` (`_mutation_dict`).
Finding: the `source_type` values written today are `pass_play`, `world_tick`, `conversation`. A proposal with no source shows no badge and no `sourceRef` in the card.
Consequence: a trial's proposal is `source_type="quest_request"` with no day; nothing branches on it but the card's badge (F).

### R-17 — the existing checks (the lines this brief needs) [M]
- `quest_designer.py:68-80` (the stub's routing), `:268-278` (QD2: a route request's payload keys exactly C-10's), `:494-497` (QD8: `quest_subject`, `quest_design` on `_author_model`).
- `knowledge_identity.py:31-35`, `:109-125` (K3: per-file `subject` census, `quest_designer.py` 10).
- `name_index.py` R5 (`CREATOR_ALLOWED` names `quest_designer.py` and `quest_lore.py`; the creator name regime used anywhere else is red).

### R-20 — module sizes [M] (the modules this brief edits)
`quest_designer.py` 20/361 (`_design` 55); `cockpit/quest_offer_save.py` 5/167; `skill_access.py` 7/116 (+ B's two); `cockpit/crud/skills.py` 24/667; `prompt_registry.py` 3/409.

### R-21 — who masters a skill [M]
Opened: `src/world_engine/cockpit/crud/skills.py:172-184` (`_masters`: the world's characters at `MAX_RANK` in one skill, `{id, name}` by name; three callers); `src/world_engine/skill_access.py:1-116`.
Consequence: `_masters` moves, unchanged but its name, to `skill_access.skill_masters` for the designer (a pure move, its own commit); no check names it (`grep -rn "_masters" tooling/verify/checks`: empty).

## Contracts

### C-07 — the trial request (consumed)
- `TRIAL_TRIGGER = "trial"` (`writes/quest_requests.py`); a trial request has `skill_key`, `target_rank`, `subject`, `declaration`, no day, no step.
- `covering_trial_offer(db, world_id, skill_key, target_rank) -> Optional[QuestOffer]`; `trial_subject(db, world_id, skill_key, target_rank) -> str` (`quest_requests.py`).

### C-05 — the `rank` currency (consumed)
- A `rank` term row: `{"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None, "fact_id": None, "skill_key": <key>, "amount": <rank>, "level": None}`.
- `quest_designer._term` drops a model's `rank` term with `RANK_TERM_FR`.

### C-08 — « Concevoir » on a trial
Produced by: BRIEF-0116-E   Consumed by: F
- `skill_access.skill_masters(db, world_id, *, definition_id, domain) -> list[dict]` -- `cockpit/crud/skills.py::_masters` moved, body unchanged; the crud's three calls renamed.
- `quest_designer`: `TRIAL_USAGE = "quest_trial"`; `_design_call(db, values, exchanges, usage=DESIGN_USAGE, outcomes=OUTCOMES)` (an outcome outside `outcomes` -> `LlmParseError`); `_design` dispatches `request.trigger == TRIAL_TRIGGER` to `_design_trial`; the offer path, from its steps to its `move_request(proposed)`, is `_offer(db, request, subject, gathering, context, ctx, answer, design_calls, usage, outcomes) -> DesignResult` (extracted unchanged for the normal path).
- `_design_trial(db, request, design_calls)`: `covering_trial_offer` -> `move_request(covered, offer_id)`, `DesignResult("covered", notes=[f"Déjà couverte par « {offer.title} »."])`, no model call; else `subject = request.subject`, `gathering = gather_lore(db, world_id, keywords=<the skill's label, then its system's name when it has one>, names=[], entity_ids=<the ids of skill_masters>)`, never `asking`; one `quest_trial` call (`outcomes=("offer",)`), then `_offer`.
- A trial's payload: C-10 of 0121's keys, then `"repeatable": True`, its `terms` = the resolved terms followed by `{"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None, "fact_id": None, "skill_key": request.skill_key, "amount": request.target_rank, "level": None}`, and one more key `"trial": {"skill_key", "target_rank", "skill_label", "rank_label"}`. A non-trial payload is unchanged (QD2).
- The proposal: `source_type="pass_play", pass_play_id=request.pass_play_id` when the request has a day; `source_type="quest_request"`, no source otherwise.
- `apply_offer_proposal`, after the request check: a `trial` request whose payload's terms hold no reward `rank` term with its `skill_key` and `target_rank` -> `"Cette épreuve doit garder sa récompense de rang."`, nothing written.
- Prompt `quest_trial`: `PROMPT_REGISTRY["quest_trial"] = PromptSpec(surface="authoring", world_scoped=False, dry_run_capable=True, call_sites=("src/world_engine/quest_designer.py:_design_call",), default_model=_author_model)`; `seed_pilot.QUEST_TRIAL_PREAMBLE` (verbatim in Scope IN), `_quest_trial_system_prompt()`, `QUEST_TRIAL_SYSTEM_PROMPT`, `QUEST_TRIAL_PROMPT_HEADS` (head `pt-quest-trial`, the design's user template and variables); `scripts/apply_ticket_0116_trial_prompt.py`.

## Context

F1: the designer of TICKET-0121 writes the trial; Nia reviews, edits and
confirms it in the review card. A trial request needs no subject call and
no existence question -- the skill exists --; it needs its own framing,
the lore of the skill and of those who master it, and the rank reward added
by the code, never by the model. The applier keeps that reward on approval.

## Scope IN

**Commit 1 -- pure move.**
1. `cockpit/crud/skills.py::_masters` moves to `src/world_engine/skill_access.py` as `skill_masters(db: Session, world_id: str, *, definition_id: Optional[str], domain: Optional[str]) -> list[dict]`, its body and docstring verbatim (the docstring's « (C1) » becomes « (TICKET-0107 C1; moved here, TICKET-0116) »); `skill_access` imports `Entity` from `.models` and `MAX_RANK` from `.skill_ranks`; `crud/skills.py` imports `skill_masters` from `...skill_access` and its three calls become `skill_masters(...)` with the same arguments; nothing else changes. `npc_skills.py` and `skill_progression.py` pass unchanged.

**Commit 2 -- the trial path.**
2. `src/world_engine/quest_designer.py` -- C-08:
   - constants `TRIAL_USAGE = "quest_trial"` and `TRIAL_OUTCOMES = ("offer",)` beside `DESIGN_USAGE`/`OUTCOMES`;
   - `_design_call(db, values, exchanges, usage=DESIGN_USAGE, outcomes=OUTCOMES)`: `prompt_call.call_json(db, usage, values, exchanges, chat)`, the outcome refusal `LlmParseError(f"{usage}: outcome {parsed.get('outcome')!r} is not one of {outcomes}")` (the design's message is unchanged: `usage` is `quest_design` there);
   - `_offer(db, request, subject, gathering, context, ctx, answer, design_calls, usage, outcomes) -> DesignResult`: the lines of `_design` from `notes: list[str] = []` to its last `return`, moved unchanged except: the retry's `_design_call(..., design_calls, usage, outcomes)` and its message `f"{usage}: the corrected answer is no offer"`; after `payload = _payload(...)`, `if request.trigger == TRIAL_TRIGGER: payload = _trial_payload(db, request, payload)`; the proposal's source per C-08 (`pass_play` with its id when `request.pass_play_id`, else `source_type="quest_request"` and no source id). `_design` ends `return _offer(db, request, subject, gathering, context, ctx, answer, design_calls, DESIGN_USAGE, OUTCOMES)` and starts `if request.trigger == TRIAL_TRIGGER: return _design_trial(db, request, design_calls)`;
   - `_design_trial(db, request, design_calls)` -- C-08, in this order: `covering_trial_offer`; `subject = request.subject`; `gathering = gather_lore(...)` with `_trial_keywords(db, request.skill_key)` (the skill's `skill_label`, then the name of its definition's system when it has one) and the ids of `skill_masters(db, world_id, definition_id=<key unless a base domain>, domain=<key when a base domain>)`; `instruction = f"{request.declaration} {subject}"` and the same `context()` closure as `_design`; one `_design_call(..., design_calls, TRIAL_USAGE, TRIAL_OUTCOMES)`; `_offer(..., TRIAL_USAGE, TRIAL_OUTCOMES)`;
   - `_trial_payload(db, request, payload) -> dict` -- C-08's three changes (`repeatable` True, the rank term last, the `trial` key with `skill_label(db, key)` and `world_ladder(db, world_id)[target_rank].label`);
   - imports: `TRIAL_TRIGGER` from `.writes.quest_requests`; `covering_trial_offer` from `.quest_requests`; `skill_label`, `skill_masters` from `.skill_access`; `world_ladder` from `.skill_ranks`; `SkillDefinition`, `SkillSystem` from `.models`.
   - The module docstring gains: « A rank trial's request (TICKET-0116, F1) skips the subject call and the existence question: an open offer that already gives the rank covers it; otherwise the lore of the skill and of its masters is read, one `quest_trial` call writes the offer, and the code adds the rank reward, makes it repeatable (H1) and sources the proposal `quest_request`. » Every function stays <= 80 lines.
3. `src/world_engine/cockpit/quest_offer_save.py`, `apply_offer_proposal` -- C-08's refusal right after the request check, through a private `_keeps_trial_rank(payload, request) -> bool` (a term dict with `direction` `reward`, `currency` `rank`, the request's `skill_key` and `amount == target_rank`); import `TRIAL_TRIGGER` from `..writes.quest_requests`. Its docstring's list of refusals gains « a rank trial's offer without its rank reward (TICKET-0116) ».
4. `src/world_engine/prompt_registry.py`: after `"quest_design"`, the entry of C-08, its comment `# TICKET-0116 (BRIEF-0116-E): a rank trial's offer -- the design's answer under a preamble of its own.`
5. `scripts/seed_pilot.py`, after `QUEST_DESIGNER_PROMPT_HEADS`:
   ```python
   # ----- prompt template: a rank trial's offer (TICKET-0116, BRIEF-0116-E) -----
   # usage "quest_trial": the offer of a rank trial -- the design's answer
   # shape, user template and condition language (the same slice of
   # CONDITION_INTERPRET_SYSTEM_PROMPT), under a preamble of its own. Called
   # by quest_designer._design_call for a request whose trigger is `trial`.
   QUEST_TRIAL_PREAMBLE = """\
   Tu conçois une épreuve de rang pour un jeu de rôle. Un personnage joueur a \
   assez pratiqué une compétence pour passer au rang suivant, mais dans ce monde \
   ce rang se mérite : il faut une épreuve, c'est-à-dire une quête qui montre \
   qu'il en est digne. On te donne la compétence, le rang visé, et tout ce que \
   le lore du monde en dit -- y compris des secrets que le joueur ignore et que \
   seules quelques personnes connaissent.

   TON TRAVAIL. "outcome" vaut toujours "offer" : tu proposes l'épreuve.

   L'ÉPREUVE. Elle met la compétence à l'épreuve, à la mesure du rang visé, \
   selon ce que le lore dit de cette compétence et de ceux qui la maîtrisent : \
   une œuvre à réussir, un adversaire, un maître à convaincre, un lieu ou un \
   objet à atteindre, un serment à tenir. Chaque étape a :
   - "objective" : ce que le personnage fait, en une phrase, vu du joueur. \
   Un objectif, le titre et le résumé nomment l'action ; le contenu d'un fait \
   secret ou réservé à la créatrice reste dans les conditions, par son code ;
   - "cost" : de 1 à 4, les moments de journée qu'elle demande ;
   - "domain" : null, ou "physical", "agility", "perception", "composure" quand \
   elle demande un jet ;
   - "prerequisite" (ce qu'il faut pour la tenter), "completion" (quand son \
   objectif est atteint), "failure" (quand elle a échoué) : chacune null ou une \
   condition (voir CONDITIONS).
   "eligibility" : à qui l'offre est proposée ; null le plus souvent (seul un \
   personnage prêt pour ce rang la reçoit, et la créatrice ajoute la rencontre \
   du donneur).
   "title" et "summary" : ce que le joueur lira de l'offre.
   "givers" : jusqu'à trois noms de personnages ou de factions du monde qui \
   pourraient la donner -- d'abord un maître de cette compétence quand le lore \
   en nomme un, puis les plus plausibles.
   "terms" : ce que l'épreuve coûte et rapporte en plus du rang, chacun \
   {"direction": "cost" | "reward", "currency": "money" | "item" | "relation" | \
   "fact" | "skill", "target": un nom d'objet ou de personnage, un code de fait \
   "f3" ou de compétence "s1", ou null pour la monnaie, "amount": un entier pour \
   la monnaie, l'objet ou la relation, sinon null, "level": null}. Le rang \
   lui-même est ajouté par le moteur : ne le mets pas dans "terms".
   "notes" : ce que tu veux signaler à la créatrice -- notamment un fait du \
   lore que personne ne sait encore.

   CONDITIONS. Chaque condition est un objet {"phrase": la condition en une \
   phrase française, "condition": l'arbre, "define": [], "define_events": [], \
   "define_sortes": [], "unsupported": []} ; l'arbre et les trois listes \
   "define" suivent le langage ci-dessous. Une feuille sur le personnage a \
   "subject": "doer".


   """


   def _quest_trial_system_prompt() -> str:
       language = CONDITION_INTERPRET_SYSTEM_PROMPT
       start = language.index("FEUILLES.")
       end = language.index("CONDITION ACTUELLE.")
       return QUEST_TRIAL_PREAMBLE + language[start:end] + QUEST_DESIGN_POSTAMBLE


   QUEST_TRIAL_SYSTEM_PROMPT = _quest_trial_system_prompt()

   QUEST_TRIAL_PROMPT_HEADS = (
       dict(
           id="pt-quest-trial",
           name="Concepteur de quêtes — l'épreuve de rang",
           usage="quest_trial",
           world_id=None,
           system_prompt=QUEST_TRIAL_SYSTEM_PROMPT,
           user_template=QUEST_DESIGN_USER_TEMPLATE,
           variables=["character_name", "declaration", "subject", "existence", "lore", "forms", "entity_types",
                      "entities", "facts", "offers", "skills", "attributes", "event_types", "sortes", "errors"],
           destination="local",
       ),
   )
   ```
   and, right after the `for entry in QUEST_DESIGNER_PROMPT_HEADS:` loop of `seed()` (`:3515`), the same loop over `QUEST_TRIAL_PROMPT_HEADS`, comment `# TICKET-0116 (BRIEF-0116-E)`.
6. `scripts/apply_ticket_0116_trial_prompt.py` -- `apply_ticket_0121_designer_prompts.py` with its docstring's names and ticket changed (« the TICKET-0116 rank trial's prompt head (quest_trial) ... BRIEF-0116-E ») and its loop over `seed_pilot.QUEST_TRIAL_PROMPT_HEADS`; nothing else.
7. `tooling/verify/checks/rank_trials.py` -- its docstring gains, and `main()` runs after TD, these rules; the model is a stub assigned to `quest_designer.chat` (the `quest_designer.py` precedent), routing a call by its system prompt: « Tu conçois une épreuve de rang » -> `trial`, « Tu prépares une quête » -> `subject`, anything else -> `design`; the fixture seeds `QUEST_DESIGNER_PROMPT_HEADS` and `QUEST_TRIAL_PROMPT_HEADS` through `seed_pilot.upsert_prompt_template`:
   - **TE1** -- the design (fixture: a world whose rank 1 asks a trial; player P whose `agility` became ready -- the request opened by D --; a Maître, Orsa, in `agility` -- a base row at rank 5 -- and a fact « Orsa forge des lames à Valmor » whose participant is Orsa, known by her). a. With an open offer giving `rank` agility 2: `design` -> `covered`, the request `covered` with that `offer_id`, zero stub calls; the offer then closed (`status='closed'`) and the request moved back to `new`. b. `design` with a scripted `offer` (one step, one `money` cost, givers [« Orsa »], and a `rank` term the model should not have written): one stub call, routed `trial`, its user message holding P's declaration and Orsa's fact; one `quest_offer_creation` proposal by `local_ai_quest_designer`, `source_type` `quest_request`, `pass_play_id` None; its payload's keys are QD2's set plus `trial`; `repeatable` True; its last term is the C-05 rank row for (`agility`, 2) and it holds no other `rank` term; `RANK_TERM_FR` is among its notes; `trial` is `{"skill_key": "agility", "target_rank": 2, "skill_label": "agility", "rank_label": "Apprenti"}`; one giver suggestion, Orsa; the request `proposed` with its `mutation_id`. c. A request whose scripted answer is `covered` -> `LlmParseError`, no proposal written, the request unchanged.
   - **TE2** -- the applier (fixture, continued). Approving TE1b's proposal with a giver and its terms without the rank row -> the proposal `approved` with « Cette épreuve doit garder sa récompense de rang. », no offer written; approving it again with the rank row -> `applied`, one offer whose terms end with the rank reward, `repeatable` True, the request's `offer_id`; `available_offers(P)` lists it; a player whose agility does not wait does not see it.
   - **TE3** -- static. `PROMPT_REGISTRY["quest_trial"]` is `authoring`, on `_author_model`, its call site `src/world_engine/quest_designer.py:_design_call`; `seed_pilot.QUEST_TRIAL_PROMPT_HEADS` holds one head `pt-quest-trial`, usage `quest_trial`, its `user_template` the design's, its system prompt starting « Tu conçois une épreuve de rang » and holding « FEUILLES. »; `scripts/apply_ticket_0116_trial_prompt.py` exists and names `QUEST_TRIAL_PROMPT_HEADS`; `cockpit/crud/skills.py` defines no `_masters` and calls `skill_masters(` three times.
8. K3 of `knowledge_identity.py` -- see Decision rights, ADAPT.
9. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the footer, two records, headers verbatim:
   - `## WHO MASTERS A SKILL IS READ IN ONE PLACE (TICKET-0116) -- skill_access.skill_masters (BRIEF-0116-e, no schema change)` -- the pure move, its reason (the designer is its second reader, R6: no copy).
   - `## THE DESIGNER PROPOSES A RANK TRIAL, NIA CONFIRMS IT (TICKET-0116) -- quest_trial, _design_trial, the rank reward kept (BRIEF-0116-e, no schema change)` -- F1, G1 (masters read as lore and suggested first, never required), H1 (repeatable), the code adds the rank reward and the model never writes one, the proposal sourced `quest_request` (no day), the applier keeps the reward, `_offer` shared by both paths.
   Then `gen_decisions_index.py`, `gen_file_map.py`.

## Scope OUT

- Any frontend change (F: the card's badge, the trial line, `REVIEW_KEYS`).
- A second model call for a trial's subject; the existence question for a trial (F1-b).
- Inventing a giver (D2 of 0121, deferred and watched).
- Changing 0121's path for a step request: QD1-QD8 must pass unchanged.
- A trial over a system (E2); a failure that costs points (H2).
- Amending INV-63: the trial's refusal is enforced by TE2, not by law (lot drafting decision 7).

## Invariants to defend

- **INV-01** -- the designer reads the lore in the creator regime it already holds (`quest_designer.py`, `quest_lore.py` in `CREATOR_ALLOWED`); no new module uses it.
- **INV-14** -- `local_ai_quest_designer` is the producer, already in `PRODUCERS`; never auto-applied: the proposal waits in the queue.
- **INV-19** -- the new usage resolves through `effective_model`: a registry entry, called through `prompt_call.call_json`.
- **INV-22** -- the model names facts by code; the rank reward is the code's, never parsed from the model.
- **INV-63** -- the applier's existing refusals stay first and unchanged; the trial refusal adds to them.

## Decision rights

STOP:
- an anchor does not hold;
- QD1-QD8 of `quest_designer.py` go red after commit 2 (the extraction changed 0121's path);
- `_offer` cannot be extracted without changing a line of the offer path other than the four named in item 2.
ADAPT:
- K3 of `knowledge_identity.py` reports a census mismatch on exactly the files this brief edits (`quest_designer.py`, `skill_access.py`, `cockpit/quest_offer_save.py`): set those entries of `_SUBJECT_CENSUS` to the counts measured (a file reaching 0 is removed), under the comment `# TICKET-0116, BRIEF-0116-E: a trial request's subject -- never a knowledge key.`; report the numbers. A mismatch on any other file is a STOP.
- `rank_trials.py` runs over 12 s locally after TE: move TE1-TE3 into `tooling/verify/checks/rank_trial_designer.py` (same fixture idiom, its own docstring and `PASS:` line), and list it in the ticket's Machine-checkable section beside `rank_trials.py`; report the timings.
REPORT-ONLY:
- a `quest_offer_creation` proposal of a `trial` request already in a database (none can exist before this brief).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit 1: `npc_skills.py`, `skill_progression.py`, `module_budget.py` -> `PASS`; `git diff` of the moved body shows only the name and its docstring's parenthesis.
- [ ] `python tooling/verify/checks/rank_trials.py` -> `PASS` (TB to TE).
- [ ] Named mutations, each red then reverted: `_trial_payload` not appending the rank term -> TE1 red; the trial dispatch removed from `_design` -> TE1 red (a subject call is made); `_keeps_trial_rank` always True -> TE2 red; the proposal sourced `pass_play` for a trial -> TE1 red; `QUEST_TRIAL_PROMPT_HEADS` emptied -> TE3 red.
- [ ] `quest_designer.py` (QD1-QD8), `prompt_registry.py`, `name_index.py`, `proposal_producers.py`, `knowledge_identity.py`, `quest_review_card.py`, `json_ui_boundary.py`, `module_budget.py`, `function_length.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] `/review-step` then `/close-step` on each commit.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 9); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change. The live gate runs `apply_ticket_0116_trial_prompt.py` (the ticket's Live section).
