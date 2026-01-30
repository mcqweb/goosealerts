import sqlite3

conn = sqlite3.connect('data/player_names.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row['name'] for row in cursor.fetchall()]
print(f"Tables: {tables}\n")

# Check schema first
print("=" * 80)
print("PLAYER_TRACKING SCHEMA")
print("=" * 80)
cursor.execute("PRAGMA table_info(player_tracking)")
columns = cursor.fetchall()
print("Columns:")
for col in columns:
    print(f"  {col['name']} ({col['type']})")
print()

# Check for amadou onana entries
print("=" * 80)
print("AMADOU ONANA ENTRIES")
print("=" * 80)
cursor.execute("""
    SELECT player_key, site_name, team_name, fixture, match_id, seen_at
    FROM player_tracking
    WHERE LOWER(player_key) LIKE '%amadou%onana%' OR LOWER(player_key) LIKE '%onana%amadou%'
    ORDER BY site_name, seen_at
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} entries:\n")
for i, row in enumerate(rows, 1):
    print(f"{i}. player_key: {row['player_key']!r}")
    print(f"   site_name: {row['site_name']!r}")
    print(f"   team_name: {row['team_name']!r}")
    print(f"   fixture: {row['fixture']!r}")
    print(f"   match_id: {row['match_id']!r}")
    print(f"   seen_at: {row['seen_at']!r}")
    print()

# Check for entries without match_id
print("=" * 80)
print("ENTRIES WITHOUT MATCH_ID")
print("=" * 80)
cursor.execute("""
    SELECT player_key, site_name, team_name, COUNT(*) as count
    FROM player_tracking
    WHERE match_id IS NULL
    GROUP BY player_key, site_name, team_name
    ORDER BY count DESC
    LIMIT 20
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} unique player/site/team combinations with NULL match_id:\n")
for row in rows:
    print(f"  {row['player_key']!r} @ {row['site_name']!r} ({row['team_name']!r}): {row['count']} entries")

# Check duplicate tracking entries
print("\n" + "=" * 80)
print("DUPLICATE TRACKING ENTRIES (same player/site/team)")
print("=" * 80)
cursor.execute("""
    SELECT player_key, site_name, team_name, COUNT(*) as count
    FROM player_tracking
    GROUP BY player_key, site_name, team_name
    HAVING count > 1
    ORDER BY count DESC
    LIMIT 20
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} player/site/team combinations with multiple entries:\n")
for row in rows:
    print(f"  {row['player_key']!r} @ {row['site_name']!r} ({row['team_name']!r}): {row['count']} entries")

conn.close()
