# NordVPN Proxy Setup Guide

## Overview

This project supports routing all William Hill API requests through NordVPN proxies. NordVPN credentials are configured separately from standard HTTP/HTTPS proxies for convenience.

## Configuration Format

The system builds proxy URLs in this format:

```python
PROXIES = {
    'http': f'http://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
    'https': f'https://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
}
```

## Quick Setup

### Method 1: .env File (Recommended)

1. Copy the example file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your NordVPN credentials:
   ```env
   # NordVPN Proxy Configuration
   NORD_USER=your_email@example.com
   NORD_PWD=your_nordvpn_password
   NORD_LOCATION=us5678
   ```

3. Run your script - proxies are automatically configured:
   ```bash
   python generate_combos.py OB_EV37926026 --stats
   ```

### Method 2: Environment Variables

Set NordVPN credentials as environment variables:

**Windows PowerShell:**
```powershell
$env:NORD_USER="your_email@example.com"
$env:NORD_PWD="your_nordvpn_password"
$env:NORD_LOCATION="us5678"
```

**Windows CMD:**
```cmd
set NORD_USER=your_email@example.com
set NORD_PWD=your_nordvpn_password
set NORD_LOCATION=us5678
```

**Linux/Mac:**
```bash
export NORD_USER="your_email@example.com"
export NORD_PWD="your_nordvpn_password"
export NORD_LOCATION="us5678"
```

### Method 3: JSON Configuration

Create a `nordvpn.json` file:

```json
{
  "session_cookie": "your_williamhill_session",
  "nord_user": "your_email@example.com",
  "nord_pwd": "your_nordvpn_password",
  "nord_location": "us5678"
}
```

Load it when running:
```bash
python generate_combos.py --config nordvpn.json OB_EV37926026 --stats
```

### Method 4: Command-Line Arguments

Pass NordVPN credentials directly:

```bash
python generate_combos.py OB_EV37926026 ^
  --nord-user "your_email@example.com" ^
  --nord-pwd "your_nordvpn_password" ^
  --nord-location "us5678" ^
  --player "Joshua Zirkzee" ^
  --team "Man Utd" ^
  --get-price
```

### Method 5: Programmatic (In Code)

```python
from config import Config

# Set NordVPN credentials
Config.NORD_USER = "your_email@example.com"
Config.NORD_PWD = "your_nordvpn_password"
Config.NORD_LOCATION = "us5678"

# Proxies are now configured
proxies = Config.get_proxies()
print(proxies)
# {'http': 'http://user:pwd@us5678.nordvpn.com:89', 'https': '...'}
```

## NordVPN Server Locations

### Format

The `NORD_LOCATION` format is: `{country_code}{server_number}`

Examples:
- `us5678` - USA server #5678
- `uk4532` - UK server #4532
- `ca1234` - Canada server #1234
- `au9876` - Australia server #9876

### Finding Server Locations

**Method 1: NordVPN App**
1. Open NordVPN desktop app
2. Browse server list
3. Note the server number (e.g., "United States #5678")
4. Use: `NORD_LOCATION=us5678`

**Method 2: NordVPN Website**
1. Visit https://nordvpn.com/servers/tools/
2. Select your desired country
3. Choose a server from the list
4. Format as: `{country}{number}`

**Method 3: API Lookup**
```python
# Use NordVPN's server API
import requests

response = requests.get("https://api.nordvpn.com/v1/servers")
servers = response.json()

# Filter by country
us_servers = [s for s in servers if s['locations'][0]['country']['code'] == 'US']
print(f"US Servers: {len(us_servers)}")

# Example: Use first US server
server_id = us_servers[0]['id']
print(f"Use: NORD_LOCATION=us{server_id}")
```

### Common Country Codes

| Country | Code | Example |
|---------|------|---------|
| United States | `us` | `us5678` |
| United Kingdom | `uk` | `uk4532` |
| Canada | `ca` | `ca1234` |
| Australia | `au` | `au9876` |
| Germany | `de` | `de3456` |
| France | `fr` | `fr2345` |
| Netherlands | `nl` | `nl6789` |
| Japan | `jp` | `jp4567` |
| Singapore | `sg` | `sg8901` |
| Brazil | `br` | `br5432` |

## Configuration Priority

If both NordVPN and standard proxy settings are configured, **NordVPN takes priority**:

