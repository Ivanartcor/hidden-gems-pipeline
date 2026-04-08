from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"

    pghost: str
    pgport: int = 5433
    pgdatabase: str
    pguser: str
    pgpassword: str

    data_raw_path: str = "./data/raw"
    data_staging_path: str = "./data/staging"
    data_reference_path: str = "./data/reference"
    data_artifacts_path: str = "./data/artifacts"

    google_maps_api_key: str | None = None
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()