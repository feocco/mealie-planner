from datetime import date
import json

import pytest

from mealie_planner.selection.openai_selector import OpenAISelector
from mealie_planner.selection.schema import PlannerInput, RecipeCandidate, WeatherContext


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        payload = {
            "meals": [
                {
                    "date": "2026-05-25",
                    "recipe_id": "r1",
                    "title": "Tofu Tikka Masala",
                    "rationale": "Matches the tofu guidance.",
                }
            ],
            "rationale": "A balanced compact plan.",
        }

        class Response:
            output_text = json.dumps(payload)

        return Response()


class FakeOpenAI:
    def __init__(self):
        self.responses = FakeResponses()


@pytest.mark.asyncio
async def test_openai_selector_uses_structured_output_and_compact_context() -> None:
    client = FakeOpenAI()
    selector = OpenAISelector(client=client, model="test-model")
    planner_input = PlannerInput(
        target_dates=[date(2026, 5, 25)],
        guidance="tofu",
        weather=WeatherContext(location="Auburn, NY", weather_unavailable=True, daily=[]),
        candidates=[
            RecipeCandidate(
                id="r1",
                slug="tofu-tikka-masala",
                title="Tofu Tikka Masala",
                categories=["Dinner"],
                tags=["Indian"],
                tools=[],
                ingredient_anchors=["tofu"],
                ingredients=["full ingredient text should not be sent"],
                instructions=["full instruction text should not be sent"],
            )
        ],
    )

    draft = await selector.select(planner_input)

    assert draft.meals[0].recipe_id == "r1"
    sent = json.dumps(client.responses.kwargs)
    assert "json_schema" in sent
    assert "full ingredient text should not be sent" not in sent
    assert "full instruction text should not be sent" not in sent


def test_openai_selector_default_client_ignores_ambient_proxy_env(monkeypatch) -> None:
    monkeypatch.setenv("NO_PROXY", "fd07:b51a:cc66:f0::/64")

    selector = OpenAISelector(api_key="sk-test", model="test-model")

    assert selector.client._client._trust_env is False
