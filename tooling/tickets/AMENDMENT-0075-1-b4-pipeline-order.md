# TICKET-0075 — AMENDMENT 1: B4 pipeline order

**Amends:** `tooling/tickets/TICKET-0075-day-resolution-chain.md`, the `B4`
bullet under "Clarifications resolved (intake)".
**Date:** 2026-08-24
**Author:** Claude (design), owning the error.
**Status of the original:** unchanged on disk. History is append-only; this
artifact supersedes one bullet and nothing else.

## What was wrong

The deposited ticket reads:

> **B4** — initial engine narration, then extraction passes analysed in a
> logical order [...]

"Initial engine narration" is a misreading of Nia's B4. Her words were
*"Écriture initiale, des extractions analysées dans un ordre logique qui
résout contre du code ou un autre AI, puis, s'il y a lieu, une réécriture de
la prose"*, immediately followed by *"AI prend **la phrase** et doit trouver
les éléments qui peuvent référer à un lieu, un nom, une faction"*.

"La phrase" is the player's declaration. The **initial writing is the
player's**, and the extraction passes run on it. There is no engine narration
before extraction — the narration is produced late, from an already-frozen
result.

The error mattered: read literally, the deposited bullet would have put a
free narration pass at the head of the chain, with every downstream pass
inferring from unconstrained engine prose. That is B3, which was explicitly
rejected.

## Corrected bullet (supersedes the original B4)

- **B4** — the player's declaration IS the initial writing. Extraction passes
  run on it in a logical order, each resolving against code or a specialised
  model. The engine's narration is produced LAST, from a frozen result, and
  is followed by a CONDITIONAL rewrite only when a late-discovered element
  must be seated. Two distinct writings exist and must not be conflated: the
  PLAYER's declaration (never rewritten, it is history) and the ENGINE's
  narration (the only thing the rewrite pass ever touches).

## Canonical pipeline order

Binding on briefs -b through -f:

```
declaration (player, immutable)
  -> extraction        : places / persons / factions named or inferred   [-c]
  -> concordance       : match against the registry, or emit a germ      [-c]
  -> plan emission     : one call, steps with cost / domain / requires   [-b]
  -> budget cut        : Python, against the 4-slot day budget           [-b]
  -> prerequisite judge: Python, four named evaluators                   [-b]
  -> step resolution   : Python dice, per budgeted step                  [-d]
  -> fact sheet        : frozen; rolls, ids, outcomes                    [-d]
  -> narration         : constrained by the fact sheet                   [-d]
  -> rewrite (rare)    : only on a late delta, T1-judged                 [-d]
  -> mutation emission : whitelisted types, all at `proposed`            [-e]
```

Note the consequence, already anticipated during design: because concordance
runs BEFORE narration, the rewrite pass should never fire in a correctly
ordered run. It exists for the case where step resolution discovers something
the concordance pass could not have known. A rewrite firing is a signal worth
counting, not a routine step — see the D3 reactivation condition, which is
phrased in exactly those terms.

## Execution-order note

Brief **-c** (extraction and concordance) precedes brief **-b** (plan
emission) in the pipeline, but the briefs are numbered in AUTHORING order,
not pipeline order: -b lands the schema and the budget machinery that -c's
germ emission and -d's resolution both depend on. Executing -b before -c is
correct. The pipeline diagram above is the runtime order; the letters are the
build order.

## Unaffected

Every other locked code — A1, C1, F1, H1, I1, L1, M1, N1, O1, P2, Q1, R1, S1,
T1, U1 — stands as deposited. The Scope OUT list, the invariants at risk and
the acceptance criteria are unchanged.
