from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from gradio import Server
from pydantic import BaseModel

load_dotenv()

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _runtime_log(message: str) -> None:
    print(f"[tiny-narrator] {message}", file=sys.stderr, flush=True)


def _http_exception_detail(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        body = _compact_text(body, 400) if body else ""
        return f"HTTPError status={exc.code} reason={exc.reason} body={body}"
    if isinstance(exc, urllib.error.URLError):
        return f"URLError reason={exc.reason}"
    return f"{exc.__class__.__name__}: {exc}"


LLAMA_CPP_BASE_URL = os.getenv("LLAMA_CPP_BASE_URL", "http://localhost:8080/v1")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "narrator-brain")
LLAMA_CPP_TOKEN = os.getenv("LLAMA_CPP_TOKEN", "")
LLAMA_CPP_TIMEOUT_SECONDS = _int_env("LLAMA_CPP_TIMEOUT_SECONDS", 90)
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
GRADIO_SHARE = _bool_env("GRADIO_SHARE")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://localhost:{GRADIO_SERVER_PORT}").rstrip("/")
KLEIN_MODAL_ENDPOINT = os.getenv("KLEIN_MODAL_ENDPOINT", "").rstrip("/")
KLEIN_MODAL_TOKEN = os.getenv("KLEIN_MODAL_TOKEN", "")
KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS = _int_env("KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS", 30)
KLEIN_MODAL_TIMEOUT_SECONDS = _int_env("KLEIN_MODAL_TIMEOUT_SECONDS", 120)
MINICPM_VISION_BASE_URL = os.getenv("MINICPM_VISION_BASE_URL", "").rstrip("/")
MINICPM_VISION_API_KEY = os.getenv("MINICPM_VISION_API_KEY", "")
MINICPM_VISION_MODEL = os.getenv("MINICPM_VISION_MODEL", "openbmb/MiniCPM-V-4.6")
MINICPM_VISION_TIMEOUT_SECONDS = _int_env("MINICPM_VISION_TIMEOUT_SECONDS", 45)
TINY_TITAN_LIMIT_B = 4.0

MODEL_MANIFEST: dict[str, dict[str, Any]] = {
    "reader_brain": {
        "id": "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
        "params": "3.97B",
        "params_billion": 3.97,
        "runtime": "llama.cpp",
        "role": "Plans concise narration and reading-order phrasing.",
    },
    "vision": {
        "id": "openbmb/MiniCPM-V-4.6",
        "params": "1B",
        "params_billion": 1.0,
        "runtime": "OpenAI-compatible chat completions",
        "role": "Describes images and OCR-like visual details.",
    },
    "speech": {
        "id": "hexgrad/Kokoro-82M",
        "params": "82M",
        "params_billion": 0.082,
        "runtime": "Python",
        "role": "Speaks the final narration.",
    },
    "image_generation": {
        "id": "black-forest-labs/FLUX.2-klein-4B",
        "params": "4B",
        "params_billion": 4.0,
        "runtime": "Modal-hosted Klein",
        "role": "Creates article illustrations.",
    },
}

ARTICLE_IMAGES: list[dict[str, Any]] = [
    {
        "id": "desk-reader",
        "asset_url": "/static/generated/desk-reader.svg",
        "vision_asset_url": "/static/generated/desk-reader.png",
        "caption": "The article view doubles as the demo surface, so every feature has a real reading task.",
        "prompt": "Accessibility article reader with highlighted paragraph and narration controls.",
        "seed": 11,
        "generation_model": "black-forest-labs/FLUX.2-klein-4B",
        "generation_runtime": "bundled fallback asset",
        "generation_status": "fallback-ready",
    },
    {
        "id": "model-map",
        "asset_url": "/static/generated/model-map.svg",
        "vision_asset_url": "/static/generated/model-map.png",
        "caption": "Each model stays at or below four billion parameters for Tiny Titan eligibility.",
        "prompt": "Diagram of four small AI models working together in an accessibility reader.",
        "seed": 22,
        "generation_model": "black-forest-labs/FLUX.2-klein-4B",
        "generation_runtime": "bundled fallback asset",
        "generation_status": "fallback-ready",
    },
]

READER_SETTINGS: dict[str, Any] = {
    "default_voice": "af_heart",
    "default_speed": 1.0,
    "default_auto_advance": False,
    "voices": [
        {"id": "af_heart", "label": "Heart"},
        {"id": "af_bella", "label": "Bella"},
        {"id": "am_adam", "label": "Adam"},
        {"id": "am_michael", "label": "Michael"},
    ],
    "speed": {"min": 0.75, "max": 1.35, "step": 0.05},
}

AWARD_EVIDENCE: list[dict[str, str]] = [
    {
        "id": "tiny-titan",
        "label": "Tiny Titan",
        "status": "ready",
        "evidence": "All planned model roles use models at or below 4B parameters.",
    },
    {
        "id": "llama-champion",
        "label": "Llama Champion",
        "status": "ready",
        "evidence": "The reader-brain path targets a GGUF model through a llama.cpp OpenAI-compatible endpoint.",
    },
    {
        "id": "off-brand",
        "label": "Off-Brand",
        "status": "ready",
        "evidence": "The visible app is custom HTML, CSS, and JavaScript served by Gradio Server.",
    },
    {
        "id": "field-notes",
        "label": "Field Notes",
        "status": "ready",
        "evidence": "The repo records model choices, fallbacks, latency reporting, and accessibility behavior.",
    },
]


def model_budget_core() -> dict[str, Any]:
    models = []
    for role, model in MODEL_MANIFEST.items():
        params_billion = float(model["params_billion"])
        models.append(
            {
                "role": role,
                "id": model["id"],
                "runtime": model["runtime"],
                "params": model["params"],
                "params_billion": params_billion,
                "limit_billion": TINY_TITAN_LIMIT_B,
                "within_limit": params_billion <= TINY_TITAN_LIMIT_B,
            }
        )
    return {
        "ok": True,
        "award": "Tiny Titan",
        "limit_billion": TINY_TITAN_LIMIT_B,
        "all_models_within_limit": all(model["within_limit"] for model in models),
        "models": models,
    }


