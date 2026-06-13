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

## Reader Mode Behavior

The frontend creates a reading queue from semantic nodes: headings, paragraphs, quotes, figures, captions, and controls. It speaks one item at a time, keeps keyboard focus synchronized with the active node, and exposes the current narration through an `aria-live` region.

Each narration is also added to a visible transcript log. This gives the demo a second accessible surface: users can review what was spoken, copy the session transcript, or clear it before exploring another part of the article.

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

The app preloads image descriptions through `/api/image-descriptions`, caches them in the frontend, and writes the descriptions back into each image's `alt` attribute. That keeps the visible article, transcript, and spoken image narration aligned.

Kokoro is still the intended model-backed TTS path. For local resilience, the frontend can use the browser speech engine when Kokoro is unavailable, and the session panel labels that as a browser fallback instead of model audio.

Reader settings are manifest-backed: the app exposes known Kokoro voices and speed bounds through `/api/article-manifest`, then the custom frontend renders the controls and passes the selected voice to `/api/speak`.

Auto-advance is intentionally opt-in. This keeps the default reader mode user-controlled while still supporting a continuous-reading demo path.

Every model-facing backend path reports `elapsed_ms`. The frontend surfaces the latest end-to-end reader latency and stores per-item timing in the transcript, giving the build report concrete evidence for the small-model responsiveness claim.

The app exposes `/api/award-evidence` and renders that data in the session panel, so the live demo can point directly to the hackathon bonus targets it is designed to satisfy.

`/api/runtime-status` keeps the demo honest: if llama.cpp or Kokoro is unavailable, the UI labels the fallback state instead of silently pretending that every model path is online.
