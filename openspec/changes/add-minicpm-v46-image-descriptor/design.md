# Design: MiniCPM-V-4.6 Image Descriptor

## Overview

Tiny Narrator will keep the existing image-description APIs but upgrade the vision role from cached-only placeholder behavior to a live MiniCPM-V-4.6 path when configured.

The backend will call an OpenAI-compatible `/v1/chat/completions` endpoint. The user will provide the base URL and API key. Local development and verification will continue to pass without credentials by using deterministic fallbacks.

## Configuration

Add environment variables:

| Variable | Purpose |
| --- | --- |
| `MINICPM_VISION_BASE_URL` | Base URL for the OpenAI-compatible MiniCPM-V-4.6 server. Accept either the server root or a URL ending in `/v1`; app code should normalize to `/v1/chat/completions`. |
| `MINICPM_VISION_API_KEY` | Bearer token for the MiniCPM vision endpoint. |
| `MINICPM_VISION_MODEL` | Optional model id, default `openbmb/MiniCPM-V-4.6`. |
| `MINICPM_VISION_TIMEOUT_SECONDS` | Request timeout, default short enough for UI responsiveness but long enough for warm inference. |

The API key must never be exposed in runtime setup/status payloads. Status may report whether a key is configured.

## Request Shape

The app should send a multimodal chat-completions request:

```json
{
  "model": "openbmb/MiniCPM-V-4.6",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe this image for a screen reader..."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://public-base-url/static/generated/model-map.svg"
          }
        }
      ]
    }
  ],
  "temperature": 0.1,
  "max_tokens": 160
}
```

The prompt should ask for concise accessibility alt text:

- one or two sentences
- no implementation details
- describe visible content, layout, text, and purpose when relevant
- avoid guessing hidden intent
- return plain text only

## Image URL Resolution

For known article images, use the `asset_url` from `ARTICLE_IMAGES`. If it is relative, prefix `PUBLIC_BASE_URL`.

For direct `POST /api/describe-image` calls:

- continue supporting `image_id`, `caption`, and `prompt`
- optionally add `image_url` to the request schema so future callers can describe external or generated images
- if no usable image URL is available, use fallback text instead of calling the vision endpoint

## Response Handling

Parse the first chat completion message:

```json
choices[0].message.content
```

Validate that the content is a non-empty string. Normalize whitespace and limit length for safe UI/transcript use. Return the existing response shape with live metadata:

```json
{
  "ok": true,
  "runtime": "minicpm-v4.6",
  "model": "openbmb/MiniCPM-V-4.6",
  "alt_text": "...",
  "elapsed_ms": 1234
}
```

If the endpoint is missing, credentials are missing, the image URL cannot be resolved, the request fails, or the response is invalid, return deterministic fallback alt text with:

```json
{
  "runtime": "fallback",
  "model": "openbmb/MiniCPM-V-4.6",
  "warning": "MiniCPM vision unavailable: ..."
}
```

When no live call was attempted because configuration is absent, warning can be omitted to keep local demos quiet.

## Runtime Setup And Status

`runtime_setup_core()` should document:

- the expected OpenAI-compatible serving path
- environment variables
- example commands for compatible runtimes, such as `vllm serve openbmb/MiniCPM-V-4.6` or `llama-server` with a MiniCPM-V-4.6 GGUF
- fallback behavior

`_runtime_status_core()` should:

- report `vision.status = "fallback-ready"` when not configured
- report `vision.status = "online"` only when both base URL and API key are configured and a lightweight readiness check succeeds
- avoid sending images in the status check; use `/models` if available, or a minimal chat-completions check only if necessary
- never expose `MINICPM_VISION_API_KEY`

## Frontend Behavior

No major frontend changes are required. The existing reader route already preloads `/api/image-descriptions`, writes returned alt text into image attributes, and uses image descriptions for screen-reader narration.

If live MiniCPM inference is slow, the frontend should still remain usable because the backend returns fallback descriptions on timeout.

## Testing Strategy

Verification should not need network or credentials. Add mocked tests for:

- no configuration returns fallback MiniCPM-V-4.6 metadata
- successful OpenAI-compatible response returns live alt text
- invalid response falls back with a warning
- failed request falls back with a warning
- runtime setup documents MiniCPM-V-4.6 configuration
- runtime status does not expose API keys
- existing `/api/image-descriptions` shape remains stable

Manual testing can cover a real configured endpoint after the user provides base URL and API key.
