import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Walk up from this file to find the repo root .env
_here = Path(__file__).resolve()
_env_candidates = [_here.parents[i] / ".env" for i in range(6)]
_env_file = next((str(p) for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str
    database_url: str
    log_level: str = "INFO"
    app_env: str = "local"


settings = Settings()  # type: ignore[call-arg]
