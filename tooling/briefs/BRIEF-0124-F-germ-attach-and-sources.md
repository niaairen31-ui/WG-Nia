<!-- slug: germ-attach-and-sources -->
# BRIEF 0124-F — "A germ says where it comes from and can join an existing character -- the sentence and the place by name (E1), the source label, `candidates` and `attach` (H1), the « Germes » metric, the H2 and W2 deferrals (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: BRIEF-0124-E (the `creation` germs C-11 labels)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot) plus BRIEF-0124-A to E.

- `src/world_engine/day_concordance.py:502-511` -> the payload of R-17 (`"anchor": item.candidate_location_id` among nine keys); `:65` imports `normalize_surface` from `.lore_resolve`; `emit_germs(unmatched, pass_play, db)` reads `pass_play` (`declared_action` is a `PassPlay` column, `models/pipeline.py:80`).
- `src/world_engine/cockpit/routes/creator.py:130` -> `def _compose_entity_creation_brief(payload: dict) -> str:`; `:155-189` -> `list_pending_creations` with `"source": "tick" if mut.tick_id else "conversation"`; `:191-220` -> `generate_creation_draft` calling `_compose_entity_creation_brief(payload)` then `_generate_draft_with_l1(entity_type, brief, db)`.
- `src/world_engine/cockpit/crud/__init__.py` exports `_link_entity_creation`; `crud/entities.py:702` -> `def _link_entity_creation(mutation_id: str, entity_id: str, db: DbSession) -> dict:`.
- `src/world_engine/cockpit/play.py:853` -> `def _location_neighbours(location_id: str, db: Session) -> list[tuple[str, str]]:`.
- `src/world_engine/dashboard_metrics.py:299-323` -> `METRICS` ending with `Metric("quest_requests", ...)`; `dashboard_deferrals.py:47` -> `_T0121 = ...`; the last `DEFERRALS` entry is `Deferral("P1", "TICKET-0121", ...)`.
- `tooling/verify/checks/json_ui_boundary.py:44` -> `# Edited field by field by the review card for event_creation (TICKET-0119) and quest_offer_creation (TICKET-0121): the « payload » deferral, reached (dashboard_deferrals.py).`
- `tooling/tickets/TICKET-0124-world-premise.md` exists (Nia deposits it with the lot) and holds each anchor of C-12's two deferrals exactly once.
- No `tooling/verify/checks/germ_attach.py`.

## Facts carried

### R-16 — the germ routes [M]
Opened: `src/world_engine/cockpit/routes/creator.py:63-94` (`_generate_draft_with_l1(entity_type, brief, db)`), `:121` (`_ENTITY_CREATION_TYPES = frozenset({"character", "location", "faction"})`), `:123-127` (`_ENTITY_CREATION_INTROS`), `:130-152` (`_compose_entity_creation_brief(payload)`: name, concept, `anchor` written as prose), `:155-189` (`list_pending_creations`: `entity_creation`, `approved`, no `created_entity_id`; item `{mutation_id, source: "tick" if tick_id else "conversation", proposed_at, name, concept, anchor, entity_type}`), `:191-220` (`generate_creation_draft`); file size 753 lines, 26 functions.
Finding: a Journée germ is labelled « CONVERSATION »; its `anchor` (a location id, R-17) is written into the brief as prose.
Consequence: brief F labels the source from the row (C-11) and composes the place by name (C-10).

