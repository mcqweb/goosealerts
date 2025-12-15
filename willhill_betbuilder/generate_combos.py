#!/usr/bin/env python3
"""
Generate Bet Builder Combinations CLI
Main interface for generating the 4 standard bet builder combinations
"""

import argparse
import json
from pathlib import Path
from config import Config
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.bet_builder_templates import BetBuilderTemplates, PlayerMarketChecker
from src.bet_builder_generator import BetBuilderGenerator


def list_templates():
    """List all available bet builder templates"""
    print(BetBuilderTemplates.format_template_info())


def list_eligible_players(event_id: str, template: str = None):
    """List all eligible players for templates"""
    # Get market data
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    markets = cache.get_cached_data(event_id)
    if not markets:
        print(f"Fetching markets for event {event_id}...")
        markets = api.get_event_markets(event_id)
        if markets:
            cache.save_to_cache(event_id, markets)
    
    if not markets:
        print(f"❌ Could not load market data for event {event_id}")
        return
    
    # Parse markets
    parser = MarketParser(markets)
    checker = PlayerMarketChecker(parser)
    
    # Get eligible players
    if template:
        # Single template
        if template not in BetBuilderTemplates.get_all_template_names():
            print(f"❌ Unknown template: {template}")
            print(f"Available templates: {', '.join(BetBuilderTemplates.get_all_template_names())}")
            return
        
        print(f"\n{'=' * 70}")
        print(f"Eligible Players for: {template}")
        print(f"{'=' * 70}\n")
        
        # Get teams
        teams = []
        for group in parser.data.get("byoMarketGroups", []):
            if group.get("category") == "PLAYER_TO_SCORE":
                teams = group.get("teams", [])
                break
        
        total_players = 0
        for team in teams:
            eligible = checker.get_eligible_players_for_template(team, template)
            if eligible:
                print(f"\n{team}:")
                print("-" * 40)
                for player in eligible:
                    print(f"  ✓ {player['name']}")
                    total_players += 1
        
        print(f"\nTotal Eligible Players: {total_players}")
    
    else:
        # All templates
        eligible_all = checker.get_all_eligible_players()
        
        for template_name, teams_data in eligible_all.items():
            print(f"\n{'=' * 70}")
            print(f"{template_name}")
            print(f"{'=' * 70}")
            
            total = 0
            for team, players in teams_data.items():
                print(f"\n{team}: ({len(players)} players)")
                for player in players:
                    print(f"  ✓ {player['name']}")
                    total += len(players)
            
            print(f"\nTotal: {total} eligible players")


def generate_player_combos(event_id: str, player_name: str, team: str, template: str = None, get_price: bool = False, session_cookie: str = None):
    """Generate combinations for a specific player"""
    # Get market data
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    markets = cache.get_cached_data(event_id)
    if not markets:
        print(f"Fetching markets for event {event_id}...")
        markets = api.get_event_markets(event_id)
        if markets:
            cache.save_to_cache(event_id, markets)
    
    if not markets:
        print(f"❌ Could not load market data for event {event_id}")
        return
    
    # Parse and generate
    parser = MarketParser(markets)
    generator = BetBuilderGenerator(parser)
    
    if template:
        # Single template
        combo = generator.generate_combo_for_player(player_name, team, template)
        
        # Get price if requested
        price_data = None
        if get_price and combo.get("success"):
            print("Fetching odds from William Hill API...")
            cookie = session_cookie or "YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5"
            price_data = generator.get_combo_price(combo, cookie)
            if not price_data:
                print("❌ Failed to fetch pricing data\n")
        
        print(generator.format_combo_output(combo, include_payload=True, price_data=price_data))
        
        # Display detailed pricing if available
        if price_data and price_data.get("status") == "ok":
            print("\n" + "=" * 70)
            print("DETAILED PRICING DATA")
            print("=" * 70)
            print(json.dumps(price_data, indent=2))
    else:
        # All templates
        combos = generator.generate_all_combos_for_player(player_name, team)
        
        if not combos:
            print(f"❌ No valid combinations found for {player_name} ({team})")
            return
        
        print(f"\nGenerated {len(combos)} combinations for {player_name} ({team}):\n")
        for combo in combos:
            # Get price if requested
            price_data = None
            if get_price and combo.get("success"):
                cookie = session_cookie or "YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5"
                price_data = generator.get_combo_price(combo, cookie)
            
            print(generator.format_combo_output(combo, include_payload=True, price_data=price_data))


def generate_all_combos(event_id: str, output_file: str = None):
    """Generate all combinations for all eligible players"""
    # Get market data
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    markets = cache.get_cached_data(event_id)
    if not markets:
        print(f"Fetching markets for event {event_id}...")
        markets = api.get_event_markets(event_id)
        if markets:
            cache.save_to_cache(event_id, markets)
    
    if not markets:
        print(f"❌ Could not load market data for event {event_id}")
        return
    
    # Parse and generate
    parser = MarketParser(markets)
    generator = BetBuilderGenerator(parser)
    
    print(f"Generating all combinations for event {event_id}...\n")
    
    all_combos = generator.generate_all_combos_for_event()
    stats = generator.get_summary_stats()
    
    # Display summary
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total Combinations: {stats['total_combinations']}")
    print(f"\nBy Template:")
    for template, count in stats['by_template'].items():
        print(f"  • {template}: {count}")
    print(f"\nBy Team:")
    for team, count in stats['by_team'].items():
        print(f"  • {team}: {count}")
    print(f"{'=' * 70}\n")
    
    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(all_combos, f, indent=2)
        print(f"✓ Saved all combinations to {output_file}")
    
    # Display first few combinations as examples
    print("\nSample Combinations:\n")
    sample_count = 0
    for template_name, combos in all_combos.items():
        if sample_count >= 3:
            break
        for combo in combos[:1]:  # Show 1 per template
            print(generator.format_combo_output(combo))
            sample_count += 1


