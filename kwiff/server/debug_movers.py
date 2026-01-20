import json

# Check events file
events_data = json.load(open('data/events_20251210.json'))
events = events_data.get('events', [])
print(f"Events in file: {len(events)}")

if events:
    sample = events[0]
    print(f"\nSample event ID: {sample.get('eventId')}")
    players = sample.get('players', [])
    print(f"Players: {len(players)}")
    if players:
        print(f"First player: {players[0].get('name')} - anytime odds: {players[0].get('anytimeOdds')}")

# Check combos file
combos_data = json.load(open('data/combos_20251210.json'))
combo_events = combos_data.get('events', [])
print(f"\nCombo events: {len(combo_events)}")

if combo_events:
    sample_combo = combo_events[0]
    event_id = sample_combo.get('metadata', {}).get('kwiff_event_id')
    combos = sample_combo.get('combos', [])
    print(f"Sample combo event ID: {event_id}")
    print(f"Combos: {len(combos)}")
    if combos:
        print(f"First combo: {combos[0].get('name')} - back odds: {combos[0].get('back_odds')}")
