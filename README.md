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

Open the local URL printed by Gradio. The custom frontend calls `/api/reader-brain`, `/api/image-descriptions`, `/api/describe-image`, `/api/speak`, and `/api/generate-image`.

Useful environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLAMA_CPP_BASE_URL` | `http://localhost:8080/v1` | OpenAI-compatible llama.cpp server URL |
| `LLAMA_CPP_MODEL` | `narrator-brain` | Alias passed to llama.cpp |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Bind address for local or Space runtime |
| `GRADIO_SERVER_PORT` / `PORT` | `7860` | App port |

## Verification

```powershell
python scripts/verify.py
```

The verifier checks syntax, static assets, deterministic fallback model paths, and generated speech file behavior.

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

The session panel keeps a transcript of recent narration with copy and clear controls, making the spoken path inspectable during demos and useful for the Field Notes write-up.

Image descriptions are preloaded into a local cache and written into the page's real `img alt` attributes. When the planned MiniCPM-V runtime is unavailable, deterministic alt-text fallbacks keep the screen-reader path usable.

Kokoro remains the planned tiny-model TTS path. During local demos, if the server-side Kokoro call falls back, the browser speech engine can read the same transcript so screen-reader mode still produces audible feedback.

The reader bar exposes Kokoro voice selection and speaking speed controls. Defaults come from `/api/article-manifest` so the UI, docs, and backend stay aligned.

Auto-advance is available as an opt-in reader control. It stays off by default so users keep manual control unless they choose continuous reading.

Reader-brain, image-description, speech, and image-generation responses include `elapsed_ms`. The session panel and transcript show recent latency so the Field Notes can discuss responsiveness with concrete numbers.

The session panel also renders a manifest-backed demo checklist for Tiny Titan, Llama Champion, Off-Brand, and Field Notes evidence.

`/api/runtime-status` performs a short readiness check for llama.cpp and local speech dependencies, then reports which fallback paths are ready for a live demo.
