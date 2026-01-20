from betfair import Betfair

bf = Betfair()
odds = bf.fetch_odds_for_match('35004095')  # Benfica vs Napoli
print(f'Total players: {len(odds)}')
print('\nBetfair players (first 20):')
for o in odds[:20]:
    print(f'  {o["outcome"]}')

# Check for specific names
search_names = ['ivanovic', 'hojlund', 'lukaku']
print('\nSearching for specific players:')
for search in search_names:
    matches = [o['outcome'] for o in odds if search.lower() in o['outcome'].lower()]
    if matches:
        print(f'  {search}: {matches}')
    else:
        print(f'  {search}: NOT FOUND')