1. **NordVPN credentials** (if all three: NORD_USER, NORD_PWD, NORD_LOCATION)
2. HTTP_PROXY / HTTPS_PROXY (if NordVPN not set)
3. No proxy (if neither configured)

Example:
```env
# Both configured - NordVPN will be used
HTTP_PROXY=http://localhost:8080
NORD_USER=user@example.com
NORD_PWD=password
NORD_LOCATION=us5678
```

## Credentials

### Getting Your NordVPN Credentials

1. **Login to NordVPN Dashboard:**
   - Go to https://my.nordaccount.com/
   - Sign in with your NordVPN account

2. **Generate Service Credentials:**
   - Navigate to "Services" → "NordVPN"
   - Click "Set up NordVPN manually"
   - Under "Service credentials", click "Generate new credentials"
   - Copy the username (email) and password

3. **Use These Credentials:**
   - `NORD_USER` = The service username (usually your email)
   - `NORD_PWD` = The generated password (NOT your account password)
   - `NORD_LOCATION` = Your chosen server (e.g., `us5678`)

### Security Best Practices

**Never commit credentials to git:**

```gitignore
.env
*.secret
nordvpn.json
```

**Use environment-specific configs:**

- `.env.dev` - Development (maybe no proxy)
- `.env.prod` - Production (with NordVPN)

```bash
# Development
python generate_combos.py OB_EV37926026 --stats

# Production with NordVPN
# (Load .env.prod manually or use config file)
python generate_combos.py --config prod.json OB_EV37926026 --stats
```

**Rotate credentials periodically:**

Regenerate service credentials every 90 days for security.

## Testing Configuration

### Verify Credentials Are Loaded

```bash
python -c "from config import Config; print('User:', Config.NORD_USER); print('Location:', Config.NORD_LOCATION)"
```

Expected output:
```
User: your_email@example.com
Location: us5678
```

### Verify Proxy URLs Are Built Correctly

```bash
python -c "from config import Config; print('Proxies:', Config.get_proxies())"
```

Expected output:
```
Proxies: {'http': 'http://your_email@example.com:your_password@us5678.nordvpn.com:89', 'https': 'https://...'}
```

### Test Full Request

```bash
python generate_combos.py OB_EV37926026 --stats
```

Check that:
- No connection errors
- API requests succeed
- Data is fetched through NordVPN

### Test with Pricing API

```bash
python generate_combos.py OB_EV37926026 ^
  --player "Joshua Zirkzee" ^
  --team "Man Utd" ^
  --template "Anytime Goalscorer" ^
  --get-price
```

Should return live odds if NordVPN proxy is working.

## Troubleshooting

### Error: "Proxy connection failed"

**Cause:** Invalid credentials or server location

**Solution:**
1. Verify credentials at https://my.nordaccount.com/
2. Check server location format: `{country_code}{number}`
3. Try a different server location

```bash
# Test with different server
python -c "from config import Config; Config.NORD_LOCATION='us1234'; print(Config.get_proxies())"
```

### Error: "Authentication failed"

**Cause:** Wrong username or password

**Solution:**
1. Regenerate service credentials in NordVPN dashboard
2. Update `.env` with new credentials
3. Restart your script

```env
# Updated credentials
NORD_USER=new_email@example.com
NORD_PWD=new_generated_password
```

### Error: "Connection timeout"

**Cause:** NordVPN server may be slow or unavailable

**Solution:**
1. Increase timeout in `.env`:
   ```env
   API_TIMEOUT=60
   ```

2. Try a different server location:
   ```env
   NORD_LOCATION=us7890
   ```

### Error: Credentials not loading

**Cause:** `.env` file not found or not loaded

**Solution:**
1. Check `.env` exists in project root:
   ```bash
   dir .env
   ```

2. Verify file is read:
   ```bash
   python -c "from pathlib import Path; print('Exists:', (Path('.') / '.env').exists())"
   ```

3. Manually load if needed:
   ```python
   from dotenv import load_dotenv
   load_dotenv('.env')
   ```

### Proxy works but requests still fail

**Possible causes:**
- William Hill blocking NordVPN IPs
- Server location restricted for William Hill
- Session cookie expired

**Solutions:**
1. Try different server location (different country)
2. Update session cookie
3. Use residential NordVPN IPs if available

