from __future__ import annotations

import logging
import os

import uvicorn

from mealie_planner.api import create_app
from mealie_planner.config import AppConfig
from mealie_planner.mealie_client import MealieClient
from mealie_planner.notifier import PhoneNotifier
from mealie_planner.selection.openai_selector import OpenAISelector
from mealie_planner.service import PlannerService
from mealie_planner.state import PlannerStore
from mealie_planner.weather import HomeAssistantWeatherProvider

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def build_service() -> PlannerService:
    config = AppConfig.from_env()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return PlannerService(
        store=PlannerStore(config.data_dir / "planner.sqlite3"),
        recipe_source=MealieClient(base_url=config.mealie_base_url, api_token=config.mealie_api_token),
        selector=OpenAISelector(api_key=config.openai_api_key, model=config.openai_model),
        weather=HomeAssistantWeatherProvider(
            location=config.household_location,
            entity_id=config.ha_weather_entity_id,
        ),
        notifier=PhoneNotifier(mealie_public_url=config.mealie_public_url),
    )


app = create_app(build_service(), start_action_listener=True)


def main() -> None:
    uvicorn.run(
        "mealie_planner.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