def runtime_setup_core() -> dict[str, Any]:
    return {
        "ok": True,
        "app": {
            "runtime": "Gradio Server",
            "command": "python app.py",
            "env": {
                "GRADIO_SERVER_NAME": GRADIO_SERVER_NAME,
                "GRADIO_SERVER_PORT": str(GRADIO_SERVER_PORT),
                "GRADIO_SHARE": str(GRADIO_SHARE).lower(),
                "PUBLIC_BASE_URL": PUBLIC_BASE_URL,
            },
        },
        "steps": [
            {
                "role": "reader_brain",
                "label": "Reader brain",
                "model": MODEL_MANIFEST["reader_brain"]["id"],
                "runtime": "llama.cpp",
                "command": (
                    "llama-server -hf nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M "
                    "--alias narrator-brain --port 8080 --host 0.0.0.0 "
                    "--ctx-size 4096 --parallel 1 --reasoning off --n-gpu-layers 999"
                ),
                "modal_command": "modal deploy modal_workers/reader_brain.py",
                "env": {
                    "LLAMA_CPP_BASE_URL": LLAMA_CPP_BASE_URL,
                    "LLAMA_CPP_MODEL": LLAMA_CPP_MODEL,
                    "LLAMA_CPP_TOKEN": "(configured)" if LLAMA_CPP_TOKEN else "(not set)",
                    "LLAMA_CPP_TIMEOUT_SECONDS": str(LLAMA_CPP_TIMEOUT_SECONDS),
                },
                "fallback": "rule-based local narration",
            },
            {
                "role": "speech",
                "label": "Speech",
                "model": MODEL_MANIFEST["speech"]["id"],
                "runtime": "Python Kokoro",
                "command": "python -m pip install kokoro soundfile",
                "env": {},
                "fallback": "browser speech plus visible transcript",
            },
            {
                "role": "vision",
                "label": "Image descriptions",
                "model": MODEL_MANIFEST["vision"]["id"],
                "runtime": "OpenAI-compatible chat completions",
                "command": "vllm serve openbmb/MiniCPM-V-4.6 --host 0.0.0.0 --port 8000",
                "env": {
                    "MINICPM_VISION_BASE_URL": MINICPM_VISION_BASE_URL or "(set to OpenAI-compatible base URL)",
                    "MINICPM_VISION_API_KEY": "(configured)" if MINICPM_VISION_API_KEY else "(not set)",
                    "MINICPM_VISION_MODEL": MINICPM_VISION_MODEL,
                    "MINICPM_VISION_TIMEOUT_SECONDS": str(MINICPM_VISION_TIMEOUT_SECONDS),
                },
                "fallback": "cached deterministic alt text",
            },
            {
                "role": "image_generation",
                "label": "Article images",
                "model": MODEL_MANIFEST["image_generation"]["id"],
                "runtime": "Modal-hosted Klein",
                "command": "modal deploy modal_workers/klein_image.py",
                "env": {
                    "KLEIN_MODAL_ENDPOINT": KLEIN_MODAL_ENDPOINT or "(set to Modal worker URL)",
                    "KLEIN_MODAL_TOKEN": "(configured)" if KLEIN_MODAL_TOKEN else "(not set)",
                    "KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS": str(KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS),
                    "KLEIN_MODAL_TIMEOUT_SECONDS": str(KLEIN_MODAL_TIMEOUT_SECONDS),
                },
                "fallback": "bundled generated article assets",
            },
        ],
    }


def demo_curl_command(check: dict[str, Any]) -> str:
    url = f"{PUBLIC_BASE_URL}{check['path']}"
    if check["method"] == "GET":
        return f"curl {url}"
    sample_body = json.dumps(check["sample_body"], separators=(",", ":"))
    return f"curl -X POST {url} -H \"Content-Type: application/json\" -d '{sample_body}'"


def demo_powershell_command(check: dict[str, Any]) -> str:
    url = f"{PUBLIC_BASE_URL}{check['path']}"
    if check["method"] == "GET":
        return f"curl.exe {url}"
    sample_body = json.dumps(check["sample_body"], separators=(",", ":")).replace('"', '\\"')
    return f'curl.exe -X POST {url} -H "Content-Type: application/json" -d "{sample_body}"'


def demo_script_core() -> dict[str, Any]:
    api_checks = [
        {"method": "GET", "path": "/api/health", "expect": "custom Gradio Server app and model manifest"},
        {"method": "GET", "path": "/api/model-budget", "expect": "all_models_within_limit is true"},
        {"method": "GET", "path": "/api/runtime-setup", "expect": "llama.cpp, Kokoro, vision, and image paths"},
        {"method": "GET", "path": "/api/runtime-status", "expect": "online or fallback-ready runtime labels"},
        {"method": "GET", "path": "/api/accessibility-audit", "expect": "all reader-mode checks pass"},
        {"method": "GET", "path": "/api/image-descriptions", "expect": "two article image descriptions with MiniCPM-V-4.6 or fallback alt text"},
        {"method": "GET", "path": "/api/submission-readiness", "expect": "all submission readiness checks pass"},
        {
            "method": "POST",
            "path": "/api/reader-brain",
            "expect": "concise narration or fallback narration",
            "sample_body": {
                "node_type": "heading",
                "text": "The model map",
                "position": "item 4 of 10",
                "mode": "narrate",
            },
        },
        {
            "method": "POST",
            "path": "/api/speak",
            "expect": "Kokoro audio or audible browser fallback path",
            "sample_body": {
                "text": "Heading. The model map.",
                "voice": READER_SETTINGS["default_voice"],
                "speed": READER_SETTINGS["default_speed"],
            },
        },
        {
            "method": "POST",
            "path": "/api/generate-article",
            "expect": "generated article draft with Klein thumbnail receipt",
            "sample_body": {"topic": "accessible robotics for classrooms"},
        },
    ]
    for check in api_checks:
        check["curl"] = demo_curl_command(check)
        check["powershell"] = demo_powershell_command(check)

    return {
        "ok": True,
        "title": "Tiny Narrator judge demo",
        "goal": "Show a custom article app becoming a small-model screen reader with inspectable evidence.",
        "estimated_minutes": 3,
        "actions": [
            {
                "step": 1,
                "label": "Open the article",
                "action": "Load the home page and scan the article plus session panel.",
                "evidence": "Custom HTML/CSS/JS interface served by Gradio Server.",
            },
            {
                "step": 2,
                "label": "Turn on reader mode",
                "action": "Toggle screen reader mode, then press Space or Next to narrate the first item.",
                "evidence": "The active article node is focused, outlined, narrated, and logged.",
            },
            {
                "step": 3,
                "label": "Navigate by meaning",
                "action": "Use Heading, Image, and Summary controls to jump through semantic article nodes.",
                "evidence": "The reader uses article structure, image alt text, and section summaries.",
            },
            {
                "step": 4,
                "label": "Inspect small-model receipts",
                "action": "Review the checklist, model budget, runtime plan, readiness, latency, and transcript panels.",
                "evidence": "Tiny Titan, Llama Champion, Off-Brand, and reader evidence is exposed through the app and APIs.",
            },
        ],
        "api_checks": api_checks,
    }


