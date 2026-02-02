#!/usr/bin/env python3
"""
Kwiff Player Data Helpers

Functions to extract player markets and build combo data from cached Kwiff match details.
This implements heuristics to find player AGS selections and the Total Goals O0.5 outcome
(or fallback to Player Shot On Target) and to request combo odds from the Kwiff WebSocket.
"""

from typing import Dict, List, Optional, Any
from .match_cache import get_cached_match_details
from .kwiff_client import KwiffClient
import asyncio


def _safe_get_markets(details: Dict) -> List[Dict]:
    """Return a list of market dicts from the raw event details."""
    if not isinstance(details, dict):
        return []
    result = details.get("data", {}).get("result", {})
    # Different payloads put market lists in different places. Try common locations.
    markets = (
        result.get("markets")
        or result.get("details", {}).get("offers")
        or details.get("data", {}).get("markets")
        or details.get("details", {}).get("offers")
        or details.get("markets")
        or details.get("offers")
        or []
    )
    if isinstance(markets, dict):
        # Some payloads might wrap markets in an object
        markets = markets.get("items") or []
    return markets if isinstance(markets, list) else []


def get_player_markets(kwiff_event_id: str) -> Optional[Dict[str, List[Dict]]]:
    """
    Extract player markets from cached match details.

    Returns a mapping of player_name -> list of markets with selection IDs.
    """
    details = get_cached_match_details(str(kwiff_event_id))
    if not details:
        return None

    markets = _safe_get_markets(details)
    player_markets: Dict[str, List[Dict]] = {}

    for market in markets:
        m_id = market.get("id") or market.get("marketId") or market.get("market_id")
        m_name = (market.get("name") or market.get("marketName") or "").strip()
        selections = market.get("outcomes") or market.get("selections") or market.get("eventSelections") or market.get("items") or []

        for sel in selections:
            s_id = sel.get("id") or sel.get("selectionId") or sel.get("outcomeId") or sel.get("selectionId") or sel.get("outcomeId")
            s_name = (sel.get("name") or sel.get("label") or sel.get("description") or sel.get("outcomeName") or sel.get("outcome_name") or "").strip()
            if not s_id or not s_name:
                continue

            # If the selection name looks like a player name, index it
            # Heuristic: contains a space and not a simple numeric outcome like '0' or 'Over 0.5'
            if " " in s_name and any(c.isalpha() for c in s_name):
                # Add market info for this player
                player_markets.setdefault(s_name, []).append({
                    "market_type": m_name,
                    "market_id": m_id,
                    "selection_id": s_id,
                    "outcome_name": s_name,
                })

            # Some player markets include the player name in the selection name with prefix/suffix
            # Also include for exact matches to support fuzzy names later
            # (We leave fuzzy matching to higher layers.)

    return player_markets if player_markets else None


def find_player_in_match(kwiff_event_id: str, player_name: str) -> Optional[Dict]:
    """Find a specific player's market entries (exact match first)."""
    player_markets = get_player_markets(kwiff_event_id)
    if not player_markets:
        return None

    # Exact match
    if player_name in player_markets:
        return {"player_name": player_name, "markets": player_markets[player_name]}

    # Case-insensitive & comma-swapped search
    target = player_name.lower()
    for name, markets in player_markets.items():
        n_lower = name.lower()
        # direct case-insensitive
        if n_lower == target:
            return {"player_name": name, "markets": markets}
        # handle "Last, First" vs "First Last"
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            swapped = " ".join(reversed(parts)).lower()
            if swapped == target:
                return {"player_name": name, "markets": markets}

    # Substring search (including swapped forms)
    for name, markets in player_markets.items():
        n_lower = name.lower()
        if target in n_lower:
            return {"player_name": name, "markets": markets}
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            swapped = " ".join(reversed(parts)).lower()
            if target in swapped:
                return {"player_name": name, "markets": markets}

    return None


def _find_goals_o05_selection(details: Dict) -> Optional[Dict]:
    """Find a Total Goals Over 0.5 selection in the event markets."""
    markets = _safe_get_markets(details)
    for market in markets:
        m_name = (market.get("name") or market.get("marketName") or "").lower()
        if "total goals" in m_name or "goals" in m_name:
            selections = market.get("outcomes") or market.get("selections") or market.get("items") or []
            for sel in selections:
                s_id = sel.get("id") or sel.get("selectionId") or sel.get("outcomeId")
                s_name = (sel.get("name") or sel.get("label") or sel.get("outcomeName") or sel.get("outcome_name") or "").lower()
                # Look for Over 0.5 variants
                if "0.5" in s_name and ("over" in s_name or s_name.startswith("o") or "o0.5" in s_name or s_name.endswith("0.5")):
                    return {"market_id": market.get("id") or market.get("marketId"), "selection_id": s_id, "outcome_name": s_name, "market_name": m_name}
    return None


def _find_player_sot_selection(details: Dict, player_name: str) -> Optional[Dict]:
    """Find a player's Shots On Target market selection (fallback).

    This function is tolerant of variants like "Shots On Target (incl. OT)" and similar.
    """
    markets = _safe_get_markets(details)
    for market in markets:
        m_name = (market.get("name") or market.get("marketName") or "").lower()
        # Detect common SOT variants including explicit "incl. OT" forms
        if any(k in m_name for k in ("shot", "shots on target", "sot", "incl ot", "incl. ot")):
            selections = market.get("outcomes") or market.get("selections") or market.get("items") or []
            for sel in selections:
                s_id = sel.get("id") or sel.get("selectionId") or sel.get("outcomeId")
                s_name = (sel.get("name") or sel.get("label") or sel.get("outcomeName") or sel.get("outcome_name") or "").lower()
                if player_name.lower() in s_name:
                    return {"market_id": market.get("id") or market.get("marketId"), "selection_id": s_id, "outcome_name": s_name, "market_name": m_name}
    return None


