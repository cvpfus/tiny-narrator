from __future__ import annotations

import importlib.util
import json
import os
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from gradio import Server
from pydantic import BaseModel


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

LLAMA_CPP_BASE_URL = os.getenv("LLAMA_CPP_BASE_URL", "http://localhost:8080/v1")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "narrator-brain")
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", "7860")))
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
        "id": "openbmb/MiniCPM-V-2",
        "params": "3B",
        "params_billion": 3.0,
        "runtime": "Python integration planned",
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
        "runtime": "Python integration planned",
        "role": "Creates article illustrations.",
    },
}

ARTICLE_IMAGES: list[dict[str, str]] = [
    {
        "id": "desk-reader",
        "asset_url": "/static/generated/desk-reader.svg",
        "caption": "The article view doubles as the demo surface, so every feature has a real reading task.",
        "prompt": "Accessibility article reader with highlighted paragraph and narration controls.",
    },
    {
        "id": "model-map",
        "asset_url": "/static/generated/model-map.svg",
        "caption": "Each model stays at or below four billion parameters for Tiny Titan eligibility.",
        "prompt": "Diagram of four small AI models working together in an accessibility reader.",
    },
    {
        "id": "field-notes",
        "asset_url": "/static/generated/field-notes.svg",
        "caption": "Field notes document the choices behind the screen-reader behavior.",
        "prompt": "Notebook page with model sizes, keyboard controls, and accessibility checks.",
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
                    "--alias narrator-brain --port 8080 --host 0.0.0.0"
                ),
                "env": {"LLAMA_CPP_BASE_URL": LLAMA_CPP_BASE_URL, "LLAMA_CPP_MODEL": LLAMA_CPP_MODEL},
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
                "runtime": "Python integration planned",
                "command": "planned MiniCPM-V adapter",
                "env": {},
                "fallback": "cached deterministic alt text",
            },
            {
                "role": "image_generation",
                "label": "Article images",
                "model": MODEL_MANIFEST["image_generation"]["id"],
                "runtime": "Python integration planned",
                "command": "planned FLUX.2 klein adapter",
                "env": {},
                "fallback": "bundled generated article assets",
            },
        ],
    }


def demo_script_core() -> dict[str, Any]:
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
                "evidence": "Tiny Titan, Llama Champion, Off-Brand, and Field Notes evidence is visible.",
            },
        ],
        "api_checks": [
            {"method": "GET", "path": "/api/health", "expect": "custom Gradio Server app and model manifest"},
            {"method": "GET", "path": "/api/model-budget", "expect": "all_models_within_limit is true"},
            {"method": "GET", "path": "/api/runtime-setup", "expect": "llama.cpp, Kokoro, vision, and image paths"},
            {"method": "GET", "path": "/api/runtime-status", "expect": "online or fallback-ready runtime labels"},
            {"method": "GET", "path": "/api/image-descriptions", "expect": "three article image descriptions"},
            {"method": "POST", "path": "/api/reader-brain", "expect": "concise narration or fallback narration"},
            {"method": "POST", "path": "/api/speak", "expect": "Kokoro audio or audible browser fallback path"},
        ],
    }


