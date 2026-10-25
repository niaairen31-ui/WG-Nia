<!-- slug: character-designer -->
# BRIEF 0126-F — "The character designer reads only what everybody knows"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: BRIEF-0126-B, BRIEF-0126-C, BRIEF-0126-D (order of the INV-66 edits)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/world_premise.py:75` is `def world_premise(db: Session,
  regime: str, *, entity_type: Optional[str] = None) -> str:` and :80 reads
  the `is_active` world; :108 `def fill(text: str, db: Session, usage: str,
  *, entity_type: Optional[str] = None) -> str:`.
- `src/world_engine/prompt_call.py:29-32` signature `call_json(db, usage,
  values, exchanges, chat)`, two `fill(` calls at :35-36.
- `src/world_engine/prompt_registry.py` holds `quest_subject` with
  `premise="creator"`; `_author_model` defined at module level.
- `tooling/verify/checks/world_premise.py:79-84` `PLAYER` holds 15 usages;
  :616 the PASS line names « 47 usages » and « 14/15/18 ».
- `scripts/seed_pilot.py` defines `QUEST_DESIGNER_PROMPT_HEADS` (~:2496) and
  loops over it at ~:3624; `scripts/apply_ticket_0121_designer_prompts.py`
  exists.
- `src/world_engine/perspective_selectors.py` exports `public_view`,
  `public_dossier`, `public_factions`, `public_facts_mentioning`;
  `PublicView` has `skill_ids` (brief D); `perspective_query.public_scope`
  exists.
- `src/world_engine/creation_check.py` exports `check_creation`,
  `Violation`; `creation_rules.py` exports `world_creation_rules`,
  `start_sheet` (brief C).
- `.claude/rules/player-surface.md` INV-66 holds the sentence `Every
  perspective question is journaled with what was withheld.` (brief D).

Halt if any anchor has moved.

## Facts carried

### R-06 -- the rank ladder reader
Opened: `src/world_engine/skill_ranks.py` (whole, 163 lines).
Finding: `RANKS = (0, 1, 2, 3, 4, 5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`
(« A new skill row starts here: Initié »), `DEFAULT_RANK_LABELS =
("Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître")`.
`world_ladder(db, world_id)` returns six `RankStep(rank, label,
points_to_next, trial_to_next)` over the engine defaults and never writes.
`points_to_next` and `trial_required` read the most specific override:
`definition`, then `system`, then the ladder (`getattr(owner, column, None)`
when the owner is not None). `skill_owners(db, skill_definition_id)` returns
`(system, definition)`, `(None, None)` for a base domain. Reads only.
Consequence: `creation_rules` (C-03) follows the same cascade order --
definition, then system, then the world's row, then the engine default --
and is reads only. The ladder's labels name the ranks in every French
message of C-04.
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
### R-13 -- the public executor and name scope
Opened: `src/world_engine/perspective_query.py` (whole, 122 lines);
`src/world_engine/name_index.py:48-68`; `src/world_engine/lore_resolve.py:30-75,
135-160`.
Finding: `public_scope(view)` is `NameScope("public",
known_fact_ids=view.fact_ids)`; `execute_public_plan` validates against
`_PERSPECTIVE_LOOKUPS`, resolves mentions under that scope and raises
`ValueError` on a row without `"section"`. `NameScope` requires
`known_fact_ids` for the `public` regime. `resolve_named(surface_form,
category, world_id, db, *, scope)` returns `NamedResolution(verdict,
entity_id, candidate_ids, rung, rungs_tried)`, verdict `matched` (one
candidate), `ambiguous` or `unmatched`; `CATEGORIES = ("place", "person",
"faction", "object", "other")` (:43); `normalize_surface(text)` (:73).
Consequence: the creation lore resolves the backstory's names with
`resolve_named(..., scope=public_scope(view))`, keeping `matched` only
(C-10).
### R-20 -- the world premise
Opened: `src/world_engine/world_premise.py` (whole, 131 lines);
`tooling/verify/checks/world_premise.py:1-90, 180-190, 610-620`.
Finding: `world_premise(db, regime, *, entity_type=None)` reads the
`is_active` world (:80) -- a player route keyed by world cannot use it as
it is. The `player` regime gives name, description, tone, laws, never a
skill system nor a state. `fill(text, db, usage, *, entity_type=None)`
replaces `{world_premise}` and runs no query when the text holds none. The
check's WP1 compares each regime's usages with literal tuples `CREATOR`
(14), `PLAYER` (15, :79-84) and `NONE` (18); its PASS line names « 47
usages » and « 14/15/18 » (:616).
Consequence: F adds a keyword `world_id=None` to `world_premise` and
`fill` (None keeps the active world: every current caller is unchanged)
and adds the designer's two usages to WP1's `PLAYER` tuple, its docstring
count (17) and its PASS line (49 usages, 14/17/18) (C-09).
### R-21 -- one templated JSON call
Opened: `src/world_engine/prompt_call.py` (whole, 47 lines);
`src/world_engine/prompt_load.py:50-72`; `src/world_engine/llm_parse.py:44-60`;
`src/world_engine/ollama_client.py:39, 73`.
Finding: `call_json(db, usage, values, exchanges, chat)` loads the usage's
head (`prompt_load.load`: active template, current version, effective
model), fills both texts with `fill(..., db, usage)` (exactly two `fill(`
calls, WP3 of `world_premise.py` asserts it), replaces `{key}` in the user
message only, records the exchange, calls `chat(..., format="json")` and
returns `llm_parse.extract_object(raw)` (`LlmParseError` on no object).
`OllamaError` (a `RuntimeError`) and `ping()` live in `ollama_client`.
Consequence: F adds `world_id: Optional[str] = None` to `call_json`, passed
to both `fill` calls (still two). Every variable of the designer's prompts
lives in the user template.
### R-22 -- the prompt registry and its check
Opened: `src/world_engine/prompt_registry.py:1-75, 340-380`;
`tooling/verify/checks/prompt_registry.py:1-30, 78-80, 120-150`.
Finding: `PromptSpec(surface, world_scoped, dry_run_capable, call_sites,
default_model, premise, premise_reason="")`; the quest designer's entries
are `surface="authoring"`, `world_scoped=False`, `dry_run_capable=True`,
`call_sites=("src/world_engine/quest_designer.py:_subject",)`,
`default_model=_author_model`, `premise="creator"`. The check requires the
registry keys to equal the usages seeded in `scripts/seed_pilot.py` and
every call site `path:function` to name a file holding `^def function(`.
Consequence: F adds `creation_subject` and `creation_design` with
`premise="player"`, call sites in `creation_designer.py` on module-level
functions (C-11), and seeds both.
### R-23 -- seeding and delivering designer prompts
Opened: `scripts/seed_pilot.py:134-160, 2350-2420, 2490-2520, 3620-3630`;
`scripts/apply_ticket_0121_designer_prompts.py` (whole, 59 lines);
`tooling/verify/checks/prompt_lean.py:1-25`.
Finding: `premised_texts(usage, system_prompt, user_template, variables)`
prefixes `{world_premise}` for a `creator` or `player` usage and appends
the variable; `upsert_prompt_template(session, id, *, system_prompt,
user_template, **head_fields)` writes v1 on a virgin head only. Heads are
tuples of dicts (`QUEST_DESIGNER_PROMPT_HEADS`, keys `id, name, usage,
world_id=None, system_prompt, user_template, variables, destination
"local"`), seeded in a loop at :3624-3627. The 0121 delivery script embeds
no text: it refuses unless `WORLD_ENGINE_ENV` is `prod` or `test`, upserts
each head of the tuple and prints `created` / `updated` / `existing`.
`prompt_lean.py` rule 2: no `*_SYSTEM_PROMPT` / `*_USER_TEMPLATE` constant
holds a pilot identifier.
Consequence: F adds `CREATION_SUBJECT_*`, `CREATION_DESIGN_*` constants
(no proper name of any world in them), `CHARACTER_DESIGNER_PROMPT_HEADS`,
its seed loop line, and `scripts/apply_ticket_0126_designer_prompts.py`
on the 0121 model.
### R-24 -- the quest designer's call pattern
Opened: `src/world_engine/quest_designer.py:1-60, 84-105`.
Finding: the module imports `chat` from `.ollama_client` and calls
`prompt_call.call_json(db, USAGE, values, exchanges, chat)`; a check
swaps `<module>.chat`. `OllamaError` and `LlmParseError` propagate; the
caller rolls back.
Consequence: `creation_designer.py` imports `chat` the same way, so a check
swaps `creation_designer.chat`.
### R-25 -- zones and visitable places
Opened: `src/world_engine/zone_rules.py:32-84`.
Finding: `is_zone(db, location_id)` is true when the location has an active
child; `zone_ids(db, world_id)` returns every zone of the world;
`require_visitable` refuses a zone.
Consequence: a starting place is a location in `view.entity_ids` that is
not in `zone_ids(db, world_id)` (D1, C-10).
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

### C-02 -- schema v2.32
Produced by: B   Consumed by: C, D, F, G, I
**`models/canon_skill.py` gains:**
```python
CREATION_COST_COLUMNS: tuple[str, ...] = tuple(f"cost_to_rank_{n}" for n in range(1, 6))
CREATION_CAP_RANKS: tuple[int, ...] = (0, 2, 3, 4, 5)
CREATION_CAP_COLUMNS: tuple[str, ...] = tuple(f"cap_at_rank_{r}" for r in CREATION_CAP_RANKS)
CREATION_RULES_CHECK = " AND ".join(
    ["pool >= 0", "max_rank BETWEEN 1 AND 5", "max_master_skills >= 0"]
    + [f"{c} >= 0" for c in CREATION_COST_COLUMNS]
    + [f"({c} IS NULL OR {c} >= 0)" for c in CREATION_CAP_COLUMNS]
)

class CreationRules(SQLModel, table=True):
    __tablename__ = "creation_rules"
    __table_args__ = (
        Index("idx_creation_rules_world", "world_id", unique=True),
        CheckConstraint(CREATION_RULES_CHECK, name="ck_creation_rules_values"),
    )
    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    pool: int = Field(default=6, sa_column_kwargs={"server_default": text("6")})
    cost_to_rank_1: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_2: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_3: int = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cost_to_rank_4: int = Field(default=3, sa_column_kwargs={"server_default": text("3")})
    cost_to_rank_5: int = Field(default=4, sa_column_kwargs={"server_default": text("4")})
    cap_at_rank_0: Optional[int] = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cap_at_rank_2: Optional[int] = None
    cap_at_rank_3: Optional[int] = None
    cap_at_rank_4: Optional[int] = None
    cap_at_rank_5: Optional[int] = None
    max_rank: int = Field(default=5, sa_column_kwargs={"server_default": text("5")})
    max_master_skills: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    skills_visible: bool = Field(default=True, sa_column_kwargs={"server_default": text("1")})
    updated_at: datetime = _created_ts()
```
A cap of NULL is « no cap »; a missing row is every default above.
`SkillSystem` gains, after `trial_to_rank_5`: `visible_at_creation:
Optional[bool] = None`, `max_rank_at_creation: Optional[int] = None`,
`cap_raised_at_creation: Optional[int] = None`, `cap_held_at_creation:
Optional[int] = None`. `SkillDefinition` gains, after `trial_to_rank_5`:
`visible_at_creation: Optional[bool] = None`, `max_rank_at_creation:
Optional[int] = None`. NULL inherits. No CHECK on them (R-04).

**`models/pc_drafts.py`** (non-canon; a player's character draft):
```python
PC_DRAFT_STATUSES: tuple[str, ...] = ("draft", "submitted", "returned", "approved")
PC_DRAFT_ORIGINS: tuple[str, ...] = ("player", "designer")
PC_SKETCH_KINDS: tuple[str, ...] = ("family", "master", "faction", "other")
PC_KNOWLEDGE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows")
PC_SKETCH_MAX = 8
```
- `PcDraft` (`pc_draft`): `id`; `world_id` FK world NOT NULL; `user_id` FK
  `user.id` NOT NULL; `status: str` default `'draft'` (server default);
  `name: str` default `''`; `backstory: str` default `''`;
  `start_location_id: Optional[str]` FK entity; `start_location_set_by:
  Optional[str]`; `creator_note: Optional[str]`; `submitted_at:
  Optional[datetime]`; `created_at`, `updated_at` (`_created_ts()`).
  CHECKs `ck_pc_draft_status` (`status IN ('draft','submitted','returned',
  'approved')`), `ck_pc_draft_set_by` (`start_location_set_by IS NULL OR
  start_location_set_by IN ('player','designer')`). Indexes
  `idx_pc_draft_world` (`world_id`), `idx_pc_draft_open` unique on
  `(world_id, user_id)` where `status <> 'approved'`.
- `PcDraftSkill` (`pc_draft_skill`): `id`; `draft_id` FK `pc_draft.id` NOT
  NULL; `world_id` FK world NOT NULL; `skill_key: str`; `player_rank:
  Optional[int]`; `designer_rank: Optional[int]`; `justification:
  Optional[str]`; `designer_reason: Optional[str]`. CHECKs
  `ck_pc_draft_skill_ranks` (`(player_rank IS NULL OR player_rank BETWEEN 0
  AND 5) AND (designer_rank IS NULL OR designer_rank BETWEEN 0 AND 5)`),
  `ck_pc_draft_skill_some` (`player_rank IS NOT NULL OR designer_rank IS NOT
  NULL`). Unique index `idx_pc_draft_skill_key` (`draft_id, skill_key`).
- `PcDraftSketch` (`pc_draft_sketch`): `id`; `draft_id`; `world_id`;
  `position: int`; `name: str`; `role: str` default `''`; `sentence: str`
  default `''`; `group_label: str` default `''`; `kind: str`; `skill_key:
  Optional[str]`; `existing_entity_id: Optional[str]` FK entity; `origin:
  str`. CHECKs `ck_pc_draft_sketch_kind` (`kind IN ('family','master',
  'faction','other')`), `ck_pc_draft_sketch_master` (`(kind = 'master') =
  (skill_key IS NOT NULL)`), `ck_pc_draft_sketch_origin` (`origin IN
  ('player','designer')`). Index `idx_pc_draft_sketch_draft` (`draft_id`).
- `PcDraftMembership` (`pc_draft_membership`): `id`; `draft_id`;
  `world_id`; `faction_id` FK entity NOT NULL; `role: Optional[str]`;
  `origin: str`. CHECK `ck_pc_draft_membership_origin`; unique index
  `idx_pc_draft_membership_faction` (`draft_id, faction_id`).
- `PcDraftKnowledge` (`pc_draft_knowledge`): `id`; `draft_id`; `world_id`;
  `position: int`; `level: str`; `content: str`; `origin: str`. CHECKs
  `ck_pc_draft_knowledge_level` (`level IN ('rumor','suspicious','partial',
  'knows')`), `ck_pc_draft_knowledge_origin`. Index
  `idx_pc_draft_knowledge_draft` (`draft_id`).
Every string default carries `server_default text("''")`; `status` carries
`text("'draft'")`. No JSON column, no `change_history`.

**Journal.** `LORE_USAGE_STEPS["creation"] = ("creation_subject",
"creation_design")`, appended after `perspective`; the CHECK
`ck_lore_usage_event_step` gains `OR (kind = 'creation' AND step IN
('creation_subject','creation_design'))` at its end. `PAYLOAD_KEYS` gains:
- `"creation_subject": frozenset({"draft_id", "asked_by", "backstory",
  "names", "keywords", "error"})`
- `"creation_design": frozenset({"draft_id", "asked_by", "lore",
  "proposal", "violations", "notes", "error"})`

**Migration** `scripts/migrate_v2_32_character_creation.py`: R-01's
skeleton, `_PREVIOUS_VERSION = "v2.31"`, `_THIS_VERSION = "v2.32"`.
`_plan()` returns (a) `CreationRules` and the five draft models to create
when their table is absent (created by `_create_from_model`, parents before
children: `creation_rules`, `pc_draft`, `pc_draft_skill`, `pc_draft_sketch`,
`pc_draft_membership`, `pc_draft_knowledge`); (b) `ALTER TABLE skill_system
ADD COLUMN visible_at_creation BOOLEAN`, `... max_rank_at_creation INTEGER`,
`... cap_raised_at_creation INTEGER`, `... cap_held_at_creation INTEGER`,
`ALTER TABLE skill_definition ADD COLUMN visible_at_creation BOOLEAN`,
`... max_rank_at_creation INTEGER`, each only when the column is absent;
(c) a rebuild of `lore_usage_event` (`models.LoreUsageEvent`, the v2.31
script's `_JOURNAL_COLUMNS`) when its stored SQL lacks `'creation'`. Writes
no data. Post-checks: the six tables exist; the six columns exist;
`'creation_design'` is in the stored journal SQL; the journal row count is
unchanged. Then `schema_meta` -> v2.32. Output lines as v2.31's.

**Cascade.** `_DIRECT_WORLD_SCOPED_DELETES` gains, after `"quest_request",`:
`"creation_rules", "pc_draft", "pc_draft_skill", "pc_draft_sketch",
"pc_draft_membership", "pc_draft_knowledge",`.
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
### C-04 -- the one creation check
Produced by: C (`check_creation`, `verdict_dict`), G (`check_draft`)   Consumed by: F, G, I
Module: `src/world_engine/creation_check.py`. Reads only.
```python
VIOLATION_CODES: tuple[str, ...] = (
    "unknown_skill", "rank_out_of_range", "not_visible", "above_max_rank",
    "over_master_count", "over_rank_cap", "over_system_raised", "over_system_held", "over_pool",
)
DRAFT_VIOLATION_CODES: tuple[str, ...] = (
    "name_missing", "backstory_missing", "start_place_missing", "start_place_invalid",
    "too_many_sketches", "master_without_sketch", "sketch_existing_invalid",
    "membership_invalid", "pc_exists",
)

@dataclass(frozen=True)
class Violation:
    code: str
    skill_key: Optional[str]
    message: str

@dataclass(frozen=True)
class SheetLine:
    skill_key: str
    start_rank: int
    rank: int
    cost: int          # positive spent, negative given back, 0 unchanged

@dataclass(frozen=True)
class CreationVerdict:
    pool: int
    spent: int         # sum of every line's cost (refunds subtract)
    remaining: int     # pool - spent
    lines: tuple[SheetLine, ...]   # every start_sheet line, in its order
    violations: tuple[Violation, ...]

def check_creation(db, world_id: str, choices: Mapping[str, int], *,
                   enforce_visibility: bool) -> CreationVerdict
def check_draft(db, draft: PcDraft) -> tuple[Violation, ...]
def verdict_dict(verdict: CreationVerdict, violations: tuple[Violation, ...]) -> dict
```
**`check_creation`.** `rules = world_creation_rules`, `sheet =
start_sheet(db, world_id, rules)`, ladder labels from
`skill_ranks.world_ladder`. `choices` maps a skill key to a wanted rank;
an absent key keeps its start rank.
1. For each key of `choices` not in the sheet: `unknown_skill`. For each
   choice whose value is not an int in 0..5 (a bool is not an int):
   `rank_out_of_range`; that key keeps its start rank for every later step.
2. Each line's `rank` = its valid choice, else `start_rank`. Cost: `rank >
   start_rank` -> `sum(costs[r] for r in start_rank+1..rank)`; `rank <
   start_rank` -> `-costs[1]` (only 1 -> 0 exists); else 0.
3. Per line whose `rank != start_rank`, in sheet order: when
   `enforce_visibility` and not `visible` -> `not_visible` (and nothing else
   for that line); else when `rank > max_rank` -> `above_max_rank`.
4. `over_master_count` when the number of `requires_master` lines at rank >=
   1 exceeds `rules.max_master_skills`.
5. For each rank `r` of `CREATION_CAP_RANKS` in order with a cap not None:
   the lines at rank `r` -- for `r == 0`, only lines that are not
   `requires_master` -- exceed the cap -> `over_rank_cap`.
6. For each system of the sheet, by system name: when its
   `cap_raised_at_creation` is not None and the count of its lines at rank
   > `DEFAULT_RANK` exceeds it -> `over_system_raised`; when its
   `cap_held_at_creation` is not None and the count of its lines at rank >=
   1 exceeds it -> `over_system_held`.
7. `spent > rules.pool` -> `over_pool`.
Order of `violations`: steps 1, 3, 4, 5, 6, 7 as listed. Messages
(verbatim; `{label}` is the world's ladder label of the rank, `{name}` the
line's name, `{default_label}` the label of `DEFAULT_RANK`):
- `unknown_skill`: `Compétence inconnue : {key}.`
- `rank_out_of_range`: `« {name} » : le rang doit être entre 0 et 5.`
  (`{name}` the key when unknown)
- `not_visible`: `« {name} » ne peut pas être choisie à la création.`
- `above_max_rank`: `« {name} » : au plus {label} à la création.`
- `over_master_count`: `Au plus {n} compétence(s) qui exigent un maître.`
- `over_rank_cap`: `Au plus {n} compétence(s) au rang {label}.`
- `over_system_raised`: `Système « {system} » : au plus {n} compétence(s) au-dessus de {default_label}.`
- `over_system_held`: `Système « {system} » : au plus {n} compétence(s) détenue(s).`
- `over_pool`: `Réserve dépassée : {spent} point(s) pour {pool}.`
`skill_key` is set for the per-line codes (steps 1-3), None for the rest.

**`check_draft`.** `view = public_view(db, draft.world_id)`; in this order:
1. `name_missing` when `draft.name.strip()` is empty: `Le personnage n'a pas de nom.`
2. `backstory_missing` when `draft.backstory.strip()` is empty: `L'histoire du personnage est vide.`
3. `start_place_missing` when `start_location_id` is None: `Choisis un lieu de départ.`;
   else `start_place_invalid` when it is not in `view.entity_ids`, not an
   active `location` of the world, or in `zone_ids(db, world_id)`:
   `Ce lieu de départ ne peut pas être choisi.`
4. every violation of `check_creation(db, world_id, {row.skill_key:
   row.player_rank for each draft skill row with player_rank not None},
   enforce_visibility=True)`.
5. `too_many_sketches` when the draft has more than `PC_SKETCH_MAX`
   sketches: `Au plus 8 personnes d'ancrage.`
6. `master_without_sketch`, per `requires_master` line at rank >= 1 of that
   verdict with no sketch of kind `master` and that `skill_key`: `« {name} »
   exige un maître : ajoute la personne qui te l'a enseignée.`
   (`skill_key` set).
7. `sketch_existing_invalid`, per sketch whose `existing_entity_id` is not
   None and not a `character` in `view.entity_ids`: `« {sketch} » : la
   personne choisie n'est pas connue de tous.`
8. `membership_invalid`, per membership whose faction is not a `faction` in
   `view.entity_ids`: `Cette faction ne peut pas être choisie.`
9. `pc_exists` when the draft's user already holds a character of
   `character_type` `player` in the world (R-09): `Ce joueur a déjà un
   personnage dans ce monde.`
**`verdict_dict`** returns `{"pool", "spent", "remaining", "lines": [{"skill_key",
"start_rank", "rank", "cost"}], "violations": [{"code", "skill_key",
"message"}]}` with `violations` the tuple passed in.
### C-08 -- the premise of a chosen world
Produced by: F   Consumed by: F (C-11)
`world_premise(db, regime, *, entity_type=None, world_id: Optional[str] =
None)`: when `world_id` is not None the world is `db.get(World, world_id)`
(`""` when None), else the `is_active` world as today. `fill(text, db,
usage, *, entity_type=None, world_id=None)` passes it through.
`prompt_call.call_json(db, usage, values, exchanges, chat, *, world_id:
Optional[str] = None)` passes it to both `fill(` calls. Every existing
caller passes nothing and is unchanged.
### C-09 -- the designer's prompts
Produced by: F   Consumed by: F (C-11)
Usages `creation_subject`, `creation_design` in `PROMPT_REGISTRY`:
`surface="authoring"`, `world_scoped=False`, `dry_run_capable=True`,
`default_model=_author_model`, `premise="player"`, call sites
`src/world_engine/creation_designer.py:_subject_call` and
`src/world_engine/creation_designer.py:_design_call`. Seeded in
`scripts/seed_pilot.py` as `CHARACTER_DESIGNER_PROMPT_HEADS`: ids
`pt-creation-subject` (variables `character_name, backstory`) and
`pt-creation-design` (variables `character_name, backstory, skills,
player_choices, rules, lore, people, places, factions, errors`), names
`Concepteur de personnage — le sujet de l'histoire` and `Concepteur de
personnage — la proposition`, `world_id=None`, `destination="local"`;
texts in BRIEF-0126-F verbatim. Delivered by
`scripts/apply_ticket_0126_designer_prompts.py` (the 0121 script's shape
over this tuple).
### C-10 -- the creation lore (public view only)
Produced by: F   Consumed by: F (C-11), G
Module: `src/world_engine/creation_lore.py`. Reads only.
```python
MAX_NAMES = 10
MAX_KEYWORDS = 6
MAX_LORE_LINES = 80
MAX_LISTED = 60

@dataclass(frozen=True)
class CreationLore:
    lines: tuple[str, ...]
    people: tuple[dict, ...]     # {"entity_id", "name"}
    places: tuple[dict, ...]     # {"entity_id", "name"}
    factions: tuple[dict, ...]   # {"entity_id", "name", "description"}

def public_places(db, world_id: str, view: PublicView) -> list[dict]
def gather_creation_lore(db, world_id: str, *, names: list[str], keywords: list[str]) -> CreationLore
```
- `public_places`: active `location` entities of the world in
  `view.entity_ids` and not in `zone_ids(db, world_id)`, `{"entity_id",
  "name"}`, sorted by (name, id).
- `gather_creation_lore`: `view = public_view(db, world_id)`; names
  stripped, empty dropped, de-duplicated under `normalize_surface`, first
  `MAX_NAMES`; for each, every category of `CATEGORIES` is tried with
  `resolve_named(name, category, world_id, db, scope=public_scope(view))`
  and every `matched` id is kept; for each kept entity, its
  `public_dossier` rows become lines; the kept `character` entities are
  `people`. Keywords likewise, first `MAX_KEYWORDS`, each through
  `public_facts_mentioning(keyword, world_id, view, db)`. Lines:
  `identity` -> `— {name} ({type})`; `facets` -> `  • {label} : {content}`;
  `memberships` -> `  • membre de {faction_name}` plus ` ({role})` when
  set; `members` -> `  • membre : {member_name}` plus ` ({role})`;
  `public_mentions` -> `• {content}`; de-duplicated in order, first
  `MAX_LORE_LINES`. `places` = first `MAX_LISTED` of `public_places`;
  `factions` = first `MAX_LISTED` of `public_factions`, keys `entity_id,
  name, description`.
`public_scope` comes from `perspective_query`; the module imports nothing
from `lore_selectors` and holds no `entity_dossier`, `who_knows_about`,
`facts_mentioning(` outside `public_facts_mentioning(`, `world_factions`,
`CREATOR`, `NameScope("creator"`, `World.is_active` or `_world_id(`.
### C-11 -- the character designer
Produced by: F   Consumed by: G
Module: `src/world_engine/creation_designer.py`; imports `chat` from
`.ollama_client` (R-24).
```python
SUBJECT_USAGE = "creation_subject"
DESIGN_USAGE = "creation_design"
MAX_KNOWLEDGE = 10
DESIGNER_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : le concepteur n'a rien proposé et rien n'a changé. "
    "Réessaie quand Ollama est démarré."
)

@dataclass(frozen=True)
class DesignedSkill:
    skill_key: str
    rank: int
    reason: Optional[str]

@dataclass(frozen=True)
class DesignedSketch:
    name: str
    role: str
    sentence: str
    group_label: str
    kind: str                          # one of PC_SKETCH_KINDS
    skill_key: Optional[str]           # set exactly when kind == "master"
    existing_entity_id: Optional[str]

@dataclass(frozen=True)
class DesignedMembership:
    faction_id: str
    role: Optional[str]

@dataclass(frozen=True)
class DesignedKnowledge:
    level: str                         # one of PC_KNOWLEDGE_LEVELS
    content: str

@dataclass(frozen=True)
class CreationDesign:
    names: tuple[str, ...]
    keywords: tuple[str, ...]
    lore: CreationLore
    skills: tuple[DesignedSkill, ...]
    sketches: tuple[DesignedSketch, ...]
    start_location_id: Optional[str]
    memberships: tuple[DesignedMembership, ...]
    knowledge: tuple[DesignedKnowledge, ...]
    notes: tuple[str, ...]
    violations: tuple[Violation, ...]  # check_creation of `skills`, after the retry

def _subject_call(db, draft, exchanges: list) -> dict
def _design_call(db, draft, values: dict[str, str], exchanges: list) -> dict
def subject(db, draft: PcDraft, exchanges: list) -> tuple[tuple[str, ...], tuple[str, ...]]
def design(db, draft: PcDraft, names: tuple[str, ...], keywords: tuple[str, ...],
           exchanges: list) -> CreationDesign
def design_record(design: CreationDesign) -> dict
```
`subject`: `_subject_call` (`call_json(db, SUBJECT_USAGE, {"character_name",
"backstory"}, exchanges, chat, world_id=draft.world_id)`) -> `(names,
keywords)`: each a list of non-empty strings in the reply, anything else ->
`()`. `design`: (1) `gather_creation_lore`; (2) `_design_call` with the
values of BRIEF-0126-F and `errors=""`; (3) resolve (case table (b)-3);
(4) `check_creation(db, world_id, {s.skill_key: s.rank},
enforce_visibility=True)`; when it has violations, one more `_design_call`
with `errors` = `\nErreurs de ta réponse précédente :` then one `\n-
{message}` per violation, re-resolve, re-check; the second result is kept
whatever it holds. `OllamaError`, `LlmParseError` propagate from both
functions. Neither writes anything.
`design_record(design)` -> `{"skills": [{"skill_key", "rank", "reason"}],
"sketches": [{"name", "role", "sentence", "group_label", "kind",
"skill_key", "existing_entity_id"}], "start_location_id", "memberships":
[{"faction_id", "role"}], "knowledge": [{"level", "content"}]}` (the
journal's `proposal`).

## Context

Nia's player writes a backstory; the designer (S1) must draw what it
implies while knowing only what everybody knows (F-c). This step builds it:
the premise of the chosen world rather than the active one (I1), the
public lore of a backstory (C-10), the two model calls with one retry
against the one check (C-11), and the two prompts. Nothing is written to
any table here; the route that runs it, journals it and applies it to a
draft is G.

## Scope IN

1. `world_premise.py` and `prompt_call.py` per C-08. The module docstring of
   `world_premise.py` gains: « `world_id` (TICKET-0126, I1): a player
   surface names the world it serves; without it, the active world, as
   every creator generator. »
2. `src/world_engine/creation_lore.py` per C-10 (docstring: « What a
   character designer may read: what everybody knows of a backstory's
   names and words, the places a character can start in, the public
   factions (TICKET-0126, BRIEF-0126-F; F-c, D1, INV-66). Built only on the
   public view. Reads only. »).
3. `src/world_engine/creation_designer.py` per C-11 (docstring: « The
   player-side character designer (TICKET-0126, BRIEF-0126-F; S1, T1,
   F'a-1, F-c). Two calls -- the backstory's names and words, then the
   proposal -- over the public lore only; its skills pass
   `creation_check.check_creation`, with one retry. Writes nothing:
   `writes/pc_drafts.apply_design` (BRIEF-0126-G) applies a design.
   `OllamaError` and `LlmParseError` propagate. »). Module-level
   `_subject_call` and `_design_call` (the registry's call sites). The
   design values, verbatim formats:
   - `skills`: one line per line of `start_sheet` that is a base domain or
     whose id is in `public_view(...).skill_ids`, in sheet order, coded
     `s1`, `s2`, ... in that order: `{code} -- {name} ; {system or "sans
     système"} ; {label of start_rank} ; {label of max_rank} ; {"exige un
     maître" if requires_master else "ouverte"}`.
   - `player_choices`: per draft skill row with `player_rank` not None, in
     sheet order: `{code} -- {name} : {label of player_rank}` plus ` --
     {justification}` when set; none -> `(aucune)`.
   - `rules`: `Réserve : {pool} point(s).`; `Coût pour atteindre : {label 1}
     {c1}, {label 2} {c2}, {label 3} {c3}, {label 4} {c4}, {label 5}
     {c5}.`; `Descendre une compétence détenue à {label 0} rend {c1}
     point(s).`; `Au plus {n} compétence(s) qui exigent un maître.`; per
     cap set, `Au plus {cap} compétence(s) au rang {label}.`; per system
     holding a listed skill and a cap set, `Système « {name} » : au plus
     {n} compétence(s) au-dessus de {label 1}.` and/or `Système « {name} » :
     au plus {n} compétence(s) détenue(s).` -- one line each, `\n`-joined.
   - `lore`: the lore lines `\n`-joined, or `(rien)`.
   - `people`, `places`, `factions`: `- {name}` lines (a faction adds ` :
     {description}` when set), or `(aucun)`.
   - `errors`: `""` on the first call; on the retry `\nErreurs de ta réponse
     précédente :` then one `\n- {message}` per violation.
   Resolution per the lot's case table (b)-3, notes verbatim; skill codes
   map back to their keys; `existing` resolves with `resolve_named(name,
   "person", world_id, db, scope=public_scope(view))`, kept only when
   `matched` and a `character` of `view.entity_ids`; the sketch room is
   `PC_SKETCH_MAX` minus the draft's sketches of origin `player`.
4. `prompt_registry.py`: `creation_subject` and `creation_design` per C-09,
   after the quest designer's entries, under `# TICKET-0126 (BRIEF-0126-F):
   the player-side character designer -- the backstory's subject, then the
   proposal. Player regime: it reads what everybody knows.`
5. `scripts/seed_pilot.py`: after `QUEST_TRIAL_PROMPT_HEADS`, the section
   comment `# ----- prompt templates: the character designer (TICKET-0126,
   BRIEF-0126-F) -----` and these constants, verbatim (backslash line
   continuations as in the quest designer's constants):
   ```python
   CREATION_SUBJECT_SYSTEM_PROMPT = """\
   Tu aides un joueur à créer son personnage dans un jeu de rôle. On te donne \
   le nom de son personnage et l'histoire qu'il a écrite. Ton travail : dire ce \
   qu'il faut chercher dans ce que tout le monde sait du monde.

   RÈGLES :
   - "names" : les noms propres de personnes, de lieux, de factions ou \
   d'objets que l'histoire cite, tels qu'écrits ; [] s'il n'y en a pas.
   - "keywords" : de 1 à 6 mots qui distinguent cette histoire (un métier, un \
   art, un lieu, un événement), sans article.

   Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne :
   {"names":["..."],"keywords":["..."]}\
   """

   CREATION_SUBJECT_USER_TEMPLATE = """\
   Personnage : {character_name}
   Histoire : {backstory}
   """

   CREATION_DESIGN_SYSTEM_PROMPT = """\
   Tu aides un joueur à créer son personnage dans un jeu de rôle. On te donne \
   l'histoire qu'il a écrite, les compétences du monde et ce qu'il demande, les \
   règles de création, et ce que tout le monde sait du monde. Tu ne sais rien \
   d'autre de ce monde : n'invente ni secret ni fait caché, et ne nomme une \
   personne, un lieu ou une faction existants que s'ils sont dans les listes.

   TON TRAVAIL. Propose ce que cette histoire implique :
   - "skills" : ta contre-proposition de compétences. Chaque élément \
   {"skill": un code "s1", "rank": un entier de 0 à 5, "reason": une phrase \
   qui s'appuie sur l'histoire}. Ne mets que les compétences dont le rang \
   diffère du départ. Respecte les règles : la réserve de points, le coût de \
   chaque rang, le rang maximal de chaque compétence, les plafonds. Une \
   compétence qui exige un maître ne s'obtient qu'avec ce maître dans \
   "sketches".
   - "sketches" : les personnes que l'histoire implique, 8 au plus. Chaque \
   élément {"name": son nom, "role": ce qu'elle est pour le personnage, \
   "sentence": la phrase de l'histoire qui la fonde, recopiée, "group": le \
   groupe auquel elle appartient pour le personnage (« sa famille », « son \
   ancienne compagnie »), "kind": "family", "master", "faction" ou "other", \
   "skill": pour un maître, le code de la compétence qu'il a enseignée, sinon \
   null, "existing": le nom d'une personne de la liste des personnes connues \
   de tous si c'est elle, sinon null}.
   - "start_place" : le nom d'un lieu de la liste des lieux où commencer, ou \
   null.
   - "memberships" : les factions de la liste dont l'histoire fait le \
   personnage membre, chacune {"faction": son nom, "role": son rôle en \
   quelques mots, ou null}.
   - "knowledge" : ce que le personnage sait grâce à son histoire, 10 au plus, \
   chacune {"level": "rumor", "suspicious", "partial" ou "knows", "content": \
   une phrase}.
   - "notes" : ce que tu veux dire au joueur, en phrases courtes ; [] sinon.

   Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne :
   {"skills":[],"sketches":[],"start_place":null,"memberships":[],"knowledge":[],"notes":[]}\
   """

   CREATION_DESIGN_USER_TEMPLATE = """\
   Personnage : {character_name}
   Histoire : {backstory}

   COMPÉTENCES (code -- nom ; système ; rang de départ ; rang maximal ; maître) :
   {skills}

   DEMANDE DU JOUEUR :
   {player_choices}

   RÈGLES DE CRÉATION :
   {rules}

   CE QUE TOUT LE MONDE SAIT :
   {lore}

   PERSONNES CONNUES DE TOUS :
   {people}

   LIEUX OÙ COMMENCER :
   {places}

   FACTIONS CONNUES DE TOUS :
   {factions}
   {errors}"""
   ```
   then `CHARACTER_DESIGNER_PROMPT_HEADS` per C-09 (the
   `QUEST_DESIGNER_PROMPT_HEADS` dict shape, R-23), and its loop line
   `for entry in CHARACTER_DESIGNER_PROMPT_HEADS:  # TICKET-0126
   (BRIEF-0126-F)` beside the quest designer's at ~:3624, calling
   `upsert_prompt_template(session, **entry)` exactly as that loop does.
6. `scripts/apply_ticket_0126_designer_prompts.py`: the 0121 script with
   its tuple, docstring and refusal message re-pointed to
   `CHARACTER_DESIGNER_PROMPT_HEADS` and this ticket.
7. `tooling/verify/checks/world_premise.py`: `PLAYER` gains
   `"creation_subject", "creation_design"` at its end; its docstring reads
   `PLAYER` (17); the PASS line reads `49 usages hold the 14/17/18 regime
   partition`.
8. `.claude/rules/player-surface.md`: in INV-66, `Every perspective question
   is journaled with what was withheld.` becomes `Every perspective question
   is journaled with what was withheld, and every character-designer call
   with what it read.`; `creation_designer.py` is appended to its `--
   enforced by` list; `paths:` gains `"src/world_engine/creation_lore.py"`
   and `"src/world_engine/creation_designer.py"`.
9. New check `tooling/verify/checks/creation_designer.py` (first sentence:
   « G1 check for TICKET-0126 (BRIEF-0126-F) -- the character designer reads
   only the public view of the chosen world, retries once against the one
   check, and keeps every rule of its resolution table. »), fresh DB
   (R-35), `creation_designer.chat` swapped with `_Stub` (R-35), its two
   heads seeded from `seed_pilot.CHARACTER_DESIGNER_PROMPT_HEADS`:
   - **CD1** two worlds, W1 active and W2 not, each with a description:
     `world_premise(db, "player", world_id=W2)` names W2 and not W1;
     without `world_id` it names W1; `call_json` with `world_id=W2` sends a
     system message holding `Monde : <W2 name>`.
   - **CD2** on `perspective_isolation._build_world` (imported) plus a
     public visitable location, a public zone with one child location, and
     a non-public location: `gather_creation_lore(names=["Hero", "Shade",
     "Nobody"], keywords=["tunnel"])` keeps Hero in `people` and not Shade;
     the lines hold Hero's identity line and no identity line for Shade or
     Nobody (their dossiers are not read); the only `tunnel` line is F6's
     public text (`• Shade creuse un tunnel`), never F7's; `places` hold the visitable
     location and the zone's child, never the zone or the non-public one;
     `factions` are exactly Guild and Guild2.
   - **CD3** static: `creation_lore.py` and `creation_designer.py` hold none
     of `CREATOR`, `NameScope("creator"`, `include_creator_only`,
     `entity_dossier`, `who_knows_about`, `world_factions`,
     `World.is_active`, `_world_id(`; neither imports from `lore_selectors`;
     neither holds `db.add(`, `.commit(`, `.flush(`.
   - **CD4** `design` on a draft added directly (status `draft`, two player
     sketches), `subject` then `design`, stubbed replies: (a) a subject, a
     design over the pool, a valid retry -> two design calls, `violations == ()`, the retry's user
     message holds `Erreurs de ta réponse précédente :`; (b) a subject, two
     invalid designs -> `violations` non-empty, exactly two design calls;
     (c) one design exercising every row of (b)-3: each outcome and each
     note verbatim; (d) an `OllamaError` reply propagates; an unparsable
     reply raises `LlmParseError`.
   - **CD5** `PROMPT_REGISTRY` holds both usages with `premise == "player"`
     and C-09's call sites; `CHARACTER_DESIGNER_PROMPT_HEADS` holds exactly
     C-09's ids, usages and variables; the delivery script exists and names
     the tuple.
10. Commits: (1) items 1, 7 (premise and its check); (2) items 2-6, 8;
    (3) item 9.

## Scope OUT

- Any write: applying a design, the journal rows, the route (G).
- Reading a secret, a creator-only note, or a non-public entity: never.
- The creator-side development of sketches into NPCs (0129, F'a-1).
- A metric of the designer in « Suivi » (carried forward).
- Changing the `player` regime's content (I1: rejected I2).
- Any existing prompt's text.

## Invariants to defend

- INV-66 (extended here): every read of `creation_lore.py` goes through the
  public view; CD2 and CD3 prove it.
- INV-65: the premise reaches the model only through `{world_premise}` in
  the `player` regime; `premised_texts` adds the placeholder at seed time.
- INV-47 / INV-48: prompt text lives in `prompt_version`, written only by
  the seed and the delivery script on a virgin head.
- INV-01: no secret reaches the designer; it has no door to one.

## Decision rights

STOP:
- An anchor does not hold.
- A resolution row of (b)-3 cannot be implemented as written.
- `world_premise.py` WP2 or WP3 turns red after Scope IN 1 (they must stay
  green unchanged).

ADAPT:
- `prompt_lean.py` rule 2 flags a word of the prompts as a pilot
  identifier: replace that word by a neutral one of the same meaning,
  report the change verbatim.
- `prompt_registry.py` (the check) counts usages elsewhere: add the two
  usages where it requires, report.
- CD2's fixture needs a location helper `_build_world` does not provide:
  add the three locations directly in CD2, as `_build_world` adds
  entities.

REPORT-ONLY:
- The default authoring model chosen by `_author_model` for a player
  surface.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creation_designer.py`
      PASS (CD1-CD5); `world_premise.py` PASS with « 49 usages ».
- [ ] Named mutations, each turning its rule red, then reverted: CD1 --
      `fill` ignores `world_id`; CD2 -- `gather_creation_lore` resolves names
      with `NAMES_ONLY`; CD3 -- import `facts_mentioning` from
      `lore_selectors` in `creation_lore.py`; CD4 -- remove the retry; CD5 --
      set `creation_design`'s premise to `creator`.
- [ ] `prompt_registry.py`, `prompt_version.py`, `prompt_lean.py`,
      `perspective_isolation.py`, `claude_md_contract.py`,
      `module_budget.py`, `corpus_gate.py` PASS.
- [ ] Nia runs `scripts/apply_ticket_0126_designer_prompts.py` on her
      database (report the line).
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `.claude/rules/player-surface.md` (Scope IN 8). No schema change.