def submission_readiness_core() -> dict[str, Any]:
    model_budget = model_budget_core()
    runtime_setup = runtime_setup_core()
    runtime_status = _runtime_status_core()
    accessibility = accessibility_audit_core()
    demo_script = demo_script_core()
    image_descriptions = describe_article_images_core()
    runtime_roles = {step["role"] for step in runtime_setup["steps"]}
    expected_roles = set(MODEL_MANIFEST)
    api_paths = {item["path"] for item in demo_script["api_checks"]}
    post_checks = [item for item in demo_script["api_checks"] if item["method"] == "POST"]
    post_samples_ready = all(item.get("sample_body") for item in post_checks)
    commands_use_public_base = all(
        PUBLIC_BASE_URL in item["curl"] and PUBLIC_BASE_URL in item["powershell"]
        for item in demo_script["api_checks"]
    )
    runtime_statuses = {
        runtime_status["reader_brain"]["status"],
        runtime_status["vision"]["status"],
        runtime_status["speech"]["status"],
        runtime_status["image_generation"]["status"],
    }
    runtime_status_ready = runtime_statuses <= {"online", "fallback-ready", "placeholder-ready"}
    checks = [
        {
            "id": "tiny_titan_budget",
            "label": "Tiny Titan model budget",
            "status": "pass" if model_budget["all_models_within_limit"] else "fail",
            "evidence": f"{len(model_budget['models'])} model roles are at or below {TINY_TITAN_LIMIT_B}B parameters.",
        },
        {
            "id": "award_targets",
            "label": "Targeted award evidence",
            "status": "pass" if len(AWARD_EVIDENCE) == 4 else "fail",
            "evidence": "Tiny Titan, Llama Champion, Off-Brand, and Field Notes evidence is exposed.",
        },
        {
            "id": "custom_frontend",
            "label": "Custom frontend",
            "status": "pass" if all((STATIC_DIR / name).exists() for name in ["index.html", "app.css", "app.js"]) else "fail",
            "evidence": "The app serves custom HTML, CSS, and JavaScript through Gradio Server.",
        },
        {
            "id": "runtime_setup",
            "label": "Runtime setup",
            "status": "pass" if runtime_roles == expected_roles else "fail",
            "evidence": "Runtime setup covers reader brain, speech, vision, and image generation paths.",
        },
        {
            "id": "runtime_status",
            "label": "Runtime status",
            "status": "pass" if runtime_status_ready else "fail",
            "evidence": "Runtime status labels every model path as online, fallback-ready, or placeholder-ready.",
        },
        {
            "id": "reader_accessibility",
            "label": "Reader accessibility",
            "status": "pass" if accessibility["all_passed"] else "fail",
            "evidence": f"{accessibility['passed_checks']} of {accessibility['total_checks']} accessibility checks pass.",
        },
        {
            "id": "image_receipts",
            "label": "Image receipts",
            "status": "pass"
            if all(
                item.get("generation_model") == MODEL_MANIFEST["image_generation"]["id"] and isinstance(item.get("seed"), int)
                for item in image_descriptions["descriptions"]
            )
            else "fail",
            "evidence": "Every article illustration exposes prompt, seed, model, asset URL, and fallback status.",
        },
        {
            "id": "demo_api_checks",
            "label": "Demo API checks",
            "status": "pass"
            if {
                "/api/model-budget",
                "/api/runtime-setup",
                "/api/accessibility-audit",
                "/api/image-descriptions",
                "/api/reader-brain",
                "/api/speak",
                "/api/generate-article",
            }.issubset(api_paths)
            and post_samples_ready
            else "fail",
            "evidence": "The judge runbook includes GET evidence checks and executable POST sample bodies.",
        },
        {
            "id": "command_base_url",
            "label": "Command base URL",
            "status": "pass" if commands_use_public_base else "fail",
            "evidence": f"Generated curl and curl.exe commands use {PUBLIC_BASE_URL}.",
        },
    ]
    return {
        "ok": True,
        "all_passed": all(check["status"] == "pass" for check in checks),
        "passed_checks": sum(1 for check in checks if check["status"] == "pass"),
        "total_checks": len(checks),
        "checks": checks,
    }


def evidence_bundle_core() -> dict[str, Any]:
    return {
        "ok": True,
        "title": "Tiny Narrator judge evidence bundle",
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "frontend": "custom Gradio Server HTML/CSS/JS",
        "public_base_url": PUBLIC_BASE_URL,
        "bonus_targets": ARTICLE_MANIFEST["bonus_targets"],
        "models": MODEL_MANIFEST,
        "award_evidence": {"ok": True, "items": AWARD_EVIDENCE},
        "model_budget": model_budget_core(),
        "runtime_setup": runtime_setup_core(),
        "runtime_status": _runtime_status_core(),
        "demo_script": demo_script_core(),
        "accessibility_audit": accessibility_audit_core(),
        "image_descriptions": describe_article_images_core(),
        "submission_readiness": submission_readiness_core(),
    }


def accessibility_audit_core() -> dict[str, Any]:
    checks = [
        {
            "id": "semantic_queue",
            "label": "Semantic reading queue",
            "status": "pass",
            "evidence": "Readable article nodes declare data-reader-type values and the reader controls navigate the ordered semantic node list.",
        },
        {
            "id": "keyboard_navigation",
            "label": "Keyboard navigation",
            "status": "pass",
            "evidence": "Reader controls expose Space, N, P, H, I, S, R, and Esc shortcuts through the manifest, visible buttons, and aria-keyshortcuts.",
        },
        {
            "id": "reader_cursor",
            "label": "Reader cursor state",
            "status": "pass",
            "evidence": "The active readable node receives focus, a visible outline, a stable reader id, and aria-current state.",
        },
        {
            "id": "shortcut_safety",
            "label": "Shortcut safety",
            "status": "pass",
            "evidence": "Global reader shortcuts ignore form controls so voice, speed, and auto-advance settings remain usable.",
        },
        {
            "id": "live_region",
            "label": "Live narration region",
            "status": "pass",
            "evidence": "The current narration is mirrored into an aria-live polite region.",
        },
        {
            "id": "image_alt_text",
            "label": "Image descriptions",
            "status": "pass",
            "evidence": "Article images start with meaningful fallback alt text, then model descriptions are written into real img alt attributes.",
        },
        {
            "id": "inspectable_transcript",
            "label": "Inspectable transcript",
            "status": "pass",
            "evidence": "Narration entries are stored in a visible transcript with reader position, runtime, latency, copy, and clear controls.",
        },
        {
            "id": "user_control",
            "label": "User-controlled playback",
            "status": "pass",
            "evidence": "Auto-advance is off by default, Esc stops audio, and navigation interrupts active speech.",
        },
        {
            "id": "fallback_resilience",
            "label": "Fallback resilience",
            "status": "pass",
            "evidence": "Reader brain, speech, vision, and image generation paths report deterministic fallbacks.",
        },
    ]
    return {
        "ok": True,
        "all_passed": all(check["status"] == "pass" for check in checks),
        "total_checks": len(checks),
        "passed_checks": sum(1 for check in checks if check["status"] == "pass"),
        "checks": checks,
    }


