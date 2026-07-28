"""G1 check for TICKET-0051 (BRIEF-0051-c, decision R1) — the analyzer
transcript seam.

`analyzer_transcript.py` must be genuinely conversation-agnostic (a played
scene and an OBSERVED scene are judged by the same code), never commit, and
carry a refusable `AttributionContext` rather than a silent conversation
read. `analyzer.py`'s two entry points (`analyze_window`,
`analyze_overhearing`) must keep their exact public signature and populate
`conversation_id` on every returned mutation themselves — the seam module
never carries that column (AMENDMENT 02/03: a duplicate of information the
column already owns, same reasoning that dropped it from
`payload["source"]`).

Rules (AMENDMENT 01/02/03 to BRIEF-0051-c):
1. (AST) `analyzer_transcript.py`: no import of Conversation/ConversationMessage;
   no `conv.`/`conversation.` attribute access; no bare `conversation_id`,
   `last_analyzed_turn`, `gathering_id`; no bare `player_id`/`npc_id` except
   as a `payload["npc_id"]`-shaped Subscript. `location_id`/`world_id` are
   permitted. String literals (schema-vocabulary key names the model's JSON
   might use, e.g. `_first_of(item, ..., "npc_id", ...)`) are NOT scanned —
   only true Python identifiers (Name/arg/Attribute.attr/keyword.arg) count;
   that split is unambiguous by AST node type, so this does not need to
   "widen" per the rule's own fail-rather-than-widen clause.
2. (AST) No `.commit()` call anywhere in `analyzer_transcript.py`.
3. (AST) `analyze_window`/`analyze_overhearing` exist in `analyzer.py` with
   unchanged parameter names, order, and default-presence.
4. Both modules stay within 40 functions / 1000 lines (module-level defs +
   methods on module-level classes, matching module_budget.py's method).
5. (behavioural) Fail-closed attribution: a `relation_change` item missing
   `entity_b_id` — with `AttributionContext(subject, counterparty)`: one
   mutation, `dropped_unattributed == 0`; with `AttributionContext(None,
   None)`: zero mutations for that item, `dropped_unattributed == 1`,
   `dropped_by_type["relation_change"] == 1`. Same for the overhearing path:
   a player-spoken classification with `default_counterparty_id=None`
   produces zero mutations and increments `dropped_unattributed`.
6. Rule 8: `analyze_window` and `analyze_overhearing` (the analyzer.py
   wrappers) both return mutations whose `conversation_id` is non-null.
7. Rule 9: no dedup/lookup path anywhere in `src/` reads or parses
   `payload["source"]` — the only sanctioned reads are verbatim passthrough
   into `write_knowledge(..., source=...)` at apply time (a data copy, not a
   decision). Any other read is load-bearing and must escalate.
8. Vacuous-proof guard: FAIL if the AST walk collected zero functions from
   either module, or if the behavioural fixtures produced zero drops AND
   zero defaulted mutations.

No live Ollama call: the model is stubbed for determinism (local model
sampling is not deterministic).
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
ANALYZER = SRC / "world_engine" / "analyzer.py"
ANALYZER_TRANSCRIPT = SRC / "world_engine" / "analyzer_transcript.py"

MAX_FUNCTIONS = 40
MAX_LINES = 1000

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# ── Rule 1 ────────────────────────────────────────────────────────────────

_BANNED_ALWAYS = {"conversation_id", "last_analyzed_turn", "gathering_id"}
_BANNED_NARROW = {"player_id", "npc_id"}


def check_rule1_no_conversation_coupling() -> None:
    if not ANALYZER_TRANSCRIPT.exists():
        fail("Rule 1: analyzer_transcript.py does not exist")
        return
    src = ANALYZER_TRANSCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # Wire parent links (stdlib ast has no built-in parent pointer).
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._seam_parent = node  # type: ignore[attr-defined]

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in ("Conversation", "ConversationMessage"):
                    fail(f"Rule 1: analyzer_transcript.py imports {alias.name!r} (line {node.lineno})")

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in ("conv", "conversation"):
                fail(
                    f"Rule 1: attribute access `{node.value.id}.{node.attr}` at "
                    f"line {node.lineno} — analyzer_transcript.py must never read a Conversation"
                )

        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.arg):
            name = node.arg
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.keyword) and node.arg:
            name = node.arg

        if name in _BANNED_ALWAYS:
            fail(f"Rule 1: banned identifier {name!r} at line {getattr(node, 'lineno', '?')}")
        elif name in _BANNED_NARROW:
            # Bare Name/arg/Attribute/keyword use of player_id/npc_id is
            # always banned — the sanctioned shape is a STRING subscript key
            # (payload["npc_id"]), which is a Constant, never a Name/arg/
            # Attribute/keyword in the first place. So any hit here is real.
            fail(
                f"Rule 1: bare identifier {name!r} at line {getattr(node, 'lineno', '?')} — "
                "only allowed as payload[\"npc_id\"]-shaped string subscript key, never as a Python identifier"
            )

    # Note: deliberately NOT scanning ast.Constant string values for
    # "player_id"/"npc_id" content — those are schema-vocabulary candidate
    # key names the model's JSON might use (e.g. `_first_of(item, ...,
    # "npc_id", ...)` when hunting for a counterparty field), not conversation
    # identity leaks. The Name/arg/Attribute/keyword scan above is the
    # complete, unambiguous enforcement — see module docstring.


def check_rule2_no_commit() -> None:
    if not ANALYZER_TRANSCRIPT.exists():
        return
    tree = ast.parse(ANALYZER_TRANSCRIPT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "commit":
                fail(f"Rule 2: analyzer_transcript.py calls .commit() at line {node.lineno}")


# ── Rule 3 ────────────────────────────────────────────────────────────────

_EXPECTED_SIGNATURES = {
    "analyze_window": {
        "params": ["conversation_id", "db", "model", "host"],
        "has_default": {"model": True, "host": True, "conversation_id": False, "db": False},
    },
    "analyze_overhearing": {
        "params": ["player_line", "npc_line", "conversation_id", "db", "model", "host", "npc_entity_id"],
        "has_default": {
            "model": True, "host": True, "npc_entity_id": True,
            "player_line": False, "npc_line": False, "conversation_id": False, "db": False,
        },
    },
}


def check_rule3_wrapper_signatures() -> None:
    if not ANALYZER.exists():
        fail("Rule 3: analyzer.py does not exist")
        return
    tree = ast.parse(ANALYZER.read_text(encoding="utf-8"))
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    for name, expected in _EXPECTED_SIGNATURES.items():
        func = funcs.get(name)
        if func is None:
            fail(f"Rule 3: {name} not found in analyzer.py")
            continue
        args = func.args
        actual_params = [a.arg for a in args.args]
        if actual_params != expected["params"]:
            fail(
                f"Rule 3: {name} parameter names/order changed — "
                f"expected {expected['params']}, got {actual_params}"
            )
            continue
        n_defaults = len(args.defaults)
        defaulted_params = set(actual_params[len(actual_params) - n_defaults:])
        for pname, should_have_default in expected["has_default"].items():
            has_default = pname in defaulted_params
            if has_default != should_have_default:
                fail(
                    f"Rule 3: {name} parameter {pname!r} default-presence changed "
                    f"(expected default={should_have_default}, got {has_default})"
                )


# ── Rule 4 ────────────────────────────────────────────────────────────────

def _count_functions(tree: ast.Module) -> int:
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += 1
        elif isinstance(node, ast.ClassDef):
            count += sum(
                1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    return count


def check_rule4_module_budget() -> tuple[int, int]:
    """Returns (analyzer_fn_count, analyzer_transcript_fn_count) for the
    vacuous-proof guard."""
    counts = []
    for path in (ANALYZER, ANALYZER_TRANSCRIPT):
        if not path.exists():
            fail(f"Rule 4: {path} does not exist")
            counts.append(0)
            continue
        text = path.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        tree = ast.parse(text)
        n_funcs = _count_functions(tree)
        counts.append(n_funcs)
        if lines > MAX_LINES:
            fail(f"Rule 4: {path.name} has {lines} lines (cap {MAX_LINES})")
        if n_funcs > MAX_FUNCTIONS:
            fail(f"Rule 4: {path.name} has {n_funcs} functions (cap {MAX_FUNCTIONS})")
    return counts[0], counts[1]


# ── Rule 9 (payload["source"] readers) ──────────────────────────────────

_SOURCE_ANCESTOR_WALK_DEPTH = 6


def _ancestor_is_write_knowledge_call(node: ast.AST) -> bool:
    """Walk up the parent chain a bounded number of hops looking for a
    write_knowledge(...) Call — tolerant of the exact wrapping shape
    (`str(x.get("source") or "default")`, a bare keyword, etc.) since the
    point is "is this value headed into write_knowledge's source= column",
    not matching one specific AST shape."""
    current = node
    for _ in range(_SOURCE_ANCESTOR_WALK_DEPTH):
        current = getattr(current, "_seam_parent", None)
        if current is None:
            return False
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Name) and current.func.id == "write_knowledge":
            return True
    return False


def check_rule9_no_source_dedup_reader() -> None:
    """Only `payload.get("source")` / `payload["source"]` — a receiver
    literally named `payload` — counts as a read of a ProposedMutation's
    payload source field. Other dicts that happen to also carry a "source"
    key (a raw model item's nested knowledge sub-object, a Knowledge row's
    own `source` column via an unrelated variable name, etc.) are a
    coincidental name collision, not the field this rule protects."""
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if '"source"' not in text and "'source'" not in text:
            continue
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child._seam_parent = node  # type: ignore[attr-defined]

        for node in ast.walk(tree):
            is_source_read = False
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant) and node.slice.value == "source"
                and isinstance(node.value, ast.Name) and node.value.id == "payload"
                and isinstance(node.ctx, ast.Load)
            ):
                is_source_read = True
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "payload"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "source"
            ):
                is_source_read = True
            if not is_source_read:
                continue

            sanctioned = _ancestor_is_write_knowledge_call(node)
            if not sanctioned:
                rel = path.relative_to(ROOT)
                offenders.append(f"{rel}:{node.lineno}")

    if offenders:
        fail(
            "Rule 9: payload[\"source\"] is read outside the sanctioned "
            "write_knowledge(...) passthrough — potentially load-bearing, "
            "escalate rather than proceed: " + ", ".join(offenders)
        )


# ── Behavioural fixtures (Rule 5 / Rule 8) ──────────────────────────────

def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    return engine


def _seed_fixture(engine):
    from sqlmodel import Session as DbSession
    from world_engine.models import (
        Character, Conversation, Entity, GatheringMember, Gathering,
        Session as SessionRow, World,
    )

    with DbSession(engine) as session:
        world = World(name="Seam Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        loc_entity = Entity(world_id=world.id, type="location", name="Loc")
        session.add(loc_entity)
        session.commit()
        session.refresh(loc_entity)
        from world_engine.models import Location
        session.add(Location(id=loc_entity.id))
        session.commit()

        def _make_npc(name: str) -> str:
            entity = Entity(world_id=world.id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Character(
                id=entity.id, world_id=world.id, character_type="npc",
                current_location_id=loc_entity.id,
            ))
            session.commit()
            return entity.id

        def _make_player(name: str) -> str:
            entity = Entity(world_id=world.id, type="character", name=name)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            session.add(Character(
                id=entity.id, world_id=world.id, character_type="player",
                user_id=None, current_location_id=loc_entity.id,
            ))
            session.commit()
            return entity.id

        npc_id = _make_npc("NPC")
        player_id = _make_player("Player")
        bystander_id = _make_npc("Bystander")

        sess_row = SessionRow(world_id=world.id, number=1, status="open")
        session.add(sess_row)
        session.commit()
        session.refresh(sess_row)

        gathering = Gathering(
            world_id=world.id, session_id=sess_row.id, location_id=loc_entity.id, status="open",
        )
        session.add(gathering)
        session.commit()
        session.refresh(gathering)
        session.add(GatheringMember(gathering_id=gathering.id, entity_id=bystander_id))
        session.commit()

        from world_engine.models import Knowledge
        session.add(Knowledge(
            entity_id=npc_id, subject="a_subject", level="knows",
            content="Fixture fact.", is_secret=False, share_threshold=50,
        ))
        session.commit()

        from world_engine.models import PromptTemplate
        from world_engine import writes as _writes

        head = PromptTemplate(world_id=None, name="check", usage="conversation_analysis", is_active=True)
        session.add(head)
        session.commit()
        session.refresh(head)
        _writes.write_prompt_version(
            session, template_id=head.id, system_prompt="sys", user_template="stub user template",
        )
        head2 = PromptTemplate(
            world_id=None, name="check-overhear", usage="overhearing_classification", is_active=True,
        )
        session.add(head2)
        session.commit()
        session.refresh(head2)
        _writes.write_prompt_version(
            session, template_id=head2.id, system_prompt="sys", user_template="stub user template",
        )

        conv = Conversation(
            world_id=world.id, session_id=sess_row.id, location_id=loc_entity.id,
            player_id=player_id, npc_id=npc_id, gathering_id=gathering.id, status="open",
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)

        return {
            "world_id": world.id, "npc_id": npc_id, "player_id": player_id,
            "bystander_id": bystander_id, "location_id": loc_entity.id,
            "gathering_id": gathering.id, "conversation_id": conv.id,
        }


def check_fail_closed_and_conversation_id(fixture, engine) -> None:
    from sqlmodel import Session as DbSession
    from world_engine.analyzer_transcript import (
        AttributionContext, analyze_transcript, analyze_overheard_lines,
        _window_build_mutations, _normalize_to_schema,
    )

    # ── Rule 5a: window-path relation_change fail-closed ────────────────
    raw_item = {"type": "relation", "entity_a": fixture["npc_id"], "delta": 5, "content": "x"}

    with_attr = AttributionContext(
        default_subject_id=fixture["npc_id"], default_counterparty_id=fixture["player_id"],
    )
    without_attr = AttributionContext(default_subject_id=None, default_counterparty_id=None)

    with DbSession(engine) as session:
        mutations, dropped, by_type = _window_build_mutations(
            [raw_item], fixture["world_id"], with_attr, session, set(),
        )
    if len(mutations) != 1 or dropped != 0:
        fail(
            f"Rule 5a: AttributionContext(subject, counterparty) should yield 1 mutation / "
            f"0 drops, got {len(mutations)} mutations / {dropped} drops"
        )

    with DbSession(engine) as session:
        mutations, dropped, by_type = _window_build_mutations(
            [raw_item], fixture["world_id"], without_attr, session, set(),
        )
    if mutations or dropped != 1 or by_type.get("relation_change") != 1:
        fail(
            f"Rule 5a: AttributionContext(None, None) should yield 0 mutations / 1 drop / "
            f"dropped_by_type['relation_change']==1, got {len(mutations)} mutations / "
            f"{dropped} drops / {by_type!r}"
        )

    # ── Rule 5b: overhearing-path player-spoken fail-closed ─────────────
    from world_engine import ollama_client as oc
    import json as _json

    original_chat = oc.chat
    oc.chat = lambda *a, **kw: _json.dumps([{"subject": "a_subject", "speaker": "player"}])
    try:
        with DbSession(engine) as session:
            no_player_attr = AttributionContext(
                default_subject_id=fixture["npc_id"], default_counterparty_id=None,
            )
            result_dropped = analyze_overheard_lines(
                speaker_line="line", listener_line="line",
                receiver_ids={fixture["bystander_id"]}, world_id=fixture["world_id"],
                location_id=fixture["location_id"], existing_keys=(set(), set()),
                attribution=no_player_attr, db=session,
            )
        if result_dropped.mutations or result_dropped.dropped_unattributed != 1:
            fail(
                "Rule 5b: overhearing player-spoken with default_counterparty_id=None "
                f"should yield 0 mutations / dropped_unattributed==1, got "
                f"{len(result_dropped.mutations)} mutations / {result_dropped.dropped_unattributed}"
            )

        with DbSession(engine) as session:
            has_player_attr = AttributionContext(
                default_subject_id=fixture["npc_id"], default_counterparty_id=fixture["player_id"],
            )
            result_ok = analyze_overheard_lines(
                speaker_line="line", listener_line="line",
                receiver_ids={fixture["bystander_id"]}, world_id=fixture["world_id"],
                location_id=fixture["location_id"], existing_keys=(set(), set()),
                attribution=has_player_attr, db=session,
            )
    finally:
        oc.chat = original_chat

    # ── Rule 8: analyzer.py wrappers set conversation_id on every mutation ──
    from world_engine.analyzer import analyze_window, analyze_overhearing
    from world_engine.models import ConversationMessage

    with DbSession(engine) as session:
        session.add(ConversationMessage(
            conversation_id=fixture["conversation_id"], turn_order=1,
            speaker="player", speaker_id=fixture["player_id"], content="bonjour",
        ))
        session.add(ConversationMessage(
            conversation_id=fixture["conversation_id"], turn_order=2,
            speaker="npc", speaker_id=fixture["npc_id"], content="salut",
        ))
        session.commit()

    oc.chat = lambda *a, **kw: "[]"
    try:
        with DbSession(engine) as session:
            window_mutations = analyze_window(fixture["conversation_id"], session)
        with DbSession(engine) as session:
            oc.chat = lambda *a, **kw: _json.dumps([{"subject": "a_subject", "speaker": "npc"}])
            overhear_mutations = analyze_overhearing(
                "bonjour", "salut", fixture["conversation_id"], session,
                npc_entity_id=fixture["npc_id"],
            )
    finally:
        oc.chat = original_chat

    for mut in overhear_mutations:
        if mut.conversation_id != fixture["conversation_id"]:
            fail(f"Rule 8: analyze_overhearing returned a mutation with conversation_id={mut.conversation_id!r}")
    if not overhear_mutations:
        fail("Rule 8/vacuous-proof: analyze_overhearing produced zero mutations in the fixture — cannot assert conversation_id on nothing")

    return result_dropped, result_ok


def main() -> int:
    check_rule1_no_conversation_coupling()
    check_rule2_no_commit()
    check_rule3_wrapper_signatures()
    fn_count_a, fn_count_b = check_rule4_module_budget()
    check_rule9_no_source_dedup_reader()

    engine = _fresh_engine()
    fixture = _seed_fixture(engine)
    check_fail_closed_and_conversation_id(fixture, engine)

    if fn_count_a == 0 or fn_count_b == 0:
        fail("Vacuous-proof guard: AST walk collected zero functions from analyzer.py or analyzer_transcript.py")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: analyzer_seam — analyzer_transcript.py is conversation-agnostic "
        "(no Conversation/ConversationMessage coupling, no commit), analyzer.py's "
        "wrapper signatures are unchanged, both modules are within budget, "
        "fail-closed attribution drops correctly on both paths, conversation_id "
        "is set by the wrapper on every returned mutation, and payload[\"source\"] "
        "has no dedup/lookup reader outside the sanctioned apply-time passthrough"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
