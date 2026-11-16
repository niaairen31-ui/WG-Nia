<!-- slug: neutral-selector-names -->
# BRIEF 0127-A — "The perspective selectors take neutral names (pure rename)"

Lot: LOT-0127-character-perspective.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `src/world_engine/perspective_selectors.py` is 338 lines; `class
  PublicView:` at :34; `def public_dossier(` at :175, `def public_factions(` at
  :204, `def public_facts_mentioning(` at :246, `def public_skills(` at :272;
  `PERSPECTIVE_SELECTORS` at :296-298 holds `"public_dossier",
  "public_factions", "public_facts_mentioning", "world_laws", "public_skills"`.
- The grep of R-03, re-run, prints exactly R-03's per-file line lists.
- `tooling/verify/checks/creation_designer.py:241` reads
  `if text.count("facts_mentioning(") != text.count("public_facts_mentioning("):`.
- `tooling/verify/checks/player_routes.py:63` and `:65` hold
  `"selector": "public_dossier"`.

Halt if any anchor has moved.

## Facts carried

### R-01 -- the base, the version, the free ids
Opened: `git log -1` (`6f4b578`, « Merge pull request #157 from
niaairen31-ui/ticket/0130 »); `world-engine-schema.md:3`;
`src/world_engine/schema_version.py:15`; `.claude/rules/*.md` (grep `INV-6`);
`ls tooling/lots tooling/briefs | grep 0127`.
Finding: `Current schema version: v2.33`;
`EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.33"`. The highest invariant is
INV-68 (`.claude/rules/character-creation.md:36`). No artifact of 0127 exists.
Consequence: no schema change, no migration, no new invariant in this lot;
E amends INV-01 and INV-66 in place.
### R-02 -- the public selectors
Opened: `src/world_engine/perspective_selectors.py:1-338` (whole).
Finding: `PublicView(world_id, fact_ids, entity_ids, skill_ids)`, frozen
dataclass (:33-38), built only by `public_view(db, world_id)` (:41-58: facts
whose public level is not `unaware`, minus `creator_only_fact_ids`; active
entities with `is_public`; `visible_skill_ids`). Helpers:
`_participant_facts(entity_id, world_id, db)` (:70-84) joins
`FactParticipant` and keeps `Fact.event_id.is_(None)` (:80), sorted by
registry facet order, `created_at`, id; `_relation_facts` (:87-99, lien facts,
`MAP_TOPOLOGY_TYPES` excluded); `_other_end` (:102-103);
`_current_memberships` (:106-116, any secrecy, audit only); `_public_members`
(:119-139, the `read_public_memberships` WHERE triplet keyed by faction, rows
`{section: "members", member_name, role}` kept when the member is in
`view.entity_ids`); `public_member_ids` (:142-156, ids for TICKET-0129's
approval); `_public_membership_rows` (:159-172, `read_public_memberships`
names kept only when every current membership of that name resolves to a
public faction). Members: `public_dossier` (:175-201: `[]` when the entity is
not in the view; rows `identity {section, entity_id, name, type}`, `facets
{section, label, aspect, content, secret}` with `secret: False`, lien rows
labelled `"Lien"` kept when the fact and the other end are in the view,
memberships, members for a faction); `public_factions` (:204-228, SQL filter
`Entity.is_public == True` at :210, rows `{section: "factions", entity_id,
name, faction_type, description}`); `_facts_matching` (:231-243, every fact of
the world whose CURRENT rendered text holds every token of 3+ letters);
`public_facts_mentioning` (:246-263, rows `{section: "public_mentions",
content, participants}`, participants from `FactParticipant` in the view);
`world_laws` (:266-269, `{section: "laws", position, text}`); `public_skills`
(:272-293, `{section: "skills", skill_id, name, base_domain, system,
description, requires_master}`). Tables (:296-338): `PERSPECTIVE_SELECTORS`
(five names), `_PERSPECTIVE_LOOKUPS` (`public_dossier` with
`context_sections=("identity",)`, arity/row caps 2/400, 1/200, 2/200, 1/100,
1/200), `PERSPECTIVE_DESCRIPTIONS`.
Consequence: A renames the members and the view class (C-01); B extends the
view (C-02); C makes every member read through the view's facts, entities
and texts (C-05, C-06) and adds a sixth member for a character (C-07).
### R-03 -- every reference to a symbol A renames (protocol step 4)
Opened: the grep below at `6f4b578`, history folders excluded.
Finding (pasted):
```
$ grep -rn "public_dossier\|public_factions\|public_facts_mentioning\|public_skills\|PublicView" src/world_engine tooling/verify/checks frontend/src --include=*.py --include=*.js --include=*.svelte | grep -v "/static/"   (lines per file)
src/world_engine/cockpit/routes/player_creation.py: 31 160 173
src/world_engine/creation_designer.py: 32 122 225 235 310
src/world_engine/creation_lore.py: 5 6 20 37 90 95 99
src/world_engine/pc_draft_reads.py: 4 18 21 28 34
src/world_engine/perspective_audit.py: 26 46 55 81 90 117 120 124
src/world_engine/perspective_query.py: 23 41 46 70
src/world_engine/perspective_selectors.py: 6 34 41 55 119 142 159 175 204 246 266 272 297 301 302 305 306 308 309 314 315 320 321 324 325 327 328 334 335
tooling/verify/checks/creation_designer.py: 19 241 242
tooling/verify/checks/perspective_isolation.py: 32 34 49 51 292 305 306 315 322 351 432 458 460 468 471 476
tooling/verify/checks/player_routes.py: 12 63 65
```
No frontend file names a selector. `tooling/verify/checks/creation_designer.py:241`
counts `facts_mentioning(` against `public_facts_mentioning(`;
`player_routes.py:62-65` holds `HERO_PLAN` and `TWIN_PLAN` on
`"public_dossier"`. `world_laws` also names `writes.write_world_laws`; that
symbol is not renamed.
Consequence: A updates exactly these files (each hit, docstrings included);
the counter of `creation_designer.py` CD3 counts `known_facts_mentioning(`
after A (the new name still contains `facts_mentioning(`). Historical
artifacts (`tooling/tickets`, `lots`, `briefs`, `recon`,
`ARCHITECTURE_DECISIONS.md`) are never edited.
### R-04 -- the public executor
Opened: `src/world_engine/perspective_query.py:1-122` (whole).
Finding: `PERSPECTIVE_VERDICTS = ("answered", "ambiguous_mention",
"nothing_known", "unsupported_selector")` (:25); `BindingRefused(ValueError)`
(:28); `PerspectiveResult(verdict, rows, ambiguous, rejection_reason)` (:33-38);
`public_scope(view)` -> `NameScope("public", known_fact_ids=view.fact_ids)`
(:41-42); `resolve_public_mentions(plan, world_id, db, view, bindings=None)`
(:45-67: unknown binding refs and a binding outside the mention's candidates
raise `BindingRefused`, a valid binding becomes `pre_resolved`);
`_ambiguous_items` (:70-86, candidates kept in `view.entity_ids`, keys
`entity_id, name, type`); `execute_public_plan(plan, world_id, db,
bindings=None)` (:89-122): `validate_plan(..., lookups=_PERSPECTIVE_LOOKUPS)`
first (invalid -> `unsupported_selector`), then `public_view`, resolutions,
`ambiguous_mention`, any `unmatched` -> `nothing_known`, every call through
`_PERSPECTIVE_LOOKUPS` with `_call_args`, a row without `"section"` raises,
truncation at `row_cap`, `answered` iff a row lies outside the spec's
`context_sections`. Callers (grep `execute_public_plan|resolve_public_mentions|public_scope`):
`cockpit/perspective_flow.py:27,44`; `perspective_audit.py:23,103`;
`creation_lore.py:19,79` and `creation_designer.py:31,228` (`public_scope`);
`perspective_isolation.py:278,293,307,310,316,322,325,347,352,359,431,474`.
Consequence: D generalizes the executor over a view (C-09) and keeps
`execute_public_plan` and `public_scope` with their signatures for these
callers.
### R-05 -- the public audit
Opened: `src/world_engine/perspective_audit.py:1-137` (whole).
Finding: `WITHHELD_REASONS` (:35-38, six values: `creator_only, not_public,
entity_not_public, secret_membership, faction_not_public, skill_not_visible`);
`_membership_line(name, membership)` -> `"Name (role or -)"` (:41-43);
`_withheld_facts` (:46-52: facts not in the view, `creator_only` when
creator-only else `not_public`); `_withheld_dossier` (:55-78);
`_withheld_factions` (:81-87); `_withheld_skills` (:90-92);
`withheld(plan, world_id, db, bindings=None)` (:95-137): `[]` for an invalid
plan or an ambiguous mention, an unmatched mention re-resolved under
`NAMES_ONLY`, per call: `world_laws` nothing, `public_factions`,
`public_skills`, `public_facts_mentioning` (`_facts_matching` on the searched
text), else the dossier of the bound entity; rows `{"reason", "subject",
"content"}` sorted. The literal `"subject"` occurs once in the module (:135).
Consequence: D adds the character's reasons and a view-taking entry point
(C-10); the public output stays byte-identical; no new `subject` reference
(R-25).
### R-22 -- the checks of the perspective, the player's door and the shell
Opened: `tooling/verify/checks/perspective_isolation.py:1-80, 108-153, 182-270`;
`player_routes.py:1-70, 74-165, 308-358`; `player_shell.py:1-40, 80-100`;
`name_index.py:1-40, 285-310`; `creation_designer.py:14-24, 228-250`;
`knowledge_identity.py:31-34, 125-131, 842-863`.
Finding: PI1 (`MODULES` :70; `FORBIDDEN` :71-72 holds `chat(`, `db.add(`,
`.commit(`, `include_creator_only`, `CREATOR`, `NameScope("creator"`,
`near_candidates`, `validate_binding`; `CREATOR_SELECTORS` :73);
`FORBIDDEN_KEYS = {"is_secret", "is_incorrect", "intensity", "internal_name",
"knowers", "creator_only", "level"}` (:74); PI2 (:137-152) requires five
public names and the three tables in their order; PI3 the verdict literals;
PI4 builds the world `_build_world(engine)` (:182-255: Hero, Shade
(non-public), Guild, Guild2, Cabal (non-public), two public Twins; F1-F7;
Hero in Guild, Cabal and secretly Guild2; one law) and plans with
`_plan(selector, *, mention=None, text=None)` (:258-265). player_routes:
harness `_fresh_engine` (:74), `_seed_prompts(db)` (:91), `_Stub(replies)`
with `.messages` (:113-122), `_swap(module, stub)` (:125-128), `_events`
(:131), `_all_events` (:140), `_attempt(n)` (:149), `_one` (:153);
`PLAYER_KEYS`, `CREATOR_KEYS` (:58-59); PR8 (:320-358): `lore_perspective.py`
and `perspective_flow.py` hold no `chat(` nor `select(`, `player.py` no
`chat(` and `select(` naming only `User`, `World`, `WorldLaw`, none holds
`World.is_active`, `_world_id(`, `write_usage_event`, `lore_selectors`, and
every route path of `player.py` starts `/api/joueur/`. player_shell PSH1
requires five French reason labels in `PerspectivePanel.svelte`; PSH2 every
URL literal under `frontend/src/joueur/` starts `/api/joueur/`; PSH3 no
import out of that folder; PSH5 a built asset carries a creation string.
knowledge_identity K3 pins one `subject` reference in `perspective_audit.py`.
Consequence: each brief names which of these it must keep green or extend;
CP (the new check, C-15) imports `_build_world`, `_plan` and the harness of
`player_routes.py` rather than copying them.
### R-25 -- name bans across `src/`
Opened: `tooling/verify/checks/knowledge_identity.py:31-34, 842-863` (K3:
attribute `.subject`, constant `"subject"`, keyword or parameter `subject`,
counted per file); `lore_as_facts.py:8-11` (R1: no attribute `appearance,
backstory, secrets, philosophy, internal_structure, internal_tensions,
aversion, goals` outside `models/`); `event_contexts.py:72, 334-337` (ED4:
no attribute `knowledge_status, occurred_at, has_magic_impact,
consequences`, no `EventEntity`); PI1 `FORBIDDEN` (R-22); PR8 `FORBIDDEN_ALL`.
Finding: every name this lot introduces was tested against them: `Belief`,
`beliefs`, `certainty`, `door`, `kind`, `member_of`, `character_name`,
`character_view`, `player_character_of`, `world_characters`,
`UnknownCharacter`, `CERTAINTY_LABELS`, `known_dossier`, `known_factions`,
`known_facts_mentioning`, `known_skills`, `self_sheet`, `acquaintances`,
`own_skills`, `rank_label`, `view_texts`, `lookups_for`, `descriptions_for`,
`perspective_scope`, `resolve_view_mentions`, `execute_perspective_plan`,
`withheld_for`, `render_perspective`: none is banned.
Consequence: no brief writes the literal `"subject"`, a `subject=` keyword or
parameter, nor any banned attribute; the audit keeps its one dict line.