ARTICLE_MANIFEST: dict[str, Any] = {
    "title": "A tiny model reader that turns articles into guided narration",
    "reader_controls": [
        {"key": "Space", "action": "Play or pause"},
        {"key": "N", "action": "Next item"},
        {"key": "P", "action": "Previous item"},
        {"key": "H", "action": "Next heading"},
        {"key": "I", "action": "Next image"},
        {"key": "S", "action": "Summarize current section"},
        {"key": "R", "action": "Repeat current item"},
        {"key": "Esc", "action": "Stop audio"},
    ],
    "bonus_targets": ["Tiny Titan", "Llama Champion", "Off-Brand", "Field Notes"],
    "images": ARTICLE_IMAGES,
    "models": MODEL_MANIFEST,
    "model_budget": model_budget_core(),
    "runtime_setup": runtime_setup_core(),
    "demo_script": demo_script_core(),
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


class SpeechRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


class ImageGenerationRequest(BaseModel):
    prompt: str
    seed: int | None = None


def _json(data: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status_code)


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _runtime_status_core() -> dict[str, Any]:
    start = time.perf_counter()
    llama_start = time.perf_counter()
    llama_status: dict[str, Any]
    try:
        request = urllib.request.Request(f"{LLAMA_CPP_BASE_URL}/models", method="GET")
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        model_ids = [item.get("id", "") for item in payload.get("data", []) if isinstance(item, dict)]
        llama_status = {
            "available": True,
            "status": "online",
            "base_url": LLAMA_CPP_BASE_URL,
            "model": LLAMA_CPP_MODEL,
            "models": model_ids,
            "elapsed_ms": _elapsed_ms(llama_start),
        }
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        llama_status = {
            "available": False,
            "status": "fallback-ready",
            "base_url": LLAMA_CPP_BASE_URL,
            "model": LLAMA_CPP_MODEL,
            "fallback": "rule-based local narration",
            "warning": exc.__class__.__name__,
            "elapsed_ms": _elapsed_ms(llama_start),
        }

    kokoro_available = importlib.util.find_spec("kokoro") is not None
    soundfile_available = importlib.util.find_spec("soundfile") is not None

    return {
        "ok": True,
        "reader_brain": llama_status,
        "vision": {
            "available": False,
            "status": "fallback-ready",
            "model": "OpenBMB MiniCPM-V-2",
            "fallback": "cached deterministic alt text",
        },
        "speech": {
            "available": kokoro_available and soundfile_available,
            "status": "online" if kokoro_available and soundfile_available else "fallback-ready",
            "model": "hexgrad/Kokoro-82M",
            "kokoro_installed": kokoro_available,
            "soundfile_installed": soundfile_available,
            "fallback": "browser speech plus transcript",
        },
        "image_generation": {
            "available": False,
            "status": "placeholder-ready",
            "model": "black-forest-labs/FLUX.2-klein-4B",
            "fallback": "bundled generated article assets",
        },
        "elapsed_ms": _elapsed_ms(start),
    }


def _compact_text(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}."


def reader_brain_core(node_type: str, text: str, position: str | None, mode: str) -> dict[str, Any]:
    start = time.perf_counter()
    if mode == "summarize":
        prompt = (
            "Summarize this article section for screen-reader navigation.\n"
            f"Node type: {node_type}\n"
            f"Position: {position or 'unknown'}\n"
            f"Content: {text}\n\n"
            "Rules: start with 'Summary.', use one or two short sentences, explain what the "
            "reader can learn in this section, and never mention implementation details."
        )
    else:
        prompt = (
            "Convert this article node into concise screen-reader narration.\n"
            f"Mode: {mode}\n"
            f"Node type: {node_type}\n"
            f"Position: {position or 'unknown'}\n"
            f"Content: {text}\n\n"
            "Rules: announce the node type only when it helps orientation, keep prose short, "
            "and never mention implementation details."
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
                            "Produce clear screen-reader narration for article content."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 180,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{LLAMA_CPP_BASE_URL}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
        narration = payload["choices"][0]["message"]["content"].strip()
        return {
            "ok": True,
            "runtime": "llama.cpp",
            "model": LLAMA_CPP_MODEL,
            "narration": narration,
            "elapsed_ms": _elapsed_ms(start),
        }
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        prefix = {
            "heading": "Heading. ",
            "image": "Image. ",
            "button": "Control. ",
            "quote": "Quote. ",
        }.get(node_type, "")
        if mode == "summarize":
            prefix = "Summary. "
        return {
            "ok": True,
            "runtime": "fallback",
            "model": "rule-based local fallback",
            "warning": f"llama.cpp unavailable: {exc.__class__.__name__}",
            "narration": f"{prefix}{_compact_text(text)}".strip(),
            "elapsed_ms": _elapsed_ms(start),
        }


def describe_image_core(image_id: str, caption: str | None, prompt: str | None) -> dict[str, Any]:
    start = time.perf_counter()
    # The first committed slice keeps the API stable while the MiniCPM-V runtime lands next.
    # The frontend passes deterministic image ids so cached descriptions can replace this later.
    descriptions = {
        "desk-reader": (
            "A person reads a long article on a laptop while an accessibility toolbar "
            "highlights the current paragraph."
        ),
        "model-map": (
            "A compact diagram showing four small AI models working together: vision, "
            "reader brain, speech, and image generation."
        ),
        "field-notes": (
            "A notebook page with short build notes, model sizes, and accessibility checks."
        ),
    }
    alt_text = descriptions.get(
        image_id,
        caption or prompt or "A generated article image awaiting model description.",
    )
    return {
        "ok": True,
        "runtime": "MiniCPM-V placeholder",
        "model": "OpenBMB MiniCPM-V-2",
        "alt_text": alt_text,
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
        )
        descriptions.append({**image, **description})
    return {
        "ok": True,
        "runtime": "MiniCPM-V placeholder",
        "model": "OpenBMB MiniCPM-V-2",
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


def speak_core(text: str, voice: str, speed: float) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from kokoro import KPipeline
        import soundfile as sf

        pipeline = KPipeline(lang_code="a")
        generator = pipeline(text, voice=voice, speed=speed)
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

    return {
        "ok": True,
        "runtime": runtime,
        "model": "hexgrad/Kokoro-82M",
        "warning": warning,
        "audio_url": f"/outputs/{output_path.name}",
        "transcript": text,
        "elapsed_ms": _elapsed_ms(start),
    }


def generate_image_core(prompt: str, seed: int | None) -> dict[str, Any]:
    start = time.perf_counter()
    return {
        "ok": True,
        "runtime": "placeholder",
        "model": "black-forest-labs/FLUX.2-klein-4B",
        "image_url": f"/static/generated/{'field-notes.svg' if seed == 3 else 'model-map.svg'}",
        "prompt": prompt,
        "seed": seed,
        "elapsed_ms": _elapsed_ms(start),
    }


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def health() -> JSONResponse:
    return _json(
        {
            "ok": True,
            "app": "Tiny Narrator",
            "frontend": "custom Gradio Server HTML/CSS/JS",
            "llama_cpp_base_url": LLAMA_CPP_BASE_URL,
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


@app.get("/api/runtime-status")
async def runtime_status() -> JSONResponse:
    return _json(_runtime_status_core())


@app.post("/api/reader-brain")
async def reader_brain_endpoint(payload: ReaderBrainRequest) -> JSONResponse:
    return _json(reader_brain_core(payload.node_type, payload.text, payload.position, payload.mode))


@app.post("/api/describe-image")
async def describe_image_endpoint(payload: ImageDescriptionRequest) -> JSONResponse:
    return _json(describe_image_core(payload.image_id, payload.caption, payload.prompt))


@app.get("/api/image-descriptions")
async def image_descriptions_endpoint() -> JSONResponse:
    return _json(describe_article_images_core())


@app.post("/api/speak")
async def speak_endpoint(payload: SpeechRequest) -> JSONResponse:
    return _json(speak_core(payload.text, payload.voice, payload.speed))


@app.post("/api/generate-image")
async def generate_image_endpoint(payload: ImageGenerationRequest) -> JSONResponse:
    return _json(generate_image_core(payload.prompt, payload.seed))


@app.api(name="reader_brain")
def reader_brain_api(node_type: str, text: str, position: str = "", mode: str = "narrate") -> str:
    return json.dumps(reader_brain_core(node_type, text, position, mode))


@app.api(name="describe_image")
def describe_image_api(image_id: str, caption: str = "", prompt: str = "") -> str:
    return json.dumps(describe_image_core(image_id, caption, prompt))


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


@app.api(name="speak")
def speak_api(text: str, voice: str = "af_heart", speed: float = 1.0) -> str:
    return json.dumps(speak_core(text, voice, speed))


@app.api(name="generate_image")
def generate_image_api(prompt: str, seed: int | None = None) -> str:
    return json.dumps(generate_image_core(prompt, seed))


@app.exception_handler(Exception)
async def handle_exception(_: Request, exc: Exception) -> JSONResponse:
    return _json({"ok": False, "error": exc.__class__.__name__, "detail": str(exc)}, status_code=500)


if __name__ == "__main__":
    app.launch(server_name=GRADIO_SERVER_NAME, server_port=GRADIO_SERVER_PORT)
