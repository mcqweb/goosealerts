# Integration Guide - Using in Your Existing Project

## Quick Start

### Files to Copy

Copy these files/folders to your project:

```
your_project/
├── willhill_betbuilder/          # Copy entire folder
│   ├── __init__.py
│   ├── client.py
│   ├── config.py
│   └── src/
│       ├── __init__.py
│       ├── api_client.py
│       ├── cache_manager.py
│       ├── market_parser.py
│       ├── bet_builder_templates.py
│       └── bet_builder_generator.py
├── .env                          # Your configuration
└── your_script.py                # Your existing script
```

**Or** install as package:
1. Put the `willhill` folder somewhere
2. Add to your Python path or install locally

### Dependencies

Add to your `requirements.txt`:
```
requests>=2.31.0
python-dateutil>=2.8.2
python-dotenv>=1.0.0
```

## Configuration

Create `.env` in your project root:

```env
# William Hill session cookie
WILLIAMHILL_SESSION=your_session_cookie_here

# NordVPN proxy (optional)
NORD_USER=your_email@example.com
NORD_PWD=your_nordvpn_password
NORD_LOCATION=us5678

# Or standard proxy (optional)
# HTTP_PROXY=http://localhost:8080
# HTTPS_PROXY=https://localhost:8080
```

## Simple Usage - Get Odds for a Bet

### Scenario: You have player name, match ID, and bet type

```python
from willhill_betbuilder import BetBuilderClient, Config

# Optional: Configure if not using .env
Config.SESSION_COOKIE = "your_session_cookie"
Config.NORD_USER = "your_email@example.com"
Config.NORD_PWD = "your_password"
Config.NORD_LOCATION = "us5678"

# Create client
client = BetBuilderClient()

# Load match data
event_id = "OB_EV37926026"  # Your match ID
client.load_event(event_id)

# Your inputs
player_name = "Joshua Zirkzee"
team = "Man Utd"
bet_type = "Anytime Goalscorer"  # or "First Goalscorer", "Score 2 or More", "Score a Hattrick"

# Get the combination with odds
combos = client.get_player_combinations(
    player_name=player_name,
    team=team,
    template_name=bet_type,
    get_price=True  # This fetches live odds
)

# Extract odds from first combination
if combos and len(combos) > 0:
    combo = combos[0]
    
    if combo.get('price_data') and combo['price_data'].get('success'):
        odds = combo['price_data']['odds']
        print(f"Odds for {player_name} - {bet_type}: {odds}")
        # Example output: "Odds for Joshua Zirkzee - Anytime Goalscorer: 2.80"
    else:
        print("Could not get odds")
else:
    print("No valid combination found")
```

## Function Reference

### Core Functions You Need

#### 1. Load Event Data
```python
client = BetBuilderClient()
client.load_event(match_id)
```

#### 2. Get Odds for Specific Player + Bet Type
```python
combos = client.get_player_combinations(
    player_name="Joshua Zirkzee",
    team="Man Utd",
    template_name="Anytime Goalscorer",
    get_price=True  # Set to True to get live odds
)
```

**Returns:** List of combinations with odds data

#### 3. Extract Odds from Response
```python
combo = combos[0]
odds = combo['price_data']['odds']  # Decimal odds (e.g., 2.80)
```

## Complete Example - Single Function Call

```python
from willhill_betbuilder import BetBuilderClient

def get_bet_odds(match_id, player_name, team, bet_type):
    """
    Get odds for a specific player bet
    
    Args:
        match_id: Event ID (e.g., "OB_EV37926026")
        player_name: Player name (e.g., "Joshua Zirkzee")
        team: Team name (e.g., "Man Utd")
        bet_type: One of "Anytime Goalscorer", "First Goalscorer", 
                  "Score 2 or More", "Score a Hattrick"
    
    Returns:
        float: Decimal odds or None if not available
    """
    try:
        client = BetBuilderClient()
        client.load_event(match_id)
        
        combos = client.get_player_combinations(
            player_name=player_name,
            team=team,
            template_name=bet_type,
            get_price=True
        )
        
        if combos and len(combos) > 0:
            combo = combos[0]
            if combo.get('price_data') and combo['price_data'].get('success'):
                return combo['price_data']['odds']
        
        return None
        
    except Exception as e:
        print(f"Error getting odds: {e}")
        return None


# Usage in your script
odds = get_bet_odds(
    match_id="OB_EV37926026",
    player_name="Joshua Zirkzee",
    team="Man Utd",
    bet_type="Anytime Goalscorer"
)

if odds:
    print(f"Odds: {odds}")  # Output: Odds: 2.80
else:
    print("Odds not available")
```

