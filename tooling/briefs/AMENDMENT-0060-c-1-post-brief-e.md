# AMENDMENT 1 to BRIEF-0060-c — resume after BRIEF-0060-e

Paste into the live `BRIEF-0060-c` execution session. Everything in
`BRIEF-0060-c` stands unchanged except the items amended below.

---

## Why you were right to stop

Both findings were verified independently against `main`, and both are
correct. Refusing to guess was the right call.

One correction to the framing, because it determines where the fix belonged
and it should not travel forward as a belief about your own work:

**The three `local-badge` / `spacer` / `sub` results were not false positives
of your rule.** They were a pre-existing fail-open in the *merged* rule7
surfacing for the first time. `BASE_RULE_RE`'s self-compound branch accepted a
Svelte scope hash — `.spacer.svelte-13t3afu` matched and yielded `spacer` —
so every component-scoped rule leaked into the global reachable set.
Measured on `main` before the repair: the built bundle contributed 11 class
names to `REACHABLE`, **all 11** via a hashed selector, **0** legitimately.
Your legacy half fed that same set into the stranding side of the formula,
where an over-grant flips from harmless to a false failure. Your diagnosis was
exact.

`BRIEF-0060-e` has since merged and repaired both defects:

- **Commit 1 (J1)** — `BASE_RULE_RE`'s final branch is now
  `(?:\.(?!svelte-)[\w-]+)`. The bundle contributes 0 class names. The
  existing rule7 half was measured green before and after; the repair had zero
  blast radius.
- **Commit 2 (K1)** — `.row-table` and `.row-card` moved from `creation.css`
  to `shared.css`, where both documents can read them.
  `.row-card-actions` deliberately stayed in `creation.css`: no legacy
  consumer.

---

## AMENDMENT 1 — mini-RECON gains three items

Run these **before** re-running your implementation. If any fails, `-e` has
not merged into your branch and you must STOP rather than compensate.

9. `tooling/verify/checks/stylesheet_partition.py` — confirm `BASE_RULE_RE`'s
   final branch carries the `(?!svelte-)` lookahead and that the
   TICKET-0060/BRIEF-0060-e comment sits above the constant. Confirm
   `.spacer.svelte-13t3afu` no longer matches.
10. `frontend/public/shared.css` — confirm `.row-table` and `.row-card` are
    declared there under a "Row containers" banner, and
    `frontend/public/creation.css` — confirm both are absent and
    `.row-card-actions` remains.
11. Re-measure the bundle's contribution to `_reachable_names()` and report
    it. The class count must be **0**.

Your original mini-RECON item 6 (the pre-`BRIEF-0060-b` SHA) still stands, and
you now also need the pre-`BRIEF-0060-e` `creation.css` for the second
historical red test below.

---

## AMENDMENT 2 — the acceptance criterion was wrong

Strike this line from **Done means**:

> - [ ] `… stylesheet_partition.py` exits 0 on unmodified `main`.

It was an inference, not a measurement: the Observation surface's 13 classes
were measured and the result generalised to the legacy document's 81 without
counting them. Replace with:

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/stylesheet_partition.py`
      exits 0 at HEAD on a tree where `BRIEF-0060-b` and `BRIEF-0060-e` have
      merged.
- [ ] The check **reports the computed `STRANDED(legacy)` set explicitly,
      including when it is empty.** A silent green does not distinguish "no
      strandings" from "the scan found nothing to scan".
- [ ] The reported set is empty for both namespaces. **If it is not empty,
      STOP and escalate — do not move any CSS.** Scope OUT item 3 of
      `BRIEF-0060-c` is unchanged: this brief writes a check, it does not fix
      what the check finds.

For reference, the complete legacy stranded set measured on `main` before
`BRIEF-0060-b` was:

```
classes -> ['r-err', 'r-warn', 'row-card', 'row-table']
ids     -> []
```

`r-err` and `r-warn` left with Observation in `-b` (decision D1);
`row-card` and `row-table` were unstranded by `-e` (decision K1). The expected
residue is therefore empty. Eight further classes that `index.html` applies
are styled nowhere at all; they are correctly **not** in the set, and if your
implementation flags any of them the intersection term is wrong.

---

## AMENDMENT 3 — a second historical red test

Your red-test list gains one case, between the existing "historical case" and
"live case":

- **The Play case.** Materialise the pre-`BRIEF-0060-e` `creation.css`
  (with `.row-table` and `.row-card` still in it) alongside the current
  `index.html`, and run the check. It must FAIL naming **both** classes. This
  proves the rule catches the Play knowledge-rows bug and not only the
  Observation one — two independent surfaces, one failure mode, one rule.

The existing historical case is unchanged: pre-`BRIEF-0060-b` `index.html`
plus a `creation.css` carrying `.r-warn` / `.r-err` must FAIL naming both.

---

## AMENDMENT 4 — PASS line reporting

Your Scope IN item 6 said to extend the PASS line with the legacy half's
counts. Tighten it: the line must report applied class names, applied id
names, **and the stranded count**, and the check must fail its vacuity guards
rather than print a zero it did not earn. A reader must be able to tell from
one line that the legacy half ran, what it scanned, and what it concluded.

---

## AMENDMENT 5 — anchor discipline

Your report cited `index.html:1769-1770` for the `row-card` / `row-table`
application. On `main` those lines are **1855-1856**, inside
`loadPlayerKnowledge`. The difference is `BRIEF-0060-b`'s deletions on your
branch, so your figure is probably right for your tree — but the two were
stated as if interchangeable.

Going forward, cite `file:line` against the tree you actually ran on and say
which tree that is. A brief's anchors are `main`-as-of-authoring and drift as
tickets land; a divergence is information, not noise, and it is worth one
sentence in the report.

---

## Unchanged

Everything else in `BRIEF-0060-c` stands: the four vacuity guards, the
retirement alarm keyed on an empty `LEGACY_MOUNTS`, the narrowed
`REACHABLE(legacy) = shared.css ∪ inline`, the intersection term, the
namespace separation, the whole Scope OUT list, and the invariants.

In particular, **Scope OUT item 4 is reaffirmed and now matters more**: do not
widen `REACHABLE(legacy)` to make a finding go away. `-e` narrowed the global
reachable set precisely so this rule could be strict. A green obtained by
unioning `creation.css` or the bundle back in would re-open both defects at
once.
