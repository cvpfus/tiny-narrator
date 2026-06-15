# Design: Load Local Env File

## Overview

The app should support the common local workflow:

1. Copy `.env.example` to `.env`.
2. Fill in local endpoints and keys.
3. Start the app without additional shell exports.

Use `python-dotenv` because it is small, conventional, and avoids custom parsing. Call `load_dotenv()` at import time before constants such as `MINICPM_VISION_BASE_URL`, `KLEIN_MODAL_ENDPOINT`, and `LLAMA_CPP_BASE_URL` are read.

## Startup Flow

In `app.py`:

- import `load_dotenv` near other third-party imports
- call `load_dotenv()` before configuration constants are assigned
- keep existing `os.getenv(...)` calls unchanged after that point

`python-dotenv` does not override already-set process environment variables by default, which is the desired precedence.

## Dependency

Add `python-dotenv` to `requirements.txt`. Pinning is not required unless the repository already pins direct dependencies strictly.

## Documentation

Update local setup docs to say:

- `.env.example` is a template
- `.env` is ignored by git
- `.env` is loaded automatically by the app
- process environment values still override `.env`

Avoid showing real API keys or suggesting that users commit `.env`.

## Verification

Extend `scripts/verify.py` to check:

- `requirements.txt` includes `python-dotenv`
- `app.py` imports and calls `load_dotenv()`
- the call appears before core env constants are read
- `.env.example` still exists and remains free of real-looking secrets

The verifier should not require a real `.env` file.
