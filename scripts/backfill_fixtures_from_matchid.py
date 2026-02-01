#!/usr/bin/env python3
"""Backfill fixture and team_name for player_tracking rows that have a match_id but missing fixture.

Usage: python scripts/backfill_fixtures_from_matchid.py
"""
import sqlite3
from pathlib import Path
import requests
import json
import re

DB = 'data/player_names.db'
if not Path(DB).exists():
    print(f"[ERROR] DB not found at {DB}")
    raise SystemExit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT DISTINCT match_id FROM player_tracking WHERE match_id IS NOT NULL AND fixture IS NULL")
rows = cur.fetchall()
print(f"Found {len(rows)} match_ids with missing fixture")
updated = 0
for r in rows:
    mid = r['match_id']
    # Try cache first
    fixture = None
    try:
        cache_file = Path('cache/matches_today.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as cf:
                cache = json.load(cf)
            for m in cache.get('matches', []):
                if str(m.get('id')) == str(mid):
                    home = m.get('home_team')
                    away = m.get('away_team')
                    if home and away:
                        fixture = f"{home} v {away}"
                        break
    except Exception:
        pass

    if not fixture:
        # Fallback to API call
        try:
            api = f"https://api.oddsmatcha.uk/matches/{mid}"
            resp = requests.get(api, timeout=10)
            if resp.ok:
                data = resp.json()
                home = data.get('home_team') or (data.get('home_lineup') or {}).get('team_name')
                away = data.get('away_team') or (data.get('away_lineup') or {}).get('team_name')
                if home and away:
                    fixture = f"{home} v {away}"
        except Exception:
            pass

    if fixture:
        # Extract home team for team_name column
        home_team = None
        m = re.match(r"^(.+?)\s+v\s+(.+)$", fixture)
        if m:
            home_team = m.group(1).strip()
        cur.execute("UPDATE player_tracking SET fixture = ?, team_name = ? WHERE match_id = ? AND fixture IS NULL", (fixture, home_team, mid))
        if cur.rowcount:
            updated += cur.rowcount
            print(f"Updated match {mid} -> {fixture} ({cur.rowcount} rows)")


conn.commit()
print(f"Done. Updated {updated} rows.\nNext: run scripts/extract_teams_from_fixtures.py to populate team_name from fixture.")
conn.close()