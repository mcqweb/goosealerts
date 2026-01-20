# Kwiff Integration Guide

## ✅ What's Been Implemented

The Kwiff module is now fully integrated into goosealerts with automatic event fetching and mapping capabilities.

### Features

- ✅ **WebSocket Client**: Connects to Kwiff's real-time API
- ✅ **Event Fetching**: Retrieves featured football matches from Kwiff
- ✅ **Auto-Mapping**: Automatically maps Kwiff event IDs to Betfair market IDs
- ✅ **Startup Integration**: Runs on script startup to ensure fresh data
- ✅ **Event Lookups**: Query Betfair IDs for Kwiff events

### Test Results

```
✅ Fetched 113 events from Kwiff WebSocket
✅ Saved events to data directory
✅ Auto-mapped 1 new event to Betfair
✅ 309 total event mappings available
✅ ALL TESTS PASSED
```

---

## 🚀 Quick Start

### 1. Import and Initialize (Recommended)

Add to your main script (e.g., `virgin_goose.py`):

```python
from kwiff import initialize_kwiff_sync

def main():
    # ... existing initialization code ...
    
    # Initialize Kwiff integration
    print("\n[INIT] Initializing Kwiff integration...")
    try:
        kwiff_result = initialize_kwiff_sync(country="GB", dry_run=False)
        if kwiff_result['overall_success']:
            print("[INIT] ✅ Kwiff integration ready")
    except Exception as e:
        print(f"[INIT] ⚠️ Kwiff initialization failed: {e}")
    
    # Continue with main loop...
```

This will:
1. Fetch featured matches from Kwiff via WebSocket
2. Save them to `kwiff/server/data/events_YYYYMMDD.json`
3. Auto-map them to Betfair market IDs
4. Store mappings in `kwiff/server/event_mappings.json`

### 2. Look Up Mappings

```python
from kwiff import get_betfair_id_for_kwiff_event, get_kwiff_event_mappings

# Get Betfair ID for a Kwiff event
betfair_id = get_betfair_id_for_kwiff_event("10748848")
print(f"Betfair Market ID: {betfair_id}")

# Get all mappings
mappings = get_kwiff_event_mappings()
print(f"Total mappings: {len(mappings)}")
```

### 3. Check if Match is on Kwiff

```python
def check_kwiff_availability(betfair_market_id):
    """Check if a Betfair match has Kwiff odds available."""
    from kwiff import get_kwiff_event_mappings
    
    mappings = get_kwiff_event_mappings()
    
    for kwiff_id, data in mappings.items():
        if data.get('betfair_id') == str(betfair_market_id):
            return kwiff_id
    
    return None

# Usage in main loop:
for match in matches:
    mid = match.get('id')
    kwiff_id = check_kwiff_availability(mid)
    if kwiff_id:
        print(f"[KWIFF] Match available on Kwiff (ID: {kwiff_id})")
```

---

## 📦 Module Structure

```
kwiff/
├── __init__.py              # Main exports
├── integration.py           # Integration module (NEW)
├── kwiff_client.py          # WebSocket client
├── kwiff_cli.py             # CLI tool
├── README.md                # This file
├── requirements.txt
└── server/
    ├── auto_map_events.py   # Event mapping script
    ├── data/
    │   └── events_YYYYMMDD.json  # Daily event cache
    └── event_mappings.json  # Kwiff → Betfair mappings
```

---

## 🛠️ API Reference

### `initialize_kwiff_sync(country="GB", dry_run=False)`

Complete initialization function for non-async code.

**Parameters:**
- `country` (str): Country code (default: "GB")
- `dry_run` (bool): If True, shows mappings without saving

**Returns:**
```python
{
    'fetch_success': bool,      # Events fetched successfully
    'mapping_success': bool,    # Events mapped successfully
    'overall_success': bool     # Both operations succeeded
}
```

**Example:**
```python
result = initialize_kwiff_sync(country="GB", dry_run=False)
if result['overall_success']:
    print("Kwiff ready!")
```

---

### `initialize_kwiff(country="GB", dry_run=False)`

Async version of initialization (for async code).

**Example:**
```python
async def main():
    result = await initialize_kwiff(country="GB")
    print(f"Success: {result['overall_success']}")
```

---

### `fetch_and_save_events(country="GB", identifier=None)`

Fetch events from Kwiff and save to data directory.

**Parameters:**
- `country` (str): Country code
- `identifier` (str, optional): Custom UUID for WebSocket

**Returns:** `bool` - Success status

**Example:**
```python
async def refresh_kwiff():
    success = await fetch_and_save_events(country="GB")
    print(f"Fetched: {success}")
```

---

### `map_kwiff_events(dry_run=False)`

Map Kwiff events to Betfair using Oddsmatcha API.

**Parameters:**
- `dry_run` (bool): Preview without saving

**Returns:** `bool` - Success status

**Example:**
```python
# Map without saving (preview)
map_kwiff_events(dry_run=True)

# Map and save
map_kwiff_events(dry_run=False)
```

---

### `get_kwiff_event_mappings()`

Get all Kwiff→Betfair event mappings.

**Returns:** `dict` - Mappings dictionary

