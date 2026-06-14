---
title: Tiny Narrator
emoji: 🔊
colorFrom: teal
colorTo: yellow
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
pinned: false
license: apache-2.0
---

# Tiny Narrator

Tiny Narrator is a Build Small Hackathon prototype: a custom Gradio Server article app that can switch into a guided screen-reader mode.

For the hackathon form, see [SUBMISSION.md](SUBMISSION.md).

## Award Strategy

- **Tiny Titan:** every planned model is at or below 4B parameters.
- **Llama Champion:** the reader-brain layer calls a GGUF model through `llama.cpp`.
- **Off-Brand:** the visible UI is custom HTML, CSS, and JavaScript served by `gr.Server`.
- **Field Notes:** the repo documents model sizes, runtime choices, fallbacks, and accessibility decisions.

## Recommended Models

| Role | Model | Params | Runtime |
| --- | ---: | ---: | --- |
| Reader brain | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 3.97B | `llama.cpp` |
| Image understanding | `openbmb/MiniCPM-V-2` | 3B | Python integration planned |
| Text to speech | `hexgrad/Kokoro-82M` | 82M | Python |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | 4B | Python integration planned |

## Run Locally

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the llama.cpp reader-brain server:

```powershell
llama-server -hf nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M --alias narrator-brain --port 8080 --host 0.0.0.0
```

Start the app:

```powershell
python app.py
```

Open the local URL printed by Gradio. The custom frontend calls `/api/reader-brain`, `/api/image-descriptions`, `/api/describe-image`, `/api/speak`, `/api/generate-image`, `/api/model-budget`, `/api/runtime-setup`, `/api/demo-script`, `/api/accessibility-audit`, `/api/submission-readiness`, and `/api/evidence-bundle`.

Useful environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLAMA_CPP_BASE_URL` | `http://localhost:8080/v1` | OpenAI-compatible llama.cpp server URL |
| `LLAMA_CPP_MODEL` | `narrator-brain` | Alias passed to llama.cpp |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Bind address for local or Space runtime |
| `GRADIO_SERVER_PORT` / `PORT` | `7860` | App port |
| `PUBLIC_BASE_URL` | `http://localhost:7860` | Base URL used in generated judge API commands |

## Verification

```powershell
python scripts/verify.py
```

The verifier checks syntax, static assets, Space metadata consistency, deterministic fallback model paths, and generated speech file behavior.

`/api/model-budget` exposes numeric parameter counts for every model role and reports whether the full stack stays within the 4B Tiny Titan limit.

`/api/runtime-setup` exposes the commands, environment values, and fallback paths used for the model stack so the demo can be reproduced from the same data the UI displays.

`/api/demo-script` exposes a compact judge runbook with the visible actions, API checks, sample bodies, curl commands, and PowerShell-friendly `curl.exe` commands that prove the submission claims. The commands use `PUBLIC_BASE_URL`, and the session panel renders those actions and API evidence checks as the Judge Runbook with per-command copy buttons.

`/api/accessibility-audit` exposes structured evidence for semantic reading order, keyboard navigation, reader cursor state, shortcut safety, live narration, image alt text, transcript review, user-controlled playback, and fallback resilience.

`/api/image-descriptions` includes image-generation provenance for every article illustration: the planned FLUX.2 klein model, prompt, seed, bundled asset URL, and fallback-ready status.

`/api/submission-readiness` aggregates the judging receipts into one pass/fail payload covering model budget, award evidence, custom frontend assets, runtime setup, accessibility, image receipts, demo API checks, and command base URL checks.

The readiness rollup only passes the demo API check when POST entries include executable sample bodies.

`/api/evidence-bundle` returns a copyable JSON bundle of the main judging receipts, including `PUBLIC_BASE_URL`, runtime status, and the submission readiness rollup. The Submission Readiness panel includes a Copy Evidence button that writes this bundle to the clipboard.

## Screen Reader Mode

The frontend builds a reading queue from semantic article nodes. When screen-reader mode is on:

- `Space` plays or pauses.
- `N` moves to the next item.
- `P` moves to the previous item.
- `H` moves to the next heading.
- `I` moves to the next image.
- `S` summarizes the current section.
- `R` repeats the current item.
- `Esc` stops the current audio.

Each readable node is sent to the reader brain for concise narration, then Kokoro generates speech. If a model is unavailable, the app uses deterministic fallbacks so the demo remains navigable.

When screen-reader mode turns on, it selects the focused or most visible article item, assigns stable reader-node ids, and marks the active item with `aria-current`. Clicking a readable article item while the mode is on reads that item directly.

Global reader shortcuts ignore buttons, links, selects, and inputs so the voice, speed, and auto-advance controls remain usable while reader mode is active.

Reader buttons expose `aria-keyshortcuts`, and the Repeat and Stop shortcuts are mirrored by visible controls so pointer and keyboard users share the same command surface.

The session panel keeps a transcript of recent narration with copy and clear controls, making the spoken path inspectable during demos and useful for the Field Notes write-up.

Image descriptions are preloaded into a local cache and written into the page's real `img alt` attributes. When the planned MiniCPM-V runtime is unavailable, deterministic alt-text fallbacks keep the screen-reader path usable.

The session panel also renders image receipts from `/api/image-descriptions`, so judges can inspect the prompt, seed, planned <=4B image model, and fallback status behind each bundled article illustration.

Kokoro remains the planned tiny-model TTS path. During local demos, if the server-side Kokoro call falls back, the browser speech engine can read the same transcript so screen-reader mode still produces audible feedback.

Generated speech files are pruned automatically so repeated demos do not grow the Space's `outputs` directory without bound.

The reader bar exposes Kokoro voice selection and speaking speed controls. Defaults come from `/api/article-manifest` so the UI, docs, and backend stay aligned.

Auto-advance is available as an opt-in reader control. It stays off by default so users keep manual control unless they choose continuous reading.

Navigation commands interrupt current speech before starting the next request, matching the expectation that a screen reader responds immediately when the user moves.

Reader-brain, image-description, speech, and image-generation responses include `elapsed_ms`. The session panel and transcript show recent latency so the Field Notes can discuss responsiveness with concrete numbers.

The session panel renders the judge runbook and API evidence checks from `/api/demo-script`, plus manifest-backed evidence for Tiny Titan, Llama Champion, Off-Brand, and Field Notes. A model-budget panel reads `/api/model-budget` so judges can see each role's parameter count in the live app.

A submission-readiness panel reads `/api/submission-readiness`, giving judges one compact rollup of the claims the live app can prove.

The Copy Evidence button reads `/api/evidence-bundle` and copies the core judge receipts as formatted JSON for quick review or submission notes.

A runtime-plan panel reads `/api/runtime-setup` and summarizes each model path's runtime plus fallback, keeping the live demo honest about what is online and what is deterministic.

`/api/runtime-status` performs a short readiness check for llama.cpp and local speech dependencies, then reports which fallback paths are ready for a live demo.
