from datetime import date

import pytest
from pydantic import ValidationError

from mealie_planner.selection.schema import MealPlanDraft, PlanMeal


def meal(day: int, recipe_id: str = "r1") -> PlanMeal:
    return PlanMeal(
        date=date(2026, 5, day),
        recipe_id=recipe_id,
        title=f"Recipe {recipe_id}",
        rationale="Fits the plan.",
    )


def test_plan_validation_rejects_duplicate_dates() -> None:
    with pytest.raises(ValidationError):
        MealPlanDraft(
            plan_id="plan",
            meals=[meal(25, "r1"), meal(25, "r2")],
            rationale="Duplicate dates should fail.",
            candidate_ids={"r1", "r2"},
            expected_dates={date(2026, 5, 25)},
        )


def test_plan_validation_rejects_unknown_recipe_ids() -> None:
    with pytest.raises(ValidationError):
        MealPlanDraft(
            plan_id="plan",
            meals=[meal(25, "missing")],
            rationale="Unknown recipe should fail.",
            candidate_ids={"r1"},
            expected_dates={date(2026, 5, 25)},
        )


def test_plan_validation_rejects_missing_dinners() -> None:
    with pytest.raises(ValidationError):
        MealPlanDraft(
            plan_id="plan",
            meals=[meal(25, "r1")],
            rationale="Missing requested date should fail.",
            candidate_ids={"r1"},
            expected_dates={date(2026, 5, 25), date(2026, 5, 26)},
        )

