# Add Live Model Smoke Tests

## Why

The verifier covers fallback and mocked behavior, but the live MiniCPM and Modal Klein paths still require ad hoc manual checks. A small smoke-test script would make it easier to prove real deployments before submission without making normal CI depend on paid or local model services.

## What Changes

- Add an opt-in live smoke-test script for configured model endpoints.
- Test MiniCPM `/api/describe-image` through the app.
- Test Modal Klein `/api/generate-image` through the app.
- Report clear pass/fail/skipped results based on environment configuration.
- Keep `scripts/verify.py` offline and deterministic.

## Capabilities

- `live-vision-smoke-test`: confirm MiniCPM-V-4.6 image-description inference returns live metadata.
- `live-image-generation-smoke-test`: confirm Modal Klein generation returns live image metadata.
- `submission-readiness-check`: produce a concise terminal report for pre-demo validation.

## Non-Goals

- Do not require live endpoints for `scripts/verify.py`.
- Do not download or start large models automatically.
- Do not store generated images outside the existing app behavior unless needed for diagnostics.
- Do not print secret values.

## Impact

- A new script such as `scripts/live_smoke.py` will exercise live paths.
- README and submission docs will document how to run the script.
- Existing manual checklist items in OpenSpec tasks can reference the script.
- The script will use existing app APIs rather than duplicating model-client logic where possible.
