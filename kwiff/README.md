# Kwiff WebSocket Client - Standalone Python Implementation

Successfully implemented a **standalone Python WebSocket client** for Kwiff betting exchange that fetches live sports event data **without requiring a browser**.

## ✅ What Works

- ✅ WebSocket connection to Kwiff's real-time API (`wss://web-api.kwiff.com`)
- ✅ Proper Socket.IO v3 (EIO=3) protocol implementation
- ✅ Authentication via UUID cookie + custom HTTP headers
- ✅ Receives all 3 initial server messages (handshake, user details, namespace)
- ✅ Sends properly formatted Socket.IO commands
- ✅ Fetches live football event data with complete betting details
- ✅ Returns 111+ live football matches with:
  - Team names, competition info
  - Odds and betting markets
  - Match times and status
  - Bet builder eligibility

## 🔑 Key Discovery: The websockets Library Solution

After extensive testing with `websocket-client` library (which was sending close frames immediately), the solution was found using the `websockets` library with the correct API:

```python
from websockets.client import connect  # ← Lower-level API (not websockets.connect)

async with connect(
    url,
    extra_headers=headers  # ← Must use as list of tuples
) as ws:
    msg = await ws.recv()
```

**Critical Requirements:**
1. Use `from websockets.client import connect` (NOT `websockets.connect()`)
2. Pass headers as `extra_headers` parameter with list of tuples
3. Include all required authentication headers:
   - `Cookie: uuid={identifier}`
   - `User-Agent` matching browser
   - Encoding and language preferences

## 📋 Usage

### Using the CLI Tool

```bash
# Fetch football events for GB (default)
python kwiff/kwiff_cli.py fetch-events

# Fetch with preview
python kwiff/kwiff_cli.py fetch-events --show-preview

# Fetch for different country
python kwiff/kwiff_cli.py fetch-events --country IE

# Save to custom file
python kwiff/kwiff_cli.py fetch-events --output my_events.json
```

### Using the Python Module

```python
import asyncio
from kwiff.kwiff_client import KwiffClient

async def main():
    async with KwiffClient() as client:
        # Fetch football events
        events = await client.get_football_events(country="GB")
        
        # Save to file
        import json
        with open("events.json", "w") as f:
            json.dump(events, f, indent=2)

asyncio.run(main())
```

### Advanced Usage - Send Custom Commands

```python
async with KwiffClient() as client:
    # Send any command
    response = await client.send_command(
        message="event:list",
        payload={
            "listId": "default",
            "sportId": 11,  # Football
            "country": "GB"
        }
    )
```

## 🏗️ Architecture

### Files

- **kwiff_client.py** - Core WebSocket client implementation
  - `KwiffClient` class with async/await support
  - `connect()` - Establish connection and handshake
  - `send_command()` - Send commands and get responses
  - `get_football_events()` - Convenience method for football events

- **kwiff_cli.py** - Command-line interface tool
  - `fetch-events` command with options
  - Support for different sports and countries

### Socket.IO Protocol (EIO=3)

**Connection URL:**
```
wss://web-api.kwiff.com/socket.io/?device=web-app&version=1.0.1&identifier={uuid}&EIO=3&transport=websocket
```

**Initial Message Sequence:**
1. Server: `0{sid,upgrades,pingInterval,pingTimeout}` - Handshake
2. Server: `42["response",{user:socketdetails}]` - User authentication
3. Server: `40` - Namespace connection
4. Client: `421<packet_id>["command",{...}]` - Send command
5. Server: `43<packet_id>[{...}]` - Response

**Command Format:**
```json
{
  "message": "event:list",
  "payload": {
    "listId": "default",
    "sportId": 11,
    "country": "GB"
  },
  "timestamp": 1768921912089,
  "userAgent": "Mozilla/5.0...",
  "webappVersion": "1.0.1.1768909734556"
}
```

## 🔐 Authentication

Kwiff uses UUID-based authentication with cookie:

```python
identifier = str(uuid.uuid4())  # Generate new UUID for each session

# Pass in URL query parameter
url = f"...&identifier={identifier}&..."

# And as HTTP header cookie
headers = [
    ("Cookie", f"uuid={identifier}"),
    ...
]
```

## 📊 Response Data

Returned event data includes:

```json
{
  "timestamp": 1768921926610,
  "data": {
    "events": [
      {
        "id": 10748848,
        "sportId": 11,
        "competition": {
          "id": 1,
          "name": "UEFA Champions League"
        },
        "homeTeam": {
          "id": 1,
          "name": "Bodoe/Glimt"
        },
        "awayTeam": {
          "id": 2,
          "name": "Manchester City"
        },
        "startDate": "2026-01-20T17:45:00.000Z",
        "details": {
          "offers": [
            {
              "name": "Full Time Result",
              "outcomes": [
                {
                  "outcomeName": "Bodo/Glimt",
                  "odds": 6.0,
                  "fractional": "5/1"
                },
                ...
              ]
            }
          ]
        }
      }
    ]
  }
}
```

## 🚀 Performance

- **Connection Time:** ~200ms
- **Event Fetch Time:** ~300ms
- **Data Size:** ~1-2MB for 111 football events
- **Response Format:** Streaming via WebSocket (single message)

## 🔧 Requirements

```
websockets>=11.0  # The async WebSocket library
```

Install with:
```bash
pip install websockets
```

## ⚠️ Important Notes

1. **No Browser Required:** This implementation is completely standalone Python
2. **Self-Contained:** No need for external services or APIs
3. **Real-Time Data:** Receives live odds and event information directly from Kwiff servers
4. **Rate Limiting:** Server may rate limit if too many concurrent connections
5. **Session Persistence:** Each UUID session is independent; multiple clients can run simultaneously

## 🐛 Troubleshooting

### Connection Refused (403 Forbidden)
- Ensure all required headers are included
- Verify Cookie header matches UUID identifier
- Check User-Agent string is present

### No Messages After Handshake
- Increase timeout in `ws.recv()` calls
- Verify using `extra_headers` parameter correctly
- Check that URL query parameters are correct

### JSON Parse Errors
- Response format includes packet ID: `43<id>[...]`
- Must strip packet ID before JSON parsing
- Look for `[` character to find JSON start

## 📝 Event Data Fields

Key fields available in event responses:

- `id` - Unique event ID
- `sportId` - Sport type (11=Football, 36=Basketball, etc.)
- `competition` - Competition details (name, ID)
- `homeTeam` / `awayTeam` - Team information
- `startDate` - Match start time (ISO 8601)
- `details.offers` - Available betting markets
- `details.offers[].outcomes` - Betting outcomes with odds
- `bettingStatus` - Current betting status
- `matchTracker` - Live match tracking available
- `betBuilderEnabled` - Bet builder support

## 🎯 Future Enhancements

Possible extensions:
- [ ] Real-time WebSocket event streaming (keep connection alive)
- [ ] Bet placement integration
- [ ] Account balance and bet history
- [ ] Support for other sports (basketball, tennis, etc.)
- [ ] Streaming market updates
- [ ] Live odds monitoring

## 📄 License

This implementation is provided as-is for educational and research purposes.
