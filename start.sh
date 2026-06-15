#!/bin/sh
# Startup script for Tiny Narrator on Hugging Face Spaces free CPU.
# Model inference endpoints are configured through environment variables.

set -eu

echo "[tiny-narrator] Starting Tiny Narrator app on ${GRADIO_SERVER_NAME:-0.0.0.0}:${PORT:-${GRADIO_SERVER_PORT:-7860}}"

if [ -n "${LLAMA_CPP_BASE_URL:-}" ]; then
    echo "[tiny-narrator] Reader brain endpoint configured at ${LLAMA_CPP_BASE_URL}"
else
    echo "[tiny-narrator] LLAMA_CPP_BASE_URL is not configured; reader brain will use deterministic fallback."
fi

exec python app.py
