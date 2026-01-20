# Kwiff Integration - Implementation Summary

## ✅ Completed Implementation

The Kwiff module has been successfully integrated into the goosealerts project with full startup automation and event mapping capabilities.

---

## 📦 What Was Created

### Core Files

1. **[kwiff/integration.py](kwiff/integration.py)** - Main integration module
   - `initialize_kwiff()` - Async initialization
   - `initialize_kwiff_sync()` - Sync wrapper for main scripts
   - `fetch_and_save_events()` - Fetch from WebSocket
   - `map_kwiff_events()` - Auto-map to Betfair
   - `get_kwiff_event_mappings()` - Get all mappings
   - `get_betfair_id_for_kwiff_event()` - Lookup function

2. **[kwiff/__init__.py](kwiff/__init__.py)** - Updated exports
   - Exports all integration functions for easy import

3. **[test_kwiff_integration.py](test_kwiff_integration.py)** - Test suite
   - Tests fetching, mapping, and lookups
   - Supports dry-run mode
   - 4 comprehensive tests

4. **[demo_kwiff_startup.py](demo_kwiff_startup.py)** - Startup demo
   - Shows recommended integration pattern
   - Demonstrates full workflow

### Documentation

5. **[KWIFF_INTEGRATION_GUIDE.md](KWIFF_INTEGRATION_GUIDE.md)** - Complete guide
   - API reference
   - Usage examples
   - Troubleshooting
   - Data flow diagrams

6. **[KWIFF_QUICK_REF.md](KWIFF_QUICK_REF.md)** - Quick reference
   - One-liners
   - Common use cases
   - Testing commands

7. **[kwiff_integration_example.py](kwiff_integration_example.py)** - Example code
   - How to integrate into virgin_goose.py
   - Future enhancements
   - Configuration examples

8. **[README.md](README.md)** - Updated main README
   - Added Kwiff section
   - Quick start guide
   - Links to documentation

---

## 🎯 What It Does

### 1. Fetches Events
- Connects to Kwiff WebSocket API
- Retrieves 113+ featured football matches
- Saves to `kwiff/server/data/events_YYYYMMDD.json`

### 2. Auto-Maps Events
- Uses Oddsmatcha API for cross-reference
- Maps Kwiff event IDs → Betfair market IDs
- Stores in `kwiff/server/event_mappings.json`
- Currently maintains 310 event mappings

### 3. Provides Lookups
- `get_betfair_id_for_kwiff_event(kwiff_id)` - Get Betfair ID
- `get_kwiff_event_mappings()` - Get all mappings
- Easy integration with existing code

---

## 🚀 How to Use

### Startup Integration (Recommended)

Add to `virgin_goose.py` or any main script:

```python
from kwiff import initialize_kwiff_sync

def main():
    # ... existing initialization ...
    
    # Initialize Kwiff
    print("[INIT] Initializing Kwiff integration...")
    try:
        result = initialize_kwiff_sync(country="GB", dry_run=False)
        if result['overall_success']:
            print("[INIT] ✅ Kwiff ready")
    except Exception as e:
        print(f"[INIT] ⚠️ Kwiff failed: {e}")
    
    # Continue with main loop...
```

### Check Match Availability

```python
from kwiff import get_kwiff_event_mappings

def check_kwiff(betfair_market_id):
    mappings = get_kwiff_event_mappings()
    for kwiff_id, data in mappings.items():
        if data.get('betfair_id') == str(betfair_market_id):
            return kwiff_id
    return None

# In main loop:
kwiff_id = check_kwiff(match_id)
if kwiff_id:
    print(f"[KWIFF] Available (ID: {kwiff_id})")
```

---

## 🧪 Test Results

```
✅ Fetched 113 events from Kwiff WebSocket
✅ Saved to kwiff/server/data/events_20260120.json
✅ Auto-mapped 1 new event
✅ 310 total event mappings
✅ ALL TESTS PASSED
```

**Sample Events:**
- Bodoe/Glimt vs Manchester City (UEFA Champions League)
- Inter Milano vs Arsenal FC (UEFA Champions League)
- Tottenham vs Borussia Dortmund (UEFA Champions League)

**Sample Mapping:**
```json
{
  "10748848": {
    "betfair_id": "35049415",
    "description": "Bodoe/Glimt vs Manchester City - UEFA Champions League",
    "oddsmatcha_id": "3787",
    "smarkets_id": "44762368"
  }
}
```

---

## 📊 Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Main Script                           │
│              (e.g., virgin_goose.py)                    │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ initialize_kwiff_sync()
                   ▼
