---
id: TICKET-0081
title: day-declaration-rewrite-and-concordance — the resolver stops blocking, and the plan is built from the rewrite
type: feature
status: live-gate
created: 2026-09-01
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0081-a-concordance-robustness-and-casting, BRIEF-0081-b-rewrite-object-and-resolution-trace, BRIEF-0081-c-germ-emission-hygiene]
schema_version_touched: one bump in BRIEF-0081-b (two new pipeline tables); Claude Code assigns the number
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> On parle de mon outil de resolution de jours. Dans mon idee initial, j'avais
> une passe de plusieurs agents qui detecte (avec des instructions precises) si
> le joueur mentionne ou infere un lieu, une faction ou un NPC. Ensuite, il y a
> un analyse /un RAG/un autre appel qui determine de quel NPC/faction/lieu, on
> parle. Ensuite, il y une re-ecriture du prompt du joueur en une version
> utilisable par le systeme. Si aucun NPC,faction/lieu n'est trouver
> correspondant, on propose la creation d'un NPC/lieu/faction correspondant. (a
> approuve par le createur). (dans la V1, je voudrais voir le prompt reecrit
> pour analyse le resultat)

> Dans l'etape 2, est-ce que cela fonctionne si le joueur n'utilise pas
> exactement le language que j'ai choisis. Ou que plusieurs personne sont des
> descriptions qui pourraient entrer dans la description? Ex : je cherche un
> servant pour faire XYZ, il esiste 12 servants dans le manoir.

> Le plan devrais ne devarsi pas etre faite avec le prompt du joueur selon moi,
> mias avec la version reecrit avec les bonnes informations concernant les
> participants

> C2 mais c'est un irritant auquel il faut une solution, cela empeche toute
> automatisation parce que le plan est souvent refuse.

## Clarifications resolved (intake)

Design conversation of 2026-09-01, run against a fresh tarball of `main` at
schema v1.96. Decisions locked as codes; every claim below is [M] measured
against that tarball unless marked [I].

**What already exists, and is NOT rebuilt here** [M]:

- Detection: `day_extract.py:148-157`, three separate model calls, returning
  `Mention(category, surface_form, kind=named|inferred, role_hint)`. The model
  never sees the registry (enforced by `verify/checks/day_concordance.py` R2).
- Resolution: `day_concordance.concord()` (`day_concordance.py:172`), four
  ordered rungs, pure SQL, zero model calls.
- Germ proposal and creator-approved realization: `emit_germs`
  (`day_concordance.py:219`) -> the normal mutation queue ->
  `_approve_entity_creation_shortcircuit` parks (`routes/mutations.py:561`,
  decision I2 of TICKET-0019) -> `GET /api/creations/pending`
  (`routes/creator.py:149`) -> `POST /api/creations/{id}/generate` (`:185`) ->
  the pre-filled Creation form -> `create_entity` stamps
  `payload.created_entity_id` and `status="applied"` under a double-commit
  guard (`crud/entities.py:674-692`). Front wired at
  `frontend/src/creation/tabs.js:656,671`. TICKET-0019 is at `live-gate`.
  **The realization path is complete. Nothing in this ticket rebuilds it.**

**Decisions locked**:

- **A2'** — the "rewrite" is a structured object (verbatim intent spans from the
  declaration + resolved participant refs) plus a deterministic Python
  rendering. No model call authors it. The rendering replaces
  `pass_play.declared_action` as the input to plan selection and plan emission.
  Rejected: a model-authored prose rewrite. Reason: it is not stable across
  runs, so it cannot serve as a comparison key for "does a plan already exist
  for this", and nothing could detect an intention silently dropped in
  rewriting (the TICKET-0079 judge watches narration, not rewriting).
  Reactivation: a golden corpus where emitted-step quality depends measurably on
  prose fluency rather than on reference resolution.
- **B2 / J2** — the resolution is persisted as a parent/child pair: one
  `day_rewrite` row per generation carrying the rendered text actually handed to
  the model, N `day_mention_resolution` rows carrying the facts. Three named
  readers: the enriched API return, `freeze_facts` (which stops re-deriving),
  and post-hoc diagnosis. Resolve-time concordance READS the trace; it no longer
  re-runs the three extraction calls. Consequence: no `stage` column, only
  `generation`, incremented by the modify/replace path.
  Rejected J1 (rendering never stored), reactivation: a decision that the
  renderer is frozen and versioned. Rejected J3 (denormalized text per row).
- **C2 + the named/inferred partition** — ambiguity stays fail-closed, but its
  trigger surface shrinks to identity collisions only. Measured: `named_exact`
  fires only on `kind == "named"` (`:96`); `occupation` and `presence` fire only
  on `kind == "inferred"` (`:120`, `:143`); `named_alias` always returns None
  (`:111`). So a multi-candidate inferred mention is a role reference, not an
  ambiguity, and is CAST rather than blocked. What still blocks: two active
  entities of the same type sharing a name — a data problem Nia wants reported.
- **D3** — germ emission stays persons-only. Places and factions are reported,
  never germinated. Reactivation: unchanged from BRIEF-0075-c.
