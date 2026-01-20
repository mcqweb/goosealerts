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
from typing import Optional, Dict, List

from .kwiff_client import KwiffClient

# Add parent directory to path for server imports
KWIFF_DIR = Path(__file__).parent
SERVER_DIR = KWIFF_DIR / "server"
sys.path.insert(0, str(SERVER_DIR))

# Import match cache
from .match_cache import (
    get_cache,
    cache_match_details,
    get_cached_match_details,
    clear_expired_cache
)


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


async def fetch_match_details_for_mapped_events(
    betfair_market_ids: Optional[List[str]] = None,
    max_matches: Optional[int] = None,
    client: Optional[KwiffClient] = None
) -> Dict[str, any]:
    """
    Fetch and cache detailed match data for mapped Kwiff events.
    
    This fetches full match details including markets, players, and odds
    for matches that we care about (in our Betfair list).
    
    Only fetches details for:
    - Events with valid Betfair mappings (not 'TODO')
    - Events with future kickoff times
    
    Args:
        betfair_market_ids: List of Betfair IDs we care about (optional)
        max_matches: Maximum number of matches to fetch (optional)
        client: Existing KwiffClient to reuse (optional, will create new if None)
        
    Returns:
        Dict with:
        {
            'fetched_count': int,
            'cached_count': int,
            'failed_count': int,
            'skipped_count': int (already cached),
            'filtered_count': int (filtered out - past KO or no mapping)
        }
    """
    print("\n[KWIFF] Fetching match details for mapped events...")
    
    result = {
        'fetched_count': 0,
        'cached_count': 0,
        'failed_count': 0,
        'skipped_count': 0,
        'filtered_count': 0
    }
    
    # Load today's events to check kickoff times
    events_file = get_events_filename()
    if not events_file.exists():
        print("[KWIFF] No events file found")
        return result
    
    try:
        with open(events_file, 'r', encoding='utf-8') as f:
            events_data = json.load(f)
        events_list = events_data.get('events', [])
    except Exception as e:
        print(f"[KWIFF] Error loading events file: {e}")
        return result
    
    # Build index of events by ID for quick lookup
    events_by_id = {}
    for event in events_list:
        event_id = str(event.get('id') or event.get('eventId', ''))
        if event_id:
            events_by_id[event_id] = event
    
    # Get mappings
    mappings = get_kwiff_event_mappings()
    if not mappings:
        print("[KWIFF] No mappings found")
        return result
    
    # Get current time for kickoff comparison
    now = datetime.now()
    
    # Filter mappings to only those we care about
    relevant_mappings = {}
    for kwiff_id, data in mappings.items():
        # Skip invalid Kwiff IDs
        if not kwiff_id or kwiff_id == 'None' or kwiff_id == 'null':
            result['filtered_count'] += 1
            continue
        
        # Validate Kwiff ID can be converted to int
        try:
            int(kwiff_id)
        except (ValueError, TypeError):
            result['filtered_count'] += 1
            continue
        
        betfair_id = data.get('betfair_id')
        
        # Skip TODO placeholders
        if not betfair_id or betfair_id == 'TODO':
            result['filtered_count'] += 1
            continue
        
        # Skip if no Betfair mapping
        if betfair_market_ids and betfair_id not in betfair_market_ids:
            result['filtered_count'] += 1
            continue
        
        # Check kickoff time
        event = events_by_id.get(kwiff_id)
        if event:
            start_date_str = event.get('startDate')
            if start_date_str:
                try:
                    # Parse ISO format: "2026-01-20T17:45:00.000Z"
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    
                    # Skip if kickoff is in the past
                    if start_date.replace(tzinfo=None) <= now:
                        result['filtered_count'] += 1
                        continue
                except Exception as e:
                    print(f"[KWIFF] Warning: Could not parse startDate for event {kwiff_id}: {e}")
        
        relevant_mappings[kwiff_id] = data
    
    if not relevant_mappings:
        print(f"[KWIFF] No relevant mappings found (filtered out {result['filtered_count']} past/unmapped events)")
        return result
    
    print(f"[KWIFF] Found {len(relevant_mappings)} future matches with Betfair mappings (filtered {result['filtered_count']})")
    
    # Limit if requested
    if max_matches:
        items = list(relevant_mappings.items())[:max_matches]
        relevant_mappings = dict(items)
        print(f"[KWIFF] Limited to {len(relevant_mappings)} matches")
    
    # Check cache first
    cache = get_cache()
    to_fetch = []
    
    for kwiff_id in relevant_mappings.keys():
        if cache.has(kwiff_id):
            result['skipped_count'] += 1
        else:
            to_fetch.append(kwiff_id)
    
    if result['skipped_count'] > 0:
        print(f"[KWIFF] {result['skipped_count']} matches already cached")
    
    if not to_fetch:
        print("[KWIFF] All matches already cached")
        return result
    
    print(f"[KWIFF] Fetching details for {len(to_fetch)} matches...")
    
    # Create or reuse client
    close_client = False
    if client is None:
        client = KwiffClient()
        await client.connect()
        close_client = True
    
    try:
        for i, kwiff_id in enumerate(to_fetch, 1):
            try:
                print(f"  [{i}/{len(to_fetch)}] Fetching event {kwiff_id}...", end=" ")
                
                details = await client.get_event_details(int(kwiff_id))
                
                if details:
                    # Cache the details
                    success = cache_match_details(kwiff_id, details)
                    if success:
                        result['fetched_count'] += 1
                        result['cached_count'] += 1
                        print("✅")
                    else:
                        result['fetched_count'] += 1
                        print("⚠️ (fetch ok, cache failed)")
                else:
                    result['failed_count'] += 1
                    print("❌ (no data)")
                
                # Small delay to avoid overwhelming the API
                if i < len(to_fetch):
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                result['failed_count'] += 1
                print(f"❌ (error: {e})")
    
    finally:
        if close_client:
            await client.disconnect()
    
    print(f"\n[KWIFF] Match details fetch complete:")
    print(f"  Fetched: {result['fetched_count']}")
    print(f"  Cached: {result['cached_count']}")
    print(f"  Already cached: {result['skipped_count']}")
    print(f"  Filtered out: {result['filtered_count']}")
    print(f"  Failed: {result['failed_count']}")
    
    return result


