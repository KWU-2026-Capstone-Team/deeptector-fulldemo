"""Regression set: face crops from the 24 local game clips (FaceForensics++-style swaps/reenactments).

Checks that fine-tuning on StyleGAN faces does not erase what the model already does well.
Sampling matches the service's video path (step = frames//32, first 16 face frames).
The service DB is opened READ-ONLY to reuse each clip's stored temporal score.
"""
from __future__ import annotations

import json
import sqlite3

import cv2
from PIL import Image

from common import DATA, SERVICE, WORKSPACE, face_crop

GAME = WORKSPACE / "deepGame"
DB = SERVICE / "deeptector-backend" / "data" / "integrated" / "deeptector.sqlite3"


def main() -> None:
    catalog = json.loads((GAME / "src" / "data" / "videos.json").read_text(encoding="utf-8"))["videos"]
    temporal = {}
    if DB.is_file():
        with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as db:
            temporal = dict(db.execute("SELECT clip_id, temporal FROM game_clip_evaluations"))
    meta = []
    for item in catalog:
        path = GAME / "public" / "videos" / item["src"].split("/")[-1]
        cap = cv2.VideoCapture(str(path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total // 32)
        out = DATA / "ffpp_eval" / item["id"]
        out.mkdir(parents=True, exist_ok=True)
        saved = 0
        for index in range(total):
            ok, frame = cap.read()
            if not ok or saved >= 16:
                break
            if index % step:
                continue
            face = face_crop(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            if face is not None:
                face.save(out / f"{saved:02d}.png")
                saved += 1
        cap.release()
        meta.append({"id": item["id"], "label": 1 if item["label"].lower() == "fake" else 0,
                     "difficulty": item.get("difficulty"), "faces": saved, "temporal": temporal.get(item["id"])})
        print(item["id"], item["label"], "faces", saved, flush=True)
    (DATA / "ffpp_eval" / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
