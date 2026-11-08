"""Shared helpers for the GAN fine-tuning experiment.

The service's model folder is only READ (infer.py for the architecture, the original
checkpoints as the starting point). Nothing in Service/ or the model folder is modified.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parents[1]  # ...\Service (this repo)
WORKSPACE = SERVICE.parent  # folder that also holds the deepGame checkout
MODEL_DIR = SERVICE / "AI-Generated-Media-Detection" / "deepfake_detector"
DATA = HERE / "data"
CKPT = HERE / "checkpoints"
SEED = 2026

sys.path.insert(0, str(MODEL_DIR))
import infer  # noqa: E402  (architecture + normalization constants, read-only)

TRANSFORM = transforms.Compose(
    [transforms.Resize((224, 224)), transforms.ToTensor(), transforms.Normalize(infer.IMG_MEAN, infer.IMG_STD)]
)

_mtcnn = None


def face_crop(im: Image.Image) -> Image.Image | None:
    """Same crop rule as the service (most confident face, +10% height padding, 224x224)."""
    global _mtcnn
    if _mtcnn is None:
        from facenet_pytorch import MTCNN

        _mtcnn = MTCNN(keep_all=False, device="cpu")
    boxes, probs = _mtcnn.detect(im)
    if boxes is None or not len(boxes):
        return None
    best = int(np.argmax(probs))
    x1, y1, x2, y2 = map(float, boxes[best])
    pad = 0.1 * (y2 - y1)
    box = (max(0, x1), max(0, y1 - pad), min(im.width, x2), min(im.height, y2 + pad))
    return im.crop(box).resize((224, 224))


def load_classifier(path: Path) -> torch.nn.Module:
    checkpoint = torch.load(path, map_location="cpu")
    model = infer.FaceClassifier(checkpoint.get("backbone", "convnext_tiny.fb_in22k_ft_in1k"))
    model.load_state_dict({k: (v.float() if torch.is_floating_point(v) else v) for k, v in checkpoint["state_dict"].items()})
    return model.eval()


def original_checkpoints() -> list[Path]:
    return sorted((MODEL_DIR / "models" / "spatial").glob("*.pt"))


@torch.no_grad()
def score_images(models: list[torch.nn.Module], images: list[Image.Image], batch: int = 32) -> np.ndarray:
    """Mean sigmoid over the given models (the service averages its 5 folds the same way)."""
    out = []
    for start in range(0, len(images), batch):
        x = torch.stack([TRANSFORM(im) for im in images[start:start + batch]])
        out.append(np.mean([torch.sigmoid(m(x)).squeeze(1).numpy() for m in models], axis=0))
    return np.concatenate(out) if out else np.zeros(0)


def list_split(split: str) -> tuple[list[Path], np.ndarray]:
    paths, labels = [], []
    for label, name in ((0, "real"), (1, "fake")):
        found = sorted((DATA / split / name).glob("*.png"))
        paths += found
        labels += [label] * len(found)
    return paths, np.array(labels)
