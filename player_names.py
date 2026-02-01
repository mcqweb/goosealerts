#!/usr/bin/env python3
"""
Player name management adapter.
Provides backward-compatible interface that uses SQLite when available,
falls back to JSON if not.
"""

import os
import json
from typing import Optional, Dict
from datetime import datetime, timezone


# Try to import SQLite backend
try:
    from player_db import get_db as _get_db
    USE_SQLITE = os.path.exists('data/player_names.db')
except ImportError:
    USE_SQLITE = False


# JSON fallback paths
PLAYER_MAPPINGS_FILE = "player_name_mappings.json"
PLAYER_TRACKING_FILE = "data/player_name_tracking.json"


# ========= PUBLIC API =========

def load_player_mappings() -> Dict[str, str]:
    """Load player name mappings.
    
    Returns:
        Dict with structure: {normalized_variation: preferred_name}
    """
    if USE_SQLITE:
        return _get_db().get_all_mappings()
    else:
        return _load_mappings_from_json()


def get_mapped_name(player_name: str, mappings: Optional[Dict] = None) -> Optional[str]:
    """Check if a manual mapping exists for a player name.
    
    Args:
        player_name: Player name to look up (will be normalized)
        mappings: Optional pre-loaded mappings dict (for batch operations)
    
    Returns:
        Preferred/canonical name if a mapping exists, None otherwise
    """
    # Import here to avoid circular dependency
    from virgin_goose import normalize_name
    
    norm_key = normalize_name(player_name)
    
    if USE_SQLITE and mappings is None:
        # Direct DB lookup is faster
        return _get_db().get_mapping(norm_key)
    else:
        # Use provided mappings or load from JSON
        if mappings is None:
            mappings = load_player_mappings()
        return mappings.get(norm_key)


def track_player_name(player_name: str, site_name: str, match_id: Optional[str] = None,
                     team_name: Optional[str] = None, fixture: Optional[str] = None) -> None:
    """Track a player name seen on a specific site.
    
    Args:
        player_name: Raw player name as it appears on the site
        site_name: Site identifier (e.g., 'betfair', 'williamhill', 'virgin')
        match_id: Optional match ID for context
        team_name: Optional team name (e.g., 'Manchester United')
        fixture: Optional fixture string (e.g., 'Manchester United v Liverpool')
    """
    if not player_name or not site_name:
        return
    
    # Import here to avoid circular dependency
    from virgin_goose import normalize_name
    
    try:
        if USE_SQLITE:
            _track_player_sqlite(player_name, site_name, match_id, team_name, fixture, normalize_name)
        else:
            # Ensure team_name and fixture are propagated in JSON fallback for compatibility
            _track_player_json(player_name, site_name, match_id, team_name, fixture, normalize_name)
    except Exception as e:
        print(f"[WARN] Failed to track player name '{player_name}' on {site_name}: {e}")


def add_player_mapping(variant: str, preferred: str) -> None:
    """Add a player name mapping.
    
    Args:
        variant: Variant name (will be normalized)
        preferred: Preferred/canonical name
    """
    from virgin_goose import normalize_name
    
    variant_norm = normalize_name(variant)
    preferred_norm = normalize_name(preferred)
    
    if USE_SQLITE:
        _get_db().add_mapping(variant_norm, preferred)
        # Also merge any existing tracking rows that used the old key into the new preferred key
        try:
            merged = _get_db().merge_player_key(variant_norm, preferred_norm)
            if merged:
                print(f"[PLAYER_DB] Merged {merged} tracking rows from '{variant_norm}' into '{preferred_norm}'")
        except Exception as e:
            print(f"[PLAYER_DB] Error merging tracking rows for mapping {variant_norm} -> {preferred_norm}: {e}")
    else:
        mappings = _load_mappings_from_json()
        mappings[variant_norm] = preferred
        _save_mappings_to_json(mappings)

# ========= INTERNAL: SQLite Implementation =========

def _track_player_sqlite(player_name: str, site_name: str, match_id: Optional[str],
                        team_name: Optional[str], fixture: Optional[str], normalize_name_func):
    """Track player using SQLite."""
    db = _get_db()
    
    norm_name = normalize_name_func(player_name)
    
    # Check if mapped - use preferred name as key if so
    preferred = db.get_mapping(norm_name)
    player_key = preferred if preferred else norm_name
    
    db.track_player(player_key, player_name, site_name, match_id, team_name, fixture)


# ========= INTERNAL: JSON Fallback Implementation =========

