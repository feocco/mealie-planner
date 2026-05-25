from datetime import date

import pytest

from mealie_planner.notifier import PhoneNotifier
from mealie_planner.selection.schema import MealPlanDraft, PlanMeal


@pytest.mark.asyncio
async def test_phone_notification_uses_three_supported_buttons(monkeypatch) -> None:
    sent = []

    def fake_notify_joe(*args, **kwargs):
        sent.append(("joe", args, kwargs))
        return {"ok": True}

    def fake_notify_jess(*args, **kwargs):
        sent.append(("jess", args, kwargs))
        return {"ok": True}

    monkeypatch.setattr("mealie_planner.notifier.notify_joe", fake_notify_joe)
    monkeypatch.setattr("mealie_planner.notifier.notify_jess", fake_notify_jess)
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

    assert sent[0][0] == "joe"
    assert [button["title"] for button in sent[0][2]["buttons"]] == ["Accept", "Regenerate", "Reply"]

    await PhoneNotifier(mealie_public_url="https://mealie.feocco.com").send_plan(draft, recipient="jess")

    assert sent[1][0] == "jess"
    assert sent[1][1][0] == "Dinner plan from Joe"
    assert "MEALIE_PLANNER_ACCEPT_JESS::plan-1" == sent[1][2]["buttons"][0]["action"]


@pytest.mark.asyncio
async def test_phone_notifier_tells_joe_when_jess_accepts(monkeypatch) -> None:
    sent = {}

    def fake_notify_joe(*args, **kwargs):
        sent["args"] = args
        sent["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr("mealie_planner.notifier.notify_joe", fake_notify_joe)
    draft = MealPlanDraft(
        plan_id="plan-1",
        meals=[
            PlanMeal(date=date(2026, 5, 25), recipe_id="r1", title="Tofu Tikka Masala", rationale="Fits.")
        ],
        rationale="Good week.",
        candidate_ids={"r1"},
        expected_dates={date(2026, 5, 25)},
    )

    await PhoneNotifier(mealie_public_url="https://mealie.feocco.com").send_jess_accepted(draft)

    assert sent["args"][0] == "Jess accepted dinner plan"
    assert sent["kwargs"]["buttons"] == []
