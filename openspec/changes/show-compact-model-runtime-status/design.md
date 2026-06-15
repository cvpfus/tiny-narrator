# Design: Compact Model Runtime Status

## Overview

The Model Stack panel should remain compact but more informative. Each model role row should include:

- role label
- model id
- parameter count
- runtime
- Tiny Titan pass/fail
- current status label, such as `online`, `fallback-ready`, `configured`, or `offline`

## Data Sources

Use existing APIs:

- `/api/model-budget` for model roles and Tiny Titan information
- `/api/runtime-status` for live/fallback readiness

No backend schema change is required unless the runtime-status payload lacks enough role identifiers. Prefer a small frontend mapping from runtime keys to model roles.

## Frontend Mapping

Suggested mapping:

| Model Role | Runtime Status Key |
| --- | --- |
| narrator brain | `llama_cpp` or equivalent brain status |
| speech | `kokoro` or TTS status |
| image descriptor | `vision` |
| image generator | `image_generation` or Klein status |

Use the actual keys in the current payload. Missing keys should render as `fallback-ready` or `unknown` without throwing.

## UI

Use existing list/budget styles. Add only minimal CSS for compact status labels:

- short uppercase or title-case text
- neutral color for fallback-ready
- green/positive treatment for online
- warning treatment for offline/error

Keep labels readable and avoid one-hue theme drift.

## Verification

Verifier should check:

- reader page still lacks removed evidence DOM ids
- `static/app.js` fetches `/api/runtime-status`
- model stack rendering includes status text/targets
- `static/app.js` handles missing runtime status gracefully

No live endpoints are required.
