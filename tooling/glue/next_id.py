"""Mechanical ID counter: prints max+1 over every 4-digit TICKET/RECON/BRIEF
number found in tooling/tickets, tooling/recon, tooling/briefs filenames,
zero-padded to 4 digits, and nothing else. Never creates, renames, or writes
any file. Legacy two-digit BRIEF-NN names are a distinct namespace and are
invisible to this scan."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIRS = (
    ROOT / "tooling" / "tickets",
    ROOT / "tooling" / "recon",
    ROOT / "tooling" / "briefs",
)
ID_RE = re.compile(r"(?:TICKET|RECON|BRIEF)-(\d{4})")


def compute_next_id() -> str:
    max_id = 0
    for d in DIRS:
        if not d.exists():
            continue
        for path in d.iterdir():
            m = ID_RE.search(path.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
    return f"{max_id + 1:04d}"


def main():
    print(compute_next_id())


if __name__ == "__main__":
    main()
