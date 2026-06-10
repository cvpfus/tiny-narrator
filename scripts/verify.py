from __future__ import annotations

import py_compile
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
from fastapi.testclient import TestClient


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_static_assets() -> None:
    required = [
        ROOT / "static" / "index.html",
        ROOT / "static" / "app.css",
        ROOT / "static" / "app.js",
        ROOT / "static" / "generated" / "desk-reader.svg",
        ROOT / "static" / "generated" / "model-map.svg",
        ROOT / "static" / "generated" / "field-notes.svg",
    ]
    for path in required:
        assert_true(path.exists(), f"Missing required asset: {path}")


def verify_core_fallbacks() -> None:
    narration = app.reader_brain_core(
        node_type="heading",
        text="Why tiny models matter",
        position="item 1 of 1",
        mode="narrate",
    )
    assert_true(narration["ok"], "Reader-brain fallback did not return ok")
    assert_true("Heading." in narration["narration"], "Reader-brain fallback lost heading prefix")

    description = app.describe_image_core("model-map", caption=None, prompt=None)
    assert_true(description["ok"], "Image description did not return ok")
    assert_true("small AI models" in description["alt_text"], "Image description fallback changed unexpectedly")

    speech = app.speak_core("Tiny Narrator verification.", voice="af_heart", speed=1.0)
    assert_true(speech["ok"], "Speech path did not return ok")
    audio_path = ROOT / speech["audio_url"].lstrip("/")
    assert_true(audio_path.exists(), f"Speech output missing: {audio_path}")
    with wave.open(str(audio_path), "rb") as wav:
        assert_true(wav.getframerate() == 24000, "Speech output should be 24 kHz")
        assert_true(wav.getnchannels() == 1, "Speech output should be mono")


def verify_routes() -> None:
    client = TestClient(app.app)

    home = client.get("/")
    assert_true(home.status_code == 200, "Home route should return 200")
    assert_true("Tiny Narrator" in home.text, "Home route should include app title")
    assert_true("readerToggle" in home.text, "Home route should include reader toggle")

    health = client.get("/api/health")
    assert_true(health.status_code == 200, "Health route should return 200")
    payload = health.json()
    assert_true(payload["ok"], "Health payload should be ok")
    assert_true(
        payload["models"]["reader_brain"]["runtime"] == "llama.cpp",
        "Health route should document llama.cpp reader-brain runtime",
    )


def main() -> None:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
    verify_static_assets()
    verify_core_fallbacks()
    verify_routes()
    print("Tiny Narrator verification passed.")


if __name__ == "__main__":
    main()
