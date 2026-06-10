from __future__ import annotations

import json
import os
import wave
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from gradio import Server
from pydantic import BaseModel


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

LLAMA_CPP_BASE_URL = os.getenv("LLAMA_CPP_BASE_URL", "http://localhost:8080/v1")
LLAMA_CPP_MODEL = os.getenv("LLAMA_CPP_MODEL", "narrator-brain")

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


def reader_brain_core(node_type: str, text: str, position: str | None, mode: str) -> dict[str, Any]:
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
        response = requests.post(
            f"{LLAMA_CPP_BASE_URL}/chat/completions",
            json={
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
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        narration = payload["choices"][0]["message"]["content"].strip()
        return {
            "ok": True,
            "runtime": "llama.cpp",
            "model": LLAMA_CPP_MODEL,
            "narration": narration,
        }
    except Exception as exc:
        prefix = {
            "heading": "Heading. ",
            "image": "Image. ",
            "button": "Control. ",
            "quote": "Quote. ",
        }.get(node_type, "")
        return {
            "ok": True,
            "runtime": "fallback",
            "model": "rule-based local fallback",
            "warning": f"llama.cpp unavailable: {exc.__class__.__name__}",
            "narration": f"{prefix}{text}".strip(),
        }


def describe_image_core(image_id: str, caption: str | None, prompt: str | None) -> dict[str, Any]:
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
    }


def _silent_wav(path: Path, seconds: float = 0.35, sample_rate: int = 24000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)


def speak_core(text: str, voice: str, speed: float) -> dict[str, Any]:
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
    }


def generate_image_core(prompt: str, seed: int | None) -> dict[str, Any]:
    return {
        "ok": True,
        "runtime": "placeholder",
        "model": "black-forest-labs/FLUX.2-klein-4B",
        "image_url": f"/static/generated/{'field-notes.svg' if seed == 3 else 'model-map.svg'}",
        "prompt": prompt,
        "seed": seed,
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
            "models": {
                "reader_brain": "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF via llama.cpp",
                "vision": "openbmb/MiniCPM-V-2",
                "speech": "hexgrad/Kokoro-82M",
                "image_generation": "black-forest-labs/FLUX.2-klein-4B",
            },
        }
    )


@app.post("/api/reader-brain")
async def reader_brain_endpoint(payload: ReaderBrainRequest) -> JSONResponse:
    return _json(reader_brain_core(payload.node_type, payload.text, payload.position, payload.mode))


@app.post("/api/describe-image")
async def describe_image_endpoint(payload: ImageDescriptionRequest) -> JSONResponse:
    return _json(describe_image_core(payload.image_id, payload.caption, payload.prompt))


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
    app.launch()
