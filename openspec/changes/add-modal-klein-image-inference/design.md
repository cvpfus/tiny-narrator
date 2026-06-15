# Design: Modal Klein Image Inference

## Overview

Tiny Narrator will keep its current `POST /api/generate-image` and `/api/generate-article` contracts, but `generate_image_core()` will become a two-path adapter:

1. If a Modal Klein endpoint is configured, call it for live `black-forest-labs/FLUX.2-klein-4B` inference.
2. If the endpoint is missing or fails, return the current bundled fallback assets with explicit fallback metadata.

This preserves the app's hackathon reliability while making the image-generation claim real when the Modal worker is deployed.

## Modal Worker

Add a new worker module, likely `modal_workers/klein_image.py`, with:

- a Modal `App`
- a persistent Modal `Volume` for generated images
- an image/container definition that installs FastAPI, Pillow, torch, transformers/diffusers dependencies, and the Klein runtime dependencies
- a model class or cached function that loads `black-forest-labs/FLUX.2-klein-4B` once per warm container
- a FastAPI web endpoint, for example `POST /generate`, accepting:
  - `prompt: str`
  - `seed: int | None`
  - optional generation controls only if needed later
- a `GET /media/{filename}` endpoint for generated PNG/WebP files

The worker should return:

```json
{
  "ok": true,
  "runtime": "modal-klein",
  "model": "black-forest-labs/FLUX.2-klein-4B",
  "image_url": "https://.../media/klein-....png",
  "prompt": "...",
  "seed": 123,
  "elapsed_ms": 12345
}
```

From the referenced TinyDeck thread, the important Modal implementation lessons are:

- Use an explicit media helper for `GET /media/{filename}`.
- Call `output_volume.reload()` before serving media from a web container.
- Return a clean 404 for missing media instead of letting `FileResponse` crash.
- Give the web endpoint a long enough timeout for cold starts.
- If using a GitHub Diffusers build, avoid incompatible `safetensors==0.7.0`; use a compatible lower bound such as `safetensors>=0.8.0rc0` if that dependency path is chosen.

## App Configuration

Add environment variables:

| Variable | Purpose |
| --- | --- |
| `KLEIN_MODAL_ENDPOINT` | Base URL for the Modal Klein worker, without trailing slash. |
| `KLEIN_MODAL_TIMEOUT_SECONDS` | Request timeout for image generation, defaulting high enough for warm inference but not blocking local demos forever. |

No Modal dependency is needed in the main Gradio app unless the implementation chooses a direct Modal SDK client. Prefer plain HTTP from `app.py` so Hugging Face Spaces can call the worker with standard library or already-small dependencies.

## App Integration

`generate_image_core(prompt, seed)` should:

- record a start time
- call `POST {KLEIN_MODAL_ENDPOINT}/generate` when configured
- validate the response shape before trusting it
- preserve the returned prompt, seed, model, runtime, image URL, and elapsed time
- add a warning and fall back to bundled SVG assets on network errors, bad responses, timeout, or missing endpoint

`generate_article_core()` can keep its current article text behavior and use the upgraded `generate_image_core()` for thumbnails.

`_runtime_status_core()` should report:

- `available: true`, `status: "online"` when the worker health check succeeds
- `available: false`, `status: "fallback-ready"` when not configured or not reachable
- endpoint and timeout metadata without exposing secrets

`runtime_setup_core()` should show a copyable `modal deploy modal_workers/klein_image.py` command and the required `KLEIN_MODAL_ENDPOINT` configuration.

## Fallbacks

Fallbacks stay first-class and visible:

- Existing bundled SVGs remain available.
- Fallback payloads keep `ok: true` because the UI can still render.
- Payloads should include `runtime: "fallback"` or `generation_runtime: "bundled fallback asset"` and a `warning` when live inference failed.
- Verification should not require Modal credentials or network access.

## Evidence And Docs

Update evidence APIs and docs so they no longer say "Python integration planned" for image generation once the worker exists. They should say Modal-hosted Klein is supported and report whether the current runtime is online or fallback-ready.

The Generate route can continue showing thumbnail provenance through the existing receipt text. If live Modal inference is active, the receipt should reflect `modal-klein` instead of placeholder/fallback runtime.

## Testing Strategy

Use unit-style tests around `generate_image_core()`:

- no endpoint configured returns deterministic fallback
- configured endpoint returning valid JSON is surfaced as live Modal inference
- configured endpoint failure falls back with a warning
- `/api/runtime-status` and `/api/runtime-setup` mention the Modal Klein path
- `/api/generate-article` thumbnail provenance remains stable

The Modal worker should be syntax-checked locally. Live deployment testing can be documented as a manual command because CI/local verification should not require GPU infrastructure.
