<!-- slug: creation-rules-and-check -->
# BRIEF 0126-C — "The creation rules and their one check"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: BRIEF-0126-B

## Anchors to confirm (Mini-RECON)

- `models/canon_skill.py` declares `CreationRules` and the constants
  `CREATION_COST_COLUMNS`, `CREATION_CAP_RANKS`, `CREATION_CAP_COLUMNS`;
  `SkillSystem` holds `visible_at_creation`, `max_rank_at_creation`,
  `cap_raised_at_creation`, `cap_held_at_creation`; `SkillDefinition` the
  first two (brief B).
- `src/world_engine/skill_ranks.py` defines `DEFAULT_RANK = 1`, `MAX_RANK =
  5`, `world_ladder(db, world_id)`.
- `src/world_engine/cockpit/crud/skills.py` is 667 lines (± brief B: 0);
  `RankPointsBody` at :329, `SkillSystemWriteBody` at :355,
  `SkillDefinitionWriteBody` at :508, `_skill_system_dict` at :303,
  `_skill_definition_dict` at :483.
- `tooling/verify/canon_write_policy.txt` lists `skill_rank` in
  `[CANON_TABLES]` and `upsert_skill_rank` at :50-51.
- `CLAUDE.md` « Path-scoped rules » lists `player-surface.md` then
  `schema-migrations.md`; the highest invariant id is INV-66.

Halt if any anchor has moved.

## Facts carried

