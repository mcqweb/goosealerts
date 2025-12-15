"""
Simple Odds Fetcher - Easy integration for existing projects

This module provides a simple function-based interface for getting odds.
Perfect for integrating into existing scripts.
"""

from .client import BetBuilderClient
from .config import Config


def get_odds(match_id, player_name, bet_type, team=None):
    """
    Get decimal odds for a player bet
    
    Args:
        match_id (str): Event ID (e.g., "OB_EV37926026")
        player_name (str): Player name (e.g., "Joshua Zirkzee")
        bet_type (str): One of:
            - "Anytime Goalscorer"
            - "First Goalscorer"
            - "Score 2 or More"
            - "Score a Hattrick"
        team (str, optional): Team name (will auto-detect if not provided)
    
    Returns:
        float: Decimal odds (e.g., 2.80) or None if not available
    
    Example:
        >>> from willhill_betbuilder import get_odds
        >>> odds = get_odds("OB_EV37926026", "Joshua Zirkzee", "Anytime Goalscorer")
        >>> print(odds)
        2.80
    """
    try:
        client = BetBuilderClient()
        client.load_event(match_id)
        
        combos = client.get_player_combinations(
            player_name=player_name,
            team=team,
            template_name=bet_type,
            get_price=True
        )
        
        if combos and len(combos) > 0:
            combo = combos[0]
            if combo.get('price_data') and combo['price_data'].get('success'):
                return combo['price_data']['odds']
        
        return None
        
    except Exception as e:
        print(f"Error getting odds: {e}")
        return None


def get_odds_detailed(match_id, player_name, bet_type, team=None):
    """
    Get detailed odds information for a player bet
    
    Args:
        match_id (str): Event ID
        player_name (str): Player name
        bet_type (str): Bet type
        team (str, optional): Team name (will auto-detect if not provided)
    
    Returns:
        dict: Detailed odds information or error
        {
            'success': bool,
            'odds': float (decimal odds),
            'display_odds': str (fractional odds, e.g., "9/5"),
            'player': str,
            'team': str,
            'bet_type': str,
            'selections': list (individual selection details)
        }
        or
        {
            'success': False,
            'error': str (error message)
        }
    
    Example:
        >>> result = get_odds_detailed("OB_EV37926026", "Joshua Zirkzee", "Man Utd", "Anytime Goalscorer")
        >>> if result['success']:
        ...     print(f"Odds: {result['odds']} ({result['display_odds']})")
        Odds: 2.80 (9/5)
    """
    try:
        client = BetBuilderClient()
        
        if not client.load_event(match_id):
            return {'success': False, 'error': 'Failed to load event data'}
        
        combos = client.get_player_combinations(
            player_name=player_name,
            team=team,
            template_name=bet_type,
            get_price=True
        )
        
        if not combos or len(combos) == 0:
            return {'success': False, 'error': 'No combinations found'}
        
        combo = combos[0]
        
        if not combo.get('success'):
            return {'success': False, 'error': 'Invalid combination'}
        
        if not combo.get('price_data') or not combo['price_data'].get('success'):
            return {'success': False, 'error': 'Failed to fetch odds'}
        
        price_data = combo['price_data']
        
        return {
            'success': True,
            'odds': price_data['odds'],
            'display_odds': price_data['selections'][0]['displayOdds'],
            'player': player_name,
            'team': combo.get('team', team),  # Use team from combo if available
            'bet_type': bet_type,
            'selections': price_data['selections']
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_multiple_odds(match_id, bets):
    """
    Get odds for multiple player bets at once
    
    Args:
        match_id (str): Event ID
        bets (list): List of dicts with keys: player_name, team, bet_type
    
    Returns:
        list: List of results, each with:
            {
                'player': str,
                'team': str,
                'bet_type': str,
                'odds': float or None,
                'success': bool
            }
    
    Example:
        >>> bets = [
        ...     {'player_name': 'Joshua Zirkzee', 'team': 'Man Utd', 'bet_type': 'Anytime Goalscorer'},
        ...     {'player_name': 'Marcus Rashford', 'team': 'Man Utd', 'bet_type': 'First Goalscorer'},
        ... ]
        >>> results = get_multiple_odds("OB_EV37926026", bets)
        >>> for r in results:
        ...     print(f"{r['player']}: {r['odds']}")
    """
    client = BetBuilderClient()
    client.load_event(match_id)
    
    results = []
    
    for bet in bets:
        try:
            combos = client.get_player_combinations(
                player_name=bet['player_name'],
                team=bet['team'],
                template_name=bet['bet_type'],
                get_price=True
            )
            
            if combos and combos[0].get('price_data', {}).get('success'):
                results.append({
                    'player': bet['player_name'],
                    'team': bet['team'],
                    'bet_type': bet['bet_type'],
                    'odds': combos[0]['price_data']['odds'],
                    'success': True
                })
            else:
                results.append({
                    'player': bet['player_name'],
                    'team': bet['team'],
                    'bet_type': bet['bet_type'],
                    'odds': None,
                    'success': False
                })
        except Exception as e:
            results.append({
                'player': bet.get('player_name', 'Unknown'),
                'team': bet.get('team', 'Unknown'),
                'bet_type': bet.get('bet_type', 'Unknown'),
                'odds': None,
                'success': False,
                'error': str(e)
            })
    
    return results


def get_available_bet_types(match_id, player_name, team):
    """
    Get list of available bet types for a specific player
    
    Args:
        match_id (str): Event ID
        player_name (str): Player name
        team (str): Team name
    
    Returns:
        list: Available bet type names
    
    Example:
        >>> types = get_available_bet_types("OB_EV37926026", "Joshua Zirkzee", "Man Utd")
        >>> print(types)
        ['Anytime Goalscorer', 'First Goalscorer', 'Score 2 or More']
    """
    try:
        client = BetBuilderClient()
        client.load_event(match_id)
        return client.get_templates(player_name=player_name, team=team)
    except Exception as e:
        print(f"Error getting available bet types: {e}")
        return []


def configure(session_cookie=None, nord_user=None, nord_pwd=None, nord_location=None,
              http_proxy=None, https_proxy=None):
    """
    Configure William Hill API credentials and proxy settings
    
    Args:
        session_cookie (str): William Hill session cookie
        nord_user (str): NordVPN username/email
        nord_pwd (str): NordVPN password
        nord_location (str): NordVPN server location (e.g., "us5678")
        http_proxy (str): HTTP proxy URL
        https_proxy (str): HTTPS proxy URL
    
    Example:
        >>> from willhill_betbuilder import configure, get_odds
        >>> configure(
        ...     session_cookie="your_session",
        ...     nord_user="your@email.com",
        ...     nord_pwd="password",
        ...     nord_location="us5678"
        ... )
        >>> odds = get_odds("OB_EV37926026", "Joshua Zirkzee", "Man Utd", "Anytime Goalscorer")
    """
    if session_cookie:
        Config.SESSION_COOKIE = session_cookie
    if nord_user:
        Config.NORD_USER = nord_user
    if nord_pwd:
        Config.NORD_PWD = nord_pwd
    if nord_location:
        Config.NORD_LOCATION = nord_location
    if http_proxy:
        Config.HTTP_PROXY = http_proxy
    if https_proxy:
        Config.HTTPS_PROXY = https_proxy


# Available bet types constant
BET_TYPES = [
    "Anytime Goalscorer",
    "First Goalscorer",
    "Score 2 or More",
    "Score a Hattrick"
]
