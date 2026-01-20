"""
Kwiff WebSocket Client
A standalone Python implementation for fetching live sports event data from Kwiff

Main exports:
- KwiffClient: Low-level WebSocket client
- initialize_kwiff: High-level integration function (fetches and maps events)
- fetch_and_save_events: Fetch events from Kwiff WebSocket
- map_kwiff_events: Map Kwiff events to Betfair market IDs
- get_betfair_id_for_kwiff_event: Look up Betfair ID for a Kwiff event
"""

from .kwiff_client import KwiffClient
from .integration import (
    initialize_kwiff,
    initialize_kwiff_sync,
    fetch_and_save_events,
    map_kwiff_events,
    get_kwiff_event_mappings,
    get_betfair_id_for_kwiff_event,
)

__version__ = "1.0.0"
__all__ = [
    "KwiffClient",
    "initialize_kwiff",
    "initialize_kwiff_sync",
    "fetch_and_save_events",
    "map_kwiff_events",
    "get_kwiff_event_mappings",
    "get_betfair_id_for_kwiff_event",
]