## Contracts

### C-01 -- neutral names (pure rename)
Produced by: BRIEF-0127-A   Consumed by: BRIEF-0127-B, C, D, E
Renames, exactly, and nothing else:
- `perspective_selectors.PublicView` -> `PerspectiveView` (same fields, same
  order, same `public_view` constructor).
- `public_dossier` -> `known_dossier`; `public_factions` -> `known_factions`;
  `public_facts_mentioning` -> `known_facts_mentioning`; `public_skills` ->
  `known_skills`. `world_laws` keeps its name.
- `PERSPECTIVE_SELECTORS == ("known_dossier", "known_factions",
  "known_facts_mentioning", "world_laws", "known_skills")`; the keys of
  `_PERSPECTIVE_LOOKUPS` and `PERSPECTIVE_DESCRIPTIONS` alike, same order. In
  each description string only the leading selector name changes.
Unchanged: `public_view`, `public_member_ids`, every private helper,
`public_scope`, `resolve_public_mentions`, `execute_public_plan`, `withheld`,
`render_public`, section names (`public_mentions` included), row keys,
`WITHHELD_REASONS`, behaviour.
Error and empty cases: none (no behaviour change).

## Context

TICKET-0127 adds a character's perspective beside the public one, with
one code for both (A1). The selectors were named for the public view; they
take neutral names first, in a commit that changes no behaviour, so the
briefs that follow change logic on names that will stay.

