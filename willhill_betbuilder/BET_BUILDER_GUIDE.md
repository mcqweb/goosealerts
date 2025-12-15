# Bet Builder Combinations Guide

## Overview

This system generates 4 standard bet builder combinations for William Hill, automatically finding eligible players and extracting OB IDs ready for pricing API calls.

## The 4 Bet Builder Templates

### 1. Anytime Goalscorer (3 selections)
- Total Goals > Both Teams Combined > 90 Minutes > Over 0.5
- Player to Score > {team} > Anytime > {player}
- Player to Score or Assist > {team} > Anytime > {player}

### 2. First Goalscorer (3 selections)
- Total Goals > Both Teams Combined > 90 Minutes > Over 0.5
- Player to Score > {team} > First > {player}
- Player to Score > {team} > Anytime > {player}

### 3. Score 2 or More (3 selections)
- Total Goals > Both Teams Combined > 90 Minutes > Over 1.5
- Player to Score > {team} > Two or More > {player}
- Player to Score > {team} > Anytime > {player}

### 4. Score a Hattrick (3 selections)
- Total Goals > Both Teams Combined > 90 Minutes > Over 1.5
- Player to Score > {team} > Hat-trick > {player}
- Player to Score > {team} > Anytime > {player}

## Quick Start Commands

### List all available templates
```bash
python generate_combos.py --list-templates
```

### Show statistics for an event
```bash
python generate_combos.py OB_EV37926026 --stats
```

### List eligible players for all templates
```bash
python generate_combos.py OB_EV37926026 --list-players
```

### List eligible players for specific template
```bash
python generate_combos.py OB_EV37926026 --list-players --template "Anytime Goalscorer"
```

### Generate combinations for a specific player
```bash
python generate_combos.py OB_EV37926026 --player "Joshua Zirkzee" --team "Man Utd"
```

### Generate specific template for a player
```bash
python generate_combos.py OB_EV37926026 --player "Joshua Zirkzee" --team "Man Utd" --template "First Goalscorer"
```

### Generate ALL combinations and save to JSON
```bash
python generate_combos.py OB_EV37926026 --all --output combos.json
```

## Sample Output

### Combination Example
```
======================================================================
Template: Anytime Goalscorer
Player: Joshua Zirkzee (Man Utd)
Selections: 3
----------------------------------------------------------------------
  1. Total Goals > Both Teams Combined > 90 Minutes
     Selection: Over 0.5
     OB ID: OB_OU5905111337
  2. Player to Score > Man Utd > Anytime
     Selection: Joshua Zirkzee
     OB ID: OB_OU5915067531
  3. Player to Score or Assist > Man Utd > Anytime
     Selection: Joshua Zirkzee
     OB ID: OB_OU5919250645

OB IDs for Pricing API:
  ['OB_OU5905111337', 'OB_OU5915067531', 'OB_OU5919250645']
======================================================================
```

## Test Event Statistics

**Event:** OB_EV37926026 (Man Utd vs Bournemouth)

- **Total Combinations:** 163
- **Anytime Goalscorer:** 37 combos (19 Man Utd + 18 Bournemouth)
- **First Goalscorer:** 42 combos (22 Man Utd + 20 Bournemouth)
- **Score 2 or More:** 42 combos (22 Man Utd + 20 Bournemouth)
- **Score a Hattrick:** 42 combos (22 Man Utd + 20 Bournemouth)

## Python API Usage

```python
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.bet_builder_generator import BetBuilderGenerator

# Load market data
api = WilliamHillAPIClient()
cache = CacheManager()
markets = api.get_event_markets("OB_EV37926026")
cache.save_to_cache("OB_EV37926026", markets)

# Generate combinations
parser = MarketParser(markets)
generator = BetBuilderGenerator(parser)

# For a specific player
combo = generator.generate_combo_for_player(
    "Joshua Zirkzee", 
    "Man Utd", 
    "Anytime Goalscorer"
)

# Print OB IDs for pricing API
print(combo['obIds'])
# ['OB_OU5905111337', 'OB_OU5915067531', 'OB_OU5919250645']

# Generate all combinations for one player
all_combos = generator.generate_all_combos_for_player(
    "Joshua Zirkzee", 
    "Man Utd"
)

# Generate everything
all_event_combos = generator.generate_all_combos_for_event()
```

## Player Eligibility

A player is eligible for a template if they have markets available for **all** required selections:

- **Anytime Goalscorer** requires:
  - Player to Score (Anytime)
  - Player to Score or Assist (Anytime)
  
- **First Goalscorer** requires:
  - Player to Score (First)
  - Player to Score (Anytime)
  
- **Score 2 or More** requires:
  - Player to Score (Two or More)
  - Player to Score (Anytime)
  
- **Score a Hattrick** requires:
  - Player to Score (Hat-trick)
  - Player to Score (Anytime)

## Next Steps - Pricing API

Once you have the OB IDs from a combination, you would:

1. **Collect the OB IDs** from the combination (3 per combo)
2. **Make a pricing API call** (endpoint to be documented by William Hill)
3. **Receive back odds** for the bet builder
4. **Compare with lay odds** to find arbitrage opportunities

## Files Created

- `src/bet_builder_templates.py` - Template definitions and player eligibility checker
- `src/bet_builder_generator.py` - Combination generator with OB ID extraction
- `generate_combos.py` - Main CLI application
- `test_bet_builders.py` - Comprehensive test script
- `all_combos.json` - Generated combinations for the test event

## Workflow Summary

```
Event ID → Fetch Markets → Parse Data → Find Eligible Players → 
Generate Combinations → Extract OB IDs → Call Pricing API → 
Get Odds → Compare Back/Lay → Identify Value
```

## Support

Run the test script to verify everything works:
```bash
python test_bet_builders.py
```

This will show all 4 templates, generate sample combinations, and display statistics.
