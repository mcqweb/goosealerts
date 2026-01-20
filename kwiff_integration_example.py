"""
Example: How to integrate Kwiff into virgin_goose.py

This file shows the recommended integration pattern for adding Kwiff
support to the main goosealerts script.
"""

# ============================================================================
# STEP 1: Add imports at the top of virgin_goose.py
# ============================================================================

# Add this near the other imports:
from kwiff import initialize_kwiff_sync, get_betfair_id_for_kwiff_event

# ============================================================================
# STEP 2: Initialize Kwiff on startup (inside main() before the main loop)
# ============================================================================

def main():
    betfair = Betfair()
    clear_cache()
    active_comps = betfair.get_active_whitelisted_competitions()
    
    # NEW: Initialize Kwiff integration
    # This fetches featured matches and maps them to Betfair IDs
    print("\n[INIT] Initializing Kwiff integration...")
    try:
        kwiff_result = initialize_kwiff_sync(country="GB", dry_run=False)
        if kwiff_result['overall_success']:
            print("[INIT] ✅ Kwiff integration ready")
        else:
            print("[INIT] ⚠️ Kwiff integration had issues (continuing anyway)")
    except Exception as e:
        print(f"[INIT] ⚠️ Kwiff initialization failed: {e}")
        print("[INIT] Continuing without Kwiff integration")
    
    # Continue with existing code...
    run_start_date = datetime.now(london).date()
    run_number = load_run_counter()
    
    while True:
        # Main loop...
        pass

# ============================================================================
# STEP 3: Use Kwiff data in the main loop (optional)
# ============================================================================

# Later in the main loop, you can check if a match has Kwiff data available:

def check_kwiff_availability(match_id, match_name):
    """
    Check if a Betfair match has Kwiff odds available.
    Returns the Kwiff event ID if found, None otherwise.
    """
    from kwiff import get_kwiff_event_mappings
    
    # Get all mappings
    mappings = get_kwiff_event_mappings()
    
    # Look for this Betfair market ID in the mappings
    for kwiff_id, data in mappings.items():
        betfair_id = data.get('betfair_id')
        if betfair_id == str(match_id):
            print(f"[KWIFF] Match {match_name} is available on Kwiff (ID: {kwiff_id})")
            return kwiff_id
    
    return None

# ============================================================================
# STEP 4: Example usage in the main loop
# ============================================================================

# Inside the main loop where you process matches:
"""
for m in matches:
    mid = m.get('id')
    mname = m.get('name')
    
    # ... existing code ...
    
    # NEW: Check if this match is available on Kwiff
    kwiff_id = check_kwiff_availability(mid, mname)
    if kwiff_id:
        print(f"[KWIFF] This match has Kwiff odds available")
        # TODO: In the future, fetch odds from Kwiff WebSocket for:
        #   - Anytime Goalscorer (AGS lay available)
        #   - Two or More goals
        #   - Hat-trick
        # For now, we just know the match is available
"""

# ============================================================================
# STEP 5: Future enhancement - Request odds from Kwiff WebSocket
# ============================================================================

async def get_kwiff_player_odds(kwiff_event_id, player_name, market_type):
    """
    Future function to request player odds from Kwiff via WebSocket.
    
    Args:
        kwiff_event_id: Kwiff event ID
        player_name: Player name to get odds for
        market_type: Type of market (e.g., 'AGS', 'TOM', 'HAT')
    
    Returns:
        Dict with odds data or None
    
    TODO: Implement WebSocket command to request specific player odds
    """
    from kwiff import KwiffClient
    
    async with KwiffClient() as client:
        # TODO: Determine the correct WebSocket command for player odds
        # This will likely be something like:
        # response = await client.send_command(
        #     message="player:odds",
        #     payload={
        #         "eventId": kwiff_event_id,
        #         "playerName": player_name,
        #         "marketType": market_type
        #     }
        # )
        # return response
        pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# Add these environment variables to .env:
"""
# Kwiff Integration
ENABLE_KWIFF=1                    # Enable/disable Kwiff integration
KWIFF_COUNTRY=GB                  # Country code for Kwiff events
KWIFF_REFRESH_MINUTES=60          # How often to refresh Kwiff events
"""

# Add to virgin_goose.py config section:
"""
ENABLE_KWIFF = os.getenv("ENABLE_KWIFF", "1") == "1"
KWIFF_COUNTRY = os.getenv("KWIFF_COUNTRY", "GB")
KWIFF_REFRESH_MINUTES = int(os.getenv("KWIFF_REFRESH_MINUTES", "60"))
"""
