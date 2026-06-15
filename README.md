---
title: Tiny Narrator
emoji: 🔊
colorFrom: teal
colorTo: yellow
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
pinned: false
license: apache-2.0
---

# Tiny Narrator

Tiny Narrator is a Build Small Hackathon prototype: a custom Gradio Server app with two routes: a guided screen-reader article and a small-model article generator.

For the hackathon form, see [SUBMISSION.md](SUBMISSION.md).

## Award Strategy

- **Tiny Titan:** every planned model is at or below 4B parameters.
- **Llama Champion:** the reader-brain layer calls a GGUF model through `llama.cpp`.
- **Off-Brand:** the visible UI is custom HTML, CSS, and JavaScript served by `gr.Server`.
- **Field Notes:** the repo documents model sizes, runtime choices, fallbacks, and accessibility decisions.

## Recommended Models

| Role | Model | Params | Runtime |
| --- | ---: | ---: | --- |
| Reader brain | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 3.97B | `llama.cpp` |
| Image understanding | `openbmb/MiniCPM-V-4.6` | 1B | OpenAI-compatible chat completions |
| Text to speech | `hexgrad/Kokoro-82M` | 82M | Python |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | 4B | Modal-hosted Klein |

## Run Locally

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Copy the example environment file to `.env` and fill in the values. The app loads `.env` automatically at startup, so no shell exports are required. Process environment variables still override `.env` values.

```powershell
Copy-Item .env.example .env
```

Start the llama.cpp reader-brain server locally:

```powershell
llama-server -hf nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M --alias narrator-brain --port 8080 --host 0.0.0.0 --ctx-size 0 --reasoning off --n-gpu-layers 999
```

Start the app:

```powershell
python app.py
```

Open the local URL printed by Gradio. The Reader route calls `/api/reader-brain`, `/api/image-descriptions`, `/api/describe-image`, `/api/speak`, and `/api/model-budget`. The Generate route calls `/api/generate-article`, which drafts an article with the reader-brain model path and attaches a Klein thumbnail receipt.

## Modal Reader Brain

For a free CPU Hugging Face Space, host the llama.cpp reader-brain server on Modal and point the app at its OpenAI-compatible `/v1` endpoint:

```powershell
modal secret create tiny-narrator-reader-brain-token LLAMA_CPP_TOKEN=your-random-token
modal deploy modal_workers/reader_brain.py
```

Set `LLAMA_CPP_BASE_URL` to the deployed Modal URL with `/v1` appended, for example:

```env
LLAMA_CPP_BASE_URL=https://your-workspace--tiny-narrator-reader-brain.modal.run/v1
LLAMA_CPP_MODEL=narrator-brain
LLAMA_CPP_TOKEN=your-random-token
```

The Modal worker starts Nemotron with `--ctx-size 0`, `--reasoning off`, full GPU offload, and `--api-key` when `LLAMA_CPP_TOKEN` is configured. It uses the prebuilt `ghcr.io/ggml-org/llama.cpp:server-cuda12` image instead of compiling llama.cpp during deploy, clears that image's entrypoint so Modal can start its Python runner, and allows up to 10 minutes for the first GGUF download/load. It scales down when idle, so the first request after a cold start can be slower.

## Modal Klein Image Generation

The image generation path uses a Modal-hosted `black-forest-labs/FLUX.2-klein-4B` worker. Deploy the worker:

```powershell
modal secret create tiny-narrator-klein-token KLEIN_MODAL_TOKEN=your-random-token
modal deploy modal_workers/klein_image.py
```

Set `KLEIN_MODAL_ENDPOINT` to the deployed worker URL. Set the same `KLEIN_MODAL_TOKEN` value in your local `.env`. The Modal worker uses the fixed `tiny-narrator-klein-token` secret name so Modal's local and remote dependency graphs stay identical.

`/api/runtime-status` reports whether the Modal Klein worker is online or fallback-ready. `/api/runtime-setup` includes the deploy command and required environment variables.

## MiniCPM-V-4.6 Image Descriptions

