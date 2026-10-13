"""G1 check for TICKET-0115 -- every review of a proposal is recorded: its round, what the creator changed, and what a step's condition said.

BRIEF-0115-B's rules (A3, C1 and H1a of the conditions series' dashboard).

RD1 -- the diff (pure). `review_diff.diff_payloads` on the cases of
   `DIFF_CASES` returns exactly the expected `(path, field, kind, before,
   after)` rows: an empty value equals an absent key; `type_name` and an
   apply's `applied_changes` are never compared; participants pair by role
   name (a role id added by the card is a change of that key only), a
   retyped participant's entity is one `changed`, a list of plain values is
   a set, `steps` pair by position, a second element of one role is
   `[role#2]`, a nested object is walked, a boolean is not an integer.
RD2 -- an edited approve (route functions, a fixture world). A
   `relation_change` approved with its delta changed from 5 to 9 is applied;
   it holds one `mutation_review` (round 1, approve, unit, applied, edited)
   and one change (`intensity_delta`, changed, `5` -> `9`), and its
   `original_payload` is the producer's payload. Approved unchanged, another
   holds round 1 not edited, no change, `original_payload` NULL.
RD3 -- rounds. A `relation_change` naming no `entity_b_id`, approved with
   its delta changed from 5 to 6, fails to apply (round 1: approve, unit,
   approved, edited, one change); approved again with the entity added it
   applies (round 2, edited, one change `entity_b_id` added -- compared to
   what round 1 stored), and `original_payload` is still the producer's
   payload, delta 5. A unit reject, a batch reject and a batch approve each
   write one round with their `via`, never edited, never a change. An
   auto-apply (`_approve_apply_and_commit` with no `ReviewCall`, the path
   of INV-15's `skill_progress`) applies and writes no round.
RD4 -- a step's verdict (C1). Rejecting an `agenda_step_change` records
   `met` when the step's completion is met (the character holds 10, the
   leaf asks 5), `unmet` when it is not, `none`
   when the step has no completion, `none` for `fail` on a step with no
   failure condition, `not_judged` for a faction's agenda and for an unknown
   step; any other type records NULL.
RD5 -- the paths (AST of `cockpit/routes/mutations.py`). `reject_mutation`,
   `approve_mutation`, `_batch_approve` and `_batch_reject` each build their
   `ReviewCall` with `step_verdict(...)` BEFORE they apply or change the
   status: in `approve_mutation` the `ReviewCall(` comes after
   `_approve_apply_edited_payload(` and before
   `_approve_apply_and_commit(`; `record_review(` is called exactly eight (one per status a path leaves)
   times in the module, never outside those functions and the two approve
   helpers.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROUTES = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "mutations.py"

FAILURES: list[str] = []

P1 = {"role_id": "r1", "role": "Chasseur", "entity_id": "e1", "sorte_id": None, "secret": None}
DIFF_CASES: tuple[tuple[str, dict, dict, list], ...] = (
    ("empty equals absent", {"title": "a"}, {"title": "a", "description": None, "scopes": [], "x": ""}, []),
    ("type_name and applied_changes ignored", {"type_id": "t", "type_name": "A"},
     {"type_id": "t", "type_name": "B", "applied_changes": [{"a": 1}]}, []),
    ("a role id added", {"participants": [{"role": "Chasseur", "entity_id": "e1"}]},
     {"participants": [P1]},
     [("participants[Chasseur].role_id", "participants[].role_id", "added", None, '"r1"')]),
    ("a participant's entity", {"participants": [P1]}, {"participants": [dict(P1, entity_id="e2")]},
     [("participants[Chasseur].entity_id", "participants[].entity_id", "changed", '"e1"', '"e2"')]),
    ("a second participant of one role", {"participants": [P1]},
     {"participants": [P1, dict(P1, entity_id="e3")]},
     [("participants[Chasseur#2]", "participants[]", "added", None, None)]),
    ("a set of plain values", {"involved_entities": ["a", "b"]}, {"involved_entities": ["b", "c"]},
     [('involved_entities["a"]', "involved_entities[]", "removed", '"a"', None),
      ('involved_entities["c"]', "involved_entities[]", "added", None, '"c"')]),
    ("steps by position", {"steps": ["x", "y"]}, {"steps": ["x", "z", "w"]},
     [("steps[2]", "steps[]", "changed", '"y"', '"z"'), ("steps[3]", "steps[]", "added", None, '"w"')]),
    ("a type changed, a nested object", {"type_id": "t1", "new_type": {"name": "A", "roles": [{"name": "R"}]}},
     {"type_id": "t2", "new_type": {"name": "B", "roles": [{"name": "R"}]}},
     [("new_type.name", "new_type.name", "changed", '"A"', '"B"'),
      ("type_id", "type_id", "changed", '"t1"', '"t2"')]),
    ("a boolean is not an integer", {"secret": 1}, {"secret": True},
     [("secret", "secret", "changed", "1", "true")]),
    ("a state change by entity and state",
     {"state_changes": [{"entity_id": "e", "attribute": "a", "mode": "set", "value": "x"}]},
     {"state_changes": [{"entity_id": "e", "attribute": "a", "mode": "set", "value": "y"}]},
     [("state_changes[e|a].value", "state_changes[].value", "changed", '"x"', '"y"')]),
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


# --- RD1 -------------------------------------------------------------------------

def check_rd1() -> None:
    from world_engine.review_diff import diff_payloads

    if not DIFF_CASES:
        fail("RD1: no case")
    for label, before, after, want in DIFF_CASES:
        got = [(c.path, c.field, c.kind, c.before_value, c.after_value) for c in diff_payloads(before, after)]
        if sorted(got) != sorted(want):
            fail(f"RD1: {label}: {got}")


# --- fixture ---------------------------------------------------------------------

def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Faction, World
    from world_engine.writes import write_ledger_entry

    with Session(engine) as db:
        world = World(name="Suivi", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind in (("brakk", "character"), ("odo", "character"), ("garde", "faction")):
            row = Entity(world_id=world.id, type=kind, name=key.capitalize())
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "brakk" else "npc")
                   if kind == "character" else Faction(id=row.id))
        db.flush()
        write_ledger_entry(db, world_id=world.id, entity_id=ids["brakk"], amount=10, reason="bourse")
        db.commit()
    return ids


def _proposal(engine, ids: dict, mutation_type: str, payload: dict) -> str:
    from sqlmodel import Session

    from world_engine.models import ProposedMutation

    with Session(engine) as db:
        row = ProposedMutation(world_id=ids["world"], source_type="conversation", mutation_type=mutation_type,
                               payload=payload, proposed_by="local_ai_window")
        db.add(row)
        db.commit()
        return row.id


def _reviews(engine, mut_id: str) -> list[tuple]:
    from sqlmodel import Session, select

    from world_engine.models import MutationReview, MutationReviewChange

    with Session(engine) as db:
        out = []
        for r in db.exec(select(MutationReview).where(MutationReview.mutation_id == mut_id)
                         .order_by(MutationReview.round)).all():
            changes = [(c.path, c.kind, c.before_value, c.after_value) for c in
                       db.exec(select(MutationReviewChange).where(MutationReviewChange.review_id == r.id)).all()]
            out.append((r.round, r.action, r.via, r.status_after, r.edited, r.step_verdict, changes))
        return out


def _original(engine, mut_id: str):
    from sqlmodel import Session

    from world_engine.models import ProposedMutation

    with Session(engine) as db:
        return db.get(ProposedMutation, mut_id).original_payload


def _relation(ids: dict, delta: int = 5, with_b: bool = True) -> dict:
    payload = {"entity_a_id": ids["brakk"], "intensity_delta": delta, "relation_type": "trust"}
    if with_b:
        payload["entity_b_id"] = ids["odo"]
    return payload


# --- RD2, RD3 --------------------------------------------------------------------

def check_rd2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes import mutations as routes

    edited = _proposal(engine, ids, "relation_change", _relation(ids))
    plain = _proposal(engine, ids, "relation_change", _relation(ids))
    with Session(engine) as db:
        answer = routes.approve_mutation(edited, routes.ApproveBody(payload=json.dumps(_relation(ids, 9))), db)
        routes.approve_mutation(plain, routes.ApproveBody(payload=json.dumps(_relation(ids))), db)
    if answer.get("status") != "applied":
        fail(f"RD2: the edited approve answered {answer.get('status')}: {answer.get('error')}")
    want = [(1, "approve", "unit", "applied", True, None, [("intensity_delta", "changed", "5", "9")])]
    if _reviews(engine, edited) != want:
        fail(f"RD2: the edited review is {_reviews(engine, edited)}")
    if _original(engine, edited) != _relation(ids):
        fail(f"RD2: original_payload is {_original(engine, edited)}")
    if _reviews(engine, plain) != [(1, "approve", "unit", "applied", False, None, [])] \
            or _original(engine, plain) is not None:
        fail(f"RD2: the unedited review is {_reviews(engine, plain)}, original {_original(engine, plain)}")


def check_rd3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes import mutations as routes

    broken = _proposal(engine, ids, "relation_change", _relation(ids, with_b=False))
    with Session(engine) as db:
        first = routes.approve_mutation(broken, routes.ApproveBody(
            payload=json.dumps(_relation(ids, 6, with_b=False))), db)
        second = routes.approve_mutation(broken, routes.ApproveBody(payload=json.dumps(_relation(ids, 6))), db)
    if (first.get("status"), second.get("status")) != ("approved", "applied"):
        fail(f"RD3: the two approvals answered {first.get('status')}, {second.get('status')}")
    want = [(1, "approve", "unit", "approved", True, None, [("intensity_delta", "changed", "5", "6")]),
            (2, "approve", "unit", "applied", True, None, [("entity_b_id", "added", None, json.dumps(ids["odo"]))])]
    if _reviews(engine, broken) != want:
        fail(f"RD3: the rounds are {_reviews(engine, broken)}")
    if _original(engine, broken) != _relation(ids, with_b=False):
        fail(f"RD3: original_payload is {_original(engine, broken)}")

    unit, batch_r, batch_a = (_proposal(engine, ids, "relation_change", _relation(ids)) for _ in range(3))
    with Session(engine) as db:
        routes.reject_mutation(unit, routes.RejectBody(), db)
        routes.batch_review_mutations(routes.BatchReviewBody(action="reject", mutation_ids=[batch_r]), db)
        routes.batch_review_mutations(routes.BatchReviewBody(action="approve", mutation_ids=[batch_a]), db)
    for mut_id, want_row in ((unit, (1, "reject", "unit", "rejected", False, None, [])),
                             (batch_r, (1, "reject", "batch", "rejected", False, None, [])),
                             (batch_a, (1, "approve", "batch", "applied", False, None, []))):
        if _reviews(engine, mut_id) != [want_row]:
            fail(f"RD3: {want_row[1]} {want_row[2]} recorded {_reviews(engine, mut_id)}")
    auto = _proposal(engine, ids, "relation_change", _relation(ids))
    with Session(engine) as db:
        from datetime import UTC, datetime

        from world_engine.models import ProposedMutation

        done = routes._approve_apply_and_commit(db.get(ProposedMutation, auto), db, datetime.now(UTC))
    if done.get("status") != "applied" or _reviews(engine, auto):
        fail(f"RD3: an auto-apply answered {done.get('status')} and recorded {_reviews(engine, auto)}")


# --- RD4 -------------------------------------------------------------------------

def _step(engine, ids: dict, owner: str, completion: dict | None) -> str:
    from datetime import UTC, datetime

    from sqlmodel import Session

    from world_engine.conditions import node_from_dict
    from world_engine.models import Agenda, AgendaStep
    from world_engine.writes.conditions import write_condition

    with Session(engine) as db:
        agenda = Agenda(world_id=ids["world"], owner_entity_id=ids[owner], title="t", status="active")
        db.add(agenda)
        db.flush()
        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active",
                          started_at=datetime.now(UTC))
        db.add(step)
        db.flush()
        if completion is not None:
            write_condition(db, world_id=ids["world"], role="completion", tree=node_from_dict(completion),
                            agenda_step_id=step.id)
        db.commit()
        return step.id


def check_rd4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes import mutations as routes

    def money(n: int) -> dict:
        return {"op": "leaf", "type": "resource", "subject_role": "doer", "target_key": "or", "threshold": n}

    cases = (
        ("met", _step(engine, ids, "brakk", money(5)), "complete"),
        ("unmet", _step(engine, ids, "brakk", money(1000)), "complete"),
        ("none", _step(engine, ids, "brakk", None), "complete"),
        ("none", _step(engine, ids, "brakk", money(5)), "fail"),
        ("not_judged", _step(engine, ids, "garde", money(5)), "complete"),
        ("not_judged", "no-such-step", "complete"),
    )
    for want, step_id, action in cases:
        mut_id = _proposal(engine, ids, "agenda_step_change", {"step_id": step_id, "action": action})
        with Session(engine) as db:
            routes.reject_mutation(mut_id, routes.RejectBody(), db)
        got = [r[5] for r in _reviews(engine, mut_id)]
        if got != [want]:
            fail(f"RD4: {action} on a step expecting {want} recorded {got}")
    other = _proposal(engine, ids, "relation_change", _relation(ids))
    with Session(engine) as db:
        routes.reject_mutation(other, routes.RejectBody(), db)
    if [r[5] for r in _reviews(engine, other)] != [None]:
        fail(f"RD4: a relation_change recorded the verdict {_reviews(engine, other)}")


# --- RD5 -------------------------------------------------------------------------

def _calls(node: ast.AST, name: str) -> list[int]:
    return sorted(n.lineno for n in ast.walk(node) if isinstance(n, ast.Call)
                  and ((isinstance(n.func, ast.Name) and n.func.id == name)
                       or (isinstance(n.func, ast.Attribute) and n.func.attr == name)))


def check_rd5() -> None:
    if not ROUTES.exists():
        fail(f"RD5: {ROUTES} not found")
        return
    tree = ast.parse(ROUTES.read_text(encoding="utf-8"))
    functions = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    for name in ("reject_mutation", "approve_mutation", "_batch_approve", "_batch_reject"):
        f = functions.get(name)
        if f is None:
            fail(f"RD5: {name} not found")
            continue
        calls, verdicts = _calls(f, "ReviewCall"), _calls(f, "step_verdict")
        if len(calls) != 1 or len(verdicts) != 1:
            fail(f"RD5: {name} builds {len(calls)} ReviewCall with {len(verdicts)} step_verdict")
            continue
        applies = _calls(f, "_apply_mutation") + _calls(f, "_approve_apply_and_commit")
        status_writes = sorted(n.lineno for n in ast.walk(f) if isinstance(n, ast.Assign)
                               and any(isinstance(t, ast.Attribute) and t.attr == "status" for t in n.targets))
        if any(line < calls[0] for line in applies + status_writes):
            fail(f"RD5: {name} applies or sets a status before its ReviewCall")
    approve = functions.get("approve_mutation")
    if approve is not None:
        edit, call, commit = (_calls(approve, n) for n in ("_approve_apply_edited_payload", "ReviewCall",
                                                         "_approve_apply_and_commit"))
        if not (edit and call and commit and edit[0] < call[0] < commit[0]):
            fail("RD5: approve_mutation does not build its ReviewCall between the edit and the apply")
    allowed = {"reject_mutation", "_batch_approve", "_batch_reject", "_approve_entity_creation_shortcircuit",
               "_approve_apply_and_commit"}
    total = 0
    for f in tree.body:
        if isinstance(f, ast.FunctionDef):
            n = len(_calls(f, "record_review"))
            total += n
            if n and f.name not in allowed:
                fail(f"RD5: {f.name} calls record_review")
    if total != 8:
        fail(f"RD5: record_review is called {total} times, not 8")


def main() -> None:
    _fresh_db()
    from sqlmodel import SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_rd1()
    ids = _fixture(engine)
    check_rd2(engine, ids)
    check_rd3(engine, ids)
    check_rd4(engine, ids)
    check_rd5()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: review_recording -- every review is a round with its changes and its step's verdict; "
          "the diff pairs by natural key")


if __name__ == "__main__":
    main()