## Scope IN

1. `src/world_engine/perspective_selectors.py`: apply C-01 -- the class
   `PublicView` becomes `PerspectiveView` (every annotation in the module
   follows); the four member definitions are renamed; the three tables use
   the new keys in the same order, `SelectorSpec(fn=...)` pointing at the
   renamed functions; in each `PERSPECTIVE_DESCRIPTIONS` string only the
   leading `public_xxx(` becomes `known_xxx(`. The module docstring's
   `PublicView` (:6) becomes `PerspectiveView`; its first sentence is
   unchanged.
2. `src/world_engine/perspective_query.py:23, 41, 46, 70`: the import and the
   annotations name `PerspectiveView`.
3. `src/world_engine/perspective_audit.py`: the import block (:24-32) names
   `PerspectiveView`; annotations at :46, :55, :81, :90; the selector-name
   literals at :117 (`"known_factions"`), :120 (`"known_skills"`), :124
   (`"known_facts_mentioning"`).
4. `src/world_engine/creation_lore.py`: docstring :5-6 names
   `known_dossier` and `known_facts_mentioning`; the import at :20; the
   annotation at :37; the calls at :90, :95, :99.
5. `src/world_engine/creation_designer.py`: the import at :32 and the
   annotations at :122, :225, :235, :310.
