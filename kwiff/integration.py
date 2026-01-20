#!/usr/bin/env python3
"""
Kwiff Integration Module

This module provides integration between Kwiff WebSocket client and the
goosealerts system. It handles:
1. Fetching featured matches from Kwiff via WebSocket
2. Saving them to the data directory
3. Auto-mapping Kwiff event IDs to Betfair market IDs

Usage:
    from kwiff.integration import initialize_kwiff
    
    # On startup:
    await initialize_kwiff()  # Fetches matches and maps them automatically
    
    # Or with more control:
    from kwiff.integration import fetch_and_save_events, map_kwiff_events
    
    await fetch_and_save_events()
    map_kwiff_events()
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from .kwiff_client import KwiffClient

# Add parent directory to path for server imports
KWIFF_DIR = Path(__file__).parent
SERVER_DIR = KWIFF_DIR / "server"
sys.path.insert(0, str(SERVER_DIR))


def get_events_filename() -> Path:
    """Get the filename for today's events file."""
    data_dir = SERVER_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    return data_dir / f"events_{today}.json"


async def fetch_and_save_events(country: str = "GB", identifier: Optional[str] = None) -> bool:
    """
    Fetch featured matches from Kwiff and save to data directory.
    
    Args:
        country: Country code (default: 'GB')
        identifier: Optional custom identifier for WebSocket connection
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("[KWIFF] Fetching featured matches...")
    
    try:
        async with KwiffClient(identifier=identifier) as client:
            events = await client.get_football_events(country=country)
            
            if not events:
                print("[KWIFF] No events received from WebSocket")
                return False
            
            # Extract event list
            event_list = []
            if isinstance(events, dict):
                if "data" in events and "events" in events["data"]:
                    event_list = events["data"]["events"]
                elif "events" in events:
                    event_list = events["events"]
            
            if not event_list:
                print("[KWIFF] No events found in response")
                return False
            
            print(f"[KWIFF] Received {len(event_list)} events from WebSocket")
            
            # Save to file with standardized format
            output_file = get_events_filename()
            output_data = {
                "events": event_list,
                "fetched_at": datetime.now().isoformat(),
                "country": country,
                "count": len(event_list)
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"[KWIFF] Saved {len(event_list)} events to {output_file.name}")
            
            # Show preview
            print("\n[KWIFF] Preview of first 3 events:")
            for i, event in enumerate(event_list[:3], 1):
                home = event.get('homeTeam', {})
                away = event.get('awayTeam', {})
                
                home_name = home.get('name', 'Unknown') if isinstance(home, dict) else home
                away_name = away.get('name', 'Unknown') if isinstance(away, dict) else away
                
                comp = event.get('competition', {})
                comp_name = comp.get('name', 'Unknown') if isinstance(comp, dict) else comp
                
                start_date = event.get('startDate', 'N/A')
                event_id = event.get('eventId') or event.get('id')
                
                print(f"  {i}. [{event_id}] {home_name} vs {away_name}")
                print(f"     Competition: {comp_name}")
                print(f"     Kickoff: {start_date}")
            
            return True
            
    except Exception as e:
        print(f"[KWIFF] Error fetching events: {e}")
        import traceback
        traceback.print_exc()
        return False


def map_kwiff_events(dry_run: bool = False) -> bool:
    """
    Map Kwiff events to Betfair market IDs using auto_map_events.
    
    Args:
        dry_run: If True, show what would be mapped without saving
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("\n[KWIFF] Starting event mapping...")
    
    try:
        # Import the auto_map_events module
        from auto_map_events import run_auto_mapping
        
        # Run the mapping
        result = run_auto_mapping(dry_run=dry_run)
        
        if result:
            print("[KWIFF] Event mapping completed successfully")
        else:
            print("[KWIFF] Event mapping completed with warnings")
        
        return result
        
    except Exception as e:
        print(f"[KWIFF] Error mapping events: {e}")
        import traceback
        traceback.print_exc()
        return False


