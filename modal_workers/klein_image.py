"""Modal worker for black-forest-labs/FLUX.2-klein-4B image generation.

Deploy:
    modal deploy modal_workers/klein_image.py

The deployed ASGI app exposes one base URL with:
    POST /generate - accepts {"prompt": str, "seed": int | None}
    GET  /health - reports worker readiness
    GET  /media/{filename} - serves generated PNG files

Tiny Narrator's app.py calls these routes through KLEIN_MODAL_ENDPOINT.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from uuid import uuid4

import modal

app = modal.App("tiny-narrator-klein")

output_volume = modal.Volume.from_name("tiny-narrator-klein-outputs", create_if_missing=True)
MEDIA_DIR = Path("/outputs")

IMAGE_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"
_PIPELINE = None

klein_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "huggingface-hub[hf-transfer]>=0.36.0",
        "pillow",
        "torch",
        "transformers",
        "git+https://github.com/huggingface/diffusers.git",
        "safetensors>=0.8.0rc0",
        "accelerate",
        "sentencepiece",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


def _get_pipeline():
    """Load the Klein pipeline once per warm ASGI container."""
    global _PIPELINE
    if _PIPELINE is None:
        import torch
        from diffusers import FluxPipeline

        pipe = FluxPipeline.from_pretrained(
            IMAGE_MODEL_ID,
            torch_dtype=torch.bfloat16,
        )
        pipe.to("cuda")
        _PIPELINE = pipe
    return _PIPELINE


@app.function(
    image=klein_image,
    gpu="A10G",
    timeout=900,
    container_idle_timeout=300,
    volumes={str(MEDIA_DIR): output_volume},
)
@modal.asgi_app()
def klein_api():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import Response
    import torch

    api = FastAPI(title="Tiny Narrator Klein Worker")

    @api.get("/health")
    async def health() -> dict:
        return {
            "ok": True,
            "model": IMAGE_MODEL_ID,
            "runtime": "modal-klein",
        }

    @api.post("/generate")
    async def generate(request: dict) -> dict:
        start = time.perf_counter()
        prompt = str(request.get("prompt") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")

        seed = request.get("seed")
        generator = None
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="seed must be an integer") from exc
            generator = torch.Generator(device="cuda").manual_seed(seed)

        result = _get_pipeline()(
            prompt=prompt,
            num_inference_steps=28,
            guidance_scale=3.5,
            generator=generator,
        )
        image = result.images[0]

        filename = f"klein-{uuid4().hex}.png"
        output_path = MEDIA_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        output_path.write_bytes(buffer.getvalue())
        output_volume.commit()

        return {
            "ok": True,
            "runtime": "modal-klein",
            "model": IMAGE_MODEL_ID,
            "image_url": f"/media/{filename}",
            "prompt": prompt,
            "seed": seed,
            "elapsed_ms": round((time.perf_counter() - start) * 1000),
        }

    @api.get("/media/{filename}")
    async def media(filename: str):
        output_volume.reload()
        media_path = MEDIA_DIR / filename
        if not media_path.exists() or not media_path.is_file():
            raise HTTPException(status_code=404, detail=f"Media file not found: {filename}")

        data = media_path.read_bytes()
        content_type = "image/png"
        if filename.endswith(".webp"):
            content_type = "image/webp"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            content_type = "image/jpeg"

        return Response(content=data, media_type=content_type)

    return api
