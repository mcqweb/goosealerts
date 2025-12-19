"""Test script: build combos between First Goalscorer and Anytime Goalscorer.

Usage: run directly. By default uses Ladbrokes id 253579498.
"""

import logging
from itertools import product
from typing import Dict, List, Optional

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
    """Find outcomes for markets whose name contains `token` (case-insensitive).

    Returns list of outcome dicts with keys similar to the client's expectations:
    `outcome_id`, `name`, `sub_event_id`, `bMId`, `bSId`, `price`.
    """
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
                price = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}

            results.append({
                "outcome_id": outcome.get("id"),
                "name": outcome.get("name"),
                "sub_event_id": market.get("eventId"),
                "bMId": bMId,
                "bSId": bSId,
                "price": price,
            })

    return results


def main(match_id: int = MATCH_ID_DEFAULT) -> None:
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("test_build_combos")

    client = LadbrokesAlerts()
    log.info("Fetching drilldown for match %s", match_id)
    drilldown = client.get_bet_ids_for_match(match_id, use_cache=False, verbose=True)
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

    combos = list(product(first_goals, anytime_goals))
    log.info("Building %d combos", len(combos))

    results = []
    for a, b in combos:
        # Create legs and payload
        leg_a = client.create_leg_from_outcome(a, event_bEId=event_bEId)
        leg_b = client.create_leg_from_outcome(b, event_bEId=event_bEId)
        payload = client.build_bet_request(match_id, [leg_a, leg_b])
        odds = client.get_back_odds(payload, debug=False)
        results.append({
            "first": a.get("name"),
            "anytime": b.get("name"),
            "odds": odds,
        })
        print(f"First: {a.get('name')!s} | Anytime: {b.get('name')!s} => odds: {odds}")

    client.close()


if __name__ == "__main__":
    main()
