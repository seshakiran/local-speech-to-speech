<div align="center">

# Local Speech-to-Speech

### A private, real-time voice assistant that runs entirely on your Mac

**Silero VAD · Parakeet STT · Gemma 4 · Qwen3-TTS · Ollama / LM Studio / MLX**

[![Local First](https://img.shields.io/badge/inference-100%25_local-70d6a3?style=for-the-badge)](#what-runs-locally)
[![Offline Ready](https://img.shields.io/badge/internet-not_required-8eb8ff?style=for-the-badge)](#offline-by-design)
[![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-optimized-111318?style=for-the-badge&logo=apple)](#quick-start)
[![License](https://img.shields.io/badge/license-Apache_2.0-f4c95d?style=for-the-badge)](LICENSE)

Speak naturally. Watch the orb react. Hear a local model answer—without sending your conversation to a hosted AI service.

</div>

---

## Why this project exists

[Hugging Face Speech-to-Speech](https://github.com/huggingface/speech-to-speech) provides an excellent modular framework for real-time voice agents, and the [Hugging Face Realtime Voice Space](https://huggingface.co/spaces/smolagents/hf-realtime-voice) demonstrates how polished the experience can feel.

**Local Speech-to-Speech** adapts that experience for a fully local Apple Silicon setup. It adds a one-command offline launcher, selectable local LLM runtimes, a private personalized interface, voice-based name onboarding, local model visibility, and an offline-safe browser transport.

## What runs locally

```text
Your microphone
      │
      ▼
Silero VAD             detects when you speak
      │
      ▼
NVIDIA Parakeet TDT    transcribes your voice
      │
      ▼
Gemma 4                thinks and writes a response
Ollama / LM Studio / MLX
      │
      ▼
Qwen3-TTS              synthesizes the reply
      │
      ▼
Your speakers
```

The browser UI and realtime API also bind to `127.0.0.1`. With model weights already downloaded, VAD, transcription, generation, synthesis, UI assets, and conversation data all stay on the machine.

## Highlights

- **Actually offline:** the launcher enforces offline mode for Hugging Face Hub, Transformers, and datasets.
- **Local Gemma 4:** defaults to `gemma4:e4b` through Ollama.
- **Choose your runtime:** configure Ollama, LM Studio, or native MLX in one file.
- **Realtime voice:** streaming transcription, response generation, and speech synthesis.
- **Personal from the first hello:** the assistant asks for your name by voice and remembers it only in browser local storage.
- **Transparent configuration:** the UI shows the active LLM, provider, speech models, transport, and privacy state.
- **Offline-safe transport:** WebSocket is the default because localhost survives when Wi-Fi is disabled.
- **Modular foundation:** VAD, STT, LLM, and TTS remain replaceable.
- **Safe Mac control:** optional allowlisted tools can type, edit selections,
  press safe keys, and activate apps without exposing a general-purpose shell.

## Control your Mac by voice

Open **Tools** in the local interface and enable **Control this Mac**. The first
action prompts macOS for permission. Allow the application that launched the
server (normally Terminal) under **System Settings → Privacy & Security →
Accessibility** and, when requested, **Automation → System Events**.

Try commands such as:

- “Which app is active?”
- “Open Notes.”
- “Type: Call the dentist tomorrow morning.”
- “Make the selected text shorter.”
- “Replace the selection with the revised version.”
- “Press Tab.”

Typing, selection replacement, Enter, Backspace, and Delete show a native
confirmation first. The controller remembers the target app before displaying
that prompt and returns focus to it before performing the action. Machine
control accepts only six fixed actions; it cannot execute model-generated shell
or AppleScript code.

## Quick start

### Requirements

- Apple Silicon Mac
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/), [LM Studio](https://lmstudio.ai/), or a cached MLX model
- Approximately 8 GB or more of free space for the default speech models

### Install

```bash
git clone https://github.com/seshakiran/local-speech-to-speech.git
cd local-speech-to-speech
uv sync
```

For the default Gemma 4 configuration:

```bash
ollama pull gemma4:e4b
```

The first setup needs internet access to download dependencies and model weights. After they are cached, the app runs offline.

### Configure the local LLM

Edit [`local-models.env`](local-models.env):

```dotenv
S2S_LLM_PROVIDER=ollama
S2S_LLM_MODEL=gemma4:e4b
S2S_LLM_BASE_URL=http://127.0.0.1:11434/v1
S2S_LLM_API_KEY=ollama
```

Supported providers:

| Provider | Runtime | Default endpoint |
|---|---|---|
| `ollama` | Ollama | `http://127.0.0.1:11434/v1` |
| `lmstudio` | LM Studio | `http://127.0.0.1:1234/v1` |
| `mlx` | Native in-process MLX | Cached model repository or local path |

### Start

```bash
./start-local.sh
```

Wait for `Speech backend is ready`, then open [http://localhost:7860](http://localhost:7860) and grant microphone access.

## Offline by design

`start-local.sh` enables:

```bash
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
DO_NOT_TRACK=1
```

The UI defaults to **WebSocket · offline-safe**. WebRTC is optional, but it can select a Wi-Fi/LAN ICE route and lose the session when that network interface is turned off—even when both browser and server run on the same Mac.

Disconnecting the internet is therefore a useful test: once installation and model downloads are complete, a conversation should continue normally.

## Audio and echo cancellation

Browser echo cancellation works best when microphone and speaker output belong to the same device. An external display microphone listening to Mac speakers creates a physical echo path that software may not fully cancel. For best results, use headphones or select a matched input/output device.

## What changed from upstream

- Added `start-local.sh` and `start-ui-only.sh` launchers.
- Added `local-models.env` for Ollama, LM Studio, and MLX selection.
- Defaulted the LLM to local Gemma 4 instead of a hosted provider.
- Forced cached/offline loading for VAD, STT, and TTS.
- Made Silero VAD load from the local Torch cache in offline mode.
- Added an offline-safe localhost WebSocket default.
- Added WebRTC lifecycle and browser audio improvements.
- Reworked the UI around local privacy and active model configuration.
- Added spoken name onboarding and local-only personalization.
- Added an optional loopback-only macOS action broker with a strict tool
  allowlist and native confirmations for consequential actions.
- Removed external fonts and hosted-service branding from the runtime UI.

For additional setup details, see [LOCAL_SETUP.md](LOCAL_SETUP.md).

## Ports

| Service | Address |
|---|---|
| Realtime speech backend | `ws://127.0.0.1:8765/v1/realtime` |
| Browser interface | `http://127.0.0.1:7860` |
| Ollama, default | `http://127.0.0.1:11434/v1` |

## Acknowledgements

This project is derived from [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech), released under the Apache License 2.0. The orb experience was inspired by the [Hugging Face Realtime Voice demo](https://huggingface.co/spaces/smolagents/hf-realtime-voice).

The default local pipeline builds on:

- [Silero VAD](https://github.com/snakers4/silero-vad)
- [NVIDIA Parakeet TDT](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [Google Gemma](https://ai.google.dev/gemma)
- [Ollama](https://ollama.com/), [LM Studio](https://lmstudio.ai/), and [MLX](https://github.com/ml-explore/mlx)
- [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)

Thank you to Hugging Face and all upstream contributors for the modular realtime foundation.

## License

Apache License 2.0. See [LICENSE](LICENSE). Upstream copyright and license notices are retained.
