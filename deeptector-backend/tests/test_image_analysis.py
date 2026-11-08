"""Still-image analysis: spatial branch only, temporal score absent."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.inference import AnalysisError, ModelAdapter, is_image, probe_image
from app.main import create_app
from app.policy import classify
from app.schemas import ModelResult
from app.worker import run_once

PNG = b"\x89PNG\r\n\x1a\n" + b"test-image"


def image_result(spatial=0.8, **overrides):
    result = {
        "spatial": spatial,
        "temporal": None,
        "fused": spatial,
        "n_faces": 1,
        "family": "image",
        "faithfulness": "spatial only",
        "metadata": {"media_type": "image"},
        "model_version": "spatial-only-test",
        "calibration_version": "not-applied-spatial-only",
        "artifacts": {"cam_spatial": PNG},
        "warnings": ["IMAGE_SPATIAL_ONLY"],
        "is_demo": False,
    }
    result.update(overrides)
    return result


class ImageAdapter:
    def analyze(self, path: Path, progress):
        assert path.suffix == ".jpg"
        progress("MODEL_INFERENCE_AND_XAI")
        return image_result()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "data" / "test.sqlite3",
        storage_dir=tmp_path / "storage",
        model_dir=tmp_path / "models",
        inference_mode="demo",
    )


def write_png(path: Path, width=64, height=48) -> Path:
    ok, buffer = cv2.imencode(".png", np.full((height, width, 3), 127, np.uint8))
    assert ok
    buffer.tofile(str(path))  # works with non-ASCII paths, like the app's storage folder
    return path


def test_image_policy_is_spatial_only():
    fake = classify(0.7, None)
    assert fake["verdict"] == "FAKE" and fake["primary_signal"] == "SPATIAL"
    assert fake["policy_version"].endswith("-image") and fake["signal_score"] == pytest.approx(70)
    assert classify(0.2, None)["verdict"] == "REAL"
    with pytest.raises(ValueError):
        classify(float("nan"), None)
    # Video policy unchanged.
    assert classify(0.6, 0.6)["policy_version"] == "traffic-v1-experimental"


def test_model_result_rules_for_images_and_videos():
    payload = {k: v for k, v in image_result().items() if k != "artifacts"}
    assert ModelResult.model_validate(payload).temporal is None
    with pytest.raises(ValidationError):
        ModelResult.model_validate({**payload, "fused": 0.1})  # image fused must equal spatial
    video = {**payload, "temporal": 0.4, "fused": 0.6, "n_faces": 2}
    with pytest.raises(ValidationError):
        ModelResult.model_validate(video)  # videos still need >= 4 face frames
    assert ModelResult.model_validate({**video, "n_faces": 4}).temporal == 0.4


def test_image_upload_runs_through_worker(settings):
    with TestClient(create_app(settings)) as client:
        token = client.post("/api/v1/sessions").json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        queued = client.post("/api/v1/analyses", headers=headers, files={"video": ("face.jpg", b"jpeg-bytes", "image/jpeg")})
        assert queued.status_code == 202
        assert run_once(settings, adapter=ImageAdapter()) is True
        detail = client.get(f"/api/v1/analyses/{queued.json()['id']}", headers=headers).json()
        assert detail["status"] == "COMPLETED"
        assert detail["result"].get("temporal") is None
        assert detail["result"]["policy"]["verdict"] == "FAKE"
        assert detail["result"]["policy"]["primary_signal"] == "SPATIAL"
        assert [a["kind"] for a in detail["artifacts"]] == ["cam_spatial"]
        rejected = client.post("/api/v1/analyses", headers=headers, files={"video": ("anim.gif", b"gif", "image/gif")})
        assert rejected.status_code == 400
        assert ".jpg" in rejected.json()["error"]["details"]["allowed_extensions"]


def test_probe_image_handles_non_ascii_paths_and_garbage(tmp_path):
    folder = tmp_path / "졸작"
    folder.mkdir()
    meta = probe_image(write_png(folder / "얼굴.png", 64, 48))
    assert (meta["media_type"], meta["width"], meta["height"]) == ("image", 64, 48)
    garbage = folder / "broken.jpg"
    garbage.write_bytes(b"not an image")
    with pytest.raises(AnalysisError) as error:
        probe_image(garbage)
    assert error.value.code == "INVALID_IMAGE"


def test_demo_adapter_handles_images(settings, tmp_path):
    assert is_image("a.JPEG") and not is_image("a.mp4")
    result = ModelAdapter(settings).analyze(write_png(tmp_path / "x.png"), lambda stage: None)
    assert result["temporal"] is None and result["fused"] == result["spatial"]
    assert "IMAGE_SPATIAL_ONLY" in result["warnings"]
    ModelResult.model_validate({k: v for k, v in result.items() if k != "artifacts"})
