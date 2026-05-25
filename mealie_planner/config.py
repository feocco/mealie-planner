from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    openai_api_key: str
    openai_model: str
    mealie_base_url: str
    mealie_api_token: str
    mealie_public_url: str
    data_dir: Path
    household_location: str
    ha_weather_entity_id: str | None

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv(".env.local")
        load_dotenv()
        return cls(
            openai_api_key=required("OPENAI_API_KEY"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
            mealie_base_url=required("MEALIE_BASE_URL"),
            mealie_api_token=required("MEALIE_API_TOKEN"),
            mealie_public_url=os.environ.get("MEALIE_PUBLIC_URL", "https://mealie.feocco.com"),
            data_dir=Path(os.environ.get("DATA_DIR", "data")),
            household_location=os.environ.get("HOUSEHOLD_LOCATION", "Auburn, NY"),
            ha_weather_entity_id=os.environ.get("HA_WEATHER_ENTITY_ID") or None,
        )


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value
