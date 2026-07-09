# BRIEF — Step "two-stage entity creation: germ, parking, on-demand realization (BRIEF-0019-a-entity-creation-two-stage)"

## Context

Last chantier of the post-0014 sequence: the world can now GROW. The tick
proposes a thin `entity_creation` GERM (need, not sheet); approval parks
it as validated (`pending_realization` — no canon write, no synchronous
authoring call during batch review, I2); the Création tab lists pending
germs and, on demand, the EXISTING pure authoring chain
(`generate_entity_draft` + L1 goals, entity_author.py:389) pre-fills the
EXISTING creation form; Nia's commit realizes the entity and flips the
mutation to `applied` with `created_entity_id` stamped — provenance
readable forever. The dormant conversation-sourced channel
(analyzer.py:58, no payload branch — RECON F6) joins the same pending
list. Grounding: RECON-0019 (F1-F8). danger_class: db_write — NO
migration (the germ lives in `proposed_mutation.payload`).

## Scope IN

1. **Emit side (tick.py, `_normalize_scope_event`).** New
   `entity_creation` branch, active for BOTH scope types (location and
   faction; per-NPC contract untouched):
   - `entity_type` validated against `{"character","location","faction"}`
     (`_TYPE_FIELDS`' keys — cite them, do not import entity_author into
     tick.py; a literal frozenset with a comment) -> drop with note
     otherwise.
   - `name` and `concept`: required non-empty strings -> drop with note.
   - `anchor`: optional string, passed through verbatim (prose, never
     resolved to ids — nothing in this payload is an id; the rule-3
     forced-field surface is untouched).
   - Collision guard, emit-time (RECON F5): `name.casefold()` present in
     an actives-name index (ALL active entities of the world, any type —
     built once per scope call alongside the existing roster/index
     builds, tick.py:985-1032) -> drop with note.
   - Quota: module constant `ENTITY_CREATION_QUOTA = 1`, own
     seen-counter — first germ wins, later ones dropped with note
     (events keep SCOPE_EVENT_QUOTA, agendas keep their 0018 caps).
   - Payload out: `{"entity_type", "name", "concept", "anchor"?}`;
     `target_table="entity"`, `target_id=None`.

