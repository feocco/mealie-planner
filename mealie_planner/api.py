from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException

from mealie_planner.event_listener import run_action_listener
from mealie_planner.service import PlannerService, SuggestRequest


def create_app(service: PlannerService, *, start_action_listener: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        listener_task: asyncio.Task | None = None
        if start_action_listener:
            listener_task = asyncio.create_task(run_action_listener(service), name="mealie-planner-ha-actions")
        try:
            yield
        finally:
            if listener_task is not None:
                listener_task.cancel()
                with suppress(asyncio.CancelledError):
                    await listener_task

    app = FastAPI(title="Mealie Planner", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/plans/suggest")
    async def suggest(request: SuggestRequest):
        return await service.suggest(request)

    @app.get("/v1/plans/latest/ingredients")
    async def get_latest_plan_ingredients():
        try:
            return await service.latest_plan_ingredients()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="accepted plan not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/plans/{plan_id}")
    async def get_plan(plan_id: str):
        try:
            return service.store.get_plan(plan_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="plan not found") from exc

    @app.get("/v1/plans/{plan_id}/ingredients")
    async def get_plan_ingredients(plan_id: str):
        try:
            return await service.plan_ingredients(plan_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="plan not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/v1/plans/{plan_id}/accept")
    async def accept(plan_id: str):
        return await service.accept(plan_id)

    @app.post("/v1/plans/{plan_id}/regenerate")
    async def regenerate(plan_id: str, payload: dict[str, str] | None = None):
        return await service.regenerate(plan_id, (payload or {}).get("feedback"))

    @app.post("/v1/plans/{plan_id}/dismiss")
    async def dismiss(plan_id: str):
        await service.dismiss(plan_id)
        return {"status": "dismissed"}

    return app
