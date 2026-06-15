# Tasks: Secure Modal Klein Endpoint

## 1. Backend Client

- [x] Add `KLEIN_MODAL_TOKEN` configuration in `app.py`.
- [x] Send bearer auth to the Modal generation endpoint when configured.
- [x] Send bearer auth to Modal health/status checks when configured.
- [x] Ensure runtime status/setup can show token configured state without exposing the value.

## 2. Modal Worker

- [x] Read `KLEIN_MODAL_TOKEN` in `modal_workers/klein_image.py`.
- [x] Add token validation helper.
- [x] Reject unauthorized `POST /generate` requests with HTTP 401 when the token is configured.
- [x] Keep requests allowed when the token is not configured.

## 3. Documentation

- [x] Add `KLEIN_MODAL_TOKEN` to `.env.example`.
- [x] Update README Modal setup notes.
- [x] Update runtime setup guidance for the shared token.

## 4. Verification

- [x] Update `scripts/verify.py` for auth wiring and redaction.
- [x] Run `python scripts\verify.py`.
- [x] Run `python -m py_compile app.py scripts\verify.py modal_workers\klein_image.py`.
- [x] Run `git diff --check`.
