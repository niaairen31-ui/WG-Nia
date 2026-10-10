"""G1 check for TICKET-0117 (BRIEF-0117-b, M1, L4-L6) -- the Claude Code
session configuration: how a brief is executed, committed and escalated.

Text and JSON only, no DB. Every rule reads a file that must exist -- a
missing file is a FAILURE, never a skip.

SC1 -- permissions. `.claude/settings.json` parses, and `permissions.allow`
   holds `Bash(git switch:*)`, `Bash(git add:*)` and `Bash(git commit:*)`:
   commits are pre-authorized (M1). Prose is matched with its whitespace
   collapsed, so a phrase may wrap.
SC2 -- the commit net. `hooks.PreToolUse` has a `Bash` matcher whose
   commands name `block-main-push.ps1`, `block-db-in-git.ps1` and
   `block-commit-on-main.ps1`, each present under `.claude/hooks/`;
   `block-commit-on-main.ps1` reads the branch with `rev-parse --abbrev-ref
   HEAD`, denies `main|master`, and denies a branch it cannot read.
SC3 -- the chain. `review-step.md` and `brief-exec.md` each say to
   continue to /close-step in the same turn; `review-step.md` names
   VIOLATION as the stop; `close-step.md` commits without waiting for
   approval and holds neither `Wait for approval` nor `Unattended mode`.
SC4 -- /pipeline. `pipeline.md` pushes only `ticket/NNNN`, escalates
   through `tooling/glue/escalation.py`, and holds neither an unattended
   mode nor a recon stage.
SC5 -- retired. `.claude/commands/recon.md` and the skills `recon`,
   `brief` and `verify-authoring` do not exist (L4-L6).
SC6 -- the whole law (BRIEF-0117-e). `review-step.md` and `close-step.md`
   each read every `.claude/rules/*.md` besides the root CLAUDE.md, and
   `review-step.md` sends a reviewer to the docstring of an invariant's
   enforcing check.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_DIR = ROOT / ".claude"
COMMANDS = CLAUDE_DIR / "commands"
HOOKS = CLAUDE_DIR / "hooks"

REQUIRED_ALLOW = ("Bash(git switch:*)", "Bash(git add:*)", "Bash(git commit:*)")
REQUIRED_HOOKS = ("block-main-push.ps1", "block-db-in-git.ps1", "block-commit-on-main.ps1")
CHAIN_PHRASE = "continue to /close-step in the same turn"
RETIRED = (
    COMMANDS / "recon.md",
    CLAUDE_DIR / "skills" / "recon",
    CLAUDE_DIR / "skills" / "brief",
    CLAUDE_DIR / "skills" / "verify-authoring",
)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def read(path: pathlib.Path) -> str:
    if not path.exists():
        fail(f"{path.relative_to(ROOT).as_posix()} not found")
        return ""
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The prose with every run of whitespace made one space: a phrase is
    found whatever line it wraps on."""
    return " ".join(text.split())


def check_settings() -> None:
    raw = read(CLAUDE_DIR / "settings.json")
    if not raw:
        return
    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"SC1: settings.json does not parse: {exc}")
        return
    allow = settings.get("permissions", {}).get("allow", [])
    for entry in REQUIRED_ALLOW:
        if entry not in allow:
            fail(f"SC1: permissions.allow lacks {entry!r}")
    commands = [
        hook.get("command", "")
        for group in settings.get("hooks", {}).get("PreToolUse", [])
        if group.get("matcher") == "Bash"
        for hook in group.get("hooks", [])
    ]
    if not commands:
        fail("SC2: no PreToolUse Bash hook collected")
    for name in REQUIRED_HOOKS:
        if not any(name in command for command in commands):
            fail(f"SC2: no PreToolUse Bash hook runs {name}")
        if not (HOOKS / name).exists():
            fail(f"SC2: .claude/hooks/{name} not found")


def check_commit_hook() -> None:
    text = read(HOOKS / "block-commit-on-main.ps1")
    if not text:
        return
    for needle, why in (
        ("rev-parse --abbrev-ref HEAD", "does not read the current branch"),
        ("'^(main|master)$'", "does not deny main or master"),
        ("$branch -eq ''", "does not deny a branch it cannot read"),
        ('permissionDecision = "deny"', "never denies"),
    ):
        if needle not in text:
            fail(f"SC2: block-commit-on-main.ps1 {why}")


def check_chain() -> None:
    review = flat(read(COMMANDS / "review-step.md"))
    brief_exec = flat(read(COMMANDS / "brief-exec.md"))
    close = flat(read(COMMANDS / "close-step.md"))
    for name, text in (("review-step.md", review), ("brief-exec.md", brief_exec)):
        if text and CHAIN_PHRASE not in text:
            fail(f"SC3: {name} does not say {CHAIN_PHRASE!r}")
    if review and "On VIOLATION, stop and report" not in review:
        fail("SC3: review-step.md does not stop on VIOLATION")
    if close:
        if "do not wait for approval" not in close:
            fail("SC3: close-step.md does not commit without approval")
        for stale in ("Wait for approval", "Unattended mode"):
            if stale in close:
                fail(f"SC3: close-step.md still holds {stale!r}")


def check_pipeline() -> None:
    text = flat(read(COMMANDS / "pipeline.md"))
    if not text:
        return
    for needle in ("git push origin ticket/NNNN", "python tooling/glue/escalation.py open TICKET-NNNN"):
        if needle not in text:
            fail(f"SC4: pipeline.md lacks {needle!r}")
    lowered = text.lower()
    for stale in ("unattended", "recon spec", "recon.md"):
        if stale in lowered:
            fail(f"SC4: pipeline.md still holds {stale!r}")


def check_retired() -> None:
    for path in RETIRED:
        if path.exists():
            fail(f"SC5: {path.relative_to(ROOT).as_posix()} exists; it was retired")


def check_whole_law() -> None:
    for name in ("review-step.md", "close-step.md"):
        text = flat(read(COMMANDS / name))
        if text and "`.claude/rules/*.md`" not in text:
            fail(f"SC6: {name} does not read every .claude/rules/*.md")
    review = flat(read(COMMANDS / "review-step.md"))
    if review and "the full law is that check's docstring" not in review:
        fail("SC6: review-step.md does not send the reviewer to the check's docstring")


def main() -> int:
    check_settings()
    check_commit_hook()
    check_chain()
    check_pipeline()
    check_retired()
    check_whole_law()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: session_config -- commits pre-authorized behind a no-commit-on-main hook; "
          "review chains to close in one turn; /pipeline escalates into the ticket")
    return 0


if __name__ == "__main__":
    sys.exit(main())