## Response Structure

### Combination Object

```python
{
    "player": "Joshua Zirkzee",
    "team": "Man Utd",
    "template": "Anytime Goalscorer",
    "selections": [
        {
            "market": "Anytime Goalscorer - Joshua Zirkzee",
            "selection": "Yes",
            "id": "12345"  # Selection ID for pricing
        },
        {
            "market": "Player to Score or Assist - Joshua Zirkzee",
            "selection": "Yes",
            "id": "67890"
        },
        {
            "market": "Player Shots on Target - Joshua Zirkzee",
            "selection": "1 or More",
            "id": "11111"
        }
    ],
    "success": true,
    "payload": {
        "eventId": "37926026",
        "selections": [12345, 67890, 11111]
    },
    "price_data": {  # Only present if get_price=True
        "success": true,
        "odds": 2.80,
        "selections": [
            {
                "id": "12345",
                "displayOdds": "9/5",
                "decimalOdds": 2.80
            }
        ]
    }
}
```

### Extracting Data

```python
# Odds (decimal)
odds = combo['price_data']['odds']  # 2.80

# Individual selection odds
for selection in combo['price_data']['selections']:
    print(f"ID: {selection['id']}, Odds: {selection['decimalOdds']}")

# Display odds (fractional)
display_odds = combo['price_data']['selections'][0]['displayOdds']  # "9/5"
```

## Available Bet Types

```python
bet_types = [
    "Anytime Goalscorer",    # 3 selections
    "First Goalscorer",      # 3 selections
    "Score 2 or More",       # 3 selections
    "Score a Hattrick"       # 3 selections
]
```

### Get Available Bet Types for a Player

```python
# Load event
client.load_event(match_id)

# Check which templates this player qualifies for
templates = client.get_templates(
    player_name="Joshua Zirkzee",
    team="Man Utd"
)

print(f"Available bet types: {templates}")
# Output: ['Anytime Goalscorer', 'First Goalscorer', 'Score 2 or More']
```

## Error Handling

```python
def get_bet_odds_safe(match_id, player_name, team, bet_type):
    """Get odds with comprehensive error handling"""
    
    try:
        client = BetBuilderClient()
        
        # Load event
        if not client.load_event(match_id):
            return {"error": "Failed to load event data"}
        
        # Get combinations
        combos = client.get_player_combinations(
            player_name=player_name,
            team=team,
            template_name=bet_type,
            get_price=True
        )
        
        # Check if we got results
        if not combos or len(combos) == 0:
            return {"error": "No combinations found for this player/bet type"}
        
        combo = combos[0]
        
        # Check if combination is valid
        if not combo.get('success'):
            return {"error": "Invalid combination"}
        
        # Check if we got price data
        if not combo.get('price_data'):
            return {"error": "No price data available"}
        
        if not combo['price_data'].get('success'):
            return {"error": "Failed to fetch odds"}
        
        # Success - return odds
        return {
            "success": True,
            "odds": combo['price_data']['odds'],
            "display_odds": combo['price_data']['selections'][0]['displayOdds'],
            "player": player_name,
            "bet_type": bet_type
        }
        
    except KeyError as e:
        return {"error": f"Missing data field: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


# Usage
result = get_bet_odds_safe(
    match_id="OB_EV37926026",
    player_name="Joshua Zirkzee",
    team="Man Utd",
    bet_type="Anytime Goalscorer"
)

if result.get('success'):
    print(f"Odds: {result['odds']} ({result['display_odds']})")
else:
    print(f"Error: {result['error']}")
```

## Batch Processing Multiple Players

