#!/usr/bin/env bash
# Start DeepTector (analysis only, real model) inside the Space container.
# Required Space settings:
#   Variable MODEL_REPO  e.g. your-team/deeptector-model  (model repo holding infer.py, xai.py, models/**)
#   Secret   HF_TOKEN    read token, only needed when MODEL_REPO is private
set -euo pipefail

export MODEL_DIR="${MODEL_DIR:-/home/user/model/deepfake_detector}"
DATA_DIR="${DATA_DIR:-/tmp/deeptector}"

if [ ! -f "$MODEL_DIR/infer.py" ]; then
  : "${MODEL_REPO:?Set the MODEL_REPO variable in the Space settings}"
  echo "Downloading model from $MODEL_REPO ..."
  /opt/venv-model/bin/python - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id=os.environ["MODEL_REPO"],
    local_dir=os.environ["MODEL_DIR"],
    token=os.environ.get("HF_TOKEN") or None,
    allow_patterns=["infer.py", "xai.py", "models/**"],
)
PY
fi

exec /opt/venv-api/bin/python deeptector-backend/scripts/run_integrated.py \
  --host 0.0.0.0 --port 7860 --mode real --behind-proxy \
  --model-dir "$MODEL_DIR" \
  --worker-python /opt/venv-model/bin/python \
  --data-dir "$DATA_DIR"
