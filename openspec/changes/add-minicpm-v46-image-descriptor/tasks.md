# Tasks: MiniCPM-V-4.6 Image Descriptor

## 1. Model Metadata And Configuration

- [x] Update `MODEL_MANIFEST["vision"]` to `openbmb/MiniCPM-V-4.6` with Tiny Titan-safe parameter metadata.
- [x] Add `MINICPM_VISION_BASE_URL`, `MINICPM_VISION_API_KEY`, `MINICPM_VISION_MODEL`, and `MINICPM_VISION_TIMEOUT_SECONDS`.
- [x] Add safe env parsing so invalid timeout values do not break app import.
- [x] Ensure no API key value appears in runtime setup/status/evidence responses.

## 2. OpenAI-Compatible Vision Client

- [x] Add a helper to normalize the configured base URL to `/v1/chat/completions`.
- [x] Add a helper to resolve known article image URLs from `ARTICLE_IMAGES` and `PUBLIC_BASE_URL`.
- [x] Add a MiniCPM-V-4.6 chat-completions client using `Authorization: Bearer <key>`.
- [x] Send multimodal messages with accessibility-focused alt-text instructions and `image_url` content.
- [x] Validate `choices[0].message.content` before using it as `alt_text`.
- [x] Normalize/compact returned alt text for UI and transcript safety.

## 3. API Behavior

- [x] Update `ImageDescriptionRequest` to optionally accept `image_url`.
- [x] Update `describe_image_core()` to call MiniCPM-V-4.6 when configuration and image URL are available.
- [x] Preserve deterministic cached fallback descriptions when not configured.
- [x] Return fallback descriptions with visible warning metadata when live inference fails or returns invalid content.
- [x] Update `describe_article_images_core()` so article image receipts include live or fallback vision runtime metadata.
- [x] Keep `/api/describe-image` and `/api/image-descriptions` response shapes backward compatible.

## 4. Runtime Evidence

- [x] Update `runtime_setup_core()` with OpenAI-compatible MiniCPM-V-4.6 setup guidance and required env vars.
- [x] Update `_runtime_status_core()` to report MiniCPM-V-4.6 online/fallback-ready status.
- [x] Use `/models` or another lightweight non-image readiness check where possible.
- [x] Update `submission_readiness_core()` and `evidence_bundle_core()` only if their expectations need to distinguish live vision from fallback.
- [x] Ensure `/api/model-budget` still passes Tiny Titan.

## 5. Docs

- [x] Update `README.md` recommended model table and setup section.
- [x] Update `SUBMISSION.md` to name MiniCPM-V-4.6 for image understanding.
- [x] Update `FIELD_NOTES.md` with the OpenAI-compatible endpoint design and fallback behavior.
- [x] Mention that the user supplies `MINICPM_VISION_BASE_URL` and `MINICPM_VISION_API_KEY`.

## 6. Verification

- [x] Add verifier tests for fallback image descriptions with no MiniCPM config.
- [x] Add mocked tests for successful MiniCPM-V-4.6 chat-completions response.
- [x] Add mocked tests for failed/invalid MiniCPM responses falling back with warnings.
- [x] Add tests that runtime status/setup mention MiniCPM-V-4.6 and do not leak API keys.
- [x] Run `python scripts\verify.py`.
- [x] Run `python -m py_compile app.py scripts\verify.py`.
- [x] Run `git diff --check`.

## 7. Manual Endpoint Check

- [ ] Set `MINICPM_VISION_BASE_URL`.
- [ ] Set `MINICPM_VISION_API_KEY`.
- [ ] Call `/api/describe-image` for `model-map` and confirm live MiniCPM-V-4.6 runtime metadata.
- [ ] Open the Reader page and confirm image alt text is updated without breaking screen-reader narration.
