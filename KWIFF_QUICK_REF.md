# Kwiff Integration - Quick Reference

## 🚀 One-Line Startup Integration

```python
from kwiff import initialize_kwiff_sync
result = initialize_kwiff_sync(country="GB", dry_run=False)
```

## 📦 Main Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `initialize_kwiff_sync()` | Fetch & map on startup | `initialize_kwiff_sync(country="GB")` |
| `get_betfair_id_for_kwiff_event()` | Lookup Betfair ID | `get_betfair_id_for_kwiff_event("10748848")` |
| `get_kwiff_event_mappings()` | Get all mappings | `mappings = get_kwiff_event_mappings()` |
| `fetch_and_save_events()` | Fetch from WebSocket | `await fetch_and_save_events()` |
| `map_kwiff_events()` | Map to Betfair | `map_kwiff_events(dry_run=False)` |

## 🔍 Common Use Cases

### 1. Initialize on Startup (virgin_goose.py)

```python
def main():
    betfair = Betfair()
    
    # Initialize Kwiff
    from kwiff import initialize_kwiff_sync
    kwiff_result = initialize_kwiff_sync(country="GB")
    
    if kwiff_result['overall_success']:
        print("[KWIFF] ✅ Ready")
    
    # Continue with main loop...
```

### 2. Check if Match is on Kwiff

```python
def is_kwiff_available(betfair_market_id):
    from kwiff import get_kwiff_event_mappings
    
    mappings = get_kwiff_event_mappings()
    for kwiff_id, data in mappings.items():
        if data.get('betfair_id') == str(betfair_market_id):
            return kwiff_id
    return None
```

### 3. Get Kwiff ID for Betfair Match

```python
kwiff_id = is_kwiff_available(match_id)
if kwiff_id:
    print(f"[KWIFF] Match available (ID: {kwiff_id})")
    # TODO: Request odds from Kwiff WebSocket
```

## 🧪 Testing Commands

```bash
# Test full integration (dry-run)
python test_kwiff_integration.py --dry-run

# Test and save mappings
python test_kwiff_integration.py --save

# Test fetch only
python test_kwiff_integration.py --fetch-only
```

## 📂 File Locations

```
kwiff/
├── integration.py                    # Main integration module
├── kwiff_client.py                   # WebSocket client
└── server/
    ├── data/events_YYYYMMDD.json    # Fetched events
    └── event_mappings.json          # Kwiff → Betfair mappings
```

## 🎯 What Works Now

✅ Fetch 113+ events from Kwiff WebSocket  
✅ Auto-map to Betfair market IDs  
✅ Lookup Betfair IDs for Kwiff events  
✅ Runs on startup automatically  
✅ 309 events currently mapped  

## 🔜 Next Phase

Request specific player odds when opportunities found:
- AGS (Anytime Goalscorer) lay available
- Two or More goals
- Hat-trick

**TODO:** Determine WebSocket command format for player odds

---

📖 **Full Documentation:** `KWIFF_INTEGRATION_GUIDE.md`  
💡 **Example Code:** `kwiff_integration_example.py`  
🧪 **Test Suite:** `test_kwiff_integration.py`
