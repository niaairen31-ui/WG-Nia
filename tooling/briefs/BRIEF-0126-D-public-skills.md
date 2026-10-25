<!-- slug: public-skills -->
# BRIEF 0126-D — "The visible skills join the public view"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: BRIEF-0126-C

## Anchors to confirm (Mini-RECON)

- `src/world_engine/perspective_selectors.py` is 281 lines; `PublicView` at
  :29-33 has three fields; `public_view` returns at :49;
  `PERSPECTIVE_SELECTORS` at :246, `_PERSPECTIVE_LOOKUPS` at :250,
  `PERSPECTIVE_DESCRIPTIONS` at :266, four keys each.
- `src/world_engine/perspective_audit.py:35-37` `WITHHELD_REASONS` has five
  reasons; :122 takes the `entity_id` argument with `next(...)`.
- `src/world_engine/lore_render.py:131-145` `_SECTION_FORMATTERS` has 13
  entries, the last `public_mentions`.
- `tooling/verify/checks/perspective_isolation.py:130-134` asserts 4 names.
- `src/world_engine/creation_rules.py` exports `visible_skill_ids(db,
  world_id)` (brief C).
- `.claude/rules/player-surface.md:17` opens `- **INV-66** A player surface
  learns about the world only through a`.

Halt if any anchor has moved.

## Facts carried

