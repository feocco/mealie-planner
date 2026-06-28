from datetime import date

import pytest

from mealie_planner.service import PlannerService, SuggestRequest
from mealie_planner.selection.schema import MealPlanDraft, PlanMeal, RecipeCandidate, WeatherContext


class FakeRecipeSource:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.existing = []
        self.detail_calls = []
        self.details = {
            "r1": {
                "id": "r1",
                "name": "Tofu Tikka Masala",
                "recipeIngredient": [
                    {
                        "quantity": 1.0,
                        "unit": {"id": "u1", "name": "block"},
                        "food": {"id": "f1", "name": "tofu"},
                        "note": "pressed",
                        "display": "1 block tofu pressed",
                        "originalText": "1 block tofu, pressed",
                    },
                    {
                        "quantity": 1.0,
                        "unit": {"id": "u2", "name": "cup"},
                        "food": {"id": "f2", "name": "rice"},
                        "note": None,
                        "display": "1 cup rice",
                        "originalText": "1 cup rice",
                    },
                    {
                        "quantity": None,
                        "unit": None,
                        "food": None,
                        "note": "salt to taste",
                        "display": "salt to taste",
                        "originalText": "salt to taste",
                    },
                ],
            },
            "r2": {
                "id": "r2",
                "name": "Soba Noodle Salad",
                "recipeIngredient": [
                    {
                        "quantity": 2.0,
                        "unit": {"id": "u1", "name": "block"},
                        "food": {"id": "f1", "name": "tofu"},
                        "note": "pressed",
                        "display": "2 block tofu pressed",
                        "originalText": "2 blocks tofu, pressed",
                    },
                    {
                        "quantity": 1.0,
                        "unit": {"id": "u3", "name": "tablespoon"},
                        "food": {"id": "f3", "name": "sesame oil"},
                        "note": None,
                        "display": "1 tablespoon sesame oil",
                        "originalText": "1 tablespoon sesame oil",
                    },
                ],
            },
        }

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
        return self.existing

    async def create_dinner_plan(self, *, meal_date, recipe_id, title, text):
        entry = {"id": f"entry-{len(self.created) + 1}", "date": meal_date.isoformat(), "recipe_id": recipe_id, "text": text}
        self.created.append(entry)
        return entry

    async def delete_mealplan(self, entry_id):
        self.deleted.append(entry_id)
        return None

    async def get_recipe_detail(self, recipe_id):
        self.detail_calls.append(recipe_id)
        return self.details[recipe_id]


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
        self.accepted_by_jess = []

    async def send_plan(self, draft, *, recipient="joe"):
        self.sent.append((recipient, draft))

    async def send_jess_accepted(self, draft):
        self.accepted_by_jess.append(draft)


@pytest.mark.asyncio
async def test_recipe_candidates_are_read_only(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    notifier = FakeNotifier()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=notifier,
    )

    result = await service.recipe_candidates()

    assert [item["title"] for item in result["recipes"]] == ["Tofu Tikka Masala", "Soba Noodle Salad"]
    assert result["recipes"][0]["url"] == "https://mealie.feocco.com/g/home/r/tofu-tikka-masala"
    assert result["recipes"][0]["ingredient_anchors"] == ["tofu"]
    assert notifier.sent == []
    assert recipe_source.created == []
    assert recipe_source.deleted == []
    assert recipe_source.detail_calls == []


@pytest.mark.asyncio
async def test_recipe_candidates_can_include_ingredients(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )

    result = await service.recipe_candidates(include_ingredients=True)

    assert recipe_source.detail_calls == ["r1", "r2"]
    assert result["recipes"][0]["ingredients"][0]["originalText"] == "1 block tofu, pressed"
    assert result["recipes"][1]["ingredients"][0]["food"]["name"] == "tofu"


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
    assert service.store.get_plan(draft.plan_id)["status"] == "draft_for_joe"
    assert service.notifier.sent[0][0] == "joe"
    assert service.notifier.sent[0][1].plan_id == draft.plan_id


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

    result = await service.accept(draft.plan_id, reviewer="joe")

    assert result.created_entry_ids == ["entry-1"]
    assert service.store.get_plan(draft.plan_id)["status"] == "joe_accepted"
    assert service.notifier.sent[-1][0] == "jess"


