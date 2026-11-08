from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _non_negative_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be zero or positive")
    return value


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be 1/0 (or true/false)")


@dataclass(frozen=True)
class Settings:
    db_path: Path
    storage_dir: Path
    model_dir: Path
    inference_mode: str = "real"
    max_upload_bytes: int = 500 * 1024 * 1024
    retention_hours: int = 24
    job_timeout_seconds: int = 3600
    max_queued_per_session: int = 3
    max_active_global: int = 32
    max_sessions: int = 10000
    max_concurrent_uploads: int = 2
    session_ttl_hours: int = 24 * 30
    # Public deployments without verified game media disable the game API entirely.
    games_enabled: bool = True
    # New sessions per client IP per hour; 0 disables the limit (local use).
    session_rate_per_ip_hour: int = 0
    # Header set by the only proxy in front of the API (e.g. cf-connecting-ip for a
    # Cloudflare Tunnel). Use only when the API is reachable through that proxy alone.
    client_ip_header: str = ""
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    )

    @classmethod
    def from_env(cls) -> "Settings":
        service_root = Path(__file__).resolve().parents[1]
        data_root = Path(os.getenv("DEEPTECTOR_DATA_DIR", service_root / "data"))
        model_default = service_root.parent / "AI-Generated-Media-Detection" / "deepfake_detector"
        mode = os.getenv("DEEPTECTOR_INFERENCE_MODE", "real").strip().lower()
        if mode not in {"real", "demo"}:
            raise ValueError("DEEPTECTOR_INFERENCE_MODE must be 'real' or 'demo'")
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "DEEPTECTOR_CORS_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(
            db_path=Path(os.getenv("DEEPTECTOR_DB_PATH", data_root / "deeptector.sqlite3")),
            storage_dir=Path(os.getenv("DEEPTECTOR_STORAGE_DIR", data_root / "storage")),
            model_dir=Path(os.getenv("DEEPTECTOR_MODEL_DIR", model_default)),
            inference_mode=mode,
            max_upload_bytes=_positive_int("DEEPTECTOR_MAX_UPLOAD_BYTES", 500 * 1024 * 1024),
            retention_hours=_positive_int("DEEPTECTOR_RETENTION_HOURS", 24),
            job_timeout_seconds=_positive_int("DEEPTECTOR_JOB_TIMEOUT_SECONDS", 3600),
            max_queued_per_session=_positive_int("DEEPTECTOR_MAX_QUEUED_PER_SESSION", 3),
            max_active_global=_positive_int("DEEPTECTOR_MAX_ACTIVE_GLOBAL", 32),
            max_sessions=_positive_int("DEEPTECTOR_MAX_SESSIONS", 10000),
            max_concurrent_uploads=_positive_int("DEEPTECTOR_MAX_CONCURRENT_UPLOADS", 2),
            session_ttl_hours=_positive_int("DEEPTECTOR_SESSION_TTL_HOURS", 24 * 30),
            games_enabled=_flag("DEEPTECTOR_ENABLE_GAMES", True),
            session_rate_per_ip_hour=_non_negative_int("DEEPTECTOR_SESSION_RATE_PER_IP_HOUR", 0),
            client_ip_header=os.getenv("DEEPTECTOR_CLIENT_IP_HEADER", "").strip().lower(),
            cors_origins=origins,
        )
