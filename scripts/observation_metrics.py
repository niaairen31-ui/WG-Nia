"""Observation run metrics (TICKET-0051, BRIEF-0051-g, decision J2/Q).

Reads one or more `observation_run`s and prints the nine locked metrics.
Read-only: opens the DB, computes, prints. Writes NOTHING — no table, no
cache, no column. Deterministic instruments ONLY — no local-model client
import, no HTTP call to the inference server (D-J1: the LLM novelty judge is
a named deferral, reactivated once this tool has shown its blind spots on
modes (b)/(c), not before).

Three failure modes this tool is built to separate (a flat scene can be any
one of these, and each points at a different fix):

  (a) nobody wants to act    -> low intent rate           -> propensity/intent prompt
  (b) all want, nothing happens -> high intent, low proposal yield -> dialogue prompt
  (c) they loop              -> high n-gram overlap        -> context/scene memory

Usage:
    python scripts/observation_metrics.py <run_id> [<run_id> ...] [--csv]

Mini-RECON note (item 2): `relation.intensity` carries no per-beat snapshot —
this script reads its CURRENT value at analysis time. If a creator approved
a `relation_change` proposal between the run and running this tool, the
correlation metric (Q7) reflects that later state, not "the intensity during
the run". No snapshot column is added here (that would be a schema change
smuggled into an analysis brief) — the limitation is stated in the
interpretation guard printed before any figure.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from math import log2
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console for French output on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "observation_metrics.py refuses to run without WORLD_ENGINE_ENV or "
        "WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import Entity, ProposedMutation, Relation  # noqa: E402
from world_engine.observation_reads import (  # noqa: E402
    derive_not_selected_reason,
    get_run,
    list_beats,
    list_intents,
    list_mutation_links,
    list_run_templates,
)

# n-gram overlap (mode (c)): fixed n=4 words, fixed window of the prior 5
# beats carrying a line (mini-RECON found no reason to deviate from the
# brief's suggested default).
NGRAM_N = 4
NGRAM_WINDOW = 5

INTERPRETATION_GUARD = (
    "These figures describe THIS run. Two runs are comparable only if their\n"
    "pinned parameters and template versions match (shown below) and the world\n"
    "did not change materially between them. Bit-exact replay is out of scope by\n"
    "decision: the world mutates under play. A metric that differs between two\n"
    "runs with different template versions says nothing about the arbitration."
)


# ── Data loading (read-only) ──────────────────────────────────────────────


def _load_run(run_id: str, session: Session):
    run = get_run(run_id, session)
    if run is None:
        raise SystemExit(f"observation_run {run_id!r} not found")
    beats = list_beats(run_id, session)
    intents = list_intents(run_id, session)
    templates = list_run_templates(run_id, session)
    return run, beats, intents, templates


def _present_npc_ids(beats, intents) -> list[str]:
    """The NPC roster this run actually exercised — derived from the intent
    rows (every present NPC gets one per beat, C3), never re-queried live
    (a run's roster is a fact about the past, not the present DB state)."""
    ids: list[str] = []
    seen = set()
    for i in intents:
        if i.npc_id not in seen:
            seen.add(i.npc_id)
            ids.append(i.npc_id)
    return ids


# ── Participation (metrics 1-2) ───────────────────────────────────────────


def acted_beat_share(beats) -> dict[str, float]:
    acted = [b for b in beats if b.outcome == "acted"]
    total = len(acted)
    if total == 0:
        return {}
    counts: dict[str, int] = defaultdict(int)
    for b in acted:
        counts[b.actor_id] += 1
    return {npc_id: count / total for npc_id, count in counts.items()}


def normalized_entropy(shares: dict[str, float], npc_ids: list[str]) -> "float | None":
    """Shannon entropy of the acted-beat distribution over the FULL present
    roster (`npc_ids`, not just NPCs with a non-zero share — a single NPC
    capturing every beat is a degenerate distribution with entropy exactly
    0, not an undefined one), normalised to [0, 1] by dividing by log2(K).
    1 means perfectly even across the K present NPCs; 0 means one NPC
    captured the entire run. None when K < 2 (can't be "even" or "uneven"
    with fewer than 2 candidates)."""
    k = len(npc_ids)
    if k < 2:
        return None
    h = -sum(p * log2(p) for p in shares.values() if p > 0)
    return h / log2(k)


# ── Intent (metrics 3-4) ──────────────────────────────────────────────────


def intent_rate(intents) -> dict[str, float]:
    opportunities: dict[str, int] = defaultdict(int)
    wanted: dict[str, int] = defaultdict(int)
    for i in intents:
        opportunities[i.npc_id] += 1
        if i.act:
            wanted[i.npc_id] += 1
    return {npc_id: wanted.get(npc_id, 0) / count for npc_id, count in opportunities.items()}


def selection_rate_given_intent(intents) -> dict[str, "float | None"]:
    wanted: dict[str, int] = defaultdict(int)
    selected: dict[str, int] = defaultdict(int)
    for i in intents:
        if i.act:
            wanted[i.npc_id] += 1
            if i.selected:
                selected[i.npc_id] += 1
    return {npc_id: (selected.get(npc_id, 0) / count if count else None) for npc_id, count in wanted.items()}


# ── Health (metrics 5-6) ───────────────────────────────────────────────────


def silence_rate(beats) -> float:
    regular = [b for b in beats if b.outcome != "event"]
    if not regular:
        return 0.0
    return sum(1 for b in regular if b.outcome == "silence") / len(regular)


def degraded_rate(beats) -> float:
    regular = [b for b in beats if b.outcome != "event"]
    if not regular:
        return 0.0
    return sum(1 for b in regular if b.outcome == "degraded") / len(regular)


# ── Originating hypothesis (metric 7) ─────────────────────────────────────


def _ranks(values: list[float]) -> list[float]:
    """Average ranks (ties share the mean rank) — standard Spearman input."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> "tuple[float, int] | None":
    """Spearman rank correlation, implemented directly (no scipy dependency
    — CLAUDE.md: no new dependency without a decision). Reported with n; the
    ticket's own n=5 caveat is printed alongside, never silently."""
    n = len(xs)
    if n < 2:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mean_rx, mean_ry = sum(rx) / n, sum(ry) / n
    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    var_x = sum((a - mean_rx) ** 2 for a in rx)
    var_y = sum((b - mean_ry) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return None
    return cov / (var_x ** 0.5 * var_y ** 0.5), n


def _mean_pairwise_intensity(npc_id: str, other_ids: list[str], session: Session) -> "float | None":
    """Mean `relation.intensity` between npc_id and every OTHER present NPC —
    a single per-NPC scalar for a pairwise table. `type='connects_to'` is a
    location-topology edge, never a social signal (CLAUDE.md invariant); this
    scan excludes it structurally."""
    others = [o for o in other_ids if o != npc_id]
    if not others:
        return None
    rows = session.exec(
        select(Relation).where(
            Relation.type != "connects_to",
            ((Relation.entity_a_id == npc_id) & (Relation.entity_b_id.in_(others)))
            | ((Relation.entity_b_id == npc_id) & (Relation.entity_a_id.in_(others))),
        )
    ).all()
    if not rows:
        return None
    return sum(r.intensity for r in rows) / len(rows)


def intensity_vs_act_rate(npc_ids: list[str], beats, session: Session) -> "tuple[float, int] | None":
    acted_counts: dict[str, int] = defaultdict(int)
    for b in beats:
        if b.outcome == "acted":
            acted_counts[b.actor_id] += 1
    total_regular = sum(1 for b in beats if b.outcome != "event")
    if total_regular == 0:
        return None

    xs, ys = [], []
    for npc_id in npc_ids:
        intensity = _mean_pairwise_intensity(npc_id, npc_ids, session)
        if intensity is None:
            continue
        xs.append(abs(intensity - 50))
        ys.append(acted_counts.get(npc_id, 0) / total_regular)
    return spearman(xs, ys)


# ── Repetition — mode (c) (metric 8) ──────────────────────────────────────


def _ngrams(text: str, n: int) -> set:
    words = text.split()
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def ngram_overlap(beats) -> "tuple[dict[int, float], float]":
    """Max containment of each beat's n-grams against the prior NGRAM_WINDOW
    lined beats — 1.0 means every n-gram of the current line already
    appeared in a recent beat (the loop signature, mode (c))."""
    lined = [b for b in beats if b.line]
    per_beat: dict[int, float] = {}
    for idx, beat in enumerate(lined):
        window = lined[max(0, idx - NGRAM_WINDOW):idx]
        current = _ngrams(beat.line, NGRAM_N)
        if not current or not window:
            per_beat[beat.beat_index] = 0.0
            continue
        best = 0.0
        for prior in window:
            prior_grams = _ngrams(prior.line, NGRAM_N)
            if not prior_grams:
                continue
            overlap = len(current & prior_grams) / len(current)
            best = max(best, overlap)
        per_beat[beat.beat_index] = best
    mean = sum(per_beat.values()) / len(per_beat) if per_beat else 0.0
    return per_beat, mean


# ── Evolution / feasibility (metric 9) ────────────────────────────────────


def proposals_by_type(run_id: str, session: Session) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for link in list_mutation_links(run_id, session):
        mutation = session.get(ProposedMutation, link.mutation_id)
        if mutation is not None:
            counts[mutation.mutation_type] += 1
    return counts


def _percentile(values: list[float], pct: float) -> "float | None":
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def latency_percentiles(intents) -> "tuple[float | None, float | None]":
    values = [i.latency_ms for i in intents if i.latency_ms is not None]
    return _percentile(values, 0.50), _percentile(values, 0.95)


# ── Presentation ───────────────────────────────────────────────────────────


def _npc_name(npc_id: str, session: Session) -> str:
    entity = session.get(Entity, npc_id)
    return entity.name if entity is not None else npc_id


def compute_report(run_id: str, session: Session) -> dict:
    run, beats, intents, templates = _load_run(run_id, session)
    npc_ids = _present_npc_ids(beats, intents)

    shares = acted_beat_share(beats)
    entropy = normalized_entropy(shares, npc_ids)
    i_rate = intent_rate(intents)
    s_rate = selection_rate_given_intent(intents)
    sil_rate = silence_rate(beats)
    deg_rate = degraded_rate(beats)
    correlation = intensity_vs_act_rate(npc_ids, beats, session)
    per_beat_overlap, mean_overlap = ngram_overlap(beats)
    proposals = proposals_by_type(run_id, session)
    p50, p95 = latency_percentiles(intents)

    not_selected_counts: dict[str, int] = defaultdict(int)
    for i in intents:
        reason = derive_not_selected_reason(i)
        if reason is not None:
            not_selected_counts[reason] += 1

    return {
        "run": run,
        "templates": templates,
        "npc_names": {npc_id: _npc_name(npc_id, session) for npc_id in npc_ids},
        "acted_beat_share": shares,
        "entropy": entropy,
        "intent_rate": i_rate,
        "selection_rate_given_intent": s_rate,
        "silence_rate": sil_rate,
        "degraded_rate": deg_rate,
        "correlation": correlation,
        "per_beat_overlap": per_beat_overlap,
        "mean_overlap": mean_overlap,
        "proposals_by_type": proposals,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "not_selected_reason_counts": dict(not_selected_counts),
        "beat_count": len(beats),
        "intent_count": len(intents),
    }


def _print_human(reports: list[dict]) -> None:
    print(INTERPRETATION_GUARD)
    print()
    for report in reports:
        run = report["run"]
        print(f"=== Run {run.id} ({run.status}, stop_reason={run.stop_reason}) ===")
        print(f"cooldown_beats={run.cooldown_beats} debt_weight={run.debt_weight} "
              f"propensity_mode={run.propensity_mode} model={run.model}")
        for t in report["templates"]:
            print(f"  template pinned: {t.usage} = {t.template_id} v{t.version}")

        if report["degraded_rate"] > 0:
            print(f"\n*** SUSPECT RUN: degraded_rate={report['degraded_rate']:.2%} — this run has a "
                  "technical fault (intent calls failing), and every other metric below is suspect. ***\n")

        print("\n-- Participation --")
        for npc_id, share in report["acted_beat_share"].items():
            print(f"  {report['npc_names'].get(npc_id, npc_id)}: acted_beat_share={share:.2%}")
        print(f"  normalized_entropy={report['entropy']:.3f}" if report["entropy"] is not None
              else "  normalized_entropy=undefined (fewer than 2 NPCs acted)")

        print("\n-- Intent --")
        for npc_id in report["npc_names"]:
            name = report["npc_names"][npc_id]
            ir = report["intent_rate"].get(npc_id)
            sr = report["selection_rate_given_intent"].get(npc_id)
            sr_txt = f"{sr:.2%}" if sr is not None else "n/a (never wanted to act)"
            print(f"  {name}: intent_rate={ir:.2%} selection_rate_given_intent={sr_txt}")

        print("\n-- Health --")
        print(f"  silence_rate={report['silence_rate']:.2%}  degraded_rate={report['degraded_rate']:.2%}")

        print("\n-- Originating hypothesis (Q7) --")
        if report["correlation"] is None:
            print("  Spearman: undetermined (fewer than 2 NPCs with a recoverable relation intensity)")
        else:
            rho, n = report["correlation"]
            print(f"  Spearman(rho)={rho:.3f}  n={n} — n={n} supports a DIRECTION, not a conclusion.")

        print("\n-- Repetition (mode c) --")
        print(f"  n-gram overlap (n={NGRAM_N}, window={NGRAM_WINDOW}): run mean={report['mean_overlap']:.2%}")
        if report["per_beat_overlap"]:
            worst = max(report["per_beat_overlap"].items(), key=lambda kv: kv[1])
            print(f"  worst beat: #{worst[0]} overlap={worst[1]:.2%}")

        print("\n-- Evolution / feasibility --")
        if report["proposals_by_type"]:
            for mtype, count in sorted(report["proposals_by_type"].items()):
                print(f"  proposals[{mtype}]={count}")
        else:
            print("  proposals: 0")
        p50 = f"{report['latency_p50_ms']:.0f}ms" if report["latency_p50_ms"] is not None else "n/a"
        p95 = f"{report['latency_p95_ms']:.0f}ms" if report["latency_p95_ms"] is not None else "n/a"
        print(f"  intent latency p50={p50} p95={p95}")
        print()


def _print_csv(reports: list[dict]) -> None:
    # lineterminator='\n': sys.stdout's own text-mode newline translation
    # would otherwise double up with csv's default '\r\n' on Windows,
    # producing a spurious blank row between every record.
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow([
        "run_id", "status", "stop_reason", "cooldown_beats", "debt_weight",
        "propensity_mode", "model", "entropy", "silence_rate", "degraded_rate",
        "spearman_rho", "spearman_n", "mean_ngram_overlap", "latency_p50_ms",
        "latency_p95_ms", "total_proposals",
    ])
    for report in reports:
        run = report["run"]
        rho, n = report["correlation"] if report["correlation"] is not None else (None, None)
        writer.writerow([
            run.id, run.status, run.stop_reason, run.cooldown_beats, run.debt_weight,
            run.propensity_mode, run.model,
            report["entropy"], report["silence_rate"], report["degraded_rate"],
            rho, n, report["mean_overlap"], report["latency_p50_ms"], report["latency_p95_ms"],
            sum(report["proposals_by_type"].values()),
        ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="+", help="one or more observation_run ids")
    parser.add_argument("--csv", action="store_true", help="machine-readable CSV output instead of stdout prose")
    args = parser.parse_args()

    with Session(engine) as session:
        reports = [compute_report(run_id, session) for run_id in args.run_ids]

    if args.csv:
        _print_csv(reports)
    else:
        _print_human(reports)


if __name__ == "__main__":
    main()
