import sqlite3

conn = sqlite3.connect('data/player_names.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, raw_name, site_name, team_name, fixture, match_id FROM player_tracking WHERE site_name='lineup' LIMIT 200")
rows = cur.fetchall()
print('Rows:', len(rows))
for r in rows:
    print({
        'id': r['id'],
        'raw_name': r['raw_name'],
        'team_name': r['team_name'],
        'fixture': r['fixture'],
        'match_id': r['match_id']
    })
conn.close()