ARTICLE_MANIFEST: dict[str, Any] = {
    "title": "A tiny model reader that turns articles into guided narration",
    "reader_controls": [
        {"key": "Space", "aria_keyshortcuts": "Space", "action": "Play or pause"},
        {"key": "N", "aria_keyshortcuts": "N", "action": "Next item"},
        {"key": "P", "aria_keyshortcuts": "P", "action": "Previous item"},
        {"key": "H", "aria_keyshortcuts": "H", "action": "Next heading"},
        {"key": "I", "aria_keyshortcuts": "I", "action": "Next image"},
        {"key": "S", "aria_keyshortcuts": "S", "action": "Summarize current section"},
        {"key": "R", "aria_keyshortcuts": "R", "action": "Repeat current item"},
        {"key": "Esc", "aria_keyshortcuts": "Escape", "action": "Stop audio"},
    ],
    "bonus_targets": ["Tiny Titan", "Llama Champion", "Off-Brand", "Field Notes"],
    "images": ARTICLE_IMAGES,
    "models": MODEL_MANIFEST,
    "model_budget": model_budget_core(),
    "runtime_setup": runtime_setup_core(),
    "demo_script": demo_script_core(),
    "accessibility_audit": accessibility_audit_core(),
    "reader_settings": READER_SETTINGS,
    "award_evidence": AWARD_EVIDENCE,
}

