<!-- slug: quest-review-card -->
# BRIEF 0121-F — "A proposed quest is reviewed in the offer editor -- OfferEditor.svelte extracted, the review card for quest_offer_creation: giver, « Quête unique », the flags, the designer's waiting conditions (B1, E1, E3a, V1; no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: BRIEF-0121-A (`is_character`), BRIEF-0121-E (the payload, `/api/conditions/view`)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0121-E).

- `frontend/src/creation/QuestOffers.svelte` -> the `{#if draft}` block holding, in order: Titre, « Donnée par » (giver select, `draft.contact_entity_id = ''` on change), « Contact de la faction », Résumé, Répétable / État, « Proposée à qui remplit » (`ConditionEditor ... role="eligibility"`), « Étapes » (objective, Coût, Jet, ↑ ↓ ✕, three `ConditionEditor`s), « + étape », the two term lists (`QuestTermRow`), the value line, the save error, « 💾 Enregistrer ».
- `frontend/src/creation/questOffers.svelte.js:47` -> `export function editOffer(offer)`; `:137` `function draftBody(draft)`; `reloadChoices()`; `refreshValue()`.
- `frontend/src/creation/questRequirements.js` -> `conditionDraft(view)`, `blankCondition()`, `conditionBody(cond)`, `REQUIREMENT_FORMS.is_character` (BRIEF-0121-A).
- `frontend/src/creation/ConditionEditor.svelte:16` -> `let { cond, choices, role, emptyLabel, addLabel, unsaved = [] } = $props();`, rendering `<ConditionInterpreter {cond} {role} {unsaved} types={...} />`.
- `frontend/src/creation/ConditionInterpreter.svelte:20` -> `let { cond, role, unsaved = [], types = [] } = $props();` and `const s = $state(interpreterState());`.
- `frontend/src/creation/conditionInterpreter.svelte.js` -> `interpreterState()`, `cardsOf`, `vocabCardsOf` (module functions), `insertProposal(state, cond, unsaved)`, `discardProposal(state)`.
- `frontend/src/creation/QueueCard.svelte:45` -> `const typedEvent = mutation.mutation_type === 'event_creation' && mutation.status === 'proposed'`; the approve path sending `payloadText` (or `payloadFromDraft` for a typed event).
- `src/world_engine/cockpit/routes/conditions.py` -> `POST /api/conditions/view` (BRIEF-0121-E).
- No `frontend/src/creation/OfferEditor.svelte`, no `tooling/verify/checks/quest_review_card.py`.

## Facts carried

### R-14 — saving an offer [M]
Opened: `writes/quests.py:108-170` (`write_quest_offer`); `cockpit/routes/quests.py:50-160` (`OfferStepBody`, `TermBody`, `OfferBody`, `_term`, `_save_offer`, `_mark_drafts`); `quest_reads.py:68-105` (`condition_view`, `offer_dict`); `canon_write_policy.txt:56-57`.
Finding: `write_quest_offer` refuses a missing title, an unknown status, a giver that is not a character or faction of the world, a contact outside the faction, any leaf `clean_condition` refuses, any term `clean_terms` refuses against the giver. `_save_offer` runs `attribute_proposals.materialize` (the proposed attributes) -> `PlanStep`s -> `write_quest_offer` -> `_mark_drafts` (each inserted interpreter draft `saved`), then commits. The policy comment on `write_quest_offer` says « creator CRUD only ».
Consequence: E moves the body classes and `_save_offer`'s core to `cockpit/quest_offer_save.py`, called by the route and by the applier; the policy comment names both callers.

