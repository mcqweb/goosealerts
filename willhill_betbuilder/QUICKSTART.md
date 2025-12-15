# Quick Start Guide

## 1. First Time Setup

```bash
# Navigate to project
cd c:\Python\willhill

# Activate virtual environment
venv\Scripts\activate

# Install dependencies (already done)
pip install -r requirements.txt
```

## 2. Basic Usage

### Fetch markets for an event:
```bash
python main.py OB_EV37926026
```

### List all available categories:
```bash
python main.py OB_EV37926026 --list-categories
```

### View specific market details:
```bash
python main.py OB_EV37926026 --categories "Result" "Total Goals" "Both Teams to Score"
```

## 3. Using in Your Code

```python
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser

# Initialize
cache = CacheManager()
api = WilliamHillAPIClient()

# Fetch markets (uses cache automatically)
event_id = "OB_EV37926026"
cached_data = cache.get_cached_data(event_id)

if cached_data:
    markets = cached_data
else:
    markets = api.get_event_markets(event_id)
    cache.save_to_cache(event_id, markets)

# Parse markets
parser = MarketParser(markets)

# Get categories
categories = parser.get_all_categories()
print(categories)

# Get specific market selections
selections = parser.get_selections_for_market("Result", "90 Minutes")
for sel in selections:
    print(f"{sel['name']} - {sel['obId']}")

api.close()
```

## 4. Creating Bet Combinations

```python
from src.combinations import BetBuilderCombinations

# Create combinations helper
combo_builder = BetBuilderCombinations(parser)

# Get popular templates
popular = combo_builder.get_popular_combinations()

# Create custom combination
selections = [
    {
        'category': 'Result',
        'period': '90 Minutes',
        'selection_id': 'sel-1',
        'selection_name': 'Man Utd Win',
        'ob_id': 'OB_OU5905111386',
        'type': 'HOME'
    },
    {
        'category': 'Total Goals',
        'period': '90 Minutes',
        'selection_id': 'sel-2',
        'selection_name': 'Over 2.5',
        'ob_id': 'OB_OU5905110489',
        'type': 'OVER'
    }
]

# Validate combination
validation = combo_builder.validate_combination(selections)
if validation['valid']:
    combination = combo_builder.create_combination(selections)
    print(f"Created combination with {combination['count']} selections")
```

## 5. Next Steps - Making Pricing Calls

Once you have your selections, you would typically:

1. Collect the OB IDs from your selected markets
2. Make a POST request to William Hill's pricing endpoint
3. The endpoint would return the combined odds

Example structure (endpoint details would need to be discovered):
```python
import requests

# Your selected OB IDs
selection_ids = ["OB_OU5905111386", "OB_OU5905110489", "OB_OU5905111848"]

# POST to pricing endpoint (URL is hypothetical - needs verification)
pricing_url = "https://sports.williamhill.com/data/byo01/en-gb/pricing"
response = requests.post(pricing_url, json={
    'eventId': 'OB_EV37926026',
    'selections': selection_ids
})

odds_data = response.json()
```

## 6. Cache Management

The cache automatically invalidates when events start. To manually manage cache:

```python
from src.cache_manager import CacheManager

cache = CacheManager()

# Get cache info
info = cache.get_cache_info("OB_EV37926026")
print(f"Cache created: {info['created']}")
print(f"Cache size: {info['size_bytes']} bytes")

# Clear specific cache
cache.clear_cache("OB_EV37926026")

# Clear all cache
cache.clear_cache()
```

## Common Market Categories

- **Result** - Match winner (Home/Draw/Away)
- **Total Goals** - Over/Under goals
- **Both Teams to Score** - Yes/No
- **Correct Score** - Exact score predictions
- **Player to Score** - Anytime/First/Last goalscorer
- **Total Corners** - Over/Under corners
- **Total Cards** - Over/Under cards
- **Double Chance** - Combined outcomes
- **Handicap** - Match with handicap applied

## Tips

1. Cache files are stored in `cache/` folder as JSON
2. Each event is cached until its start time
3. Use `--force-refresh` to bypass cache
4. Most markets have multiple periods: "90 Minutes", "1st Half", "2nd Half", "1st 15 Minutes"
5. Player markets are team-specific
6. Check `impactSubEligible` to see if selections can be combined with others
