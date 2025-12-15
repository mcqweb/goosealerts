# William Hill Bet Builder 🎯

A comprehensive Python application to fetch, analyze, and create bet builder combinations from William Hill's BYO (Build Your Own) API.

## 🌟 Features

✅ **API Integration** - Fetches markets from William Hill BYO API  
✅ **Smart Caching** - Caches market data until event start time  
✅ **Market Analysis** - Parses 33+ market categories  
✅ **Combination Builder** - Creates and validates bet combinations  
✅ **CLI Tools** - Command-line interface for easy interaction  
✅ **Utilities** - Cache management, search, and export tools  
✅ **Documentation** - Comprehensive guides and examples  

## 📦 What's Included

### Core Components
- **API Client** (`src/api_client.py`) - HTTP client for William Hill API
- **Cache Manager** (`src/cache_manager.py`) - Smart caching with auto-expiration
- **Market Parser** (`src/market_parser.py`) - Parses and categorizes markets
- **Combination Builder** (`src/combinations.py`) - Creates valid bet combinations

### Applications
- **main.py** - Primary CLI application
- **utils.py** - Utility commands (list, search, export, clear)
- **examples.py** - 5 working examples
- **test_workflow.py** - Complete workflow demonstration

### Documentation
- **README.md** - This file (overview)
- **QUICKSTART.md** - Quick start guide with code samples
- **PROJECT_SUMMARY.md** - Complete project details

## 🚀 Quick Start

### 1. Installation
```bash
# Navigate to project
cd c:\Python\willhill

# Dependencies already installed in venv
# If needed: venv\Scripts\activate && pip install -r requirements.txt
```

### 2. Fetch Markets for an Event
```bash
python main.py OB_EV37926026
```

### 3. Explore Categories
```bash
python main.py OB_EV37926026 --list-categories
```

### 4. View Specific Markets
```bash
python main.py OB_EV37926026 --categories "Result" "Total Goals" "Both Teams to Score"
```

### 5. Run Examples
```bash
python examples.py
```

### 6. Complete Workflow Test
```bash
python test_workflow.py
```

## 📊 Available Market Categories

The system currently supports **33 market categories** including:

**Match Markets**
- Result, Double Chance, Correct Score
- Both Teams to Score, Winning Margin
- Double Result, First Team to Score

**Goals Markets**
- Total Goals (Over/Under with multiple lines)
- Highest Scoring Half

**Player Markets** (14 categories)
- Player to Score (Anytime/First/Last/2+/Hat-trick)
- Player to Assist
- Player to Score or Assist
- Player Shots, Player Shots on Target
- Player Tackles, Player Fouls, Player Offsides
- Player to Score a Header
- Player to Score Outside/Inside Box
- Player to Score with Left/Right Foot
- Player to be Carded

**Other Markets**
- Total Corners, Total Cards, Total Booking Points
- Corner/Card/Match Handicap
- Team with most Corners/Cards/Booking Points
- Penalty

## 💻 Usage Examples

### Basic Python Usage
```python
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser

# Fetch markets
api = WilliamHillAPIClient()
cache = CacheManager()

event_id = "OB_EV37926026"
markets = api.get_event_markets(event_id)
cache.save_to_cache(event_id, markets)

# Parse markets
parser = MarketParser(markets)
categories = parser.get_all_categories()
print(f"Found {len(categories)} categories")

# Get specific market
selections = parser.get_selections_for_market("Result", "90 Minutes")
for sel in selections:
    print(f"{sel['name']} - {sel['obId']}")
```

### Creating Combinations
```python
from src.combinations import BetBuilderCombinations

combo_builder = BetBuilderCombinations(parser)

# Create a combination
selections = [
    {
        'category': 'Result',
        'selection_name': 'Man Utd Win',
        'ob_id': 'OB_OU5905111386'
    },
    {
        'category': 'Total Goals',
        'selection_name': 'Over 2.5',
        'ob_id': 'OB_OU5905111344'
    }
]

combination = combo_builder.create_combination(selections)
validation = combo_builder.validate_combination(selections)
```

### Utility Commands
```bash
# List all cached events
python utils.py list

# Search for markets
python utils.py search OB_EV37926026 "player"

# Export markets to JSON
python utils.py export OB_EV37926026 --output markets.json

# View cache details
python utils.py view OB_EV37926026 --detail

# Clear cache
python utils.py clear --event-id OB_EV37926026
```

## 📁 Project Structure

```
willhill/
├── venv/                      # Virtual environment
├── cache/                     # Cached market data
│   └── OB_EV37926026.json    # Example (635KB)
├── src/                       # Source code
│   ├── __init__.py
│   ├── api_client.py         # William Hill API client
│   ├── cache_manager.py      # Cache with auto-expiration
│   ├── market_parser.py      # Market data parser
│   └── combinations.py       # Combination logic
├── main.py                    # Main CLI application
├── utils.py                   # Utility commands
├── examples.py                # Usage examples
├── test_workflow.py           # Workflow demonstration
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── README.md                  # This file
├── QUICKSTART.md              # Quick start guide
├── PROJECT_SUMMARY.md         # Complete summary
└── .gitignore                # Git ignore rules
```

## 🎯 Example Bet Builder Combinations

The system suggests these popular templates:

1. **Result + Goals** - Match winner with total goals
2. **Both Teams to Score + Winner** - BTTS with match result  
3. **Player to Score + Result** - Player to score with outcome
4. **Goals + Corners** - Total goals and corners
5. **Cards + Corners** - Total cards and corners

## 🔧 API Endpoint

```
https://sports.williamhill.com/data/byo01/en-gb/event/{event_id}/markets/byoFreedom
```

## 📝 Test Results

✅ Successfully tested with event **OB_EV37926026** (Man Utd vs Bournemouth)
- Fetched 33 market categories
- Cached 635KB of market data
- Created valid combinations
- All utilities working
- Examples run successfully

## 🎓 Learning Resources

- **QUICKSTART.md** - Step-by-step guide with code examples
- **examples.py** - 5 comprehensive working examples
- **test_workflow.py** - Complete workflow from fetch to combination
- **PROJECT_SUMMARY.md** - Detailed project documentation

## 🔮 Next Steps

To extend this project, you could:

1. **Pricing Integration** - Make POST requests to get odds for combinations
2. **Web Interface** - Build a Flask/Django web app
3. **Database Storage** - Store historical markets and odds
4. **Multi-Event** - Combine selections across multiple events
5. **Automation** - Auto-generate and test combinations
6. **Notifications** - Alert on specific market conditions

## 📋 Dependencies

```
requests>=2.31.0       # HTTP requests
python-dateutil>=2.8.2 # Date parsing
```

## 🧪 Testing

Run the complete test suite:
```bash
python test_workflow.py
```

Output includes:
- Market fetching and caching
- Parsing 33 categories
- Creating valid combinations
- Extracting OB IDs for pricing calls

## 📌 Important Notes

- Cache automatically expires when event starts
- All selections include OB IDs for pricing API calls
- Player markets are team-specific
- Most markets support multiple periods
- Some markets have combination restrictions (impactSubEligible flag)

## 🎉 Success Criteria

✅ Fetch markets for any event ID  
✅ Cache responses with expiration  
✅ Parse and categorize all markets  
✅ Create valid bet combinations  
✅ Extract OB IDs for pricing calls  
✅ Comprehensive documentation  

## 📄 License

This is a demonstration project for educational purposes.

## 🤝 Contributing

This is a personal project. Feel free to fork and modify for your own use.

---

**Ready to build bet combinations? Start with:**
```bash
python main.py OB_EV37926026 --list-categories
```
