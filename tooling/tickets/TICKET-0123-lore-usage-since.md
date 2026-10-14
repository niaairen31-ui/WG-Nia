---
id: TICKET-0123
title: The Lore usage export reads `--since` on the cockpit's clock -- one meaning of « a day » for the export and the dashboard
type: bug
status: live-gate
created: 2026-10-13
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
lot_id: LOT-0123-lore-usage-since.md
brief_ids: [A]
current_brief: A
schema_version_touched:
retry_count: 0
slug: lore-usage-since
---

## Request (verbatim, as Nia stated it)

The handover for this conversation (2026-10-13, `main` at `301d178`) states
the defect:

> `tooling/verify/checks/lore_usage.py`, règle **U12c**, échoue chaque soir
> entre 20 h et minuit (heure de Toronto, UTC−4) : le contrôle appelle
> `scripts/export_lore_usage.py --since <demain>` et attend un fichier vide ;
> le script exporte quand même les lignes du jour. Le reste de la journée, la
> règle passe. Signalé par Claude Code pendant BRIEF-0121-E ; rien de 0121 ne
> touche ce code. Conséquence pratique : `corpus_gate.py` (donc `/verify`) est
> rouge le soir.

After the RECON and the decision blocks:

> A1, B Je suis a UTC-4, que recommande tu ?, C1, Redige le ticket avec le lot.

## Clarifications resolved (intake)

- **Reproduced, not inferred.** On `main` at `301d178`, 2026-10-13 at 22:02
  Toronto (02:02 UTC on the 14th): `TZ=America/Toronto` ->
  `FAIL: U12c: --since 2026-10-14 exit 0, 8 line(s)`; the same instant under
  `TZ=UTC` -> PASS.
- **Which side is wrong.** The script, not the check. `--since 2026-10-14`
  means the 14th at Nia's place, as the dashboard's « Suivi » reads its dates
  (E2 of TICKET-0115). The script reads it as midnight UTC.
- **Why B3 at UTC-4.** At UTC-4 (UTC-5 in winter) an end-to-end rule on
  Nia's machine (B4) would catch the defect at any hour. B3 was chosen anyway
  because its proof holds on any machine, at any hour, in any season. The
  B2 route (`TZ=...` in the subprocess) proves nothing on Windows, where
  `/verify` runs (`CLAUDE.md:25`) and the project carries no `tzdata`.
- **Production.** No schema change, no data written: the script is
  read-only (U12d) and the dashboard's behaviour is unchanged by a pure move.

## Decisions locked (do not re-litigate without Nia)

- **A1** -- the conversion of a day into its UTC instant lives once, in a new
  module `src/world_engine/local_day.py` (`local_midnight_utc`), moved
  verbatim from the dashboard route's `_utc` in its own commit; the route
  and the export script both import it. Rejected: A2, a copy in the script
  (two meanings of « a day »). Reactivation: none.
- **B3** -- `local_midnight_utc(day, tz=None)`: `None` is the machine's
  clock (every production caller); a new rule U12f proves the conversion in
  process at fixed UTC offsets (standard library only) and proves by AST that
  the script's `--since` goes through it. U12c stays as it is. Rejected: B1
  (U12c alone: the defect shows only in the evening); B2 (`TZ=` in the
  subprocess: vacuous on Windows; reactivation: `tzdata` becomes a
  dependency for another reason); B4 (rows re-stamped in the check's
  database: proves nothing on a UTC machine; reactivation: none while B3
  holds).
- **C1** -- `--since` accepts a date `YYYY-MM-DD` and nothing else; any
  other value exits 2 with a message, no file written. Rejected: C2, keep
  accepting a date-time (no clock it could be read on). Reactivation: none.

## Drafting decisions (made in the lot; Nia may reverse before execution)

1. One brief, two commits: the pure move, then the script, the check and the
   docs.
2. `danger_class: []`, `blast_radius: small`, no schema change.
3. U12f's clocks are UTC-4, UTC-12, UTC+14 and UTC+0 on 2026-10-14 (the two
   extremes plus Nia's summer offset and the identity case).
4. The dashboard route's now-unused `UTC`, `datetime` and `time` imports are
   removed in the pure-move commit.
