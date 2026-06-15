"""Modal worker for black-forest-labs/FLUX.2-klein-4B image generation.

Deploy:
    modal deploy modal_workers/klein_image.py

The deployed ASGI app exposes one base URL with:
    POST /generate - accepts {"prompt": str, "seed": int | None}
    GET  /health - reports worker readiness
    GET  /media/{filename} - serves generated PNG files

Tiny Narrator's app.py calls these routes through KLEIN_MODAL_ENDPOINT.
"""

import io
import os
from pathlib import Path
from uuid import uuid4

import modal


APP_NAME = "tiny-narrator-klein"
CACHE_DIR = Path("/cache")
MEDIA_DIR = Path("/outputs")
IMAGE_MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"

app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name("tiny-narrator-klein-cache", create_if_missing=True)
output_volume = modal.Volume.from_name("tiny-narrator-klein-outputs", create_if_missing=True)

klein_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install(
        "torch==2.9.1",
        index_url="https://download.pytorch.org/whl/cu128",
    )
    .pip_install(
        "accelerate==1.12.0",
        "diffusers @ git+https://github.com/huggingface/diffusers.git",
        "fastapi[standard]==0.136.3",
        "huggingface-hub[hf-transfer]==0.36.0",
        "pillow==12.2.0",
        "safetensors>=0.8.0rc0",
        "sentencepiece==0.2.1",
        "transformers==4.57.3",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


def _secret_names() -> list[modal.Secret]:
    """Return the fixed secrets used by Modal deployments.

    Modal requires dependencies to be identical between local deploy-time import
    and remote container import. Keep this list static; do not derive it from
    environment variables.
    """

    return [modal.Secret.from_name("tiny-narrator-klein-token")]


async def _media_file_response(filename: str):
    from fastapi import HTTPException
    from fastapi.responses import Response

    path = MEDIA_DIR / filename
    if not path.exists() or not path.is_file():
        try:
            await output_volume.reload.aio()
        except RuntimeError as exc:
            if not path.exists() or not path.is_file():
                raise HTTPException(status_code=503, detail=f"Media volume reload failed: {exc}") from exc

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Media file not found: {filename}")

    content_type = "image/png"
    if filename.endswith(".webp"):
        content_type = "image/webp"
    elif filename.endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    return Response(content=path.read_bytes(), media_type=content_type)


@app.cls(
    image=klein_image,
    gpu=os.getenv("KLEIN_MODAL_GPU", "A10G"),
    volumes={str(CACHE_DIR): model_cache, str(MEDIA_DIR): output_volume},
    secrets=_secret_names(),
    timeout=900,
    scaledown_window=300,
    max_containers=1,
)
class KleinImageModel:
    @modal.enter()
    def load(self) -> None:
        import torch
        from diffusers import Flux2KleinPipeline

        self.model_id = os.environ.get("KLEIN_IMAGE_MODEL_ID", IMAGE_MODEL_ID)
        token = os.environ.get("HF_TOKEN")
        self.pipe = Flux2KleinPipeline.from_pretrained(
            self.model_id,
            cache_dir=str(CACHE_DIR / "huggingface"),
            torch_dtype=torch.bfloat16,
            token=token,
        )
        self.pipe.to("cuda")

    @modal.method()
    def generate(self, prompt: str, seed: int | None = None) -> dict:
        import torch

        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)

        result = self.pipe(
            prompt=prompt,
            num_inference_steps=int(os.environ.get("KLEIN_MODAL_STEPS", "4")),
            guidance_scale=float(os.environ.get("KLEIN_MODAL_GUIDANCE", "1.0")),
            generator=generator,
        )
        image = result.images[0]

        filename = f"klein-{uuid4().hex}.png"
        output_path = MEDIA_DIR / filename
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        output_path.write_bytes(buffer.getvalue())
        output_volume.commit()

        return {
            "filename": filename,
            "model": self.model_id,
        }


@app.function(
    image=klein_image,
    volumes={str(MEDIA_DIR): output_volume},
    secrets=_secret_names(),
    timeout=300,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(label="tiny-narrator-klein")
def klein_api():
    from fastapi import FastAPI, HTTPException, Request

    import time

    api = FastAPI(title="Tiny Narrator Klein Worker")
    model = KleinImageModel()

    def _check_token(request: Request) -> None:
        """Reject the request if a token is configured but not provided or mismatched."""
        expected = os.getenv("KLEIN_MODAL_TOKEN", "")
        if not expected:
            return
        auth_header = request.headers.get("authorization", "")
        token_header = request.headers.get("x-tiny-narrator-token", "")
        provided = ""
        if auth_header.startswith("Bearer "):
            provided = auth_header[len("Bearer "):]
        elif token_header:
            provided = token_header
        if provided != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    @api.get("/health")
    async def health(request: Request) -> dict:
        _check_token(request)
        return {
            "ok": True,
            "model": IMAGE_MODEL_ID,
            "runtime": "modal-klein",
        }

    @api.get("/media/{filename}")
    async def media(filename: str):
        return await _media_file_response(filename)

    @api.post("/generate")
    async def generate(request: Request) -> dict:
        _check_token(request)
        start = time.perf_counter()
        body = await request.json()
        prompt = str(body.get("prompt") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")

        seed = body.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="seed must be an integer") from exc

        result = await model.generate.remote.aio(prompt, seed)
        model_id = result.get("model") or IMAGE_MODEL_ID
        if model_id != IMAGE_MODEL_ID:
            raise HTTPException(status_code=500, detail=f"unexpected model: {model_id}")

        filename = result["filename"]
        image_url = str(request.url_for("media", filename=filename))
        return {
            "ok": True,
            "runtime": "modal-klein",
            "model": IMAGE_MODEL_ID,
            "image_url": image_url,
            "prompt": prompt,
            "seed": seed,
            "elapsed_ms": round((time.perf_counter() - start) * 1000),
        }

    return api