def _load_mappings_from_json() -> Dict[str, str]:
    """Load mappings from JSON file."""
    from virgin_goose import normalize_name
    
    try:
        if os.path.exists(PLAYER_MAPPINGS_FILE):
            with open(PLAYER_MAPPINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filter out comment keys and normalize
                mappings = {k: v for k, v in data.items() if not k.startswith('_')}
                return {normalize_name(k): v for k, v in mappings.items()}
    except Exception as e:
        print(f"[WARN] Failed to load player mappings: {e}")
    return {}


def _save_mappings_to_json(mappings: Dict[str, str]) -> None:
    """Save mappings to JSON file."""
    mappings['__alias__'] = 'preferred name'  # Add comment
    with open(PLAYER_MAPPINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2)


def _track_player_json(player_name: str, site_name: str, match_id: Optional[str], team_name: Optional[str], fixture: Optional[str], normalize_name_func):
    """Track player using JSON files (legacy).

    This JSON fallback now records `team_name` and `fixture` (lists) on each tracking
    entry so callers that only have JSON storage will still retain contextual data
    collected from lineups and match contexts.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(PLAYER_TRACKING_FILE), exist_ok=True)
    
    # Load existing tracking data
    tracking_data = {}
    if os.path.exists(PLAYER_TRACKING_FILE):
        try:
            with open(PLAYER_TRACKING_FILE, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        except Exception:
            tracking_data = {}
    
    # Check if this name has a mapping
    mappings = _load_mappings_from_json()
    norm_name = normalize_name_func(player_name)
    preferred_name = mappings.get(norm_name)
    
    # Use preferred name as key if mapped, otherwise use normalized name
    tracking_key = preferred_name if preferred_name else norm_name
    
    if tracking_key not in tracking_data:
        tracking_data[tracking_key] = {
            'raw_names': {},
            'team_names': [],   # List of observed team names
            'fixtures': [],     # List of observed fixtures
            'first_seen': datetime.now(timezone.utc).isoformat(),
            'last_seen': datetime.now(timezone.utc).isoformat(),
            'occurrence_count': 0
        }
    
    entry = tracking_data[tracking_key]
    
    # Track raw name by site
    if site_name not in entry['raw_names']:
        entry['raw_names'][site_name] = []
    
    # Add raw name if not already tracked for this site
    if player_name not in entry['raw_names'][site_name]:
        entry['raw_names'][site_name].append(player_name)

    # Record team_name and fixture when available
    try:
        if team_name:
            if team_name not in entry.get('team_names', []):
                entry.setdefault('team_names', []).append(team_name)
        if fixture:
            if fixture not in entry.get('fixtures', []):
                entry.setdefault('fixtures', []).append(fixture)
    except Exception:
        # Be defensive - don't fail tracking on odd data
        pass
    
    # Update metadata
    entry['last_seen'] = datetime.now(timezone.utc).isoformat()
    entry['occurrence_count'] = entry.get('occurrence_count', 0) + 1
    
    # Save atomically
    tmp_file = PLAYER_TRACKING_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(tracking_data, f, indent=2, sort_keys=True)
    os.replace(tmp_file, PLAYER_TRACKING_FILE)


# ========= STATUS =========

def get_backend_info() -> Dict[str, any]:
    """Get information about which backend is being used.
    
    Returns:
        Dict with backend info
    """
    info = {
        'backend': 'sqlite' if USE_SQLITE else 'json',
        'db_exists': os.path.exists('data/player_names.db'),
        'json_mappings_exists': os.path.exists(PLAYER_MAPPINGS_FILE),
        'json_tracking_exists': os.path.exists(PLAYER_TRACKING_FILE)
    }
    
    if USE_SQLITE:
        try:
            stats = _get_db().get_stats()
            info['stats'] = stats
        except Exception as e:
            info['error'] = str(e)
    
    return info


def print_backend_status():
    """Print backend status to console."""
    info = get_backend_info()
    
    if info['backend'] == 'sqlite':
        print("[PLAYER_DB] Using SQLite backend")
        if 'stats' in info:
            s = info['stats']
            print(f"[PLAYER_DB]   - Mappings: {s['player_mappings']}")
            print(f"[PLAYER_DB]   - Players: {s['player_stats']}")
            print(f"[PLAYER_DB]   - Tracking: {s['player_tracking']}")
    else:
        print("[PLAYER_DB] Using JSON backend (legacy)")
        if info['json_mappings_exists']:
            print(f"[PLAYER_DB]   - Mappings: {PLAYER_MAPPINGS_FILE}")
        if info['json_tracking_exists']:
            print(f"[PLAYER_DB]   - Tracking: {PLAYER_TRACKING_FILE}")
