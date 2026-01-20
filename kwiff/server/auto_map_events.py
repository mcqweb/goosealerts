#!/usr/bin/env python3
"""
Auto-mapping script for Kwiff event IDs to Betfair market IDs.
Fetches matches from Oddsmatcha API and cross-references with local events file.
Automatically updates event_mappings.json with new mappings.
"""

import json
import os
import sys
from datetime import datetime, timedelta
import requests
from pathlib import Path

# Fix encoding for Windows terminals that don't support UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


def get_events_file():
    """Get the latest events file from data folder (today's date)."""
    data_dir = Path(__file__).parent / "data"
    today = datetime.now().strftime("%Y%m%d")
    events_file = data_dir / f"events_{today}.json"
    
    if events_file.exists():
        return events_file
    
    # If today's file doesn't exist, check yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    yesterday_file = data_dir / f"events_{yesterday}.json"
    
    if yesterday_file.exists():
        return yesterday_file
    
    return None


def load_events_file(file_path):
    """Load and parse events file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both direct array and wrapped format
            if isinstance(data, dict) and 'events' in data:
                return data['events']
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading events file: {e}")
        return []


def load_event_mappings():
    """Load current event mappings."""
    mapping_file = Path(__file__).parent / "event_mappings.json"
    
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Handle different formats
                if isinstance(data, dict):
                    return data if 'events' in data else {"events": {}}
                elif isinstance(data, list):
                    # Convert list to dict format
                    return {"events": {}}
                else:
                    return {"events": {}}
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Error loading mappings: {e}")
            return {"events": {}}
    
    return {"events": {}}


def save_event_mappings(mappings):
    """Save updated event mappings."""
    mapping_file = Path(__file__).parent / "event_mappings.json"
    
    try:
        # Ensure proper structure
        if not isinstance(mappings, dict):
            print("Warning: Invalid mappings structure")
            return False
        
        if 'events' not in mappings:
            mappings = {"events": mappings}
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving mappings: {e}")
        return False


def fetch_oddsmatcha_matches():
    """Fetch matches from Oddsmatcha API."""
    try:
        url = "https://api.oddsmatcha.uk/matches/?next_days=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"  API Response type: {type(data)}")
        if isinstance(data, dict):
            print(f"  API Response keys: {list(data.keys())[:5]}")
        
        # Save API response for inspection
        api_file = Path(__file__).parent / "data" / "api_matches_dump.json"
        with open(api_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"  Saved API response to: {api_file}")
        
        return data
    except requests.RequestException as e:
        print(f"Error fetching Oddsmatcha API: {e}")
        return {}
    except Exception as e:
        print(f"Error parsing API response: {e}")
        return {}


def extract_ids(match):
    """Extract Betfair, Smarkets, and Oddsmatcha IDs from match data.
    
    Returns a dict with:
    - betfair_id: from mappings where site_name == 'betfair'
    - smarkets_id: from mappings where site_name == 'smarkets'
    - oddsmatcha_id: the parent match id from Oddsmatcha
    """
    ids = {
        'betfair_id': None,
        'smarkets_id': None,
        'oddsmatcha_id': match.get('id')
    }
    
    try:
        # Extract from mappings array
        if 'mappings' in match and isinstance(match['mappings'], list):
            for mapping in match['mappings']:
                site_name = mapping.get('site_name', '').lower()
                site_match_id = mapping.get('site_match_id')
                
                if site_match_id:
                    if site_name == 'betfair':
                        ids['betfair_id'] = site_match_id
                    elif site_name == 'smarkets':
                        ids['smarkets_id'] = site_match_id
    except Exception as e:
        print(f"Error extracting IDs: {e}")
    
    return ids


def normalize_team_name(name):
    """Normalize team name for comparison."""
    if not name:
        return ""
    return name.lower().strip()


def team_name_matches(team1, team2):
    """Check if two team names match.
    
    Returns True if:
    - One name is entirely contained in the other
    - They are identical after normalization
    """
    t1 = normalize_team_name(team1)
    t2 = normalize_team_name(team2)
    
    if not t1 or not t2:
        return False
    
    # Exact match
    if t1 == t2:
        return True
    
    # One contained in the other (e.g., "Chelsea" in "Chelsea FC")
    if t1 in t2 or t2 in t1:
        return True
    
    return False


def match_teams(local_home, local_away, api_home, api_away):
    """Check if teams match between local events and API data.
    
    Returns True if AT LEAST ONE team name matches.
    This allows flexibility in match identification.
    """
    # Check if local home matches either API team
    home_matches = team_name_matches(local_home, api_home) or team_name_matches(local_home, api_away)
    
    # Check if local away matches either API team
    away_matches = team_name_matches(local_away, api_home) or team_name_matches(local_away, api_away)
    
    # Return true if at least one team matches
    return home_matches or away_matches


def auto_map_events(dry_run=False):
    """
    Match local events with API data and update mappings.
    
    Args:
        dry_run: If True, show what would be added without saving
    """
    print("=" * 60)
    print("AUTO-MAPPING EVENTS")
    print("=" * 60)
    # Load local events
    events_file = get_events_file()
    if not events_file:
        print("[!] No events file found in data folder")
        return
    
    print(f"[*] Loading events from: {events_file.name}")
    local_events = load_events_file(events_file)
    
    if not local_events:
        print("[!] No events found in file")
        return
    
    print(f"[+] Found {len(local_events)} local events")
    
    # Fetch API matches
    print("\n[*] Fetching matches from Oddsmatcha API...")
    api_data = fetch_oddsmatcha_matches()
    
    if not api_data:
        print("[!] Failed to fetch API data")
        return
    
    # Handle different API response formats
    api_matches = []
    if isinstance(api_data, list):
        api_matches = api_data
    elif isinstance(api_data, dict):
        api_matches = api_data.get('matches', []) or api_data.get('data', []) or list(api_data.values())
    
    if not api_matches:
        print(f"[!] No matches found in API response")
        return
    
    print(f"[+] Found {len(api_matches)} matches from API")
    
    # Load existing mappings
    print("\n[*] Loading current mappings...")
    mappings = load_event_mappings()
    existing_count = len(mappings.get('events', {}))
    print(f"[+] Found {existing_count} existing mappings")
    
    # Try to match events
    print("\n[*] Matching events...")
    print(f"\nSample local events:")
    for i, event in enumerate(local_events[:2]):
        print(f"  Event {i+1}: {event.get('homeTeam')} vs {event.get('awayTeam')}")
    
    print(f"\nSample API matches:")
    for i, match in enumerate(api_matches[:3]):
        home = match.get('home_team') or match.get('homeTeam')
        away = match.get('away_team') or match.get('awayTeam')
        print(f"  Match {i+1}: {home} vs {away}")
        print(f"    Keys: {list(match.keys())[:8]}")
    
    new_mappings = 0
    matched_events = []
    no_match_count = 0
    
    for local_event in local_events:
        local_id = str(local_event.get('eventId'))
        
        # Skip only if already mapped with a real betfair_id (not TODO)
        if local_id in mappings['events']:
            existing = mappings['events'][local_id]
            betfair_id = existing.get('betfair_id', '')
            if betfair_id and betfair_id != 'TODO':
                continue
            # If betfair_id is TODO, we'll try to find it below
        
        # Handle both string and object formats for team names
        local_home = local_event.get('homeTeam')
        if isinstance(local_home, dict):
            local_home = local_home.get('name', '')
        
        local_away = local_event.get('awayTeam')
        if isinstance(local_away, dict):
            local_away = local_away.get('name', '')
        
        if not local_home or not local_away:
            continue
        
        found_match = False
        # Try to find matching API event
        for api_match in api_matches:
            api_home = api_match.get('home_team') or api_match.get('homeTeam')
            api_away = api_match.get('away_team') or api_match.get('awayTeam')
            
            if not api_home or not api_away:
                continue
            
            if match_teams(local_home, local_away, api_home, api_away):
                ids = extract_ids(api_match)
                
                if ids['betfair_id']:
                    # Get match details
                    competition = local_event.get('competition', 'Unknown')
                    start_date = local_event.get('startDate', '')
                    
                    # Preserve existing description if updating a TODO
                    if local_id in mappings['events'] and 'description' in mappings['events'][local_id]:
                        mapping_entry = mappings['events'][local_id]
                        mapping_entry['betfair_id'] = str(ids['betfair_id'])
                    else:
                        mapping_entry = {
                            "betfair_id": str(ids['betfair_id']),
                            "description": f"{local_home} vs {local_away} - {competition} - {start_date}"
                        }
                    
                    # Add optional fields
                    if ids['oddsmatcha_id']:
                        mapping_entry['oddsmatcha_id'] = str(ids['oddsmatcha_id'])
                    if ids['smarkets_id']:
                        mapping_entry['smarkets_id'] = str(ids['smarkets_id'])
                    
                    mappings['events'][local_id] = mapping_entry
                    matched_events.append({
                        'kwiff_id': local_id,
                        'betfair_id': ids['betfair_id'],
                        'oddsmatcha_id': ids['oddsmatcha_id'],
                        'smarkets_id': ids['smarkets_id'],
                        'home': local_home,
                        'away': local_away,
                        'competition': competition
                    })
                    new_mappings += 1
                    found_match = True
                    break
        
        if not found_match:
            no_match_count += 1
    
    # Display results
    print(f"\n[*] RESULTS:")
    print(f"  New mappings found: {new_mappings}")
    print(f"  Events without matches: {no_match_count}")
    
    # Show unmapped events
    if no_match_count > 0:
        print(f"\n[!] UNMAPPED EVENTS (create placeholders):")
        unmapped = []
        for local_event in local_events:
            local_id = str(local_event.get('eventId'))
            if local_id not in mappings['events']:
                local_home = local_event.get('homeTeam')
                if isinstance(local_home, dict):
                    local_home = local_home.get('name', '')
                
                local_away = local_event.get('awayTeam')
                if isinstance(local_away, dict):
                    local_away = local_away.get('name', '')
                
                if local_home and local_away:
                    competition = local_event.get('competition', 'Unknown')
                    start_date = local_event.get('startDate', '')
                    
                    placeholder = {
                        "betfair_id": "TODO",
                        "description": f"{local_home} vs {local_away} - {competition} - {start_date}"
                    }
                    
                    mappings['events'][local_id] = placeholder
                    unmapped.append({
                        'kwiff_id': local_id,
                        'home': local_home,
                        'away': local_away,
                        'competition': competition
                    })
                    print(f"  • {local_id}: {local_home} vs {local_away} ({competition})")
        
        # Save placeholders
        if unmapped and not dry_run:
            if save_event_mappings(mappings):
                print(f"\n[+] Created {len(unmapped)} placeholder(s) in event_mappings.json")
                print("   Please fill in the Betfair IDs manually or use --dry-run to see them")
            else:
                print("\n[!] Failed to save placeholder mappings")
    
    if matched_events:
        print(f"\n[+] New mappings:")
        for event in matched_events:
            print(f"  • {event['kwiff_id']} → Betfair: {event['betfair_id']}")
            if event['oddsmatcha_id']:
                print(f"    (Oddsmatcha: {event['oddsmatcha_id']})", end="")
            if event['smarkets_id']:
                print(f" (Smarkets: {event['smarkets_id']})", end="")
            if event['oddsmatcha_id'] or event['smarkets_id']:
                print()
            print(f"    {event['home']} vs {event['away']} ({event['competition']})")
    
    # Save if not dry run
    if (new_mappings > 0 or no_match_count > 0):
        if dry_run:
            print("\n[!] DRY RUN: Changes not saved")
        else:
            if new_mappings > 0:
                if save_event_mappings(mappings):
                    print(f"\n[+] Saved {new_mappings} new mapping(s) to event_mappings.json")
                else:
                    print("\n[!] Failed to save mappings")
    else:
        print("\n[*] No new mappings found")
    
    print("=" * 60)


def run_auto_mapping(dry_run=False):
    """Wrapper function for external imports."""
    try:
        auto_map_events(dry_run=dry_run)
        return True
    except Exception as e:
        print(f"Error in auto_map_events: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-map Kwiff event IDs to Betfair markets')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be added without saving')
    parser.add_argument('--verbose', action='store_true', help='Show detailed matching info')
    
    args = parser.parse_args()
    
    run_auto_mapping(dry_run=args.dry_run)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
