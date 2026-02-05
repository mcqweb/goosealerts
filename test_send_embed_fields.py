#!/usr/bin/env python3
"""Unit tests for embed field normalization in send_discord_embed"""

from pathlib import Path
import sys
import types
# Provide a minimal stub for optional external dependency used at module-import time
# so unit tests can run without requiring all environment packages.
if 'unidecode' not in sys.modules:
    sys.modules['unidecode'] = types.SimpleNamespace(unidecode=lambda s: s)

sys.path.insert(0, str(Path(__file__).parent))

from virgin_goose import send_discord_embed, DISCORD_ENABLED


def test_send_discord_embed_accepts_dict_fields(monkeypatch):
    """Fields provided as dicts should be normalized and not raise."""
    # Disable network call by toggling DISCORD_ENABLED temporarily
    monkeypatch.setattr('virgin_goose.DISCORD_ENABLED', False)

    fields = [
        {"name": "Match", "value": "A vs B", "inline": False},
        {"name": "Odds", "value": "2.4", "inline": True}
    ]

    # Should return None (function has no explicit return) and not raise
    send_discord_embed("Title", "Desc", fields, channel_id='dummy', bot_token='dummy')


def test_send_discord_embed_accepts_tuple_fields(monkeypatch):
    monkeypatch.setattr('virgin_goose.DISCORD_ENABLED', False)

    fields = [
        ("Match", "A vs B"),
        ("Odds", "2.4", False)
    ]

    send_discord_embed("Title", "Desc", fields, channel_id='dummy', bot_token='dummy')


def test_send_discord_embed_mixed_fields(monkeypatch):
    monkeypatch.setattr('virgin_goose.DISCORD_ENABLED', False)

    fields = [
        {"name": "Match", "value": "A vs B"},
        ("Confirmed Starter", "✅"),
        ("Extra", "val", True)
    ]

    send_discord_embed("Title", "Desc", fields, channel_id='dummy', bot_token='dummy')


def test_send_alert_to_destinations_with_dict_fields(monkeypatch):
    """Integration-style unit test: send_alert_to_destinations should accept dict-form fields and call send_discord_embed."""
    # Provide a minimal stub for unidecode again in case of isolated test runs
    import sys, types
    if 'unidecode' not in sys.modules:
        sys.modules['unidecode'] = types.SimpleNamespace(unidecode=lambda s: s)

    # Capture calls to send_discord_embed
    called = {}
    def fake_send(title, description, fields, colour=0x3AA3E3, channel_id=None, footer=None, icon=None, bot_token=None, footer_url=None):
        called['title'] = title
        called['description'] = description
        called['fields'] = fields
        called['channel_id'] = channel_id
        return None

    monkeypatch.setattr('virgin_goose.send_discord_embed', fake_send)

    # Build a minimal config with one destination
    cfg = {
        'kwiff': [
            {
                'name': 'kw_test',
                'enabled': True,
                'bot_token': 'dummy-token',
                'channel_id': '123',
                'threshold': 0
            }
        ]
    }

    # Provide dict-style fields (as produced in the kwiff flow)
    fields = [
        {"name": "Match", "value": "Test Match", "inline": False},
        {"name": "Kwiff Odds", "value": "4.7", "inline": True}
    ]

    sent = __import__('virgin_goose').send_alert_to_destinations('kwiff', 'T', 'D', fields, footer='F', rating=100, config=cfg)
    assert sent == 1
    assert 'fields' in called and isinstance(called['fields'], list)
    assert called['fields'][0]['name'] == 'Match' and called['fields'][0]['value'] == 'Test Match'


def test_format_kwiff_footer():
    from virgin_goose import format_kwiff_footer

    o05_markets = {'goals': {'market_name': 'Total Goals', 'outcome_name': 'Over 0.5'}}
    out = format_kwiff_footer(o05_markets)
    assert out == '♿ AGS + O0.5'

    sot_markets = {'goals': {'market_name': 'Shots On Target', 'outcome_name': 'Shots On Target (incl. OT)'}}
    out2 = format_kwiff_footer(sot_markets)
    assert out2 == '♿ AGS + SoT'

    unknown_markets = {'goals': {'market_name': 'Some Market', 'outcome_name': 'Special Case'}}
    out3 = format_kwiff_footer(unknown_markets)
    assert out3.startswith('♿ AGS')


def test_format_lay_prices_bolds_best():
    """The helper should bold the best (lowest) lay option and append sizes correctly."""
    from virgin_goose import format_lay_prices

    exchanges = [
        {'site': 'Betfair', 'lay_odds': 11.0, 'lay_size': 13},
        {'site': 'Smarkets', 'lay_odds': 9.6, 'lay_size': 5}
    ]

    out = format_lay_prices(exchanges)
    assert "**Smarkets @ 9.6** (£5)" in out
    assert "Betfair @ 11.0 (£13)" in out


def test_build_kwiff_message_ruben_format():
    from virgin_goose import build_kwiff_message

    title, desc, fields, footer = build_kwiff_message(
        player_name='Ruben Loftus-Cheek',
        mname='Bologna v AC Milan',
        ko_str='19:45',
        cname='Serie A',
        kwiff_odds=7.0,
        lay_price=7.0,
        lay_prices_text='Betfair @ 7 (£32)',
        midid=12345,
        best_site='Betfair',
        is_confirmed=True,
        markets={'goals': {'market_name': 'Total Goals', 'outcome_name': 'Over 0.5'}},
        rating_pct=100
    )

    assert title == 'Ruben Loftus-Cheek - 7/7 (100%)'
    assert '**Bologna v AC Milan** (19:45)' in desc
    assert 'Serie A' in desc
    assert 'Lay Prices' in desc and 'Betfair @ 7' in desc
    assert '[Betfair Market](https://www.betfair.com/exchange/plus/football/market/12345)' in desc
    assert ('Confirmed Starter', '✅') in fields
    assert footer == '♿ AGS + O0.5'
