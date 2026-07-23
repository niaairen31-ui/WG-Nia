"""G1 gate (static, no DB, TICKET-0044, BRIEF-0044-a): the code-side
`EXPECTED_STATIC_SCHEMA_VERSION` constant must equal the
`Current schema version:` line in `world-engine-schema.md`. Fails if either
value is unparseable, or if the two disagree — never reports green on zero
parsed values (vacuous-proof)."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA_VERSION_PY = ROOT / "src" / "world_engine" / "schema_version.py"
SCHEMA_MD = ROOT / "world-engine-schema.md"

CONST_RE = re.compile(r'EXPECTED_STATIC_SCHEMA_VERSION\s*:?\s*(?:str\s*)?=\s*"([^"]+)"')
DOC_RE = re.compile(r"^Current schema version:\s*(\S+)\s*$", re.MULTILINE)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    if not SCHEMA_VERSION_PY.exists():
        fail(f"{SCHEMA_VERSION_PY} not found")
    if not SCHEMA_MD.exists():
        fail(f"{SCHEMA_MD} not found")

    const_match = CONST_RE.search(SCHEMA_VERSION_PY.read_text(encoding="utf-8"))
    doc_match = DOC_RE.search(SCHEMA_MD.read_text(encoding="utf-8"))

    if not const_match:
        fail(f"could not parse EXPECTED_STATIC_SCHEMA_VERSION from {SCHEMA_VERSION_PY}")
    if not doc_match:
        fail(f"could not parse 'Current schema version:' line from {SCHEMA_MD}")

    code_version = const_match.group(1)
    doc_version = doc_match.group(1)

    if not code_version or not doc_version:
        fail("parsed an empty version value — vacuous proof, treating as failure")

    if code_version != doc_version:
        fail(
            f"schema_version.py says {code_version!r}, "
            f"world-engine-schema.md says {doc_version!r} — bump them together"
        )

    print(f"PASS: code and doc agree on schema version {code_version!r}")
    sys.exit(0)


if __name__ == "__main__":
    main()
