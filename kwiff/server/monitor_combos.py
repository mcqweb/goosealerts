#!/usr/bin/env python3
"""
Monitor the data folder for *_combos.json files and send Discord messages when they arrive or change.
Supports both single-event and multi-event combo file formats.
"""

import json
import os
import sys
import argparse
import time
import hashlib
import requests
import random
import subprocess
from pathlib import Path
from datetime import datetime

# Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1447536804478717984/YPoFdLyu987B4Tp35Toa_WK6mH3bRPDKUTnFrQqcw0DBfT1bjdR5JUu2TakaU_wqyfoH"

# Data folder path
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
STATE_FOLDER = os.path.join(os.path.dirname(__file__), 'state')
os.makedirs(STATE_FOLDER, exist_ok=True)

# Track processed files (hash -> timestamp)
PROCESSED_FILES = {}

# Track sent players to avoid duplicates (player_name -> event_id)
SENT_PLAYERS = {}

# Track last sent GIF to avoid repeats
LAST_GIF_SENT = None

# Track events file hash for auto-mapping
EVENTS_FILE_HASH = None


def get_state_filepath():
    """Get today's state file path."""
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(STATE_FOLDER, f"sent_players_{today}.json")


def check_events_file_updated():
    """Check if events_{date}.json has been updated and run auto_map_events if needed."""
    global EVENTS_FILE_HASH
    
    today = datetime.now().strftime("%Y%m%d")
    events_file = os.path.join(DATA_FOLDER, f"events_{today}.json")
    
    if not os.path.exists(events_file):
        return
    
    try:
        current_hash = get_file_hash(events_file)
        
        if EVENTS_FILE_HASH is None:
            # First check - just store the hash
            EVENTS_FILE_HASH = current_hash
        elif EVENTS_FILE_HASH != current_hash:
            # File has changed - run auto_map_events
            print(f"\n🔄 events_{today}.json was updated - running auto_map_events.py...")
            EVENTS_FILE_HASH = current_hash
            
            try:
                script_path = os.path.join(os.path.dirname(__file__), 'auto_map_events.py')
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"[+] Auto-mapping completed successfully")
                    if result.stdout:
                        for line in result.stdout.split('\n')[-10:]:  # Show last 10 lines
                            if line.strip():
                                print(f"   {line}")
                else:
                    print(f"[!] Auto-mapping encountered an issue")
                    if result.stderr:
                        print(f"   Error: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"[!] Auto-mapping timed out")
            except Exception as e:
                print(f"[!] Failed to run auto-mapping: {e}")
    except Exception as e:
        pass  # Silently fail - don't clutter output


def load_sent_players():
    """Load sent players from today's state file."""
    global SENT_PLAYERS
    filepath = get_state_filepath()
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                SENT_PLAYERS = json.load(f)
                print(f"Loaded {len(SENT_PLAYERS)} sent players from state file")
        except Exception as e:
            print(f"Error loading state file: {e}")
            SENT_PLAYERS = {}
    else:
        SENT_PLAYERS = {}


def save_sent_players():
    """Save sent players to today's state file."""
    filepath = get_state_filepath()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(SENT_PLAYERS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state file: {e}")


def get_file_hash(filepath):
    """Get SHA256 hash of file contents."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_random_gif():
    """Get a random GIF from the gifs folder, avoiding the last one sent."""
    global LAST_GIF_SENT
    gifs_dir = os.path.join(os.path.dirname(__file__), 'gifs')
    if not os.path.exists(gifs_dir):
        return None
    
    gif_files = [f for f in os.listdir(gifs_dir) if f.lower().endswith(('.gif', '.png', '.jpg', '.jpeg'))]
    if not gif_files:
        return None
    
    # Remove last sent GIF from options if there are multiple
    available_gifs = [f for f in gif_files if f != LAST_GIF_SENT] if len(gif_files) > 1 else gif_files
    
    selected_gif = random.choice(available_gifs)
    LAST_GIF_SENT = selected_gif  # Remember what we just selected
    return os.path.join(gifs_dir, selected_gif)


def send_discord_embed(combo, metadata, include_gifs=False):
    """Send a Discord embed with a single combo information."""
    fixture = metadata.get('fixture', {})
    home_team = fixture.get('home_team', 'Unknown')
    away_team = fixture.get('away_team', 'Unknown')
    start_date = fixture.get('start_date', 'Unknown')
    competition = fixture.get('competition', 'Unknown')
    event_id = metadata.get('fixture', {}).get('event_id', 'unknown')
    
    # Extract combo details
    name = combo.get('name', 'Unknown')
    lay_odds = combo.get('lay_odds', 0)
    lay_size = combo.get('lay_size', 0)
    kwiff_odds = combo.get('kwiff_odds', 'N/A')
    best_exchange = combo.get('best_exchange', 'Betfair')
    all_exchanges = combo.get('all_exchanges', '')
    
    # Create unique player key (name + event to track per event)
    player_key = f"{name}_{event_id}"
    
    # Check if we've already sent this player for this event
    if player_key in SENT_PLAYERS:
        print(f"  ⊘ Skipping {name} (already sent)")
        return True  # Don't retry
    
    # Format player name: convert "Surname Firstname" to "Firstname Surname"
    name_parts = name.split()
    if len(name_parts) >= 2:
        # Assume first part is surname, rest is first name
        formatted_name = ' '.join(name_parts[1:]) + ' ' + name_parts[0]
    else:
        formatted_name = name
    
    # Extract kick-off time (HH:MM from ISO format)
    kick_off_time = 'Unknown'
    if start_date and 'T' in start_date:
        try:
            kick_off_time = start_date.split('T')[1][:5]  # Extract HH:MM
        except:
            pass
    
    # Create title with player name and best lay odds
    title = f"{formatted_name} - {kwiff_odds} | Best: {best_exchange} @ {lay_odds}"
    
    # Create description with fixture info
    description = (
        f"**{home_team}** vs **{away_team}**\n"
        f"{competition} • {kick_off_time}"
    )
    
    # Build fields
    fields = []
    
    # Show all exchanges if available
    if all_exchanges:
        fields.append({
            "name": "Lay Prices (All Exchanges)",
            "value": all_exchanges,
            "inline": False
        })
    
    # Show liquidity only if we have Betfair data
    if lay_size and lay_size > 0:
        fields.append({
            "name": "Betfair Liquidity",
            "value": f"£{lay_size:.2f}",
            "inline": False
        })
    
    embed = {
        "title": title,
        "description": description,
        "fields": fields,
        "color": 0x8334f1,  # Purple
        "footer": {
            "text": "♿ Potter Trick, AGS + O0.5"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
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
                print(f"  [!] Could not attach GIF: {e}")
                # Fall back to sending without GIF
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        else:
            # Send without GIF
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code in (200, 204):
            # Mark player as sent
            SENT_PLAYERS[player_key] = datetime.now().isoformat()
            save_sent_players()  # Persist to file
            return True
        else:
            print(f"  ✗ Discord error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error sending Discord message: {e}")
        return False


def process_combos_file(filepath, test_mode=False, include_gifs=False):
    """Process a combos JSON file (supports both single-event and multi-event formats).
    If test_mode=True, sends one test message regardless of filter.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle multi-event format: { "events": [...], "summary": {...} }
        if 'events' in data:
            events = data.get('events', [])
            if not events:
                print(f"  No events found in file")
                return False
            
            total_combos = 0
            total_filtered = 0
            success_count = 0
            
            # Process each event
            for event in events:
                combos = event.get('combos', [])
                metadata = event.get('metadata', {})
                
                if not combos:
                    continue
                
                # Check if event is in the past
                fixture = metadata.get('fixture', {})
                start_date = fixture.get('start_date')
                if start_date:
                    try:
                        from datetime import datetime
                        ko_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        now = datetime.now(ko_time.tzinfo)
                        
                        if ko_time < now:
                            fixture_name = f"{fixture.get('home_team', 'Unknown')} vs {fixture.get('away_team', 'Unknown')}"
                            print(f"  ⊘ Skipping past event: {fixture_name} (started {start_date})")
                            continue
                    except Exception as e:
                        # If we can't parse the date, continue processing to be safe
                        pass
                
                total_combos += len(combos)
                
                # Filter combos: only send alerts where lay_odds <= kwiff_odds (back odds)
                filtered_combos = []
                for combo in combos:
                    lay_odds = combo.get('lay_odds', float('inf'))
                    kwiff_odds = combo.get('kwiff_odds')
                    
                    # Skip if kwiff_odds is not available
                    if kwiff_odds is None:
                        continue
                    
                    # Only include if lay odds <= back odds (profitable opportunity)
                    if lay_odds <= kwiff_odds:
                        filtered_combos.append(combo)
                
                total_filtered += len(filtered_combos)
                
                # In test mode, send first combo even if filtered
                combos_to_send = filtered_combos
                if test_mode and not filtered_combos and combos:
                    combos_to_send = [combos[0]]
                    print(f"  [TEST MODE] Sending first combo regardless of filter")
                
                # Send a separate message for each combo
                for i, combo in enumerate(combos_to_send, 1):
                    if send_discord_embed(combo, metadata, include_gifs=include_gifs):
                        success_count += 1
                    # Small delay between messages to avoid rate limiting
                    if i < len(combos_to_send) or event != events[-1]:
                        time.sleep(0.5)
            
            if total_filtered == 0:
                print(f"  Found {total_combos} combos across {len(events)} events, but none passed filter")
                return False
            
            print(f"  Found {total_combos} combos across {len(events)} events, {total_filtered} passed filter, sending {total_filtered} Discord embeds...")
            print(f"  SUCCESS: Sent {success_count}/{total_filtered} messages successfully")
            return success_count > 0
        
        # Handle legacy single-event format: { "combos": [...], "metadata": {...} }
        else:
            combos = data.get('combos', [])
            metadata = data.get('metadata', {})
            
            if not combos:
                print(f"  No combos found in file")
                return False
            
            # Check if event is in the past
            fixture = metadata.get('fixture', {})
            start_date = fixture.get('start_date')
            if start_date:
                try:
                    from datetime import datetime
                    ko_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    now = datetime.now(ko_time.tzinfo)
                    
                    if ko_time < now:
                        fixture_name = f"{fixture.get('home_team', 'Unknown')} vs {fixture.get('away_team', 'Unknown')}"
                        print(f"  ⊘ Skipping past event: {fixture_name} (started {start_date})")
                        return False
                except Exception as e:
                    # If we can't parse the date, continue processing to be safe
                    pass
            
            # Filter combos: only send alerts where lay_odds <= kwiff_odds (back odds)
            filtered_combos = []
            for combo in combos:
                lay_odds = combo.get('lay_odds', float('inf'))
                kwiff_odds = combo.get('kwiff_odds')
                
                # Skip if kwiff_odds is not available
                if kwiff_odds is None:
                    continue
                
                # Only include if lay odds <= back odds (profitable opportunity)
                if lay_odds <= kwiff_odds:
                    filtered_combos.append(combo)
            
            if not filtered_combos:
                print(f"  Found {len(combos)} combos, but none passed filter (lay_odds <= kwiff_odds)")
                return False
            
            print(f"  Found {len(combos)} combos, {len(filtered_combos)} passed filter, sending {len(filtered_combos)} Discord embeds...")
            
            # Send a separate message for each filtered combo
            success_count = 0
            for i, combo in enumerate(filtered_combos, 1):
                if send_discord_embed(combo, metadata):
                    success_count += 1
                # Small delay between messages to avoid rate limiting
                if i < len(filtered_combos):
                    time.sleep(0.5)
            
            print(f"  SUCCESS: Sent {success_count}/{len(filtered_combos)} messages successfully")
            return success_count > 0
    
    except json.JSONDecodeError as e:
        print(f"  Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  Error processing file: {e}")
        return False


def monitor_folder(watch_path=None, test_mode=False, include_gifs=False):
    """Monitor the data folder for new/changed {eventid}_combos.json files."""
    if watch_path is None:
        watch_path = DATA_FOLDER
    
    print(f"Monitoring folder: {watch_path}")
    print(f"Looking for: combos_*.json files")
    if test_mode:
        print(f"[TEST MODE] Test messages will bypass filter")
        print(f"[TEST MODE] Will process files once and exit")
    else:
        print(f"Checking every 5 seconds...")
        print(f"Press Ctrl+C to stop\n")
    
    test_mode_processed = False
    
    while True:
        try:
            # Check if events file was updated and run auto-mapping if needed
            check_events_file_updated()
            
            # Find all combos_*.json files
            combos_files = sorted(Path(watch_path).glob('combos_*.json'))
            
            if not combos_files:
                if test_mode and not test_mode_processed:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No combos files found in {watch_path}")
                    test_mode_processed = True
            
            for filepath in combos_files:
                filename = filepath.name
                filepath_str = str(filepath)
                
                # Get current file hash
                try:
                    current_hash = get_file_hash(filepath_str)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue
                
                # Check if file is new or changed (force processing in test mode once)
                if test_mode:
                    if not test_mode_processed:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing: {filename}")
                        process_combos_file(filepath_str, test_mode=test_mode, include_gifs=include_gifs)
                        test_mode_processed = True
                        print("\n[TEST MODE] Test complete. Exiting.")
                        return
                else:
                    if filename not in PROCESSED_FILES or PROCESSED_FILES[filename] != current_hash:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing: {filename}")
                        
                        # Process the file
                        if process_combos_file(filepath_str, test_mode=test_mode, include_gifs=include_gifs):
                            PROCESSED_FILES[filename] = current_hash
                        else:
                            # Still track the hash even if processing failed
                            PROCESSED_FILES[filename] = current_hash
            
            # Check every 5 seconds (skip in test mode)
            if not test_mode:
                time.sleep(5)
            else:
                time.sleep(1)  # Brief pause before checking again in test mode
        
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            time.sleep(5)


def main():
    global DISCORD_WEBHOOK_URL
    
    parser = argparse.ArgumentParser(description="Monitor combos files and send Discord embeds")
    parser.add_argument('--file', type=str, 
                        help='Process specific file once (for testing). If not provided, monitors combos_{YYYYMMDD}.json')
    parser.add_argument('--test', action='store_true',
                        help='Send one test message regardless of filter')
    parser.add_argument('--webhook', type=str, default=DISCORD_WEBHOOK_URL,
                        help='Discord webhook URL')
    parser.add_argument('--include-gifs', action='store_true',
                        help='Include animated GIFs in Discord messages')
    args = parser.parse_args()
    
    # Update webhook URL if provided
    DISCORD_WEBHOOK_URL = args.webhook
    
    # Load state from file
    load_sent_players()
    
    # Test mode: process specific file once
    if args.file:
        filepath = args.file
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            sys.exit(1)
        
        filename = os.path.basename(filepath)
        print(f"Processing file: {filename}")
        if args.test:
            print("[TEST MODE] Sending test message...")
        if args.include_gifs:
            print("[GIF MODE] Including animated GIFs\n")
        process_combos_file(filepath, test_mode=args.test, include_gifs=args.include_gifs)
        return
    
    # Continuous monitoring mode (default)
    if args.include_gifs:
        print("[GIF MODE] Including animated GIFs\n")
    monitor_folder(test_mode=args.test, include_gifs=args.include_gifs)


if __name__ == '__main__':
    main()