### R-12 -- the public view and the perspective selectors
Opened: `src/world_engine/perspective_selectors.py` (whole, 281 lines); the
enumeration (c)-4.
Finding: `PublicView(world_id, fact_ids, entity_ids)` is a frozen dataclass
(:29-33) built only by `public_view(db, world_id)` (:36-49): facts whose
public level is not `unaware` minus creator-only notes, and active
`is_public` entities. Members take `(*args, view, db)` and return rows
carrying `"section"`: `public_dossier` (:149-175, sections `identity`,
`facets`, `memberships`, `members`), `public_factions` (:178-202, section
`factions`, keys `entity_id, name, faction_type, description`),
`public_facts_mentioning` (:220-237, section `public_mentions`, every token
of 3+ letters present), `world_laws` (:240-243). `PERSPECTIVE_SELECTORS`
(:246-248), `_PERSPECTIVE_LOOKUPS` (:250-264, `SelectorSpec(fn, arity,
row_cap, arg_kinds, context_sections)`) and `PERSPECTIVE_DESCRIPTIONS`
(:266-281) share the four keys. The module imports `Entity, Fact,
FactionMembership, FactParticipant, Faction, Relation, WorldLaw` from
`.models`.
Consequence: D adds `skill_ids` to `PublicView` (built only at :49), a fifth
member `public_skills`, and its entries in the three tables, in that order
(C-07). The creation surfaces read places, factions and people through
this module's view (N2).
### R-14 -- the audit
Opened: `src/world_engine/perspective_audit.py` (whole, 128 lines).
Finding: `WITHHELD_REASONS = ("creator_only", "not_public",
"entity_not_public", "secret_membership", "faction_not_public")` (:35-37).
`withheld(plan, world_id, db, bindings=None)` handles `world_laws`
(nothing), `public_factions`, `public_facts_mentioning`, and otherwise
takes `next(a for a, kind in zip(call.args, spec.arg_kinds) if kind ==
"entity_id")` (:122) -- a selector with no `entity_id` argument that
reached this line would raise `StopIteration`.
Consequence: D gives `public_skills` its own branch before :122 and a sixth
reason, `skill_not_visible` (C-07).
### R-15 -- the Lore renderer's section vocabulary
Opened: `src/world_engine/lore_render.py:100-176` (340 lines).
Finding: `_SECTION_FORMATTERS` (:131-145) maps 13 sections to formatters;
`_group_rows_by_section` raises `ValueError` on a section it does not hold
(:157-161). `_format_laws` returns `row["text"]`; `_format_public_mentions`
quotes the content and appends the participants.
Consequence: D adds a `skills` formatter, or an answered question about
skills would raise at render (C-07).
### R-16 -- the perspective isolation check
Opened: `tooling/verify/checks/perspective_isolation.py:1-200, 280-300`.
Finding: PI1 forbids `chat(`, `db.add(`, `.commit(`,
`include_creator_only`, `CREATOR`, `NameScope("creator"`,
`near_candidates`, `validate_binding` and four `lore_selectors` imports in
the four perspective modules (`FORBIDDEN`, :61-64); PI2 asserts
`len(PERSPECTIVE_SELECTORS) == 4` (:130-134) and that the three tables
share its keys in order, every `row_cap` non-zero, every context section a
`"section"` literal; PI4 builds its world in `_build_world(engine)` (:172), which `player_routes.py` imports.
Consequence: D edits PI2's count to 5 and adds a rule PI6 (C-07). The
`creation_rules` module D imports must keep PI1 true for the perspective
modules: it is imported, never inlined, and holds none of PI1's needles
itself only by choice -- PI1 scans the four perspective modules, not it.
### R-17 -- the plan validator and selector spec
Opened: `src/world_engine/lore_selectors.py:30-50`;
`src/world_engine/lore_query.py:66-110, 163-171`.
Finding: `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections=())`.
`validate_plan(plan, db, *, lookups=None)` rejects a selector outside
`lookups`, a wrong arity and an arg-kind mismatch (`"$world"` for
`world_id`). `_call_args` passes the world id for `$world`.
Consequence: `public_skills` is `SelectorSpec(fn=public_skills, arity=1,
row_cap=200, arg_kinds=("world_id",))`, like `public_factions`.
### R-18 -- the shared perspective flow
Opened: `src/world_engine/cockpit/perspective_flow.py` (whole, 113 lines).
Finding: `ask_flow` pings (`ollama_client.ping()`), drafts the plan with
`descriptions=PERSPECTIVE_DESCRIPTIONS` (:73-74), runs it, audits, renders,
and journals through `_usage.record(..., kind="perspective", ...)`; on
`OllamaError` it journals `unavailable` and raises 503 with
`lore_render.PLANNER_UNAVAILABLE_MESSAGE`; on `LlmParseError` it journals
`parse_error` and raises 502.
Consequence: the planner sees `public_skills` as soon as D adds it to
`PERSPECTIVE_DESCRIPTIONS` -- nothing to change here. The designer route
(G) follows this ping / journal / status shape.
### R-35 -- the check fixture and the stubbed model
Opened: `tooling/verify/checks/world_sheet.py:48-62`;
`tooling/verify/checks/lore_usage.py:427-466, 655-665`;
`tooling/verify/checks/player_routes.py:88-130, 180-185`;
`.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` points `WORLD_ENGINE_DATABASE_URL` at a temp
file, sets `WORLD_ENGINE_ENV=test`, drops cached `world_engine` modules,
imports `world_engine.models` and runs `SQLModel.metadata.create_all`.
`_Stub(replies)` pops one reply per call (an `Exception` is raised, a dict
is JSON-dumped); `_swap(module, stub)` replaces `module.chat` and returns
the original; route tests use `TestClient(app,
base_url="http://127.0.0.1")`; `_seed_prompts` upserts heads through
`seed_pilot.upsert_prompt_template` after `sys.path.insert(0, scripts)`.
Rules: fail-closed, never Nia's DB, rows through sanctioned writers, every
rule proven by a named mutation.
Consequence: every DB check of this lot copies `_fresh_engine`'s body, and
the designer and route checks stub `chat` with `_Stub`/`_swap` and
`ollama_client.ping` by attribute.
### R-36 -- governance texts and budgets
Opened: `CLAUDE.md:234-254` (20 589 characters);
`.claude/rules/player-surface.md` (889), `skills.md` (2 896);
`tooling/verify/checks/claude_md_contract.py:1-76`;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last 15 lines).
Finding: budgets 22 000 characters for the root, 4 000 per rule file, 100
characters per line; every invariant bullet starts `- **INV-NN**` and ends
with `-- enforced by` and checks, or `[no check]`; ids run INV-01 to the
highest with none dropped; the highest is INV-66
(`player-surface.md:17`); a rule file opens with `paths:` globs that each
match a file; the root's « Path-scoped rules » list equals the files on
disk. ARCHITECTURE_DECISIONS ends with `---` then `*Co-built with Claude,
June 2026.*`; an entry is inserted above that footer.
Consequence: C creates `.claude/rules/character-creation.md` (INV-67) and
its list line in CLAUDE.md; D and F amend INV-66 in `player-surface.md`;
I inserts the ticket's entry above the footer.

