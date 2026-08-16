from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WakeWordResult:
    activated: bool
    transcript: str
    matched_phrase: str | None = None


def parse_wake_words(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_words = value.split(",")
    else:
        raw_words = list(value)
    return tuple(word.strip() for word in raw_words if word and word.strip())


def apply_wake_word_gate(
    transcript: str,
    wake_words: str | list[str] | tuple[str, ...] | None,
    *,
    enabled: bool = False,
    strip_wake_word: bool = True,
) -> WakeWordResult:
    """Return whether *transcript* should activate the assistant.

    Matching is transcript-level and phrase-based, intended for STT outputs such
    as "hey alice what's the weather". It uses word boundaries so "malice" does
    not match "alice".
    """

    text = transcript.strip()
    if not enabled:
        return WakeWordResult(activated=True, transcript=text)

    phrases = parse_wake_words(wake_words)
    if not phrases:
        return WakeWordResult(activated=True, transcript=text)

    for phrase in phrases:
        pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
        match = pattern.search(text)
        if match is None:
            continue

        if not strip_wake_word:
            return WakeWordResult(activated=True, transcript=text, matched_phrase=phrase)

        stripped = f"{text[: match.start()]} {text[match.end() :]}".strip()
        stripped = re.sub(r"^[\s,.:;!?-]+", "", stripped).strip()
        stripped = re.sub(r"\s+", " ", stripped)
        return WakeWordResult(activated=True, transcript=stripped, matched_phrase=phrase)

    return WakeWordResult(activated=False, transcript=text)
