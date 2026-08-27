# BRIEF — Step "context disclosure floor"

## Context

TICKET-0051 decision E2. Today `assemble_npc_context` derives ONE intensity —
the speaking NPC's relation toward its interlocutor — and uses it for two
different jobs: deciding what the NPC may DISCLOSE, and colouring how it
PERCEIVES those present. With a single interlocutor that conflation is
harmless. With a plural audience it is a leak: an NPC that trusts Maelis will
disclose in front of Reike, who is standing right there and is trusted by
nobody.

Observed scenes make the plural case the normal case, so this must be fixed
before any loop runs. It is independent of BRIEF-0051-a and may land first.

The rule: **disclosure is gated by the worst-disposed listener present, not by
the addressee.** Perception stays keyed on the addressee — that part is
correct today.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate rather than adapting the design.

1. **Intensity derivation** — `context.py:503`
   (`intensity = inter_relation.intensity if inter_relation else
   NEUTRAL_INTENSITY`, `NEUTRAL_INTENSITY = 50` at `context.py:63`). Confirm it
   is the ONLY derivation and that it feeds both `_npc_context_speak`
   (`context.py:314`) and `_npc_context_perception` (`context.py:334`).
2. **Gating predicate** — confirm `intensity >= k.share_threshold`
   (`context.py:323`) is the only disclosure filter, and report every other
   `share_threshold` comparison in `src/`.
3. **Audience source** — how the set of NPCs co-present at a location is
   obtained today. `_npc_context_company` (`context.py:383-412`) is one
   reader; report whether the `gathering` / `gathering_member` roster
   (`left_at IS NULL`, cf. `analyzer.py:443-456`) is available at the
   `assemble_npc_context` call site or must be passed in.
4. **The five call sites** — `play_initiative.py:110`,
   `play_physical.py:219`, `play.py:569`, `routes/prompts.py:60`,
   `routes/play.py:111`. For each: is a plural audience knowable there, and is
   the call inside or outside a live turn?
5. **Player exclusion** — `_npc_context_company` (`context.py:391`) filters
   `Character.character_type != "player"`. Report exactly how, since a future
   `player_presence='silent'` must count as an auditor here (named deferral
   H2, not implemented in this brief).
6. **Module budget** — current line and top-level-function count of
   `context.py` against the 40/1000 caps.

## Scope IN

### 1. Split the single intensity into two named values

In `assemble_npc_context` (`context.py:460`), keep the existing derivation as
the **interlocutor** intensity, and derive a second **disclosure** intensity:

- `inter_intensity` — unchanged, `inter_relation.intensity` or
  `NEUTRAL_INTENSITY`. Passed to `_npc_context_perception` exactly as today.
- `disclosure_intensity` — the MINIMUM, over every auditor present, of the
  speaking NPC's relation intensity toward that auditor, with
  `NEUTRAL_INTENSITY` substituted where no relation row exists. The
  interlocutor is always a member of the auditor set. Passed to
  `_npc_context_speak`.

With a single auditor the two values are equal by construction and today's
behaviour is bit-identical. This is the property the check in item 4 asserts.

### 2. New parameter with a behaviour-preserving default

`assemble_npc_context` gains `audience_ids: list[str] | None = None`.

- `None` (all five existing call sites, unchanged) -> the auditor set is
  `[interlocutor_id]` -> `disclosure_intensity == inter_intensity` -> no
  behaviour change.
- A non-empty list -> the auditor set is that list plus `interlocutor_id`,
  de-duplicated.
- An EMPTY list is not "no audience": raise `ValueError`. An empty list is a
  caller bug, and silently treating it as "disclose freely" is the exact
  failure this brief exists to prevent.

`_npc_context_speak` (`context.py:314`) keeps its signature; it already takes a
scalar. Only the value handed to it changes. Rename its parameter to
`disclosure_intensity` for readability; do NOT change its logic.

### 3. Docstring, verbatim

On `assemble_npc_context`:

