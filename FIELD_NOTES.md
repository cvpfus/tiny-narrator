# Field Notes

These notes are the seed for the hackathon build report.

## Submission Thesis

Tiny Narrator is a small-model accessibility article reader. It is not a generic chatbot wrapped in a page. The app uses semantic article structure, a keyboard-first reader mode, and model-specific jobs so each small model has a clear reason to exist.

## Bonus Targets

| Target | Evidence we are building |
| --- | --- |
| Tiny Titan | Every planned model is at or below 4B parameters. |
| Llama Champion | The reader-brain layer calls a GGUF model through a llama.cpp OpenAI-compatible endpoint. |
| Off-Brand | The visible app is custom HTML, CSS, and JavaScript served by `gr.Server`. |
| Field Notes | This file documents model choices, architecture, fallbacks, and accessibility behavior. |

## Model Budget

| Role | Model | Size | Why it belongs |
| --- | --- | ---: | --- |
| Reader brain | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 3.97B | Local narration planning through llama.cpp. |
| Vision | `openbmb/MiniCPM-V-4.6` | 1B | Describes generated article images and handles OCR-like image text through an OpenAI-compatible endpoint. |
| Speech | `hexgrad/Kokoro-82M` | 82M | Fast screen-reader voice with a tiny footprint. |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | 4B | Generates the article illustrations through a Modal-hosted worker, with bundled SVG fallback. |

The app exposes the same budget through `/api/model-budget`, including numeric `params_billion` values, per-model `within_limit` values, and a boolean `all_models_within_limit` check. The sidebar model stack renders each model id, runtime, parameter count, and Tiny Titan pass state so the claim is visible during the demo.

Runtime setup is also data-backed. `/api/runtime-setup` lists the app command, llama.cpp launch command, model-specific runtime paths, environment values, and fallbacks so the demo can distinguish real model wiring from deterministic safety nets.

The judge runbook lives at `/api/demo-script`. It keeps the live presentation repeatable by pairing visible actions with API checks for health, model budget, runtime setup, runtime status, image descriptions, reader narration, and speech. Each API check includes copyable curl and PowerShell-friendly `curl.exe` commands for quick reproduction. Deployed demos can set `PUBLIC_BASE_URL` so those commands point at the public Space instead of localhost.

Submission readiness lives at `/api/submission-readiness`. It aggregates the demo-critical checks into one payload: model budget, award evidence, custom frontend assets, runtime setup, runtime status, accessibility audit, image receipts, executable demo API checks, and command base URL checks. POST checks must include sample bodies before readiness passes.

The judge evidence bundle lives at `/api/evidence-bundle`. That endpoint returns the core receipts, including schema version, UTC generation time, `PUBLIC_BASE_URL`, runtime status, and readiness, as formatted JSON.

Image provenance lives in `/api/image-descriptions`. Each article illustration carries the planned FLUX.2 klein generation model id, prompt, seed, asset URL, and fallback status. The same response also reports whether image descriptions came from MiniCPM-V-4.6 or cached fallback alt text.

The Generate route uses `/api/generate-article` to turn a user's topic into a short semantic article. It uses the reader-brain model path for article text when llama.cpp is online, keeps a deterministic fallback draft for demos, and attaches thumbnail provenance from `black-forest-labs/FLUX.2-klein-4B`. When `KLEIN_MODAL_ENDPOINT` is configured, the thumbnail uses live Modal Klein inference. Otherwise, bundled SVG assets are served with explicit fallback runtime metadata.

Accessibility evidence lives at `/api/accessibility-audit`. It records the reader-mode choices that matter most for this prototype: semantic reading order, keyboard navigation, reader cursor state, shortcut safety, live narration, image alt text, transcript review, user-controlled playback, and fallback resilience.

## Reader Mode Behavior

The frontend creates an internal reading queue from semantic nodes: headings, paragraphs, quotes, figures, captions, and controls. It speaks one item at a time, keeps keyboard focus synchronized with the active node, marks that node with `aria-current`, and exposes the current narration through an `aria-live` region.

When screen reader mode turns on, the reader cursor starts at the focused article node or the most visible article node. That makes the feature feel connected to what the user is already reading instead of always jumping back to the top of the page.

Reader shortcuts deliberately ignore form controls. A user can adjust the Kokoro voice, speed slider, and auto-advance checkbox without the page treating those keystrokes as navigation commands.

The reader bar exposes the same shortcut contract through `aria-keyshortcuts`. Repeat and Stop also have visible buttons, which keeps the assistive command model available to pointer users and easy for judges to inspect.

Each narration is also added to a visible transcript log with reader position, runtime, and latency. This gives the demo a second accessible surface: users can review what was spoken, copy the session transcript, or clear it before exploring another part of the article. Clipboard failures are labeled in the live narration region instead of being treated as successful copies.

