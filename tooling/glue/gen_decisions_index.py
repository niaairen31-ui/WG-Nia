"""Tolerant generator: regenerates DECISIONS_INDEX.md from every '## ' record
header in ARCHITECTURE_DECISIONS.md. Reads only; never writes the archive."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "tooling" / "standards" / "ARCHITECTURE_DECISIONS.md"
INDEX = ROOT / "tooling" / "standards" / "DECISIONS_INDEX.md"

BRIEF_RE = re.compile(r"BRIEF-\d{2,4}(?:-[a-z])?")
VERSION_RE = re.compile(r"v\d+\.\d+")

HEADER = (
    "# DECISIONS_INDEX — generated file, DO NOT EDIT\n"
    "Regenerate: python tooling/glue/gen_decisions_index.py\n"
    "Source: tooling/standards/ARCHITECTURE_DECISIONS.md (byte-intact archive)"
)


def parse_records(text: str):
    """Returns a list of (line_no, raw_line, title, briefs, versions) tuples,
    one per '## ' header, skipping any that fall inside a fenced code block."""
    records = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            briefs = ", ".join(BRIEF_RE.findall(line))
            versions = ", ".join(VERSION_RE.findall(line))
            records.append((i, line, title, briefs, versions))
    return records


def render(records) -> str:
    lines = [HEADER, "", "| line | title | briefs | versions |", "|---|---|---|---|"]
    for line_no, _raw, title, briefs, versions in records:
        lines.append(f"| {line_no} | {title} | {briefs} | {versions} |")
    return "\n".join(lines) + "\n"


def main():
    text = ARCHIVE.read_text(encoding="utf-8")
    records = parse_records(text)
    INDEX.write_text(render(records), encoding="utf-8")
    print(f"wrote {len(records)} records to {INDEX}")


if __name__ == "__main__":
    main()
