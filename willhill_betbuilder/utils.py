"""
Utility script for managing cache and exploring events
"""

import argparse
import json
from pathlib import Path
from src.cache_manager import CacheManager
from src.market_parser import MarketParser


def list_cache():
    """List all cached events"""
    cache = CacheManager()
    cache_files = list(cache.cache_dir.glob("*.json"))
    
    if not cache_files:
        print("No cached events found.")
        return
    
    print(f"\nCached Events ({len(cache_files)}):")
    print("=" * 80)
    
    for cache_file in cache_files:
        event_id = cache_file.stem
        info = cache.get_cache_info(event_id)
        
        print(f"\nEvent ID: {event_id}")
        print(f"  File: {cache_file.name}")
        print(f"  Size: {info['size_bytes']:,} bytes")
        print(f"  Created: {info['created'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Modified: {info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")


def view_cache(event_id: str, detail: bool = False):
    """View cached event data"""
    cache = CacheManager()
    data = cache.get_cached_data(event_id)
    
    if not data:
        print(f"No cached data found for event {event_id}")
        return
    
    print(f"\nCached Data for {event_id}:")
    print("=" * 80)
    
    # Basic info
    print(f"Start Time: {data.get('startTime')}")
    print(f"Sport ID: {data.get('sportId')}")
    
    # Market summary
    market_groups = data.get('byoMarketGroups', [])
    print(f"Market Groups: {len(market_groups)}")
    
    if detail:
        parser = MarketParser(data)
        parser.print_category_summary()


def clear_cache_cmd(event_id: str = None):
    """Clear cache"""
    cache = CacheManager()
    
    if event_id:
        cache.clear_cache(event_id)
        print(f"✓ Cleared cache for event {event_id}")
    else:
        response = input("Clear ALL cache files? (yes/no): ")
        if response.lower() == 'yes':
            cache.clear_cache()
            print("✓ Cleared all cache files")
        else:
            print("Cancelled")


def export_markets(event_id: str, output_file: str = None):
    """Export market categories to a file"""
    cache = CacheManager()
    data = cache.get_cached_data(event_id)
    
    if not data:
        print(f"No cached data found for event {event_id}")
        return
    
    parser = MarketParser(data)
    summary = parser.get_category_summary()
    
    if not output_file:
        output_file = f"{event_id}_markets.json"
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Exported {len(summary)} market categories to {output_file}")


def search_markets(event_id: str, search_term: str):
    """Search for markets containing a term"""
    cache = CacheManager()
    data = cache.get_cached_data(event_id)
    
    if not data:
        print(f"No cached data found for event {event_id}")
        return
    
    parser = MarketParser(data)
    summary = parser.get_category_summary()
    
    print(f"\nSearching for '{search_term}' in event {event_id}:")
    print("=" * 80)
    
    found = 0
    for cat in summary:
        category_name = cat['category'].lower()
        if search_term.lower() in category_name:
            found += 1
            print(f"\n{cat['category']}")
            print(f"  Type: {cat['type']}")
            print(f"  Periods: {', '.join(cat['periods'])}")
    
    if found == 0:
        print(f"No markets found matching '{search_term}'")
    else:
        print(f"\n{found} market(s) found")


def main():
    """Main CLI"""
    parser = argparse.ArgumentParser(description='Cache and Event Utilities')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    subparsers.add_parser('list', help='List all cached events')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View cached event')
    view_parser.add_argument('event_id', help='Event ID')
    view_parser.add_argument('--detail', action='store_true', help='Show detailed info')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear cache')
    clear_parser.add_argument('--event-id', help='Specific event ID (or all if omitted)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export markets to JSON')
    export_parser.add_argument('event_id', help='Event ID')
    export_parser.add_argument('--output', help='Output file name')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for markets')
    search_parser.add_argument('event_id', help='Event ID')
    search_parser.add_argument('term', help='Search term')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_cache()
    elif args.command == 'view':
        view_cache(args.event_id, args.detail)
    elif args.command == 'clear':
        clear_cache_cmd(args.event_id)
    elif args.command == 'export':
        export_markets(args.event_id, args.output)
    elif args.command == 'search':
        search_markets(args.event_id, args.term)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