### R-05 -- `skill_rank` and its one writer
Opened: `src/world_engine/models/config.py:230-259`;
`src/world_engine/writes/config.py:536-577`;
`tooling/verify/canon_write_policy.txt:50-51`.
Finding: `SkillRank` (`skill_rank`): at most one row per (world, rank), the
rank's label, `points_to_next`, `trial_to_next`; a missing row reads the
engine default. `upsert_skill_rank(db, *, world_id, rank, label,
points_to_next, trial_to_next=False)` is « the one writer of skill_rank »
(policy line 50 says so); `PUT /api/skill-ranks` rewrites all six rows.
Consequence: nothing in this lot writes or adds a column to `skill_rank`
(J1'); creation reads its labels through `skill_ranks.world_ladder` only.
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
### R-07 -- the skills CRUD
Opened: `src/world_engine/cockpit/crud/skills.py` (whole, 667 lines, 23
top-level functions and methods, R-40).
Finding: routes on the shared `/api` router (`crud/_router.py`): `GET/PUT
/skill-ranks` (:124-159), `GET /skills/player-characters`, `GET
/skills/learnable`, `POST /skills` (`grant_skill`, :220-251: `rank` default
0, a `taught_by_id` must be another character at Maître in the skill, 422
otherwise), `GET /skills`, `PATCH /skills/{id}`, `GET/POST /skill-systems`,
`PUT/DELETE /skill-systems/{id}` (:318-445), `GET /skill-gaps`, `GET/POST
/skill-definitions`, `PUT/DELETE /skill-definitions/{id}` (:497-667).
`RankPointsBody` (:329-344) holds the ten optional threshold/trial fields;
`_rank_points(row)` (:346-347) and `_set_rank_points(row, body)` (:350-352)
copy them; `SkillSystemWriteBody(RankPointsBody)` adds `name, description`
(:355-357); `SkillDefinitionWriteBody(RankPointsBody)` adds `name,
base_domain, system_id, description, requires_master` (:508-515).
`_skill_system_dict` (:303-315) and `_skill_definition_dict` (:483-494)
return the row fields plus `**_rank_points(row)`. `create_skill_system`
(:360-383) and `update_skill_system` (:386-409) and
`update_skill_definition` (:581-641) set every body field, a PUT replacing
all of them. Every route reads the active world through `_world_id(db)`
(`crud/_shared.py:57-61`: the `is_active` world, 400 when none).
Consequence: C adds `GET/PUT /api/creation-rules` here and the override
fields to the two write bodies, their dicts and their setters (C-06). The
creator CRUD is keyed by the active world -- Création's posture, untouched.
### R-08 -- the canon write policy
Opened: `tooling/verify/canon_write_policy.txt:1-14, 44-60, 140-180`;
`tooling/verify/checks/single_canon_write.py:1-12`.
Finding: `[CANON_TABLES]` lists `skill skill_definition skill_system` and
`skill_rank` among others; `[ALLOWED_SITES]` lists `path::function tables`,
a comment line above each addition naming its ticket and brief; the six
skill-system and skill-definition routes of `crud/skills.py` are listed
(:175-180). `single_canon_write.py` fails when a canon table is written
from a site not listed; sites on non-canon tables are ignored; an
unattributable write site always fails.
Consequence: `creation_rules` is canon curated config (a world's rules, the
`skill_rank` family): C adds it to `[CANON_TABLES]` and adds
`src/world_engine/writes/creation_rules.py::write_creation_rules
creation_rules` with its comment line. The five `pc_draft*` tables are not
canon (pending, non-canon, the `quest_request` posture) and are never added.
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
### R-40 -- module budgets of the files this lot edits
Opened: `ast` count and `wc -l` at `fb8557a`;
`tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 physical lines and 40 top-level functions plus methods
for `src/**/*.py`, 1000 lines for `frontend/src/**/*.svelte|js`.
`models/canon.py` 964; `crud/skills.py` 667 lines / 23; `models/pipeline.py`
813; `perspective_selectors.py` 281; `perspective_audit.py` 128;
`lore_render.py` 340; `world_premise.py` 131; `prompt_call.py` 47;
`prompt_registry.py` 488; `writes/worlds.py` 168; `cockpit/app.py` 343 /
12; `routes/player.py` 129; `tabs.js` 890; `EntityList.svelte` 413;
`registry.js` 604; `Creation.svelte` 250; `CompetencesSheet.svelte` 253;
`competences.svelte.js` 361; `joueur.svelte.js` 168; `WorldPage.svelte` 83.
Consequence: `canon.py` cannot take B's columns before A; every other edit
stays far under its cap; `tabs.js` takes at most 15 lines; new logic goes
to new modules.

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
### C-05 -- the creation rules writer
Produced by: C   Consumed by: C (C-06)
`src/world_engine/writes/creation_rules.py::write_creation_rules(db, *,
world_id: str, pool: int, costs: Sequence[int], caps: Mapping[int,
Optional[int]], max_rank: int, max_master_skills: int, skills_visible:
bool) -> CreationRules`. `costs` lists ranks 1..5 in order (exactly 5);
`caps` has exactly the keys of `CREATION_CAP_RANKS`. Fetch-or-create the
world's row, set every field, `updated_at` now, add, flush; never deletes,
never commits. `ValueError`, before any write, with these messages:
- pool not an int >= 0: `La réserve est un nombre entier, au moins 0.`
- costs not 5 ints >= 0: `Chaque coût est un nombre entier, au moins 0.`
- caps keys not exactly `CREATION_CAP_RANKS`, or a value neither None nor
  an int >= 0: `Chaque plafond est vide ou un nombre entier, au moins 0.`
- max_rank not an int in 1..5: `Le rang maximal va d'Initié à Maître.`
- max_master_skills not an int >= 0: `Le nombre de compétences à maître est un nombre entier, au moins 0.`
- skills_visible not a bool: `La visibilité est oui ou non.`
(a bool is never accepted as an int).
### C-06 -- the creator's rules routes and the override fields
Produced by: C   Consumed by: E
In `cockpit/crud/skills.py`, on the shared `/api` router:
- `GET /api/creation-rules` -> `rules_dict(world_creation_rules(db,
  world_id))` for the active world (`_world_id`).
- `PUT /api/creation-rules`, body `CreationRulesBody{pool: int, costs:
  list[CreationCostBody{rank: int, cost: int}], caps:
  list[CreationCapBody{rank: int, cap: Optional[int]}], max_rank: int,
  max_master_skills: int, skills_visible: bool}`: costs must list ranks
  1..5 exactly once and caps ranks 0, 2, 3, 4, 5 exactly once (422 `Chaque
  rang est donné une fois.` otherwise), then `write_creation_rules`, commit,
  return the GET shape; `ValueError` -> rollback, 422 with its message.
- `rules_dict(rules) -> dict` lives in `creation_rules.py` (C-03's module):
  `{"pool": int, "costs": [{"rank": 1..5, "cost": int}], "caps": [{"rank":
  r, "cap": int | None} for r in CREATION_CAP_RANKS], "max_rank": int,
  "max_master_skills": int, "skills_visible": bool}`.
- `SkillSystemWriteBody` gains `visible_at_creation: Optional[bool] = None`,
  `max_rank_at_creation: Optional[int] = Field(default=None, ge=1, le=5)`,
  `cap_raised_at_creation: Optional[int] = Field(default=None, ge=0)`,
  `cap_held_at_creation: Optional[int] = Field(default=None, ge=0)`;
  `SkillDefinitionWriteBody` gains the first two. `create_skill_system`,
  `update_skill_system`, `create_skill_definition`,
  `update_skill_definition` set them (a PUT replaces them like every other
  field); `_skill_system_dict` and `_skill_definition_dict` return them.

## Context

The world's creation rules exist as columns (B). This step gives them
their reader (C-03), the one function that judges a skill sheet (C-04's
`check_creation`), their writer (C-05) and the creator's routes and
override fields (C-06). The player, the designer and the creator's final
review (0129) will all call `check_creation`; nothing else computes a
cost. `check_draft` comes with the draft writer in G.

## Scope IN

1. `src/world_engine/creation_rules.py` per C-03, plus `rules_dict(rules)`
   per C-06. Docstring: « The character creation rules of a world and the
   start sheet a new character holds (TICKET-0126, BRIEF-0126-C; decisions
   J1', L2, Q, Q-limits, A1, P1). Reads only: no write, no flush, no commit,
   no model call. The cascade is `skill_ranks`' (R-06): the definition, then
   its system, then the world's `creation_rules` row, then the engine
   default. » It imports `BASE_SKILL_DOMAINS`, `CREATION_CAP_RANKS`,
   `CreationRules`, `SkillDefinition`, `SkillSystem` from `.models` and
   `DEFAULT_RANK` from `.skill_ranks`.
2. `src/world_engine/creation_check.py` with `VIOLATION_CODES`,
   `DRAFT_VIOLATION_CODES`, `Violation`, `SheetLine`, `CreationVerdict`,
   `check_creation` and `verdict_dict` per C-04, messages verbatim.
   Docstring: « The one check of a character-creation skill sheet
   (TICKET-0126, BRIEF-0126-C; INV-67): the player's, the designer's and the
   one submitted are judged here and nowhere else. Reads only. » Leave a
   marked place for `check_draft` (brief G): a comment `# check_draft:
   BRIEF-0126-G (C-04).` at the end of the module.
3. `src/world_engine/writes/creation_rules.py::write_creation_rules` per
   C-05, docstring naming C-05 and « never deletes, never commits ».
4. `cockpit/crud/skills.py` per C-06: import `world_creation_rules`,
   `rules_dict` from `...creation_rules` and `write_creation_rules` from
   `...writes.creation_rules`; add `CreationCostBody`, `CreationCapBody`,
   `CreationRulesBody` and the two routes after `update_skill_ranks`; add
   the override fields to the two write bodies, their dicts and the four
   create/update setters.
5. `tooling/verify/canon_write_policy.txt`: `creation_rules` appended to the
   last `[CANON_TABLES]` line; in `[ALLOWED_SITES]`, after the
   `upsert_skill_rank` line, the comment `# TICKET-0126, BRIEF-0126-C:
   write_creation_rules is the one writer of creation_rules -- a world's
   character creation rules, curated-config family, never a DELETE.` and
   the line `src/world_engine/writes/creation_rules.py::write_creation_rules
   creation_rules` (aligned as its neighbours).
6. `.claude/rules/character-creation.md`, verbatim:
   ```
   ---
   paths:
     - "src/world_engine/creation_rules.py"
     - "src/world_engine/creation_check.py"
     - "src/world_engine/writes/creation_rules.py"
   ---

   # Character creation

   A world's creation rules live in one `creation_rules` row (a missing row
   is every default); a system and a skill override visibility and the
   maximum rank, a system caps its raised and held skills. Costs are per
   step; lowering a held skill to Inexpérimenté gives back the Initié cost.

   ## Invariants

   - **INV-67** A character-creation skill sheet -- the player's, the
     designer's, the one submitted -- is judged only by
     `creation_check.check_creation`, over the rules read by
     `creation_rules`; no other module reads a rank's creation cost.
     -- enforced by `creation_budget.py`
   ```
7. `CLAUDE.md` « Path-scoped rules »: after the `player-surface.md` line,
   `- \`character-creation.md\` — creation rules, the creation check,
   drafts.`
8. New check `tooling/verify/checks/creation_budget.py` (first sentence: «
   G1 check for TICKET-0126 (BRIEF-0126-C) -- one function judges a
   character-creation sheet, over rules the creator reads and writes. »),
   fresh temp-file DB (R-35), rows through the sanctioned writers and the
   CRUD route functions called directly:
   - **CB1** the 17 rows of the lot's case table (b)-1 (fixture: one
     active world; systems through `create_skill_system`, definitions
     through `create_skill_definition`; the rules of rows 16-17 through
     `write_creation_rules`): `spent`, `remaining` and the violation codes in
     order equal the table; rows 4, 5, 9, 12 also compare the full French
     message.
   - **CB2** the cascade table (b)-2 for `skill_visible` and
     `skill_max_rank`, on `SimpleNamespace` owners, and `start_sheet`'s
     order and start ranks on CB1's world (four base domains first, then
     `Nécromancie, Sorts` (Magie), `Escrime, Lutte` (Martial), then
     `Alchimie, Pistage` (no system); `Nécromancie` and `Alchimie` start at
     0, every other line at 1).
   - **CB3** `write_creation_rules`: each refusal of C-05 raises with its
     message and writes nothing; a valid call then a second call update one
     row; `world_creation_rules` reads them back; a world without a row
     reads every default.
   - **CB4** routes: `GET /api/creation-rules` on a fresh world equals the
     defaults' `rules_dict`; a PUT changes them and the GET returns them; a
     PUT listing rank 3 twice -> 422 `Chaque rang est donné une fois.`; a PUT
     with `pool: -1` -> 422 with C-05's message and nothing written; a system
     created with `cap_held_at_creation: 1, visible_at_creation: false` reads
     them back; a definition updated with `max_rank_at_creation: 2` then
     with it omitted reads 2 then null.
   - **CB5** static: under `src/`, the token `cost_to_rank_` occurs only in
     `models/canon_skill.py`, `creation_rules.py` and
     `writes/creation_rules.py` (migration scripts are outside `src/`);
     `creation_rules.py` and `creation_check.py` contain none of `db.add(`,
     `.commit(`, `.flush(`, `chat(`.
9. Commits: (1) reader, check, writer, policy (items 1-3, 5); (2) routes and
   overrides (item 4); (3) rule file, CLAUDE.md, check (items 6-8).

## Scope OUT

- `check_draft` (G), any draft table write (G), the designer (F).
- Any UI (E). The routes are tested here, rendered in E.
- `skill_rank` and `upsert_skill_rank` (J1').
- Reading the rules from a player route (G) or the public view (D).
- A « Suivi » metric for creation (carried forward).

## Invariants to defend

- INV-67 (new): `check_creation` is the only judge; CB5 keeps the cost
  columns confined.
- The canon write doctrine (`single_canon_write.py`): `creation_rules` is
  written only by its listed writer; the route commits, the writer never.
- INV-41 to INV-46: the override fields change nothing in grants, backfill
  or rolls; a PUT that omits them resets them to NULL (inherit), which the
  UI of brief E always sends.

## Decision rights

STOP:
- An anchor does not hold.
- A case of (b)-1 cannot reach its listed outcome with C-04 as written (the
  table, not the code, is then wrong: report the case, change nothing).
- `single_canon_write.py` attributes a write to a canon table from a site
  this brief does not list.

ADAPT:
- `create_skill_definition`'s response lacks a field CB1 needs to read the
  new id: read it from the returned dict's `id`, report.
- A message in C-04 or C-05 exceeds what a test can compare because of an
  f-string detail (spacing, apostrophe): keep C-04's text exactly as
  written, report.

REPORT-ONLY:
- Worlds of Nia's database: they have no `creation_rules` row and read the
  defaults.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creation_budget.py`
      PASS (CB1-CB5).
- [ ] Named mutations, each turning its rule red, then reverted: CB1 -- the
      refund becomes `-costs[2]`; CB2 -- `skill_visible` reads the system
      before the definition; CB3 -- `write_creation_rules` accepts a bool as
      `pool`; CB4 -- `update_skill_definition` stops setting
      `max_rank_at_creation`; CB5 -- `creation_check.py` reads
      `rules_row.cost_to_rank_2` directly.
- [ ] `single_canon_write.py`, `claude_md_contract.py`, `module_budget.py`,
      `npc_skills.py`, `rank_trials.py`, `skill_progression.py`,
      `corpus_gate.py` PASS.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `.claude/rules/character-creation.md` and CLAUDE.md (Scope IN 6, 7).
- `canon_write_policy.txt` (Scope IN 5).
- No schema change; ARCHITECTURE_DECISIONS in brief I.
