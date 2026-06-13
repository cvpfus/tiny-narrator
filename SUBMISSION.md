# Tiny Narrator Submission Packet

## One-line pitch

Tiny Narrator turns an article into a guided screen-reader experience using small, inspectable model paths.

## Short description

Tiny Narrator is a custom Gradio Server app that looks like an article/blog reader until screen-reader mode is switched on. In reader mode, the app builds a semantic reading queue, narrates headings and paragraphs, describes generated images, summarizes the current section, speaks with Kokoro, and keeps a visible transcript of the spoken path.

The prototype is designed for a live hackathon demo: every model-facing path has a deterministic fallback, runtime readiness is labeled in the UI, and the repo exposes machine-readable evidence for model size, setup, demo flow, and accessibility behavior.

## Award targets

- Tiny Titan: `/api/model-budget` reports every model role at or below 4B parameters.
- Llama Champion: the reader-brain path targets a GGUF model through a llama.cpp OpenAI-compatible endpoint.
- Off-Brand: the visible UI is custom HTML, CSS, and JavaScript served by `gr.Server`.
- Field Notes: `FIELD_NOTES.md` and the evidence APIs document model choices, fallbacks, latency, and accessibility decisions.

## Model stack

| Role | Model | Size | Runtime |
| --- | --- | ---: | --- |
| Reader brain | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 3.97B | `llama.cpp` |
| Image understanding | `openbmb/MiniCPM-V-2` | 3B | Python integration planned |
| Speech | `hexgrad/Kokoro-82M` | 82M | Python |
| Image generation | `black-forest-labs/FLUX.2-klein-4B` | 4B | Python integration planned |

## Demo flow

1. Open the article and show that the app is a custom article interface, not a stock chatbot page.
2. Turn on screen-reader mode and press `Space` or `Next` to narrate the first semantic node.
3. Use `Heading`, `Image`, and `Summary` to navigate by article meaning instead of by raw page order.
4. Show the session panel: transcript, runtime readiness, latency, demo checklist, model budget, and runtime plan.
5. Mention that `/api/demo-script` exposes the same judge runbook as structured data.

## Evidence endpoints

- `/api/health`: app identity, custom frontend marker, llama.cpp base URL, and model manifest.
- `/api/model-budget`: Tiny Titan parameter proof with numeric `params_billion` values.
- `/api/runtime-setup`: app command, model runtime commands, environment values, and fallback paths.
- `/api/runtime-status`: online or fallback-ready status for model paths.
- `/api/accessibility-audit`: semantic queue, keyboard navigation, live narration, alt text, transcript, user control, and fallback evidence.
- `/api/demo-script`: repeatable judge runbook and API checks.
- `/api/image-descriptions`: generated article image descriptions for reader mode.

The POST checks in `/api/demo-script` include sample JSON bodies for `/api/reader-brain` and `/api/speak`.

## Reliability notes

The demo remains navigable when local models are unavailable. The reader brain falls back to deterministic narration, image descriptions fall back to cached alt text, speech falls back to browser speech plus transcript, and generated images fall back to bundled article assets. Fallback states are labeled instead of hidden.