```
audience_ids: every entity that can HEAR this NPC speak, beyond the
addressee. Disclosure is gated on the LOWEST relation intensity across the
whole audience (fail-closed), because a secret told to a trusted addressee
in front of a distrusted bystander is disclosed to the bystander too.
Perception stays keyed on the addressee alone — that is about manner, not
about facts. None means single-auditor and reproduces pre-v1.90 behaviour
exactly; an empty list raises, since "nobody is listening" is never a
reason to disclose more.
```

### 4. Verify check `tooling/verify/checks/context_disclosure_floor.py`

`FAILURES` list + `_report_and_exit`, `ROOT` via `parents[3]`.

- **Rule 1** (behavioural, in-process, temp DB): build a world with NPC A,
  auditors B and C, A->B intensity 80, A->C intensity 10, and a knowledge row
  on A with `share_threshold` 50. Assert the fact appears with
  `audience_ids=[B]` and is ABSENT with `audience_ids=[B, C]`. This asserts
  the floor, not merely that a parameter exists.
- **Rule 2**: `assemble_npc_context(..., audience_ids=[])` raises `ValueError`.
- **Rule 3** (regression): for the same fixture, `audience_ids=None` and
  `audience_ids=[B]` produce byte-identical output.
- **Rule 4** (AST): `_npc_context_perception` is never called with the
  disclosure intensity — the two values are not re-conflated downstream.
- **Rule 5, vacuous-proof guard**: if the fixture produced zero knowledge rows
  or the assembled context is empty, FAIL. A rule that passes because nothing
  was disclosed is not a passing rule.

## Scope OUT

- **`share_threshold` semantics.** The threshold values, the ladder, and the
  rubric are untouched. Only WHICH intensity is compared changes.
- **`character.secrets`.** Creator meta-narrative, read by no assembler.
  Do not touch it, do not add it to any context section.
- **`knowledge.is_secret` filtering** and every other structural exclusion:
  unchanged.
- **Perception.** `_npc_context_perception` keeps the interlocutor intensity.
  Do not "improve" it to use the floor — that would flatten how an NPC sees
  its addressee, which is a manner concern, not a disclosure concern.
- **Call-site changes.** All five existing callers keep passing nothing. The
  first real audience is supplied by BRIEF-0051-e's runner.
- **`player_presence='silent'`.** Named deferral H2. `_npc_context_company`
  (`context.py:391`) is reported by the mini-RECON and left ALONE.
- **Observation tables.** This brief has no dependency on BRIEF-0051-a and
  writes nothing.
- **Any model call, prompt, or template.**

## Invariants to defend

- **Exclusion is structural, never instructional.** The floor is computed at
  query/assembly construction. No prompt is ever told "do not mention X in
  front of Y".
- **Fail-closed over advisory.** Missing relation -> `NEUTRAL_INTENSITY`, not
  "assume trust". Empty audience -> raise, not disclose.
- **Behaviour preservation is asserted, not assumed.** Rule 3 exists because
  this touches the disclosure path of the live game.

## Done means

- [ ] `python tooling/verify/checks/context_disclosure_floor.py` exits 0 and
      its output names a non-zero count of disclosed facts in the fixture.
- [ ] Rule 1 fails if the floor is reverted to the interlocutor intensity
      (demonstrate by temporarily reverting, then restore).
- [ ] A live conversation with a single NPC produces the same context as
      before the change (spot-check via the Prompts tab preview).
- [ ] `grep -rn "audience_ids" src/` shows the parameter defined once and
      passed by no existing caller.
- [ ] `context.py` remains within 40 functions / 1000 lines.
- [ ] Full-tree verify passes.

## Docs to update

`world-engine-schema.md` is NOT touched (no schema change).
`ARCHITECTURE_DECISIONS.md`: subsection under the TICKET-0051 section recording
E2 — the worst-case-listener floor, why perception stays keyed on the
addressee, and why an empty audience raises. `DECISIONS_INDEX.md` entry.
`CLAUDE.md` unchanged.
