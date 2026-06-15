# Describe Generated Thumbnails

## Why

The generated-article page creates a thumbnail image through the image-generation role, but the UI assigns a generic alt string instead of asking the image descriptor role to describe the actual generated image. That weakens the core accessibility demo because generated visual content should become screen-reader-readable automatically.

## What Changes

- Call `/api/describe-image` after a generated thumbnail is available.
- Send the generated thumbnail URL, prompt, and article topic to the backend.
- Replace the generic thumbnail alt text with MiniCPM-generated or fallback alt text.
- Keep the page responsive if the descriptor endpoint is slow or unavailable.
- Ensure reader-mode narration uses the updated alt text when available.

## Capabilities

- `generated-image-description`: describe generated thumbnails with the configured MiniCPM-V-4.6 image descriptor path.
- `generated-image-fallback-alt`: preserve a useful fallback alt string when live description fails.
- `reader-alt-refresh`: let the reader experience pick up improved generated-image alt text.

## Non-Goals

- Do not change the image-generation API response shape.
- Do not change MiniCPM endpoint configuration.
- Do not block article rendering on image description.
- Do not require live MiniCPM credentials for verification.

## Impact

- `static/generate.js` will request a generated-thumbnail description after rendering the generated article.
- `app.py` already supports optional `image_url`; backend changes should be minimal unless validation gaps are found.
- `scripts/verify.py` will check that generated-image alt text flows through `/api/describe-image`.
- Docs may mention that generated thumbnails are also described for screen readers.
