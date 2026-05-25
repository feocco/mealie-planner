from datetime import date

from mealie_planner.selection.rules import build_compact_context, choose_plan_dates, prefilter_recipes
from mealie_planner.selection.schema import RecipeCandidate, WeatherContext


def recipe(slug: str, *, tags: list[str], categories: list[str] | None = None) -> RecipeCandidate:
    return RecipeCandidate(
        id=slug,
        slug=slug,
        title=slug.replace("-", " ").title(),
        categories=categories or ["Dinner"],
        tags=tags,
        tools=[],
        servings=4,
        ingredient_anchors=["tofu", "bok choy"],
    )


def test_choose_plan_dates_skips_blocked_dates_and_limits_count() -> None:
    days = choose_plan_dates(
        start_date=date(2026, 5, 25),
        day_count=7,
        dinner_count=4,
        blocked_dates={date(2026, 5, 28)},
    )

    assert days == [
        date(2026, 5, 25),
        date(2026, 5, 26),
        date(2026, 5, 27),
        date(2026, 5, 29),
    ]


def test_prefilter_recipes_prefers_dinner_guidance_and_weather_fit() -> None:
    recipes = [
        recipe("tofu-tikka-masala", tags=["60 Minutes", "Indian", "Tofu", "Cozy"]),
        recipe("soba-noodle-salad", tags=["Fresh", "Japanese", "30 Minutes", "Salad"]),
        recipe("banana-smoothie", tags=["Fresh"], categories=["Breakfast"]),
        recipe("chicken-riggies", tags=["60 Minutes", "Meat", "Cozy"]),
    ]
    weather = WeatherContext(
        location="Auburn, NY",
        weather_unavailable=False,
        daily=[{"date": "2026-05-26", "high_f": 82, "condition": "partly cloudy"}],
    )

    selected = prefilter_recipes(
        recipes,
        guidance="tofu tikka masala and fresh warm weather dinners",
        weather=weather,
        max_candidates=3,
    )

    assert [item.slug for item in selected] == [
        "soba-noodle-salad",
        "tofu-tikka-masala",
        "chicken-riggies",
    ]


def test_compact_context_excludes_full_ingredient_and_instruction_text() -> None:
    candidate = RecipeCandidate(
        id="r1",
        slug="test-recipe",
        title="Test Recipe",
        categories=["Dinner"],
        tags=["30 Minutes"],
        tools=["Sheet Pan"],
        servings=4,
        ingredient_anchors=["tofu", "rice"],
        ingredients=["1 block tofu", "2 cups rice"],
        instructions=["Do a long detailed thing."],
    )

    context = build_compact_context([candidate])

    assert "ingredients" not in context[0]
    assert "instructions" not in context[0]
    assert context[0]["ingredient_anchors"] == ["tofu", "rice"]

