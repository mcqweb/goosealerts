# William Hill Bet Builder - Module Usage Guide

## Installation as a Module

You can use this William Hill Bet Builder in your own Python projects as a module.

### Option 1: Direct Integration

Copy the entire `willhill` directory into your project:

```
your_project/
├── willhill_betbuilder/      # Copy entire directory here
│   ├── __init__.py
│   ├── client.py
│   ├── config.py
│   ├── src/
│   └── ...
├── your_script.py
└── requirements.txt
```

### Option 2: Add to Python Path

Add the William Hill directory to your Python path:

```python
import sys
sys.path.append('/path/to/willhill')

from client import BetBuilderClient
from config import Config
```

## Quick Start

### Basic Usage

```python
from willhill_betbuilder import BetBuilderClient, Config

# Create client
client = BetBuilderClient()

# Load event
client.load_event("OB_EV37926026")

# Get combinations for a player
combos = client.get_player_combinations("Joshua Zirkzee", "Man Utd")

# Display combinations
for combo in combos:
    print(client.format_combination(combo))
```

### With Configuration

```python
from willhill_betbuilder import BetBuilderClient, Config

# Configure session and proxy
Config.set_session_cookie("YOUR_SESSION_COOKIE_HERE")
Config.set_proxy(
    http_proxy="http://localhost:8080",
    https_proxy="https://localhost:8080"
)

# Create client
client = BetBuilderClient()

# Load event
client.load_event("OB_EV37926026")

# Get combinations with pricing
combos = client.get_player_combinations("Joshua Zirkzee", "Man Utd", "Anytime Goalscorer")

for combo in combos:
    price = client.get_combination_price(combo)
    if price:
        odds = price['selection']['price']['decimal']
        print(f"{combo['template']}: {odds}")
```

### Load from Configuration File

```python
from willhill_betbuilder import BetBuilderClient, load_config

# Load settings from JSON file
load_config("my_config.json")

# Create client
client = BetBuilderClient()
```

**my_config.json:**
```json
{
  "session_cookie": "YOUR_SESSION_COOKIE",
  "http_proxy": "http://localhost:8080",
  "https_proxy": "https://localhost:8080",
  "cache_expiry_hours": 24
}
```

## Configuration

### Session Cookie

The session cookie is required for pricing API calls:

```python
from willhill_betbuilder import Config

# Set directly
Config.set_session_cookie("YOUR_SESSION_COOKIE")

# Or via environment variable
import os
os.environ['WILLIAMHILL_SESSION'] = "YOUR_SESSION_COOKIE"
```

### Proxy Configuration

Route all API calls through a proxy:

```python
from willhill_betbuilder import Config

# HTTP proxy only
Config.set_proxy(http_proxy="http://user:pass@proxy.com:8080")

# Both HTTP and HTTPS
Config.set_proxy(
    http_proxy="http://localhost:8080",
    https_proxy="https://localhost:8080"
)

# Or via environment variables
import os
os.environ['HTTP_PROXY'] = "http://localhost:8080"
os.environ['HTTPS_PROXY'] = "https://localhost:8080"
```

### Cache Directory

Customize the cache location:

```python
from willhill_betbuilder import BetBuilderClient
from pathlib import Path

# Custom cache directory
client = BetBuilderClient(cache_dir=Path("/my/custom/cache"))
```

## Complete Examples

### Example 1: Get All Combinations for an Event

```python
from willhill_betbuilder import BetBuilderClient

client = BetBuilderClient()
client.load_event("OB_EV37926026")

# Get all combinations
all_combos = client.get_all_combinations()

# Display summary
stats = client.get_summary_stats()
print(f"Total combinations: {stats['total_combinations']}")
print("\nBy template:")
for template, count in stats['by_template'].items():
    print(f"  {template}: {count}")
```

### Example 2: Find Best Odds for a Player

```python
from willhill_betbuilder import BetBuilderClient, Config

Config.set_session_cookie("YOUR_SESSION_COOKIE")

client = BetBuilderClient()
client.load_event("OB_EV37926026")

# Get all templates for a player
combos = client.get_player_combinations("Joshua Zirkzee", "Man Utd")

best_odds = 0
best_combo = None

for combo in combos:
    price = client.get_combination_price(combo)
    if price and price.get('status') == 'ok':
        odds = price['selection']['price']['decimal']
        if odds > best_odds:
            best_odds = odds
            best_combo = combo

print(f"Best odds: {best_odds}")
print(f"Template: {best_combo['template']}")
```

### Example 3: Export to CSV

```python
import csv
from willhill_betbuilder import BetBuilderClient, Config

Config.set_session_cookie("YOUR_SESSION_COOKIE")

client = BetBuilderClient()
client.load_event("OB_EV37926026")

all_combos = client.get_all_combinations()

# Export to CSV
with open('combos.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Template', 'Player', 'Team', 'Decimal Odds', 'Fractional Odds'])
    
    for template_name, combos in all_combos.items():
        for combo in combos[:5]:  # First 5 per template
            price = client.get_combination_price(combo)
            if price and price.get('status') == 'ok':
                decimal = price['selection']['price']['decimal']
                frac = f"{price['selection']['price']['numerator']}/{price['selection']['price']['denominator']}"
                
                writer.writerow([
                    combo['template'],
                    combo['player'],
                    combo['team'],
                    decimal,
                    frac
                ])

print("✓ Exported to combos.csv")
```

