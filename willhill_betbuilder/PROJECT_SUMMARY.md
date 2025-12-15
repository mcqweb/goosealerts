# William Hill Bet Builder - Project Summary

## Overview
A Python application that fetches and analyzes bet builder markets from William Hill's BYO (Build Your Own) API. The tool caches market data, parses available betting options, and helps create bet builder combinations.

## Features Implemented

### ✅ 1. API Client (`src/api_client.py`)
- Fetches market data from William Hill BYO API
- Handles HTTP requests with proper headers
- Extracts event start times
- Error handling for failed requests

### ✅ 2. Cache Manager (`src/cache_manager.py`)
- Saves API responses to local JSON files
- Cache validation based on event start time
- Automatic cache invalidation after event starts
- Cache info and management utilities

### ✅ 3. Market Parser (`src/market_parser.py`)
- Parses market groups from API response
- Extracts categories, periods, and teams
- Gets selections for specific markets
- Category summary and search functionality

### ✅ 4. Combination Generator (`src/combinations.py`)
- Creates bet builder combinations
- Validates selections for conflicts
- Suggests popular combination templates
- Combination management utilities

### ✅ 5. Command Line Interface (`main.py`)
- Fetch markets for any event ID
- List all available categories
- View specific market details
- Force cache refresh option

### ✅ 6. Utilities (`utils.py`)
- List all cached events
- View cached data
- Clear cache (specific or all)
- Export markets to JSON
- Search markets by keyword

### ✅ 7. Examples (`examples.py`)
- 5 comprehensive examples
- Demonstrates all major features
- Ready-to-use code snippets

## Project Structure

```
willhill/
├── venv/                   # Virtual environment
├── cache/                  # Cached market data (JSON files)
│   └── OB_EV37926026.json # Example cached event
├── src/                    # Source code
│   ├── __init__.py
│   ├── api_client.py      # API client
│   ├── cache_manager.py   # Cache management
│   ├── market_parser.py   # Market parsing
│   └── combinations.py    # Combination logic
├── main.py                # Main CLI application
├── utils.py               # Utility scripts
├── examples.py            # Example usage
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── README.md              # Full documentation
├── QUICKSTART.md          # Quick start guide
└── .gitignore             # Git ignore rules
```

## Available Market Categories (Example Event)

The test event (OB_EV37926026 - Man Utd vs Bournemouth) has **33 market categories**:

1. Total Goals
2. Total Corners
3. Total Cards
4. Player to be Carded
5. Player to Score
6. Player to Assist
7. Player to Score or Assist
8. Result (Match Result)
9. Player Shots on Target
10. Player Shots
11. Player Tackles
12. Player Fouls
13. Player Offsides
14. Player to Score a Header
15. Player to Score Outside Box
16. Player to Score Inside 6 Yard Box
17. Player to Score with Left Foot
18. Player to Score with Right Foot
19. Both Teams to Score
20. Team with most Corners
21. Team with most Cards
22. Team with most Booking Points
23. Total Booking Points
24. Double Chance
25. Correct Score
26. Winning Margin
27. Double Result
28. First Team to Score
29. Match Handicap
30. Penalty
31. Corner Handicap
32. Card Handicap
33. Highest Scoring Half

## Usage Examples

### Basic Usage
```bash
# Fetch and cache markets
python main.py OB_EV37926026

# List all categories
python main.py OB_EV37926026 --list-categories

# View specific markets
python main.py OB_EV37926026 --categories "Result" "Total Goals"
```

### Utilities
```bash
# List cached events
python utils.py list

# Search for markets
python utils.py search OB_EV37926026 "player"

# Export markets to JSON
python utils.py export OB_EV37926026

# View cache details
python utils.py view OB_EV37926026 --detail
```

### Run Examples
```bash
python examples.py
```

## Key Components

### WilliamHillAPIClient
```python
api = WilliamHillAPIClient()
markets = api.get_event_markets("OB_EV37926026")
start_time = api.get_event_start_time(markets)
api.close()
```

### CacheManager
```python
cache = CacheManager()
cache.save_to_cache(event_id, data)
cached_data = cache.get_cached_data(event_id)
is_valid = cache.is_cache_valid(event_id, start_time)
```

### MarketParser
```python
parser = MarketParser(markets_data)
categories = parser.get_all_categories()
selections = parser.get_selections_for_market("Result", "90 Minutes")
parser.print_category_summary()
```

### BetBuilderCombinations
```python
combo = BetBuilderCombinations(parser)
popular = combo.get_popular_combinations()
validation = combo.validate_combination(selections)
combination = combo.create_combination(selections)
```

## Popular Bet Builder Templates

1. **Result + Goals** - Match winner with total goals
2. **Both Teams to Score + Winner** - BTTS with match result
3. **Player to Score + Result** - Player to score with outcome
4. **Goals + Corners** - Total goals and corners
5. **Cards + Corners** - Total cards and corners

## Next Steps for Enhancement

### 1. Pricing API Integration
Make subsequent calls to get odds for combinations:
```python
# Hypothetical pricing endpoint
pricing_url = "https://sports.williamhill.com/data/byo01/en-gb/pricing"
response = requests.post(pricing_url, json={
    'eventId': event_id,
    'selections': [ob_id1, ob_id2, ob_id3]
})
```

### 2. Web Interface
Create a Flask/Django web app for easier interaction

### 3. Automated Combination Testing
Test all valid combinations to find value bets

### 4. Historical Analysis
Store and analyze historical odds and results

### 5. Multi-Event Support
Combine selections across multiple events

### 6. Notifications
Alert when certain market conditions are met

### 7. Database Integration
Store markets and combinations in a database

## Dependencies

```
requests>=2.31.0
python-dateutil>=2.8.2
```

## Testing

All features tested with event ID: **OB_EV37926026** (Man Utd vs Bournemouth)

- ✅ API fetching works
- ✅ Cache saves correctly (635KB JSON file)
- ✅ Cache validation works
- ✅ Market parsing successful (33 categories)
- ✅ Combination creation works
- ✅ All utilities functional
- ✅ Examples run successfully

## Cache Details

Cache file for test event:
- **File**: `cache/OB_EV37926026.json`
- **Size**: 635,741 bytes
- **Contains**: Complete market data with all 33 categories
- **Valid until**: Event start time

## API Endpoint Used

```
https://sports.williamhill.com/data/byo01/en-gb/event/{event_id}/markets/byoFreedom
```

## Notes

- Cache automatically invalidates when event starts
- All market data includes OB IDs for subsequent API calls
- Player markets are team-specific
- Most markets support multiple periods (90 Minutes, 1st Half, 2nd Half, 1st 15 Minutes)
- Some markets have `impactSubEligible` flag indicating combination restrictions

## Success Criteria Met

✅ Event ID can be supplied  
✅ API call made to William Hill  
✅ JSON response saved in cache folder  
✅ Cache valid until event start time  
✅ Markets identified and parsed  
✅ Ready for subsequent combination calls  

## Documentation Files

- **README.md** - Complete project documentation
- **QUICKSTART.md** - Quick start guide with code examples
- **This file** - Project summary and overview
- Inline code documentation in all Python files

## Total Files Created

- 10 Python files (src modules, main, utils, examples, config)
- 4 Documentation files
- 1 Requirements file
- 1 .gitignore file
- 1 Cached JSON file

**Total: 17 files**
