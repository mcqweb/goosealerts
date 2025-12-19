"""Clean Ladbrokes alerts client copied from previous implementation.

This is a self-contained client which implements the useful parts of
`existing_class.py` so that the final project does not depend on that
file. It prefers `tls_client` if available, otherwise falls back to
`requests`.
"""

import gzip
import json
import logging
import os
import zlib
from typing import Any, Dict, List, Optional

try:
    import tls_client
    _HAS_TLS_CLIENT = True
except Exception:
    import requests
    _HAS_TLS_CLIENT = False

from .config import LadbrokesConfig, _get_nord_proxy

logger = logging.getLogger(__name__)


class LadbrokesAlerts:
    """Handler for fetching Ladbrokes Bet Builder odds and drilldown markets.

    Methods mirror the previous implementation but are cleaned up and
    made self-contained.
    """

    def __init__(self, config: Optional[LadbrokesConfig] = None):
        self.config = config or LadbrokesConfig()
        self.build_bet_url = "https://betting-ms.ladbrokes.com/v1/buildBet"
        self.drilldown_url_template = (
            "https://ss-aka-ori.ladbrokes.com/openbet-ssviewer/Drilldown/2.86/EventToOutcomeForEvent/{}"
            "?scorecast=true&translationLang=en&responseFormat=json&referenceEachWayTerms=true"
        )

        proxy = self.config.proxy or _get_nord_proxy()

        if _HAS_TLS_CLIENT:
            self.session = tls_client.Session()
            if proxy:
                # tls_client expects a single proxy string
                self.session.proxies = proxy
        else:
            self.session = requests.Session()
            if proxy:
                # requests accepts a dict
                self.session.proxies = {"http": proxy, "https": proxy}

        # Default headers used when building bet request
        self.user_agent = "goosealerts/ladbrokes-module"

    def get_headers(self) -> Dict[str, str]:
        return {
            "authority": "betting-ms.ladbrokes.com",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "cache-control": "no-cache",
            "origin": "https://www.ladbrokes.com",
            "pragma": "no-cache",
            "referer": "https://www.ladbrokes.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.user_agent,
        }

    def get_bet_ids_for_match(self, ladbrokes_match_id: int, use_cache: bool = True, verbose: bool = False) -> Optional[Dict]:
        cache_file = f"ladbrokes_drilldown_{ladbrokes_match_id}.json"

        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if verbose:
                        logger.info("Loaded cached drilldown data from %s", cache_file)
                    return data
            except Exception as e:
                if verbose:
                    logger.warning("Failed to load cache %s: %s", cache_file, e)

        url = self.drilldown_url_template.format(ladbrokes_match_id)

        try:
            if _HAS_TLS_CLIENT:
                # tls_client.Session.get doesn't accept the `timeout` kw forwarded
                r = self.session.get(url)
            else:
                r = self.session.get(url, timeout=15)
            status = getattr(r, "status_code", None)
            if status is not None and status != 200:
                logger.warning("Failed to fetch bet IDs: HTTP %s", status)
                return None

            data = r.json() if hasattr(r, "json") else json.loads(r.text)

            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                logger.info("Saved drilldown data to %s", cache_file)
            except Exception as e:
                logger.warning("Failed to save cache %s: %s", cache_file, e)

            return data

        except Exception as e:
            logger.exception("Error fetching bet IDs")
            return None

    def parse_markets(self, drilldown_data: Dict) -> Dict:
        markets = {
            "match_betting": {},
            "btts": {},
            "2up_win": {},
            "double_chance": {},
            "over_under": {},
        }

        if "SSResponse" not in drilldown_data:
            return markets

        ss_response = drilldown_data["SSResponse"]
        if "children" not in ss_response or not ss_response["children"]:
            return markets

        first_child = ss_response["children"][0]
        if "event" not in first_child:
            return markets

        event = first_child["event"]
        if "children" not in event:
            return markets

        event_ext_ids = event.get("extIds", "")
        event_bEId = ""
        if event_ext_ids:
            parts = event_ext_ids.split(",")
            if len(parts) >= 2:
                event_bEId = parts[1]

        markets["event_bEId"] = event_bEId

        for child in event["children"]:
            if "market" not in child:
                continue

            market = child["market"]
            market_name = market.get("name", "")
            market_ext_ids = market.get("extIds", "")
            market_bMId = ""
            if market_ext_ids:
                parts = market_ext_ids.split(",")
                if len(parts) >= 2:
                    market_bMId = parts[1]

            if market_name == "Match Betting":
                for oc in market.get("children", []):
                    if "outcome" not in oc:
                        continue
                    outcome = oc["outcome"]
                    outcome_code = outcome.get("outcomeMeaningMinorCode", "")
                    outcome_name = outcome.get("name", "")
                    if outcome_code in ["H", "A", "D"]:
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}

                        ext_ids = outcome.get("extIds", "")
                        bSId = ""
                        if ext_ids:
                            parts = ext_ids.split(",")
                            if len(parts) >= 2:
                                bSId = parts[1]

                        code_map = {"H": "HOME", "A": "AWAY", "D": "DRAW"}
                        markets["match_betting"][code_map[outcome_code]] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data,
                        }

            elif market_name == "Both Teams to Score":
                for oc in market.get("children", []):
                    if "outcome" not in oc:
                        continue
                    outcome = oc["outcome"]
                    outcome_name = outcome.get("name", "")
                    if outcome_name in ["Yes", "No"]:
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}
                        ext_ids = outcome.get("extIds", "")
                        bSId = ""
                        if ext_ids:
                            parts = ext_ids.split(",")
                            if len(parts) >= 2:
                                bSId = parts[1]

                        markets["btts"][outcome_name] = {
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data,
                        }

            elif market_name == "2Up&Win - Early Payout":
                for oc in market.get("children", []):
                    if "outcome" not in oc:
                        continue
                    outcome = oc["outcome"]
                    outcome_code = outcome.get("outcomeMeaningMinorCode", "")
                    outcome_name = outcome.get("name", "")
                    if outcome_code in ["H", "A"]:
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}
                        ext_ids = outcome.get("extIds", "")
                        bSId = ""
                        if ext_ids:
                            parts = ext_ids.split(",")
                            if len(parts) >= 2:
                                bSId = parts[1]
                        code_map = {"H": "HOME", "A": "AWAY"}
                        markets["2up_win"][code_map[outcome_code]] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data,
                        }

            elif market_name == "Double chance":
                for oc in market.get("children", []):
                    if "outcome" not in oc:
                        continue
                    outcome = oc["outcome"]
                    outcome_name = outcome.get("name", "")
                    price_data = {}
                    if "children" in outcome and outcome["children"]:
                        price_obj = outcome["children"][0].get("price", {})
                        price_data = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}
                    ext_ids = outcome.get("extIds", "")
                    bSId = ""
                    if ext_ids:
                        parts = ext_ids.split(",")
                        if len(parts) >= 2:
                            bSId = parts[1]
                    if "or" in outcome_name.lower():
                        outcome_key = outcome_name.replace(" or ", "_").upper()
                        markets["double_chance"][outcome_key] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data,
                        }

            elif market_name.startswith("Over/Under Total Goals") and "First Half" not in market_name and "Second Half" not in market_name:
                # accept any numeric handicap (including 0.5) rather than a hardcoded list
                handicap = market.get("rawHandicapValue", "") or market.get("handicap", "") or ""
                try:
                    float(handicap)
                except Exception:
                    # non-numeric or missing handicap, skip
                    continue

                for oc in market.get("children", []):
                        if "outcome" not in oc:
                            continue
                        outcome = oc["outcome"]
                        outcome_name = outcome.get("name", "")
                        if outcome_name in ["Over", "Under"]:
                            price_data = {}
                            if "children" in outcome and outcome["children"]:
                                price_obj = outcome["children"][0].get("price", {})
                                price_data = {"num": price_obj.get("priceNum", "0"), "den": price_obj.get("priceDen", "1")}
                            ext_ids = outcome.get("extIds", "")
                            bSId = ""
                            if ext_ids:
                                parts = ext_ids.split(",")
                                if len(parts) >= 2:
                                    bSId = parts[1]
                            markets["over_under"][f"{outcome_name} {handicap}"] = {
                                "outcome_id": outcome.get("id"),
                                "market_id": market.get("id"),
                                "bMId": market_bMId,
                                "sub_event_id": market.get("eventId"),
                                "bSId": bSId,
                                "price": price_data,
                                "handicap": handicap,
                            }

        return markets

    def create_leg_from_outcome(self, outcome_data: Dict, event_bEId: str = "") -> Dict:
        price = outcome_data.get("price", {})
        leg_part = [{"outcomeRef": {"id": str(outcome_data["outcome_id"])}}]

        if outcome_data.get("handicap"):
            handicap = outcome_data["handicap"]
            leg_part[0]["range"] = {
                "low": handicap,
                "high": handicap,
                "rangeTypeRef": {"id": "HIGHER_LOWER"},
            }

        bEId = event_bEId
        if event_bEId and "," in event_bEId:
            parts = event_bEId.split(",")
            if len(parts) >= 2:
                bEId = parts[1]

        return {
            "sportsLeg": {
                "price": {"num": int(price.get("num", 0)), "den": int(price.get("den", 1)), "priceTypeRef": {"id": "LP"}},
                "legPart": leg_part,
                "winPlaceRef": {"id": "WIN"},
            },
            "bEId": bEId if bEId else f"2:{outcome_data['sub_event_id']}",
            "oSId": str(outcome_data["outcome_id"]),
            "bMId": str(outcome_data.get("bMId", "")),
            "bSId": str(outcome_data.get("bSId", "")),
            "sportId": "16",
        }

    def build_bet_request(self, ladbrokes_match_id: int, legs: List[Dict]) -> Dict:
        body = {"channelRef": {"id": "I"}, "leg": [], "legGroup": [], "returnOffers": "N", "byb": []}

        for idx, leg in enumerate(legs, 1):
            body["leg"].append({"documentId": idx, "sportsLeg": leg["sportsLeg"]})
            body["legGroup"].append({"legRef": [{"documentId": idx}]})

        if len(legs) > 1:
            body["legGroup"].append({"legRef": [{"documentId": i} for i in range(1, len(legs) + 1)]})

        for idx, leg in enumerate(legs, 1):
            body["byb"].append({
                "oEId": ladbrokes_match_id,
                "bEId": leg.get("bEId", ""),
                "oSId": leg.get("oSId", ""),
                "bMId": leg.get("bMId", ""),
                "bSId": leg.get("bSId", ""),
                "sportId": leg.get("sportId", "16"),
                "documentId": idx,
            })

        return body

    def get_back_odds(self, payload: Dict, debug: bool = False) -> Optional[float]:
        try:
            if debug:
                with open("ladbrokes_payload_debug.json", "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)

            if _HAS_TLS_CLIENT:
                r = self.session.post(self.build_bet_url, headers=self.get_headers(), json=payload)
            else:
                r = self.session.post(self.build_bet_url, headers=self.get_headers(), json=payload, timeout=15)
            status = getattr(r, "status_code", None)
            if status is not None and status >= 400:
                logger.warning("Failed to fetch odds: HTTP %s", status)
                return None

            content = getattr(r, "content", None) or getattr(r, "text", "")
            if isinstance(content, bytes):
                encoding = (r.headers.get("Content-Encoding") or "").lower()
                if encoding == "gzip":
                    content = gzip.decompress(content).decode("utf-8")
                elif encoding == "deflate":
                    content = zlib.decompress(content).decode("utf-8")
                else:
                    try:
                        content = content.decode("utf-8")
                    except Exception:
                        content = content.decode("latin-1", errors="ignore")

            data = json.loads(content) if isinstance(content, str) else content

            if "bets" in data:
                for bet in data["bets"]:
                    if bet.get("betTypeRef", {}).get("id") == "BB":
                        if "betErrors" in bet:
                            return None
                        payout = bet.get("payout", [])
                        if payout and len(payout) > 0:
                            potential = payout[0].get("potential")
                            if potential:
                                return float(potential)

            return None

        except Exception as e:
            logger.exception("Error fetching back odds")
            return None

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    c = LadbrokesAlerts()
    print(c.get_bet_ids_for_match(7708666, use_cache=False, verbose=True))
    sys.exit(0)
