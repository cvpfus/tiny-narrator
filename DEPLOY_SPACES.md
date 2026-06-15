# Deploy Tiny Narrator to Hugging Face Spaces

This guide deploys Tiny Narrator on Hugging Face Spaces using the **Docker SDK on free CPU**. The Space serves the custom article UI, FastAPI routes, Kokoro/browser speech path, and fallback assets. GPU inference runs outside the Space through Modal or other OpenAI-compatible endpoints.

> **Why Docker SDK?** Tiny Narrator uses `gradio.Server` with custom FastAPI routes and static files. The Docker SDK preserves that app shape without rewriting the UI into `gr.Blocks`.
>
> **Why free CPU?** Paid HF GPU is not required when `llama.cpp` and image generation are hosted externally. The Space can stay on CPU Basic while still calling live model endpoints.

---

## Prerequisites

- A Hugging Face account
- Git and Git LFS installed locally
- Python 3.11+ installed locally for testing
- Modal CLI installed if you want live reader-brain or Klein image generation

---

## Step 1 - Create a New Space

1. Go to [https://huggingface.co/new-space](https://huggingface.co/new-space).
2. Fill in the form:
   - **Space name**: `tiny-narrator`
   - **SDK**: **Docker**
   - **Hardware**: **CPU Basic**
   - **Visibility**: Public or Private
3. Click **Create Space**.

Your Space README metadata should include:

```yaml
---
title: Tiny Narrator
emoji: book
colorFrom: blue
colorTo: teal
sdk: docker
app_port: 7860
---
```

The `app_port: 7860` line is important because Tiny Narrator binds to port 7860 by default.

---

## Step 2 - Copy Project Files

Clone the Space repository and copy the Tiny Narrator project files into it:

```bash
git clone https://huggingface.co/spaces/<YOUR_USERNAME>/tiny-narrator
cd tiny-narrator
```

Include these files and directories:

```text
app.py
requirements.txt
Dockerfile
start.sh
README.md
SUBMISSION.md
FIELD_NOTES.md
LICENSE
static/
modal_workers/
scripts/
```

Do **not** copy `.env`; configure secrets in the Space Settings UI.

---

## Step 3 - Deploy Modal Reader Brain

The reader-brain role uses `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M` through `llama.cpp`. Deploy it to Modal:

```bash
pip install modal
modal setup
modal secret create tiny-narrator-reader-brain-token LLAMA_CPP_TOKEN=your-random-token
modal deploy modal_workers/reader_brain.py
```

After deployment, Modal prints a URL similar to:

```text
https://your-workspace--tiny-narrator-reader-brain.modal.run
```

Set the Space variable:

```text
LLAMA_CPP_BASE_URL=https://your-workspace--tiny-narrator-reader-brain.modal.run/v1
LLAMA_CPP_MODEL=narrator-brain
LLAMA_CPP_TOKEN=your-random-token
LLAMA_CPP_TIMEOUT_SECONDS=90
```

The worker starts `llama-server` with:

```bash
llama-server \
  -hf nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M \
  --alias narrator-brain \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 0 \
  --reasoning off \
  --n-gpu-layers 999 \
  --api-key your-random-token
```

Modal scales the worker down when idle. The first request after scale-to-zero can be slow while the container and model start.

---

## Step 4 - Optional Live Image Generation

Tiny Narrator can use the Modal Klein worker for `black-forest-labs/FLUX.2-klein-4B` thumbnails:

```bash
modal secret create tiny-narrator-klein-token KLEIN_MODAL_TOKEN=your-random-token
modal deploy modal_workers/klein_image.py
```

Set these Space values:

```text
KLEIN_MODAL_ENDPOINT=https://your-workspace--tiny-narrator-klein.modal.run
KLEIN_MODAL_TOKEN=your-random-token
KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS=30
KLEIN_MODAL_TIMEOUT_SECONDS=120
```

If the Klein worker is not configured, the app falls back to bundled SVG assets.

---

## Step 5 - Optional MiniCPM-V Image Descriptions

If you have an OpenAI-compatible MiniCPM-V-4.6 endpoint, set:

```text
MINICPM_VISION_BASE_URL=https://your-vision-endpoint.example.com/v1
MINICPM_VISION_API_KEY=<secret>
MINICPM_VISION_MODEL=openbmb/MiniCPM-V-4.6
MINICPM_VISION_TIMEOUT_SECONDS=45
```

If this endpoint is not configured, Tiny Narrator uses deterministic cached alt text.

---

## Step 6 - Configure Space Variables

In your Space, open **Settings -> Variables and secrets**.

Add these variables:

| Variable | Example | Notes |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | `https://your-username-tiny-narrator.hf.space` | Used in generated judge/demo links |
| `GRADIO_SHARE` | `false` | Keep false on Spaces |
| `LLAMA_CPP_BASE_URL` | `https://...modal.run/v1` | Modal reader-brain endpoint |
| `LLAMA_CPP_MODEL` | `narrator-brain` | Alias served by llama.cpp |
| `LLAMA_CPP_TIMEOUT_SECONDS` | `90` | Reader/article generation timeout |
| `KLEIN_MODAL_ENDPOINT` | `https://...modal.run` | Optional image generation endpoint |
| `KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS` | `30` | Optional Klein health timeout |
| `KLEIN_MODAL_TIMEOUT_SECONDS` | `120` | Optional Klein generation timeout |
| `MINICPM_VISION_BASE_URL` | `https://.../v1` | Optional image descriptor endpoint |
| `MINICPM_VISION_MODEL` | `openbmb/MiniCPM-V-4.6` | Optional descriptor model id |
| `MINICPM_VISION_TIMEOUT_SECONDS` | `45` | Optional descriptor timeout |

Add these as **Secrets**:

| Secret | Notes |
| --- | --- |
| `LLAMA_CPP_TOKEN` | Recommended for Modal reader-brain auth |
| `KLEIN_MODAL_TOKEN` | Only needed if Modal Klein is enabled |
| `MINICPM_VISION_API_KEY` | Only needed if MiniCPM-V is enabled |

---

## Step 7 - Commit and Push

```bash
git add .
git commit -m "Deploy Tiny Narrator to HF Spaces CPU"
git push origin main
```

HF Spaces will:

1. Detect the Dockerfile.
2. Build a small CPU image.
3. Run `start.sh`.
4. Launch `python app.py` on port 7860.
5. Expose the app at `https://<YOUR_USERNAME>-tiny-narrator.hf.space`.

---

## Step 8 - Verify the Deployment

Open the Space URL in a browser, then check:

```bash
curl https://<YOUR_USERNAME>-tiny-narrator.hf.space/api/health
curl https://<YOUR_USERNAME>-tiny-narrator.hf.space/api/model-budget
curl https://<YOUR_USERNAME>-tiny-narrator.hf.space/api/runtime-status
curl https://<YOUR_USERNAME>-tiny-narrator.hf.space/api/submission-readiness
```

`/api/runtime-status` should show:

- `reader_brain`: `online` when Modal llama.cpp is reachable, `fallback-ready` otherwise
- `speech`: Kokoro or fallback speech path
- `vision`: MiniCPM online or fallback-ready
- `image_generation`: Modal Klein online or fallback-ready

---

## Troubleshooting

### Space starts but reader brain is fallback-ready

- Confirm `LLAMA_CPP_BASE_URL` ends in `/v1`.
- Confirm the Space `LLAMA_CPP_TOKEN` secret matches the Modal `tiny-narrator-reader-brain-token` secret.
- Open the Modal logs for `tiny-narrator-reader-brain`.
- Check that the Modal URL is reachable at `/v1/models`.
- The first request after scale-to-zero may need extra time while Modal starts the container and loads the GGUF.

### Space stuck on "Starting"

- Check the Space **Container** logs.
- Make sure `requirements.txt` installed successfully.
- Make sure the app binds to `0.0.0.0:7860`; the defaults already do this.

### Kokoro TTS not producing audio

- `libsndfile1` is installed in the Docker image.
- If Kokoro fails to load, the app falls back to browser speech synthesis and transcript output.

### Modal reader-brain cold starts are slow

- Keep `scaledown_window` higher in `modal_workers/reader_brain.py` if you want the container to stay warm longer.
- Use a faster GPU by setting `READER_BRAIN_MODAL_GPU` before deploying.
- Keep `min_containers=0` for cheapest operation; use a warm container only if you accept continuous cost.

### External services unreachable

- HF Spaces has outbound internet access, but private endpoints are not reachable.
- Use public HTTPS endpoints for Modal, MiniCPM, and any tunnels.

---

## Architecture Overview

```text
Hugging Face Space (Docker CPU)
  app.py
  static HTML/CSS/JS
  outputs WAV files
  deterministic fallbacks
        |
        +--> Modal reader-brain worker
        |     llama.cpp /v1/chat/completions
        |
        +--> Modal Klein image worker (optional)
        |
        +--> MiniCPM-V-4.6 OpenAI-compatible endpoint (optional)
```

---

## Quick Reference

| Item | Value |
| --- | --- |
| Space SDK | Docker |
| Space hardware | CPU Basic |
| App port | 7860 |
| Space base image | `python:3.12-slim` |
| Reader brain runtime | Modal-hosted llama.cpp |
| Reader brain model | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M` |
| Reader brain base URL | `https://<modal-url>/v1` |
| Image generation | Modal Klein worker or SVG fallback |
| Image descriptions | MiniCPM-V endpoint or cached fallback |

---

## Further Reading

- [HF Spaces Docker SDK docs](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [HF Spaces Secrets & Variables](https://huggingface.co/docs/hub/spaces-overview#managing-secrets)
- [Modal Web Functions](https://modal.com/docs/guide/webhooks)
- [Modal GPU acceleration](https://modal.com/docs/guide/gpu)
- [llama.cpp repository](https://github.com/ggml-org/llama.cpp)
