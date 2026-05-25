from datetime import date

import pytest

from mealie_planner.service import PlannerService, SuggestRequest
from mealie_planner.selection.schema import MealPlanDraft, PlanMeal, RecipeCandidate, WeatherContext


class FakeRecipeSource:
    async def list_recipes(self):
        return [
            RecipeCandidate(
                id="r1",
                slug="tofu-tikka-masala",
                title="Tofu Tikka Masala",
                categories=["Dinner"],
                tags=["60 Minutes", "Indian", "Tofu"],
                tools=[],
                servings=4,
                ingredient_anchors=["tofu"],
            ),
            RecipeCandidate(
                id="r2",
                slug="soba-noodle-salad",
                title="Soba Noodle Salad",
                categories=["Dinner"],
                tags=["30 Minutes", "Fresh"],
                tools=[],
                servings=4,
                ingredient_anchors=["noodles"],
            ),
        ]

    async def list_mealplans(self, start_date, end_date):
        return []

    async def create_dinner_plan(self, *, meal_date, recipe_id, title, text):
        return {"id": f"entry-{recipe_id}", "date": meal_date.isoformat()}

    async def delete_mealplan(self, entry_id):
        return None


class FakeSelector:
    def __init__(self):
        self.calls = []

    async def select(self, planner_input):
        self.calls.append(planner_input)
        meals = [
            PlanMeal(date=day, recipe_id=planner_input.candidates[index].id, title=planner_input.candidates[index].title, rationale="Good fit.")
            for index, day in enumerate(planner_input.target_dates)
        ]
        return MealPlanDraft(
            plan_id="ignored",
            meals=meals,
            rationale="Balanced week.",
            candidate_ids={item.id for item in planner_input.candidates},
            expected_dates=set(planner_input.target_dates),
        )


class FakeWeather:
    async def get_weather(self, start_date, day_count):
        return WeatherContext(location="Auburn, NY", weather_unavailable=True, daily=[])


class FakeNotifier:
    def __init__(self):
        self.sent = []

    async def send_plan(self, draft):
        self.sent.append(draft)


@pytest.mark.asyncio
async def test_suggest_records_draft_and_sends_notification(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )

    draft = await service.suggest(
        SuggestRequest(
            start_date=date(2026, 5, 25),
            day_count=4,
            dinner_count=2,
            blocked_dates={date(2026, 5, 28)},
            guidance="include tofu",
        )
    )

    assert len(draft.meals) == 2
    assert service.store.get_plan(draft.plan_id)["status"] == "draft"
    assert service.notifier.sent[0].plan_id == draft.plan_id


@pytest.mark.asyncio
async def test_regenerate_records_feedback_and_creates_new_draft(tmp_path) -> None:
    selector = FakeSelector()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=selector,
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    first = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))

    second = await service.regenerate(first.plan_id, "make it fresher")

    assert second.plan_id != first.plan_id
    assert service.store.list_feedback(first.plan_id) == ["make it fresher"]
    assert selector.calls[-1].feedback_history == ["make it fresher"]


@pytest.mark.asyncio
async def test_accept_writes_only_accepted_plan(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))

    result = await service.accept(draft.plan_id)

    assert result.created_entry_ids == ["entry-r1"]
    assert service.store.get_plan(draft.plan_id)["status"] == "accepted"

