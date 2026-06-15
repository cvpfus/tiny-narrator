# Design: Describe Generated Thumbnails

## Overview

The generate page should render the generated article immediately, then asynchronously enhance the generated thumbnail with a real image description.

This preserves perceived speed and keeps fallback behavior reliable. The image descriptor request can return either live MiniCPM output or deterministic fallback text through the existing backend endpoint.

## Frontend Flow

After `renderArticle(payload)` sets the thumbnail `src`:

1. Set a generic initial alt text such as `Generated thumbnail for <topic>.`
2. Start `describeGeneratedThumbnail(payload)` without blocking page rendering.
3. POST to `/api/describe-image` with:
   - `image_id`: stable id such as `generated-thumbnail`
   - `caption`: article title/topic
   - `prompt`: image-generation prompt or topic prompt
   - `image_url`: `payload.thumbnail.image_url`
4. If the response returns `ok` and `alt_text`, assign it to `generatedThumbnail.alt`.
5. Update any visible receipt/status text with descriptor runtime if existing UI has a suitable compact place.
6. Refresh reader node state if required so screen-reader mode reads the improved alt text.

If the request fails, keep the generic alt text and do not interrupt the generated article UI.

## Reader Behavior

Reader narration should read `img.alt` dynamically or refresh readable nodes after the alt update. If the current readable node is the generated thumbnail when the new alt arrives, the app may leave current narration alone; the updated text should be used for future navigation.

## Backend

No new API is required. `/api/describe-image` already accepts `image_url`. If implementation discovers URL normalization problems for generated image URLs, fix them in the existing resolver.

## Verification

Add verifier coverage that:

- `static/generate.js` calls `/api/describe-image`
- the request includes `image_url`
- `generatedThumbnail.alt` is updated from `alt_text`
- failures keep a fallback alt path

No network calls or live credentials should be required.
