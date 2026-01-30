import sqlite3

conn = sqlite3.connect('data/player_names.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check sample fixtures
print("=" * 80)
print("SAMPLE FIXTURES")
print("=" * 80)
cursor.execute("""
    SELECT DISTINCT fixture 
    FROM player_tracking 
    WHERE team_name IS NULL AND fixture IS NOT NULL 
    LIMIT 10
""")
rows = cursor.fetchall()
print(f"Found {len(rows)} fixtures with NULL team_name:\n")
for row in rows:
    print(f"  {row['fixture']!r}")

# Update team_name from fixture
print("\n" + "=" * 80)
print("EXTRACTING TEAM FROM FIXTURE")
print("=" * 80)

cursor.execute("""
    SELECT id, fixture 
    FROM player_tracking 
    WHERE team_name IS NULL AND fixture IS NOT NULL
""")
rows = cursor.fetchall()

updated = 0
for row in rows:
    fixture = row['fixture']
    # Extract first team from "Team A v Team B" format
    parts = fixture.split(' v ')
    if len(parts) >= 2:
        team_name = parts[0].strip()
        cursor.execute("""
            UPDATE player_tracking 
            SET team_name = ? 
            WHERE id = ?
        """, (team_name, row['id']))
        updated += 1

conn.commit()
print(f"✓ Updated {updated} entries with team names extracted from fixture")

# Check remaining NULL team_name
cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE team_name IS NULL")
remaining = cursor.fetchone()[0]
print(f"✓ Remaining NULL team_name entries: {remaining}")

# Show stats by team
print("\n" + "=" * 80)
print("PLAYERS BY TEAM")
print("=" * 80)
cursor.execute("""
    SELECT team_name, COUNT(*) as count
    FROM player_tracking
    WHERE team_name IS NOT NULL
    GROUP BY team_name
    ORDER BY count DESC
""")
rows = cursor.fetchall()
for row in rows:
    print(f"  {row['team_name']}: {row['count']} players")

conn.close()
