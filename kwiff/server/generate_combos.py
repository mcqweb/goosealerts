#!/usr/bin/env python3
"""
Generate combo JSON response for matched Kwiff players with Betfair odds.
Returns a JSON structure with matched player combos for the webserver.
"""

import json
import os
import sys
import argparse
import time
import requests
from datetime import datetime
from betfair import Betfair

# Load event mappings
def load_event_mappings():
    """Load Kwiff to Betfair/OddsMatcha event mappings from config file."""
    config_path = os.path.join(os.path.dirname(__file__), 'event_mappings.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data.get('events', {})
    return {}

EVENT_MAPPINGS = load_event_mappings()

# Default minimum lay size (in GBP)
DEFAULT_MIN_SIZE = 10.0

# Lock file for preventing simultaneous execution
LOCK_FILE = os.path.join(os.path.dirname(__file__), '.script_lock')
LOCK_TIMEOUT = 300  # 5 minutes in seconds


def acquire_lock():
    """Acquire a lock to prevent simultaneous execution."""
    if os.path.exists(LOCK_FILE):
        lock_age = time.time() - os.path.getmtime(LOCK_FILE)
        if lock_age < LOCK_TIMEOUT:
            print(json.dumps({"error": "Script is already running. Please wait for it to complete."}))
            sys.exit(1)
        else:
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
    
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except OSError as e:
        print(json.dumps({"error": f"Could not acquire lock: {str(e)}"}))
        sys.exit(1)


def release_lock():
    """Release the lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


def normalize_name(name: str) -> str:
    """Normalize name for comparison (lowercase, remove extra spaces)."""
    return ' '.join(name.lower().split())


def flip_name_format(name: str) -> str:
    """Convert 'Surname Firstname' to 'Firstname Surname'."""
    parts = name.split()
    if len(parts) < 2:
        return name
    # Assume first part is surname, rest is first name
    return ' '.join(parts[1:]) + ' ' + parts[0]


def find_best_name_match(kwiff_name: str, betfair_map: dict) -> tuple:
    """
    Find the best match for a Kwiff player name in the Betfair map.
    Returns (matched_key, match_type) or (None, None) if no match found.
    
    Tries multiple strategies:
    1. Exact match (normalized)
    2. Flipped name (Surname Firstname <-> Firstname Surname)
    3. Partial match (at least 2 name parts match)
    """
    kwiff_normalized = normalize_name(kwiff_name)
    kwiff_parts = set(kwiff_normalized.split())
    
    # Strategy 1: Exact match
    if kwiff_normalized in betfair_map:
        return (kwiff_normalized, "exact")
    
    # Strategy 2: Flipped name
    flipped = flip_name_format(kwiff_name)
    flipped_normalized = normalize_name(flipped)
    if flipped_normalized in betfair_map:
        return (flipped_normalized, "flipped")
    
    # Strategy 3: Partial match (at least 2 name parts match)
    if len(kwiff_parts) >= 2:
        best_match = None
        best_match_count = 0
        
        for bf_key in betfair_map.keys():
            bf_parts = set(bf_key.split())
            common_parts = kwiff_parts & bf_parts
            
            # Require at least 2 matching parts
            if len(common_parts) >= 2:
                if len(common_parts) > best_match_count:
                    best_match = bf_key
                    best_match_count = len(common_parts)
        
        if best_match:
            return (best_match, f"partial_{best_match_count}_parts")
    
    return (None, None)


def fetch_exchange_odds(oddsmatcha_match_id):
    """
    Fetch Smarkets lay odds from OddsMatcha API.
    
    Args:
        oddsmatcha_match_id: OddsMatcha match ID (different from Betfair ID)
    
    Returns:
        Dict structure:
        {
            'Anytime Goalscorer': {
                'Player Name': [
                    {'site_name': 'Smarkets', 'lay_odds': 5.5}
                ]
            }
        }
    """
    try:
        url = f"https://api.oddsmatcha.uk/matches/{oddsmatcha_match_id}/markets/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Only keep fresh odds (< 5 minutes old)
        FRESHNESS_THRESHOLD = 300  # 5 minutes in seconds
        current_time = time.time()
        
        result = {}
        
        for market in data:
            market_name = market.get('name', '')
            
            # Map OddsMatcha market names to our format (we only use Anytime Goalscorer)
            if 'Anytime Goalscorer' in market_name or 'Anytime Goal Scorer' in market_name:
                market_key = 'Anytime Goalscorer'
            else:
                continue
            
            if market_key not in result:
                result[market_key] = {}
            
            runners = market.get('runners', [])
            for runner in runners:
                player_name = runner.get('name', '')
                if not player_name:
                    continue
                
                if player_name not in result[market_key]:
                    result[market_key][player_name] = []
                
                # Process each site's odds
                for site_name, site_data in runner.items():
                    if site_name in ['name', 'id']:
                        continue
                    
                    if not isinstance(site_data, dict):
                        continue
                    
                    # Only include Smarkets (ignore Betfair from OddsMatcha - we fetch that directly)
                    if site_name.lower() != 'smarkets':
                        continue
                    
                    lay_price = site_data.get('lay_price')
                    last_updated = site_data.get('last_updated', 0)
                    
                    # Check freshness
                    if lay_price and (current_time - last_updated) <= FRESHNESS_THRESHOLD:
                        result[market_key][player_name].append({
                            'site_name': 'Smarkets',
                            'lay_odds': float(lay_price)
                        })
        
        return result
        
    except Exception as e:
        # Silent fallback - return empty dict
        return {}


def combine_betfair_and_exchange_odds(betfair_odds, exchange_odds):
    """
    Combine Betfair and exchange odds for Anytime Goalscorer market.
    
    Args:
        betfair_odds: List of dicts with 'outcome', 'odds', 'size' from Betfair
        exchange_odds: Dict from fetch_exchange_odds() with player names as keys
    
    Returns:
        Dict mapping player names to list of exchange data:
        {
            'Player Name': [
                {
                    'site': 'Betfair',
                    'lay_odds': 5.0,
                    'lay_size': 100.0,
                    'has_size': True
                },
                {
                    'site': 'Smarkets',
                    'lay_odds': 4.8,
                    'lay_size': None,
                    'has_size': False
                }
            ]
        }
    """
    player_odds_map = {}
    
    # Add Betfair odds (with liquidity info)
    for odd in betfair_odds:
        player_name = odd.get('outcome', '')
        if not player_name:
            continue
            
        if player_name not in player_odds_map:
            player_odds_map[player_name] = []
            
        player_odds_map[player_name].append({
            'site': 'Betfair',
            'lay_odds': float(odd.get('odds', 0)),
            'lay_size': float(odd.get('size', 0)),
            'has_size': True
        })
    
    # Add exchange odds (no liquidity info)
    exchange_market = exchange_odds.get('Anytime Goalscorer', {})
    for player_name, site_odds_list in exchange_market.items():
        if player_name not in player_odds_map:
            player_odds_map[player_name] = []
            
        for site_odd in site_odds_list:
            player_odds_map[player_name].append({
                'site': site_odd['site_name'],
                'lay_odds': site_odd['lay_odds'],
                'lay_size': None,
                'has_size': False
            })
    
    return player_odds_map


def load_kwiff_data(kwiff_id: str) -> dict:
    """Load Kwiff JSON data from data folder."""
    # Look for specific eventId_kwiff.json file first
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    target_filename = f"{kwiff_id}_kwiff.json"
    filepath = os.path.join(data_dir, target_filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            events = data.get('events', [])
            if events:
                return events[0]
    
    return None


def load_all_events_for_today():
    """Load all events from today's events batch file."""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    today = datetime.now().strftime("%Y%m%d")
    events_filename = f"events_{today}.json"
    filepath = os.path.join(data_dir, events_filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('events', [])
    
    return []


def main():
    # Acquire lock before proceeding
    acquire_lock()
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Generate combo JSON for all events from today's batch")
        parser.add_argument('--min-size', type=float, default=DEFAULT_MIN_SIZE,
                            help=f'Minimum lay size in GBP (default: {DEFAULT_MIN_SIZE})')
        args = parser.parse_args()
        
        min_size = args.min_size
        
        # Load all events from today's batch file
        all_events = load_all_events_for_today()
        
        if not all_events:
            print(json.dumps({"error": f"No events file found for today"}))
            return
        
        # Initialize Betfair client
        try:
            bf = Betfair()
        except Exception as e:
            print(json.dumps({"error": f"Failed to initialize Betfair client: {str(e)}"}))
            return
        
        # Process all events
        all_events_data = []
        log_entries = []
        
        for kwiff_event in all_events:
            kwiff_event_id = str(kwiff_event.get('eventId'))
            event_mapping = EVENT_MAPPINGS.get(kwiff_event_id, {})
            betfair_event_id = event_mapping.get('betfair_id')
            oddsmatcha_match_id = event_mapping.get('oddsmatcha_id')
            
            home_team = kwiff_event.get('homeTeam', 'Unknown')
            away_team = kwiff_event.get('awayTeam', 'Unknown')
            start_date = kwiff_event.get('startDate')
            
            if not betfair_event_id:
                log_entries.append({
                    "event_id": kwiff_event_id,
                    "fixture": f"{home_team} vs {away_team}",
                    "reason": "NO_BETFAIR_MAPPING",
                    "details": "Event ID not found in event_mappings.json"
                })
                continue
            
            # Check if match is within 90 minutes of kickoff
            if start_date:
                try:
                    ko_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    now = datetime.now(ko_time.tzinfo)
                    time_to_ko = (ko_time - now).total_seconds() / 60  # minutes
                    
                    if time_to_ko > 90:  # More than 90 minutes to KO
                        log_entries.append({
                            "event_id": kwiff_event_id,
                            "fixture": f"{home_team} vs {away_team}",
                            "betfair_id": betfair_event_id,
                            "reason": "TOO_FAR_FROM_KO",
                            "details": f"Match starts in {time_to_ko:.0f} minutes (> 90 min threshold)"
                        })
                        continue
                except Exception as e:
                    # If we can't parse the time, log but continue processing
                    pass
            
            kwiff_players = kwiff_event.get('players', [])
            over_half_goals_id = kwiff_event.get('overHalfGoalsId')
            
            # Fetch Betfair odds
            try:
                betfair_odds = bf.fetch_odds_for_match(betfair_event_id)
            except Exception as e:
                log_entries.append({
                    "event_id": kwiff_event_id,
                    "fixture": f"{home_team} vs {away_team}",
                    "betfair_id": betfair_event_id,
                    "reason": "BETFAIR_API_ERROR",
                    "details": str(e)
                })
                continue
            
            # Fetch exchange odds from OddsMatcha (Smarkets/Matchbook)
            exchange_odds = {}
            if oddsmatcha_match_id:
                exchange_odds = fetch_exchange_odds(oddsmatcha_match_id)
                if exchange_odds:
                    total_exchange_players = sum(len(players) for players in exchange_odds.values())
                    log_entries.append({
                        "event_id": kwiff_event_id,
                        "fixture": f"{home_team} vs {away_team}",
                        "reason": "EXCHANGE_ODDS_FETCHED",
                        "exchange_players": total_exchange_players
                    })
            
            # Combine Betfair and exchange odds
            combined_odds_map = combine_betfair_and_exchange_odds(betfair_odds, exchange_odds)
            
            # Create map by normalized name for matching
            player_odds_lookup = {}
            for player_name, exchange_list in combined_odds_map.items():
                normalized = normalize_name(flip_name_format(player_name))
                player_odds_lookup[normalized] = (player_name, exchange_list)
            
            # Build combos array for this event
            combos = []
            players_skipped = []
            
            for kwiff_player in kwiff_players:
                kwiff_name = kwiff_player.get('name', '')
                kwiff_normalized = normalize_name(kwiff_name)
                scorer_id = kwiff_player.get('scorerId')
                sot_id = kwiff_player.get('SoTId')
                
                # Determine id_two: use overHalfGoalsId if available, otherwise use SoTId
                id_two = over_half_goals_id if over_half_goals_id else sot_id
                
                # Try to find in combined odds data using smart matching
                matched = False
                skip_reason = None
                match_type = None
                
                matched_key, match_type = find_best_name_match(kwiff_name, player_odds_lookup)
                
                if matched_key:
                    player_name, exchange_list = player_odds_lookup[matched_key]
                    
                    # Find best (lowest) lay odds across all exchanges
                    best_exchange = min(exchange_list, key=lambda x: x['lay_odds'])
                    best_odds = best_exchange['lay_odds']
                    best_site = best_exchange['site']
                    has_size = best_exchange['has_size']
                    lay_size = best_exchange['lay_size']
                    
                    # Build display text with all available exchanges (without liquidity)
                    all_exchanges_text = []
                    for ex in exchange_list:
                        all_exchanges_text.append(f"{ex['site']} @ {ex['lay_odds']}")
                    lay_prices_display = " | ".join(all_exchanges_text)
                    
                    # Check if size meets minimum threshold (only for Betfair, exchange odds have no size)
                    if not has_size or (lay_size and lay_size >= min_size):
                        combos.append({
                            'name': kwiff_name,
                            'id_one': scorer_id,
                            'id_two': id_two,
                            'lay_odds': best_odds,
                            'lay_size': lay_size if has_size else None,
                            'best_exchange': best_site,
                            'all_exchanges': lay_prices_display
                        })
                        matched = True
                        # Log successful match type in debug if needed
                        if match_type and match_type != "exact":
                            log_entries.append({
                                "player": kwiff_name,
                                "matched_as": matched_key,
                                "match_type": match_type,
                                "best_exchange": best_site
                            })
                    else:
                        skip_reason = f"SIZE_TOO_SMALL (£{lay_size:.2f} < £{min_size})"
                else:
                    skip_reason = "NO_EXCHANGE_MATCH"
                
                if not matched:
                    players_skipped.append({
                        "name": kwiff_name,
                        "reason": skip_reason
                    })
            
            # Log skipped players if any
            if players_skipped:
                log_entries.append({
                    "event_id": kwiff_event_id,
                    "fixture": f"{home_team} vs {away_team}",
                    "betfair_id": betfair_event_id,
                    "reason": "PLAYERS_FILTERED",
                    "players_total": len(kwiff_players),
                    "players_matched": len(combos),
                    "players_skipped": len(players_skipped),
                    "skipped_details": players_skipped[:5]  # First 5 for brevity
                })
            
            # Add this event's data to the collection
            event_data = {
                'combos': combos,
                'metadata': {
                    'fixture': {
                        'event_id': kwiff_event.get('eventId'),
                        'match_id': kwiff_event.get('matchId'),
                        'home_team': kwiff_event.get('homeTeam'),
                        'away_team': kwiff_event.get('awayTeam'),
                        'start_date': kwiff_event.get('startDate'),
                        'competition': kwiff_event.get('competition')
                    },
                    'kwiff_event_id': kwiff_event_id,
                    'betfair_event_id': betfair_event_id,
                    'min_size': min_size,
                    'total_players': len(kwiff_players),
                    'matched_players': len(combos)
                }
            }
            all_events_data.append(event_data)
        
        # Write log file
        if log_entries:
            log_dir = os.path.join(os.path.dirname(__file__), 'data', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"{timestamp}_generation_log.json")
            with open(log_file, 'w') as f:
                json.dump({
                    "timestamp": timestamp,
                    "total_events_in_file": len(all_events),
                    "events_processed": len(all_events_data),
                    "events_skipped": len(all_events) - len(all_events_data),
                    "min_size": min_size,
                    "log_entries": log_entries
                }, f, indent=2)
        
        # Create response with all events
        response = {
            'events': all_events_data,
            'summary': {
                'total_events': len(all_events_data),
                'min_size': min_size
            }
        }
        
        # Output as JSON
        print(json.dumps(response, indent=2))
    except Exception as e:
        import traceback
        print(json.dumps({"error": f"Script error: {str(e)}", "traceback": traceback.format_exc()}))
    finally:
        # Always release lock
        release_lock()


if __name__ == '__main__':
    main()
