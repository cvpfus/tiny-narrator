# Tasks: Describe Generated Thumbnails

## 1. Frontend Integration

- [x] Add a generated-thumbnail description helper in `static/generate.js`.
- [x] Call `/api/describe-image` with `image_id`, `caption`, `prompt`, and `image_url`.
- [x] Update `generatedThumbnail.alt` from returned `alt_text`.
- [x] Preserve generic fallback alt text when description fails.
- [x] Refresh reader state if needed so later narration uses the updated alt text.

## 2. Runtime Feedback

- [x] Reuse existing thumbnail receipt/status UI for descriptor runtime if it remains compact.
- [x] Avoid adding a large evidence panel or separate page.

## 3. Verification

- [x] Update `scripts/verify.py` for generated-thumbnail description wiring.
- [x] Run `python scripts\verify.py`.
- [x] Run `node --check static\generate.js`.
- [x] Run `git diff --check`.
