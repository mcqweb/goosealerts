"""
William Hill API Client
Handles requests to the William Hill BYO (Build Your Own) API
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


class WilliamHillAPIClient:
    """Client for interacting with William Hill BYO API"""
    
    def __init__(self, timeout: Optional[int] = None, proxies: Optional[Dict] = None, session_cookie: Optional[str] = None):
        """
        Initialize the API client
        
        Args:
            timeout: Request timeout in seconds (defaults to Config.API_TIMEOUT)
            proxies: Proxy configuration dict (defaults to Config.get_proxies())
            session_cookie: Session cookie for authentication (defaults to Config.SESSION_COOKIE)
        """
        self.timeout = timeout or Config.API_TIMEOUT
        self.proxies = proxies if proxies is not None else Config.get_proxies()
        self.session_cookie = session_cookie or Config.SESSION_COOKIE
        
        self.session = requests.Session()
        self.session.headers.update(Config.API_HEADERS)
        
        # Set proxies if configured
        if self.proxies:
            self.session.proxies.update(self.proxies)
    
    def get_event_markets(self, event_id: str) -> Dict[str, Any]:
        """
        Fetch available markets for a given event
        
        Args:
            event_id: The event ID (e.g., 'OB_EV37926026')
            
        Returns:
            Dict containing market data
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{Config.WILLIAMHILL_BYO_API_BASE}/event/{event_id}/markets/byoFreedom"
        
        print(f"\n[API DEBUG] Making request to: {url}")
        print(f"[API DEBUG] Headers: {dict(self.session.headers)}")
        print(f"[API DEBUG] Cookies: {dict(self.session.cookies)}")
        if self.proxies:
            print(f"[API DEBUG] Proxies: {self.proxies}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            print(f"[API DEBUG] Response status: {response.status_code}")
            print(f"[API DEBUG] Response headers: {dict(response.headers)}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[API DEBUG] Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[API DEBUG] Response body: {e.response.text[:500]}")
            raise Exception(f"Failed to fetch markets for event {event_id}: {str(e)}")
    
    def get_event_start_time(self, markets_data: Dict[str, Any]) -> datetime:
        """
        Extract event start time from markets data
        
        Args:
            markets_data: The markets data returned from get_event_markets
            
        Returns:
            datetime object representing event start time
        """
        try:
            start_time_str = markets_data.get('startTime')
            if start_time_str:
                # Parse ISO format: 2024-12-22T14:00:00.000+0000
                return datetime.fromisoformat(start_time_str.replace('+0000', '+00:00'))
            return None
        except Exception as e:
            print(f"Warning: Could not parse start time: {e}")
            return None
    
    def close(self):
        """Close the session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
