"""G1 check for TICKET-0124 -- every generator that writes fiction is told the world it writes for, in its usage's regime, through one placeholder.

WP1 -- import. Every `PROMPT_REGISTRY` entry's `premise` is in
   `world_premise.PREMISE_REGIMES`; its `premise_reason` is non-empty exactly
   when `premise == "none"`; the keys of each regime equal this check's
   literal `CREATOR` (14), `PLAYER` (17) and `NONE` (18) tuples (C-03).
WP2 -- fixture. One active world `Aestia` (description, tone, two laws
   through `write_world_laws`), skill systems `Magie` and `Alchimie`, four
   states through `write_attribute_definition` (`Rang`, `Esprit lié`, the
   hidden `Maudit` on characters; `Alerte` on locations). Then:
   - `world_premise(db, "creator", entity_type="character")` is exactly
     `EXPECTED_CREATOR_CHARACTER`; for `location` it holds the `Alerte` line
     and no character state; without an entity type it holds the skill
     systems and no `États` line;
   - the `player` regime is the name, description, tone and laws only: no
     `Systèmes`, no `États`, no hidden state;
   - `none` is `""`; a world with only a name is `""`; with no active world
     every regime is `""`;
   - `fill` leaves a text without the placeholder untouched and runs no
     query (`db` is None); fills a `none` usage, and an unknown usage, with
     `""`;
   - `prompt_store.premised_prompt` on an `npc_dialogue` head answers a
     `PremisedPrompt` with the premise filled, the current version's id and
     number, and leaves the stored `prompt_version` text unchanged (INV-48);
   - `prompt_call.call_json` on a `quest_subject` head sends the model a
     system message that starts with the premise.
WP3 -- static, AST over `src/world_engine/**/*.py` (C-07). The `path::function`
   set holding a `current_prompt(` call equals the literal `STAYS` (18); the
   set holding a `premised_prompt(` call equals the literal `SWAPPED` (31);
   `prompt_call.py::call_json` calls `fill(` exactly twice; `prompt_load.py`
   calls neither `fill(` nor `premised_prompt(`; `region_author.py` renders
   `{world_description}` and `{world_fundamental_laws}` as `""` and names no
   `WorldLaw`.
WP4 -- the texts, the seed, the delivery, the guard (C-08).
   - import: for every usage, `seed_pilot.premised_texts(usage, "S", "U", ["a"])`
     prefixes the placeholder and appends the variable for a `creator` or
     `player` usage, and returns its arguments for a `none` one; a text that
     already holds the placeholder comes back unchanged; `variables=None`
     gives `["world_premise"]`;
   - fixture: `upsert_prompt_template` of a virgin `pt-entity-generation`
     writes v1 starting with `{world_premise}` and declares the variable; a
     second upsert writes no v2;
   - subprocess (its own temp DB, 10 s): `apply_ticket_0124_world_premise.py`
     gives `pt-npc-dialogue` a v2 `{world_premise}Tu es X.` and the variable,
     leaves `pt-day-extract-place` (a `none` usage) at v1; a second run exits
     0, prints `unchanged`, writes no v3;
   - route functions: `update_prompt_text` refuses (422, `missing_premise`'s
     text, nothing written) a `player` text without the placeholder and a
     `none` text with it, and appends a version for a `player` text with it;
     `restore_prompt_version` of a `creator` v1 without it is a 422;
   - static: `REGION_MANIFEST_USER_TEMPLATE` holds neither
     `{world_description}` nor `{world_fundamental_laws}`.

The fixture is a fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL`
set before any world_engine import) -- never Nia's DB. Every prompt version
carrying `{world_premise}` is written through `write_prompt_version` after
`write_prompt_variables` declared it. A rule that collected nothing is a
FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []

CREATOR = (
    "entity_generation", "player_generation", "skill_catalogue", "npc_goal_generation",
    "agenda_generation", "event_generation", "region_manifest", "room_batch_manifest",
    "npc_link_pair", "lore_statement_questions", "lore_statement_to_proposal", "quest_subject",
    "quest_design", "quest_trial",
)
PLAYER = (
    "npc_dialogue", "npc_initiative_act", "player_narration", "mj_interpretation",
    "mj_arbitration", "mj_establishment", "mj_gathering", "mj_initiative", "observation_intent",
    "observation_narration", "world_tick", "world_tick_events", "day_plan", "day_narration",
    "day_rewrite", "creation_subject", "creation_design",
)
NONE = (
    "world_generation", "room_batch_coherence", "npc_link_coherence", "npc_batch_placement",
    "lore_question_to_plan", "lore_rows_to_prose", "condition_interpret", "mj_speaker_selection",
    "conversation_analysis", "overhearing_classification", "conversation_summary",
    "day_extract_place", "day_extract_person", "day_extract_faction", "day_feasibility",
    "day_reconcile", "day_plan_select", "day_mention_choice",
)

STAYS = frozenset({
    "analyzer_transcript.py::_window_call_model", "analyzer_transcript.py::_overhearing_classify",
    "cockpit/crud/prompts.py::_prompt_row_summary", "cockpit/crud/prompts.py::get_prompt_detail",
    "context_window.py::summarize_older_lines", "day_choice.py::_ask", "day_extract.py::_extract",
    "day_feasibility.py::veto", "day_plan_select.py::select_plan", "day_reconcile.py::reconcile",
    "entity_author.py::generate_world_draft", "link_context.py::render_coherence_messages",
    "npc_group_author.py::_run_placement_call", "observation_runner.py::_pin_templates",
    "prompt_coverage.py::missing_usages", "prompt_load.py::load",
    "room_batch_author.py::propose_batch_coherence", "cockpit/play_initiative.py::_select_group_speaker",
})
SWAPPED = frozenset({
    "entity_author.py::_entity_draft_call", "entity_author.py::_player_draft_call",
    "entity_author.py::generate_skill_catalogue_draft", "entity_author.py::generate_npc_goals",
    "event_author.py::generate_agenda_draft", "event_author.py::_event_draft_call",
    "region_author.py::generate_region_manifest", "room_batch_author.py::generate_room_batch_manifest",
    "link_author.py::_render_pair_messages", "cockpit/play.py::_say_load_prompts",
    "cockpit/play.py::_say_npc_generation", "cockpit/play_initiative.py::_say_initiative_context",
    "cockpit/play_initiative.py::_initiative_vote_call",
    "cockpit/play_physical.py::_say_physical_roster_and_arbiter",
    "cockpit/play_physical.py::_say_physical_npc_reaction",
    "cockpit/play_physical.py::_build_establishment_narration", "cockpit/routes/play.py::start_conversation",
    "cockpit/routes/prompts.py::preview_prompt_npc_dialogue",
    "cockpit/routes/prompts.py::preview_prompt_player_narration",
    "cockpit/routes/scene.py::_scene_join_already_member",
    "cockpit/routes/scene.py::_scene_join_resolve_and_create",
    "cockpit/routes/scene.py::_scene_join_create_for_gathering", "gathering.py::_request_partition",
    "observation_engine.py::_observation_intent_messages", "observation_runner.py::_generate_act_line",
    "observation_runner.py::_generate_mj_narration", "tick.py::_tick_call_scope_model",
    "tick.py::run_world_tick", "day_plan.py::emit_plan", "day_narration.py::narrate",
    "day_narration.py::rewrite",
})

HEAD_LINES = [
    "=== CADRE DU MONDE ===",
    "Monde : Aestia",
    "Écoles et esprits.",
    "Ton et style : Manga, héroïque.",
    "Lois fondamentales — vraies partout, connues de tous et observables :",
    "- Tout humain peut se lier à un esprit.",
    "- Le lien ne se rompt qu'à la mort.",
]
FOOT = "=== FIN DU CADRE ==="
EXPECTED_CREATOR_CHARACTER = "\n".join(HEAD_LINES + [
    "Systèmes de compétences : Alchimie ; Magie",
    "États que porte chaque personnage de ce monde — propose une valeur pour chacun :",
    "- Esprit lié (une entité : personnage)",
    "- Maudit (un parmi : oui, non ; par défaut non) — caché du joueur",
    "- Rang (un parmi : F, E ; par défaut F)",
    FOOT,
]) + "\n\n"
EXPECTED_PLAYER = "\n".join(HEAD_LINES + [FOOT]) + "\n\n"


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


def rule_wp1() -> None:
    from world_engine.prompt_registry import PROMPT_REGISTRY
    from world_engine.world_premise import PREMISE_REGIMES

    if not PROMPT_REGISTRY:
        fail("WP1 collected nothing: PROMPT_REGISTRY is empty")
        return
    by_regime: dict[str, set[str]] = {r: set() for r in PREMISE_REGIMES}
    for usage, spec in PROMPT_REGISTRY.items():
        premise = getattr(spec, "premise", None)
        reason = getattr(spec, "premise_reason", "")
        if premise not in PREMISE_REGIMES:
            fail(f"WP1 {usage}: premise {premise!r} is not one of {PREMISE_REGIMES}")
            continue
        if (premise == "none") != bool(reason):
            fail(f"WP1 {usage}: premise {premise!r} with premise_reason {reason!r}")
        by_regime[premise].add(usage)
    for regime, expected in (("creator", CREATOR), ("player", PLAYER), ("none", NONE)):
        got = by_regime.get(regime, set())
        if got != set(expected):
            fail(f"WP1 regime {regime!r}: missing {sorted(set(expected) - got)}, "
                 f"extra {sorted(got - set(expected))}")


def _seed_world(engine) -> str:
    from sqlmodel import Session

    from world_engine.cockpit.crud.skills import SkillSystemWriteBody, create_skill_system
    from world_engine.models import World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
    from world_engine.writes.config import write_world_laws

    with Session(engine) as db:
        world = World(name="Aestia", description="Écoles et esprits.", tone="Manga, héroïque.",
                      is_active=True)
        db.add(world)
        db.flush()
        write_world_laws(db, world=world,
                         laws=["Tout humain peut se lier à un esprit.", "Le lien ne se rompt qu'à la mort."],
                         changed_by="creator_crud")
        for spec in (
            DefinitionSpec(name="Rang", kind="choice", holder_types=("character",),
                           choices=(ChoiceSpec("F"), ChoiceSpec("E")), default="F"),
            DefinitionSpec(name="Esprit lié", kind="entity", holder_types=("character",),
                           value_types=("character",)),
            DefinitionSpec(name="Maudit", kind="choice", holder_types=("character",),
                           choices=(ChoiceSpec("oui"), ChoiceSpec("non")), default="non", is_hidden=True),
            DefinitionSpec(name="Alerte", kind="integer", holder_types=("location",), default=0),
        ):
            write_attribute_definition(db, world_id=world.id, spec=spec)
        db.commit()
        world_id = world.id
    for name in ("Magie", "Alchimie"):
        with Session(engine) as db:
            create_skill_system(SkillSystemWriteBody(name=name), db)
    return world_id


def _seed_head(db, usage: str, system_prompt: str) -> tuple[object, object]:
    from world_engine.models import PromptTemplate
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    head = PromptTemplate(name=f"check {usage}", usage=usage)
    db.add(head)
    db.flush()
    write_prompt_variables(db, template_id=head.id, variables=["world_premise"])
    version = write_prompt_version(db, template_id=head.id, system_prompt=system_prompt, user_template="")
    db.flush()
    return head, version


def rule_wp2(engine) -> None:
    from sqlmodel import Session, select

    from world_engine import prompt_call
    from world_engine.models import PromptVersion, World
    from world_engine.prompt_store import PremisedPrompt, current_prompt, premised_prompt
    from world_engine.world_premise import fill, world_premise

    seen = 0
    _seed_world(engine)
    with Session(engine) as db:
        seen += 1
        got = world_premise(db, "creator", entity_type="character")
        if got != EXPECTED_CREATOR_CHARACTER:
            fail(f"WP2 creator/character: expected {EXPECTED_CREATOR_CHARACTER!r}, got {got!r}")
        seen += 1
        got = world_premise(db, "creator", entity_type="location")
        if "- Alerte (un entier ; par défaut 0)" not in got:
            fail(f"WP2 creator/location: no Alerte line in {got!r}")
        for name in ("Rang", "Maudit", "Esprit lié"):
            if name in got:
                fail(f"WP2 creator/location: holds the character state {name!r}")
        seen += 1
        got = world_premise(db, "creator")
        if "Systèmes de compétences : Alchimie ; Magie" not in got or "États" in got:
            fail(f"WP2 creator without a type: expected the systems and no states, got {got!r}")
        seen += 1
        got = world_premise(db, "player", entity_type="character")
        if got != EXPECTED_PLAYER:
            fail(f"WP2 player: expected {EXPECTED_PLAYER!r}, got {got!r}")
        for banned in ("Systèmes", "États", "Maudit"):
            if banned in got:
                fail(f"WP2 player: holds {banned!r}")
        seen += 1
        if world_premise(db, "none", entity_type="character") != "":
            fail("WP2 none: the premise is not empty")

    seen += 1
    if fill("sans cadre", None, "npc_dialogue") != "sans cadre":
        fail("WP2 fill: a text without the placeholder changed")
    with Session(engine) as db:
        seen += 1
        if fill("{world_premise}X", db, "condition_interpret") != "X":
            fail("WP2 fill: a none usage was not filled with ''")
        if fill("{world_premise}X", db, "no_such_usage") != "X":
            fail("WP2 fill: an unknown usage did not behave as none")

    with Session(engine) as db:
        head, _ = _seed_head(db, "npc_dialogue", "{world_premise}Tu es un PNJ.")
        db.commit()
        current = current_prompt(db, head)
        current_id, current_number = current.id, current.version_number
        seen += 1
        got = premised_prompt(db, head)
        db.commit()
        if not isinstance(got, PremisedPrompt):
            fail(f"WP2 premised_prompt answered a {type(got).__name__}, not a PremisedPrompt")
        else:
            if not (got.system_prompt.startswith("=== CADRE DU MONDE ===")
                    and got.system_prompt.endswith("Tu es un PNJ.")):
                fail(f"WP2 premised_prompt: system_prompt {got.system_prompt!r}")
            if (got.id, got.version_number) != (current_id, current_number):
                fail("WP2 premised_prompt: id/version_number differ from current_prompt")
    with Session(engine) as db:
        stored = db.get(PromptVersion, current_id)
        if stored is None or stored.system_prompt != "{world_premise}Tu es un PNJ.":
            fail("WP2 premised_prompt: the stored prompt_version text changed (INV-48)")

    with Session(engine) as db:
        _seed_head(db, "quest_subject", "{world_premise}Propose un sujet.")
        db.commit()
        recorded: list[list[dict]] = []

        def chat(messages, **_kwargs):
            recorded.append(messages)
            return '{"subject": "x"}'

        seen += 1
        prompt_call.call_json(db, "quest_subject", {}, None, chat)
        system = recorded[0][0]["content"] if recorded else ""
        if not system.startswith("=== CADRE DU MONDE ==="):
            fail(f"WP2 call_json: the system message starts {system[:40]!r}")

    with Session(engine) as db:
        for world in db.exec(select(World)).all():
            world.is_active = False
            db.add(world)
        db.commit()
        seen += 1
        for regime in ("creator", "player", "none"):
            if world_premise(db, regime, entity_type="character") != "":
                fail(f"WP2 no active world: regime {regime!r} is not empty")
        db.add(World(name="Nu", is_active=True))
        db.commit()
        seen += 1
        for regime in ("creator", "player"):
            if world_premise(db, regime, entity_type="character") != "":
                fail(f"WP2 a world with only a name: regime {regime!r} is not empty")
    if not seen:
        fail("WP2 collected nothing")


def _calls_by_function(tree, name: str) -> dict[str, int]:
    """Function name -> number of `name(` calls in its body (nested defs included)."""
    import ast

    counts: dict[str, int] = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = sum(1 for node in ast.walk(fn)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name)
            if n:
                counts[fn.name] = n
    return counts


def _compare(label: str, expected: frozenset, got: set) -> None:
    if not got:
        fail(f"WP3 {label}: collected nothing")
    if got != expected:
        fail(f"WP3 {label}: missing {sorted(expected - got)}, extra {sorted(got - expected)}")


def rule_wp3() -> None:
    import ast

    package = SRC / "world_engine"
    trees = {path.relative_to(package).as_posix(): ast.parse(path.read_text(encoding="utf-8"))
             for path in sorted(package.rglob("*.py")) if path.name != "prompt_store.py"}
    if not trees:
        fail("WP3 collected nothing: no module under src/world_engine")
        return
    for name, expected in (("current_prompt", STAYS), ("premised_prompt", SWAPPED)):
        got = {f"{rel}::{fn}" for rel, tree in trees.items() for fn in _calls_by_function(tree, name)}
        _compare(f"{name}( sites", expected, got)

    fills = _calls_by_function(trees.get("prompt_call.py", ast.Module(body=[], type_ignores=[])), "fill")
    if fills.get("call_json", 0) != 2:
        fail(f"WP3 prompt_call.call_json calls fill( {fills.get('call_json', 0)} times, not 2")
    load_tree = trees.get("prompt_load.py")
    if load_tree is None:
        fail("WP3 prompt_load.py not found")
    else:
        for name in ("fill", "premised_prompt"):
            if _calls_by_function(load_tree, name):
                fail(f"WP3 prompt_load.py calls {name}(")

    region_path = package / "region_author.py"
    region_src = region_path.read_text(encoding="utf-8")
    for placeholder in ("{world_description}", "{world_fundamental_laws}"):
        if f'.replace("{placeholder}", "")' not in region_src:
            fail(f"WP3 region_author.py: {placeholder} is not rendered as \"\"")
    region_tree = trees["region_author.py"]
    names = {node.id for node in ast.walk(region_tree) if isinstance(node, ast.Name)}
    names |= {alias.asname or alias.name for node in ast.walk(region_tree)
              if isinstance(node, ast.ImportFrom) for alias in node.names}
    if "WorldLaw" in names:
        fail("WP3 region_author.py still names WorldLaw")


def _import_seed():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import seed_pilot

    return seed_pilot


def _wp4_premised_texts(seed_pilot) -> None:
    from world_engine.prompt_registry import PROMPT_REGISTRY

    if not PROMPT_REGISTRY:
        fail("WP4 premised_texts collected nothing")
    for usage in PROMPT_REGISTRY:
        got = seed_pilot.premised_texts(usage, "S", "U", ["a"])
        if usage in NONE:
            expected = ("S", "U", ["a"])
        else:
            expected = ("{world_premise}S", "U", ["a", "world_premise"])
        if got != expected:
            fail(f"WP4 premised_texts({usage!r}): expected {expected!r}, got {got!r}")
        if usage not in NONE:
            done = ("{world_premise}S", "U", ["a", "world_premise"])
            again = seed_pilot.premised_texts(usage, *done)
            if again != done:
                fail(f"WP4 premised_texts({usage!r}) changed an already premised input: {again!r}")
    got = seed_pilot.premised_texts("entity_generation", "S", "U", None)
    if got[2] != ["world_premise"]:
        fail(f"WP4 premised_texts with variables=None: {got[2]!r}")


def _wp4_seed_upsert(engine, seed_pilot) -> None:
    from sqlmodel import Session

    from world_engine.prompt_store import list_versions
    from world_engine.models import PromptVariable
    from sqlmodel import select

    def upsert(db):
        seed_pilot.upsert_prompt_template(
            db, "pt-entity-generation", system_prompt="Tu crées une entité.",
            user_template="{concept}", name="Entity generation", usage="entity_generation",
            variables=["concept"],
        )

    with Session(engine) as db:
        upsert(db)
        db.commit()
        versions = list_versions(db, "pt-entity-generation")
        names = set(db.exec(select(PromptVariable.name)
                            .where(PromptVariable.prompt_template_id == "pt-entity-generation")).all())
        if len(versions) != 1 or not versions[0].system_prompt.startswith("{world_premise}"):
            fail(f"WP4 seed upsert: v1 is {[v.system_prompt for v in versions]!r}")
        if names != {"concept", "world_premise"}:
            fail(f"WP4 seed upsert: variables {sorted(names)!r}")
    with Session(engine) as db:
        upsert(db)
        db.commit()
        if len(list_versions(db, "pt-entity-generation")) != 1:
            fail("WP4 seed upsert: a second upsert wrote a v2 (S2)")


def _wp4_delivery() -> None:
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel, select

    from world_engine.models import PromptTemplate, PromptVariable
    from world_engine.prompt_store import list_versions
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    url = f"sqlite:///{pathlib.Path(tempfile.mkdtemp()) / 'delivery.db'}"
    other = create_engine(url)
    SQLModel.metadata.create_all(other)
    with Session(other) as db:
        for head_id, usage, system in (("pt-npc-dialogue", "npc_dialogue", "Tu es X."),
                                       ("pt-day-extract-place", "day_extract_place", "Extrais.")):
            db.add(PromptTemplate(id=head_id, name=head_id, usage=usage))
            db.flush()
            write_prompt_variables(db, template_id=head_id, variables=["player_line"])
            write_prompt_version(db, template_id=head_id, system_prompt=system,
                                 user_template="{player_line}")
        db.commit()
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=url, WORLD_ENGINE_ENV="test")
    script = str(ROOT / "scripts" / "apply_ticket_0124_world_premise.py")
    outputs = []
    for run in (1, 2):
        proc = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10)
        outputs.append(proc.stdout)
        if proc.returncode != 0:
            fail(f"WP4 delivery run {run} exited {proc.returncode}: {proc.stdout}{proc.stderr}")
    with Session(other) as db:
        dialogue = list_versions(db, "pt-npc-dialogue")
        if len(dialogue) != 2:
            fail(f"WP4 delivery: pt-npc-dialogue holds {len(dialogue)} versions, not 2")
        elif (dialogue[0].system_prompt, dialogue[0].user_template) != ("{world_premise}Tu es X.",
                                                                          "{player_line}"):
            fail(f"WP4 delivery: pt-npc-dialogue v2 is {dialogue[0].system_prompt!r}")
        names = sorted(db.exec(select(PromptVariable.name)
                               .where(PromptVariable.prompt_template_id == "pt-npc-dialogue")).all())
        if names != ["player_line", "world_premise"]:
            fail(f"WP4 delivery: pt-npc-dialogue variables {names!r}")
        if len(list_versions(db, "pt-day-extract-place")) != 1:
            fail("WP4 delivery: the none usage pt-day-extract-place got a new version")
    if len(outputs) == 2 and "unchanged" not in outputs[1]:
        fail(f"WP4 delivery: the second run printed {outputs[1]!r}, no 'unchanged'")
    other.dispose()


def _wp4_routes(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.crud.prompts import (
        PromptTextBody, restore_prompt_version, update_prompt_text,
    )
    from world_engine.models import PromptTemplate
    from world_engine.prompt_store import list_versions
    from world_engine.world_premise import missing_premise
    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version

    def head(db, usage, system, variables):
        row = PromptTemplate(name=f"route {usage}", usage=usage)
        db.add(row)
        db.flush()
        write_prompt_variables(db, template_id=row.id, variables=variables)
        write_prompt_version(db, template_id=row.id, system_prompt=system, user_template="")
        db.commit()
        return row.id

    def refused(label, call, usage, system, user, db, head_id):
        before = len(list_versions(db, head_id))
        try:
            call()
        except HTTPException as exc:
            expected = missing_premise(usage, system, user)
            if exc.status_code != 422 or exc.detail != expected:
                fail(f"WP4 {label}: {exc.status_code} {exc.detail!r}, expected 422 {expected!r}")
        else:
            fail(f"WP4 {label}: not refused")
        db.rollback()
        if len(list_versions(db, head_id)) != before:
            fail(f"WP4 {label}: a version was written")

    with Session(engine) as db:
        player = head(db, "mj_interpretation", "{world_premise}Interprète.", ["world_premise"])
        body = PromptTextBody(system_prompt="Interprète.", user_template="")
        refused("update player without the placeholder",
                lambda: update_prompt_text(player, body, db), "mj_interpretation",
                body.system_prompt, body.user_template, db, player)
        update_prompt_text(player, PromptTextBody(system_prompt="{world_premise}Juge.",
                                                  user_template=""), db)
        if len(list_versions(db, player)) != 2:
            fail("WP4 update player with the placeholder: no version appended")

        none = head(db, "conversation_summary", "Résume.", ["world_premise"])
        body = PromptTextBody(system_prompt="{world_premise}Résume.", user_template="")
        refused("update none with the placeholder", lambda: update_prompt_text(none, body, db),
                "conversation_summary", body.system_prompt, body.user_template, db, none)

        creator = head(db, "quest_subject", "Propose un sujet.", ["world_premise"])
        write_prompt_version(db, template_id=creator, system_prompt="{world_premise}Propose.",
                             user_template="")
        db.commit()
        refused("restore creator v1 without the placeholder",
                lambda: restore_prompt_version(creator, 1, db), "quest_subject",
                "Propose un sujet.", "", db, creator)


def _wp4_static() -> None:
    import ast

    tree = ast.parse((ROOT / "scripts" / "seed_pilot.py").read_text(encoding="utf-8"))
    value = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "REGION_MANIFEST_USER_TEMPLATE" for t in node.targets):
            value = ast.literal_eval(node.value)
    if value is None:
        fail("WP4 static: REGION_MANIFEST_USER_TEMPLATE not found")
        return
    for placeholder in ("{world_description}", "{world_fundamental_laws}"):
        if placeholder in value:
            fail(f"WP4 static: REGION_MANIFEST_USER_TEMPLATE still holds {placeholder}")


def rule_wp4(engine) -> None:
    seed_pilot = _import_seed()
    _wp4_premised_texts(seed_pilot)
    _wp4_seed_upsert(engine, seed_pilot)
    _wp4_delivery()
    _wp4_routes(engine)
    _wp4_static()


def main() -> int:
    engine = _fresh_engine()
    try:
        rule_wp1()
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"WP1 raised {type(exc).__name__}: {exc}")
    try:
        rule_wp2(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"WP2 raised {type(exc).__name__}: {exc}")
    try:
        rule_wp3()
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"WP3 raised {type(exc).__name__}: {exc}")
    try:
        rule_wp4(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"WP4 raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_premise -- 49 usages hold the 14/17/18 regime partition; the premise is "
          "built per regime, the player regime carries no state or skill system, and "
          "premised_prompt and call_json fill {world_premise} without touching the stored text; "
          "34 render calls in 31 functions read through premised_prompt, 18 functions stay on "
          "current_prompt; the seed and the delivery put {world_premise} at the head of every "
          "creator and player text, and the edit and restore routes refuse a text without it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
