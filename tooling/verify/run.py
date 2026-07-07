"""Deterministic G1 gate. Parses a ticket's machine criteria, runs each linked
check as a subprocess, writes a verdict JSON, exits non-zero if any check fails."""
import argparse, json, pathlib, re, subprocess, sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
TICKETS = ROOT / "tooling" / "tickets"
CHECKS = ROOT / "tooling" / "verify" / "checks"
RESULTS = ROOT / "tooling" / "verify" / "results"
LINK = re.compile(r"->\s*verify/checks/([A-Za-z0-9_./-]+\.py)")


def machine_checks(ticket_md: str):
    seen, out = set(), []
    in_machine = False
    for line in ticket_md.splitlines():
        if line.strip().lower().startswith("### machine"): in_machine = True; continue
        if line.strip().lower().startswith("### live"):    in_machine = False; continue
        if in_machine:
            m = LINK.search(line)
            if m and m.group(1) not in seen:
                seen.add(m.group(1)); out.append(m.group(1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", required=True)
    tid = ap.parse_args().ticket
    md = (TICKETS / f"{tid}.md").read_text(encoding="utf-8")
    checks = machine_checks(md)

    if not checks:
        # Fail-closed (TICKET-0013 escalation): a Machine-checkable section
        # that parses to zero criteria is a malformed ticket, not a green
        # ticket. Never let an empty checks list report green — that masks
        # a missing/mismatched arrow (or a genuinely empty section) as a
        # passing gate.
        verdict = {
            "ticket": tid,
            "when": datetime.now(timezone.utc).isoformat(),
            "green": False,
            "checks": [],
            "error": "machine-checkable section parsed to zero criteria — malformed arrows or empty section",
        }
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / f"{tid}.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
        print(json.dumps(verdict, indent=2))
        sys.exit(1)

    results, ok = [], True
    for rel in checks:
        path = (CHECKS / pathlib.Path(rel).name)
        if not path.exists():
            results.append({"check": rel, "status": "MISSING", "msg": f"{path} not found"}); ok = False; continue
        p = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        passed = p.returncode == 0
        ok = ok and passed
        results.append({"check": rel, "status": "PASS" if passed else "FAIL",
                        "msg": (p.stdout or p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr).strip() else ""})
    verdict = {"ticket": tid, "when": datetime.now(timezone.utc).isoformat(),
               "green": ok, "checks": results}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{tid}.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print(json.dumps(verdict, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
