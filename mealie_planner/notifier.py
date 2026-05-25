from __future__ import annotations

import asyncio

from homelab import notify_joe

from mealie_planner.actions import ACCEPT_PREFIX, DISMISS_PREFIX, REGENERATE_PREFIX, REPLY_PREFIX, action
from mealie_planner.selection.schema import MealPlanDraft


class PhoneNotifier:
    def __init__(self, *, mealie_public_url: str) -> None:
        self.mealie_public_url = mealie_public_url.rstrip("/")

    async def send_plan(self, draft: MealPlanDraft) -> None:
        await asyncio.to_thread(
            notify_joe,
            "Dinner plan ready",
            format_plan(draft),
            tag=f"mealie-planner-{draft.plan_id}",
            group="mealie-planner",
            url=self.mealie_public_url,
            buttons=[
                {"title": "Accept", "action": action(ACCEPT_PREFIX, draft.plan_id)},
                {"title": "Regenerate", "action": action(REGENERATE_PREFIX, draft.plan_id)},
                {"title": "Dismiss", "action": action(DISMISS_PREFIX, draft.plan_id)},
                {
                    "title": "Reply",
                    "action": action(REPLY_PREFIX, draft.plan_id),
                    "behavior": "textInput",
                    "textInputButtonTitle": "Send",
                    "textInputPlaceholder": "more tofu, less pasta...",
                },
            ],
        )


def format_plan(draft: MealPlanDraft) -> str:
    lines = [f"{meal.date.strftime('%A')}: {meal.title}" for meal in draft.meals]
    lines.append("")
    lines.append(draft.rationale)
    return "\n".join(lines)

