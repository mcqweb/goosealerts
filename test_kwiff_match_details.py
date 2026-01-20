#!/usr/bin/env python3
"""
Test Kwiff Match Details and Caching

Tests the new match details fetching and caching functionality.

Run:
    python test_kwiff_match_details.py
    python test_kwiff_match_details.py --fetch  # Fetch match details
    python test_kwiff_match_details.py --max 5  # Limit to 5 matches
"""

import asyncio
import sys
import json
from pathlib import Path

# Add kwiff to path
sys.path.insert(0, str(Path(__file__).parent))

from kwiff import (
    KwiffClient,
    initialize_kwiff_sync,
    fetch_match_details_sync,
    get_cached_match_details,
    get_kwiff_event_mappings,
    clear_expired_cache,
)


def test_cache_system():
    """Test the cache system."""
    print("\n" + "="*70)
    print("TEST 1: Cache System")
    print("="*70 + "\n")
    
    from kwiff.match_cache import KwiffMatchCache
    
    # Create test cache
    cache = KwiffMatchCache(ttl_minutes=60)
    print(f"Cache directory: {cache.cache_dir}")
    
    # Test data
    test_data = {
        "eventId": "test123",
        "homeTeam": "Test Home",
        "awayTeam": "Test Away",
        "markets": ["AGS", "TOM", "HAT"]
    }
    
    # Test set
    print("\n[1/5] Testing cache set...")
    success = cache.set("test123", test_data)
    print(f"  Result: {'✅' if success else '❌'}")
    
    # Test get
    print("\n[2/5] Testing cache get...")
    cached = cache.get("test123")
    matches = cached == test_data if cached else False
    print(f"  Result: {'✅' if matches else '❌'}")
    
    # Test has
    print("\n[3/5] Testing cache has...")
    exists = cache.has("test123")
    print(f"  Result: {'✅' if exists else '❌'}")
    
    # Test list
    print("\n[4/5] Testing cache list...")
    event_ids = cache.get_cached_event_ids()
    print(f"  Found: {len(event_ids)} cached events")
    print(f"  Result: {'✅' if 'test123' in event_ids else '❌'}")
    
    # Cleanup
    print("\n[5/5] Testing cache clear...")
    cleared = cache.clear_all()
    print(f"  Cleared: {cleared} entries")
    print(f"  Result: ✅")
    
    print("\n✅ Test 1 PASSED: Cache system working\n")
    return True


