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