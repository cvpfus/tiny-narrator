# Tasks: Compact Model Runtime Status

## 1. Frontend Data Flow

- [x] Fetch `/api/runtime-status` on the reader page.
- [x] Merge runtime status with `/api/model-budget` model rows.
- [x] Handle missing or failed runtime status without breaking model stack rendering.

## 2. UI

- [x] Add compact per-role status labels to the Model Stack panel.
- [x] Reuse existing model budget/list styles where possible.
- [x] Add minimal CSS only for status labels.
- [x] Confirm removed evidence sections and `/evidence` UI do not return.

## 3. Verification

- [x] Update `scripts/verify.py` for model stack status rendering.
- [x] Run `python scripts\verify.py`.
- [x] Run `node --check static\app.js`.
- [x] Run `git diff --check`.
