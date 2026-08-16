import json

from speech_to_speech.api.openai_realtime.runtime_config import RuntimeConfig
from speech_to_speech.LLM.chat import Chat
from speech_to_speech.LLM.memory_prompt import apply_memory_context
from speech_to_speech.memory.local_memory import LocalMemoryStore, extract_memory_fact
from speech_to_speech.pipeline.messages import Transcription
from speech_to_speech.STT.transcription_notifier import TranscriptionNotifier


def test_extract_memory_fact_accepts_explicit_remember_phrases():
    assert extract_memory_fact("remember that my editor is Neovim") == "my editor is Neovim"
    assert extract_memory_fact("Please note that I prefer brief answers.") == "I prefer brief answers"
    assert extract_memory_fact("what is my editor") is None


def test_local_memory_store_persists_and_deduplicates(tmp_path):
    path = tmp_path / "memories.json"
    store = LocalMemoryStore(path)

    store.add_fact("my editor is Neovim")
    store.add_fact("my editor is Neovim")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert [item["text"] for item in data] == ["my editor is Neovim"]


def test_local_memory_store_builds_relevant_prompt_context(tmp_path):
    store = LocalMemoryStore(tmp_path / "memories.json", max_prompt_items=1)
    store.add_fact("my editor is Neovim")
    store.add_fact("my dog is Fido")

    context = store.build_prompt_context("which editor do I use?")

    assert "my editor is Neovim" in context
    assert "my dog is Fido" not in context


def test_apply_memory_context_adds_ephemeral_user_context(tmp_path):
    store = LocalMemoryStore(tmp_path / "memories.json")
    store.add_fact("my editor is Neovim")
    cfg = RuntimeConfig(chat=Chat(10), memory_store=store, last_user_transcript="what editor do I use?")
    active_chat = cfg.chat.copy()

    apply_memory_context(active_chat, cfg)

    assert active_chat.buffer[-1].role == "user"
    assert "Context from local memory" in active_chat.buffer[-1].content[0].text
    assert cfg.chat.buffer == []


def test_transcription_notifier_stores_memory_fact(tmp_path):
    store = LocalMemoryStore(tmp_path / "memories.json")
    cfg = RuntimeConfig(memory_store=store)
    notifier = object.__new__(TranscriptionNotifier)
    notifier.setup(runtime_config=cfg)

    list(notifier.process(Transcription(text="remember that my editor is Neovim")))

    assert json.loads((tmp_path / "memories.json").read_text(encoding="utf-8"))[0]["text"] == "my editor is Neovim"
