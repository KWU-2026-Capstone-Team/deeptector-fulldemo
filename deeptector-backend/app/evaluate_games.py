"""Explicit, resumable real-model evaluation of registered local game clips."""

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from .config import Settings
from .db import connect, initialize
from .game import initialize_game, now
from .inference import ModelAdapter
from .policy import classify


def record_evaluation(settings, clip_id, result):
    if result.get("is_demo") is not False or not result.get("model_version"):
        raise ValueError("Only real model results with a model version may be recorded")
    classify(result["spatial"], result["temporal"])
    with connect(settings) as db:
        db.execute(
            """INSERT INTO game_clip_evaluations(clip_id,model_version,spatial,temporal,evaluated_at)
               VALUES(?,?,?,?,?) ON CONFLICT(clip_id,model_version) DO UPDATE SET
               spatial=excluded.spatial,temporal=excluded.temporal,evaluated_at=excluded.evaluated_at""",
            (clip_id, result["model_version"], result["spatial"], result["temporal"], now()),
        )


def export_evaluations(settings, path: Path) -> int:
    """Write stored model scores (no media, no labels) so another PC can skip re-running the model."""
    with connect(settings) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT clip_id,model_version,spatial,temporal,evaluated_at FROM game_clip_evaluations ORDER BY clip_id,model_version"
        )]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"evaluations": rows}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(rows)


def import_evaluations(settings, path: Path, model_dir: Path | None) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))["evaluations"]
    with connect(settings) as db:
        known = {row[0] for row in db.execute("SELECT id FROM game_clips")}
    unknown = sorted({row["clip_id"] for row in rows} - known)
    if unknown:
        raise SystemExit(f"Register the game clips first (Import-Game.ps1); unknown clip IDs: {unknown}")
    if model_dir is not None:
        current = model_version(model_dir)
        stale = sorted({row["model_version"] for row in rows} - {current})
        if stale:
            raise SystemExit(f"Saved scores are for model {stale}, but the local model is {current}; run the evaluation instead.")
    for row in rows:
        classify(row["spatial"], row["temporal"])
    with connect(settings) as db:
        db.executemany(
            """INSERT INTO game_clip_evaluations(clip_id,model_version,spatial,temporal,evaluated_at)
               VALUES(:clip_id,:model_version,:spatial,:temporal,:evaluated_at) ON CONFLICT(clip_id,model_version) DO UPDATE SET
               spatial=excluded.spatial,temporal=excluded.temporal,evaluated_at=excluded.evaluated_at""",
            rows,
        )
    return len(rows)


def model_version(model_dir: Path) -> str:
    """Same fingerprint the inference adapter stamps on real results."""
    root = model_dir.resolve()
    spatial = sorted((root / "models/spatial").glob("*.pt"))
    temporal = sorted((root / "models/temporal").glob("*.pt"))
    digest = hashlib.sha256()
    for file in [*spatial, *temporal, root / "models/temporal/calibration.json", root / "infer.py", root / "xai.py"]:
        digest.update(file.name.encode())
        with file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return "dual-branch-" + digest.hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, help="required to evaluate; with --import-json it checks the model version")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data/integrated")
    parser.add_argument("--clip-id", action="append", help="Evaluate only these IDs; repeatable")
    parser.add_argument("--force", action="store_true", help="Re-evaluate clips that already have an evaluation")
    parser.add_argument("--export", type=Path, help="write stored evaluations to this JSON file and exit")
    parser.add_argument("--import-json", type=Path, help="load evaluations from an --export file and exit")
    args = parser.parse_args()
    data = args.data_dir.resolve()
    settings = replace(Settings.from_env(), inference_mode="real",
                       model_dir=(args.model_dir or Path(".")).resolve(),
                       db_path=data / "deeptector.sqlite3", storage_dir=data / "storage")
    initialize(settings)
    initialize_game(settings)
    if args.export:
        print(f"exported {export_evaluations(settings, args.export)} evaluations to {args.export}")
        return
    if args.import_json:
        print(f"imported {import_evaluations(settings, args.import_json, args.model_dir)} evaluations")
        return
    if args.model_dir is None:
        parser.error("--model-dir is required to evaluate clips")
    with connect(settings) as db:
        clips = list(db.execute("SELECT id,video_path FROM game_clips WHERE enabled=1"))
        evaluated = {row[0] for row in db.execute("SELECT DISTINCT clip_id FROM game_clip_evaluations")}
    if args.clip_id:
        missing = set(args.clip_id) - {row["id"] for row in clips}
        if missing:
            parser.error(f"Unknown or disabled clip IDs: {sorted(missing)}")
        clips = [row for row in clips if row["id"] in args.clip_id]
    adapter = ModelAdapter(settings)
    for clip in clips:
        if clip["id"] in evaluated and not args.force:
            print(f"skip {clip['id']}: existing evaluation (use --force for a new model)")
            continue
        print(f"evaluating {clip['id']}", flush=True)
        result = adapter.analyze(Path(clip["video_path"]), lambda stage: print(stage, flush=True))
        record_evaluation(settings, clip["id"], result)
        print(f"saved {clip['id']}: {result['model_version']}", flush=True)


if __name__ == "__main__":
    main()
