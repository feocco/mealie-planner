from datetime import date

import pytest

from mealie_planner.actions import ActionHandler
from mealie_planner.weather import HomeAssistantWeatherProvider


class FakePlanner:
    def __init__(self):
        self.accepted = []
        self.regenerated = []
        self.dismissed = []

    async def accept(self, plan_id, *, reviewer="joe"):
        self.accepted.append((plan_id, reviewer))

    async def regenerate(self, plan_id, feedback=None, *, reviewer="joe"):
        self.regenerated.append((plan_id, feedback, reviewer))

    async def dismiss(self, plan_id):
        self.dismissed.append(plan_id)


@pytest.mark.asyncio
async def test_action_handler_routes_stage_aware_accept_regenerate_dismiss_and_reply() -> None:
    planner = FakePlanner()
    handler = ActionHandler(planner)

    await handler.handle_event({"event_type": "mobile_app_notification_action", "data": {"action": "MEALIE_PLANNER_ACCEPT_JOE::p1"}})
    await handler.handle_event({"event_type": "mobile_app_notification_action", "data": {"action": "MEALIE_PLANNER_REGENERATE_JESS::p2"}})
    await handler.handle_event({"event_type": "mobile_app_notification_action", "data": {"action": "MEALIE_PLANNER_DISMISS::p3"}})
    await handler.handle_event({"event_type": "mobile_app_notification_action", "data": {"action": "MEALIE_PLANNER_REPLY_JESS::p4", "reply_text": "less pasta"}})

    assert planner.accepted == [("p1", "joe")]
    assert planner.regenerated == [("p2", None, "jess"), ("p4", "less pasta", "jess")]
    assert planner.dismissed == ["p3"]


class BrokenHA:
    async def __aenter__(self):
        raise RuntimeError("HA is down")

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_weather_provider_returns_explicit_unavailable_context() -> None:
    provider = HomeAssistantWeatherProvider(ha_factory=lambda: BrokenHA(), location="Auburn, NY")

    weather = await provider.get_weather(date(2026, 5, 25), 4)

    assert weather.weather_unavailable is True
    assert weather.location == "Auburn, NY"
    assert weather.daily == []
