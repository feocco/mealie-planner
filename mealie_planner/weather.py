from __future__ import annotations

from datetime import date
import logging
from typing import Any, Callable

from homelab import HomeAssistantWebSocketClient

from mealie_planner.selection.schema import WeatherContext

LOGGER = logging.getLogger(__name__)


class HomeAssistantWeatherProvider:
    def __init__(
        self,
        *,
        ha_factory: Callable[[], Any] | None = None,
        location: str = "Auburn, NY",
        entity_id: str | None = None,
    ) -> None:
        self.ha_factory = ha_factory or HomeAssistantWebSocketClient.from_env
        self.location = location
        self.entity_id = entity_id

    async def get_weather(self, start_date: date, day_count: int) -> WeatherContext:
        try:
            async with self.ha_factory() as ha:
                entity_id = self.entity_id or await self._discover_entity(ha)
                if entity_id is None:
                    return WeatherContext(location=self.location, weather_unavailable=True, daily=[])
                forecast = await self._daily_forecast(ha, entity_id)
                return WeatherContext(
                    location=self.location,
                    weather_unavailable=False,
                    daily=forecast[:day_count],
                )
        except Exception as exc:  # noqa: BLE001 - weather is advisory, not plan-blocking.
            LOGGER.warning("Home Assistant weather unavailable: %s", exc)
            return WeatherContext(location=self.location, weather_unavailable=True, daily=[])

    async def _discover_entity(self, ha: Any) -> str | None:
        states = await ha.get_states()
        if isinstance(states, dict):
            iterable = states.values()
        else:
            iterable = states
        for state in iterable:
            entity_id = getattr(state, "entity_id", None)
            if entity_id is None and isinstance(state, dict):
                entity_id = state.get("entity_id")
            if isinstance(entity_id, str) and entity_id.startswith("weather."):
                return entity_id
        return None

    async def _daily_forecast(self, ha: Any, entity_id: str) -> list[dict[str, Any]]:
        response = await ha.call_service(
            "weather",
            "get_forecasts",
            {"entity_id": entity_id, "type": "daily"},
        )
        payload = response.get("response") if isinstance(response, dict) else response
        if isinstance(payload, dict):
            forecast = payload.get(entity_id, {}).get("forecast")
            if isinstance(forecast, list):
                return [normalize_forecast_day(day) for day in forecast]
        return []


def normalize_forecast_day(day: dict[str, Any]) -> dict[str, Any]:
    temperature = day.get("temperature")
    return {
        "date": str(day.get("datetime", ""))[:10],
        "condition": day.get("condition"),
        "high_f": temperature,
        "low_f": day.get("templow"),
    }

