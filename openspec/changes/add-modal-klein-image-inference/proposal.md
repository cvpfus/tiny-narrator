# Add Modal Klein Image Inference

## Why

Tiny Narrator currently documents `black-forest-labs/FLUX.2-klein-4B` as the image-generation model, but `generate_image_core()` only returns bundled fallback SVG assets with placeholder runtime metadata. That is honest, but it leaves the Generate route short of real image-generation inference.

Adding a Modal-hosted Klein worker gives the project a live image-generation path while preserving the deterministic fallback behavior that keeps hackathon demos reliable.

## What Changes

- Add a Modal worker for `black-forest-labs/FLUX.2-klein-4B` image generation.
- Expose an HTTP JSON endpoint that accepts a prompt and optional seed, writes generated images to Modal storage, and serves them through a media route.
- Update Tiny Narrator's image-generation backend path to call the Modal endpoint when configured.
- Keep bundled fallback assets when Modal is not configured, cold-starts fail, or generation times out.
- Update runtime setup/status, evidence payloads, docs, and verifier expectations so the app distinguishes live Klein inference from fallback assets.

## Capabilities

- `modal-klein-image-generation`: generate article thumbnails through a Modal-hosted Klein inference endpoint.
- `image-generation-fallbacks`: retain deterministic local fallback assets and explicit fallback metadata.
- `image-generation-evidence`: surface runtime status, model id, prompt, seed, latency, and generated media URL in existing evidence APIs.

## Non-Goals

- Do not implement MiniCPM-V image-description inference in this change.
- Do not replace the existing reader, TTS, or llama.cpp paths.
- Do not require live Modal inference for local verification to pass.
- Do not add a separate evidence UI page.

## Impact

- `app.py` will gain Modal endpoint configuration, a small image-generation client, and updated runtime/status metadata.
- A new `modal_workers/` script will be added for deploying the Klein worker.
- `README.md`, `SUBMISSION.md`, and `FIELD_NOTES.md` will describe live Modal Klein setup and fallback behavior.
- `scripts/verify.py` will assert that the API contract and fallback path remain stable without requiring Modal credentials.