**Example:**
```python
mappings = get_kwiff_event_mappings()
# Returns:
# {
#     "10748848": {
#         "betfair_id": "35049415",
#         "description": "Bodoe/Glimt vs Man City - UEFA Champions League",
#         "oddsmatcha_id": "3787",
#         "smarkets_id": "44762368"
#     },
#     ...
# }
```

---

### `get_betfair_id_for_kwiff_event(kwiff_event_id)`

Look up Betfair market ID for a Kwiff event.

**Parameters:**
- `kwiff_event_id` (str): Kwiff event ID

**Returns:** `str | None` - Betfair market ID or None

**Example:**
```python
betfair_id = get_betfair_id_for_kwiff_event("10748848")
if betfair_id:
    print(f"Betfair ID: {betfair_id}")
```

---

## 🧪 Testing

### Run All Tests

```bash
# Dry-run (don't save mappings)
python test_kwiff_integration.py --dry-run

# Save mappings
python test_kwiff_integration.py --save

# Only test fetching
python test_kwiff_integration.py --fetch-only
```

### Test Individual Components

```bash
# Test integration module directly
cd kwiff
python integration.py --dry-run

# Test WebSocket client
python kwiff_client.py

# Test auto-mapping
cd server
python auto_map_events.py --dry-run
```

---

## 📊 Data Flow

```
1. Kwiff WebSocket
   ↓ (fetch_and_save_events)
2. kwiff/server/data/events_YYYYMMDD.json
   ↓ (map_kwiff_events)
3. Oddsmatcha API (for Betfair/Smarkets IDs)
   ↓
4. kwiff/server/event_mappings.json
   ↓ (get_betfair_id_for_kwiff_event)
5. Your application
```

---

## 🔧 Configuration

### Environment Variables

Add to `.env`:

```bash
# Kwiff Integration
ENABLE_KWIFF=1                    # Enable/disable Kwiff
KWIFF_COUNTRY=GB                  # Country code
KWIFF_REFRESH_MINUTES=60          # Refresh interval
```

### In Your Script

```python
ENABLE_KWIFF = os.getenv("ENABLE_KWIFF", "1") == "1"
KWIFF_COUNTRY = os.getenv("KWIFF_COUNTRY", "GB")
KWIFF_REFRESH_MINUTES = int(os.getenv("KWIFF_REFRESH_MINUTES", "60"))

if ENABLE_KWIFF:
    initialize_kwiff_sync(country=KWIFF_COUNTRY)
```

---

## 🎯 Next Steps (Future Enhancement)

The integration is ready for the next phase: **requesting specific odds via WebSocket**.

### Future: Request Player Odds

When you find an AGS lay, two_or_more, or hat-trick opportunity:

```python
async def get_kwiff_player_odds(kwiff_event_id, player_name, market_type):
    """
    Request player odds from Kwiff WebSocket.
    
    TODO: Determine the correct WebSocket command format.
    """
    from kwiff import KwiffClient
    
    async with KwiffClient() as client:
        # TODO: Implement command to request player odds
        # response = await client.send_command(
        #     message="player:odds",  # or similar
        #     payload={
        #         "eventId": kwiff_event_id,
        #         "playerName": player_name,
        #         "marketType": market_type  # AGS, TOM, HAT
        #     }
        # )
        # return response
        pass
```

### Markets to Target

Based on goosealerts needs:
- **AGS** (Anytime Goalscorer) - when lay is available
- **TOM** (Two or More goals) - player scoring 2+
- **HAT** (Hat-trick) - player scoring 3+

---

## ❓ Troubleshooting

### Events Not Fetching

```python
# Check WebSocket connection
from kwiff import KwiffClient
import asyncio

async def test():
    async with KwiffClient() as client:
        print("Connected!")
        events = await client.get_football_events()
        print(f"Events: {len(events) if events else 0}")

asyncio.run(test())
```

### Mappings Not Saving

```python
# Check if dry-run is enabled
initialize_kwiff_sync(dry_run=False)  # Make sure this is False

# Check permissions
import os
mapping_file = "kwiff/server/event_mappings.json"
print(f"Writable: {os.access(mapping_file, os.W_OK)}")
```

### No Matches Found

The auto-mapper uses Oddsmatcha API to find Betfair IDs. If matches aren't found:
- Oddsmatcha might not have the match yet
- Team names might not match exactly
- Try running again closer to kickoff

---

## 📚 Related Files

- **Example Integration**: `kwiff_integration_example.py`
- **Test Suite**: `test_kwiff_integration.py`
- **WebSocket Client**: `kwiff/kwiff_client.py`
- **CLI Tool**: `kwiff/kwiff_cli.py`
- **Auto-Mapper**: `kwiff/server/auto_map_events.py`

---

## ✅ Summary

The Kwiff module is now fully integrated and ready to use:

1. ✅ **Fetches** featured matches from Kwiff WebSocket
2. ✅ **Maps** them to Betfair market IDs automatically
3. ✅ **Provides** easy lookup functions
4. ✅ **Works** on startup with one function call
5. ✅ **Tested** and verified with 113 events

Next phase: Request specific player odds when opportunities are found!
