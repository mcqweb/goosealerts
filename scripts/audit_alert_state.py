import json, os
from virgin_goose import _normalize_alert_key_player

state_files = [
    'state/goose_alert_state.json',
    'state/arb_alert_state.json',
    'state/WH_alert_state.json',
    'state/WH_smarkets_alert_state.json',
    'state/lad_alert_state.json',
    'state/test_alert_state.json'
]

results = {}
for sf in state_files:
    if not os.path.exists(sf):
        continue
    with open(sf, 'r', encoding='utf-8') as f:
        try:
            st = json.load(f) or {}
        except Exception:
            continue
    alerted = st.get('alerted', {}) if isinstance(st, dict) else {}
    collisions = []
    for raw_key in alerted.keys():
        # raw_key format: {match}_{player}[_{market}]
        parts = raw_key.split('_')
        if not parts:
            continue
        match_id = parts[0]
        player_and_suffix = '_'.join(parts[1:])
        norm_player = _normalize_alert_key_player(player_and_suffix)
        norm_key = f"{match_id}_{norm_player}"
        if norm_key != raw_key and norm_key in alerted:
            collisions.append((raw_key, norm_key))
    if collisions:
        results[sf] = collisions

if not results:
    print('No normalized collisions found in state files.')
else:
    for sf, cols in results.items():
        print(f"File: {sf}")
        for raw, norm in cols[:50]:
            print(f"  {raw} -> {norm}")