### R-17 — the Journée germ [M]
Opened: `src/world_engine/day_concordance.py:463-522` (`emit_germs(unmatched, pass_play, db)`: the payload at `:502-511` is `entity_type, name, concept="Rôle à pourvoir : {name}.", anchor=candidate_location_id, role_hint, surface_form, kind, candidate_location_id`; `source_type="pass_play"`, `proposed_by="local_ai"`, `status="proposed"`); `day_extract.py:42-46` (`Mention`: `category, surface_form, kind, role_hint` -- no sentence); `models/pipeline.py:80` (`PassPlay.declared_action: str`); `cockpit/routes/day.py:455-474` (the caller).
Finding: the declaration is on the pass-play; the mention carries only its words. `routes/day.py:470-471` pairs `person_unmatched` with `germs` by `zip`, while `emit_germs` skips blocked candidates and truncates over its quota -- the pairing shifts when a germ is skipped (report-only, drafting decision 12).
Consequence: `emit_germs` adds `source_sentence` (the declaration's sentence holding the surface form) and `anchor_name` (C-10).

### R-18 — why an existing character was missed [M]
Opened: `src/world_engine/day_concordance.py:218-243` (`_rung_occupation`: an inferred person's `role_hint` keywords against the descriptions of reachable NPCs' standing goals); `day_choice.py:94-116` (`choice_requests`: « Cast and inferred mentions never produce a request »).
Finding: « professeur d'escrime » shares no keyword with « maître des épées »; the model arbitration never sees an inferred mention.
Consequence: H1 handles it on the creator side; H2 (opening the arbitration to inferred mentions) is deferred with a metric (C-12).

### R-19 — the entity create path [M]
Opened: `src/world_engine/cockpit/crud/entities.py:382-404` (`EntityWriteBody`: `entity, extension, mutation_id, facets, mentions, confirm_promotion, link_to, carrure`), `:558-573` (`_create_entity_core`), `:702-723` (`_link_entity_creation(mutation_id, entity_id, db)`: guards -- exists, `entity_creation`, `approved`, no `created_entity_id`; reassigns the payload with `created_entity_id`, status `applied`, `applied_at`, commits), `:729-775` (`create_entity`: `_create_entity_core`, one commit, `dissolve_emptied(...)`, then the response, then `_link_entity_creation` when `mutation_id`); file size 905 lines, 26 functions.
Finding: the core never commits (INV-18); the route owns the single commit.
Consequence: brief E writes the extras between the core and that commit, from a new module (`entity_extras.py`); `entities.py` gains only the three body fields and one call.

### R-20 — a proposal row [M]
Opened: `src/world_engine/models/pipeline.py:99-150` (`ProposedMutation`: no CHECK in `__table_args__`; `source_type: str  # pass_play | conversation | world_tick`, « exactly one of these is set » as a comment; `tick_id` for a tick, which sets neither FK; `target_table`, `target_id` free text; `payload` JSON NOT NULL; `status` default `proposed`; `creator_notes`; `proposed_by` default `local_ai`); every `source_type="..."` written under `src/` (Gate (c)).
Finding: nothing enforces one source; a tick row sets no FK at all.
Consequence: a germ ticked in a draft is `source_type="creation"`, no FK (the tick precedent). An attached germ records its entity in `target_table="entity"`, `target_id` -- relational, so the metric reads no JSON (R-26).

### R-25 — a location's neighbours, a character's place [M]
Opened: `src/world_engine/cockpit/play.py:853-880` (`_location_neighbours(location_id, db) -> list[tuple[str, str]]`: active locations joined by `connects_to`); CLAUDE.md INV-06 (its sole gameplay reader of `connects_to`); `models/canon.py:143-170` (`class Character`: `id` primary key and FK to `entity.id` (`:158`), `world_id`, `character_type` `player | npc` (`:163`), `current_location_id` (`:165`), indexed).
Consequence: `germ_candidates` imports it rather than reading `connects_to` itself.

### R-26 — the dashboard registries [M]
Opened: `src/world_engine/dashboard_deferrals.py:30-49` (`Deferral(code, ticket, deferred_fr, condition_fr, source, anchor, metric=None, status="open", follow_up=None)`; `_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"`), `:150-170` (the last entries, `P1` of TICKET-0121); `dashboard_metrics.py:39-74` (`Scope`, `Row(group, label, value, of=None)`, `Metric(key, title, question, watches, dated, compute)`, `_in_worlds`, `_dated`), `:299-323` (`METRICS`, last `quest_requests`); `tooling/verify/checks/dashboard_registry.py:90-116` (`check_db1`: `(code, ticket)` unique; every text non-empty; the source exists and holds the anchor exactly once, whitespace folded; `metric` None, `EXPORT` or a `METRICS` key), `:124-140` (`check_db2`: unique keys; `dashboard_metrics.py` and the route module use no attribute `payload`, `original_payload`, `model_calls` and no `text(` call); `json_ui_boundary.py:44-48` (the payload exemption and its anchor sentence « First structured UI consumer must relationalize. »).
Consequence: the « Germes » metric counts by `status`, `source_type` and `target_table` only; the H2 and W2 anchors live in the ticket file; the exemption's comment line gains the pending-creation card, its anchor sentence untouched.

## Contracts

### C-10 — the germ payloads and the brief composed from them
Produced by: BRIEF-0124-E (draft germs), BRIEF-0124-F (Journée germs, compose)   Consumed by: BRIEF-0124-F, G, H
- Draft germ payload: `{"entity_type", "name", "concept", "origin_entity_id", "link_type"}`.
- Journée germ payload: today's keys (R-17) plus `"source_sentence"` (the sentence of `pass_play.declared_action` that holds `mention.surface_form`, compared through `lore_resolve.normalize_surface`; the whole declaration, truncated to 300 characters, when none holds it) and `"anchor_name"` (`Entity.name` of `candidate_location_id`, or `None`).
- `_compose_entity_creation_brief(payload, db)` writes, in order: the intro sentence (unchanged); the concept (unchanged); `"Lieu : {anchor_name}."` when `anchor_name`, else — when `anchor` equals `candidate_location_id` (a Journée germ born before this lot) — `"Lieu : {that entity's name}."`, else the `anchor` prose (a tick germ, unchanged); `"Mentionné ainsi : « {source_sentence} »."` when present; `"Lié à {origin name} ({link_type})."` when `origin_entity_id` resolves.

### C-11 — the germ routes and the pending item
Produced by: BRIEF-0124-F   Consumed by: BRIEF-0124-G, H
- Pending item (`GET /api/creations/pending`): today's keys, with `source` one of `"tick"` (`tick_id`), `"journee"` (`pass_play_id`), `"creation"` (`source_type == "creation"`), `"conversation"` (otherwise), plus `"anchor_name"`, `"source_sentence"`, `"origin_entity_id"`, `"origin_name"`, `"link_type"` (each `None` when absent).
- `germ_candidates(db, mut) -> list[dict]` in `cockpit/routes/creator.py`: for a `character` germ, the active non-player characters whose `current_location_id` is the germ's location (`candidate_location_id`, or for a `creation` germ the origin character's `current_location_id`) or one of its `_location_neighbours`, ordered by name, at most `MAX_GERM_CANDIDATES = 12`; each `{"entity_id", "name", "location_name", "reason"}`, `reason` « au même lieu » or « lieu voisin ». Any other type, or no location: `[]`.
- `GET /api/creations/{mutation_id}/candidates` -> `{"mutation_id", "candidates": [...]}`; 409 when the row is not an approved, unrealized `entity_creation`.
- `POST /api/creations/{mutation_id}/attach` body `{"entity_id"}` -> `{"ok": True, "mutation_id", "entity_id", "name"}`. Guards: the germ as above (409); the entity active, in the germ's world, of the germ's `entity_type` (422). Sets `target_table="entity"`, `target_id=entity_id`, `creator_notes` += « rattaché à une entité existante : {name} », then `_link_entity_creation(mutation_id, entity_id, db)` (which applies and commits); its failure is a 409 with its error.
- `generate_creation_draft` returns the germ's candidates as `"candidates"` (BRIEF-0124-F); BRIEF-0124-G passes their ids to the draft (C-13) and prepends a `creation` germ's origin link.