```python
def get_multiple_player_odds(match_id, players_data):
    """
    Get odds for multiple players
    
    Args:
        match_id: Event ID
        players_data: List of dicts with player_name, team, bet_type
    
    Returns:
        List of results
    """
    client = BetBuilderClient()
    client.load_event(match_id)
    
    results = []
    
    for data in players_data:
        combos = client.get_player_combinations(
            player_name=data['player_name'],
            team=data['team'],
            template_name=data['bet_type'],
            get_price=True
        )
        
        if combos and combos[0].get('price_data', {}).get('success'):
            results.append({
                'player': data['player_name'],
                'bet_type': data['bet_type'],
                'odds': combos[0]['price_data']['odds'],
                'success': True
            })
        else:
            results.append({
                'player': data['player_name'],
                'bet_type': data['bet_type'],
                'odds': None,
                'success': False
            })
    
    return results


# Usage
players = [
    {'player_name': 'Joshua Zirkzee', 'team': 'Man Utd', 'bet_type': 'Anytime Goalscorer'},
    {'player_name': 'Marcus Rashford', 'team': 'Man Utd', 'bet_type': 'First Goalscorer'},
    {'player_name': 'Evanilson', 'team': 'Bournemouth', 'bet_type': 'Score 2 or More'},
]

results = get_multiple_player_odds("OB_EV37926026", players)

for result in results:
    if result['success']:
        print(f"{result['player']} - {result['bet_type']}: {result['odds']}")
    else:
        print(f"{result['player']} - {result['bet_type']}: Not available")
```

## Performance Tips

### 1. Cache Event Data

```python
# Load once, use multiple times
client = BetBuilderClient()
client.load_event(match_id)  # Cached automatically

# Multiple calls use cached data
odds1 = client.get_player_combinations(...)
odds2 = client.get_player_combinations(...)
odds3 = client.get_player_combinations(...)
```

### 2. Batch Odds Requests

```python
# Get all combinations first (no pricing)
all_combos = client.get_all_combinations()

# Then get pricing for selected ones
for combo in selected_combos:
    price = client.get_combination_price(combo)
```

### 3. Disable Cache for Live Odds

```python
from config import Config

# Force fresh data
Config.CACHE_EXPIRY_HOURS = 0  # Disable cache
```

## Minimal Integration Example

```python
# your_script.py
import sys
sys.path.insert(0, './willhill_betbuilder')  # Adjust path as needed

from willhill_betbuilder import BetBuilderClient, Config

# Configure
Config.SESSION_COOKIE = "your_session_cookie"
Config.NORD_USER = "your_email"
Config.NORD_PWD = "your_password"
Config.NORD_LOCATION = "us5678"

# Get odds
def get_odds(match_id, player, team, bet_type):
    client = BetBuilderClient()
    client.load_event(match_id)
    combos = client.get_player_combinations(player, team, bet_type, get_price=True)
    
    if combos and combos[0].get('price_data', {}).get('success'):
        return combos[0]['price_data']['odds']
    return None

# Use in your existing code
odds = get_odds("OB_EV37926026", "Joshua Zirkzee", "Man Utd", "Anytime Goalscorer")
print(f"Odds: {odds}")
```

## Troubleshooting

### "No module named 'willhill_betbuilder'"

**Solution:** Adjust Python path or copy folder to correct location
```python
import sys
sys.path.insert(0, '/path/to/willhill_betbuilder')
```

### "Failed to fetch pricing data"

**Solution:** Check session cookie is valid
```python
Config.SESSION_COOKIE = "new_session_cookie"
```

### "No combinations found"

**Possible causes:**
- Player name spelling doesn't match exactly
- Team name doesn't match (use "Man Utd" not "Manchester United")
- Bet type not available for this player
- Player not in the match

**Solution:** Check available players first
```python
eligible = client.get_eligible_players(template_name="Anytime Goalscorer")
print(eligible)
```

### Proxy connection issues

**Solution:** Test proxy configuration
```python
from config import Config
print(Config.get_proxies())
```

## Summary - What You Need

### Minimum Setup

1. **Copy files:** `willhill_betbuilder/` folder to your project
2. **Install deps:** `pip install requests python-dateutil python-dotenv`
3. **Configure:** Create `.env` with WILLIAMHILL_SESSION and NordVPN settings
4. **Use:** Three lines of code:
   ```python
   from willhill_betbuilder import BetBuilderClient
   client = BetBuilderClient()
   client.load_event(match_id)
   combos = client.get_player_combinations(player, team, bet_type, get_price=True)
   odds = combos[0]['price_data']['odds']
   ```

That's it! You now have live odds integrated into your script.
