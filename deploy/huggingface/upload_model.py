"""Upload the trusted model code + weights to a Hugging Face *model* repo (private by default).

Run with the model venv (it has huggingface_hub):
  deeptector-backend\\.venv-model\\Scripts\\python.exe deploy\\huggingface\\upload_model.py ^
      --repo your-team/deeptector-model --model-dir AI-Generated-Media-Detection\\deepfake_detector

Authentication: set HF_TOKEN (write token) or run `hf auth login` first.
Only infer.py, xai.py and models/** are uploaded (what the worker loads).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

PATTERNS = ["infer.py", "xai.py", "models/**"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="namespace/name of the model repo")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--public", action="store_true", help="create the repo as public (default private)")
    args = parser.parse_args()

    root = args.model_dir.resolve()
    spatial = sorted((root / "models" / "spatial").glob("*.pt"))
    temporal = sorted((root / "models" / "temporal").glob("*.pt"))
    required = [root / "infer.py", root / "xai.py", root / "models" / "temporal" / "calibration.json"]
    if len(spatial) != 5 or len(temporal) != 6 or not all(path.is_file() for path in required):
        raise SystemExit("model dir must contain infer.py, xai.py, calibration.json and 5+6 checkpoints")

    api = HfApi()
    api.create_repo(args.repo, repo_type="model", private=not args.public, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo,
        repo_type="model",
        folder_path=str(root),
        allow_patterns=PATTERNS,
        commit_message="Upload DeepTector model code and checkpoints",
    )
    print(f"uploaded {len(spatial) + len(temporal)} checkpoints to https://huggingface.co/{args.repo}")


if __name__ == "__main__":
    main()
