#!/usr/bin/env python3
"""
SQLite-based player name management system.
Replaces JSON files for improved performance with large datasets.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from contextlib import contextmanager


class PlayerDatabase:
    """Thread-safe SQLite database for player name management."""
    
    def __init__(self, db_path: str = "data/player_names.db"):
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                -- Player name mappings
                CREATE TABLE IF NOT EXISTS player_mappings (
                    variant_normalized TEXT PRIMARY KEY,
                    preferred_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_preferred 
                    ON player_mappings(preferred_name);
                
                -- Player sighting tracking
                CREATE TABLE IF NOT EXISTS player_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_key TEXT NOT NULL,
                    raw_name TEXT NOT NULL,
                    site_name TEXT NOT NULL,
                    match_id TEXT,
                    team_name TEXT,
                    fixture TEXT,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_player_key 
                    ON player_tracking(player_key);
                CREATE INDEX IF NOT EXISTS idx_site 
                    ON player_tracking(site_name);
                CREATE INDEX IF NOT EXISTS idx_seen_at 
                    ON player_tracking(seen_at);
                CREATE INDEX IF NOT EXISTS idx_team_name 
                    ON player_tracking(team_name);
                CREATE INDEX IF NOT EXISTS idx_fixture 
                    ON player_tracking(fixture);
                
                -- Player statistics (cached aggregates)
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_key TEXT PRIMARY KEY,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    occurrence_count INTEGER DEFAULT 0
                );
                
                -- Skipped player pairs (for suggestion tool)
                CREATE TABLE IF NOT EXISTS skipped_pairs (
                    name1_normalized TEXT NOT NULL,
                    name2_normalized TEXT NOT NULL,
                    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (name1_normalized, name2_normalized)
                );
                
                -- Metadata
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Set initial metadata
            conn.execute("""
                INSERT OR IGNORE INTO metadata (key, value) 
                VALUES ('schema_version', '1')
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========= MAPPING OPERATIONS =========
    
    def add_mapping(self, variant_normalized: str, preferred_name: str) -> bool:
        """Add or update a player name mapping.
        
        Args:
            variant_normalized: Normalized variant name (key)
            preferred_name: Preferred/canonical name (value)
        
        Returns:
            True if added, False if updated
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM player_mappings WHERE variant_normalized = ?",
                (variant_normalized,)
            )
            exists = cursor.fetchone() is not None
            
            conn.execute("""
                INSERT OR REPLACE INTO player_mappings 
                (variant_normalized, preferred_name, created_at)
                VALUES (?, ?, COALESCE(
                    (SELECT created_at FROM player_mappings WHERE variant_normalized = ?),
                    ?
                ))
            """, (variant_normalized, preferred_name, variant_normalized, 
                  datetime.now(timezone.utc).isoformat()))
            conn.commit()
            
            return not exists
    
    def get_mapping(self, variant_normalized: str) -> Optional[str]:
        """Get preferred name for a variant.
        
        Args:
            variant_normalized: Normalized variant name
        
        Returns:
            Preferred name if mapping exists, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT preferred_name FROM player_mappings WHERE variant_normalized = ?",
                (variant_normalized,)
            )
            row = cursor.fetchone()
            return row['preferred_name'] if row else None
    
    def get_all_mappings(self) -> Dict[str, str]:
        """Get all player name mappings.
        
        Returns:
            Dict of {variant_normalized: preferred_name}
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT variant_normalized, preferred_name FROM player_mappings")
            return {row['variant_normalized']: row['preferred_name'] for row in cursor}
    
    def delete_mapping(self, variant_normalized: str) -> bool:
        """Delete a mapping.
        
        Args:
            variant_normalized: Normalized variant name to delete
        
        Returns:
            True if deleted, False if didn't exist
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM player_mappings WHERE variant_normalized = ?",
                (variant_normalized,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # ========= TRACKING OPERATIONS =========
    
    def track_player(self, player_key: str, raw_name: str, site_name: str, 
                    match_id: Optional[str] = None, team_name: Optional[str] = None,
                    fixture: Optional[str] = None) -> None:
        """Track a player sighting.
        
        Args:
            player_key: Normalized or preferred name (used for grouping)
            raw_name: Raw name as it appeared on site
            site_name: Site identifier (e.g., 'betfair', 'williamhill')
            match_id: Optional match identifier
            team_name: Optional team name (e.g., 'Manchester United')
            fixture: Optional fixture string (e.g., 'Manchester United v Liverpool')
        """
        now = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            # Add tracking record
            conn.execute("""
                INSERT INTO player_tracking (player_key, raw_name, site_name, match_id, team_name, fixture, seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (player_key, raw_name, site_name, match_id, team_name, fixture, now))
            
            # Update stats (upsert)
            conn.execute("""
                INSERT INTO player_stats (player_key, first_seen, last_seen, occurrence_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(player_key) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    occurrence_count = occurrence_count + 1
            """, (player_key, now, now))
            
            conn.commit()
    
    def get_player_stats(self, player_key: str) -> Optional[Dict]:
        """Get statistics for a player.
        
        Args:
            player_key: Player key to lookup
        
        Returns:
            Dict with stats or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT first_seen, last_seen, occurrence_count
                FROM player_stats
                WHERE player_key = ?
            """, (player_key,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'first_seen': row['first_seen'],
                'last_seen': row['last_seen'],
                'occurrence_count': row['occurrence_count']
            }
    
    def get_all_players(self) -> Dict[str, Dict]:
        """Get all tracked players with their stats.
        
        Returns:
            Dict of {player_key: stats_dict}
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT player_key, first_seen, last_seen, occurrence_count
                FROM player_stats
                ORDER BY occurrence_count DESC
            """)
            
            return {
                row['player_key']: {
                    'first_seen': row['first_seen'],
                    'last_seen': row['last_seen'],
                    'occurrence_count': row['occurrence_count']
                }
                for row in cursor
            }
    
    def get_player_raw_names(self, player_key: str) -> Dict[str, List[str]]:
        """Get all raw names seen for a player, grouped by site.
        
        Args:
            player_key: Player key to lookup
        
        Returns:
            Dict of {site_name: [raw_names]}
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT site_name, raw_name
                FROM player_tracking
                WHERE player_key = ?
                ORDER BY site_name, raw_name
            """, (player_key,))
            
            result = {}
            for row in cursor:
                site = row['site_name']
                if site not in result:
                    result[site] = []
                if row['raw_name'] not in result[site]:
                    result[site].append(row['raw_name'])
            
            return result
    
    def get_player_teams(self, player_key: str) -> Set[str]:
        """Get all teams a player has been seen with.
        
        Args:
            player_key: Player key to lookup
        
        Returns:
            Set of team names (empty if none recorded)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT team_name
                FROM player_tracking
                WHERE player_key = ? AND team_name IS NOT NULL
            """, (player_key,))
            
            return {row['team_name'] for row in cursor}
    
    def get_player_fixtures(self, player_key: str) -> Set[str]:
        """Get all fixtures a player has been seen in.
        
        Args:
            player_key: Player key to lookup
        
        Returns:
            Set of fixture strings (empty if none recorded)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT fixture
                FROM player_tracking
                WHERE player_key = ? AND fixture IS NOT NULL
            """, (player_key,))
            
            return {row['fixture'] for row in cursor}
    
    def have_conflicting_teams(self, player_key1: str, player_key2: str) -> bool:
        """Check if two players have been seen with different teams.
        
        This helps avoid suggesting mappings for players who are clearly
        different people (e.g., two different 'J. Smith' on different teams).
        
        Args:
            player_key1: First player key
            player_key2: Second player key
        
        Returns:
            True if they have conflicting team data, False otherwise
        """
        teams1 = self.get_player_teams(player_key1)
        teams2 = self.get_player_teams(player_key2)
        
        # If either has no team data, we can't determine conflict
        if not teams1 or not teams2:
            return False
        
        # If they share any teams, no conflict
        if teams1 & teams2:
            return False
        
        # They have team data but no overlap - conflicting!
        return True
    
    # ========= SKIPPED PAIRS OPERATIONS =========
    
    def add_skipped_pair(self, name1_normalized: str, name2_normalized: str) -> None:
        """Mark a player name pair as skipped.
        
        Args:
            name1_normalized: First normalized name
            name2_normalized: Second normalized name
        """
        # Always store in sorted order for consistency
        name1, name2 = sorted([name1_normalized, name2_normalized])
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO skipped_pairs (name1_normalized, name2_normalized, skipped_at)
                VALUES (?, ?, ?)
            """, (name1, name2, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    
    def is_pair_skipped(self, name1_normalized: str, name2_normalized: str) -> bool:
        """Check if a pair has been skipped.
        
        Args:
            name1_normalized: First normalized name
            name2_normalized: Second normalized name
        
        Returns:
            True if pair has been skipped
        """
        name1, name2 = sorted([name1_normalized, name2_normalized])
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 1 FROM skipped_pairs 
                WHERE name1_normalized = ? AND name2_normalized = ?
            """, (name1, name2))
            return cursor.fetchone() is not None
    
    def get_all_skipped_pairs(self) -> Set[Tuple[str, str]]:
        """Get all skipped pairs.
        
        Returns:
            Set of (name1, name2) tuples (sorted)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT name1_normalized, name2_normalized FROM skipped_pairs")
            return {(row['name1_normalized'], row['name2_normalized']) for row in cursor}
    
    def clear_skipped_pairs(self) -> int:
        """Clear all skipped pairs.
        
        Returns:
            Number of pairs deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM skipped_pairs")
            conn.commit()
            return cursor.rowcount
    
    # ========= MIGRATION & MAINTENANCE =========
    
    def import_from_json(self, mappings_file: str, tracking_file: str, 
                        skipped_file: Optional[str] = None) -> Dict[str, int]:
        """Import data from legacy JSON files.
        
        Args:
            mappings_file: Path to player_name_mappings.json
            tracking_file: Path to player_name_tracking.json
            skipped_file: Optional path to skipped_player_pairs.json
        
        Returns:
            Dict with import counts
        """
        counts = {'mappings': 0, 'players': 0, 'tracking_records': 0, 'skipped_pairs': 0}
        
        # Import mappings
        if os.path.exists(mappings_file):
            with open(mappings_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            for variant, preferred in mappings.items():
                if not variant.startswith('_'):  # Skip comment keys
                    self.add_mapping(variant, preferred)
                    counts['mappings'] += 1
        
        # Import tracking data
        if os.path.exists(tracking_file):
            with open(tracking_file, 'r', encoding='utf-8') as f:
                tracking = json.load(f)
            
            for player_key, data in tracking.items():
                # Add to stats
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO player_stats 
                        (player_key, first_seen, last_seen, occurrence_count)
                        VALUES (?, ?, ?, ?)
                    """, (
                        player_key,
                        data.get('first_seen', datetime.now(timezone.utc).isoformat()),
                        data.get('last_seen', datetime.now(timezone.utc).isoformat()),
                        data.get('occurrence_count', 0)
                    ))
                    
                    # Add tracking records for each raw name
                    raw_names = data.get('raw_names', {})
                    for site_name, names in raw_names.items():
                        for raw_name in names:
                            conn.execute("""
                                INSERT INTO player_tracking 
                                (player_key, raw_name, site_name, team_name, fixture, seen_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                player_key,
                                raw_name,
                                site_name,
                                None,  # Legacy data doesn't have team info
                                None,  # Legacy data doesn't have fixture info
                                data.get('last_seen', datetime.now(timezone.utc).isoformat())
                            ))
                            counts['tracking_records'] += 1
                    
                    conn.commit()
                
                counts['players'] += 1
        
        # Import skipped pairs
        if skipped_file and os.path.exists(skipped_file):
            with open(skipped_file, 'r', encoding='utf-8') as f:
                skipped_list = json.load(f)
            
            for pair in skipped_list:
                if len(pair) == 2:
                    self.add_skipped_pair(pair[0], pair[1])
                    counts['skipped_pairs'] += 1
        
        return counts
    
    def export_to_json(self, mappings_file: str, tracking_file: str) -> None:
        """Export data to JSON files (for backup/compatibility).
        
        Args:
            mappings_file: Path for player_name_mappings.json
            tracking_file: Path for player_name_tracking.json
        """
        # Export mappings
        mappings = self.get_all_mappings()
        mappings['__alias__'] = 'preferred name'  # Add comment key
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        
        # Export tracking
        players = self.get_all_players()
        tracking = {}
        for player_key, stats in players.items():
            tracking[player_key] = {
                'first_seen': stats['first_seen'],
                'last_seen': stats['last_seen'],
                'occurrence_count': stats['occurrence_count'],
                'raw_names': self.get_player_raw_names(player_key)
            }
        
        with open(tracking_file, 'w', encoding='utf-8') as f:
            json.dump(tracking, f, indent=2, sort_keys=True)
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics.
        
        Returns:
            Dict with table counts
        """
        with self._get_connection() as conn:
            stats = {}
            
            for table in ['player_mappings', 'player_tracking', 'player_stats', 'skipped_pairs']:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            
            return stats


# Global instance (initialized on first use)
_db_instance: Optional[PlayerDatabase] = None

def get_db() -> PlayerDatabase:
    """Get the global PlayerDatabase instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = PlayerDatabase()
    return _db_instance
