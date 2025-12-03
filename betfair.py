import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import json
import os
import csv

# Try to load local .env so BETFAIR_DEBUG_SAVE and other opts in .env are available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except Exception:
    # fallback: simple parser (don't override existing env vars)
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

# Ensure data folder and whitelist CSV exist on import so callers see the file immediately
_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(_DATA_DIR, exist_ok=True)
_WHITELIST_FILE = os.path.join(_DATA_DIR, 'competitions_whitelist.csv')
if not os.path.exists(_WHITELIST_FILE):
    try:
        with open(_WHITELIST_FILE, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=['comp_id', 'comp_name', 'active'])
            writer.writeheader()
    except Exception:
        # Best-effort creation on import; don't crash import if filesystem prevents it
        pass


class Betfair():
    """Betfair exchange implementation (read-only, no login).

    This is a self-contained template focused on fetching competitions,
    matches and player markets. It deliberately avoids DB/alias logic.
    """

    def __init__(self):
        self.api_url = "https://ero.betfair.com/www/sports/exchange/readonly/v1/"
        self.search_url = "https://scan-inbf.betfair.com/www/sports/navigation/facet/v1/search?alt=json"
        self.proxies = None  # e.g., {"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"}
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "origin": "https://www.betfair.com",
            "referer": "https://www.betfair.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
        }
        self.AGS_MARKET_NAME = "TO_SCORE"
        self.FGS_MARKET_NAME = "FIRST_GOAL_SCORER"
        # ensure the whitelist CSV exists (header written) so callers see the file immediately
        try:
            self.ensure_whitelist_exists()
        except Exception:
            # don't fail construction if filesystem is read-only; callers can create later
            pass
        # debug JSON saving toggle (constructor arg could be added later). Default from env var.
        self.debug_save = os.getenv('BETFAIR_DEBUG_SAVE', '').strip().lower() in ('1', 'true', 'yes')
        # minimum lay size threshold (currency). Only consider lays above this size.
        try:
            self.min_lay_size = float(os.getenv('GBP_THRESHOLD_GOOSE', '0') or 0)
        except Exception:
            self.min_lay_size = 0.0
        # debug directory inside the project (created only if debug_save enabled)
        self.debug_dir = os.path.join(os.path.dirname(__file__), 'debug')
        if self.debug_save:
            try:
                os.makedirs(self.debug_dir, exist_ok=True)
            except Exception:
                # best-effort
                self.debug_save = False

    def fetch_competitions(self) -> List[Dict[str, Any]]:
        params = {
            "filter": {
                "marketBettingTypes": ["ODDS"],
                "eventTypeIds": [1],
                "productTypes": ["EXCHANGE"],
                "marketTypeCodes": [],
                "selectBy": "MAXIMUM_TRADED",
                "contentGroup": {"language": "en", "regionCode": "UK"},
                "attachments": [],
                "maxResults": 0
            },
            "facets": [
                {"type": "COMPETITION", "maxValues": 50, "skipValues": 0}
            ],
            "currencyCode": "GBP",
            "locale": "en_GB"
        }

        r = requests.post(self.search_url, headers=self.headers, json=params, proxies=self.proxies)
        r.raise_for_status()
        data = r.json()
        if getattr(self, 'debug_save', False):
            try:
                self._maybe_save_debug(f"competitions", data)
            except Exception:
                pass
        competitions = []
        competitions_data = data.get('attachments', {}).get('competitions', {})
        for comp_id, comp_data in competitions_data.items():
            competitions.append({'id': comp_id, 'name': comp_data.get('name', ''), 'competition': comp_data.get('name', '')})
        return competitions

    def fetch_matches_for_competition(self, competition_id: str, cached=True) -> List[Dict[str, Any]]:
        params = {
                "filter": {
                    "marketBettingTypes": [
                        "ODDS"
                    ],
                    "competitionIds": [
                        int(competition_id)
                    ],
                    "productTypes": [
                        "EXCHANGE"
                    ],
                    "marketTypeCodes": [],
                    "selectBy": "MAXIMUM_TRADED",
                    "contentGroup": {
                        "language": "en",
                        "regionCode": "UK"
                    },
                    "attachments": [],
                    "maxResults": 0
                },
                "facets": [
                    {
                        "type": "COMPETITION",
                        "maxValues": 1,
                        "skipValues": 0,
                        "applyNextTo": 0
                    },
                    {
                        "type": "MARKET",
                        "maxValues": 5,
                        "skipValues": 0,
                        "applyNextTo": 0,
                        "next": {
                            "type": "EVENT",
                            "maxValues": 1,
                            "skipValues": 0,
                            "applyNextTo": 0
                        }
                    },
                    {
                        "type": "MARKET_TYPE",
                        "maxValues": 0,
                        "skipValues": 0,
                        "applyNextTo": 0,
                        "values": [
                            "TO_SCORE"
                        ],
                        "next": {
                            "type": "MARKET",
                            "maxValues": 5,
                            "skipValues": 0,
                            "applyNextTo": 0,
                            "next": {
                                "type": "EVENT",
                                "maxValues": 1,
                                "skipValues": 0,
                                "applyNextTo": 0
                            }
                        }
                    },
                    {
                        "type": "MARKET_LEVEL",
                        "maxValues": 0,
                        "skipValues": 0,
                        "applyNextTo": 0,
                        "values": [
                            "COMPETITION",
                            "SUB_COMPETITION"
                        ],
                        "next": {
                            "type": "MARKET",
                            "maxValues": 3,
                            "skipValues": 0,
                            "applyNextTo": 0,
                            "next": {
                                "type": "EVENT",
                                "maxValues": 1,
                                "skipValues": 0,
                                "applyNextTo": 0
                            }
                        }
                    },
                    {
                        "type": "EVENT_TYPE",
                        "maxValues": 1,
                        "skipValues": 0,
                        "applyNextTo": 0
                    }
                ],
                "currencyCode": "GBP",
                "locale": "en_GB"
            }
        # Try reuse cached search response if requested (use `cache/` directory)
        cache_dir = os.path.join(os.path.dirname(__file__),  "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_file = os.path.join(cache_dir, f"events_comp_{competition_id}.json")
        data = None
        if cached:
            try:
                if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
                    with open(cached_file, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)

            except Exception:
                data = None

        # If no fresh cache, perform the network request and save the result to cache
        if data is None:
            r = requests.post(self.search_url, headers=self.headers, json=params, proxies=self.proxies)
            r.raise_for_status()
            data = r.json()
            # always persist a cached copy for reuse
            try:
                with open(cached_file, 'w', encoding='utf-8') as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            except Exception:
                print(f"Warning: failed to save cached events for competition {competition_id}")
                exit()
                pass
            if getattr(self, 'debug_save', False):
                try:
                    self._maybe_save_debug(f"events_comp_{competition_id}", data)
                except Exception:
                    pass
        matches = []
        events_data = data.get('attachments', {}).get('events', {})
        markets_data = data.get('attachments', {}).get('markets', {}) # New: Retrieve markets data

        for event_id, event_data in events_data.items():
            open_date = event_data.get('openDate')
            # collect any market nodes included in the event payload (if present)
            market_nodes = []
            # try the common key
            if isinstance(event_data, dict):
                # some payloads embed marketNodes directly
                mnodes = event_data.get('marketNodes') or event_data.get('marketNodes', [])
                if isinstance(mnodes, list):
                    market_nodes.extend(mnodes)
                # some payloads may include attachments with markets
                attachments = event_data.get('attachments', {})
                if isinstance(attachments, dict):
                    for k in ('markets', 'marketNodes'):
                        am = attachments.get(k)
                        if isinstance(am, dict):
                            for mk, mv in am.items():
                                market_nodes.append(mv)
                        elif isinstance(am, list):
                            market_nodes.extend(am)

            if open_date:
                try:
                    match_time = datetime.fromisoformat(open_date.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    if now <= match_time <= now + timedelta(days=5):
                        matches.append({'id': event_id, 'name': event_data.get('name', ''), 'openDate': open_date, 'competitionId': event_data.get('competitionId', competition_id), 'market_nodes': market_nodes})
                except Exception:
                    continue

        # Create a set of event IDs found in the first pass for quick lookup
        future_event_ids = {match['id'] for match in matches} 
        
        # Store the TO_SCORE market for each event ID
        event_to_score_markets = {}

        for market_id, market_data in markets_data.items():
            market_event_id = str(market_data.get('eventId')) # Ensure comparison is with string ID
            market_type = market_data.get('marketType')
            
            # Check if the market belongs to one of the future events and is the 'TO_SCORE' type
            if market_event_id in future_event_ids and (market_type == self.AGS_MARKET_NAME or market_type == self.FGS_MARKET_NAME):
                # Collect the market node. Since you want it as 'market_nodes', 
                # and you're looking for one specific market, we'll store it as a list 
                # for consistency with the original structure.
                event_to_score_markets[market_event_id] = [market_data]

        # 3. Final step: Update the 'matches' list with the 'TO_SCORE' market nodes
        final_matches = []
        for match in matches:
            event_id = match['id']
            # If we found the TO_SCORE market for this event, update the 'market_nodes' key
            if event_id in event_to_score_markets:
                match['market_nodes'] = event_to_score_markets[event_id]
                final_matches.append(match) # Only keep matches that have the market
            
        return final_matches    

    def parse_team_names(self, match_data: Dict) -> tuple[str, str]:
        match_name = match_data.get('name', '')
        if ' v ' in match_name:
            parts = match_name.split(' v ')
            return parts[0].strip(), parts[1].strip()
        for separator in [' vs ', ' - ']:
            if separator in match_name:
                parts = match_name.split(separator)
                return parts[0].strip(), parts[1].strip()
        return match_name, ''

    def parse_competition(self, match_data: Dict) -> str:
        return match_data.get('competitionId', '')

    def get_match_id(self, match_data: Dict) -> str:
        return str(match_data.get('id'))

    def get_kickoff_time(self, match_data: Dict) -> str:
        return match_data.get('openDate')

    def fetch_odds_for_match(self, match_id: str, match: Optional[Dict] = None) -> List[Dict[str, Any]]:
        markets_url = f"{self.api_url}byevent"
        markets_params = {
            "currencyCode": "GBP",
            "eventIds": str(match_id),
            "locale": "en_GB",
            "rollupLimit": 10,
            "rollupModel": "STAKE",
            "types": "MARKET_STATE,EVENT,MARKET_DESCRIPTION"
        }

        r = requests.get(markets_url, headers=self.headers, params=markets_params, proxies=self.proxies)
        r.raise_for_status()
        markets_data = r.json()
        if getattr(self, 'debug_save', False):
            try:
                self._maybe_save_debug(f"markets_event_{match_id}", markets_data)
            except Exception:
                pass

        # cache raw response
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_file = os.path.join(cache_dir, f"betfair_markets_{match_id}.json")
        with open(cached_file, 'w', encoding='utf-8') as f:
            json.dump(markets_data, f, indent=2, ensure_ascii=False)

        supported_markets = {}
        for event_type in markets_data.get('eventTypes', []):
            for event_node in event_type.get('eventNodes', []):
                for market in event_node.get('marketNodes', []):
                    desc = market.get('description', {})
                    market_type = desc.get('marketType', '')
                    market_id = market.get('marketId', '')
                    if market_type == self.AGS_MARKET_NAME:
                        supported_markets[market_type] = {
                            'market_id': market_id,
                            'market_name': desc.get('marketName', ''),
                            'internal_market_name': "AGS"
                        }
                    if market_type == self.FGS_MARKET_NAME:
                        supported_markets[market_type] = {
                            'market_id': market_id,
                            'market_name': desc.get('marketName', ''),
                            'internal_market_name': "FGS"
                        }

        if not supported_markets:
            return []

        market_ids_to_fetch = [info['market_id'] for info in supported_markets.values()]
        all_odds = []
        for market_id in market_ids_to_fetch:
            odds = self._fetch_market_odds(market_id, supported_markets, match)
            all_odds.extend(odds)
        return all_odds

    def _fetch_market_odds(self, market_id: str, supported_markets: Dict, match: Optional[Dict]) -> List[Dict[str, Any]]:
        url = f"{self.api_url}bymarket"
        params = {
            'alt': 'json',
            'currencyCode': 'GBP',
            'locale': 'en_GB',
            'marketIds': market_id,
            'rollupLimit': '10',
            'rollupModel': 'STAKE',
            'types': 'MARKET_STATE,MARKET_RATES,MARKET_DESCRIPTION,EVENT,RUNNER_DESCRIPTION,RUNNER_STATE,RUNNER_EXCHANGE_PRICES_BEST,RUNNER_METADATA,MARKET_LICENCE,MARKET_LINE_RANGE_INFO'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, proxies=self.proxies)
            response.raise_for_status()
            data = response.json()
            if getattr(self, 'debug_save', False):
                try:
                    self._maybe_save_debug(f"market_{market_id}", data)
                except Exception:
                    pass
        except requests.RequestException:
            return []

        # cache market response
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_file = os.path.join(cache_dir, f"betfair_market_{market_id}.json")
        with open(cached_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        odds_list = []
        market_type = None
        internal_market_name = None
        for mtype, minfo in supported_markets.items():
            if minfo['market_id'] == market_id:
                market_type = mtype
                internal_market_name = minfo['internal_market_name']
                break

        if not market_type:
            return []

        for event_type in data.get('eventTypes', []):
            for event_node in event_type.get('eventNodes', []):
                for market_node in event_node.get('marketNodes', []):
                    if market_node.get('marketId') != market_id:
                        continue
                    runners = market_node.get('runners', [])
                    for runner in runners:
                        outcome = self._extract_outcome_name(runner, market_type, match)
                        if not outcome:
                            continue
                        price, size = self._extract_best_lay(runner)
                        if price > 0 and size >= getattr(self, 'min_lay_size', 0.0):
                            odds_list.append({'market': internal_market_name, 'market_type': market_type, 'outcome': outcome, 'odds': price, 'size': size})
        return odds_list

    def _extract_outcome_name(self, runner: Dict, market_type: str, match: Optional[Dict]) -> str:
        runner_desc = runner.get('description', {})
        outcome = runner_desc.get('runnerName', '')
        return outcome or ''

    def _extract_best_lay(self, runner: Dict) -> tuple[float, float]:
        """Return (price, size) of best lay available for runner, or (0.0, 0.0) if none."""
        exchange = runner.get('exchange', {})
        available_to_lay = exchange.get('availableToLay', [])
        if not available_to_lay:
            return 0.0, 0.0
        try:
            # best lay defined as lowest lay price
            best_lay = min(available_to_lay, key=lambda x: x.get('price', float('inf')))
            price = float(best_lay.get('price', 0) or 0)
            size = float(best_lay.get('size', 0) or 0)
            return price, size
        except (ValueError, TypeError):
            return 0.0, 0.0

    # --- Whitelist helpers (CSV) integrated on the class ---
    def _whitelist_path(self) -> str:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, 'competitions_whitelist.csv')

    def ensure_whitelist_exists(self) -> None:
        """Create the whitelist CSV with header if it doesn't already exist."""
        path = self._whitelist_path()
        if not os.path.exists(path):
            with open(path, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.DictWriter(fh, fieldnames=['comp_id', 'comp_name', 'active'])
                writer.writeheader()

    def load_whitelist(self) -> List[Dict[str, Any]]:
        """Return list of whitelist rows as dicts: {'comp_id','comp_name','active'}"""
        path = self._whitelist_path()
        rows: List[Dict[str, Any]] = []
        if not os.path.exists(path):
            return rows
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                active = r.get('active', '').strip().upper() in ('TRUE', '1', 'YES')
                rows.append({'comp_id': r.get('comp_id', '').strip(), 'comp_name': r.get('comp_name', '').strip(), 'active': active})
        return rows

    def save_whitelist(self, rows: List[Dict[str, Any]]) -> None:
        path = self._whitelist_path()
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=['comp_id', 'comp_name', 'active'])
            writer.writeheader()
            for r in rows:
                writer.writerow({'comp_id': r.get('comp_id', ''), 'comp_name': r.get('comp_name', ''), 'active': 'TRUE' if r.get('active') else 'FALSE'})

    def sync_competitions_to_whitelist(self, competitions: List[Dict[str, Any]]) -> None:
        """Ensure any newly discovered competitions are added to the CSV with active=FALSE.

        competitions: list of dicts with keys 'id' and 'name' (as returned by fetch_competitions)
        Existing rows are preserved; comp_name is updated if changed.
        """
        existing = {r['comp_id']: r for r in self.load_whitelist()}
        changed = False
        for c in competitions:
            cid = str(c.get('id'))
            cname = c.get('name', '')
            if cid in existing:
                # update name if changed
                if existing[cid].get('comp_name') != cname:
                    existing[cid]['comp_name'] = cname
                    changed = True
            else:
                existing[cid] = {'comp_id': cid, 'comp_name': cname, 'active': False}
                changed = True

        if changed:
            rows = list(existing.values())
            # keep deterministic order by comp_id
            rows.sort(key=lambda x: x.get('comp_id'))
            self.save_whitelist(rows)

    def get_active_whitelisted_competitions(self) -> List[Dict[str, Any]]:
        """Return competitions flagged active=TRUE from the whitelist CSV."""
        rows = self.load_whitelist()
        return [r for r in rows if r.get('active')]

    # --- debug helper ---
    def _maybe_save_debug(self, prefix: str, data: Any) -> None:
        """Save JSON `data` to `debug/{prefix}_{timestamp}.json` if debug_save enabled."""
        if not getattr(self, 'debug_save', False):
            return
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
        fname = f"{prefix}_{ts}.json"
        path = os.path.join(self.debug_dir, fname)
        # write atomically
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        try:
            os.replace(tmp, path)
        except Exception:
            # best-effort cleanup
            try:
                os.remove(tmp)
            except Exception:
                pass



def _print_competition_list(comps: List[Dict[str, Any]], limit: Optional[int] = None) -> None:
    if limit is None:
        limit = len(comps)
    print(f"Found {len(comps)} competitions")
    for comp in comps[:limit]:
        cid = comp.get('id')
        name = comp.get('name')
        print(f"- {cid}: {name}")


def main() -> None:
    """Simple CLI entrypoint for quick inspection of competitions.

    Usage: python betfair_website.py --limit 10
    """
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Betfair competitions (read-only)")
    parser.add_argument('--limit', '-n', type=int, default=50, help='max competitions to show')
    args = parser.parse_args()
    WINDOW_MINUTES = int(os.getenv('WINDOW_MINUTES', '90') or 90)
    wf = Betfair()
    try:
        comps = wf.fetch_competitions()
    except Exception as e:
        print(f"Error fetching competitions: {e}")
        return
    _print_competition_list(comps, limit=args.limit)

    # Now list matches for competitions that are active in our whitelist
    active = wf.get_active_whitelisted_competitions()
    if not active:
        print("No active whitelisted competitions found (check data/competitions_whitelist.csv)")
        return
    exit()
    print('\nMatches for active whitelisted competitions:')
    for comp in active:
        cid = comp.get('comp_id')
        cname = comp.get('comp_name')
        print(f"\nCompetition {cid}: {cname}")
        try:
            matches = wf.fetch_matches_for_competition(cid)
        except Exception as e:
            print(f"  Error fetching matches for {cid}: {e}")
            continue
        if not matches:
            print("  No upcoming matches found for this competition")
            continue
        for m in matches:
            mid = m.get('id')
            mname = m.get('name')
            kickoff = m.get('openDate')
            print(f"  - {mid}: {mname} @ {kickoff}")
            # If the match is today (UTC), fetch odds for the TO_SCORE market
            try:
                if kickoff:
                    kt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                    now_utc = datetime.now(timezone.utc)
                    # consider matches within the next x minutes (inclusive)
                    if now_utc <= kt <= now_utc + timedelta(minutes=WINDOW_MINUTES):
                        print(f"    -> Match within next {WINDOW_MINUTES} minutes; fetching odds...")
                        # If the fetch_matches_for_competition response included market_nodes with TO_SCORE markets,
                        # call _fetch_market_odds directly using the known market id(s).
                        used_direct = False
                        mnodes = m.get('market_nodes') or []
                        if mnodes:
                            # build supported_markets mapping from nodes
                            supported = {}
                            for node in mnodes:
                                try:
                                    desc = node.get('description', {}) if isinstance(node, dict) else {}
                                    mtype = desc.get('marketType') or node.get('marketType') or ''
                                    midid = node.get('marketId') or node.get('market_id') or node.get('marketId')
                                    if (mtype == wf.FGS_MARKET_NAME or mtype == wf.AGS_MARKET_NAME) and midid:
                                        supported[mtype] = {'market_id': midid, 'market_name': desc.get('marketName', ''), 'internal_market_name': 'AGS'}
                                        # call _fetch_market_odds for this market id
                                        try:
                                            odds = wf._fetch_market_odds(str(midid), supported, m)
                                        except Exception as e:
                                            print(f"    Error fetching market {midid}: {e}")
                                            odds = []
                                        if odds:
                                            used_direct = True
                                            for o in odds:
                                                out = o.get('outcome')
                                                price = o.get('odds')
                                                size = o.get('size')
                                                mkt = o.get('market') or o.get('market_type')
                                                print(f"    - {mkt}: {out} @ {price} (size=£{size})")
                                except Exception:
                                    continue
                        if not used_direct:
                            print("FALLBACK")
                            # fallback to the existing fetch which will discover markets
                            try:
                                odds = wf.fetch_odds_for_match(mid, m)
                            except Exception as e:
                                print(f"    Error fetching odds for match {mid}: {e}")
                                odds = []
                            if not odds:
                                print("    No odds found for TO_SCORE markets (or market not available)")
                            else:
                                for o in odds:
                                    out = o.get('outcome')
                                    price = o.get('odds')
                                    size = o.get('size')
                                    mkt = o.get('market') or o.get('market_type')
                                    print(f"    - {mkt}: {out} @ {price} (size={size})")
            except Exception:
                # don't let a parse error break the listing
                pass


if __name__ == '__main__':
    main()