### R-20 — the review card, the queue, the offer editor [M]
Opened: `frontend/src/creation/QueueCard.svelte:1-80` (`typedEvent`, the inline EventEditor precedent), `:200-260`; `Queue.svelte:1-55`; `QuestOffers.svelte:100-200` (the editor, inline); `questOffers.svelte.js:33-175` (`blankStep`, `newDraft`, `editOffer`, `draftBody`, `saveDraft`); `questRequirements.js:190-217` (`conditionDraft`, `blankCondition`, `conditionBody`); `ConditionInterpreter.svelte:20`; `conditionInterpreter.svelte.js:1-60`; `.claude/rules/frontend.md` (INV-49, INV-50, INV-55).
Finding: a typed proposal is edited in place in its card and approved as edited; the offer editor is markup inside `QuestOffers.svelte` bound to `questOffersState.draft`; `editOffer(offer)` reads `offer_dict`'s shape (conditions as `condition_view`s); `draftBody(draft)` gives `OfferBody`'s shape; the interpreter component holds its own state from `interpreterState()`. A child component of `Queue.svelte` is not a Création island.
Consequence: F extracts `OfferEditor.svelte`; G renders `QuestRequests.svelte` inside `Queue.svelte`.


## Contracts

### C-01 — the form `is_character`
Produced by: BRIEF-0121-A   Consumed by: BRIEF-0121-F
`condition_forms.REQUIREMENT_TYPES` ends `..., "event", "is_character"`; `ENTITY_TARGET_TYPES` ends `..., "item_held", "is_character"`. A leaf `RequirementSpec(type="is_character", subject_role="doer", target_entity_id=<character id>)`. Evaluator `_eval_is_character(req, character, db, reachable_ids) -> Verdict(type="is_character", met=character.id == req.target_entity_id, current=character.id, required=req.target_entity_id, reason=..., required_label=<target name>)`. `clean_leaf` refuses an `is_character` leaf whose subject is not the role `doer` (« is_character judges the one who acts »); its target is a `character` of the world. French: `FORM_PHRASES_FR["is_character"] = "{who} est {target}"`; `_BLOCKED_DETAIL_FR["is_character"] = "cette quête est réservée à {required}"`; `TARGET_HINTS_FR["is_character"] = "un personnage, par son nom (le seul à qui l'offre est proposée)"`; `REQUIREMENT_FORMS.is_character = { label: 'Est le personnage', list: 'characters', column: 'entity', threshold: false }`.
Error and empty cases: a fixed subject or another role -> `ValueError`; an unknown or non-character target -> `ValueError` (existing `_clean_target` message).