## Contracts

### C-03 -- the creation rules reader
Produced by: C   Consumed by: C (C-04, C-06), D, F, G
Module: `src/world_engine/creation_rules.py`. Reads only: no write, no
flush, no commit, no model call.
```python
DEFAULT_POOL = 6
DEFAULT_COSTS: tuple[int, ...] = (0, 1, 1, 2, 3, 4)   # index = rank reached; index 0 unused
DEFAULT_CAPS: dict[int, Optional[int]] = {0: 2, 2: None, 3: None, 4: None, 5: None}
DEFAULT_MAX_RANK = 5
DEFAULT_MAX_MASTER_SKILLS = 1
DEFAULT_SKILLS_VISIBLE = True

@dataclass(frozen=True)
class CreationRuleSet:
    pool: int
    costs: tuple[int, ...]               # len 6, costs[0] == 0
    caps: tuple[tuple[int, Optional[int]], ...]   # (rank, cap) for CREATION_CAP_RANKS, in order
    max_rank: int
    max_master_skills: int
    skills_visible: bool
    def cap(self, rank: int) -> Optional[int]: ...   # None for a rank not in CREATION_CAP_RANKS

@dataclass(frozen=True)
class StartSkill:
    skill_key: str                 # a base domain literal, or a skill definition id
    name: str                      # the domain literal, or the definition's name
    base_domain: str
    system_id: Optional[str]
    system_name: Optional[str]
    description: Optional[str]     # the definition's; None for a base domain
    requires_master: bool
    start_rank: int                # 0 for requires_master, else DEFAULT_RANK
    max_rank: int                  # skill_max_rank
    visible: bool                  # skill_visible

def world_creation_rules(db, world_id: str) -> CreationRuleSet
def skill_visible(rules: CreationRuleSet, *, system, definition) -> bool
def skill_max_rank(rules: CreationRuleSet, *, system, definition) -> int
def visible_skill_ids(db, world_id: str) -> frozenset[str]
def start_sheet(db, world_id: str, rules: Optional[CreationRuleSet] = None) -> tuple[StartSkill, ...]
```
- `world_creation_rules`: the world's `creation_rules` row, else every
  `DEFAULT_*`; `costs = (0, cost_to_rank_1, ..., cost_to_rank_5)`.
- `skill_visible`: `definition.visible_at_creation` when `definition` is not
  None and that value is not None; else `system.visible_at_creation` under
  the same test; else `rules.skills_visible`. A base domain (`definition`
  None) is always True.
- `skill_max_rank`: the same cascade over `max_rank_at_creation`, ending at
  `rules.max_rank`; a base domain reads `rules.max_rank`.
- `visible_skill_ids`: the ids of the world's definitions for which
  `skill_visible` is True.
- `start_sheet`: the four base domains first, in `BASE_SKILL_DOMAINS` order
  (`skill_key = name = base_domain = domain`, start `DEFAULT_RANK`, system
  None, `requires_master` False, visible True), then every definition of
  the world, sorted by (system name, with no system last; definition name;
  id): `start_rank = 0` when `requires_master`, else `DEFAULT_RANK`.
