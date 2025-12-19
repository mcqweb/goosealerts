# ladbrokes_alerts

Minimal template package to integrate Ladbrokes alerts into `virgin_goose.py`.

Quick start

- Import: `from ladbrokes_alerts.client import LadbrokesAlerts`
- Create: `client = LadbrokesAlerts()`
- Test connectivity: `client.ping()`

Notes

- This is a template: replace endpoints and auth as needed for the real Ladbrokes API.
- The module uses `requests`; add it to your environment if missing.
