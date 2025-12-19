"""Test script: build combos between First/Anytime goalscorer.

Place this in the project root and run: `python -m ladbrokes_alerts.test_build_combos`
or run directly from root: `python test_build_combos.py`.
"""

import argparse
import logging
from itertools import product
from typing import Dict, List, Optional
import os
import sys

# Ensure package can be imported when executed from project root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ladbrokes_alerts.client import LadbrokesAlerts


MATCH_ID_DEFAULT = 253579498


def extract_event_bEId(drilldown: Dict) -> str:
    try:
        ss = drilldown.get("SSResponse", {})
        first = ss.get("children", [None])[0]
        event = first.get("event", {})
        ext = event.get("extIds", "")
        if ext and "," in ext:
            parts = ext.split(",")
            if len(parts) >= 2:
                return parts[1]
    except Exception:
        pass
    return ""


def find_market_outcomes(drilldown: Dict, token: str) -> List[Dict]:
    results: List[Dict] = []
    ss = drilldown.get("SSResponse", {})
    children = ss.get("children", [])
    if not children:
        return results

    event = children[0].get("event", {})
    for child in event.get("children", []):
        if "market" not in child:
            continue
        market = child["market"]
        name = market.get("name", "")
        if token.lower() not in name.lower():
            continue

        market_ext_ids = market.get("extIds", "")
        bMId = ""
        if market_ext_ids and "," in market_ext_ids:
            parts = market_ext_ids.split(",")
            if len(parts) >= 2:
                bMId = parts[1]

        for oc in market.get("children", []):
            if "outcome" not in oc:
                continue
            outcome = oc["outcome"]
            out_ext = outcome.get("extIds", "")
            bSId = ""
            if out_ext and "," in out_ext:
                parts = out_ext.split(",")
                if len(parts) >= 2:
                    bSId = parts[1]

            price = {}
            if "children" in outcome and outcome["children"]:
                price_obj = outcome["children"][0].get("price", {})
                # Preserve decimal price when available, otherwise keep fractional
                price = {
                    "num": price_obj.get("priceNum", "0"),
                    "den": price_obj.get("priceDen", "1"),
                    "priceDec": price_obj.get("priceDec"),
                }

            results.append({
                "outcome_id": outcome.get("id"),
                "name": outcome.get("name"),
                "sub_event_id": market.get("eventId"),
                "market_id": market.get("id"),
                "bMId": bMId,
                "bSId": bSId,
                "price": price,
            })

    return results


def find_over_under_outcome(drilldown: Dict, handicap: str = "0.5", side: str = "Over") -> Optional[Dict]:
    """Find the Over/Under Total Goals market for the given handicap and return the outcome for side ('Over' or 'Under')."""
    ss = drilldown.get("SSResponse", {})
    children = ss.get("children", [])
    if not children:
        return None

    event = children[0].get("event", {})
    for child in event.get("children", []):
        if "market" not in child:
            continue
        market = child["market"]
        name = market.get("name", "").strip()
        # Only accept the exact full-match market name, e.g. 'Over/Under Total Goals 0.5'
        exact_name = f"Over/Under Total Goals {handicap}"
        if name != exact_name:
            continue

        market_ext_ids = market.get("extIds", "")
        bMId = ""
        if market_ext_ids and "," in market_ext_ids:
            parts = market_ext_ids.split(",")
            if len(parts) >= 2:
                bMId = parts[1]

        for oc in market.get("children", []):
            if "outcome" not in oc:
                continue
            outcome = oc["outcome"]
            if outcome.get("name", "").lower() != side.lower():
                continue

            out_ext = outcome.get("extIds", "")
            bSId = ""
            if out_ext and "," in out_ext:
                parts = out_ext.split(",")
                if len(parts) >= 2:
                    bSId = parts[1]

            price = {}
            if "children" in outcome and outcome["children"]:
                price_obj = outcome["children"][0].get("price", {})
                price = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1"), "priceDec": price_obj.get("priceDec")}

            return {
                "outcome_id": outcome.get("id"),
                "name": outcome.get("name"),
                "sub_event_id": market.get("eventId"),
                "market_id": market.get("id"),
                "bMId": bMId,
                "bSId": bSId,
                "price": price,
                "handicap": str(handicap),
            }

    return None


def main(match_id: int = MATCH_ID_DEFAULT) -> None:
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("test_build_combos")

    client = LadbrokesAlerts()
    log.info("Fetching drilldown for match %s", match_id)
    drilldown = client.get_bet_ids_for_match(match_id, use_cache=False, verbose=True)
    cache_file = f"ladbrokes_drilldown_{match_id}.json"
    log.info("Drilldown cached to %s", cache_file)
    if not drilldown:
        log.error("Failed to fetch drilldown data")
        return

    event_bEId = extract_event_bEId(drilldown)
    log.info("event_bEId=%s", event_bEId)

    first_goals = find_market_outcomes(drilldown, "First Goalscorer")
    anytime_goals = find_market_outcomes(drilldown, "Anytime Goalscorer")

    if not first_goals:
        log.warning("No First Goalscorer market found")
    if not anytime_goals:
        log.warning("No Anytime Goalscorer market found")

    # Only build combos for the same player across both markets.
    def _norm(name: Optional[str]) -> str:
        if not name:
            return ""
        return " ".join(name.strip().split()).lower()

    # Build maps name->outcome for each market
    first_map = { _norm(o.get("name")): o for o in first_goals if _norm(o.get("name")) }
    anytime_map = { _norm(o.get("name")): o for o in anytime_goals if _norm(o.get("name")) }

    # Remove generic non-player entries
    for bad in ("no goalscorer", "no goalscorer - any time"):
        first_map.pop(bad, None)
        anytime_map.pop(bad, None)

    common = sorted(set(first_map.keys()) & set(anytime_map.keys()))
    log.info("Found %d matching players in both markets", len(common))

    # locate Over/Under 0.5 Over outcome once
    over0 = find_over_under_outcome(drilldown, handicap="0.5", side="Over")
    if not over0:
        log.warning("No Over/Under 0.5 'Over' market found; aborting AGS combos")
        client.close()
        return

    # price -> float helper (prefer priceDec)
    def _price_to_float(price_obj: dict) -> Optional[float]:
        try:
            dec = price_obj.get("priceDec")
            if dec is not None:
                return float(dec)
            num = float(price_obj.get("num", 0))
            den = float(price_obj.get("den", 1))
            if den == 0:
                return None
            return num / den
        except Exception:
            return None

    return {
        "client": client,
        "drilldown": drilldown,
        "event_bEId": event_bEId,
        "first_map": first_map,
        "anytime_map": anytime_map,
        "common": common,
        "over0": over0,
    }


