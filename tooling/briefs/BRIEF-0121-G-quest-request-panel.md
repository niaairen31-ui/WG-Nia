<!-- slug: quest-request-panel -->
# BRIEF 0121-G — "« Demandes de quête » above the review queue -- design a request, answer the existence question, write it in Lore and come back (L1, N1; no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: BRIEF-0121-E (the request routes, the Lore commit's `quest_request_id`), BRIEF-0121-F (the card a request's proposal opens in)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0121-F).

- `frontend/src/creation/Queue.svelte` -> `<h2>Review Queue</h2>` then the batch verdict, then `{#each queueState.mutations as m (m.id)}` / `<QueueCard ...>`.
- `frontend/src/lib/router.js` -> `export function navigate(surface, subTab)`.
- `frontend/src/lore/Lore.svelte:30` -> `let loreTab = $state('question');` and the three tab buttons (`question`, `names`, `write`).
- `frontend/src/lore/writePanel.svelte.js:63` -> `export const writeState = $state(blank());`, `blank()` holding `statement`; `:357` `export function commit()` posting `{ proposal: toProposal(), attempt_id: writeState.attemptId }`.
- `src/world_engine/cockpit/routes/quest_requests.py` -> `GET /api/quest-requests`, `POST .../{id}/design`, `.../answer`, `.../drop` (BRIEF-0121-E); `routes/lore_write.py` `CommitBody.quest_request_id`.
- `GET /api/quest-offers/choices` -> lists `characters`, `locations`, `factions`, `items`.
- No `frontend/src/creation/QuestRequests.svelte`, no `frontend/src/creation/questRequests.svelte.js`, no `tooling/verify/checks/quest_request_panel.py`.

## Facts carried

### R-18 — the Lore writing panel [M]
Opened: `cockpit/routes/lore_write.py:1-75` (docstring, `StatementBody`, `CommitBody {proposal, attempt_id}`), `:140-160` (`write_commit` returns `{ok, entry_id, written, skipped}`); `models/pipeline.py:418-428` (`LoreEntry`); `frontend/src/lore/writePanel.svelte.js:63` (`writeState`), `:357-367` (`commit`); `frontend/src/lore/Lore.svelte:30` (`let loreTab = $state('question')`).
Finding: the commit writes everything in one transaction through `lore_write_apply.apply_proposal`; the panel's tab is local state of `Lore.svelte`; `writeState.statement` holds the text.
Consequence: the commit accepts an optional `quest_request_id` and links the entry to the request in its transaction; the panel opens pre-filled through `writeState`.

### R-20 — the review card, the queue, the offer editor [M]
Opened: `frontend/src/creation/QueueCard.svelte:1-80` (`typedEvent`, the inline EventEditor precedent), `:200-260`; `Queue.svelte:1-55`; `QuestOffers.svelte:100-200` (the editor, inline); `questOffers.svelte.js:33-175` (`blankStep`, `newDraft`, `editOffer`, `draftBody`, `saveDraft`); `questRequirements.js:190-217` (`conditionDraft`, `blankCondition`, `conditionBody`); `ConditionInterpreter.svelte:20`; `conditionInterpreter.svelte.js:1-60`; `.claude/rules/frontend.md` (INV-49, INV-50, INV-55).
Finding: a typed proposal is edited in place in its card and approved as edited; the offer editor is markup inside `QuestOffers.svelte` bound to `questOffersState.draft`; `editOffer(offer)` reads `offer_dict`'s shape (conditions as `condition_view`s); `draftBody(draft)` gives `OfferBody`'s shape; the interpreter component holds its own state from `interpreterState()`. A child component of `Queue.svelte` is not a Création island.
Consequence: F extracts `OfferEditor.svelte`; G renders `QuestRequests.svelte` inside `Queue.svelte`.


## Contracts

