"""Regenerate-and-diff gate: the committed DECISIONS_INDEX.md must equal a
fresh regeneration from ARCHITECTURE_DECISIONS.md, and every header added
since the grandfathered baseline must match the strict header pattern.
Baseline headers (the 47 pre-existing ones) are never validated."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling" / "glue"))

from gen_decisions_index import ARCHIVE, INDEX, parse_records, render

BASELINE = ROOT / "tooling" / "verify" / "baselines" / "decisions_headers.baseline"
STRICT_HEADER = re.compile(
    r"^## .+ \(BRIEF-\d{4}(-[a-z])?(, BRIEF-\d{4}(-[a-z])?)*, (schema v\d+\.\d+|no schema change)\)$"
)


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    text = ARCHIVE.read_text(encoding="utf-8")
    records = parse_records(text)

    fresh = render(records)
    committed = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    if fresh != committed:
        fail("index stale: regenerate gen_decisions_index.py")

    baseline_headers = set(BASELINE.read_text(encoding="utf-8").splitlines())
    for _line_no, raw, _title, _briefs, _versions in records:
        if raw in baseline_headers:
            continue
        if not STRICT_HEADER.match(raw):
            fail(f"header fails strict pattern: {raw!r}")

    print("PASS: index matches archive, new headers pass the strict gate")
    sys.exit(0)


if __name__ == "__main__":
    main()
