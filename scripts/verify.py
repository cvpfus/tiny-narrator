from __future__ import annotations

import json
import py_compile
import sys
import wave
from pathlib import Path
from unittest.mock import patch, MagicMock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app
from fastapi.testclient import TestClient


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_static_assets() -> None:
    required = [
        ROOT / "LICENSE",
        ROOT / "SUBMISSION.md",
        ROOT / "static" / "index.html",
        ROOT / "static" / "generate.html",
        ROOT / "static" / "app.css",
        ROOT / "static" / "app.js",
        ROOT / "static" / "generate.js",
        ROOT / "static" / "generated" / "desk-reader.svg",
        ROOT / "static" / "generated" / "model-map.svg",
        ROOT / "static" / "generated" / "field-notes.svg",
    ]
    for path in required:
        assert_true(path.exists(), f"Missing required asset: {path}")

    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    generate_js = (ROOT / "static" / "generate.js").read_text(encoding="utf-8")
    index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    generate_html = (ROOT / "static" / "generate.html").read_text(encoding="utf-8")
    assert_true('href="/" aria-current="page">Reader' in index_html, "Reader page should mark Reader route current")
    assert_true('href="/generate">Generate' in index_html, "Reader page should link to Generate route")
    assert_true('href="/">Reader' in generate_html, "Generate page should link back to Reader route")
    assert_true('href="/generate" aria-current="page">Generate' in generate_html, "Generate page should mark Generate route current")
    assert_true("articleGeneratorForm" in generate_html, "Generate page should expose the article generator form")
    assert_true("generatedThumbnail" in generate_html, "Generate page should expose a generated thumbnail preview")
    assert_true("readerToggle" in generate_html, "Generate page should expose a screen reader toggle")
    assert_true("transcriptLog" in generate_html, "Generate page should expose a narration transcript")
    assert_true("speechAudio" in generate_html, "Generate page should expose speech playback")
    assert_true("/api/generate-article" in generate_js, "Generate frontend should call article generation API")
    assert_true("/api/reader-brain" in generate_js, "Generate frontend should call reader-brain narration API")
    assert_true("/api/speak" in generate_js, "Generate frontend should call speech API")
    assert_true("refreshReaderNodes" in generate_js, "Generate frontend should build a generated article reader path")
    assert_true('data-reader-type="heading"' in generate_js, "Generated article sections should mark heading reader nodes")
    assert_true('data-reader-type="paragraph"' in generate_js, "Generated article sections should mark paragraph reader nodes")
    assert_true("thumbnail.generation_model" in generate_js, "Generate frontend should render Klein thumbnail receipt")
    assert_true('data-reader-type="heading"' in index_html, "Article should mark heading reader nodes")
    assert_true('data-reader-type="image"' in index_html, "Article should mark image reader nodes")
    assert_true('href="#notes"' not in index_html, "Article navigation should not include the Field Notes section")
    assert_true('id="notes"' not in index_html, "Article UI should not render the Field Notes section")
    assert_true("Field Notes" not in index_html, "Article UI should not render Field Notes copy")
    assert_true("Field Notes" not in generate_html, "Generate UI should not render Field Notes copy")
    assert_true('alt=""' not in index_html, "Article images should not start with empty alt text")
    assert_true(
        "reader brain, vision, speech, and image generation models" in index_html,
        "Article should include meaningful fallback alt text for generated images",
    )
    assert_true('aria-live="polite"' in index_html, "Article should expose an aria-live narration region")
    for shortcut in ['aria-keyshortcuts="Space"', 'aria-keyshortcuts="N"', 'aria-keyshortcuts="R"', 'aria-keyshortcuts="S"']:
        assert_true(shortcut in index_html, f"Reader controls should expose {shortcut}")
    assert_true("transcriptLog" in index_html, "Article should expose a visible transcript log")
    assert_true("readerQueueList" not in index_html, "Article sidebar should not include a visible reader queue")
    assert_true("repeatButton" in index_html, "Reader controls should expose a visible repeat command")
    assert_true("stopButton" in index_html, "Reader controls should expose a visible stop command")
    assert_true("modelStackList" in index_html, "Article sidebar should expose the model stack panel")
    assert_true("modelBudgetStatus" in index_html, "Article sidebar should expose model stack status")
    for removed_id in [
        "demoScriptList",
        "demoApiCheckList",
        "imageReceiptList",
        "runtimeStatusList",
        "submissionReadinessList",
        "copyEvidenceButton",
        "modelBudgetList",
        "runtimeSetupList",
    ]:
        assert_true(removed_id not in index_html, f"Article sidebar should not include removed evidence panel: {removed_id}")
    assert_true("loadDemoScript" not in app_js, "Article frontend should not render the structured demo script")
    assert_true("loadModelBudget" in app_js, "Article frontend should render the model stack panel")
    assert_true("/api/model-budget" in app_js, "Article frontend should fetch model budget data")
    assert_true("/api/runtime-status" in app_js, "Article frontend should fetch runtime status")
    assert_true("status-pill" in app_js or "statusClass" in app_js, "Article frontend should render per-role status labels")
    assert_true("modelStackList.innerHTML" in app_js, "Article frontend should render model stack items")
    assert_true("Tiny Titan pass" in app_js, "Article frontend should render per-model Tiny Titan pass labels")
    assert_true("/evidence" not in index_html, "Article page should not link to a removed evidence page")
    assert_true("copyTextToClipboard" in app_js, "Frontend copy actions should share clipboard fallback handling")
    assert_true(
        "Transcript is visible, but clipboard access is unavailable." in app_js,
        "Transcript copy should report unavailable clipboard access",
    )
    assert_true("transcript-position" in app_js, "Transcript should render the narrated reader position")
    assert_true("readerItemStatus(node)" in app_js, "Narration transcript entries should include reader item position")
    assert_true(
        "[${entry.type} / ${entry.position} / ${entry.runtime}]" in app_js,
        "Copied transcript should include type, position, and runtime",
    )
    assert_true("function haltPlayback" in app_js, "Reader controls should expose a shared playback halt helper")
    assert_true(
        "haltPlayback({ clearAutoAdvance: false });" in app_js,
        "New narration commands should interrupt current speech immediately",
    )
    assert_true("aria-current" in app_js, "Reader mode should expose the active item as current")
    assert_true("shouldHandleReaderShortcut" in app_js, "Reader shortcuts should not hijack form controls")
    assert_true("controls.repeat.click()" in app_js, "R should route through the visible repeat command")
    assert_true("controls.stop.click()" in app_js, "Escape should route through the visible stop command")
    assert_true("reader-node-" in app_js, "Reader nodes should receive stable ids for control context")
    assert_true("renderReaderQueue" not in app_js, "Frontend should not render a visible reader queue")
    assert_true("readerQueueList" not in app_js, "Frontend should not bind a visible reader queue")
    assert_true("narrate(node.index)" in app_js, "Reader mode should support click-to-read article items")

    assert_true("describeGeneratedThumbnail" in generate_js, "Generate frontend should describe generated thumbnails")
    assert_true("/api/describe-image" in generate_js, "Generate frontend should call describe-image for thumbnails")
    assert_true("image_url" in generate_js, "Generate frontend should send image_url to describe-image")
    assert_true("generatedThumbnail.alt" in generate_js, "Generate frontend should update thumbnail alt from descriptor")
    assert_true("fallbackAlt" in generate_js, "Generate frontend should preserve fallback alt on descriptor failure")

    submission = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    for target in ["Tiny Titan", "Llama Champion", "Off-Brand", "Field Notes"]:
        assert_true(target in submission, f"Submission packet should mention {target}")
    for endpoint in [
        "/api/model-budget",
        "/api/runtime-setup",
        "/api/accessibility-audit",
        "/api/demo-script",
        "/api/submission-readiness",
        "/api/evidence-bundle",
        "/api/generate-article",
    ]:
        assert_true(endpoint in submission, f"Submission packet should mention {endpoint}")
    assert_true(
        "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF" in submission,
        "Submission packet should include the reader-brain model",
    )
    for evidence in ["reader cursor", "shortcut safety", "aria-current"]:
        assert_true(evidence in submission, f"Submission packet should mention {evidence}")
    for evidence in ["prompt", "seed", "FLUX.2-klein-4B", "fallback asset"]:
        assert_true(evidence in submission, f"Submission packet should mention image receipt evidence: {evidence}")


