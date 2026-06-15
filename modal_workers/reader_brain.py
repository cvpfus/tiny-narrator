"""Modal worker for Tiny Narrator's llama.cpp reader brain.

Deploy:
    modal deploy modal_workers/reader_brain.py

The deployed web server exposes llama.cpp's OpenAI-compatible API. Set:
    LLAMA_CPP_BASE_URL=https://<modal-app-url>/v1
    LLAMA_CPP_MODEL=narrator-brain
    LLAMA_CPP_TOKEN=<same value as Modal secret>

The server intentionally binds to 0.0.0.0 because Modal's web_server proxy
routes traffic to the container port.
"""

import os
import subprocess

import modal


APP_NAME = "tiny-narrator-reader-brain"
MODEL_REF = "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M"
MODEL_ALIAS = "narrator-brain"
SERVER_PORT = 8080
CACHE_DIR = "/cache"

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name("tiny-narrator-reader-brain-cache", create_if_missing=True)


def _secret_names() -> list[modal.Secret]:
    return [modal.Secret.from_name("tiny-narrator-reader-brain-token")]

reader_brain_image = (
    modal.Image.from_registry(
        "ghcr.io/ggml-org/llama.cpp:server-cuda12",
        add_python="3.12",
    )
    .dockerfile_commands("ENTRYPOINT []")
    .env(
        {
            "HF_HOME": f"{CACHE_DIR}/huggingface",
        }
    )
)


@app.function(
    image=reader_brain_image,
    gpu=os.getenv("READER_BRAIN_MODAL_GPU", "T4"),
    volumes={CACHE_DIR: model_cache},
    secrets=_secret_names(),
    timeout=900,
    scaledown_window=300,
    max_containers=1,
)
@modal.concurrent(max_inputs=20)
@modal.web_server(SERVER_PORT)
def reader_brain_server():
    model_ref = os.getenv("READER_BRAIN_MODEL_REF", MODEL_REF)
    model_alias = os.getenv("READER_BRAIN_MODEL_ALIAS", MODEL_ALIAS)
    context_size = os.getenv("READER_BRAIN_CTX_SIZE", "0")
    gpu_layers = os.getenv("READER_BRAIN_GPU_LAYERS", "999")
    api_key = os.getenv("LLAMA_CPP_TOKEN", "")

    command = [
        "llama-server",
        "--host",
        "0.0.0.0",
        "--port",
        str(SERVER_PORT),
        "-hf",
        model_ref,
        "--alias",
        model_alias,
        "--ctx-size",
        context_size,
        "--reasoning",
        "off",
        "--n-gpu-layers",
        gpu_layers,
    ]
    if api_key:
        command.extend(["--api-key", api_key])

    display_command = command.copy()
    if "--api-key" in display_command:
        key_index = display_command.index("--api-key") + 1
        if key_index < len(display_command):
            display_command[key_index] = "***"
    print(f"[tiny-narrator-reader-brain] starting: {' '.join(display_command)}", flush=True)
    subprocess.Popen(command)
