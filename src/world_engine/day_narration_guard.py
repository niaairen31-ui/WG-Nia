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

A run that is a SINGLE capitalized word is discarded when that word,
case-folded, is a known French function word (`_FUNCTION_WORD_STOPWORDS`
— articles, pronouns, prepositions, conjunctions), REGARDLESS of sentence
position. Position-gating this (discard only at sentence-start) was tried
first and live-tested wrong: French sentence punctuation is not the only
thing that precedes a capital in generated prose — a colon, a marker tag,
or the model's own inconsistent punctuation can put a function word
("Il", "En") in a position this module cannot reliably prove is
"sentence-initial," and a false negative there (treating a stray pronoun
as an invented name) is a real, observed failure, not a hypothetical one.
A multi-word run is always kept regardless of position — the false-
positive risk this trades away (a genuine one-word name that collides
with a function word, e.g. a character actually named "Il") is
vanishingly rare next to that. This is a real, if imperfect, detector —
not a rule that discards everything (the vacuity failure this brief warns
against) nor one so broad it discards genuine signal.
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

# Capitalized function words — the ONLY case a lone single-word
# capitalized run is discarded, at ANY position (see module docstring).
# Closed word classes (articles, pronouns, prepositions, conjunctions)
# plus the common discourse/temporal adverbs a narrative model reaches
# for to open a sentence. Necessarily incomplete — French has no small
# closed set of "words that can never be a name" — so this stays a real,
# if imperfect, detector (module docstring) rather than a claim of
# completeness.
_FUNCTION_WORD_STOPWORDS = frozenset({
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
    tokens = [m.group() for m in _TOKEN_RE.finditer(prose) if m.group()[0] not in ".!?"]

    names: set[str] = set()
    i = 0
    while i < len(tokens):
        word = tokens[i]
        if not word[0].isupper():
            i += 1
            continue
        run = [word]
        j = i + 1
        while j < len(tokens):
            nxt = tokens[j]
            if nxt[0].isupper():
                run.append(nxt)
                j += 1
            elif nxt.lower() in _CONNECTORS and j + 1 < len(tokens) and tokens[j + 1][0].isupper():
                run.append(nxt)
                j += 1
            else:
                break
        if len(run) > 1 or word.casefold() not in _FUNCTION_WORD_STOPWORDS:
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


def _authorised_words(fact_sheet: FactSheet) -> frozenset[str]:
    """Word-level expansion of `authorised_names` (live-discovered: a model
    naturally refers to a multi-word authorised name — "Joran Vey" — by
    ONE of its words alone — "Joran" — which is not itself a fabrication).
    Every word of every authorised full name is individually authorised in
    addition to the full name."""
    words: set[str] = set()
    for name in fact_sheet.authorised_names:
        words.update(name.split())
    return frozenset(words)


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

    # A candidate run passes if it is EITHER the full authorised string
    # verbatim, OR every one of its own words is individually authorised
    # (the "Joran" vs "Joran Vey" case). This also sharpens a merge
    # artifact like "Maelis En" (two adjacent capitalized words the
    # extractor could not tell apart from a real two-word name): only the
    # genuinely unauthorised word ("En") is reported, not the whole run.
    authorised_words = _authorised_words(fact_sheet)
    unauthorised: set[str] = set()
    for run in extracted:
        if run in fact_sheet.authorised_names:
            continue
        for word in run.split():
            if word not in authorised_words:
                unauthorised.add(word)
    if unauthorised:
        return JudgeVerdict(
            passed=False,
            reason=f"unauthorised name(s) not in authorised_names: {', '.join(sorted(unauthorised))}",
        )

    if not fact_sheet.steps:
        return JudgeVerdict(passed=False, reason="anti-vacuity: zero steps on the fact sheet")

    missing = _missing_band_markers(prose, fact_sheet)
    if missing:
        return JudgeVerdict(
            passed=False, reason=f"step(s) not discernible in the prose (band marker missing): {', '.join(missing)}",
        )

    return JudgeVerdict(passed=True, reason="ok")