### C-07 -- the visible skills in the public view
Produced by: D   Consumed by: F, G
In `perspective_selectors.py`:
- `PublicView` gains `skill_ids: frozenset[str]` (last field);
  `public_view` sets it to `creation_rules.visible_skill_ids(db, world_id)`.
- `public_skills(world_id, view, db) -> list[dict]`: one row per skill
  definition of the world in `view.skill_ids`: `{"section": "skills",
  "skill_id", "name", "base_domain", "system", "description",
  "requires_master"}`, `system` the system's name or None, `description` the
  definition's or None; sorted by (system name, with no system last; name;
  id).
- `PERSPECTIVE_SELECTORS` = `("public_dossier", "public_factions",
  "public_facts_mentioning", "world_laws", "public_skills")`;
  `_PERSPECTIVE_LOOKUPS["public_skills"] = SelectorSpec(fn=public_skills,
  arity=1, row_cap=200, arg_kinds=("world_id",))`;
  `PERSPECTIVE_DESCRIPTIONS["public_skills"] = "public_skills($world) -- les
  compétences de ce monde connues de tous : celles qu'un personnage peut
  choisir à sa création."`
In `perspective_audit.py`: `WITHHELD_REASONS` gains `"skill_not_visible"`
(last); in `withheld`, before the `entity_id` branch, a `public_skills`
call adds `("skill_not_visible", name, name)` for every skill definition of
the world not in `view.skill_ids`.
In `lore_render.py`: `_SECTION_FORMATTERS["skills"] = _format_skills`,
`_format_skills(row)` = `f"{name} ({system or 'sans système'},
{base_domain})"`, then ` ; exige un maître` when `requires_master`, then `
-- {description}` when `description`.

## Context

Nia chose one door (N2): what a player may know is the public view, and a
skill the creator made visible at creation is publicly known. This step
puts those skills in the view, gives the perspective a fifth selector --
also offered to the Lore planner, so « Ce que tout le monde sait » can
answer about skills -- and teaches the audit and the renderer the new
section. The creation screen (G, H) reads its catalogue through it.

## Scope IN

1. `perspective_selectors.py` per C-07: import `visible_skill_ids` from
   `.creation_rules` and `SkillDefinition, SkillSystem` from `.models`;
   `PublicView` gains `skill_ids: frozenset[str]` as its last field;
   `public_view` builds it (docstring gains « and the skill definitions
   visible at creation (`creation_rules.visible_skill_ids`) »);
   `public_skills` after `world_laws`, docstring « The skills everybody
   knows: the definitions visible at creation, one row each. »; the three
   tables gain `public_skills` last, with C-07's spec and description
   verbatim. The module docstring's list of what the view holds gains « and
   the skills visible at creation ».
2. `perspective_audit.py` per C-07: `"skill_not_visible"` appended to
   `WITHHELD_REASONS`; in `withheld`, right after the `public_factions`
   branch, `if call.selector == "public_skills":` adds the hidden skills
   (`SkillDefinition` rows of the world not in `view.skill_ids`) and
   `continue`s; the module docstring's list of reasons gains « a skill not
   visible at creation ».
3. `lore_render.py`: `_format_skills` beside `_format_public_mentions`, and
   `"skills": _format_skills` last in `_SECTION_FORMATTERS` (C-07).
