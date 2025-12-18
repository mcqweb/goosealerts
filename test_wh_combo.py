"""
Quick test script to fetch a single WH combo for a given event ID.

Usage:
  python test_wh_combo.py OB_EV38028112 [player_name] [template_name]

Examples:
  python test_wh_combo.py OB_EV38028112
  python test_wh_combo.py OB_EV38028112 "Eddie Nketiah"
  python test_wh_combo.py OB_EV38028112 "Eddie Nketiah" "Anytime Goalscorer"

This script will:
1. Load the WH BetBuilderClient
2. Load the specified event
3. Attempt to fetch a combo for the specified player
4. Print the result (odds, availability, errors)
"""
import sys
import traceback
from willhill_betbuilder import BetBuilderClient

EVENT_ID = sys.argv[1] if len(sys.argv) > 1 else "OB_EV38028112"
PLAYER_NAME = sys.argv[2] if len(sys.argv) > 2 else None
TEMPLATE_NAME = sys.argv[3] if len(sys.argv) > 3 else None


def main():
    print(f"Testing WH combo for event: {EVENT_ID}")
    print("-" * 60)
    
    try:
        client = BetBuilderClient()
        print(f"✓ BetBuilderClient initialized")
    except Exception as e:
        print(f"✗ Failed to create BetBuilderClient: {e}")
        traceback.print_exc()
        return
    
    # Load the event
    try:
        print(f"\nLoading event {EVENT_ID}...")
        loaded = client.load_event(EVENT_ID)
        if not loaded:
            print(f"✗ load_event({EVENT_ID}) returned False")
            print("This likely means:")
            print("  - Event ID is invalid")
            print("  - Event is not available for bet builder")
            print("  - Session/cookies expired")
            return
        print(f"✓ Event loaded successfully")
    except Exception as e:
        print(f"✗ load_event raised exception: {e}")
        traceback.print_exc()
        return
    
    # Get eligible players
    players = []
    if not PLAYER_NAME:
        try:
            print(f"\nFetching eligible players for Anytime Goalscorer...")
            players = client.get_eligible_players("Anytime Goalscorer")
            print(f"✓ Found {len(players)} eligible players")
            if players:
                print(f"  Sample players: {players[:5]}")
        except Exception as e:
            print(f"✗ Could not retrieve eligible players: {e}")
            traceback.print_exc()
            players = []
    
    # Get available templates
    try:
        templates = client.get_templates()
        print(f"\n✓ Found {len(templates)} available templates")
        print(f"  Templates: {templates}")
    except Exception as e:
        print(f"✗ Could not retrieve templates: {e}")
        templates = []
    
    # Determine player and template to use
    if PLAYER_NAME:
        test_player = PLAYER_NAME
        print(f"\nUsing specified player: {test_player}")
    elif players:
        test_player = players[0]
        print(f"\nUsing first eligible player: {test_player}")
    else:
        print("\n✗ No player specified and no eligible players found - cannot test combo")
        print("Usage: python test_wh_combo.py OB_EV38028112 \"Player Name\" [\"Template Name\"]")
        return
    
    if TEMPLATE_NAME:
        test_template = TEMPLATE_NAME
        print(f"Using specified template: {test_template}")
    elif templates:
        test_template = templates[0] if templates else "Anytime Goalscorer"
        print(f"Using first template: {test_template}")
    else:
        test_template = "Anytime Goalscorer"
        print(f"Using default template: {test_template}")
    
    print(f"\nAttempting to generate combo for player: {test_player}")
    print(f"Using template: {test_template}")
    
    try:
        # Generate combo using the proper client method
        combos = client.get_player_combinations(
            player_name=test_player,
            template_name=test_template,
            get_price=False  # We'll get price separately to show the flow
        )
        
        if not combos:
            print(f"✗ No valid combos generated for {test_player} with template {test_template}")
            return
        
        print(f"\n✓ Generated {len(combos)} combo(s)")
        combo = combos[0]
        
        # Show combo structure
        print(f"\nCombo structure:")
        print(f"  Success: {combo.get('success')}")
        print(f"  Template: {combo.get('template_name')}")
        print(f"  Selections: {len(combo.get('selections', []))}")
        for i, sel in enumerate(combo.get('selections', [])[:3]):
            print(f"    [{i+1}] {sel.get('outcomeDescription')} - {sel.get('marketDescription')}")
        
        # Now get the price (force fresh fetch, no cache)
        print(f"\nFetching price for combo (bypassing cache)...")
        price_result = client.get_combination_price(combo, use_cache=False)
        
        if price_result:
            print(f"\n✓ Price fetched successfully:")
            odds = price_result.get('odds')
            if odds:
                print(f"  Odds: {odds}")
            else:
                # Try alternate structure
                sel = price_result.get('selection', {})
                price_info = sel.get('price', {})
                decimal = price_info.get('decimal')
                if decimal:
                    print(f"  Decimal Odds: {decimal}")
                else:
                    print(f"  Raw result: {price_result}")
        else:
            print(f"✗ Failed to get price")
            
    except Exception as e:
        print(f"\n✗ Error during combo generation/pricing: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test complete")


if __name__ == '__main__':
    main()
