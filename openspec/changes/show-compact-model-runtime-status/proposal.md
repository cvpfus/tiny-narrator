# Show Compact Model Runtime Status

## Why

The reader page now has a compact model stack panel, but it does not clearly show whether each role is running live inference or fallback behavior. Judges should be able to confirm the active model path without bringing back the long evidence sidebar.

## What Changes

- Fetch runtime status alongside model budget data on the main reader page.
- Add compact live/fallback/offline status labels to the Model Stack panel.
- Keep the sidebar reader-first and short.
- Avoid restoring removed evidence panels or the `/evidence` page.

## Capabilities

- `compact-model-runtime-status`: show per-role live/fallback status in the existing Model Stack panel.
- `reader-first-proof`: expose enough model proof for judges without crowding narration controls.
- `status-refresh`: refresh model status at startup and after relevant actions if useful.

## Non-Goals

- Do not add a dedicated evidence page.
- Do not add back runtime runbooks, image receipts, or award evidence panels.
- Do not expose API keys or secrets.
- Do not block reader controls on status checks.

## Impact

- `static/app.js` will merge `/api/model-budget` with `/api/runtime-status` results.
- `static/index.html` may add small status target elements inside the model stack section if needed.
- `static/app.css` may gain compact status-pill styles.
- `scripts/verify.py` will ensure runtime status is fetched and evidence panels remain absent.
