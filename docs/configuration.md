# Configuration

Runtime config is environment-based. Secrets belong in `.env.local` for local development or the homelab secret flow for deployment.

| Variable | Required | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | yes | OpenAI API key for plan generation. |
| `OPENAI_MODEL` | no | Defaults to `gpt-5.4-mini`; use a stronger model when plan quality needs review. |
| `MEALIE_BASE_URL` | yes | Local Mealie URL reachable from the container, usually `http://host.docker.internal:9925`. |
| `MEALIE_PUBLIC_URL` | no | User-facing Mealie URL used in notifications. |
| `MEALIE_API_TOKEN` | yes | Mealie API token for reading recipes and writing accepted meal plans. |
| `HA_URL` | yes | Home Assistant base URL for WebSocket access. |
| `HA_LONG_LIVED_TOKEN` | yes | Home Assistant token for weather and notification action events. |
| `HA_WEATHER_ENTITY_ID` | no | Reviewed weather entity. If omitted, the service tries the first `weather.*` entity. |
| `HOMELAB_FUNCTIONS_URL` | yes | Notification broker URL. |
| `HOMELAB_FUNCTIONS_TOKEN` | yes | Notification broker token. |
| `HOUSEHOLD_LOCATION` | no | Defaults to `Auburn, NY`. |
| `DATA_DIR` | no | Defaults to `data`. Stores local SQLite plan history. |
| `HOST` / `PORT` | no | Defaults to `0.0.0.0:8080`. |

If Home Assistant weather is unavailable, planning still runs with `weather_unavailable=true`; the service does not silently call a public weather API.
