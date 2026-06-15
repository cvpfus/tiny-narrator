# Tiny Narrator - Hugging Face Spaces Docker deployment (free CPU)
# Serves the custom Gradio/FastAPI app. GPU model runtimes are external.

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user

WORKDIR /home/user/app

COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user app.py app.py
COPY --chown=user start.sh start.sh
COPY --chown=user static/ static/
COPY --chown=user modal_workers/ modal_workers/
COPY --chown=user scripts/ scripts/
COPY --chown=user README.md README.md
COPY --chown=user SUBMISSION.md SUBMISSION.md
COPY --chown=user FIELD_NOTES.md FIELD_NOTES.md
COPY --chown=user LICENSE LICENSE

RUN mkdir -p /home/user/app/outputs && \
    chown user:user /home/user/app/outputs && \
    chmod +x /home/user/app/start.sh

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    GRADIO_SHARE=false \
    LLAMA_CPP_BASE_URL= \
    LLAMA_CPP_MODEL=narrator-brain

EXPOSE 7860

CMD ["/home/user/app/start.sh"]
