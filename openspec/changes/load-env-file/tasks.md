# Tasks: Load Local Env File

## 1. Dependency And Startup

- [x] Add `python-dotenv` to `requirements.txt`.
- [x] Import `load_dotenv` in `app.py`.
- [x] Call `load_dotenv()` before environment-backed configuration constants are assigned.
- [x] Confirm explicit process environment variables still take precedence.

## 2. Documentation

- [x] Update README setup instructions to mention automatic `.env` loading.
- [x] Update `.env.example` comments if needed.
- [x] Update runtime setup text if it currently implies shell exports are required.

## 3. Verification

- [x] Update `scripts/verify.py` to assert the dependency and startup wiring.
- [x] Run `python scripts\verify.py`.
- [x] Run `python -m py_compile app.py scripts\verify.py`.
- [x] Run `git diff --check`.
