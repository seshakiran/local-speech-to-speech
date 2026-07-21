# Local Speech-to-Speech

This checkout is configured for a fully local Apple Silicon pipeline:

`microphone → Silero VAD → Parakeet TDT STT → selected local LLM → Qwen3-TTS → speakers`

The browser UI is an animated local voice orb in `demo/`, inspired by the
Hugging Face Realtime Voice demo. The backend uses the OpenAI
Realtime-compatible WebSocket protocol,
but no OpenAI or hosted inference API is required by the default launcher.

The launcher enforces Hugging Face and Transformers offline mode. All inference
uses cached model files, Silero loads from the local Torch Hub checkout, and the
UI uses system fonts instead of requesting Google Fonts. Internet access is not
required after the initial model download has completed.

## Choose the local LLM

Edit `local-models.env`. The default uses the installed Ollama Gemma 4 model:

```text
S2S_LLM_PROVIDER=ollama
S2S_LLM_MODEL=gemma4:e4b
S2S_LLM_BASE_URL=http://127.0.0.1:11434/v1
S2S_LLM_API_KEY=ollama
S2S_LLM_REASONING_EFFORT=none
```

Supported providers are `ollama`, `lmstudio`, and `mlx`. Ollama and LM Studio
must be running with the configured model loaded before `start-local.sh` runs.
For native MLX, set the model to a fully cached MLX repository or local model
path; no separate model server is used. STT and TTS remain local in every mode.

## Run

```bash
cd ~/Downloads/Projects/speech-to-speech
./start-local.sh
```

Then open <http://localhost:7860>, click the orb, and grant microphone access.

On first use, the assistant asks aloud what name it should use. The spoken name
is captured by the local Parakeet transcription stream and saved only in browser
local storage. Clear the name in Settings to repeat voice onboarding. The UI
shows the active local provider, LLM, speech models, transport, and privacy state.

The first run downloads several gigabytes of model weights from Hugging Face and
may spend several minutes loading them. The launcher waits until the speech
backend is ready before it starts the browser interface. Do not open the page
until the terminal prints `Speech backend is ready.` Later runs reuse the local
cache. Keep the terminal open while using the app; press `Ctrl-C` once to stop
both the UI and backend.

The local UI defaults to WebSocket because it stays on the localhost loopback
interface when Wi-Fi is disabled. WebRTC remains available in Settings, but it
requires an active network interface; turning Wi-Fi off can invalidate its ICE
route even when the browser and server are on the same Mac.

For the best acoustic echo cancellation, keep microphone input and speaker
output on the same audio device. An external microphone listening to the Mac's
speakers creates a physical echo path that browser cancellation may not remove.

## Control the active Mac application

Open the wrench-shaped **Tools** panel and enable **Control this Mac**. macOS may
ask the launcher (usually Terminal) for permission to control System Events.
Grant it in **System Settings → Privacy & Security → Accessibility** and
**Automation**. Restart the launcher if macOS does not apply the permission to
the already-running process.

The available actions are deliberately limited to reading the active app,
activating an app, typing text, pressing an approved key, reading selected text,
and replacing selected text. Typing, replacing, Enter, Backspace, and Delete
display a native confirmation. There is no arbitrary shell-command endpoint.

For reliable targeting, put focus in the destination field before speaking.
When confirmation is required, the app records that destination, shows the
prompt, then restores focus before executing the approved action.

## Run the UI separately

If the realtime backend is already running:

```bash
./start-ui-only.sh
```

To point the UI at another compatible backend:

```bash
SPEECH_TO_SPEECH_URL=ws://localhost:9000/v1/realtime ./start-ui-only.sh
```

Web search is optional. Enable it by setting `SERPER_API_KEY` before starting
the UI. Camera support is available from the Tools panel when the chosen local
vision model/backend supports image input.

## Installed environment

- Python environment: `.venv` (managed with `uv`)
- Backend address: `ws://127.0.0.1:8765/v1/realtime` (built in by default)
- Browser interface: `http://localhost:7860`
- Git repository: `https://github.com/seshakiran/local-speech-to-speech.git`
