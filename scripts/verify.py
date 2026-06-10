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

    summary = app.reader_brain_core(
        node_type="section",
        text="Tiny models can run close to the reader. They keep latency low and preserve privacy.",
        position="Why",
        mode="summarize",
    )
    assert_true(summary["ok"], "Reader-brain summary fallback did not return ok")
    assert_true(summary["narration"].startswith("Summary."), "Summary fallback should announce summary mode")

    description = app.describe_image_core("model-map", caption=None, prompt=None)
    assert_true(description["ok"], "Image description did not return ok")
    assert_true("small AI models" in description["alt_text"], "Image description fallback changed unexpectedly")

    article_descriptions = app.describe_article_images_core()
    assert_true(article_descriptions["ok"], "Article image descriptions did not return ok")
    assert_true(len(article_descriptions["descriptions"]) == 3, "Article should expose three image descriptions")

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
    assert_true("summaryButton" in home.text, "Home route should include summary control")
    assert_true("imageStatus" in home.text, "Home route should include image status")
    assert_true("voiceStatus" in home.text, "Home route should include voice status")
    assert_true("transcriptLog" in home.text, "Home route should include transcript log")

    health = client.get("/api/health")
    assert_true(health.status_code == 200, "Health route should return 200")
    payload = health.json()
    assert_true(payload["ok"], "Health payload should be ok")
    assert_true(
        payload["models"]["reader_brain"]["runtime"] == "llama.cpp",
        "Health route should document llama.cpp reader-brain runtime",
    )

    manifest = client.get("/api/article-manifest")
    assert_true(manifest.status_code == 200, "Article manifest route should return 200")
    manifest_payload = manifest.json()
    assert_true("Tiny Titan" in manifest_payload["bonus_targets"], "Manifest should include Tiny Titan target")
    assert_true(
        {"key": "S", "action": "Summarize current section"} in manifest_payload["reader_controls"],
        "Manifest should include summary shortcut",
    )
    assert_true(
        manifest_payload["models"]["speech"]["id"] == "hexgrad/Kokoro-82M",
        "Manifest should document Kokoro speech model",
    )

    image_descriptions = client.get("/api/image-descriptions")
    assert_true(image_descriptions.status_code == 200, "Image descriptions route should return 200")
    image_payload = image_descriptions.json()
    assert_true(image_payload["model"] == "OpenBMB MiniCPM-V-2", "Image route should document MiniCPM-V model")
    assert_true(
        {item["id"] for item in image_payload["descriptions"]} == {"desk-reader", "model-map", "field-notes"},
        "Image route should describe all article images",
    )


def main() -> None:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
    verify_static_assets()
    verify_core_fallbacks()
    verify_routes()
    print("Tiny Narrator verification passed.")


if __name__ == "__main__":
    main()
