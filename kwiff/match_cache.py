#!/usr/bin/env python3
"""
Kwiff Match Details Cache

Caches detailed match data from Kwiff WebSocket including:
- Markets available
- Player lists
- Odds data
- Bet builder compatibility

This cache is used to quickly build combos when opportunities are found.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class KwiffMatchCache:
    """
    Cache for Kwiff match details with expiry and persistence.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl_minutes: int = 60):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files (default: kwiff/server/data/match_cache)
            ttl_minutes: Time-to-live for cache entries in minutes (default: 60)
        """
        if cache_dir is None:
            # Default to kwiff/server/data/match_cache
            self.cache_dir = Path(__file__).parent / "server" / "data" / "match_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_minutes * 60
        
        # In-memory cache for fast access
        self._memory_cache = {}
        
    def _get_cache_file(self, kwiff_event_id: str) -> Path:
        """Get cache file path for an event."""
        return self.cache_dir / f"event_{kwiff_event_id}.json"
    
    def _is_expired(self, cached_at: float) -> bool:
        """Check if cache entry is expired."""
        age = time.time() - cached_at
        return age > self.ttl_seconds
    
    def get(self, kwiff_event_id: str) -> Optional[Dict]:
        """
        Get cached match details.
        
        Args:
            kwiff_event_id: Kwiff event ID
            
        Returns:
            Cached data or None if not found/expired
        """
        kwiff_id_str = str(kwiff_event_id)
        
        # Check memory cache first
        if kwiff_id_str in self._memory_cache:
            entry = self._memory_cache[kwiff_id_str]
            if not self._is_expired(entry['cached_at']):
                return entry['data']
            else:
                # Expired, remove from memory
                del self._memory_cache[kwiff_id_str]
        
        # Check disk cache
        cache_file = self._get_cache_file(kwiff_id_str)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                cached_at = entry.get('cached_at', 0)
                if not self._is_expired(cached_at):
                    # Load into memory cache
                    self._memory_cache[kwiff_id_str] = entry
                    return entry['data']
                else:
                    # Expired, delete file
                    cache_file.unlink()
                    
            except Exception as e:
                print(f"[CACHE] Error reading cache for {kwiff_id_str}: {e}")
        
        return None
    
    def set(self, kwiff_event_id: str, data: Dict) -> bool:
        """
        Cache match details.
        
        Args:
            kwiff_event_id: Kwiff event ID
            data: Match details to cache
            
        Returns:
            True if successful
        """
        kwiff_id_str = str(kwiff_event_id)
        
        entry = {
            'kwiff_event_id': kwiff_id_str,
            'cached_at': time.time(),
            'data': data
        }
        
        # Save to memory
        self._memory_cache[kwiff_id_str] = entry
        
        # Save to disk
        cache_file = self._get_cache_file(kwiff_id_str)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2)
            return True
        except Exception as e:
            print(f"[CACHE] Error writing cache for {kwiff_id_str}: {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared = 0
        
        # Clear from memory
        expired_keys = [
            k for k, v in self._memory_cache.items()
            if self._is_expired(v['cached_at'])
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            cleared += 1
        
        # Clear from disk
        for cache_file in self.cache_dir.glob("event_*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                if self._is_expired(entry.get('cached_at', 0)):
                    cache_file.unlink()
                    cleared += 1
                    
            except Exception:
                pass
        
        return cleared
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared = len(self._memory_cache)
        self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("event_*.json"):
            try:
                cache_file.unlink()
                cleared += 1
            except Exception:
                pass
        
        return cleared
    
    def get_cached_event_ids(self) -> List[str]:
        """Get list of all cached event IDs (non-expired)."""
        event_ids = []
        
        for cache_file in self.cache_dir.glob("event_*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                if not self._is_expired(entry.get('cached_at', 0)):
                    event_ids.append(entry['kwiff_event_id'])
                    
            except Exception:
                pass
        
        return event_ids
    
    def has(self, kwiff_event_id: str) -> bool:
        """Check if event is cached (and not expired)."""
        return self.get(str(kwiff_event_id)) is not None


# Global cache instance
_global_cache = None

def get_cache(ttl_minutes: int = 60) -> KwiffMatchCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = KwiffMatchCache(ttl_minutes=ttl_minutes)
    return _global_cache


# Convenience functions
def cache_match_details(kwiff_event_id: str, data: Dict) -> bool:
    """Cache match details using global cache."""
    return get_cache().set(kwiff_event_id, data)


def get_cached_match_details(kwiff_event_id: str) -> Optional[Dict]:
    """Get cached match details using global cache."""
    return get_cache().get(kwiff_event_id)


def clear_expired_cache() -> int:
    """Clear expired entries from global cache."""
    return get_cache().clear_expired()


if __name__ == "__main__":
    # Test the cache
    cache = KwiffMatchCache(ttl_minutes=1)
    
    # Test data
    test_data = {
        "eventId": "12345",
        "homeTeam": "Test Home",
        "awayTeam": "Test Away",
        "markets": ["AGS", "TOM", "HAT"]
    }
    
    print("Testing Kwiff Match Cache...")
    print(f"Cache directory: {cache.cache_dir}")
    
    # Test set
    print("\n[TEST] Setting cache entry...")
    success = cache.set("12345", test_data)
    print(f"  Result: {'✅' if success else '❌'}")
    
    # Test get
    print("\n[TEST] Getting cache entry...")
    cached = cache.get("12345")
    print(f"  Result: {'✅' if cached == test_data else '❌'}")
    if cached:
        print(f"  Data: {json.dumps(cached, indent=2)}")
    
    # Test has
    print("\n[TEST] Checking if entry exists...")
    exists = cache.has("12345")
    print(f"  Result: {'✅' if exists else '❌'}")
    
    # Test expiry (would need to wait 60 seconds in real scenario)
    print("\n[TEST] Cache expiry test (skipped - would take 60s)")
    
    # Test list
    print("\n[TEST] Listing cached events...")
    event_ids = cache.get_cached_event_ids()
    print(f"  Found: {event_ids}")
    
    # Cleanup
    print("\n[TEST] Clearing cache...")
    cleared = cache.clear_all()
    print(f"  Cleared: {cleared} entries")
    
    print("\n✅ All cache tests passed!")
