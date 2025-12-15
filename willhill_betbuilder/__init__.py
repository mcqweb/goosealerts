"""
William Hill Bet Builder Module

A Python module for generating and pricing William Hill bet builder combinations.

Usage:
    from willhill_betbuilder import BetBuilderClient, Config
    
    # Configure
    Config.set_session_cookie("YOUR_SESSION_COOKIE")
    Config.set_proxy(http_proxy="http://localhost:8080")
    
    # Create client
    client = BetBuilderClient()
    
    # Get combinations
    combos = client.get_player_combinations("OB_EV37926026", "Joshua Zirkzee", "Man Utd")
    
    # Get pricing
    for combo in combos:
        price = client.get_price(combo)
        print(f"{combo['template']}: {price}")
"""

from .config import Config
from .client import BetBuilderClient
from .simple import (
    get_odds,
    get_odds_detailed,
    get_multiple_odds,
    get_available_bet_types,
    configure,
    BET_TYPES
)

__version__ = "1.0.0"
__all__ = [
    "BetBuilderClient",
    "Config",
    "get_odds",
    "get_odds_detailed",
    "get_multiple_odds",
    "get_available_bet_types",
    "configure",
    "BET_TYPES"
]