4. `tooling/verify/checks/perspective_isolation.py`: PI2 expects 5 names
   (docstring « the same five keys »); a new rule **PI6** (docstring entry
   and function), on a fixture world of its own built in the check
   (`World`, two systems and three definitions added directly, as
   `_build_world` adds entities): system `Visible` (default), system
   `Cachée` (`visible_at_creation = False`); `Lame` in `Visible`, `Ombre` in
   `Cachée`, `Voix` in `Cachée` with `visible_at_creation = True`, `Voix`
   requiring a master. Exact sets: `public_view(...).skill_ids == {Lame,
   Voix}`; `public_skills` returns two rows, in this order: `Voix` (system
   `Cachée`), then `Lame` (system `Visible`); each row's keys are exactly C-07's; no row holds a
   forbidden key; `withheld` of a plan `public_skills($world)` is exactly
   `[{"reason": "skill_not_visible", "subject": "Ombre", "content":
   "Ombre"}]`; `execute_public_plan` of that plan is `answered`;
   `lore_render._serialize_rows_by_section` of its rows holds `- Voix
   (Cachée, <domain>) ; exige un maître` and `- Lame (Visible, <domain>)`.
5. `.claude/rules/player-surface.md`: replace the INV-66 bullet by, verbatim
   (each line under 100 characters):
   ```
   - **INV-66** A player surface learns about the world only through the
     public view (`perspective_selectors`, or `perspective_query` for a
     planned question), never a creator selector, the creator name regime,
     a trace, near names or the audit. A skill is in that view only when
     visible at creation (`creation_rules`); the creation rules themselves
     (pool, costs, caps) are game rules, read through `creation_rules`.
     Every perspective question is journaled with what was withheld. The
     perspective selectors read `faction_membership` with the
     `read_public_memberships` WHERE triplet, keyed by faction (a third
     sanctioned reader, INV-03). -- enforced by `perspective_isolation.py`,
     `player_routes.py`, `player_shell.py`
   ```
   and add `  - "src/world_engine/creation_rules.py"` to its `paths:`.
6. Commits: (1) items 1-3; (2) items 4-5.

## Scope OUT

- The creation catalogue route (G) and screen (H).
- A perspective of a character (0127); bindings for skills (a skill is not
  an entity: no mention, no binding).
- Changing `perspective_flow.py`: the planner already reads
  `PERSPECTIVE_DESCRIPTIONS` (R-18).
- Base domains in `public_skills`: they are no world lore; the catalogue
  (G) adds them itself.
- Any secret check on a skill's description (carried forward).

## Invariants to defend

- INV-66 (amended here): the public view stays the only door. PI1 must stay
  green: none of its needles may enter the four perspective modules;
  `creation_rules` is imported, never inlined.
- INV-58 (an empty verdict never reaches a model) and the audit's posture
  (creator and journal only): the new reason is journaled through the
  existing flow, never returned to a player.
- INV-01 (secrets): an invisible skill never appears in a player answer;
  PI6 proves it on the rows and the render.

## Decision rights

STOP:
- An anchor does not hold.
- PI1 fails because a needle is needed in a perspective module.
- `player_routes.py` changes verdict on PR4-PR7 (the player's answers must
  not move).

ADAPT:
- PI6's literal sort order disagrees with C-07's rule because of accents
  (`Cachée` vs `Visible`): keep C-07's rule (Python string order), fix the
  check's expected list, report.
- The Lore planner prompt names its selectors in a seeded text that lists
  them by name: report the text and leave it (the descriptions reach the
  planner at call time, R-18).

REPORT-ONLY:
- Worlds whose skills are all visible by default: every definition joins
  the view; that is N2.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/perspective_isolation.py`
      PASS (PI1-PI6).
- [ ] Named mutations, each turning PI6 red, then reverted: `public_view`
      sets `skill_ids` to every definition; the audit branch for
      `public_skills` is removed (the check sees a crash or an empty list);
      `_format_skills` drops the « exige un maître » part.
- [ ] `player_routes.py`, `lore_isolation.py`, `claude_md_contract.py`,
      `module_budget.py`, `corpus_gate.py` PASS.
- [ ] Live, in Lore > Perspective, « Quelles compétences existe-t-il ? »
      lists the visible skills and the audit names the hidden ones (noted
      for the ticket's live gate).
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `.claude/rules/player-surface.md` (Scope IN 5). No schema change.
