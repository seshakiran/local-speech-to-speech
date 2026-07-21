#!/bin/zsh
set -euo pipefail

PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/speech-to-speech ]]; then
  echo "Dependencies are missing. Run: uv sync"
  exit 1
fi

MODEL_CONFIG="$PROJECT_DIR/local-models.env"
if [[ ! -f "$MODEL_CONFIG" ]]; then
  echo "Missing model configuration: $MODEL_CONFIG"
  exit 1
fi
set -a
source "$MODEL_CONFIG"
set +a

: "${S2S_LLM_PROVIDER:?Set S2S_LLM_PROVIDER in local-models.env}"
: "${S2S_LLM_MODEL:?Set S2S_LLM_MODEL in local-models.env}"

typeset -a LLM_ARGS
case "$S2S_LLM_PROVIDER" in
  mlx)
    LLM_ARGS=(
      --llm_backend mlx-lm
      --model_name "$S2S_LLM_MODEL"
      --llm_device mps
    )
    ;;
  ollama|lmstudio)
    : "${S2S_LLM_BASE_URL:?Set S2S_LLM_BASE_URL for $S2S_LLM_PROVIDER}"
    S2S_LLM_API_KEY="${S2S_LLM_API_KEY:-local}"
    if ! curl --fail --silent --show-error "${S2S_LLM_BASE_URL%/}/models" >/dev/null; then
      echo "Cannot reach $S2S_LLM_PROVIDER at $S2S_LLM_BASE_URL"
      echo "Start the local model server and load '$S2S_LLM_MODEL', then retry."
      exit 1
    fi
    LLM_ARGS=(
      --llm_backend chat-completions
      --model_name "$S2S_LLM_MODEL"
      --responses_api_base_url "$S2S_LLM_BASE_URL"
      --responses_api_api_key "$S2S_LLM_API_KEY"
      --responses_api_stream true
    )
    if [[ -n "${S2S_LLM_REASONING_EFFORT:-}" ]]; then
      LLM_ARGS+=(--responses_api_reasoning_effort "$S2S_LLM_REASONING_EFFORT")
    fi
    ;;
  *)
    echo "Unsupported S2S_LLM_PROVIDER: $S2S_LLM_PROVIDER"
    echo "Choose: ollama, lmstudio, or mlx"
    exit 1
    ;;
esac

cleanup() {
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting the fully local speech pipeline on ws://127.0.0.1:8765/v1/realtime"
echo "LLM: $S2S_LLM_MODEL via $S2S_LLM_PROVIDER"
echo "Offline mode enabled: VAD, STT, LLM, and TTS must load from local caches."
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
.venv/bin/speech-to-speech \
  --mode realtime \
  --device mps \
  --stt parakeet-tdt \
  "${LLM_ARGS[@]}" \
  --tts qwen3 \
  --qwen3_tts_mlx_quantization 6bit \
  --enable_live_transcription \
  --ws_host 127.0.0.1 \
  --ws_port 8765 &
BACKEND_PID=$!

echo "Loading local models. This can take several minutes on the first run..."
while ! nc -z 127.0.0.1 8765 2>/dev/null; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    wait "$BACKEND_PID"
    echo "The speech backend stopped before it became ready."
    exit 1
  fi
  sleep 2
done

echo "Speech backend is ready."
echo "Starting the orb interface at http://localhost:7860"
SPEECH_TO_SPEECH_URL=ws://127.0.0.1:8765/v1/realtime \
  .venv/bin/uvicorn --app-dir demo server:app --host 127.0.0.1 --port 7860