def show_stats(event_id: str):
    """Show statistics about available combinations"""
    # Get market data
    cache = CacheManager()
    api = WilliamHillAPIClient()
    
    markets = cache.get_cached_data(event_id)
    if not markets:
        print(f"Fetching markets for event {event_id}...")
        markets = api.get_event_markets(event_id)
        if markets:
            cache.save_to_cache(event_id, markets)
    
    if not markets:
        print(f"❌ Could not load market data for event {event_id}")
        return
    
    parser = MarketParser(markets)
    generator = BetBuilderGenerator(parser)
    stats = generator.get_summary_stats()
    
    print(f"\n{'=' * 70}")
    print(f"BET BUILDER STATISTICS - Event {event_id}")
    print(f"{'=' * 70}")
    print(f"\nTotal Available Combinations: {stats['total_combinations']}")
    
    print(f"\nBreakdown by Template:")
    print("-" * 40)
    for template, count in sorted(stats['by_template'].items(), key=lambda x: -x[1]):
        print(f"  {template:<30} {count:>3} combos")
    
    print(f"\nBreakdown by Team:")
    print("-" * 40)
    for team, count in sorted(stats['by_team'].items(), key=lambda x: -x[1]):
        print(f"  {team:<30} {count:>3} combos")
    
    print(f"\n{'=' * 70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate William Hill Bet Builder Combinations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load configuration file
  python generate_combos.py --config config.json
  
  # List all templates
  python generate_combos.py --list-templates
  
  # Show statistics
  python generate_combos.py OB_EV37926026 --stats
  
  # List eligible players for all templates
  python generate_combos.py OB_EV37926026 --list-players
  
  # List eligible players for specific template
  python generate_combos.py OB_EV37926026 --list-players --template "Anytime Goalscorer"
  
  # Generate combos for specific player
  python generate_combos.py OB_EV37926026 --player "Bryan Mbeumo" --team "Man Utd"
  
  # Generate specific template for player
  python generate_combos.py OB_EV37926026 --player "Joshua Zirkzee" --team "Man Utd" --template "First Goalscorer"
  
  # Get live pricing for a combination
  python generate_combos.py OB_EV37926026 --player "Joshua Zirkzee" --team "Man Utd" --template "Anytime Goalscorer" --get-price
  
  # Use with proxy
  python generate_combos.py OB_EV37926026 --player "Joshua Zirkzee" --team "Man Utd" --http-proxy "http://localhost:8080" --get-price
  
  # Generate ALL combinations and save to file
  python generate_combos.py OB_EV37926026 --all --output combos.json
        """
    )
    
    parser.add_argument('event_id', nargs='?', help='Event ID (e.g., OB_EV37926026)')
    parser.add_argument('--config', help='Load configuration from JSON file')
    parser.add_argument('--list-templates', action='store_true', help='List all available templates')
    parser.add_argument('--list-players', action='store_true', help='List eligible players')
    parser.add_argument('--stats', action='store_true', help='Show combination statistics')
    parser.add_argument('--player', help='Player name')
    parser.add_argument('--team', help='Team name (e.g., "Man Utd", "Bournemouth")')
    parser.add_argument('--template', help='Specific template name')
    parser.add_argument('--all', action='store_true', help='Generate all combinations for all players')
    parser.add_argument('--output', help='Output file for JSON results')
    parser.add_argument('--get-price', action='store_true', help='Fetch live odds from William Hill API')
    parser.add_argument('--session', help='SESSION cookie value for API authentication')
    parser.add_argument('--http-proxy', help='HTTP proxy URL (e.g., "http://localhost:8080")')
    parser.add_argument('--https-proxy', help='HTTPS proxy URL (e.g., "https://localhost:8080")')
    parser.add_argument('--nord-user', help='NordVPN username/email')
    parser.add_argument('--nord-pwd', help='NordVPN password')
    parser.add_argument('--nord-location', help='NordVPN server location (e.g., us5678)')
    
    args = parser.parse_args()
    
    # Load config file if provided
    if args.config:
        try:
            Config.load_from_file(args.config)
            print(f"✓ Loaded configuration from {args.config}\n")
        except Exception as e:
            print(f"❌ Error loading config file: {e}\n")
            return
    
    # Override config with command-line arguments
    if args.session:
        Config.set_session_cookie(args.session)
    if args.http_proxy or args.https_proxy:
        Config.set_proxy(args.http_proxy, args.https_proxy)
    if args.nord_user:
        Config.NORD_USER = args.nord_user
    if args.nord_pwd:
        Config.NORD_PWD = args.nord_pwd
    if args.nord_location:
        Config.NORD_LOCATION = args.nord_location
    
    # List templates (no event ID needed)
    if args.list_templates:
        list_templates()
        return
    
    # All other commands need event ID
    if not args.event_id:
        parser.print_help()
        return
    
    # Show stats
    if args.stats:
        show_stats(args.event_id)
        return
    
    # List eligible players
    if args.list_players:
        list_eligible_players(args.event_id, args.template)
        return
    
    # Generate for specific player
    if args.player:
        if not args.team:
            print("❌ Error: --team is required when specifying --player")
            return
        generate_player_combos(args.event_id, args.player, args.team, args.template, args.get_price, args.session)
        return
    
    # Generate all combinations
    if args.all:
        generate_all_combos(args.event_id, args.output)
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