### C-10 — the `quest_offer_creation` proposal
Produced by: BRIEF-0121-E   Consumed by: F, G
A `ProposedMutation(world_id, source_type="pass_play", pass_play_id=<request's>, mutation_type="quest_offer_creation", target_table="quest_offer", payload=<below>, status="proposed", proposed_by="local_ai_quest_designer", rationale="quest request <id> -- <subject>")`.
Payload -- `OfferBody`'s keys, plus the review's own:
```
{
  "request_id": str, "character_id": str, "subject": str,
  "giver_entity_id": "", "contact_entity_id": null,
  "giver_suggestions": [{"entity_id": str, "name": str, "type": str}],   # 0..3
  "title": str, "summary": str, "repeatable": false, "status": "open",
  "eligibility": <tree dict> | null, "eligibility_draft_id": str | null,
  "steps": [{"objective": str, "cost": 1..4, "domain": str | null,
             "prerequisite": <tree> | null, "completion": <tree> | null, "failure": <tree> | null,
             "prerequisite_draft_id": ..., "completion_draft_id": ..., "failure_draft_id": ...}],
  "terms": [<TermBody dict>],
  "unsaved_attributes": [],
  "pending_drafts": [{"where": "eligibility" | "steps.<i>.<role>", "answer": <the dict `routes/conditions.py::_answer` returns for that draft, plus "instruction" and "role">}],
  "notes": [str],
  "consulted_fact_ids": [str],
  "secret_fact_ids": [str],
  "flags": [{"path": "title" | "summary" | "steps.<i>.objective", "fact_id": str, "words": str}],
  "flags_confirmed": false
}
```
A condition the designer proposed cleanly is in its tree, its `*_draft_id` the draft it came from (outcome `proposed`, so the save marks it `saved`); one that needs a name or was refused has tree `null` and appears in `pending_drafts`.
`prose_guard.flags(db, texts: dict[str, str], fact_ids: list[str]) -> list[dict]`: for each text and each fact, the first run of >= 4 consecutive tokens of `normalize_surface(text)` that is also a run of `normalize_surface(<fact text>)`; `secret_ids(db, world_id, fact_ids) -> list[str]` (R-22's definition).
Applier `cockpit/mutations.py::_mutation_apply_quest_offer_creation(mut, payload, db) -> Optional[str]`: refuses (returns the error) when the request is missing or its `mutation_id` is not `mut.id`; when `giver_entity_id` is empty; when `prose_guard.flags` recomputed on the payload's title, summary and objectives against `secret_fact_ids` is non-empty and `flags_confirmed` is not `true`; when `pending_drafts` is non-empty; on any `ValueError` of `save_offer_body` (the message). Otherwise writes the offer through `save_offer_body(db, world_id, OfferBody.model_validate(<OfferBody keys>), None)`, sets `mut.target_id = offer.id`, `move_request(request, "proposed", offer_id=offer.id)`. Writes nothing on refusal.

### C-13 — the interpreter's reuse points
Produced by: BRIEF-0121-E   Consumed by: C-11, F
- `build_context(..., unsaved=(), extra_fact_ids: tuple[str, ...] = ())`: `extra_fact_ids` first, then what it codes today; the cap unchanged.
- `settle_answer(db, world_id, parsed, ctx, unsaved, retried) -> Interpretation`: the public name of `_answer` (`_answer` stays, delegating, for its two callers).
- `routes/conditions.py::answer_dict(draft, result, db, unsaved) -> dict`: the public name of `_answer` (`_answer` stays, delegating) -- the designer builds each pending condition's answer with it, at proposal time, into the proposal's payload. No route reads a draft back: `ConditionDraft.payload` stays never rendered (`json_ui_boundary.py`).
- `POST /api/conditions/view` `{tree, unsaved_attributes}` -> `condition_view` of the cleaned tree; 422 on a tree `clean_condition` refuses.

### C-14 — the review card and the request panel
Produced by: BRIEF-0121-F (card), BRIEF-0121-G (panel)   Consumed by: Nia
- `frontend/src/creation/OfferEditor.svelte` props `{draft, choices, seeds = {}, onchange}` -- the editor markup of `QuestOffers.svelte` (title to terms and value), bound to `draft`; `seeds[<where>]` an interpreter answer for one condition (`pending_drafts`, C-10), passed to its `ConditionEditor` as `seed`.
- `ConditionEditor` and `ConditionInterpreter` accept `seed` (a `pending_drafts[i].answer` of the payload, C-10): the interpreter opens on it, as after « Interpréter »; « Choisir », « Insérer » and « Écarter » go through the existing draft routes by its `draft_id`.
- `questOffers.svelte.js`: `draftFromProposal(payload, views) -> draft` and `proposalBody(draft, payload) -> payload` (`draftBody(draft)` plus the payload's review keys, `flags_confirmed`).
- `QueueCard.svelte`: a `quest_offer_creation` in `proposed` renders `OfferEditor` (giver from every character and faction, suggestions first), « Quête unique » (adds or removes the leaf `is_character` doer -> `payload.character_id` in the eligibility list), the flags with « Je confirme » (sets `flags_confirmed`), the notes; « Approuver » sends `proposalBody` as the payload. Choosing a giver adds the leaf `has_met` doer -> the giver (the contact when the giver is a faction and a contact is set), once, removable (E1).
- `frontend/src/creation/QuestRequests.svelte`, rendered by `Queue.svelte` above the card list: one row per request -- declaration, day, trigger, status -- with « Concevoir » (`new`, `covered`, rejected), the existence question (`asking`: « Elle existe » + text, « Elle n'existe pas » + text, « Le lore le dit déjà » + entity), « Écrire dans Lore » (`writing_lore`), « Mettre de côté », and a link to its proposal's card.
- `writeState.questRequestId` (`writePanel.svelte.js`): set with `statement` before `navigate('lore')`; `Lore.svelte` opens « Écrire » when it is set; `commit()` sends it as `quest_request_id`, then calls `/design` and clears it.


## Context

B1: the creator reviews a proposed quest in the very editor she uses to
write one. This brief extracts that editor, lets a condition open on the
designer's interpretation when it still waits for her choice, and gives the
review card what only a proposal needs: the giver picked among suggestions
(which adds « a rencontré le donneur », E1), « Quête unique » (E3a), the
passages that repeat a secret and their « Je confirme » (V1).

## Scope IN

**Commit 1 -- pure move: the offer editor.**

1. `frontend/src/creation/OfferEditor.svelte` holds the editor markup of `QuestOffers.svelte`'s `{#if draft}` block from « Titre » to the value line, inclusive, and its helpers (`moveStep`, `giverMembers`), with props `{draft, choices, value, seeds = {}, onchange = () => {}}`; « 💾 Enregistrer » and the save error stay in `QuestOffers.svelte`, which renders `<OfferEditor {draft} {choices} {value} onchange={refreshValue} />` in the same place. Term changes call `onchange` where they called `refreshValue`. Rendering and behaviour of « Quêtes » unchanged; its CSS moves with the markup.

**Commit 2 -- a condition seeded by the designer.**

2. `conditionInterpreter.svelte.js`: `seededState(answer)` = `interpreterState()` with `open: true`, `instruction: answer.instruction || ''`, `proposal: answer`, `cards: cardsOf(answer)`, `vocab: vocabCardsOf(answer)`. `insertProposal` and `discardProposal` take an optional last argument `onsettle` and call it after they succeed.
3. `ConditionInterpreter.svelte`: props gain `seed = null, onsettle = null`; `const s = $state(seed ? seededState(seed) : interpreterState());`; « Insérer » and « Écarter » pass `onsettle`. `ConditionEditor.svelte` props gain `seed = null, onsettle = null`, passed through. `OfferEditor` passes `seed={seeds[where]}` and `onsettle={() => delete seeds[where]}` for `where` in `eligibility`, `steps.<i>.prerequisite`, `steps.<i>.completion`, `steps.<i>.failure`.
4. `questOffers.svelte.js`: `draftFromProposal(payload, views)` -- the draft `editOffer` would build from an `offer_dict`, its conditions `conditionDraft(views[where])` with `draftId` the payload's `*_draft_id`, a `null` tree `blankCondition()`; terms as `editOffer` maps them; `giver_entity_id` the payload's; `id: null`. And `proposalBody(draft, payload, seeds, flagsConfirmed)` -- `draftBody(draft)` plus `request_id, character_id, subject, giver_suggestions, notes, consulted_fact_ids, secret_fact_ids, flags` copied from `payload`, `pending_drafts` = the payload's entries whose `where` is still a key of `seeds`, `flags_confirmed: flagsConfirmed`.

**Commit 3 -- the review card.**

5. `QueueCard.svelte`: `const quest = mutation.mutation_type === 'quest_offer_creation' && mutation.status === 'proposed';`. On mount (once, like `typedEvent`): `reloadChoices()`; for each non-null tree of the payload, `POST /api/conditions/view` -> the view; `draftFromProposal`; `seeds` from `payload.pending_drafts` (`where` -> `answer`). Then it renders, above the JSON toggle:
   - « Donneur » -- the payload's `giver_suggestions` first (« suggéré »), then every giver of `choices.givers`; picking one sets `draft.giver_entity_id` and, when it is a faction, shows « Contact de la faction » as the editor does; it adds ONCE to the eligibility list the row `has_met`, subject `doer`, target the giver (the contact once one is chosen, for a faction) -- an ordinary row the creator may remove; changing the giver moves that row's target, never adds a second;
   - « Quête unique » -- a checkbox; ticked adds the row `is_character`, subject `doer`, target `payload.character_id`; unticked removes it;
   - `<OfferEditor {draft} {choices} {value} {seeds} onchange={...} />`;
   - « Passages qui répètent un secret » -- one line per `payload.flags` entry (`path`, `words`), and the checkbox « Je confirme » (unticked by default);
   - the payload's `notes`, read-only;
   - « Approuver » sends `JSON.stringify(proposalBody(draft, payload, seeds, confirmed))` as the payload; « Rejeter » unchanged. An approval the applier refuses shows its error as for any proposal.
   Every other mutation type: unchanged. The JSON view stays available, collapsed.
6. Rebuild the frontend, commit the build output.
7. New check `tooling/verify/checks/quest_review_card.py` (static text and AST-free regex, the frontend checks' precedent; a pattern that matches nothing fails):
   - **RC1** `OfferEditor.svelte` exists, holds the three `ConditionEditor` roles and `QuestTermRow`; `QuestOffers.svelte` renders `<OfferEditor` and holds no `role="prerequisite"` of its own.
   - **RC2** `ConditionInterpreter.svelte` declares `seed` and `onsettle` props and calls `seededState(`; `conditionInterpreter.svelte.js` exports `seededState`.
   - **RC3** `QueueCard.svelte` names `quest_offer_creation`, renders `<OfferEditor`, posts to `/api/conditions/view`, names `is_character`, `has_met`, `flags_confirmed` and `giver_suggestions`.
   - **RC4** `questOffers.svelte.js` exports `draftFromProposal` and `proposalBody`; `proposalBody` copies `request_id`, `pending_drafts`, `flags`, `flags_confirmed`.
8. `tooling/standards/ARCHITECTURE_DECISIONS.md`: entries above the footer:
   `## ONE OFFER EDITOR FOR CRÉATION AND THE REVIEW CARD (TICKET-0121) -- OfferEditor.svelte (BRIEF-0121-f, no schema change)` (commit 1) and
   `## A PROPOSED QUEST IS REVIEWED IN THE OFFER EDITOR (TICKET-0121) -- THE GIVER, « QUÊTE UNIQUE », THE FLAGS, THE DESIGNER'S WAITING CONDITIONS (BRIEF-0121-f, no schema change)` (commit 3: B1, E1, E3a, V1; the payload edited field by field under the reached « payload » deferral). Regenerate `DECISIONS_INDEX.md`, `FILE_MAP.md`.

## Scope OUT

- Any server change (E did them); the request panel and the Lore hand-off (G).
- A new Création tab or island (INV-50): the card lives in the existing queue.
- Editing an applied offer from the card: Création › Quêtes does that.
- Every later brief of this lot.

## Invariants to defend

- **INV-50** -- no new Création island; `OfferEditor` is a child component.
- **INV-51** -- the review tree component untouched.
- **INV-55** -- the card's one-shot seeding writes `$state` it does not read back in the same `$effect` body.
- **INV-63** -- the card never sets `flags_confirmed` on its own: only the creator's tick does.
- **INV-62** -- untouched: the card is a creator surface.

## Decision rights

STOP:
- an anchor does not hold;
- commit 1 changes what « Quêtes » renders or saves;
- `creation_island.py` or `page_contract.py` requires a registry entry for the card's new markup.
ADAPT:
- `QueueCard.svelte` passes 600 lines: move the quest card's markup into `QuestProposalCard.svelte` rendered by `QueueCard`, report.
- the interpreter component already exposes a different seeding mechanism: use it, report.
REPORT-ONLY:
- any visual rough edge in the card on a narrow window.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `quest_review_card.py` PASS (RC1-RC4); `frontend_build_fresh.py`, `module_budget.py`, `creation_island.py`, `page_contract.py`, `effect_self_write.py`, `quests.py` (QC1, QC2) PASS.
- [ ] Named mutations, red then reverted: render the editor inline again in `QuestOffers.svelte` (RC1); drop `onsettle` from `ConditionInterpreter` (RC2); stop copying `pending_drafts` in `proposalBody` (RC4).
- [ ] `/review-step` then `/close-step` on each of the three commits.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` (two entries), regenerated `DECISIONS_INDEX.md`, `FILE_MAP.md`. No schema change.
