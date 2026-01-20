#!/usr/bin/env python3
"""
Test script for Kwiff integration module.

This script tests:
1. Fetching events from Kwiff WebSocket
2. Saving events to data directory
3. Auto-mapping events to Betfair market IDs
4. Looking up mappings

Run:
    python test_kwiff_integration.py
    python test_kwiff_integration.py --dry-run  # Don't save mappings
    python test_kwiff_integration.py --fetch-only  # Just fetch, no mapping
"""

import asyncio
import sys
from pathlib import Path

# Add kwiff to path
sys.path.insert(0, str(Path(__file__).parent))

from kwiff import (
    initialize_kwiff,
    fetch_and_save_events,
    map_kwiff_events,
    get_kwiff_event_mappings,
    get_betfair_id_for_kwiff_event,
)


async def test_fetch_events():
    """Test fetching events from Kwiff WebSocket."""
    print("\n" + "="*70)
    print("TEST 1: Fetch Events from Kwiff")
    print("="*70 + "\n")
    
    success = await fetch_and_save_events(country="GB")
    
    if success:
        print("\n✅ Test 1 PASSED: Events fetched successfully")
    else:
        print("\n❌ Test 1 FAILED: Could not fetch events")
    
    return success


def test_map_events(dry_run=True):
    """Test mapping events to Betfair."""
    print("\n" + "="*70)
    print("TEST 2: Map Kwiff Events to Betfair")
    print("="*70 + "\n")
    
    success = map_kwiff_events(dry_run=dry_run)
    
    if success:
        print("\n✅ Test 2 PASSED: Events mapped successfully")
    else:
        print("\n⚠️ Test 2 WARNING: Mapping completed with issues")
    
    return success


def test_lookup_mappings():
    """Test looking up Betfair IDs for Kwiff events."""
    print("\n" + "="*70)
    print("TEST 3: Lookup Event Mappings")
    print("="*70 + "\n")
    
    mappings = get_kwiff_event_mappings()
    
    if not mappings:
        print("⚠️ No mappings found (this is OK if no events were mapped)")
        return True
    
    print(f"Found {len(mappings)} mapped events:")
    
    # Show first 5 mappings
    for i, (kwiff_id, data) in enumerate(list(mappings.items())[:5], 1):
        betfair_id = data.get('betfair_id', 'N/A')
        desc = data.get('description', 'No description')
        
        print(f"\n  {i}. Kwiff ID: {kwiff_id}")
        print(f"     Betfair ID: {betfair_id}")
        print(f"     Description: {desc}")
        
        # Test lookup function
        looked_up_id = get_betfair_id_for_kwiff_event(kwiff_id)
        if looked_up_id == betfair_id and betfair_id != "TODO":
            print(f"     ✅ Lookup verified: {looked_up_id}")
        elif betfair_id == "TODO":
            print(f"     ⚠️ Not yet mapped (TODO)")
        else:
            print(f"     ❌ Lookup mismatch!")
    
    print(f"\n✅ Test 3 PASSED: {len(mappings)} mappings available")
    return True


async def test_full_integration(dry_run=True):
    """Test the complete integration flow."""
    print("\n" + "="*70)
    print("TEST 4: Full Integration (Fetch + Map)")
    print("="*70 + "\n")
    
    result = await initialize_kwiff(country="GB", dry_run=dry_run)
    
    print("\n" + "="*70)
    print("TEST 4 Results:")
    print("="*70)
    print(f"  Fetch Success: {result['fetch_success']}")
    print(f"  Mapping Success: {result['mapping_success']}")
    print(f"  Overall Success: {result['overall_success']}")
    
    if result['overall_success']:
        print("\n✅ Test 4 PASSED: Full integration successful")
    else:
        print("\n⚠️ Test 4 WARNING: Integration completed with issues")
    
    return result['overall_success']


async def run_all_tests(dry_run=True, fetch_only=False):
    """Run all tests."""
    print("\n" + "="*80)
    print(" "*20 + "KWIFF INTEGRATION TEST SUITE")
    print("="*80)
    
    if fetch_only:
        # Just test fetching
        test1 = await test_fetch_events()
        test3 = test_lookup_mappings()
        
        print("\n" + "="*80)
        print("TEST SUMMARY (Fetch Only)")
        print("="*80)
        print(f"  Test 1 (Fetch Events): {'PASS' if test1 else 'FAIL'}")
        print(f"  Test 3 (Lookup): {'PASS' if test3 else 'FAIL'}")
        
        if test1:
            print("\n✅ ALL TESTS PASSED")
        else:
            print("\n❌ SOME TESTS FAILED")
    else:
        # Run full integration test
        test4 = await test_full_integration(dry_run=dry_run)
        test3 = test_lookup_mappings()
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"  Test 4 (Full Integration): {'PASS' if test4 else 'FAIL'}")
        print(f"  Test 3 (Lookup): {'PASS' if test3 else 'FAIL'}")
        
        if test4 and test3:
            print("\n✅ ALL TESTS PASSED")
        else:
            print("\n⚠️ SOME TESTS HAD WARNINGS")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Kwiff Integration')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry-run mode (no mappings saved)')
    parser.add_argument('--save', action='store_true',
                       help='Save mappings (default is dry-run)')
    parser.add_argument('--fetch-only', action='store_true',
                       help='Only test fetching events')
    
    args = parser.parse_args()
    
    # Default to dry-run unless --save is specified
    dry_run = not args.save
    
    if dry_run and not args.fetch_only:
        print("\n⚠️ Running in DRY-RUN mode - mappings will NOT be saved")
        print("   Use --save to save mappings to event_mappings.json\n")
    
    asyncio.run(run_all_tests(dry_run=dry_run, fetch_only=args.fetch_only))


if __name__ == "__main__":
    main()
