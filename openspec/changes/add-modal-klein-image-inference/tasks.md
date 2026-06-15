# Tasks: Modal Klein Image Inference

## 1. Modal Worker

- [x] Add `modal_workers/klein_image.py` with a Modal app, persistent output volume, and FastAPI web endpoints.
- [x] Implement `POST /generate` for `black-forest-labs/FLUX.2-klein-4B` prompt + optional seed inference.
- [x] Implement `GET /media/{filename}` with volume reload before serving and clean 404 handling for missing files.
- [x] Add worker-level timeout and dependency pins suitable for cold starts.
- [x] Document the deploy command and expected endpoint shape in comments or docs.

## 2. App Configuration And Client

- [x] Add `KLEIN_MODAL_ENDPOINT` and `KLEIN_MODAL_TIMEOUT_SECONDS` configuration in `app.py`.
- [x] Add a small HTTP client/helper for calling the Modal Klein worker.
- [x] Update `generate_image_core()` to use Modal when configured.
- [x] Preserve deterministic bundled fallback behavior when Modal is missing, slow, or returns invalid data.
- [x] Include `warning`, `runtime`, `model`, `prompt`, `seed`, `image_url`, and `elapsed_ms` consistently in live and fallback responses.

## 3. Runtime Evidence

- [x] Update `MODEL_MANIFEST["image_generation"]["runtime"]` from planned integration to Modal-hosted Klein.
- [x] Update `runtime_setup_core()` with Modal deploy/setup instructions and environment variables.
- [x] Update `_runtime_status_core()` to report Modal Klein online/fallback-ready status.
- [x] Update `demo_script_core()`, `submission_readiness_core()`, and `evidence_bundle_core()` expectations as needed.
- [x] Ensure `/api/model-budget` still proves Tiny Titan <= 4B.

## 4. Generate Route Behavior

- [x] Ensure `/api/generate-image` returns live Modal image URLs when configured.
- [x] Ensure `/api/generate-article` thumbnail receipts reflect live Modal runtime when available.
- [x] Keep the Generate page UI stable and screen-reader-compatible with generated thumbnails.
- [x] Avoid adding a new evidence UI page.

## 5. Docs

- [x] Update `README.md` with Modal Klein setup, environment variables, and fallback behavior.
- [x] Update `SUBMISSION.md` to distinguish live Modal Klein inference from bundled fallback assets.
- [x] Update `FIELD_NOTES.md` with architecture notes, runtime honesty, and manual deploy guidance.

## 6. Verification

- [x] Add tests in `scripts/verify.py` for fallback image generation without Modal.
- [x] Add mocked/stubbed tests for successful Modal worker responses.
- [x] Add mocked/stubbed tests for Modal failure fallback with a visible warning.
- [x] Add static checks for the Modal worker file.
- [x] Run `python scripts\verify.py`.
- [x] Run `python -m py_compile app.py scripts\verify.py modal_workers\klein_image.py`.
- [x] Run `git diff --check`.

## 7. Manual Modal Check

- [ ] Deploy with `modal deploy modal_workers/klein_image.py`.
- [ ] Set `KLEIN_MODAL_ENDPOINT` locally or in the Space runtime.
- [ ] Call `/api/generate-image` with a sample prompt and confirm it returns a Modal media URL.
- [ ] Generate an article from `/generate` and confirm the thumbnail receipt reports live Modal Klein runtime.
