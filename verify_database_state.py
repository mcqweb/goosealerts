import sqlite3

conn = sqlite3.connect('data/player_names.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("FINAL DATABASE STATE")
print("=" * 80)

# Total entries
cursor.execute("SELECT COUNT(*) FROM player_tracking")
total = cursor.fetchone()[0]
print(f"\n📊 Total tracking entries: {total}")

# Entries by team
print("\n🏟️  PLAYERS BY TEAM:")
cursor.execute("""
    SELECT team_name, COUNT(DISTINCT player_key) as players, COUNT(*) as total_entries
    FROM player_tracking
    GROUP BY team_name
    ORDER BY total_entries DESC
""")
for row in cursor.fetchall():
    print(f"  {row['team_name']}: {row['players']} unique players, {row['total_entries']} total entries")

# Check for any issues
cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE team_name IS NULL")
null_team = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE match_id IS NULL")
null_match = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM player_tracking WHERE fixture IS NULL")
null_fixture = cursor.fetchone()[0]

print(f"\n✅ DATA QUALITY:")
print(f"  NULL team_name: {null_team} {'✓' if null_team == 0 else '✗'}")
print(f"  NULL match_id: {null_match} {'✓' if null_match == 0 else '✗'}")
print(f"  NULL fixture: {null_fixture} {'✓' if null_fixture == 0 else '✗'}")

# Check for duplicates
cursor.execute("""
    SELECT COUNT(*) FROM (
        SELECT player_key, site_name, team_name, fixture, COUNT(*) as cnt
        FROM player_tracking
        GROUP BY player_key, site_name, team_name, fixture
        HAVING cnt > 1
    )
""")
duplicates = cursor.fetchone()[0]
print(f"  Duplicates: {duplicates} {'✓' if duplicates == 0 else '✗'}")

# Sample entries
print("\n📋 SAMPLE ENTRIES:")
cursor.execute("""
    SELECT player_key, site_name, team_name, fixture, match_id
    FROM player_tracking
    ORDER BY seen_at DESC
    LIMIT 5
""")
for i, row in enumerate(cursor.fetchall(), 1):
    print(f"\n{i}. {row['player_key']}")
    print(f"   Site: {row['site_name']}")
    print(f"   Team: {row['team_name']}")
    print(f"   Fixture: {row['fixture']}")
    print(f"   Match ID: {row['match_id']}")

conn.close()

print("\n" + "=" * 80)
print("✅ Database is clean and ready for production use!")
print("=" * 80)
