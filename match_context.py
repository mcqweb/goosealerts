#!/usr/bin/env python3
"""
Helper functions for extracting team/fixture information from match data.
Used to enhance player tracking with team context.
"""


def extract_team_from_fixture(fixture_name: str, player_position: str = None) -> str:
    """Extract team name from fixture string.
    
    Args:
        fixture_name: Fixture string like "Manchester United v Liverpool"
        player_position: 'home' or 'away' if known, None otherwise
    
    Returns:
        Team name, or None if can't determine
    """
    if not fixture_name:
        return None
    
    # Common separators
    separators = [' v ', ' vs ', ' V ', ' VS ', ' - ']
    
    for sep in separators:
        if sep in fixture_name:
            parts = fixture_name.split(sep, 1)
            if len(parts) == 2:
                home_team = parts[0].strip()
                away_team = parts[1].strip()
                
                if player_position == 'home':
                    return home_team
                elif player_position == 'away':
                    return away_team
                else:
                    # If we don't know position, we can't determine team
                    # Better to return None than guess wrong
                    return None
    
    return None


def normalize_fixture(home_team: str, away_team: str) -> str:
    """Create normalized fixture string.
    
    Args:
        home_team: Home team name
        away_team: Away team name
    
    Returns:
        Normalized fixture string (e.g., "Manchester United v Liverpool")
    """
    if not home_team or not away_team:
        return None
    
    return f"{home_team.strip()} v {away_team.strip()}"


def get_match_context(match_data: dict, player_name: str = None) -> dict:
    """Extract team/fixture context from match data.
    
    Args:
        match_data: Match dictionary with home_team, away_team, etc.
        player_name: Optional player name (for future lineup-based team detection)
    
    Returns:
        Dict with 'team_name' and 'fixture' keys (values may be None)
    """
    context = {
        'team_name': None,
        'fixture': None
    }
    
    home_team = match_data.get('home_team')
    away_team = match_data.get('away_team')
    
    # Always create fixture if we have both teams
    if home_team and away_team:
        context['fixture'] = normalize_fixture(home_team, away_team)
    
    # TODO: In future, we could detect team from lineup data
    # For now, we'll leave team_name as None unless we have definitive info
    # This is safer than guessing wrong
    
    return context


# Example usage in virgin_goose.py:
# 
# # When tracking a player:
# match_context = get_match_context(match_data)
# track_player_name(
#     player_name=name,
#     site_name='betfair',
#     match_id=match_id,
#     team_name=match_context['team_name'],
#     fixture=match_context['fixture']
# )
