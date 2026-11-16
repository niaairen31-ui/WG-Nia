"""G1 check for TICKET-0127 -- a character's perspective answers only what he knows, keeps a secret from the player's door, and journals every question.

The fixture is `perspective_isolation._build_world` extended by `_extend`
through sanctioned writers: Mira, Vex and a third Twin (non-public NPCs),
Ordre (non-public faction), Lune (non-public player character of profile
Ana; a second profile Bo), the world open to players; F8 « Shade porte un
masque » (Shade, a `rencontre` default on Shade at `knows`, Mira meets
Shade, then the text changes); Mira's knowledge of F7 (`rumor`, secret)
and F2 (`knows`, « Hero fut affranchi », incorrect), Lune's of F7 (`rumor`,
secret, a deliberate breach of INV-07); Mira openly in Cabal; F9 « Vex vend
des secrets » (Vex, no default); an event type « Fait », E1 « Le sacre de
Hero » (Hero, world `knows`) and E2 « La fuite de Shade » (Shade and Mira,
no scope); the hidden skills Ombre (Mira holds it at rank 1, and agility at
rank 2) and Lame (held by nobody); F10 « Hero cache une dague » (Hero, no
default); Shade openly in Guild.

CP1 -- static. `perspective_view.py` holds none of
   `perspective_isolation.FORBIDDEN` and imports none of its
   `CREATOR_SELECTORS`.
CP2 -- `character_view(db, wid, mira, door="creator")`: `fact_ids == {F1,
   F2, F4, F5, F6, F7, F8, E1, E2}`; `entity_ids == {hero, guild, guild2,
   twin1, twin2, mira, shade, cabal}`; `skill_ids == {ombre}`; `member_of ==
   {cabal}`; `beliefs[F2]` text « Hero fut affranchi », `incorrect`;
   `beliefs[F7]` certainty « rumeur », `secret`, text `None`; `beliefs[F8]`
   text `None`, `fact_is_stale(F8, as_of)`; `beliefs[F1].as_of is None`;
   `set(beliefs) == fact_ids`. `door="player"`: the same minus F7.
   `character_view` on `ordre` (a faction), on an unknown id, and on `mira`
   under the world id `"no-world"` raise `UnknownCharacter`; `door="x"`
   raises `ValueError`. `public_view(db, wid)` has the defaults of C-02.
CP3 -- the names of `surfaces(db, wid, NameScope("character",
   known_fact_ids=v.fact_ids, entity_ids=v.entity_ids))` (Mira's creator
   view `v`) belong exactly to `v.entity_ids`; `resolve_named("Twin",
   "person", ...)` under it is `ambiguous` with exactly `{twin1, twin2}`;
   « Vex » is `unmatched`; `NameScope("character", known_fact_ids=frozenset())`
   and `NameScope("public", known_fact_ids=frozenset(), entity_ids=frozenset())`
   raise `ValueError`.
CP4 -- selectors on Mira's creator view (labels from `FACETS`):
   `known_dossier(hero)` facets `{(Description, « Hero porte une cape
   rouge », False, None), (Histoire, « Hero fut affranchi », False, None),
   (Événement, « Le sacre de Hero », False, None), (Lien, F5's text, False,
   None)}` as `(label, content, secret, certainty)`; memberships `{Guild,
   Cabal}`; `known_dossier(shade)` facets contents `{« Shade est une ombre »,
   « Shade creuse un tunnel », « Shade porte un masque », « La fuite de
   Shade »}`; `known_dossier(cabal)` members `{Hero, Mira}`;
   `known_dossier(vex)` and `(ordre)` are `[]`; `known_factions` names
   `[Cabal, Guild, Guild2]`; `known_facts_mentioning("tunnel")` is `[(« Le
   tunnel cache un tresor », [], True, « rumeur »), (« Shade creuse un
   tunnel », [Shade], False, None)]` as `(content, participants, secret,
   certainty)`, and on the player's view only the second; `self_sheet`
   acquaintances `[(Shade, character)]`, own_skills `[(agility, agility,
   None, Apprenti), (Ombre, perception, None, Initié)]`; `known_skills` names
   `[Ombre]`. On `public_view`: `known_dossier(hero)` facets contents `{F1,
   « Le sacre de Hero », F5}`, memberships `{Guild}`; `self_sheet` is `[]`.
   No row of any call holds a key of `FORBIDDEN_KEYS`.
CP5 -- `lore_render._serialize_rows_by_section` over the tunnel rows holds
   `« Le tunnel cache un tresor » (certitude : rumeur) [secret]` and
   `« Shade creuse un tunnel » -- Shade`; over `self_sheet`'s rows `Shade
   (character)` and `agility (sans système, agility) : Apprenti`; over public
   `known_dossier(hero)` the F1 line `Description : Hero porte une cape
   rouge` with no suffix.
CP6 -- executor and audit on Mira's views (`perspective_isolation._plan`):
   `known_dossier` « Hero » answered with C-06's rows; « Vex »
   `nothing_known`; « Twin » `ambiguous_mention` with exactly the two public
   Twins; a binding to `twin3` raises `BindingRefused`; `_plan("self_sheet")`
   on `public_view` is `unsupported_selector`. `withheld_for` as `(reason,
   subject, content)`: « Hero », creator door -> creator_only « Hero trahira
   la guilde », false_belief « Hero fut esclave », not_known « Hero cache une
   dague », secret_membership « Guild2 (-) »; « Shade » -> stale_version
   « Shade a ote son masque », membership_unknown « Guild (-) »; `text:tunnel`
   creator door -> `[]`, player door -> concealed « Le tunnel cache un
   tresor »; `known_factions` -> entity_unknown Ordre; « Vex » ->
   entity_unknown Vex; `known_skills` -> skill_unknown Lame, and on
   `public_view` skill_not_visible Lame and Ombre. `withheld` (public) of
   « Hero » is PI4g's four lines plus not_public « Hero cache une dague ».
   `render_perspective(nothing_known, ..., nom="Mira")` prose is « Rien de ce
   que Mira sait ne répond à cette question. ».
CP7 -- the routes (TestClient, the `player_routes` harness): (a) `GET
   /api/lore/perspective/characters` lists Lune first, then Hero, Mira,
   Shade, Twin x3, Vex, keys exactly `{id, name, character_type}`; (b)
   `character` without `character_id`, `public` with one, and an unknown id
   -> 422, no journal row; (c) the creator asks as Mira about « tunnel »: 200
   with `CREATOR_KEYS`, the render prompt holds the rumor and `[secret]`, one
   `perspective_ask/ok` row naming `character`, Mira, `creator`; (d) `GET
   /api/joueur/personnage` names Lune for Ana, nothing for Bo; (e) Ana asks
   as Lune, same plan: 200 with `PLAYER_KEYS`, the render prompt does NOT
   hold the rumor, the journal's `withheld` holds it as `concealed`, with
   Lune and `player:<ana>`; (f) Bo with Lune's id -> 404, no row; (g)
   resolve as Lune, « Twin » bound to `twin3` -> 422 `Choix refusé.`, one
   `perspective_resolve/refused` row.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import, by `player_routes._fresh_engine`) -- never Nia's DB. A
rule that collected nothing is a FAILURE; exit 1 on any failure.
"""
from __future__ import annotations