def front_matter_value(readme: str, key: str) -> str:
    lines = readme.splitlines()
    if not lines or lines[0] != "---":
        return ""
    for line in lines[1:]:
        if line == "---":
            break
        name, separator, value = line.partition(":")
        if separator and name.strip() == key:
            return value.strip()
    return ""


def verify_space_metadata() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    sdk_version = front_matter_value(readme, "sdk_version")
    app_file = front_matter_value(readme, "app_file")
    sdk = front_matter_value(readme, "sdk")
    emoji = front_matter_value(readme, "emoji")
    title = front_matter_value(readme, "title")
    license_id = front_matter_value(readme, "license")

    assert_true(title == "Tiny Narrator", "Space metadata should name the app")
    assert_true(sdk == "gradio", "Space metadata should declare the Gradio SDK")
    assert_true(app_file == "app.py", "Space metadata should launch app.py")
    assert_true(emoji and "ð" not in emoji, "Space metadata emoji should be valid UTF-8")
    assert_true(license_id == "apache-2.0", "Space metadata should declare the Apache-2.0 license")
    assert_true("Apache License" in license_text, "Repository should include the Apache license text")
    assert_true("Version 2.0" in license_text, "Repository license should match Space metadata")
    assert_true(f"gradio=={sdk_version}" in requirements, "requirements.txt should pin Gradio to sdk_version")
    for package in ["pydantic", "kokoro", "soundfile", "python-dotenv"]:
        assert_true(
            any(
                line.startswith(f"{package}>=") or line.startswith(f"{package}==") or line.strip() == package
                for line in requirements
            ),
            f"requirements.txt should include {package}",
        )


def verify_dotenv_wiring() -> None:
    """Verify that python-dotenv is wired in before core env constants are read."""
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert_true(
        any(line.strip() == "python-dotenv" or line.startswith("python-dotenv>=") for line in requirements),
        "requirements.txt should include python-dotenv",
    )

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert_true("from dotenv import load_dotenv" in app_source, "app.py should import load_dotenv")
    assert_true("load_dotenv()" in app_source, "app.py should call load_dotenv()")

    import_pos = app_source.index("from dotenv import load_dotenv")
    call_pos = app_source.index("load_dotenv()")
    llama_const = app_source.index("LLAMA_CPP_BASE_URL = os.getenv")
    assert_true(
        import_pos < call_pos < llama_const,
        "load_dotenv() should be called before LLAMA_CPP_BASE_URL is assigned",
    )

    env_example = ROOT / ".env.example"
    assert_true(env_example.exists(), ".env.example should exist")
    env_content = env_example.read_text(encoding="utf-8")
    for secret_pattern in ["sk-", "AKIA", "ghp_", "xoxb-"]:
        assert_true(
            secret_pattern not in env_content,
            f".env.example should not contain real-looking secrets ({secret_pattern})",
        )


