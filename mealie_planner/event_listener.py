from __future__ import annotations

import asyncio
import logging
from typing import Any

from homelab import HomeAssistantWebSocketClient

from mealie_planner.actions import ActionHandler

LOGGER = logging.getLogger(__name__)


async def run_action_listener(planner: Any, *, reconnect_seconds: float = 10) -> None:
    handler = ActionHandler(planner)
    while True:
        try:
            async with HomeAssistantWebSocketClient.from_env() as ha:
                ha.add_event_handler(handler.handle_event)
                await ha.subscribe_events("mobile_app_notification_action")
                LOGGER.info("Listening for Mealie planner notification actions")
                await ha.wait_closed()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - reconnect long-lived listener after HA outages.
            LOGGER.warning("Mealie planner action listener disconnected: %s", exc)
            await asyncio.sleep(reconnect_seconds)

