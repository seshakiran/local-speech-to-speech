from speech_to_speech.pipeline.wake_word import apply_wake_word_gate, parse_wake_words


def test_parse_wake_words_accepts_comma_separated_string():
    assert parse_wake_words("hey alice, okay assistant, ") == ("hey alice", "okay assistant")


def test_wake_word_gate_passes_through_when_disabled():
    result = apply_wake_word_gate("hello there", "hey alice", enabled=False)

    assert result.activated is True
    assert result.transcript == "hello there"


def test_wake_word_gate_strips_matched_phrase():
    result = apply_wake_word_gate("Hey Alice, what time is it?", "hey alice", enabled=True)

    assert result.activated is True
    assert result.matched_phrase == "hey alice"
    assert result.transcript == "what time is it?"


def test_wake_word_gate_rejects_transcript_without_phrase():
    result = apply_wake_word_gate("what time is it?", "hey alice", enabled=True)

    assert result.activated is False
    assert result.transcript == "what time is it?"


def test_wake_word_gate_uses_word_boundaries():
    result = apply_wake_word_gate("malice is not a wake word", "alice", enabled=True)

    assert result.activated is False
