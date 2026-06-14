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
| Vision | `openbmb/MiniCPM-V-2` | 3B | Describes generated article images and handles OCR-like image text. |
| Speech | `hexgrad/Kokoro-82M` | 82M | Fast screen-reader voice with a tiny footprint. |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | 4B | Generates the article illustrations while staying Tiny Titan-safe. |

The app exposes the same budget through `/api/model-budget`, including numeric `params_billion` values, per-model `within_limit` values, and a boolean `all_models_within_limit` check. The session panel renders each model's parameter count and Tiny Titan pass state so the claim is visible during the demo.

Runtime setup is also data-backed. `/api/runtime-setup` lists the app command, llama.cpp launch command, model-specific runtime paths, environment values, and fallbacks. The session panel renders the runtime labels, setup commands, and fallbacks so the demo can distinguish real model wiring from deterministic safety nets.

The judge runbook lives at `/api/demo-script` and is rendered in the session panel with its API evidence checks. It keeps the live presentation repeatable by pairing visible actions with API checks for health, model budget, runtime setup, runtime status, image descriptions, reader narration, and speech. Each API check includes copyable curl and PowerShell-friendly `curl.exe` commands for quick reproduction. Deployed demos can set `PUBLIC_BASE_URL` so those commands point at the public Space instead of localhost.

Submission readiness lives at `/api/submission-readiness`. It aggregates the demo-critical checks into one payload: model budget, award evidence, custom frontend assets, runtime setup, accessibility audit, image receipts, executable demo API checks, and command base URL checks. POST checks must include sample bodies before readiness passes.

The copyable judge evidence bundle lives at `/api/evidence-bundle`. The session panel's Copy Evidence button uses that endpoint to put the core receipts, including `PUBLIC_BASE_URL`, runtime status, and readiness, on the clipboard as formatted JSON.

Image provenance lives in `/api/image-descriptions`. Each article illustration carries the planned FLUX.2 klein model id, prompt, seed, asset URL, and fallback status, and the session panel renders those receipts so the generated-image claim is inspectable.

Accessibility evidence lives at `/api/accessibility-audit`. It records the reader-mode choices that matter most for this prototype: semantic reading order, keyboard navigation, reader cursor state, shortcut safety, live narration, image alt text, transcript review, user-controlled playback, and fallback resilience.

## Reader Mode Behavior

The frontend creates a reading queue from semantic nodes: headings, paragraphs, quotes, figures, captions, and controls. It renders that same queue in the session panel with click-to-read controls, speaks one item at a time, keeps keyboard focus synchronized with the active node, marks that node with `aria-current`, and exposes the current narration through an `aria-live` region.

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

Live accessibility demos need dependable behavior. If llama.cpp is not available, the app uses deterministic local narration prefixes. If Kokoro is not installed or cannot load a voice, the app returns a short silent WAV while keeping the transcript visible. If the VLM integration is unavailable, image ids map to cached alt text.

The HTML starts with meaningful fallback `alt` text for each generated image. The app then preloads image descriptions through `/api/image-descriptions`, caches them in the frontend, and writes the descriptions back into each image's `alt` attribute. That keeps the visible article, transcript, and spoken image narration aligned even if the model path is unavailable.

The same payload carries image-generation receipts. In fallback mode, the app is explicit that bundled assets stand in for the FLUX.2 klein runtime instead of presenting static files as live model output.

Kokoro is still the intended model-backed TTS path. For local resilience, the frontend can use the browser speech engine when Kokoro is unavailable, and the session panel labels that as a browser fallback instead of model audio.

Generated speech outputs are capped by a small retention cleanup. That keeps repeated demo sessions from turning the Space output directory into hidden state.

Reader settings are manifest-backed: the app exposes known Kokoro voices and speed bounds through `/api/article-manifest`, then the custom frontend renders the controls and passes the selected voice to `/api/speak`.

Auto-advance is intentionally opt-in. This keeps the default reader mode user-controlled while still supporting a continuous-reading demo path.

Reader navigation interrupts active playback before requesting the next narration. That keeps fast keyboard movement predictable and avoids overlapping speech during demos.

Every model-facing backend path reports `elapsed_ms`. The frontend surfaces the latest end-to-end reader latency and stores per-item timing in the transcript, giving the build report concrete evidence for the small-model responsiveness claim.

The app exposes `/api/award-evidence` and renders that data in the session panel, so the live demo can point directly to the hackathon bonus targets it is designed to satisfy.

The app also renders `/api/submission-readiness`, so the Field Notes story has a single rollup of which submission claims are currently backed by app evidence.

`/api/runtime-status` keeps the demo honest: if llama.cpp or Kokoro is unavailable, the UI labels the fallback state instead of silently pretending that every model path is online. The session panel also lists the live or fallback state for reader brain, vision, speech, and image generation.
