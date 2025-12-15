# William Hill Pricing API Integration

## Overview
The bet builder system now includes full integration with William Hill's pricing API to fetch live odds for any combination.

## API Details

### Endpoint
```
POST https://transact.williamhill.com/betslip/api/bets/getByoPrice
```

### Headers
```json
{
  "accept": "application/json",
  "accept-encoding": "gzip, deflate, br, zstd",
  "accept-language": "en-GB,en;q=0.9",
  "content-type": "application/json",
  "origin": "https://sports.williamhill.com",
  "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

### Cookie
```
SESSION=YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5
```

### Request Payload
```json
{
  "eventID": "1e0e2839-f47a-49ad-be8c-501a8d3c3e5d",
  "selections": [
    {
      "selectionId": "e2defd9b-3148-3d94-aa3a-cdde92c36feb",
      "handicap": null
    }
  ],
  "combinationIdCheckValue": ""
}
```

### Response
```json
{
  "status": "ok",
  "traceId": "693ff0d23d3089f7a46ee25e0b768b51",
  "selection": {
    "price": {
      "type": "FIXED_ODDS",
      "numerator": 9,
      "denominator": 5,
      "us": 180.0,
      "decimal": 2.8
    },
    "byoMarketId": "1664853671"
  }
}
```

## Usage

### Basic Usage - Get Pricing for a Single Template
```bash
python generate_combos.py OB_EV37926026 \
  --player "Joshua Zirkzee" \
  --team "Man Utd" \
  --template "Anytime Goalscorer" \
  --get-price
```

**Output:**
```
======================================================================
Template: Anytime Goalscorer
Player: Joshua Zirkzee (Man Utd)
Selections: 3
Odds: 2.8 (9/5)
----------------------------------------------------------------------
  1. Total Goals > Both Teams Combined > 90 Minutes
     Selection: Over 0.5
     Selection ID: e2defd9b-3148-3d94-aa3a-cdde92c36feb
  2. Player to Score > Man Utd > Anytime
     Selection: Joshua Zirkzee
     Selection ID: 6206a11d-02b3-3338-bd35-116124631a5a
  3. Player to Score or Assist > Man Utd > Anytime
     Selection: Joshua Zirkzee
     Selection ID: e2d4bc4c-cc39-3a8a-b684-9092101b310b
======================================================================
```

### Get Pricing for All 4 Templates
```bash
python generate_combos.py OB_EV37926026 \
  --player "Bryan Mbeumo" \
  --team "Man Utd" \
  --get-price
```

**Output shows all 4 templates with live odds:**
- Anytime Goalscorer: **2.25 (5/4)**
- First Goalscorer: **5.25 (17/4)**
- Score 2 or More: **8.0 (7/1)**
- Score a Hattrick: **29.0 (28/1)**

### Custom Session Cookie
If you need to use a different session cookie:
```bash
python generate_combos.py OB_EV37926026 \
  --player "Joshua Zirkzee" \
  --team "Man Utd" \
  --template "Anytime Goalscorer" \
  --get-price \
  --session "YOUR_CUSTOM_SESSION_COOKIE_HERE"
```

## Code Integration

### Using the API in Python
```python
from src.market_parser import MarketParser
from src.bet_builder_generator import BetBuilderGenerator

# Initialize with market data
parser = MarketParser(market_data)
generator = BetBuilderGenerator(parser)

# Generate a combination
combo = generator.generate_combo_for_player(
    "Joshua Zirkzee",
    "Man Utd",
    "Anytime Goalscorer"
)

# Get live pricing
price_data = generator.get_combo_price(combo)

if price_data and price_data.get("status") == "ok":
    price = price_data["selection"]["price"]
    print(f"Decimal odds: {price['decimal']}")
    print(f"Fractional: {price['numerator']}/{price['denominator']}")
    print(f"American: {price['us']}")
```

### Custom Session Cookie in Code
```python
# Use custom session cookie
price_data = generator.get_combo_price(
    combo,
    session_cookie="YOUR_CUSTOM_SESSION_COOKIE"
)
```

## Price Data Structure

### Odds Formats
The API returns odds in multiple formats:

1. **Decimal** (`2.8`) - European format
2. **Fractional** (`9/5`) - UK format  
3. **American** (`180.0`) - US format

### Market ID
The response includes a `byoMarketId` which uniquely identifies this specific bet builder combination.

## Example: Complete Workflow

```bash
# 1. List eligible players for a template
python generate_combos.py OB_EV37926026 \
  --list-players \
  --template "Anytime Goalscorer"

# 2. Generate combination with live pricing
python generate_combos.py OB_EV37926026 \
  --player "Joshua Zirkzee" \
  --team "Man Utd" \
  --template "Anytime Goalscorer" \
  --get-price

# 3. Compare odds across all 4 templates
python generate_combos.py OB_EV37926026 \
  --player "Joshua Zirkzee" \
  --team "Man Utd" \
  --get-price
```

## Best Practices

1. **Rate Limiting**: The API may have rate limits. When fetching prices for many combinations, add delays between requests if needed.

2. **Error Handling**: Always check the response status:
   ```python
   if price_data and price_data.get("status") == "ok":
       # Process pricing
   else:
       # Handle error
   ```

3. **Session Cookies**: Session cookies may expire. If you get authentication errors, you may need to refresh the cookie.

4. **Cache Market Data**: Market data is cached locally, but pricing is always fetched live to ensure current odds.

## Troubleshooting

### "Failed to fetch pricing data"
- Check your internet connection
- Verify the SESSION cookie is valid
- Ensure the event is still active on William Hill

### Rate Limiting
If you're fetching prices for many combinations:
```python
import time

for combo in combos:
    price_data = generator.get_combo_price(combo)
    time.sleep(0.5)  # Add 500ms delay between requests
```

## Next Steps

Potential enhancements:
1. Batch pricing requests to reduce API calls
2. Store historical pricing data for analysis
3. Compare back vs lay odds across exchanges
4. Alert system for favorable odds
5. Export to spreadsheet with live odds
