# William Hill Bet Builder - Configuration Guide

## Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
copy .env.example .env
```

Edit `.env` with your settings:

```env
# Required: Your William Hill session cookie
WILLIAMHILL_SESSION=your_session_cookie_here

# Optional: Proxy settings (choose one method)
# Method 1: Standard proxy
HTTP_PROXY=http://localhost:8080
HTTPS_PROXY=https://localhost:8080

# Method 2: NordVPN (see NORDVPN_SETUP.md for details)
NORD_USER=your_email@example.com
NORD_PWD=your_nordvpn_password
NORD_LOCATION=us5678

# Optional: Cache and timeout settings
CACHE_EXPIRY_HOURS=24
API_TIMEOUT=30
```

### 3. Test Configuration

```bash
python -c "from config import Config; print('Session configured:', len(Config.SESSION_COOKIE) > 0)"
```

## Configuration Methods

### Method 1: .env File (Recommended)

Create a `.env` file in the project root:

```env
WILLIAMHILL_SESSION=YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5
HTTP_PROXY=http://user:pass@proxy.com:8080
HTTPS_PROXY=https://user:pass@proxy.com:8080

# Or use NordVPN instead (takes priority if set)
NORD_USER=your_email@example.com
NORD_PWD=your_nordvpn_password
NORD_LOCATION=us5678

CACHE_EXPIRY_HOURS=24
API_TIMEOUT=30
```

**Advantages:**
- Keeps secrets out of code
- Easy to manage different environments
- Automatically loaded at startup
- Gitignored by default

### Method 2: Environment Variables

Set system environment variables:

**Windows (PowerShell):**
```powershell
$env:WILLIAMHILL_SESSION="your_session_cookie"
$env:HTTP_PROXY="http://localhost:8080"
$env:HTTPS_PROXY="https://localhost:8080"
```

**Windows (CMD):**
```cmd
set WILLIAMHILL_SESSION=your_session_cookie
set HTTP_PROXY=http://localhost:8080
set HTTPS_PROXY=https://localhost:8080
```

**Linux/Mac:**
```bash
export WILLIAMHILL_SESSION="your_session_cookie"
export HTTP_PROXY="http://localhost:8080"
export HTTPS_PROXY="https://localhost:8080"
```

### Method 3: JSON Configuration File

Create a `config.json`:

```json
{
  "session_cookie": "your_session_cookie",
  "http_proxy": "http://localhost:8080",
  "https_proxy": "https://localhost:8080",
  "cache_expiry_hours": 24
}
```

Load it in your script:

```python
from config import Config

Config.load_from_file("config.json")
```

### Method 4: Programmatic Configuration

Set values directly in code:

```python
from config import Config

Config.set_session_cookie("your_session_cookie")
Config.set_proxy(
    http_proxy="http://localhost:8080",
    https_proxy="https://localhost:8080"
)
```

### Method 5: CLI Arguments

Pass configuration via command-line:

```bash
python generate_combos.py OB_EV37926026 \
  --session "your_session_cookie" \
  --http-proxy "http://localhost:8080" \
  --https-proxy "https://localhost:8080" \
  --player "Joshua Zirkzee" \
  --team "Man Utd" \
  --get-price
```

Or load a config file:

```bash
python generate_combos.py --config config.json OB_EV37926026 --stats
```

## Configuration Priority

Settings are loaded in this order (later overrides earlier):

1. Default values in `config.py`
2. `.env` file (if exists)
3. Environment variables
4. JSON config file (if loaded via `--config`)
5. CLI arguments (if provided)

## Configuration Options

### Required Settings

#### WILLIAMHILL_SESSION
Your William Hill session cookie for API authentication.

**How to get it:**
1. Open William Hill website in your browser
2. Log in to your account
3. Open Developer Tools (F12)
4. Go to Application/Storage → Cookies
5. Find the `SESSION` cookie value
6. Copy the entire value

**Example:**
```env
WILLIAMHILL_SESSION=YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5
```

### Optional Settings

#### HTTP_PROXY & HTTPS_PROXY
Route all API requests through a proxy server.

**Format:**
```
http://[username:password@]host:port
https://[username:password@]host:port
```

**Examples:**
```env
# No authentication
HTTP_PROXY=http://localhost:8080
HTTPS_PROXY=https://localhost:8080

# With authentication
HTTP_PROXY=http://user:pass@proxy.company.com:8080
HTTPS_PROXY=https://user:pass@proxy.company.com:8080

