# Tiny Narrator Submission Packet

## One-line pitch

Tiny Narrator turns an article into a guided screen-reader experience using small, inspectable model paths.

## Short description

Tiny Narrator is a custom Gradio Server app that looks like an article/blog reader until screen-reader mode is switched on. In reader mode, the app builds a semantic reading queue, narrates headings and paragraphs, describes generated images, summarizes the current section, speaks with Kokoro, and keeps a visible transcript of the spoken path with reader position, runtime, and latency.

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
4. Show the session panel: transcript, runtime readiness, latency, judge runbook, award evidence, model budget, and runtime plan.
5. Mention that `/api/demo-script` exposes the same judge runbook and API evidence checks as structured data.

## Evidence endpoints

- `/api/health`: app identity, custom frontend marker, llama.cpp base URL, and model manifest.
- `/api/model-budget`: Tiny Titan parameter proof with numeric `params_billion` values.
- `/api/runtime-setup`: app command, model runtime commands, environment values, and fallback paths.
- `/api/runtime-status`: online or fallback-ready status for each model path, rendered in the session panel.
- `/api/accessibility-audit`: semantic queue, keyboard navigation, reader cursor state, shortcut safety, live narration, alt text, transcript, user control, and fallback evidence.
- `/api/demo-script`: repeatable judge runbook and API checks.
- `/api/image-descriptions`: generated article image descriptions plus prompt, seed, model, asset URL, and fallback status receipts.
- `/api/submission-readiness`: one pass/fail rollup for model budget, award evidence, custom frontend, runtime setup, accessibility, image receipts, and demo API checks.
- `/api/evidence-bundle`: copyable JSON bundle containing the core judge evidence receipts, runtime status, and readiness rollup.

The checks in `/api/demo-script` include copyable curl and PowerShell-friendly `curl.exe` commands generated from `PUBLIC_BASE_URL`, and the POST checks include sample JSON bodies for `/api/reader-brain` and `/api/speak`.

The accessibility audit also documents reader-mode details that matter during judging: the active item is exposed as a reader cursor with focus, visible outline, stable id, and `aria-current`; global shortcuts ignore form controls so voice, speed, and auto-advance settings remain usable while reader mode is active; reader controls expose `aria-keyshortcuts` plus visible Repeat and Stop commands.

The image receipts keep the generated-asset claim inspectable: each article illustration names the planned `black-forest-labs/FLUX.2-klein-4B` path, prompt, seed, and bundled fallback asset.

The submission-readiness panel and API give judges a compact checklist for the whole build, so the live demo can move from individual receipts to an overall readiness view.

The Copy Evidence button pulls `/api/evidence-bundle` and writes the formatted JSON bundle to the clipboard for quick judging notes. Transcript, evidence, and command copy actions label clipboard-unavailable fallback states in the live narration region.

## Reliability notes

The demo remains navigable when local models are unavailable. The reader brain falls back to deterministic narration, generated images start with meaningful HTML alt text, image descriptions fall back to cached alt text, speech falls back to browser speech plus transcript, and generated images fall back to bundled article assets. Fallback states are labeled instead of hidden.
