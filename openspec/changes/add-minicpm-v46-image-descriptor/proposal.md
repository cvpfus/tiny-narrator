# Add MiniCPM-V-4.6 Image Descriptor

## Why

Tiny Narrator currently lists `openbmb/MiniCPM-V-2` for the image descriptor role, but the implementation still returns deterministic cached alt text. The project needs real visual description inference for generated article images while keeping the existing screen-reader fallback path reliable.

`openbmb/MiniCPM-V-4.6` is a better fit for the role because it is newer, smaller, Tiny Titan-safe, and supports OpenAI-compatible chat-completions deployments through runtimes such as vLLM, SGLang, llama.cpp, or hosted services.

## What Changes

- Switch the planned vision model from `openbmb/MiniCPM-V-2` to `openbmb/MiniCPM-V-4.6`.
- Add configuration for an OpenAI-compatible `/v1/chat/completions` vision endpoint.
- Call the configured MiniCPM-V-4.6 endpoint from the image-description path when credentials are available.
- Preserve deterministic cached alt-text fallbacks when the endpoint is not configured, unreachable, or returns invalid content.
- Update runtime setup/status, evidence payloads, docs, and verifier expectations to distinguish live MiniCPM-V-4.6 inference from fallback descriptions.

## Capabilities

- `minicpm-v46-image-description`: generate screen-reader-ready image descriptions using MiniCPM-V-4.6 through an OpenAI-compatible chat-completions API.
- `image-description-fallbacks`: retain deterministic alt text for stable local and hackathon demos.
- `vision-runtime-evidence`: expose model id, runtime status, latency, fallback state, and setup instructions through the existing evidence APIs.

## Non-Goals

- Do not change the reader-brain llama.cpp path.
- Do not change Kokoro TTS.
- Do not change the Modal Klein image-generation worker.
- Do not require the MiniCPM endpoint or API key for local verification to pass.
- Do not add a separate evidence UI page.

## Impact

- `app.py` will gain MiniCPM-V-4.6 endpoint configuration and an OpenAI-compatible vision client.
- Existing `/api/describe-image` and `/api/image-descriptions` responses will keep their current shape but may return live MiniCPM runtime metadata.
- README, SUBMISSION, and FIELD_NOTES will describe MiniCPM-V-4.6 setup and fallback behavior.
- `scripts/verify.py` will cover fallback behavior and mocked live MiniCPM responses without making network calls.