## Advanced Usage

### Rotating Servers

Rotate through multiple NordVPN servers:

```python
from config import Config
import random

servers = ['us5678', 'us7890', 'uk4532', 'ca1234']

for server in servers:
    Config.NORD_LOCATION = server
    print(f"Using server: {server}")
    
    # Make your requests
    # ...
```

### Using with Multiple Projects

Create a shared NordVPN config:

**shared_nordvpn.json:**
```json
{
  "nord_user": "your_email@example.com",
  "nord_pwd": "your_password",
  "nord_location": "us5678"
}
```

Use across projects:
```bash
python project1/generate_combos.py --config shared_nordvpn.json ...
python project2/script.py --config shared_nordvpn.json ...
```

### Programmatic Server Selection

```python
from config import Config
import requests

def get_fastest_server(country='us'):
    """Find fastest NordVPN server for a country"""
    response = requests.get("https://api.nordvpn.com/v1/servers/recommendations")
    servers = response.json()
    
    # Filter by country
    country_servers = [s for s in servers if s['locations'][0]['country']['code'].lower() == country]
    
    if country_servers:
        # Use first (fastest) server
        server_id = country_servers[0]['id']
        Config.NORD_LOCATION = f"{country}{server_id}"
        print(f"Selected: {Config.NORD_LOCATION}")
    
# Usage
get_fastest_server('us')
proxies = Config.get_proxies()
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "generate_combos.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  betbuilder:
    build: .
    environment:
      - WILLIAMHILL_SESSION=${WILLIAMHILL_SESSION}
      - NORD_USER=${NORD_USER}
      - NORD_PWD=${NORD_PWD}
      - NORD_LOCATION=${NORD_LOCATION}
    volumes:
      - ./cache:/app/cache
```

Run with:
```bash
# .env file in same directory
docker-compose up
```

## Performance Considerations

### Server Selection

- **Closer servers = Lower latency**: Choose servers geographically close to William Hill's servers (likely UK/EU)
- **Less loaded servers = Better speed**: Check NordVPN's server load before selecting

### Optimal Locations for William Hill

Recommended NordVPN server locations:

1. **UK servers** (`uk####`) - Closest to William Hill
2. **Netherlands** (`nl####`) - Good EU performance
3. **Germany** (`de####`) - Reliable EU option
4. **US East Coast** (`us####`) - If UK/EU blocked

### Timeout Settings

Adjust based on server performance:

```env
# For slower/distant servers
API_TIMEOUT=60

# For fast/local servers
API_TIMEOUT=30
```

## Examples

### Example 1: Basic Setup with NordVPN

**.env:**
```env
WILLIAMHILL_SESSION=YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5
NORD_USER=myemail@example.com
NORD_PWD=abc123xyz789
NORD_LOCATION=uk4532
```

**Run:**
```bash
python generate_combos.py OB_EV37926026 --stats
```

### Example 2: CLI Override

Override `.env` location from command line:

```bash
python generate_combos.py OB_EV37926026 ^
  --nord-location us7890 ^
  --player "Joshua Zirkzee" ^
  --team "Man Utd" ^
  --get-price
```

### Example 3: Multiple Environments

**.env.uk:**
```env
NORD_LOCATION=uk4532
```

**.env.us:**
```env
NORD_LOCATION=us5678
```

Load specific environment:
```python
from dotenv import load_dotenv
load_dotenv('.env.uk')  # or .env.us
```

### Example 4: Production Script

```python
from config import Config
from src.api_client import WilliamHillAPIClient

# Load NordVPN from .env
# (automatically loaded)

# Verify configuration
if not all([Config.NORD_USER, Config.NORD_PWD, Config.NORD_LOCATION]):
    raise ValueError("NordVPN credentials not configured!")

print(f"Using NordVPN server: {Config.NORD_LOCATION}")

# Create client (proxies automatically applied)
client = WilliamHillAPIClient()

# Make requests - now routed through NordVPN
markets = client.get_event_markets("OB_EV37926026")
```

## Support

### NordVPN Issues

Contact NordVPN support: https://support.nordvpn.com/

### Project Issues

Check:
1. `CONFIG_GUIDE.md` - General configuration
2. `MODULE_USAGE.md` - Module integration
3. `.env.example` - Configuration template
