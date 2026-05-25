from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from mealie_planner.selection.schema import RecipeCandidate


class MealieClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.http = http

    async def list_recipes(self) -> list[RecipeCandidate]:
        items: list[dict[str, Any]] = []
        page = 1
        async with self._client() as http:
            while True:
                response = await http.get("/api/recipes", params={"page": page, "perPage": 100})
                response.raise_for_status()
                payload = response.json()
                page_items = payload.get("items", payload if isinstance(payload, list) else [])
                items.extend(page_items)
                total_pages = int(payload.get("total_pages") or payload.get("totalPages") or page)
                if page >= total_pages:
                    break
                page += 1
        return [recipe_candidate(item) for item in items]

    async def list_mealplans(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        async with self._client() as http:
            response = await http.get(
                "/api/households/mealplans",
                params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("items", payload if isinstance(payload, list) else [])

    async def create_dinner_plan(self, *, meal_date: date, recipe_id: str, title: str, text: str) -> dict[str, Any]:
        payload = {
            "date": meal_date.isoformat(),
            "entryType": "dinner",
            "title": title,
            "text": text,
            "recipeId": recipe_id,
        }
        async with self._client() as http:
            response = await http.post("/api/households/mealplans", json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_mealplan(self, entry_id: str) -> None:
        async with self._client() as http:
            response = await http.delete(f"/api/households/mealplans/{entry_id}")
            response.raise_for_status()

    def _client(self) -> httpx.AsyncClient:
        if self.http is not None:
            return _BorrowedClient(self.http, self.api_token)  # type: ignore[return-value]
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"},
            timeout=30,
            trust_env=False,
        )


class _BorrowedClient:
    def __init__(self, client: httpx.AsyncClient, api_token: str) -> None:
        self.client = client
        self.api_token = api_token

    async def __aenter__(self) -> httpx.AsyncClient:
        self.client.headers.update({"Authorization": f"Bearer {self.api_token}", "Accept": "application/json"})
        return self.client

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


def recipe_candidate(item: dict[str, Any]) -> RecipeCandidate:
    return RecipeCandidate(
        id=str(item.get("id") or item.get("slug")),
        slug=str(item.get("slug") or item.get("id")),
        title=str(item.get("name") or item.get("title") or item.get("slug")),
        categories=names(item.get("recipeCategory") or item.get("categories")),
        tags=names(item.get("tags")),
        tools=names(item.get("tools")),
        servings=item.get("recipeServings") or item.get("servings"),
        ingredient_anchors=ingredient_anchors(item),
    )


def names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, dict):
            name = value.get("name")
        else:
            name = str(value)
        if name:
            result.append(str(name))
    return result


def ingredient_anchors(item: dict[str, Any]) -> list[str]:
    values = item.get("recipeIngredient") or item.get("ingredients") or []
    anchors: list[str] = []
    if isinstance(values, list):
        for value in values[:12]:
            if isinstance(value, dict):
                food = value.get("food") or {}
                name = food.get("name") if isinstance(food, dict) else value.get("note")
            else:
                name = str(value)
            if name:
                anchors.append(str(name))
    return anchors
