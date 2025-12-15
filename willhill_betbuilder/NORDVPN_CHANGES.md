# NordVPN Integration Summary

## What Was Added

The project now supports NordVPN proxies with automatic URL generation from credentials.

## Changes Made

### 1. config.py
Added NordVPN-specific configuration:
```python
# New environment variables
NORD_USER = os.environ.get("NORD_USER", None)
NORD_PWD = os.environ.get("NORD_PWD", None)
NORD_LOCATION = os.environ.get("NORD_LOCATION", None)

# Updated get_proxies() to build NordVPN URLs
def get_proxies(cls):
    if cls.NORD_USER and cls.NORD_PWD and cls.NORD_LOCATION:
        return {
            'http': f'http://{cls.NORD_USER}:{cls.NORD_PWD}@{cls.NORD_LOCATION}.nordvpn.com:89',
            'https': f'https://{cls.NORD_USER}:{cls.NORD_PWD}@{cls.NORD_LOCATION}.nordvpn.com:89',
        }
    # Falls back to HTTP_PROXY/HTTPS_PROXY if NordVPN not configured
```

### 2. .env.example
Added NordVPN configuration template:
```env
# NordVPN Proxy Settings (Method 2 - NordVPN)
# If these are set, they override HTTP_PROXY/HTTPS_PROXY
# NORD_USER=your_nordvpn_email@example.com
# NORD_PWD=your_nordvpn_password
# NORD_LOCATION=us5678
```

### 3. config.example.json
Added NordVPN fields:
```json
{
  "nord_user": null,
  "nord_pwd": null,
  "nord_location": null
}
```

### 4. generate_combos.py
Added CLI arguments:
```python
parser.add_argument('--nord-user', help='NordVPN username/email')
parser.add_argument('--nord-pwd', help='NordVPN password')
parser.add_argument('--nord-location', help='NordVPN server location (e.g., us5678)')
```

## Usage Examples

### Method 1: .env File (Recommended)
```env
WILLIAMHILL_SESSION=your_session_cookie
NORD_USER=your_email@example.com
NORD_PWD=your_nordvpn_password
NORD_LOCATION=us5678
```

### Method 2: Command Line
```bash
python generate_combos.py OB_EV37926026 \
  --nord-user "your_email@example.com" \
  --nord-pwd "your_password" \
  --nord-location "us5678" \
  --stats
```

### Method 3: JSON Config
```json
{
  "session_cookie": "your_session",
  "nord_user": "your_email@example.com",
  "nord_pwd": "your_password",
  "nord_location": "us5678"
}
```

### Method 4: Programmatic
```python
from config import Config

Config.NORD_USER = "your_email@example.com"
Config.NORD_PWD = "your_password"
Config.NORD_LOCATION = "us5678"

proxies = Config.get_proxies()
# Returns:
# {
#   'http': 'http://your_email@example.com:your_password@us5678.nordvpn.com:89',
#   'https': 'https://your_email@example.com:your_password@us5678.nordvpn.com:89'
# }
```

## Generated Proxy Format

Input:
- `NORD_USER` = your_email@example.com
- `NORD_PWD` = your_password
- `NORD_LOCATION` = us5678

Output:
```python
{
    'http': 'http://your_email@example.com:your_password@us5678.nordvpn.com:89',
    'https': 'https://your_email@example.com:your_password@us5678.nordvpn.com:89'
}
```

This matches your required format:
```python
PROXIES = {
    'http': f'http://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
    'https': f'https://{NORD_USER}:{NORD_PWD}@{NORD_LOCATION}.nordvpn.com:89',
}
```

## Configuration Priority

1. **NordVPN** (if all three: NORD_USER, NORD_PWD, NORD_LOCATION set)
2. **HTTP_PROXY/HTTPS_PROXY** (if NordVPN not configured)
3. **No proxy** (if neither configured)

## Testing

Test NordVPN configuration:
```bash
python -c "from config import Config; print(Config.get_proxies())"
```

With credentials set, should output:
```
{'http': 'http://user:pwd@us5678.nordvpn.com:89', 'https': 'https://user:pwd@us5678.nordvpn.com:89'}
```

## Documentation

- **NORDVPN_SETUP.md** - Complete NordVPN setup guide
  - Getting credentials
  - Finding server locations
  - Configuration examples
  - Troubleshooting
  
- **CONFIG_GUIDE.md** - Updated with NordVPN section
  - Configuration options
  - Priority explanation
  - Security best practices

## Files Modified

1. ✅ `config.py` - Added NORD_* variables and updated get_proxies()
2. ✅ `.env.example` - Added NordVPN configuration template
3. ✅ `config.example.json` - Added nord_* fields
4. ✅ `generate_combos.py` - Added --nord-* CLI arguments
5. ✅ `CONFIG_GUIDE.md` - Updated with NordVPN documentation
6. ✅ `NORDVPN_SETUP.md` - NEW comprehensive NordVPN guide

## Backward Compatibility

✅ All existing functionality preserved:
- Standard HTTP_PROXY/HTTPS_PROXY still work
- No breaking changes
- NordVPN is optional
- Falls back to standard proxies if NordVPN not configured