def verify_live_smoke_script() -> None:
    """Verify that the live smoke test script exists, is syntactically valid, and documents redaction."""
    smoke_path = ROOT / "scripts" / "live_smoke.py"
    assert_true(smoke_path.exists(), "scripts/live_smoke.py should exist")
    py_compile.compile(str(smoke_path), doraise=True)
    smoke_source = smoke_path.read_text(encoding="utf-8")
    assert_true("--base-url" in smoke_source, "Smoke script should support --base-url argument")
    assert_true("/api/runtime-status" in smoke_source, "Smoke script should check runtime status")
    assert_true("/api/describe-image" in smoke_source, "Smoke script should check describe-image")
    assert_true("/api/generate-image" in smoke_source, "Smoke script should check generate-image")
    assert_true("_role_is_configured" in smoke_source, "Smoke script should fail configured live paths instead of skipping them")
    assert_true('details.get("configured") is True' in smoke_source, "Smoke script should preserve configured metadata from runtime status")
    assert_true("SKIP" in smoke_source or "skip" in smoke_source, "Smoke script should document skipping behavior")
    assert_true("Secrets" in smoke_source or "secrets" in smoke_source or "never printed" in smoke_source.lower(), "Smoke script should document secret redaction")


def verify_core_fallbacks() -> None:
    narration = app.reader_brain_core(
        node_type="heading",
        text="Why tiny models matter",
        position="item 1 of 1",
        mode="narrate",
    )
    assert_true(narration["ok"], "Reader-brain fallback did not return ok")
    assert_true("Heading." in narration["narration"], "Reader-brain fallback lost heading prefix")
    assert_true(isinstance(narration["elapsed_ms"], int), "Reader-brain response should include elapsed_ms")

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
    assert_true(description["runtime"] == "fallback", "Image description without MiniCPM config should use fallback runtime")
    assert_true(description["model"] == app.MODEL_MANIFEST["vision"]["id"], "Image description should report the vision model id")
    assert_true(isinstance(description["elapsed_ms"], int), "Image description should include elapsed_ms")

    article_descriptions = app.describe_article_images_core()
    assert_true(article_descriptions["ok"], "Article image descriptions did not return ok")
    assert_true(len(article_descriptions["descriptions"]) == 2, "Article should expose two image descriptions")
    assert_true(
        all(item["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"] for item in article_descriptions["descriptions"]),
        "Article image descriptions should include the planned image-generation model",
    )
    assert_true(
        all(isinstance(item["seed"], int) for item in article_descriptions["descriptions"]),
        "Article image descriptions should include generation seeds",
    )
    assert_true(isinstance(article_descriptions["elapsed_ms"], int), "Article image descriptions should include elapsed_ms")
    assert_true(article_descriptions["model"] == app.MODEL_MANIFEST["vision"]["id"], "Article image descriptions should report vision model id")
    assert_true(article_descriptions["runtime"] == "fallback", "Article image descriptions should use fallback without MiniCPM config")

    speech = app.speak_core("Tiny Narrator verification.", voice="af_heart", speed=1.0)
    assert_true(speech["ok"], "Speech path did not return ok")
    assert_true(isinstance(speech["elapsed_ms"], int), "Speech response should include elapsed_ms")
    audio_path = ROOT / speech["audio_url"].lstrip("/")
    assert_true(audio_path.exists(), f"Speech output missing: {audio_path}")
    with wave.open(str(audio_path), "rb") as wav:
        assert_true(wav.getframerate() == 24000, "Speech output should be 24 kHz")
        assert_true(wav.getnchannels() == 1, "Speech output should be mono")

    generated = app.generate_image_core("Tiny accessibility article image.", seed=3)
    assert_true(generated["ok"], "Image generation placeholder should return ok")
    assert_true(isinstance(generated["elapsed_ms"], int), "Image generation should include elapsed_ms")
    assert_true(generated["runtime"] == "fallback", "Image generation without Modal should report fallback runtime")
    assert_true(generated["model"] == app.MODEL_MANIFEST["image_generation"]["id"], "Image generation should report Klein model id")
    assert_true(generated["seed"] == 3, "Image generation should preserve the seed")
    assert_true(generated["image_url"].startswith("/static/generated/"), "Fallback image should use bundled assets")
    assert_true(generated.get("warning") is None, "Fallback without attempted call should have no warning")

    generated_no_seed = app.generate_image_core("Another image prompt.", seed=None)
    assert_true(generated_no_seed["ok"], "Image generation without seed should return ok")
    assert_true(generated_no_seed["runtime"] == "fallback", "Image generation without Modal should report fallback")
    assert_true(generated_no_seed["seed"] is None, "Image generation should pass through None seed")

    article = app.generate_article_core("tiny classroom robotics")
    assert_true(article["ok"], "Article generation should return ok")
    assert_true(article["model"] == app.MODEL_MANIFEST["reader_brain"]["id"], "Article generation should use reader-brain model")
    assert_true(len(article["article"]["sections"]) == 3, "Article generation should return three sections")
    assert_true(
        article["thumbnail"]["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"],
        "Article generation should use the Klein image model for thumbnail receipt",
    )


