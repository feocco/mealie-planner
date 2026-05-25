# Security

This service is internal-only in V1. It should not receive a public Cloudflare hostname.

Trust boundaries:

- OpenAI receives compact recipe metadata and planning guidance, not full recipe bodies by default.
- Mealie API token can read recipes and create/delete meal planner entries. Keep it secret.
- Home Assistant token can read states and subscribe to mobile app action events. Keep it secret.
- `homelab-functions` token can send phone notifications. Keep it secret.

The app only writes to Mealie after explicit acceptance through the API or phone notification. It refuses to overwrite dinner entries that do not look like planner-created entries.

Local draft history is stored in SQLite under `DATA_DIR`. It may contain prompt payloads, recipe titles, tags, and user feedback, but must not contain API keys.