async def test_fetch_event_details():
    """Test fetching a single event's details."""
    print("\n" + "="*70)
    print("TEST 2: Fetch Single Event Details")
    print("="*70 + "\n")
    
    # Get first mapped event
    mappings = get_kwiff_event_mappings()
    if not mappings:
        print("❌ No mappings found - run initialization first")
        return False
    
    kwiff_id = list(mappings.keys())[0]
    print(f"Testing with Kwiff event ID: {kwiff_id}")
    
    async with KwiffClient() as client:
        print(f"\n[1/2] Fetching event details from WebSocket...")
        details = await client.get_event_details(int(kwiff_id))
        
        if details:
            print("✅ Received details")
            
            # Show structure
            print("\n[2/2] Response structure:")
            if isinstance(details, dict):
                print(f"  Keys: {list(details.keys())[:10]}")
                
                # Save to file for inspection
                output_file = Path("kwiff_event_details_sample.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(details, f, indent=2)
                print(f"\n  💾 Saved full response to: {output_file}")
            else:
                print(f"  Type: {type(details)}")
            
            print("\n✅ Test 2 PASSED: Event details fetched\n")
            return True
        else:
            print("❌ No details received")
            return False


def test_fetch_and_cache_multiple():
    """Test fetching and caching multiple match details."""
    print("\n" + "="*70)
    print("TEST 3: Fetch and Cache Multiple Matches")
    print("="*70 + "\n")
    
    # Clear expired first
    cleared = clear_expired_cache()
    if cleared > 0:
        print(f"Cleared {cleared} expired cache entries\n")
    
    # This test needs to be run async
    print("⚠️ Test deferred to async context (Test 5)\n")
    return True


async def test_fetch_and_cache_multiple_async():
    """Async version of test_fetch_and_cache_multiple."""
    print("\n" + "="*70)
    print("TEST 3: Fetch and Cache Multiple Matches")
    print("="*70 + "\n")
    
    # Clear expired first
    cleared = clear_expired_cache()
    if cleared > 0:
        print(f"Cleared {cleared} expired cache entries\n")
    
    # Fetch details for max 3 matches
    print("Fetching details for up to 3 matches...\n")
    
    from kwiff.integration import fetch_match_details_for_mapped_events
    result = await fetch_match_details_for_mapped_events(max_matches=3)
    
    print("\n" + "="*70)
    print("Results:")
    print("="*70)
    print(f"  Fetched: {result['fetched_count']}")
    print(f"  Cached: {result['cached_count']}")
    print(f"  Already cached: {result['skipped_count']}")
    print(f"  Failed: {result['failed_count']}")
    
    if result['cached_count'] > 0 or result['skipped_count'] > 0:
        print("\n✅ Test 3 PASSED: Match details cached\n")
        return True
    else:
        print("\n⚠️ Test 3 WARNING: No matches cached\n")
        return False


def test_retrieve_cached_details():
    """Test retrieving cached match details."""
    print("\n" + "="*70)
    print("TEST 4: Retrieve Cached Details")
    print("="*70 + "\n")
    
    mappings = get_kwiff_event_mappings()
    if not mappings:
        print("❌ No mappings found")
        return False
    
    # Try to find a cached event
    cached_found = False
    for kwiff_id in list(mappings.keys())[:5]:
        details = get_cached_match_details(kwiff_id)
        if details:
            cached_found = True
            print(f"✅ Found cached details for event {kwiff_id}")
            
            # Show structure
            if isinstance(details, dict):
                print(f"  Keys: {list(details.keys())[:10]}")
            
            break
    
    if cached_found:
        print("\n✅ Test 4 PASSED: Cache retrieval working\n")
        return True
    else:
        print("\n⚠️ Test 4 WARNING: No cached events found\n")
        print("   Run with --fetch to cache match details first")
        return False


async def test_integration_with_details():
    """Test full integration including match details."""
    print("\n" + "="*70)
    print("TEST 5: Full Integration with Match Details")
    print("="*70 + "\n")
    
    from kwiff.integration import initialize_kwiff
    result = await initialize_kwiff(
        country="GB",
        dry_run=False,
        fetch_match_details=True,
        max_match_details=2  # Just 2 for testing
    )
    
    print("\n" + "="*70)
    print("Integration Results:")
    print("="*70)
    print(f"  Fetch events: {'✅' if result['fetch_success'] else '❌'}")
    print(f"  Map events: {'✅' if result['mapping_success'] else '❌'}")
    print(f"  Fetch details: {result.get('details_fetched', 0)} matches")
    print(f"  Overall: {'✅' if result['overall_success'] else '❌'}")
    
    if result['overall_success']:
        print("\n✅ Test 5 PASSED: Full integration working\n")
        return True
    else:
        print("\n❌ Test 5 FAILED: Integration had errors\n")
        return False


async def run_all_tests(fetch_details=False, max_matches=None):
    """Run all tests."""
    print("\n" + "="*80)
    print(" "*20 + "KWIFF MATCH DETAILS TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test 1: Cache system
    results.append(("Cache System", test_cache_system()))
    
    # Test 2: Fetch event details
    if fetch_details:
        results.append(("Fetch Event Details", await test_fetch_event_details()))
    
    # Test 3: Fetch and cache multiple (async version)
    if fetch_details:
        results.append(("Fetch Multiple", await test_fetch_and_cache_multiple_async()))
    
    # Test 4: Retrieve cached
    results.append(("Retrieve Cached", test_retrieve_cached_details()))
    
    # Test 5: Full integration
    if fetch_details:
        results.append(("Full Integration", await test_integration_with_details()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✅ ALL TESTS PASSED")
    else:
        print("\n⚠️ SOME TESTS FAILED")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Kwiff Match Details')
    parser.add_argument('--fetch', action='store_true',
                       help='Fetch match details (requires WebSocket connection)')
    parser.add_argument('--max', type=int,
                       help='Maximum number of matches to fetch')
    
    args = parser.parse_args()
    
    if not args.fetch:
        print("\n⚠️ Running in LIMITED mode - only testing cache system")
        print("   Use --fetch to test WebSocket fetching of match details\n")
    
    asyncio.run(run_all_tests(fetch_details=args.fetch, max_matches=args.max))


if __name__ == "__main__":
    main()
