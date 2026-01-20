# goosealerts

Initial commit — linked to https://github.com/mcqweb/goosealerts.git

## Modules

### Core Modules
- **virgin_goose.py** - Main alert system for Virgin Bet, OddsChecker, William Hill
- **whale.py** - Liquidity monitoring bot
- **betfair.py** - Betfair API integration
- **oc.py** - OddsChecker scraper

### New: Kwiff Integration ✨

The Kwiff module provides WebSocket-based integration with Kwiff betting exchange:

- ✅ Fetch featured matches from Kwiff WebSocket
- ✅ Auto-map Kwiff event IDs to Betfair market IDs  
- ✅ Startup integration (one function call)
- ✅ Event lookup functions

**Quick Start:**
```python
from kwiff import initialize_kwiff_sync

# On startup:
result = initialize_kwiff_sync(country="GB")
if result['overall_success']:
    print("Kwiff ready!")
```

**Documentation:**
- 📖 [Full Integration Guide](KWIFF_INTEGRATION_GUIDE.md)
- 📋 [Quick Reference](KWIFF_QUICK_REF.md)
- 💡 [Example Code](kwiff_integration_example.py)
- 🧪 [Test Suite](test_kwiff_integration.py)

**Test:**
```bash
python test_kwiff_integration.py --dry-run
```
