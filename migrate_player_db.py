#!/usr/bin/env python3
"""
Migration script: JSON files → SQLite database for player names.
"""

import os
import sys
import json
from pathlib import Path
from player_db import PlayerDatabase


def backup_json_files():
    """Create backups of existing JSON files."""
    files_to_backup = [
        'player_name_mappings.json',
        'data/player_name_tracking.json',
        'data/skipped_player_pairs.json'
    ]
    
    backup_dir = Path('data/json_backups')
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_name = f"{Path(file_path).stem}_{timestamp}.json"
            backup_path = backup_dir / backup_name
            shutil.copy2(file_path, backup_path)
            print(f"✓ Backed up: {file_path} → {backup_path}")
    
    return True


def migrate_to_sqlite():
    """Perform the migration from JSON to SQLite."""
    print("\n" + "="*70)
    print("PLAYER NAME SYSTEM MIGRATION: JSON → SQLite")
    print("="*70 + "\n")
    
    # Step 1: Backup
    print("[1/4] Creating backups of JSON files...")
    if not backup_json_files():
        print("❌ Backup failed. Aborting migration.")
        return False
    
    # Step 2: Initialize database
    print("\n[2/4] Initializing SQLite database...")
    db = PlayerDatabase('data/player_names.db')
    print("✓ Database initialized")
    
    # Step 3: Import data
    print("\n[3/4] Importing data from JSON files...")
    
    counts = db.import_from_json(
        mappings_file='player_name_mappings.json',
        tracking_file='data/player_name_tracking.json',
        skipped_file='data/skipped_player_pairs.json'
    )
    
    print(f"  ✓ Imported {counts['mappings']} player name mappings")
    print(f"  ✓ Imported {counts['players']} unique players")
    print(f"  ✓ Imported {counts['tracking_records']} tracking records")
    print(f"  ✓ Imported {counts['skipped_pairs']} skipped pairs")
    
    # Step 4: Verify
    print("\n[4/4] Verifying migration...")
    stats = db.get_stats()
    
    print(f"  Database statistics:")
    print(f"    - player_mappings: {stats['player_mappings']} rows")
    print(f"    - player_stats: {stats['player_stats']} rows")
    print(f"    - player_tracking: {stats['player_tracking']} rows")
    print(f"    - skipped_pairs: {stats['skipped_pairs']} rows")
    
    # Sanity checks
    success = True
    if stats['player_mappings'] != counts['mappings']:
        print("  ⚠️  Mapping count mismatch!")
        success = False
    
    if stats['player_stats'] != counts['players']:
        print("  ⚠️  Player count mismatch!")
        success = False
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Test the system with: python virgin_goose.py")
        print("  2. Test suggestions with: python suggest_player_mappings.py")
        print("  3. If everything works, you can archive the JSON files")
        print("\nTo rollback: Delete data/player_names.db and restore from data/json_backups/")
    else:
        print("\n⚠️  Migration completed with warnings. Please review.")
    
    return success


def export_from_sqlite():
    """Export SQLite data back to JSON (for backup/compatibility)."""
    print("\n" + "="*70)
    print("EXPORTING SQLite → JSON")
    print("="*70 + "\n")
    
    db = PlayerDatabase('data/player_names.db')
    
    print("Exporting to JSON files...")
    db.export_to_json(
        mappings_file='player_name_mappings.json',
        tracking_file='data/player_name_tracking.json'
    )
    
    print("✓ Exported to player_name_mappings.json")
    print("✓ Exported to data/player_name_tracking.json")
    print("\n✅ Export complete!")


def show_stats():
    """Display database statistics."""
    if not os.path.exists('data/player_names.db'):
        print("❌ Database not found: data/player_names.db")
        print("   Run migration first: python migrate_player_db.py migrate")
        return
    
    db = PlayerDatabase('data/player_names.db')
    stats = db.get_stats()
    
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)
    print(f"\nPlayer Mappings:    {stats['player_mappings']:>6} entries")
    print(f"Unique Players:     {stats['player_stats']:>6} players")
    print(f"Tracking Records:   {stats['player_tracking']:>6} sightings")
    print(f"Skipped Pairs:      {stats['skipped_pairs']:>6} pairs")
    print()


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate_player_db.py migrate   - Migrate JSON → SQLite")
        print("  python migrate_player_db.py export    - Export SQLite → JSON")
        print("  python migrate_player_db.py stats     - Show database stats")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'migrate':
        migrate_to_sqlite()
    elif command == 'export':
        export_from_sqlite()
    elif command == 'stats':
        show_stats()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
