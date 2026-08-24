"""The T1 judge for day narration (TICKET-0075, BRIEF-0075-d, Scope IN item
4). Python only — no model, no `chat(` anywhere in this module. Fail-closed
and vacuity-guarded: a judge that checks nothing and silently passes is the
single worst outcome this module could produce (the anti-vacuity guards
below exist for exactly that reason, R5).

What this module proves, and — just as important — what it does NOT prove:
name containment proves no proper name outside `fact_sheet.authorised_names`
appears in the prose; it does NOT prove the prose is coherent, and it does
NOT prove a role hint was rendered as a function rather than quietly
dropped (a beat that mentions no one at all still passes name containment).
Outcome survival proves the prose contains, for each band present on the
fact sheet, AT LEAST as many band markers as there are steps of that band
— a count, not a per-step positional match — so two same-band steps are
provably both rendered in aggregate, not individually pinned to their own
sentence.

Name-extraction heuristic (documented per the brief's own STOP condition:
"a weak extractor makes this check vacuous"): the prose's `[MARKER]` band
tags (`day_narration.BAND_MARKERS` — all-caps, structural, never narrative
content) are stripped first, so a marker like `[RÉUSSITE]` can never fuse
onto the name that follows it. What remains is scanned for a run of one or
more consecutive capitalized words, optionally bridged by a lowercase
connector (de/du/des/le/la/l'/d'/von/van) followed by another capitalized
word.

A run that is a SINGLE capitalized word at the very start of a sentence is
discarded ONLY when that word, case-folded, is a known French function
word (`_SENTENCE_INITIAL_STOPWORDS` — articles, pronouns, prepositions,
conjunctions: "Le marchand refuse." must not false-positive "Le" as a
name). A sentence-initial word NOT on that stoplist is kept — a name is
exactly as likely to open a sentence as to sit mid-sentence ("Jehan
insiste." must not be silently dropped, or a real unauthorised name in
the same position would slip past just as invisibly). A multi-word run is
always kept regardless of position. This is a real, if imperfect,
detector — not a rule that discards everything (the vacuity failure this
brief warns against) nor one so broad it discards genuine signal.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .day_narration import BAND_MARKERS
from .day_resolve import FactSheet

_CONNECTORS = frozenset({"de", "du", "des", "le", "la", "l'", "d'", "von", "van"})
_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ'-]+|[.!?]+")
_MARKER_RE = re.compile(r"\[[^\[\]]*\]")

# Sentence-initial capitalized function words — the ONLY case a lone
# single-word capitalized run is discarded (see module docstring). Closed
# word classes (articles, pronouns, prepositions, conjunctions) plus the
# common discourse/temporal adverbs a narrative model reaches for to open
# a sentence. Necessarily incomplete — French has no small closed set of
# "words that can never be a name" — so this stays a real, if imperfect,
# detector (module docstring) rather than a claim of completeness.
_SENTENCE_INITIAL_STOPWORDS = frozenset({
    "le", "la", "les", "un", "une", "des", "ce", "cet", "cette", "ces",
    "il", "elle", "ils", "elles", "on", "nous", "vous", "tu", "je",
    "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes", "notre",
    "votre", "leur", "leurs", "au", "aux", "du", "de", "en", "dans", "à",
    "y",
    "sur", "sous", "avec", "sans", "pour", "par", "vers", "chez", "entre",
    "parmi", "selon", "sauf", "hormis", "outre", "hors", "devant",
    "derrière", "pendant", "durant", "depuis", "dès", "jusque", "malgré",
    "grâce", "contre",
    "après", "avant", "puis", "ensuite", "alors", "mais", "et", "ou",
    "donc", "or", "ni", "car", "si", "quand", "lorsque", "comme",
    "pourtant", "cependant", "néanmoins", "toutefois", "enfin", "soudain",
    "soudainement", "brusquement", "finalement", "ainsi", "aussi",
    "encore", "toujours", "jamais", "parfois", "souvent", "rarement",
    "beaucoup", "peu", "trop", "assez", "plus", "moins", "très", "bien",
    "mal", "vite", "lentement", "doucement", "voici", "voilà",
    "quoi", "que", "qui", "dont", "où", "comment", "pourquoi", "combien",
    "certes", "d'abord", "d'ailleurs", "lors", "cela", "ceci", "celui",
    "celle", "ceux", "celles",
})


@dataclass(frozen=True)
class JudgeVerdict:
    passed: bool
    reason: str


def extract_names(prose: str) -> frozenset[str]:
    """Deterministic name-candidate extraction — see the module docstring
    for the exact rule."""
    prose = _MARKER_RE.sub(" ", prose)
    tokens: list[tuple[str, bool]] = []
    sentence_initial = True
    for match in _TOKEN_RE.finditer(prose):
        tok = match.group()
        if tok[0] in ".!?":
            sentence_initial = True
            continue
        tokens.append((tok, sentence_initial))
        sentence_initial = False

    names: set[str] = set()
    i = 0
    while i < len(tokens):
        word, is_initial = tokens[i]
        if not word[0].isupper():
            i += 1
            continue
        run = [word]
        j = i + 1
        while j < len(tokens):
            nxt, _ = tokens[j]
            if nxt[0].isupper():
                run.append(nxt)
                j += 1
            elif nxt.lower() in _CONNECTORS and j + 1 < len(tokens) and tokens[j + 1][0][0].isupper():
                run.append(nxt)
                j += 1
            else:
                break
        if len(run) > 1 or not (is_initial and word.casefold() in _SENTENCE_INITIAL_STOPWORDS):
            names.add(" ".join(run))
        i = j
    return frozenset(names)


def _missing_band_markers(prose: str, fact_sheet: FactSheet) -> list[str]:
    """Outcome survival: the prose must carry at least as many occurrences
    of each band's marker as there are steps of that band on the fact
    sheet. Returns the objectives of every step whose band is under-
    represented (for the failure message) — empty when every band's count
    is satisfied."""
    needed = Counter(step.band for step in fact_sheet.steps)
    missing_objectives: list[str] = []
    for band, count in needed.items():
        marker = BAND_MARKERS[band]
        if prose.count(marker) < count:
            missing_objectives.extend(s.objective for s in fact_sheet.steps if s.band == band)
    return missing_objectives


def judge_narration(prose: str, fact_sheet: FactSheet) -> JudgeVerdict:
    """The T1 judge (Scope IN item 4). Fail-closed: any of the checks
    below not passing is a FAILURE, reported by name, never a silent
    degrade."""
    extracted = extract_names(prose)
    if not extracted:
        # Anti-vacuity (R5): zero names extracted is a FAILURE, not a pass —
        # this line, and the one below, are the single most important
        # lines in this module.
        return JudgeVerdict(passed=False, reason="anti-vacuity: zero names extracted from the prose")

    unauthorised = sorted(n for n in extracted if n not in fact_sheet.authorised_names)
    if unauthorised:
        return JudgeVerdict(
            passed=False, reason=f"unauthorised name(s) not in authorised_names: {', '.join(unauthorised)}",
        )

    if not fact_sheet.steps:
        return JudgeVerdict(passed=False, reason="anti-vacuity: zero steps on the fact sheet")

    missing = _missing_band_markers(prose, fact_sheet)
    if missing:
        return JudgeVerdict(
            passed=False, reason=f"step(s) not discernible in the prose (band marker missing): {', '.join(missing)}",
        )

    return JudgeVerdict(passed=True, reason="ok")
