"""Download a small slice of 140k Real and Fake Faces and pre-crop faces like the service does.

Uses ONE train shard and ONE test shard (~770 MB) and samples a balanced subset.
Real = FFHQ photos, fake = StyleGAN. Research/internal use only; do not redistribute.
"""
from __future__ import annotations

import argparse
import io
import json
import random

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from PIL import Image

from common import DATA, HERE, SEED, face_crop

REPO = "TheKernel01/140k-Real-and-Fake-Faces"
SHARDS = {"train": "data/train-00000-of-00006.parquet", "test": "data/test-00000-of-00002.parquet"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-per-class", type=int, default=2500)
    parser.add_argument("--test-per-class", type=int, default=1000)
    args = parser.parse_args()
    want = {"train": args.train_per_class, "test": args.test_per_class}
    rng = random.Random(SEED)
    report = {}
    for split, shard in SHARDS.items():
        local = hf_hub_download(REPO, shard, repo_type="dataset", local_dir=HERE / "raw")
        table = pq.read_table(local, columns=["image", "label"])
        labels = table.column("label").to_pylist()
        by_label = {0: [i for i, v in enumerate(labels) if v == 0], 1: [i for i, v in enumerate(labels) if v == 1]}
        print(f"{split}: shard has real={len(by_label[0])} fake={len(by_label[1])}", flush=True)
        images = table.column("image")
        stats = {}
        for label, name in ((0, "real"), (1, "fake")):
            out = DATA / split / name
            out.mkdir(parents=True, exist_ok=True)
            order = by_label[label][:]
            rng.shuffle(order)
            saved = skipped = 0
            for index in order:
                if saved >= want[split]:
                    break
                raw = images[index].as_py()["bytes"]
                face = face_crop(Image.open(io.BytesIO(raw)).convert("RGB"))
                if face is None:
                    skipped += 1
                    continue
                face.save(out / f"{split}_{name}_{index:06d}.png")
                saved += 1
                if saved % 500 == 0:
                    print(f"  {split}/{name}: {saved}", flush=True)
            stats[name] = {"saved": saved, "no_face_skipped": skipped}
        report[split] = stats
    (DATA / "prepare_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
