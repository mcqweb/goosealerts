#!/usr/bin/env python3
"""
Cleanup script: Remove player records without team information.
This helps maintain a clean database with only contextual player data.
"""

import sqlite3
import os
from datetime import datetime


def cleanup_players_without_teams(db_path='data/player_names.db', dry_run=True):
    """Remove players that have no team information in any tracking record.
    
    Args:
        db_path: Path to the SQLite database
        dry_run: If True, only show what would be deleted without actually deleting
    
    Returns:
        Dict with cleanup statistics
    """
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return {'error': 'Database not found'}
    
    print(f"\n{'='*70}")
    print("PLAYER DATABASE CLEANUP: Removing Records Without Team Info")
    print(f"{'='*70}\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("   Run with --execute flag to perform actual cleanup\n")
    
    # Backup first (if not dry run)
    if not dry_run:
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"[1/4] Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created\n")
    else:
        print("[1/4] Skipping backup (dry run)\n")
    
    # Connect to database
    print("[2/4] Analyzing database...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Find players with no team info
        cursor.execute("""
            SELECT DISTINCT player_key
            FROM player_stats
            WHERE player_key NOT IN (
                SELECT DISTINCT player_key
                FROM player_tracking
                WHERE team_name IS NOT NULL
            )
        """)
        
        players_without_teams = [row['player_key'] for row in cursor.fetchall()]
        
        print(f"  Found {len(players_without_teams)} players with no team information")
        
        # Count records that would be affected
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM player_tracking
            WHERE player_key IN (
                SELECT DISTINCT player_key
                FROM player_stats
                WHERE player_key NOT IN (
                    SELECT DISTINCT player_key
                    FROM player_tracking
                    WHERE team_name IS NOT NULL
                )
            )
        """)
        tracking_records = cursor.fetchone()['count']
        
        print(f"  Would affect {tracking_records} tracking records")
        print()
        
        # Show sample of players that would be removed
        if players_without_teams:
            print("  Sample players to be removed:")
            for player_key in players_without_teams[:20]:
                cursor.execute("""
                    SELECT occurrence_count, last_seen
                    FROM player_stats
                    WHERE player_key = ?
                """, (player_key,))
                stats = cursor.fetchone()
                if stats:
                    last_seen = stats['last_seen'][:10] if stats['last_seen'] else 'N/A'
                    print(f"    • {player_key} - {stats['occurrence_count']} occurrences, last seen {last_seen}")
            
            if len(players_without_teams) > 20:
                print(f"    ... and {len(players_without_teams) - 20} more")
        print()
        
        if not dry_run:
            print("[3/4] Performing cleanup...")
            
            # Delete tracking records
            cursor.execute("""
                DELETE FROM player_tracking
                WHERE player_key IN (
                    SELECT DISTINCT player_key
                    FROM player_stats
                    WHERE player_key NOT IN (
                        SELECT DISTINCT player_key
                        FROM player_tracking
                        WHERE team_name IS NOT NULL
                    )
                )
            """)
            deleted_tracking = cursor.rowcount
            print(f"  ✓ Deleted {deleted_tracking} tracking records")
            
            # Delete stats
            cursor.execute("""
                DELETE FROM player_stats
                WHERE player_key NOT IN (
                    SELECT DISTINCT player_key
                    FROM player_tracking
                    WHERE team_name IS NOT NULL
                )
            """)
            deleted_stats = cursor.rowcount
            print(f"  ✓ Deleted {deleted_stats} player stats")
            
            conn.commit()
            print()
        else:
            print("[3/4] Skipping cleanup (dry run)\n")
        
        # Show final stats
        print("[4/4] Database statistics:")
        cursor.execute("SELECT COUNT(*) as count FROM player_stats")
        remaining_players = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM player_tracking")
        remaining_tracking = cursor.fetchone()['count']
        
        print(f"  Remaining players: {remaining_players}")
        print(f"  Remaining tracking records: {remaining_tracking}")
        print()
        
        stats = {
            'players_without_teams': len(players_without_teams),
            'tracking_records_affected': tracking_records,
            'remaining_players': remaining_players,
            'remaining_tracking': remaining_tracking
        }
        
        if not dry_run:
            stats['deleted_tracking'] = deleted_tracking
            stats['deleted_stats'] = deleted_stats
        
        return stats
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        conn.rollback()
        return {'error': str(e)}
    
    finally:
        conn.close()


def main():
    """Main entry point."""
    import sys
    
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] in ['--execute', '-e', '--real']:
        dry_run = False
    
    stats = cleanup_players_without_teams(dry_run=dry_run)
    
    if 'error' in stats:
        sys.exit(1)
    
    print(f"{'='*70}")
    if dry_run:
        print("✅ DRY RUN COMPLETE")
        print(f"{'='*70}")
        print(f"\nWould remove:")
        print(f"  • {stats['players_without_teams']} players")
        print(f"  • {stats['tracking_records_affected']} tracking records")
        print(f"\nTo perform actual cleanup, run:")
        print(f"  python cleanup_players_no_teams.py --execute")
    else:
        print("✅ CLEANUP COMPLETE")
        print(f"{'='*70}")
        print(f"\nRemoved:")
        print(f"  • {stats.get('deleted_stats', 0)} players")
        print(f"  • {stats.get('deleted_tracking', 0)} tracking records")
        print(f"\nBackup saved to: data/player_names.db.backup_*")
        print(f"\nRemaining in database:")
        print(f"  • {stats['remaining_players']} players")
        print(f"  • {stats['remaining_tracking']} tracking records")


if __name__ == '__main__':
    main()
