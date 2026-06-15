"""Live model smoke tests for Tiny Narrator.

Run against a running local app to verify configured model endpoints:

    python scripts/live_smoke.py --base-url http://127.0.0.1:7860

Checks:
  - /api/runtime-status: confirms reader brain, speech, vision, image generation status
  - /api/describe-image: confirms MiniCPM-V-4.6 image description path
  - /api/generate-image: confirms Modal Klein image generation path

Exit codes:
  0 - all configured checks passed or skipped
  1 - one or more configured checks failed

Secrets (API keys, tokens) are never printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _get_json(url: str, timeout: int = 30) -> dict:
    """Fetch a JSON GET endpoint and return the parsed payload."""
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    """POST JSON to an endpoint and return the parsed response."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _format_elapsed(ms: float) -> str:
    if ms < 1000:
        return f"{round(ms)} ms"
    return f"{ms / 1000:.2f} s"


def _status_label(status: str) -> str:
    return {
        "online": "PASS",
        "fallback-ready": "SKIP",
        "fallback": "SKIP",
        "placeholder-ready": "SKIP",
        "offline": "FAIL",
    }.get(status, "SKIP")


def _role_status(runtime_status: dict[str, dict], role: str) -> str:
    return str(runtime_status.get(role, {}).get("status", "unknown"))


def _role_is_configured(runtime_status: dict[str, dict], role: str) -> bool:
    details = runtime_status.get(role, {})
    if details.get("configured") is True:
        return True
    return bool(details.get("endpoint") or details.get("base_url"))


def check_runtime_status(base_url: str) -> dict[str, dict]:
    """Fetch runtime status and return per-role metadata."""
    start = time.perf_counter()
    try:
        payload = _get_json(f"{base_url}/api/runtime-status")
        elapsed = (time.perf_counter() - start) * 1000
        roles = {
            "reader_brain": payload.get("reader_brain", {}),
            "vision": payload.get("vision", {}),
            "speech": payload.get("speech", {}),
            "image_generation": payload.get("image_generation", {}),
        }
        labels = ", ".join(f"{role}={_role_status(roles, role)}" for role in roles)
        print(f"  runtime-status    {_format_elapsed(elapsed):>10}  {labels}")
        return roles
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  runtime-status    {_format_elapsed(elapsed):>10}  FAIL ({exc.__class__.__name__})")
        return {}


def check_describe_image(base_url: str, runtime_status: dict[str, dict]) -> bool:
    """Smoke test /api/describe-image for a known article image."""
    vision_status = _role_status(runtime_status, "vision")
    vision_configured = _role_is_configured(runtime_status, "vision")
    if not vision_configured and vision_status in {"fallback-ready", "unknown"}:
        print(f"  describe-image    {'SKIP':>10}  vision not configured")
        return True
    if vision_configured and vision_status != "online":
        print(f"  describe-image    {'FAIL':>10}  vision configured but status={vision_status}")
        return False

    start = time.perf_counter()
    try:
        payload = _post_json(
            f"{base_url}/api/describe-image",
            {"image_id": "desk-reader", "caption": "article reader"},
            timeout=90,
        )
        elapsed = (time.perf_counter() - start) * 1000
        runtime = payload.get("runtime", "unknown")
        alt_text = payload.get("alt_text", "")
        truncated = alt_text[:80] + ("..." if len(alt_text) > 80 else "") if alt_text else "(empty)"
        if runtime == "minicpm-v4.6":
            print(f"  describe-image    {_format_elapsed(elapsed):>10}  PASS  runtime={runtime}  alt={truncated}")
            return True
        elif runtime == "fallback":
            print(f"  describe-image    {_format_elapsed(elapsed):>10}  FAIL  runtime={runtime} (expected live)")
            return False
        else:
            print(f"  describe-image    {_format_elapsed(elapsed):>10}  FAIL  runtime={runtime} (unexpected)")
            return False
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  describe-image    {_format_elapsed(elapsed):>10}  FAIL  ({exc.__class__.__name__})")
        return False


def check_generate_image(base_url: str, runtime_status: dict[str, dict]) -> bool:
    """Smoke test /api/generate-image with a deterministic prompt."""
    image_status = _role_status(runtime_status, "image_generation")
    image_configured = _role_is_configured(runtime_status, "image_generation")
    if not image_configured and image_status in {"fallback-ready", "unknown"}:
        print(f"  generate-image    {'SKIP':>10}  Klein not configured")
        return True
    if image_configured and image_status != "online":
        print(f"  generate-image    {'FAIL':>10}  Klein configured but status={image_status}")
        return False

    start = time.perf_counter()
    try:
        payload = _post_json(
            f"{base_url}/api/generate-image",
            {"prompt": "smoke test accessible article thumbnail", "seed": 42},
            timeout=180,
        )
        elapsed = (time.perf_counter() - start) * 1000
        runtime = payload.get("runtime", "unknown")
        image_url = payload.get("image_url", "")
        if runtime == "modal-klein":
            print(f"  generate-image    {_format_elapsed(elapsed):>10}  PASS  runtime={runtime}  url={image_url[:60]}")
            return True
        elif runtime == "fallback":
            print(f"  generate-image    {_format_elapsed(elapsed):>10}  FAIL  runtime={runtime} (expected live Klein)")
            return False
        else:
            print(f"  generate-image    {_format_elapsed(elapsed):>10}  FAIL  runtime={runtime} (unexpected)")
            return False
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  generate-image    {_format_elapsed(elapsed):>10}  FAIL  ({exc.__class__.__name__})")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Tiny Narrator live model smoke tests")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860", help="App base URL (default: http://127.0.0.1:7860)")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    overall_start = time.perf_counter()

    print(f"Tiny Narrator live smoke tests — {base_url}")
    print()

    print("Checks:")
    runtime_status = check_runtime_status(base_url)

    if not runtime_status:
        print()
        print("Could not reach the app. Is it running?")
        sys.exit(1)

    vision_configured = _role_is_configured(runtime_status, "vision")
    klein_configured = _role_is_configured(runtime_status, "image_generation")

    describe_ok = check_describe_image(base_url, runtime_status)
    generate_ok = check_generate_image(base_url, runtime_status)

    overall_elapsed = (time.perf_counter() - overall_start) * 1000
    print()

    failures = []
    if vision_configured and not describe_ok:
        failures.append("describe-image")
    if klein_configured and not generate_ok:
        failures.append("generate-image")

    if failures:
        print(f"FAILED: {', '.join(failures)}  ({_format_elapsed(overall_elapsed)} total)")
        sys.exit(1)
    else:
        configured_count = sum(1 for v in [vision_configured, klein_configured] if v)
        skipped_count = 2 - configured_count
        print(f"DONE: {configured_count} passed, {skipped_count} skipped  ({_format_elapsed(overall_elapsed)} total)")
        sys.exit(0)


if __name__ == "__main__":
    main()