6. `src/world_engine/pc_draft_reads.py`: docstring :4, import :18,
   annotations :21, :28, :34.
7. `src/world_engine/cockpit/routes/player_creation.py`: the import at :31
   and the calls at :160, :173.
8. `tooling/verify/checks/perspective_isolation.py`: the docstring lines
   :32, :34, :49, :51 and the code lines :292, :305, :306, :315, :322, :351,
   :432, :458, :460, :468, :471, :476 use the new names.
9. `tooling/verify/checks/player_routes.py`: docstring :12 and `HERO_PLAN`,
   `TWIN_PLAN` (:63, :65) name `known_dossier`.
10. `tooling/verify/checks/creation_designer.py`: docstring :19 and CD3
    (:241-242) count `known_facts_mentioning(` and say so in the message
    (« calls facts_mentioning( outside known_facts_mentioning( »).
11. One commit: « TICKET-0127 A: the perspective selectors take neutral
    names (pure rename, C-01) ».

## Scope OUT

- Any behaviour change, any new field, any new selector (B, C).
- `public_view`, `public_member_ids`, `public_scope`,
  `resolve_public_mentions`, `execute_public_plan`, `withheld`,
  `render_public`, private helpers, section names, row keys: unchanged here.
- `world_laws` and `writes.write_world_laws`: not renamed.
- Historical artifacts (`tooling/tickets`, `lots`, `briefs`, `recon`,
  `ARCHITECTURE_DECISIONS.md`): never edited.
- FILE_MAP: no first sentence changes in this brief; do not regenerate unless
  `file_map.py` says so (then ADAPT).

## Invariants to defend

- INV-66 (`.claude/rules/player-surface.md`): the player's surface reads
  the world only through the perspective selectors -- a rename must not route
  any caller to a creator selector (`entity_dossier`, `facts_mentioning`,
  `world_factions`, `who_knows_about`). CD3 and PI1 guard it; both must stay
  green.
- INV-03: the membership readers are untouched.

## Decision rights

STOP:
- An anchor does not hold.
- A file outside R-03's list names a renamed symbol.
- A check other than those of Scope IN 8-10 needs an edit to stay green.

ADAPT:
- `file_map.py` reports a stale map: run `python tooling/glue/gen_file_map.py`,
  commit the result with the rename, report.
- A comment (not a docstring) names a renamed symbol in a file of R-03's
  list on a line R-03 did not count: rename it, report.

REPORT-ONLY:
- Any wording of a description string beyond its leading selector name.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after (paste both).
- [ ] `grep -rn "public_dossier\|public_factions\|public_facts_mentioning\|public_skills\|PublicView" src/world_engine tooling/verify/checks frontend/src --include=*.py --include=*.js --include=*.svelte | grep -v "/static/"`
      prints nothing (paste the empty output).
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/<name>.py` PASS for
      `perspective_isolation.py`, `player_routes.py`, `player_shell.py`,
      `creation_designer.py`, `player_creation.py`, `draft_approval.py`,
      `creator_review.py`, `knowledge_identity.py`, `name_index.py`,
      `file_map.py`, `module_budget.py`.
- [ ] Named mutation, red then reverted: in `creation_lore.py`, call
      `facts_mentioning(` (any argument) once -> `creation_designer.py` CD3
      red.
- [ ] `corpus_gate.py`: every check green except the ones the ticket's
      arrows name that B creates (`character_perspective.py` missing is the
      expected red until B lands); name them in the report.
- [ ] /review-step and /close-step run.

## Docs to update

This step changes no document: no schema entry, no decision entry (E
writes the ticket's), no CLAUDE.md line.
