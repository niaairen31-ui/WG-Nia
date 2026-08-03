# BRIEF — Step "graph lock: prove convergence, not presence"

Ticket: TICKET-0058. Relies on RECON-0058-a M9.

## Context

`graph_primitive.py` refuses a registry that parses zero entries
(`tooling/verify/checks/graph_primitive.py:151`). `relation_cytoscape` is the
last entry (`frontend/src/graph/registry.js:11-18`), and brief -c retires it.
As written, the lock would fail at the exact moment its guarantee becomes
total - a fail-closed guard firing as a false alarm.

The registry's own comment already states the intended endgame:
"When the last entry goes, 'un graph est un graph' stops being a claim and
becomes a measured fact" (`registry.js:6-7`). The check cannot currently
encode that sentence. This step teaches it to.

The rule changes direction. Today it asks: does each declared
implementation still exist where it says it does? It will ask: is each
baselined implementation gone from where it used to be? The baseline stops
being only a shrink-ceiling and becomes the list of things that must be
proven absent.

This lands BEFORE brief -c, because -c must remove the registry entry in the
same commit that deletes `relGraph*` (rule 5 would otherwise fail on a live
entry whose locus no longer declares its prefix). With -b first, that commit
is green.

## Scope IN

1. **`tooling/verify/checks/graph_primitive.py` - amend `_parse_registry`.**
   An empty parse is no longer a failure by itself. It returns an empty dict.
   It remains a failure if the file does not exist, or if the file contains a
   `GRAPH_IMPLS` literal whose entries fail to parse into the expected shape -
   distinguish "declares nothing" from "declares something unreadable" and
   fail only on the second. State the distinguishing test in a comment.

2. **Amend rule 3.** Keep the monotone-shrink assertion unchanged (every live
   key must be in the baseline; the baseline must be non-empty). Add: the set
   of *retired* keys is `baseline - live`, and it is this set the new rule 5b
   ranges over.

3. **Amend rule 5, and add rule 5b.** Verbatim intent for the docstring:
   - rule 5 (live entries, unchanged): every registry entry's `locus` still
     contains at least one `function <fnPrefix>\w+(` declaration.
   - rule 5b (retired entries, new): for every key in `baseline - live`, its
     recorded `fnPrefix` and `locus` are read from
     `tooling/verify/baselines/graph_impls.retired`, and the check asserts
     that `locus` contains ZERO occurrences of that prefix in ANY context -
     raw substring, comments included. A converged implementation kept "just
     in case" is the failure this rule exists to catch.

4. **Create `tooling/verify/baselines/graph_impls.retired`.** One record per
   line, tab- or pipe-free, of the exact form
   `<key>|<fnPrefix>|<locus>`. It is APPEND-ONLY: a key enters it in the same
   commit that removes it from `registry.js`, and is never removed. Seed it
   empty in this brief - brief -c appends `relation_cytoscape`. Add a header
   comment recording that append-only rule.

5. **Vacuous-proof the new path.** Zero live entries plus zero retired
   records is a FAILURE (nothing was ever registered, so nothing is proven).
   A retired record whose `locus` file does not exist is a FAILURE. A
   malformed record line is a FAILURE. Follow the existing FAILURES /
   `fail()` / `_report_and_exit(counts)` idiom already in the file.

6. **Extend the pass message** so it reports both counts: live entries
   checked and retired implementations proven absent.

## Scope OUT

- **Converging the relation graph, or touching `registry.js`.** Brief -c.
  This step leaves `relation_cytoscape` live and the check passing on it
  exactly as today.
- **Appending anything to `graph_impls.retired`.** It ships empty.
- **Touching rules 1, 2, 6, 7, 8, 9.** The GONE token list grows in -c, not
  here.
- **Touching `graph_impls.baseline`.** It never shrinks; it is the ceiling.
- **Any other check.** `relation_graph.py` is re-homed in -c.

## Invariants to defend

- **Fail-closed over advisory.** The amendment makes the check pass in one
  new circumstance; every added path must have its own failure mode. If a
  reader cannot name what makes rule 5b fail, it is not a rule.
- **Vacuous-proof guards on all verify checks** (standing rule). Zero
  collected records is a failure, never a trivially satisfied comparison.
- **No structure without a reader (E2).** `graph_impls.retired` ships with
  its reader in the same commit.

## Done means

- [ ] With the tree unchanged, `python tooling/verify/checks/graph_primitive.py`
      exits 0 and its pass line reports 1 live entry, 0 retired.
- [ ] On a scratch copy with `registry.js`'s single entry deleted and no
      matching record in `graph_impls.retired`, the check exits 1 with a
      failure naming `relation_cytoscape` as unproven.
- [ ] On a scratch copy with the entry deleted, a correct record appended,
      and `relGraph` still present in `index.html`, the check exits 1.
- [ ] On a scratch copy with the entry deleted, a correct record appended,
      and every `relGraph` occurrence stripped from a copy of `index.html`,
      the check exits 0 and reports 0 live, 1 retired.
- [ ] With `graph_impls.retired` deleted, the check exits 1.
- [ ] `tooling/verify/baselines/graph_impls.retired` exists, is empty of
      records, and carries the append-only header comment.
- [ ] `/review-step` and `/close-step` run; one commit.

## Docs to update

None yet. The doctrine sentence - the lock now proves convergence rather
than presence - is written once, in brief -l's ARCHITECTURE_DECISIONS entry.
