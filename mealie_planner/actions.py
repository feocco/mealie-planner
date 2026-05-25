from __future__ import annotations

from typing import Any

from homelab import NotificationActionRouter


ACCEPT_PREFIX = "MEALIE_PLANNER_ACCEPT"
REGENERATE_PREFIX = "MEALIE_PLANNER_REGENERATE"
DISMISS_PREFIX = "MEALIE_PLANNER_DISMISS"
REPLY_PREFIX = "MEALIE_PLANNER_REPLY"


class ActionHandler:
    def __init__(self, planner: Any) -> None:
        self.planner = planner

    async def handle_event(self, event: dict[str, Any]) -> bool:
        if event.get("event_type") != "mobile_app_notification_action":
            return False
        data = event.get("data") or {}
        action = data.get("action")
        if not isinstance(action, str):
            return False
        prefix, separator, plan_id = action.partition("::")
        if not separator or not plan_id:
            return False
        if prefix == ACCEPT_PREFIX:
            await self.planner.accept(plan_id)
            return True
        if prefix == REGENERATE_PREFIX:
            await self.planner.regenerate(plan_id)
            return True
        if prefix == DISMISS_PREFIX:
            await self.planner.dismiss(plan_id)
            return True
        if prefix == REPLY_PREFIX:
            reply_text = data.get("reply_text")
            await self.planner.regenerate(plan_id, reply_text if isinstance(reply_text, str) else None)
            return True
        return False


def action(prefix: str, plan_id: str) -> str:
    return NotificationActionRouter.make_action(prefix, plan_id)

