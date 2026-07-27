from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_MEMORY_COMMAND_RE = re.compile(
    r"^\s*(?:please\s+)?(?:remember|note)\s+(?:that\s+)?(?P<fact>.+?)\s*[.?!]?\s*$",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "can",
    "for",
    "from",
    "have",
    "how",
    "that",
    "the",
    "this",
    "what",
    "when",
    "where",
    "with",
    "you",
    "your",
}


@dataclass(frozen=True)
class MemoryFact:
    text: str
    created_at: str


def extract_memory_fact(transcript: str) -> str | None:
    match = _MEMORY_COMMAND_RE.match(transcript)
    if match is None:
        return None
    fact = re.sub(r"\s+", " ", match.group("fact")).strip()
    return fact or None


class LocalMemoryStore:
    def __init__(self, path: str | Path, *, max_prompt_items: int = 8) -> None:
        self.path = Path(path).expanduser()
        self.max_prompt_items = max(1, max_prompt_items)
        self._lock = Lock()

    def add_fact(self, fact: str) -> MemoryFact:
        text = re.sub(r"\s+", " ", fact).strip()
        if not text:
            raise ValueError("Memory fact cannot be empty.")
        item = MemoryFact(text=text, created_at=datetime.now(timezone.utc).isoformat())
        with self._lock:
            data = self._read_unlocked()
            if not any(entry.get("text") == text for entry in data):
                data.append({"text": item.text, "created_at": item.created_at})
                self._write_unlocked(data)
        logger.info("Stored local memory fact: %s", text)
        return item

    def remember_from_transcript(self, transcript: str) -> MemoryFact | None:
        fact = extract_memory_fact(transcript)
        if fact is None:
            return None
        return self.add_fact(fact)

    def relevant_facts(self, query: str, *, limit: int | None = None) -> list[MemoryFact]:
        limit = limit or self.max_prompt_items
        with self._lock:
            data = self._read_unlocked()
        facts = [MemoryFact(text=str(entry.get("text", "")), created_at=str(entry.get("created_at", ""))) for entry in data]
        facts = [fact for fact in facts if fact.text]
        if not facts:
            return []

        query_tokens = _tokens(query)
        if not query_tokens:
            return facts[-limit:]

        scored: list[tuple[int, int, MemoryFact]] = []
        for index, fact in enumerate(facts):
            overlap = len(query_tokens & _tokens(fact.text))
            if overlap:
                scored.append((overlap, index, fact))
        if not scored:
            return facts[-limit:]
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [fact for _, _, fact in scored[:limit]]

    def build_prompt_context(self, query: str) -> str:
        facts = self.relevant_facts(query, limit=self.max_prompt_items)
        if not facts:
            return ""
        lines = ["Remembered user facts:"]
        lines.extend(f"- {fact.text}" for fact in facts)
        return "\n".join(lines)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid memory JSON at %s", self.path)
            return []
        return raw if isinstance(raw, list) else []

    def _write_unlocked(self, data: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _tokens(text: str) -> set[str]:
    return {token for token in _WORD_RE.findall(text.lower()) if len(token) >= 3 and token not in _STOPWORDS}