def run_combos(state: dict, match_id: int) -> None:
    """Run combo requests and print comparisons."""
    client = state.get("client")
    first_map = state.get("first_map", {})
    anytime_map = state.get("anytime_map", {})
    common = state.get("common", [])
    over0 = state.get("over0")
    event_bEId = state.get("event_bEId")

    def _price_to_float(price_obj: dict) -> Optional[float]:
        try:
            dec = price_obj.get("priceDec")
            if dec is not None:
                return float(dec)
            num = float(price_obj.get("num", 0))
            den = float(price_obj.get("den", 1))
            if den == 0:
                return None
            return num / den
        except Exception:
            return None

    for name in common:
        a = first_map[name]
        b = anytime_map[name]
        leg_a = client.create_leg_from_outcome(a, event_bEId=event_bEId)
        leg_b = client.create_leg_from_outcome(b, event_bEId=event_bEId)
        leg_over = client.create_leg_from_outcome(over0, event_bEId=event_bEId)

        single_odds = _price_to_float(a.get("price", {}))
        anytime_odds = _price_to_float(b.get("price", {}))

        # AGS combo: Anytime + Over0.5 (2-leg)
        ags_payload = client.build_bet_request(match_id, [leg_b, leg_over])
        ags_combo_odds = client.get_back_odds(ags_payload, debug=False)

        # FGS combo: FGS + AGS (Anytime) -> 2-leg
        fgs_combo_payload = client.build_bet_request(match_id, [leg_a, leg_b])
        fgs_combo_odds = client.get_back_odds(fgs_combo_payload, debug=False)

        def fmt(o):
            return f"{o:.2f}" if isinstance(o, (int, float)) else (str(o) if o is not None else "None")

        display_name = a.get("name") or b.get("name")

        # Indicate if the FGS combo (FGS+Anytime) is lower/higher than standalone FGS
        lower = False
        higher = False
        try:
            if isinstance(fgs_combo_odds, (int, float)) and isinstance(single_odds, (int, float)):
                lower = fgs_combo_odds < single_odds
                higher = fgs_combo_odds > single_odds
        except Exception:
            lower = higher = False

        note = "(fgs combo higher)" if higher else ("(fgs combo lower)" if lower else "")

        print(
            f"Player: {display_name} — FGS: {fmt(single_odds)} | AGS(Anytime): {fmt(anytime_odds)} | AGS(combo: Anytime+Over0.5): {fmt(ags_combo_odds)} | FGS+AGS(combo): {fmt(fgs_combo_odds)} {note}"
        )

    client.close()


def _print_ids_state(state: dict) -> None:
    client = state.get("client")
    first_map = state.get("first_map", {})
    anytime_map = state.get("anytime_map", {})
    common = state.get("common", [])
    over0 = state.get("over0")

    print("event_bEId:", state.get("event_bEId"))
    print("\nOver/Under 0.5 (Over):")
    if over0:
        print(f"  market_id={over0.get('market_id')} outcome_id={over0.get('outcome_id')} bMId={over0.get('bMId')} bSId={over0.get('bSId')} priceDec={over0.get('price', {}).get('priceDec')}")
    else:
        print("  <not found>")

    print("\nPlayers found in both First/Anytime markets:")
    for name in common:
        f = first_map.get(name, {})
        a = anytime_map.get(name, {})
        print(f"- {name}")
        print(f"    FGS: outcome_id={f.get('outcome_id')} market_id={f.get('market_id')} bMId={f.get('bMId')} bSId={f.get('bSId')} priceDec={f.get('price', {}).get('priceDec')}")
        print(f"    AGS(Anytime): outcome_id={a.get('outcome_id')} market_id={a.get('market_id')} bMId={a.get('bMId')} bSId={a.get('bSId')} priceDec={a.get('price', {}).get('priceDec')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test build combos (ladbrokes)")
    parser.add_argument("match_id", nargs="?", type=int, default=MATCH_ID_DEFAULT)
    parser.add_argument("--print-ids", action="store_true", help="Only fetch drilldown and print market/outcome IDs; do not call buildBet")
    args = parser.parse_args()

    state = main(args.match_id)
    if args.print_ids:
        _print_ids_state(state)
        # close client after printing
        state.get("client").close()
    else:
        run_combos(state, args.match_id)
