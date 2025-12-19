from dataclasses import dataclass
from typing import Optional, Dict
import os


@dataclass
class LadbrokesConfig:
    api_key: Optional[str] = None
    base_url: str = "https://api.ladbrokes.com"
    poll_interval: int = 30
    # Optional proxy string (eg. "http://user:pass@host:port")
    proxy: Optional[str] = None


def _get_nord_proxy() -> Optional[str]:
    """Return a proxy string if one is configured for NordVPN or env vars.

    Priority:
    - `LADBROKES_NORD_PROXY` env var
    - `NORD_PROXY` env var
    - `PROXY` env var
    Returns None when no proxy is configured.
    """
    for name in ("LADBROKES_NORD_PROXY", "NORD_PROXY", "PROXY"):
        val = os.environ.get(name)
        if val:
            return val
    return None
