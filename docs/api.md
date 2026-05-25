# API Usage

Mealie Planner is an internal FastAPI service. In production, agents should call
the Mac mini planner service, not the Cloudflare-protected Mealie UI hostname.

## Plan Workflow

- `POST /v1/plans/suggest` creates a draft and sends the first notification.
- `GET /v1/plans/{plan_id}` returns stored request, draft, status, and write metadata.
- `POST /v1/plans/{plan_id}/accept` accepts the current reviewer stage and writes planner-owned dinner entries to Mealie.
- `POST /v1/plans/{plan_id}/regenerate` creates a replacement draft from optional feedback.
- `POST /v1/plans/{plan_id}/dismiss` marks a draft dismissed.

Accepted plan statuses are `joe_accepted` and `jess_accepted`.

## Ingredients

- `GET /v1/plans/{plan_id}/ingredients` returns ingredients for an accepted plan.
- `GET /v1/plans/latest/ingredients` returns ingredients for the most recently accepted plan.
- The response includes `by_recipe` and conservative `consolidated` views.
- Consolidation only sums exact structured matches; it does not convert units.
- This endpoint is read-only. It does not modify Mealie, send notifications, or create grocery lists.

Use the latest accepted plan endpoint when chaining into grocery services that do
not need a user to manually copy a plan id.
