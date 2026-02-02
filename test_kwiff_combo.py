#!/usr/bin/env python3
"""Tests for Kwiff combo odds and helper parsing"""

import asyncio
import sys
from pathlib import Path
import json

# Add kwiff to path
sys.path.insert(0, str(Path(__file__).parent))

from kwiff import KwiffClient, prepare_combo_ids, build_combo_data_sync
from kwiff.match_cache import KwiffMatchCache


def test_kwiff_client_combo_odds_live():
    """Integration test: call Kwiff WebSocket to get combo odds for known Sunderland combo."""
    async def run():
        client = KwiffClient()
        async with client as c:
            # Known example from debugging session
            event_id = 11489081
            outcome_ids = [1226809867, 1247501707]
            resp = await c.get_combo_odds(event_id, outcome_ids)
            print("Combo response:", resp)
            assert resp is not None
            assert resp.get("odds") is not None and resp.get("odds") > 0
    asyncio.run(run())


def test_prepare_combo_ids_from_sample_cache():
    """Unit test: craft a sample event details payload in cache and verify prepare_combo_ids extracts the right ids."""
    cache = KwiffMatchCache(ttl_minutes=60)
    sample = {
        "data": {
            "result": {
                "id": 11489081,
                "markets": [
                    {
                        "id": 10,
                        "name": "Player Anytime Scorer",
                        "outcomes": [
                            {"id": 1226809867, "name": "John Sunderland"},
                            {"id": 111, "name": "Other Player"}
                        ]
                    },
                    {
                        "id": 20,
                        "name": "Total Goals",
                        "outcomes": [
                            {"id": 1247501707, "name": "Over 0.5"},
                            {"id": 125, "name": "Under 0.5"}
                        ]
                    }
                ]
            }
        }
    }

    cache.set("11489081", sample)

    combo = prepare_combo_ids("11489081", "John Sunderland")
    print("Prepared combo ids:", combo)
    assert combo is not None
    assert combo["outcome_ids"] == [1226809867, 1247501707]
    assert combo["player_name"] == "John Sunderland"


def test_prepare_combo_ids_sot_fallback():
    """Unit test: when Total Goals O0.5 isn't present, ensure Shots On Target (incl. OT) for the player is used as fallback."""
    cache = KwiffMatchCache(ttl_minutes=60)
    sample = {
        "data": {
            "result": {
                "id": 999999,
                "markets": [
                    {
                        "id": 10,
                        "name": "Anytime Goalscorer",
                        "outcomes": [
                            {"id": 1001, "name": "John Sunderland"},
                            {"id": 111, "name": "Other Player"}
                        ]
                    },
                    {
                        "id": 20,
                        "name": "Shots On Target (incl. OT)",
                        "outcomes": [
                            {"id": 2001, "name": "John Sunderland"},
                            {"id": 201, "name": "No Shot"}
                        ]
                    }
                ]
            }
        }
    }

    cache.set("999999", sample)

    combo = prepare_combo_ids("999999", "John Sunderland")
    print("Prepared combo ids (SOT fallback):", combo)
    assert combo is not None
    assert combo["outcome_ids"] == [1001, 2001]


def test_prepare_combo_ids_vedat_live():
    """Integration test: fetch live event details for 11505695 (Mallorca v Sevilla) and ensure Vedat Muriqi combo builds."""
    async def run():
        client = KwiffClient()
        async with client as c:
            details = await c.get_event_details(11505695)
            # Cache details
            from kwiff.match_cache import cache_match_details
            cache_match_details('11505695', details)
            combo_ids = prepare_combo_ids('11505695', 'Vedat Muriqi')
            print('Prepared combo ids for Vedat:', combo_ids)
            assert combo_ids is not None
            combo = await c.get_combo_odds(combo_ids['event_id'], combo_ids['outcome_ids'])
            print('Combo odds response:', combo)
            assert combo is not None and combo.get('odds') and combo.get('odds') > 0
    import asyncio
    asyncio.run(run())
