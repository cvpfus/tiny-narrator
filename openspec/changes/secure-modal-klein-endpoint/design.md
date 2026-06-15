# Design: Secure Modal Klein Endpoint

## Overview

Use a shared token because the Modal worker is an app-to-app endpoint, not an end-user API. The token is optional but recommended for live deployment.

Both sides read `KLEIN_MODAL_TOKEN`:

- Tiny Narrator backend sends it when calling Modal.
- Modal worker requires it when set in the worker environment.

## Request Authentication

Tiny Narrator should include:

```http
Authorization: Bearer <KLEIN_MODAL_TOKEN>
```

The worker should accept either:

- `Authorization: Bearer <token>`
- `X-Tiny-Narrator-Token: <token>`

Bearer auth should be the primary documented path.

## Worker Behavior

In `modal_workers/klein_image.py`:

- read `KLEIN_MODAL_TOKEN` from the environment
- if empty, allow requests for compatibility
- if set, reject missing or mismatched token with HTTP 401
- apply the check to `POST /generate`
- optionally apply the check to `GET /health` so private deployments can hide readiness details
- avoid applying auth to media URLs unless generated media needs to be private

## App Behavior

In `app.py`:

- read `KLEIN_MODAL_TOKEN`
- include auth headers in `_call_modal_klein()`
- include auth headers in Modal health/status checks
- expose only whether a token is configured, never the token itself

## Documentation

Docs should explain that the same token must be configured in:

- local/server `.env`
- Modal secret or deployment environment

Do not include real token examples. Use placeholder values only.

## Verification

Verifier should assert:

- token env variable exists in `.env.example`
- app sends `Authorization` for Modal calls
- worker validates configured token
- runtime/status/setup payloads do not include token values

No live Modal call is required.
