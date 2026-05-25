from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecipeCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    title: str
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    servings: int | None = None
    ingredient_anchors: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list, exclude=True)
    instructions: list[str] = Field(default_factory=list, exclude=True)


class WeatherContext(BaseModel):
    location: str = "Auburn, NY"
    weather_unavailable: bool = False
    daily: list[dict[str, Any]] = Field(default_factory=list)


class PlannerInput(BaseModel):
    target_dates: list[date]
    guidance: str = ""
    blocked_dates: set[date] = Field(default_factory=set)
    weather: WeatherContext
    candidates: list[RecipeCandidate]
    feedback_history: list[str] = Field(default_factory=list)


class PlanMeal(BaseModel):
    date: date
    recipe_id: str
    title: str
    rationale: str


class MealPlanDraft(BaseModel):
    plan_id: str
    meals: list[PlanMeal]
    rationale: str
    candidate_ids: set[str] = Field(default_factory=set)
    expected_dates: set[date] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_plan(self) -> "MealPlanDraft":
        dates = [meal.date for meal in self.meals]
        if len(dates) != len(set(dates)):
            raise ValueError("meal plan has duplicate dates")
        unknown = sorted({meal.recipe_id for meal in self.meals} - self.candidate_ids)
        if unknown:
            raise ValueError(f"meal plan contains unknown recipe ids: {', '.join(unknown)}")
        missing = sorted(self.expected_dates - set(dates))
        if missing:
            missing_text = ", ".join(day.isoformat() for day in missing)
            raise ValueError(f"meal plan is missing requested dates: {missing_text}")
        return self


class AcceptResult(BaseModel):
    plan_id: str
    created_entry_ids: list[str]
