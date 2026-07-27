from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ModuleArguments:
    device: Optional[str] = field(
        default=None,
        metadata={"help": "If specified, overrides the device for all handlers."},
    )
    mode: Optional[Literal["local", "socket", "websocket", "realtime"]] = field(
        default="realtime",
        metadata={
            "help": "The mode to run the pipeline in. Either 'local', 'socket', 'websocket', or 'realtime'. Default is 'realtime'."
        },
    )
    local_mac_optimal_settings: bool = field(
        default=False,
        metadata={
            "help": "If specified, sets the optimal settings for Mac OS. Sets Parakeet TDT for STT, MLX LM for language model, and Qwen3-TTS for TTS, with MPS device and local mode."
        },
    )
    stt: Optional[
        Literal["whisper", "whisper-mlx", "mlx-audio-whisper", "faster-whisper", "parakeet-tdt", "paraformer"]
    ] = field(
        default="parakeet-tdt",
        metadata={
            "help": "The STT to use. Either 'whisper', 'whisper-mlx', 'mlx-audio-whisper', 'faster-whisper', 'parakeet-tdt', or 'paraformer'. Default is 'parakeet-tdt'."
        },
    )
    llm_backend: Optional[Literal["transformers", "mlx-lm", "responses-api", "chat-completions"]] = field(
        default="responses-api",
        metadata={
            "help": "The LLM backend to use. Either 'transformers', 'mlx-lm', 'responses-api', or "
            "'chat-completions' (OpenAI-compatible /v1/chat/completions). Default is 'responses-api'."
        },
    )
    tts: Optional[Literal["chatTTS", "facebookMMS", "pocket", "kokoro", "qwen3"]] = field(
        default="qwen3",
        metadata={
            "help": "The TTS to use. Either 'chatTTS', 'facebookMMS', 'pocket', 'kokoro', or 'qwen3'. Default is 'qwen3'."
        },
    )
    log_level: str = field(
        default="info",
        metadata={"help": "Provide logging level. Example --log_level debug, default=info."},
    )
    enable_live_transcription: bool = field(
        default=True,
        metadata={
            "help": "Enable live transcription display while user is speaking (works with parakeet-tdt). Default is true."
        },
    )
    live_transcription_update_interval: float = field(
        default=0.5,
        metadata={"help": "Update interval for live transcription in seconds (default: 0.5s = 500ms)"},
    )
    live_transcription_min_silence_ms: int = field(
        default=500,
        metadata={
            "help": "Minimum silence duration (ms) before ending speech when live transcription is enabled (default: 500ms)"
        },
    )
    num_pipelines: int = field(
        default=1,
        metadata={
            "help": "Number of isolated realtime pipelines in the pool. One uvicorn server listens on "
            "--ws_port and routes each incoming websocket to the next free pipeline (each has its own "
            "VAD/STT/LM/TTS handlers and conversation state). Max concurrent websocket sessions equals "
            "num_pipelines; further connections are rejected. Only valid for --mode realtime. Default is 1."
        },
    )
    wake_word_enabled: bool = field(
        default=False,
        metadata={
            "help": "When True, final transcripts must contain one of --wake_words before the assistant responds. "
            "The final transcription event is still emitted to clients."
        },
    )
    wake_words: str = field(
        default="hey alice",
        metadata={"help": "Comma-separated transcript wake phrases, e.g. 'hey alice,okay assistant'."},
    )
    wake_word_strip: bool = field(
        default=True,
        metadata={"help": "When True, remove the matched wake phrase before sending the user text to the LLM."},
    )
    custom_tools_enabled: bool = field(
        default=False,
        metadata={"help": "Enable local Python custom tools loaded from --custom_tools_path."},
    )
    custom_tools_path: str = field(
        default="user-customization/custom-tools.json",
        metadata={"help": "Path to a JSON array of local custom tool definitions."},
    )
    custom_tools_timeout_s: float = field(
        default=10.0,
        metadata={"help": "Default timeout in seconds for local custom tool scripts."},
    )
    memory_enabled: bool = field(
        default=False,
        metadata={"help": "Enable lightweight local memory for explicit 'remember that ...' user facts."},
    )
    memory_path: str = field(
        default="user-customization/memories.json",
        metadata={"help": "Path to the local JSON memory store."},
    )
    memory_max_prompt_items: int = field(
        default=8,
        metadata={"help": "Maximum remembered facts injected into each LLM prompt."},
    )