### C-02 — `quest_request` (v2.28) and its writer
Produced by: BRIEF-0121-B   Consumed by: D, E, G
Table `quest_request` in `models/pipeline.py`:
`id` TEXT PK; `world_id` FK world NOT NULL; `character_id` FK entity NOT NULL; `pass_play_id` FK pass_play NOT NULL; `agenda_step_id` FK agenda_step NOT NULL; `trigger` TEXT NOT NULL; `declaration` TEXT NOT NULL; `subject` TEXT NULL; `status` TEXT NOT NULL DEFAULT `'new'`; `existence_answer` TEXT NULL; `creator_text` TEXT NULL; `existing_entity_id` FK entity NULL; `lore_entry_id` FK lore_entry NULL; `mutation_id` FK proposed_mutation NULL; `offer_id` FK quest_offer NULL; `note` TEXT NULL; `created_at`, `updated_at` (`_created_ts()`); `change_history` JSON NOT NULL DEFAULT `'[]'`.
CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped')`; `ck_quest_request_status` `status IN ('new','asking','writing_lore','proposed','covered','dropped')`; `ck_quest_request_answer` `existence_answer IS NULL OR existence_answer IN ('exists','absent','already')`.
Indexes: `idx_quest_request_world` (`world_id`, `created_at`); `idx_quest_request_step` UNIQUE (`agenda_step_id`): one request per step.
Constants in `writes/quest_requests.py`: `QUEST_REQUEST_TRIGGERS = ("route", "blocked", "dropped")`, `QUEST_REQUEST_STATUSES = ("new", "asking", "writing_lore", "proposed", "covered", "dropped")`, `EXISTENCE_ANSWERS = ("exists", "absent", "already")`, `QUEST_OFFER_CREATION = "quest_offer_creation"`, `DESIGNER_PRODUCER = "local_ai_quest_designer"`.
Writer:
- `open_request(db, *, world_id, character_id, pass_play_id, trigger, declaration, agenda_step_id) -> QuestRequest` -- `ValueError` on an unknown trigger, an empty declaration, a missing step; a step that already has a request returns that request unchanged (idempotent per step). Adds and flushes, never commits.
Reads in `src/world_engine/quest_requests.py`: `inquiry_step_ids(db, agenda_id) -> frozenset[str]` -- the `agenda_step_id`s of the requests on that agenda's steps whose trigger is `route` or `dropped`.
- `move_request(db, request, status, **fields) -> QuestRequest` -- appends `{status, updated_at, <every field it changes, before>}` to `change_history`, then sets `status`, `updated_at` and the given fields (only `subject`, `existence_answer`, `creator_text`, `existing_entity_id`, `lore_entry_id`, `mutation_id`, `offer_id`, `note`); `ValueError` on an unknown status, an unknown field, an answer outside `EXISTENCE_ANSWERS`. Never commits.
Status meanings: `new` -- waits for « Concevoir »; `asking` -- the subject is unknown, the existence question is shown; `writing_lore` -- answered `exists` or `absent`, the Lore panel is open for it; `proposed` -- a `quest_offer_creation` (`mutation_id`) exists; whether it was approved or rejected is that row's `status`, never a second column; `covered` -- an open offer already covers it (`offer_id`); `dropped` -- the creator set it aside. Re-design is allowed from `new`, `covered`, and `proposed` when its proposal is `rejected`; refused otherwise (C-12).

### C-12 — the request routes
Produced by: BRIEF-0121-E   Consumed by: G
`cockpit/routes/quest_requests.py`, every POST behind the origin guard like every write route:
- `GET /api/quest-requests` -> `[{id, trigger, status, declaration, subject, character_name, day_number, existence_answer, creator_text, note, created_at, proposal: {id, status} | null, offer: {id, title} | null}]`, newest first, the active world, `dropped` excluded.
- `POST /api/quest-requests/{id}/design` -> runs C-11, commits, returns the request dict plus `{outcome, notes}`; 409 when re-design is not allowed (C-02); 503 `DESIGNER_UNAVAILABLE_MESSAGE` on `OllamaError`; 502 on `LlmParseError`.
- `POST /api/quest-requests/{id}/answer` `{answer: "exists" | "absent" | "already", text: str, entity_id: str | null}` -> `asking` only (409 otherwise); `exists`/`absent` -> `writing_lore`, `creator_text`; `already` needs an entity of the world -> `new`, `existing_entity_id`; returns `{request, statement}` where `statement` is the Lore panel's pre-filled text (`exists`: `"<subject> : <text>"`; `absent`: `"<subject> n'existe pas dans ce monde. <text>"`; `already`: null).
- `POST /api/quest-requests/{id}/drop` -> `dropped` (from any status but `proposed` with a pending proposal: 409).
- `CommitBody.quest_request_id: Optional[str]` (`routes/lore_write.py`): when set, the request must be `writing_lore` of the active world (422 otherwise, before `apply_proposal`); after a successful apply, in the same transaction, `move_request(new, lore_entry_id=<entry_id>)`.