The image description path uses `openbmb/MiniCPM-V-4.6` through an OpenAI-compatible `/v1/chat/completions` endpoint. Provide `MINICPM_VISION_BASE_URL` and `MINICPM_VISION_API_KEY` to enable live screen-reader alt text for article images.

When the endpoint is not configured, unreachable, or returns invalid content, `/api/describe-image` and `/api/image-descriptions` fall back to deterministic cached alt text so reader mode remains usable.

Useful environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLAMA_CPP_BASE_URL` | `http://localhost:8080/v1` | OpenAI-compatible llama.cpp server URL, local or Modal |
| `LLAMA_CPP_MODEL` | `narrator-brain` | Alias passed to llama.cpp |
| `LLAMA_CPP_TOKEN` | *(empty)* | Optional bearer token for protected llama.cpp endpoints. When set, the app sends `Authorization: Bearer <token>`. |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Bind address for local or Space runtime |
| `GRADIO_SERVER_PORT` / `PORT` | `7860` | App port |
| `GRADIO_SHARE` | `false` | Set to `true` if Gradio cannot verify localhost and needs a share URL |
| `PUBLIC_BASE_URL` | `http://localhost:7860` | Base URL used in generated judge API commands |
| `LLAMA_CPP_TIMEOUT_SECONDS` | `90` | Timeout for local llama.cpp reader-brain and article generation calls |
| `KLEIN_MODAL_ENDPOINT` | *(empty)* | Base URL for the Modal Klein worker, without trailing slash. When set, `/api/generate-image` calls the live worker. |
| `KLEIN_MODAL_TOKEN` | *(empty)* | Shared bearer token for Modal worker auth. When set, the app sends `Authorization: Bearer <token>` and the worker rejects unauthenticated requests. |
| `KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS` | `30` | Timeout for Modal Klein `/health`; increase for cold-starting Modal endpoints. |
| `KLEIN_MODAL_TIMEOUT_SECONDS` | `120` | Request timeout for Modal Klein image generation. |
| `MINICPM_VISION_BASE_URL` | *(empty)* | OpenAI-compatible MiniCPM-V-4.6 base URL; root or `/v1` both work. |
| `MINICPM_VISION_API_KEY` | *(empty)* | Bearer token for the MiniCPM vision endpoint. |
| `MINICPM_VISION_MODEL` | `openbmb/MiniCPM-V-4.6` | Model id sent to chat completions. |
| `MINICPM_VISION_TIMEOUT_SECONDS` | `45` | Request timeout for image descriptions. |

## Verification

```powershell
python scripts/verify.py
```

The verifier checks syntax, static assets, Space metadata consistency, deterministic fallback model paths, and generated speech file behavior.

## Live Model Smoke Tests

After starting the app with configured model endpoints, run the opt-in smoke script to verify live inference:

```powershell
python scripts/live_smoke.py --base-url http://127.0.0.1:7860
```

The smoke script checks `/api/runtime-status`, `/api/describe-image`, and `/api/generate-image`. It skips checks for unconfigured runtimes and exits non-zero only when a configured live check fails. Secrets are never printed.

`/api/model-budget` exposes numeric parameter counts for every model role and reports whether the full stack stays within the 4B Tiny Titan limit.

`/api/runtime-setup` exposes the commands, environment values, and fallback paths used for the model stack so the demo can be reproduced from the same data the UI displays.

`/api/demo-script` exposes a compact judge runbook with the visible actions, API checks, sample bodies, curl commands, and PowerShell-friendly `curl.exe` commands that prove the submission claims, including `/api/generate-article`. The commands use `PUBLIC_BASE_URL` so they can be copied from the API response or submission notes.

`/api/accessibility-audit` exposes structured evidence for semantic reading order, keyboard navigation, reader cursor state, shortcut safety, live narration, image alt text, transcript review, user-controlled playback, and fallback resilience.

`/api/image-descriptions` includes image-generation provenance for every article illustration: the planned FLUX.2 klein model, prompt, seed, bundled asset URL, and fallback-ready status.

`/api/generate-article` accepts a topic and returns a generated article draft plus thumbnail provenance from `black-forest-labs/FLUX.2-klein-4B`.

