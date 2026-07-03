from datetime import date

from fastapi.testclient import TestClient

from mealie_planner.api import create_app
from mealie_planner.service import PlannerService
from tests.test_service import FakeNotifier, FakeRecipeSource, FakeSelector, FakeWeather


def test_api_suggest_and_get_plan(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))

    response = client.post(
        "/v1/plans/suggest",
        json={"start_date": date(2026, 5, 25).isoformat(), "dinner_count": 1},
    )

    assert response.status_code == 200
    plan_id = response.json()["plan_id"]
    assert client.get(f"/v1/plans/{plan_id}").json()["plan_id"] == plan_id


def test_api_plan_ingredients_requires_accepted_plan(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))
    plan_id = client.post(
        "/v1/plans/suggest",
        json={"start_date": date(2026, 5, 25).isoformat(), "dinner_count": 1},
    ).json()["plan_id"]

    response = client.get(f"/v1/plans/{plan_id}/ingredients")

    assert response.status_code == 409
    assert "accepted" in response.json()["detail"]


def test_api_latest_plan_ingredients_returns_latest_accepted_plan(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))
    plan_id = client.post(
        "/v1/plans/suggest",
        json={"start_date": date(2026, 5, 25).isoformat(), "dinner_count": 1},
    ).json()["plan_id"]
    assert client.post(f"/v1/plans/{plan_id}/accept").status_code == 200

    response = client.get("/v1/plans/latest/ingredients")

    assert response.status_code == 200
    assert response.json()["plan_id"] == plan_id
    assert response.json()["consolidated"][0]["food_name"] == "tofu"


def test_api_latest_plan_ingredients_returns_404_without_accepted_plan(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))

    response = client.get("/v1/plans/latest/ingredients")

    assert response.status_code == 404
    assert response.json()["detail"] == "accepted plan not found"


def test_api_docs_serves_html(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))

    response = client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<!DOCTYPE html>" in response.text


def test_api_openapi_serves_openapi_31_json(tmp_path) -> None:
    service = PlannerService.for_testing(
        data_dir=tmp_path,
        recipe_source=FakeRecipeSource(),
        selector=FakeSelector(),
        weather=FakeWeather(),
        notifier=FakeNotifier(),
    )
    client = TestClient(create_app(service))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["openapi"] == "3.1.0"
    assert payload["info"]["title"] == "Mealie Planner"
    assert "/health" in payload["paths"]
