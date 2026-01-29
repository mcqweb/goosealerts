#!/usr/bin/env python3
"""
Database schema upgrade: Add team_name and fixture columns to player_tracking.
Run this if you already have an existing player_names.db database.
"""

import os
import sqlite3
from datetime import datetime


def upgrade_database(db_path='data/player_names.db'):
    """Add team_name and fixture columns to existing database."""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   No upgrade needed - create new database with migration script.")
        return False
    
    print(f"\n{'='*70}")
    print("DATABASE SCHEMA UPGRADE: Adding Team/Fixture Tracking")
    print(f"{'='*70}\n")
    
    # Backup first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"[1/3] Creating backup: {backup_path}")
    
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✓ Backup created\n")
    
    # Connect and upgrade
    print("[2/3] Upgrading schema...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(player_tracking)")
        columns = [row[1] for row in cursor.fetchall()]
        
        needs_team = 'team_name' not in columns
        needs_fixture = 'fixture' not in columns
        
        if not needs_team and not needs_fixture:
            print("✓ Schema already up-to-date!")
            conn.close()
            return True
        
        # Add missing columns
        if needs_team:
            cursor.execute("ALTER TABLE player_tracking ADD COLUMN team_name TEXT")
            print("  ✓ Added team_name column")
        
        if needs_fixture:
            cursor.execute("ALTER TABLE player_tracking ADD COLUMN fixture TEXT")
            print("  ✓ Added fixture column")
        
        # Create indexes
        if needs_team:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_team_name 
                ON player_tracking(team_name)
            """)
            print("  ✓ Created team_name index")
        
        if needs_fixture:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fixture 
                ON player_tracking(fixture)
            """)
            print("  ✓ Created fixture index")
        
        conn.commit()
        print()
        
    except Exception as e:
        print(f"\n❌ Upgrade failed: {e}")
        conn.rollback()
        conn.close()
        
        # Restore backup
        print(f"Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, db_path)
        return False
    
    finally:
        if conn:
            conn.close()
    
    # Verify
    print("[3/3] Verifying upgrade...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(player_tracking)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    has_team = 'team_name' in columns
    has_fixture = 'fixture' in columns
    
    if has_team and has_fixture:
        print("✓ Schema verification passed\n")
        print(f"{'='*70}")
        print("✅ UPGRADE COMPLETE")
        print(f"{'='*70}")
        print(f"\nBackup saved to: {backup_path}")
        print("\nNew features enabled:")
        print("  • Team-based conflict detection")
        print("  • Fixture tracking")
        print("  • Smarter duplicate suggestions")
        return True
    else:
        print("❌ Schema verification failed")
        return False


if __name__ == '__main__':
    upgrade_database()
