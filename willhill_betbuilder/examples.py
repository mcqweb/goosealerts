"""
Example script showing how to use the bet builder components
"""

from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.combinations import BetBuilderCombinations


def example_basic_usage():
    """Example 1: Basic usage - fetch and cache markets"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Market Fetching")
    print("="*80)
    
    event_id = "OB_EV37926026"
    
    # Initialize components
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    # Fetch markets (uses cache if available)
    cached = cache.get_cached_data(event_id)
    if cached:
        print(f"✓ Using cached data for {event_id}")
        markets = cached
    else:
        print(f"→ Fetching markets for {event_id}...")
        markets = api.get_event_markets(event_id)
        cache.save_to_cache(event_id, markets)
        print("✓ Saved to cache")
    
    # Get event info
    start_time = api.get_event_start_time(markets)
    print(f"Event starts: {start_time}")
    
    api.close()


def example_explore_categories():
    """Example 2: Explore available market categories"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Exploring Market Categories")
    print("="*80)
    
    event_id = "OB_EV37926026"
    cache = CacheManager()
    
    # Get cached data
    markets = cache.get_cached_data(event_id)
    if not markets:
        print("Please run example 1 first to cache data")
        return
    
    # Parse markets
    parser = MarketParser(markets)
    
    # Get all categories
    categories = parser.get_all_categories()
    print(f"\nFound {len(categories)} market categories")
    print("\nFirst 10 categories:")
    for cat in categories[:10]:
        print(f"  - {cat}")


def example_specific_market():
    """Example 3: Get selections from a specific market"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Specific Market Selections")
    print("="*80)
    
    event_id = "OB_EV37926026"
    cache = CacheManager()
    markets = cache.get_cached_data(event_id)
    
    if not markets:
        print("Please run example 1 first to cache data")
        return
    
    parser = MarketParser(markets)
    
    # Get Match Result selections
    print("\nMatch Result (90 Minutes):")
    selections = parser.get_selections_for_market("Result", "90 Minutes")
    for sel in selections:
        print(f"  {sel.get('name'):20} - ID: {sel.get('obId')}")
    
    # Get Total Goals selections
    print("\nTotal Goals - Both Teams (90 Minutes):")
    market_group = parser.get_markets_by_category("Total Goals")
    if market_group:
        markets_dict = market_group.get('markets', {})
        both_teams = markets_dict.get('Both Teams Combined', {})
        ninety_mins = both_teams.get('90 Minutes', {})
        selections = ninety_mins.get('selections', [])
        
        for sel in selections[:10]:  # Show first 10
            name = sel.get('name')
            sel_type = sel.get('type')
            number = sel.get('numberValue')
            print(f"  {name:20} - {sel_type:10} - Line: {number}")


def example_player_markets():
    """Example 4: Player-specific markets"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Player Markets")
    print("="*80)
    
    event_id = "OB_EV37926026"
    cache = CacheManager()
    markets = cache.get_cached_data(event_id)
    
    if not markets:
        print("Please run example 1 first to cache data")
        return
    
    parser = MarketParser(markets)
    
    # Get Player to Score - Anytime
    print("\nPlayer to Score - Anytime (Man Utd):")
    market_group = parser.get_markets_by_category("Player to Score")
    if market_group:
        markets_dict = market_group.get('markets', {})
        man_utd = markets_dict.get('Man Utd', {})
        anytime = man_utd.get('Anytime', {})
        selections = anytime.get('selections', [])
        
        for sel in selections[:10]:  # Show first 10 players
            name = sel.get('name')
            ob_id = sel.get('obId')
            print(f"  {name:25} - {ob_id}")


def example_combination_suggestions():
    """Example 5: Generate bet builder suggestions"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Bet Builder Combinations")
    print("="*80)
    
    event_id = "OB_EV37926026"
    cache = CacheManager()
    markets = cache.get_cached_data(event_id)
    
    if not markets:
        print("Please run example 1 first to cache data")
        return
    
    parser = MarketParser(markets)
    combo_builder = BetBuilderCombinations(parser)
    
    # Show popular combinations
    popular = combo_builder.get_popular_combinations()
    print("\nPopular Bet Builder Templates:")
    for combo in popular:
        print(f"\n{combo['name']}")
        print(f"  Categories: {', '.join(combo['categories'])}")
        print(f"  Description: {combo['description']}")
    
    # Example: Create a custom combination
    print("\n" + "-"*80)
    print("Custom Combination Example:")
    
    # This shows the structure - in practice you'd select actual selections
    custom_selections = [
        {
            'category': 'Result',
            'period': '90 Minutes',
            'selection_id': 'example-id-1',
            'selection_name': 'Man Utd Win',
            'ob_id': 'OB_EXAMPLE1',
            'type': 'HOME'
        },
        {
            'category': 'Total Goals',
            'period': '90 Minutes',
            'selection_id': 'example-id-2',
            'selection_name': 'Over 2.5',
            'ob_id': 'OB_EXAMPLE2',
            'type': 'OVER'
        },
        {
            'category': 'Both Teams to Score',
            'period': '90 Minutes',
            'selection_id': 'example-id-3',
            'selection_name': 'Yes',
            'ob_id': 'OB_EXAMPLE3',
            'type': 'YES'
        }
    ]
    
    combination = combo_builder.create_combination(custom_selections)
    print(f"\nCombination with {combination['count']} selections:")
    for sel in combination['selections']:
        print(f"  - {sel['category']}: {sel['selection_name']}")
    
    # Validate the combination
    validation = combo_builder.validate_combination(custom_selections)
    print(f"\nValidation: {'✓ Valid' if validation['valid'] else '✗ Invalid'}")
    if not validation['valid']:
        print(f"Reason: {validation['reason']}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("WILLIAM HILL BET BUILDER - EXAMPLES")
    print("="*80)
    
    # Run examples
    example_basic_usage()
    example_explore_categories()
    example_specific_market()
    example_player_markets()
    example_combination_suggestions()
    
    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
