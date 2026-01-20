#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarize combos from combos_YYYYMMDD.json by match and player, showing back/lay odds and liquidity.
"""

import json
import os
import sys
import argparse
import requests
import random
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# Discord webhook URL (same as monitor_combos.py)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1447536804478717984/YPoFdLyu987B4Tp35Toa_WK6mH3bRPDKUTnFrQqcw0DBfT1bjdR5JUu2TakaU_wqyfoH"

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def calculate_rating(back_odds, lay_odds):
    """Calculate rating as Back/Lay percentage."""
    if back_odds == 'N/A' or lay_odds == 'N/A':
        return None
    try:
        back_float = float(back_odds)
        lay_float = float(lay_odds)
        if lay_float == 0:
            return None
        rating = (back_float / lay_float) * 100
        return rating
    except (ValueError, TypeError):
        return None


def format_player_name(name):
    """Convert 'Surname Firstname' to 'Firstname Surname'."""
    if not name or name == 'Unknown':
        return name
    parts = name.split()
    if len(parts) >= 2:
        # Assume first part is surname, rest is first name
        return ' '.join(parts[1:]) + ' ' + parts[0]
    return name


def get_random_gif():
    """Get a random GIF from the gifs folder."""
    gifs_dir = os.path.join(os.path.dirname(__file__), 'gifs')
    if not os.path.exists(gifs_dir):
        return None
    
    gif_files = [f for f in os.listdir(gifs_dir) if f.lower().endswith(('.gif', '.png', '.jpg', '.jpeg'))]
    if not gif_files:
        return None
    
    selected_gif = random.choice(gif_files)
    return os.path.join(gifs_dir, selected_gif)


def load_events_file():
    """Load the events_{YYYYMMDD}.json file for today."""
    today = datetime.now().strftime("%Y%m%d")
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    events_file = os.path.join(data_dir, f"events_{today}.json")
    
    if os.path.exists(events_file):
        with open(events_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('events', [])
    return []


def show_biggest_movers(combo_data):
    """Show biggest odds movers from events file to combos file."""
    # Load original events file
    events = load_events_file()
    if not events:
        return
    
    # Build lookup of original anytime odds by player name and event
    original_odds = {}
    for event in events:
        event_id = str(event.get('eventId'))
        for player in event.get('players', []):
            player_name = player.get('name', '')
            anytime_odds = player.get('anytimeOdds')
            if player_name and anytime_odds:
                original_odds[f"{event_id}_{player_name}"] = anytime_odds
    
    # Calculate movers
    movers = []
    for event_data in combo_data.get('events', []):
        event_id = event_data.get('event_id')
        fixture = event_data.get('fixture', {})
        home_team = fixture.get('home_team', 'Unknown')
        away_team = fixture.get('away_team', 'Unknown')
        
        for combo in event_data.get('combos', []):
            player_name = combo.get('name', '')
            kwiff_odds = combo.get('kwiff_odds')  # Current combo odds from Kwiff
            lay_odds = combo.get('lay_odds', 0)
            
            # Skip if kwiff_odds is null
            if kwiff_odds is None:
                continue
            
            key = f"{event_id}_{player_name}"
            if key in original_odds:
                original = original_odds[key]
                try:
                    original_float = float(original)
                    kwiff_float = float(kwiff_odds)
                    change = kwiff_float - original_float
                    change_percent = (change / original_float) * 100
                    
                    movers.append({
                        'player': format_player_name(player_name),
                        'fixture': f"{home_team} vs {away_team}",
                        'original': original_float,
                        'current': kwiff_float,
                        'lay_odds': lay_odds,
                        'change': change,
                        'change_percent': change_percent
                    })
                except (ValueError, TypeError, ZeroDivisionError):
                    pass
    
    if not movers:
        return
    
    # Sort by absolute change percentage
    movers.sort(key=lambda x: abs(x['change_percent']), reverse=True)
    
    # Display biggest movers
    print(f"{'='*110}")
    print(f"BIGGEST MOVERS (Anytime Odds)")
    print(f"{'='*110}")
    print(f"{'Player':<30} {'Match':<35} {'Original':>8} {'Boosted':>8} {'Current Lay':>8}")
    print(f"{'-'*110}")
    
    for mover in movers[:15]:  # Show top 15
        player = mover['player'][:29]
        fixture = mover['fixture'][:34]
        original = f"{mover['original']:.2f}"
        current = f"{mover['current']:.2f}"
        lay = f"{mover['lay_odds']:.2f}"
        pct = f"{mover['change_percent']:+.1f}%"
        if float(current) > 1:
            print(f"{player:<30} {fixture:<35} {original:>8} {current:>8} {lay:>8}")
    
    print(f"{'='*110}\n")


def send_match_to_discord(match_key, match_data, include_gifs=False):
    """Send a match summary as a Discord embed."""
    info = match_data['info']
    players = match_data['players']
    
    # Extract fixture info
    home_team = match_key.split(' vs ')[0]
    away_team = match_key.split(' vs ')[1] if ' vs ' in match_key else 'Unknown'
    competition = info['competition']
    start_date = info['start_date']
    
    # Extract kick-off time
    kick_off_time = 'Unknown'
    if start_date and 'T' in start_date:
        try:
            kick_off_time = start_date.split('T')[1][:5]
        except:
            pass
    
    # Build player list for embed
    player_lines = []
    for player in sorted(players, key=lambda x: x['rating'] if x['rating'] else 0, reverse=True):
        name = format_player_name(player['name'])[:25]
        back_odds = str(player['back_odds'])
        
        # Show best exchange and all exchanges if available
        best_exchange = player.get('best_exchange', 'Betfair')
        all_exchanges = player.get('all_exchanges')
        
        if all_exchanges:
            # Use all_exchanges display (e.g., "Betfair @ 5.0 (£150) | Smarkets @ 4.8")
            lay_display = all_exchanges
        else:
            # Fallback to simple display
            lay_odds = str(player['lay_odds'])
            lay_size = player.get('lay_size')
            if lay_size:
                lay_display = f"{best_exchange} @ {lay_odds} (£{lay_size:.2f})"
            else:
                lay_display = f"{best_exchange} @ {lay_odds}"
        
        rating = f"{player['rating']:.1f}%" if player['rating'] else "N/A"
        
        player_lines.append(f"**{name}**: {back_odds} | {lay_display} | {rating}")
    
    # Split into multiple fields if too long
    fields = []
    current_field_lines = []
    current_field_value = ""
    
    for line in player_lines:
        test_value = current_field_value + line + "\n"
        if len(test_value) > 1024:
            # Save current field and start new one
            if current_field_value:
                fields.append({
                    "name": "Players" if not fields else "Players (continued)",
                    "value": current_field_value.strip(),
                    "inline": False
                })
            current_field_value = line + "\n"
        else:
            current_field_value = test_value
    
    # Add remaining lines
    if current_field_value:
        fields.append({
            "name": "Players" if not fields else "Players (continued)",
            "value": current_field_value.strip(),
            "inline": False
        })
    
    # Summary stats
    total_combos = len(players)
    total_lay_size = sum(p['lay_size'] for p in players)
    profitable = sum(1 for p in players if p['rating'] and p['rating'] < 100)
    
    fields.append({
        "name": "Summary",
        "value": f"**Combos**: {total_combos}\n**Total Liquidity**: £{total_lay_size:.2f}\n**Profitable**: {profitable}",
        "inline": False
    })
    
    embed = {
        "title": match_key,
        "description": f"**{competition}** • {kick_off_time}",
        "fields": fields,
        "color": 3447003,  # Blue
        "footer": {
            "text": "♿ Potter Trick, AGS + O0.5"
        }
    }
    
    payload = {"embeds": [embed]}
    
    try:
        # Try to attach a random GIF if flag is set
        gif_path = get_random_gif() if include_gifs else None
        files = None
        if gif_path and os.path.exists(gif_path):
            try:
                # Open and attach GIF file
                gif_file = open(gif_path, 'rb')
                files = {'file': (os.path.basename(gif_path), gif_file, 'image/gif')}
                # Update embed to reference the attachment
                embed["image"] = {
                    "url": f"attachment://{os.path.basename(gif_path)}"
                }
                response = requests.post(DISCORD_WEBHOOK_URL, data={"payload_json": json.dumps(payload)}, files=files, timeout=10)
                gif_file.close()
            except Exception as e:
                print(f"  ⚠ Could not attach GIF: {e}")
                # Fall back to sending without GIF
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        else:
            # Send without GIF
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        
        print(f"  Response code: {response.status_code}")
        if response.status_code in (200, 204):
            print(f"  ✓ Sent to Discord")
            return True
        else:
            print(f"  ✗ Discord error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Error sending to Discord: {e}")
        return False


def summarize_combos(filepath, send_discord=False, include_gifs=False):
    """Summarize combos file by match and player."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            combo_data = json.load(f)
        
        # Handle multi-event format
        if 'events' in combo_data:
            events = combo_data.get('events', [])
        else:
            # Legacy single-event format
            events = [{
                'combos': combo_data.get('combos', []),
                'metadata': combo_data.get('metadata', {})
            }]
        
        if not events:
            print("No events found in file")
            return
        
        # Group by match
        matches = defaultdict(lambda: defaultdict(list))
        
        for event in events:
            combos = event.get('combos', [])
            metadata = event.get('metadata', {})
            fixture = metadata.get('fixture', {})
            
            match_key = f"{fixture.get('home_team', 'Unknown')} vs {fixture.get('away_team', 'Unknown')}"
            competition = fixture.get('competition', 'Unknown')
            start_date = fixture.get('start_date', 'Unknown')
            
            for combo in combos:
                player_name = combo.get('name', 'Unknown')
                kwiff_odds = combo.get('kwiff_odds', 'N/A')
                lay_odds = combo.get('lay_odds', 'N/A')
                lay_size = combo.get('lay_size', 0)
                
                rating = calculate_rating(kwiff_odds, lay_odds)
                
                matches[match_key]['info'] = {
                    'competition': competition,
                    'start_date': start_date
                }
                
                matches[match_key]['players'].append({
                    'name': player_name,
                    'back_odds': kwiff_odds,
                    'lay_odds': lay_odds,
                    'lay_size': lay_size,
                    'rating': rating
                })
        
        # Print summary
        print("\n" + "="*110)
        print("COMBOS SUMMARY BY MATCH")
        print("="*110 + "\n")
        
        for match_key, match_data in sorted(matches.items()):
            info = match_data['info']
            players = match_data['players']
            
            # Print match header
            print(f"\n{'─'*110}")
            print(f"MATCH: {match_key}")
            print(f"Competition: {info['competition']} | Start: {info['start_date']}")
            print(f"{'─'*110}")
            
            # Print player summary (sorted by rating)
            print(f"\n{'Player':<30} {'Back':<10} {'Lay':<10} {'Liquidity':<15} {'Rating':<10}")
            print(f"{'-'*75}")
            
            for player in sorted(players, key=lambda x: x['rating'] if x['rating'] else 0, reverse=True):
                name = format_player_name(player['name'])[:28]
                back_odds = str(player['back_odds'])
                lay_odds = str(player['lay_odds'])
                lay_size = f"£{player['lay_size']:.2f}"
                rating = f"{player['rating']:.1f}%" if player['rating'] else "N/A"
                
                print(f"{name:<30} {back_odds:<10} {lay_odds:<10} {lay_size:<15} {rating:<10}")
            
            # Print match summary stats
            total_combos = len(players)
            total_lay_size = sum(p['lay_size'] for p in players)
            profitable = sum(1 for p in players if p['rating'] and p['rating'] < 100)
            
            print(f"\n  Total combos: {total_combos}")
            print(f"  Total liquidity: £{total_lay_size:.2f}")
            print(f"  Profitable opportunities (Rating < 100%): {profitable}")
            
            # Send to Discord if flag is set
            if send_discord:
                send_match_to_discord(match_key, match_data, include_gifs=include_gifs)
        
        # Overall summary
        total_matches = len(matches)
        total_combos = sum(len(match_data['players']) for match_data in matches.values())
        total_lay = sum(sum(p['lay_size'] for p in match_data['players']) for match_data in matches.values())
        
        print(f"\n{'='*110}")
        print(f"OVERALL SUMMARY")
        print(f"{'='*110}")
        print(f"Total matches: {total_matches}")
        print(f"Total combos: {total_combos}")
        print(f"Total liquidity: £{total_lay:.2f}")
        print(f"{'='*110}\n")
        
        # Calculate and display biggest movers
        show_biggest_movers(combo_data)
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)


