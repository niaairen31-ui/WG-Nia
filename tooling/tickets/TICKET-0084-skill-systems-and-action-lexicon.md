---
id: TICKET-0084
title: Skill systems and the action lexicon
type: feature
status: live-gate
created: 2026-09-11
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration, destructive_data]
blast_radius: medium
brief_ids: [BRIEF-0084-a, BRIEF-0084-b, BRIEF-0084-c, BRIEF-0084-d, BRIEF-0084-e]
schema_version_touched: v2.01, v2.02, v2.03
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je pense qu'il manque une compétence de base. magic, nullable a la création
> du monde si la magie n'existe pas. Parce que je n'ai rien pour categorisé mes
> compétenses de magie. En bonus, les nom de compétenses deviendront le lexique
> pour permettre de déterminer si l'action que le joueur veux faire est déja
> géré par un système de compétense qui pourra venir avec ses rêgles et ses jet
> ou son lore.

## Clarifications resolved (intake)

**A3 — magic is not a base domain; it is a world-authored SYSTEM.**
`BASE_SKILL_DOMAINS` stays at four. A new world-scoped table `skill_system`
holds named systems of rules (magic, technology, ritual, ...) and
`skill_definition.system_id` attaches a catalogue entry to one. A 5th base
domain was rejected: `resolution.py::resolve_physical` does not read `domain`
in its math, so a 5th domain buys nothing mechanically while breaking the
standing "strictly physical/sensory" design guard.

**B3 — magic's existence is row presence, never a flag.** A world where magic
does not exist simply owns no magic `skill_system` row, and therefore owns no
magic `skill_definition` rows either (FK). The arbiter clamp then cannot emit
a magic skill name for that world: exclusion is structural, by data absence,
the same idiom as secrets.

**D3 dropped.** Because of B3 there is no "matched skill whose system is absent"
case to refuse — the clamp already cannot produce it. Reactivation condition:
the day a world must keep its magic catalogue with magic mechanically switched
off (that needs `skill_system.status` and the refusal returns with it).

**C1 + C3a — the lexicon leaves Play, and matches by exact name.** The clamp
currently sealed inside `cockpit/play_physical.py::_arbitrate` moves to a
shared resolver. Matching stays exact-name, code-judged, fail-closed. C3b (an
alias table) is deferred; its reactivation condition is measurable off the new
`skill_resolution` table (see below).

**F2 — `skill_system`'s first reader is the creator surface.** Creation groups
the skill catalogue by system. `roll_spec` / differentiated rolls are OUT: the
rules are not decided, and a brief never embeds an unsettled design choice.

**G3 + verdicts persisted — one row per occurrence, append-only.** Named
`skill_resolution`, not `skill_gap`: it holds successful matches too. The
"holes in my world" view is a filter on it (`verdict = 'unmatched'`), and the
C3b reactivation counter is a query on it, not separate instrumentation.

**L1 — a resolution row is anchored by `conversation_id` alone.** Play is the
only caller in this ticket; the day-chain arm arrives with the ticket that
wires the day chain, and that ticket pays for the column.

**K dropped — the world-creation form is not touched.** No checkbox, no field.
`skill_system` rows are authored through Creation CRUD like everything else,
which makes that CRUD mandatory in BRIEF-0084-a rather than optional.

**J4 — `world.magic_status` is removed.** It has no reader, no creator surface,
and one writer (`scripts/seed_pilot.py`). Its two siblings were already dealt
with: `location.magic_status` was unplugged from every prompt surface by D3
(ARCHITECTURE_DECISIONS.md), and `faction.magic_knowledge_level` is named as
`fact_default`'s direct ancestor. Its own brief, its own migration, its own
commit.

**Named non-goal for the whole ticket.** The day chain is not wired to the
catalogue. `day_plan.py::_validate_step` keeps accepting only `null` or a base
domain. The lexicon serves Play only, in this ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `skill_system` and `skill_definition.system_id` exist with the exact DDL
      of BRIEF-0084-a  -> verify/checks/skill_system_shape.py
- [ ] `BASE_SKILL_DOMAINS` still has exactly four members, and
      `ck_skill_definition_base_domain` still lists exactly those four
      -> verify/checks/skill_system_shape.py
- [ ] `skill_resolution` is append-only: no `.delete()` and no UPDATE site
      against it anywhere under `src/`  -> verify/checks/skill_resolution_append_only.py
- [ ] every `skill_resolution` row satisfies the shape CHECK (verdict `base`
      carries `base_domain` only, `matched` carries `skill_definition_id` only,
      `unmatched` carries neither)  -> verify/checks/skill_resolution_append_only.py
- [ ] the exact-name clamp is total: any arbiter output outside
      `BASE_SKILL_DOMAINS ∪ catalogue names` yields verdict `unmatched` and the
      `physical` fallback, never an exception and never an unclamped value
      -> verify/checks/skill_lexicon_clamp.py
- [ ] `skill_resolution` is absent from `canon_write_policy.txt`
      `[CANON_TABLES]`  -> verify/checks/skill_resolution_append_only.py
- [ ] zero occurrences of `magic_status` on the `world` table remain in `src/`,
      `scripts/`, and the schema doc  -> verify/checks/no_world_magic_status.py
- [ ] `pytest`, `no_print_in_src.py`, `undefined_names.py`, `import_cycle.py`
      green after every brief

### Live  ->  human gate (Nia)

- [ ] Creation: a system can be created, renamed, described, and deleted; the
      skill catalogue displays grouped under its systems, and ungrouped skills
      appear under an explicit "no system" group
- [ ] Creation: deleting a system that still has skills attached is refused
      with a legible message, not a silent cascade
- [ ] Play: a physical turn naming a catalogue skill routes to that skill and
      writes one `matched` row
- [ ] Play: a physical turn naming nothing known still resolves normally on a
      base domain and writes one `unmatched` row carrying the rejected string
- [ ] Creation: the gaps view lists those rejected strings, most frequent
      first, and Nia can create a skill definition from what she reads there
- [ ] A world with no magic system cannot be made to produce a magic
      classification, by any phrasing tried in a live session
- [ ] The pilot world loads, plays a turn, and runs a day pass after the
      `world.magic_status` drop