2. **Approval short-circuit (cockpit/app.py, approve endpoint,
   app.py:5330-5364).** BEFORE the savepoint, when
   `mut.mutation_type == "entity_creation"`:
   - Canon collision re-check (same casefolded-name-among-actives
     question, asked fresh — 0014 doctrine): hit -> the Needs-attention
     path with an explicit message ("une entité active porte déjà ce
     nom"), nothing else changes.
   - Pass -> `status="approved"`, `reviewed_at=now`, creator_notes
     appended with "en attente de réalisation — onglet Création";
     response `{"status": "pending_realization", "mutation": ...}`.
     NO savepoint, NO `_apply_mutation` call, NO "[apply error]"
     framing (RECON F3). `_apply_mutation`'s docstring: "Unimplemented"
     shrinks to `other`, with a pointer: "entity_creation is realized
     through the Création tab (BRIEF-0019-a), never applied here."

3. **Pending list (cockpit/app.py, write-free router region —
   beside app.py:127, RECON F2).**
   `GET /api/creations/pending` — ProposedMutation where
   `mutation_type == "entity_creation"`, `status == "approved"`, and
   payload lacks `created_entity_id`; ALL sources (tick AND
   conversation). Each item: mutation_id, source label
   (TICK/CONVERSATION via tick_id/conversation_id), age, and a
   TOLERANT germ summary (RECON F6): name from `name|title`, concept
   from `concept|description|content`, entity_type validated — invalid
   or missing type renders the item with a "type inconnu" badge and NO
   Generate action (visible, not realizable; the creator rejects it in
   the queue if unwanted).

4. **Realization generation (same router region).**
   `POST /api/creations/{mutation_id}/generate`:
   - Guards: mutation exists, is `entity_creation`, `approved`,
     unrealized, and its germ has a valid entity_type -> else 409 with
     a clear message.
   - Composes the brief IN CODE (French; one small template per
     entity_type weaving name + concept + anchor + the invoking scope's
     context when derivable from the payload/tick — 2-4 sentences, the
     prose shape `generate_entity_draft` expects).
   - Reuses the EXISTING generation flow — the same code path as
     `/api/entities/generate` including L1 goals for characters (factor
     the body of app.py:127-150 into a shared helper in the same
     write-free region rather than duplicating; both routes call it).
   - Returns `{ok, draft, notes, mutation_id, entity_type}` — pure,
     writes nothing; regenerating later is free (an abandoned draft
     costs nothing; the mutation stayed `approved`).

5. **Commit linkage (`cockpit/crud.py:690`, `create_entity`).**
   `EntityWriteBody` gains optional `mutation_id`. AFTER the entity
   commit succeeds: load the mutation; guards — exists, is
   `entity_creation`, `approved`, payload lacks `created_entity_id`
   (double-commit protection); then
   `mut.payload = {**mut.payload, "created_entity_id": new_entity_id}`
   (REASSIGNMENT — JSON columns don't detect in-place mutation; or
   `flag_modified` — RECON F4), `status="applied"`,
   `applied_at=now`. A guard failure NEVER rolls back the entity (the
   creator's hand made it); it is returned as a linkage note in the
   response.

6. **Création tab UI.** A "Créations en attente" strip above the
   existing creation form (HTMX idioms of the tab): germ cards (type
   badge, name, concept, source, age) + "Générer la fiche" -> loads the
   existing form pre-filled from the draft with `mutation_id` in a
   hidden field; the form's normal submit does the rest (item 5). No
   new form, no new commit path.

7. **Prompt version (`scripts/seed_pilot.py` +
   `scripts/apply_ticket_0019_prompt_updates.py`).** New VERSION of
   `pt-world-tick-events`: germ shape
   (`entity_creation -> {"entity_type": "character|location|faction",
   "name", "concept", "anchor"?}`); rules — propose a creation ONLY
   when the interval's happenings imply someone or somewhere absent
   from the briefing; at most ONE; concept = one line; never a name
   already present in the briefing; the anchor situates (near/within/
   serves), it does not wire. Delivery: append-version branch,
   idempotent (0015-0018 shape).

8. **Verify checks (`tooling/verify/checks/world_tick.py` + new/extended
   rules).**
   - Rule 15: `"entity_creation"` appears in `_normalize_scope_event`
     but not in `_normalize_tick_item` / the per-NPC sets.
   - Rule 16: `ENTITY_CREATION_QUOTA` exists and is referenced in the
     scope emit path (rule-7 idiom).
   - Rule 17: `_apply_mutation` contains no `entity_creation`
     canon-writing branch (the string may appear only in
     docstring/short-circuit comments; concretely: no `Entity(`
     construction anywhere in `_apply_mutation` — confirm
     single_canon_write's existing constructor scan covers
     cockpit/app.py and rely on it, adding app.py to its scan surface
     if it does not).
   - Rule 18: the create_entity linkage block references all three
     guards (type, status, unrealized) before any status flip (AST
     scan of the function).

## Scope OUT

- H2 (tick-authored full sheets) — permanently rejected, not deferred.
- Auto-application of drafts; any canon write in the generation path
  (its purity is a named property — RECON F1/F2).
- connects_to auto-wiring; auto faction-membership for created NPCs;
  germ anchors resolving to ids.
- entity types beyond the three; `object`/`world` germs.
- Expiry/cleanup of stale pending germs (queue rejection is the
  existing path; revisit if measured).
- Analyzer changes (its shapeless entity_creation payloads are
  TOLERATED downstream, not reformed — RECON F6).
- Any change to per-NPC ticks, agendas, events, or the 0016 delta.

## Invariants to defend

- **Model proposes, code judges — twice** — the germ passes creator
  review (need), the sheet passes creator review (form commit); the
  gameplay model authors neither ids nor sheets; the authoring model
  authors sheets only through the pure chain.
- **Two sanctioned canon-write paths, unchanged** — the entity is
  written by creator CRUD (`create_entity`), exactly as before; the
  queue's apply path writes NOTHING for this type; the linkage flip
  touches only the mutation row.
- **Volume by construction** — ENTITY_CREATION_QUOTA=1; a tick cannot
  flood the world with people.
- **Canon-existence guards, never tick_id** — collision asked fresh at
  approval; double-commit blocked by payload state, not by history
  comparison.
- **Purity of the generation path** — both generate routes share one
  write-free helper; failure returns `{ok: false}`, never a 500, never
  a write.
- **History is sacred** — nothing is deleted; an unwanted germ is
  REJECTED (existing queue path), a realized germ carries its
  provenance forever.

## Done means

Machine gate (`python tooling/verify/run.py`, fail-closed):
- [ ] Rules 15-18 pass; rules 1-14 still green -> tooling/verify/checks/world_tick.py (+ single_canon_write surface confirmation)
- [ ] Full suite green -> tooling/verify/run.py

Live gate (Nia):
- [ ] Backup; `python scripts/apply_ticket_0019_prompt_updates.py` (immediate re-run: no-op)
- [ ] Faction tick: a germ appears in the queue (thin payload visible: type, name, concept, anchor); a second germ in the same reply shows as a dropped note (quota)
- [ ] Approving the germ returns "en attente de réalisation"; the mutation is approved, not applied; nothing exists in canon
- [ ] Création tab lists it (TICK badge); "Générer la fiche" pre-fills the form (a character germ arrives WITH generated goals — L1); commit creates the entity; the mutation shows applied + created_entity_id
- [ ] Navigate away from a generated draft, come back, regenerate: works — the mutation never left approved
- [ ] A germ named like an existing active entity: dropped at emit (note in the R3 summary); rename an entity to collide AFTER a fresh germ is proposed, then approve it -> Needs attention (approval-time canon guard)
- [ ] A location germ realizes with zero connects_to edges; manual wiring afterwards works as usual
- [ ] If a conversation-sourced entity_creation sits dormant in the live queue: it appears in the pending list (CONVERSATION badge) and realizes — or shows "type inconnu" without a Generate button if its free-form payload lacks a valid type
- [ ] npcs-scoped tick: no germs, ever

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new section
  "TWO-STAGE ENTITY CREATION (BRIEF-0019-a)": H1/I2 verbatim, the
  pending_realization parking semantics (approved-but-not-applied as a
  deliberate lifecycle state), the linkage-never-rolls-back-the-entity
  rule, any-type collision scope, the awakened conversation channel and
  its tolerated shapelessness, H2's permanent rejection.
- `world-engine-schema.md` — `proposed_mutation` commentary: the
  entity_creation lifecycle (proposed -> approved/pending realization ->
  applied at commit, `created_entity_id` provenance); changelog entry
  (no version bump).
- `CLAUDE.md` — freshness contract decides.

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **Quota = 1 germ per scope call.** The world grows one being at a
   time per tick scope. Reverse = any other constant.
2. **Collision scope = ANY active entity type** (a faction named like a
   location is confusion, not richness). Reverse = same-type-only
   collisions.
3. **Both scope types may propose germs** (a location can need an
   occupant; a faction can need an agent). Reverse = faction-only.
4. **The linkage failure never rolls back the entity commit** — the
   entity is the creator's hand; a broken link is a visible note.
   Reverse = strict transactional coupling (entity + flip or nothing).
5. **Invalid-type conversation germs stay visible ("type inconnu",
   no Generate)** rather than being filtered out — the creator sees
   everything the world proposed and rejects in the queue. Reverse =
   silently exclude them from the pending list.
6. **The two generate routes share one factored helper** (L1 included).
   Reverse = the new route calls entity_author directly and duplicates
   the L1 merge (recommended against — one generation path).