def main():
    global DISCORD_WEBHOOK_URL
    
    parser = argparse.ArgumentParser(description="Summarize combos by match and player")
    parser.add_argument('--file', type=str, 
                        help='Specific combos file to summarize. If not provided, uses combos_{YYYYMMDD}.json')
    parser.add_argument('--discord', action='store_true',
                        help='Send each match summary as a Discord message')
    parser.add_argument('--webhook', type=str, default=DISCORD_WEBHOOK_URL,
                        help='Discord webhook URL')
    parser.add_argument('--include-gifs', action='store_true',
                        help='Include animated GIFs in Discord messages')
    args = parser.parse_args()
    
    # Update webhook URL if provided
    DISCORD_WEBHOOK_URL = args.webhook
    
    # Determine which file to process
    if args.file:
        filepath = args.file
    else:
        # Use today's combos file
        today = datetime.now().strftime("%Y%m%d")
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        filepath = os.path.join(data_dir, f"combos_{today}.json")
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)
    
    print(f"Summarizing: {os.path.basename(filepath)}")
    if args.discord:
        print("Discord mode: ON\n")
    if args.include_gifs:
        print("GIF mode: ON\n")
    
    summarize_combos(filepath, send_discord=args.discord, include_gifs=args.include_gifs)


if __name__ == '__main__':
    main()

