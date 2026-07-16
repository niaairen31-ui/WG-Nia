"""Disposable record/replay harness for the authoring paths (BRIEF-0027-e,
extended BRIEF-0028-d).

Proves the `llm_parse.py` chokepoint migration (entity_author.py,
region_author.py) is behavior-preserving, and — since BRIEF-0028-d — proves
the entity_author -> event_author extraction and the in-place decomposition
of `generate_entity_draft`/`generate_event_draft`/`generate_player_draft`
are behavior-preserving too. Disposable: deleted at TICKET-0028 stage f
along with the transition baselines it exists to protect (sibling of
`harness_say_replay.py`/`harness_mutation_apply.py`/`harness_tick_replay.py`,
same DB-copy discipline — never the live DB). `print` is fine here — this
script lives in scripts/, never in src/.

Every traversed function (`generate_entity_draft`, `generate_region_manifest`,
`generate_region_draft`, `generate_npc_goals`, `generate_event_draft`,
`generate_agenda_draft`, `generate_player_draft` — `generate_world_draft`
and `generate_skill_catalogue_draft` stay untraversed, out of scope per
BRIEF-0028-d Scope OUT) is pure generate-and-return: none write canon
anywhere in their call path, so there is nothing to dump from the DB —
only the returned dict(s) matter.

Record mode runs, against a REAL Ollama model on a disposable copy of the
live DB:
  - one `generate_entity_draft` call (entity-author)
  - one `generate_region_manifest` + `generate_region_draft` pair
    (region-author, which transitively exercises `generate_entity_draft`
    and `generate_npc_goals` per faction/location/NPC)
  - one `generate_player_draft` call
  - one `generate_agenda_draft` call (faction owner, public fields only —
    mirrors `cockpit/routes/creator.py:generate_agenda`)
  - one `generate_event_draft` call (location pre-selected via
    `build_world_roster` — mirrors `cockpit/routes/creator.py:generate_event`)
Captures every Ollama request/response pair (by monkeypatching
`ollama_client.chat`) and the returned dict(s), plus a manifest of every
function name actually invoked (including the two transitively exercised
by the region pipeline). Record refuses to write fixtures if the manifest
does not cover `REQUIRED_MANIFEST_FUNCTIONS` (vacuous-proof rule).

Replay mode: restores the exact DB snapshot the record run started from,
then re-runs the same calls with the recorded model responses played back
instead of calling Ollama. Refuses PASS if the recorded manifest does not
cover `REQUIRED_MANIFEST_FUNCTIONS`. Diffs the returned dict(s) against the
recorded fixtures. Empty diff on every fixture + full manifest coverage =
PASS.

Usage:
    python scripts/harness_entity_author_replay.py record
    python scripts/harness_entity_author_replay.py replay
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "harness_entity_author_fixtures"
WORKDB_PATH = FIXTURE_DIR / "workdb.sqlite"
PRESTATE_PATH = FIXTURE_DIR / "pre_state.sqlite"
ENTITY_CALLS_PATH = FIXTURE_DIR / "entity_calls.json"
ENTITY_RESULT_PATH = FIXTURE_DIR / "entity_result.json"
REGION_CALLS_PATH = FIXTURE_DIR / "region_calls.json"
REGION_RESULT_PATH = FIXTURE_DIR / "region_result.json"
PLAYER_CALLS_PATH = FIXTURE_DIR / "player_calls.json"
PLAYER_RESULT_PATH = FIXTURE_DIR / "player_result.json"
AGENDA_CALLS_PATH = FIXTURE_DIR / "agenda_calls.json"
AGENDA_RESULT_PATH = FIXTURE_DIR / "agenda_result.json"
EVENT_CALLS_PATH = FIXTURE_DIR / "event_calls.json"
EVENT_RESULT_PATH = FIXTURE_DIR / "event_result.json"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

LIVE_DB_PATH = Path.home() / ".world_engine" / "world_engine.db"

ENTITY_BRIEF = (
    "Un forgeron itinérant, taciturne, qui répare des reliques anciennes "
    "contre des faveurs plutôt que de l'argent."
)
REGION_BRIEF = (
    "Un hameau de pêcheurs isolé sur une côte rocheuse, tiraillé entre une "
    "guilde de pêcheurs traditionaliste et une petite loge de contrebandiers."
)
PLAYER_BRIEF = (
    "Une ancienne cartographe reconvertie en exploratrice, en quête de "
    "ruines oubliées le long de la côte."
)
# Fixture anchors — both rows exist in the pilot Verkhaal world seed and are
# active/public, so the derived context is stable across record and replay.
AGENDA_OWNER_NAME = "La Garde de Verkhaal"
AGENDA_BRIEF = (
    "Réaffirmer le contrôle de la garde sur les quais après une vague de "
    "contrebande récente."
)
EVENT_LOCATION_NAME = "Le Dernier Verre"
EVENT_BRIEF = (
    "Une rixe éclate entre deux voyageurs au comptoir et dégénère en "
    "esclandre général."
)

# Vacuous-proof rule (TICKET-0028 D1 precedent): replay refuses PASS unless
# the recorded manifest names every one of these — including the two only
# ever exercised transitively, inside `generate_region_draft`.
REQUIRED_MANIFEST_FUNCTIONS = frozenset(
    {
        "generate_entity_draft",
        "generate_region_manifest",
        "generate_region_draft",
        "generate_npc_goals",
        "generate_event_draft",
        "generate_agenda_draft",
        "generate_player_draft",
    }
)


def _sqlite_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()


def _prepare_workdb(mode: str) -> None:
    if mode == "record":
        if not LIVE_DB_PATH.exists():
            raise SystemExit(f"Live DB not found at {LIVE_DB_PATH}")
        _sqlite_copy(LIVE_DB_PATH, WORKDB_PATH)
        _sqlite_copy(LIVE_DB_PATH, PRESTATE_PATH)
    else:
        if not PRESTATE_PATH.exists():
            raise SystemExit(
                f"No recorded pre-state at {PRESTATE_PATH} — run `record` first."
            )
        _sqlite_copy(PRESTATE_PATH, WORKDB_PATH)


def _install_record_wrapper(modules: list, calls: list[dict], real_chat):
    """`entity_author.py`/`region_author.py` do `from .ollama_client import
    chat` — a direct name import, not a module-attribute lookup — so
    patching `ollama_client.chat` alone doesn't intercept their calls.
    Patch the imported name on each caller module instead. `real_chat` is
    always the pristine, never-wrapped function — callers must not chain
    wrappers by reusing an already-patched module's `.chat`."""

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        kwargs = {"timeout": timeout, "format": format, "options": options}
        if model is not None:
            kwargs["model"] = model
        if host is not None:
            kwargs["host"] = host
        result = real_chat(messages, **kwargs)
        calls.append({
            "model": model, "format": format, "options": options,
            "messages": messages, "response": result,
        })
        return result

    for mod in modules:
        mod.chat = chat


