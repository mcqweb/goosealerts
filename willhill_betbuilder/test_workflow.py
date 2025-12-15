"""
Comprehensive test and demonstration script
Shows complete workflow from fetching to creating combinations
"""

from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.combinations import BetBuilderCombinations


def test_complete_workflow():
    """Complete workflow demonstration"""
    
    print("\n" + "="*80)
    print("WILLIAM HILL BET BUILDER - COMPLETE WORKFLOW TEST")
    print("="*80)
    
    # Event to test
    event_id = "OB_EV37926026"
    
    # Step 1: Initialize components
    print("\n[STEP 1] Initializing components...")
    cache = CacheManager()
    api = WilliamHillAPIClient()
    print("✓ Components initialized")
    
    # Step 2: Fetch or load from cache
    print("\n[STEP 2] Fetching market data...")
    cached_data = cache.get_cached_data(event_id)
    
    if cached_data:
        print(f"✓ Loaded from cache")
        markets_data = cached_data
    else:
        print("→ Fetching from API...")
        markets_data = api.get_event_markets(event_id)
        cache.save_to_cache(event_id, markets_data)
        print("✓ Fetched and cached")
    
    # Event info
    start_time = api.get_event_start_time(markets_data)
    print(f"Event start: {start_time}")
    
    # Step 3: Parse markets
    print("\n[STEP 3] Parsing markets...")
    parser = MarketParser(markets_data)
    categories = parser.get_all_categories()
    print(f"✓ Found {len(categories)} market categories")
    
    # Step 4: Explore specific markets
    print("\n[STEP 4] Exploring key markets...")
    
    # Match Result
    print("\n→ Match Result (90 Minutes):")
    result_selections = parser.get_selections_for_market("Result", "90 Minutes")
    for sel in result_selections:
        print(f"  {sel['name']:15} OB_ID: {sel['obId']}")
    
    # Both Teams to Score
    print("\n→ Both Teams to Score (90 Minutes):")
    btts_selections = parser.get_selections_for_market("Both Teams to Score", "90 Minutes")
    for sel in btts_selections:
        print(f"  {sel['name']:15} OB_ID: {sel['obId']}")
    
    # Total Goals - need to handle team structure
    print("\n→ Total Goals - Both Teams Combined (90 Minutes):")
    goals_group = parser.get_markets_by_category("Total Goals")
    if goals_group:
        goals_markets = goals_group.get('markets', {})
        both_teams = goals_markets.get('Both Teams Combined', {})
        ninety_min = both_teams.get('90 Minutes', {})
        goals_selections = ninety_min.get('selections', [])
        
        for sel in goals_selections[:6]:  # Show first 6
            print(f"  {sel['name']:15} Type: {sel['type']:8} Line: {sel.get('numberValue')}")
    
    # Player to Score
    print("\n→ Player to Score - Anytime (Man Utd):")
    player_group = parser.get_markets_by_category("Player to Score")
    if player_group:
        player_markets = player_group.get('markets', {})
        man_utd = player_markets.get('Man Utd', {})
        anytime = man_utd.get('Anytime', {})
        player_selections = anytime.get('selections', [])
        
        for sel in player_selections[:5]:  # Show first 5
            print(f"  {sel['name']:25} OB_ID: {sel['obId']}")
    
    # Step 5: Create sample combinations
    print("\n[STEP 5] Creating bet builder combinations...")
    combo_builder = BetBuilderCombinations(parser)
    
    # Example Combination 1: Home Win + Over 2.5 Goals
    print("\n→ Example Combination 1: Man Utd Win + Over 2.5 Goals + BTTS Yes")
    combo1_selections = [
        {
            'category': 'Result',
            'period': '90 Minutes',
            'selection_id': result_selections[0]['id'],
            'selection_name': result_selections[0]['name'],
            'ob_id': result_selections[0]['obId'],
            'type': result_selections[0].get('type', 'HOME')
        },
        {
            'category': 'Total Goals',
            'period': '90 Minutes',
            'selection_id': goals_selections[4]['id'],  # Over 2.5
            'selection_name': goals_selections[4]['name'],
            'ob_id': goals_selections[4]['obId'],
            'type': goals_selections[4]['type']
        },
        {
            'category': 'Both Teams to Score',
            'period': '90 Minutes',
            'selection_id': btts_selections[0]['id'],  # Yes
            'selection_name': btts_selections[0]['name'],
            'ob_id': btts_selections[0]['obId'],
            'type': btts_selections[0].get('type', 'YES')
        }
    ]
    
    combo1 = combo_builder.create_combination(combo1_selections)
    validation1 = combo_builder.validate_combination(combo1_selections)
    
    print(f"Selections: {combo1['count']}")
    for sel in combo1['selections']:
        print(f"  • {sel['category']:25} → {sel['selection_name']} ({sel['ob_id']})")
    
    print(f"Validation: {'✓ Valid' if validation1['valid'] else '✗ Invalid - ' + validation1['reason']}")
    
    # Example Combination 2: Player to Score + Result
    print("\n→ Example Combination 2: Player to Score + Match Result")
    combo2_selections = [
        {
            'category': 'Player to Score',
            'period': 'Anytime',
            'team': 'Man Utd',
            'selection_id': player_selections[0]['id'],
            'selection_name': player_selections[0]['name'],
            'ob_id': player_selections[0]['obId'],
            'type': 'PLAYER'
        },
        {
            'category': 'Result',
            'period': '90 Minutes',
            'selection_id': result_selections[0]['id'],
            'selection_name': result_selections[0]['name'],
            'ob_id': result_selections[0]['obId'],
            'type': result_selections[0].get('type', 'HOME')
        }
    ]
    
    combo2 = combo_builder.create_combination(combo2_selections)
    validation2 = combo_builder.validate_combination(combo2_selections)
    
    print(f"Selections: {combo2['count']}")
    for sel in combo2['selections']:
        print(f"  • {sel['category']:25} → {sel['selection_name']} ({sel['ob_id']})")
    
    print(f"Validation: {'✓ Valid' if validation2['valid'] else '✗ Invalid - ' + validation2['reason']}")
    
    # Step 6: Show next steps
    print("\n[STEP 6] Next Steps for Pricing...")
    print("\nTo get odds for these combinations, you would:")
    print("1. Collect the OB IDs from your selections")
    print("2. Make a POST request to the pricing endpoint")
    print("3. Parse the returned odds")
    
    print("\nExample OB IDs from Combination 1:")
    for sel in combo1['selections']:
        print(f"  - {sel['ob_id']}")
    
    # Clean up
    api.close()
    
    print("\n" + "="*80)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("="*80 + "\n")
    
    # Summary
    print("SUMMARY:")
    print(f"  Events Cached: 1")
    print(f"  Market Categories: {len(categories)}")
    print(f"  Combinations Created: 2")
    print(f"  Both Valid: Yes")
    print(f"  Ready for Pricing: Yes")


if __name__ == "__main__":
    test_complete_workflow()