### C-12 — the « Germes » metric and two deferrals
Produced by: BRIEF-0124-F   Consumed by: nothing in this lot
- `Metric("germs", "Germes de création", "Que deviennent les germes, et combien rejoignent une fiche existante ?", ("H2",), True, _germs)`, appended to `METRICS`. Rows over `entity_creation` rows in scope (`_in_worlds(ProposedMutation.world_id)`, `_dated(ProposedMutation.proposed_at)`), grouped by source label (`"Journée"`: `source_type == "pass_play"`; `"Tick"`: `"world_tick"`; `"Brouillon"`: `"creation"`; `"Conversation"`: otherwise): `Row(group, "Proposés", n_proposed, n)`, `Row(group, "En attente de réalisation", n_approved, n)`, `Row(group, "Réalisés en nouvelle fiche", n_applied_new, n)` (`applied`, `target_table` NULL), `Row(group, "Rattachés à une fiche existante", n_attached, n)` (`applied`, `target_table == "entity"`), `Row(group, "Rejetés", n_rejected, n)`; a group with `n == 0` is omitted. Note: « Ce que deviennent les germes ; H2 regarde les germes de Journée rattachés. »
- `_T0124 = "tooling/tickets/TICKET-0124-world-premise.md"`; `Deferral("H2", "TICKET-0124", "Le modèle reconnaît en jeu un personnage existant derrière un rôle.", "Des germes de Journée que Nia rattache à une fiche existante.", _T0124, "H2 (the model recognises an existing character in play; reactivation: Journée germs the creator attaches to an existing character)", metric="germs")`; `Deferral("W2", "TICKET-0124", "Garder l'historique des lois du monde.", "Un writer passe world_law_id= à un fait.", _T0124, "W2 (law history; reactivation: a writer passes world_law_id= to a fact)")`.

