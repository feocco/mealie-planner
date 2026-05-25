from __future__ import annotations

import json
from typing import Any

import httpx
from openai import AsyncOpenAI

from mealie_planner.selection.rules import build_compact_context
from mealie_planner.selection.schema import MealPlanDraft, PlannerInput


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "meals": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "date": {"type": "string", "format": "date"},
                    "recipe_id": {"type": "string"},
                    "title": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["date", "recipe_id", "title", "rationale"],
            },
        },
        "rationale": {"type": "string"},
    },
    "required": ["meals", "rationale"],
}


SYSTEM_PROMPT = """You choose realistic household dinner plans from a compact Mealie recipe list.
Return only the requested structured JSON. Do not invent recipe ids. Respect blocked dates.
Prefer practical weeknight cooking, weather fit, user guidance, and useful variety."""


class OpenAISelector:
    def __init__(self, *, api_key: str | None = None, model: str, client: Any | None = None) -> None:
        self.client = client or AsyncOpenAI(api_key=api_key, http_client=httpx.AsyncClient(trust_env=False))
        self.model = model

    async def select(self, planner_input: PlannerInput) -> MealPlanDraft:
        response = await self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(build_prompt_payload(planner_input), default=str)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "meal_plan",
                    "schema": PLAN_SCHEMA,
                    "strict": True,
                }
            },
        )
        payload = json.loads(response.output_text)
        return MealPlanDraft(
            plan_id="pending",
            meals=payload["meals"],
            rationale=payload["rationale"],
            candidate_ids={candidate.id for candidate in planner_input.candidates},
            expected_dates=set(planner_input.target_dates),
        )


def build_prompt_payload(planner_input: PlannerInput) -> dict[str, Any]:
    return {
        "target_dates": [day.isoformat() for day in planner_input.target_dates],
        "guidance": planner_input.guidance,
        "blocked_dates": [day.isoformat() for day in sorted(planner_input.blocked_dates)],
        "weather": planner_input.weather.model_dump(mode="json"),
        "feedback_history": planner_input.feedback_history,
        "recipes": build_compact_context(planner_input.candidates),
    }
