---
id: TICKET-0033
title: Region wizard — full manifest/review editing, pre-commit location graph, global NPC relation graph, faction-roles commit fix
type: feature            # includes one corrective sub-item (BRIEF-0033-a, type bug)
status: live-gate
created: 2026-07-17
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
brief_ids: [BRIEF-0033-a, BRIEF-0033-b, BRIEF-0033-c, BRIEF-0033-d, BRIEF-0033-e]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Lors de la generation des appercus (manifest) : j'aimerais pouvoir modifie
> les champs qui ne sont pas modifiable en ce moment : le texte en haut
> (concept) s'il est reutilise, les noms des factions en plus des
> descriptions, ajoute/enlever des factions, lieux et NPC. La prochaine etape
> est faite a l'aide de la version modifiee.
>
> Ensuite je fais generer les fiches : pouvoir faire des modifications
> lorsque je suis sur l'entite que je veux modifier ; modifier les champs
> lorsque je zoom sur le lieu, la faction ou le NPC (nom, description, roles
> et tous les autres champs). Visualiser le graphe de lieux (reprendre
> l'existant). Visualiser le graphe de NPC — global cette fois, avec tous
> les NPC generes, disponible dans NPC aussi ; ajouter et retirer des liens
> entre les NPC (type, intensity, direction, note) ; clic sur un NPC =
> description, double-clic = il devient plus gros pour le suivre.
>
> J'ai un bug qui empeche le commit des roles dans les factions (a regler
> avant). Le graphe de lieux pre-commit est le besoin ; je veux qu'il ne
> soit pas toujours visible, juste si je l'ouvre. Le graphe NPC global
> repliable aussi.

## Clarifications resolved (intake)

- Q: Does the region creator reuse the atomic entity creators?
  A: Yes, confirmed — Phase B composes `entity_author.generate_entity_draft`
  as-is (`region_author.py:34, 454, 478, 545`). Only Phase A (manifest) has
  its own dedicated `region_manifest` prompt, by design. No work needed.
- Q: Is the concept reused downstream? A: Yes — injected into every
  composite faction/location/NPC brief (`region_author.py:242, 256, 269`)
  and the top-up (`:343`). Making it editable is meaningful.
- Faction-roles bug root cause (RECON): the faction draft carries
  `public.roles` (`entity_author.py:464`) and the review sheet displays
  them, but `_commit_region_factions` (`cockpit/routes/regions.py:135-165`)
  never writes `FactionRole` rows. Deterministic silent loss. The unitary
  faction creator commits roles correctly via
  `POST /api/factions/{id}/roles` (`index.html:8039-8048`).
- Locked decisions: A1 (manifest fully editable: concept, names,
  add/remove factions/locations/NPCs), B1 (zoom sheet becomes an editable
  form writing into the client-held draft; tree stays scannable), F1
  (faction roles editable in the review sheet, committed via the -a fix),
  C1 (pre-commit location graph, collapsible/on-demand, reusing the
  existing SVG renderer), D1 (global NPC relation graph in the NPC tab,
  collapsible, link editing via the existing relation CRUD), E1 (global
  mode: double-tap enlarges the node; ego mode keeps double-tap =
  recenter; link creation by tap-A-then-tap-B; tap edge = edit panel).
- Named deferral -> D2: NPC graph inside the region review (pre-commit)
  with staged links written at commit (reusing the stage-4 mechanism).
  Explicitly deferred to the NEXT ticket, to be opened immediately after
  TICKET-0033 closes. Not silently dropped.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] All existing verify checks pass on the merged tree  -> tooling/verify/
- [ ] `_commit_region_factions` writes FactionRole rows through
      `write_faction_role` (AST-visible call), no new commit points inside
      the region commit transaction  -> verify/checks/single_canon_write.py
      (existing) + review-step
- [ ] No new canon-write path outside the closed list  ->
      verify/checks/single_canon_write.py

### Live  ->  human gate (Nia)
- [ ] A region committed with faction roles in the draft shows those roles
      in `GET /api/factions/{id}/roles` and in the faction editor
- [ ] Manifest screen: concept, names editable; factions/locations/NPCs can
      be added and removed; "Generer les fiches" consumes the edited version
- [ ] Review screen: zoom sheet edits (name, description, roles, all
      displayed fields) survive into the committed entities
- [ ] Location graph opens on demand in the review (hidden by default),
      shows accepted locations + hierarchy + confirmed connections
- [ ] NPC tab: global graph mode shows all active characters, links can be
      added/edited/removed with type/intensity/direction/note; tap = info
      card, double-tap enlarges in global mode; panel remains on-demand