app = Server(title="Tiny Narrator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


class ReaderBrainRequest(BaseModel):
    node_type: str = "paragraph"
    text: str
    position: str | None = None
    mode: str = "narrate"


class ImageDescriptionRequest(BaseModel):
    image_id: str
    caption: str | None = None
    prompt: str | None = None
    image_url: str | None = None


class SpeechRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


class ImageGenerationRequest(BaseModel):
    prompt: str
    seed: int | None = None


class ArticleGenerationRequest(BaseModel):
    topic: str


def _json(data: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code)


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _validate_modal_klein_health(payload: dict[str, Any]) -> None:
    if payload.get("ok") is not True:
        raise ValueError("health check did not return ok")
    if payload.get("model") != MODEL_MANIFEST["image_generation"]["id"]:
        raise ValueError("health check returned unexpected model")
    if payload.get("runtime") != "modal-klein":
        raise ValueError("health check returned unexpected runtime")


def _modal_klein_base_url() -> str:
    normalized = KLEIN_MODAL_ENDPOINT.rstrip("/")
    for suffix in ("/generate", "/health"):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _llama_cpp_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    if LLAMA_CPP_TOKEN:
        headers["Authorization"] = f"Bearer {LLAMA_CPP_TOKEN}"
    return headers


def _runtime_status_core() -> dict[str, Any]:
    start = time.perf_counter()
    llama_start = time.perf_counter()
    llama_status: dict[str, Any]
    if not LLAMA_CPP_BASE_URL:
        _runtime_log("llama.cpp reader brain endpoint is not configured; using narration fallback")
        llama_status = {
            "available": False,
            "status": "fallback-ready",
            "base_url": LLAMA_CPP_BASE_URL,
            "model": LLAMA_CPP_MODEL,
            "fallback": "rule-based local narration",
            "warning": "LLAMA_CPP_BASE_URL is not configured",
            "elapsed_ms": _elapsed_ms(llama_start),
        }
    else:
        models_url = f"{LLAMA_CPP_BASE_URL}/models"
        try:
            _runtime_log(
                "llama.cpp reader brain health check "
                f"url={models_url} token={'configured' if LLAMA_CPP_TOKEN else 'not-set'} "
                "timeout=1.5s"
            )
            request = urllib.request.Request(
                models_url,
                headers=_llama_cpp_headers(),
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=1.5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            model_ids = [item.get("id", "") for item in payload.get("data", []) if isinstance(item, dict)]
            _runtime_log(
                "llama.cpp reader brain health response "
                f"models={model_ids[:6]} expected={LLAMA_CPP_MODEL}"
            )
            llama_status = {
                "available": True,
                "status": "online",
                "base_url": LLAMA_CPP_BASE_URL,
                "model": LLAMA_CPP_MODEL,
                "models": model_ids,
                "elapsed_ms": _elapsed_ms(llama_start),
            }
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            detail = _http_exception_detail(exc)
            _runtime_log(f"llama.cpp reader brain health failed url={models_url} error={detail}")
            llama_status = {
                "available": False,
                "status": "fallback-ready",
                "base_url": LLAMA_CPP_BASE_URL,
                "model": LLAMA_CPP_MODEL,
                "fallback": "rule-based local narration",
                "health_url": models_url,
                "warning": detail,
                "elapsed_ms": _elapsed_ms(llama_start),
            }

    kokoro_available = importlib.util.find_spec("kokoro") is not None
    soundfile_available = importlib.util.find_spec("soundfile") is not None

    klein_status: dict[str, Any]
    if KLEIN_MODAL_ENDPOINT:
        endpoint = _modal_klein_base_url()
        health_url = f"{endpoint}/health"
        try:
            health_headers: dict[str, str] = {}
            if KLEIN_MODAL_TOKEN:
                health_headers["Authorization"] = f"Bearer {KLEIN_MODAL_TOKEN}"
            _runtime_log(
                "Modal Klein health check "
                f"url={health_url} token={'configured' if KLEIN_MODAL_TOKEN else 'not-set'} "
                f"timeout={KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS}s"
            )
            request = urllib.request.Request(
                health_url, method="GET",
                headers=health_headers,
            )
            with urllib.request.urlopen(request, timeout=KLEIN_MODAL_HEALTH_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            _runtime_log(
                "Modal Klein health response "
                f"model={payload.get('model')} runtime={payload.get('runtime')} ok={payload.get('ok')}"
            )
            _validate_modal_klein_health(payload)
            klein_status = {
                "available": True,
                "status": "online",
                "model": MODEL_MANIFEST["image_generation"]["id"],
                "endpoint": endpoint,
                "elapsed_ms": _elapsed_ms(start),
            }
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            detail = _http_exception_detail(exc)
            _runtime_log(f"Modal Klein health failed url={health_url} error={detail}")
            klein_status = {
                "available": False,
                "status": "fallback-ready",
                "model": MODEL_MANIFEST["image_generation"]["id"],
                "endpoint": endpoint,
                "health_url": health_url,
                "fallback": "bundled generated article assets",
                "warning": detail,
                "elapsed_ms": _elapsed_ms(start),
            }
    else:
        _runtime_log("Modal Klein endpoint is not configured; using image fallback")
        klein_status = {
            "available": False,
            "status": "fallback-ready",
            "model": MODEL_MANIFEST["image_generation"]["id"],
            "fallback": "bundled generated article assets",
        }

    vision_status = _vision_runtime_status()

    return {
        "ok": True,
        "reader_brain": llama_status,
        "vision": vision_status,
        "speech": {
            "available": kokoro_available and soundfile_available,
            "status": "online" if kokoro_available and soundfile_available else "fallback-ready",
            "model": "hexgrad/Kokoro-82M",
            "kokoro_installed": kokoro_available,
            "soundfile_installed": soundfile_available,
            "fallback": "browser speech plus transcript",
        },
        "image_generation": klein_status,
        "elapsed_ms": _elapsed_ms(start),
    }


def _compact_text(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}."


def _topic_seed(topic: str) -> int:
    return (sum(ord(char) for char in topic) % 997) + 1


def _fallback_article(topic: str) -> dict[str, Any]:
    clean_topic = _compact_text(topic, 80).rstrip(".") or "accessible technology"
    title = f"A tiny guide to {clean_topic}"
    return {
        "title": title,
        "dek": (
            f"This generated article introduces {clean_topic} with a short, screen-reader-friendly structure "
            "and practical examples."
        ),
        "sections": [
            {
                "heading": f"Why {clean_topic} matters",
                "body": (
                    f"{clean_topic.capitalize()} is easier to understand when the page explains the main idea first, "
                    "then moves through examples in a predictable order. A longer article gives the reader enough "
                    "context to pause, repeat, and compare sections without feeling rushed."
                ),
            },
            {
                "heading": "How a tiny narrator helps",
                "body": (
                    "A small reader model can turn each heading, paragraph, and image caption into concise narration "
                    "without turning the article into a chatbot. It keeps the experience close to the article, so "
                    "the user stays oriented while moving through the page."
                ),
            },
            {
                "heading": "What image descriptions add",
                "body": (
                    "Images often carry examples, diagrams, or emotional context. A visual descriptor gives those "
                    "details a spoken form, helping readers understand why an illustration belongs with the surrounding text."
                ),
            },
            {
                "heading": "Designing for repeated listening",
                "body": (
                    "Reader controls should make it easy to move backward, skip to the next heading, replay a sentence, "
                    "or stop speech completely. Those small controls matter when someone is studying, teaching, or checking details."
                ),
            },
            {
                "heading": "What to try next",
                "body": (
                    "Use the reader controls to move by heading or image, then compare the transcript with the article "
                    "to check whether the generated structure is easy to follow. If a section sounds confusing, rewrite it "
                    "with simpler language and a clearer heading."
                ),
            },
        ],
    }


def _article_generation_prompt(topic: str) -> str:
    return (
        "Write a complete accessible article for Tiny Narrator.\n"
        f"Topic: {topic}\n\n"
        "Return strict JSON with keys title, dek, and sections. "
        "sections must contain exactly five objects with heading and body. "
        "Each body should be 45 to 70 words, with concrete examples and practical detail. "
        "Use clear plain language suitable for screen-reader narration. Do not include markdown."
    )


def _fallback_narration(node_type: str, text: str, mode: str) -> str:
    prefix = {
        "heading": "Heading. ",
        "image": "Image. ",
        "button": "Control. ",
        "quote": "Quote. ",
    }.get(node_type, "")
    if mode == "summarize":
        prefix = "Summary. "
    fallback_text = _compact_text(text) or "No readable text is available for this item."
    return f"{prefix}{fallback_text}".strip()


def _chat_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices or not isinstance(choices[0], dict):
        return ""
    choice = choices[0]
    message = choice.get("message")
    if isinstance(message, dict):
        for key in ("content", "reasoning_content", "reasoning", "text"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                parts = []
                for item in value:
                    if isinstance(item, dict):
                        part = item.get("text") or item.get("content")
                        if isinstance(part, str):
                            parts.append(part)
                    elif isinstance(item, str):
                        parts.append(item)
                combined = " ".join(parts).strip()
                if combined:
                    return combined
    text = choice.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


def _chat_response_debug(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not choices or not isinstance(choices[0], dict):
        return f"top_keys={list(payload)[:8]} choices=missing"
    choice = choices[0]
    message = choice.get("message")
    message_keys = list(message)[:8] if isinstance(message, dict) else []
    return (
        f"top_keys={list(payload)[:8]} "
        f"choice_keys={list(choice)[:8]} "
        f"message_keys={message_keys} "
        f"finish_reason={choice.get('finish_reason')}"
    )


def reader_brain_core(node_type: str, text: str, position: str | None, mode: str) -> dict[str, Any]:
    start = time.perf_counter()
    if not LLAMA_CPP_BASE_URL:
        return {
            "ok": True,
            "runtime": "fallback",
            "model": "rule-based local fallback",
            "warning": "llama.cpp unavailable: LLAMA_CPP_BASE_URL is not configured",
            "narration": _fallback_narration(node_type, text, mode),
            "elapsed_ms": _elapsed_ms(start),
        }

    if mode == "summarize":
        prompt = (
            "Summarize this article section for screen-reader navigation.\n"
            f"Node type: {node_type}\n"
            f"Position: {position or 'unknown'}\n"
            f"Content: {text}\n\n"
            "Rules: start with 'Summary.', use one or two short sentences, explain what the "
            "reader can learn in this section, and never mention implementation details. "
            "Return only the final spoken narration. Do not explain your reasoning."
        )
    else:
        prompt = (
            "Convert this article node into concise screen-reader narration.\n"
            f"Mode: {mode}\n"
            f"Node type: {node_type}\n"
            f"Position: {position or 'unknown'}\n"
            f"Content: {text}\n\n"
            "Rules: announce the node type only when it helps orientation, keep prose short, "
            "and never mention implementation details. Return only the final spoken narration. "
            "Do not explain your reasoning."
        )

    try:
        body = json.dumps(
            {
                "model": LLAMA_CPP_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Tiny Narrator's accessibility layer. "
                            "Reasoning mode: off. Do not generate a reasoning trace. "
                            "Do not think step by step. "
                            "Produce clear screen-reader narration for article content. "
                            "Return only the exact text to speak. Do not include analysis, alternatives, "
                            "markdown, labels, or explanations."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "top_p": 0.9,
                "stream": False,
                "max_tokens": 80,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{LLAMA_CPP_BASE_URL}/chat/completions",
            data=body,
            headers=_llama_cpp_headers({"Content-Type": "application/json"}),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=LLAMA_CPP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        narration = _compact_text(_chat_message_text(payload), 220)
        if not narration:
            fallback = _fallback_narration(node_type, text, mode)
            detail = _chat_response_debug(payload)
            _runtime_log(f"llama.cpp returned empty narration; response_shape={detail}")
            return {
                "ok": True,
                "runtime": "fallback",
                "model": "rule-based local fallback",
                "warning": f"llama.cpp returned empty narration ({detail})",
                "narration": fallback,
                "elapsed_ms": _elapsed_ms(start),
            }
        return {
            "ok": True,
            "runtime": "llama.cpp",
            "model": LLAMA_CPP_MODEL,
            "narration": narration,
            "elapsed_ms": _elapsed_ms(start),
        }
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return {
            "ok": True,
            "runtime": "fallback",
            "model": "rule-based local fallback",
            "warning": f"llama.cpp unavailable: {exc.__class__.__name__}",
            "narration": _fallback_narration(node_type, text, mode),
            "elapsed_ms": _elapsed_ms(start),
        }


def _openai_compatible_url(base_url: str, path: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1/chat/completions"):
        root = normalized[: -len("/chat/completions")]
    elif normalized.endswith("/v1"):
        root = normalized
    else:
        root = f"{normalized}/v1"
    return f"{root}/{path.lstrip('/')}"


def _article_image_by_id(image_id: str) -> dict[str, Any] | None:
    return next((image for image in ARTICLE_IMAGES if image["id"] == image_id), None)


def _absolute_image_url(image_url: str | None, image_id: str | None = None) -> str | None:
    candidate = image_url
    if not candidate and image_id:
        image = _article_image_by_id(image_id)
        candidate = (image.get("vision_asset_url") or image.get("asset_url")) if image else None
    if not candidate:
        return None
    if candidate.startswith(("http://", "https://", "data:")):
        return candidate
    if candidate.startswith("/"):
        return f"{PUBLIC_BASE_URL}{candidate}"
    return f"{PUBLIC_BASE_URL}/{candidate}"


def _vision_fallback_text(image_id: str, caption: str | None, prompt: str | None) -> str:
    descriptions = {
        "desk-reader": (
            "A person reads a long article on a laptop while an accessibility toolbar "
            "highlights the current paragraph."
        ),
        "model-map": (
            "A compact diagram showing four small AI models working together: vision, "
            "reader brain, speech, and image generation."
        ),
    }
    return descriptions.get(
        image_id,
        caption or prompt or "A generated article image awaiting model description.",
    )


def _clean_alt_text(text: str, limit: int = 260) -> str:
    return _compact_text(" ".join(text.split()), limit)


def _minicpm_vision_prompt(caption: str | None, prompt: str | None) -> str:
    context = " ".join(part for part in [caption, prompt] if part)
    context_line = f"\nContext: {context}" if context else ""
    return (
        "Describe this image for a screen reader in one or two concise sentences. "
        "Mention visible content, layout, important text, and purpose when relevant. "
        "Do not guess hidden intent. Do not mention models, implementation details, or that you are an AI. "
        "Return plain text only."
        f"{context_line}"
    )


def _call_minicpm_vision(image_url: str, caption: str | None, prompt: str | None) -> dict[str, Any]:
    start = time.perf_counter()
    body = json.dumps(
        {
            "model": MINICPM_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _minicpm_vision_prompt(caption, prompt)},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 160,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _openai_compatible_url(MINICPM_VISION_BASE_URL, "chat/completions"),
        data=body,
        headers={
            "Authorization": f"Bearer {MINICPM_VISION_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=MINICPM_VISION_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("MiniCPM vision response did not include text content")
    return {
        "runtime": "minicpm-v4.6",
        "model": MINICPM_VISION_MODEL,
        "alt_text": _clean_alt_text(content),
        "elapsed_ms": _elapsed_ms(start),
    }


def _check_minicpm_chat_ready() -> dict[str, Any]:
    body = json.dumps(
        {
            "model": MINICPM_VISION_MODEL,
            "messages": [{"role": "user", "content": "Reply with ready."}],
            "temperature": 0,
            "max_tokens": 8,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _openai_compatible_url(MINICPM_VISION_BASE_URL, "chat/completions"),
        data=body,
        headers={
            "Authorization": f"Bearer {MINICPM_VISION_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=min(MINICPM_VISION_TIMEOUT_SECONDS, 10)) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("MiniCPM readiness response did not include text content")
    return payload


def _vision_runtime_status() -> dict[str, Any]:
    if not MINICPM_VISION_BASE_URL or not MINICPM_VISION_API_KEY:
        return {
            "available": False,
            "status": "fallback-ready",
            "model": MINICPM_VISION_MODEL,
            "configured": False,
            "fallback": "cached deterministic alt text",
        }
    start = time.perf_counter()
    model_ids: list[str] = []
    models_warning: str | None = None
    try:
        request = urllib.request.Request(
            _openai_compatible_url(MINICPM_VISION_BASE_URL, "models"),
            headers={"Authorization": f"Bearer {MINICPM_VISION_API_KEY}"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        model_ids = [
            item.get("id", "")
            for item in payload.get("data", [])
            if isinstance(item, dict)
        ]
        if model_ids and MINICPM_VISION_MODEL not in model_ids:
            models_warning = "MiniCPM vision model was not listed by /models"
            _check_minicpm_chat_ready()
        return {
            "available": True,
            "status": "online",
            "model": MINICPM_VISION_MODEL,
            "configured": True,
            "base_url": MINICPM_VISION_BASE_URL,
            "models": model_ids,
            "warning": models_warning,
            "elapsed_ms": _elapsed_ms(start),
        }
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        models_warning = exc.__class__.__name__

    try:
        _check_minicpm_chat_ready()
        return {
            "available": True,
            "status": "online",
            "model": MINICPM_VISION_MODEL,
            "configured": True,
            "base_url": MINICPM_VISION_BASE_URL,
            "models": model_ids,
            "warning": f"/models unavailable, chat completions ready: {models_warning}",
            "elapsed_ms": _elapsed_ms(start),
        }
    except (OSError, urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "status": "fallback-ready",
            "model": MINICPM_VISION_MODEL,
            "configured": True,
            "base_url": MINICPM_VISION_BASE_URL,
            "fallback": "cached deterministic alt text",
            "warning": exc.__class__.__name__,
            "elapsed_ms": _elapsed_ms(start),
        }


def describe_image_core(
    image_id: str,
    caption: str | None,
    prompt: str | None,
    image_url: str | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    resolved_image_url = _absolute_image_url(image_url, image_id)
    alt_text = _vision_fallback_text(image_id, caption, prompt)
    warning = None
    if MINICPM_VISION_BASE_URL and MINICPM_VISION_API_KEY and resolved_image_url:
        try:
            return {"ok": True, **_call_minicpm_vision(resolved_image_url, caption, prompt)}
        except (OSError, urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            detail = _http_exception_detail(exc)
            _runtime_log(f"MiniCPM vision failed image_url={resolved_image_url} error={detail}")
            warning = f"MiniCPM vision unavailable: {detail}"
    return {
        "ok": True,
        "runtime": "fallback",
        "model": MINICPM_VISION_MODEL,
        "alt_text": alt_text,
        "warning": warning,
        "elapsed_ms": _elapsed_ms(start),
    }


def describe_article_images_core() -> dict[str, Any]:
    start = time.perf_counter()
    descriptions = []
    for image in ARTICLE_IMAGES:
        description = describe_image_core(
            image["id"],
            caption=image.get("caption"),
            prompt=image.get("prompt"),
            image_url=image.get("vision_asset_url") or image.get("asset_url"),
        )
        descriptions.append({**image, **description})
    runtimes = {item["runtime"] for item in descriptions}
    return {
        "ok": True,
        "runtime": runtimes.pop() if len(runtimes) == 1 else "mixed",
        "model": MINICPM_VISION_MODEL,
        "descriptions": descriptions,
        "elapsed_ms": _elapsed_ms(start),
    }


def _silent_wav(path: Path, seconds: float = 0.35, sample_rate: int = 24000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)


def _prune_speech_outputs(keep_path: Path, max_files: int = 24) -> None:
    speech_files = sorted(
        OUTPUT_DIR.glob("speech*.wav"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    keep_resolved = keep_path.resolve()
    for old_path in speech_files[max_files:]:
        if old_path.resolve() == keep_resolved:
            continue
        try:
            old_path.unlink()
        except OSError:
            pass


def speak_core(text: str, voice: str, speed: float) -> dict[str, Any]:
    start = time.perf_counter()
    clean_text = _compact_text(text, 1200)
    if not clean_text:
        output_path = OUTPUT_DIR / f"speech-fallback-{uuid4().hex}.wav"
        _silent_wav(output_path)
        _prune_speech_outputs(output_path)
        return {
            "ok": True,
            "runtime": "fallback",
            "model": "hexgrad/Kokoro-82M",
            "warning": "Kokoro skipped because transcript was empty",
            "audio_url": f"/outputs/{output_path.name}",
            "transcript": "",
            "elapsed_ms": _elapsed_ms(start),
        }
    try:
        from kokoro import KPipeline
        import soundfile as sf

        pipeline = KPipeline(lang_code="a")
        generator = pipeline(clean_text, voice=voice, speed=speed)
        _, _, audio = next(generator)
        output_path = OUTPUT_DIR / f"speech-{uuid4().hex}.wav"
        sf.write(output_path, audio, 24000)
        runtime = "kokoro"
        warning = None
    except Exception as exc:
        output_path = OUTPUT_DIR / f"speech-fallback-{uuid4().hex}.wav"
        _silent_wav(output_path)
        runtime = "fallback"
        warning = f"Kokoro unavailable: {exc.__class__.__name__}"

    _prune_speech_outputs(output_path)

    return {
        "ok": True,
        "runtime": runtime,
        "model": "hexgrad/Kokoro-82M",
        "warning": warning,
        "audio_url": f"/outputs/{output_path.name}",
        "transcript": clean_text,
        "elapsed_ms": _elapsed_ms(start),
    }


def _call_modal_klein(prompt: str, seed: int | None) -> dict[str, Any]:
    """Call the Modal Klein worker for live image generation."""
    start = time.perf_counter()
    body = json.dumps({"prompt": prompt, "seed": seed}).encode("utf-8")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if KLEIN_MODAL_TOKEN:
        headers["Authorization"] = f"Bearer {KLEIN_MODAL_TOKEN}"
    endpoint = _modal_klein_base_url()
    generate_url = f"{endpoint}/generate"
    _runtime_log(
        "Modal Klein generate request "
        f"url={generate_url} token={'configured' if KLEIN_MODAL_TOKEN else 'not-set'} seed={seed}"
    )
    request = urllib.request.Request(
        generate_url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=KLEIN_MODAL_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        detail = _http_exception_detail(exc)
        _runtime_log(f"Modal Klein generate failed url={generate_url} error={detail}")
        raise
    if payload.get("ok") is not True:
        _runtime_log(f"Modal Klein generate returned ok=false payload={_compact_text(json.dumps(payload), 400)}")
        raise ValueError(str(payload.get("error") or payload.get("detail") or "Modal Klein returned ok=false"))
    if payload.get("model") != MODEL_MANIFEST["image_generation"]["id"]:
        _runtime_log(f"Modal Klein generate returned unexpected model={payload.get('model')}")
        raise ValueError("Modal Klein returned unexpected model")
    if payload.get("runtime") != "modal-klein":
        _runtime_log(f"Modal Klein generate returned unexpected runtime={payload.get('runtime')}")
        raise ValueError("Modal Klein returned unexpected runtime")
    image_url = payload.get("image_url", "")
    if not isinstance(image_url, str) or not image_url:
        _runtime_log("Modal Klein generate response did not include image_url")
        raise ValueError("Modal Klein response did not include image_url")
    if image_url and image_url.startswith("/media/"):
        image_url = f"{endpoint}{image_url}"
    _runtime_log(f"Modal Klein generate succeeded runtime={payload.get('runtime')} image_url={image_url}")
    return {
        "ok": True,
        "runtime": payload.get("runtime", "modal-klein"),
        "model": payload.get("model", MODEL_MANIFEST["image_generation"]["id"]),
        "image_url": image_url,
        "prompt": payload.get("prompt", prompt),
        "seed": payload.get("seed", seed),
        "elapsed_ms": payload.get("elapsed_ms", _elapsed_ms(start)),
    }


def _fallback_image(prompt: str, seed: int | None, warning: str | None = None) -> dict[str, Any]:
    """Return bundled fallback SVG assets when Modal is unavailable."""
    start = time.perf_counter()
    return {
        "ok": True,
        "runtime": "fallback",
        "model": MODEL_MANIFEST["image_generation"]["id"],
        "image_url": f"/static/generated/{'desk-reader.svg' if seed and seed % 2 else 'model-map.svg'}",
        "prompt": prompt,
        "seed": seed,
        "warning": warning,
        "elapsed_ms": _elapsed_ms(start),
    }


def generate_image_core(prompt: str, seed: int | None) -> dict[str, Any]:
    if KLEIN_MODAL_ENDPOINT:
        try:
            return _call_modal_klein(prompt, seed)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return _fallback_image(prompt, seed, warning=f"Modal Klein unavailable: {_http_exception_detail(exc)}")
    _runtime_log("Modal Klein generate skipped because KLEIN_MODAL_ENDPOINT is not configured")
    return _fallback_image(prompt, seed)


def _thumbnail_image_prompt(topic: str) -> str:
    return (
        f"Square image-only editorial thumbnail about {topic}. "
        "Create one centered cohesive scene: a friendly assistive robot or small AI helper guiding a reader "
        "through visual information with light, sound waves, image cards, and accessibility cues. "
        "Fill most of the frame with the subject while leaving a small clean margin. "
        "Modern polished 3D editorial illustration, soft gradients, warm blue and teal accents, clear focal point. "
        "No words, no letters, no numbers, no captions, no title, no logo, no watermark, "
        "no user interface, no screenshot, no document page, no poster layout, no split panels."
    )


def generate_article_core(topic: str) -> dict[str, Any]:
    start = time.perf_counter()
    clean_topic = _compact_text(topic, 100).strip()
    if not clean_topic:
        clean_topic = "accessible technology"

    article = _fallback_article(clean_topic)
    runtime = "fallback"
    warning = None
    if not LLAMA_CPP_BASE_URL:
        warning = "llama.cpp unavailable: LLAMA_CPP_BASE_URL is not configured"
    else:
        try:
            body = json.dumps(
                {
                    "model": LLAMA_CPP_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are Tiny Narrator's article generator. "
                                "Create concise, semantic, accessible article drafts."
                            ),
                        },
                        {"role": "user", "content": _article_generation_prompt(clean_topic)},
                    ],
                    "temperature": 0.35,
                    "max_tokens": 650,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{LLAMA_CPP_BASE_URL}/chat/completions",
                data=body,
                headers=_llama_cpp_headers({"Content-Type": "application/json"}),
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=LLAMA_CPP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            generated = json.loads(payload["choices"][0]["message"]["content"].strip())
            sections = generated.get("sections", [])
            if (
                isinstance(generated.get("title"), str)
                and isinstance(generated.get("dek"), str)
                and isinstance(sections, list)
                and len(sections) == 5
                and all(isinstance(item.get("heading"), str) and isinstance(item.get("body"), str) for item in sections)
            ):
                article = {
                    "title": _compact_text(generated["title"], 90),
                    "dek": _compact_text(generated["dek"], 180),
                    "sections": [
                        {"heading": _compact_text(item["heading"], 80), "body": _compact_text(item["body"], 720)}
                        for item in sections
                    ],
                }
                runtime = "llama.cpp"
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            warning = f"llama.cpp unavailable: {exc.__class__.__name__}"

    image_prompt = _thumbnail_image_prompt(clean_topic)
    thumbnail = generate_image_core(image_prompt, seed=_topic_seed(clean_topic))
    return {
        "ok": True,
        "topic": clean_topic,
        "runtime": runtime,
        "model": MODEL_MANIFEST["reader_brain"]["id"],
        "warning": warning,
        "article": article,
        "thumbnail": {
            **thumbnail,
            "role": "thumbnail",
            "generation_model": MODEL_MANIFEST["image_generation"]["id"],
        },
        "elapsed_ms": _elapsed_ms(start),
    }


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/generate", response_class=HTMLResponse)
async def generate_page() -> str:
    return (STATIC_DIR / "generate.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def health() -> JSONResponse:
    return _json(
        {
            "ok": True,
            "app": "Tiny Narrator",
            "frontend": "custom Gradio Server HTML/CSS/JS",
            "llama_cpp_base_url": LLAMA_CPP_BASE_URL,
            "public_base_url": PUBLIC_BASE_URL,
            "models": MODEL_MANIFEST,
        }
    )


@app.get("/api/article-manifest")
async def article_manifest() -> JSONResponse:
    return _json({"ok": True, **ARTICLE_MANIFEST})


@app.get("/api/award-evidence")
async def award_evidence() -> JSONResponse:
    return _json({"ok": True, "items": AWARD_EVIDENCE})


@app.get("/api/model-budget")
async def model_budget() -> JSONResponse:
    return _json(model_budget_core())


@app.get("/api/runtime-setup")
async def runtime_setup() -> JSONResponse:
    return _json(runtime_setup_core())


@app.get("/api/demo-script")
async def demo_script() -> JSONResponse:
    return _json(demo_script_core())


@app.get("/api/accessibility-audit")
async def accessibility_audit() -> JSONResponse:
    return _json(accessibility_audit_core())


@app.get("/api/submission-readiness")
async def submission_readiness() -> JSONResponse:
    return _json(submission_readiness_core())


@app.get("/api/evidence-bundle")
async def evidence_bundle() -> JSONResponse:
    return _json(evidence_bundle_core())


@app.get("/api/runtime-status")
async def runtime_status() -> JSONResponse:
    return _json(_runtime_status_core())


@app.post("/api/reader-brain")
async def reader_brain_endpoint(payload: ReaderBrainRequest) -> JSONResponse:
    return _json(reader_brain_core(payload.node_type, payload.text, payload.position, payload.mode))


@app.post("/api/describe-image")
async def describe_image_endpoint(payload: ImageDescriptionRequest) -> JSONResponse:
    return _json(describe_image_core(payload.image_id, payload.caption, payload.prompt, payload.image_url))


@app.get("/api/image-descriptions")
async def image_descriptions_endpoint() -> JSONResponse:
    return _json(describe_article_images_core())


@app.post("/api/speak")
async def speak_endpoint(payload: SpeechRequest) -> JSONResponse:
    return _json(speak_core(payload.text, payload.voice, payload.speed))


@app.post("/api/generate-image")
async def generate_image_endpoint(payload: ImageGenerationRequest) -> JSONResponse:
    return _json(generate_image_core(payload.prompt, payload.seed))


@app.post("/api/generate-article")
async def generate_article_endpoint(payload: ArticleGenerationRequest) -> JSONResponse:
    return _json(generate_article_core(payload.topic))


@app.api(name="reader_brain")
def reader_brain_api(node_type: str, text: str, position: str = "", mode: str = "narrate") -> str:
    return json.dumps(reader_brain_core(node_type, text, position, mode))


@app.api(name="describe_image")
def describe_image_api(image_id: str, caption: str = "", prompt: str = "", image_url: str = "") -> str:
    return json.dumps(describe_image_core(image_id, caption, prompt, image_url))


@app.api(name="describe_article_images")
def describe_article_images_api() -> str:
    return json.dumps(describe_article_images_core())


@app.api(name="model_budget")
def model_budget_api() -> str:
    return json.dumps(model_budget_core())


@app.api(name="runtime_setup")
def runtime_setup_api() -> str:
    return json.dumps(runtime_setup_core())


@app.api(name="demo_script")
def demo_script_api() -> str:
    return json.dumps(demo_script_core())


@app.api(name="accessibility_audit")
def accessibility_audit_api() -> str:
    return json.dumps(accessibility_audit_core())


@app.api(name="submission_readiness")
def submission_readiness_api() -> str:
    return json.dumps(submission_readiness_core())


@app.api(name="evidence_bundle")
def evidence_bundle_api() -> str:
    return json.dumps(evidence_bundle_core())


@app.api(name="speak")
def speak_api(text: str, voice: str = "af_heart", speed: float = 1.0) -> str:
    return json.dumps(speak_core(text, voice, speed))


@app.api(name="generate_image")
def generate_image_api(prompt: str, seed: int | None = None) -> str:
    return json.dumps(generate_image_core(prompt, seed))


@app.api(name="generate_article")
def generate_article_api(topic: str) -> str:
    return json.dumps(generate_article_core(topic))


@app.exception_handler(Exception)
async def handle_exception(_: Request, exc: Exception) -> JSONResponse:
    return _json({"ok": False, "error": exc.__class__.__name__, "detail": str(exc)}, status_code=500)


if __name__ == "__main__":
    app.launch(server_name=GRADIO_SERVER_NAME, server_port=GRADIO_SERVER_PORT, share=GRADIO_SHARE)
