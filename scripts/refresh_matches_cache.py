import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from virgin_goose import fetch_matches_from_oddsmatcha

print('Refreshing matches cache...')
matches = fetch_matches_from_oddsmatcha(next_days=0)
print('Fetched', len(matches), 'matches')
