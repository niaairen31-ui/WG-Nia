"""Hot/cold partition holds: world-engine-schema.md carries exactly one
current-version header line and no CHANGELOG content; the extracted
world-engine-schema-changelog.md exists, has both boundary entries, and its
newest entry matches the header version (newest-first invariant)."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "world-engine-schema.md"
CHANGELOG = ROOT / "world-engine-schema-changelog.md"

VERSION_HEADER = re.compile(r"^Current schema version: v(\d+\.\d+)$")
ENTRY = re.compile(r"^- \*\*v(\d+\.\d+)\*\*")


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not SCHEMA.exists():
        fail(f"{SCHEMA} not found")
    if not CHANGELOG.exists():
        fail(f"{CHANGELOG} not found")

    schema_lines = SCHEMA.read_text(encoding="utf-8").splitlines()

    header_matches = [m for m in (VERSION_HEADER.match(l) for l in schema_lines) if m]
    if len(header_matches) != 1:
        fail(f"expected exactly one 'Current schema version: vX.YY' line in {SCHEMA.name}, found {len(header_matches)}")
    header_version = header_matches[0].group(1)

    if any(l.strip() == "## CHANGELOG" for l in schema_lines):
        fail(f"{SCHEMA.name} still contains a '## CHANGELOG' heading")
    if any(ENTRY.match(l) for l in schema_lines):
        fail(f"{SCHEMA.name} still contains changelog entry lines")

    changelog_lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    changelog_entries = [m.group(1) for m in (ENTRY.match(l) for l in changelog_lines) if m]

    if "1.66" not in changelog_entries:
        fail(f"{CHANGELOG.name} missing boundary entry v1.66")
    if "1.1" not in changelog_entries:
        fail(f"{CHANGELOG.name} missing boundary entry v1.1")

    first_entry_version = changelog_entries[0]
    if first_entry_version != header_version:
        fail(
            f"header version v{header_version} does not match first (newest) "
            f"changelog entry v{first_entry_version}"
        )

    print("PASS: hot/cold partition holds")
    sys.exit(0)


if __name__ == "__main__":
    main()