# SOCKS proxy
HTTP_PROXY=socks5://localhost:1080
```

**Use cases:**
- Hide your IP address
- Bypass rate limiting
- Monitor API traffic
- Route through corporate proxy
- Use rotating proxies

#### NORD_USER, NORD_PWD, NORD_LOCATION (NordVPN)
Route all API requests through NordVPN. These settings take **priority** over HTTP_PROXY/HTTPS_PROXY if configured.

**Format:**
```env
NORD_USER=your_email@example.com
NORD_PWD=your_service_password
NORD_LOCATION=us5678
```

**Location format:** `{country_code}{server_number}`
- `us5678` - USA server #5678
- `uk4532` - UK server #4532  
- `ca1234` - Canada server #1234

**See NORDVPN_SETUP.md for complete guide:**
- Getting service credentials
- Finding server locations
- Configuration examples
- Troubleshooting

**Automatic proxy URL generation:**
```python
# Automatically builds:
# http://user:pwd@us5678.nordvpn.com:89
# https://user:pwd@us5678.nordvpn.com:89
```

#### CACHE_EXPIRY_HOURS
How long to cache market data before refreshing.

**Default:** `24` hours

**Examples:**
```env
CACHE_EXPIRY_HOURS=24    # Cache for 1 day
CACHE_EXPIRY_HOURS=1     # Cache for 1 hour
CACHE_EXPIRY_HOURS=0     # Disable caching
```

#### API_TIMEOUT
Timeout for API requests in seconds.

**Default:** `30` seconds

**Examples:**
```env
API_TIMEOUT=30    # 30 seconds (default)
API_TIMEOUT=10    # 10 seconds (faster, may fail)
API_TIMEOUT=60    # 60 seconds (more reliable)
```

## Security Best Practices

### 1. Never Commit Secrets

Add to `.gitignore`:
```
.env
config.json
*.secret
```

### 2. Use Different Configs for Different Environments

**Development (.env.dev):**
```env
WILLIAMHILL_SESSION=dev_session_cookie
HTTP_PROXY=http://localhost:8888
API_TIMEOUT=60
```

**Production (.env.prod):**
```env
WILLIAMHILL_SESSION=prod_session_cookie
HTTP_PROXY=http://prod-proxy:8080
API_TIMEOUT=30
```

Load the appropriate file:
```python
from dotenv import load_dotenv

load_dotenv('.env.prod')  # or .env.dev
```

### 3. Rotate Session Cookies

Session cookies expire. Update your `.env` when you see authentication errors.

### 4. Secure Proxy Credentials

If using proxy with authentication, store credentials securely:

```env
PROXY_USER=myusername
PROXY_PASS=mypassword
HTTP_PROXY=http://${PROXY_USER}:${PROXY_PASS}@proxy.com:8080
```

## Example Configurations

### Local Development (No Proxy)

**.env:**
```env
WILLIAMHILL_SESSION=YTFmZGRkZjYtYThkZC00MGExLTlmYTQtYjgxMmYyMzA1NmY5
CACHE_EXPIRY_HOURS=1
API_TIMEOUT=60
```

### Production with Proxy

**.env:**
```env
WILLIAMHILL_SESSION=production_session_cookie_here
HTTP_PROXY=http://10.0.0.1:8080
HTTPS_PROXY=https://10.0.0.1:8080
CACHE_EXPIRY_HOURS=24
API_TIMEOUT=30
```

### Development with BurpSuite Proxy (Debugging)

**.env:**
```env
WILLIAMHILL_SESSION=dev_session_cookie
HTTP_PROXY=http://127.0.0.1:8080
HTTPS_PROXY=http://127.0.0.1:8080
API_TIMEOUT=120
```

### Corporate Network

**.env:**
```env
WILLIAMHILL_SESSION=session_cookie
HTTP_PROXY=http://username:password@proxy.company.com:8080
HTTPS_PROXY=https://username:password@proxy.company.com:8080
CACHE_EXPIRY_HOURS=24
API_TIMEOUT=45
```

## Troubleshooting

### Issue: "Failed to fetch pricing data"

**Solution:** Check your session cookie is valid
```bash
python -c "from config import Config; print('Session:', Config.SESSION_COOKIE[:20])"
```

Update if needed:
```env
WILLIAMHILL_SESSION=new_session_cookie_here
```

### Issue: "Connection timeout"

**Solution:** Increase timeout
```env
API_TIMEOUT=60
```

Or check proxy settings:
```bash
python -c "from config import Config; print('Proxies:', Config.get_proxies())"
```

### Issue: "Proxy authentication failed"

**Solution:** Check credentials in proxy URL
```env
HTTP_PROXY=http://correct_user:correct_pass@proxy:8080
```

### Issue: Changes not taking effect

**Solution:** Restart your Python process. `.env` is loaded once at startup.

### Issue: "ModuleNotFoundError: No module named 'dotenv'"

**Solution:** Install dependencies
```bash
pip install python-dotenv
```

Or:
```bash
pip install -r requirements.txt
```

## Advanced Usage

### Multiple Environments

Use different `.env` files:

```python
from dotenv import load_dotenv
import sys

env = sys.argv[1] if len(sys.argv) > 1 else 'dev'
load_dotenv(f'.env.{env}')

from config import Config
# Config now loaded from .env.dev, .env.prod, etc.
```

Run with:
```bash
python your_script.py prod
```

### Override Specific Values

Load `.env` then override:

```python
from config import Config

# .env loaded automatically
# Now override specific values
Config.set_session_cookie("temporary_session")
```

### Save Current Config

Save runtime config to file:

```python
from config import Config

# Make changes
Config.set_session_cookie("new_cookie")
Config.set_proxy(http_proxy="http://localhost:8080")

# Save for later
Config.save_to_file("my_config.json")
```

### Validate Configuration

```python
from config import Config

def validate_config():
    if not Config.SESSION_COOKIE:
        raise ValueError("SESSION_COOKIE not set")
    if len(Config.SESSION_COOKIE) < 20:
        raise ValueError("SESSION_COOKIE appears invalid")
    print("✓ Configuration valid")

validate_config()
```

## Docker Usage

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
      - HTTP_PROXY=${HTTP_PROXY}
      - HTTPS_PROXY=${HTTPS_PROXY}
    volumes:
      - ./cache:/app/cache
      - ./output:/app/output
```

Run with:
```bash
docker-compose up
```

Environment variables will be read from your `.env` file automatically.
