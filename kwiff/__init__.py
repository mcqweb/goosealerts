"""
Kwiff WebSocket Client
A standalone Python implementation for fetching live sports event data from Kwiff

Main exports:
- KwiffClient: Low-level WebSocket client
- initialize_kwiff: High-level integration function (fetches and maps events)
- fetch_and_save_events: Fetch events from Kwiff WebSocket
- map_kwiff_events: Map Kwiff events to Betfair market IDs
- get_betfair_id_for_kwiff_event: Look up Betfair ID for a Kwiff event

Match Details & Caching:
- fetch_match_details_sync: Fetch and cache detailed match data
- get_cached_match_details: Get cached match details
- cache_match_details: Cache match details manually
- clear_expired_cache: Clean up old cache entries

Player Market Helpers:
- get_player_markets: Extract player markets from cached data
- get_player_market_odds: Get odds for specific player market
- build_combo_data: Build combo structure for betting
- is_market_available: Check if market is available
"""

from .kwiff_client import KwiffClient
from .integration import (
    initialize_kwiff,
    initialize_kwiff_sync,
    fetch_and_save_events,
    map_kwiff_events,
    get_kwiff_event_mappings,
    get_betfair_id_for_kwiff_event,
    fetch_match_details_for_mapped_events,
    fetch_match_details_sync,
)
from .match_cache import (
    get_cached_match_details,
    cache_match_details,
    clear_expired_cache,
    get_cache,
)
from .player_helpers import (
    get_player_markets,
    get_player_market_odds,
    build_combo_data,
    is_market_available,
    find_player_in_match,
    get_all_players_in_match,
)

__version__ = "1.1.0"
__all__ = [
    # Client
    "KwiffClient",
    
    # Initialization
    "initialize_kwiff",
    "initialize_kwiff_sync",
    "fetch_and_save_events",
    "map_kwiff_events",
    
    # Event Mappings
    "get_kwiff_event_mappings",
    "get_betfair_id_for_kwiff_event",
    
    # Match Details
    "fetch_match_details_for_mapped_events",
    "fetch_match_details_sync",
    "get_cached_match_details",
    "cache_match_details",
    "clear_expired_cache",
    "get_cache",
    
    # Player Helpers
    "get_player_markets",
    "get_player_market_odds",
    "build_combo_data",
    "is_market_available",
    "find_player_in_match",
    "get_all_players_in_match",
]