import ast
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import perspective_isolation as pi  # noqa: E402 -- imports no world_engine at module level
import player_routes as pr  # noqa: E402 -- idem

PKG = pi.PKG

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _extend(engine, ids: dict) -> dict:
    from sqlmodel import Session

    from world_engine.encounters import record_encounter
    from world_engine.event_vocab import type_view
    from world_engine.models import Character, Entity, Faction, Skill, SkillDefinition, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type
    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, event_fact, write_event
    from world_engine.writes.factions import write_membership
    from world_engine.writes.facts import attach_participants, create_fact, create_fact_default, update_fact_content
    from world_engine.writes.knowledge import write_knowledge
    from world_engine.writes.users import create_player_profile

    wid = ids["world"]
    with Session(engine) as db:
        # 1. entities
        ana = create_player_profile(db, "Ana")
        bo = create_player_profile(db, "Bo")
        ids["ana"], ids["bo"] = ana.id, bo.id

        def entity(key, name, type_, *, character_type="npc", user_id=None):
            e = Entity(world_id=wid, type=type_, name=name, is_public=False)
            db.add(e)
            db.flush()
            if type_ == "character":
                db.add(Character(id=e.id, world_id=wid, character_type=character_type, user_id=user_id))
            elif type_ == "faction":
                db.add(Faction(id=e.id))
            ids[key] = e.id

        entity("mira", "Mira", "character")
        entity("vex", "Vex", "character")
        entity("twin3", "Twin", "character")
        entity("ordre", "Ordre", "faction")
        entity("lune", "Lune", "character", character_type="player", user_id=ana.id)
        db.get(World, wid).open_to_players = True
        db.flush()

        def fact(key, content, facet, about):
            f = create_fact(db, world_id=wid, content=content, created_by="check", facet=facet)
            db.flush()
            attach_participants(db, fact=f, entity_ids=[ids[a] for a in about])
            ids[key] = f.id
            return f

        # 2. F8, met then changed
        f8 = fact("F8", "Shade porte un masque", "description", ["shade"])
        create_fact_default(db, world_id=wid, fact_id=f8.id, scope_type="rencontre", scope_id=ids["shade"],
                            level="knows", created_by="check")
        db.flush()
        record_encounter(db, world_id=wid, a_id=ids["mira"], b_id=ids["shade"], source="relation")
        db.flush()
        update_fact_content(db, fact=f8, content="Shade a ote son masque", changed_by="check", kind="changement")
        db.flush()
        # 3. knowledge
        write_knowledge(db, entity_id=ids["mira"], fact_id=ids["F7"], level="rumor", is_secret=True,
                        changed_by="check")
        write_knowledge(db, entity_id=ids["mira"], fact_id=ids["F2"], level="knows",
                        content="Hero fut affranchi", is_incorrect=True, changed_by="check")
        write_knowledge(db, entity_id=ids["lune"], fact_id=ids["F7"], level="rumor", is_secret=True,
                        changed_by="check")
        db.flush()
        # 4. Mira openly in Cabal
        db.add(write_membership(db, mode="open", world_id=wid, entity_id=ids["mira"],
                                faction_id=ids["cabal"], is_secret=False))
        db.flush()
        # 5. F9
        fact("F9", "Vex vend des secrets", "description", ["vex"])
        # 6. events
        etype = write_event_type(db, world_id=wid, spec=EventTypeSpec(
            name="Fait", roles=(RoleSpec("qui", ("character", "faction")),)))
        db.flush()
        role_id = type_view(db, etype.id).roles[0].id
        e1 = write_event(db, world_id=wid, created_by="check", spec=EventSpec(
            type_id=etype.id, title="Le sacre de Hero",
            participants=(ParticipantSpec(role_id, entity_id=ids["hero"]),),
            scopes=(EventScopeSpec("world", None, "knows"),)))
        e2 = write_event(db, world_id=wid, created_by="check", spec=EventSpec(
            type_id=etype.id, title="La fuite de Shade",
            participants=(ParticipantSpec(role_id, entity_id=ids["shade"]),
                          ParticipantSpec(role_id, entity_id=ids["mira"])),
            scopes=()))
        db.flush()
        ids["E1"], ids["E2"] = event_fact(db, e1.id).id, event_fact(db, e2.id).id
        # 7. skills
        ombre = SkillDefinition(world_id=wid, name="Ombre", base_domain="perception", visible_at_creation=False)
        lame = SkillDefinition(world_id=wid, name="Lame", base_domain="agility", visible_at_creation=False)
        db.add(ombre)
        db.add(lame)
        db.flush()
        ids["ombre"], ids["lame"] = ombre.id, lame.id
        db.add(Skill(character_id=ids["mira"], domain="agility", rank=2))
        db.add(Skill(character_id=ids["mira"], domain="perception", rank=1, skill_definition_id=ombre.id))
        db.flush()
        # 8. F10, Shade openly in Guild
        fact("F10", "Hero cache une dague", "information", ["hero"])
        db.add(write_membership(db, mode="open", world_id=wid, entity_id=ids["shade"],
                                faction_id=ids["guild"], is_secret=False))
        db.commit()
    return ids


