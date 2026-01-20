#!/usr/bin/env python3
"""
Comprehensive Test - Kwiff WebSocket Client
Demonstrates all functionality and validates the implementation.
"""

import asyncio
import json
from pathlib import Path
from kwiff_client import KwiffClient


async def test_basic_connection():
    """Test 1: Basic connection and handshake."""
    print("\n" + "="*60)
    print("TEST 1: Basic Connection & Handshake")
    print("="*60)
    
    try:
        async with KwiffClient() as client:
            print("✅ Successfully connected to Kwiff WebSocket")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_fetch_events():
    """Test 2: Fetch football events."""
    print("\n" + "="*60)
    print("TEST 2: Fetch Football Events")
    print("="*60)
    
    try:
        async with KwiffClient() as client:
            print("Fetching football events for GB...")
            
            events = await client.get_football_events(country="GB")
            
            if not events:
                print("❌ No events received")
                return False
            
            if "data" not in events or "events" not in events["data"]:
                print("❌ Unexpected response format")
                return False
            
            event_list = events["data"]["events"]
            print(f"✅ Received {len(event_list)} football events")
            
            # Validate event structure
            if len(event_list) > 0:
                first_event = event_list[0]
                required_fields = ["id", "sportId", "homeTeam", "awayTeam", "competition"]
                
                missing = [f for f in required_fields if f not in first_event]
                if missing:
                    print(f"❌ Missing fields: {missing}")
                    return False
                
                print(f"✅ Event structure validated")
                print(f"   - ID: {first_event['id']}")
                print(f"   - Competition: {first_event['competition']['name']}")
                print(f"   - Match: {first_event['homeTeam']['name']} vs {first_event['awayTeam']['name']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_data_persistence():
    """Test 3: Save and load events from file."""
    print("\n" + "="*60)
    print("TEST 3: Data Persistence")
    print("="*60)
    
    try:
        output_file = Path("test_events.json")
        
        # Fetch and save
        async with KwiffClient() as client:
            print("Fetching events...")
            events = await client.get_football_events(country="GB")
            
            with open(output_file, "w") as f:
                json.dump(events, f, indent=2)
            
            print(f"✅ Saved {len(events['data']['events'])} events to {output_file}")
        
        # Load and verify
        with open(output_file, "r") as f:
            loaded = json.load(f)
        
        if loaded == events:
            print("✅ Data integrity verified (save/load match)")
        else:
            print("❌ Data mismatch after save/load")
            return False
        
        # Cleanup
        output_file.unlink()
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_event_details():
    """Test 4: Validate complete event details."""
    print("\n" + "="*60)
    print("TEST 4: Event Details Validation")
    print("="*60)
    
    try:
        async with KwiffClient() as client:
            events = await client.get_football_events(country="GB")
            event_list = events["data"]["events"]
            
            if len(event_list) == 0:
                print("❌ No events to validate")
                return False
            
            # Check first event in detail
            event = event_list[0]
            
            checks = {
                "Basic Info": {
                    "id": event.get("id"),
                    "sportId": event.get("sportId"),
                    "status": event.get("status"),
                },
                "Teams": {
                    "homeTeam": event.get("homeTeam", {}).get("name"),
                    "awayTeam": event.get("awayTeam", {}).get("name"),
                },
                "Dates": {
                    "startDate": event.get("startDate"),
                },
                "Competition": {
                    "name": event.get("competition", {}).get("name"),
                },
                "Betting": {
                    "bettingStatus": event.get("bettingStatus"),
                    "betBuilderEnabled": event.get("betBuilderEnabled"),
                },
            }
            
            print("Event details:")
            for category, fields in checks.items():
                print(f"\n  {category}:")
                for name, value in fields.items():
                    status = "✅" if value else "❌"
                    print(f"    {status} {name}: {value}")
            
            # Check for betting offers
            if "details" in event and "offers" in event["details"]:
                offers = event["details"]["offers"]
                print(f"\n  Betting Markets:")
                print(f"    ✅ {len(offers)} markets available")
                
                for i, offer in enumerate(offers[:3]):
                    print(f"      - {offer.get('name')} ({len(offer.get('outcomes', []))} outcomes)")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_multiple_countries():
    """Test 5: Fetch events for different countries."""
    print("\n" + "="*60)
    print("TEST 5: Multiple Countries Support")
    print("="*60)
    
    try:
        countries = ["GB", "IE"]
        results = {}
        
        for country in countries:
            async with KwiffClient() as client:
                print(f"\nFetching events for {country}...")
                events = await client.get_football_events(country=country)
                
                count = len(events["data"]["events"]) if events and "data" in events else 0
                results[country] = count
                print(f"  ✅ Got {count} events for {country}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print("KWIFF WEBSOCKET CLIENT - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Fetch Events", test_fetch_events),
        ("Data Persistence", test_data_persistence),
        ("Event Details", test_event_details),
        ("Multiple Countries", test_multiple_countries),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"\n[ERROR] Test crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*70}")
    print(f"RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("ALL TESTS PASSED! Implementation is working correctly.")
    else:
        print(f"{total - passed} test(s) failed.")
    
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
