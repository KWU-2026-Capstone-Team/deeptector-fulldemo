from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import math


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


class SessionResponse(BaseModel):
    session_id: str
    token: str
    expires_at: str


class ArtifactResponse(BaseModel):
    kind: str
    mime_type: str
    url: str


class AnalysisSummary(BaseModel):
    id: str
    filename: str
    status: Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
    stage: str
    created_at: str
    updated_at: str
    expires_at: str


class Thresholds(BaseModel):
    fused_fake: float
    branch_fake: float
    branch_caution: float


class RiskPolicy(BaseModel):
    verdict: Literal["REAL", "FAKE"]
    traffic_light: Literal["RED", "YELLOW", "GREEN"]
    reason: str
    primary_signal: Literal["SPATIAL", "TEMPORAL", "BALANCED"]
    policy_version: str
    signal_score: float = Field(ge=0, le=100)
    thresholds: Thresholds
    score_interpretation: str


class ModelResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)
    spatial: float = Field(ge=0, le=1)
    # None for still images: no motion, so the temporal branch does not run.
    temporal: float | None = Field(default=None, ge=0, le=1)
    fused: float = Field(ge=0, le=1)
    n_faces: int = Field(ge=1, le=16)
    family: str
    faithfulness: str
    metadata: dict[str, Any]
    model_version: str = Field(min_length=1)
    calibration_version: str = Field(min_length=1)
    warnings: list[str]
    is_demo: bool
    policy: RiskPolicy | None = None

    @model_validator(mode="after")
    def consistent_fusion(self):
        if self.temporal is None:
            # Still image: spatial branch only, and a single face crop.
            if not math.isclose(self.fused, self.spatial, rel_tol=0, abs_tol=1e-8):
                raise ValueError("Image fused score must equal the spatial score")
            return self
        if self.n_faces < 4:
            raise ValueError("Video analysis requires at least 4 face frames")
        if not math.isclose(self.fused, (self.spatial + self.temporal) / 2, rel_tol=0, abs_tol=1e-8):
            raise ValueError("Fused score does not match branch mean")
        return self


class AnalysisDetail(AnalysisSummary):
    result: ModelResult | None = None
    error: dict[str, Any] | None = None
    artifacts: list[ArtifactResponse] = Field(default_factory=list)


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]


class ModelInfoResponse(BaseModel):
    inference_mode: str
    configured_model_dir: str
    model_dir_exists: bool
    loaded: bool
