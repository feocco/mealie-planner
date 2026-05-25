from __future__ import annotations

from typing import Any

from homelab import NotificationActionRouter


ACCEPT_JOE_PREFIX = "MEALIE_PLANNER_ACCEPT_JOE"
ACCEPT_JESS_PREFIX = "MEALIE_PLANNER_ACCEPT_JESS"
REGENERATE_JOE_PREFIX = "MEALIE_PLANNER_REGENERATE_JOE"
REGENERATE_JESS_PREFIX = "MEALIE_PLANNER_REGENERATE_JESS"
DISMISS_PREFIX = "MEALIE_PLANNER_DISMISS"
REPLY_JOE_PREFIX = "MEALIE_PLANNER_REPLY_JOE"
REPLY_JESS_PREFIX = "MEALIE_PLANNER_REPLY_JESS"

# Backward-compatible action names for notifications that were sent before the
# two-person handoff existed.
ACCEPT_PREFIX = "MEALIE_PLANNER_ACCEPT"
REGENERATE_PREFIX = "MEALIE_PLANNER_REGENERATE"
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
        if prefix in (ACCEPT_PREFIX, ACCEPT_JOE_PREFIX):
            await self.planner.accept(plan_id, reviewer="joe")
            return True
        if prefix == ACCEPT_JESS_PREFIX:
            await self.planner.accept(plan_id, reviewer="jess")
            return True
        if prefix in (REGENERATE_PREFIX, REGENERATE_JOE_PREFIX):
            await self.planner.regenerate(plan_id, reviewer="joe")
            return True
        if prefix == REGENERATE_JESS_PREFIX:
            await self.planner.regenerate(plan_id, reviewer="jess")
            return True
        if prefix == DISMISS_PREFIX:
            await self.planner.dismiss(plan_id)
            return True
        if prefix in (REPLY_PREFIX, REPLY_JOE_PREFIX):
            reply_text = data.get("reply_text")
            await self.planner.regenerate(
                plan_id,
                reply_text if isinstance(reply_text, str) else None,
                reviewer="joe",
            )
            return True
        if prefix == REPLY_JESS_PREFIX:
            reply_text = data.get("reply_text")
            await self.planner.regenerate(
                plan_id,
                reply_text if isinstance(reply_text, str) else None,
                reviewer="jess",
            )
            return True
        return False


def action(prefix: str, plan_id: str) -> str:
    return NotificationActionRouter.make_action(prefix, plan_id)
