#!/usr/bin/env python3
"""
Interactive manual mapping helper for Kwiff events.

Usage:
    python kwiff/server/manual_map.py [--dry-run] [--limit N]

Features:
- Lists Kwiff events from today's `events_YYYYMMDD.json` (falls back to yesterday)
- Shows current mapping state from `event_mappings.json`
- For unmapped or TODO-mapped events it fetches candidate matches from Oddsmatcha and suggests potential Betfair IDs
- Prompts the user to select a candidate, enter a Betfair market id manually, mark as TODO, skip, or quit
- Saves mappings back to `event_mappings.json` (atomic save)

This is intentionally conservative: it only writes mappings the user confirms.
"""

from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from auto_map_events import (
    get_events_file,
    load_events_file,
    load_event_mappings,
    save_event_mappings,
    fetch_oddsmatcha_matches,
    extract_ids,
    match_teams,
)


def find_candidates_for_event(ev: Dict, oddsmatcha_data: Dict) -> List[Dict]:
    """Return candidate matches from Oddsmatcha that match at least one team name."""
    candidates = []
    home = ev.get('homeTeam', {}).get('name') or ev.get('home') or ev.get('homeTeam')
    away = ev.get('awayTeam', {}).get('name') or ev.get('away') or ev.get('awayTeam')

    # Oddsmatcha response structure may vary; try to find a list of matches
    matches = []
    if isinstance(oddsmatcha_data, dict):
        # Common shapes: data['matches'] or top-level list
        if 'matches' in oddsmatcha_data and isinstance(oddsmatcha_data['matches'], list):
            matches = oddsmatcha_data['matches']
        elif isinstance(oddsmatcha_data.get('data', {}), dict) and isinstance(oddsmatcha_data['data'].get('matches', []), list):
            matches = oddsmatcha_data['data']['matches']
        else:
            # Fallback to any list-valued top-level
            for v in oddsmatcha_data.values():
                if isinstance(v, list):
                    matches = v
                    break
    elif isinstance(oddsmatcha_data, list):
        matches = oddsmatcha_data

    for m in matches:
        # Compare team names heuristically
        am_home = m.get('homeName') or m.get('home') or m.get('homeTeam')
        am_away = m.get('awayName') or m.get('away') or m.get('awayTeam')
        if match_teams(home, away, am_home, am_away):
            # extract any IDs (betfair, smarkets)
            ids = extract_ids(m)
            m_copy = m.copy()
            m_copy['_ids'] = ids
            candidates.append(m_copy)
    return candidates


def prompt_user_choice(ev: Dict, candidates: List[Dict]) -> Optional[str]:
    """Prompt user for action and return chosen betfair_id or 'TODO' or None (skip)."""
    print("\n--- Unmapped Kwiff Event ---")
    k_id = ev.get('id') or ev.get('eventId')
    home = ev.get('homeTeam', {}).get('name') or ev.get('home') or ev.get('homeTeam')
    away = ev.get('awayTeam', {}).get('name') or ev.get('away') or ev.get('awayTeam')
    start = ev.get('startDate') or ev.get('start')
    print(f"Kwiff ID: {k_id}  |  {home} v {away}  |  start: {start}")

    if candidates:
        print('\nCandidates from Oddsmatcha API:')
        for i, c in enumerate(candidates, 1):
            ids = c.get('_ids', {})
            b = ids.get('betfair_id') or 'N/A'
            s = ids.get('smarkets_id') or 'N/A'
            apid = c.get('id') or c.get('match_id') or '<no-id>'
            am_home = c.get('homeName') or c.get('home') or ''
            am_away = c.get('awayName') or c.get('away') or ''
            print(f"  [{i}] {am_home} v {am_away}  (api_id={apid})  betfair={b}  smarkets={s}")
    else:
        print('\nNo candidates found via Oddsmatcha.')

    print('\nOptions:')
    print('  number  -> choose candidate by index (uses its Betfair id)')
    print('  m       -> enter Betfair market id manually')
    print('  t       -> mark as TODO (skip mapping for now)')
    print('  s       -> skip (leave unmapped)')
    print('  d       -> print full event JSON for debugging')
    print('  q       -> quit now')

    while True:
        choice = input('Choice: ').strip()
        if not choice:
            continue
        if choice.lower() == 'q':
            return 'QUIT'
        if choice.lower() == 's':
            return None
        if choice.lower() == 't':
            return 'TODO'
        if choice.lower() == 'd':
            try:
                print(json.dumps(ev, indent=2))
            except Exception:
                print(ev)
            continue
        if choice.lower() == 'm':
            bid = input('Enter Betfair market id (numeric): ').strip()
            if bid:
                return bid
            else:
                continue
        # number
        try:
            n = int(choice)
            if 1 <= n <= len(candidates):
                cand = candidates[n-1]
                ids = cand.get('_ids', {})
                bid = ids.get('betfair_id')
                if bid:
                    return str(bid)
                else:
                    print('Selected candidate does not have a Betfair id; you can still enter it manually with m.')
            else:
                print('Invalid index')
        except ValueError:
            print('Unknown option')


def main(dry_run: bool = False, limit: Optional[int] = None):
    events_file = get_events_file()
    if not events_file:
        print('No events file found for today or yesterday. Run fetch first.')
        return

    events = load_events_file(events_file)
    mappings = load_event_mappings()
    mapped = mappings.get('events', {}) if isinstance(mappings, dict) else {}

    oddsa = fetch_oddsmatcha_matches()

    unmapped = []
    for ev in events:
        kwid = str(ev.get('id') or ev.get('eventId') or ev.get('eventId'))
        if not kwid:
            continue
        mdata = mapped.get(kwid)
        if not mdata or not mdata.get('betfair_id') or mdata.get('betfair_id') == 'TODO':
            unmapped.append(ev)

    print(f"Total events loaded: {len(events)}. Unmapped or TODO: {len(unmapped)}")

    count = 0
    for ev in unmapped:
        if limit and count >= limit:
            break
        k_id = str(ev.get('id') or ev.get('eventId'))
        candidates = find_candidates_for_event(ev, oddsa)
        choice = prompt_user_choice(ev, candidates)
        if choice == 'QUIT':
            print('Quitting without further changes')
            break
        if choice is None:
            print(f"Skipping Kwiff event {k_id}")
            count += 1
            continue
        # choice is 'TODO' or a betfair id
        if choice == 'TODO':
            print(f"Marking Kwiff {k_id} as TODO")
            mapped[k_id] = {'betfair_id': 'TODO', 'description': 'manually marked TODO', 'updated_at': datetime.utcnow().isoformat()}
        else:
            bf = str(choice)
            print(f"Mapping Kwiff {k_id} -> Betfair {bf}")
            mapped[k_id] = {'betfair_id': bf, 'description': 'manually mapped', 'updated_at': datetime.utcnow().isoformat()}

        if not dry_run:
            saved = save_event_mappings({'events': mapped})
            if saved:
                print('Saved mappings')
            else:
                print('Failed to save mappings')
        else:
            print('Dry-run mode; not saving changes')

        count += 1

    print('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manual Kwiff -> Betfair mapping helper')
    parser.add_argument('--dry-run', action='store_true', help='Do not persist changes')
    parser.add_argument('--limit', type=int, help='Limit number of unmapped events to process')
    args = parser.parse_args()
    main(dry_run=args.dry_run, limit=args.limit)
