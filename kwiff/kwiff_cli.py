#!/usr/bin/env python3
"""
Kwiff CLI Tool - Fetch live sports events and betting data

Usage:
    python kwiff_cli.py fetch-events --sport football --country GB
    python kwiff_cli.py fetch-events --sport football --output custom_events.json
    python kwiff_cli.py fetch-events (uses defaults: football, GB)
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path
from kwiff_client import KwiffClient


def main():
    parser = argparse.ArgumentParser(
        description="Kwiff WebSocket Client - Fetch Live Sports Events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch football events for GB (default)
  python kwiff_cli.py fetch-events
  
  # Fetch football events for Ireland
  python kwiff_cli.py fetch-events --country IE
  
  # Save to custom file
  python kwiff_cli.py fetch-events --output my_events.json
  
  # Get help
  python kwiff_cli.py fetch-events --help
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # fetch-events command
    fetch_parser = subparsers.add_parser(
        "fetch-events",
        help="Fetch live sports events"
    )
    
    fetch_parser.add_argument(
        "--sport",
        type=str,
        choices=["football", "basketball", "tennis", "horse-racing"],
        default="football",
        help="Sport type (default: football)"
    )
    
    fetch_parser.add_argument(
        "--country",
        type=str,
        default="GB",
        help="Country code (default: GB)"
    )
    
    fetch_parser.add_argument(
        "--output",
        type=str,
        default="football_events.json",
        help="Output file (default: football_events.json)"
    )
    
    fetch_parser.add_argument(
        "--show-preview",
        action="store_true",
        help="Show event preview after fetching"
    )
    
    args = parser.parse_args()
    
    if args.command == "fetch-events":
        return asyncio.run(fetch_events(args))
    elif args.command is None:
        parser.print_help()
        return 0
    else:
        print(f"Unknown command: {args.command}")
        return 1


async def fetch_events(args) -> int:
    """Fetch events from Kwiff."""
    
    # Map sport names to IDs
    sport_ids = {
        "football": 11,
        "basketball": 36,
        "tennis": 25,
        "horse-racing": 39,
    }
    
    sport_id = sport_ids.get(args.sport, 11)
    
    print(f"[*] Kwiff Event Fetcher")
    print(f"[*] Sport: {args.sport} (ID: {sport_id})")
    print(f"[*] Country: {args.country}")
    print(f"[*] Output: {args.output}\n")
    
    try:
        async with KwiffClient() as client:
            print(f"[+] Connected to Kwiff\n")
            print(f"[*] Fetching {args.sport} events for {args.country}...\n")
            
            # Get events
            payload = {
                "listId": "default",
                "sportId": sport_id,
                "country": args.country
            }
            
            events = await client.get_football_events(country=args.country)
            
            if not events:
                print(f"[!] No events received")
                return 1
            
            # Save to file
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(events, f, indent=2)
            
            print(f"[+] Saved to {output_path}\n")
            
            # Show preview
            if "data" in events and "events" in events["data"]:
                event_list = events["data"]["events"]
                print(f"[*] Found {len(event_list)} events\n")
                
                if args.show_preview:
                    for i, event in enumerate(event_list[:5]):
                        print(f"  {i+1}. {event.get('competition', {}).get('name')} - ", end="")
                        
                        home = event.get('homeTeam', {}).get('name', 'N/A')
                        away = event.get('awayTeam', {}).get('name', 'N/A')
                        print(f"{home} vs {away}")
                        
                        start_date = event.get('startDate', 'N/A')
                        print(f"     Start: {start_date}\n")
                
                print(f"[+] Success! Fetched {len(event_list)} {args.sport} events")
                return 0
            else:
                print(f"[!] Unexpected response format")
                return 1
                
    except KeyboardInterrupt:
        print(f"\n[!] Interrupted by user")
        return 130
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
