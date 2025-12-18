"""
Configuration settings for William Hill Bet Builder
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (check both module dir and parent dir)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try parent directory (for when used as submodule)
    parent_env = Path(__file__).parent.parent / '.env'
    if parent_env.exists():
        load_dotenv(parent_env)


class Config:
    """Configuration class for William Hill API integration"""
    
    # API Settings
    WILLIAMHILL_BYO_API_BASE = "https://sports.williamhill.com/data/byo01/en-gb"
    WILLIAMHILL_PRICING_API = "https://transact.williamhill.com/betslip/api/bets/getByoPrice"
    
    # Session Cookie - Always read from file before use
    SESSION_FILE = os.path.join(os.path.dirname(__file__), "williamhill_session.txt")
    SESSION_COOKIE = None  # Will be loaded dynamically

    @classmethod
    def get_session_cookie(cls):
        """
        Always read the session cookie from williamhill_session.txt if it exists, else fallback to env.
        """
        try:
            # If session file exists and has content, return it
            if os.path.exists(cls.SESSION_FILE):
                with open(cls.SESSION_FILE, "r", encoding="utf-8") as f:
                    value = f.read().strip()
                    if value:
                        cls.SESSION_COOKIE = value
                        return value

            # If file missing or empty, try to create it by running the login flow
            # Load .env and read credentials
            try:
                from dotenv import load_dotenv
                load_dotenv(Path(__file__).parent.parent / '.env')
            except Exception:
                pass

            username = os.environ.get('WILLIAMHILL_USERNAME')
            password = os.environ.get('WILLIAMHILL_PASSWORD')
            if (not cls.SESSION_FILE.exists() or cls.SESSION_FILE.stat().st_size == 0) and username and password:
                try:
                    print('[Config] williamhill_session.txt missing — running wh_login.py to create it')
                    import subprocess, sys
                    from pathlib import Path as _P
                    wh_login_path = os.path.join(os.path.dirname(__file__), "wh_login.py")
                    print(wh_login_path)
                    subprocess.run([
                        sys.executable, str(wh_login_path), 'login', username, password
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f'[Config] Failed to run wh_login.py: {e}')

            # Try reading again after attempted creation
            if cls.SESSION_FILE.exists():
                try:
                    with open(cls.SESSION_FILE, "r", encoding="utf-8") as f:
                        value = f.read().strip()
                        if value:
                            cls.SESSION_COOKIE = value
                            return value
                except Exception:
                    pass

            # Final fallback to env var
            value = os.environ.get("WILLIAMHILL_SESSION", "REDACTED")
            cls.SESSION_COOKIE = value
            return value
        except Exception as e:
            print(f"[Config] Failed to read/create session file: {e}")
            value = os.environ.get("WILLIAMHILL_SESSION", "REDACTED")
            cls.SESSION_COOKIE = value
            return value
    
    # Proxy Settings - Set these to route requests through a proxy
    # Format: "http://user:pass@host:port" or "http://host:port"
    HTTP_PROXY = os.environ.get("HTTP_PROXY", None)
    HTTPS_PROXY = os.environ.get("HTTPS_PROXY", None)
    
    # NordVPN Proxy Settings - Alternative to HTTP_PROXY/HTTPS_PROXY
    # If these are set, they override HTTP_PROXY/HTTPS_PROXY
    NORD_USER = os.environ.get("NORD_USER", None)
    NORD_PWD = os.environ.get("NORD_PWD", None)
    NORD_LOCATION = os.environ.get("NORD_LOCATION", None)  # e.g., "us5678"
    
    # Cache Settings
    CACHE_DIR = Path(__file__).parent / "cache"
    CACHE_EXPIRY_HOURS = int(os.environ.get("CACHE_EXPIRY_HOURS", "24"))
    
    # API Headers
    API_HEADERS = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://sports.williamhill.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
    }
    
    # API Timeout
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "30"))  # seconds
    
    @classmethod
    def get_proxies(cls):
        """
        Get proxy configuration for requests
        
        Supports two formats:
        1. Direct proxy URLs via HTTP_PROXY/HTTPS_PROXY
        2. NordVPN credentials via NORD_USER/NORD_PWD/NORD_LOCATION
        
        Returns:
            dict: Proxy configuration or None if no proxies configured
        """
        # If NordVPN credentials are provided, build proxy URLs
        if cls.NORD_USER and cls.NORD_PWD and cls.NORD_LOCATION:
            return {
                'http': f'http://{cls.NORD_USER}:{cls.NORD_PWD}@{cls.NORD_LOCATION}.nordvpn.com:89',
                'https': f'https://{cls.NORD_USER}:{cls.NORD_PWD}@{cls.NORD_LOCATION}.nordvpn.com:89',
            }
        
        # Otherwise use direct proxy URLs if provided
        proxies = {}
        if cls.HTTP_PROXY:
            proxies['http'] = cls.HTTP_PROXY
        if cls.HTTPS_PROXY:
            proxies['https'] = cls.HTTPS_PROXY
        
        return proxies if proxies else None
    
    @classmethod
    def set_session_cookie(cls, cookie):
        """
        Update the session cookie in the file and in memory
        """
        try:
            with open(cls.SESSION_FILE, "w", encoding="utf-8") as f:
                f.write(cookie.strip())
            cls.SESSION_COOKIE = cookie.strip()
        except Exception as e:
            print(f"[Config] Failed to write session file: {e}")
            cls.SESSION_COOKIE = cookie.strip()
    
    @classmethod
    def set_proxy(cls, http_proxy=None, https_proxy=None):
        """
        Set proxy configuration
        
        Args:
            http_proxy (str): HTTP proxy URL
            https_proxy (str): HTTPS proxy URL
        """
        if http_proxy:
            cls.HTTP_PROXY = http_proxy
        if https_proxy:
            cls.HTTPS_PROXY = https_proxy
    
    @classmethod
    def load_from_file(cls, config_file):
        """
        Load configuration from a file
        
        Args:
            config_file (str or Path): Path to configuration file
        """
        import json
        
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Update configuration
        if 'session_cookie' in config_data:
            cls.SESSION_COOKIE = config_data['session_cookie']
        if 'http_proxy' in config_data:
            cls.HTTP_PROXY = config_data['http_proxy']
        if 'https_proxy' in config_data:
            cls.HTTPS_PROXY = config_data['https_proxy']
        if 'nord_user' in config_data:
            cls.NORD_USER = config_data['nord_user']
        if 'nord_pwd' in config_data:
            cls.NORD_PWD = config_data['nord_pwd']
        if 'nord_location' in config_data:
            cls.NORD_LOCATION = config_data['nord_location']
        if 'cache_expiry_hours' in config_data:
            cls.CACHE_EXPIRY_HOURS = config_data['cache_expiry_hours']
    
    @classmethod
    def save_to_file(cls, config_file):
        """
        Save current configuration to a file
        
        Args:
            config_file (str or Path): Path to save configuration
        """
        import json
        
        config_data = {
            'session_cookie': cls.SESSION_COOKIE,
            'http_proxy': cls.HTTP_PROXY,
            'https_proxy': cls.HTTPS_PROXY,
            'nord_user': cls.NORD_USER,
            'nord_pwd': cls.NORD_PWD,
            'nord_location': cls.NORD_LOCATION,
            'cache_expiry_hours': cls.CACHE_EXPIRY_HOURS
        }
        
        config_path = Path(config_file)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
