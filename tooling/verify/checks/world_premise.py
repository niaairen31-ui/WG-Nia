"""G1 check for TICKET-0124 -- every generator that writes fiction is told the world it writes for, in its usage's regime, through one placeholder.

WP1 -- import. Every `PROMPT_REGISTRY` entry's `premise` is in
   `world_premise.PREMISE_REGIMES`; its `premise_reason` is non-empty exactly
   when `premise == "none"`; the keys of each regime equal this check's
   literal `CREATOR` (14), `PLAYER` (15) and `NONE` (18) tuples (C-03).
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

The fixture is a fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL`
set before any world_engine import) -- never Nia's DB. Every prompt version
carrying `{world_premise}` is written through `write_prompt_version` after
`write_prompt_variables` declared it. A rule that collected nothing is a
FAILURE.
"""
from __future__ import annotations

import os
import pathlib
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
    "day_rewrite",
)
NONE = (
    "world_generation", "room_batch_coherence", "npc_link_coherence", "npc_batch_placement",
    "lore_question_to_plan", "lore_rows_to_prose", "condition_interpret", "mj_speaker_selection",
    "conversation_analysis", "overhearing_classification", "conversation_summary",
    "day_extract_place", "day_extract_person", "day_extract_faction", "day_feasibility",
    "day_reconcile", "day_plan_select", "day_mention_choice",
)

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
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_premise -- 47 usages hold the 14/15/18 regime partition; the premise is "
          "built per regime, the player regime carries no state or skill system, and "
          "premised_prompt and call_json fill {world_premise} without touching the stored text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