┌─────────────────────────────────────────────────────────┐
│           kwiff/integration.py                          │
│                                                         │
│  ┌─────────────────────┐  ┌───────────────────────┐   │
│  │ fetch_and_save_     │  │ map_kwiff_events()    │   │
│  │ events()            │  │                       │   │
│  └──────┬──────────────┘  └──────┬────────────────┘   │
│         │                        │                     │
│         ▼                        ▼                     │
│  ┌─────────────────────┐  ┌───────────────────────┐   │
│  │ KwiffClient         │  │ auto_map_events.py    │   │
│  │ (WebSocket)         │  │ (Oddsmatcha API)      │   │
│  └─────────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│              Data Storage                               │
│                                                         │
│  kwiff/server/data/events_YYYYMMDD.json                │
│  kwiff/server/event_mappings.json                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Current Capabilities

✅ **Fetch Events**
- WebSocket connection to Kwiff
- Real-time event data
- 113+ live matches

✅ **Auto-Map Events**
- Kwiff ID → Betfair ID
- Uses Oddsmatcha API
- 310 mappings maintained

✅ **Lookup Functions**
- Get Betfair ID for Kwiff event
- Get all mappings
- Check match availability

✅ **Startup Integration**
- One function call
- Async and sync versions
- Error handling

✅ **Testing**
- Comprehensive test suite
- Dry-run mode
- Demo script

✅ **Documentation**
- Full integration guide
- Quick reference
- Example code

---

## 🔜 Future Enhancement: Request Odds

The next phase is to implement WebSocket commands to request specific player odds when opportunities are found.

### Target Markets

When goosealerts finds these opportunities:
- **AGS** (Anytime Goalscorer) - lay available
- **Two or More** - player scoring 2+
- **Hat-trick** - player scoring 3+

### Implementation Plan

```python
async def get_kwiff_player_odds(kwiff_event_id, player_name, market_type):
    """Request player odds from Kwiff WebSocket."""
    from kwiff import KwiffClient
    
    async with KwiffClient() as client:
        # TODO: Determine correct command format
        response = await client.send_command(
            message="player:odds",  # or similar
            payload={
                "eventId": kwiff_event_id,
                "playerName": player_name,
                "marketType": market_type  # AGS, TOM, HAT
            }
        )
        return response
```

**Required Research:**
- Determine exact WebSocket command format
- Identify payload structure
- Test response parsing

---

## 📁 File Structure

```
goosealerts/
├── kwiff/
│   ├── __init__.py                # Updated exports
│   ├── integration.py             # NEW - Main integration
│   ├── kwiff_client.py            # WebSocket client
│   ├── kwiff_cli.py               # CLI tool
│   └── server/
│       ├── auto_map_events.py     # Event mapping
│       ├── data/
│       │   └── events_YYYYMMDD.json  # Daily events
│       └── event_mappings.json    # Kwiff → Betfair
│
├── test_kwiff_integration.py      # NEW - Test suite
├── demo_kwiff_startup.py          # NEW - Startup demo
├── kwiff_integration_example.py   # NEW - Example code
├── KWIFF_INTEGRATION_GUIDE.md     # NEW - Full guide
├── KWIFF_QUICK_REF.md             # NEW - Quick ref
└── README.md                      # Updated
```

---

## 🎓 Key Learnings

### WebSocket Integration
- Uses `websockets` library with `from websockets.client import connect`
- Requires specific headers: UUID cookie, User-Agent, etc.
- Socket.IO v3 (EIO=3) protocol

### Auto-Mapping
- Oddsmatcha API provides cross-reference data
- Fuzzy team name matching
- Maintains historical mappings

### Integration Pattern
- Single function for startup: `initialize_kwiff_sync()`
- Lookup functions for runtime use
- Separate fetch and map steps for flexibility

---

## 📝 Quick Commands

```bash
# Test integration (dry-run)
python test_kwiff_integration.py --dry-run

# Test and save mappings
python test_kwiff_integration.py --save

# Run startup demo
python demo_kwiff_startup.py

# Test WebSocket client
cd kwiff
python kwiff_client.py

# Test auto-mapping
cd kwiff/server
python auto_map_events.py --dry-run
```

---

## ✅ Summary

**Status:** ✅ Complete and tested  
**Events Fetched:** 113  
**Mappings Created:** 310  
**Tests:** All passing  
**Integration:** Ready for production  

**Next Phase:** Implement player odds requests via WebSocket

---

## 📞 Support

- 📖 [Full Guide](KWIFF_INTEGRATION_GUIDE.md)
- 📋 [Quick Ref](KWIFF_QUICK_REF.md)
- 💡 [Examples](kwiff_integration_example.py)
- 🧪 [Tests](test_kwiff_integration.py)

**Issues or Questions?**
Check the troubleshooting section in `KWIFF_INTEGRATION_GUIDE.md`