async def initialize_kwiff(country: str = "GB", dry_run: bool = False) -> Dict[str, bool]:
    """
    Complete initialization: fetch events and map them to Betfair.
    Call this on script startup.
    
    Args:
        country: Country code (default: 'GB')
        dry_run: If True, mapping will show results without saving
        
    Returns:
        Dict with status of each operation:
        {
            'fetch_success': bool,
            'mapping_success': bool,
            'overall_success': bool
        }
    """
    print("\n" + "="*70)
    print("KWIFF INTEGRATION - INITIALIZATION")
    print("="*70 + "\n")
    
    result = {
        'fetch_success': False,
        'mapping_success': False,
        'overall_success': False
    }
    
    # Step 1: Fetch events from Kwiff
    result['fetch_success'] = await fetch_and_save_events(country=country)
    
    if not result['fetch_success']:
        print("\n[KWIFF] ❌ Failed to fetch events - skipping mapping")
        return result
    
    # Step 2: Map events to Betfair
    result['mapping_success'] = map_kwiff_events(dry_run=dry_run)
    
    # Overall success requires both steps
    result['overall_success'] = result['fetch_success'] and result['mapping_success']
    
    print("\n" + "="*70)
    if result['overall_success']:
        print("[KWIFF] ✅ Initialization completed successfully")
    else:
        print("[KWIFF] ⚠️ Initialization completed with errors")
    print("="*70 + "\n")
    
    return result


def get_kwiff_event_mappings() -> Dict:
    """
    Load current Kwiff event mappings from event_mappings.json.
    
    Returns:
        Dict of mappings: {kwiff_id: {betfair_id, description, ...}}
    """
    mapping_file = SERVER_DIR / "event_mappings.json"
    
    if not mapping_file.exists():
        return {}
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict) and 'events' in data:
            return data['events']
        
        return {}
        
    except Exception as e:
        print(f"[KWIFF] Error loading mappings: {e}")
        return {}


def get_betfair_id_for_kwiff_event(kwiff_event_id: str) -> Optional[str]:
    """
    Get the Betfair market ID for a given Kwiff event ID.
    
    Args:
        kwiff_event_id: Kwiff event ID
        
    Returns:
        Betfair market ID or None if not found
    """
    mappings = get_kwiff_event_mappings()
    event_data = mappings.get(str(kwiff_event_id), {})
    betfair_id = event_data.get('betfair_id')
    
    # Return None if it's a TODO placeholder
    if betfair_id and betfair_id != "TODO":
        return betfair_id
    
    return None


# Convenience function for sync code
def initialize_kwiff_sync(country: str = "GB", dry_run: bool = False) -> Dict[str, bool]:
    """
    Synchronous wrapper for initialize_kwiff().
    Use this if calling from non-async code.
    
    Args:
        country: Country code (default: 'GB')
        dry_run: If True, mapping will show results without saving
        
    Returns:
        Dict with status of each operation
    """
    return asyncio.run(initialize_kwiff(country=country, dry_run=dry_run))


if __name__ == "__main__":
    # Test the module standalone
    import argparse
    
    parser = argparse.ArgumentParser(description='Kwiff Integration Module')
    parser.add_argument('--country', default='GB', help='Country code (default: GB)')
    parser.add_argument('--dry-run', action='store_true', help='Show mappings without saving')
    parser.add_argument('--fetch-only', action='store_true', help='Only fetch events, skip mapping')
    parser.add_argument('--map-only', action='store_true', help='Only map existing events, skip fetch')
    
    args = parser.parse_args()
    
    if args.map_only:
        # Just run mapping
        map_kwiff_events(dry_run=args.dry_run)
    elif args.fetch_only:
        # Just fetch events
        asyncio.run(fetch_and_save_events(country=args.country))
    else:
        # Full initialization
        initialize_kwiff_sync(country=args.country, dry_run=args.dry_run)