- **E2c** — the `occupation` rung is scoped by REACHABILITY, not by knowledge.
  Measured constraint that forced this: `Knowledge.subject` is a free string,
  not an entity FK (`models/canon.py:455`), so "this character knows of this
  NPC" is not expressible; and `npc_goal` carries no secrecy flag at all
  (`models/canon.py:503-529`). Rejected E2b (filter by `relation` existence):
  in a fresh manor no relation exists, so every inferred mention would become
  unmatched and germinate a thirteenth servant beside twelve real ones — worse
  than no filter. Rejected E2d (`npc_goal.is_secret` column), reactivation: a
  locally present NPC whose secret occupation is revealed by inference in live
  play.
- **F1** — casting among N inferred candidates is deterministic Python, with a
  declared precedence, recorded in the trace. Rejected F2 (bounded model
  selection): unstable across runs, which breaks plan comparison. Reactivation:
  a corpus where the deterministic precedence picks a narratively wrong NPC
  often enough to be noticed. Rejected F3 (defer casting to resolution):
  `agenda_step_requirement.target_entity_id` is a plain FK
  (`models/config.py:145`) with no role-target form, so F3 costs schema.
  Reactivation: a live day where a cast NPC's unavailability failed a step the
  player did not intend.
- **G2** — the named path gains normalization plus token containment. Rejected
  G3 (creator-populated alias table, reopening BRIEF-0075-c's D1),
  reactivation: a measured miss rate G2 cannot close. Rejected G4 (edit
  distance) without condition: a near-miss becomes a silent wrong match.
- **R2 in scope** — germ emission gains the collision guard and quota that
  TICKET-0019 gave the tick path. R1 (day-sourced germs mislabelled
  "conversation" by `routes/creator.py:174`, which reads `mut.tick_id`) and R3
  (no forward link from a day to an entity realized later) are named deferrals.
  R1 reactivation: wanting to distinguish origins in the pending-creations list.
  R3 reactivation: an explicit decision on the before/after link, never
  retroactive.

**Named deferral, out of scope, with a measured consequence to carry**:
an INFERRED place or faction resolves to nothing and is reported nowhere. No
rung fires (`occupation` and `presence` are persons-only), no germ is emitted
(D3), and `plan_context` skips non-person unmatched mentions (`:269`).
Consequence to state in BRIEF-0081-a: F1's first precedence criterion
("present at a place already matched in this call") is inert whenever the place
was inferred rather than named, because `place_candidate_ids` is built only from
`_rung_named_exact` (`day_concordance.py:160-169`). Reactivation: a measured
count of unresolved inferred place mentions over a corpus of real declarations.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `MATCHING_RUNGS` and `_RUNG_LOOKUPS` remain in bijection and include
      `named_token`  -> verify/checks/day_concordance.py
- [ ] `CAST_PRECEDENCE` and `_CAST_LOOKUPS` are in bijection, and `_cast_one`
      has no return path that yields no candidate  -> verify/checks/day_concordance.py
- [ ] `day_concordance.py` defines its own `connects_to` traversal and does not
      import `day_plan._day_reachable_ids`  -> verify/checks/day_concordance.py
- [ ] `day_concordance.py` still contains no `db.add(` and no `.commit(`
      (R1 purity, unchanged)  -> verify/checks/day_concordance.py
- [ ] `day_rewrite.py` imports no LLM client and constructs no canon model
      -> verify/checks/day_rewrite.py
- [ ] Neither `day_rewrite` nor `day_mention_resolution` is ever the target of
      an UPDATE anywhere in the tree  -> verify/checks/day_rewrite.py
- [ ] Zero `select(` in `day_concordance.py` or `day_rewrite.py` lacks a
      world scope at query construction  -> verify/checks/day_rewrite.py
- [ ] `plan_context` has no remaining caller in the tree
      -> verify/checks/day_rewrite.py
- [ ] `emit_germs` reads a collision guard and a quota constant
      -> verify/checks/day_concordance.py
- [ ] Every check above fails on an empty collection rather than passing
      vacuously  -> all three checks
- [ ] Schema doc version line and `EXPECTED_STATIC_SCHEMA_VERSION` agree
      -> verify/checks/schema_version_agreement.py (existing)

### Live  ->  human gate (Nia)

- [ ] A declaration naming a person with a qualifier ("Aldric le forgeron"
      against an entity named "Aldric") resolves, where it previously did not.
- [ ] A declaration referring to a role held by many NPCs ("un servant") plans
      without a 409, and the API return names which NPC was cast and on what
      basis.
- [ ] A declaration naming a person who does not exist still produces a germ,
      the germ still reaches "Creations en attente", and realizing it still
      creates the entity.
- [ ] Two active entities of the same type sharing a name produce a 409 naming
      both candidates, and nothing is committed.
- [ ] The API return for `/api/day/{id}/plan` shows the rendered rewrite, and
      the rewrite reads as the declaration with participants named.
- [ ] Resolving the same day does not re-run extraction (visible as three fewer
      model calls in the Ollama log for the resolve step).
- [ ] Declaring the same intent twice in a row produces the same rendered
      rewrite, character for character.
