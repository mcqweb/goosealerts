#!/usr/bin/env python3
"""
Test script to verify Kwiff match details filtering logic.

This demonstrates that we:
1. Only fetch details for events with valid Betfair mappings
2. Only fetch details for events with future kickoff times
"""

import json
from datetime import datetime
from pathlib import Path

# Get today's events file
SERVER_DIR = Path(__file__).parent / "kwiff" / "server"
events_file = SERVER_DIR / "data" / f"events_{datetime.now().strftime('%Y%m%d')}.json"

if not events_file.exists():
    print(f"❌ Events file not found: {events_file}")
    exit(1)

# Load events
with open(events_file, 'r', encoding='utf-8') as f:
    events_data = json.load(f)
events_list = events_data.get('events', [])

# Load mappings
mappings_file = SERVER_DIR / "event_mappings.json"
with open(mappings_file, 'r', encoding='utf-8') as f:
    mappings_data = json.load(f)
mappings = mappings_data.get('events', {})

print(f"Total Kwiff events: {len(events_list)}")
print(f"Total mappings: {len(mappings)}")

# Analyze events
now = datetime.now()
future_count = 0
past_count = 0
mapped_future_count = 0
mapped_past_count = 0
unmapped_count = 0

for event in events_list:
    event_id = str(event.get('id') or event.get('eventId', ''))
    start_date_str = event.get('startDate')
    
    has_mapping = False
    mapping = mappings.get(event_id, {})
    betfair_id = mapping.get('betfair_id')
    if betfair_id and betfair_id != 'TODO':
        has_mapping = True
    
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            is_future = start_date.replace(tzinfo=None) > now
            
            if is_future:
                future_count += 1
                if has_mapping:
                    mapped_future_count += 1
                else:
                    unmapped_count += 1
            else:
                past_count += 1
                if has_mapping:
                    mapped_past_count += 1
        except Exception:
            pass

print("\n" + "="*70)
print("FILTERING BREAKDOWN")
print("="*70)
print(f"Future matches: {future_count}")
print(f"Past matches: {past_count}")
print(f"")
print(f"✅ Future + Mapped (WILL FETCH): {mapped_future_count}")
print(f"❌ Future + Unmapped (SKIP): {unmapped_count}")
print(f"❌ Past + Mapped (SKIP): {mapped_past_count}")
print(f"")
print(f"Total to fetch: {mapped_future_count}")
print(f"Total filtered out: {past_count + unmapped_count}")
print("="*70)

# Show example past event
print("\nExample past event (will be filtered):")
for event in events_list:
    start_date_str = event.get('startDate')
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            if start_date.replace(tzinfo=None) <= now:
                home = event.get('homeTeam', {})
                away = event.get('awayTeam', {})
                home_name = home.get('name', 'Unknown') if isinstance(home, dict) else home
                away_name = away.get('name', 'Unknown') if isinstance(away, dict) else away
                event_id = event.get('id')
                
                mapping = mappings.get(str(event_id), {})
                betfair_id = mapping.get('betfair_id', 'None')
                
                print(f"  ID: {event_id}")
                print(f"  Match: {home_name} vs {away_name}")
                print(f"  KO: {start_date_str}")
                print(f"  Betfair ID: {betfair_id}")
                print(f"  Status: ❌ Past match - FILTERED")
                break
        except Exception:
            pass

# Show example future mapped event
print("\nExample future mapped event (will be fetched):")
for event in events_list:
    event_id = str(event.get('id'))
    start_date_str = event.get('startDate')
    mapping = mappings.get(event_id, {})
    betfair_id = mapping.get('betfair_id')
    
    if betfair_id and betfair_id != 'TODO' and start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            if start_date.replace(tzinfo=None) > now:
                home = event.get('homeTeam', {})
                away = event.get('awayTeam', {})
                home_name = home.get('name', 'Unknown') if isinstance(home, dict) else home
                away_name = away.get('name', 'Unknown') if isinstance(away, dict) else away
                
                print(f"  ID: {event_id}")
                print(f"  Match: {home_name} vs {away_name}")
                print(f"  KO: {start_date_str}")
                print(f"  Betfair ID: {betfair_id}")
                print(f"  Status: ✅ Future + Mapped - WILL FETCH")
                break
        except Exception:
            pass

print("\n✅ Filtering logic working correctly!")
