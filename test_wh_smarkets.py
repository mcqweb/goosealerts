def test_smarkets_detection_handles_missing():
    """Ensure Smarkets detection logic doesn't raise and sets defaults when no Smarkets present."""
    player_exchanges = [{'site':'Betfair','lay_odds':7.0,'lay_size':32,'has_size':True}]

    sm_entries = [e for e in player_exchanges if 'smarkets' in (e.get('site') or '').lower()]
    assert sm_entries == []

    # Default values should remain None/False when no Smarkets entries
    has_smarkets = False
    smarkets_price = None
    smarkets_liquidity = None

    if sm_entries:
        has_smarkets = True
        best_sm = min(sm_entries, key=lambda x: x.get('lay_odds', float('inf')))
        smarkets_price = best_sm.get('lay_odds')
        smarkets_liquidity = best_sm.get('lay_size') or best_sm.get('liquidity') or best_sm.get('size')

    assert has_smarkets is False and smarkets_price is None and smarkets_liquidity is None


def test_smarkets_detection_with_entry():
    """Ensure the detection finds the Smarkets entry and picks the lowest lay odds."""
    player_exchanges = [
        {'site':'Betfair','lay_odds':7.0,'lay_size':32,'has_size':True},
        {'site':'Smarkets','lay_odds':6.5,'liquidity':10},
        {'site':'Smarkets_ws','lay_odds':6.6,'liquidity':5}
    ]

    sm_entries = [e for e in player_exchanges if 'smarkets' in (e.get('site') or '').lower()]
    assert len(sm_entries) == 2

    has_smarkets = False
    smarkets_price = None
    smarkets_liquidity = None

    if sm_entries:
        has_smarkets = True
        best_sm = min(sm_entries, key=lambda x: x.get('lay_odds', float('inf')))
        smarkets_price = best_sm.get('lay_odds')
        smarkets_liquidity = best_sm.get('lay_size') or best_sm.get('liquidity') or best_sm.get('size')

    assert has_smarkets
    assert smarkets_price == 6.5
    assert smarkets_liquidity == 10