`/api/submission-readiness` aggregates the judging receipts into one pass/fail payload covering model budget, award evidence, custom frontend assets, runtime setup, runtime status, accessibility, image receipts, demo API checks, and command base URL checks.

The readiness rollup only passes the demo API check when POST entries include executable sample bodies.

`/api/evidence-bundle` returns a JSON bundle of the main judging receipts, including schema version, UTC generation time, `PUBLIC_BASE_URL`, runtime status, and the submission readiness rollup.

## Screen Reader Mode

The frontend builds a reading queue from semantic article nodes. When screen-reader mode is on:

- `Space` plays or pauses.
- `N` moves to the next item.
- `P` moves to the previous item.
- `H` moves to the next heading.
- `I` moves to the next image.
- `S` summarizes the current section.
- `R` repeats the current item.
- `Esc` stops the current audio.

Each readable node is sent to the reader brain for concise narration, then Kokoro generates speech. If a model is unavailable, the app uses deterministic fallbacks so the demo remains navigable.

The session panel stays reader-first: it shows current reader state, live narration, transcript controls, latency, and the tiny-model stack. The semantic reader queue remains internal to playback and keyboard navigation.

When screen-reader mode turns on, it selects the focused or most visible article item, assigns stable reader-node ids, and marks the active item with `aria-current`. Clicking a readable article item while the mode is on reads that item directly.

Global reader shortcuts ignore buttons, links, selects, and inputs so the voice, speed, and auto-advance controls remain usable while reader mode is active.

Reader buttons expose `aria-keyshortcuts`, and the Repeat and Stop shortcuts are mirrored by visible controls so pointer and keyboard users share the same command surface.

The session panel keeps a transcript of recent narration with reader position, runtime, latency, copy, and clear controls, making the spoken path inspectable during demos and useful for the Field Notes write-up. Copy actions report when browser clipboard access is unavailable, so the visible transcript and commands remain inspectable.

Images start with meaningful fallback `alt` text in the HTML. Image descriptions are then preloaded into a local cache and written into the page's real `img alt` attributes. When the MiniCPM-V-4.6 endpoint is unavailable, deterministic alt-text fallbacks keep the screen-reader path usable.

`/api/image-descriptions` exposes image receipts so judges can inspect the prompt, seed, planned <=4B image model, and fallback status behind each bundled article illustration without lengthening the reader sidebar.

Kokoro remains the planned tiny-model TTS path. During local demos, if the server-side Kokoro call falls back, the browser speech engine can read the same transcript so screen-reader mode still produces audible feedback.

Generated speech files are pruned automatically so repeated demos do not grow the Space's `outputs` directory without bound.

The reader bar exposes Kokoro voice selection and speaking speed controls. Defaults come from `/api/article-manifest` so the UI, docs, and backend stay aligned.

Auto-advance is available as an opt-in reader control. It stays off by default so users keep manual control unless they choose continuous reading.

Navigation commands interrupt current speech before starting the next request, matching the expectation that a screen reader responds immediately when the user moves.

Reader-brain, image-description, speech, and image-generation responses include `elapsed_ms`. The session panel and transcript show recent latency so the Field Notes can discuss responsiveness with concrete numbers.

The sidebar model stack reads `/api/model-budget` so judges can see each role's model id, runtime, parameter count, and Tiny Titan pass status in the live app.

`/api/submission-readiness` gives judges one compact rollup of the claims the live app can prove.

`/api/evidence-bundle` returns the core judge receipts as formatted JSON for quick review or submission notes.

`/api/runtime-setup` summarizes each model path's runtime, setup command, and fallback, keeping the live demo honest about what is online and what is deterministic.

`/api/runtime-status` performs a short readiness check for llama.cpp and local speech dependencies, then reports which fallback paths are ready for a live demo.

## Generate Route

The header exposes two routes: Reader and Generate. Generate lets a user enter a topic, calls `/api/generate-article`, and renders a short semantic article with a thumbnail receipt. The text path uses the configured llama.cpp reader-brain model when available and falls back to deterministic article structure. The thumbnail path calls the Modal Klein worker for live image generation when `KLEIN_MODAL_ENDPOINT` is configured, and falls back to bundled SVG assets with explicit runtime metadata when the worker is unavailable.
