from datetime import date

import httpx
import pytest

from mealie_planner.mealie_client import MealieClient


@pytest.mark.asyncio
async def test_mealie_client_maps_recipe_summaries_to_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "r1",
                        "slug": "tofu-tikka-masala",
                        "name": "Tofu Tikka Masala",
                        "recipeCategory": [{"name": "Dinner"}],
                        "tags": [{"name": "Indian"}, {"name": "Tofu"}],
                        "tools": [],
                        "recipeServings": 4,
                    }
                ],
                "page": 1,
                "total_pages": 1,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://mealie.test") as http:
        client = MealieClient(base_url="http://mealie.test", api_token="token", http=http)
        recipes = await client.list_recipes()

    assert recipes[0].slug == "tofu-tikka-masala"
    assert recipes[0].categories == ["Dinner"]
    assert recipes[0].tags == ["Indian", "Tofu"]


@pytest.mark.asyncio
async def test_mealie_client_creates_dinner_plan_entry() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"id": "entry-1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://mealie.test") as http:
        client = MealieClient(base_url="http://mealie.test", api_token="token", http=http)
        result = await client.create_dinner_plan(
            meal_date=date(2026, 5, 25),
            recipe_id="r1",
            title="Tofu Tikka Masala",
            text="Generated",
        )

    assert result["id"] == "entry-1"
    assert requests[0].url.path == "/api/households/mealplans"
    assert requests[0].read() == b'{"date":"2026-05-25","entryType":"dinner","title":"Tofu Tikka Masala","text":"Generated","recipeId":"r1"}'


def test_mealie_client_ignores_ambient_proxy_environment() -> None:
    client = MealieClient(base_url="http://host.docker.internal:9925", api_token="token")

    http = client._client()

    assert http.trust_env is False


@pytest.mark.asyncio
async def test_mealie_client_fetches_recipe_detail_without_losing_ingredient_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/recipes/r1"
        return httpx.Response(
            200,
            json={
                "id": "r1",
                "name": "Tofu Tikka Masala",
                "recipeIngredient": [
                    {
                        "quantity": 1.0,
                        "unit": {"id": "u1", "name": "block"},
                        "food": {"id": "f1", "name": "tofu"},
                        "note": "pressed",
                        "display": "1 block tofu, pressed",
                        "originalText": "1 block tofu, pressed",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://mealie.test") as http:
        client = MealieClient(base_url="http://mealie.test", api_token="token", http=http)
        detail = await client.get_recipe_detail("r1")

    ingredient = detail["recipeIngredient"][0]
    assert ingredient["display"] == "1 block tofu, pressed"
    assert ingredient["originalText"] == "1 block tofu, pressed"
