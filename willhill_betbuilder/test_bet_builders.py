#!/usr/bin/env python3
"""
Test Bet Builder Combinations
Demonstrates the 4 bet builder templates with sample players
"""

from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.bet_builder_templates import BetBuilderTemplates, PlayerMarketChecker
from src.bet_builder_generator import BetBuilderGenerator


def main():
    # Event ID
    event_id = "OB_EV37926026"
    
    print("=" * 70)
    print("WILLIAM HILL BET BUILDER COMBINATIONS TEST")
    print("=" * 70)
    print(f"\nEvent ID: {event_id}")
    print("Testing 4 Bet Builder Templates\n")
    
    # Load market data
    print("Loading market data...")
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    markets = cache.get_cached_data(event_id)
    if not markets:
        print(f"Fetching from API...")
        markets = api.get_event_markets(event_id)
        if markets:
            cache.save_to_cache(event_id, markets)
    
    if not markets:
        print("❌ Failed to load market data")
        return
    
    print("✓ Market data loaded\n")
    
    # Initialize parser and generator
    parser = MarketParser(markets)
    generator = BetBuilderGenerator(parser)
    checker = PlayerMarketChecker(parser)
    
    # Show templates
    print("\n" + "=" * 70)
    print("AVAILABLE TEMPLATES")
    print("=" * 70)
    print(BetBuilderTemplates.format_template_info())
    
    # Test players - one from each team
    test_players = [
        {"name": "Joshua Zirkzee", "team": "Man Utd"},
        {"name": "Antoine Semenyo", "team": "Bournemouth"}
    ]
    
    print("\n" + "=" * 70)
    print("GENERATING COMBINATIONS FOR SAMPLE PLAYERS")
    print("=" * 70)
    
    for player_info in test_players:
        player_name = player_info["name"]
        team = player_info["team"]
        
        print(f"\n\nPlayer: {player_name} ({team})")
        print("-" * 70)
        
        # Generate all combinations for this player
        combos = generator.generate_all_combos_for_player(player_name, team)
        
        print(f"Generated {len(combos)} combinations:\n")
        
        for combo in combos:
            print(generator.format_combo_output(combo))
    
    # Show statistics
    print("\n" + "=" * 70)
    print("OVERALL STATISTICS")
    print("=" * 70)
    
    stats = generator.get_summary_stats()
    
    print(f"\nTotal Combinations Available: {stats['total_combinations']}")
    print(f"\nBy Template:")
    for template, count in stats['by_template'].items():
        print(f"  • {template}: {count}")
    
    print(f"\nBy Team:")
    for team, count in stats['by_team'].items():
        print(f"  • {team}: {count}")
    
    # Show eligible player counts
    print("\n" + "=" * 70)
    print("ELIGIBLE PLAYERS BY TEMPLATE")
    print("=" * 70)
    
    for template_name in BetBuilderTemplates.get_all_template_names():
        print(f"\n{template_name}:")
        
        # Get teams
        teams = []
        for group in parser.data.get("byoMarketGroups", []):
            if group.get("category") == "PLAYER_TO_SCORE":
                teams = group.get("teams", [])
                break
        
        total = 0
        for team in teams:
            eligible = checker.get_eligible_players_for_template(team, template_name)
            count = len(eligible)
            total += count
            print(f"  {team}: {count} players")
        
        print(f"  Total: {total} players")
    
    print("\n" + "=" * 70)
    print("✓ TEST COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Use the OB IDs to call the pricing API")
    print("2. Compare back vs lay odds")
    print("3. Identify value opportunities")
    print("\nGenerate all combinations with:")
    print(f"  python generate_combos.py {event_id} --all --output combos.json")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