@pytest.mark.asyncio
async def test_jess_accept_replaces_joe_entries_and_notifies_joe(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))

    joe_result = await service.accept(draft.plan_id, reviewer="joe")
    recipe_source.existing = [
        {"id": entry_id, "entryType": "dinner"} for entry_id in joe_result.created_entry_ids
    ]
    jess_result = await service.accept(draft.plan_id, reviewer="jess")

    assert recipe_source.deleted == joe_result.created_entry_ids
    assert jess_result.created_entry_ids == ["entry-2"]
    assert service.store.get_plan(draft.plan_id)["status"] == "jess_accepted"
    assert service.notifier.accepted_by_jess[0].plan_id == draft.plan_id


@pytest.mark.asyncio
async def test_accept_does_not_overwrite_human_meal_plan_entries(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    recipe_source.existing = [{"id": "human-entry", "entryType": "dinner"}]
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))

    with pytest.raises(RuntimeError, match="human-created"):
        await service.accept(draft.plan_id, reviewer="joe")


@pytest.mark.asyncio
async def test_jess_regenerate_creates_jess_draft_without_notifying_joe(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))
    await service.accept(draft.plan_id, reviewer="joe")

    jess_draft = await service.regenerate(draft.plan_id, "make Friday easier", reviewer="jess")

    stored = service.store.get_plan(jess_draft.plan_id)
    assert stored["parent_plan_id"] == draft.plan_id
    assert stored["status"] == "draft_for_jess"
    assert service.notifier.sent[-1][0] == "jess"


@pytest.mark.asyncio
async def test_rejects_stale_wrong_stage_actions(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))
    await service.accept(draft.plan_id, reviewer="joe")

    with pytest.raises(RuntimeError, match="Joe can only accept"):
        await service.accept(draft.plan_id, reviewer="joe")


@pytest.mark.asyncio
async def test_accepted_plan_ingredients_include_grouped_and_consolidated_views(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=2))
    await service.accept(draft.plan_id, reviewer="joe")

    result = await service.plan_ingredients(draft.plan_id)

    assert result["plan_id"] == draft.plan_id
    assert result["status"] == "joe_accepted"
    assert [item["recipe_id"] for item in result["by_recipe"]] == ["r1", "r2"]
    assert result["by_recipe"][0]["ingredients"][0]["originalText"] == "1 block tofu, pressed"
    tofu = next(item for item in result["consolidated"] if item["food_name"] == "tofu")
    assert tofu["quantity"] == 3.0
    assert tofu["unit_name"] == "block"
    assert tofu["note"] == "pressed"
    assert tofu["source_recipes"] == ["Tofu Tikka Masala", "Soba Noodle Salad"]


@pytest.mark.asyncio
async def test_draft_plan_ingredients_are_rejected_without_fetching_recipe_details(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=1))

    with pytest.raises(RuntimeError, match="accepted"):
        await service.plan_ingredients(draft.plan_id)

    assert recipe_source.detail_calls == []


@pytest.mark.asyncio
async def test_consolidation_keeps_mismatched_units_and_unstructured_rows_separate(tmp_path) -> None:
    recipe_source = FakeRecipeSource()
    recipe_source.details["r2"]["recipeIngredient"][0]["unit"] = {"id": "u4", "name": "package"}
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=recipe_source,
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    draft = await service.suggest(SuggestRequest(start_date=date(2026, 5, 25), dinner_count=2))
    await service.accept(draft.plan_id, reviewer="joe")

    result = await service.plan_ingredients(draft.plan_id)

    tofu_rows = [item for item in result["consolidated"] if item["food_name"] == "tofu"]
    assert [item["unit_name"] for item in tofu_rows] == ["block", "package"]
    assert any(item["display"] == "salt to taste" and item["quantity"] is None for item in result["consolidated"])
