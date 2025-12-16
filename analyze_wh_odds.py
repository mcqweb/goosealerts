import json
from collections import defaultdict

# Load the tracking data
with open('wh_odds_tracking/OB_EV37938547.json', 'r') as f:
    data = json.load(f)

print(f"Match: {data['match_name']}")
print(f"Total records: {len(data['records'])}\n")

# Group by player and market type
players = defaultdict(list)
for record in data['records']:
    key = (record['player_name'], record['market_type'])
    players[key].append({
        'timestamp': record['timestamp'],
        'wh_odds': record['wh_odds'],
        'boosted_odds': record['boosted_odds'],
        'lay_odds': record['lay_odds']
    })

# Find players with odds changes
changes = {}
for key, records in players.items():
    wh_odds_set = set(r['wh_odds'] for r in records)
    if len(wh_odds_set) > 1:
        changes[key] = records

print(f"Total players tracked: {len(players)}")
print(f"Players with odds changes: {len(changes)}\n")

if changes:
    print("=" * 80)
    print("ODDS CHANGES DETECTED:")
    print("=" * 80)
    
    for (player_name, market_type), records in sorted(changes.items()):
        print(f"\n{player_name} ({market_type}):")
        prev_odds = None
        for i, r in enumerate(records):
            ts = r['timestamp'][:19].replace('T', ' ')
            wh = r['wh_odds']
            boosted = r['boosted_odds']
            
            if i == 0:
                print(f"  {ts}: WH {wh} -> Boosted {boosted}")
                prev_odds = wh
            elif wh != prev_odds:
                print(f"  {ts}: WH {wh} -> Boosted {boosted} *** CHANGED from {prev_odds}")
                prev_odds = wh
            
            if i >= 4:  # Show first 5 records
                if len(records) > 5:
                    print(f"  ... and {len(records) - 5} more records")
                break
else:
    print("No odds changes detected yet. All prices have remained stable.")

# Show some stats
print("\n" + "=" * 80)
print("SAMPLE OF CURRENT ODDS:")
print("=" * 80)
for (player_name, market_type), records in sorted(players.items())[:10]:
    latest = records[-1]
    print(f"{player_name} ({market_type}): WH {latest['wh_odds']} -> Boosted {latest['boosted_odds']}, Lay {latest['lay_odds']}")