def verify_modal_klein_integration() -> None:
    """Test Modal Klein integration with mocked HTTP responses."""
    # Test: no endpoint configured returns deterministic fallback
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", ""):
        result = app.generate_image_core("test prompt", seed=42)
        assert_true(result["ok"], "No-endpoint fallback should return ok")
        assert_true(result["runtime"] == "fallback", "No-endpoint should report fallback runtime")
        assert_true(result["image_url"].startswith("/static/generated/"), "No-endpoint should use bundled assets")
        assert_true(result["model"] == app.MODEL_MANIFEST["image_generation"]["id"], "Fallback should report Klein model")

    # Test: configured endpoint returning valid JSON is surfaced as live Modal inference
    mock_response_data = {
        "ok": True,
        "runtime": "modal-klein",
        "model": "black-forest-labs/FLUX.2-klein-4B",
        "image_url": "/media/klein-abc123.png",
        "prompt": "test prompt",
        "seed": 42,
        "elapsed_ms": 5000,
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"):
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = app.generate_image_core("test prompt", seed=42)
            assert_true(result["ok"], "Modal success should return ok")
            assert_true(result["runtime"] == "modal-klein", "Modal success should report modal-klein runtime")
            assert_true(
                result["image_url"] == "https://example-modal.modal.run/media/klein-abc123.png",
                "Modal success should return full media URL",
            )
            assert_true(result["prompt"] == "test prompt", "Modal success should preserve prompt")
            assert_true(result["seed"] == 42, "Modal success should preserve seed")

    # Test: configured endpoint failure falls back with a visible warning
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            result = app.generate_image_core("test prompt", seed=42)
            assert_true(result["ok"], "Modal failure fallback should return ok")
            assert_true(result["runtime"] == "fallback", "Modal failure should report fallback runtime")
            assert_true(
                result["image_url"].startswith("/static/generated/"),
                "Modal failure should use bundled assets",
            )
            assert_true(
                result.get("warning") is not None and "TimeoutError" in result["warning"],
                "Modal failure should include a visible warning with the error class",
            )

    # Test: invalid Modal JSON response falls back instead of pretending success
    invalid_response = MagicMock()
    invalid_response.read.return_value = json.dumps({"ok": False, "error": "prompt is required"}).encode("utf-8")
    invalid_response.__enter__ = lambda s: s
    invalid_response.__exit__ = MagicMock(return_value=False)

    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"):
        with patch("urllib.request.urlopen", return_value=invalid_response):
            result = app.generate_image_core("test prompt", seed=42)
            assert_true(result["runtime"] == "fallback", "Invalid Modal response should use fallback runtime")
            assert_true(
                result.get("warning") is not None and "ValueError" in result["warning"],
                "Invalid Modal response should include a validation warning",
            )

    # Test: Modal worker static checks
    worker_path = ROOT / "modal_workers" / "klein_image.py"
    assert_true(worker_path.exists(), "Modal worker file should exist")
    worker_source = worker_path.read_text(encoding="utf-8")
    assert_true("modal.App" in worker_source, "Modal worker should create a Modal App")
    assert_true("modal.Volume" in worker_source, "Modal worker should use a Modal Volume")
    assert_true("FLUX.2-klein-4B" in worker_source, "Modal worker should reference the Klein model")
    assert_true("modal.asgi_app" in worker_source, "Modal worker should expose one ASGI app")
    assert_true('@api.post("/generate")' in worker_source, "Modal worker should expose POST /generate")
    assert_true('@api.get("/health")' in worker_source, "Modal worker should expose GET /health")
    assert_true('@api.get("/media/{filename}")' in worker_source, "Modal worker should expose GET /media/{filename}")
    assert_true("404" in worker_source or "not found" in worker_source.lower(), "Modal worker should handle missing media with 404")
    assert_true("reload" in worker_source, "Modal worker should reload volume before serving")

    # Test: auth wiring — app sends bearer token when configured
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"), patch.object(app, "KLEIN_MODAL_TOKEN", "test-secret-token"):
        with patch("urllib.request.urlopen", return_value=mock_response) as urlopen_mock:
            app.generate_image_core("auth test", seed=1)
            sent_request = urlopen_mock.call_args.args[0]
            assert_true(
                sent_request.headers.get("Authorization") == "Bearer test-secret-token",
                "App should send Bearer token when KLEIN_MODAL_TOKEN is configured",
            )

    # Test: auth wiring — health check sends bearer token when configured
    good_health = MagicMock()
    good_health.read.return_value = json.dumps({"ok": True, "model": app.MODEL_MANIFEST["image_generation"]["id"], "runtime": "modal-klein"}).encode("utf-8")
    good_health.__enter__ = lambda s: s
    good_health.__exit__ = MagicMock(return_value=False)
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"), patch.object(app, "KLEIN_MODAL_TOKEN", "test-secret-token"):
        with patch("urllib.request.urlopen", return_value=good_health) as urlopen_mock:
            app._runtime_status_core()
            health_request = urlopen_mock.call_args.args[0]
            assert_true(
                health_request.headers.get("Authorization") == "Bearer test-secret-token",
                "App should send Bearer token for health checks when KLEIN_MODAL_TOKEN is configured",
            )

    # Test: .env.example includes KLEIN_MODAL_TOKEN
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert_true("KLEIN_MODAL_TOKEN" in env_example, ".env.example should document KLEIN_MODAL_TOKEN")

    # Test: worker validates token
    assert_true("KLEIN_MODAL_TOKEN" in worker_source, "Modal worker should read KLEIN_MODAL_TOKEN")
    assert_true("401" in worker_source, "Modal worker should reject unauthorized requests with 401")
    assert_true("_check_token" in worker_source, "Modal worker should have a token validation helper")
    assert_true(
        "async def health(request: Request)" in worker_source,
        "Modal worker health route should accept the request for token validation",
    )

    # Test: runtime setup does not expose the token value
    with patch.object(app, "KLEIN_MODAL_TOKEN", "super-secret-value"):
        setup = app.runtime_setup_core()
        setup_json = json.dumps(setup)
        assert_true("super-secret-value" not in setup_json, "Runtime setup must never expose the token value")
        image_step = next(step for step in setup["steps"] if step["role"] == "image_generation")
        assert_true(
            "KLEIN_MODAL_TOKEN" in image_step["env"],
            "Runtime setup should document KLEIN_MODAL_TOKEN",
        )
        assert_true(
            image_step["env"]["KLEIN_MODAL_TOKEN"] == "(configured)",
            "Runtime setup should show token as configured without exposing the value",
        )

    # Test: runtime status includes Modal Klein path
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", ""):
        status = app._runtime_status_core()
        assert_true("image_generation" in status, "Runtime status should include image_generation")
        assert_true(
            status["image_generation"]["status"] in {"online", "fallback-ready"},
            "Image generation status should be online or fallback-ready",
        )
        assert_true(
            status["image_generation"]["model"] == app.MODEL_MANIFEST["image_generation"]["id"],
            "Image generation status should reference the Klein model",
        )

    # Test: invalid health payload is fallback-ready, not online
    bad_health = MagicMock()
    bad_health.read.return_value = json.dumps({"ok": True, "model": "wrong", "runtime": "modal-klein"}).encode("utf-8")
    bad_health.__enter__ = lambda s: s
    bad_health.__exit__ = MagicMock(return_value=False)
    with patch.object(app, "KLEIN_MODAL_ENDPOINT", "https://example-modal.modal.run"):
        with patch("urllib.request.urlopen", return_value=bad_health):
            status = app._runtime_status_core()
            assert_true(
                status["image_generation"]["status"] == "fallback-ready",
                "Invalid Modal health should not be marked online",
            )
            assert_true("ValueError" in status["image_generation"].get("warning", ""), "Invalid health should report validation warning")

    # Test: runtime setup includes Modal deploy command
    setup = app.runtime_setup_core()
    image_step = next(step for step in setup["steps"] if step["role"] == "image_generation")
    assert_true(
        "modal deploy" in image_step["command"],
        "Runtime setup should include modal deploy command for image generation",
    )
    assert_true(
        "KLEIN_MODAL_ENDPOINT" in image_step["env"],
        "Runtime setup should document KLEIN_MODAL_ENDPOINT",
    )


def verify_minicpm_vision_integration() -> None:
    with patch.object(app, "MINICPM_VISION_BASE_URL", ""), patch.object(app, "MINICPM_VISION_API_KEY", ""):
        result = app.describe_image_core("model-map", caption=None, prompt=None)
        assert_true(result["ok"], "No-config MiniCPM fallback should return ok")
        assert_true(result["runtime"] == "fallback", "No-config MiniCPM should report fallback runtime")
        assert_true(result["model"] == app.MODEL_MANIFEST["vision"]["id"], "No-config MiniCPM should report vision model")
        assert_true(result.get("warning") is None, "No-config MiniCPM fallback should stay quiet")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": "A compact diagram shows four small AI models connected around an accessibility reader."
                }
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch.object(app, "MINICPM_VISION_BASE_URL", "https://vision.example/v1"):
        with patch.object(app, "MINICPM_VISION_API_KEY", "secret-key"):
            with patch("urllib.request.urlopen", return_value=mock_response) as urlopen_mock:
                result = app.describe_image_core("model-map", caption="diagram", prompt="model map", image_url="/static/generated/model-map.svg")
                assert_true(result["ok"], "Live MiniCPM response should return ok")
                assert_true(result["runtime"] == "minicpm-v4.6", "Live MiniCPM response should report runtime")
                assert_true(result["model"] == app.MINICPM_VISION_MODEL, "Live MiniCPM response should report configured model")
                assert_true("accessibility reader" in result["alt_text"], "Live MiniCPM response should use returned alt text")
                request = urlopen_mock.call_args.args[0]
                assert_true(
                    request.full_url == "https://vision.example/v1/chat/completions",
                    "MiniCPM client should normalize base URL to chat completions",
                )
                assert_true(
                    request.headers.get("Authorization") == "Bearer secret-key",
                    "MiniCPM client should send bearer auth",
                )

    invalid_response = MagicMock()
    invalid_response.read.return_value = json.dumps({"choices": [{"message": {"content": ""}}]}).encode("utf-8")
    invalid_response.__enter__ = lambda s: s
    invalid_response.__exit__ = MagicMock(return_value=False)

    with patch.object(app, "MINICPM_VISION_BASE_URL", "https://vision.example"):
        with patch.object(app, "MINICPM_VISION_API_KEY", "secret-key"):
            with patch("urllib.request.urlopen", return_value=invalid_response):
                result = app.describe_image_core("custom", caption="fallback caption", prompt=None, image_url="https://example.com/image.png")
                assert_true(result["runtime"] == "fallback", "Invalid MiniCPM response should fall back")
                assert_true(result["alt_text"] == "fallback caption", "Invalid MiniCPM response should preserve fallback text")
                assert_true(
                    result.get("warning") is not None and "ValueError" in result["warning"],
                    "Invalid MiniCPM response should include validation warning",
                )

    models_response = MagicMock()
    models_response.read.return_value = json.dumps({"data": [{"id": app.MINICPM_VISION_MODEL}]}).encode("utf-8")
    models_response.__enter__ = lambda s: s
    models_response.__exit__ = MagicMock(return_value=False)

    with patch.object(app, "MINICPM_VISION_BASE_URL", "https://vision.example/v1"):
        with patch.object(app, "MINICPM_VISION_API_KEY", "secret-key"):
            with patch("urllib.request.urlopen", return_value=models_response):
                status = app._vision_runtime_status()
                assert_true(status["status"] == "online", "MiniCPM /models response should mark vision online")
                assert_true("secret-key" not in json.dumps(status), "Vision runtime status should not expose API key")

    setup = app.runtime_setup_core()
    vision_step = next(step for step in setup["steps"] if step["role"] == "vision")
    assert_true("MiniCPM-V-4.6" in vision_step["model"], "Runtime setup should document MiniCPM-V-4.6")
    assert_true("MINICPM_VISION_BASE_URL" in vision_step["env"], "Runtime setup should document MiniCPM base URL")
    assert_true("secret" not in json.dumps(vision_step).lower(), "Runtime setup should not expose MiniCPM API key")


