from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from mealie_planner.selection.rules import choose_plan_dates, prefilter_recipes
from mealie_planner.selection.schema import AcceptResult, MealPlanDraft, PlannerInput
from mealie_planner.state import PlannerStore


class SuggestRequest(BaseModel):
    start_date: date
    day_count: int = 7
    dinner_count: int = 4
    blocked_dates: set[date] = Field(default_factory=set)
    guidance: str = ""


class PlannerService:
    def __init__(
        self,
        *,
        store: PlannerStore,
        recipe_source: Any,
        selector: Any,
        weather: Any,
        notifier: Any,
    ) -> None:
        self.store = store
        self.recipe_source = recipe_source
        self.selector = selector
        self.weather = weather
        self.notifier = notifier

    @classmethod
    def for_testing(
        cls,
        *,
        data_dir: str | Path,
        recipe_source: Any,
        selector: Any,
        weather: Any,
        notifier: Any,
    ) -> "PlannerService":
        return cls(
            store=PlannerStore(Path(data_dir) / "planner.sqlite3"),
            recipe_source=recipe_source,
            selector=selector,
            weather=weather,
            notifier=notifier,
        )

    async def suggest(
        self,
        request: SuggestRequest,
        *,
        parent_plan_id: str | None = None,
        feedback_history: list[str] | None = None,
        recipient: str = "joe",
    ) -> MealPlanDraft:
        target_dates = choose_plan_dates(
            start_date=request.start_date,
            day_count=request.day_count,
            dinner_count=request.dinner_count,
            blocked_dates=request.blocked_dates,
        )
        recipes = await self.recipe_source.list_recipes()
        weather = await self.weather.get_weather(request.start_date, request.day_count)
        candidates = prefilter_recipes(recipes, guidance=request.guidance, weather=weather)
        planner_input = PlannerInput(
            target_dates=target_dates,
            guidance=request.guidance,
            blocked_dates=request.blocked_dates,
            weather=weather,
            candidates=candidates,
            feedback_history=feedback_history or [],
        )
        draft = await self.selector.select(planner_input)
        draft.plan_id = uuid4().hex
        self.store.save_plan(
            draft.plan_id,
            request=request.model_dump(mode="json"),
            draft=draft.model_dump(mode="json"),
            parent_plan_id=parent_plan_id,
            status=f"draft_for_{recipient}",
        )
        if self.notifier is not None:
            await self.notifier.send_plan(draft, recipient=recipient)
        return draft

    async def regenerate(self, plan_id: str, feedback: str | None = None, *, reviewer: str = "joe") -> MealPlanDraft:
        original = self.store.get_plan(plan_id)
        if feedback:
            self.store.record_feedback(plan_id, feedback)
        request = SuggestRequest.model_validate(original["request"])
        return await self.suggest(
            request,
            parent_plan_id=plan_id,
            feedback_history=self.store.list_feedback(plan_id),
            recipient=reviewer,
        )

    async def accept(self, plan_id: str, *, reviewer: str = "joe") -> AcceptResult:
        stored = self.store.get_plan(plan_id)
        status = str(stored["status"])
        if reviewer == "joe" and status != "draft_for_joe":
            raise RuntimeError("Joe can only accept a draft_for_joe plan")
        if reviewer == "jess" and status not in {"joe_accepted", "draft_for_jess"}:
            raise RuntimeError("Jess can only accept a Joe-accepted or draft_for_jess plan")
        if reviewer not in {"joe", "jess"}:
            raise RuntimeError(f"Unknown reviewer: {reviewer}")

        draft = MealPlanDraft.model_validate(stored["draft"])
        start = min(meal.date for meal in draft.meals)
        end = max(meal.date for meal in draft.meals) + timedelta(days=1)
        existing_entry_ids = (
            self.store.list_created_entries(plan_id)
            if reviewer == "joe"
            else self.store.list_created_entries_for_family(plan_id)
        )
        planner_entry_ids = set(existing_entry_ids)
        existing = await self.recipe_source.list_mealplans(start, end)
        human_conflicts = [
            item
            for item in existing
            if item.get("entryType") == "dinner" and str(item.get("id")) not in planner_entry_ids
        ]
        if human_conflicts:
            raise RuntimeError("Refusing to overwrite human-created Mealie dinner entries")

        for entry_id in existing_entry_ids:
            await self.recipe_source.delete_mealplan(entry_id)

        created: list[dict[str, str]] = []
        for meal in draft.meals:
            entry = await self.recipe_source.create_dinner_plan(
                meal_date=meal.date,
                recipe_id=meal.recipe_id,
                title=meal.title,
                text=f"Generated by mealie-planner plan {plan_id}: {meal.rationale}",
            )
            entry_id = str(entry.get("id"))
            created.append({"entry_id": entry_id, "date": meal.date.isoformat(), "recipe_id": meal.recipe_id})
        accepted_status = "joe_accepted" if reviewer == "joe" else "jess_accepted"
        self.store.mark_accepted(plan_id, created, status=accepted_status)
        if self.notifier is not None:
            if reviewer == "joe":
                await self.notifier.send_plan(draft, recipient="jess")
            else:
                await self.notifier.send_jess_accepted(draft)
        return AcceptResult(plan_id=plan_id, created_entry_ids=[entry["entry_id"] for entry in created])

    async def dismiss(self, plan_id: str) -> None:
        self.store.mark_dismissed(plan_id)