Keyboard map:

- `Space`: play or pause.
- `N`: next item.
- `P`: previous item.
- `H`: next heading.
- `I`: next image.
- `S`: summarize the current section.
- `R`: repeat current item.
- `Esc`: stop audio.

## Fallback Strategy

Live accessibility demos need dependable behavior. If llama.cpp is not available, the app uses deterministic local narration prefixes. If Kokoro is not installed or cannot load a voice, the app returns a short silent WAV while keeping the transcript visible. If the MiniCPM-V-4.6 endpoint is unavailable, image ids map to cached alt text.

The HTML starts with meaningful fallback `alt` text for each generated image. The app then preloads image descriptions through `/api/image-descriptions`, caches them in the frontend, and writes the descriptions back into each image's `alt` attribute. That keeps the visible article, transcript, and spoken image narration aligned even if the model path is unavailable.

The same payload carries image-generation receipts. In fallback mode, the app is explicit that bundled assets stand in for the FLUX.2 klein runtime instead of presenting static files as live model output.

Kokoro is still the intended model-backed TTS path. For local resilience, the frontend can use the browser speech engine when Kokoro is unavailable, and the session panel labels that as a browser fallback instead of model audio.

Generated speech outputs are capped by a small retention cleanup. That keeps repeated demo sessions from turning the Space output directory into hidden state.

Reader settings are manifest-backed: the app exposes known Kokoro voices and speed bounds through `/api/article-manifest`, then the custom frontend renders the controls and passes the selected voice to `/api/speak`.

Auto-advance is intentionally opt-in. This keeps the default reader mode user-controlled while still supporting a continuous-reading demo path.

Reader navigation interrupts active playback before requesting the next narration. That keeps fast keyboard movement predictable and avoids overlapping speech during demos.

Every model-facing backend path reports `elapsed_ms`. The frontend surfaces the latest end-to-end reader latency and stores per-item timing in the transcript, giving the build report concrete evidence for the small-model responsiveness claim.

The app exposes `/api/award-evidence`, so the live demo can point directly to the hackathon bonus targets it is designed to satisfy.

The app also exposes `/api/submission-readiness`, so the Field Notes story has a single rollup of which submission claims are currently backed by app evidence.

`/api/runtime-status` keeps the demo honest: if llama.cpp, MiniCPM-V-4.6, Kokoro, or Modal Klein is unavailable, the API labels the fallback state instead of silently pretending that every model path is online. The same endpoint reports whether the Modal Klein image worker is online or fallback-ready, so the demo can distinguish live Klein inference from bundled assets.

## MiniCPM-V-4.6 Image Descriptions

The image-description path uses `openbmb/MiniCPM-V-4.6` through an OpenAI-compatible `/v1/chat/completions` endpoint. Set `MINICPM_VISION_BASE_URL` and `MINICPM_VISION_API_KEY` to enable live alt-text generation. `MINICPM_VISION_MODEL` defaults to `openbmb/MiniCPM-V-4.6`, and `MINICPM_VISION_TIMEOUT_SECONDS` controls the request timeout.

The app sends a multimodal chat message with an accessibility-focused prompt and an `image_url`. It asks for one or two concise screen-reader sentences, visible content, meaningful layout or text, and no implementation details.

If the endpoint is missing, unreachable, or returns invalid content, `/api/describe-image` and `/api/image-descriptions` return deterministic cached alt text with fallback runtime metadata. API keys are never included in runtime setup, runtime status, or evidence bundle responses.

## Modal Klein Image Generation

The image generation path runs `black-forest-labs/FLUX.2-klein-4B` through a Modal worker (`modal_workers/klein_image.py`). The worker exposes `POST /generate` for inference and `GET /media/{filename}` for serving generated PNGs from a persistent Modal volume.

Deploy the worker with `modal deploy modal_workers/klein_image.py`, then set `KLEIN_MODAL_ENDPOINT` to the deployed worker URL. The app's `generate_image_core()` calls the Modal endpoint when configured and falls back to bundled SVG assets on missing endpoint, network errors, timeouts, or invalid responses.

`KLEIN_MODAL_TIMEOUT_SECONDS` defaults to 120 seconds, which accommodates warm inference but avoids blocking local demos indefinitely during cold starts.

This design keeps verification stable without requiring Modal credentials or GPU access: the verifier checks fallback behavior, and live Modal deployment is a manual step documented in the README.

## Pre-Demo Validation

`scripts/live_smoke.py` is an opt-in script for confirming live model inference before a demo. It calls `/api/runtime-status`, `/api/describe-image`, and `/api/generate-image`, then reports pass/skip/fail per role. Unconfigured runtimes are skipped, and the script exits non-zero only when a configured live check fails. Secrets are never printed, so the output is safe to include in demo logs or field notes.
