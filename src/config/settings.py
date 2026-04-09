from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "hidden-gems-pipeline"
    app_env: str = "dev"
    log_level: str = "INFO"

    pghost: str
    pgport: int = Field(default=5433, gt=0)
    pgdatabase: str
    pguser: str
    pgpassword: str
    pgschema: str = "hidden_gems"

    db_echo: bool = False

    data_raw_path: Path = BASE_DIR / "data" / "raw"
    data_staging_path: Path = BASE_DIR / "data" / "staging"
    data_reference_path: Path = BASE_DIR / "data" / "reference"
    data_artifacts_path: Path = BASE_DIR / "data" / "artifacts"

    google_maps_api_key: str | None = None
    google_places_base_url: str = "https://places.googleapis.com/v1"
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"
    request_timeout_seconds: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def logs_path(self) -> Path:
        return self.data_artifacts_path / "logs"

    def ensure_directories(self) -> None:
        for path in (
            self.data_raw_path,
            self.data_staging_path,
            self.data_reference_path,
            self.data_artifacts_path,
            self.logs_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()