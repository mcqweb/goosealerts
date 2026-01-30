#!/usr/bin/env python3
"""
Fix player_tracking table to prevent duplicates.
- Add unique constraint on (player_key, site_name, team_name, fixture)
- Change track_player to UPSERT instead of INSERT
- Clean up existing duplicates
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "data/player_names.db"
BACKUP_PATH = f"data/player_names_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_database():
    """Create backup before making changes."""
    if os.path.exists(DB_PATH):
        import shutil
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"✓ Backup created: {BACKUP_PATH}")
    else:
        print(f"! Database not found: {DB_PATH}")
        return False
    return True

def get_db_stats(conn):
    """Get current database statistics."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM player_tracking")
    total_tracking = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT player_key, site_name, COALESCE(team_name, ''), COALESCE(fixture, '')
            FROM player_tracking
            GROUP BY player_key, site_name, COALESCE(team_name, ''), COALESCE(fixture, '')
        )
    """)
    unique_tracking = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE match_id IS NULL")
    null_match_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE team_name IS NULL")
    null_team = cursor.fetchone()[0]
    
    return {
        'total_tracking': total_tracking,
        'unique_tracking': unique_tracking,
        'duplicates': total_tracking - unique_tracking,
        'null_match_id': null_match_id,
        'null_team': null_team
    }

def deduplicate_tracking(conn):
    """Remove duplicate tracking entries, keeping the most recent with best data."""
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("DEDUPLICATING PLAYER_TRACKING")
    print("=" * 80)
    
    # Create temp table with deduplicated data
    # Keep the most recent entry for each player/site/team/fixture combination
    # Prioritize entries with match_id over NULL
    cursor.execute("""
        CREATE TEMP TABLE tracking_dedup AS
        SELECT 
            player_key,
            raw_name,
            site_name,
            MAX(match_id) as match_id,  -- Keep non-NULL match_id if available
            team_name,
            fixture,
            MAX(seen_at) as seen_at  -- Keep most recent timestamp
        FROM player_tracking
        GROUP BY 
            player_key, 
            site_name, 
            COALESCE(team_name, ''),
            COALESCE(fixture, '')
    """)
    
    rows_kept = cursor.execute("SELECT COUNT(*) FROM tracking_dedup").fetchone()[0]
    
    # Clear original table and copy back deduplicated data
    cursor.execute("DELETE FROM player_tracking")
    cursor.execute("""
        INSERT INTO player_tracking (player_key, raw_name, site_name, match_id, team_name, fixture, seen_at)
        SELECT player_key, raw_name, site_name, match_id, team_name, fixture, seen_at
        FROM tracking_dedup
    """)
    
    cursor.execute("DROP TABLE tracking_dedup")
    conn.commit()
    
    print(f"✓ Deduplicated to {rows_kept} unique entries")
    return rows_kept

def add_unique_constraint(conn):
    """Recreate player_tracking table with unique constraint."""
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("ADDING UNIQUE CONSTRAINT")
    print("=" * 80)
    
    # Create new table with unique constraint
    cursor.execute("""
        CREATE TABLE player_tracking_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_key TEXT NOT NULL,
            raw_name TEXT NOT NULL,
            site_name TEXT NOT NULL,
            match_id TEXT,
            team_name TEXT,
            fixture TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_key, site_name, team_name, fixture)
        )
    """)
    
    # Copy data
    cursor.execute("""
        INSERT INTO player_tracking_new (player_key, raw_name, site_name, match_id, team_name, fixture, seen_at)
        SELECT player_key, raw_name, site_name, match_id, team_name, fixture, seen_at
        FROM player_tracking
    """)
    
    # Drop old table and rename new one
    cursor.execute("DROP TABLE player_tracking")
    cursor.execute("ALTER TABLE player_tracking_new RENAME TO player_tracking")
    
    # Recreate index
    cursor.execute("CREATE INDEX idx_player_key ON player_tracking(player_key)")
    cursor.execute("CREATE INDEX idx_site_name ON player_tracking(site_name)")
    cursor.execute("CREATE INDEX idx_team_name ON player_tracking(team_name)")
    cursor.execute("CREATE INDEX idx_fixture ON player_tracking(fixture)")
    
    conn.commit()
    print("✓ Unique constraint added")

def main():
    print("=" * 80)
    print("PLAYER TRACKING DEDUPLICATION & CONSTRAINT FIX")
    print("=" * 80)
    
    # Backup
    if not backup_database():
        return
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    # Get initial stats
    print("\n📊 BEFORE:")
    before_stats = get_db_stats(conn)
    for key, value in before_stats.items():
        print(f"  {key}: {value}")
    
    # Deduplicate
    deduplicate_tracking(conn)
    
    # Add unique constraint
    add_unique_constraint(conn)
    
    # Get final stats
    print("\n📊 AFTER:")
    after_stats = get_db_stats(conn)
    for key, value in after_stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ SUMMARY:")
    print(f"  Removed {before_stats['duplicates']} duplicate entries")
    print(f"  Entries with NULL match_id: {after_stats['null_match_id']}")
    print(f"  Entries with NULL team_name: {after_stats['null_team']}")
    print(f"\n⚠️  Note: NULL team_name entries should be investigated")
    
    conn.close()
    print("\n✓ Database upgrade complete!")

if __name__ == '__main__':
    main()
