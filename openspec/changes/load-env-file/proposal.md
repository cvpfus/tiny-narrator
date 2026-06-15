# Load Local Env File

## Why

Tiny Narrator now documents credentials in `.env.example`, but the app only reads process environment variables. A local developer can create `.env` exactly as the docs imply and still get fallback behavior because `app.py` never loads the file.

This should be fixed before more live-model work lands, because MiniCPM, Modal Klein, llama.cpp, public URLs, and timeouts all depend on environment configuration.

## What Changes

- Load `.env` automatically during app startup before environment-backed settings are read.
- Add `python-dotenv` to project dependencies.
- Keep explicit process environment values authoritative.
- Update setup docs to say `.env` is read automatically.
- Extend verification so missing dependency or misplaced loading is caught.

## Capabilities

- `local-env-loading`: load `.env` for local development without requiring shell-specific export commands.
- `env-precedence`: preserve process environment precedence over `.env` values.
- `configuration-verification`: verify dependency and docs coverage for local environment loading.

## Non-Goals

- Do not commit real secrets.
- Do not change names or meanings of existing environment variables.
- Do not require `.env` to exist for verification or production startup.
- Do not expose any secret values through runtime APIs.

## Impact

- `app.py` will import and call `load_dotenv()` before reading configuration constants.
- `requirements.txt` will include `python-dotenv`.
- `.env.example`, README, and runtime setup text may be updated to clarify the workflow.
- `scripts/verify.py` will assert that local env loading is wired in.