def _install_replay_wrapper(modules: list, queue: list[dict], mismatches: list[dict]) -> None:
    state = {"i": 0}

    def chat(messages, model=None, host=None, timeout=300.0, format=None, options=None):
        entry = queue[state["i"]]
        state["i"] += 1
        if entry["messages"] != messages or entry["model"] != model or entry["options"] != options:
            mismatches.append({"index": state["i"] - 1})
        return entry["response"]

    for mod in modules:
        mod.chat = chat


def _install_manifest_wrapper(module, func_name: str, manifest: set[str]) -> None:
    """Records `func_name` as traversed at the moment it actually fires.

    Needed only for functions never called directly by this script — today
    just `generate_npc_goals`, invoked exclusively from inside
    `generate_region_draft`. Same direct-name-import caveat as `chat` (see
    `_install_record_wrapper`): patches the name on `module`'s own
    namespace, since that's the binding the caller's code actually looks up
    at call time, not the origin module's attribute.
    """
    original = getattr(module, func_name)

    def wrapper(*args, **kwargs):
        manifest.add(func_name)
        return original(*args, **kwargs)

    setattr(module, func_name, wrapper)


def _agenda_owner_fields(db, entity_name: str) -> tuple[str, str, str]:
    """Mirrors `cockpit/routes/creator.py:generate_agenda`'s owner_kind /
    owner_context derivation for a `faction` owner — public fields only
    (`Entity.description` + `Faction.philosophy`), same as the live route."""
    from sqlmodel import select
    from world_engine.models import Entity, Faction

    owner = db.exec(select(Entity).where(Entity.name == entity_name)).first()
    if owner is None:
        raise SystemExit(f"Fixture agenda owner {entity_name!r} not found in the DB")
    faction = db.get(Faction, owner.id)
    philosophy = (
        f"Philosophie : {faction.philosophy}" if faction and faction.philosophy else None
    )
    parts = [p for p in (owner.description, philosophy) if p]
    owner_context = "\n".join(parts) if parts else "(aucune description)"
    return "faction", owner.name, owner_context


def _event_inputs(db, location_name: str) -> tuple[str, str, dict[str, str]]:
    """Mirrors `cockpit/routes/creator.py:generate_event`'s location_hint /
    location_context / roster derivation — location's name + description
    only, roster from `build_world_roster` (public-only, filtered in SQL)."""
    from sqlmodel import select
    from world_engine.entity_author import _world_id
    from world_engine.event_author import build_world_roster
    from world_engine.models import Entity

    location = db.exec(select(Entity).where(Entity.name == location_name)).first()
    if location is None:
        raise SystemExit(f"Fixture event location {location_name!r} not found in the DB")
    parts = [p for p in (location.name, location.description) if p]
    location_context = "\n".join(parts)
    roster = build_world_roster(db, _world_id(db))
    return location.name, location_context, roster


