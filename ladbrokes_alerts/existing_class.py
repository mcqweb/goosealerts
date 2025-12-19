class LadbrokesOddsComparison:
    """Handler for fetching Ladbrokes Bet Builder odds"""
    
    def __init__(self):
        self.build_bet_url = 'https://betting-ms.ladbrokes.com/v1/buildBet'
        self.drilldown_url_template = 'https://ss-aka-ori.ladbrokes.com/openbet-ssviewer/Drilldown/2.86/EventToOutcomeForEvent/{}?scorecast=true&translationLang=en&responseFormat=json&referenceEachWayTerms=true'
        
        # Setup Nord proxy
        proxy_dict = _get_nord_proxy()
        self.session = tls_client.Session()
        
        # Set proxy on session if available
        if proxy_dict:
            # tls_client expects proxy as a string, not dict
            self.session.proxies = proxy_dict
    
    def get_headers(self):
        """Return headers for API requests"""
        return {
            "authority": "betting-ms.ladbrokes.com",
            "method": "POST",
            "path": "/v1/buildBet",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "cache-control": "no-cache",
            "origin": "https://www.ladbrokes.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.ladbrokes.com/",
            "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
        }


    
    def get_bet_ids_for_match(self, ladbrokes_match_id: int, use_cache: bool = True, verbose: bool = True) -> Optional[Dict]:
        """
        Fetch available markets and outcomes for a match
        
        Args:
            ladbrokes_match_id: Ladbrokes event ID
            use_cache: Whether to use cached response if available
            
        Returns:
            Dictionary of market data with bet IDs
        """
        cache_file = f"ladbrokes_drilldown_{ladbrokes_match_id}.json"
        
        # Check if cached file exists
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if verbose:
                        print(f"[+] Loaded cached drilldown data from {cache_file}")
                    return data
            except Exception as e:
                if verbose:
                    print(f"[!] Failed to load cache: {e}, fetching fresh data...")
        
        url = self.drilldown_url_template.format(ladbrokes_match_id)
        
        try:
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"[-] Failed to fetch bet IDs: HTTP {response.status_code}")
                return None
            
            data = response.json()
            
            # Save to cache file
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"[*] Saved drilldown data to {cache_file}")
            except Exception as e:
                print(f"[!] Failed to save cache: {e}")
            
            return data
            
        except Exception as e:
            print(f"[-] Error fetching bet IDs: {e}")
            return None
    
    def parse_markets(self, drilldown_data: Dict) -> Dict:
        """
        Parse drilldown data to extract Match Betting and BTTS markets
        
        Args:
            drilldown_data: Response from drilldown API
            
        Returns:
            Dictionary with parsed market data
        """
        markets = {
            "match_betting": {},
            "btts": {},
            "2up_win": {},
            "double_chance": {},
            "over_under": {}
        }
        
        # Navigate to SSResponse.children[0].event.children
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
        
        # Extract event bEId from extIds (format: "BWIN_PG,2:7708666,")
        event_ext_ids = event.get("extIds", "")
        event_bEId = ""
        if event_ext_ids:
            parts = event_ext_ids.split(",")
            if len(parts) >= 2:
                event_bEId = parts[1]  # "2:7708666"
        
        # Store event bEId for use in leg creation
        markets["event_bEId"] = event_bEId
        
        # Now iterate through event.children to find markets
        for child in event["children"]:
            if "market" not in child:
                continue
            
            market = child["market"]
            market_name = market.get("name", "")
            
            # Extract market bMId from extIds (format: "BWIN_PG,190172767,")
            market_ext_ids = market.get("extIds", "")
            market_bMId = ""
            if market_ext_ids:
                parts = market_ext_ids.split(",")
                if len(parts) >= 2:
                    market_bMId = parts[1]
            
            # Parse Match Betting market
            if market_name == "Match Betting":
                for outcome_child in market.get("children", []):
                    if "outcome" not in outcome_child:
                        continue
                    
                    outcome = outcome_child["outcome"]
                    outcome_code = outcome.get("outcomeMeaningMinorCode", "")
                    outcome_name = outcome.get("name", "")
                    
                    # Look for H (Home), A (Away), D (Draw)
                    if outcome_code in ["H", "A", "D"]:
                        # Extract price from outcome.children[0].price
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {
                                "num": price_obj.get("priceNum", "0"),
                                "den": price_obj.get("priceDen", "1")
                            }
                        
                        # Extract bSId from extIds (format: "BWIN_PG,694961192,")
                        ext_ids = outcome.get("extIds", "")
                        bSId = ""
                        if ext_ids:
                            parts = ext_ids.split(",")
                            if len(parts) >= 2:
                                bSId = parts[1]
                        
                        # Map to HOME/AWAY/DRAW for consistency
                        code_map = {"H": "HOME", "A": "AWAY", "D": "DRAW"}
                        markets["match_betting"][code_map[outcome_code]] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data
                        }
            
            # Parse Both Teams To Score market
            elif market_name == "Both Teams to Score":
                for outcome_child in market.get("children", []):
                    if "outcome" not in outcome_child:
                        continue
                    
                    outcome = outcome_child["outcome"]
                    outcome_name = outcome.get("name", "")
                    
                    if outcome_name in ["Yes", "No"]:
                        # Extract price from outcome.children[0].price
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {
                                "num": price_obj.get("priceNum", "0"),
                                "den": price_obj.get("priceDen", "1")
                            }
                        
                        # Extract bSId from extIds (format: "BWIN_PG,694961192,")
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
                            "price": price_data
                        }
            
            # Parse 2Up&Win - Early Payout market
            elif market_name == "2Up&Win - Early Payout":
                for outcome_child in market.get("children", []):
                    if "outcome" not in outcome_child:
                        continue
                    
                    outcome = outcome_child["outcome"]
                    outcome_code = outcome.get("outcomeMeaningMinorCode", "")
                    outcome_name = outcome.get("name", "")
                    
                    # Look for H (Home), A (Away)
                    if outcome_code in ["H", "A"]:
                        # Extract price from outcome.children[0].price
                        price_data = {}
                        if "children" in outcome and outcome["children"]:
                            price_obj = outcome["children"][0].get("price", {})
                            price_data = {
                                "num": price_obj.get("priceNum", "0"),
                                "den": price_obj.get("priceDen", "1")
                            }
                        
                        # Extract bSId from extIds
                        ext_ids = outcome.get("extIds", "")
                        bSId = ""
                        if ext_ids:
                            parts = ext_ids.split(",")
                            if len(parts) >= 2:
                                bSId = parts[1]
                        
                        # Map to HOME/AWAY for consistency
                        code_map = {"H": "HOME", "A": "AWAY"}
                        markets["2up_win"][code_map[outcome_code]] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data
                        }
            
            # Parse Double Chance market
            elif market_name == "Double chance":
                for outcome_child in market.get("children", []):
                    if "outcome" not in outcome_child:
                        continue
                    
                    outcome = outcome_child["outcome"]
                    outcome_name = outcome.get("name", "")
                    
                    # Extract price from outcome.children[0].price
                    price_data = {}
                    if "children" in outcome and outcome["children"]:
                        price_obj = outcome["children"][0].get("price", {})
                        price_data = {
                            "num": price_obj.get("priceNum", "0"),
                            "den": price_obj.get("priceDen", "1")
                        }
                    
                    # Extract bSId from extIds
                    ext_ids = outcome.get("extIds", "")
                    bSId = ""
                    if ext_ids:
                        parts = ext_ids.split(",")
                        if len(parts) >= 2:
                            bSId = parts[1]
                    
                    # Store with simplified names for easy access
                    # "England or Draw" -> "HOME_DRAW"
                    # "Serbia or Draw" -> "AWAY_DRAW"
                    # "England or Serbia" -> "EITHER_TEAM"
                    if "or" in outcome_name.lower():
                        outcome_key = outcome_name.replace(" or ", "_").upper()
                        markets["double_chance"][outcome_key] = {
                            "name": outcome_name,
                            "outcome_id": outcome.get("id"),
                            "market_id": market.get("id"),
                            "bMId": market_bMId,
                            "sub_event_id": market.get("eventId"),
                            "bSId": bSId,
                            "price": price_data
                        }
            
            # Parse Over/Under Total Goals markets (full match only, exclude First Half and Second Half)
            elif market_name.startswith("Over/Under Total Goals") and "First Half" not in market_name and "Second Half" not in market_name:
                # Extract the handicap value (1.5, 2.5, 3.5, 4.5)
                handicap = market.get("rawHandicapValue", "")
                if handicap in ["1.5", "2.5", "3.5", "4.5"]:
                    for outcome_child in market.get("children", []):
                        if "outcome" not in outcome_child:
                            continue
                        
                        outcome = outcome_child["outcome"]
                        outcome_name = outcome.get("name", "")
                        
                        # Get "Over" and "Under" outcomes
                        if outcome_name in ["Over", "Under"]:
                            # Extract price from outcome.children[0].price
                            price_data = {}
                            if "children" in outcome and outcome["children"]:
                                price_obj = outcome["children"][0].get("price", {})
                                price_data = {
                                    "num": price_obj.get("priceNum", "0"),
                                    "den": price_obj.get("priceDen", "1")
                                }
                            
                            # Extract bSId from extIds
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
                                "handicap": handicap
                            }
        
        return markets
    
    def create_leg_from_outcome(self, outcome_data: Dict, event_bEId: str = "") -> Dict:
        """
        Create a leg configuration from outcome data
        
        Args:
            outcome_data: Outcome data from parsed markets
            event_bEId: Event bEId from drilldown data (full extIds string)
            
        Returns:
            Leg configuration dict
        """
        price = outcome_data.get("price", {})
        
        # Build legPart - handle both regular outcomes and range-based (Over/Under)
        leg_part = [{"outcomeRef": {"id": str(outcome_data["outcome_id"])}}]
        
        # For Over/Under markets, add range specification
        if outcome_data.get("handicap"):
            handicap = outcome_data["handicap"]
            leg_part[0]["range"] = {
                "low": handicap,
                "high": handicap,
                "rangeTypeRef": {"id": "HIGHER_LOWER"}
            }
        
        # Extract bEId from event_bEId (format: "BWIN_PG,2:7707915,")
        bEId = event_bEId
        if event_bEId and "," in event_bEId:
            parts = event_bEId.split(",")
            if len(parts) >= 2:
                bEId = parts[1]
        
        return {
            "sportsLeg": {
                "price": {
                    "num": int(price.get("num", 0)),
                    "den": int(price.get("den", 1)),
                    "priceTypeRef": {"id": "LP"}
                },
                "legPart": leg_part,
                "winPlaceRef": {"id": "WIN"}
            },
            "bEId": bEId if bEId else f"2:{outcome_data['sub_event_id']}",
            "oSId": str(outcome_data["outcome_id"]),
            "bMId": str(outcome_data.get("bMId", "")),
            "bSId": str(outcome_data.get("bSId", "")),
            "sportId": "16"
        }
    
    def build_bet_request(self, ladbrokes_match_id: int, legs: List[Dict]) -> Dict:
        """
        Build the bet request payload for given legs
        
        Args:
            ladbrokes_match_id: Ladbrokes event ID
            legs: List of leg configurations
            
        Returns:
            Request payload dict
        """
        body = {
            "channelRef": {"id": "I"},
            "leg": [],
            "legGroup": [],
            "returnOffers": "N",
            "byb": []
        }
        
        # Build legs
        for idx, leg in enumerate(legs, 1):
            body["leg"].append({
                "documentId": idx,
                "sportsLeg": leg["sportsLeg"]
            })
            
            # Add to legGroup (individual legs)
            body["legGroup"].append({"legRef": [{"documentId": idx}]})
        
        # Add combined legGroup at the end
        if len(legs) > 1:
            body["legGroup"].append({
                "legRef": [{"documentId": i} for i in range(1, len(legs) + 1)]
            })
        
        # Build byb entries
        for idx, leg in enumerate(legs, 1):
            body["byb"].append({
                "oEId": ladbrokes_match_id,
                "bEId": leg.get("bEId", ""),
                "oSId": leg.get("oSId", ""),
                "bMId": leg.get("bMId", ""),
                "bSId": leg.get("bSId", ""),
                "sportId": leg.get("sportId", "16"),
                "documentId": idx
            })
        
        return body
    
    def get_back_odds(self, payload: Dict, debug: bool = False) -> Optional[float]:
        """
        Get back odds from Ladbrokes for given bet builder
        
        Args:
            payload: Bet request payload
            debug: Whether to save payload to file for debugging
            
        Returns:
            Decimal odds or None
        """
        try:
            # Debug: Save payload if requested
            if debug:
                with open("ladbrokes_payload_debug.json", "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
            
            response = self.session.post(
                self.build_bet_url,
                headers=self.get_headers(),
                json=payload
            )
            
            if response.status_code >= 400:
                print(f"[-] Failed to fetch odds: HTTP {response.status_code}")
                return None
            
            content = response.content
            encoding = response.headers.get('Content-Encoding', '').lower()
            
            if encoding == 'gzip':
                import gzip
                content = gzip.decompress(content)
            elif encoding == 'deflate':
                import zlib
                content = zlib.decompress(content)
            
            data = json.loads(content)
            
            # Check for bet builder bet in bets array
            if "bets" in data:
                for bet in data["bets"]:
                    # Look for bet builder bet type
                    if bet.get("betTypeRef", {}).get("id") == "BB":
                        # Check for errors first
                        if "betErrors" in bet:
                            error_desc = bet["betErrors"].get("errorDesc", "Unknown error")
                            # Bet builder not available on this event
                            return None
                        
                        # Extract odds from payout
                        payout = bet.get("payout", [])
                        if payout and len(payout) > 0:
                            potential = payout[0].get("potential")
                            if potential:
                                return float(potential)
            
            return None
            
        except Exception as e:
            print(f"[-] Error fetching back odds: {e}")
            return None