### C-14 — the review card and the request panel
Produced by: BRIEF-0121-F (card), BRIEF-0121-G (panel)   Consumed by: Nia
- `frontend/src/creation/OfferEditor.svelte` props `{draft, choices, seeds = {}, onchange}` -- the editor markup of `QuestOffers.svelte` (title to terms and value), bound to `draft`; `seeds[<where>]` an interpreter answer for one condition (`pending_drafts`, C-10), passed to its `ConditionEditor` as `seed`.
- `ConditionEditor` and `ConditionInterpreter` accept `seed` (a `pending_drafts[i].answer` of the payload, C-10): the interpreter opens on it, as after « Interpréter »; « Choisir », « Insérer » and « Écarter » go through the existing draft routes by its `draft_id`.
- `questOffers.svelte.js`: `draftFromProposal(payload, views) -> draft` and `proposalBody(draft, payload) -> payload` (`draftBody(draft)` plus the payload's review keys, `flags_confirmed`).
- `QueueCard.svelte`: a `quest_offer_creation` in `proposed` renders `OfferEditor` (giver from every character and faction, suggestions first), « Quête unique » (adds or removes the leaf `is_character` doer -> `payload.character_id` in the eligibility list), the flags with « Je confirme » (sets `flags_confirmed`), the notes; « Approuver » sends `proposalBody` as the payload. Choosing a giver adds the leaf `has_met` doer -> the giver (the contact when the giver is a faction and a contact is set), once, removable (E1).
- `frontend/src/creation/QuestRequests.svelte`, rendered by `Queue.svelte` above the card list: one row per request -- declaration, day, trigger, status -- with « Concevoir » (`new`, `covered`, rejected), the existence question (`asking`: « Elle existe » + text, « Elle n'existe pas » + text, « Le lore le dit déjà » + entity), « Écrire dans Lore » (`writing_lore`), « Mettre de côté », and a link to its proposal's card.
- `writeState.questRequestId` (`writePanel.svelte.js`): set with `statement` before `navigate('lore')`; `Lore.svelte` opens « Écrire » when it is set; `commit()` sends it as `quest_request_id`, then calls `/design` and clears it.


## Context

L1 and N1 made visible: every request the days opened waits above the
review queue. « Concevoir » runs the designer; a subject the lore does not
hold asks her whether it exists -- and her answer, either way, is written
through the Lore panel she already uses, then the designer runs again on
what she wrote. A proposal lands in the queue below, reviewed in the card
of BRIEF-0121-F.

## Scope IN

1. `frontend/src/creation/questRequests.svelte.js` (new): `questRequestsState = $state({ requests: [], loading: false, error: '', busy: {} })`; `loadRequests()` (`GET /api/quest-requests`); `designRequest(id)` (`POST .../design`, then `loadRequests()` and the queue's reload trigger -- `queueState.reloadToken += 1`, the existing second reload trigger of `Queue.svelte`); `answerRequest(id, answer, text, entityId)` (`POST .../answer`; on `exists`/`absent`: `writeState.statement = <the returned statement>`, `writeState.questRequestId = id`, `navigate('lore')`; on `already`: `designRequest(id)`); `dropRequest(id)`. Each sets `busy[id]` while running and `error` on failure (the server's `detail`, e.g. the 503 message).
2. `frontend/src/creation/QuestRequests.svelte` (new), rendered by `Queue.svelte` between the batch verdict and the queue body, reloading on `serverState.worldId` and `queueState.reloadToken` like the queue: the title « Demandes de quête » and its count; nothing else when there is none. One row per request: « Jour N », the declaration (first line), the trigger in French (« déclaration », « étape bloquée », « savoir introuvable »), the status in French (`new` « à concevoir », `asking` « question d'existence », `writing_lore` « à écrire dans Lore », `proposed` « proposée » + the proposal's status, `covered` « déjà couverte par : <offer title> »), the subject once known, the note. Actions by status (C-02's case table, the server deciding):
   - « Concevoir » for `new`, `covered`, and `proposed` with a `rejected` proposal;
   - `asking`: « <subject> existe-t-il dans ce monde ? » with a text field and three buttons -- « Oui, il existe » (`exists`), « Non, il n'existe pas » (`absent`), « Le lore le dit déjà » (shows an entity select from `characters`, `locations`, `factions`, `items` of the offer choices, then `already`);
   - `writing_lore`: « Écrire dans Lore » (sets `writeState` as item 1 does from the stored `creator_text` -- the statement rebuilt client-side the same way the server builds it -- and navigates);
   - « Mettre de côté » for every status the server allows.
3. `writePanel.svelte.js`: `blank()` gains `questRequestId: null`; `commit()` sends `quest_request_id: writeState.questRequestId || null`; on success, when it was set, `POST /api/quest-requests/<id>/design` (its error shown in the panel's error line, the commit already done), then `writeState.questRequestId = null`. `restart()` and a world change clear it.
4. `Lore.svelte`: when it mounts or `writeState.questRequestId` becomes set, `loreTab = 'write'` (an `$effect` that reads `writeState.questRequestId` and writes only `loreTab` -- INV-55); the « Écrire » panel shows one line « Pour la demande de quête : <subject> » while it is set.
5. Rebuild the frontend, commit the build output.
6. New check `tooling/verify/checks/quest_request_panel.py` (static text, a pattern matching nothing fails):
   - **RP1** `Queue.svelte` imports and renders `<QuestRequests`; `QuestRequests.svelte` names the five statuses' French labels and the three existence answers' values.
   - **RP2** `questRequests.svelte.js` calls the four routes of C-12 and `navigate('lore')`.
   - **RP3** `writePanel.svelte.js` sends `quest_request_id` in the commit body and calls `/design` after it; `blank()` holds `questRequestId`.
   - **RP4** `Lore.svelte` switches `loreTab` to `'write'` on `writeState.questRequestId`.
7. `tooling/standards/ARCHITECTURE_DECISIONS.md`: an entry above the footer, `## A QUEST REQUEST IS WORKED FROM THE REVIEW QUEUE, ITS LORE FROM THE LORE PANEL (TICKET-0121) -- QuestRequests.svelte (BRIEF-0121-g, no schema change)`: L1, N1, why above the queue and not a new tab (no new island, INV-50), the Lore hand-off and its return. Regenerate `DECISIONS_INDEX.md`, `FILE_MAP.md`.

## Scope OUT

- Any server change (E); the review card (F).
- Showing anything of a request on a player surface (J2-a1): Journée is untouched.
- Deleting a request (never: set aside).
- Every later brief of this lot.

## Invariants to defend

- **INV-50** -- no new Création island: `QuestRequests` is a child of `Queue.svelte`.
- **INV-55** -- the Lore tab switch reads one state and writes another.
- **INV-01** -- the panel shows the creator what she asked about; nothing here reaches a model or a player.

## Decision rights

STOP:
- an anchor does not hold;
- a check requires the panel to be a Création registry entry.
ADAPT:
- `queueState` has no `reloadToken`: use the queue's existing reload function, report.
- the Lore shell keeps its tab elsewhere than `loreTab`: switch it there, report.
REPORT-ONLY:
- the time a design takes, as the creator sees it (the button stays busy).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `quest_request_panel.py` PASS (RP1-RP4); `frontend_build_fresh.py`, `module_budget.py`, `creation_island.py`, `effect_self_write.py`, `lore_isolation.py`, `lore_write.py` PASS.
- [ ] Named mutations, red then reverted: remove `<QuestRequests` from `Queue.svelte` (RP1); drop `quest_request_id` from the commit body (RP3); leave `loreTab` on `question` (RP4).
- [ ] `/review-step` then `/close-step`.
- [ ] The ticket's Live gate is Nia's (TICKET-0121, « Live »).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`, regenerated `DECISIONS_INDEX.md`, `FILE_MAP.md`. No schema change.
