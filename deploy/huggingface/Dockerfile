# DeepTector public analysis-only image for Hugging Face Spaces (Docker SDK).
# Build context = the folder assembled by prepare-space.ps1 (frontend/, deeptector-backend/, this file).
# Model code + weights are NOT in the image; entrypoint.sh downloads them from MODEL_REPO at startup.

FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Games off (media redistribution rights unverified) + public copy (privacy notice).
ENV NEXT_PUBLIC_ENABLE_GAMES=0 \
    NEXT_PUBLIC_DEPLOYMENT=public \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.11.9-slim-bookworm
# opencv-python needs libGL and glib at import time.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY deeptector-backend/requirements-lock.txt deeptector-backend/requirements-model-lock.txt /tmp/req/
# API env (light) and model env (torch) stay separate, as the backend README requires.
RUN python -m venv /opt/venv-api \
 && /opt/venv-api/bin/pip install --no-cache-dir -r /tmp/req/requirements-lock.txt
# CPU-only torch first so the lock's torch==2.2.2 is already satisfied (avoids ~2 GB of CUDA wheels).
RUN python -m venv /opt/venv-model \
 && /opt/venv-model/bin/pip install --no-cache-dir torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu \
 && /opt/venv-model/bin/pip install --no-cache-dir -r /tmp/req/requirements-model-lock.txt \
 && /opt/venv-model/bin/pip check

# Spaces run containers as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR /home/user/app

COPY --chown=user deeptector-backend/ deeptector-backend/
COPY --from=frontend --chown=user /src/frontend/out frontend/out
COPY --chown=user entrypoint.sh entrypoint.sh

ENV DEEPTECTOR_ENABLE_GAMES=0 \
    DEEPTECTOR_SESSION_RATE_PER_IP_HOUR=30 \
    DEEPTECTOR_SESSION_TTL_HOURS=24 \
    DEEPTECTOR_RETENTION_HOURS=24 \
    DEEPTECTOR_MAX_QUEUED_PER_SESSION=2 \
    DEEPTECTOR_MAX_ACTIVE_GLOBAL=20 \
    DEEPTECTOR_JOB_TIMEOUT_SECONDS=900 \
    OMP_NUM_THREADS=2 \
    PYTHONUNBUFFERED=1

EXPOSE 7860
CMD ["bash", "entrypoint.sh"]
