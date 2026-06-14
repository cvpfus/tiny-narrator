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
    assert_true("/api/generate-article" in generate_js, "Generate frontend should call article generation API")
    assert_true("thumbnail.generation_model" in generate_js, "Generate frontend should render Klein thumbnail receipt")
    assert_true('data-reader-type="heading"' in index_html, "Article should mark heading reader nodes")
    assert_true('data-reader-type="image"' in index_html, "Article should mark image reader nodes")
    assert_true('href="#notes"' not in index_html, "Article navigation should not include the Field Notes section")
    assert_true('id="notes"' not in index_html, "Article UI should not render the Field Notes section")
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
    for package in ["pydantic", "kokoro", "soundfile"]:
        assert_true(
            any(line.startswith(f"{package}>=") or line.startswith(f"{package}==") for line in requirements),
            f"requirements.txt should include {package}",
        )


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
    assert_true(isinstance(description["elapsed_ms"], int), "Image description should include elapsed_ms")

    article_descriptions = app.describe_article_images_core()
    assert_true(article_descriptions["ok"], "Article image descriptions did not return ok")
    assert_true(len(article_descriptions["descriptions"]) == 3, "Article should expose three image descriptions")
    assert_true(
        all(item["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"] for item in article_descriptions["descriptions"]),
        "Article image descriptions should include the planned image-generation model",
    )
    assert_true(
        all(isinstance(item["seed"], int) for item in article_descriptions["descriptions"]),
        "Article image descriptions should include generation seeds",
    )
    assert_true(isinstance(article_descriptions["elapsed_ms"], int), "Article image descriptions should include elapsed_ms")

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

    article = app.generate_article_core("tiny classroom robotics")
    assert_true(article["ok"], "Article generation should return ok")
    assert_true(article["model"] == app.MODEL_MANIFEST["reader_brain"]["id"], "Article generation should use reader-brain model")
    assert_true(len(article["article"]["sections"]) == 3, "Article generation should return three sections")
    assert_true(
        article["thumbnail"]["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"],
        "Article generation should use the Klein image model for thumbnail receipt",
    )


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
        {"reader_brain", "speech"} <= set(evidence_payload["runtime_status"]),
        "Evidence bundle runtime status should include reader brain and speech status",
    )
    assert_true(
        evidence_payload["runtime_status"]["reader_brain"]["status"] in {"online", "fallback-ready"},
        "Evidence bundle reader brain status should be online or fallback-ready",
    )
    assert_true(
        evidence_payload["runtime_status"]["speech"]["status"] in {"online", "fallback-ready"},
        "Evidence bundle speech status should be online or fallback-ready",
    )

    runtime = client.get("/api/runtime-status")
    assert_true(runtime.status_code == 200, "Runtime status route should return 200")
    runtime_payload = runtime.json()
    assert_true(runtime_payload["ok"], "Runtime status payload should be ok")
    assert_true("reader_brain" in runtime_payload, "Runtime status should include reader brain status")
    assert_true("speech" in runtime_payload, "Runtime status should include speech status")
    assert_true(
        runtime_payload["reader_brain"]["status"] in {"online", "fallback-ready"},
        "Reader brain status should be online or fallback-ready",
    )

    image_descriptions = client.get("/api/image-descriptions")
    assert_true(image_descriptions.status_code == 200, "Image descriptions route should return 200")
    image_payload = image_descriptions.json()
    assert_true(image_payload["model"] == "OpenBMB MiniCPM-V-2", "Image route should document MiniCPM-V model")
    assert_true(
        {item["id"] for item in image_payload["descriptions"]} == {"desk-reader", "model-map", "field-notes"},
        "Image route should describe all article images",
    )
    assert_true(
        all(item["generation_model"] == app.MODEL_MANIFEST["image_generation"]["id"] for item in image_payload["descriptions"]),
        "Image route should expose image-generation provenance",
    )
    assert_true(
        all(item["generation_status"] == "fallback-ready" for item in image_payload["descriptions"]),
        "Image route should label bundled image fallback status",
    )


def main() -> None:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
    verify_static_assets()
    verify_space_metadata()
    verify_core_fallbacks()
    verify_output_retention()
    verify_routes()
    print("Tiny Narrator verification passed.")


if __name__ == "__main__":
    main()
