#!/usr/bin/env python3
"""
Match Kwiff players to Betfair players and display lay odds for Player to Score market.

Kwiff format: "{surname} {first_name}"
Betfair format: "{first_name} {surname}"

Manual mapping: Kwiff eventId 10529217 -> Betfair eventId 35013346
"""

import json
import os
import sys
import argparse
import time
from betfair import Betfair

# Load event mappings
def load_event_mappings():
    """Load Kwiff to Betfair event mappings from config file."""
    config_path = os.path.join(os.path.dirname(__file__), 'event_mappings.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            mapping = {}
            for kwiff_id, event_info in data.get('events', {}).items():
                mapping[kwiff_id] = event_info.get('betfair_id')
            return mapping
    return {}

KWIFF_TO_BETFAIR_MAP = load_event_mappings()

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
            print("ERROR: Script is already running. Please wait for it to complete.")
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
        print(f"ERROR: Could not acquire lock: {str(e)}")
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

def load_kwiff_data(kwiff_id: str) -> dict:
    """Load Kwiff JSON data from data folder."""
    # Look for specific eventId_kwiff.json file
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    target_filename = f"{kwiff_id}_kwiff.json"
    filepath = os.path.join(data_dir, target_filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Return the first event from the file (or handle as needed)
            events = data.get('events', [])
            if events:
                return events[0]
    
    return None

def main():
    # Acquire lock before proceeding
    acquire_lock()
    
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Match Kwiff players to Betfair odds")
        parser.add_argument('--min-size', type=float, default=DEFAULT_MIN_SIZE,
                            help=f'Minimum lay size in GBP (default: {DEFAULT_MIN_SIZE})')
        parser.add_argument('--kwiff-id', type=str, default="10529217",
                            help='Kwiff event ID (default: 10529217)')
        args = parser.parse_args()
        
        kwiff_event_id = args.kwiff_id
        min_size = args.min_size
        betfair_event_id = KWIFF_TO_BETFAIR_MAP.get(kwiff_event_id)
        
        if not betfair_event_id:
            print(f"No Betfair mapping found for Kwiff event {kwiff_event_id}")
            return
        
        print(f"Loading Kwiff data for event {kwiff_event_id}...")
        kwiff_event = load_kwiff_data(kwiff_event_id)
        
        if not kwiff_event:
            print(f"Could not find Kwiff event {kwiff_event_id} in data folder")
            return
        
        kwiff_players = kwiff_event.get('players', [])
        print(f"Found {len(kwiff_players)} players in Kwiff data\n")
        
        # Initialize Betfair client
        bf = Betfair()
        
        print(f"Fetching Betfair odds for event {betfair_event_id}...")
        try:
            betfair_odds = bf.fetch_odds_for_match(betfair_event_id)
        except Exception as e:
            print(f"Error fetching Betfair odds: {e}")
            return
        
        # Create map of Betfair players by normalized name (flipped format)
        betfair_map = {}
        for odd in betfair_odds:
            outcome = odd.get('outcome', '')
            normalized = normalize_name(flip_name_format(outcome))
            betfair_map[normalized] = odd
        
        print(f"Found {len(betfair_odds)} runners in Betfair TO_SCORE market\n")
        print("=" * 80)
        print(f"{'Kwiff Player':<30} {'Betfair Match':<30} {'Odds':<10} {'Size (£)':<10}")
        print("=" * 80)
        
        matched_count = 0
        unmatched_count = 0
        filtered_count = 0
        
        for kwiff_player in kwiff_players:
            kwiff_name = kwiff_player.get('name', '')
            kwiff_normalized = normalize_name(kwiff_name)
            
            # Try to find in Betfair data
            if kwiff_normalized in betfair_map:
                bf_data = betfair_map[kwiff_normalized]
                odds = bf_data.get('odds', 0)
                size = bf_data.get('size', 0)
                bf_name = bf_data.get('outcome', '')
                
                # Check if size meets minimum threshold
                if size >= min_size:
                    print(f"{kwiff_name:<30} {bf_name:<30} {odds:<10.2f} {size:<10.2f}")
                    matched_count += 1
                else:
                    filtered_count += 1
            else:
                unmatched_count += 1
                # Try fuzzy matching as fallback
                flipped = flip_name_format(kwiff_name)
                flipped_normalized = normalize_name(flipped)
                
                if flipped_normalized in betfair_map:
                    bf_data = betfair_map[flipped_normalized]
                    odds = bf_data.get('odds', 0)
                    size = bf_data.get('size', 0)
                    bf_name = bf_data.get('outcome', '')
                    
                    # Check if size meets minimum threshold
                    if size >= min_size:
                        print(f"{kwiff_name:<30} {bf_name:<30} {odds:<10.2f} {size:<10.2f}")
                        matched_count += 1
                        unmatched_count -= 1
                    else:
                        filtered_count += 1
                        unmatched_count -= 1
        
        print("=" * 80)
        print(f"\nMatched (size >= £{min_size}): {matched_count}/{len(kwiff_players)} players")
        print(f"Filtered (insufficient size): {filtered_count} players")
        print(f"Unmatched (not in market): {unmatched_count}/{len(kwiff_players)} players")
    finally:
        # Always release lock
        release_lock()

if __name__ == '__main__':
    main()
