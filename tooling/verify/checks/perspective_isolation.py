"""G1 check for TICKET-0125 (BRIEF-0125-D) -- the public perspective returns only what everybody knows, and its audit names every line it withheld.

PI1 -- static isolation. `perspective_selectors.py`, `perspective_query.py`,
   `perspective_audit.py`, `perspective_render.py` contain none of `chat(`,
   `db.add(`, `.commit(`, `include_creator_only`, `CREATOR`,
   `NameScope("creator"`, `near_candidates`, `validate_binding`, and import
   none of `entity_dossier`, `who_knows_about`, `facts_mentioning`,
   `world_factions` from `lore_selectors`. `perspective_render.py` contains
   no `Session` and no `select(`.
PI2 -- tables. `PERSPECTIVE_SELECTORS`, `_PERSPECTIVE_LOOKUPS`,
   `PERSPECTIVE_DESCRIPTIONS` have the same five keys, in the tuple's order;
   every `SelectorSpec` has a non-zero `row_cap`; every `context_sections`
   string is a `"section"` literal of `perspective_selectors.py`.
PI3 -- closed verdicts. The string literals assigned to `verdict` in
   `perspective_query.py` equal `PERSPECTIVE_VERDICTS`.
PI4 -- fixture (sanctioned writers). One world: Hero (public character),
   Shade (non-public character), Guild and Guild2 (public factions), Cabal
   (non-public faction), two public characters named Twin. F1 description
   of Hero (world `knows`), F2 histoire of Hero (`unaware`), F3 the
   creator's note on Hero (world `knows`, creator-only), F4 description of
   Shade (world `knows`), F5 the lien fact of Hero -> Guild (world `knows`),
   F6 information about Shade holding `tunnel` (world `knows`), F7 a free
   fact holding `tunnel` (`unaware`). Hero belongs to Guild, to Cabal, and
   secretly to Guild2; one law. Exact sets:
   a. `public_view`: facts {F1, F4, F5, F6}; entities {Hero, Guild, Guild2,
      Twin, Twin}.
   b. a dossier on « Hero » answers; its facets are {F1, F5}; its
      memberships {Guild}; no row holds a key forbidden by C-04.
   c. a dossier on « Shade » and d. on « Nobody »: `nothing_known`, no rows;
      « Shade » does not resolve under the public scope (its name is no
      public surface).
   e. `public_facts_mentioning("tunnel")`: one `public_mentions` row (F6),
      no participant.
   f. `public_factions` names {Guild, Guild2}; `world_laws` the law.
   g. `withheld`: b -> {not_public F2, creator_only F3, faction_not_public
      "Cabal (-)", secret_membership "Guild2 (-)"}, all subject Hero;
      c -> {entity_not_public Shade "Shade"}; e -> {not_public "tunnel" F7}.
   h. a binding to Shade on « Shade » raises `BindingRefused`; « Twin » is
      `ambiguous_mention` with both Twins (keys `entity_id, name, type`), and
      a binding to either is accepted.
   i. `NameScope("public")` without `known_fact_ids` raises `ValueError`.
PI5 -- render, `chat` stubbed. Each non-`answered` verdict renders its
   constant, renderer `deterministic`, no model call; `answered` makes
   exactly one call.
PI6 -- skills (BRIEF-0126-D). A world of its own: system `Visible`
   (default) and system `Cachée` (`visible_at_creation = False`); `Lame` in
   `Visible`, `Ombre` in `Cachée`, `Voix` in `Cachée` with
   `visible_at_creation = True` and `requires_master`. Exact sets:
   `public_view(...).skill_ids == {Lame, Voix}`; `public_skills` returns
   `Voix` (system `Cachée`) then `Lame` (system `Visible`), each row's keys
   exactly C-07's, none forbidden; `withheld` of `public_skills($world)` is
   exactly `[skill_not_visible Ombre "Ombre"]`; the plan is `answered`; its
   serialized rows hold `- Voix (Cachée, composure) ; exige un maître` and
   `- Lame (Visible, agility)`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
MODULES = ("perspective_selectors.py", "perspective_query.py", "perspective_audit.py", "perspective_render.py")
FORBIDDEN = ("chat(", "db.add(", ".commit(", "include_creator_only", "CREATOR", 'NameScope("creator"',
             "near_candidates", "validate_binding")
CREATOR_SELECTORS = {"entity_dossier", "who_knows_about", "facts_mentioning", "world_factions"}
FORBIDDEN_KEYS = {"is_secret", "is_incorrect", "intensity", "internal_name", "knowers", "creator_only", "level"}

FAILURES: list[str] = []


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


def _read(name: str) -> str | None:
    path = PKG / name
    if not path.exists():
        fail(f"{name} missing")
        return None
    return path.read_text(encoding="utf-8")


def rule_pi1() -> None:
    for name in MODULES:
        text = _read(name)
        if text is None:
            continue
        for needle in FORBIDDEN:
            if needle in text:
                fail(f"PI1 {name} contains {needle!r}")
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("lore_selectors"):
                bad = {alias.name for alias in node.names} & CREATOR_SELECTORS
                if bad:
                    fail(f"PI1 {name} imports creator selector(s) {sorted(bad)}")
        if name == "perspective_render.py":
            for needle in ("Session", "select("):
                if needle in text:
                    fail(f"PI1 perspective_render.py contains {needle!r}")


def _section_literals(text: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "section" and isinstance(value, ast.Constant):
                    found.add(value.value)
    return found


def rule_pi2() -> None:
    from world_engine import perspective_selectors as ps

    names = ps.PERSPECTIVE_SELECTORS
    if len(names) != 5:
        fail(f"PI2 PERSPECTIVE_SELECTORS holds {len(names)} names, expected 5")
    if tuple(ps._PERSPECTIVE_LOOKUPS) != names or tuple(ps.PERSPECTIVE_DESCRIPTIONS) != names:
        fail("PI2 the three tables do not share PERSPECTIVE_SELECTORS's keys in its order")
    text = _read("perspective_selectors.py") or ""
    sections = _section_literals(text)
    for name, spec in ps._PERSPECTIVE_LOOKUPS.items():
        if not spec.row_cap:
            fail(f"PI2 {name} has no row_cap")
        for section in spec.context_sections:
            if section not in sections:
                fail(f"PI2 {name} context section {section!r} is not a section literal")


def _verdict_literals(text: str) -> set[str]:
    found: set[str] = set()

    def collect(value) -> None:
        for sub in ast.walk(value):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                found.add(sub.value)

    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.keyword) and node.arg == "verdict":
            collect(node.value)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "verdict" for t in node.targets):
            collect(node.value)
    return found


def rule_pi3() -> None:
    from world_engine.perspective_query import PERSPECTIVE_VERDICTS

    text = _read("perspective_query.py")
    if text is None:
        return
    got = _verdict_literals(text)
    if got != set(PERSPECTIVE_VERDICTS):
        fail(f"PI3 verdict literals {sorted(got)} != PERSPECTIVE_VERDICTS {sorted(PERSPECTIVE_VERDICTS)}")


def _build_world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Faction, World
    from world_engine.prose_render import fact_text
    from world_engine.writes.config import write_world_laws
    from world_engine.writes.facets import write_entity_facets
    from world_engine.writes.factions import write_membership
    from world_engine.writes.facts import attach_participants, create_fact, create_fact_default
    from world_engine.writes.relations import lien_fact_of, write_relation

    ids: dict = {}
    with Session(engine) as db:
        world = World(name="PI World")
        db.add(world)
        db.flush()
        wid = world.id

        def entity(key, name, type_, public=True):
            e = Entity(world_id=wid, type=type_, name=name, is_public=public)
            db.add(e)
            db.flush()
            if type_ == "character":
                db.add(Character(id=e.id, world_id=wid, character_type="npc"))
            elif type_ == "faction":
                db.add(Faction(id=e.id))
            ids[key] = e.id

        entity("hero", "Hero", "character")
        entity("shade", "Shade", "character", public=False)
        entity("guild", "Guild", "faction")
        entity("guild2", "Guild2", "faction")
        entity("cabal", "Cabal", "faction", public=False)
        entity("twin1", "Twin", "character")
        entity("twin2", "Twin", "character")
        db.flush()

        def fact(key, content, facet, about, level=None):
            f = create_fact(db, world_id=wid, content=content, created_by="check", facet=facet)
            db.flush()
            if about:
                attach_participants(db, fact=f, entity_ids=[ids[a] for a in about])
            if level:
                create_fact_default(db, world_id=wid, fact_id=f.id, scope_type="world", scope_id=None,
                                    level=level, created_by="check")
            ids[key] = f.id

        fact("F1", "Hero porte une cape rouge", "description", ["hero"], "knows")
        fact("F2", "Hero fut esclave", "histoire", ["hero"])
        fact("F4", "Shade est une ombre", "description", ["shade"], "knows")
        fact("F6", "Shade creuse un tunnel", "information", ["shade"], "knows")
        fact("F7", "Le tunnel cache un tresor", "information", [])
        notes = write_entity_facets(db, entity_id=ids["hero"], created_by="check",
                                    facets={"creator_meta": "Hero trahira la guilde"})
        db.flush()
        ids["F3"] = notes[0].id
        create_fact_default(db, world_id=wid, fact_id=ids["F3"], scope_type="world", scope_id=None,
                            level="knows", created_by="check")
        rel = write_relation(db, mode="set", world_id=wid, entity_a_id=ids["hero"],
                             entity_b_id=ids["guild"], type="ally", value=50)
        db.flush()
        lien = lien_fact_of(db, rel)
        ids["F5"] = lien.id
        create_fact_default(db, world_id=wid, fact_id=lien.id, scope_type="world", scope_id=None,
                            level="knows", created_by="check")
        for faction, secret in (("guild", False), ("cabal", False), ("guild2", True)):
            db.add(write_membership(db, mode="open", world_id=wid, entity_id=ids["hero"],
                                    faction_id=ids[faction], is_secret=secret))
        write_world_laws(db, world=world, laws=["La magie a un prix"], changed_by="check")
        db.commit()
        from world_engine.models import Fact
        ids["text"] = {key: fact_text(db, db.get(Fact, ids[key])) for key in ("F1", "F2", "F3", "F5", "F6", "F7")}
        ids["world"] = wid
    return ids


def _plan(selector: str, *, mention: str | None = None, text: str | None = None, category: str = "person"):
    from world_engine.lore_query import LorePlan, PlanCall, PlanMention

    if mention is not None:
        return LorePlan(mentions=(PlanMention("m1", mention, category),), calls=(PlanCall(selector, ("m1", "$world")),))
    if text is not None:
        return LorePlan(mentions=(), calls=(PlanCall(selector, (f"text:{text}", "$world")),))
    return LorePlan(mentions=(), calls=(PlanCall(selector, ("$world",)),))


def _rows(result, section: str) -> list[dict]:
    return [r for r in result.rows if r["section"] == section]


def rule_pi4(engine) -> int:
    from sqlmodel import Session

    from world_engine.name_index import NameScope
    from world_engine.perspective_audit import withheld
    from world_engine.lore_resolve import resolve_named
    from world_engine.perspective_query import BindingRefused, execute_public_plan, public_scope
    from world_engine.perspective_selectors import public_view

    ids = _build_world(engine)
    wid, text = ids["world"], ids["text"]
    reached = 0
    with Session(engine) as db:
        view = public_view(db, wid)
        if set(view.fact_ids) != {ids["F1"], ids["F4"], ids["F5"], ids["F6"]}:
            fail(f"PI4a public facts {sorted(view.fact_ids)} != F1, F4, F5, F6")
        if set(view.entity_ids) != {ids[k] for k in ("hero", "guild", "guild2", "twin1", "twin2")}:
            fail("PI4a public entities are not Hero, Guild, Guild2 and the two Twins")
        reached += 1

        hero_plan = _plan("public_dossier", mention="Hero")
        hero = execute_public_plan(hero_plan, wid, db)
        if hero.verdict != "answered":
            fail(f"PI4b the dossier on Hero is {hero.verdict!r}, expected 'answered'")
        if {r["content"] for r in _rows(hero, "facets")} != {text["F1"], text["F5"]}:
            fail(f"PI4b Hero's facets are {[r['content'] for r in _rows(hero, 'facets')]}")
        if {r["faction_name"] for r in _rows(hero, "memberships")} != {"Guild"}:
            fail(f"PI4b Hero's memberships are {[r['faction_name'] for r in _rows(hero, 'memberships')]}")
        for row in hero.rows:
            if set(row) & FORBIDDEN_KEYS:
                fail(f"PI4b a row holds forbidden key(s) {sorted(set(row) & FORBIDDEN_KEYS)}")
        reached += 1

        shade_plan = _plan("public_dossier", mention="Shade")
        for label, plan in (("PI4c Shade", shade_plan), ("PI4d Nobody", _plan("public_dossier", mention="Nobody"))):
            result = execute_public_plan(plan, wid, db)
            if result.verdict != "nothing_known" or result.rows:
                fail(f"{label}: {result.verdict!r} with {len(result.rows)} row(s), expected nothing_known, none")
        shade_named = resolve_named("Shade", "person", wid, db, scope=public_scope(view))
        if shade_named.verdict != "unmatched":
            fail(f"PI4c « Shade » resolves under the public scope ({shade_named.verdict!r})")
        reached += 1

        tunnel_plan = _plan("public_facts_mentioning", text="tunnel")
        tunnel = execute_public_plan(tunnel_plan, wid, db)
        mentions = _rows(tunnel, "public_mentions")
        if [(r["content"], r["participants"]) for r in mentions] != [(text["F6"], [])]:
            fail(f"PI4e tunnel mentions are {mentions!r}, expected F6 with no participant")
        reached += 1

        factions = execute_public_plan(_plan("public_factions"), wid, db)
        if {r["name"] for r in _rows(factions, "factions")} != {"Guild", "Guild2"}:
            fail(f"PI4f public factions are {[r['name'] for r in factions.rows]}")
        laws = execute_public_plan(_plan("world_laws"), wid, db)
        if [r["text"] for r in _rows(laws, "laws")] != ["La magie a un prix"]:
            fail(f"PI4f laws are {[r.get('text') for r in laws.rows]}")
        reached += 1

        def audit(plan) -> set[tuple]:
            return {(r["reason"], r["subject"], r["content"]) for r in withheld(plan, wid, db)}

        expected = {
            "Hero": (hero_plan, {("not_public", "Hero", text["F2"]), ("creator_only", "Hero", text["F3"]),
                                 ("faction_not_public", "Hero", "Cabal (-)"),
                                 ("secret_membership", "Hero", "Guild2 (-)")}),
            "Shade": (shade_plan, {("entity_not_public", "Shade", "Shade")}),
            "tunnel": (tunnel_plan, {("not_public", "tunnel", text["F7"])}),
        }
        for label, (plan, want) in expected.items():
            got = audit(plan)
            if got != want:
                fail(f"PI4g audit of {label}: {sorted(got)} != {sorted(want)}")
        reached += 1

        try:
            execute_public_plan(shade_plan, wid, db, bindings={"m1": ids["shade"]})
            fail("PI4h a binding to Shade was accepted")
        except BindingRefused:
            pass
        twin_plan = _plan("public_dossier", mention="Twin")
        twin = execute_public_plan(twin_plan, wid, db)
        candidates = twin.ambiguous[0]["candidates"] if twin.ambiguous else []
        if twin.verdict != "ambiguous_mention" or {c["entity_id"] for c in candidates} != {ids["twin1"], ids["twin2"]}:
            fail(f"PI4h « Twin » is {twin.verdict!r} with {candidates!r}")
        if any(set(c) != {"entity_id", "name", "type"} for c in candidates):
            fail(f"PI4h candidate keys are {[sorted(c) for c in candidates]}")
        for key in ("twin1", "twin2"):
            bound = execute_public_plan(twin_plan, wid, db, bindings={"m1": ids[key]})
            if bound.verdict not in ("nothing_known", "answered"):
                fail(f"PI4h a binding to {key} gave {bound.verdict!r}")
        reached += 1

    try:
        NameScope("public")
        fail("PI4i NameScope('public') without known_fact_ids was accepted")
    except ValueError:
        pass
    reached += 1
    return reached


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else __import__("json").dumps(reply)


def _swap(module, stub):
    original = module.chat
    module.chat = stub
    return original


def rule_pi5() -> int:
    from world_engine import lore_render
    from world_engine import perspective_render as pr
    from world_engine.lore_prompt import RenderSpec
    from world_engine.perspective_query import PerspectiveResult

    spec = RenderSpec(system_prompt="s", user_template="{question}\n{rows}", model="m",
                      version_id="v", version_number=1)
    stub = _Stub(["Une réponse."])
    original = _swap(lore_render, stub)
    reached = 0
    try:
        for verdict, message in (("nothing_known", pr.NOTHING_KNOWN_MESSAGE),
                                 ("unsupported_selector", pr.UNSUPPORTED_MESSAGE),
                                 ("ambiguous_mention", pr.AMBIGUOUS_MESSAGE)):
            answer = pr.render_public(PerspectiveResult(verdict, (), (), None), "q", spec)
            if (answer.prose, answer.renderer) != (message, "deterministic"):
                fail(f"PI5 {verdict} rendered {answer.prose!r} by {answer.renderer!r}")
            reached += 1
        if stub.messages:
            fail(f"PI5 an empty verdict reached the model ({len(stub.messages)} call(s))")
        rows = ({"section": "laws", "position": 0, "text": "La magie a un prix"},)
        answer = pr.render_public(PerspectiveResult("answered", rows, (), None), "q", spec)
        if len(stub.messages) != 1 or answer.renderer != "model":
            fail(f"PI5 answered made {len(stub.messages)} call(s), renderer {answer.renderer!r}")
        reached += 1
    finally:
        lore_render.chat = original
    return reached


SKILL_KEYS = {"section", "skill_id", "name", "base_domain", "system", "description", "requires_master"}


def rule_pi6(engine) -> int:
    from sqlmodel import Session

    from world_engine import lore_render
    from world_engine.models import SkillDefinition, SkillSystem, World
    from world_engine.perspective_audit import withheld
    from world_engine.perspective_query import execute_public_plan
    from world_engine.perspective_selectors import public_skills, public_view

    reached = 0
    with Session(engine) as db:
        world = World(name="PI6 World")
        db.add(world)
        db.flush()
        wid = world.id
        visible = SkillSystem(world_id=wid, name="Visible")
        hidden = SkillSystem(world_id=wid, name="Cachée", visible_at_creation=False)
        db.add(visible)
        db.add(hidden)
        db.flush()
        lame = SkillDefinition(world_id=wid, name="Lame", base_domain="agility", system_id=visible.id)
        ombre = SkillDefinition(world_id=wid, name="Ombre", base_domain="perception", system_id=hidden.id)
        voix = SkillDefinition(world_id=wid, name="Voix", base_domain="composure", system_id=hidden.id,
                               visible_at_creation=True, requires_master=True)
        for definition in (lame, ombre, voix):
            db.add(definition)
        db.commit()

        view = public_view(db, wid)
        if set(view.skill_ids) != {lame.id, voix.id}:
            fail(f"PI6 public skill ids {sorted(view.skill_ids)} != Lame, Voix")
        reached += 1

        rows = public_skills(wid, view, db)
        if [(r["name"], r["system"]) for r in rows] != [("Voix", "Cachée"), ("Lame", "Visible")]:
            fail(f"PI6 public_skills rows are {[(r.get('name'), r.get('system')) for r in rows]}")
        for row in rows:
            if set(row) != SKILL_KEYS:
                fail(f"PI6 a skill row's keys are {sorted(row)}")
            if set(row) & FORBIDDEN_KEYS:
                fail(f"PI6 a skill row holds forbidden key(s) {sorted(set(row) & FORBIDDEN_KEYS)}")
        reached += 1

        plan = _plan("public_skills")
        got = withheld(plan, wid, db)
        if got != [{"reason": "skill_not_visible", "subject": "Ombre", "content": "Ombre"}]:
            fail(f"PI6 the audit of public_skills is {got!r}")
        reached += 1

        result = execute_public_plan(plan, wid, db)
        if result.verdict != "answered":
            fail(f"PI6 public_skills is {result.verdict!r}, expected 'answered'")
        text = lore_render._serialize_rows_by_section(result.rows)
        for line in ("- Voix (Cachée, composure) ; exige un maître", "- Lame (Visible, agility)"):
            if line not in text.splitlines():
                fail(f"PI6 the render lacks {line!r}: {text!r}")
        if "Ombre" in text:
            fail("PI6 the hidden skill Ombre reaches the render")
        reached += 1
    return reached


def main() -> int:
    engine = _fresh_engine()
    for rule in (rule_pi1, rule_pi2, rule_pi3):
        try:
            rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
    for rule, count, args in ((rule_pi4, 8, (engine,)), (rule_pi5, 4, ()), (rule_pi6, 4, (engine,))):
        reached = 0
        try:
            reached = rule(*args)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
        if reached != count:
            fail(f"{rule.__name__} reached {reached} of its {count} cases")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: perspective_isolation -- public view, selectors, executor, audit and renderer: "
          "nothing creator-only, secret or non-public reaches the public answer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