def _run_record() -> None:
    from sqlmodel import Session
    from world_engine import entity_author, event_author, region_author
    from world_engine.db import engine
    from world_engine.entity_author import generate_entity_draft, generate_player_draft
    from world_engine.event_author import generate_agenda_draft, generate_event_draft
    from world_engine.ollama_client import chat as pristine_chat
    from world_engine.region_author import generate_region_draft, generate_region_manifest

    manifest: set[str] = set()

    entity_calls: list[dict] = []
    _install_record_wrapper([entity_author], entity_calls, pristine_chat)
    with Session(engine) as db:
        entity_result = generate_entity_draft("character", ENTITY_BRIEF, db)
    manifest.add("generate_entity_draft")

    region_calls: list[dict] = []
    _install_record_wrapper([entity_author, region_author], region_calls, pristine_chat)
    _install_manifest_wrapper(region_author, "generate_npc_goals", manifest)
    with Session(engine) as db:
        manifest_result = generate_region_manifest(REGION_BRIEF, db)
        manifest.add("generate_region_manifest")
        if not manifest_result.get("ok"):
            raise SystemExit(f"generate_region_manifest failed: {manifest_result.get('error')}")
        region_result = generate_region_draft(manifest_result["manifest"], db)
        manifest.add("generate_region_draft")

    player_calls: list[dict] = []
    _install_record_wrapper([entity_author], player_calls, pristine_chat)
    with Session(engine) as db:
        player_result = generate_player_draft(PLAYER_BRIEF, db)
    manifest.add("generate_player_draft")

    agenda_calls: list[dict] = []
    _install_record_wrapper([event_author], agenda_calls, pristine_chat)
    with Session(engine) as db:
        owner_kind, owner_name, owner_context = _agenda_owner_fields(db, AGENDA_OWNER_NAME)
        agenda_result = generate_agenda_draft(owner_kind, owner_name, owner_context, AGENDA_BRIEF, db)
    manifest.add("generate_agenda_draft")

    event_calls: list[dict] = []
    _install_record_wrapper([event_author], event_calls, pristine_chat)
    with Session(engine) as db:
        location_hint, location_context, roster = _event_inputs(db, EVENT_LOCATION_NAME)
        event_result = generate_event_draft(EVENT_BRIEF, location_hint, location_context, roster, db)
    manifest.add("generate_event_draft")

    missing = REQUIRED_MANIFEST_FUNCTIONS - manifest
    if missing:
        raise SystemExit(
            f"RECORD refused: manifest missing required function(s) {sorted(missing)} — "
            "nothing written (vacuous-proof rule)"
        )

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    ENTITY_CALLS_PATH.write_text(json.dumps(entity_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    ENTITY_RESULT_PATH.write_text(json.dumps(entity_result, ensure_ascii=False, indent=2), encoding="utf-8")
    REGION_CALLS_PATH.write_text(json.dumps(region_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    REGION_RESULT_PATH.write_text(
        json.dumps({"manifest": manifest_result, "draft": region_result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    PLAYER_CALLS_PATH.write_text(json.dumps(player_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    PLAYER_RESULT_PATH.write_text(json.dumps(player_result, ensure_ascii=False, indent=2), encoding="utf-8")
    AGENDA_CALLS_PATH.write_text(json.dumps(agenda_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    AGENDA_RESULT_PATH.write_text(json.dumps(agenda_result, ensure_ascii=False, indent=2), encoding="utf-8")
    EVENT_CALLS_PATH.write_text(json.dumps(event_calls, ensure_ascii=False, indent=2), encoding="utf-8")
    EVENT_RESULT_PATH.write_text(json.dumps(event_result, ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST_PATH.write_text(
        json.dumps(sorted(manifest), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"RECORD: entity-author ({len(entity_calls)} Ollama calls), "
        f"region-author ({len(region_calls)} Ollama calls), "
        f"player-author ({len(player_calls)} Ollama calls), "
        f"agenda-author ({len(agenda_calls)} Ollama calls), "
        f"event-author ({len(event_calls)} Ollama calls) captured to {FIXTURE_DIR}; "
        f"manifest covers {sorted(manifest)}"
    )


def _run_replay() -> bool:
    from sqlmodel import Session
    from world_engine import entity_author, event_author, region_author
    from world_engine.db import engine
    from world_engine.entity_author import generate_entity_draft, generate_player_draft
    from world_engine.event_author import generate_agenda_draft, generate_event_draft
    from world_engine.region_author import generate_region_draft, generate_region_manifest

    ok = True

    if not MANIFEST_PATH.exists():
        raise SystemExit(f"No recorded manifest at {MANIFEST_PATH} — run `record` first.")
    recorded_manifest = set(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
    missing = REQUIRED_MANIFEST_FUNCTIONS - recorded_manifest
    if missing:
        raise SystemExit(
            f"REPLAY refused: recorded manifest missing required function(s) "
            f"{sorted(missing)} — re-run `record` (vacuous-proof rule)"
        )

    entity_calls = json.loads(ENTITY_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_entity_result = json.loads(ENTITY_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches: list[dict] = []
    _install_replay_wrapper([entity_author], entity_calls, mismatches)
    with Session(engine) as db:
        entity_result = generate_entity_draft("character", ENTITY_BRIEF, db)
    if mismatches:
        print(f"WARN: entity-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    if entity_result != recorded_entity_result:
        ok = False
        print("FAIL: entity-author result diverged")
        print(f"  recorded: {recorded_entity_result!r}")
        print(f"  replayed: {entity_result!r}")

    region_calls = json.loads(REGION_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_region_result = json.loads(REGION_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches = []
    _install_replay_wrapper([entity_author, region_author], region_calls, mismatches)
    with Session(engine) as db:
        manifest_result = generate_region_manifest(REGION_BRIEF, db)
        region_result = (
            generate_region_draft(manifest_result["manifest"], db)
            if manifest_result.get("ok")
            else None
        )
    if mismatches:
        print(f"WARN: region-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    replayed_region = {"manifest": manifest_result, "draft": region_result}
    if replayed_region != recorded_region_result:
        ok = False
        print("FAIL: region-author result diverged")
        print(f"  recorded: {recorded_region_result!r}")
        print(f"  replayed: {replayed_region!r}")

    player_calls = json.loads(PLAYER_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_player_result = json.loads(PLAYER_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches = []
    _install_replay_wrapper([entity_author], player_calls, mismatches)
    with Session(engine) as db:
        player_result = generate_player_draft(PLAYER_BRIEF, db)
    if mismatches:
        print(f"WARN: player-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    if player_result != recorded_player_result:
        ok = False
        print("FAIL: player-author result diverged")
        print(f"  recorded: {recorded_player_result!r}")
        print(f"  replayed: {player_result!r}")

    agenda_calls = json.loads(AGENDA_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_agenda_result = json.loads(AGENDA_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches = []
    _install_replay_wrapper([event_author], agenda_calls, mismatches)
    with Session(engine) as db:
        owner_kind, owner_name, owner_context = _agenda_owner_fields(db, AGENDA_OWNER_NAME)
        agenda_result = generate_agenda_draft(owner_kind, owner_name, owner_context, AGENDA_BRIEF, db)
    if mismatches:
        print(f"WARN: agenda-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    if agenda_result != recorded_agenda_result:
        ok = False
        print("FAIL: agenda-author result diverged")
        print(f"  recorded: {recorded_agenda_result!r}")
        print(f"  replayed: {agenda_result!r}")

    event_calls = json.loads(EVENT_CALLS_PATH.read_text(encoding="utf-8"))
    recorded_event_result = json.loads(EVENT_RESULT_PATH.read_text(encoding="utf-8"))
    mismatches = []
    _install_replay_wrapper([event_author], event_calls, mismatches)
    with Session(engine) as db:
        location_hint, location_context, roster = _event_inputs(db, EVENT_LOCATION_NAME)
        event_result = generate_event_draft(EVENT_BRIEF, location_hint, location_context, roster, db)
    if mismatches:
        print(f"WARN: event-author: {len(mismatches)} Ollama request(s) drifted from the recording")
    if event_result != recorded_event_result:
        ok = False
        print("FAIL: event-author result diverged")
        print(f"  recorded: {recorded_event_result!r}")
        print(f"  replayed: {event_result!r}")

    print(
        "REPLAY: PASS — entity, region, player, agenda, event outputs all match the "
        "recording; manifest covers " + str(sorted(recorded_manifest))
        if ok else "REPLAY: FAIL — see diffs above"
    )
    return ok


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("record", "replay"):
        raise SystemExit(__doc__)
    mode = sys.argv[1]
    _prepare_workdb(mode)
    # Point the engine at the disposable copy BEFORE any world_engine import,
    # so db.py binds to it instead of the live DB.
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{WORKDB_PATH}"

    if mode == "record":
        _run_record()
    else:
        if not _run_replay():
            raise SystemExit(1)


if __name__ == "__main__":
    main()
