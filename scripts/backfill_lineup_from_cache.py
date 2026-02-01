import json, sqlite3, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from virgin_goose import fetch_lineups, fetch_matches_from_oddsmatcha

DB = 'data/player_names.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT DISTINCT match_id FROM player_tracking WHERE site_name='lineup' AND team_name IS NULL AND match_id IS NOT NULL")
rows = cur.fetchall()
print('Found', len(rows), 'match_ids to process')

# Load cached matches if available
cache_file = os.path.join('cache', 'matches_today.json')
cache_matches = {}
if os.path.exists(cache_file):
    try:
        with open(cache_file, 'r', encoding='utf-8') as cf:
            cache = json.load(cf)
            for m in cache.get('matches', []):
                cache_matches[str(m.get('id'))] = m
    except Exception as e:
        print('Failed to read cache:', e)

processed = 0
updated_total = 0
for r in rows:
    mid = r['match_id']
    fallback = cache_matches.get(str(mid))
    print('Processing match', mid, 'fallback present=', bool(fallback))
    starters = fetch_lineups(mid, fallback_match=fallback)
    # fetch_lineups will backfill DB rows where possible
    processed += 1

print(f'Done. Processed {processed} match ids.')
conn.close()