def verify_output_retention() -> None:
    keep_path = app.OUTPUT_DIR / "speech-retention-keep.wav"
    _ = app.speak_core("Tiny Narrator retention check.", voice="af_heart", speed=1.0)
    keep_path.write_bytes(b"keep")
    stale_files = []
    for index in range(30):
        stale_path = app.OUTPUT_DIR / f"speech-retention-stale-{index:02d}.wav"
        stale_path.write_bytes(b"stale")
        stale_files.append(stale_path)

    app._prune_speech_outputs(keep_path, max_files=4)

    remaining = list(app.OUTPUT_DIR.glob("speech*.wav"))
    assert_true(keep_path.exists(), "Speech retention should keep the active output")
    assert_true(len(remaining) <= 5, "Speech retention should prune stale generated audio")

    keep_path.unlink(missing_ok=True)
    for stale_path in stale_files:
        stale_path.unlink(missing_ok=True)


def verify_routes() -> None:
    client = TestClient(app.app)

    home = client.get("/")
    assert_true(home.status_code == 200, "Home route should return 200")
    assert_true("Tiny Narrator" in home.text, "Home route should include app title")
    assert_true('href="/generate">Generate' in home.text, "Home route should link to Generate route")
    assert_true("readerToggle" in home.text, "Home route should include reader toggle")
    assert_true("summaryButton" in home.text, "Home route should include summary control")
    assert_true("imageStatus" in home.text, "Home route should include image status")
    assert_true("voiceStatus" in home.text, "Home route should include voice status")
    assert_true("latencyStatus" in home.text, "Home route should include latency status")
    assert_true("voiceControl" in home.text, "Home route should include voice control")
    assert_true("speedValue" in home.text, "Home route should include speed value output")
    assert_true("autoAdvanceControl" in home.text, "Home route should include auto-advance control")
    assert_true("transcriptLog" in home.text, "Home route should include transcript log")
    assert_true("readerQueueList" not in home.text, "Home route should not include reader queue list")
    assert_true("modelBudgetStatus" in home.text, "Home route should include model stack status")
    assert_true("modelStackList" in home.text, "Home route should include model stack list")
    assert_true("/evidence" not in home.text, "Home route should not link to a removed evidence page")
    assert_true("copyEvidenceButton" not in home.text, "Home route should keep judge evidence off the reader sidebar")

    generate_page = client.get("/generate")
    assert_true(generate_page.status_code == 200, "Generate route should return 200")
    assert_true("Generate a readable article" in generate_page.text, "Generate route should include generator title")
    assert_true("articleGeneratorForm" in generate_page.text, "Generate route should include article generator form")
    assert_true("generatedThumbnail" in generate_page.text, "Generate route should include generated thumbnail")
    assert_true("readerToggle" in generate_page.text, "Generate route should include reader toggle")
    assert_true("summaryButton" in generate_page.text, "Generate route should include summary control")
    assert_true("transcriptLog" in generate_page.text, "Generate route should include transcript log")
    assert_true("speechAudio" in generate_page.text, "Generate route should include speech playback")

    health = client.get("/api/health")
    assert_true(health.status_code == 200, "Health route should return 200")
    payload = health.json()
    assert_true(payload["ok"], "Health payload should be ok")
    assert_true(payload["public_base_url"] == app.PUBLIC_BASE_URL, "Health route should expose the public command base URL")
    assert_true(
        payload["models"]["reader_brain"]["runtime"] == "llama.cpp",
        "Health route should document llama.cpp reader-brain runtime",
    )

    manifest = client.get("/api/article-manifest")
    assert_true(manifest.status_code == 200, "Article manifest route should return 200")
    manifest_payload = manifest.json()
    assert_true("Tiny Titan" in manifest_payload["bonus_targets"], "Manifest should include Tiny Titan target")
    reader_controls = manifest_payload["reader_controls"]
    summary_shortcut = next((item for item in reader_controls if item["key"] == "S"), None)
    assert_true(summary_shortcut is not None, "Manifest should include summary shortcut")
    assert_true(
        summary_shortcut["action"] == "Summarize current section"
        and summary_shortcut["aria_keyshortcuts"] == "S",
        "Manifest summary shortcut should include action and aria-keyshortcuts value",
    )
    assert_true(
        {item["aria_keyshortcuts"] for item in reader_controls} >= {"Space", "N", "P", "H", "I", "S", "R", "Escape"},
        "Manifest should expose aria-keyshortcuts values for reader controls",
    )
    assert_true(
        manifest_payload["models"]["speech"]["id"] == "hexgrad/Kokoro-82M",
        "Manifest should document Kokoro speech model",
    )
    assert_true(
        manifest_payload["reader_settings"]["default_voice"] == "af_heart",
        "Manifest should document default Kokoro voice",
    )
    assert_true(
        len(manifest_payload["reader_settings"]["voices"]) >= 4,
        "Manifest should expose multiple Kokoro voice choices",
    )
    assert_true(
        manifest_payload["reader_settings"]["default_auto_advance"] is False,
        "Manifest should default auto-advance off",
    )
    assert_true(
        len(manifest_payload["award_evidence"]) == 4,
        "Manifest should expose four award evidence items",
    )
    assert_true(
        manifest_payload["model_budget"]["all_models_within_limit"],
        "Manifest should prove every model is within the Tiny Titan limit",
    )
    assert_true(
        len(manifest_payload["runtime_setup"]["steps"]) == 4,
        "Manifest should expose setup steps for each model role",
    )
    assert_true(
        len(manifest_payload["demo_script"]["actions"]) >= 4,
        "Manifest should expose a judge demo script",
    )
    assert_true(
        manifest_payload["accessibility_audit"]["all_passed"],
        "Manifest should expose passing accessibility audit evidence",
    )

    awards = client.get("/api/award-evidence")
    assert_true(awards.status_code == 200, "Award evidence route should return 200")
    award_payload = awards.json()
    assert_true(award_payload["ok"], "Award evidence payload should be ok")
    assert_true(
        {item["id"] for item in award_payload["items"]} == {"tiny-titan", "llama-champion", "off-brand", "field-notes"},
        "Award evidence route should cover the targeted bonuses",
    )

    budget = client.get("/api/model-budget")
    assert_true(budget.status_code == 200, "Model budget route should return 200")
    budget_payload = budget.json()
    assert_true(budget_payload["ok"], "Model budget payload should be ok")
    assert_true(budget_payload["limit_billion"] == 4.0, "Tiny Titan limit should be 4B")
    assert_true(budget_payload["all_models_within_limit"], "All models should stay within the Tiny Titan limit")
    assert_true(
        all(item["params_billion"] <= budget_payload["limit_billion"] for item in budget_payload["models"]),
        "Every model budget item should be at or below the limit",
    )

    setup = client.get("/api/runtime-setup")
    assert_true(setup.status_code == 200, "Runtime setup route should return 200")
    setup_payload = setup.json()
    assert_true(setup_payload["ok"], "Runtime setup payload should be ok")
    assert_true(
        {item["role"] for item in setup_payload["steps"]}
        == {"reader_brain", "speech", "vision", "image_generation"},
        "Runtime setup should cover every model path",
    )
    assert_true(
        "llama-server" in setup_payload["steps"][0]["command"],
        "Runtime setup should include the llama.cpp launch command",
    )
    assert_true(
        setup_payload["app"]["env"]["PUBLIC_BASE_URL"] == app.PUBLIC_BASE_URL,
        "Runtime setup should expose the public command base URL",
    )

    demo = client.get("/api/demo-script")
    assert_true(demo.status_code == 200, "Demo script route should return 200")
    demo_payload = demo.json()
    assert_true(demo_payload["ok"], "Demo script payload should be ok")
    assert_true(
        "Tiny Narrator judge demo" == demo_payload["title"],
        "Demo script should be labeled for judging",
    )
    assert_true(
        {item["path"] for item in demo_payload["api_checks"]} >= {"/api/model-budget", "/api/runtime-setup"},
        "Demo script should include evidence API checks",
    )
    assert_true(
        any("Tiny Titan" in action["evidence"] for action in demo_payload["actions"]),
        "Demo script should point to targeted award evidence",
    )
    assert_true(
        any(item["path"] == "/api/accessibility-audit" for item in demo_payload["api_checks"]),
        "Demo script should include the accessibility audit check",
    )
    assert_true(
        any(item["path"] == "/api/submission-readiness" for item in demo_payload["api_checks"]),
        "Demo script should include the submission readiness check",
    )
    reader_check = next(item for item in demo_payload["api_checks"] if item["path"] == "/api/reader-brain")
    speech_check = next(item for item in demo_payload["api_checks"] if item["path"] == "/api/speak")
    assert_true(reader_check["sample_body"]["mode"] == "narrate", "Reader-brain demo check should include a sample body")
    assert_true(
        speech_check["sample_body"]["voice"] == app.READER_SETTINGS["default_voice"],
        "Speech demo check should use the default reader voice",
    )
    assert_true(
        all(item.get("sample_body") for item in demo_payload["api_checks"] if item["method"] == "POST"),
        "Every POST demo check should include an executable sample body",
    )
    assert_true(
        all(item["curl"].startswith("curl ") for item in demo_payload["api_checks"]),
        "Every demo API check should include a curl command",
    )
    assert_true(
        all(app.PUBLIC_BASE_URL in item["curl"] for item in demo_payload["api_checks"]),
        "Every curl command should use the public command base URL",
    )
    assert_true(
        all(item["powershell"].startswith("curl.exe ") for item in demo_payload["api_checks"]),
        "Every demo API check should include a PowerShell-friendly curl.exe command",
    )
    assert_true(
        all(app.PUBLIC_BASE_URL in item["powershell"] for item in demo_payload["api_checks"]),
        "Every PowerShell command should use the public command base URL",
    )
    assert_true(
        "-d '" in reader_check["curl"] and "/api/reader-brain" in reader_check["curl"],
        "Reader-brain curl command should include the sample JSON body",
    )
    assert_true(
        '\\"node_type\\"' in reader_check["powershell"] and "/api/reader-brain" in reader_check["powershell"],
        "Reader-brain PowerShell command should include escaped sample JSON",
    )
    reader_sample = client.post(reader_check["path"], json=reader_check["sample_body"])
    assert_true(reader_sample.status_code == 200, "Reader-brain sample payload should be executable")
    reader_sample_payload = reader_sample.json()
    assert_true(reader_sample_payload["ok"], "Reader-brain sample payload should return ok")
    assert_true("narration" in reader_sample_payload, "Reader-brain sample payload should return narration")

    speech_sample = client.post(speech_check["path"], json=speech_check["sample_body"])
    assert_true(speech_sample.status_code == 200, "Speech sample payload should be executable")
    speech_sample_payload = speech_sample.json()
    assert_true(speech_sample_payload["ok"], "Speech sample payload should return ok")
    assert_true(
        speech_sample_payload["audio_url"].startswith("/outputs/"),
        "Speech sample payload should return an output audio URL",
    )

    article_sample = client.post("/api/generate-article", json={"topic": "accessible classroom robotics"})
    assert_true(article_sample.status_code == 200, "Article generation route should return 200")
    article_sample_payload = article_sample.json()
    assert_true(article_sample_payload["ok"], "Article generation payload should return ok")
    assert_true(len(article_sample_payload["article"]["sections"]) == 3, "Article generation payload should include three sections")
    assert_true(
        article_sample_payload["thumbnail"]["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"],
        "Article generation payload should include Klein thumbnail provenance",
    )

    audit = client.get("/api/accessibility-audit")
    assert_true(audit.status_code == 200, "Accessibility audit route should return 200")
    audit_payload = audit.json()
    assert_true(audit_payload["ok"], "Accessibility audit payload should be ok")
    assert_true(audit_payload["all_passed"], "Accessibility audit should pass")
    assert_true(audit_payload["passed_checks"] == audit_payload["total_checks"], "All audit checks should pass")
    assert_true(
        {item["id"] for item in audit_payload["checks"]}
        >= {
            "semantic_queue",
            "keyboard_navigation",
            "reader_cursor",
            "shortcut_safety",
            "live_region",
            "image_alt_text",
            "inspectable_transcript",
        },
        "Accessibility audit should cover reader semantics, keyboard use, cursor state, shortcut safety, live narration, alt text, and transcript",
    )

    readiness = client.get("/api/submission-readiness")
    assert_true(readiness.status_code == 200, "Submission readiness route should return 200")
    readiness_payload = readiness.json()
    assert_true(readiness_payload["ok"], "Submission readiness payload should be ok")
    assert_true(readiness_payload["all_passed"], "Submission readiness checks should pass")
    assert_true(
        {item["id"] for item in readiness_payload["checks"]}
        >= {
            "tiny_titan_budget",
            "award_targets",
            "custom_frontend",
            "runtime_setup",
            "runtime_status",
            "reader_accessibility",
            "image_receipts",
            "demo_api_checks",
            "command_base_url",
        },
        "Submission readiness should aggregate model, award, frontend, runtime, accessibility, image, and demo evidence",
    )
    runtime_status_check = next(item for item in readiness_payload["checks"] if item["id"] == "runtime_status")
    assert_true(runtime_status_check["status"] == "pass", "Submission readiness should pass runtime status checks")
    demo_api_check = next(item for item in readiness_payload["checks"] if item["id"] == "demo_api_checks")
    assert_true(demo_api_check["status"] == "pass", "Submission readiness should pass executable demo API checks")
    command_base_check = next(item for item in readiness_payload["checks"] if item["id"] == "command_base_url")
    assert_true(command_base_check["status"] == "pass", "Submission readiness should pass command base URL checks")

    evidence = client.get("/api/evidence-bundle")
    assert_true(evidence.status_code == 200, "Evidence bundle route should return 200")
    evidence_payload = evidence.json()
    assert_true(evidence_payload["ok"], "Evidence bundle payload should be ok")
    assert_true(evidence_payload["schema_version"] == "1.0", "Evidence bundle should include schema version")
    assert_true(evidence_payload["generated_at"].endswith("Z"), "Evidence bundle should include UTC timestamp")
    assert_true(evidence_payload["public_base_url"] == app.PUBLIC_BASE_URL, "Evidence bundle should include public base URL")
    assert_true(evidence_payload["submission_readiness"]["all_passed"], "Evidence bundle should include passing readiness")
    assert_true(evidence_payload["model_budget"]["all_models_within_limit"], "Evidence bundle should include Tiny Titan proof")
    assert_true(
        {"runtime_status", "demo_script", "accessibility_audit", "image_descriptions"} <= set(evidence_payload),
        "Evidence bundle should include runtime status, demo script, accessibility audit, and image descriptions",
    )
    assert_true(evidence_payload["runtime_status"]["ok"], "Evidence bundle should include ok runtime status")
    assert_true(
        {"reader_brain", "speech", "image_generation"} <= set(evidence_payload["runtime_status"]),
        "Evidence bundle runtime status should include reader brain, speech, and image generation status",
    )
    assert_true(
        evidence_payload["runtime_status"]["reader_brain"]["status"] in {"online", "fallback-ready"},
        "Evidence bundle reader brain status should be online or fallback-ready",
    )
    assert_true(
        evidence_payload["runtime_status"]["speech"]["status"] in {"online", "fallback-ready"},
        "Evidence bundle speech status should be online or fallback-ready",
    )
    assert_true(
        evidence_payload["runtime_status"]["image_generation"]["status"] in {"online", "fallback-ready"},
        "Evidence bundle image generation status should be online or fallback-ready",
    )

    runtime = client.get("/api/runtime-status")
    assert_true(runtime.status_code == 200, "Runtime status route should return 200")
    runtime_payload = runtime.json()
    assert_true(runtime_payload["ok"], "Runtime status payload should be ok")
    assert_true("reader_brain" in runtime_payload, "Runtime status should include reader brain status")
    assert_true("speech" in runtime_payload, "Runtime status should include speech status")
    assert_true("image_generation" in runtime_payload, "Runtime status should include image generation status")
    assert_true(
        runtime_payload["reader_brain"]["status"] in {"online", "fallback-ready"},
        "Reader brain status should be online or fallback-ready",
    )
    assert_true(
        runtime_payload["image_generation"]["status"] in {"online", "fallback-ready"},
        "Image generation status should be online or fallback-ready",
    )
    assert_true(
        runtime_payload["image_generation"]["model"] == app.MODEL_MANIFEST["image_generation"]["id"],
        "Image generation status should reference the Klein model",
    )

    image_descriptions = client.get("/api/image-descriptions")
    assert_true(image_descriptions.status_code == 200, "Image descriptions route should return 200")
    image_payload = image_descriptions.json()
    assert_true(image_payload["model"] == app.MODEL_MANIFEST["vision"]["id"], "Image route should document MiniCPM-V model")
    assert_true(image_payload["runtime"] == "fallback", "Image route should use fallback runtime without MiniCPM config")
    assert_true(
        {item["id"] for item in image_payload["descriptions"]} == {"desk-reader", "model-map"},
        "Image route should describe all visible article images",
    )
    assert_true(
        all(item["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"] for item in image_payload["descriptions"]),
        "Image route should expose image-generation provenance",
    )
    assert_true(
        all(item["generation_status"] == "fallback-ready" for item in image_payload["descriptions"]),
        "Image route should label bundled image fallback status",
    )

    # Verify generate-image endpoint returns fallback when Modal is not configured
    gen_image = client.post("/api/generate-image", json={"prompt": "test thumbnail", "seed": 7})
    assert_true(gen_image.status_code == 200, "Generate image route should return 200")
    gen_image_payload = gen_image.json()
    assert_true(gen_image_payload["ok"], "Generate image payload should be ok")
    assert_true(gen_image_payload["model"] == app.MODEL_MANIFEST["image_generation"]["id"], "Generate image should report Klein model")
    assert_true(gen_image_payload["runtime"] == "fallback", "Generate image without Modal should report fallback")
    assert_true(isinstance(gen_image_payload["elapsed_ms"], int), "Generate image should include elapsed_ms")


def main() -> None:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
    py_compile.compile(str(ROOT / "modal_workers" / "klein_image.py"), doraise=True)
    verify_static_assets()
    verify_space_metadata()
    verify_dotenv_wiring()
    verify_live_smoke_script()
    verify_core_fallbacks()
    verify_modal_klein_integration()
    verify_minicpm_vision_integration()
    verify_output_retention()
    verify_routes()
    print("Tiny Narrator verification passed.")


if __name__ == "__main__":
    main()
