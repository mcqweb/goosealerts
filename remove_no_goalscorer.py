import sqlite3

conn = sqlite3.connect('data/player_names.db')
cursor = conn.cursor()

# Find No Goalscorer entries
cursor.execute("""
    SELECT COUNT(*) FROM player_tracking 
    WHERE LOWER(player_key) LIKE '%no%goalscorer%'
""")
before = cursor.fetchone()[0]
print(f"Found {before} 'No Goalscorer' entries")

# Delete them
cursor.execute("""
    DELETE FROM player_tracking 
    WHERE LOWER(player_key) LIKE '%no%goalscorer%'
""")
deleted = cursor.rowcount
conn.commit()
print(f"Deleted {deleted} entries")

# Show remaining count
cursor.execute("SELECT COUNT(*) FROM player_tracking")
remaining = cursor.fetchone()[0]
print(f"Total remaining entries: {remaining}")

conn.close()
