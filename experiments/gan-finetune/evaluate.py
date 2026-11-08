"""Evaluate spatial models on (1) StyleGAN test faces and (2) the FF++-style regression clips.

  python evaluate.py --name original5                     # service's 5-fold ensemble
  python evaluate.py --name original-fold1 --fold 1        # the single model we fine-tune
  python evaluate.py --name finetuned --ckpt checkpoints/convnext_fold1_gan.pt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

from common import DATA, HERE, list_split, load_classifier, original_checkpoints, score_images


def service_verdict(spatial: float, temporal: float) -> int:
    """Same rule as Service/deeptector-backend/app/policy.py (video)."""
    fused = (spatial + temporal) / 2
    return int(fused >= 0.5 or max(spatial, temporal) >= 0.85)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--ckpt", type=Path, action="append", help="checkpoint(s) to average; default = original 5 folds")
    parser.add_argument("--fold", type=int, help="use only this original fold (1-5)")
    args = parser.parse_args()
    paths = args.ckpt or original_checkpoints()
    if args.fold:
        paths = [original_checkpoints()[args.fold - 1]]
    models = [load_classifier(p) for p in paths]
    report: dict = {"name": args.name, "checkpoints": [str(p) for p in paths]}

    files, labels = list_split("test")
    scores = score_images(models, [Image.open(p).convert("RGB") for p in files])
    pred = (scores >= 0.5).astype(int)
    report["stylegan_test"] = {
        "n": int(len(labels)),
        "accuracy": float((pred == labels).mean()),
        "auc": float(roc_auc_score(labels, scores)),
        "real_correct": float((pred[labels == 0] == 0).mean()),
        "fake_detected": float((pred[labels == 1] == 1).mean()),
    }

    meta = json.loads((DATA / "ffpp_eval" / "meta.json").read_text(encoding="utf-8"))
    clip_scores, clip_labels, dual = [], [], []
    for clip in meta:
        faces = [Image.open(p).convert("RGB") for p in sorted((DATA / "ffpp_eval" / clip["id"]).glob("*.png"))]
        if not faces:
            continue
        s = float(score_images(models, faces).mean())
        clip_scores.append(s)
        clip_labels.append(clip["label"])
        if clip["temporal"] is not None:
            dual.append(service_verdict(s, clip["temporal"]) == clip["label"])
    clip_scores, clip_labels = np.array(clip_scores), np.array(clip_labels)
    clip_pred = (clip_scores >= 0.5).astype(int)
    report["ffpp_clips"] = {
        "n": int(len(clip_labels)),
        "spatial_accuracy": float((clip_pred == clip_labels).mean()),
        "spatial_auc": float(roc_auc_score(clip_labels, clip_scores)),
        "real_correct": float((clip_pred[clip_labels == 0] == 0).mean()),
        "fake_detected": float((clip_pred[clip_labels == 1] == 1).mean()),
        "service_dual_branch_accuracy": float(np.mean(dual)) if dual else None,
    }
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / f"{args.name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    g, f = report["stylegan_test"], report["ffpp_clips"]
    print(f"[{args.name}] StyleGAN test  acc {g['accuracy']:.3f}  AUC {g['auc']:.3f}  real-ok {g['real_correct']:.3f}  fake-caught {g['fake_detected']:.3f}")
    print(f"[{args.name}] FF++ clips     acc {f['spatial_accuracy']:.3f}  AUC {f['spatial_auc']:.3f}  real-ok {f['real_correct']:.3f}  fake-caught {f['fake_detected']:.3f}  service(dual) {f['service_dual_branch_accuracy']}")


if __name__ == "__main__":
    main()
