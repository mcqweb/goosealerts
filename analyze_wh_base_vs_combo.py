import json
import os
from collections import defaultdict
from datetime import datetime

def load_tracking_data(match_id):
    """Load both combo and base odds tracking data for a match."""
    tracking_dir = 'wh_odds_tracking'
    
    combo_file = os.path.join(tracking_dir, f"{match_id}.json")
    base_file = os.path.join(tracking_dir, f"{match_id}_base.json")
    
    combo_data = None
    base_data = None
    
    if os.path.exists(combo_file):
        with open(combo_file, 'r') as f:
            combo_data = json.load(f)
    
    if os.path.exists(base_file):
        with open(base_file, 'r') as f:
            base_data = json.load(f)
    
    return combo_data, base_data

def analyze_changes(combo_data, base_data):
    """Compare base odds changes with combo odds changes."""
    
    if not combo_data or not base_data:
        print("Missing tracking data")
        return
    
    print(f"Match: {combo_data['match_name']}")
    print(f"Combo records: {len(combo_data['records'])}")
    print(f"Base odds snapshots: {len(base_data['records'])}")
    print("=" * 80)
    
    # Build a lookup for combo odds at any timestamp
    # Structure: {(player, market): [(timestamp, odds), ...]}
    combo_timeline = defaultdict(list)
    for record in combo_data['records']:
        key = (record['player_name'], record['market_type'])
        combo_timeline[key].append((record['timestamp'], record['wh_odds']))
    
    # Sort each timeline
    for key in combo_timeline:
        combo_timeline[key].sort()
    
    def get_combo_odds_at_time(player, market, timestamp):
        """Get combo odds for a player/market at or near a given timestamp."""
        key = (player, market)
        if key not in combo_timeline:
            return None, None
        
        timeline = combo_timeline[key]
        
        # Find the closest record at or before this timestamp
        prev_odds = None
        next_odds = None
        
        for ts, odds in timeline:
            if ts <= timestamp:
                prev_odds = odds
            elif ts > timestamp and next_odds is None:
                next_odds = odds
                break
        
        return prev_odds, next_odds
    
    # Build timeline of base odds changes
    base_changes = defaultdict(list)
    
    for i, record in enumerate(base_data['records'][1:], 1):  # Skip first record
        prev_record = base_data['records'][i-1]
        timestamp = record['timestamp']
        
        for key, odds in record['odds'].items():
            prev_odds = prev_record['odds'].get(key)
            if prev_odds and prev_odds != odds:
                player_name, market_type = key.split('|')
                
                # Get corresponding combo odds
                combo_before, combo_after = get_combo_odds_at_time(player_name, market_type, timestamp)
                
                base_changes[timestamp].append({
                    'player': player_name,
                    'market': market_type,
                    'old_odds': prev_odds,
                    'new_odds': odds,
                    'change': odds - prev_odds,
                    'combo_before': combo_before,
                    'combo_after': combo_after
                })
    
    # Build timeline of combo odds changes
    combo_changes = defaultdict(list)
    
    # Group combo records by player and market
    player_combos = defaultdict(list)
    for record in combo_data['records']:
        key = (record['player_name'], record['market_type'])
        player_combos[key].append(record)
    
    # Find changes in combo odds
    for (player_name, market_type), records in player_combos.items():
        for i in range(1, len(records)):
            prev = records[i-1]
            curr = records[i]
            
            if prev['wh_odds'] != curr['wh_odds']:
                timestamp = curr['timestamp']
                combo_changes[timestamp].append({
                    'player': player_name,
                    'market': market_type,
                    'old_odds': prev['wh_odds'],
                    'new_odds': curr['wh_odds'],
                    'change': curr['wh_odds'] - prev['wh_odds']
                })
    
    # Analyze correlation
    print("\n" + "=" * 80)
    print("BASE ODDS CHANGES (with corresponding combo odds):")
    print("=" * 80)
    
    if not base_changes:
        print("No base odds changes detected yet")
    else:
        for timestamp in sorted(base_changes.keys()):
            ts_str = timestamp[:19].replace('T', ' ')
            print(f"\n{ts_str}:")
            for change in base_changes[timestamp]:
                direction = "↑" if change['change'] > 0 else "↓"
                base_info = f"  {direction} {change['player']} ({change['market']}): {change['old_odds']} → {change['new_odds']}"
                
                # Add combo odds info
                if change['combo_before'] is not None:
                    if change['combo_after'] and change['combo_after'] != change['combo_before']:
                        combo_info = f" [Combo: {change['combo_before']} → {change['combo_after']}]"
                    else:
                        combo_info = f" [Combo: {change['combo_before']} unchanged]"
                else:
                    combo_info = ""  # No combo data for this player/market
                
                print(base_info + combo_info)
    
    print("\n" + "=" * 80)
    print("COMBO ODDS CHANGES:")
    print("=" * 80)
    
    if not combo_changes:
        print("No combo odds changes detected yet")
    else:
        for timestamp in sorted(combo_changes.keys()):
            ts_str = timestamp[:19].replace('T', ' ')
            print(f"\n{ts_str}:")
            for change in combo_changes[timestamp]:
                direction = "↑" if change['change'] > 0 else "↓"
                print(f"  {direction} {change['player']} ({change['market']}): {change['old_odds']} → {change['new_odds']}")
    
    # Correlation analysis
    print("\n" + "=" * 80)
    print("CORRELATION ANALYSIS:")
    print("=" * 80)
    
    base_timestamps = set(base_changes.keys())
    combo_timestamps = set(combo_changes.keys())
    
    # Only show correlation analysis if we have base data
    if not base_timestamps:
        print("\nNo base odds tracking data available for this match (monitoring may have started later)")
        return
    
    # Find combo changes that happened at same time as base changes
    correlated = base_timestamps & combo_timestamps
    combo_only = combo_timestamps - base_timestamps
    base_only = base_timestamps - combo_timestamps
    
    print(f"\nTotal base odds change events: {len(base_timestamps)}")
    print(f"Total combo odds change events: {len(combo_timestamps)}")
    print(f"Correlated changes (same timestamp): {len(correlated)}")
    print(f"Combo changes without base change: {len(combo_only)}")
    print(f"Base changes without combo change: {len(base_only)}")
    
    if correlated:
        print("\nCorrelated changes (happened at same time):")
        for ts in sorted(correlated):
            ts_display = ts[:19].replace('T', ' ')
            base_desc = ', '.join([f"{c['player']} {c['market']}" for c in base_changes[ts]])
            combo_desc = ', '.join([f"{c['player']} {c['market']}" for c in combo_changes[ts]])
            print(f"\n  {ts_display}:")
            print(f"    Base: {base_desc}")
            print(f"    Combo: {combo_desc}")
    
    # Only show combo-only changes if they occurred after base monitoring started
    if combo_only and base_timestamps:
        first_base_ts = min(base_timestamps)
        combo_only_after_base = [ts for ts in combo_only if ts >= first_base_ts]
        
        if combo_only_after_base:
            print("\nCombo changes WITHOUT corresponding base change (after base monitoring started):")
            for ts in sorted(combo_only_after_base[:5]):  # Show first 5
                ts_display = ts[:19].replace('T', ' ')
                combo_desc = ', '.join([f"{c['player']} {c['market']}" for c in combo_changes[ts]])
                print(f"  {ts_display}: {combo_desc}")
            if len(combo_only_after_base) > 5:
                print(f"  ... and {len(combo_only_after_base) - 5} more")

if __name__ == "__main__":
    # Find all match IDs with tracking data
    tracking_dir = 'wh_odds_tracking'
    if not os.path.exists(tracking_dir):
        print(f"Tracking directory not found: {tracking_dir}")
        exit(1)
    
    # Get all match IDs (files without _base suffix)
    match_ids = set()
    for filename in os.listdir(tracking_dir):
        if filename.endswith('.json') and not filename.endswith('_base.json'):
            match_id = filename.replace('.json', '')
            match_ids.add(match_id)
    
    if not match_ids:
        print("No tracking data found")
        exit(1)
    
    print(f"Found {len(match_ids)} matches with tracking data\n")
    
    for match_id in sorted(match_ids):
        combo_data, base_data = load_tracking_data(match_id)
        analyze_changes(combo_data, base_data)
        print("\n" + "=" * 80 + "\n")
