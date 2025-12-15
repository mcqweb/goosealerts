"""
Cache Manager for William Hill Market Data
Handles caching of market data with expiration based on event start time
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


class CacheManager:
    """Manages caching of market data for events"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the cache manager
        
        Args:
            cache_dir: Directory to store cache files (defaults to Config.CACHE_DIR)
        """
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, event_id: str) -> Path:
        """
        Get the cache file path for an event
        
        Args:
            event_id: The event ID
            
        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{event_id}.json"
    
    def is_cache_valid(self, event_id: str, event_start_time: datetime) -> bool:
        """
        Check if cached data exists and is still valid
        
        Args:
            event_id: The event ID
            event_start_time: When the event starts
            
        Returns:
            True if cache exists and event hasn't started yet
        """
        cache_path = self._get_cache_path(event_id)
        
        if not cache_path.exists():
            return False
        
        # Cache is valid if event hasn't started yet
        if event_start_time and datetime.now(event_start_time.tzinfo) >= event_start_time:
            return False
        
        return True
    
    def get_cached_data(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached market data
        
        Args:
            event_id: The event ID
            
        Returns:
            Cached data dict or None if not found
        """
        cache_path = self._get_cache_path(event_id)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading cache for {event_id}: {e}")
            return None
    
    def save_to_cache(self, event_id: str, data: Dict[str, Any]) -> bool:
        """
        Save market data to cache
        
        Args:
            event_id: The event ID
            data: Market data to cache
            
        Returns:
            True if save was successful
        """
        cache_path = self._get_cache_path(event_id)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving cache for {event_id}: {e}")
            return False
    
    def clear_cache(self, event_id: Optional[str] = None):
        """
        Clear cache for a specific event or all events
        
        Args:
            event_id: Event ID to clear, or None to clear all
        """
        if event_id:
            cache_path = self._get_cache_path(event_id)
            if cache_path.exists():
                cache_path.unlink()
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def get_cache_info(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about cached data
        
        Args:
            event_id: The event ID
            
        Returns:
            Dict with cache metadata or None
        """
        cache_path = self._get_cache_path(event_id)
        
        if not cache_path.exists():
            return None
        
        stat = cache_path.stat()
        return {
            'event_id': event_id,
            'path': str(cache_path),
            'size_bytes': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime)
        }
