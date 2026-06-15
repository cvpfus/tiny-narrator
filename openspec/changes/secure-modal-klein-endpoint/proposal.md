# Secure Modal Klein Endpoint

## Why

The Modal Klein worker exposes `POST /generate` without an app-level token. Modal URLs are not meant to be treated as secrets, and image generation can consume paid compute. The endpoint should support a simple shared-token guard while keeping local fallback behavior unchanged.

## What Changes

- Add optional `KLEIN_MODAL_TOKEN` configuration.
- Send the token from Tiny Narrator to the Modal worker when configured.
- Require the token in the Modal worker when configured there.
- Keep unauthenticated behavior only when no token is configured, so local tests and demos remain simple.
- Ensure runtime setup/status never exposes the token value.

## Capabilities

- `modal-klein-token-auth`: protect live Klein generation with bearer or app token headers.
- `safe-modal-status`: perform health checks with auth when required.
- `secret-redaction`: document and verify that token values are never leaked.

## Non-Goals

- Do not add user accounts or browser login.
- Do not require auth for local fallback generation.
- Do not change the `/api/generate-image` browser-facing contract.
- Do not hard-code secrets in code, docs, or verifier fixtures.

## Impact

- `app.py` will read `KLEIN_MODAL_TOKEN` and attach it to Modal worker requests.
- `modal_workers/klein_image.py` will validate the incoming token when configured.
- `.env.example`, README, and runtime setup text will document the token.
- `scripts/verify.py` will check auth wiring and secret redaction.