def rule_cp1() -> int:
    path = PKG / "perspective_view.py"
    text = path.read_text(encoding="utf-8")
    for needle in pi.FORBIDDEN:
        if needle in text:
            fail(f"CP1 perspective_view.py contains {needle!r}")
    imported = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ImportFrom):
            imported |= {alias.name for alias in node.names}
    bad = imported & pi.CREATOR_SELECTORS
    if bad:
        fail(f"CP1 perspective_view.py imports creator selectors {sorted(bad)}")
    return 1 if imported else 0


def rule_cp2(engine, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine.prose_render import fact_is_stale
    from world_engine.models import Fact
    from world_engine.perspective_selectors import public_view
    from world_engine.perspective_view import UnknownCharacter, character_view

    reached = 0
    wid = ids["world"]
    want_facts = {ids[k] for k in ("F1", "F2", "F4", "F5", "F6", "F7", "F8", "E1", "E2")}
    want_entities = {ids[k] for k in ("hero", "guild", "guild2", "twin1", "twin2", "mira", "shade", "cabal")}
    with Session(engine) as db:
        v = character_view(db, wid, ids["mira"], door="creator")
        names = {value: key for key, value in ids.items() if isinstance(value, str)}

        def show(s):
            return sorted(names.get(x, x) for x in s)

        if set(v.fact_ids) != want_facts:
            fail(f"CP2 creator fact_ids {show(v.fact_ids)} != {show(want_facts)}")
        if set(v.entity_ids) != want_entities:
            fail(f"CP2 entity_ids {show(v.entity_ids)} != {show(want_entities)}")
        if set(v.skill_ids) != {ids["ombre"]}:
            fail(f"CP2 skill_ids {show(v.skill_ids)} != ['ombre']")
        if set(v.member_of) != {ids["cabal"]}:
            fail(f"CP2 member_of {show(v.member_of)} != ['cabal']")
        if set(v.beliefs) != set(v.fact_ids):
            fail("CP2 set(beliefs) != fact_ids")
        if (v.kind, v.character_id, v.character_name, v.door) != ("character", ids["mira"], "Mira", "creator"):
            fail(f"CP2 header {(v.kind, v.character_name, v.door)!r}")
        b2, b7, b8, b1 = (v.beliefs.get(ids[k]) for k in ("F2", "F7", "F8", "F1"))
        if b2 is None or b2.text != "Hero fut affranchi" or not b2.incorrect:
            fail(f"CP2 beliefs[F2] {b2!r}")
        if b7 is None or b7.certainty != "rumeur" or not b7.secret or b7.text is not None:
            fail(f"CP2 beliefs[F7] {b7!r}")
        if b8 is None or b8.text is not None or not fact_is_stale(db.get(Fact, ids["F8"]), b8.as_of):
            fail(f"CP2 beliefs[F8] {b8!r} is not stale")
        if b1 is None or b1.as_of is not None:
            fail(f"CP2 beliefs[F1] {b1!r} as_of is not None")
        reached += 1

        p = character_view(db, wid, ids["mira"], door="player")
        if set(p.fact_ids) != want_facts - {ids["F7"]}:
            fail(f"CP2 player fact_ids {show(p.fact_ids)} != creator's minus F7")
        if set(p.beliefs) != set(p.fact_ids) or p.door != "player":
            fail("CP2 player beliefs or door")
        reached += 1

        for label, args in (("ordre", (wid, ids["ordre"])), ("unknown", (wid, "no-such-id")),
                            ("no-world", ("no-world", ids["mira"]))):
            try:
                character_view(db, *args, door="creator")
                fail(f"CP2 character_view on {label} did not raise UnknownCharacter")
            except UnknownCharacter:
                reached += 1
        try:
            character_view(db, wid, ids["mira"], door="x")
            fail("CP2 door='x' did not raise ValueError")
        except UnknownCharacter:
            fail("CP2 door='x' raised UnknownCharacter, not a plain ValueError")
        except ValueError:
            reached += 1

        pub = public_view(db, wid)
        defaults = (pub.kind, pub.character_id, pub.character_name, pub.door, pub.member_of, dict(pub.beliefs))
        if defaults != ("public", None, None, "creator", frozenset(), {}):
            fail(f"CP2 public_view defaults {defaults!r}")
        reached += 1
    return reached


def rule_cp3(engine, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine.lore_resolve import resolve_named
    from world_engine.name_index import NameScope, surfaces
    from world_engine.perspective_view import character_view

    reached = 0
    wid = ids["world"]
    with Session(engine) as db:
        v = character_view(db, wid, ids["mira"], door="creator")
        scope = NameScope("character", known_fact_ids=v.fact_ids, entity_ids=v.entity_ids)
        found = surfaces(db, wid, scope)
        if not found:
            fail("CP3 surfaces under the character regime is empty")
        elif {s.entity_id for s in found} != set(v.entity_ids):
            fail("CP3 the character regime's surfaces do not belong exactly to the view's entities")
        else:
            reached += 1
        twin = resolve_named("Twin", "person", wid, db, scope=scope)
        if twin.verdict != "ambiguous" or set(twin.candidate_ids) != {ids["twin1"], ids["twin2"]}:
            fail(f"CP3 « Twin » {twin.verdict} {twin.candidate_ids!r}")
        else:
            reached += 1
        vex = resolve_named("Vex", "person", wid, db, scope=scope)
        if vex.verdict != "unmatched":
            fail(f"CP3 « Vex » is {vex.verdict}, not unmatched")
        else:
            reached += 1
    for label, kwargs in (("character without entity_ids", {"regime": "character", "known_fact_ids": frozenset()}),
                          ("public with entity_ids", {"regime": "public", "known_fact_ids": frozenset(),
                                                       "entity_ids": frozenset()})):
        try:
            NameScope(**kwargs)
            fail(f"CP3 NameScope {label} did not raise ValueError")
        except ValueError:
            reached += 1
    return reached


class _Rule:
    """Counts the cases a rule reached; a failed case is reported, not counted."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.reached = 0

    def expect(self, ok: bool, msg: str) -> None:
        if ok:
            self.reached += 1
        else:
            fail(f"{self.name} {msg}")


def _cp4_calls(engine, ids: dict) -> dict:
    """Every selector call CP4 and CP5 read, by label."""
    from sqlmodel import Session

    from world_engine import perspective_selectors as ps
    from world_engine.perspective_view import character_view

    wid = ids["world"]
    with Session(engine) as db:
        v = character_view(db, wid, ids["mira"], door="creator")
        vp = character_view(db, wid, ids["mira"], door="player")
        pub = ps.public_view(db, wid)
        return {
            "hero": ps.known_dossier(ids["hero"], wid, v, db),
            "shade": ps.known_dossier(ids["shade"], wid, v, db),
            "cabal": ps.known_dossier(ids["cabal"], wid, v, db),
            "vex": ps.known_dossier(ids["vex"], wid, v, db),
            "ordre": ps.known_dossier(ids["ordre"], wid, v, db),
            "factions": ps.known_factions(wid, v, db),
            "tunnel": ps.known_facts_mentioning("tunnel", wid, v, db),
            "tunnel_player": ps.known_facts_mentioning("tunnel", wid, vp, db),
            "self": ps.self_sheet(wid, v, db),
            "skills": ps.known_skills(wid, v, db),
            "public_hero": ps.known_dossier(ids["hero"], wid, pub, db),
            "public_self": ps.self_sheet(wid, pub, db),
        }


def _section(rows: list[dict], section: str) -> list[dict]:
    return [r for r in rows if r["section"] == section]


def rule_cp4(engine, ids: dict) -> int:
    from world_engine.facets import FACETS

    r = _Rule("CP4")
    calls = _cp4_calls(engine, ids)
    f5 = ids["text"]["F5"]
    hero = {(x["label"], x["content"], x["secret"], x["certainty"]) for x in _section(calls["hero"], "facets")}
    r.expect(hero == {
        (FACETS["description"].label, "Hero porte une cape rouge", False, None),
        (FACETS["histoire"].label, "Hero fut affranchi", False, None),
        ("Événement", "Le sacre de Hero", False, None),
        ("Lien", f5, False, None),
    }, f"known_dossier(hero) facets {sorted(hero)!r}")
    hero_m = {x["faction_name"] for x in _section(calls["hero"], "memberships")}
    r.expect(hero_m == {"Guild", "Cabal"}, f"known_dossier(hero) memberships {sorted(hero_m)!r}")
    shade = {x["content"] for x in _section(calls["shade"], "facets")}
    r.expect(shade == {"Shade est une ombre", "Shade creuse un tunnel", "Shade porte un masque", "La fuite de Shade"},
             f"known_dossier(shade) facets {sorted(shade)!r}")
    cabal = {x["member_name"] for x in _section(calls["cabal"], "members")}
    r.expect(cabal == {"Hero", "Mira"}, f"known_dossier(cabal) members {sorted(cabal)!r}")
    r.expect(calls["vex"] == [] and calls["ordre"] == [], "known_dossier(vex) or (ordre) is not []")
    factions = [x["name"] for x in calls["factions"]]
    r.expect(factions == ["Cabal", "Guild", "Guild2"], f"known_factions {factions!r}")

    def mentions(rows):
        return [(x["content"], x["participants"], x["secret"], x["certainty"]) for x in rows]

    tunnel_rumor = ("Le tunnel cache un tresor", [], True, "rumeur")
    tunnel_dig = ("Shade creuse un tunnel", ["Shade"], False, None)
    r.expect(mentions(calls["tunnel"]) == [tunnel_rumor, tunnel_dig],
             f"known_facts_mentioning(tunnel) {mentions(calls['tunnel'])!r}")
    r.expect(mentions(calls["tunnel_player"]) == [tunnel_dig],
             f"known_facts_mentioning(tunnel) at the player's door {mentions(calls['tunnel_player'])!r}")
    met = [(x["name"], x["type"]) for x in _section(calls["self"], "acquaintances")]
    r.expect(met == [("Shade", "character")], f"self_sheet acquaintances {met!r}")
    own = [(x["name"], x["base_domain"], x["system"], x["rank_label"]) for x in _section(calls["self"], "own_skills")]
    r.expect(own == [("agility", "agility", None, "Apprenti"), ("Ombre", "perception", None, "Initié")],
             f"self_sheet own_skills {own!r}")
    skills = [x["name"] for x in calls["skills"]]
    r.expect(skills == ["Ombre"], f"known_skills {skills!r}")
    pub = {x["content"] for x in _section(calls["public_hero"], "facets")}
    r.expect(pub == {ids["text"]["F1"], "Le sacre de Hero", f5}, f"public known_dossier(hero) facets {sorted(pub)!r}")
    pub_m = {x["faction_name"] for x in _section(calls["public_hero"], "memberships")}
    r.expect(pub_m == {"Guild"}, f"public known_dossier(hero) memberships {sorted(pub_m)!r}")
    r.expect(calls["public_self"] == [], "public self_sheet is not []")
    leaked = sorted({k for rows in calls.values() for row in rows for k in row} & pi.FORBIDDEN_KEYS)
    r.expect(not leaked, f"rows hold forbidden keys {leaked!r}")
    return r.reached


def rule_cp5(engine, ids: dict) -> int:
    from world_engine.lore_render import _serialize_rows_by_section

    r = _Rule("CP5")
    calls = _cp4_calls(engine, ids)
    tunnel = _serialize_rows_by_section(tuple(calls["tunnel"]))
    r.expect("« Le tunnel cache un tresor » (certitude : rumeur) [secret]" in tunnel, f"tunnel rows:\n{tunnel}")
    r.expect("« Shade creuse un tunnel » -- Shade\n" in tunnel + "\n", f"tunnel rows:\n{tunnel}")
    sheet = _serialize_rows_by_section(tuple(calls["self"]))
    r.expect("Shade (character)" in sheet, f"self_sheet rows:\n{sheet}")
    r.expect("agility (sans système, agility) : Apprenti" in sheet, f"self_sheet rows:\n{sheet}")
    public = _serialize_rows_by_section(tuple(calls["public_hero"])).splitlines()
    r.expect("- Description : Hero porte une cape rouge" in public, f"public dossier rows:\n{public}")
    return r.reached


def rule_cp6(engine, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine import perspective_selectors as ps
    from world_engine.lore_prompt import RenderSpec
    from world_engine.perspective_audit import withheld, withheld_for
    from world_engine.perspective_query import BindingRefused, PerspectiveResult, execute_perspective_plan
    from world_engine.perspective_render import render_perspective
    from world_engine.perspective_view import character_view

    r = _Rule("CP6")
    wid, text = ids["world"], ids["text"]
    with Session(engine) as db:
        v = character_view(db, wid, ids["mira"], door="creator")
        vp = character_view(db, wid, ids["mira"], door="player")
        pub = ps.public_view(db, wid)
        hero = execute_perspective_plan(pi._plan("known_dossier", mention="Hero"), v, db)
        r.expect(hero.verdict == "answered" and list(hero.rows) == ps.known_dossier(ids["hero"], wid, v, db),
                 f"« Hero » {hero.verdict}")
        vex = execute_perspective_plan(pi._plan("known_dossier", mention="Vex"), v, db)
        r.expect(vex.verdict == "nothing_known", f"« Vex » {vex.verdict}")
        twin_plan = pi._plan("known_dossier", mention="Twin")
        twin = execute_perspective_plan(twin_plan, v, db)
        found = {c["entity_id"] for item in twin.ambiguous for c in item["candidates"]}
        r.expect(twin.verdict == "ambiguous_mention" and found == {ids["twin1"], ids["twin2"]},
                 f"« Twin » {twin.verdict} {sorted(found)}")
        try:
            execute_perspective_plan(twin_plan, v, db, bindings={"m1": ids["twin3"]})
            fail("CP6 a binding to twin3 was accepted")
        except BindingRefused:
            r.reached += 1
        sheet = execute_perspective_plan(pi._plan("self_sheet"), pub, db)
        r.expect(sheet.verdict == "unsupported_selector", f"public self_sheet {sheet.verdict}")

        def audit(plan, view):
            return {(x["reason"], x["subject"], x["content"]) for x in withheld_for(plan, view, db)}

        cases = {
            "Hero": (pi._plan("known_dossier", mention="Hero"), v, {
                ("creator_only", "Hero", "Hero trahira la guilde"), ("false_belief", "Hero", "Hero fut esclave"),
                ("not_known", "Hero", "Hero cache une dague"), ("secret_membership", "Hero", "Guild2 (-)")}),
            "Shade": (pi._plan("known_dossier", mention="Shade"), v, {
                ("stale_version", "Shade", "Shade a ote son masque"), ("membership_unknown", "Shade", "Guild (-)")}),
            "tunnel creator": (pi._plan("known_facts_mentioning", text="tunnel"), v, set()),
            "tunnel player": (pi._plan("known_facts_mentioning", text="tunnel"), vp, {
                ("concealed", "tunnel", "Le tunnel cache un tresor")}),
            "factions": (pi._plan("known_factions"), v, {("entity_unknown", "Ordre", "Ordre")}),
            "Vex": (pi._plan("known_dossier", mention="Vex"), v, {("entity_unknown", "Vex", "Vex")}),
            "skills": (pi._plan("known_skills"), v, {("skill_unknown", "Lame", "Lame")}),
            "public skills": (pi._plan("known_skills"), pub, {
                ("skill_not_visible", "Lame", "Lame"), ("skill_not_visible", "Ombre", "Ombre")}),
        }
        for label, (plan, view, want) in cases.items():
            got = audit(plan, view)
            r.expect(got == want, f"withheld_for {label}: {sorted(got)} != {sorted(want)}")
        public_hero = {(x["reason"], x["subject"], x["content"])
                       for x in withheld(pi._plan("known_dossier", mention="Hero"), wid, db)}
        want = {("not_public", "Hero", text["F2"]), ("creator_only", "Hero", text["F3"]),
                ("faction_not_public", "Hero", "Cabal (-)"), ("secret_membership", "Hero", "Guild2 (-)"),
                ("not_public", "Hero", "Hero cache une dague")}
        r.expect(public_hero == want, f"public withheld « Hero »: {sorted(public_hero)} != {sorted(want)}")
    nothing = PerspectiveResult(verdict="nothing_known", rows=(), ambiguous=(), rejection_reason=None)
    spec = RenderSpec.__new__(RenderSpec)
    prose = render_perspective(nothing, "?", spec, nom="Mira").prose
    r.expect(prose == "Rien de ce que Mira sait ne répond à cette question.", f"render nothing_known {prose!r}")
    return r.reached


TUNNEL_PLAN = {"mentions": [], "calls": [{"selector": "known_facts_mentioning", "args": ["text:tunnel", "$world"]}]}


def _user_text(stub) -> str:
    """Every user message the stub received, joined."""
    return "\n".join(m.get("content", "") for messages in stub.messages for m in messages if m.get("role") == "user")


def rule_cp7(engine, ids: dict) -> int:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine import lore_plan, lore_render, ollama_client
    from world_engine.cockpit.app import app

    r = _Rule("CP7")
    wid, ana, bo, rumor = ids["world"], ids["ana"], ids["bo"], "Le tunnel cache un tresor"
    with Session(engine) as db:
        pr._seed_prompts(db)
    client = TestClient(app, base_url="http://127.0.0.1")
    original_ping = ollama_client.ping
    plan_stub, prose_stub = pr._Stub([TUNNEL_PLAN] * 3), pr._Stub(["Un tunnel."] * 3)
    plan_original, prose_original = pr._swap(lore_plan, plan_stub), pr._swap(lore_render, prose_stub)
    ollama_client.ping = lambda *a, **k: []
    try:
        # (a) the characters
        listed = client.get("/api/lore/perspective/characters", params={"world_id": wid}).json()
        names = [c.get("name") for c in listed] if isinstance(listed, list) else listed
        r.expect(names == ["Lune", "Hero", "Mira", "Shade", "Twin", "Twin", "Twin", "Vex"]
                 and all(set(c) == {"id", "name", "character_type"} for c in listed), f"(a) characters {names!r}")
        # (b) refused before any row
        before = pr._all_events(engine)
        ask = {"question": "?", "world_id": wid}
        for label, body, detail in (
                ("character without id", dict(ask, perspective="character"), "Perspective inconnue."),
                ("public with id", dict(ask, perspective="public", character_id=ids["mira"]), "Perspective inconnue."),
                ("unknown id", dict(ask, perspective="character", character_id="no-such-id"), "Personnage inconnu.")):
            got = client.post("/api/lore/perspective/ask", json=body)
            r.expect(got.status_code == 422 and got.json().get("detail") == detail,
                     f"(b) {label} -> {got.status_code} {got.text[:200]}")
        r.expect(pr._all_events(engine) == before, "(b) a refused perspective was journaled")
        # (c) the creator asks as Mira
        creator = client.post("/api/lore/perspective/ask", json=dict(
            ask, question="Le tunnel ?", perspective="character", character_id=ids["mira"],
            attempt_id=pr._attempt(701)))
        r.expect(creator.status_code == 200 and set(creator.json()) == pr.CREATOR_KEYS,
                 f"(c) creator ask -> {creator.status_code} {creator.text[:200]}")
        prompt = _user_text(prose_stub)
        r.expect(rumor in prompt and "[secret]" in prompt, f"(c) render prompt lacks the secret rumor:\n{prompt}")
        row = pr._one("CP7 (c)", engine, pr._attempt(701), "perspective_ask", "ok", "creator")
        r.expect(row is not None and row.payload.get("perspective") == "character"
                 and row.payload.get("character_id") == ids["mira"], "(c) journal row perspective / character_id")
        # (d) the player's own character
        own = client.get("/api/joueur/personnage", params={"profile_id": ana, "world_id": wid}).json()
        none = client.get("/api/joueur/personnage", params={"profile_id": bo, "world_id": wid}).json()
        r.expect(own == {"character_id": ids["lune"], "name": "Lune"}
                 and none == {"character_id": None, "name": None}, f"(d) {own!r} / {none!r}")
        # (e) Ana asks as Lune
        prose_stub.messages.clear()
        player = client.post("/api/joueur/personnage/savoir/ask", json={
            "profile_id": ana, "world_id": wid, "character_id": ids["lune"], "question": "Le tunnel ?",
            "attempt_id": pr._attempt(702)})
        r.expect(player.status_code == 200 and set(player.json()) == pr.PLAYER_KEYS,
                 f"(e) player ask -> {player.status_code} {player.text[:200]}")
        r.expect(rumor not in _user_text(prose_stub) and rumor not in player.text,
                 "(e) the secret rumor reached the player's render prompt or answer")
        row = pr._one("CP7 (e)", engine, pr._attempt(702), "perspective_ask", "ok", f"player:{ana}")
        audit = {(x["reason"], x["subject"], x["content"]) for x in (row.payload.get("withheld") or [])} if row else set()
        r.expect(row is not None and ("concealed", "tunnel", rumor) in audit
                 and row.payload.get("character_id") == ids["lune"], f"(e) journal withheld {sorted(audit)!r}")
        # (f) Bo with Lune's id
        before = pr._all_events(engine)
        foreign = client.post("/api/joueur/personnage/savoir/ask", json={
            "profile_id": bo, "world_id": wid, "character_id": ids["lune"], "question": "?"})
        r.expect(foreign.status_code == 404 and foreign.json().get("detail") == "Personnage introuvable."
                 and pr._all_events(engine) == before, f"(f) foreign character -> {foreign.status_code}")
        # (g) a binding outside Lune's candidates
        refused = client.post("/api/joueur/personnage/savoir/resolve", json={
            "profile_id": ana, "world_id": wid, "character_id": ids["lune"], "plan": pr.TWIN_PLAN,
            "bindings": {"m1": ids["twin3"]}, "question": "Twin ?", "attempt_id": pr._attempt(703)})
        r.expect(refused.status_code == 422 and refused.json().get("detail") == pr.REFUSED,
                 f"(g) binding to twin3 -> {refused.status_code} {refused.text[:200]}")
        r.expect(pr._one("CP7 (g)", engine, pr._attempt(703), "perspective_resolve", "refused") is not None,
                 "(g) no refused row")
    finally:
        ollama_client.ping = original_ping
        lore_plan.chat = plan_original
        lore_render.chat = prose_original
    return r.reached


def main() -> int:
    engine = pr._fresh_engine()
    try:
        ids = _extend(engine, pi._build_world(engine))
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        print(f"FAIL: fixture raised {type(exc).__name__}: {exc}")
        return 1
    for rule, count, args in ((rule_cp1, 1, ()), (rule_cp2, 7, (engine, ids)), (rule_cp3, 5, (engine, ids)),
                              (rule_cp4, 15, (engine, ids)), (rule_cp5, 5, (engine, ids)),
                              (rule_cp6, 15, (engine, ids)), (rule_cp7, 15, (engine, ids))):
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
    print("PASS: character_perspective -- a character's view holds exactly what he knows, the player's door "
          "drops his secret rows, the character name regime names only his entities, the audit names every "
          "withheld line, and both doors journal every question")
    return 0


if __name__ == "__main__":
    sys.exit(main())
