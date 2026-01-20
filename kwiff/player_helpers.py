#!/usr/bin/env python3
"""
Kwiff Player Data Helpers

Functions to extract player markets and build combo data from cached Kwiff match details.
Used for building AGS, Two or More, and Hat-trick combos when opportunities are found.
"""

from typing import Dict, List, Optional, Any
from .match_cache import get_cached_match_details


def get_player_markets(kwiff_event_id: str) -> Optional[Dict[str, List[Dict]]]:
    """
    Extract player markets from cached match details.
    
    Args:
        kwiff_event_id: Kwiff event ID
        
    Returns:
        Dict with player names as keys and their available markets:
        {
            "Player Name": [
                {
                    "market_type": "AGS",
                    "market_id": "123",
                    "odds": 5.0,
                    "selection_id": "456",
                    ...
                },
                ...
            ],
            ...
        }
        None if not cached or no player markets found
    """
    details = get_cached_match_details(str(kwiff_event_id))
    
    if not details:
        return None
    
    # TODO: Parse the actual structure of Kwiff event details
    # This will depend on what the event:get response looks like
    # For now, return a placeholder structure
    
    player_markets = {}
    
    # Expected structure (to be confirmed):
    # details['data']['markets'] or similar
    # details['data']['players'] or similar
    
    return player_markets if player_markets else None


def find_player_in_match(kwiff_event_id: str, player_name: str) -> Optional[Dict]:
    """
    Find a specific player in cached match details.
    
    Args:
        kwiff_event_id: Kwiff event ID
        player_name: Player name to search for
        
    Returns:
        Player data dict or None if not found
    """
    details = get_cached_match_details(str(kwiff_event_id))
    
    if not details:
        return None
    
    # TODO: Implement actual player search based on response structure
    # This will need fuzzy matching similar to player name consolidation
    
    return None


def get_player_market_odds(
    kwiff_event_id: str,
    player_name: str,
    market_type: str
) -> Optional[Dict]:
    """
    Get odds for a specific player market (AGS, TOM, HAT).
    
    Args:
        kwiff_event_id: Kwiff event ID
        player_name: Player name
        market_type: Market type ('AGS', 'TOM', 'HAT')
        
    Returns:
        Dict with odds data:
        {
            'odds': float,
            'market_id': str,
            'selection_id': str,
            'available': bool
        }
        None if not found
    """
    player_markets = get_player_markets(kwiff_event_id)
    
    if not player_markets or player_name not in player_markets:
        return None
    
    # Find the specific market type
    for market in player_markets[player_name]:
        if market.get('market_type') == market_type:
            return {
                'odds': market.get('odds'),
                'market_id': market.get('market_id'),
                'selection_id': market.get('selection_id'),
                'available': True
            }
    
    return None


def build_combo_data(
    kwiff_event_id: str,
    player_name: str,
    market_type: str
) -> Optional[Dict]:
    """
    Build combo data structure for placing a bet.
    
    This is the data needed to construct a Kwiff combo bet for
    AGS, Two or More, or Hat-trick markets.
    
    Args:
        kwiff_event_id: Kwiff event ID
        player_name: Player name
        market_type: Market type ('AGS', 'TOM', 'HAT')
        
    Returns:
        Dict with combo structure or None if not available
    """
    odds_data = get_player_market_odds(kwiff_event_id, player_name, market_type)
    
    if not odds_data:
        return None
    
    # Build combo structure
    combo = {
        'event_id': kwiff_event_id,
        'player_name': player_name,
        'market_type': market_type,
        'odds': odds_data['odds'],
        'market_id': odds_data['market_id'],
        'selection_id': odds_data['selection_id'],
        'available': odds_data['available']
    }
    
    return combo


def get_all_players_in_match(kwiff_event_id: str) -> List[str]:
    """
    Get list of all players available in a match.
    
    Args:
        kwiff_event_id: Kwiff event ID
        
    Returns:
        List of player names
    """
    player_markets = get_player_markets(kwiff_event_id)
    
    if not player_markets:
        return []
    
    return list(player_markets.keys())


def is_market_available(
    kwiff_event_id: str,
    player_name: str,
    market_type: str
) -> bool:
    """
    Check if a specific player market is available.
    
    Args:
        kwiff_event_id: Kwiff event ID
        player_name: Player name
        market_type: Market type ('AGS', 'TOM', 'HAT')
        
    Returns:
        True if market is available
    """
    odds_data = get_player_market_odds(kwiff_event_id, player_name, market_type)
    return odds_data is not None and odds_data.get('available', False)


# Example usage
if __name__ == "__main__":
    print("Kwiff Player Data Helpers")
    print("\nThese functions extract player markets from cached match details.")
    print("They will need to be updated once we see the actual event:get response structure.")
    print("\nExample usage:")
    print("""
    from kwiff.player_helpers import get_player_market_odds, build_combo_data
    
    # Get odds for a player
    odds = get_player_market_odds(
        kwiff_event_id="10748848",
        player_name="Erling Haaland",
        market_type="AGS"
    )
    
    # Build combo data
    combo = build_combo_data(
        kwiff_event_id="10748848",
        player_name="Erling Haaland",
        market_type="AGS"
    )
    """)