## Context

A Journée germ reached the generator as « Rôle à pourvoir : forgeron. »
plus a location UUID, labelled « CONVERSATION », and could only become a new
entity -- the « professeur d'escrime » who was the « maître des épées » (R-18).
This brief gives the germ its sentence and its place, names its source,
lists the characters it could be, and lets Nia attach it to one (H1),
counted so H2's condition can be read.

## Scope IN

1. `day_concordance.py`: new `def _source_sentence(declaration: str, surface_form: str) -> str` (C-10: split on `re.split(r"(?<=[.!?…])\s+", declaration.strip())`, first sentence whose `normalize_surface` holds `normalize_surface(surface_form)`, else `declaration.strip()[:300]`). In `emit_germs`, the payload gains `"source_sentence": _source_sentence(pass_play.declared_action, mention.surface_form)` and `"anchor_name": <Entity.name of item.candidate_location_id, or None>` (one `db.get(Entity, ...)`; `Entity` imported if not already). The docstring gains « TICKET-0124 (E1): each germ keeps the sentence it was mentioned in and its place's name. »
2. `cockpit/routes/creator.py`:
   - `_compose_entity_creation_brief(payload: dict, db: Session) -> str` per C-10 (the origin's name read with `db.get(Entity, origin_entity_id)`); its one caller passes `db`.
   - New `def _pending_source(mut: ProposedMutation) -> str` per Gate (b) table 4; `list_pending_creations` uses it and adds C-11's five keys (`origin_name` read with `db.get(Entity, ...)`, `None` when absent).
   - `MAX_GERM_CANDIDATES = 12`; `def germ_candidates(db: Session, mut: ProposedMutation) -> list[dict]` per C-11, `_location_neighbours` imported inside the function from `..play` (« lazy: `play` is a heavy module; creator routes never import it at load »); characters read with `select(Entity, Character).join(Character, Character.id == Entity.id)` (`Character.id` is its PK and `entity.id` FK, `models/canon.py:158`) filtered on `Entity.world_id == mut.world_id`, `Entity.status == "active"`, `Character.character_type != "player"`, `Character.current_location_id.in_(...)`.
   - New `def _open_germ(mutation_id: str, db: Session) -> ProposedMutation` raising 409 « Mutation is not an approved, unrealized entity_creation germ » exactly where `generate_creation_draft` raises today; `generate_creation_draft` uses it.
   - `@router.get("/api/creations/{mutation_id}/candidates")` and `@router.post("/api/creations/{mutation_id}/attach")` per C-11; `class GermAttachBody(BaseModel): entity_id: str`. `attach` appends the note inline -- `creator.py` does not import `cockpit/routes/mutations.py::_append_note` (`:687`) and does not start to: `mut.creator_notes = f"{mut.creator_notes}\n{note}" if mut.creator_notes else note`.
   - `generate_creation_draft` returns `"candidates": germ_candidates(db, mut)` beside its other keys (the ids reach the draft in brief G).
   - `creator.py` imports `Character` already (`:34`); `Entity` and `ProposedMutation` too (`:35`, `:37`).
3. `dashboard_metrics.py`: `def _germs(db, scope)` and its `Metric` per C-12, appended after `quest_requests`; it reads only `ProposedMutation.world_id`, `.proposed_at`, `.mutation_type`, `.source_type`, `.status`, `.target_table` (DB2).
4. `dashboard_deferrals.py`: `_T0124 = "tooling/tickets/TICKET-0124-world-premise.md"` after `_T0121`; the two `Deferral(...)` of C-12 appended after `P1`.
5. `json_ui_boundary.py:44`: the comment line becomes `# Edited field by field by the review card for event_creation (TICKET-0119) and quest_offer_creation (TICKET-0121), read key by key by the pending-creation card for entity_creation (TICKET-0124): the « payload » deferral, reached (dashboard_deferrals.py).` -- the anchor sentence two lines below untouched.
6. New check `tooling/verify/checks/germ_attach.py` (fixture idiom of `.claude/rules/verify-checks.md`). Docstring first sentence « G1 check for TICKET-0124 -- a germ says where it comes from, and can join an existing character instead of creating one. » Rules:
   - **GA1** -- `emit_germs` over a fixture pass-play declaring `Je vais à la forge. Je cherche un professeur d'escrime pour apprendre.` with one unmatched inferred person (`surface_form` `un professeur d'escrime`, `role_hint` `professeur d'escrime`) anchored at location `Terrain d'entraînement`: the payload's `source_sentence` is `Je cherche un professeur d'escrime pour apprendre.`, `anchor_name` `Terrain d'entraînement`; a mention found in no sentence gives the declaration (300 characters at most).
   - **GA2** -- `_compose_entity_creation_brief` on: a payload with `anchor_name` and `source_sentence` -> holds « Lieu : Terrain d'entraînement. » and « Mentionné ainsi : « … » »; a pre-0124 Journée payload (`anchor` == `candidate_location_id`, no `anchor_name`) -> « Lieu : <its name>. », never the id; a tick payload with prose `anchor` -> that prose; a draft germ payload -> « Lié à <origin> (<link_type>). »
   - **GA3** -- `list_pending_creations` labels the four sources of table 4 and carries C-11's keys; `germ_candidates` on a character germ at `Terrain d'entraînement` lists the character there (« au même lieu ») and one at a `connects_to` neighbour (« lieu voisin »), not a player character nor an inactive one nor one two hops away; a location germ -> `[]`; every row of table 5 (`attach`); after a valid `attach` the row is `applied`, `target_table == "entity"`, `target_id` the character, its payload's `created_entity_id` the character, its notes hold « rattaché à une entité existante », no new `entity` row.
   - **GA4** -- `compute_metrics` over the fixture: the `germs` metric's `Journée` group counts one attached, one realized (applied, `target_table` NULL), one proposed; its `Brouillon` group one `En attente de réalisation`; a dated scope after today counts nothing.
   Each rule fails on zero items. One `PASS: germ_attach -- ...` line.

## Scope OUT

- The draft's use of the candidates (brief G) and every frontend change (brief H).
- H2 itself: `day_choice` is not opened to inferred mentions.
- The two report-only defects (R-15's `_world_id`, R-17's `zip` pairing) -- not fixed here.
- A tick germ's prose `anchor` (unchanged).
- Any `proposed_mutation` column.

## Invariants to defend

- **INV-06** -- the neighbours come from `_location_neighbours`, the sole gameplay reader of `connects_to`; this route reads no `connects_to` itself.
- **INV-08 / INV-12** -- `attach` writes `proposed_mutation` only (pipeline, not canon); no entity, no delete.
- **INV-20** -- the new pending keys are read from the payload by the route and served as plain keys (the reached « payload » deferral, comment line updated); no new JSON column.
- **INV-14** -- no new producer here.

## Decision rights

STOP: a Mini-RECON anchor that does not hold; `day_concordance_golden.py` fails on the new payload keys (it pins names only, R-17); DB1 cannot find an anchor in the ticket file exactly once.
ADAPT: none beyond the default clause (`Character.character_type` -- `player | npc` -- and `current_location_id` are declared at `models/canon.py:163-165`).
REPORT-ONLY: any other germ source you meet.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/germ_attach.py` -> `PASS`.
- [ ] Named mutations, each turning its rule red, then reverted: drop `anchor_name` from the payload -> GA1; write the anchor id as prose again -> GA2; let `germ_candidates` include player characters -> GA3; count attached germs as realized -> GA4.
- [ ] `day_concordance.py`, `day_concordance_golden.py`, `dashboard_registry.py`, `json_ui_boundary.py`, `module_budget.py`, `function_length.py` -> `PASS`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## A GERM SAYS WHERE IT COMES FROM AND CAN JOIN AN EXISTING CHARACTER (TICKET-0124) -- source sentence, place name, candidates, attach, the Germes metric (BRIEF-0124-F, no schema change)` -- E1, H1, `target_table="entity"` as the relational mark of an attached germ, H2 and W2 with their conditions.
