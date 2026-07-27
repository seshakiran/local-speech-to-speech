from __future__ import annotations

from typing import Any

from speech_to_speech.LLM.chat import Chat, make_user_message


def apply_memory_context(chat: Chat, runtime_config: Any) -> None:
    memory_store = getattr(runtime_config, "memory_store", None)
    if memory_store is None:
        return
    query = getattr(runtime_config, "last_user_transcript", "") or ""
    context = memory_store.build_prompt_context(query)
    if context:
        chat.add_item(make_user_message(f"Context from local memory:\n{context}"))
