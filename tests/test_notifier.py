from datetime import date

import pytest

from mealie_planner.notifier import PhoneNotifier
from mealie_planner.selection.schema import MealPlanDraft, PlanMeal


@pytest.mark.asyncio
async def test_phone_notification_uses_three_supported_buttons(monkeypatch) -> None:
    sent = {}

    def fake_notify_joe(*args, **kwargs):
        sent.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr("mealie_planner.notifier.notify_joe", fake_notify_joe)
    draft = MealPlanDraft(
        plan_id="plan-1",
        meals=[
            PlanMeal(
                date=date(2026, 5, 25),
                recipe_id="r1",
                title="Tofu Tikka Masala",
                rationale="Fits.",
            )
        ],
        rationale="Good week.",
        candidate_ids={"r1"},
        expected_dates={date(2026, 5, 25)},
    )

    await PhoneNotifier(mealie_public_url="https://mealie.feocco.com").send_plan(draft)

    assert [button["title"] for button in sent["buttons"]] == ["Accept", "Regenerate", "Reply"]
