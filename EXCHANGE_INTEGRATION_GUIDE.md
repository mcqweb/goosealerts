# Exchange Integration Guide
## Adding Smarkets & Matchbook lay odds alongside Betfair

This guide explains how to integrate additional exchange odds (Smarkets, Matchbook) from OddsMatcha API into a Betfair-based betting project.

---

## Overview

**What this does:**
- Fetches lay odds from Smarkets and Matchbook via OddsMatcha API
- Combines them with Betfair lay odds
- Uses the best (lowest) lay price across all exchanges
- Displays all exchange prices in alerts/messages
- Handles players that exist on exchanges but not Betfair

**Benefits:**
- Better lay prices (lower = better for laying)
- More player coverage (some players only on certain exchanges)
- Liquidity information (Betfair shows size, exchanges don't)

---

## Prerequisites

1. **OddsMatcha API Key**: Get from https://oddsmatcha.com
2. **Environment Variable**: Add to `.env`:
   ```
   ODDSMATCHA_API_KEY=your_api_key_here
   ```

---

## Implementation Steps

### Step 1: Add OddsMatcha Fetch Function

Add this function to fetch exchange odds for a match:

```python
def fetch_exchange_odds(oddsmatcha_match_id):
    """
    Fetch Smarkets and Matchbook lay odds from OddsMatcha API.
    
    Args:
        oddsmatcha_match_id: OddsMatcha match ID (different from Betfair ID)
    
    Returns:
        Dict structure:
        {
            'First Goalscorer': {
                'Player Name': [
                    {'site_name': 'Smarkets', 'lay_odds': 5.5},
                    {'site_name': 'Matchbook', 'lay_odds': 5.6}
                ]
            },
            'Anytime Goalscorer': {
                'Player Name': [...]
            }
        }
    """
    import os
    import requests
    import time
    
    ODDSMATCHA_API_KEY = os.getenv("ODDSMATCHA_API_KEY")
    if not ODDSMATCHA_API_KEY:
        return {}
    
    try:
        url = f"https://api.oddsmatcha.com/api/soccer/{oddsmatcha_match_id}/markets"
        headers = {"x-api-key": ODDSMATCHA_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Only keep fresh odds (< 5 minutes old)
        FRESHNESS_THRESHOLD = 300  # 5 minutes in seconds
        current_time = time.time()
        
        result = {}
        
        for market in data:
            market_name = market.get('name', '')
            
            # Map OddsMatcha market names to your format
            if 'First Goalscorer' in market_name or 'First Goal Scorer' in market_name:
                market_key = 'First Goalscorer'
            elif 'Anytime Goalscorer' in market_name or 'Anytime Goal Scorer' in market_name:
                market_key = 'Anytime Goalscorer'
            else:
                continue
            
            if market_key not in result:
                result[market_key] = {}
            
            runners = market.get('runners', [])
            for runner in runners:
                player_name = runner.get('name', '')
                if not player_name:
                    continue
                
                if player_name not in result[market_key]:
                    result[market_key][player_name] = []
                
                # Process each site's odds
                for site_name, site_data in runner.items():
                    if site_name in ['name', 'id']:
                        continue
                    
                    if not isinstance(site_data, dict):
                        continue
                    
                    # Only include Smarkets and Matchbook
                    if site_name.lower() not in ['smarkets', 'matchbook']:
                        continue
                    
                    lay_price = site_data.get('lay_price')
                    last_updated = site_data.get('last_updated', 0)
                    
                    # Check freshness
                    if lay_price and (current_time - last_updated) <= FRESHNESS_THRESHOLD:
                        # Capitalize site name for display
                        display_name = site_name.capitalize()
                        
                        result[market_key][player_name].append({
                            'site_name': display_name,
                            'lay_odds': float(lay_price)
                        })
        
        return result
        
    except Exception as e:
        print(f"Error fetching exchange odds for match {oddsmatcha_match_id}: {e}")
        return {}
```

---

### Step 2: Add Combine Function

Add this function to merge Betfair and exchange odds:

```python
def combine_betfair_and_exchange_odds(betfair_odds, exchange_odds, market_type):
    """
    Combine Betfair and exchange odds for a market.
    
    Args:
        betfair_odds: List of dicts with 'outcome', 'odds', 'size' from Betfair
        exchange_odds: Dict from fetch_exchange_odds() with player names as keys
        market_type: 'Anytime Goalscorer' or 'First Goalscorer'
    
    Returns:
        List of combined odds entries:
        [
            {
                'player_name': 'Player Name',
                'site': 'Betfair',
                'lay_odds': 5.0,
                'lay_size': 100.0,
                'has_size': True
            },
            {
                'player_name': 'Player Name',
                'site': 'Smarkets',
                'lay_odds': 4.8,
                'lay_size': None,
                'has_size': False
            }
        ]
    """
    combined = []
    
    # Add Betfair odds (with liquidity info)
    for odd in betfair_odds:
        combined.append({
            'player_name': odd.get('outcome', ''),
            'site': 'Betfair',
            'lay_odds': float(odd.get('odds', 0)),
            'lay_size': float(odd.get('size', 0)),
            'has_size': True
        })
    
    # Add exchange odds (no liquidity info)
    exchange_market = exchange_odds.get(market_type, {})
    for player_name, site_odds_list in exchange_market.items():
        for site_odd in site_odds_list:
            combined.append({
                'player_name': player_name,
                'site': site_odd['site_name'],
                'lay_odds': site_odd['lay_odds'],
                'lay_size': None,
                'has_size': False
            })
    
    return combined
```

---

### Step 3: Update Match Processing Loop

In your main Betfair processing loop, integrate the exchange odds:

```python
# Inside your match loop, after getting Betfair match ID:
betfair_match_id = "1.234567890"  # Your Betfair market ID

# Get OddsMatcha match ID (if you have mappings)
oddsmatcha_match_id = mappings.get('oddsmatcha')

# Fetch exchange odds once per match
exchange_odds = {}
if oddsmatcha_match_id:
    exchange_odds = fetch_exchange_odds(oddsmatcha_match_id)
    if exchange_odds:
        total_players = sum(len(players) for players in exchange_odds.values())
        print(f"[EXCHANGE] Fetched odds for {total_players} players from Smarkets/Matchbook")

# Process each market (FGS, AGS)
for market_type in ['First Goalscorer', 'Anytime Goalscorer']:
    # Get Betfair odds for this market
    betfair_odds = get_betfair_odds_for_market(...)  # Your existing function
    
    # Combine with exchange odds
    all_odds = combine_betfair_and_exchange_odds(betfair_odds, exchange_odds, market_type)
    
    # Group by player name
    player_odds_map = {}
    for odd_entry in all_odds:
        pname = odd_entry['player_name']
        if pname not in player_odds_map:
            player_odds_map[pname] = []
        player_odds_map[pname].append(odd_entry)
    
    # Process each player
    for player_name, player_exchanges in player_odds_map.items():
        # Find best (lowest) lay odds
        best_odds = min(player_exchanges, key=lambda x: x['lay_odds'])
        price = best_odds['lay_odds']
        lay_size = best_odds['lay_size']
        has_size = best_odds['has_size']  # True only for Betfair
        
        # Build display text with all exchanges
        all_lay_prices = []
        for exchange in player_exchanges:
            site = exchange['site']
            odds = exchange['lay_odds']
            size = exchange['lay_size']
            
            if exchange['has_size']:
                all_lay_prices.append(f"{site} @ {odds} (£{int(size)})")
            else:
                all_lay_prices.append(f"{site} @ {odds}")
        
        lay_prices_text = " | ".join(all_lay_prices)
        
        # Now use 'price' (best lay) for comparisons
        # Use 'has_size' to determine if liquidity checks apply
        # Use 'lay_prices_text' for display in messages
        
        # Example threshold logic:
        if not has_size or lay_size > YOUR_THRESHOLD:
            # Process this player (no Betfair liquidity, or enough liquidity)
            print(f"[ALERT] {player_name}: Lay @ {price}")
            print(f"  Available on: {lay_prices_text}")
```

---

### Step 4: Update Threshold Logic

**Important:** Exchange odds don't have liquidity info, so adjust your threshold checks:

```python
# OLD (Betfair only):
if lay_size > THRESHOLD:
    # Process player

# NEW (with exchanges):
if not has_size or lay_size > THRESHOLD:
    # Process player
    # - has_size=False: No Betfair data, exchange only → always process
    # - has_size=True: Betfair exists → check threshold
```

---

### Step 5: Update Discord/Alert Messages

Include all exchange prices in your alert messages:

```python
# Build message with all exchanges
description = f"""
**Match:** {match_name}
**Player:** {player_name}
**Market:** {market_type}

**Lay Prices:** {lay_prices_text}

**Back Odds:** {back_odds}
**Best Lay:** {price}
**Rating:** {rating}%
"""
```

---

## Key Differences: Betfair vs Exchanges

| Feature | Betfair | Smarkets/Matchbook |
|---------|---------|-------------------|
| Liquidity (size) | ✅ Available | ❌ Not available |
| Freshness check | ❌ Not needed | ✅ Required (5 min) |
| Player coverage | Medium | Higher (more players) |
| Threshold checks | Apply size check | Skip size check |

---

## Match ID Mappings

You'll need a mapping system to convert between platforms:

```python
# Example mapping structure
mappings = {
    'betfair': '1.234567890',
    'oddsmatcha': 'abc-123-def',
    'virginbet': 'VB_12345',
    'williamhill': 'OB_EV12345'
}
```

**How to get OddsMatcha match IDs:**
1. Use OddsMatcha fixtures API: `GET https://api.oddsmatcha.com/api/soccer/fixtures`
2. Match by team names and kick-off time
3. Store mapping in your database/file

---

## Error Handling

```python
# Always handle missing exchange data gracefully
exchange_odds = fetch_exchange_odds(oddsmatcha_match_id)
if not exchange_odds:
    # Fall back to Betfair-only mode
    exchange_odds = {}

# Continue processing - combine function handles empty exchange_odds
all_odds = combine_betfair_and_exchange_odds(betfair_odds, exchange_odds, market_type)
```

---

## Testing

1. **Test with exchange-only player:**
   - Find a player on Smarkets but not Betfair
   - Verify `has_size = False`
   - Verify threshold bypass works

2. **Test with Betfair + exchange:**
   - Player on all platforms
   - Verify best (lowest) price is selected
   - Verify all exchanges shown in display

3. **Test freshness:**
   - Check only odds < 5 minutes old are used
   - Verify stale odds are filtered out

---

## Performance Considerations

- **Cache exchange data:** Fetch once per match, not per player
- **Freshness threshold:** 5 minutes is recommended
- **API rate limits:** OddsMatcha has rate limits, handle errors gracefully
- **Parallel fetching:** Consider fetching exchange data in parallel with Betfair

---

## Example Output

```
[EXCHANGE] Fetched odds for 42 players from Smarkets/Matchbook
[ALERT] Cole Palmer: Lay @ 2.1
  Available on: Betfair @ 2.15 (£150) | Smarkets @ 2.1 | Matchbook @ 2.12
```

---

## Common Issues

**Issue:** Player names don't match between platforms  
**Solution:** Implement fuzzy matching (2/3 name parts, handle hyphens)

**Issue:** Too many stale odds  
**Solution:** Adjust freshness threshold or check OddsMatcha data quality

**Issue:** No exchange data for some matches  
**Solution:** Gracefully fall back to Betfair-only mode

**Issue:** Duplicate players in combined list  
**Solution:** Group by player name before processing (see Step 3)

---

## Summary Checklist

- [ ] Add `ODDSMATCHA_API_KEY` to `.env`
- [ ] Implement `fetch_exchange_odds()` function
- [ ] Implement `combine_betfair_and_exchange_odds()` function
- [ ] Update match loop to fetch exchange data once per match
- [ ] Group combined odds by player name
- [ ] Update threshold logic: `if not has_size or lay_size > THRESHOLD`
- [ ] Update alert messages to show `lay_prices_text`
- [ ] Test with exchange-only players
- [ ] Test freshness filtering
- [ ] Handle missing exchange data gracefully

---

## Code Location Reference (from goosealerts)

- **Fetch function:** `virgin_goose.py` lines 882-970
- **Combine function:** `virgin_goose.py` lines 972-1018
- **Integration in loop:** `virgin_goose.py` lines 1139-1235
- **Threshold logic:** `virgin_goose.py` lines 1238, 1291, 1329
- **Display usage:** `virgin_goose.py` lines 1277, 1318, 1420

---

*This integration pattern has been successfully implemented in the goosealerts project for Virgin Bet (Goose), OddsChecker (ARB), and William Hill alerts.*
