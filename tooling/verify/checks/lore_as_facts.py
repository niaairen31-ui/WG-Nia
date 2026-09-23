"""G1 check: lore as facts — the prose columns and `location_subculture` are
gone (TICKET-0091, BRIEF-0091-I, gate (e)).

Schema v2.06 relocated every descriptive prose column and every
`location_subculture` row into descriptive `fact` rows and dropped the
sources. Nothing may read or declare them again. Four rules:

R1 (AST) -- no `ast.Attribute` whose `attr` is one of `appearance`,
   `backstory`, `secrets`, `philosophy`, `internal_structure`,
   `internal_tensions`, `aversion`, `goals` anywhere under
   `src/world_engine/` outside `models/`.
R2 (tokens) -- the identifier `LocationSubculture` appears nowhere under
   `src/` (comments and strings are not identifiers).
R3 (AST) -- the dropped columns are absent from the model classes under
   `models/`: `Entity.description`; `Character.appearance`, `.backstory`,
   `.aversion`, `.secrets`; `Faction.internal_structure`, `.philosophy`,
   `.internal_tensions`, `.goals`, `.aversion`. Each class must be found
   (a missing class is a FAILURE, never a vacuous pass).
R4 (tokens) -- the identifier `_SAFE_SUBCULTURE_KEYS` appears nowhere
   under `src/`; the ambient-custom allow-list is
   `FACETS["coutume"].aspects` (pinned by `prompt_lean.py` rule 3).

Zero Python files examined is a FAILURE (vacuous-proof guard).
"""
from __future__ import annotations

import ast
import io
import pathlib
import sys
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
MODELS = PKG / "models"

MOVED_ATTRS = frozenset({
    "appearance", "backstory", "secrets", "philosophy", "internal_structure",
    "internal_tensions", "aversion", "goals",
})
DROPPED_FIELDS = {
    "Entity": ("description",),
    "Character": ("appearance", "backstory", "aversion", "secrets"),
    "Faction": ("internal_structure", "philosophy", "internal_tensions", "goals", "aversion"),
}
BANNED_IDENTIFIERS = ("LocationSubculture", "_SAFE_SUBCULTURE_KEYS")

FAILURES: list[str] = []


def _fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _r1(files: list[pathlib.Path]) -> int:
    examined = 0
    for path in files:
        if MODELS in path.parents:
            continue
        examined += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in MOVED_ATTRS:
                _fail(f"R1 {_rel(path)}:{node.lineno} reads moved column attribute .{node.attr}")
    return examined


def _r2_r4(files: list[pathlib.Path]) -> None:
    for path in files:
        source = path.read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.NAME and tok.string in BANNED_IDENTIFIERS:
                rule = "R2" if tok.string == "LocationSubculture" else "R4"
                _fail(f"{rule} {_rel(path)}:{tok.start[0]} identifier {tok.string} still present")


def _r3() -> None:
    found: set[str] = set()
    for path in _py_files(MODELS):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name not in DROPPED_FIELDS:
                continue
            found.add(node.name)
            declared = {
                stmt.target.id for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            } | {
                target.id for stmt in node.body if isinstance(stmt, ast.Assign)
                for target in stmt.targets if isinstance(target, ast.Name)
            }
            for field in DROPPED_FIELDS[node.name]:
                if field in declared:
                    _fail(f"R3 {_rel(path)}: {node.name}.{field} is still declared (dropped in v2.06)")
    for name in sorted(set(DROPPED_FIELDS) - found):
        _fail(f"R3 model class {name} not found under {_rel(MODELS)}")


def main() -> int:
    files = _py_files(PKG)
    if not files:
        _fail(f"no Python file found under {_rel(PKG)}")
    examined = _r1(files)
    src_files = _py_files(SRC)
    _r2_r4(src_files)
    _r3()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: lore_as_facts — "
        f"R1 {examined} module(s) read no moved column; R2/R4 no LocationSubculture / "
        f"_SAFE_SUBCULTURE_KEYS identifier in {len(src_files)} file(s); R3 "
        f"{sum(len(v) for v in DROPPED_FIELDS.values())} dropped field(s) absent from "
        f"{len(DROPPED_FIELDS)} model class(es)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
