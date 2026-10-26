"""Approach A - keyword/regex rules baseline (no training).

Written from general logistics-ops knowledge, NOT tuned on the test split.
It has simple negation handling ("no injuries", "nobody was hurt") because a
baseline without it would be a strawman. It has no probabilities, so it can
only "abstain" when no rule fires (-> unclear_other).
"""
import re

CATEGORY_PATTERNS = {
    "accident_injury": r"\b(injur\w*|hurt|bleed\w*|ambulance|collid\w*|collision|crash\w*|accident|fender|unconscious|"
                       r"casualt\w*|first aid|chest pain|trapped|overturn\w*|rolled over|near miss|struck)\b",
    "hazmat_spill": r"\b(spill\w*|hazmat|fumes?|vapou?r|chemical|corrosive|acid|toxic|gas|cylinders?|leak\w*|aerosol|"
                    r"flammable|fuel|diesel|solvent|pesticide|ammonia|chlorine|drums?|oil)\b",
    "theft_security": r"\b(theft|stolen|steal\w*|pilfer\w*|break-?in|hijack\w*|armed|robber\w*|tamper\w*|"
                      r"cctv|suspects?|intruder|burglar\w*|knife|threaten\w*)\b",
    "cargo_damage": r"\b(damag\w*|crushed|dented|cracked|broken|torn|collapsed|wet|water damage|rejected)\b",
    "delay_late": r"\b(late|delay\w*|eta|behind schedule|congestion|missed (the )?(delivery )?window|not arrived|"
                  r"reschedul\w*|overdue)\b",
    "vehicle_breakdown": r"\b(broke down|breakdown|engine|tyre|tire|brakes?|battery|stalled|check engine|gearbox|"
                         r"axle|steering|workshop|radiator|clutch)\b",
    "customs_documentation": r"\b(customs?|hs code|bill of lading|invoice|declaration|permit|certificate of origin|"
                             r"clearance|manifest|duty|broker|packing list|cut-?off)\b",
    "misdelivery_lost": r"\b(wrong address|wrong unit|wrong office|misdeliver\w*|lost|missing|proof of delivery|"
                        r"pod|delivered to the wrong|non-delivery)\b",
}
# NOTE (author leakage): a first draft of these patterns contained ~25 words copied from the generator's own
# templates (e.g. "ankle", "bollard", "padlock", "siphon", "claim form"). That made the baseline look better than
# it is, so they were removed before any reported result; only generic ops vocabulary remains.
# order used to break ties: safety first
TIE_ORDER = ["accident_injury", "hazmat_spill", "theft_security", "vehicle_breakdown", "customs_documentation",
             "misdelivery_lost", "cargo_damage", "delay_late"]

# strong urgent cues (high precision) and weaker ones
URGENT_STRONG = (r"\b(ambulance|bleeding|unconscious|not responding|trapped|casualty|flames?|fire|explosion|evacuat\w*|"
                 r"fumes|vapou?r cloud|hijack\w*|armed|knife|held|in progress|brakes failed|"
                 r"expire\w*|seize|surgery|hospital|medical)\b")
URGENT_WEAK = r"\b(urgent|asap|emergency|immediately|now|serious|escalat\w*|cut-?off)\b"

NEGATORS = {"no", "not", "nobody", "without", "never", "zero", "nothing", "none", "neither", "thankfully", "fortunately"}
_tok = re.compile(r"[a-z0-9'\-/]+")


def _negated(text, start):
    """True if one of the 3 tokens before position `start` is a negator."""
    before = _tok.findall(text[:start].lower())[-3:]
    return any(t in NEGATORS for t in before)


def _count(pattern, text, respect_negation=True):
    n = 0
    for m in re.finditer(pattern, text, flags=re.I):
        if respect_negation and _negated(text, m.start()):
            continue
        n += 1
    return n


class RulesTriage:
    name = "rules_baseline"

    def __init__(self, extra_patterns=None, extra_urgent=None):
        """extra_patterns: {category: regex} added at runtime (used to show how fast rules adapt to a new category)."""
        self.patterns = dict(CATEGORY_PATTERNS)
        self.tie_order = list(TIE_ORDER)
        self.extra_urgent = extra_urgent
        for c, pat in (extra_patterns or {}).items():
            self.patterns[c] = pat
            self.tie_order.append(c)

    def predict_one(self, text):
        scores = {c: _count(p, text) for c, p in self.patterns.items()}
        best = max(scores.values())
        if best == 0:
            cat = "unclear_other"
        else:
            tied = [c for c in self.tie_order if scores[c] == best]
            cat = tied[0]
        strong = _count(URGENT_STRONG, text)
        if self.extra_urgent:
            strong += _count(self.extra_urgent, text)
        weak = _count(URGENT_WEAK, text)
        # urgent if any strong cue, or weak cue on a safety-critical category
        urgent = strong > 0 or (weak > 0 and cat in ("accident_injury", "hazmat_spill", "theft_security", "unclear_other"))
        return {"category": cat, "p_category": None, "urgent": bool(urgent), "p_urgent": None,
                "abstain": cat == "unclear_other", "strong_urgent_cue": strong > 0}

    def predict(self, texts):
        return [self.predict_one(t) for t in texts]


def strong_urgent_cue(text):
    """Used by the hybrid approach as a recall-oriented safety net."""
    return _count(URGENT_STRONG, text) > 0


RULE_CATS = list(CATEGORY_PATTERNS)


def rule_features(texts, weight=3.0):
    """Dense matrix of negation-aware rule hit counts (capped at 3, scaled to 0..weight).
    Lets the ML model use general domain knowledge when the training phrasing is narrow."""
    import numpy as np
    M = [[_count(CATEGORY_PATTERNS[c], t) for c in RULE_CATS] + [_count(URGENT_STRONG, t), _count(URGENT_WEAK, t)]
         for t in texts]
    return np.minimum(np.array(M, dtype=float), 3.0) / 3.0 * weight
