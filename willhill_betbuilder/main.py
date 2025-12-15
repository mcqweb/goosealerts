"""
Main entry point for William Hill Bet Builder
"""

import argparse
from datetime import datetime
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.combinations import BetBuilderCombinations


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='William Hill Bet Builder Tool')
    parser.add_argument('event_id', help='Event ID (e.g., OB_EV37926026)')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='Force refresh cache even if valid')
    parser.add_argument('--list-categories', action='store_true',
                       help='List all available market categories')
    parser.add_argument('--categories', nargs='+',
                       help='Specific categories to analyze')
    
    args = parser.parse_args()
    
    # Initialize components
    cache_manager = CacheManager()
    api_client = WilliamHillAPIClient()
    
    print(f"\nFetching markets for event: {args.event_id}")
    print("=" * 80)
    
    # Check cache first
    markets_data = None
    event_start_time = None
    
    if not args.force_refresh:
        cached_data = cache_manager.get_cached_data(args.event_id)
        if cached_data:
            event_start_time = api_client.get_event_start_time(cached_data)
            if cache_manager.is_cache_valid(args.event_id, event_start_time):
                print("✓ Using cached data")
                markets_data = cached_data
            else:
                print("✗ Cache expired (event has started)")
    
    # Fetch from API if needed
    if markets_data is None:
        print("→ Fetching from API...")
        try:
            markets_data = api_client.get_event_markets(args.event_id)
            event_start_time = api_client.get_event_start_time(markets_data)
            
            # Save to cache
            if cache_manager.save_to_cache(args.event_id, markets_data):
                print("✓ Saved to cache")
            
            # Display event info
            if event_start_time:
                print(f"Event starts: {event_start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return
    
    # Parse markets
    market_parser = MarketParser(markets_data)
    
    if args.list_categories:
        market_parser.print_category_summary()
    
    # Show combination suggestions
    print("\n" + "=" * 80)
    print("Popular Bet Builder Combinations:")
    print("=" * 80)
    
    combo_builder = BetBuilderCombinations(market_parser)
    popular = combo_builder.get_popular_combinations()
    
    for combo in popular:
        print(f"\n{combo['name']}")
        print(f"  Categories: {', '.join(combo['categories'])}")
        print(f"  {combo['description']}")
    
    # Display specific categories if requested
    if args.categories:
        print("\n" + "=" * 80)
        print("Selected Market Details:")
        print("=" * 80)
        
        for category in args.categories:
            print(f"\n{category}:")
            selections = market_parser.get_selections_for_market(category)
            if selections:
                for sel in selections[:10]:  # Show first 10
                    name = sel.get('name', 'N/A')
                    ob_id = sel.get('obId', 'N/A')
                    print(f"  - {name} ({ob_id})")
                if len(selections) > 10:
                    print(f"  ... and {len(selections) - 10} more")
            else:
                print("  No selections found")
    
    api_client.close()
    print("\n" + "=" * 80)
    print("Done!")


if __name__ == "__main__":
    main()
