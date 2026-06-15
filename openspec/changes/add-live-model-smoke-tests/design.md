# Design: Live Model Smoke Tests

## Overview

Add a separate opt-in script for live model checks. Normal verification remains fast and offline. The smoke script is for the developer to run after configuring model endpoints and starting the app.

## Script Shape

Suggested command:

```powershell
python scripts\live_smoke.py --base-url http://127.0.0.1:7860
```

Default base URL can be `http://127.0.0.1:7860`.

The script should:

1. call `/api/runtime-status`
2. call `/api/describe-image` for a known article image
3. call `/api/generate-image` with a short deterministic prompt
4. summarize which roles were live, fallback, skipped, or failed
5. exit non-zero only when a configured live check fails

## Skipping Rules

If the relevant env/config is not present or runtime status says fallback-ready, mark that check as skipped instead of failed. This keeps the script usable in partial setups.

## Output

Output should be concise and redacted:

- model role
- endpoint path tested
- runtime returned
- elapsed time
- pass/skip/fail

Never print API keys, Modal tokens, or bearer headers.

## Dependencies

Prefer standard-library `urllib.request` to avoid adding a new dependency. If the repo already depends on `requests` and uses it in scripts, reusing it is acceptable.

## Verification

`scripts/verify.py` should check that the smoke script exists, is syntactically valid, and documents redaction/skipping behavior. It should not run live checks.
