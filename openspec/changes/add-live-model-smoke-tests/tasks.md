# Tasks: Live Model Smoke Tests

## 1. Smoke Script

- [x] Add `scripts/live_smoke.py`.
- [x] Support `--base-url` with a local default.
- [x] Check `/api/runtime-status`.
- [x] Check `/api/describe-image` for a known article image.
- [x] Check `/api/generate-image` with a deterministic prompt.
- [x] Print concise pass/skip/fail results with elapsed time.
- [x] Redact secrets and avoid printing headers.

## 2. Behavior

- [x] Skip live checks when the corresponding runtime is not configured.
- [x] Fail configured checks when the app returns fallback or invalid live metadata.
- [x] Exit non-zero only for failed configured checks.

## 3. Documentation

- [x] Update README with the smoke-test command.
- [x] Update SUBMISSION or FIELD_NOTES with the pre-demo validation workflow.

## 4. Verification

- [x] Update `scripts/verify.py` to check smoke script presence and syntax.
- [x] Run `python scripts\verify.py`.
- [x] Run `python -m py_compile scripts\live_smoke.py scripts\verify.py`.
- [x] Run `git diff --check`.