5. A decision record « A DAY IS THE COCKPIT'S DAY » is added to
   `ARCHITECTURE_DECISIONS.md`, so a third reader of a date reaches for
   `local_day.py` rather than writing a third conversion.

## Carried forward / open

- **Other date readers.** The RECON opened the dashboard route and the
  export script only. Any other place that turns a typed date into a UTC
  instant was not enumerated; this ticket claims nothing about it. If one
  surfaces, it goes in a ticket numbered above 0123.
- Speed up lore_usage.py's U12 exports so it fits the default timeout
  again; then remove its SLOW_CHECK_TIMEOUTS entry. Own ticket, numbered
  above 0123.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `--since` is a date on the cockpit's clock; U12c and U12f pass  -> verify/checks/lore_usage.py
- [ ] The dashboard's dates are unchanged by the move  -> verify/checks/dashboard_registry.py
- [ ] `local_day.py` has a docstring and the module map is fresh  -> verify/checks/file_map.py
- [ ] The new decision record's header and the index  -> verify/checks/decisions_index.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] On Nia's machine, after 20 h Toronto time,
      `python tooling/verify/checks/lore_usage.py` (with
      `WORLD_ENGINE_ENV=test`) prints PASS.
- [ ] In « Suivi », a « du ... au ... » range still shows the same numbers
      as before the change for the same range.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0123-01 | A | lore_usage.py at ~15–18 s exceeds corpus_gate's single 15 s timeout | none (one brief) |

## Escalations

### E-01 — D1-d — A

**Context:**
BRIEF-0123-A executed in full: commits 07462d0 (pure move, dashboard_registry/file_map/import_cycle/module_budget PASS) and 79de685 (--since through local_midnight_utc, U12f, decision record). lore_usage.py prints PASS standalone at 22:20 Toronto (the evening window where U12c used to fail); M1 -> 2 U12f FAILs, M2 -> 3 U12f FAILs (UTC-4, UTC-12, UTC+14), both reverted; --since hier exits 2 with no file. /verify run 1 (2026-10-14T02:28:56Z): lore_usage.py PASS, dashboard_registry.py PASS, file_map.py PASS, decisions_index.py PASS, corpus_gate.py FAIL "SUMMARY: 1 check(s) failed (0 environment, 0 crash, 1 timeout, 0 other)"; a standalone corpus_gate.py run at the same time printed "TIMEOUT: event_analyzer.py exceeded 15s" and "TIMEOUT: lore_usage.py exceeded 15s". /verify run 2 (retry, no code change): identical verdict, corpus_gate.py FAIL "SUMMARY: 1 check(s) failed (0 environment, 0 crash, 1 timeout, 0 other)". Timings of lore_usage.py standalone on this machine: 13.9 s with the U12f call removed, 15.5 s / 16.4 s / 17.0 s / 17.7 s with it (event_analyzer.py, untouched: 10.7-11.5 s). corpus_gate.py's TIMEOUT_SECONDS = 15 is fixed per check. The brief's ADAPT rule for exactly this case says: report the timing with and without U12f, change nothing -- so the retry had no admissible fix (any fix changes U12f as specified or corpus_gate.py, both outside Scope IN).

**Question:**
How should lore_usage.py, now 15.5-17.7 s with U12f (13.9 s without, already near the limit before this ticket), fit under corpus_gate.py's 15 s per-check timeout?

**Options:**
A. Raise corpus_gate.py's TIMEOUT_SECONDS (e.g. 15 -> 30), re-measuring and rewriting its stale comment (it cites 3.22 s as the slowest check); one commit on ticket/0123. B. Give lore_usage.py (or a named list of slow checks) its own baselined timeout in corpus_gate.py, keeping 15 s for all others. C. Make U12f's exit-2 probe in-process (call the script's main([...]) / _since_day instead of a subprocess) to save ~1.5 s -- leaves lore_usage.py at ~14-16 s, still at the edge. D. Defer: accept the red corpus_gate on this ticket and open a ticket above 0123 to speed up lore_usage.py's U12 subprocess exports. Recommendation: A (or B), because lore_usage.py was already at 13.9 s and event_analyzer.py timed out once with no change of this ticket.

**Response:**
Voila l'amendement. fini le pipeline.
-- AMENDMENT-0123-01: decision B, named per-check timeouts (SLOW_CHECK_TIMEOUTS); A rejected.
