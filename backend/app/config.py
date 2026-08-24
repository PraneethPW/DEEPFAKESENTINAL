from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./sentinel.db"
    jwt_secret: str = "development-only-change-this-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    frontend_url: str = "http://localhost:5173"

    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    deepfake_model_id: str = "hamzenium/ViT-Deepfake-Classifier"
    deepfake_model_checkpoint: str = ""
    synthetic_detector_enabled: bool = True
    synthetic_model_id: str = "delpot/steganograph-ia-detector"
    model_device: str = "auto"
    model_local_only: bool = False
    calibration_artifact: str = ""
    authentic_threshold: float = 0.35
    manipulated_threshold: float = 0.65

    max_image_mb: int = 15
    max_video_mb: int = 80
    max_video_seconds: int = 60
    max_video_frames: int = 24
    max_concurrent_inference: int = 1

    storage_provider: str = "local"
    storage_root: Path = Path("./private_storage")
    store_original_media: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Use the installed Psycopg 3 driver for generic Neon/Postgres URLs."""
        url = (value or "sqlite:///./sentinel.db").strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

    @field_validator("manipulated_threshold")
    @classmethod
    def thresholds_must_be_ordered(cls, value: float, info) -> float:
        authentic = info.data.get("authentic_threshold", 0.35)
        if not 0 <= authentic < value <= 1:
            raise ValueError("thresholds must satisfy 0 <= authentic < manipulated <= 1")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]

    @property
    def detector_model_id(self) -> str:
        primary = (
            Path(self.deepfake_model_checkpoint).name
            if self.deepfake_model_checkpoint
            else self.deepfake_model_id
        )
        if self.synthetic_detector_enabled:
            return f"{primary} + {self.synthetic_model_id}"
        return primary


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