def fetch_match_details_sync(
    betfair_market_ids: Optional[List[str]] = None,
    max_matches: Optional[int] = None
) -> Dict[str, any]:
    """
    Synchronous wrapper for fetch_match_details_for_mapped_events.
    
    Args:
        betfair_market_ids: List of Betfair IDs we care about (optional)
        max_matches: Maximum number of matches to fetch (optional)
        
    Returns:
        Dict with fetch results
    """
    return asyncio.run(
        fetch_match_details_for_mapped_events(
            betfair_market_ids=betfair_market_ids,
            max_matches=max_matches
        )
    )


async def initialize_kwiff(
    country: str = "GB",
    dry_run: bool = False,
    fetch_match_details: bool = False,
    betfair_market_ids: Optional[List[str]] = None,
    max_match_details: Optional[int] = None
) -> Dict[str, any]:
    """
    Complete initialization: fetch events, map them to Betfair, and optionally fetch match details.
    Call this on script startup.
    
    Args:
        country: Country code (default: 'GB')
        dry_run: If True, mapping will show results without saving
        fetch_match_details: If True, fetch detailed match data for mapped events
        betfair_market_ids: List of Betfair IDs to fetch details for (optional)
        max_match_details: Maximum number of match details to fetch (optional)
        
    Returns:
        Dict with status of each operation:
        {
            'fetch_success': bool,
            'mapping_success': bool,
            'details_fetched': int (if fetch_match_details=True),
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
    
    # Step 3: Optionally fetch match details for mapped events
    if fetch_match_details and result['mapping_success']:
        print("\n" + "="*70)
        print("FETCHING MATCH DETAILS")
        print("="*70)
        
        details_result = await fetch_match_details_for_mapped_events(
            betfair_market_ids=betfair_market_ids,
            max_matches=max_match_details
        )
        
        result['cached_events_count'] = details_result['cached_count']
        result['details_fetched'] = details_result['cached_count']
        result['details_failed'] = details_result['failed_count']
        result['details_skipped'] = details_result['skipped_count']
        result['details_filtered'] = details_result['filtered_count']
    
    # Overall success requires fetch and mapping
    result['overall_success'] = result['fetch_success'] and result['mapping_success']
    
    print("\n" + "="*70)
    if result['overall_success']:
        print("[KWIFF] ✅ Initialization completed successfully")
        if fetch_match_details:
            print(f"[KWIFF] 📦 Cached {result.get('details_fetched', 0)} match details")
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
def initialize_kwiff_sync(
    country: str = "GB",
    dry_run: bool = False,
    fetch_match_details: bool = False,
    betfair_market_ids: Optional[List[str]] = None,
    max_match_details: Optional[int] = None
) -> Dict[str, any]:
    """
    Synchronous wrapper for initialize_kwiff().
    Use this if calling from non-async code.
    
    Args:
        country: Country code (default: 'GB')
        dry_run: If True, mapping will show results without saving
        fetch_match_details: If True, fetch detailed match data
        betfair_market_ids: List of Betfair IDs to fetch details for
        max_match_details: Maximum number of match details to fetch
        
    Returns:
        Dict with status of each operation
    """
    return asyncio.run(
        initialize_kwiff(
            country=country,
            dry_run=dry_run,
            fetch_match_details=fetch_match_details,
            betfair_market_ids=betfair_market_ids,
            max_match_details=max_match_details
        )
    )


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
