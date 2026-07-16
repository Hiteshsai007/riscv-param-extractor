"""
Pass 1 — Deterministic Candidate Detection

This module implements the high-recall, permissive first pass of the pipeline.
It uses regex-based trigger keyword matching to identify candidate sentences
that MAY contain architectural parameters.

Design decision: Pass 1 is deterministic (no LLM call) because:
1. Cheaper — can run thousands of times for free during gold set development
2. Faster — no API latency
3. Fully reproducible — identical output every time
4. Simpler — removes one source of LLM variability

The LLM is reserved for Pass 2 where classification judgment is needed.
"""

import re
from dataclasses import dataclass

from schema.parameter_schema import CandidateSentence


# Trigger keywords ordered by specificity (most specific first).
# These are the linguistic signals that indicate potential implementation variability
# in RISC-V normative prose.
TRIGGER_KEYWORDS: list[str] = [
    # High-specificity: almost always indicates a parameter
    "implementation-defined",
    "implementation-specific",
    "implementation dependent",
    "implementation-dependent",
    # Medium-specificity: often indicates a parameter but needs classification
    "optionally",
    "optional",
    "may optionally",
    # Lower-specificity: frequently used for non-parameter statements too
    "might",
    "may",
    "should",
    # RISC-V specific field behavior markers
    "WARL",
    "WLRL",
    "WPRI",
]


def _split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using a regex-based approach.

    Handles common abbreviations and avoids splitting on:
    - Decimal numbers (e.g., "2.1")
    - Common abbreviations (e.g., "e.g.", "i.e.", "etc.")
    - Section references (e.g., "§2.1")

    This is intentionally simple — we don't need perfect NLP sentence
    segmentation, just good-enough splitting for candidate detection.
    Over-segmentation is acceptable (high recall > precision in Pass 1).
    """
    # Protect common abbreviations from being split
    protected = text
    abbreviations = ["e.g.", "i.e.", "etc.", "Fig.", "Sec.", "Ch.", "vol."]
    placeholders: dict[str, str] = {}
    for i, abbr in enumerate(abbreviations):
        placeholder = f"__ABBR{i}__"
        placeholders[placeholder] = abbr
        protected = protected.replace(abbr, placeholder)

    # Split on sentence-ending punctuation followed by whitespace and uppercase
    # or newline boundaries that look like paragraph breaks
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])|(?:\n\s*\n)', protected)

    # Restore abbreviations and clean up
    sentences = []
    for sent in raw_sentences:
        sent = sent.strip()
        if not sent:
            continue
        for placeholder, abbr in placeholders.items():
            sent = sent.replace(placeholder, abbr)
        sentences.append(sent)

    return sentences


def _find_trigger_in_sentence(sentence: str) -> list[str]:
    """
    Find all trigger keywords present in a sentence.

    Returns a list of matched keywords (may be multiple per sentence).
    Matching is case-insensitive for general keywords but case-sensitive
    for RISC-V specific terms (WARL, WLRL, WPRI).
    """
    found: list[str] = []
    sentence_lower = sentence.lower()

    for keyword in TRIGGER_KEYWORDS:
        # Case-sensitive matching for RISC-V field behavior acronyms
        if keyword in ("WARL", "WLRL", "WPRI"):
            if keyword in sentence:
                found.append(keyword)
        else:
            # Case-insensitive matching for general English keywords
            # Use word boundary matching to avoid partial matches
            # (e.g., "may" should not match "maybe")
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sentence_lower):
                found.append(keyword)

    return found


def detect_candidates(text: str) -> list[CandidateSentence]:
    """
    Pass 1: Detect candidate sentences containing trigger keywords.

    This is the high-recall pass — it intentionally over-extracts.
    Every sentence containing a trigger keyword is returned as a candidate.
    False positives are expected and will be filtered by Pass 2 (LLM classification).

    Args:
        text: Raw text snippet from the ISA manual.

    Returns:
        List of CandidateSentence objects, each containing the sentence,
        the trigger keyword that matched, and the sentence index.
        A sentence matching multiple keywords produces multiple candidates.
    """
    sentences = _split_into_sentences(text)
    candidates: list[CandidateSentence] = []

    for idx, sentence in enumerate(sentences):
        triggers = _find_trigger_in_sentence(sentence)
        for trigger in triggers:
            candidates.append(
                CandidateSentence(
                    sentence=sentence,
                    trigger_keyword=trigger,
                    sentence_index=idx,
                )
            )

    return candidates