### Example 4: Filter by Minimum Odds

```python
from willhill_betbuilder import BetBuilderClient, Config

Config.set_session_cookie("YOUR_SESSION_COOKIE")

client = BetBuilderClient()
client.load_event("OB_EV37926026")

MIN_ODDS = 3.0

# Get all combinations
all_combos = client.get_all_combinations()

high_odds_combos = []

for template_name, combos in all_combos.items():
    for combo in combos:
        price = client.get_combination_price(combo)
        if price and price.get('status') == 'ok':
            odds = price['selection']['price']['decimal']
            if odds >= MIN_ODDS:
                combo['odds'] = odds
                high_odds_combos.append(combo)

# Sort by odds
high_odds_combos.sort(key=lambda x: x['odds'], reverse=True)

print(f"Found {len(high_odds_combos)} combinations with odds >= {MIN_ODDS}")
for combo in high_odds_combos[:10]:
    print(f"{combo['player']} ({combo['team']}) - {combo['template']}: {combo['odds']}")
```

### Example 5: Integrate with Flask API

```python
from flask import Flask, jsonify, request
from willhill_betbuilder import BetBuilderClient, Config

app = Flask(__name__)

# Configure
Config.set_session_cookie("YOUR_SESSION_COOKIE")

@app.route('/event/<event_id>/players/<team>')
def get_players(event_id, team):
    client = BetBuilderClient()
    client.load_event(event_id)
    
    eligible = client.get_eligible_players()
    players = eligible.get(team, [])
    
    return jsonify({
        'team': team,
        'players': [p['name'] for p in players]
    })

@app.route('/event/<event_id>/combinations')
def get_combinations(event_id):
    player = request.args.get('player')
    team = request.args.get('team')
    template = request.args.get('template')
    
    client = BetBuilderClient()
    client.load_event(event_id)
    
    combos = client.get_player_combinations(player, team, template)
    
    # Add pricing
    results = []
    for combo in combos:
        price = client.get_combination_price(combo)
        if price:
            combo['price'] = price
        results.append(combo)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
```

## API Reference

### BetBuilderClient

#### Methods

- `load_event(event_id, force_refresh=False)` - Load market data for an event
- `get_templates()` - Get list of available templates
- `get_template_info(template_name)` - Get template configuration
- `get_eligible_players(template_name=None)` - Get eligible players
- `get_player_combinations(player_name, team, template_name=None)` - Generate combinations
- `get_all_combinations()` - Generate all combinations for event
- `get_combination_price(combination)` - Get live pricing
- `get_summary_stats()` - Get summary statistics
- `format_combination(combination, include_payload=False, price_data=None)` - Format for display

### Config

#### Class Methods

- `set_session_cookie(cookie)` - Set session cookie
- `set_proxy(http_proxy=None, https_proxy=None)` - Set proxy configuration
- `load_from_file(config_file)` - Load from JSON file
- `save_to_file(config_file)` - Save to JSON file
- `get_proxies()` - Get proxy dictionary for requests

#### Properties

- `SESSION_COOKIE` - Current session cookie
- `HTTP_PROXY` - HTTP proxy URL
- `HTTPS_PROXY` - HTTPS proxy URL
- `CACHE_DIR` - Cache directory path
- `CACHE_EXPIRY_HOURS` - Cache expiration time
- `API_TIMEOUT` - API request timeout

## Environment Variables

You can also configure via environment variables:

- `WILLIAMHILL_SESSION` - Session cookie
- `HTTP_PROXY` - HTTP proxy URL
- `HTTPS_PROXY` - HTTPS proxy URL

```bash
export WILLIAMHILL_SESSION="YOUR_SESSION_COOKIE"
export HTTP_PROXY="http://localhost:8080"
export HTTPS_PROXY="https://localhost:8080"

python your_script.py
```

## Error Handling

```python
from willhill_betbuilder import BetBuilderClient

client = BetBuilderClient()

try:
    # Try to load event
    if not client.load_event("OB_EV37926026"):
        print("Failed to load event data")
        exit(1)
    
    # Try to get combinations
    combos = client.get_player_combinations("Joshua Zirkzee", "Man Utd")
    
    if not combos:
        print("No combinations found for this player")
        exit(1)
    
    # Try to get pricing
    for combo in combos:
        price = client.get_combination_price(combo)
        if price and price.get('status') == 'ok':
            print(f"Odds: {price['selection']['price']['decimal']}")
        else:
            print("Failed to fetch pricing")

except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

1. **Reuse Client Instances**: Create one client per event rather than multiple instances
2. **Cache Configuration**: Load config once at startup
3. **Handle Rate Limits**: Add delays between pricing requests if processing many combinations
4. **Error Handling**: Always check return values and handle None cases
5. **Proxy for Production**: Use proxies to avoid IP blocking
6. **Update Session Cookie**: Session cookies expire, update regularly
