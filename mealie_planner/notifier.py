from __future__ import annotations

import asyncio

from homelab import notify_jess, notify_joe

from mealie_planner.actions import (
    ACCEPT_JESS_PREFIX,
    ACCEPT_JOE_PREFIX,
    REGENERATE_JESS_PREFIX,
    REGENERATE_JOE_PREFIX,
    REPLY_JESS_PREFIX,
    REPLY_JOE_PREFIX,
    action,
)
from mealie_planner.selection.schema import MealPlanDraft


class PhoneNotifier:
    def __init__(self, *, mealie_public_url: str) -> None:
        self.mealie_public_url = mealie_public_url.rstrip("/")

    async def send_plan(self, draft: MealPlanDraft, *, recipient: str = "joe") -> None:
        if recipient == "jess":
            notify = notify_jess
            title = "Dinner plan from Joe"
            accept_prefix = ACCEPT_JESS_PREFIX
            regenerate_prefix = REGENERATE_JESS_PREFIX
            reply_prefix = REPLY_JESS_PREFIX
        else:
            notify = notify_joe
            title = "Dinner plan ready"
            accept_prefix = ACCEPT_JOE_PREFIX
            regenerate_prefix = REGENERATE_JOE_PREFIX
            reply_prefix = REPLY_JOE_PREFIX

        await asyncio.to_thread(
            notify,
            title,
            format_plan(draft),
            tag=f"mealie-planner-{draft.plan_id}",
            group="mealie-planner",
            url=self.mealie_public_url,
            buttons=[
                {"title": "Accept", "action": action(accept_prefix, draft.plan_id)},
                {"title": "Regenerate", "action": action(regenerate_prefix, draft.plan_id)},
                {
                    "title": "Reply",
                    "action": action(reply_prefix, draft.plan_id),
                    "behavior": "textInput",
                    "textInputButtonTitle": "Send",
                    "textInputPlaceholder": "more tofu, less pasta...",
                },
            ],
        )

    async def send_jess_accepted(self, draft: MealPlanDraft) -> None:
        await asyncio.to_thread(
            notify_joe,
            "Jess accepted dinner plan",
            format_plan(draft),
            tag=f"mealie-planner-{draft.plan_id}-jess-accepted",
            group="mealie-planner",
            url=self.mealie_public_url,
            buttons=[],
        )


def format_plan(draft: MealPlanDraft) -> str:
    lines = [f"{meal.date.strftime('%A')}: {meal.title}" for meal in draft.meals]
    lines.append("")
    lines.append(draft.rationale)
    return "\n".join(lines)