def prepare_combo_ids(kwiff_event_id: str, player_name: str) -> Optional[Dict]:
    """Prepare the outcome IDs for a combo between player's AGS and Goals O0.5 (or SOT fallback)."""
    details = get_cached_match_details(str(kwiff_event_id))
    if not details:
        return None

    # Find player AGS selection
    player_entry = find_player_in_match(kwiff_event_id, player_name)
    if not player_entry:
        return None

    # Find an AGS-like market for the player
    ags_sel = None
    # Prefer an "Anytime" market when available
    for m in player_entry["markets"]:
        m_name = (m.get("market_type") or "").lower()
        if "anytime" in m_name:
            ags_sel = {"market_id": m.get("market_id"), "selection_id": m.get("selection_id"), "market_name": m.get("market_type")}
            break
    # Otherwise look for other scorer-like markets
    if not ags_sel:
        for m in player_entry["markets"]:
            m_name = (m.get("market_type") or "").lower()
            if "scorer" in m_name or "to score" in m_name or "any time" in m_name:
                ags_sel = {"market_id": m.get("market_id"), "selection_id": m.get("selection_id"), "market_name": m.get("market_type")}
                break
    # If not matched by name, take the first player market
    if not ags_sel and player_entry["markets"]:
        m = player_entry["markets"][0]
        ags_sel = {"market_id": m.get("market_id"), "selection_id": m.get("selection_id"), "market_name": m.get("market_type")}

    if not ags_sel:
        return None

    # Find Goals O0.5
    goals_sel = _find_goals_o05_selection(details)

    # Fallback: player's Shots On Target
    if not goals_sel:
        goals_sel = _find_player_sot_selection(details, player_entry["player_name"])

    if not goals_sel:
        return None

    # Ensure selection ids are integers
    try:
        ags_id = int(ags_sel["selection_id"])
        goals_id = int(goals_sel["selection_id"])
    except Exception:
        return None

    return {
        "event_id": int(kwiff_event_id),
        "player_name": player_entry["player_name"],
        "ags": ags_sel,
        "goals": goals_sel,
        "outcome_ids": [ags_id, goals_id]
    }


async def build_combo_data(kwiff_event_id: str, player_name: str, client: Optional[KwiffClient] = None) -> Optional[Dict]:
    """Build a combo and fetch its live odds from Kwiff.

    Returns a dict:
    {
        'event_id': int,
        'player_name': str,
        'outcome_ids': [int, int],
        'odds': float,
        'fractionalOdds': str,
        'raw': dict,
        'markets': { 'ags': {...}, 'goals': {...} }
    }
    """
    combo_ids = prepare_combo_ids(kwiff_event_id, player_name)
    if not combo_ids:
        return None

    close_client = False
    if client is None:
        client = KwiffClient()
        connected = await client.connect()
        if not connected:
            return None
        close_client = True

    try:
        resp = await client.get_combo_odds(combo_ids["event_id"], combo_ids["outcome_ids"])
        if not resp:
            return None

        return {
            "event_id": combo_ids["event_id"],
            "player_name": combo_ids["player_name"],
            "outcome_ids": combo_ids["outcome_ids"],
            "odds": resp.get("odds"),
            "fractionalOdds": resp.get("fractionalOdds"),
            "raw": resp.get("raw"),
            "markets": {"ags": combo_ids["ags"], "goals": combo_ids["goals"]}
        }

    finally:
        if close_client:
            await client.disconnect()


def build_combo_data_sync(kwiff_event_id: str, player_name: str) -> Optional[Dict]:
    """Synchronous wrapper for build_combo_data."""
    return asyncio.run(build_combo_data(kwiff_event_id, player_name))


def get_player_market_odds(
    kwiff_event_id: str,
    player_name: str,
    market_type: str
) -> Optional[Dict]:
    """
    Get odds for a specific player market (AGS, TOM, HAT).

    Note: this function will only return odds if the selection data includes a price; otherwise
    use `build_combo_data` to request combo odds from the socket.
    """
    player_markets = get_player_markets(kwiff_event_id)
    if not player_markets:
        return None

    # Look for the player entry
    entry = find_player_in_match(kwiff_event_id, player_name)
    if not entry:
        return None

    for market in entry["markets"]:
        m_name = (market.get("market_type") or "").lower()
        if market_type.lower() in m_name or market_type == m_name:
            # Per-selection odds rarely available in cached event.get; return selection reference
            return {
                "odds": market.get("odds"),
                "market_id": market.get("market_id"),
                "selection_id": market.get("selection_id"),
                "available": True
            }
    return None


def get_all_players_in_match(kwiff_event_id: str) -> List[str]:
    """Get list of all players available in a match."""
    player_markets = get_player_markets(kwiff_event_id)
    if not player_markets:
        return []
    return list(player_markets.keys())


def is_market_available(
    kwiff_event_id: str,
    player_name: str,
    market_type: str
) -> bool:
    """Check if a specific player market is available."""
    odds_data = get_player_market_odds(kwiff_event_id, player_name, market_type)
    return odds_data is not None and odds_data.get('available', False)


# Example usage
if __name__ == "__main__":
    print("Kwiff Player Data Helpers")
    print("\nThese functions extract player markets from cached match details and can request combo odds.")
    print("\nExample usage:")
    print("""
    from kwiff.player_helpers import build_combo_data_sync

    combo = build_combo_data_sync(
        kwiff_event_id="11489081",
        player_name="Example Player"
    )
    if combo:
        print(combo)
    """)
