#!/usr/bin/env python3
"""Inspect player tracking storage (SQLite or JSON fallback) and report entries
with missing team_name or fixture for debugging.

Usage: python scripts/inspect_player_tracking.py
"""
import sys
from pathlib import Path
# Ensure project root is on sys.path when run from scripts/ directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from player_names import get_backend_info, PLAYER_TRACKING_FILE

import sqlite3
import json

info = get_backend_info()
print(f"[INFO] Backend: {info['backend']}")
print(f"[INFO] DB exists: {info.get('db_exists')}")
print(f"[INFO] JSON tracking exists: {info.get('json_tracking_exists')}")

if info['backend'] == 'sqlite':
    db_path = 'data/player_names.db'
    if not Path(db_path).exists():
        print(f"[WARN] DB file not found at {db_path}")
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM player_tracking")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM player_tracking WHERE team_name IS NULL")
        null_team = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM player_tracking WHERE fixture IS NULL")
        null_fixture = cur.fetchone()[0]
        print(f"[DB] Total tracking rows: {total}")
        print(f"[DB] Rows with NULL team_name: {null_team}")
        print(f"[DB] Rows with NULL fixture: {null_fixture}")
        # Show a few examples of NULL team_name
        cur.execute("SELECT id, player_key, raw_name, site_name, match_id, team_name, fixture, seen_at FROM player_tracking WHERE team_name IS NULL LIMIT 10")
        rows = cur.fetchall()
        if rows:
            print("[DB] Sample rows with NULL team_name:")
            for r in rows:
                print(dict(r))
        else:
            print("[DB] No rows with NULL team_name found")
        # Show some rows with non-null team_name
        cur.execute("SELECT id, player_key, raw_name, site_name, match_id, team_name, fixture, seen_at FROM player_tracking WHERE team_name IS NOT NULL LIMIT 10")
        rows2 = cur.fetchall()
        if rows2:
            print("[DB] Sample rows with NON-NULL team_name:")
            for r in rows2:
                print(dict(r))
        else:
            print("[DB] No rows with NON-NULL team_name found")
        conn.close()

else:
    # JSON fallback
    from player_names import PLAYER_TRACKING_FILE
    p = Path(PLAYER_TRACKING_FILE)
    if not p.exists():
        print(f"[WARN] JSON tracking file not found at {PLAYER_TRACKING_FILE}")
    else:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        total = len(data)
        null_team = sum(1 for v in data.values() if not v.get('team_names'))
        null_fixture = sum(1 for v in data.values() if not v.get('fixtures'))
        print(f"[JSON] Total tracking entries: {total}")
        print(f"[JSON] Entries without team_names: {null_team}")
        print(f"[JSON] Entries without fixtures: {null_fixture}")
        # Print a few samples
        sample_no_team = [ (k, v) for k,v in data.items() if not v.get('team_names') ][:10]
        if sample_no_team:
            print("[JSON] Sample entries without team_names:")
            for k,v in sample_no_team:
                print(k, v)
        else:
            print("[JSON] No entries without team_names found")

print("[INFO] Inspection complete")